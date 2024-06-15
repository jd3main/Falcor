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
#include "ReprojectionPass.h"

#include "RenderGraph/RenderPassLibrary.h"
#include "RenderGraph/RenderPassHelpers.h"
#include "RenderGraph/BasePasses/FullScreenPass.h"

const RenderPass::Info ReprojectionPass::kInfo { "ReprojectionPass", "Insert pass description here." };

namespace
{
    const char kPackLinearZAndNormalShader[] = "RenderPasses/SVGFPass/SVGFPackLinearZAndNormal.ps.slang";
    const char kReprjectionShader[] = "RenderPasses/ReprojectionPass/Reprojection.ps.slang";
    const char kReflectTypesShader[] = "RenderPasses/ReprojectionPass/ReflectTypes.cs.slang";

    // Input buffers
    const char kInputBufferPosNormalFwidth[] = "PositionNormalFwidth";
    const char kInputBufferLinearZ[] = "LinearZ";
    const char kInputBufferMotionVector[] = "MotionVec";
    const ChannelList kInputChannels =
    {
        /* { name, texname, desc, optional, format } */
        { kInputBufferPosNormalFwidth,  "_",   "PosNormalFwidth", false, ResourceFormat::Unknown},
        { kInputBufferLinearZ,          "_",   "Linear Z",        false, ResourceFormat::Unknown},
        { kInputBufferMotionVector,     "_",   "Motion Vector",   false, ResourceFormat::Unknown},
    };

    // Output buffers
    const char kOutputBufferReprojection[] = "Reprojection";
    const char kOutputBufferTapWidthAndPrevPos[] = "TapWidthAndPrevPos";
    const char kOutputBufferW0123[] = "W0123";
    const char kOutputBufferW4567[] = "W4567";
    const ChannelList kOutputChannels =
    {
        { kOutputBufferTapWidthAndPrevPos,  "_", "TapWidthAndPrevPos",  false, ResourceFormat::RGBA32Int},
        { kOutputBufferW0123,               "_", "W0123",               false, ResourceFormat::RGBA32Float},
        { kOutputBufferW4567,               "_", "W4567",               false, ResourceFormat::RGBA32Float},
    };

    // Internal buffers
    const char kInternalBufferPreviousLinearZAndNormal[] = "PreviousLinearZAndNormal";

    // Parameters
    const char kVarianceEpsilon[] = "VarianceEpsilon";
    const char kPhiColor[] = "PhiColor";
    const char kPhiNormal[] = "PhiNormal";

    // Fbo Fields
    enum ReprojectionFboFields
    {
        REPROJECTION_FBO_FIELDS_TAP_WIDTH_AND_PREV_POS,
        REPROJECTION_FBO_FIELDS_W0123,
        REPROJECTION_FBO_FIELDS_W4567,
    };
}

// Don't remove this. it's required for hot-reload to function properly
extern "C" FALCOR_API_EXPORT const char* getProjDir()
{
    return PROJECT_DIR;
}

extern "C" FALCOR_API_EXPORT void getPasses(Falcor::RenderPassLibrary& lib)
{
    lib.registerPass(ReprojectionPass::kInfo, ReprojectionPass::create);
}

ReprojectionPass::SharedPtr ReprojectionPass::create(RenderContext* pRenderContext, const Dictionary& dict)
{
    SharedPtr pPass = SharedPtr(new ReprojectionPass(dict));
    return pPass;
}

ReprojectionPass::ReprojectionPass(const Dictionary& dict)
    : RenderPass(kInfo)
{
    for (const auto& [key, value] : dict)
    {
        // ...
    }

    mpReflectTypes = ComputePass::create(kReflectTypesShader);
    FALCOR_ASSERT(mpReflectTypes);
}

Dictionary ReprojectionPass::getScriptingDictionary()
{
    Dictionary dict;
    return dict;
}

RenderPassReflection ReprojectionPass::reflect(const CompileData& compileData)
{
    RenderPassReflection reflector;
    addRenderPassInputs(reflector, kInputChannels);
    addRenderPassOutputs(reflector, kOutputChannels, ResourceBindFlags::RenderTarget | ResourceBindFlags::UnorderedAccess);

    reflector.addInternal(kInternalBufferPreviousLinearZAndNormal, "Previous Linear Z and Packed Normal")
        .format(ResourceFormat::RGBA32Float)
        .bindFlags(Resource::BindFlags::RenderTarget | Resource::BindFlags::ShaderResource);

    return reflector;
}

void ReprojectionPass::compile(RenderContext* pRenderContext, const CompileData& compileData)
{
    allocateResources(compileData.defaultTexDims, pRenderContext);
}

