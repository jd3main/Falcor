#include "DynamicWeightingSVGF.h"

#include "RenderGraph/RenderPassLibrary.h"
#include "RenderGraph/RenderPassHelpers.h"
#include "RenderGraph/BasePasses/FullScreenPass.h"

using std::string;
using std::vector;
using std::cerr;
using std::endl;

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
    const char kSelectAfterIterations[] = "GradientFilterIterations";
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
    const char kNormalizationMode[] = "NormalizationMode";

    // Input buffers
    const char kInputBufferAlbedo[] = "Albedo";
    const char kInputBufferColor[] = "Color";
    const char kInputBufferSampleCount[] = "SampleCount";
    const char kInputBufferEmission[] = "Emission";
    const char kInputBufferWorldPosition[] = "WorldPosition";
    const char kInputBufferWorldNormal[] = "WorldNormal";
    const char kInputBufferPosNormalFwidth[] = "PositionNormalFwidth";
    const char kInputBufferLinearZ[] = "LinearZ";
    const char kInputBufferMotionVector[] = "MotionVec";
    const ChannelList kInputChannels =
    {
        { kInputBufferAlbedo,           "_",   "Albedo",          false, ResourceFormat::Unknown},
        { kInputBufferColor,            "_",   "Color",           false, ResourceFormat::Unknown},
        { kInputBufferSampleCount,      "_",   "Sample Count",    true,  ResourceFormat::R8Uint},
        { kInputBufferEmission,         "_",   "Emission",        false, ResourceFormat::Unknown},
        { kInputBufferWorldPosition,    "_",   "World Position",  false, ResourceFormat::Unknown},
        { kInputBufferWorldNormal,      "_",   "World Normal",    false, ResourceFormat::Unknown},
        { kInputBufferPosNormalFwidth,  "_",   "PosNormalFwidth", false, ResourceFormat::Unknown},
        { kInputBufferLinearZ,          "_",   "Linear Z",        false, ResourceFormat::Unknown},
        { kInputBufferMotionVector,     "_",   "Motion Vector",   false, ResourceFormat::Unknown},
    };


    // Internal buffers
    const char kInternalBufferPreviousLinearZAndNormal[] = "Previous Linear Z and Packed Normal";
    const char kInternalBufferPreviousGradient[] = "Previous Gradient";
    const char kInternalBufferVariance[] = "Variance";
    const char kInternalBufferPreviousUnweightedIllumination[] = "PrevUnweightedIllumination";
    const char kInternalBufferPreviousWeightedIllumination[] = "PrevWeightedIllumination";

    // Output buffers
    const char kOutputBufferFilteredImage[] = "Filtered image";
    const char kOutputHistoryLength[] = "HistLength";
    const char kOutputUnweightedHistoryWeight[] = "Weight_U";
    const char kOutputWeightedHistoryWeight[] = "Weight_W";
    const char kOutputUnweightedHistoryIllumination[] = "Illumination_U";
    const char kOutputWeightedHistoryIllumination[] = "Illumination_W";
    const char kOutputGradient[] = "OutGradient";
    const char kOutputGamma[] = "OutGamma";
    const ChannelList kOutputChannels =
    {
        /* { name, texname, description, optional, format } */
        { kOutputBufferFilteredImage,           "_",   "Filtered image",                  false,  ResourceFormat::RGBA16Float },
        { kOutputHistoryLength,                 "_",   "History Length",                  false,  ResourceFormat::R32Float },
        { kOutputUnweightedHistoryWeight,       "_",   "Unweighted History Weight",       false,  ResourceFormat::R32Float },
        { kOutputWeightedHistoryWeight,         "_",   "Weighted History Weight",         false,  ResourceFormat::R32Float },
        { kOutputUnweightedHistoryIllumination, "_",   "Unweightedly temporal filtered illumination",   false,  ResourceFormat::RGBA16Float },
        { kOutputWeightedHistoryIllumination,   "_",   "Weightedly tmeporal filtered illumination",     false,  ResourceFormat::RGBA16Float },
        { kOutputGradient,                      "_",   "Gradient",                        false,  ResourceFormat::RGBA32Float },
        { kOutputGamma,                         "_",   "Gamma",                           false,  ResourceFormat::RGBA32Float },
    };

    enum TemporalFilterOutFields
    {
        UnweightedHistoryIllumination,
        Moments,
        HistoryLength,
        UnweightedHistoryWeight,
        WeightedHistoryIllumination,
        WeightedHistoryWeight,
    };

    enum DynamicWeightingOutFields
    {
        Color,
        Gradient,
        Gamma,
    };

    Gui::DropdownList kSelectionModeList = {
        #define X(x) { (uint32_t)SelectionMode::x, #x },
        FOR_SELECTION_MODES(X)
        #undef X
    };

    Gui::DropdownList kNormalizationModeList = {
        #define X(x) { (uint32_t)NormalizationMode::x, #x },
        FOR_NORMALIZATION_MODES(X)
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
        else if (key == kSelectAfterIterations) mSelectAfterIterations = value;
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
        else if (key == kNormalizationMode) mNormalizationMode = value;
        else logWarning("Unknown field '{}' in DynamicWeightingSVGF dictionary.", key);
    }

    mpReflectTypes = ComputePass::create(kReflectTypesShader);
    FALCOR_ASSERT(mpReflectTypes);
}

