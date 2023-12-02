import Scene.ShadingData;
import Utils.Color.ColorHelpers;
import RenderPasses.SVGFPass.SVGFCommon;
import RenderPasses.DynamicWeightingSVGF.Common;

#include "RenderPasses/DynamicWeightingSVGF/Enums.h"

// Workaround for isnan() not working in slang.
bool isNaN(float f)
{
    uint u = asuint(f) & ~0x80000000u; // clear out the sign bit
    return (u > 0x7F800000);           // greater than Inf is NaN
}

bool isNaN(float3 f)
{
    return isNaN(f.x) || isNaN(f.y) || isNaN(f.z);
}

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
    float gGammaMidpoint;
    float gGammaSteepness;
    SelectionMode gSelectionMode;
};

struct History
{
    float3 gradient;
    float3 unweightedIllumination;
}

bool loadHistory(int2 ipos, out History h)
{
    const int2 imageDim = getTextureDims(gUnweightedIllumination, 0);
    int idx = ipos.y * imageDim.x + ipos.x;
    Reprojection reprojection = gReprojection[idx];

    h.gradient = float3(0, 0, 0);
    h.unweightedIllumination = float3(0, 0, 0);

    if (reprojection.tapWidth == 2)
    {
        const int2 offset[4] = { int2(0, 0), int2(1, 0), int2(0, 1), int2(1, 1) };
        for (int i = 0; i < 4; i++)
        {
            const int2 loc = reprojection.iposPrev + offset[i];
            h.gradient += gPrevGradient[loc].xyz * reprojection.w[i];
            h.unweightedIllumination += gPrevUnweightedIllumination[loc].xyz * reprojection.w[i];
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
                    h.gradient += gPrevGradient[loc].xyz * reprojection.w[i];
                    h.unweightedIllumination += gPrevUnweightedIllumination[loc].xyz * reprojection.w[i];
                }
            }
        }
    }

    if (isNaN(h.gradient))
        h.gradient = float3(0, 0, 0);
    if (isNaN(h.unweightedIllumination))
        h.unweightedIllumination = float3(0, 0, 0);

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

    // TODO: take log or normalize by illumination

    float3 delta = success ? (unweightedIllumination - h.unweightedIllumination) : float3(0, 0, 0);
    delta = clamp(delta, -1, 1);

    float3 gradient = success ? lerp(h.gradient, delta, gGradientAlpha) : float3(0, 0, 0);
    gradient = clamp(gradient, -1, 1);
    float gamma = luminance(abs(gradient));
    switch (gSelectionMode)
    {
    case SelectionMode::Linear:
        gamma = clamp(gamma * gGammaSteepness, 0, 1);
        break;
    case SelectionMode::Step:
        gamma = (gamma >= gGammaMidpoint) ? 1 : 0;
        break;
    case SelectionMode::Logistic:
        gamma = 1 / (1 + exp(-gGammaSteepness * (gamma - gGammaMidpoint)));
        break;
    }

    // outIllumination = lerp(weightedIllumination, unweightedIllumination, gamma);

    float3 outIllumination = float3(0, 0, 0);
    if (gSelectionMode == SelectionMode::Weighted)
        outIllumination = weightedIllumination;
    else if (gSelectionMode == SelectionMode::Unweighted)
        outIllumination = unweightedIllumination;
    else
        outIllumination = lerp(weightedIllumination, unweightedIllumination, gamma);

    // if (isnan(h.gradient.x))
    //     gGradient[ipos] = float4(1, 0, 0, 1);
    // else
    gGradient[ipos] = float4(gradient, 1);
    gOutGamma[ipos] = float4(gamma, 0, 0, 0);


    return float4(outIllumination, 1);
}
