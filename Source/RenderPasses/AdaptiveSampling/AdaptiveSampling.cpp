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
#include "AdaptiveSampling.h"
#include "Configs.h"

#include "RenderGraph/RenderPassLibrary.h"
#include "RenderGraph/RenderPassHelpers.h"

const RenderPass::Info AdaptiveSampling::kInfo { "AdaptiveSampling", "Insert pass description here." };

namespace
{
    const char kWeightEstimationShaderFile[] = "RenderPasses/AdaptiveSampling/WeightEstimation.ps.slang";
    const char kNormalizationShaderFile[] = "RenderPasses/AdaptiveSampling/Normalization.ps.slang";
    const char kReflectTypesShader[] = "RenderPasses/ReprojectionPass/ReflectTypes.cs.slang";

    // Input channels
    const char kInputVariance[] = "var";
    const char kInputHistoryLength[] = "histLength";
    const char kInputBufferReprojection[] = "Reprojection";
    const ChannelList kInputChannels =
    {
        { kInputHistoryLength,              "_", "History Length",              false, ResourceFormat::R32Float },
        { kInputVariance,                   "_", "Variance",                    false, ResourceFormat::R32Float },
    };

    // Output channels
    const char kOutputSampleCount[] = "sampleCount";
#if DEBUG_OUTPUT_ENABLED
    const char kOutputDensityWeight[] = "densityWeight";
#endif
    const ChannelList kOutputChannels =
    {
        { kOutputSampleCount,   "_", "The number of samples per pixel",     false, ResourceFormat::R8Uint },
#if DEBUG_OUTPUT_ENABLED
        { kOutputDensityWeight, "_", "Unnormalized density",                false, ResourceFormat::R32Float },
#endif
    };

    // Serialized parameters
    const char kEnabled[] = "Enabled";
    const char kAverageSampleCountBudget[] = "AverageSampleCountBudget";
    const char kMinVariance[] = "MinVariance";
    const char kMaxVariance[] = "MaxVariance";
    const char kMinSamplePerPixel[] = "MinSamplePerPixel";
    const char kMaxSamplePerPixel[] = "MaxSamplePerPixel";
}

// Don't remove this. it's required for hot-reload to function properly
extern "C" FALCOR_API_EXPORT const char* getProjDir()
{
    return PROJECT_DIR;
}

extern "C" FALCOR_API_EXPORT void getPasses(Falcor::RenderPassLibrary& lib)
{
    lib.registerPass(AdaptiveSampling::kInfo, AdaptiveSampling::create);
}

AdaptiveSampling::AdaptiveSampling(const Dictionary& dict)
    : RenderPass(kInfo)
{
    for (const auto& [key, value] : dict)
    {
        if (key == kEnabled) mEnabled = value;
        else if (key == kAverageSampleCountBudget) mAverageSampleCountBudget = value;
        else if (key == kMinVariance) mMinVariance = value;
        else if (key == kMaxVariance) mMaxVariance = value;
        else if (key == kMinSamplePerPixel) mMinSamplePerPixel = value;
        else if (key == kMaxSamplePerPixel) mMaxSamplePerPixel = value;
        else logWarning("Unknown field '" + key + "' in a AdaptiveSampling dictionary");
    }
    mpReflectTypes = ComputePass::create(kReflectTypesShader);
}

AdaptiveSampling::SharedPtr AdaptiveSampling::create(RenderContext* pRenderContext, const Dictionary& dict)
{
    SharedPtr pPass = SharedPtr(new AdaptiveSampling(dict));
    return pPass;
}

Dictionary AdaptiveSampling::getScriptingDictionary()
{
    Dictionary dict;
    dict[kEnabled] = mEnabled;
    dict[kAverageSampleCountBudget] = mAverageSampleCountBudget;
    dict[kMinVariance] = mMinVariance;
    dict[kMaxVariance] = mMaxVariance;
    dict[kMinSamplePerPixel] = mMinSamplePerPixel;
    dict[kMaxSamplePerPixel] = mMaxSamplePerPixel;
    return dict;
}

