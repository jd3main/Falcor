import Scene.Raster; // Imports defaultVS.

#define OUTPUT_COLOR false

#if OUTPUT_COLOR
    #define OUTPUT_TYPE float
#else
    #define OUTPUT_TYPE uint
#endif


cbuffer PerFrameCB
{
    float gInnerTargetQuality;
    float gOuterTargetQuality;
    float2 gFoveaCenter;
    float gFoveaRadius;
    float2 gViewportSize;
};

RWTexture2D<OUTPUT_TYPE> gPrevSampleCount;

VSOut vsMain(VSIn vIn)
{
    return defaultVS(vIn);
}

OUTPUT_TYPE psMain(VSOut vsOut) : SV_TARGET
{
    OUTPUT_TYPE sampleCount = 0;
    uint2 pixelPos = vsOut.posH.xy;
    float dist = length(pixelPos - gFoveaCenter);
    OUTPUT_TYPE prevSampleCount = gPrevSampleCount[pixelPos];

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

    // float4 color = float4(float(sampleCount)/gInnerTargetQuality, 0, 0, 1);
    // return color;

    #if OUTPUT_COLOR
    sampleCount /= gInnerTargetQuality;
    #endif

    gPrevSampleCount[pixelPos] = sampleCount;

    return sampleCount;
}
