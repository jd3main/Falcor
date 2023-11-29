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
    const char kTemporalFilterShader[] = "RenderPasses/DynamicWeightingSVGF/TemporalFilter.ps.slang";
    const char kAtrousShader[] = "RenderPasses/SVGFPass/SVGFAtrous.ps.slang";
    const char kFilterMomentShader[] = "RenderPasses/SVGFPass/SVGFFilterMoments.ps.slang";
    const char kReprojectShader[] = "RenderPasses/DynamicWeightingSVGF/Reprojection.ps.slang";
    const char kDynamicWeightingShader[] = "RenderPasses/DynamicWeightingSVGF/DynamicWeighting.ps.slang";
    const char kFinalModulateShader[] = "RenderPasses/SVGFPass/SVGFFinalModulate.ps.slang";
    const char kReflectTypesShader[] = "RenderPasses/DynamicWeightingSVGF/ReflectTypes.cs.slang";

    // Names of valid entries in the parameter dictionary.
    const char kEnabled[] = "Enabled";
    const char kDynamicWeighingEnabled[] = "DynamicWeighingEnabled";
    const char kIterations[] = "Iterations";
    const char kFeedbackTap[] = "FeedbackTap";
    const char kGradientFilterIterations[] = "GradientFilterIterations";
    const char kVarianceEpsilon[] = "VarianceEpsilon";
    const char kPhiColor[] = "PhiColor";
    const char kPhiNormal[] = "PhiNormal";
    const char kAlpha[] = "Alpha";
    const char kMomentsAlpha[] = "MomentsAlpha";
    const char kGradientAlpha[] = "GradientAlpha";
    const char kGradientMidpoint[] = "GradientMidpoint";
    const char kGammaSteepness[] = "GammaSteepness";
    const char kSelectionMode[] = "SelectionMode";
    const char kSampleCountOverride[] = "SampleCountOverride";

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
    // const char kInternalBufferPreviousUnweightedHistoryWeight[] = "Previous Weight (Unweighted)";
    // const char kInternalBufferPreviousWeightedHistoryWeight[] = "Previous Weight (Weighted)";
    const char kInternalBufferPreviousGradient[] = "Previous Gradient";
    const char kInternalBufferGradient[] = "Gradient";
    const char kInternalBufferGamma[] = "Gamma";
    const char kInternalBufferVariance[] = "Variance";
    const char kInternalBufferPreviousUnweightedIllumination[] = "PrevUnweightedIllumination";
    const char kInternalBufferPreviousWeightedIllumination[] = "PrevWeightedIllumination";

    // Output buffer name
    const char kOutputBufferFilteredImage[] = "Filtered image";
    const char kOutputHistoryLength[] = "HistLength";
    const char kOutputUnweightedHistoryWeight[] = "Weight_U";
    const char kOutputWeightedHistoryWeight[] = "Weight_W";
    const char kOutputUnweightedHistoryIllumination[] = "Illumination_U";
    const char kOutputWeightedHistoryIllumination[] = "Illumination_W";
    const char kOutputSampleCount[] = "SampleCount";
    const char kOutputGradient[] = "OutGradient";
    const char kOutputGamma[] = "OutGamma";
    const char kOutputUnweightedAlpha[] = "UnweightedAlpha";
    const char kOutputWeightedAlpha[] = "WeightedAlpha";

    enum TemporalFilterOutFields
    {
        UnweightedHistoryIllumination,
        WeightedHistoryIllumination,
        Moments,
        HistoryLength,
        UnweightedHistoryWeight,
        WeightedHistoryWeight
    };

    Gui::DropdownList kSelectionModeList = {
        #define X(x) { (uint32_t)SelectionMode::x, #x },
        FOR_SELECTION_MODES(X)
        #undef X
    };

    static const uint2 kScreenTileDim = { 16, 16 };     ///< Screen-tile dimension in pixels.
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
        else if (key == kDynamicWeighingEnabled) mDynamicWeighingEnabled = value;
        else if (key == kIterations) mFilterIterations = value;
        else if (key == kFeedbackTap) mFeedbackTap = value;
        else if (key == kGradientFilterIterations) mGradientFilterIterations = value;
        else if (key == kVarianceEpsilon) mVarainceEpsilon = value;
        else if (key == kPhiColor) mPhiColor = value;
        else if (key == kPhiNormal) mPhiNormal = value;
        else if (key == kAlpha) mAlpha = value;
        else if (key == kMomentsAlpha) mMomentsAlpha = value;
        else if (key == kGradientAlpha) mGradientAlpha = value;
        else if (key == kGradientMidpoint) mGammaMidpoint = value;
        else if (key == kGammaSteepness) mGammaSteepness = value;
        else if (key == kSelectionMode) mSelectionMode = value;
        else if (key == kSampleCountOverride) mSampleCountOverride = value;
        else logWarning("Unknown field '{}' in DynamicWeightingSVGF dictionary.", key);
    }

    mpPackLinearZAndNormal = FullScreenPass::create(kPackLinearZAndNormalShader);
    mpTemporalFilter = FullScreenPass::create(kTemporalFilterShader);
    mpAtrous = FullScreenPass::create(kAtrousShader);
    mpReproject = FullScreenPass::create(kReprojectShader);
    mpDynamicWeighting = FullScreenPass::create(kDynamicWeightingShader);
    mpFilterMoments = FullScreenPass::create(kFilterMomentShader);

    mpReflectTypes = ComputePass::create(kReflectTypesShader);

    mpFinalModulate = FullScreenPass::create(kFinalModulateShader);
    FALCOR_ASSERT(mpPackLinearZAndNormal && mpTemporalFilter && mpAtrous && mpFilterMoments && mpFinalModulate);
}

