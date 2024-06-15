#include "FoveatedPass.h"

#include "Enums.h"
#include "RenderGraph/RenderPassLibrary.h"
#include "RenderGraph/RenderPassHelpers.h"
#include "Utils/Math/FalcorMath.h"

#include <iostream>
#include <chrono>
#include <random>

using namespace std;
using namespace std::chrono;


const RenderPass::Info FoveatedPass::kInfo { "FoveatedPass", "Generate texture representing number of samples required" };

namespace
{
    const std::string kShaderFile = "RenderPasses/FoveatedPass/FoveatedPass.cs.slang";
    const std::string kShaderEntryPoint = "calculateSampleCount";

    // Dictionary keys
    const std::string kShape = "shape";
    const std::string kFoveaInputType = "foveaInputType";
    const std::string kUseHistory = "useHistory";
    const std::string kAlpha = "alpha";
    const std::string kFoveaRadius = "foveaRadius";
    const std::string kFoveaSampleCount = "foveaSampleCount";
    const std::string kPeriphSampleCount = "periphSampleCount";
    const std::string kUniformSampleCount = "uniformSampleCount";

    const std::string kFoveaMovePattern = "foveaMovePattern";
    const std::string kFoveaMoveRadius = "foveaMoveRadius";
    const std::string kFoveaMoveFreq = "foveaMoveFreq";
    const std::string kFoveaMovePhase = "foveaMovePhase";
    const std::string kFoveaMoveSpeed = "foveaMoveSpeed";
    const std::string kFoveaMoveStayDuration = "foveaMoveStayDuration";

    const std::string kUseRealTime = "useRealTime";
    const std::string kFlickerEnabled = "flickerEnabled";
    const std::string kFlickerBrightDurationMs = "flickerBrightDurationMs";
    const std::string kFlickerDarkDurationMs = "flickerDarkDurationMs";

    // Input channels
    const std::string kInputHistorySampleWeight = "historySampleCount";

    // Output channels
    const std::string kOutputSampleCount = "sampleCount";


    // UI
    Gui::DropdownList kShapeList = {
        { (uint32_t)FOVEA_SHAPE_UNIFORM, "Uniform" },
        { (uint32_t)FOVEA_SHAPE_CIRCLE, "Circle" },
        { (uint32_t)FOVEA_SHAPE_SPLITHORIZONTALLY, "SplitHorizontally" },
        { (uint32_t)FOVEA_SHAPE_SPLITVERTICALLY, "SplitVertically" },
    };

    Gui::DropdownList kFoveaInputTypeList = {
        { (uint32_t)FoveaInputType::FOVEA_INPUT_TYPE_NONE, "None" },
        { (uint32_t)FoveaInputType::FOVEA_INPUT_TYPE_PROCEDURAL, "Procedural" },
        { (uint32_t)FoveaInputType::FOVEA_INPUT_TYPE_MOUSE, "Mouse" },
    };

    Gui::DropdownList kFoveaMoveDirectionList = {
        { (uint32_t)FoveatedPass::FoveaMovePattern::FOVEA_MOVE_PATTERN_LISSAJOUS, "Lissajous" },
        { (uint32_t)FoveatedPass::FoveaMovePattern::FOVEA_MOVE_PATTERN_MOVE_AND_STAY, "Move and Stay" },
    };
}


static void regBindings(pybind11::module& m)
{
}

// Don't remove this. it's required for hot-reload to function properly
extern "C" FALCOR_API_EXPORT const char* getProjDir()
{
    return PROJECT_DIR;
}

extern "C" FALCOR_API_EXPORT void getPasses(Falcor::RenderPassLibrary& lib)
{
    lib.registerPass(FoveatedPass::kInfo, FoveatedPass::create);
    ScriptBindings::registerBinding(regBindings);
}

FoveatedPass::SharedPtr FoveatedPass::create(RenderContext* pRenderContext, const Dictionary& dict)
{
    SharedPtr pPass = SharedPtr(new FoveatedPass(dict));
    return pPass;
}

