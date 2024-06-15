#define INPUT_FORMAT_R8UINT 1
#define INPUT_FORMAT_R16UINT 2
#define INPUT_FORMAT_R32UINT 3
#define INPUT_FORMAT_R16FLOAT 4
#define INPUT_FORMAT_R32FLOAT 5


cbuffer CB
{
    uint gMaxValue = 1;
    uint2 gResolution;
}

#if _INPUT_FORMAT == INPUT_FORMAT_R8UINT || _INPUT_FORMAT == INPUT_FORMAT_R16UINT || _INPUT_FORMAT == INPUT_FORMAT_R32UINT
Texture2D<uint> gInputCount;
#elif _INPUT_FORMAT == INPUT_FORMAT_R16FLOAT || _INPUT_FORMAT == INPUT_FORMAT_R32FLOAT
Texture2D<float> gInputCount;
#endif

RWTexture2D gOutputColor;

[numthreads(16, 16, 1)]
void main(uint3 dispatchThreadId : SV_DispatchThreadID)
{
    const uint2 pixPos = dispatchThreadId.xy;
#if _INPUT_FORMAT == INPUT_FORMAT_R8UINT
    float count = float(gInputCount[pixPos] & 0x000000FF);
#elif _INPUT_FORMAT == INPUT_FORMAT_R16UINT
    float count = float(gInputCount[pixPos] & 0x0000FFFF);
#elif _INPUT_FORMAT == INPUT_FORMAT_R32UINT
    float count = float(gInputCount[pixPos]);
#elif _INPUT_FORMAT == INPUT_FORMAT_R16FLOAT
    float count = gInputCount[pixPos];
#elif _INPUT_FORMAT == INPUT_FORMAT_R32FLOAT
    float count = gInputCount[pixPos];
#endif

    float value = count / float(gMaxValue);
    float4 color = float4(value, value, value, 1);
    gOutputColor[pixPos] = color;
}
