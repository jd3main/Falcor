#define OUTPUT_T uint

static const uint kMaxSamplesPerPixel = 16; ///< Maximum sample count supported by path tracer.

cbuffer PerFrameCB
{
    bool gEnabled;
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
RWTexture2D<OUTPUT_T> gOutputSampleCount;


[numthreads(16, 16, 1)]
void calculateSampleCount(uint3 dispatchThreadId : SV_DispatchThreadID)
{
    if (any(dispatchThreadId.xy >= gResolution)) return;

    const uint2 pixelPos = dispatchThreadId.xy;
    float dist = length(pixelPos - gFoveaCenter);
    float historySampleWeight = gHistorySampleWeight[pixelPos];
    OUTPUT_T sampleCount = 0;

    float alpha = gAlpha;
    float beta = (1-alpha);
    float stableWeight = beta / alpha; // sum to infinity of geometric series

    if (gEnabled)
    {
        if (dist < gFoveaRadius)
        {
            // inside foveated region
            sampleCount = gUseHistory ? gInnerTargetQuality*stableWeight - historySampleWeight : gInnerTargetQuality;
        }
        else
        {
            // outside foveated region
            sampleCount = gUseHistory ? gOuterTargetQuality*stableWeight - historySampleWeight : gOuterTargetQuality;
        }
        sampleCount = clamp(sampleCount, 1, kMaxSamplesPerPixel);
        #ifdef _OUTPUT_COLOR
        sampleCount /= kMaxSamplesPerPixel;
        #endif
    }
    else
    {
        sampleCount = gSampleCountWhenDisabled;
    }

    gOutputSampleCount[pixelPos] = sampleCount;
}
