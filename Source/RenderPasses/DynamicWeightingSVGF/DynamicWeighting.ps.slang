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
    Texture2D gUnweightedIllumination;
    Texture2D gWeightedIllumination;
    Texture2D gGradient;

    // Parameters
    float gGammaMidpoint;
    float gGammaSteepness;
    SelectionMode gSelectionMode;
    NormalizationMode gNormalizationMode;
};

struct PS_OUT
{
    float4 color        : SV_Target0;
#if DEBUG_OUTPUT_ENABLED
    float gamma         : SV_Target2;
#endif
};

PS_OUT main(FullScreenPassVsOut vsOut)
{
    const int2 ipos = int2(vsOut.posH.xy);

    const float3 unweightedIllumination = gUnweightedIllumination[ipos].rgb;
    const float3 weightedIllumination = gWeightedIllumination[ipos].rgb;
    const float variance = gUnweightedIllumination[ipos].a;
    const float3 gradient = gGradient[ipos].rgb;

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
    psOut.gamma = gamma;
#endif

    return psOut;
}
