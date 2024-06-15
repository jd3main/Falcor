
namespace FullScreenPass
{
    #include "RenderGraph/BasePasses/FullScreenPass.vs.slang"
}

#include "Enums.h"

#define EPS 1e-4f

cbuffer PerImageCB
{
    // Input buffers
    Texture2D gInputWeight;

    // Parameters
    uint2 gResolution;
    float gAverageSampleCountBudget;
    float gMinWeight;
    Buffer<float> gTotalWeight;
    uint gMinSamplePerPixel;
    uint gMaxSamplePerPixel;
};


struct PS_OUT
{
    float sampleCount : SV_Target0;
};

PS_OUT main(FullScreenPass.VsOut vsOut)
{
    const int2 ipos = int2(vsOut.posH.xy);

    const float weight = gInputWeight[ipos].x;
    const float totalWeight = gTotalWeight[0];

    if (totalWeight == 0)
    {
        PS_OUT psOut;
        psOut.sampleCount = gMinSamplePerPixel;
        return psOut;
    }

    const float averageWeight = totalWeight / (gResolution.x * gResolution.y);
    const float averageExtraSampleCount = (gAverageSampleCountBudget - gMinSamplePerPixel);
    const float averageExtraWeight = (averageWeight - gMinWeight);
    const float extraSampleCountPerExtraWeight = averageExtraSampleCount / (averageExtraWeight + EPS);

    const float sampleCount = floor(gMinSamplePerPixel + extraSampleCountPerExtraWeight * (weight - gMinWeight));
    const float sampleCountClamped = clamp(sampleCount, gMinSamplePerPixel, gMaxSamplePerPixel);

    PS_OUT psOut;
    psOut.sampleCount = sampleCountClamped;
    return psOut;
}