RenderPassReflection FoveatedPass::reflect(const CompileData& compileData)
{
    RenderPassReflection reflector;
    const uint2 sz = compileData.defaultTexDims;

    reflector.addInput(kInputHistorySampleWeight, "history sample weight")
        .bindFlags(ResourceBindFlags::ShaderResource)
        .format(ResourceFormat::R32Float)
        .flags(RenderPassReflection::Field::Flags::Optional)
        .texture2D(sz.x, sz.y);

    reflector.addOutput(kOutputSampleCount, "sample count")
        .bindFlags(ResourceBindFlags::RenderTarget | ResourceBindFlags::UnorderedAccess | ResourceBindFlags::ShaderResource)
        .format(mOutputFormat)
        .texture2D(sz.x, sz.y);

    return reflector;
}

void FoveatedPass::execute(RenderContext* pRenderContext, const RenderData& renderData)
{
    const auto& pOutputSampleCount = renderData.getTexture(kOutputSampleCount);

    const auto currentTime = high_resolution_clock::now();
    float realTime = duration_cast<microseconds>(currentTime.time_since_epoch()).count() / 1'000'000.0f;
    static float lastRealTime = realTime;
    float t = mUseRealTime ? realTime : gpFramework->getGlobalClock().getTime();
    float dt = mUseRealTime ? realTime - lastRealTime : gpFramework->getGlobalClock().getDelta();
    lastRealTime = realTime;
    uint2 resolution = renderData.getDefaultTextureDims();

    // Reset accumulation when resolution changes.
    if (resolution != mFrameDim)
    {
        mFrameDim = resolution;
        reset();
    }


    if (mpScene)
    {
        updateFovea(t, dt);

        auto CB = mpVars["PerFrameCB"];
        CB["gShape"] = (int)mShape;
        CB["gUseHistory"] = mUseHistory;
        CB["gAlpha"] = mAlpha;
        CB["gInnerTargetQuality"] = mFoveaSampleCount;
        CB["gOuterTargetQuality"] = mPeriphSampleCount;
        CB["gFoveaCenter"] = mFoveaPos;
        CB["gFoveaRadius"] = mFoveaRadius;
        CB["gResolution"] = resolution;
        CB["gFlickerEnabled"] = mFlickerEnabled;
        CB["gFlickerBrightDuration"] = mFlickerBrightDuration;
        CB["gFlickerDarkDuration"] = mFlickerDarkDuration;
        CB["gFrameTime"] = t;

        mpVars["gHistorySampleWeight"] = renderData.getTexture(kInputHistorySampleWeight);
        mpVars["gOutputSampleCount"] = pOutputSampleCount;

        //std::clog << "width = " << resolution.x << ", height = " << resolution.y << std::endl;
        //std::clog << "foveatCenter = " << to_string(foveatCenter) << std::endl;

        uint3 numGroups = div_round_up(uint3(mFrameDim.x, mFrameDim.y, 1u), mpProgram->getReflector()->getThreadGroupSize());

        mpState->setProgram(mpProgram);
        pRenderContext->dispatch(mpState.get(), mpVars.get(), numGroups);
    }
}

void FoveatedPass::setScene(RenderContext* pRenderContext, const Scene::SharedPtr& pScene)
{
    mpScene = pScene;
    if (mpScene)
        mpProgram->addDefines(mpScene->getSceneDefines());
}

bool FoveatedPass::onMouseEvent(const MouseEvent& mouseEvent)
{
    if (mFoveaInputType == FoveaInputType::FOVEA_INPUT_TYPE_MOUSE)
    {
        if (mouseEvent.type == MouseEvent::Type::Move)
        {
            mMousePos = mouseEvent.pos;
            return true;
        }
    }
    return false;
}

