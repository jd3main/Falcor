
#include "DynamicWeightingSVGF.h"

#include "RenderGraph/RenderPassLibrary.h"
#include "RenderGraph/RenderPassHelpers.h"
#include "RenderGraph/BasePasses/FullScreenPass.h"

#include <string>

using std::vector;
using std::string;
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
    const char kAtrousShader[] = "RenderPasses/DynamicWeightingSVGF/Atrous.ps.slang";
    const char kFilterMomentShader[] = "RenderPasses/SVGFPass/SVGFFilterMoments.ps.slang";
    const char kReprojectShader[] = "RenderPasses/ReprojectionPass/Reprojection.ps.slang";
    const char kDynamicWeightingShader[] = "RenderPasses/DynamicWeightingSVGF/DynamicWeighting.ps.slang";
    const char kFinalModulateShader[] = "RenderPasses/SVGFPass/SVGFFinalModulate.ps.slang";
    const char kReflectTypesShader[] = "RenderPasses/ReprojectionPass/ReflectTypes.cs.slang";

    // Names of valid entries in the parameter dictionary.
    const char kEnabled[] = "Enabled";
    const char kSpatialFilterEnabled[] = "SpatialFilterEnabled";
    const char kDynamicWeighingEnabled[] = "DynamicWeighingEnabled";
    const char kIterations[] = "Iterations";
    const char kFeedbackTap[] = "FeedbackTap";
    const char kSelectAfterIterations[] = "GradientFilterIterations";
    const char kVarianceEpsilon[] = "VarianceEpsilon";
    const char kPhiColor[] = "PhiColor";
    const char kPhiNormal[] = "PhiNormal";
    const char kAlpha[] = "Alpha";
    const char kWeightedAlpha[] = "WeightedAlpha";
    const char kMomentsAlpha[] = "MomentsAlpha";
    const char kGradientAlpha[] = "GradientAlpha";
    const char kMaxGradient[] = "MaxGradient";
    const char kGradientMidpoint[] = "GradientMidpoint";
    const char kGammaSteepness[] = "GammaSteepness";
    const char kSelectionMode[] = "SelectionMode";
    const char kSampleCountOverride[] = "SampleCountOverride";
    const char kNormalizationMode[] = "NormalizationMode";
    const char kUseInputReprojection[] = "UseInputReprojection";
    const char kOutputPingPongAfterIters[] = "OutputPingPongAfterIters";
    const char kOutputPingPongIdx[] = "OutputPingPongIdx";
    const char kEnableDebugTag[] = "EnableDebugTag";
    const char kEnableDebugOutput[] = "EnableDebugOutput";
    const char kEnableOutputVariance[] = "EnableOutputVariance";

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
    const char kInputReprojectionTapWidthAndPrevPos[] = "TapWidthAndPrevPos";
    const char kInputReprojectionW0123[] = "W0123";
    const char kInputReprojectionW4567[] = "W4567";
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
        { kInputReprojectionTapWidthAndPrevPos, "_", "Reprojection Tap Width and Prev Pos", true, ResourceFormat::Unknown},
        { kInputReprojectionW0123,      "_",   "Reprojection W0123", true, ResourceFormat::Unknown},
        { kInputReprojectionW4567,      "_",   "Reprojection W4567", true, ResourceFormat::Unknown},
    };


    // Internal buffers
    const char kInternalBufferPreviousLinearZAndNormal[] = "Previous Linear Z and Packed Normal";
    const char kInternalBufferPreviousGradient[] = "Previous Gradient";

    // Output buffers
    const char kOutputBufferFilteredImage[] = "Filtered image";
    const char kOutputHistoryLength[] = "HistLength";
    const char kOutputVariance[] = "Variance";

    // Debug output buffers
    const char kOutputUnweightedHistoryWeight[] = "Weight_U";
    const char kOutputWeightedHistoryWeight[] = "Weight_W";
    const char kOutputUnweightedHistoryIllumination[] = "Illumination_U";
    const char kOutputWeightedHistoryIllumination[] = "Illumination_W";
    const char kOutputUnweightedFilteredIllumination[] = "Filtered_Illumination_U";
    const char kOutputWeightedFilteredIllumination[] = "Filtered_Illumination_W";
    const char kOutputPingPong[] = "PingPong";
    const char kOutputGradient[] = "OutGradient";
    const char kOutputGamma[] = "OutGamma";

    const ChannelList kOutputChannels =
    {
        /* { name, texname, description, optional, format } */
        { kOutputBufferFilteredImage,           "_",   "Filtered image",                  false,  ResourceFormat::RGBA16Float },
        { kOutputUnweightedHistoryWeight,       "_",   "Unweighted History Weight",       false,  ResourceFormat::R32Float },
        { kOutputWeightedHistoryWeight,         "_",   "Weighted History Weight",         false,  ResourceFormat::R32Float },
        { kOutputUnweightedHistoryIllumination, "_",   "Unweighted temporal filtered illumination",   false,  ResourceFormat::RGBA16Float },
        { kOutputWeightedHistoryIllumination,   "_",   "Weighted tmeporal filtered illumination",     false,  ResourceFormat::RGBA16Float },
        { kOutputUnweightedFilteredIllumination,"_",   "Filtered unweighted temporal filtered illumination",   false,  ResourceFormat::RGBA16Float },
        { kOutputWeightedFilteredIllumination,  "_",   "Filtered weighted tmeporal filtered illumination",     false,  ResourceFormat::RGBA16Float },
        { kOutputPingPong,                      "_",   "PingPong",                        false,  ResourceFormat::RGBA16Float },
        { kOutputGradient,                      "_",   "Gradient",                        false,  ResourceFormat::RGBA32Float },
        { kOutputGamma,                         "_",   "Gamma",                           false,  ResourceFormat::RGBA32Float },
    };

    enum TemporalFilterOutFields
    {
        TemporalFilterOutFields_Illumination,
        TemporalFilterOutFields_Moments,
        TemporalFilterOutFields_HistoryLength,
        TemporalFilterOutFields_HistoryWeight,
        TemporalFilterOutFields_WeightedIllumination,
        TemporalFilterOutFields_Variance,
        TemporalFilterOutFields_Gradient,
    };

    enum DynamicWeightingOutFields
    {
        DynamicWeightingOutFields_Color,
        DynamicWeightingOutFields_Gamma,
    };

    Gui::DropdownList kSelectionModeList = {
        #define X(x) { (uint32_t)x, #x },
        FOR_SELECTION_MODES(X)
        #undef X
    };

    Gui::DropdownList kNormalizationModeList = {
        #define X(x) { (uint32_t)x, #x },
        FOR_NORMALIZATION_MODES(X)
        #undef X
    };

    static const uint2 kScreenTileDim = { 16, 16 };     ///< Screen-tile dimension in pixels.
}