Dictionary DynamicWeightingSVGF::getScriptingDictionary()
{
    Dictionary dict;
    dict[kEnabled] = mFilterEnabled;
    dict[kDynamicWeighingEnabled] = mDynamicWeighingEnabled;
    dict[kIterations] = mFilterIterations;
    dict[kFeedbackTap] = mFeedbackTap;
    dict[kSelectAfterIterations] = mSelectAfterIterations;
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
    dict[kNormalizationMode] = mNormalizationMode;
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

    addRenderPassInputs(reflector, kInputChannels);

    reflector.addInternal(kInternalBufferPreviousLinearZAndNormal, "Previous Linear Z and Packed Normal")
        .format(ResourceFormat::RGBA32Float)
        .bindFlags(Resource::BindFlags::RenderTarget | Resource::BindFlags::ShaderResource);

    reflector.addInternal(kInternalBufferPreviousGradient, "Previous gradient")
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

    addRenderPassOutputs(reflector, kOutputChannels, ResourceBindFlags::RenderTarget);

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
    Texture::SharedPtr pOutputGradient = renderData.getTexture(kOutputGradient);
    Texture::SharedPtr pOutputGamma = renderData.getTexture(kOutputGamma);



    if (!mpPackLinearZAndNormal || mRecompile)
    {
        mRecompile = false;
        mBuffersNeedClear = true;

        mpPackLinearZAndNormal = FullScreenPass::create(kPackLinearZAndNormalShader);
        {
            Program::DefineList defines;
            defines.add("_DW_ENABLED", mDynamicWeighingEnabled ? "1" : "0");
            mpTemporalFilter = FullScreenPass::create(kTemporalFilterShader, defines);
        }
        mpAtrous = FullScreenPass::create(kAtrousShader);
        mpReproject = FullScreenPass::create(kReprojectShader);
        mpDynamicWeighting = FullScreenPass::create(kDynamicWeightingShader);
        mpFilterMoments = FullScreenPass::create(kFilterMomentShader);
        mpFinalModulate = FullScreenPass::create(kFinalModulateShader);
    }
    FALCOR_ASSERT(mpPackLinearZAndNormal && mpTemporalFilter && mpAtrous && mpFilterMoments && mpFinalModulate);

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
        pRenderContext->blit(mpDynamicWeightingFbo->getColorTexture(DynamicWeightingOutFields::Gradient)->getSRV(), pOutputGradient->getRTV());
        pRenderContext->blit(mpDynamicWeightingFbo->getColorTexture(DynamicWeightingOutFields::Gamma)->getSRV(), pOutputGamma->getRTV());

        // Swap resources so we're ready for next frame.
        std::swap(mpCurTemporalFilterFbo, mpPrevTemporalFilterFbo);

        // Blit into internal buffers for next frame.
        pRenderContext->blit(mpLinearZAndNormalFbo->getColorTexture(0)->getSRV(), mpPrevLinearZAndNormalTexture->getRTV());
        pRenderContext->blit(mpDynamicWeightingFbo->getColorTexture(DynamicWeightingOutFields::Gradient)->getSRV(), mpPrevGradientTexture->getRTV());
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
    }

    {
        Fbo::Desc desc;
        desc.setColorTarget(DynamicWeightingOutFields::Color, Falcor::ResourceFormat::RGBA32Float);
        desc.setColorTarget(DynamicWeightingOutFields::Gamma, Falcor::ResourceFormat::RGBA32Float);
        desc.setColorTarget(DynamicWeightingOutFields::Gradient, Falcor::ResourceFormat::RGBA32Float);
        mpDynamicWeightingFbo = Fbo::create2D(dim.x, dim.y, desc);
    }

    mBuffersNeedClear = true;
}

