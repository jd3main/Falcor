#include "Enums.h"

static const uint kMaxSamplesPerPixel = 16; ///< Maximum sample count supported by path tracer.


cbuffer PerFrameCB
{
    FoveaShape gShape;
    bool gUseHistory;
    float gAlpha;
    uint2 gResolution;
    float gInnerTargetQuality;
    float gOuterTargetQuality;
    float2 gFoveaCenter;
    float gFoveaRadius;
    bool gFlickerEnabled;
    float gFlickerBrightDuration;
    float gFlickerDarkDuration;
    float gFrameTime;
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
    case FoveaShape::FOVEA_SHAPE_UNIFORM:
        baseSampleCount = gInnerTargetQuality;
        break;
    case FoveaShape::FOVEA_SHAPE_CIRCLE:
        baseSampleCount = (dist < gFoveaRadius) ? gInnerTargetQuality : gOuterTargetQuality;
        break;
    case FoveaShape::FOVEA_SHAPE_SPLITHORIZONTALLY:
        baseSampleCount = (pixelPos.y < gFoveaCenter.y) ? gInnerTargetQuality : gOuterTargetQuality;
        break;
    case FoveaShape::FOVEA_SHAPE_SPLITVERTICALLY:
        baseSampleCount = (pixelPos.x < gFoveaCenter.x) ? gInnerTargetQuality : gOuterTargetQuality;
        break;
    }

    sampleCount = gUseHistory
                      ? min(baseSampleCount * stability - historySampleWeight * beta, baseSampleCount)
                      : baseSampleCount;

    if (gFlickerEnabled)
    {
        float flickerDuration = gFlickerBrightDuration + gFlickerDarkDuration;
        float flickerProgress = fmod(gFrameTime, flickerDuration);

        if (flickerProgress < gFlickerBrightDuration)
            sampleCount = gInnerTargetQuality;
        else
            sampleCount = gOuterTargetQuality;
    }

    sampleCount = clamp(sampleCount, 1.0f, kMaxSamplesPerPixel);


    gOutputSampleCount[pixelPos] = (uint)round(sampleCount);
}
