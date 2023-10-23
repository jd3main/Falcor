#include "DynamicWeightingSVGF.h"

#include "RenderGraph/RenderPassLibrary.h"
#include "RenderGraph/BasePasses/FullScreenPass.h"

 /*
 (from original SVGF Pass)
 TODO:
 - clean up shaders
 - clean up UI: tooltips, etc.
 - handle skybox pixels
 - enum for fbo channel indices
 */

const RenderPass::Info DynamicWeightingSVGF::kInfo{ "DynamicWeightingSVGF", "Modified SVGF denoising pass." };

namespace
{
    // Shader source files
    const char kPackLinearZAndNormalShader[] = "RenderPasses/SVGFPass/SVGFPackLinearZAndNormal.ps.slang";
    const char kReprojectShader[] = "RenderPasses/DynamicWeightingSVGF/DynamicWeightingSVGFReproject.ps.slang";
    const char kAtrousShader[] = "RenderPasses/SVGFPass/SVGFAtrous.ps.slang";
    const char kFilterMomentShader[] = "RenderPasses/SVGFPass/SVGFFilterMoments.ps.slang";
    const char kFinalModulateShader[] = "RenderPasses/SVGFPass/SVGFFinalModulate.ps.slang";

    // Names of valid entries in the parameter dictionary.
    const char kEnabled[] = "Enabled";
    const char kIterations[] = "Iterations";
    const char kFeedbackTap[] = "FeedbackTap";
    const char kVarianceEpsilon[] = "VarianceEpsilon";
    const char kPhiColor[] = "PhiColor";
    const char kPhiNormal[] = "PhiNormal";
    const char kMomentsAlpha[] = "MomentsAlpha";
    const char kMaxHistoryLength[] = "MaxHistoryLength";
    const char kExpectedDelay[] = "ExpectedDelay";
    const char kUnweightedHistoryMaxWeight[] = "UnweightedHistoryMaxWeight";
    const char kWeightedHistoryMaxWeight[] = "WeightedHistoryMaxWeight";

    // Input buffer names
    const char kInputBufferAlbedo[] = "Albedo";
    const char kInputBufferColor[] = "Color";
    const char kInputBufferSampleCount[] = "SampleCount";
    const char kInputBufferEmission[] = "Emission";
    const char kInputBufferWorldPosition[] = "WorldPosition";
    const char kInputBufferWorldNormal[] = "WorldNormal";
    const char kInputBufferPosNormalFwidth[] = "PositionNormalFwidth";
    const char kInputBufferLinearZ[] = "LinearZ";
    const char kInputBufferMotionVector[] = "MotionVec";

    // Internal buffer names
    const char kInternalBufferPreviousLinearZAndNormal[] = "Previous Linear Z and Packed Normal";
    const char kInternalBufferPreviousUnweightedHistoryWeight[] = "Previous Weight (Unweighted)";
    const char kInternalBufferPreviousWeightedHistoryWeight[] = "Previous Weight (Weighted)";

    // Output buffer name
    const char kOutputBufferFilteredImage[] = "Filtered image";
    const char kOutputHistoryLength[] = "HistLength";
    const char kOutputUnweightedHistoryWeight[] = "Weight_U";
    const char kOutputWeightedHistoryWeight[] = "Weight_W";
    const char kOutputUnweightedHistoryIllumination[] = "Illumination_U";
    const char kOutputWeightedHistoryIllumination[] = "Illumination_W";
    const char kOutputUnweightedHistoryFilteredImage[] = "Filtered_U";
    const char kOutputWeightedHistoryFilteredImage[] = "Filtered_W";
    const char kOutputSampleCount[] = "SampleCount";

    enum ReprojectOutFields
    {
        Illumination,
        Moments,
        HistoryLength,
        UnweightedHistoryWeight,
        WeightedHistoryWeight,
        UnweightedHistoryIllumination,
        WeightedHistoryIllumination,
    };
}

// Don't remove this. it's required for hot-reload to function properly
extern "C" FALCOR_API_EXPORT const char* getProjDir()
{
    return PROJECT_DIR;
}

extern "C" FALCOR_API_EXPORT void getPasses(Falcor::RenderPassLibrary & lib)
{
    lib.registerPass(DynamicWeightingSVGF::kInfo, DynamicWeightingSVGF::create);
}

