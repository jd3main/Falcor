
#define INPUT_FORMAT_R8_UINT 0
#define INPUT_FORMAT_R16_UINT 1
#define INPUT_FORMAT_R32_UINT 2


cbuffer CB
{
    uint gMaxValue = 0;
    uint2 gResolution;
}

Texture2D<uint> gInputCount;
RWTexture2D gOutputColor;

[numthreads(16, 16, 1)]
void main(uint3 dispatchThreadId : SV_DispatchThreadID)
{
    const uint2 pixPos = dispatchThreadId.xy;
    uint count = gInputCount[pixPos];


#if _INPUT_FORMAT == INPUT_FORMAT_R8_UINT
    count = (count & 0x000000FF);
#elif _INPUT_FORMAT == INPUT_FORMAT_R16_UINT
    count = (count & 0x0000FFFF);
#endif

    float value = count / float(gMaxValue);
    float4 color = float4(value, value, value, 1);
    gOutputColor[pixPos] = color;
}
