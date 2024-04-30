#pragma once
#include "Falcor.h"
#include "RenderGraph/BasePasses/FullScreenPass.h"
#include "RenderGraph/BasePasses/ComputePass.h"
#include "Enums.h"

using namespace Falcor;


class DynamicWeightingSVGF : public RenderPass
{
public:
    using SharedPtr = std::shared_ptr<DynamicWeightingSVGF>;

    static const Info kInfo;

    static SharedPtr create(RenderContext* pRenderContext = nullptr, const Dictionary& dict = {});

    virtual Dictionary getScriptingDictionary() override;
    virtual RenderPassReflection reflect(const CompileData& compileData) override;
    virtual void execute(RenderContext* pRenderContext, const RenderData& renderData) override;
    virtual void compile(RenderContext* pRenderContext, const CompileData& compileData) override;
    virtual void renderUI(Gui::Widgets& widget) override;

private:
    DynamicWeightingSVGF(const Dictionary& dict);

    bool init(const Dictionary& dict);
    void allocateFbos(uint2 dim, RenderContext* pRenderContext);
    void clearBuffers(RenderContext* pRenderContext, const RenderData& renderData);

    void computeLinearZAndNormal(RenderContext* pRenderContext, Texture::SharedPtr pLinearZTexture,
        Texture::SharedPtr pWorldNormalTexture);
    void computeTemporalFilter(RenderContext* pRenderContext,
        const RenderData& renderData,
        Texture::SharedPtr pAlbedoTexture,
        Texture::SharedPtr pColorTexture,
        Texture::SharedPtr pSampleCount,
        Texture::SharedPtr pEmissionTexture,
        Texture::SharedPtr pMotionVectorTexture,
        Texture::SharedPtr pPositionNormalFwidthTexture);
    void computeReprojection(RenderContext* pRendercontext,
        Texture::SharedPtr pColorTexture,
        Texture::SharedPtr pLinearZTexture,
        Texture::SharedPtr pMotionoTexture,
        Texture::SharedPtr pPositionNormalFwidthTexture);
    void computeFilterGradient(RenderContext* pRenderContext, const RenderData& renderData);
    void computeFilteredMoments(RenderContext* pRenderContext);
    void computeAtrousDecomposition(RenderContext* pRenderContext, const RenderData& renderData, Texture::SharedPtr pAlbedoTexture);
    void computeFinalModulate(RenderContext* pRenderContext, Texture::SharedPtr pAlbedoTexture, Texture::SharedPtr pEmissionTexture);
    void dynamicWeighting(
        RenderContext* pRenderContext,
        const RenderData& renderData,
        Texture::SharedPtr pUnweightedIlluminationTexture,
        Texture::SharedPtr pWeightedIlluminationTexture,
        Fbo::SharedPtr pOutputFbo);

    // Utility functions
    uint32_t getReprojectStructSize();

    // Internal states
    bool mBuffersNeedClear = false;
    bool mRecompile = true;

    // static params
    uint2   mFrameDim;

    // parameters
    bool    mFilterEnabled = true;
    bool    mSpatialFilterEnabled = true;
    bool    mDynamicWeighingEnabled = true;
    int32_t mFilterIterations = 4;
    int32_t mFeedbackTap = 1;
    float   mVarainceEpsilon = 1e-4f;
    float   mPhiColor = 10.0f;
    float   mPhiNormal = 128.0f;
    float   mAlpha = 0.05f;
    float   mWeightedAlpha = 0.05f;
    float   mMomentsAlpha = 0.2f;
    float   mGradientAlpha = 0.2f;
    float   mMaxGradient = 1e6f;
    bool    mAutoMidpoint = false;
    float   mGammaMidpoint = 0.01f;
    float   mGammaSteepness = 100;
    uint32_t mSelectionMode = SELECTION_MODE_LOGISTIC;
    uint32_t mNormalizationMode = NORMALIZATION_MODE_NONE;
    bool    mUseInputReprojection = false;
    bool    mEnableOutputVariance = true;
    bool    mFilterGradientEnabled = false;
    bool    mBestGammaEnabled = false;
    bool    mOptinalWeightingEnabled = false;

    // Debug parameters
    bool mEnableDebugOutput = false;
    bool mEnableDebugTag = false;
    int32_t mOutputPingPongAfterIters = 0;
    int32_t mOutputPingPongIdx = 0;
    int32_t mSampleCountOverride = -1;


    // SVGF passes
    FullScreenPass::SharedPtr mpPackLinearZAndNormal;
    FullScreenPass::SharedPtr mpTemporalFilter;
    FullScreenPass::SharedPtr mpFilterMoments;
    FullScreenPass::SharedPtr mpFilterGradient;
    FullScreenPass::SharedPtr mpAtrous;
    FullScreenPass::SharedPtr mpReproject;
    FullScreenPass::SharedPtr mpDynamicWeighting;
    FullScreenPass::SharedPtr mpFinalModulate;

    ComputePass::SharedPtr mpReflectTypes;  ///< Helper for reflecting structured buffer types.

    // Intermediate framebuffers
    Fbo::SharedPtr mpPingPongFbo[4];
    Fbo::SharedPtr mpLinearZAndNormalFbo;
    Fbo::SharedPtr mpFilteredPastFbo[2];
    Fbo::SharedPtr mpCurTemporalFilterFbo;
    Fbo::SharedPtr mpPrevTemporalFilterFbo;
    Fbo::SharedPtr mpMomentFilterFbo;
    Fbo::SharedPtr mpDynamicWeightingFbo;
    Fbo::SharedPtr mpSpatialFilteredFbo;
    Fbo::SharedPtr mpFinalFbo;
    Fbo::SharedPtr mpFilterGradientFbo;

    // Reprojection buffers
    Texture::SharedPtr mpReprojectionTapWidthAndPrevPosTexture;
    Texture::SharedPtr mpReprojectionW0123Texture;
    Texture::SharedPtr mpReprojectionW4567Texture;
    Fbo::SharedPtr mpReprojectionFbo;

    // Intermediate textures
    Texture::SharedPtr mpPrevLinearZAndNormalTexture;
};