DynamicWeightingSVGF::SharedPtr DynamicWeightingSVGF::create(RenderContext* pRenderContext, const Dictionary& dict)
{
    return SharedPtr(new DynamicWeightingSVGF(dict));
}

DynamicWeightingSVGF::DynamicWeightingSVGF(const Dictionary& dict)
    : RenderPass(kInfo)
{
    for (const auto& [key, value] : dict)
    {
        if (key == kEnabled) mFilterEnabled = value;
        else if (key == kIterations) mFilterIterations = value;
        else if (key == kFeedbackTap) mFeedbackTap = value;
        else if (key == kVarianceEpsilon) mVarainceEpsilon = value;
        else if (key == kPhiColor) mPhiColor = value;
        else if (key == kPhiNormal) mPhiNormal = value;
        else if (key == kMomentsAlpha) mMomentsAlpha = value;
        else if (key == kMaxHistoryLength) mMaxHistoryLength = value;
        else if (key == kExpectedDelay) mExpectedDelay = value;
        else if (key == kUnweightedHistoryMaxWeight) mUnweightedHistoryMaxWeight = value;
        else if (key == kWeightedHistoryMaxWeight) mWeightedHistoryMaxWeight = value;
        else logWarning("Unknown field '{}' in DynamicWeightingSVGF dictionary.", key);
    }

    mpPackLinearZAndNormal = FullScreenPass::create(kPackLinearZAndNormalShader);
    mpReprojection = FullScreenPass::create(kReprojectShader);
    mpAtrous = FullScreenPass::create(kAtrousShader);
    mpFilterMoments = FullScreenPass::create(kFilterMomentShader);
    mpFinalModulate = FullScreenPass::create(kFinalModulateShader);
    FALCOR_ASSERT(mpPackLinearZAndNormal && mpReprojection && mpAtrous && mpFilterMoments && mpFinalModulate);
}

Dictionary DynamicWeightingSVGF::getScriptingDictionary()
{
    Dictionary dict;
    dict[kEnabled] = mFilterEnabled;
    dict[kIterations] = mFilterIterations;
    dict[kFeedbackTap] = mFeedbackTap;
    dict[kVarianceEpsilon] = mVarainceEpsilon;
    dict[kPhiColor] = mPhiColor;
    dict[kPhiNormal] = mPhiNormal;
    dict[kMomentsAlpha] = mMomentsAlpha;
    dict[kMaxHistoryLength] = mMaxHistoryLength;
    dict[kExpectedDelay] = mExpectedDelay;
    dict[kUnweightedHistoryMaxWeight] = mUnweightedHistoryMaxWeight;
    dict[kWeightedHistoryMaxWeight] = mWeightedHistoryMaxWeight;
    return dict;
}

/*
Reproject:
  - takes: motion, color, prevLighting, prevMoments, linearZ, prevLinearZ, historyLen
    returns: illumination, moments, historyLength
Variance/filter moments:
  - takes: illumination, moments, history length, normal+depth
  - returns: filtered illumination+variance (to ping pong fbo)
a-trous:
  - takes: albedo, filtered illumination+variance, normal+depth, history length
  - returns: final color
*/

RenderPassReflection DynamicWeightingSVGF::reflect(const CompileData& compileData)
{
    RenderPassReflection reflector;

    reflector.addInput(kInputBufferAlbedo, "Albedo");
    reflector.addInput(kInputBufferColor, "Color");
    reflector.addInput(kInputBufferSampleCount, "SampleCount").format(ResourceFormat::R8Uint).bindFlags(Resource::BindFlags::ShaderResource);
    reflector.addInput(kInputBufferEmission, "Emission");
    reflector.addInput(kInputBufferWorldPosition, "posW");
    reflector.addInput(kInputBufferWorldNormal, "World Normal");
    reflector.addInput(kInputBufferPosNormalFwidth, "PositionNormalFwidth");
    reflector.addInput(kInputBufferLinearZ, "LinearZ");
    reflector.addInput(kInputBufferMotionVector, "Motion vectors");

    reflector.addInternal(kInternalBufferPreviousLinearZAndNormal, "Previous Linear Z and Packed Normal")
        .format(ResourceFormat::RGBA32Float)
        .bindFlags(Resource::BindFlags::RenderTarget | Resource::BindFlags::ShaderResource);

    reflector.addInternal(kInternalBufferPreviousUnweightedHistoryWeight, "Previous weight of unweighted history");
    reflector.addInternal(kInternalBufferPreviousWeightedHistoryWeight, "Previous weight of weighted history");

    reflector.addOutput(kOutputBufferFilteredImage, "Filtered image").format(ResourceFormat::RGBA16Float);
    reflector.addOutput(kOutputHistoryLength, "History Sample Length").format(ResourceFormat::R32Float);
    reflector.addOutput(kOutputUnweightedHistoryWeight, "Weight of unweighted history").format(ResourceFormat::R32Float);
    reflector.addOutput(kOutputWeightedHistoryWeight, "Weight of long history").format(ResourceFormat::R32Float);
    reflector.addOutput(kOutputUnweightedHistoryIllumination, "Unweighted History Illumination").format(ResourceFormat::RGBA16Float);
    reflector.addOutput(kOutputWeightedHistoryIllumination, "Weighted History Illumination").format(ResourceFormat::RGBA16Float);
    reflector.addOutput(kOutputUnweightedHistoryFilteredImage, "Filtered image with unweighted history").format(ResourceFormat::RGBA16Float);
    reflector.addOutput(kOutputWeightedHistoryFilteredImage, "Filtered image with long history ").format(ResourceFormat::RGBA16Float);
    reflector.addOutput(kOutputSampleCount, "Sample Count").format(ResourceFormat::R8Uint);

    return reflector;
}