std::string toUpperCase(std::string&& str) {
    for (char &c : str) {
        c = std::toupper(c);
    }
    return str;
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
        else if (key == kSpatialFilterEnabled) mSpatialFilterEnabled = value;
        else if (key == kDynamicWeighingEnabled) mDynamicWeighingEnabled = value;
        else if (key == kIterations) mFilterIterations = value;
        else if (key == kFeedbackTap) mFeedbackTap = value;
        else if (key == kSelectAfterIterations) mSelectAfterIterations = value;
        else if (key == kVarianceEpsilon) mVarainceEpsilon = value;
        else if (key == kPhiColor) mPhiColor = value;
        else if (key == kPhiNormal) mPhiNormal = value;
        else if (key == kAlpha) mAlpha = value;
        else if (key == kWeightedAlpha) mWeightedAlpha = value;
        else if (key == kMomentsAlpha) mMomentsAlpha = value;
        else if (key == kGradientAlpha) mGradientAlpha = value;
        else if (key == kMaxGradient) mMaxGradient = value;
        else if (key == kGradientMidpoint) mGammaMidpoint = value;
        else if (key == kGammaSteepness) mGammaSteepness = value;
        else if (key == kSelectionMode) mSelectionMode = value;
        else if (key == kSampleCountOverride) mSampleCountOverride = value;
        else if (key == kNormalizationMode) mNormalizationMode = value;
        else if (key == kUseInputReprojection) mUseInputReprojection = value;
        else if (key == kOutputPingPongAfterIters) mOutputPingPongAfterIters = value;
        else if (key == kOutputPingPongIdx) mOutputPingPongIdx = value;
        else if (key == kEnableDebugTag) mEnableDebugTag = value;
        else if (key == kEnableDebugOutput) mEnableDebugOutput = value;
        else if (key == kEnableOutputVariance) mEnableOutputVariance = value;
        else logWarning("Unknown field '{}' in DynamicWeightingSVGF dictionary.", key);
    }
    mRecompile = true;
    mpReflectTypes = ComputePass::create(kReflectTypesShader);
    FALCOR_ASSERT(mpReflectTypes);
}

