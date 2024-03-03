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

    // Internal buffers
    const char kInternalBufferPreviousLinearZAndNormal[] = "PreviousLinearZAndNormal";

    // Parameters
    const char kVarianceEpsilon[] = "VarianceEpsilon";
    const char kPhiColor[] = "PhiColor";
    const char kPhiNormal[] = "PhiNormal";
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

uint32_t ReprojectionPass::getReprojectStructSize()
{
    auto rootVar = mpReflectTypes->getRootVar();
    auto reflectionType = rootVar["reprojection"].getType().get();
    const ReflectionResourceType* pResourceType = reflectionType->unwrapArray()->asResourceType();
    uint32_t structSize = pResourceType->getSize();
    return structSize;
}

RenderPassReflection ReprojectionPass::reflect(const CompileData& compileData)
{
    RenderPassReflection reflector;
    addRenderPassInputs(reflector, kInputChannels);

    uint32_t structSize = getReprojectStructSize();
    FALCOR_ASSERT(structSize > 0);
    std::cerr << "structSize: " << structSize << std::endl;
    uint32_t bufferSize = compileData.defaultTexDims.x * compileData.defaultTexDims.y * structSize;
    reflector.addField(RenderPassReflection::Field())
        .rawBuffer(bufferSize)
        .name(kOutputBufferReprojection)
        .desc("Reprojection Buffer")
        .visibility(RenderPassReflection::Field::Visibility::Output)
        .bindFlags(Resource::BindFlags::ShaderResource | Resource::BindFlags::UnorderedAccess | Resource::BindFlags::RenderTarget);

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
        mpReprojectionFbo = Fbo::create2D(dim.x, dim.y, Falcor::ResourceFormat::RGBA32Float);
    }
}

void ReprojectionPass::execute(RenderContext* pRenderContext, const RenderData& renderData)
{
    Texture::SharedPtr pLinearZTexture = renderData.getTexture(kInputBufferLinearZ);
    Texture::SharedPtr pMotionoTexture = renderData.getTexture(kInputBufferMotionVector);
    Texture::SharedPtr pPositionNormalFwidthTexture = renderData.getTexture(kInputBufferPosNormalFwidth);
    Buffer::SharedPtr pReprojectionBuffer = renderData.getResource(kOutputBufferReprojection)->asBuffer();

    mpPrevLinearZAndNormalTexture = renderData.getTexture(kInternalBufferPreviousLinearZAndNormal);

    if (!mpPackLinearZAndNormal)
    {
        mpPackLinearZAndNormal = FullScreenPass::create(kPackLinearZAndNormalShader);
        mpReproject = FullScreenPass::create(kReprjectionShader);
    }

    computeLinearZAndNormal(pRenderContext, pLinearZTexture, pPositionNormalFwidthTexture);
    computeReprojection(pRenderContext, renderData, pLinearZTexture, pMotionoTexture, pPositionNormalFwidthTexture);
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

    Buffer::SharedPtr pReprojectionBuffer = renderData.getResource(kOutputBufferReprojection)->asBuffer();

    auto perImageCB = mpReproject["PerImageCB"];
    perImageCB["gMotion"] = pMotionoTexture;
    perImageCB["gPositionNormalFwidth"] = pPositionNormalFwidthTexture;
    perImageCB["gLinearZAndNormal"] = mpLinearZAndNormalFbo->getColorTexture(0);
    perImageCB["gPrevLinearZAndNormal"] = mpPrevLinearZAndNormalTexture;
    perImageCB["gReprojection"] = pReprojectionBuffer;
    mpReproject->execute(pRendercontext, mpReprojectionFbo);

    pRendercontext->blit(mpLinearZAndNormalFbo->getColorTexture(0)->getSRV(), mpPrevLinearZAndNormalTexture->getRTV());
}


void ReprojectionPass::renderUI(Gui::Widgets& widget)
{
}