uint32_t AdaptiveSampling::getReprojectStructSize()
{
    auto rootVar = mpReflectTypes->getRootVar();
    auto reflectionType = rootVar["reprojection"].getType().get();
    const ReflectionResourceType* pResourceType = reflectionType->unwrapArray()->asResourceType();
    uint32_t structSize = pResourceType->getSize();
    FALCOR_ASSERT(structSize == 48);
    return structSize;
}

RenderPassReflection AdaptiveSampling::reflect(const CompileData& compileData)
{
    // Define the required resources here
    RenderPassReflection reflector;
    addRenderPassInputs(reflector, kInputChannels, ResourceBindFlags::ShaderResource | ResourceBindFlags::UnorderedAccess);
    addRenderPassOutputs(reflector, kOutputChannels, ResourceBindFlags::RenderTarget | ResourceBindFlags::UnorderedAccess);

    reflector.addField(RenderPassReflection::Field())
        .rawBuffer(getReprojectStructSize() * compileData.defaultTexDims.x * compileData.defaultTexDims.y)
        .name(kInputBufferReprojection)
        .desc("Reprojection Buffer")
        .visibility(RenderPassReflection::Field::Visibility::Input)
        .bindFlags(ResourceBindFlags::ShaderResource | ResourceBindFlags::UnorderedAccess);

    return reflector;
}

void AdaptiveSampling::compile(RenderContext* pRenderContext, const CompileData& compileData)
{
    mFrameDim = compileData.defaultTexDims;
    allocateResources(mFrameDim, pRenderContext);

    {
        Program::DefineList defines;
        mpParallelReduction = ComputeParallelReduction::create();
        mpWeightEstimationPass = FullScreenPass::create(kWeightEstimationShaderFile);
        mpNormalizationPass = FullScreenPass::create(kNormalizationShaderFile);
    }
}

void AdaptiveSampling::execute(RenderContext* pRenderContext, const RenderData& renderData)
{
    // Check if the output texture size has changed
    uint2 resolution = renderData.getDefaultTextureDims();
    if (resolution != mFrameDim)
    {
        mFrameDim = resolution;
        allocateResources(mFrameDim, pRenderContext);
    }

    if (mBuffersNeedClear)
    {
        clearBuffers(pRenderContext, renderData);
        mBuffersNeedClear = false;
    }

    if (!mEnabled)
    {
        pRenderContext->clearUAV(renderData.getTexture(kOutputSampleCount)->getUAV().get(), uint4((int)mAverageSampleCountBudget));
        return;
    }

    runWeightEstimationPass(pRenderContext, renderData);
    runReductionPass(pRenderContext, renderData);
    runNormalizeWeightPass(pRenderContext, renderData);
}

void AdaptiveSampling::allocateResources(uint2 dim, RenderContext* pRenderContext)
{
    mpTotalWeightBuffer = Buffer::create(sizeof(float4), Buffer::BindFlags::UnorderedAccess | Buffer::BindFlags::ShaderResource, Buffer::CpuAccess::None, nullptr);

    {
        Fbo::Desc desc;
        desc.setColorTarget(0, ResourceFormat::R32Float);
        mpWeightEstimationFbo = Fbo::create2D(dim.x, dim.y, desc);
    }

    {
        Fbo::Desc desc;
        desc.setColorTarget(0, ResourceFormat::R32Float);
        mpNormalizationFbo = Fbo::create2D(dim.x, dim.y, desc);
    }
}