Dictionary DynamicWeightingSVGF::getScriptingDictionary()
{
    Dictionary dict;
    dict[kEnabled] = mFilterEnabled;
    dict[kSpatialFilterEnabled] = mSpatialFilterEnabled;
    dict[kDynamicWeighingEnabled] = mDynamicWeighingEnabled;
    dict[kIterations] = mFilterIterations;
    dict[kFeedbackTap] = mFeedbackTap;
    dict[kSelectAfterIterations] = mSelectAfterIterations;
    dict[kVarianceEpsilon] = mVarainceEpsilon;
    dict[kPhiColor] = mPhiColor;
    dict[kPhiNormal] = mPhiNormal;
    dict[kAlpha] = mAlpha;
    dict[kWeightedAlpha] = mWeightedAlpha;
    dict[kMomentsAlpha] = mMomentsAlpha;
    dict[kGradientAlpha] = mGradientAlpha;
    dict[kMaxGradient] = mMaxGradient;
    dict[kGradientMidpoint] = mGammaMidpoint;
    dict[kGammaSteepness] = mGammaSteepness;
    dict[kSelectionMode] = mSelectionMode;
    dict[kSampleCountOverride] = mSampleCountOverride;
    dict[kNormalizationMode] = mNormalizationMode;
    dict[kUseInputReprojection] = mUseInputReprojection;
    dict[kOutputPingPongAfterIters] = mOutputPingPongAfterIters;
    dict[kOutputPingPongIdx] = mOutputPingPongIdx;
    dict[kEnableDebugTag] = mEnableDebugTag;
    dict[kEnableDebugOutput] = mEnableDebugOutput;
    dict[kEnableOutputVariance] = mEnableOutputVariance;
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


uint32_t DynamicWeightingSVGF::getReprojectStructSize()
{
    auto rootVar = mpReflectTypes->getRootVar();
    auto reflectionType = rootVar["reprojection"].getType().get();
    const ReflectionResourceType* pResourceType = reflectionType->unwrapArray()->asResourceType();
    uint32_t structSize = pResourceType->getSize();
    FALCOR_ASSERT(structSize == 48);
    return structSize;
}

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

    addRenderPassOutputs(reflector, kOutputChannels, ResourceBindFlags::RenderTarget);

    reflector.addOutput(kOutputHistoryLength, "History Length")
        .format(ResourceFormat::R32Float)
        .bindFlags(ResourceBindFlags::RenderTarget | ResourceBindFlags::ShaderResource | ResourceBindFlags::UnorderedAccess);

    reflector.addOutput(kOutputVariance, "Variance")
        .format(ResourceFormat::R32Float)
        .bindFlags(ResourceBindFlags::RenderTarget | ResourceBindFlags::ShaderResource | ResourceBindFlags::UnorderedAccess);

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
    // Texture::SharedPtr pReprjectionTapWidthAndPrevPos = renderData.getTexture(kInputReprojectionTapWidthAndPrevPos);
    // Texture::SharedPtr pReprojectionW0123 = renderData.getTexture(kInputReprojectionW0123);
    // Texture::SharedPtr pReprojectionW4567 = renderData.getTexture(kInputReprojectionW4567);

    // Output Textures
    Texture::SharedPtr pOutputTexture = renderData.getTexture(kOutputBufferFilteredImage);
    Texture::SharedPtr pOutputHistoryLength = renderData.getTexture(kOutputHistoryLength);
    Texture::SharedPtr pOutputVariance = renderData.getTexture(kOutputVariance);

    // Debug output textures
    Texture::SharedPtr pOutputUnweightedHistoryWeight = renderData.getTexture(kOutputUnweightedHistoryWeight);
    Texture::SharedPtr pOutputWeightedHistoryWeight = renderData.getTexture(kOutputWeightedHistoryWeight);
    Texture::SharedPtr pOutputUnweightedHistoryIllumination = renderData.getTexture(kOutputUnweightedHistoryIllumination);
    Texture::SharedPtr pOutputWeightedHistoryIllumination = renderData.getTexture(kOutputWeightedHistoryIllumination);
    Texture::SharedPtr pOutputUnweightedFilteredIllumination = renderData.getTexture(kOutputUnweightedFilteredIllumination);
    Texture::SharedPtr pOutputWeightedFilteredIllumination = renderData.getTexture(kOutputWeightedFilteredIllumination);
    Texture::SharedPtr pOutputGradient = renderData.getTexture(kOutputGradient);
    Texture::SharedPtr pOutputGamma = renderData.getTexture(kOutputGamma);

    /*
    if (mUseInputReprojection)
    {
        FALCOR_ASSERT(pReprjectionTapWidthAndPrevPos && pReprojectionW0123 && pReprojectionW4567);
    }
    */

    if (!mpPackLinearZAndNormal || mRecompile)
    {
        cerr << "Recompile\n";
        mRecompile = false;
        mBuffersNeedClear = true;

        Program::DefineList defines;
        defines.add("_DW_ENABLED", mDynamicWeighingEnabled ? "1" : "0");
        defines.add("_DEBUG_TAG_ENABLED", mEnableDebugTag ? "1" : "0");
        defines.add("_DEBUG_OUTPUT_ENABLED", mEnableDebugOutput ? "1" : "0");

        #define X(x) defines.add(toUpperCase(#x), std::to_string(x));
        FOR_SELECTION_MODES(X)
        FOR_NORMALIZATION_MODES(X)
        #undef X

        defines.add("_SELECTION_MODE", SelectionModeNames[mSelectionMode]);
        defines.add("_NORMALIZATION_MODE", NormalizationModeNames[mNormalizationMode]);

        mpPackLinearZAndNormal = FullScreenPass::create(kPackLinearZAndNormalShader);
        // mpReproject = FullScreenPass::create(kReprojectShader);
        mpTemporalFilter = FullScreenPass::create(kTemporalFilterShader, defines);
        mpFilterMoments = FullScreenPass::create(kFilterMomentShader);
        mpAtrous = FullScreenPass::create(kAtrousShader, defines);
        mpDynamicWeighting = FullScreenPass::create(kDynamicWeightingShader, defines);
        mpFinalModulate = FullScreenPass::create(kFinalModulateShader);
    }
    FALCOR_ASSERT(mpPackLinearZAndNormal && mpTemporalFilter && mpAtrous && mpFilterMoments && mpFinalModulate);

    if (!mpDynamicWeightingFbo)
    {
        allocateFbos(mFrameDim, pRenderContext);
    }

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

        /*
        if (mUseInputReprojection)
        {
            mpReprojectionTapWidthAndPrevPosTexture = pReprjectionTapWidthAndPrevPos;
            mpReprojectionW0123Texture = pReprojectionW0123;
            mpReprojectionW4567Texture = pReprojectionW4567;
        }
        else
        {
            computeReprojection(pRenderContext, pColorTexture, pLinearZTexture, pMotionVectorTexture, pPosNormalFwidthTexture);
        }
        */


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

        if (mEnableDebugOutput)
        {
            FALCOR_PROFILE("[debug] blit history illumination");
            pRenderContext->blit(
                mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields_Illumination)->getSRV(),
                pOutputUnweightedHistoryIllumination->getRTV());
        }

        if (mSpatialFilterEnabled)
        {
            // Do a first cross-bilateral filtering of the illumination and
            // estimate its variance, storing the result into a float4 in
            // mpPingPongFbo[0].  Takes mpCurReprojFbo as input.
            computeFilteredMoments(pRenderContext);

            if (mEnableDebugOutput)
            {
                FALCOR_PROFILE("[debug] blit filtered moments");
                pRenderContext->blit(mpPingPongFbo[0]->getColorTexture(0)->getSRV(), pOutputUnweightedFilteredIllumination->getRTV());
                pRenderContext->blit(mpPingPongFbo[2]->getColorTexture(0)->getSRV(), pOutputWeightedFilteredIllumination->getRTV());
            }

            // Filter illumination from mpCurReprojFbo[0], storing the result
            // in mpPingPongFbo[0].  Along the way (or at the end, depending on
            // the value of mFeedbackTap), save the filtered illumination for
            // next time into mpFilteredPastFbo.
            computeAtrousDecomposition(pRenderContext, renderData, pAlbedoTexture);
        }
        else
        {
            pRenderContext->blit(mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields_Illumination)->getSRV(), mpFilteredPastFbo[0]->getColorTexture(0)->getRTV());
            pRenderContext->blit(mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields_Illumination)->getSRV(), mpSpatialFilteredFbo->getColorTexture(0)->getRTV());
        }


        // Compute albedo * filtered illumination and add emission back in.
        // Read from mpPingPongFbo and write to mpFinalFbo.
        computeFinalModulate(pRenderContext, pAlbedoTexture, pEmissionTexture);

        // Blit into the output texture.
        pRenderContext->blit(mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields_HistoryLength)->getSRV(), pOutputHistoryLength->getRTV());
        if (mEnableOutputVariance)
            pRenderContext->blit(mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields_Variance)->getSRV(), pOutputVariance->getRTV());

        if (mEnableDebugOutput)
        {
            FALCOR_PROFILE("[debug] blit history weight");
            pRenderContext->blit(mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields_HistoryWeight)->getSRV(), pOutputUnweightedHistoryWeight->getRTV());
        }

        pRenderContext->blit(mpFinalFbo->getColorTexture(0)->getSRV(), pOutputTexture->getRTV());

        // Swap resources so we're ready for next frame.
        std::swap(mpCurTemporalFilterFbo, mpPrevTemporalFilterFbo);

        // Blit into internal buffers for next frame.
        pRenderContext->blit(mpLinearZAndNormalFbo->getColorTexture(0)->getSRV(), mpPrevLinearZAndNormalTexture->getRTV());
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
        desc.setColorTarget(TemporalFilterOutFields_Illumination, Falcor::ResourceFormat::RGBA32Float);
        desc.setColorTarget(TemporalFilterOutFields_Moments, Falcor::ResourceFormat::RG32Float);
        desc.setColorTarget(TemporalFilterOutFields_HistoryLength, Falcor::ResourceFormat::R32Float);
        desc.setColorTarget(TemporalFilterOutFields_HistoryWeight,
                            mDynamicWeighingEnabled ? Falcor::ResourceFormat::RG32Float : Falcor::ResourceFormat::R32Float);
        desc.setColorTarget(TemporalFilterOutFields_WeightedIllumination, Falcor::ResourceFormat::RGBA32Float);
        desc.setColorTarget(TemporalFilterOutFields_Variance, Falcor::ResourceFormat::R32Float);
        desc.setColorTarget(TemporalFilterOutFields_Gradient, Falcor::ResourceFormat::RGBA32Float);
        mpCurTemporalFilterFbo = Fbo::create2D(dim.x, dim.y, desc);
        mpPrevTemporalFilterFbo = Fbo::create2D(dim.x, dim.y, desc);
    }

    {
        // Screen-size RGBA32F buffer for linear Z, derivative, and packed normal
        Fbo::Desc desc;
        desc.setColorTarget(0, Falcor::ResourceFormat::RGBA32Float);
        mpLinearZAndNormalFbo = Fbo::create2D(dim.x, dim.y, desc);
    }

    if (!mUseInputReprojection)
    {
        Fbo::Desc desc;
        desc.setColorTarget(0, Falcor::ResourceFormat::RGBA32Int);
        desc.setColorTarget(1, Falcor::ResourceFormat::RGBA32Float);
        desc.setColorTarget(2, Falcor::ResourceFormat::RGBA32Float);
        mpReprojectionFbo = Fbo::create2D(dim.x, dim.y, desc);
    }

    {
        // Screen-size FBOs with 1 RGBA32F buffer
        Fbo::Desc desc;
        desc.setColorTarget(0, Falcor::ResourceFormat::RGBA32Float);
        for (int i=0; i<2; i++)
        {
            mpFilteredPastFbo[i] = Fbo::create2D(dim.x, dim.y, desc);
        }
        mpSpatialFilteredFbo = Fbo::create2D(dim.x, dim.y, desc);
        mpFinalFbo = Fbo::create2D(dim.x, dim.y, desc);
    }

    {
        Fbo::Desc desc;
        desc.setColorTarget(DynamicWeightingOutFields_Color, Falcor::ResourceFormat::RGBA32Float);
        desc.setColorTarget(DynamicWeightingOutFields_Gamma, Falcor::ResourceFormat::R32Float);
        for (int i=0; i<4; i++)
        {
            mpPingPongFbo[i] = Fbo::create2D(dim.x, dim.y, desc);
        }
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
    if (mpReprojectionFbo)
        pRenderContext->clearFbo(mpReprojectionFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpSpatialFilteredFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpDynamicWeightingFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpFinalFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);

    // Clear the internal buffers
    pRenderContext->clearTexture(renderData.getTexture(kInternalBufferPreviousLinearZAndNormal).get());
    pRenderContext->clearTexture(renderData.getTexture(kInternalBufferPreviousGradient).get());
}