void DynamicWeightingSVGF::clearBuffers(RenderContext* pRenderContext, const RenderData& renderData)
{
    // Clear the FBOs
    for (int i=0; i<4; i++)
        pRenderContext->clearFbo(mpPingPongFbo[i].get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpLinearZAndNormalFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    for (int i=0; i<2; i++)
        pRenderContext->clearFbo(mpFilteredPastFbo[i].get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpCurTemporalFilterFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpPrevTemporalFilterFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpDynamicWeightingFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpFinalFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);

    // Clear the internal buffers
    pRenderContext->clearTexture(renderData.getTexture(kInternalBufferPreviousLinearZAndNormal).get());
    pRenderContext->clearTexture(renderData.getTexture(kInternalBufferPreviousGradient).get());
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
    mpVarianceTexture = renderData.getTexture(kInternalBufferVariance);

    auto perImageCB = mpTemporalFilter["PerImageCB"];

    // Setup textures for our reprojection shader pass

    // From input channels
    perImageCB["gAlbedo"] = pAlbedoTexture;
    perImageCB["gColor"] = pColorTexture;
    perImageCB["gSampleCount"] = pSampleCountTexture;
    perImageCB["gEmission"] = pEmissionTexture;
    perImageCB["gMotion"] = pMotionVectorTexture;
    perImageCB["gPositionNormalFwidth"] = pPositionNormalFwidthTexture;

    // From computeLinearZAndNormal
    perImageCB["gLinearZAndNormal"] = mpLinearZAndNormalFbo->getColorTexture(0);

    // From previous frame
    perImageCB["gPrevMoments"] = mpPrevTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::Moments);
    perImageCB["gPrevLinearZAndNormal"] = mpPrevLinearZAndNormalTexture;
    perImageCB["gPrevHistoryLength"] = mpPrevTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::HistoryLength);
    perImageCB["gPrevUnweightedHistoryWeight"] = mpPrevTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::UnweightedHistoryWeight);
    perImageCB["gPrevWeightedHistoryWeight"] = mpPrevTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::WeightedHistoryWeight);
    perImageCB["gPrevUnweightedIllum"] = mpFilteredPastFbo[0]->getColorTexture(0);
    perImageCB["gPrevWeightedIllum"] = mpFilteredPastFbo[1]->getColorTexture(0);

    // Outputs
    perImageCB["gVariance"] = mpVarianceTexture;

    // Parameters
    perImageCB["gAlpha"] = mAlpha;
    perImageCB["gMomentsAlpha"] = mMomentsAlpha;
    perImageCB["gSampleCountOverride"] = mSampleCountOverride;

    mpTemporalFilter->execute(pRenderContext, mpCurTemporalFilterFbo);
}

void DynamicWeightingSVGF::computeFilteredMoments(RenderContext* pRenderContext)
{
    auto perImageCB = mpFilterMoments["PerImageCB"];

    perImageCB["gLinearZAndNormal"] = mpLinearZAndNormalFbo->getColorTexture(0);
    perImageCB["gMoments"] = mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::Moments);

    // Parameters
    perImageCB["gPhiColor"] = mPhiColor;
    perImageCB["gPhiNormal"] = mPhiNormal;

    // Filter unweighted history
    perImageCB["gHistoryLength"] = mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::UnweightedHistoryWeight);
    perImageCB["gIllumination"] = mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::UnweightedHistoryIllumination);
    mpFilterMoments->execute(pRenderContext, mpPingPongFbo[0]);

    // Filter weighted history
    perImageCB["gHistoryLength"] = mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::WeightedHistoryWeight);
    perImageCB["gIllumination"] = mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::WeightedHistoryIllumination);
    mpFilterMoments->execute(pRenderContext, mpPingPongFbo[2]);
}

