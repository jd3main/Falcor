#include "Enums.h"

cbuffer PerImageCB
{
    // Parameters
    uint2 gResolution;
    float gMinSamplePerPixel;
    float gMinVariance;
    float gScale;
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

    const float sampleCount = gMinSamplePerPixel + (weight - gMinVariance) * gScale;

    gOutputSampleCount[pixelPos] = max((uint)floor(sampleCount), 1u);
}