void DynamicWeightingSVGF::compile(RenderContext* pRenderContext, const CompileData& compileData)
{
    allocateFbos(compileData.defaultTexDims, pRenderContext);
    mBuffersNeedClear = true;
}

void DynamicWeightingSVGF::execute(RenderContext* pRenderContext, const RenderData& renderData)
{
    // Input textures
    Texture::SharedPtr pAlbedoTexture = renderData.getTexture(kInputBufferAlbedo);
    Texture::SharedPtr pColorTexture = renderData.getTexture(kInputBufferColor);
    Texture::SharedPtr pSampleCountTexture = renderData.getTexture(kInputBufferSampleCount);
    Texture::SharedPtr pEmissionTexture = renderData.getTexture(kInputBufferEmission);
    Texture::SharedPtr pWorldPositionTexture = renderData.getTexture(kInputBufferWorldPosition);
    Texture::SharedPtr pWorldNormalTexture = renderData.getTexture(kInputBufferWorldNormal);
    Texture::SharedPtr pPosNormalFwidthTexture = renderData.getTexture(kInputBufferPosNormalFwidth);
    Texture::SharedPtr pLinearZTexture = renderData.getTexture(kInputBufferLinearZ);
    Texture::SharedPtr pMotionVectorTexture = renderData.getTexture(kInputBufferMotionVector);

    // Output Textures
    Texture::SharedPtr pOutputTexture = renderData.getTexture(kOutputBufferFilteredImage);
    Texture::SharedPtr pOutputHistoryLength = renderData.getTexture(kOutputHistoryLength);
    Texture::SharedPtr pOutputUnweightedHistoryWeight = renderData.getTexture(kOutputUnweightedHistoryWeight);
    Texture::SharedPtr pOutputWeightedHistoryWeight = renderData.getTexture(kOutputWeightedHistoryWeight);
    Texture::SharedPtr pOutputUnweightedHistoryIllumination = renderData.getTexture(kOutputUnweightedHistoryIllumination);
    Texture::SharedPtr pOutputWeightedHistoryIllumination = renderData.getTexture(kOutputWeightedHistoryIllumination);
    Texture::SharedPtr pOutputUnweightedHistoryFilteredImage = renderData.getTexture(kOutputUnweightedHistoryFilteredImage);
    Texture::SharedPtr pOutputWeightedHistoryFilteredImage = renderData.getTexture(kOutputWeightedHistoryFilteredImage);
    Texture::SharedPtr pOutputSampleCount = renderData.getTexture(kOutputSampleCount);

    FALCOR_ASSERT(mpFilteredIlluminationFbo &&
        mpFilteredIlluminationFbo->getWidth() == pAlbedoTexture->getWidth() &&
        mpFilteredIlluminationFbo->getHeight() == pAlbedoTexture->getHeight());

    if (mBuffersNeedClear)
    {
        clearBuffers(pRenderContext, renderData);
        mBuffersNeedClear = false;
    }

    if (mFilterEnabled)
    {
        // Grab linear z and its derivative and also pack the normal into
        // the last two channels of the mpLinearZAndNormalFbo.
        computeLinearZAndNormal(pRenderContext, pLinearZTexture, pWorldNormalTexture);

        // Demodulate input color & albedo to get illumination and lerp in
        // reprojected filtered illumination from the previous frame.
        // Stores the result as well as initial moments and an updated
        // per-pixel history length in mpCurReprojFbo.
        Texture::SharedPtr pPrevLinearZAndNormalTexture = renderData.getTexture(kInternalBufferPreviousLinearZAndNormal);
        computeReprojection(pRenderContext, pAlbedoTexture, pColorTexture, pSampleCountTexture,
            pEmissionTexture,
            pMotionVectorTexture, pPosNormalFwidthTexture,
            pPrevLinearZAndNormalTexture);

        // Do a first cross-bilateral filtering of the illumination and
        // estimate its variance, storing the result into a float4 in
        // mpPingPongFbo[0].  Takes mpCurReprojFbo as input.
        computeFilteredMoments(pRenderContext);

        // Filter illumination from mpCurReprojFbo[0], storing the result
        // in mpPingPongFbo[0].  Along the way (or at the end, depending on
        // the value of mFeedbackTap), save the filtered illumination for
        // next time into mpFilteredPastFbo.
        computeAtrousDecomposition(pRenderContext, pAlbedoTexture);


        // Compute albedo * filtered illumination and add emission back in.
        // Read from mpPingPongFbo and write to mpFinalFbo.
        computeFinalModulate(pRenderContext, pAlbedoTexture, pEmissionTexture);

        // Blit into the output texture.
        pRenderContext->blit(mpFinalFbo->getColorTexture(0)->getSRV(), pOutputTexture->getRTV());
        pRenderContext->blit(mpPingPongFbo[2]->getColorTexture(0)->getSRV(), pOutputUnweightedHistoryIllumination->getRTV());
        pRenderContext->blit(mpPingPongFbo[4]->getColorTexture(0)->getSRV(), pOutputWeightedHistoryIllumination->getRTV());
        pRenderContext->blit(mpFinalFboUnweighted->getColorTexture(0)->getSRV(), pOutputUnweightedHistoryFilteredImage->getRTV());
        pRenderContext->blit(mpFinalFboWeighted->getColorTexture(0)->getSRV(), pOutputWeightedHistoryFilteredImage->getRTV());
        pRenderContext->blit(mpPrevReprojFbo->getColorTexture(ReprojectOutFields::HistoryLength)->getSRV(), pOutputHistoryLength->getRTV());
        pRenderContext->blit(mpPrevReprojFbo->getColorTexture(ReprojectOutFields::UnweightedHistoryWeight)->getSRV(), pOutputUnweightedHistoryWeight->getRTV());
        pRenderContext->blit(mpPrevReprojFbo->getColorTexture(ReprojectOutFields::WeightedHistoryWeight)->getSRV(), pOutputWeightedHistoryWeight->getRTV());
        pRenderContext->blit(pSampleCountTexture->getSRV(), pOutputSampleCount->getRTV());

        // Swap resources so we're ready for next frame.
        std::swap(mpCurReprojFbo, mpPrevReprojFbo);
        pRenderContext->blit(mpLinearZAndNormalFbo->getColorTexture(0)->getSRV(), pPrevLinearZAndNormalTexture->getRTV());
    }
    else
    {
        pRenderContext->blit(pColorTexture->getSRV(), pOutputTexture->getRTV());
    }
}

