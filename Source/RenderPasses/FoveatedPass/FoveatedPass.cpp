#include "FoveatedPass.h"
#include "RenderGraph/RenderPassLibrary.h"
#include "RenderGraph/RenderPassHelpers.h"
#include "Utils/Math/FalcorMath.h"
#include <chrono>

using namespace std::chrono;

const float PI = 3.14159265358979323846f;
const float TAU = PI*2;

const RenderPass::Info FoveatedPass::kInfo { "FoveatedPass", "Generate texture representing number of samples required" };

namespace
{
    const std::string kShaderFile = "RenderPasses/FoveatedPass/FoveatedPass.cs.slang";
    const std::string kShaderEntryPoint = "calculateSampleCount";

    const std::string kInputHistorySampleWeight = "historySampleCount";
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
    SharedPtr pPass = SharedPtr(new FoveatedPass());
    return pPass;
}

Dictionary FoveatedPass::getScriptingDictionary()
{
    return Dictionary();
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

    auto current_time = steady_clock::now();
    float t = (float)duration_cast<milliseconds>(current_time.time_since_epoch()).count()/1000.0;
    float moveRadius = 300;
    float moveFrequency = 0.5;

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
        float2 foveatCenter = float2(resolution)/2.0f + float2(sin(t*TAU*moveFrequency)* moveRadius, 0);

        auto CB = mpVars["PerFrameCB"];
        CB["gInnerTargetQuality"] = 32.0f;
        CB["gOuterTargetQuality"] = 1.0f;
        CB["gFoveaCenter"] = foveatCenter;
        CB["gFoveaRadius"] = 200.0f;
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

void FoveatedPass::renderUI(Gui::Widgets& widget)
{
}

void FoveatedPass::setScene(RenderContext* pRenderContext, const Scene::SharedPtr& pScene)
{
    mpScene = pScene;
    if (mpScene)
        mpProgram->addDefines(mpScene->getSceneDefines());
}

FoveatedPass::FoveatedPass() : RenderPass(kInfo)
{
    Program::DefineList defines;
    if (mOutputFormat == ResourceFormat::R32Float)
        defines.add("_OUTPUT_COLOR");
    mpProgram = ComputeProgram::createFromFile(kShaderFile, kShaderEntryPoint, defines, Shader::CompilerFlags::TreatWarningsAsErrors);

    mpVars = ComputeVars::create(mpProgram->getReflector());

    mpState = ComputeState::create();
}


void FoveatedPass::reset()
{
    // TODO
}