// Extracts linear z and its derivative from the linear Z texture and packs
// the normal from the world normal texture and packes them into the FBO.
// (It's slightly wasteful to copy linear z here, but having this all
// together in a single buffer is a small simplification, since we make a
// copy of it to refer to in the next frame.)
void DynamicWeightingSVGF::computeLinearZAndNormal(RenderContext* pRenderContext, Texture::SharedPtr pLinearZTexture,
    Texture::SharedPtr pWorldNormalTexture)
{
    FALCOR_PROFILE("computeLinearZAndNormal");

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
    FALCOR_PROFILE("computeReprojection");

    auto perImageCB = mpReproject["PerImageCB"];
    perImageCB["gMotion"] = pMotionoTexture;
    perImageCB["gPositionNormalFwidth"] = pPositionNormalFwidthTexture;
    perImageCB["gLinearZAndNormal"] = mpLinearZAndNormalFbo->getColorTexture(0);
    perImageCB["gPrevLinearZAndNormal"] = mpPrevLinearZAndNormalTexture;
    mpReproject->execute(pRendercontext, mpReprojectionFbo);

    mpReprojectionTapWidthAndPrevPosTexture = mpReprojectionFbo->getColorTexture(0);
    mpReprojectionW0123Texture = mpReprojectionFbo->getColorTexture(1);
    mpReprojectionW4567Texture = mpReprojectionFbo->getColorTexture(2);
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
    FALCOR_PROFILE("computeTemporalFilter");

    mpPrevLinearZAndNormalTexture = renderData.getTexture(kInternalBufferPreviousLinearZAndNormal);
    mpPrevGradientTexture = renderData.getTexture(kInternalBufferPreviousGradient);

    auto perImageCB = mpTemporalFilter["PerImageCB"];

    // From input channels
    perImageCB["gAlbedo"] = pAlbedoTexture;
    perImageCB["gColor"] = pColorTexture;
    perImageCB["gEmission"] = pEmissionTexture;
    perImageCB["gMotion"] = pMotionVectorTexture;
    perImageCB["gPositionNormalFwidth"] = pPositionNormalFwidthTexture;
    perImageCB["gSampleCount"] = pSampleCountTexture;

    // From computeLinearZAndNormal
    perImageCB["gLinearZAndNormal"] = mpLinearZAndNormalFbo->getColorTexture(0);

    // From previous frame
    perImageCB["gPrevMoments"] = mpPrevTemporalFilterFbo->getColorTexture(TemporalFilterOutFields_Moments);
    perImageCB["gPrevHistoryLength"] = mpPrevTemporalFilterFbo->getColorTexture(TemporalFilterOutFields_HistoryLength);
    perImageCB["gPrevHistoryWeight"] = mpPrevTemporalFilterFbo->getColorTexture(TemporalFilterOutFields_HistoryWeight);
    perImageCB["gPrevUnweightedIllum"] = mpFilteredPastFbo[0]->getColorTexture(0);
    perImageCB["gPrevLinearZAndNormal"] = mpPrevLinearZAndNormalTexture;
    if (mDynamicWeighingEnabled)
    {
        perImageCB["gPrevWeightedIllum"] = mpFilteredPastFbo[1]->getColorTexture(0);
        perImageCB["gPrevGradient"] = mpPrevGradientTexture;
    }

    // Parameters
    perImageCB["gAlpha"] = mAlpha;
    perImageCB["gWeightedAlpha"] = mWeightedAlpha;
    perImageCB["gMomentsAlpha"] = mMomentsAlpha;
    perImageCB["gSampleCountOverride"] = mSampleCountOverride;
    if (mDynamicWeighingEnabled)
    {
        perImageCB["gGradientAlpha"] = mGradientAlpha;
        perImageCB["gMaxGradient"] = mMaxGradient;
    }

    mpTemporalFilter->execute(pRenderContext, mpCurTemporalFilterFbo);

    if (mDynamicWeighingEnabled)
    {
        pRenderContext->blit(mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields_Gradient)->getSRV(), mpPrevGradientTexture->getRTV());
    }

    if (mEnableDebugOutput)
    {
        pRenderContext->blit(mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields_Gradient)->getSRV(), renderData.getTexture(kOutputGradient)->getRTV());
    }
}

