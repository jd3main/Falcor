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

// Workaround for isnan() not working in slang.
bool isNaN(float f)
{
    uint u = asuint(f) & ~0x80000000u; // clear out the sign bit
    return (u > 0x7F800000);           // greater than Inf is NaN
}

cbuffer PerImageCB
{
    Texture2D gMotion;
    Texture2D gPositionNormalFwidth;
    Texture2D gColor;
    Texture2D gAlbedo;
    Texture2D gEmission;
    Texture2D gPrevIllum;
    Texture2D gPrevShortIllum;
    Texture2D gPrevLongIllum;
    Texture2D gPrevMoments;
    Texture2D gLinearZAndNormal;
    Texture2D gPrevLinearZAndNormal;

    Texture2D<uint> gSampleCount;
    Texture2D gPrevHistoryLength;
    Texture2D gPrevShortHistoryWeight;
    Texture2D gPrevLongHistoryWeight;

    RWTexture2D gOutShortHistoryCentroid;
    RWTexture2D gOutLongHistoryCentroid;
    Texture2D gPrevShortHistoryCentroid;
    Texture2D gPrevLongHistoryCentroid;

    float gDelay;
    float gMomentsAlpha;
    float gMaxHistoryLength;
    float gShortHistoryMaxWeight;
    float gLongHistoryMaxWeight;
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
    float shortWeight;
    float longWeight;
    float3 shortIllumination;
    float3 longIllumination;
    float shortCentroid;
    float longCentroid;
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
    float shortHistoryWeight = 0;
    float longHistoryWeight = 0;
    float3 shortHistoryIllum = float3(0, 0, 0);
    float3 longHistoryIllum = float3(0, 0, 0);
    float shortHistoryCentroid = 0;
    float longHistoryCentroid = 0;

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
                shortHistoryWeight += w[sampleIdx] * gPrevShortHistoryWeight[loc].x;
                longHistoryWeight += w[sampleIdx] * gPrevLongHistoryWeight[loc].x;
                shortHistoryIllum += w[sampleIdx] * gPrevShortIllum[loc].xyz;
                longHistoryIllum += w[sampleIdx] * gPrevLongIllum[loc].xyz;
                shortHistoryCentroid += w[sampleIdx] * gPrevShortHistoryCentroid[loc].x;
                longHistoryCentroid += w[sampleIdx] * gPrevLongHistoryCentroid[loc].x;
            }
        }

        // redistribute weights in case not all taps were used
        valid = (sumw >= 0.01);
        prevMoments = valid ? prevMoments / sumw : float2(0, 0);
        historyLength = valid ? historyLength / sumw : 0;
        shortHistoryWeight = valid ? shortHistoryWeight / sumw : 0;
        longHistoryWeight = valid ? longHistoryWeight / sumw : 0;
        shortHistoryIllum = valid ? shortHistoryIllum / sumw : float3(0, 0, 0);
        longHistoryIllum = valid ? longHistoryIllum / sumw : float3(0, 0, 0);
        shortHistoryCentroid = valid ? shortHistoryCentroid / sumw : 0;
        longHistoryCentroid = valid ? longHistoryCentroid / sumw : 0;
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
                    shortHistoryWeight += gPrevShortHistoryWeight[p].x;
                    longHistoryWeight += gPrevLongHistoryWeight[p].x;
                    shortHistoryIllum += gPrevShortIllum[p].xyz;
                    longHistoryIllum += gPrevLongIllum[p].xyz;
                    shortHistoryCentroid += gPrevShortHistoryCentroid[p].x;
                    longHistoryCentroid += gPrevLongHistoryCentroid[p].x;
                }
            }
        }
        if (nValid > 0)
        {
            valid = true;
            prevMoments /= nValid;
            historyLength /= nValid;
            shortHistoryWeight /= nValid;
            longHistoryWeight /= nValid;
            shortHistoryIllum /= nValid;
            longHistoryIllum /= nValid;
            shortHistoryCentroid /= nValid;
        }
    }

    history.moments = prevMoments;
    history.length = historyLength;
    history.shortWeight = shortHistoryWeight;
    history.longWeight = longHistoryWeight;
    history.shortIllumination = shortHistoryIllum;
    history.longIllumination = longHistoryIllum;
    history.shortCentroid = shortHistoryCentroid;
    history.longCentroid = longHistoryCentroid;

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
    float4 OutIllumination  : SV_TARGET0;
    float2 OutMoments       : SV_TARGET1;
    float OutHistoryLength  : SV_TARGET2;
    float OutShortHistoryWeight : SV_TARGET3;
    float OutLongHistoryWeight  : SV_TARGET4;
    float4 OutShortHistoryIllumination  : SV_TARGET5;
    float4 OutLongHistoryIllumination   : SV_TARGET6;
};

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
    History history;
    const int sampleCount = gSampleCount[ipos];
    const bool success = loadHistory(posH.xy, history);

    // Compute alpha
    float alpha = 0;
    float3 curOutIllumination = float3(0, 0, 0);

    if (history.longWeight <= gShortHistoryMaxWeight)
    {
        alpha = sampleCount / (sampleCount + history.longWeight);
        curOutIllumination = lerp(history.longIllumination, illumination, alpha);

    }
    else
    {
        /*
            C_m = lerp(C_s, C_l, beta)
            W_m = lerp(W_s, W_l, beta)
            gDelay = lerp((C_m - 1), 0, n / (W_m + n))
        */

        const float diffCentroid = history.shortCentroid - history.longCentroid;
        const float diffWeight = history.shortWeight - history.longWeight;
        const float shortCentroid_sub_D_sub_1 = history.shortCentroid - gDelay - 1;

        const float a = diffCentroid * diffWeight;
        const float b = diffCentroid * history.shortWeight + diffWeight * shortCentroid_sub_D_sub_1;
        const float c = shortCentroid_sub_D_sub_1 * history.shortWeight - sampleCount * gDelay;

        const float beta = (-b - sqrt(b * b - 4 * a * c)) / (2 * a);
        const float betaClamped = clamp(beta, 0, 1);

        /*
        if (ipos.x < 100)
        {
            if (beta <= 0)
                curOutIllumination = float3(0, 0, 1);
            else if (beta >= 1)
                curOutIllumination = float3(1, 0, 0);
            else
                curOutIllumination = colormapInferno(beta);
        }
        else*/
        {
            float3 blendedIllumination = lerp(history.shortIllumination, history.longIllumination, betaClamped);
            float blendedWeight = lerp(history.shortWeight, history.longWeight, betaClamped);
            curOutIllumination = lerp(blendedIllumination.xyz, illumination, sampleCount / (blendedWeight + sampleCount));
        }
    }

    // Calculate alpha for moments in simpler way
    const float curWeight = success ? min(history.length + 1, gMaxHistoryLength) : 1;
    float alphaMoments = success ? max(gMomentsAlpha, 1 / curWeight) : 1.0f;

    // compute first two moments of luminance
    float2 moments;
    moments.r = curLuminance;
    moments.g = moments.r * moments.r;

    // temporal integration of the moments
    moments = lerp(history.moments, moments, alphaMoments);

    float variance = max(0.f, moments.g - moments.r * moments.r);

    //variance *= computeVarianceScale(16, 16, alpha);

    PS_OUT psOut;
    // temporal integration of illumination
    psOut.OutIllumination.rgb = curOutIllumination;
    // variance is propagated through the alpha channel
    psOut.OutIllumination.a = variance;
    psOut.OutMoments = moments;
    psOut.OutHistoryLength = curWeight;

    // float n = sampleCount;
    float n = 1;
    psOut.OutShortHistoryWeight = min(history.shortWeight + n, gShortHistoryMaxWeight);
    psOut.OutLongHistoryWeight = min(history.longWeight + n, gLongHistoryMaxWeight);
    psOut.OutShortHistoryIllumination.rgb = lerp(history.shortIllumination, illumination, n / (history.shortWeight + n));
    psOut.OutLongHistoryIllumination.rgb = lerp(history.longIllumination, illumination, n / (history.longWeight + n));
    psOut.OutShortHistoryIllumination.a = variance;
    psOut.OutLongHistoryIllumination.a = variance;

    // Calculate Centroid
    const float newShortCentroid = success ? (history.shortCentroid - 1) * history.shortWeight / (history.shortWeight + n) : 0;
    const float newLongCentroid = success ? (history.longCentroid - 1) * history.longWeight / (history.longWeight + n) : 0;
    gOutShortHistoryCentroid[ipos] = newShortCentroid;
    gOutLongHistoryCentroid[ipos] = newLongCentroid;

    return psOut;
}
