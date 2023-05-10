// #define _OUTPUT_COLOR

#ifdef _OUTPUT_COLOR
    #define PIXEL_T float
#else
    #define PIXEL_T uint
#endif


cbuffer PerFrameCB
{
    uint2 gResolution;
    float gInnerTargetQuality;
    float gOuterTargetQuality;
    float2 gFoveaCenter;
    float gFoveaRadius;
};

RWTexture2D<PIXEL_T> gPrevSampleCount;
RWTexture2D<PIXEL_T> gOutputSampleCount;

[numthreads(16, 16, 1)]
void calculateSampleCount(uint3 dispatchThreadId : SV_DispatchThreadID)
{
    if (any(dispatchThreadId.xy >= gResolution)) return;
    const uint2 pixelPos = dispatchThreadId.xy;

    float dist = length(pixelPos - gFoveaCenter);
    PIXEL_T prevSampleCount = gPrevSampleCount[pixelPos];
    PIXEL_T sampleCount = 0;

    if (dist < gFoveaRadius)
    {
        // inside foveated region
        sampleCount = gInnerTargetQuality;
    }
    else
    {
        // outside foveated region
        sampleCount = gOuterTargetQuality;
    }

    #ifdef _OUTPUT_COLOR
    sampleCount /= gInnerTargetQuality;
    #endif

    gPrevSampleCount[pixelPos] = gOutputSampleCount[pixelPos];
    gOutputSampleCount[pixelPos] = sampleCount;
}
