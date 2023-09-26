#include "TwoHistorySVGFPass.h"

#include "RenderGraph/RenderPassLibrary.h"

 /*
 (from original SVGF Pass)
 TODO:
 - clean up shaders
 - clean up UI: tooltips, etc.
 - handle skybox pixels
 - enum for fbo channel indices
 */

const RenderPass::Info TwoHistorySVGFPass::kInfo{ "TwoHistorySVGFPass", "Modified SVGF denoising pass." };

namespace
{
    // Shader source files
    const char kPackLinearZAndNormalShader[] = "RenderPasses/SVGFPass/SVGFPackLinearZAndNormal.ps.slang";
    const char kReprojectShader[] = "RenderPasses/TwoHistorySVGFPass/TwoHistorySVGFReproject.ps.slang";
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
    const char kAlpha[] = "Alpha";
    const char kMomentsAlpha[] = "MomentsAlpha";
    const char kMaxHistoryWeight[] = "MaxHistoryWeight";

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
    const char kInputBufferHistoryWeight[] = "HistoryWeight";
    const char kInputBufferShortHistoryWeight[] = "wShort";
    const char kInputBufferLongHistoryWeight[] = "wLong";

    // Internal buffer names
    const char kInternalBufferPreviousLinearZAndNormal[] = "Previous Linear Z and Packed Normal";
    const char kInternalBufferPreviousLighting[] = "Previous Lighting";
    const char kInternalBufferPreviousMoments[] = "Previous Moments";
    const char kInternalBufferPreviousTotalWeight[] = "Previous Total Weight";

    // Output buffer name
    const char kOutputBufferFilteredImage[] = "Filtered image";
    const char kOutputHistoryWeight[] = "History Weight";
    const char kOutputShortHistoryWeight[] = "wShort";
    const char kOutputLongHistoryWeight[] = "wLong";
    const char kOutputVariance[] = "Variance";

    enum ReprojectOutFields
    {
        Illumination,
        Moments,
        HistoryWeight,
        Varaince,
        ShortHistoryWeight,
        LongHistoryWeight,
        ShortHistoryIllumination,
        LongHistoryIllumination,
    };
}

// Don't remove this. it's required for hot-reload to function properly
extern "C" FALCOR_API_EXPORT const char* getProjDir()
{
    return PROJECT_DIR;
}

extern "C" FALCOR_API_EXPORT void getPasses(Falcor::RenderPassLibrary & lib)
{
    lib.registerPass(TwoHistorySVGFPass::kInfo, TwoHistorySVGFPass::create);
}

TwoHistorySVGFPass::SharedPtr TwoHistorySVGFPass::create(RenderContext* pRenderContext, const Dictionary& dict)
{
    return SharedPtr(new TwoHistorySVGFPass(dict));
}

TwoHistorySVGFPass::TwoHistorySVGFPass(const Dictionary& dict)
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
        else if (key == kAlpha) mAlpha = value;
        else if (key == kMomentsAlpha) mMomentsAlpha = value;
        else if (key == kMaxHistoryWeight) mMaxHistoryWeight = value;
        else logWarning("Unknown field '{}' in TwoHistorySVGFPass dictionary.", key);
    }

    mpPackLinearZAndNormal = FullScreenPass::create(kPackLinearZAndNormalShader);
    mpReprojection = FullScreenPass::create(kReprojectShader);
    mpAtrous = FullScreenPass::create(kAtrousShader);
    mpFilterMoments = FullScreenPass::create(kFilterMomentShader);
    mpFinalModulate = FullScreenPass::create(kFinalModulateShader);
    FALCOR_ASSERT(mpPackLinearZAndNormal && mpReprojection && mpAtrous && mpFilterMoments && mpFinalModulate);
}

