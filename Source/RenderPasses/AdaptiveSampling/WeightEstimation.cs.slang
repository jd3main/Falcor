import RenderPasses.ReprojectionPass.ReprojectionStruct;

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
    StructuredBuffer<Reprojection> gInputReprojection;
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

int loadReprojectedHistory(int2 ipos, out History h)
{
    h.length = 0;
    h.variance = 0;

    const int2 imageDim = getTextureDims(gInputHistoryLength, 0);
    const int idx = ipos.y * imageDim.x + ipos.x;
    const Reprojection reprojection = gInputReprojection[idx];

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
                if (reprojection.w[i] != 0)
                {
                    h.length += gInputHistoryLength[loc].x * reprojection.w[i];
                    h.variance += gInputVariance[loc].x * reprojection.w[i];
                }
            }
        }
    }

    if (isNaN(h.length))
        h.length = 0;
    if (isNaN(h.variance))
        h.variance = 0;

    return reprojection.tapWidth > 0;
}

[numthreads(16, 16, 1)]
void main(uint3 dispatchThreadId : SV_DispatchThreadID)
{
    if (any(dispatchThreadId.xy >= gResolution)) return;
    const uint2 pixelPos = dispatchThreadId.xy;

    History history;
    const bool valid = loadReprojectedHistory(pixelPos, history);
    float variance = (!valid) ? gMaxVariance : max(history.variance, gMaxVariance / history.length);
    variance = clamp(variance, gMinVariance, gMaxVariance);
    const float weight = variance;
    gOutputSampleDensityWeight[pixelPos] = weight;
}
