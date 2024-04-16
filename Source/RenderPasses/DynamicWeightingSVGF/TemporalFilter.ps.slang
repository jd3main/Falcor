/***************************************************************************
 # Copyright (c) 2015-21, NVIDIA CORPORATION. All rights reserved.
 #
 # Redistribution and use in source and binary forms, with or without
 # modification, are permitted provided that the following conditions
 # are met:
 #  * Redistributions of source code must retain the above copyright
 #    notice, this list of conditions and the following disclaimer.
 #  * Redistributions in binary form must reproduce the above copyright
 #    notice, this list of conditions and the following disclaimer in the
 #    documentation and/or other materials provided with the distribution.
 #  * Neither the name of NVIDIA CORPORATION nor the names of its
 #    contributors may be used to endorse or promote products derived
 #    from this software without specific prior written permission.
 #
 # THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS "AS IS" AND ANY
 # EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 # IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
 # PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR
 # CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
 # EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
 # PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
 # PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
 # OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 # (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 # OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 **************************************************************************/
import Scene.ShadingData;
import Utils.Math.MathHelpers;
import Utils.Color.ColorHelpers;
import Utils.Color.ColorMap;
import RenderPasses.SVGFPass.SVGFCommon;

#define MAX_HISTORY_LENGTH 32

#define DW_ENABLED _DW_ENABLED

#if DW_ENABLED
typedef float2 HistoryWeightType;
#else
typedef float HistoryWeightType;
#endif

// Workaround for isnan() not working in slang.
bool isNaN(float f)
{
    uint u = asuint(f) & ~0x80000000u; // clear out the sign bit
    return (u > 0x7F800000);           // greater than Inf is NaN
}

cbuffer PerImageCB
{
    Texture2D gAlbedo;
    Texture2D gColor;
    Texture2D gEmission;
    Texture2D gMotion;
    Texture2D gPositionNormalFwidth;
    Texture2D<uint> gSampleCount;

    Texture2D gLinearZAndNormal;

    Texture2D gPrevMoments;
    Texture2D gPrevHistoryLength;
    Texture2D gPrevHistoryWeight;
    Texture2D gPrevUnweightedIllum;
    Texture2D gPrevLinearZAndNormal;

    float gAlpha;
    float gWeightedAlpha;
    float gMomentsAlpha;

    int gSampleCountOverride = -1;

#if DW_ENABLED
    Texture2D gPrevWeightedIllum;
    Texture2D gPrevGradient;

    float gGradientAlpha;
    float gMaxGradient;
#endif
};

float3 demodulate(float3 c, float3 albedo)
{
    return c / max(albedo, float3(0.001, 0.001, 0.001));
}

bool isReprjValid(int2 coord, float Z, float Zprev, float fwidthZ, float3 normal, float3 normalPrev, float fwidthNormal)
{
    const int2 imageDim = getTextureDims(gColor, 0);

    // check whether reprojected pixel is inside of the screen
    if (any(coord < int2(1,1)) || any(coord > imageDim - int2(1,1))) return false;

    // check if deviation of depths is acceptable
    if (abs(Zprev - Z) / (fwidthZ + 1e-2f) > 10.f) return false;

    // check normals for compatibility
    if (distance(normal, normalPrev) / (fwidthNormal + 1e-2) > 16.0) return false;

    return true;
}

struct History
{
    float2 moments;
    float length;
    HistoryWeightType weight;
    float3 unweightedIllumination;
#if DW_ENABLED
    float3 weightedIllumination;
    float3 gradient;
#endif
};

