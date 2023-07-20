#include "FoveatedPass.h"

#include "RenderGraph/RenderPassLibrary.h"
//#include "RenderGraph/RenderPassHelpers.h"
//#include "Utils/Math/FalcorMath.h"

#include <chrono>

using namespace std::chrono;

const float PI = 3.14159265358979323846f;
const float TAU = PI*2;

const RenderPass::Info FoveatedPass::kInfo { "FoveatedPass", "Generate texture representing number of samples required" };

namespace
{
    const std::string kShaderFile = "RenderPasses/FoveatedPass/FoveatedPass.cs.slang";
    const std::string kShaderEntryPoint = "calculateSampleCount";

    // Dictionary keys
    const std::string kEnabled = "enabled";
    const std::string kUseHistory = "useHistory";
    const std::string kAlpha = "alpha";
    const std::string kFoveaRadius = "foveaRadius";
    const std::string kFoveaSampleCount = "foveaSampleCount";
    const std::string kPeriphSampleCount = "periphSampleCount";
    const std::string kUniformSampleCount = "uniformSampleCount";
    const std::string kFoveaMoveRadius = "foveaMoveRadius";
    const std::string kFoveaMoveFreq = "foveaMoveFreq";

    // Input channels
    const std::string kInputHistorySampleWeight = "historySampleCount";

    // Output channels
    const std::string kOutputSampleCount = "sampleCount";
}


// Don't remove this. it's required for hot-reload to function properly
extern "C" FALCOR_API_EXPORT const char* getProjDir()
{
    return PROJECT_DIR;
}

extern "C" FALCOR_API_EXPORT void getPasses(Falcor::RenderPassLibrary& lib)
{
    lib.registerPass(FoveatedPass::kInfo, FoveatedPass::create);
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

    const auto currentTime = steady_clock::now();
    float t = gpFramework->getGlobalClock().getTime();
    uint2 resolution = renderData.getDefaultTextureDims();

    // Reset accumulation when resolution changes.
    if (resolution != mFrameDim)
    {
        mFrameDim = resolution;
        reset();
    }


    if (mpScene)
    {
        //float foveaDegree = 10.0f;
        //float foveaRadius = tan(foveaDegree * PI / 180.0f) * 0.5f;
        float2 foveatCenter = float2(resolution)/2.0f + float2(sin(t*TAU* mFoveaMoveFreq)* mFoveaMoveRadius, 0);

        auto CB = mpVars["PerFrameCB"];
        CB["gEnabled"] = mEnabled;
        CB["gUseHistory"] = mUseHistory;
        CB["gAlpha"] = mAlpha;
        CB["gInnerTargetQuality"] = mFoveaSampleCount;
        CB["gOuterTargetQuality"] = mPeriphSampleCount;
        CB["gSampleCountWhenDisabled"] = mSampleCountWhenDisabled;
        CB["gFoveaCenter"] = foveatCenter;
        CB["gFoveaRadius"] = mFoveaRadius;
        CB["gResolution"] = resolution;

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

FoveatedPass::FoveatedPass(const Dictionary& dict) : RenderPass(kInfo)
{
    for (const auto& [key, value] : dict)
    {
        if (key == kEnabled) mEnabled = value;
        else if (key == kUseHistory) mUseHistory = value;
        else if (key == kAlpha) mAlpha = value;
        else if (key == kFoveaRadius) mFoveaRadius = value;
        else if (key == kFoveaSampleCount) mFoveaSampleCount = value;
        else if (key == kPeriphSampleCount) mPeriphSampleCount = value;
        else if (key == kUniformSampleCount) mSampleCountWhenDisabled = value;
        else if (key == kFoveaMoveRadius) mFoveaMoveRadius = value;
        else if (key == kFoveaMoveFreq) mFoveaMoveFreq = value;
        else logWarning("Unknown field '" + key + "' in a FoveatedPass dictionary");
    }

    Program::DefineList defines;
    mpProgram = ComputeProgram::createFromFile(kShaderFile, kShaderEntryPoint, defines, Shader::CompilerFlags::TreatWarningsAsErrors);

    mpVars = ComputeVars::create(mpProgram->getReflector());

    mpState = ComputeState::create();
}

Dictionary FoveatedPass::getScriptingDictionary()
{
    Dictionary d;
    d[kEnabled] = mEnabled;
    d[kUseHistory] = mUseHistory;
    d[kAlpha] = mAlpha;
    d[kFoveaRadius] = mFoveaRadius;
    d[kFoveaSampleCount] = mFoveaSampleCount;
    d[kPeriphSampleCount] = mPeriphSampleCount;
    d[kUniformSampleCount] = mSampleCountWhenDisabled;
    d[kFoveaMoveRadius] = mFoveaMoveRadius;
    d[kFoveaMoveFreq] = mFoveaMoveFreq;
    return d;
}

void FoveatedPass::renderUI(Gui::Widgets& widget)
{
    int dirty = 0;

    dirty |= (int)widget.checkbox("Enable", mEnabled);
    dirty |= (int)widget.checkbox("Use History", mUseHistory);
    dirty |= (int)widget.var("Alpha", mAlpha);
    dirty |= (int)widget.var("Fovea Radius", mFoveaRadius);
    if (mEnabled)
    {
        dirty |= (int)widget.var("Fovea Sample Count", mFoveaSampleCount, 0.0f, 128.0f, 1.0f);
        dirty |= (int)widget.var("Periph Sample Count", mPeriphSampleCount, 0.0f, 128.0f, 1.0f);
    }
    else
    {
        dirty |= (int)widget.var("Sample Count", mSampleCountWhenDisabled, 0.0f, 128.0f, 1.0f);
    }
    dirty |= (int)widget.var("Move Frequency", mFoveaMoveFreq);
    dirty |= (int)widget.var("Move Radius", mFoveaMoveRadius);

    if (dirty) mBuffersNeedClear = true;
}

void FoveatedPass::reset()
{
}