Dictionary DynamicWeightingSVGF::getScriptingDictionary()
{
    Dictionary dict;
    dict[kEnabled] = mFilterEnabled;
    dict[kDynamicWeighingEnabled] = mDynamicWeighingEnabled;
    dict[kIterations] = mFilterIterations;
    dict[kFeedbackTap] = mFeedbackTap;
    dict[kGradientFilterIterations] = mGradientFilterIterations;
    dict[kVarianceEpsilon] = mVarainceEpsilon;
    dict[kPhiColor] = mPhiColor;
    dict[kPhiNormal] = mPhiNormal;
    dict[kAlpha] = mAlpha;
    dict[kMomentsAlpha] = mMomentsAlpha;
    dict[kGradientAlpha] = mGradientAlpha;
    dict[kGradientMidpoint] = mGammaMidpoint;
    dict[kGammaSteepness] = mGammaSteepness;
    dict[kSelectionMode] = mSelectionMode;
    dict[kSampleCountOverride] = mSampleCountOverride;
    return dict;
}

/*
// TODO: update comments
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

    // reflector.addInternal(kInternalBufferPreviousUnweightedHistoryWeight, "Previous weight of unweighted history");
    // reflector.addInternal(kInternalBufferPreviousWeightedHistoryWeight, "Previous weight of weighted history");
    reflector.addInternal(kInternalBufferPreviousGradient, "Previous gradient")
        .format(ResourceFormat::RGBA32Float)
        .bindFlags(Resource::BindFlags::RenderTarget | Resource::BindFlags::ShaderResource | Resource::BindFlags::UnorderedAccess);
    reflector.addInternal(kInternalBufferGradient, "Gradient")
        .format(ResourceFormat::RGBA32Float)
        .bindFlags(Resource::BindFlags::RenderTarget | Resource::BindFlags::ShaderResource | Resource::BindFlags::UnorderedAccess);
    reflector.addInternal(kInternalBufferGamma, "Gamma")
        .format(ResourceFormat::RGBA32Float)
        .bindFlags(Resource::BindFlags::RenderTarget | Resource::BindFlags::ShaderResource | Resource::BindFlags::UnorderedAccess);
    reflector.addInternal(kInternalBufferVariance, "Variance")
        .format(ResourceFormat::R32Float)
        .bindFlags(Resource::BindFlags::RenderTarget | Resource::BindFlags::ShaderResource | Resource::BindFlags::UnorderedAccess);
    reflector.addInternal(kInternalBufferPreviousUnweightedIllumination, "Previous Unweighted Illumination")
        .format(ResourceFormat::RGBA32Float)
        .bindFlags(Resource::BindFlags::RenderTarget | Resource::BindFlags::ShaderResource | Resource::BindFlags::UnorderedAccess);
    reflector.addInternal(kInternalBufferPreviousWeightedIllumination, "Previous Weighted Illumination")
        .format(ResourceFormat::RGBA32Float)
        .bindFlags(Resource::BindFlags::RenderTarget | Resource::BindFlags::ShaderResource | Resource::BindFlags::UnorderedAccess);

    reflector.addOutput(kOutputBufferFilteredImage, "Filtered image").format(ResourceFormat::RGBA16Float);
    reflector.addOutput(kOutputHistoryLength, "History Sample Length").format(ResourceFormat::R32Float);
    reflector.addOutput(kOutputUnweightedHistoryWeight, "Weight of unweighted history").format(ResourceFormat::R32Float);
    reflector.addOutput(kOutputWeightedHistoryWeight, "Weight of long history").format(ResourceFormat::R32Float);
    reflector.addOutput(kOutputUnweightedHistoryIllumination, "Unweighted History Illumination").format(ResourceFormat::RGBA16Float);
    reflector.addOutput(kOutputWeightedHistoryIllumination, "Weighted History Illumination").format(ResourceFormat::RGBA16Float);
    reflector.addOutput(kOutputSampleCount, "Sample Count").format(ResourceFormat::R8Uint);

    reflector.addOutput(kOutputGradient, "Gradient").format(ResourceFormat::RGBA32Float);
    reflector.addOutput(kOutputGamma, "Gamma").format(ResourceFormat::RGBA32Float);
    reflector.addOutput(kOutputUnweightedAlpha, "Unweighted Alpha").format(ResourceFormat::R32Float);
    reflector.addOutput(kOutputWeightedAlpha, "Weighted Alpha").format(ResourceFormat::R32Float);

    return reflector;
}

void DynamicWeightingSVGF::compile(RenderContext* pRenderContext, const CompileData& compileData)
{
    mFrameDim = compileData.defaultTexDims;
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
    Texture::SharedPtr pOutputSampleCount = renderData.getTexture(kOutputSampleCount);
    Texture::SharedPtr pOutputGradient = renderData.getTexture(kOutputGradient);
    Texture::SharedPtr pOutputGamma = renderData.getTexture(kOutputGamma);

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
        computeTemporalFilter(pRenderContext, renderData,
            pAlbedoTexture,
            pColorTexture,
            pSampleCountTexture,
            pEmissionTexture,
            pMotionVectorTexture,
            pPosNormalFwidthTexture);

        computeReprojection(pRenderContext, pColorTexture, pLinearZTexture, pMotionVectorTexture, pPosNormalFwidthTexture);

        // Do a first cross-bilateral filtering of the illumination and
        // estimate its variance, storing the result into a float4 in
        // mpPingPongFbo[0].  Takes mpCurReprojFbo as input.
        computeFilteredMoments(pRenderContext);

        pRenderContext->blit(mpPingPongFbo[0]->getColorTexture(0)->getSRV(), pOutputUnweightedHistoryIllumination->getRTV());
        pRenderContext->blit(mpPingPongFbo[2]->getColorTexture(0)->getSRV(), pOutputWeightedHistoryIllumination->getRTV());

        // Filter illumination from mpCurReprojFbo[0], storing the result
        // in mpPingPongFbo[0].  Along the way (or at the end, depending on
        // the value of mFeedbackTap), save the filtered illumination for
        // next time into mpFilteredPastFbo.
        computeAtrousDecomposition(pRenderContext, renderData, pAlbedoTexture);


        // Compute albedo * filtered illumination and add emission back in.
        // Read from mpPingPongFbo and write to mpFinalFbo.
        computeFinalModulate(pRenderContext, pAlbedoTexture, pEmissionTexture);

        // Blit into the output texture.
        pRenderContext->blit(mpFinalFbo->getColorTexture(0)->getSRV(), pOutputTexture->getRTV());
        pRenderContext->blit(mpPrevTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::HistoryLength)->getSRV(), pOutputHistoryLength->getRTV());
        pRenderContext->blit(mpPrevTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::UnweightedHistoryWeight)->getSRV(), pOutputUnweightedHistoryWeight->getRTV());
        pRenderContext->blit(mpPrevTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::WeightedHistoryWeight)->getSRV(), pOutputWeightedHistoryWeight->getRTV());
        pRenderContext->blit(pSampleCountTexture->getSRV(), pOutputSampleCount->getRTV());
        pRenderContext->blit(mpGradientTexture->getSRV(), pOutputGradient->getRTV());
        pRenderContext->blit(mpGammaTexture->getSRV(), pOutputGamma->getRTV());

        // Swap resources so we're ready for next frame.
        std::swap(mpCurTemporalFilterFbo, mpPrevTemporalFilterFbo);
        pRenderContext->blit(mpLinearZAndNormalFbo->getColorTexture(0)->getSRV(), mpPrevLinearZAndNormalTexture->getRTV());
        pRenderContext->blit(mpGradientTexture->getSRV(), mpPrevGradientTexture->getRTV());
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
        desc.setColorTarget(TemporalFilterOutFields::UnweightedHistoryIllumination, Falcor::ResourceFormat::RGBA32Float);
        desc.setColorTarget(TemporalFilterOutFields::WeightedHistoryIllumination, Falcor::ResourceFormat::RGBA32Float);
        desc.setColorTarget(TemporalFilterOutFields::Moments, Falcor::ResourceFormat::RG32Float);
        desc.setColorTarget(TemporalFilterOutFields::HistoryLength, Falcor::ResourceFormat::R32Float);
        desc.setColorTarget(TemporalFilterOutFields::UnweightedHistoryWeight, Falcor::ResourceFormat::R32Float);
        desc.setColorTarget(TemporalFilterOutFields::WeightedHistoryWeight, Falcor::ResourceFormat::R32Float);
        mpCurTemporalFilterFbo = Fbo::create2D(dim.x, dim.y, desc);
        mpPrevTemporalFilterFbo = Fbo::create2D(dim.x, dim.y, desc);
    }

    {
        // Screen-size RGBA32F buffer for linear Z, derivative, and packed normal
        Fbo::Desc desc;
        desc.setColorTarget(0, Falcor::ResourceFormat::RGBA32Float);
        mpLinearZAndNormalFbo = Fbo::create2D(dim.x, dim.y, desc);
    }

    {
        mpReprojectionFbo = Fbo::create2D(dim.x, dim.y, Falcor::ResourceFormat::RGBA32Float);

        const uint32_t sampleCount = dim.x * dim.y;
        auto var = mpReflectTypes->getRootVar();
        mpReprojectionBuffer = Buffer::createStructured(var["reprojection"], sampleCount,
            Resource::BindFlags::ShaderResource | Resource::BindFlags::UnorderedAccess,
            Buffer::CpuAccess::None,
            nullptr, false);
    }

    {
        // Screen-size FBOs with 1 RGBA32F buffer
        Fbo::Desc desc;
        desc.setColorTarget(0, Falcor::ResourceFormat::RGBA32Float);
        for (int i=0; i<4; i++)
        {
            mpPingPongFbo[i] = Fbo::create2D(dim.x, dim.y, desc);
        }
        for (int i=0; i<2; i++)
        {
            mpFilteredPastFbo[i] = Fbo::create2D(dim.x, dim.y, desc);
        }
        mpFinalFbo = Fbo::create2D(dim.x, dim.y, desc);
        mpDynamicWeightingFbo = Fbo::create2D(dim.x, dim.y, desc);
    }

    mBuffersNeedClear = true;
}

void DynamicWeightingSVGF::clearBuffers(RenderContext* pRenderContext, const RenderData& renderData)
{
    for (int i=0; i<4; i++)
        pRenderContext->clearFbo(mpPingPongFbo[i].get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpLinearZAndNormalFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    for (int i=0; i<2; i++)
        pRenderContext->clearFbo(mpFilteredPastFbo[i].get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpCurTemporalFilterFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpPrevTemporalFilterFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpDynamicWeightingFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpFinalFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);

    pRenderContext->clearTexture(renderData.getTexture(kInternalBufferPreviousLinearZAndNormal).get());
    // pRenderContext->clearTexture(renderData.getTexture(kInternalBufferPreviousUnweightedHistoryWeight).get());
    // pRenderContext->clearTexture(renderData.getTexture(kInternalBufferPreviousWeightedHistoryWeight).get());
    pRenderContext->clearTexture(renderData.getTexture(kInternalBufferPreviousGradient).get());
    pRenderContext->clearTexture(renderData.getTexture(kInternalBufferGradient).get());
    pRenderContext->clearTexture(renderData.getTexture(kInternalBufferGamma).get());
    pRenderContext->clearTexture(renderData.getTexture(kInternalBufferVariance).get());
    pRenderContext->clearTexture(renderData.getTexture(kInternalBufferPreviousUnweightedIllumination).get());
    pRenderContext->clearTexture(renderData.getTexture(kInternalBufferPreviousWeightedIllumination).get());
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

void DynamicWeightingSVGF::computeReprojection(RenderContext* pRendercontext,
    Texture::SharedPtr pColorTexture,
    Texture::SharedPtr pLinearZTexture,
    Texture::SharedPtr pMotionoTexture,
    Texture::SharedPtr pPositionNormalFwidthTexture)
{
    auto perImageCB = mpReproject["PerImageCB"];
    perImageCB["gMotion"] = pMotionoTexture;
    perImageCB["gColor"] = pColorTexture;
    perImageCB["gPositionNormalFwidth"] = pPositionNormalFwidthTexture;
    perImageCB["gLinearZAndNormal"] = mpLinearZAndNormalFbo->getColorTexture(0);
    perImageCB["gPrevLinearZAndNormal"] = mpPrevLinearZAndNormalTexture;
    perImageCB["gReprojection"] = mpReprojectionBuffer;
    mpReproject->execute(pRendercontext, mpReprojectionFbo);
}

void DynamicWeightingSVGF::computeTemporalFilter(RenderContext* pRenderContext,
    const RenderData& renderData,
    Texture::SharedPtr pAlbedoTexture,
    Texture::SharedPtr pColorTexture,
    Texture::SharedPtr pSampleCountTexture,
    Texture::SharedPtr pEmissionTexture,
    Texture::SharedPtr pMotionVectorTexture,
    Texture::SharedPtr pPositionNormalFwidthTexture)
{
    mpPrevLinearZAndNormalTexture = renderData.getTexture(kInternalBufferPreviousLinearZAndNormal);
    mpPrevGradientTexture = renderData.getTexture(kInternalBufferPreviousGradient);
    mpGradientTexture = renderData.getTexture(kInternalBufferGradient);
    mpVarianceTexture = renderData.getTexture(kInternalBufferVariance);

    Texture::SharedPtr pUnweightedAlpha = renderData.getTexture(kOutputUnweightedAlpha);
    Texture::SharedPtr pWeightedAlpha = renderData.getTexture(kOutputWeightedAlpha);

    auto perImageCB = mpTemporalFilter["PerImageCB"];

    // Setup textures for our reprojection shader pass
    perImageCB["gMotion"] = pMotionVectorTexture;
    perImageCB["gColor"] = pColorTexture;
    perImageCB["gEmission"] = pEmissionTexture;
    perImageCB["gAlbedo"] = pAlbedoTexture;
    perImageCB["gPositionNormalFwidth"] = pPositionNormalFwidthTexture;
    perImageCB["gPrevMoments"] = mpPrevTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::Moments);
    perImageCB["gLinearZAndNormal"] = mpLinearZAndNormalFbo->getColorTexture(0);
    perImageCB["gPrevLinearZAndNormal"] = mpPrevLinearZAndNormalTexture;
    perImageCB["gPrevHistoryLength"] = mpPrevTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::HistoryLength);
    perImageCB["gSampleCount"] = pSampleCountTexture;
    perImageCB["gPrevUnweightedHistoryWeight"] = mpPrevTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::UnweightedHistoryWeight);
    perImageCB["gPrevWeightedHistoryWeight"] = mpPrevTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::WeightedHistoryWeight);
    perImageCB["gPrevUnweightedIllum"] = mpFilteredPastFbo[0]->getColorTexture(0);
    perImageCB["gPrevWeightedIllum"] = mpFilteredPastFbo[1]->getColorTexture(0);
    perImageCB["gVariance"] = mpVarianceTexture;
    perImageCB["gSampleCountOverride"] = mSampleCountOverride;
    perImageCB["gUnweightedAlpha"] = pUnweightedAlpha;
    perImageCB["gWeightedAlpha"] = pWeightedAlpha;

    // Setup variables for our reprojection pass
    perImageCB["gAlpha"] = mAlpha;
    perImageCB["gMomentsAlpha"] = mMomentsAlpha;

    mpTemporalFilter->execute(pRenderContext, mpCurTemporalFilterFbo);
}

void DynamicWeightingSVGF::computeFilteredMoments(RenderContext* pRenderContext)
{
    auto perImageCB = mpFilterMoments["PerImageCB"];

    perImageCB["gLinearZAndNormal"] = mpLinearZAndNormalFbo->getColorTexture(0);
    perImageCB["gMoments"] = mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::Moments);

    perImageCB["gPhiColor"] = mPhiColor;
    perImageCB["gPhiNormal"] = mPhiNormal;

    // Unweighted History
    perImageCB["gHistoryLength"] = mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::UnweightedHistoryWeight);
    perImageCB["gIllumination"] = mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::UnweightedHistoryIllumination);
    mpFilterMoments->execute(pRenderContext, mpPingPongFbo[0]);

    // Weighted History
    perImageCB["gHistoryLength"] = mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::WeightedHistoryWeight);
    perImageCB["gIllumination"] = mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::WeightedHistoryIllumination);
    mpFilterMoments->execute(pRenderContext, mpPingPongFbo[2]);
}

void DynamicWeightingSVGF::computeAtrousDecomposition(RenderContext* pRenderContext, const RenderData& renderData, Texture::SharedPtr pAlbedoTexture)
{
    auto perImageCB = mpAtrous["PerImageCB"];

    perImageCB["gAlbedo"] = pAlbedoTexture;
    perImageCB["gLinearZAndNormal"] = mpLinearZAndNormalFbo->getColorTexture(0);

    perImageCB["gPhiColor"] = mPhiColor;
    perImageCB["gPhiNormal"] = mPhiNormal;

    int weightTextureIds[] = {
        TemporalFilterOutFields::UnweightedHistoryWeight,
        TemporalFilterOutFields::WeightedHistoryWeight,
    };

    for (int i = 0; i < mFilterIterations; i++)
    {
        for (int srcId = 0; srcId < 4; srcId += 2)
        {
            int dstId = srcId + 1;
            perImageCB["gHistoryLength"] = mpCurTemporalFilterFbo->getColorTexture(weightTextureIds[srcId/2]);
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
        pRenderContext->blit(mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::UnweightedHistoryIllumination)->getSRV(), mpFilteredPastFbo[0]->getRenderTargetView(0));
        pRenderContext->blit(mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::WeightedHistoryIllumination)->getSRV(), mpFilteredPastFbo[1]->getRenderTargetView(0));
    }

    mpGammaTexture = renderData.getTexture(kInternalBufferGamma);
    mpGradientTexture = renderData.getTexture(kInternalBufferGradient);
    mpPrevUnweightedIllumination = renderData.getTexture(kInternalBufferPreviousUnweightedIllumination);
    mpPrevWeightedIllumination = renderData.getTexture(kInternalBufferPreviousWeightedIllumination);

    if (mDynamicWeighingEnabled)
    {
        mpDynamicWeighting["PerImageCB"]["gPrevUnweightedIllumination"] = mpPrevUnweightedIllumination;
        mpDynamicWeighting["PerImageCB"]["gPrevWeightedIllumination"] = mpPrevWeightedIllumination;
        mpDynamicWeighting["PerImageCB"]["gUnweightedIllumination"] = mpPingPongFbo[0]->getColorTexture(0);
        mpDynamicWeighting["PerImageCB"]["gWeightedIllumination"] = mpPingPongFbo[2]->getColorTexture(0);
        mpDynamicWeighting["PerImageCB"]["gPrevGradient"] = mpPrevGradientTexture;
        mpDynamicWeighting["PerImageCB"]["gVariance"] = mpVarianceTexture;
        mpDynamicWeighting["PerImageCB"]["gReprojection"] = mpReprojectionBuffer;
        mpDynamicWeighting["PerImageCB"]["gGradient"] = mpGradientTexture;
        mpDynamicWeighting["PerImageCB"]["gOutGamma"] = mpGammaTexture;
        mpDynamicWeighting["PerImageCB"]["gGradientAlpha"] = mGradientAlpha;
        mpDynamicWeighting["PerImageCB"]["gGammaSteepness"] = mGammaSteepness;
        mpDynamicWeighting["PerImageCB"]["gGammaMidpoint"] = mGammaMidpoint;
        mpDynamicWeighting["PerImageCB"]["gSelectionMode"] = mSelectionMode;
        mpDynamicWeighting->execute(pRenderContext, mpDynamicWeightingFbo);

        pRenderContext->blit(mpPingPongFbo[0]->getColorTexture(0)->getSRV(), mpPrevUnweightedIllumination->getRTV());
        pRenderContext->blit(mpPingPongFbo[2]->getColorTexture(0)->getSRV(), mpPrevWeightedIllumination->getRTV());

        pRenderContext->blit(mpDynamicWeightingFbo->getColorTexture(0)->getSRV(), mpPingPongFbo[0]->getColorTexture(0)->getRTV());
    }
}

void DynamicWeightingSVGF::computeFinalModulate(RenderContext* pRenderContext, Texture::SharedPtr pAlbedoTexture, Texture::SharedPtr pEmissionTexture)
{
    auto perImageCB = mpFinalModulate["PerImageCB"];
    perImageCB["gAlbedo"] = pAlbedoTexture;
    perImageCB["gEmission"] = pEmissionTexture;
    perImageCB["gIllumination"] = mpPingPongFbo[0]->getColorTexture(0);
    mpFinalModulate->execute(pRenderContext, mpFinalFbo);
}

void DynamicWeightingSVGF::renderUI(Gui::Widgets& widget)
{
    int dirty = 0;
    dirty |= (int)widget.checkbox("Enable SVGF", mFilterEnabled);

    widget.text("");
    widget.text("Number of filter iterations.  Which");
    widget.text("    iteration feeds into future frames?");
    dirty |= (int)widget.var("Iterations", mFilterIterations, 0, 10, 1);
    dirty |= (int)widget.var("Feedback", mFeedbackTap, -1, mFilterIterations - 1, 1);
    // dirty |= (int)widget.var("Gradient Filter Iterations", mGradientFilterIterations, 0, mFilterIterations, 1);

    widget.text("");
    widget.text("Contol edge stopping on bilateral fitler");
    dirty |= (int)widget.var("For Color", mPhiColor, 0.0f, 10000.0f, 0.01f);
    dirty |= (int)widget.var("For Normal", mPhiNormal, 0.001f, 1000.0f, 0.2f);

    widget.text("");
    widget.text("How much history should be used?");
    widget.text("    (alpha; 0 = full reuse; 1 = no reuse)");
    dirty |= (int)widget.var("Alpha", mAlpha, 0.0f, 1.0f, 0.001f);
    dirty |= (int)widget.var("Moments Alpha", mMomentsAlpha, 0.0f, 1.0f, 0.001f);

    widget.text("");
    widget.text("Dynamic Weighting");
    dirty |= (int)widget.checkbox("Enable Dynamic Weighting", mDynamicWeighingEnabled);
    if (mDynamicWeighingEnabled)
    {
        dirty |= (int)widget.dropdown("Selection Mode", kSelectionModeList, mSelectionMode);
        dirty |= (int)widget.var("Gradient Alpha", mGradientAlpha, 0.0f, 1.0f, 0.001f);
        dirty |= (int)widget.var("Gamma Midpoint", mGammaMidpoint, -1e6f, 1e6f, 0.1f);
        dirty |= (int)widget.var("Gamma Steepness", mGammaSteepness, 0.0f, 1e6f, 0.1f);

        if (mSelectionMode == SelectionMode::Logistic)
        {
            float gamma0 = 1.0f / (1.0f + expf(-mGammaSteepness * (0 - mGammaMidpoint)));
            widget.text("gamma(0) = " + std::to_string(gamma0));
        }
    }

    widget.text("");
    widget.text("Debug");
    mBuffersNeedClear |= (int)widget.button("Clear History");
    dirty |= (int)widget.var("Sample Count Override", mSampleCountOverride, -1, 16, 1);

    if (dirty) mBuffersNeedClear = true;
}
