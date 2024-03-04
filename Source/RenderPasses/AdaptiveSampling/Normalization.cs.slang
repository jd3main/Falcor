#include "Enums.h"

cbuffer PerImageCB
{
    // Parameters
    uint2 gResolution;
    float gAverageSampleCountBudget;
    float gMinSamplePerPixel;
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
    const float scale = (averageWeight - gMinWeight) / (gAverageSampleCountBudget - gMinSamplePerPixel);

    const float sampleCount = gMinSamplePerPixel + (weight - gMinWeight) * scale;

    gOutputSampleCount[pixelPos] = max((uint)floor(sampleCount), 1u);
}