bool loadHistory(float2 posH, out History history)
{
    const int2 ipos = posH;
    const float2 imageDim = float2(getTextureDims(gColor, 0));

    const float2 motion = gMotion[ipos].xy;
    const float normalFwidth = gPositionNormalFwidth[ipos].y;

    // +0.5 to account for texel center offset
    const int2 iposPrev = int2(float2(ipos) + motion.xy * imageDim + float2(0.5, 0.5));

    float2 depth = gLinearZAndNormal[ipos].xy;
    float3 normal = oct_to_ndir_snorm(gLinearZAndNormal[ipos].zw);

    float2 prevMoments = float2(0, 0);
    float historyLength = 0;
    HistoryWeightType historyWeight = 0;
    float3 unweightedHistoryIllum = float3(0, 0, 0);
#if DW_ENABLED
    float3 weightedHistoryIllum = float3(0, 0, 0);
    float3 gradient = float3(0, 0, 0);
#endif

    bool v[4];
    const float2 posPrev = floor(posH.xy) + motion.xy * imageDim;
    const int2 offset[4] = { int2(0, 0), int2(1, 0), int2(0, 1), int2(1, 1) };

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
        float sumw = 0;
        float x = frac(posPrev.x);
        float y = frac(posPrev.y);

        // bilinear weights
        const float w[4] = { (1 - x) * (1 - y),
                             x * (1 - y),
                             (1 - x) * y,
                             x * y };

        // perform the actual bilinear interpolation
        for (int sampleIdx = 0; sampleIdx < 4; sampleIdx++)
        {
            const int2 loc = int2(posPrev) + offset[sampleIdx];
            if (v[sampleIdx])
            {
                prevMoments += w[sampleIdx] * gPrevMoments[loc].xy;
                sumw += w[sampleIdx];
                historyLength += w[sampleIdx] * gPrevHistoryLength[loc].x;
                unweightedHistoryIllum += w[sampleIdx] * gPrevUnweightedIllum[loc].xyz;
#if !DW_ENABLED
                historyWeight += w[sampleIdx] * gPrevHistoryWeight[loc].x;
#else
                historyWeight += w[sampleIdx] * gPrevHistoryWeight[loc].xy;
                weightedHistoryIllum += w[sampleIdx] * gPrevWeightedIllum[loc].xyz;
                gradient += w[sampleIdx] * gPrevGradient[loc].xyz;
#endif
            }
        }

        // redistribute weights in case not all taps were used
        valid = (sumw >= 0.01);
        prevMoments = valid ? prevMoments / sumw : float2(0, 0);
        historyLength = valid ? historyLength / sumw : 0;
        historyWeight = valid ? historyWeight / sumw : 0;
        unweightedHistoryIllum = valid ? unweightedHistoryIllum / sumw : float3(0, 0, 0);
#if DW_ENABLED
        weightedHistoryIllum = valid ? weightedHistoryIllum / sumw : float3(0, 0, 0);
        gradient = valid ? gradient / sumw : 0;
#endif
    }

    if (!valid) // perform cross-bilateral filter in the hope to find some suitable samples somewhere
    {
        float nValid = 0.0;

        // this code performs a binary descision for each tap of the cross-bilateral filter
        const int radius = 1;
        for (int yy = -radius; yy <= radius; yy++)
        {
            for (int xx = -radius; xx <= radius; xx++)
            {
                const int2 p = iposPrev + int2(xx, yy);
                const float2 depthFilter = gPrevLinearZAndNormal[p].xy;
                const float3 normalFilter = oct_to_ndir_snorm(gPrevLinearZAndNormal[p].zw);

                if (isReprjValid(iposPrev, depth.x, depthFilter.x, depth.y, normal, normalFilter, normalFwidth))
                {
                    prevMoments += gPrevMoments[p].xy;
                    nValid += 1.0;
                    historyLength += gPrevHistoryLength[p].x;
                    unweightedHistoryIllum += gPrevUnweightedIllum[p].xyz;
#if !DW_ENABLED
                    historyWeight += gPrevHistoryWeight[p].x;
#else
                    historyWeight += gPrevHistoryWeight[p].xy;
                    weightedHistoryIllum += gPrevWeightedIllum[p].xyz;
                    gradient += gPrevGradient[p].xyz;
#endif
                }
            }
        }
        if (nValid > 0)
        {
            valid = true;
            prevMoments /= nValid;
            historyLength /= nValid;
            historyWeight /= nValid;
            unweightedHistoryIllum /= nValid;
#if DW_ENABLED
            weightedHistoryIllum /= nValid;
            gradient /= nValid;
#endif
        }
    }

    history.moments = prevMoments;
    history.length = historyLength;
    history.weight = historyWeight;
    history.unweightedIllumination = unweightedHistoryIllum;
