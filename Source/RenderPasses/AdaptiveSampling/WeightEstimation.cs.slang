#include "Enums.h"

cbuffer PerImageCB
{
    // Input buffers
    Texture2D gInputVariance;
    Texture2D gInputHistoryLength;

    // Output buffers
    RWTexture2D<float> gOutputSampleDensityWeight;

    // Parameters
    uint2 gResolution;
    float gMaxVariance;
};


[numthreads(16, 16, 1)]
void main(uint3 dispatchThreadId : SV_DispatchThreadID)
{
    if (any(dispatchThreadId.xy >= gResolution)) return;
    const uint2 pixelPos = dispatchThreadId.xy;

    const float historyLength = gInputHistoryLength[pixelPos].r;
    float variance = (historyLength < 2.0f) ? gMaxVariance : gInputVariance[pixelPos].r;
    variance = min(variance, gMaxVariance);

    float weight = variance;

    gOutputSampleDensityWeight[pixelPos] = weight;
}