Dictionary TwoHistorySVGFPass::getScriptingDictionary()
{
    Dictionary dict;
    dict[kEnabled] = mFilterEnabled;
    dict[kIterations] = mFilterIterations;
    dict[kFeedbackTap] = mFeedbackTap;
    dict[kVarianceEpsilon] = mVarainceEpsilon;
    dict[kPhiColor] = mPhiColor;
    dict[kPhiNormal] = mPhiNormal;
    dict[kAlpha] = mAlpha;
    dict[kMomentsAlpha] = mMomentsAlpha;
    dict[kMaxHistoryWeight] = mMaxHistoryWeight;
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

RenderPassReflection TwoHistorySVGFPass::reflect(const CompileData& compileData)
{
    RenderPassReflection reflector;

    reflector.addInput(kInputBufferAlbedo, "Albedo");
    reflector.addInput(kInputBufferColor, "Color");
    reflector.addInput(kInputBufferSampleCount, "Sample Count");
    reflector.addInput(kInputBufferEmission, "Emission");
    reflector.addInput(kInputBufferWorldPosition, "World Position");
    reflector.addInput(kInputBufferWorldNormal, "World Normal");
    reflector.addInput(kInputBufferPosNormalFwidth, "PositionNormalFwidth");
    reflector.addInput(kInputBufferLinearZ, "LinearZ");
    reflector.addInput(kInputBufferMotionVector, "Motion vectors");
    reflector.addInput(kInputBufferHistoryWeight, "Buffer for storing history weight");
    reflector.addInput(kInputBufferShortHistoryWeight, "Weight of short history");
    reflector.addInput(kInputBufferLongHistoryWeight, "Weight of long history");

    reflector.addInternal(kInternalBufferPreviousLinearZAndNormal, "Previous Linear Z and Packed Normal")
        .format(ResourceFormat::RGBA32Float)
        .bindFlags(Resource::BindFlags::RenderTarget | Resource::BindFlags::ShaderResource)
        ;
    reflector.addInternal(kInternalBufferPreviousLighting, "Previous Filtered Lighting")
        .format(ResourceFormat::RGBA32Float)
        .bindFlags(Resource::BindFlags::RenderTarget | Resource::BindFlags::ShaderResource)
        ;
    reflector.addInternal(kInternalBufferPreviousMoments, "Previous Moments")
        .format(ResourceFormat::RG32Float)
        .bindFlags(Resource::BindFlags::RenderTarget | Resource::BindFlags::ShaderResource)
        ;

    reflector.addOutput(kOutputBufferFilteredImage, "Filtered image").format(ResourceFormat::RGBA16Float);
    reflector.addOutput(kOutputHistoryWeight, "History Sample Weight").format(ResourceFormat::R32Float);
    reflector.addOutput(kOutputShortHistoryWeight, "Weight of short history").format(ResourceFormat::R32Float);
    reflector.addOutput(kOutputLongHistoryWeight, "Weight of long history").format(ResourceFormat::R32Float);
    reflector.addOutput(kOutputVariance, "Variance").format(ResourceFormat::R32Float);

    return reflector;
}

void TwoHistorySVGFPass::compile(RenderContext* pRenderContext, const CompileData& compileData)
{
    allocateFbos(compileData.defaultTexDims, pRenderContext);
    mBuffersNeedClear = true;
}

void TwoHistorySVGFPass::execute(RenderContext* pRenderContext, const RenderData& renderData)
{
    Texture::SharedPtr pAlbedoTexture = renderData.getTexture(kInputBufferAlbedo);
    Texture::SharedPtr pColorTexture = renderData.getTexture(kInputBufferColor);
    Texture::SharedPtr pSampleCountTexture = renderData.getTexture(kInputBufferSampleCount);
    Texture::SharedPtr pEmissionTexture = renderData.getTexture(kInputBufferEmission);
    Texture::SharedPtr pWorldPositionTexture = renderData.getTexture(kInputBufferWorldPosition);
    Texture::SharedPtr pWorldNormalTexture = renderData.getTexture(kInputBufferWorldNormal);
    Texture::SharedPtr pPosNormalFwidthTexture = renderData.getTexture(kInputBufferPosNormalFwidth);
    Texture::SharedPtr pLinearZTexture = renderData.getTexture(kInputBufferLinearZ);
    Texture::SharedPtr pMotionVectorTexture = renderData.getTexture(kInputBufferMotionVector);

    Texture::SharedPtr pOutputTexture = renderData.getTexture(kOutputBufferFilteredImage);
    Texture::SharedPtr pOutputHistoryWeight = renderData.getTexture(kOutputHistoryWeight);
    Texture::SharedPtr pOutputShortHistoryWeight = renderData.getTexture(kOutputShortHistoryWeight);
    Texture::SharedPtr pOutputLongHistoryWeight = renderData.getTexture(kOutputLongHistoryWeight);
    Texture::SharedPtr pInputBufferHistoryWeight = renderData.getTexture(kInputBufferHistoryWeight);
    Texture::SharedPtr pOutputVariance = renderData.getTexture(kOutputVariance);

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
        Texture::SharedPtr pPrevLinearZAndNormalTexture =
            renderData.getTexture(kInternalBufferPreviousLinearZAndNormal);
        Texture::SharedPtr pPrevTotalWeightTexture =
            renderData.getTexture(kInternalBufferPreviousTotalWeight);
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
        auto perImageCB = mpFinalModulate["PerImageCB"];
        perImageCB["gAlbedo"] = pAlbedoTexture;
        perImageCB["gEmission"] = pEmissionTexture;
        perImageCB["gIllumination"] = mpPingPongFbo[0]->getColorTexture(0);
        mpFinalModulate->execute(pRenderContext, mpFinalFbo);

        // Blit into the output texture.
        pRenderContext->blit(mpFinalFbo->getColorTexture(0)->getSRV(), pOutputTexture->getRTV());
        pRenderContext->blit(mpPrevReprojFbo->getColorTexture(ReprojectOutFields::HistoryWeight)->getSRV(), pOutputHistoryWeight->getRTV());
        pRenderContext->blit(mpPrevReprojFbo->getColorTexture(ReprojectOutFields::ShortHistoryWeight)->getSRV(), pOutputShortHistoryWeight->getRTV());
        pRenderContext->blit(mpPrevReprojFbo->getColorTexture(ReprojectOutFields::LongHistoryWeight)->getSRV(), pOutputLongHistoryWeight->getRTV());
        pRenderContext->blit(mpPrevReprojFbo->getColorTexture(ReprojectOutFields::HistoryWeight)->getSRV(), pInputBufferHistoryWeight->getRTV());
        pRenderContext->blit(mpPrevReprojFbo->getColorTexture(ReprojectOutFields::Varaince)->getSRV(), pOutputVariance->getRTV());


        // Swap resources so we're ready for next frame.
        std::swap(mpCurReprojFbo, mpPrevReprojFbo);
        pRenderContext->blit(mpLinearZAndNormalFbo->getColorTexture(0)->getSRV(),
            pPrevLinearZAndNormalTexture->getRTV());
    }
    else
    {
        pRenderContext->blit(pColorTexture->getSRV(), pOutputTexture->getRTV());
    }
}

