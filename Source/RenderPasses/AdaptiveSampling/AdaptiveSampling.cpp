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

#include "RenderGraph/RenderPassLibrary.h"
#include "RenderGraph/RenderPassHelpers.h"

const RenderPass::Info AdaptiveSampling::kInfo { "AdaptiveSampling", "Insert pass description here." };

namespace
{
    const char kWeightEstimationShaderFile[] = "RenderPasses/AdaptiveSampling/WeightEstimation.cs.slang";
    const char kNormalizationShaderFile[] = "RenderPasses/AdaptiveSampling/Normalization.cs.slang";
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
    const char kOutputDensityWeight[] = "densityWeight";
    const ChannelList kOutputChannels =
    {
        { kOutputSampleCount,   "_", "The number of samples per pixel",     false, ResourceFormat::R8Uint },
        { kOutputDensityWeight, "_", "Unnormalized density",                false, ResourceFormat::R32Float },
    };

    // Serialized parameters
    const char kEnabled[] = "Enabled";
    const char kAverageSampleCountBudget[] = "AverageSampleCountBudget";
    const char kMinVariance[] = "MinVariance";
    const char kMaxVariance[] = "MaxVariance";
    const char kMinSamplePerPixel[] = "MinSamplePerPixel";
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
    addRenderPassInputs(reflector, kInputChannels);
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
    allocateResources();

    {
        Program::DefineList defines;

        mpWeightEstimationProgram = ComputeProgram::createFromFile(kWeightEstimationShaderFile, "main", defines, Shader::CompilerFlags::TreatWarningsAsErrors);
        mpWeightEstimationVars = ComputeVars::create(mpWeightEstimationProgram->getReflector());
        mpWeightEstimationState = ComputeState::create();

        mpParallelReduction = ComputeParallelReduction::create();

        mpNormalizationProgram = ComputeProgram::createFromFile(kNormalizationShaderFile, "main", defines, Shader::CompilerFlags::TreatWarningsAsErrors);
        mpNormalizationVars = ComputeVars::create(mpNormalizationProgram->getReflector());
        mpNormalizationState = ComputeState::create();
    }

    mBuffersNeedClear = true;
}

void AdaptiveSampling::execute(RenderContext* pRenderContext, const RenderData& renderData)
{
    // Check if the output texture size has changed
    uint2 resolution = renderData.getDefaultTextureDims();
    if (resolution != mFrameDim)
    {
        mFrameDim = resolution;
        allocateResources();
    }

    // Compile shaders
    if (!mpWeightEstimationProgram)
    {
        Program::DefineList defines;

        mpWeightEstimationProgram = ComputeProgram::createFromFile(kWeightEstimationShaderFile, "main", defines, Shader::CompilerFlags::TreatWarningsAsErrors);
        mpWeightEstimationVars = ComputeVars::create(mpWeightEstimationProgram->getReflector());
        mpWeightEstimationState = ComputeState::create();

        mpParallelReduction = ComputeParallelReduction::create();

        mpNormalizationProgram = ComputeProgram::createFromFile(kNormalizationShaderFile, "main", defines, Shader::CompilerFlags::TreatWarningsAsErrors);
        mpNormalizationVars = ComputeVars::create(mpNormalizationProgram->getReflector());
        mpNormalizationState = ComputeState::create();
    }

    if (mBuffersNeedClear)
    {
        clearBuffers(pRenderContext, renderData);
        mBuffersNeedClear = false;
    }

    if (!mEnabled)
    {
        runNormalizeWeightPass(pRenderContext, renderData);
        return;
    }

    runWeightEstimationPass(pRenderContext, renderData);
    runReductionPass(pRenderContext, renderData);
    runNormalizeWeightPass(pRenderContext, renderData);
}

void AdaptiveSampling::allocateResources()
{
    mpDensityWeight = Texture::create2D(mFrameDim.x, mFrameDim.y, ResourceFormat::RGBA32Float, 1, 1, nullptr,
        ResourceBindFlags::UnorderedAccess | ResourceBindFlags::ShaderResource | ResourceBindFlags::RenderTarget);
}

void AdaptiveSampling::clearBuffers(RenderContext* pRenderContext, const RenderData& renderData)
{
    pRenderContext->clearTexture(mpDensityWeight.get(), float4(0.0f, 0.0f, 0.0f, 0.0f));
    mBuffersNeedClear = false;
}

