#pragma once
#include "Falcor.h"
#include "RenderGraph/BasePasses/FullScreenPass.h"

using namespace Falcor;

class MySVGFPass : public RenderPass
{
public:
    using SharedPtr = std::shared_ptr<MySVGFPass>;

    static const Info kInfo;

    static SharedPtr create(RenderContext* pRenderContext = nullptr, const Dictionary& dict = {});

    virtual Dictionary getScriptingDictionary() override;
    virtual RenderPassReflection reflect(const CompileData& compileData) override;
    virtual void execute(RenderContext* pRenderContext, const RenderData& renderData) override;
    virtual void compile(RenderContext* pRenderContext, const CompileData& compileData) override;
    virtual void renderUI(Gui::Widgets& widget) override;

private:
    MySVGFPass(const Dictionary& dict);

    bool init(const Dictionary& dict);
    void allocateFbos(uint2 dim, RenderContext* pRenderContext);
    void clearBuffers(RenderContext* pRenderContext, const RenderData& renderData);

    void computeLinearZAndNormal(RenderContext* pRenderContext, Texture::SharedPtr pLinearZTexture,
        Texture::SharedPtr pWorldNormalTexture);
    void computeReprojection(RenderContext* pRenderContext, Texture::SharedPtr pAlbedoTexture,
        Texture::SharedPtr pColorTexture,
        Texture::SharedPtr pSampleCount,
        Texture::SharedPtr pSampleTotalWeight,
        Texture::SharedPtr pEmissionTexture,
        Texture::SharedPtr pMotionVectorTexture,
        Texture::SharedPtr pPositionNormalFwidthTexture);
    void computeFilteredMoments(RenderContext* pRenderContext);
    void computeAtrousDecomposition(RenderContext* pRenderContext, Texture::SharedPtr pAlbedoTexture);

    bool mBuffersNeedClear = false;

    // SVGF parameters
    bool    mFilterEnabled = true;
    int32_t mFilterIterations = 4;
    int32_t mFeedbackTap = 1;
    float   mVarainceEpsilon = 1e-4f;
    float   mPhiColor = 10.0f;
    float   mPhiNormal = 128.0f;
    float   mAlpha = 0.05f;
    float   mMomentsAlpha = 0.2f;

    // SVGF passes
    FullScreenPass::SharedPtr mpPackLinearZAndNormal;
    FullScreenPass::SharedPtr mpReprojection;
    FullScreenPass::SharedPtr mpFilterMoments;
    FullScreenPass::SharedPtr mpAtrous;
    FullScreenPass::SharedPtr mpFinalModulate;

    // Intermediate framebuffers
    Fbo::SharedPtr mpPingPongFbo[2];
    Fbo::SharedPtr mpLinearZAndNormalFbo;
    Fbo::SharedPtr mpFilteredPastFbo;
    Fbo::SharedPtr mpCurReprojFbo;
    Fbo::SharedPtr mpPrevReprojFbo;
    Fbo::SharedPtr mpFilteredIlluminationFbo;
    Fbo::SharedPtr mpFinalFbo;
};