void ReprojectionPass::allocateResources(uint2 dim, RenderContext *pRenderContext)
{
    {
        // Screen-size RGBA32F buffer for linear Z, derivative, and packed normal
        Fbo::Desc desc;
        desc.setColorTarget(0, Falcor::ResourceFormat::RGBA32Float);
        mpLinearZAndNormalFbo = Fbo::create2D(dim.x, dim.y, desc);
    }

    {
        Fbo::Desc desc;
        desc.setColorTarget(REPROJECTION_FBO_FIELDS_TAP_WIDTH_AND_PREV_POS, Falcor::ResourceFormat::RGBA32Int);
        desc.setColorTarget(REPROJECTION_FBO_FIELDS_W0123, Falcor::ResourceFormat::RGBA32Float);
        desc.setColorTarget(REPROJECTION_FBO_FIELDS_W4567, Falcor::ResourceFormat::RGBA32Float);
        mpReprojectionFbo = Fbo::create2D(dim.x, dim.y, desc);
    }
}

void ReprojectionPass::execute(RenderContext* pRenderContext, const RenderData& renderData)
{
    Texture::SharedPtr pLinearZTexture = renderData.getTexture(kInputBufferLinearZ);
    Texture::SharedPtr pMotionoTexture = renderData.getTexture(kInputBufferMotionVector);
    Texture::SharedPtr pPositionNormalFwidthTexture = renderData.getTexture(kInputBufferPosNormalFwidth);

    Texture::SharedPtr pTapWidthAndPrevPosTexture = renderData.getTexture(kOutputBufferTapWidthAndPrevPos);
    Texture::SharedPtr pW0123Texture = renderData.getTexture(kOutputBufferW0123);
    Texture::SharedPtr pW4567Texture = renderData.getTexture(kOutputBufferW4567);

    FALCOR_ASSERT(pLinearZTexture && pMotionoTexture && pPositionNormalFwidthTexture);
    FALCOR_ASSERT(pTapWidthAndPrevPosTexture && pW0123Texture && pW4567Texture);

    mpPrevLinearZAndNormalTexture = renderData.getTexture(kInternalBufferPreviousLinearZAndNormal);

    if (!mpPackLinearZAndNormal)
    {
        mpPackLinearZAndNormal = FullScreenPass::create(kPackLinearZAndNormalShader);
        mpReproject = FullScreenPass::create(kReprjectionShader);
    }

    computeLinearZAndNormal(pRenderContext, pLinearZTexture, pPositionNormalFwidthTexture);
    computeReprojection(pRenderContext, renderData, pLinearZTexture, pMotionoTexture, pPositionNormalFwidthTexture);

    // blit to prev
    pRenderContext->blit(mpLinearZAndNormalFbo->getColorTexture(0)->getSRV(), mpPrevLinearZAndNormalTexture->getRTV());

    // blit to output
    pRenderContext->blit(mpReprojectionFbo->getColorTexture(REPROJECTION_FBO_FIELDS_TAP_WIDTH_AND_PREV_POS)->getSRV(), pTapWidthAndPrevPosTexture->getRTV());
    pRenderContext->blit(mpReprojectionFbo->getColorTexture(REPROJECTION_FBO_FIELDS_W0123)->getSRV(), pW0123Texture->getRTV());
    pRenderContext->blit(mpReprojectionFbo->getColorTexture(REPROJECTION_FBO_FIELDS_W4567)->getSRV(), pW4567Texture->getRTV());
}

void ReprojectionPass::computeLinearZAndNormal(
    RenderContext* pRenderContext,
    Texture::SharedPtr pLinearZTexture,
    Texture::SharedPtr pWorldNormalTexture)
{
    FALCOR_PROFILE("computeLinearZAndNormal");

    auto perImageCB = mpPackLinearZAndNormal["PerImageCB"];
    perImageCB["gLinearZ"] = pLinearZTexture;
    perImageCB["gNormal"] = pWorldNormalTexture;

    mpPackLinearZAndNormal->execute(pRenderContext, mpLinearZAndNormalFbo);
}


void ReprojectionPass::computeReprojection(
    RenderContext* pRendercontext, const RenderData& renderData,
    Texture::SharedPtr pLinearZTexture,
    Texture::SharedPtr pMotionoTexture,
    Texture::SharedPtr pPositionNormalFwidthTexture)
{
    FALCOR_PROFILE("computeReprojection");
    auto perImageCB = mpReproject["PerImageCB"];
    perImageCB["gMotion"] = pMotionoTexture;
    perImageCB["gPositionNormalFwidth"] = pPositionNormalFwidthTexture;
    perImageCB["gLinearZAndNormal"] = mpLinearZAndNormalFbo->getColorTexture(0);
    perImageCB["gPrevLinearZAndNormal"] = mpPrevLinearZAndNormalTexture;

    mpReproject->execute(pRendercontext, mpReprojectionFbo);
}


void ReprojectionPass::renderUI(Gui::Widgets& widget)
{
}