void DynamicWeightingSVGF::computeAtrousDecomposition(RenderContext* pRenderContext, const RenderData& renderData, Texture::SharedPtr pAlbedoTexture)
{
    // cerr << "computeAtrousDecomposition()" << endl;
    mpPrevUnweightedIllumination = renderData.getTexture(kInternalBufferPreviousUnweightedIllumination);
    mpPrevWeightedIllumination = renderData.getTexture(kInternalBufferPreviousWeightedIllumination);

    auto perImageCB = mpAtrous["PerImageCB"];

    perImageCB["gAlbedo"] = pAlbedoTexture;
    perImageCB["gLinearZAndNormal"] = mpLinearZAndNormalFbo->getColorTexture(0);

    perImageCB["gPhiColor"] = mPhiColor;
    perImageCB["gPhiNormal"] = mPhiNormal;

    int weightTextureIds[] = {
        TemporalFilterOutFields::UnweightedHistoryWeight,
        TemporalFilterOutFields::WeightedHistoryWeight,
    };

    bool doneSelection = false;
    for (int i = 0; i < mFilterIterations; i++)
    {
        if (mDynamicWeighingEnabled && mSelectAfterIterations == i)
        {
            dynamicWeighting(pRenderContext,
                mpPingPongFbo[0]->getColorTexture(0),
                mpPingPongFbo[2]->getColorTexture(0));

            pRenderContext->blit(mpPingPongFbo[0]->getColorTexture(0)->getSRV(), mpPrevUnweightedIllumination->getRTV());
            pRenderContext->blit(mpPingPongFbo[2]->getColorTexture(0)->getSRV(), mpPrevWeightedIllumination->getRTV());

            pRenderContext->blit(mpDynamicWeightingFbo->getColorTexture(0)->getSRV(), mpPingPongFbo[0]->getColorTexture(0)->getRTV());

            doneSelection = true;
        }
        // If dynamic doneSelection has been done, we only need to filter the first pair of ping-pong buffers
        int nSrcIds = doneSelection ? 2 : 4;
        // int nSrcIds = 4;
        for (int srcId = 0; srcId < nSrcIds; srcId += 2)
        {
            // cerr << "i=" << i << ", " << "srcId=" << srcId << endl;
            int dstId = srcId + 1;
            perImageCB["gHistoryLength"] = mpCurTemporalFilterFbo->getColorTexture(weightTextureIds[srcId/2]);
            perImageCB["gStepSize"] = 1 << i;
            perImageCB["gIllumination"] = mpPingPongFbo[srcId]->getColorTexture(0);
            Fbo::SharedPtr curTargetFbo = mpPingPongFbo[dstId];
            mpAtrous->execute(pRenderContext, curTargetFbo);

            // store the filtered color for the feedback path
            if (i == std::min(mFeedbackTap, mFilterIterations - 1))
            {
                FALCOR_ASSERT(!doneSelection)
                pRenderContext->blit(curTargetFbo->getColorTexture(0)->getSRV(), mpFilteredPastFbo[srcId/2]->getRenderTargetView(0));
            }

            std::swap(mpPingPongFbo[srcId], mpPingPongFbo[dstId]);
        }
    }

    if (mDynamicWeighingEnabled && mSelectAfterIterations == mFilterIterations)
    {
        dynamicWeighting(pRenderContext,
            mpPingPongFbo[0]->getColorTexture(0),
            mpPingPongFbo[2]->getColorTexture(0));

        pRenderContext->blit(mpPingPongFbo[0]->getColorTexture(0)->getSRV(), mpPrevUnweightedIllumination->getRTV());
        pRenderContext->blit(mpPingPongFbo[2]->getColorTexture(0)->getSRV(), mpPrevWeightedIllumination->getRTV());

        pRenderContext->blit(mpDynamicWeightingFbo->getColorTexture(0)->getSRV(), mpPingPongFbo[0]->getColorTexture(0)->getRTV());
    }

    if (mFeedbackTap < 0)
    {
        pRenderContext->blit(mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::UnweightedHistoryIllumination)->getSRV(), mpFilteredPastFbo[0]->getRenderTargetView(0));
        pRenderContext->blit(mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields::WeightedHistoryIllumination)->getSRV(), mpFilteredPastFbo[1]->getRenderTargetView(0));
    }
}