void DynamicWeightingSVGF::computeFilteredMoments(RenderContext* pRenderContext)
{
    FALCOR_PROFILE("computeFilteredMoments");

    auto perImageCB = mpFilterMoments["PerImageCB"];

    perImageCB["gLinearZAndNormal"] = mpLinearZAndNormalFbo->getColorTexture(0);
    perImageCB["gMoments"] = mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields_Moments);

    // Parameters
    perImageCB["gPhiColor"] = mPhiColor;
    perImageCB["gPhiNormal"] = mPhiNormal;

    // Filter unweighted history
    perImageCB["gHistoryLength"] = mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields_HistoryLength);
    perImageCB["gIllumination"] = Texture::SharedPtr();
    perImageCB["gIllumination"] = mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields_Illumination);
    mpFilterMoments->execute(pRenderContext, mpPingPongFbo[0]);

    // Filter weighted history
    if (mDynamicWeighingEnabled)
    {
        perImageCB["gHistoryLength"] = mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields_HistoryLength);
        perImageCB["gIllumination"] = Texture::SharedPtr();
        perImageCB["gIllumination"] = mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields_WeightedIllumination);
        mpFilterMoments->execute(pRenderContext, mpPingPongFbo[2]);
    }
}

void DynamicWeightingSVGF::computeAtrousDecomposition(RenderContext* pRenderContext, const RenderData& renderData, Texture::SharedPtr pAlbedoTexture)
{
    FALCOR_PROFILE("computeAtrousDecomposition");
    // cerr << "computeAtrousDecomposition()" << endl;

    Texture::SharedPtr pOutputPingPong = renderData.getTexture(kOutputPingPong);

    bool doneSelection = false;

    if (mFeedbackTap < 0)
    {
        FALCOR_PROFILE("feedback");
        // cerr << "*feedback" << endl;
        pRenderContext->blit(mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields_Illumination)->getSRV(), mpFilteredPastFbo[0]->getRenderTargetView(0));
        if (mDynamicWeighingEnabled)
            pRenderContext->blit(mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields_WeightedIllumination)->getSRV(), mpFilteredPastFbo[1]->getRenderTargetView(0));
    }

    if (mDynamicWeighingEnabled && mSelectAfterIterations == 0)
    {

        dynamicWeighting(pRenderContext, renderData,
            mpPingPongFbo[0]->getColorTexture(0),
            mpPingPongFbo[2]->getColorTexture(0),
            mpDynamicWeightingFbo);

        pRenderContext->blit(mpDynamicWeightingFbo->getColorTexture(DynamicWeightingOutFields_Color)->getSRV(),
                             mpPingPongFbo[0]->getRenderTargetView(0));

        // pRenderContext->blit(mpPingPongFbo[0]->getColorTexture(0)->getSRV(),
        //                      mpPingPongFbo[1]->getRenderTargetView(0));
        // std::swap(mpPingPongFbo[0], mpPingPongFbo[1]);

        doneSelection = true;
    }

    if (mEnableDebugOutput && mOutputPingPongAfterIters == 0 && mOutputPingPongIdx >= 0)
    {
        FALCOR_PROFILE("blit mpPingPongFbo["+std::to_string(mOutputPingPongIdx)+"] -> pOutputPingPong");
        pRenderContext->blit(mpPingPongFbo[mOutputPingPongIdx]->getColorTexture(0)->getSRV(), pOutputPingPong->getRTV());
    }

    for (int i = 0; i < mFilterIterations; i++)
    {
        // If dynamic doneSelection has been done, we only need to filter the first pair of ping-pong buffers
        int nSrcIds = (mDynamicWeighingEnabled && !doneSelection) ? 4 : 2;
        // int nSrcIds = 4;
        for (int srcId = 0; srcId < nSrcIds; srcId += 2)
        {
            // cerr << "i=" << i << ", " << "srcId=" << srcId << endl;
            int dstId = srcId + 1;

            auto perImageCB = mpAtrous["PerImageCB"];
            perImageCB["gAlbedo"] = pAlbedoTexture;
            perImageCB["gLinearZAndNormal"] = mpLinearZAndNormalFbo->getColorTexture(0);
            perImageCB["gPhiColor"] = mPhiColor;
            perImageCB["gPhiNormal"] = mPhiNormal;
            perImageCB["gHistoryLength"] = mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields_HistoryLength);
            perImageCB["gStepSize"] = 1 << i;
            perImageCB["gIllumination"] = mpPingPongFbo[srcId]->getColorTexture(0);
            perImageCB["gNIterations"] = i;

            {
                FALCOR_PROFILE("Atrous["+std::to_string(i)+"], srcId="+std::to_string(srcId)+", dstId="+std::to_string(dstId));
                // cerr << "atrous: mpPingPongFbo[" << srcId << "] => mpPingPongFbo[" << dstId << "]\n";
                mpAtrous->execute(pRenderContext, mpPingPongFbo[dstId]);
            }

            // store the filtered color for the feedback path
            if (i == std::min(mFeedbackTap, mFilterIterations - 1))
            {
                FALCOR_PROFILE("feedback");
                FALCOR_ASSERT(!doneSelection)
                // cerr << "feedback: mpPingPongFbo[" << dstId << "] => mpFilteredPastFbo[" << srcId/2 << "]\n";
                pRenderContext->blit(mpPingPongFbo[dstId]->getColorTexture(0)->getSRV(),
                                     mpFilteredPastFbo[srcId/2]->getRenderTargetView(0));
            }

            // cerr << "swap mpPingPongFbo[" << srcId << "] <=> mpPingPongFbo[" << dstId << "]\n";
            std::swap(mpPingPongFbo[srcId], mpPingPongFbo[dstId]);
        }

        if (mDynamicWeighingEnabled && i == mSelectAfterIterations-1)
        {
            dynamicWeighting(pRenderContext, renderData,
                mpPingPongFbo[0]->getColorTexture(0),
                mpPingPongFbo[2]->getColorTexture(0),
                mpDynamicWeightingFbo);

            pRenderContext->blit(mpDynamicWeightingFbo->getColorTexture(DynamicWeightingOutFields_Color)->getSRV(),
                                 mpPingPongFbo[0]->getRenderTargetView(0));
            // std::swap(mpPingPongFbo[0], mpPingPongFbo[1]);

            doneSelection = true;
        }

        if (mEnableDebugOutput && i == mOutputPingPongAfterIters-1 && mOutputPingPongIdx >= 0)
        {
            FALCOR_PROFILE("blit mpPingPongFbo["+std::to_string(mOutputPingPongIdx)+"] -> pOutputPingPong");
            pRenderContext->blit(mpPingPongFbo[mOutputPingPongIdx]->getColorTexture(0)->getSRV(), pOutputPingPong->getRTV());
        }
    }

    {
        FALCOR_PROFILE("blit mpPingPongFbo[0] -> mpSpatialFilteredFbo");
        pRenderContext->blit(mpPingPongFbo[0]->getColorTexture(0)->getSRV(), mpSpatialFilteredFbo->getColorTexture(0)->getRTV());
    }
}

