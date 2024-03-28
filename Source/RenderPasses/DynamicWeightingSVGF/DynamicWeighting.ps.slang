import Scene.ShadingData;
import Utils.Color.ColorHelpers;
import RenderPasses.SVGFPass.SVGFCommon;
import RenderPasses.ReprojectionPass.ReprojectionStruct;

#define NORMALIZATION_MODE _NORMALIZATION_MODE
#define SELECTION_MODE _SELECTION_MODE
#define DEBUG_OUTPUT_ENABLED _DEBUG_OUTPUT_ENABLED
#define DEBUG_TAG_ENABLED _DEBUG_TAG_ENABLED


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
};

struct PS_OUT
{
    float4 color        : SV_Target0;
#if DEBUG_OUTPUT_ENABLED
    float gamma         : SV_Target1;
#endif
};

PS_OUT main(FullScreenPassVsOut vsOut)
{
    const int2 ipos = int2(vsOut.posH.xy);

    const float4 _unweightedIllumination = gUnweightedIllumination[ipos];
    const float3 unweightedIllumination = _unweightedIllumination.rgb;
    const float variance = _unweightedIllumination.a;
    const float3 weightedIllumination = gWeightedIllumination[ipos].rgb;
    const float3 gradient = gGradient[ipos].rgb;

    float gamma = luminance(abs(gradient));

// normalize
#if NORMALIZATION_MODE == NORMALIZATION_MODE_LUMINANCE
    gamma = gamma / luminance(unweightedIllumination);
#elif NORMALIZATION_MODE == NORMALIZATION_MODE_VARIANCE
    gamma = gamma / max(variance, 1e-6f);
#elif NORMALIZATION_MODE == NORMALIZATION_MODE_STANDARDDEVIATION
    gamma = gamma / sqrt(max(variance, 1e-6f));
#endif

#if SELECTION_MODE == SELECTION_MODE_UNWEIGHTED
    gamma = 1.0f;
#elif SELECTION_MODE == SELECTION_MODE_WEIGHTED
    gamma = 0.0f;
#elif SELECTION_MODE == SELECTION_MODE_LINEAR
    gamma = clamp(0.5 + (gamma - gGammaMidpoint) * gGammaSteepness, 0, 1);
#elif SELECTION_MODE == SELECTION_MODE_STEP
    gamma = (gamma >= gGammaMidpoint) ? 1 : 0;
#elif SELECTION_MODE == SELECTION_MODE_LOGISTIC
    gamma = 1 / (1 + exp(-gGammaSteepness * (gamma - gGammaMidpoint)));
#endif

    float3 outIllumination = lerp(weightedIllumination, unweightedIllumination, gamma);

#if DEBUG_TAG_ENABLED
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