void DynamicWeightingSVGF::allocateFbos(uint2 dim, RenderContext* pRenderContext)
{
    {
        // Screen-size FBOs with 3 MRTs: one that is RGBA32F, one that is
        // RG32F for the luminance moments, and one that is R16F.
        Fbo::Desc desc;
        desc.setSampleCount(0);
        desc.setColorTarget(ReprojectOutFields::Illumination, Falcor::ResourceFormat::RGBA32Float);
        desc.setColorTarget(ReprojectOutFields::Moments, Falcor::ResourceFormat::RG32Float);
        desc.setColorTarget(ReprojectOutFields::HistoryLength, Falcor::ResourceFormat::R32Float);
        desc.setColorTarget(ReprojectOutFields::UnweightedHistoryWeight, Falcor::ResourceFormat::R32Float);
        desc.setColorTarget(ReprojectOutFields::WeightedHistoryWeight, Falcor::ResourceFormat::R32Float);
        desc.setColorTarget(ReprojectOutFields::UnweightedHistoryIllumination, Falcor::ResourceFormat::RGBA32Float);
        desc.setColorTarget(ReprojectOutFields::WeightedHistoryIllumination, Falcor::ResourceFormat::RGBA32Float);
        mpCurReprojFbo = Fbo::create2D(dim.x, dim.y, desc);
        mpPrevReprojFbo = Fbo::create2D(dim.x, dim.y, desc);
    }

    {
        // Screen-size RGBA32F buffer for linear Z, derivative, and packed normal
        Fbo::Desc desc;
        desc.setColorTarget(0, Falcor::ResourceFormat::RGBA32Float);
        mpLinearZAndNormalFbo = Fbo::create2D(dim.x, dim.y, desc);
    }

    {
        // Screen-size FBOs with 1 RGBA32F buffer
        Fbo::Desc desc;
        desc.setColorTarget(0, Falcor::ResourceFormat::RGBA32Float);
        for (int i=0; i<6; i++)
        {
            mpPingPongFbo[i] = Fbo::create2D(dim.x, dim.y, desc);
        }
        for (int i=0; i<3; i++)
        {
            mpFilteredPastFbo[i] = Fbo::create2D(dim.x, dim.y, desc);
        }
        mpFinalFbo = Fbo::create2D(dim.x, dim.y, desc);
        mpFinalFboUnweighted = Fbo::create2D(dim.x, dim.y, desc);
        mpFinalFboWeighted = Fbo::create2D(dim.x, dim.y, desc);
        mpFilteredIlluminationFbo = Fbo::create2D(dim.x, dim.y, desc);
    }

    mBuffersNeedClear = true;
}