void AdaptiveSampling::clearBuffers(RenderContext* pRenderContext, const RenderData& renderData)
{
    pRenderContext->clearFbo(mpWeightEstimationFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    pRenderContext->clearFbo(mpNormalizationFbo.get(), float4(0), 1.0f, 0, FboAttachmentType::All);
    mBuffersNeedClear = false;
}

void AdaptiveSampling::runWeightEstimationPass(RenderContext* pRenderContext, const RenderData& renderData)
{
    FALCOR_PROFILE("runWeightEstimationPass");

    Texture::SharedPtr pInputVariance = renderData.getTexture(kInputVariance);
    Texture::SharedPtr pInputHistoryLength = renderData.getTexture(kInputHistoryLength);
    Buffer::SharedPtr pInputBufferReprojection = renderData.getResource(kInputBufferReprojection)->asBuffer();

#if DEBUG_OUTPUT_ENABLED
    Texture::SharedPtr pOutputDensityWeight = renderData.getTexture(kOutputDensityWeight);
#endif

    // FALCOR_ASSERT(pInputBufferReprojection);

    // Set shader parameters
    auto perImageCB = mpWeightEstimationPass["PerImageCB"];
    perImageCB["gInputReprojection"] = pInputBufferReprojection;
    perImageCB["gInputVariance"] = pInputVariance;
    perImageCB["gInputHistoryLength"] = pInputHistoryLength;
    perImageCB["gResolution"] = mFrameDim;
    perImageCB["gMinVariance"] = mMinVariance;
    perImageCB["gMaxVariance"] = mMaxVariance;

    mpWeightEstimationPass->execute(pRenderContext, mpWeightEstimationFbo);

#if DEBUG_OUTPUT_ENABLED
    pRenderContext->blit(mpWeightEstimationFbo->getColorTexture(0)->getSRV(), pOutputDensityWeight->getRTV());
#endif
}


void AdaptiveSampling::runReductionPass(RenderContext* pRenderContext, const RenderData& renderData)
{
    FALCOR_PROFILE("runReductionPass");

    float4 totalWeight;
    mpParallelReduction->execute<float4>(pRenderContext, mpWeightEstimationFbo->getColorTexture(0), ComputeParallelReduction::Type::Sum, nullptr, mpTotalWeightBuffer, 0);
    mAverageWeight = totalWeight.x / (mFrameDim.x * mFrameDim.y);
}

void AdaptiveSampling::runNormalizeWeightPass(RenderContext* pRenderContext, const RenderData& renderData)
{
    FALCOR_PROFILE("runNormalizeWeightPass");

    Texture::SharedPtr pOutputSampleCount = renderData.getTexture(kOutputSampleCount);

    auto perImageCB = mpNormalizationPass["PerImageCB"];
    perImageCB["gInputWeight"] = mpWeightEstimationFbo->getColorTexture(0);
    perImageCB["gResolution"] = mFrameDim;
    perImageCB["gAverageSampleCountBudget"] = mAverageSampleCountBudget;
    perImageCB["gMinWeight"] = mMinVariance;
    perImageCB["gTotalWeight"] = mpTotalWeightBuffer;
    perImageCB["gMinSamplePerPixel"] = mMinSamplePerPixel;
    perImageCB["gMaxSamplePerPixel"] = mMaxSamplePerPixel;

    mpNormalizationPass->execute(pRenderContext, mpNormalizationFbo);

    pRenderContext->blit(mpNormalizationFbo->getColorTexture(0)->getSRV(), pOutputSampleCount->getRTV());
}

// void AdaptiveSampling::setScene(RenderContext* pRenderContext, const Scene::SharedPtr& pScene)
// {
//     mpScene = pScene;
//     if (mpScene)
//         mpWeightEstimationProgram->addDefines(mpScene->getSceneDefines());
// }


void AdaptiveSampling::renderUI(Gui::Widgets& widget)
{
    bool dirty = false;
    dirty |= widget.checkbox("Enabled", mEnabled);
    dirty |= widget.var("Average Sample Count Budget", mAverageSampleCountBudget, 1.0f, 16.0f);
    dirty |= widget.var("Min Variance", mMinVariance, 0.0f, 1.0f);
    dirty |= widget.var("Max Variance", mMaxVariance, 0.0f, 100.0f);
    dirty |= widget.var("Min Sample Per Pixel", mMinSamplePerPixel, 0u, 16u, 1u);
    dirty |= widget.var("Max Sample Per Pixel", mMaxSamplePerPixel, 1u, 16u, 1u);
    widget.text("Average Weight: " + std::to_string(mAverageWeight));

    if (dirty) mBuffersNeedClear = true;
}
