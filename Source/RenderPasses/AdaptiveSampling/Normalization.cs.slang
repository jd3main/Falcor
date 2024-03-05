#include "Enums.h"

#define EPS 1e-4f

cbuffer PerImageCB
{
    // Parameters
    uint2 gResolution;
    float gAverageSampleCountBudget;
    uint gMinSamplePerPixel;
    uint gMaxSamplePerPixel;
    float gMinWeight;
    Buffer<float> gTotalWeight;
};

// Input buffers
Texture2D gInputDensityWeight;
// Output buffers
RWTexture2D<uint> gOutputSampleCount;

[numthreads(16, 16, 1)]
void main(uint3 dispatchThreadId : SV_DispatchThreadID)
{
    if (any(dispatchThreadId.xy >= gResolution)) return;
    const uint2 pixelPos = dispatchThreadId.xy;

    const float weight = gInputDensityWeight[pixelPos].x;
    const float totalWeight = gTotalWeight[0];
    const float averageWeight = totalWeight / (gResolution.x * gResolution.y);
    const float averageExtraSampleCount = (gAverageSampleCountBudget - gMinSamplePerPixel);
    const float averageExtraWeight = (averageWeight - gMinWeight);
    const float extraSampleCountPerExtraWeight = averageExtraSampleCount / (averageExtraWeight + EPS);

    const float sampleCount = gMinSamplePerPixel + extraSampleCountPerExtraWeight * (weight - gMinWeight);

    gOutputSampleCount[pixelPos] = clamp((uint)floor(sampleCount), gMinSamplePerPixel, gMaxSamplePerPixel);
}