FoveatedPass::FoveatedPass(const Dictionary& dict) : RenderPass(kInfo)
{
    for (const auto& [key, value] : dict)
    {
        if (key == kShape) mShape = value;
        else if (key == kFoveaInputType) mFoveaInputType = value;
        else if (key == kUseHistory) mUseHistory = value;
        else if (key == kAlpha) mAlpha = value;
        else if (key == kFoveaRadius) mFoveaRadius = value;
        else if (key == kFoveaSampleCount) mFoveaSampleCount = value;
        else if (key == kPeriphSampleCount) mPeriphSampleCount = value;
        else if (key == kFoveaMovePattern) mFoveaMovePattern = value;
        else if (key == kFoveaMoveRadius) mLissajousParams.radius = value;
        else if (key == kFoveaMoveFreq) mLissajousParams.freq = value;
        else if (key == kFoveaMovePhase) mLissajousParams.phase = value;
        else if (key == kFoveaMoveSpeed) mMoveAndStayParams.speed = value;
        else if (key == kFoveaMoveStayDuration) mMoveAndStayParams.stayDuration = value;
        else if (key == kUseRealTime) mUseRealTime = value;
        else if (key == kFlickerEnabled) mFlickerEnabled = value;
        else if (key == kFlickerBrightDurationMs) mFlickerBrightDuration = value;
        else if (key == kFlickerDarkDurationMs) mFlickerDarkDuration = value;
        else logWarning("Unknown field '" + key + "' in a FoveatedPass dictionary");
    }

    std::cerr << "FoveatedPass: Shape = " << mShape << std::endl;
    std::cerr << "FoveatedPass: FoveaMovePattern = " << mFoveaMovePattern << std::endl;
    std::cerr << "FoveatedPass: FoveaMoveRadius = " << to_string(mLissajousParams.radius) << std::endl;
    std::cerr << "FoveatedPass: FoveaMoveFreq = " << to_string(mLissajousParams.freq) << std::endl;
    std::cerr << "FoveatedPass: FoveaMovePhase = " << to_string(mLissajousParams.phase) << std::endl;
    std::cerr << "FoveatedPass: FoveaMoveSpeed = " << to_string(mMoveAndStayParams.speed) << std::endl;
    std::cerr << "FoveatedPass: FoveaMoveStayDuration = " << to_string(mMoveAndStayParams.stayDuration) << std::endl;

    Program::DefineList defines;
    mpProgram = ComputeProgram::createFromFile(kShaderFile, kShaderEntryPoint, defines, Shader::CompilerFlags::TreatWarningsAsErrors);

    mpVars = ComputeVars::create(mpProgram->getReflector());

    mpState = ComputeState::create();
}

Dictionary FoveatedPass::getScriptingDictionary()
{
    Dictionary d;
    d[kShape] = mShape;
    d[kFoveaInputType] = mFoveaInputType;
    d[kUseHistory] = mUseHistory;
    d[kAlpha] = mAlpha;
    d[kFoveaRadius] = mFoveaRadius;
    d[kFoveaSampleCount] = mFoveaSampleCount;
    d[kPeriphSampleCount] = mPeriphSampleCount;
    d[kFoveaMovePattern] = mFoveaMovePattern;
    d[kFoveaMoveRadius] = mLissajousParams.radius;
    d[kFoveaMoveFreq] = mLissajousParams.freq;
    d[kFoveaMovePhase] = mLissajousParams.phase;
    d[kFoveaMoveSpeed] = mMoveAndStayParams.speed;
    d[kFoveaMoveStayDuration] = mMoveAndStayParams.stayDuration;
    d[kUseRealTime] = mUseRealTime;
    d[kFlickerEnabled] = mFlickerEnabled;
    d[kFlickerBrightDurationMs] = mFlickerBrightDuration;
    d[kFlickerDarkDurationMs] = mFlickerDarkDuration;
    return d;
}

