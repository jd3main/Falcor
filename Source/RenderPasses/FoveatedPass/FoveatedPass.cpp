/***************************************************************************
 # Copyright (c) 2015-22, NVIDIA CORPORATION. All rights reserved.
 #
 # Redistribution and use in source and binary forms, with or without
 # modification, are permitted provided that the following conditions
 # are met:
 #  * Redistributions of source code must retain the above copyright
 #    notice, this list of conditions and the following disclaimer.
 #  * Redistributions in binary form must reproduce the above copyright
 #    notice, this list of conditions and the following disclaimer in the
 #    documentation and/or other materials provided with the distribution.
 #  * Neither the name of NVIDIA CORPORATION nor the names of its
 #    contributors may be used to endorse or promote products derived
 #    from this software without specific prior written permission.
 #
 # THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS "AS IS" AND ANY
 # EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 # IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
 # PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR
 # CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
 # EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
 # PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
 # PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
 # OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 # (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 # OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 **************************************************************************/
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

        mpVars["PerFrameCB"]["gInnerTargetQuality"] = 32.0f;
        mpVars["PerFrameCB"]["gOuterTargetQuality"] = 1.0f;
        mpVars["PerFrameCB"]["gFoveaCenter"] = foveatCenter;
        mpVars["PerFrameCB"]["gFoveaRadius"] = 200.0f;
        mpVars["PerFrameCB"]["gResolution"] = resolution;

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