void DynamicWeightingSVGF::clearBuffers(RenderContext* pRenderContext, const RenderData& renderData)
{
    for (int i=0; i<6; i++)
        pRenderContext->clearFbo(mpPingPongFbo[i].get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpLinearZAndNormalFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    for (int i=0; i<3; i++)
        pRenderContext->clearFbo(mpFilteredPastFbo[i].get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpCurReprojFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpPrevReprojFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpFilteredIlluminationFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpFinalFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpFinalFboUnweighted.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpFinalFboWeighted.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearTexture(renderData.getTexture(kInternalBufferPreviousLinearZAndNormal).get());
    pRenderContext->clearTexture(renderData.getTexture(kInternalBufferPreviousUnweightedHistoryWeight).get());
    pRenderContext->clearTexture(renderData.getTexture(kInternalBufferPreviousWeightedHistoryWeight).get());
}

// Extracts linear z and its derivative from the linear Z texture and packs
// the normal from the world normal texture and packes them into the FBO.
// (It's slightly wasteful to copy linear z here, but having this all
// together in a single buffer is a small simplification, since we make a
// copy of it to refer to in the next frame.)
void DynamicWeightingSVGF::computeLinearZAndNormal(RenderContext* pRenderContext, Texture::SharedPtr pLinearZTexture,
    Texture::SharedPtr pWorldNormalTexture)
{
    auto perImageCB = mpPackLinearZAndNormal["PerImageCB"];
    perImageCB["gLinearZ"] = pLinearZTexture;
    perImageCB["gNormal"] = pWorldNormalTexture;

    mpPackLinearZAndNormal->execute(pRenderContext, mpLinearZAndNormalFbo);
}

void DynamicWeightingSVGF::computeReprojection(RenderContext* pRenderContext, Texture::SharedPtr pAlbedoTexture,
    Texture::SharedPtr pColorTexture,
    Texture::SharedPtr pSampleCountTexture,
    Texture::SharedPtr pEmissionTexture,
    Texture::SharedPtr pMotionVectorTexture,
    Texture::SharedPtr pPositionNormalFwidthTexture,
    Texture::SharedPtr pPrevLinearZTexture)
{
    auto perImageCB = mpReprojection["PerImageCB"];

    // Setup textures for our reprojection shader pass
    perImageCB["gMotion"] = pMotionVectorTexture;
    perImageCB["gColor"] = pColorTexture;
    perImageCB["gSampleCount"] = pSampleCountTexture;
    perImageCB["gEmission"] = pEmissionTexture;
    perImageCB["gAlbedo"] = pAlbedoTexture;
    perImageCB["gPositionNormalFwidth"] = pPositionNormalFwidthTexture;
    perImageCB["gPrevIllum"] = mpFilteredPastFbo[0]->getColorTexture(0);
    perImageCB["gPrevMoments"] = mpPrevReprojFbo->getColorTexture(ReprojectOutFields::Moments);
    perImageCB["gLinearZAndNormal"] = mpLinearZAndNormalFbo->getColorTexture(0);
    perImageCB["gPrevLinearZAndNormal"] = pPrevLinearZTexture;
    perImageCB["gPrevHistoryLength"] = mpPrevReprojFbo->getColorTexture(ReprojectOutFields::HistoryLength);
    perImageCB["gPrevUnweightedHistoryWeight"] = mpPrevReprojFbo->getColorTexture(ReprojectOutFields::UnweightedHistoryWeight);
    perImageCB["gPrevWeightedHistoryWeight"] = mpPrevReprojFbo->getColorTexture(ReprojectOutFields::WeightedHistoryWeight);
    perImageCB["gPrevUnweightedIllum"] = mpFilteredPastFbo[1]->getColorTexture(0);
    perImageCB["gPrevWeightedIllum"] = mpFilteredPastFbo[2]->getColorTexture(0);

    // Setup variables for our reprojection pass
    perImageCB["gMomentsAlpha"] = mMomentsAlpha;
    perImageCB["gMaxHistoryLength"] = mMaxHistoryLength;
    perImageCB["gDelay"] = mExpectedDelay;
    perImageCB["gUnweightedHistoryMaxWeight"] = mUnweightedHistoryMaxWeight;
    perImageCB["gWeightedHistoryMaxWeight"] = mWeightedHistoryMaxWeight;

    mpReprojection->execute(pRenderContext, mpCurReprojFbo);
}

void DynamicWeightingSVGF::computeFilteredMoments(RenderContext* pRenderContext)
{
    auto perImageCB = mpFilterMoments["PerImageCB"];

    perImageCB["gLinearZAndNormal"] = mpLinearZAndNormalFbo->getColorTexture(0);
    perImageCB["gMoments"] = mpCurReprojFbo->getColorTexture(ReprojectOutFields::Moments);

    perImageCB["gPhiColor"] = mPhiColor;
    perImageCB["gPhiNormal"] = mPhiNormal;

    // Main illumination
    perImageCB["gHistoryLength"] = mpCurReprojFbo->getColorTexture(ReprojectOutFields::HistoryLength);
    perImageCB["gIllumination"] = mpCurReprojFbo->getColorTexture(ReprojectOutFields::Illumination);
    mpFilterMoments->execute(pRenderContext, mpPingPongFbo[0]);

    // Unweighted History
    perImageCB["gHistoryLength"] = mpCurReprojFbo->getColorTexture(ReprojectOutFields::UnweightedHistoryWeight);
    perImageCB["gIllumination"] = mpCurReprojFbo->getColorTexture(ReprojectOutFields::UnweightedHistoryIllumination);
    mpFilterMoments->execute(pRenderContext, mpPingPongFbo[2]);

    // Weighted History
    perImageCB["gHistoryLength"] = mpCurReprojFbo->getColorTexture(ReprojectOutFields::WeightedHistoryWeight);
    perImageCB["gIllumination"] = mpCurReprojFbo->getColorTexture(ReprojectOutFields::WeightedHistoryIllumination);
    mpFilterMoments->execute(pRenderContext, mpPingPongFbo[4]);
}

void DynamicWeightingSVGF::computeAtrousDecomposition(RenderContext* pRenderContext, Texture::SharedPtr pAlbedoTexture)
{
    auto perImageCB = mpAtrous["PerImageCB"];

    perImageCB["gAlbedo"] = pAlbedoTexture;
    perImageCB["gLinearZAndNormal"] = mpLinearZAndNormalFbo->getColorTexture(0);

    perImageCB["gPhiColor"] = mPhiColor;
    perImageCB["gPhiNormal"] = mPhiNormal;

    int weightTextureIds[] = {
        ReprojectOutFields::HistoryLength,
        ReprojectOutFields::UnweightedHistoryWeight,
        ReprojectOutFields::WeightedHistoryWeight,
    };

    for (int srcId = 0; srcId < 6; srcId += 2)
    {
        int dstId = srcId + 1;
        perImageCB["gHistoryLength"] = mpCurReprojFbo->getColorTexture(weightTextureIds[srcId/2]);
        for (int i = 0; i < mFilterIterations; i++)
        {
            perImageCB["gStepSize"] = 1 << i;
            perImageCB["gIllumination"] = mpPingPongFbo[srcId]->getColorTexture(0);
            Fbo::SharedPtr curTargetFbo = mpPingPongFbo[dstId];
            mpAtrous->execute(pRenderContext, curTargetFbo);

            // store the filtered color for the feedback path
            if (i == std::min(mFeedbackTap, mFilterIterations - 1))
            {
                pRenderContext->blit(curTargetFbo->getColorTexture(0)->getSRV(), mpFilteredPastFbo[srcId/2]->getRenderTargetView(0));
            }

            std::swap(mpPingPongFbo[srcId], mpPingPongFbo[dstId]);
        }
    }

    if (mFeedbackTap < 0)
    {
        pRenderContext->blit(mpCurReprojFbo->getColorTexture(ReprojectOutFields::Illumination)->getSRV(), mpFilteredPastFbo[0]->getRenderTargetView(0));
        pRenderContext->blit(mpCurReprojFbo->getColorTexture(ReprojectOutFields::UnweightedHistoryIllumination)->getSRV(), mpFilteredPastFbo[1]->getRenderTargetView(0));
        pRenderContext->blit(mpCurReprojFbo->getColorTexture(ReprojectOutFields::WeightedHistoryIllumination)->getSRV(), mpFilteredPastFbo[2]->getRenderTargetView(0));
    }
}

void DynamicWeightingSVGF::computeFinalModulate(RenderContext* pRenderContext, Texture::SharedPtr pAlbedoTexture, Texture::SharedPtr pEmissionTexture)
{
    auto perImageCB = mpFinalModulate["PerImageCB"];
    perImageCB["gAlbedo"] = pAlbedoTexture;
    perImageCB["gEmission"] = pEmissionTexture;

    perImageCB["gIllumination"] = Texture::SharedPtr();     // Force trigger update (probably). I don't know why this is necessary.
    perImageCB["gIllumination"] = mpPingPongFbo[0]->getColorTexture(0);
    mpFinalModulate->execute(pRenderContext, mpFinalFbo);

    perImageCB["gIllumination"] = Texture::SharedPtr();
    perImageCB["gIllumination"] = mpPingPongFbo[2]->getColorTexture(0);
    mpFinalModulate->execute(pRenderContext, mpFinalFboUnweighted);

    perImageCB["gIllumination"] = Texture::SharedPtr();
    perImageCB["gIllumination"] = mpPingPongFbo[4]->getColorTexture(0);
    mpFinalModulate->execute(pRenderContext, mpFinalFboWeighted);
}

void DynamicWeightingSVGF::renderUI(Gui::Widgets& widget)
{
    int dirty = 0;
    dirty |= (int)widget.checkbox("Enable SVGF", mFilterEnabled);

    widget.text("");
    widget.text("Number of filter iterations.  Which");
    widget.text("    iteration feeds into future frames?");
    dirty |= (int)widget.var("Iterations", mFilterIterations, 2, 10, 1);
    dirty |= (int)widget.var("Feedback", mFeedbackTap, -1, mFilterIterations - 2, 1);

    widget.text("");
    widget.text("Contol edge stopping on bilateral fitler");
    dirty |= (int)widget.var("For Color", mPhiColor, 0.0f, 10000.0f, 0.01f);
    dirty |= (int)widget.var("For Normal", mPhiNormal, 0.001f, 1000.0f, 0.2f);

    widget.text("");
    widget.text("How much history should be used?");
    widget.text("    (alpha; 0 = full reuse; 1 = no reuse)");
    dirty |= (int)widget.var("Moments Alpha", mMomentsAlpha, 0.0f, 1.0f, 0.001f);
    dirty |= (int)widget.var("Max History Length", mMaxHistoryLength, 0.0f, 1024.0f, 0.1f);
    dirty |= (int)widget.var("Expected Delay", mExpectedDelay, -1024.0f, 0.0f, 0.05f);
    dirty |= (int)widget.var("Unweighted History Max Weight", mUnweightedHistoryMaxWeight, 0.0f, 1024.0f, 0.1f);
    dirty |= (int)widget.var("Weighted History Max Weight", mWeightedHistoryMaxWeight, 0.0f, 1024.0f, 0.1f);

    if (dirty) mBuffersNeedClear = true;
}
