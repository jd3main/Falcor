import Scene.ShadingData;
import Utils.Color.ColorHelpers;
import RenderPasses.SVGFPass.SVGFCommon;
import RenderPasses.ReprojectionPass.ReprojectionStruct;

#include "RenderPasses/DynamicWeightingSVGF/Enums.h"
#include "RenderPasses/DynamicWeightingSVGF/Configs.h"

#ifndef _DEBUG_TAG_ENABLED
#define _DEBUG_TAG_ENABLED 0
#endif

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
    // Input buffer
    Texture2D gPrevUnweightedIllumination;
    Texture2D gPrevWeightedIllumination;
    Texture2D gUnweightedIllumination;
    Texture2D gWeightedIllumination;
    Texture2D gPrevGradient;
    Texture2D<int4> gInputReprojectionTapWidthAndPrevPos;
    Texture2D gInputReprojectionW0123;
    Texture2D gInputReprojectionW4567;

    // Parameters
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
    h.gradient = float3(0, 0, 0);
    h.unweightedIllumination = float3(0, 0, 0);

    const int4 tapWidthAndPrevPos = gInputReprojectionTapWidthAndPrevPos[ipos];
    const float4 w0123 = gInputReprojectionW0123[ipos];
    const float4 w4567 = gInputReprojectionW4567[ipos];
    const Reprojection reprojection = toReprojectionStruct(tapWidthAndPrevPos, w0123, w4567);

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
#if DEBUG_OUTPUT_ENABLED
    float4 gradient     : SV_Target1;
    float gamma         : SV_Target2;
#endif
};

PS_OUT main(FullScreenPassVsOut vsOut)
{
    const int2 ipos = int2(vsOut.posH.xy);

    const float3 unweightedIllumination = gUnweightedIllumination[ipos].rgb;
    const float variance = gUnweightedIllumination[ipos].a;
    const float3 weightedIllumination = gWeightedIllumination[ipos].rgb;

    History h;
    bool success = loadHistory(ipos, h);

    float3 delta = success ? (unweightedIllumination - h.unweightedIllumination) : float3(0, 0, 0);
    delta = clamp(delta, -1, 1);

    float3 gradient = success ? lerp(h.gradient, delta, gGradientAlpha) : float3(0, 0, 0);
    gradient = clamp(gradient, -1, 1);
    float gamma = luminance(abs(gradient));

    // normalize
    if (gNormalizationMode == NormalizationMode::Luminance)
        gamma = gamma / luminance(unweightedIllumination);
    else if (gNormalizationMode == NormalizationMode::Variance)
        gamma = gamma / max(variance, 1e-6f);
    else if (gNormalizationMode == NormalizationMode::StandardDeviation)
        gamma = gamma / sqrt(max(variance, 1e-6f));

    switch (gSelectionMode)
    {
    case SelectionMode::Unweighted:
        gamma = 1.0f;
        break;
    case SelectionMode::Weighted:
        gamma = 0.0f;
        break;
    case SelectionMode::Linear:
        gamma = clamp(0.5 + (gamma-gGammaMidpoint) * gGammaSteepness, 0, 1);
        break;
    case SelectionMode::Step:
        gamma = (gamma >= gGammaMidpoint) ? 1 : 0;
        break;
    case SelectionMode::Logistic:
        gamma = 1 / (1 + exp(-gGammaSteepness * (gamma - gGammaMidpoint)));
        break;
    }

    float3 outIllumination = lerp(weightedIllumination, unweightedIllumination, gamma);

#if _DEBUG_TAG_ENABLED
    if (ipos.x < 20 && ipos.y < 100)
    {
        float3 debugColor = float3(1, 0, 0);
        outIllumination = debugColor;
    }
#endif

    PS_OUT psOut;
    psOut.color = float4(outIllumination, variance);
#if DEBUG_OUTPUT_ENABLED
    psOut.gradient = float4(gradient, 0);
    psOut.gamma = gamma;
#endif

    return psOut;
}