void TwoHistorySVGFPass::allocateFbos(uint2 dim, RenderContext* pRenderContext)
{
    {
        // Screen-size FBOs with 3 MRTs: one that is RGBA32F, one that is
        // RG32F for the luminance moments, and one that is R16F.
        Fbo::Desc desc;
        desc.setSampleCount(0);
        desc.setColorTarget(ReprojectOutFields::Illumination, Falcor::ResourceFormat::RGBA32Float);
        desc.setColorTarget(ReprojectOutFields::Moments, Falcor::ResourceFormat::RG32Float);
        desc.setColorTarget(ReprojectOutFields::HistoryWeight, Falcor::ResourceFormat::R32Float);
        desc.setColorTarget(ReprojectOutFields::Varaince, Falcor::ResourceFormat::R32Float);
        desc.setColorTarget(ReprojectOutFields::ShortHistoryWeight, Falcor::ResourceFormat::R32Float);
        desc.setColorTarget(ReprojectOutFields::LongHistoryWeight, Falcor::ResourceFormat::R32Float);
        desc.setColorTarget(ReprojectOutFields::ShortHistoryIllumination, Falcor::ResourceFormat::RGBA32Float);
        desc.setColorTarget(ReprojectOutFields::LongHistoryIllumination, Falcor::ResourceFormat::RGBA32Float);
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
        mpFilteredIlluminationFbo = Fbo::create2D(dim.x, dim.y, desc);
        mpFinalFbo = Fbo::create2D(dim.x, dim.y, desc);
    }

    mBuffersNeedClear = true;
}

