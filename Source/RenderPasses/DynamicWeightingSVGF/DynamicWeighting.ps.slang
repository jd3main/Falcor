import Scene.ShadingData;
import Utils.Color.ColorHelpers;
import RenderPasses.SVGFPass.SVGFCommon;
import RenderPasses.DynamicWeightingSVGF.Common;

cbuffer PerImageCB
{
    Texture2D gPrevUnweightedIllumination;
    Texture2D gPrevWeightedIllumination;
    Texture2D gUnweightedIllumination;
    Texture2D gWeightedIllumination;
    Texture2D gPrevGradient;
    Texture2D<float> gVariance;
    StructuredBuffer<Reprojection> gReprojection;

    RWTexture2D gGradient;
    RWTexture2D gOutGamma;

    float gGradientAlpha;
    float gGammaRatio;
};

struct History
{
    float3 gradient;
    float3 unweightedIllumination;
    float3 weightedIllumination;
}

bool loadHistory(int2 ipos, out History history)
{
    const int2 imageDim = getTextureDims(gUnweightedIllumination, 0);
    int idx = ipos.y * imageDim.x + ipos.x;
    Reprojection reprojection = gReprojection[idx];

    history.gradient = float3(0, 0, 0);
    history.unweightedIllumination = float3(0, 0, 0);
    history.weightedIllumination = float3(0, 0, 0);

    if (reprojection.tapWidth == 2)
    {
        const int2 offset[4] = { int2(0, 0), int2(1, 0), int2(0, 1), int2(1, 1) };
        for (int i = 0; i < 4; i++)
        {
            const int2 loc = reprojection.iposPrev + offset[i];
            history.gradient += gPrevGradient[loc].xyz * reprojection.w[i];
            history.unweightedIllumination += gPrevUnweightedIllumination[loc].xyz * reprojection.w[i];
            history.weightedIllumination += gPrevWeightedIllumination[loc].xyz * reprojection.w[i];
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
                    history.gradient += gPrevGradient[loc].xyz * reprojection.w[i];
                    history.unweightedIllumination += gPrevUnweightedIllumination[loc].xyz * reprojection.w[i];
                    history.weightedIllumination += gPrevWeightedIllumination[loc].xyz * reprojection.w[i];
                }
            }
        }
    }
    else
    {
        history.unweightedIllumination = float3(0, 0, 1);
    }

    return reprojection.tapWidth > 0;
}

float4 main(FullScreenPassVsOut vsOut) : SV_TARGET0
{
    const int2 ipos = int2(vsOut.posH.xy);

    float3 unweightedIllumination = gUnweightedIllumination[ipos].rgb;
    float3 weightedIllumination = gWeightedIllumination[ipos].rgb;
    float variance = gVariance[ipos].x;

    History h;
    bool success = loadHistory(ipos, h);

    float3 gradient = (unweightedIllumination - h.unweightedIllumination);
    gradient = lerp(h.gradient, gradient, gGradientAlpha);
    float std = sqrt(variance);
    float gamma = abs(luminance(gradient)) * gGammaRatio;
    float gammaClamped = clamp(gamma, 0, 1);
    float3 outIllumination = lerp(h.weightedIllumination, h.unweightedIllumination, gammaClamped);

    gGradient[ipos] = float4(gradient, 1);
    gOutGamma[ipos] = float4(gammaClamped, 0, 0, 0);
    return float4(outIllumination, 1);
}
