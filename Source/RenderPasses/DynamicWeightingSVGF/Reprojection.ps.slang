import Scene.ShadingData;
import Utils.Math.MathHelpers;
import Utils.Color.ColorHelpers;
import Utils.Color.ColorMap;
import RenderPasses.SVGFPass.SVGFCommon;
import RenderPasses.DynamicWeightingSVGF.Common;

// Workaround for isnan() not working in slang.
bool isNaN(float f)
{
    uint u = asuint(f) & ~0x80000000u; // clear out the sign bit
    return (u > 0x7F800000);           // greater than Inf is NaN
}

cbuffer PerImageCB
{
    Texture2D gColor;
    Texture2D gPositionNormalFwidth;
    Texture2D gLinearZAndNormal;
    Texture2D gPrevLinearZAndNormal;
    Texture2D gMotion;

    RWStructuredBuffer<Reprojection> gReprojection;
};

bool isReprjValid(int2 coord, float Z, float Zprev, float fwidthZ, float3 normal, float3 normalPrev, float fwidthNormal)
{
    const int2 imageDim = getTextureDims(gColor, 0);

    // check whether reprojected pixel is inside of the screen
    if (any(coord < int2(1, 1)) || any(coord > imageDim - int2(1, 1))) return false;

    // check if deviation of depths is acceptable
    if (abs(Zprev - Z) / (fwidthZ + 1e-2f) > 10.f) return false;

    // check normals for compatibility
    if (distance(normal, normalPrev) / (fwidthNormal + 1e-2) > 16.0) return false;

    return true;
}

Reprojection reproject(float2 posH)
{
    const int2 ipos = posH;
    const float2 imageDim = float2(getTextureDims(gColor, 0));

    const float2 motion = gMotion[ipos].xy;
    const float normalFwidth = gPositionNormalFwidth[ipos].y;

    // +0.5 to account for texel center offset
    const int2 iposPrev = int2(float2(ipos) + motion.xy * imageDim + float2(0.5, 0.5));

    float2 depth = gLinearZAndNormal[ipos].xy;
    float3 normal = oct_to_ndir_snorm(gLinearZAndNormal[ipos].zw);

    bool v[4];
    const float2 posPrev = floor(posH.xy) + motion.xy * imageDim;
    const int2 offset[4] = { int2(0, 0), int2(1, 0), int2(0, 1), int2(1, 1) };

    Reprojection weights;
    weights.tapWidth = 0;
    weights.iposPrev = int2(posPrev);
    for (int i = 0; i < 9; i++)
        weights.w[i] = 0;

    // check for all 4 taps of the bilinear filter for validity
    bool valid = false;
    for (int sampleIdx = 0; sampleIdx < 4; sampleIdx++)
    {
        int2 loc = int2(posPrev) + offset[sampleIdx];
        float2 depthPrev = gPrevLinearZAndNormal[loc].xy;
        float3 normalPrev = oct_to_ndir_snorm(gPrevLinearZAndNormal[loc].zw);

        v[sampleIdx] = isReprjValid(iposPrev, depth.x, depthPrev.x, depth.y, normal, normalPrev, normalFwidth);

        valid = valid || v[sampleIdx];
    }

    if (valid)
    {
        weights.tapWidth = 2;

        float sumw = 0;
        float x = frac(posPrev.x);
        float y = frac(posPrev.y);

        // bilinear weights
        const float w[4] = { (1 - x) * (1 - y),
                             x * (1 - y),
                             (1 - x) * y,
                             x * y };

        for (int sampleIdx = 0; sampleIdx < 4; sampleIdx++)
        {
            const int2 loc = int2(posPrev) + offset[sampleIdx];
            if (v[sampleIdx])
            {
                sumw += w[sampleIdx];
                // the actual bilinear interpolation
                // illum += w[sampleIdx] * prevIllum[loc]
            }
        }
        // redistribute weights in case not all taps were used
        valid = (sumw >= 0.01);
        for (int i = 0; i < 4; i++)
        {
            weights.w[i] = valid ? w[i] / sumw : 0;
        }
    }

    if (!valid) // perform cross-bilateral filter in the hope to find some suitable samples somewhere
    {
        float nValid = 0.0;

        // this code performs a binary descision for each tap of the cross-bilateral filter
        const int radius = 1;
        int sampleIdx = 0;
        for (int yy = -radius; yy <= radius; yy++)
        {
            for (int xx = -radius; xx <= radius; xx++)
            {
                sampleIdx++;
                const int2 p = iposPrev + int2(xx, yy);
                const float2 depthFilter = gPrevLinearZAndNormal[p].xy;
                const float3 normalFilter = oct_to_ndir_snorm(gPrevLinearZAndNormal[p].zw);

                if (isReprjValid(iposPrev, depth.x, depthFilter.x, depth.y, normal, normalFilter, normalFwidth))
                {
                    nValid += 1.0;
                    weights.w[sampleIdx] = 1;
                }
            }
        }

        if (nValid > 0)
        {
            weights.tapWidth = 3;
            for (int i = 0; i < 9; i++)
            {
                weights.w[i] /= nValid;
            }
        }
    }


    return weights;
}

float4 main(FullScreenPassVsOut vsOut) : SV_TARGET0
{
    const float4 posH = vsOut.posH;
    const int2 ipos = posH.xy;
    Reprojection reprojection = reproject(posH.xy);

    const int2 imageDim = getTextureDims(gColor, 0);
    int idx = ipos.y * imageDim.x + ipos.x;
    gReprojection[idx] = reprojection;

    return float4(0, 0, 0, 0);
}
