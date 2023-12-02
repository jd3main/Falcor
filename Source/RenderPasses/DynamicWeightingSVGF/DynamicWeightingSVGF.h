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
    void computeReprojection(RenderContext* pRendercontext);
    void computeTemporalFilter(RenderContext* pRenderContext,
        const RenderData& renderData,
        Texture::SharedPtr pAlbedoTexture,
        Texture::SharedPtr pColorTexture,
        Texture::SharedPtr pSampleCount,
        Texture::SharedPtr pEmissionTexture,
        Texture::SharedPtr pMotionVectorTexture,
        Texture::SharedPtr pPositionNormalFwidthTexture);
    void DynamicWeightingSVGF::computeReprojection(RenderContext* pRendercontext,
        Texture::SharedPtr pColorTexture,
        Texture::SharedPtr pLinearZTexture,
        Texture::SharedPtr pMotionoTexture,
        Texture::SharedPtr pPositionNormalFwidthTexture);
    void computeFilteredMoments(RenderContext* pRenderContext);
    void computeAtrousDecomposition(RenderContext* pRenderContext, const RenderData& renderData, Texture::SharedPtr pAlbedoTexture);
    void computeFinalModulate(RenderContext* pRenderContext, Texture::SharedPtr pAlbedoTexture, Texture::SharedPtr pEmissionTexture);
    void dynamicWeighting(
        RenderContext* pRenderContext,
        Texture::SharedPtr pUnweightedIlluminationTexture,
        Texture::SharedPtr pWeightedIlluminationTexture);

    bool mBuffersNeedClear = false;

    // static params
    uint2   mFrameDim;

    // SVGF parameters
    bool    mFilterEnabled = true;
    bool    mDynamicWeighingEnabled = true;
    int32_t mFilterIterations = 4;
    int32_t mFeedbackTap = 1;
    int32_t mSelectAfterIterations = 1;
    float   mVarainceEpsilon = 1e-4f;
    float   mPhiColor = 10.0f;
    float   mPhiNormal = 128.0f;
    float   mAlpha = 0.05f;
    float   mMomentsAlpha = 0.2f;
    float   mGradientAlpha = 0.2f;
    float   mExpectedDelay = -10;
    float   mGammaMidpoint = 0.01f;
    float   mGammaSteepness = 100;
    uint32_t mSelectionMode = SelectionMode::Logistic;
    int32_t mSampleCountOverride = -1;

    // SVGF passes
    FullScreenPass::SharedPtr mpPackLinearZAndNormal;
    FullScreenPass::SharedPtr mpTemporalFilter;
    FullScreenPass::SharedPtr mpFilterMoments;
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
    Fbo::SharedPtr mpDynamicWeightingFbo;
    Fbo::SharedPtr mpFinalFbo;

    // Intermediate textures
    Texture::SharedPtr mpPrevLinearZAndNormalTexture;
    Texture::SharedPtr mpPrevGradientTexture;
    Texture::SharedPtr mpGradientTexture;
    Texture::SharedPtr mpGammaTexture;
    Texture::SharedPtr mpVarianceTexture;
    Texture::SharedPtr mpPrevUnweightedIllumination;
    Texture::SharedPtr mpPrevWeightedIllumination;

    // Intermediate buffers
    Buffer::SharedPtr mpReprojectionBuffer;
    Fbo::SharedPtr mpReprojectionFbo;
};
