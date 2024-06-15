import RenderPasses.ReprojectionPass.ReprojectionStruct;

namespace FullScreenPass
{
    #include "RenderGraph/BasePasses/FullScreenPass.vs.slang"
}
#include "Enums.h"


int2 getTextureDims(Texture2D tex, uint mip)
{
    uint w, h;
    tex.GetDimensions(w, h);
    return int2(w, h);
}

// Workaround for isnan() not working in slang.
bool isNaN(float f)
{
    uint u = asuint(f) & ~0x80000000u; // clear out the sign bit
    return (u > 0x7F800000);           // greater than Inf is NaN
}


cbuffer PerImageCB
{
    // Input buffers
    Texture2D<int4> gInputReprojectionTapWidthAndPrevPos;
    Texture2D gInputReprojectionW0123;
    Texture2D gInputReprojectionW4567;
    Texture2D gInputHistoryLength;
    Texture2D gInputVariance;

    // Output buffers
    RWTexture2D<float> gOutputSampleDensityWeight;

    // Parameters
    uint2 gResolution;
    float gMinVariance;
    float gMaxVariance;
};

struct History
{
    float length;
    float variance;
};

bool loadReprojectedHistory(int2 ipos, out History h)
{
    h.length = 0;
    h.variance = 0;

    const int4 reprojectionTapWidthAndPrevPos = gInputReprojectionTapWidthAndPrevPos[ipos];
    const float4 reprojectionW0123 = gInputReprojectionW0123[ipos];
    const float4 reprojectionW4567 = gInputReprojectionW4567[ipos];

    const Reprojection reprojection = toReprojectionStruct(reprojectionTapWidthAndPrevPos, reprojectionW0123, reprojectionW4567);

    if (reprojection.tapWidth == 2)
    {
        const int2 offset[4] = { int2(0, 0), int2(1, 0), int2(0, 1), int2(1, 1) };
        for (int i = 0; i < 4; i++)
        {
            const int2 loc = reprojection.iposPrev + offset[i];
            h.length += gInputHistoryLength[loc].x * reprojection.w[i];
            h.variance += gInputVariance[loc].x * reprojection.w[i];
        }
    }
    else if (reprojection.tapWidth == 3)
    {
        const int radius = 1;
        int i = 0;
        for (int yy = -radius; yy <= radius; yy++)
        {
            for (int xx = -radius; xx <= radius; xx++)
            {
                i++;
                const int2 loc = reprojection.iposPrev + int2(xx, yy);
                h.length += gInputHistoryLength[loc].x * reprojection.w[i];
                h.variance += gInputVariance[loc].x * reprojection.w[i];
            }
        }
    }

    if (isNaN(h.length) || isinf(h.length))
        h.length = 0;
    if (isNaN(h.variance) || isinf(h.variance))
        h.variance = 0;

    return reprojection.tapWidth > 0;
}

struct PS_OUT
{
    float weight : SV_Target0;
};

PS_OUT main(FullScreenPass.VsOut vsOut)
{
    const int2 ipos = int2(vsOut.posH.xy);

    History history;
    const bool valid = loadReprojectedHistory(ipos, history);
    const float variance = (history.length >= 1) ? max(history.variance, gMaxVariance / history.length) : gMaxVariance;
    const float weight = clamp(variance, gMinVariance, gMaxVariance);

    PS_OUT psOut;
    psOut.weight = weight;
    return psOut;
}
