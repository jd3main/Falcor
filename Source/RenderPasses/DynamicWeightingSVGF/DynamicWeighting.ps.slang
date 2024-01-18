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

    float gGradientAlpha;
    float gGammaMidpoint;
    float gGammaSteepness;
    SelectionMode gSelectionMode;
    NormalizationMode gNormalizationMode;
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

struct PS_OUT
{
    float4 color        : SV_Target0;
    float4 gradient     : SV_Target1;
    float4 gamma        : SV_Target2;
};

PS_OUT main(FullScreenPassVsOut vsOut)
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

    // normalize
    if (gNormalizationMode == NormalizationMode::Luminance)
        gamma = gamma / luminance(unweightedIllumination);
    if (gNormalizationMode == NormalizationMode::Variance)
        gamma = gamma / max(variance, 1e-6f);
    if (gNormalizationMode == NormalizationMode::StandardDeviation)
        gamma = gamma / sqrt(max(variance, 1e-6f));

    switch (gSelectionMode)
    {
    case SelectionMode::Unweighted:
        gamma = 1.0f;
    case SelectionMode::Weighted:
        gamma = 0.0f;
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

    float3 outIllumination = lerp(weightedIllumination, unweightedIllumination, gamma);

    if (gSelectionMode == SelectionMode::Unweighted)
        outIllumination = unweightedIllumination;
    if (gSelectionMode == SelectionMode::Weighted)
        outIllumination = weightedIllumination;


    PS_OUT psOut;
    psOut.color = float4(outIllumination, 1);
    psOut.gradient = float4(gradient, 1);
    psOut.gamma = float4(gamma, 0, 0, 0);

    return psOut;
}