#if DW_ENABLED
    history.weightedIllumination = weightedHistoryIllum;
    history.gradient = gradient;
#endif

    return valid;
}
// not used currently
float computeVarianceScale(float numSamples, float loopLength, float alpha)
{
    const float aa = (1.0 - alpha) * (1.0 - alpha);
    return (1.0 - pow(aa, min(loopLength, numSamples))) / (1.0 - aa);
}


struct PS_OUT
{
    float4 OutIllumination                  : SV_TARGET0;
    float2 OutMoments                       : SV_TARGET1;
    float OutHistoryLength                  : SV_TARGET2;
    HistoryWeightType OutHistoryWeight      : SV_TARGET3;
    float4 OutWeightedIllumination          : SV_TARGET4;
    float OutVariance                       : SV_TARGET5;
    float4 OutGradient                      : SV_TARGET6;
};

// PS_OUT main(FullScreenPassVsOut vsOut)
PS_OUT main(FullScreenPassVsOut vsOut)
{
    const float4 posH = vsOut.posH;
    const int2 ipos = posH.xy;

    float3 illumination = demodulate(gColor[ipos].rgb - gEmission[ipos].rgb, gAlbedo[ipos].rgb);
    // Workaround path tracer bugs. TODO: remove this when we can.
    if (isNaN(illumination.x) || isNaN(illumination.y) || isNaN(illumination.z))
    {
        illumination = float3(0, 0, 0);
    }
    const float curLuminance = luminance(illumination);

    // Load history
    History h;
    // int sampleCount = max(gSampleCount[ipos], 1);
    uint sampleCount = (gSampleCountOverride > 0) ? gSampleCountOverride : gSampleCount[ipos];
    sampleCount = max(sampleCount, 1);
    bool success = loadHistory(posH.xy, h);

    // Calculate alpha for moments
    float curLength = success ? min(h.length + 1, MAX_HISTORY_LENGTH) : 1;
    float alphaMoments = success ? max(gMomentsAlpha, 1 / curLength) : 1.0f;

    // compute first two moments of luminance
    float2 moments;
    moments.r = curLuminance;
    moments.g = moments.r * moments.r;
    moments = lerp(h.moments, moments, alphaMoments);

    const float variance = max(0.f, moments.g - moments.r * moments.r);
    const bool isHistoryShort = curLength < 8;

    const float decay = isHistoryShort ? 1.0 : (success ? (1.0f - gAlpha) : 0.0f);
    const float unweightedAlpha = 1.0f / (decay * h.weight.x + 1);
    const float historyWeight = decay * h.weight.x + 1;
    const float3 outUnweightedIllumination = success ? lerp(h.unweightedIllumination, illumination, unweightedAlpha) : illumination;

#if DW_ENABLED
    const float weightedDecay = isHistoryShort ? 1.0 : (success ? (1.0f - gWeightedAlpha) : 0.0f);
    const float weightedAlpha = float(sampleCount) / (weightedDecay * h.weight.y + float(sampleCount));
    const float weightedHistoryWeight = weightedDecay * h.weight.y + sampleCount;
    const float3 outWeightedIllumination = success ? lerp(h.weightedIllumination, illumination, weightedAlpha) : illumination;

    const float3 delta = clamp((illumination - h.unweightedIllumination), -gMaxGradient, gMaxGradient);
    const float3 outGradient = success ? lerp(h.gradient, delta, gGradientAlpha) : delta;
#endif


    PS_OUT psOut;
    psOut.OutIllumination = float4(outUnweightedIllumination, variance);
    psOut.OutMoments = moments;
    psOut.OutHistoryLength = curLength;
#if DW_ENABLED
    psOut.OutHistoryWeight = float2(historyWeight, weightedHistoryWeight);
    psOut.OutWeightedIllumination = float4(outWeightedIllumination, variance);
    psOut.OutGradient.xyz = outGradient;
#else
    psOut.OutHistoryWeight = historyWeight;
#endif
    psOut.OutVariance = variance;

    return psOut;
}
