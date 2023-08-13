#include "Enums.h"

static const uint kMaxSamplesPerPixel = 16; ///< Maximum sample count supported by path tracer.


cbuffer PerFrameCB
{
    Shape gShape;
    bool gUseHistory;
    float gAlpha;
    uint2 gResolution;
    float gInnerTargetQuality;
    float gOuterTargetQuality;
    float gSampleCountWhenDisabled;
    float2 gFoveaCenter;
    float gFoveaRadius;
};

RWTexture2D<float> gHistorySampleWeight;
RWTexture2D<uint> gOutputSampleCount;


[numthreads(16, 16, 1)]
void calculateSampleCount(uint3 dispatchThreadId : SV_DispatchThreadID)
{
    if (any(dispatchThreadId.xy >= gResolution)) return;

    const uint2 pixelPos = dispatchThreadId.xy;
    float dist = length(pixelPos - gFoveaCenter);
    float historySampleWeight = gHistorySampleWeight[pixelPos];
    float sampleCount = 0;

    float alpha = gAlpha;
    float beta = (1.0f-alpha);
    float stability = 1.0f / alpha; // sum to infinity of geometric series


    float baseSampleCount;

    switch (gShape)
    {
    case Shape::Uniform:
        baseSampleCount = gSampleCountWhenDisabled;
        break;
    case Shape::Circle:
        baseSampleCount = (dist < gFoveaRadius) ? gInnerTargetQuality : gSampleCountWhenDisabled;
        break;
    case Shape::SplitHorizontally:
        baseSampleCount = (pixelPos.y < gFoveaCenter.y) ? gInnerTargetQuality : gSampleCountWhenDisabled;
        break;
    case Shape::SplitVertically:
        baseSampleCount = (pixelPos.x < gFoveaCenter.x) ? gInnerTargetQuality : gSampleCountWhenDisabled;
        break;
    }

    sampleCount = gUseHistory
                    ? min(baseSampleCount*stability - historySampleWeight*beta, baseSampleCount)
                    : baseSampleCount;
    sampleCount = clamp(sampleCount, 1.0f, kMaxSamplesPerPixel);


    gOutputSampleCount[pixelPos] = (uint)round(sampleCount);
}