void TwoHistorySVGFPass::clearBuffers(RenderContext* pRenderContext, const RenderData& renderData)
{
    for (int i=0; i<6; i++)
        pRenderContext->clearFbo(mpPingPongFbo[i].get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpLinearZAndNormalFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    for (int i=0; i<3; i++)
        pRenderContext->clearFbo(mpFilteredPastFbo[i].get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpCurReprojFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpPrevReprojFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpFilteredIlluminationFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);

    pRenderContext->clearTexture(renderData.getTexture(kInternalBufferPreviousLinearZAndNormal).get());
    pRenderContext->clearTexture(renderData.getTexture(kInternalBufferPreviousLighting).get());
    pRenderContext->clearTexture(renderData.getTexture(kInternalBufferPreviousMoments).get());
    pRenderContext->clearTexture(renderData.getTexture(kInputBufferHistoryWeight).get());
    pRenderContext->clearTexture(renderData.getTexture(kInputBufferShortHistoryWeight).get());
    pRenderContext->clearTexture(renderData.getTexture(kInputBufferLongHistoryWeight).get());
}

// Extracts linear z and its derivative from the linear Z texture and packs
// the normal from the world normal texture and packes them into the FBO.
// (It's slightly wasteful to copy linear z here, but having this all
// together in a single buffer is a small simplification, since we make a
// copy of it to refer to in the next frame.)
void TwoHistorySVGFPass::computeLinearZAndNormal(RenderContext* pRenderContext, Texture::SharedPtr pLinearZTexture,
    Texture::SharedPtr pWorldNormalTexture)
{
    auto perImageCB = mpPackLinearZAndNormal["PerImageCB"];
    perImageCB["gLinearZ"] = pLinearZTexture;
    perImageCB["gNormal"] = pWorldNormalTexture;

    mpPackLinearZAndNormal->execute(pRenderContext, mpLinearZAndNormalFbo);
}

void TwoHistorySVGFPass::computeReprojection(RenderContext* pRenderContext, Texture::SharedPtr pAlbedoTexture,
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
    perImageCB["gPrevShortHistoryWeight"] = mpPrevReprojFbo->getColorTexture(ReprojectOutFields::ShortHistoryWeight);
    perImageCB["gPrevLongHistoryWeight"] = mpPrevReprojFbo->getColorTexture(ReprojectOutFields::LongHistoryWeight);
    perImageCB["gPrevShortIllum"] = mpFilteredPastFbo[1]->getColorTexture(0);
    perImageCB["gPrevLongIllum"] = mpFilteredPastFbo[2]->getColorTexture(0);

    // Setup variables for our reprojection pass
    perImageCB["gAlpha"] = mAlpha;
    perImageCB["gMomentsAlpha"] = mMomentsAlpha;
    perImageCB["gMaxHistoryWeight"] = mMaxHistoryWeight;
    perImageCB["gShortHistoryMaxWeight"] = 16.0f;
    perImageCB["gLongHistoryMaxWeight"] = 32.0f;

    mpReprojection->execute(pRenderContext, mpCurReprojFbo);
}

void TwoHistorySVGFPass::computeFilteredMoments(RenderContext* pRenderContext)
{
    auto perImageCB = mpFilterMoments["PerImageCB"];

    perImageCB["gIllumination"] = mpCurReprojFbo->getColorTexture(ReprojectOutFields::Illumination);
    perImageCB["gHistoryLength"] = mpCurReprojFbo->getColorTexture(ReprojectOutFields::HistoryWeight);
    perImageCB["gLinearZAndNormal"] = mpLinearZAndNormalFbo->getColorTexture(0);
    perImageCB["gMoments"] = mpCurReprojFbo->getColorTexture(ReprojectOutFields::Moments);

    perImageCB["gPhiColor"] = mPhiColor;
    perImageCB["gPhiNormal"] = mPhiNormal;

    mpFilterMoments->execute(pRenderContext, mpPingPongFbo[0]);


    // Short History
    perImageCB["gIllumination"] = mpCurReprojFbo->getColorTexture(ReprojectOutFields::ShortHistoryIllumination);
    mpFilterMoments->execute(pRenderContext, mpPingPongFbo[2]);

    // Long History
    perImageCB["gIllumination"] = mpCurReprojFbo->getColorTexture(ReprojectOutFields::LongHistoryIllumination);
    mpFilterMoments->execute(pRenderContext, mpPingPongFbo[4]);
}

void TwoHistorySVGFPass::computeAtrousDecomposition(RenderContext* pRenderContext, Texture::SharedPtr pAlbedoTexture)
{
    auto perImageCB = mpAtrous["PerImageCB"];

    perImageCB["gAlbedo"] = pAlbedoTexture;
    perImageCB["gHistoryLength"] = mpCurReprojFbo->getColorTexture(ReprojectOutFields::HistoryWeight);
    perImageCB["gLinearZAndNormal"] = mpLinearZAndNormalFbo->getColorTexture(0);

    perImageCB["gPhiColor"] = mPhiColor;
    perImageCB["gPhiNormal"] = mPhiNormal;

    for (int i = 0; i < mFilterIterations; i++)
    {
        perImageCB["gStepSize"] = 1 << i;

        for (int srcId = 0; srcId < 6; srcId+=2)
        {
            const int targetId = srcId + 1;
            Fbo::SharedPtr curTargetFbo = mpPingPongFbo[targetId];
            perImageCB["gIllumination"] = mpPingPongFbo[srcId]->getColorTexture(0);
            mpAtrous->execute(pRenderContext, curTargetFbo);

            // store the filtered color for the feedback path
            if (i == std::min(mFeedbackTap, mFilterIterations - 1))
            {
                pRenderContext->blit(curTargetFbo->getColorTexture(0)->getSRV(), mpFilteredPastFbo[srcId/2]->getRenderTargetView(0));
            }

            std::swap(mpPingPongFbo[srcId], mpPingPongFbo[targetId]);
        }
    }

    if (mFeedbackTap < 0)
    {
        pRenderContext->blit(mpCurReprojFbo->getColorTexture(ReprojectOutFields::Illumination)->getSRV(), mpFilteredPastFbo[0]->getRenderTargetView(0));
        pRenderContext->blit(mpCurReprojFbo->getColorTexture(ReprojectOutFields::ShortHistoryIllumination)->getSRV(), mpFilteredPastFbo[1]->getRenderTargetView(0));
        pRenderContext->blit(mpCurReprojFbo->getColorTexture(ReprojectOutFields::LongHistoryIllumination)->getSRV(), mpFilteredPastFbo[2]->getRenderTargetView(0));
    }
}

void TwoHistorySVGFPass::renderUI(Gui::Widgets& widget)
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
    dirty |= (int)widget.var("Alpha", mAlpha, 0.0f, 1.0f, 0.001f);
    dirty |= (int)widget.var("Moments Alpha", mMomentsAlpha, 0.0f, 1.0f, 0.001f);
    dirty |= (int)widget.var("Max History Weight", mMaxHistoryWeight, 0.0f, 128.0f, 0.1f);

    if (dirty) mBuffersNeedClear = true;
}