void FoveatedPass::renderUI(Gui::Widgets& widget)
{
    int dirty = 0;

    widget.text("Current position: " + to_string(mFoveaPos));

    widget.dropdown("Fovea Shape", kShapeList, mShape);
    widget.dropdown("Fovea Input Type", kFoveaInputTypeList, mFoveaInputType);

    widget.checkbox("Use History", mUseHistory);
    widget.var("Alpha", mAlpha);
    if (mShape == FOVEA_SHAPE_CIRCLE || mShape == FOVEA_SHAPE_SPLITHORIZONTALLY || mShape == FOVEA_SHAPE_SPLITVERTICALLY)
    {
        widget.var("Fovea Radius", mFoveaRadius);
        widget.var("Fovea Sample Count", mFoveaSampleCount, 0.0f, 128.0f, 1.0f, false, "%.0f");
        widget.var("Periph Sample Count", mPeriphSampleCount, 0.0f, 128.0f, 1.0f, false, "%.0f");
    }
    else
    {
        widget.var("Sample Count", mFoveaSampleCount, 0.0f, 128.0f, 1.0f, false, "%.0f");
    }

    widget.text("Fovea Movement");

    widget.dropdown("Move Pattern", kFoveaMoveDirectionList, mFoveaMovePattern);
    if (mFoveaMovePattern == FoveaMovePattern::FOVEA_MOVE_PATTERN_LISSAJOUS)
    {
        widget.var("Frequency", mLissajousParams.freq, 0.0f, 100.0f, 0.01f, false, "%.2f");
        widget.var("Radius", mLissajousParams.radius, 0.0f, 1000.0f, 1.0f, false, "%.2f");
    }
    else if (mFoveaMovePattern == FoveaMovePattern::FOVEA_MOVE_PATTERN_MOVE_AND_STAY)
    {
        widget.var("Stay Duration", mMoveAndStayParams.stayDuration, 0.0f, 100.0f, 0.01f, false, "%.2f");
        widget.tooltip("Duration to stay at a position before moving to the next. Unit: seconds.");
        widget.var("Speed", mMoveAndStayParams.speed, 0.0f, 10000.0f, 1.0f, false, "%.0f");
        widget.tooltip("Speed of movement. Unit: pixels per second.");
    }

    widget.checkbox("Use Real Time", mUseRealTime);

    widget.text("Flicker");
    widget.checkbox("Flicker", mFlickerEnabled);
    if (mFlickerEnabled)
    {
        widget.var("Bright Duration", mFlickerBrightDuration, 0.0f, 20.0f, 0.001f, false, "%.3f");
        widget.var("Dark Duration", mFlickerDarkDuration, 0.0f, 20.0f, 0.001f, false, "%.3f");
    }
}

void FoveatedPass::reset()
{
}


void FoveatedPass::updateFovea(float t, float dt)
{
    switch (mFoveaInputType) {
    case FOVEA_INPUT_TYPE_NONE:
        mFoveaPos = float2(mFrameDim) / 2.0f;
        break;
    case FOVEA_INPUT_TYPE_PROCEDURAL:
        switch (mFoveaMovePattern) {
        case FoveaMovePattern::FOVEA_MOVE_PATTERN_LISSAJOUS:
            updateFoveaLissajous(t, dt);
            break;
        case FoveaMovePattern::FOVEA_MOVE_PATTERN_MOVE_AND_STAY:
            updateFoveaMoveAndStay(t, dt);
            break;
        }
        break;
    case FOVEA_INPUT_TYPE_MOUSE:
        mFoveaPos = mMousePos * float2(mFrameDim);
        break;
    }
}

void FoveatedPass::updateFoveaLissajous(float t, float dt)
{
    float2 displace = sin(t * TAU * mLissajousParams.freq + mLissajousParams.phase) * mLissajousParams.radius;
    mFoveaPos = float2(mFrameDim) / 2.0f + displace;
}

void FoveatedPass::updateFoveaMoveAndStay(float t, float dt)
{
    // check if it's time to move
    if (t - mLastStayStartTime > mMoveAndStayParams.stayDuration)
    {
        // check if we are just starting to move
        if (mLastMoveStartTime < mLastStayStartTime)
        {
            mLastMoveStartTime = mLastStayStartTime + mMoveAndStayParams.stayDuration;
            mPrevStayPos = mFoveaPos;
            mNextStayPos = randomFoveaPos();
        }

        float2 targetDisplace = mNextStayPos - mPrevStayPos;
        float2 moveDir = targetDisplace / length(targetDisplace);
        float2 displace = moveDir * mMoveAndStayParams.speed * (t - mLastMoveStartTime);
        if (length(displace) < length(targetDisplace))
        {
            mFoveaPos = mPrevStayPos + displace;
        }
        else
        {
            mFoveaPos = mNextStayPos;
            mLastStayStartTime = t;
        }
    }
}

uint2 FoveatedPass::randomFoveaPos()
{
    return uint2(mRng() % mFrameDim.x, mRng() % mFrameDim.y);
}