void DynamicWeightingSVGF::dynamicWeighting(
    RenderContext* pRenderContext,
    const RenderData& renderData,
    Texture::SharedPtr pUnweightedIlluminationTexture,
    Texture::SharedPtr pWeightedIlluminationTexture,
    Fbo::SharedPtr pOutputFbo)
{
    FALCOR_PROFILE("dynamicWeighting");

    Texture::SharedPtr pOutputGammaTexture = renderData.getTexture(kOutputGamma);

    // cerr << "dynamicWeighting()" << endl;
    auto perImageCB = mpDynamicWeighting["PerImageCB"];

    // Input textures
    perImageCB["gUnweightedIllumination"] = pUnweightedIlluminationTexture;
    perImageCB["gWeightedIllumination"] = pWeightedIlluminationTexture;
    perImageCB["gGradient"] = mpCurTemporalFilterFbo->getColorTexture(TemporalFilterOutFields_Gradient);

    // Parameters
    perImageCB["gGammaMidpoint"] = mGammaMidpoint;
    perImageCB["gGammaSteepness"] = mGammaSteepness;

    mpDynamicWeighting->execute(pRenderContext, pOutputFbo);

    if (mEnableDebugOutput)
    {
        FALCOR_PROFILE("[debug] blit debug outputs");
        pRenderContext->blit(pOutputFbo->getColorTexture(DynamicWeightingOutFields_Gamma)->getSRV(), pOutputGammaTexture->getRTV());
    }
}

