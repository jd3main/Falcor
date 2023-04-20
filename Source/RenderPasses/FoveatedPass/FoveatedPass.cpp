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

//const std::string kPrevSampleCount = "prevSampleCount";
const std::string kOutputSampleCount = "sampleCount";


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
    //reflector.addInput(kPrevSampleCount, "sample count of previous frame");
    //reflector.addInternal(kPrevSampleCount, "sample count of previous frame");
    reflector.addOutput(kOutputSampleCount, "sample count");
    return reflector;
}

void FoveatedPass::execute(RenderContext* pRenderContext, const RenderData& renderData)
{
    const auto& pOutputSampleCount = renderData.getTexture(kOutputSampleCount);
    //const auto& pPrevSampleCount = renderData.getTexture(kPrevSampleCount);
    auto pTargetFbo = Fbo::create({renderData.getTexture(kOutputSampleCount)});
    const float4 clearColor(0, 0, 0, 0);
    pRenderContext->clearFbo(pTargetFbo.get(), clearColor, 1.0f, 0, FboAttachmentType::All);
    mpGraphicsState->setFbo(pTargetFbo);

    auto current_time = steady_clock::now();
    float t = (float)duration_cast<milliseconds>(current_time.time_since_epoch()).count()/1000.0;
    float moveRadius = 300;
    float moveFrequency = 0.5;

    if (mpScene)
    {
        //float foveaDegree = 10.0f;
        //float foveaRadius = tan(foveaDegree * PI / 180.0f) * 0.5f;
        uint2 frameDim = renderData.getDefaultTextureDims();
        float2 foveatCenter = float2(frameDim)/2.0f + float2(sin(t*TAU*moveFrequency)* moveRadius, 0);
        mpVars["PerFrameCB"]["gInnerTargetQuality"] = 32.0f;
        mpVars["PerFrameCB"]["gOuterTargetQuality"] = 1.0f;
        mpVars["PerFrameCB"]["gFoveaCenter"] = foveatCenter;
        mpVars["PerFrameCB"]["gFoveaRadius"] = 200.0f;
        mpVars["PerFrameCB"]["gViewportSize"] = float2(frameDim);
        //mpVars["gPrevSampleCount"] = renderData.getTexture(kPrevSampleCount);
        std::clog << "width = " << frameDim.x << ", height = " << frameDim.y << std::endl;
        std::clog << "foveatCenter = " << to_string(foveatCenter) << std::endl;
        //pRenderContext->blit(pOutputSampleCount->getSRV(), pPrevSampleCount->getRTV());
        mpScene->rasterize(pRenderContext, mpGraphicsState.get(), mpVars.get(), mpRasterState, mpRasterState);


        //uint3 numGroups = div_round_up(uint3(frameDim.xy, 1u), pProgram->getReflector()->getThreadGroupSize());
        //mpState->setProgram(pProgram);
        //pRenderContext->dispatch(mpState.get(), mpVars.get(), numGroups);
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
    mpVars = GraphicsVars::create(mpProgram->getReflector());
}

FoveatedPass::FoveatedPass() : RenderPass(kInfo)
{
    mpProgram = GraphicsProgram::createFromFile("RenderPasses/FoveatedPass/FoveatedPass.3d.slang", "vsMain", "psMain");
    
    RasterizerState::Desc rasterDesc;
    rasterDesc.setFillMode(RasterizerState::FillMode::Solid);
    rasterDesc.setCullMode(RasterizerState::CullMode::Back);
    mpRasterState = RasterizerState::create(rasterDesc);


    mpGraphicsState = GraphicsState::create();
    mpGraphicsState->setProgram(mpProgram);
    mpGraphicsState->setRasterizerState(mpRasterState);
}
