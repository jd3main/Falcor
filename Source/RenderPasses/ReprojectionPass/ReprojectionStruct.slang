
struct Reprojection
{
    int tapWidth;
    int2 iposPrev;
    float w[9];
};

struct ReprojectionPsOut
{
    // .x = tapWidth, .yz = iposPrev
    int4 tapWidthAndPrevPos : SV_TARGET0;

    // w[8] is inferred to be 1 - sum(w[0], w[1], ... , w[7])
    float4 w0123            : SV_TARGET1;
    float4 w4567            : SV_TARGET2;
};

Reprojection toReprojectionStruct(int4 taWidthAndPrevPos, float4 w0123, float4 w4567)
{
    Reprojection reprojection;
    reprojection.tapWidth = taWidthAndPrevPos.x;
    reprojection.iposPrev = taWidthAndPrevPos.yz;
    reprojection.w[0] = w0123.x;
    reprojection.w[1] = w0123.y;
    reprojection.w[2] = w0123.z;
    reprojection.w[3] = w0123.w;
    reprojection.w[4] = w4567.x;
    reprojection.w[5] = w4567.y;
    reprojection.w[6] = w4567.z;
    reprojection.w[7] = w4567.w;
    reprojection.w[8] = 1.0f - dot(w0123, float4(1, 1, 1, 1)) - dot(w4567, float4(1, 1, 1, 1));
    return reprojection;
}