void DynamicWeightingSVGF::dynamicWeighting(
    RenderContext* pRenderContext,
    Texture::SharedPtr pUnweightedIlluminationTexture,
    Texture::SharedPtr pWeightedIlluminationTexture)
{
    // cerr << "dynamicWeighting()" << endl;
    auto perImageCB = mpDynamicWeighting["PerImageCB"];

    // Input textures
    perImageCB["gPrevUnweightedIllumination"] = mpPrevUnweightedIllumination;
    perImageCB["gPrevWeightedIllumination"] = mpPrevWeightedIllumination;
    perImageCB["gUnweightedIllumination"] = pUnweightedIlluminationTexture;
    perImageCB["gWeightedIllumination"] = pWeightedIlluminationTexture;
    perImageCB["gPrevGradient"] = mpPrevGradientTexture;
    perImageCB["gVariance"] = mpVarianceTexture;
    perImageCB["gReprojection"] = mpReprojectionBuffer;

    // Parameters
    perImageCB["gGradientAlpha"] = mGradientAlpha;
    perImageCB["gGammaMidpoint"] = mGammaMidpoint;
    perImageCB["gGammaSteepness"] = mGammaSteepness;
    perImageCB["gSelectionMode"] = mSelectionMode;
    perImageCB["gNormalizationMode"] = mNormalizationMode;

    mpDynamicWeighting->execute(pRenderContext, mpDynamicWeightingFbo);
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
    bool dirty = 0;
    dirty |= widget.checkbox("Enable SVGF", mFilterEnabled);

    widget.text("");
    widget.text("Number of filter iterations.  Which");
    widget.text("    iteration feeds into future frames?");
    dirty |= widget.var("Iterations", mFilterIterations, 0, 10, 1);
    dirty |= widget.var("Feedback", mFeedbackTap, -1, mFilterIterations - 1, 1);
    if (mDynamicWeighingEnabled)
        dirty |= widget.var("Select After Iterations", mSelectAfterIterations, std::max(0, mFeedbackTap+1), mFilterIterations, 1);

    widget.text("");
    widget.text("Contol edge stopping on bilateral fitler");
    dirty |= widget.var("For Color", mPhiColor, 0.0f, 10000.0f, 0.01f);
    dirty |= widget.var("For Normal", mPhiNormal, 0.001f, 1000.0f, 0.2f);

    widget.text("");
    widget.text("How much history should be used?");
    widget.text("    (alpha; 0 = full reuse; 1 = no reuse)");
    dirty |= widget.var("Alpha", mAlpha, 0.0f, 1.0f, 0.001f);
    dirty |= widget.var("Moments Alpha", mMomentsAlpha, 0.0f, 1.0f, 0.001f);

    widget.text("");
    widget.text("Dynamic Weighting");
    bool enabledChanged = widget.checkbox("Enable Dynamic Weighting", mDynamicWeighingEnabled);
    dirty |= enabledChanged;
    mRecompile |= enabledChanged;
    if (mDynamicWeighingEnabled)
    {
        dirty |= widget.dropdown("Selection Mode", kSelectionModeList, mSelectionMode);
        dirty |= widget.var("Gradient Alpha", mGradientAlpha, 0.0f, 1.0f, 0.001f);
        dirty |= widget.var("Gamma Midpoint", mGammaMidpoint, -1e6f, 1e6f, 0.1f);
        dirty |= widget.var("Gamma Steepness", mGammaSteepness, 0.0f, 1e6f, 0.1f);
        dirty |= widget.dropdown("Normalization Mode", kNormalizationModeList, mNormalizationMode);

        if (mSelectionMode == (uint32_t)SelectionMode::Logistic)
        {
            float gamma0 = 1.0f / (1.0f + expf(-mGammaSteepness * (0 - mGammaMidpoint)));
            widget.text("gamma(0) = " + std::to_string(gamma0));
        }
    }

    widget.text("");
    widget.text("Debug");
    mBuffersNeedClear |= widget.button("Clear History");
    dirty |= widget.var("Sample Count Override", mSampleCountOverride, -1, 16, 1);

    if (dirty) mBuffersNeedClear = true;
}
