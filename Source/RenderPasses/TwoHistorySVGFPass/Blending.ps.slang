import Scene.ShadingData;
import Utils.Color.ColorHelpers;
import RenderPasses.SVGFPass.SVGFCommon;
import RenderPasses.ReprojectionPass.ReprojectionStruct;

#define NORMALIZATION_MODE _NORMALIZATION_MODE
#define SELECTION_MODE _SELECTION_MODE
#define DEBUG_OUTPUT_ENABLED _DEBUG_OUTPUT_ENABLED
#define DEBUG_TAG_ENABLED _DEBUG_TAG_ENABLED
#define BEST_GAMMA_ENABLED _BEST_GAMMA_ENABLED

#define MIN_VARIANCE 1e-6f

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

float max(float3 v)
{
    return max(max(v.x, v.y), v.z);
}

cbuffer PerImageCB
{
    // Input buffer
    Texture2D gUnweightedIllumination;
    Texture2D gWeightedIllumination;
    Texture2D gGradient;

#if BEST_GAMMA_ENABLED
    Texture2D gHistoryLength;
    Texture2D gHistoryWeight;
    Texture2D gSampleCountMoments;
#endif


    // Parameters
    float gGammaMidpoint;
    float gGammaSteepness;
    float gAlpha;
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


    float3 outIllumination;
    float gamma = luminance(abs(gradient));


// normalize
#if NORMALIZATION_MODE == NORMALIZATION_MODE_LUMINANCE
    gamma = gamma / luminance(unweightedIllumination);
#elif NORMALIZATION_MODE == NORMALIZATION_MODE_VARIANCE
    gamma = gamma / max(variance, MIN_VARIANCE);
#elif NORMALIZATION_MODE == NORMALIZATION_MODE_STANDARDDEVIATION
    gamma = gamma / sqrt(max(variance, MIN_VARIANCE));
#elif NORMALIZATION_MODE == NORMALIZATION_MODE_STANDARDDEVIATION2
    gamma = gamma / sqrt(max(variance, MIN_VARIANCE));
    const float h = gHistoryLength[ipos].r;
    const float beta = 1 - gAlpha;
    const float var_y = (1 - beta) / beta * ((1 + pow(beta, h)) / (1 - pow(beta, h + 1)));
    const float std_y = sqrt(var_y);
    gamma = gamma / std_y;
    // gamma = gamma / 0.5503262028604377;
#endif


#if SELECTION_MODE == SELECTION_MODE_UNWEIGHTED
    // gamma = 1.0f;
    outIllumination = unweightedIllumination;
#elif SELECTION_MODE == SELECTION_MODE_WEIGHTED
    // gamma = 0.0f;
    outIllumination = weightedIllumination;
#elif SELECTION_MODE == SELECTION_MODE_LINEAR
    gamma = clamp(0.5 + (gamma - gGammaMidpoint) * gGammaSteepness, 0, 1);
#elif SELECTION_MODE == SELECTION_MODE_STEP
    gamma = (gamma >= gGammaMidpoint) ? 1 : 0;
#elif SELECTION_MODE == SELECTION_MODE_LOGISTIC
    gamma = 1 / (1 + exp(-gGammaSteepness * (gamma - gGammaMidpoint)));
#endif

#if BEST_GAMMA_ENABLED
    const float2 weights = gHistoryWeight[ipos].rg;
    const float3 scm = gSampleCountMoments[ipos].rgb;
    // const float wu2 = weights.x * weights.x;
    // const float wuww = weights.x * weights.y;
    // const float ww2 = weights.y * weights.y;
    // float best_gamma = (wu2 * scm.x - wuww * scm.y) / (wu2 * scm.x - 2 * wuww * scm.y + ww2 * scm.z);
    const float X = weights[0] * (weights[0] * scm.x - weights[1] * scm.y);
    const float Y = weights[1] * (weights[0] * scm.y - weights[1] * scm.z);
    float best_gamma = X / (X - Y);
    if (isNaN(best_gamma))
    {
        best_gamma = 1.0;
    }
    best_gamma = saturate(best_gamma);
    // gamma = max(best_gamma, gamma);
    gamma = lerp(best_gamma, 1.0, gamma);
    gamma = saturate(gamma);
#endif


#if SELECTION_MODE == SELECTION_MODE_LINEAR || SELECTION_MODE == SELECTION_MODE_STEP || SELECTION_MODE == SELECTION_MODE_LOGISTIC
    outIllumination = lerp(weightedIllumination, unweightedIllumination, gamma);
#endif

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