void DynamicWeightingSVGF::computeFinalModulate(RenderContext* pRenderContext, Texture::SharedPtr pAlbedoTexture, Texture::SharedPtr pEmissionTexture)
{
    FALCOR_PROFILE("computeFinalModulate");

    auto perImageCB = mpFinalModulate["PerImageCB"];
    perImageCB["gAlbedo"] = pAlbedoTexture;
    perImageCB["gEmission"] = pEmissionTexture;
    perImageCB["gIllumination"] = mpSpatialFilteredFbo->getColorTexture(0);
    mpFinalModulate->execute(pRenderContext, mpFinalFbo);
}

void DynamicWeightingSVGF::renderUI(Gui::Widgets& widget)
{
    bool changed = false;
    bool dirty = 0;
    dirty |= widget.checkbox("Enable SVGF", mFilterEnabled);

    dirty |= widget.checkbox("Enable Spatial Filtering", mSpatialFilterEnabled);
    if (mSpatialFilterEnabled)
    {
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
    }


    widget.text("");
    widget.text("How much history should be used?");
    widget.text("    (alpha; 0 = full reuse; 1 = no reuse)");
    dirty |= widget.var("Alpha", mAlpha, 0.0f, 1.0f, 0.001f);
    dirty |= widget.var("Weighted Alpha", mWeightedAlpha, 0.0f, 1.0f, 0.001f);
    dirty |= widget.var("Moments Alpha", mMomentsAlpha, 0.0f, 1.0f, 0.001f);

    widget.text("");
    widget.text("Dynamic Weighting");
    changed = widget.checkbox("Enable Dynamic Weighting", mDynamicWeighingEnabled);
    dirty |= changed;
    mRecompile |= changed;
    if (mDynamicWeighingEnabled)
    {
        changed |= widget.dropdown("Selection Mode", kSelectionModeList, mSelectionMode);
        dirty |= changed;
        mRecompile |= changed;
        dirty |= widget.var("Gradient Alpha", mGradientAlpha, 0.0f, 1.0f, 0.001f);
        dirty |= widget.var("Max Gradient", mMaxGradient, 0.0f, 1e6f, 0.1f, false, "%.2f");
        dirty |= widget.var("Gamma Midpoint", mGammaMidpoint, -1e6f, 1e6f, 0.1f);
        dirty |= widget.var("Gamma Steepness", mGammaSteepness, 0.0f, 1e6f, 0.1f);
        changed |= widget.dropdown("Normalization Mode", kNormalizationModeList, mNormalizationMode);
        dirty |= changed;
        mRecompile |= changed;

        if (mSelectionMode == SELECTION_MODE_LOGISTIC)
        {
            float gamma0 = 1.0f / (1.0f + expf(-mGammaSteepness * (0 - mGammaMidpoint)));
            widget.text("gamma(0) = " + std::to_string(gamma0));
        }
    }

    widget.checkbox("Use Input Reprojection", mUseInputReprojection);
    widget.checkbox("Enable Output Variance", mEnableOutputVariance);

    widget.text("");
    widget.text("Debug");
    mBuffersNeedClear |= widget.button("Clear History");
    dirty |= widget.var("Sample Count Override", mSampleCountOverride, -1, 16, 1);
    changed = widget.checkbox("Enable Debug Tag", mEnableDebugTag);
    dirty |= changed;
    mRecompile |= changed;
    changed |= widget.checkbox("Enable Debug Output", mEnableDebugOutput);
    dirty |= changed;
    mRecompile |= changed;
    widget.var("Output PingPong After Iters", mOutputPingPongAfterIters, 0, mFilterIterations, 1);
    widget.var("Output PingPong Idx", mOutputPingPongIdx, 0, 3, 1);

    if (dirty) mBuffersNeedClear = true;
}
