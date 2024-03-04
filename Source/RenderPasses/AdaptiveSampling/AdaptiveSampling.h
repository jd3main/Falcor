/***************************************************************************
 # Copyright (c) 2015-21, NVIDIA CORPORATION. All rights reserved.
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
#pragma once
#include "Falcor.h"
#include "RenderGraph/BasePasses/FullScreenPass.h"
#include "Utils/Algorithm/ComputeParallelReduction.h"

using namespace Falcor;

class AdaptiveSampling : public RenderPass
{
public:
    using SharedPtr = std::shared_ptr<AdaptiveSampling>;

    static const Info kInfo;

    /** Create a new render pass object.
        \param[in] pRenderContext The render context.
        \param[in] dict Dictionary of serialized parameters.
        \return A new object, or an exception is thrown if creation failed.
    */
    static SharedPtr create(RenderContext* pRenderContext = nullptr, const Dictionary& dict = {});

    virtual Dictionary getScriptingDictionary() override;
    virtual RenderPassReflection reflect(const CompileData& compileData) override;
    virtual void compile(RenderContext* pRenderContext, const CompileData& compileData) override;
    virtual void execute(RenderContext* pRenderContext, const RenderData& renderData) override;
    virtual void renderUI(Gui::Widgets& widget) override;
    virtual void setScene(RenderContext* pRenderContext, const Scene::SharedPtr& pScene) override {};
    virtual bool onMouseEvent(const MouseEvent& mouseEvent) override { return false; }
    virtual bool onKeyEvent(const KeyboardEvent& keyEvent) override { return false; }

private:
    AdaptiveSampling(const Dictionary& dict);

    void allocateResources();
    void clearBuffers(RenderContext* pRenderContext, const RenderData& renderData);
    void runWeightEstimationPass(RenderContext* pRenderContext, const RenderData& renderData);
    void runReductionPass(RenderContext* pRenderContext, const RenderData& renderData);
    void runNormalizeWeightPass(RenderContext* pRenderContext, const RenderData& renderData);

    uint32_t getReprojectStructSize();

    // Compute programs and state
    ComputeProgram::SharedPtr mpWeightEstimationProgram;
    ComputeVars::SharedPtr mpWeightEstimationVars;
    ComputeState::SharedPtr mpWeightEstimationState;

    ComputeProgram::SharedPtr mpNormalizationProgram;
    ComputeVars::SharedPtr mpNormalizationVars;
    ComputeState::SharedPtr mpNormalizationState;

    ComputePass::SharedPtr mpReflectTypes;  ///< Helper for reflecting structured buffer types.

    // Internal buffers
    Texture::SharedPtr mpDensityWeight = nullptr;

    // Internal states
    uint2 mFrameDim = uint2(0);
    Scene::SharedPtr mpScene = nullptr;
    ComputeParallelReduction::SharedPtr mpParallelReduction;
    float mAverageWeight = 0.0f;
    Buffer::SharedPtr mpTotalWeightBuffer;
    bool mBuffersNeedClear = true;

    // Serialized parameters
    bool mEnabled = true;
    float mAverageSampleCountBudget = 2.0f;
    float mMinVariance = 0.01f;
    float mMaxVariance = 10.0f;
    float mMinSamplePerPixel = 1.0f;
};