void AdaptiveSampling::runWeightEstimationPass(RenderContext* pRenderContext, const RenderData& renderData)
{
    Texture::SharedPtr pInputVariance = renderData.getTexture(kInputVariance);
    Texture::SharedPtr pInputHistoryLength = renderData.getTexture(kInputHistoryLength);
    Buffer::SharedPtr pInputBufferReprojection = renderData.getResource(kInputBufferReprojection)->asBuffer();

    Texture::SharedPtr pOutputDensityWeight = renderData.getTexture(kOutputDensityWeight);

    FALCOR_ASSERT(pInputBufferReprojection);

    // Set shader parameters
    auto perImageCB = mpWeightEstimationVars["PerImageCB"];
    perImageCB["gInputReprojection"] = pInputBufferReprojection;
    perImageCB["gInputVariance"] = pInputVariance;
    perImageCB["gInputHistoryLength"] = pInputHistoryLength;
    perImageCB["gOutputSampleDensityWeight"] = mpDensityWeight;
    perImageCB["gResolution"] = mFrameDim;
    perImageCB["gMinVariance"] = mMinVariance;
    perImageCB["gMaxVariance"] = mMaxVariance;

    uint3 numGroups = div_round_up(uint3(mFrameDim.x, mFrameDim.y, 1u), mpWeightEstimationProgram->getReflector()->getThreadGroupSize());

    mpWeightEstimationState->setProgram(mpWeightEstimationProgram);
    pRenderContext->dispatch(mpWeightEstimationState.get(), mpWeightEstimationVars.get(), numGroups);

    pRenderContext->blit(mpDensityWeight->getSRV(), pOutputDensityWeight->getRTV());
}


void AdaptiveSampling::runReductionPass(RenderContext* pRenderContext, const RenderData& renderData)
{
    float4 totalWeight;
    mpParallelReduction->execute(pRenderContext, mpDensityWeight, ComputeParallelReduction::Type::Sum, &totalWeight);

    const float pixelCountf = static_cast<float>(mpDensityWeight->getWidth() * mpDensityWeight->getHeight());
    mAverageWeight = totalWeight.x / pixelCountf;
}

void AdaptiveSampling::runNormalizeWeightPass(RenderContext* pRenderContext, const RenderData& renderData)
{
    Texture::SharedPtr pOutputSampleCount = renderData.getTexture(kOutputSampleCount);

    float scale = (mAverageWeight - mMinVariance) / (mAverageSampleCountBudget - mMinSamplePerPixel);

    auto perImageCB = mpNormalizationVars["PerImageCB"];
    perImageCB["gResolution"] = mFrameDim;
    perImageCB["gMinSamplePerPixel"] = mMinSamplePerPixel;
    perImageCB["gMinVariance"] = mMinVariance;
    perImageCB["gScale"] = mEnabled ? scale : 0.0f;
    mpNormalizationVars["gInputDensityWeight"] = mpDensityWeight;
    mpNormalizationVars["gOutputSampleCount"] = pOutputSampleCount;


    uint3 numGroups = div_round_up(uint3(mFrameDim.x, mFrameDim.y, 1u), mpNormalizationProgram->getReflector()->getThreadGroupSize());

    mpNormalizationState->setProgram(mpNormalizationProgram);
    pRenderContext->dispatch(mpNormalizationState.get(), mpNormalizationVars.get(), numGroups);
}

// void AdaptiveSampling::setScene(RenderContext* pRenderContext, const Scene::SharedPtr& pScene)
// {
//     mpScene = pScene;
//     if (mpScene)
//         mpWeightEstimationProgram->addDefines(mpScene->getSceneDefines());
// }


void AdaptiveSampling::renderUI(Gui::Widgets& widget)
{
    widget.checkbox("Enabled", mEnabled);
    widget.var("Min Variance", mMinVariance, 0.0f, 1.0f);
    widget.var("Max Variance", mMaxVariance, 0.0f, 100.0f);
    widget.var("Average Sample Count Budget", mAverageSampleCountBudget, 1.0f, 16.0f);
    widget.text(std::string("Current average weight: ") + std::to_string(mAverageWeight));
}
