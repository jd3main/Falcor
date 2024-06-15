#pragma once
#include <chrono>
#include <random>

#include "Falcor.h"
#include "RenderGraph/RenderPassHelpers.h"
#include "Enums.h"

using namespace Falcor;


const float PI = 3.14159265358979323846f;
const float TAU = PI*2;

class FoveatedPass : public RenderPass
{
public:

    enum FoveaMovePattern
    {
        FOVEA_MOVE_PATTERN_LISSAJOUS,
        FOVEA_MOVE_PATTERN_MOVE_AND_STAY,
    };

    struct LissajousParams
    {
        float2 radius = float2(200, 200);
        float2 freq = float2(4, 5);
        float2 phase = float2(PI/2, 0);
    };

    struct MoveAndStayParams
    {
        float speed;
        float stayDuration;
    };

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
    virtual bool onMouseEvent(const MouseEvent& mouseEvent);
    virtual bool onKeyEvent(const KeyboardEvent& keyEvent) override { return false; }

    void reset();

private:
    FoveatedPass(const Dictionary& dict);

    void updateFovea(float t, float);
    void updateFoveaLissajous(float t, float dt);
    void updateFoveaMoveAndStay(float t, float dt);
    uint2 randomFoveaPos();

    Scene::SharedPtr            mpScene;
    ComputeProgram::SharedPtr   mpProgram;
    ComputeState::SharedPtr     mpState;
    ComputeVars::SharedPtr      mpVars;

    // Internal states
    ResourceFormat mOutputFormat = ResourceFormat::R8Uint;
    uint2 mFrameDim;
    float2 mFoveaPos = float2(0, 0);
    float2 mPrevStayPos = float2(0, 0);
    float2 mNextStayPos;
    float mLastStayStartTime = 0;
    float mLastMoveStartTime = -1;
    std::mt19937 mRng = std::mt19937(777);

    // Foveated rendering parameters
    uint32_t mShape = FOVEA_SHAPE_CIRCLE;
    uint32_t mFoveaInputType = FOVEA_INPUT_TYPE_PROCEDURAL;
    bool mUseHistory = true;
    float mAlpha = 0.05f;
    float mFoveaRadius = 200;
    float mFoveaSampleCount = 8;
    float mPeriphSampleCount = 1;
    uint32_t mFoveaMovePattern = FOVEA_MOVE_PATTERN_LISSAJOUS;
    LissajousParams mLissajousParams;
    MoveAndStayParams mMoveAndStayParams;
    bool mUseRealTime = false;
    bool mFlickerEnabled = false;
    float mFlickerBrightDuration = 1.0f;
    float mFlickerDarkDuration = 1.0f;
    float2 mMousePos;
};
