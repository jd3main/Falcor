#pragma once
#include "Falcor.h"
#include "RenderGraph/RenderPassHelpers.h"

using namespace Falcor;

class FoveatedPass : public RenderPass
{
public:
    using SharedPtr = std::shared_ptr<FoveatedPass>;

    static const Info kInfo;

    /** Create a new render pass object.
        \param[in] pRenderContext The render context.
        \param[in] dict Dictionary of serialized parameters.
        \return A new object, or an exception is thrown if creation failed.
    */
    static SharedPtr create(RenderContext* pRenderContext = nullptr, const Dictionary& dict = {});

    virtual Dictionary getScriptingDictionary() override;
    virtual RenderPassReflection reflect(const CompileData& compileData) override;
    virtual void compile(RenderContext* pRenderContext, const CompileData& compileData) override {}
    virtual void execute(RenderContext* pRenderContext, const RenderData& renderData) override;
    virtual void renderUI(Gui::Widgets& widget) override;
    virtual void setScene(RenderContext* pRenderContext, const Scene::SharedPtr& pScene) override;
    virtual bool onMouseEvent(const MouseEvent& mouseEvent) override { return false; }
    virtual bool onKeyEvent(const KeyboardEvent& keyEvent) override { return false; }


    void reset();

private:
    FoveatedPass();
    Scene::SharedPtr            mpScene;
    ComputeProgram::SharedPtr   mpProgram;
    ComputeState::SharedPtr     mpState;
    ComputeVars::SharedPtr      mpVars;

    uint2 mFrameDim;

    ResourceFormat              mOutputFormat = ResourceFormat::R8Uint;
};
