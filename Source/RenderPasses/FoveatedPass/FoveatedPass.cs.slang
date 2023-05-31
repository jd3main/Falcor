#define OUTPUT_T uint


cbuffer PerFrameCB
{
    uint2 gResolution;
    float gInnerTargetQuality;
    float gOuterTargetQuality;
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

    gOutputSampleCount[pixelPos] = sampleCount;
}
