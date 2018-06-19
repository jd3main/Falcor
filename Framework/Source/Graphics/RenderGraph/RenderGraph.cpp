/***************************************************************************
# Copyright (c) 2018, NVIDIA CORPORATION. All rights reserved.
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
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ``AS IS'' AND ANY
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
***************************************************************************/
#include "Framework.h"
#include "RenderGraph.h"
#include "API/FBO.h"

namespace Falcor
{
    RenderGraph::SharedPtr RenderGraph::create()
    {
        try
        {
            return SharedPtr(new RenderGraph);
        }
        catch (const std::exception&)
        {
            return nullptr;
        }
    }

    RenderGraph::RenderGraph() = default;

    size_t RenderGraph::getPassIndex(const std::string& name) const
    {
        auto& it = mNameToIndex.find(name);
        return (it == mNameToIndex.end()) ? kInvalidIndex : it->second;
    }

    void RenderGraph::setScene(const std::shared_ptr<Scene>& pScene)
    {
        mpScene = pScene;
        for (auto& pPass : mpPasses)
        {
            pPass->setScene(pScene);
        }
    }

    bool RenderGraph::addRenderPass(const RenderPass::SharedPtr& pPass, const std::string& passName)
    {
        assert(pPass);
        if (getPassIndex(passName) != kInvalidIndex)
        {
            logWarning("Pass named `" + passName + "' already exists. Pass names must be unique");
            return false;
        }

        pPass->setScene(mpScene);
        mNameToIndex[passName] = mpPasses.size();
        mpPasses.push_back(pPass);
        mRecompile = true;
        return true;
    }

    void RenderGraph::removeRenderPass(const std::string& name)
    {
        size_t index = getPassIndex(name);
        if (index == kInvalidIndex)
        {
            logWarning("Can't remove pass `" + name + "`. Pass doesn't exist");
            return;
        }

        // Update the indices
        for (auto& i : mNameToIndex)
        {
            if (i.second > index) i.second--;
        }

        mNameToIndex.erase(name);
        // Remove all the edges associated with this pass
        RenderPass* pPass = mpPasses[index].get();
        for (size_t i = 0 ; i < mEdges.size() ;)
        {
            if (mEdges[i].pSrc == pPass || mEdges[i].pDst == pPass)
            {
                mEdges.erase(mEdges.begin() + i);
            }
            else
            {
                i++;
            }
        }

        mpPasses.erase(mpPasses.begin() + index);
        mRecompile = true;
    }

    const RenderPass::SharedPtr& RenderGraph::getRenderPass(const std::string& name) const
    {
        size_t index = getPassIndex(name);
        if (index == kInvalidIndex)
        {
            static RenderPass::SharedPtr pNull;
            logWarning("RenderGraph::getRenderPass() - can't find a pass named `" + name + "`");
            return pNull;
        }
        return mpPasses[index];
    }
    
    using str_pair = std::pair<std::string, std::string>;
    
    template<bool input>
    static bool checkRenderPassIoExist(const RenderPass* pPass, const std::string& name)
    {
        const auto& ioVec = input ? pPass->getRenderPassData().inputs : pPass->getRenderPassData().outputs;
        for (const auto& f : ioVec)
        {
            if (f.name == name) return true;
        }
        return false;
    }

    static bool parseFieldName(const std::string& fullname, str_pair& strPair)
    {
        if (std::count(fullname.begin(), fullname.end(), '.') != 1)
        {
            logWarning("RenderGraph node field string is incorrect. Must be in the form of `PassName.FieldName` but got `" + fullname + "`");
            return false;
        }

        size_t dot = fullname.find_first_of('.');
        strPair.first = fullname.substr(0, dot);
        strPair.second = fullname.substr(dot + 1);
        return true;
    }

    template<bool input>
    static RenderPass* getRenderPassAndField(const RenderGraph* pGraph, const std::string& fullname, const std::string& errorPrefix, std::string& field)
    {
        str_pair strPair;
        if (parseFieldName(fullname, strPair) == false) return false;

        RenderPass* pPass = pGraph->getRenderPass(strPair.first).get();
        if (!pPass)
        {
            logWarning(errorPrefix + " - can't find render-pass named '" + strPair.first + "'");
            return nullptr;
        }

        if (checkRenderPassIoExist<input>(pPass, strPair.second) == false)
        {
            logWarning(errorPrefix + "- can't find field named `" + strPair.second + "` in render-pass `" + strPair.first + "`");
            return nullptr;
        }
        field = strPair.second;
        return pPass;
    }

    bool RenderGraph::addEdge(const std::string& src, const std::string& dst)
    {
        Edge newEdge;
        newEdge.pSrc = getRenderPassAndField<false>(this, src, "Invalid src string in RenderGraph::addEdge()", newEdge.srcField);
        newEdge.pDst = getRenderPassAndField<true>(this, dst, "Invalid dst string in RenderGraph::addEdge()", newEdge.dstField);

        if (newEdge.pSrc == nullptr || newEdge.pDst == nullptr) return false;

        // Check that the dst field is not already initialized
        for (const Edge& e : mEdges)
        {
            if (newEdge.pDst == e.pDst && newEdge.dstField == e.dstField)
            {
                logWarning("RenderGraph::addEdge() - destination `" + dst + "` is already initialized. Please remove the existing connection before trying to add an edge");
                return false;
            }
        }
 
        mEdges.push_back(newEdge);
        mRecompile = true;
        return true;
    }

    void RenderGraph::RemoveEdge(const std::string& src, const std::string& dst)
    {
        // I need to find a faster way to remove connections
        Edge newEdge;
        newEdge.pSrc = getRenderPassAndField<false>(this, src, "Invalid src string in RenderGraph::removeEdge()", newEdge.srcField);
        newEdge.pDst = getRenderPassAndField<true>(this, dst, "Invalid dst string in RenderGraph::removeEdge()", newEdge.dstField);

        auto& edgeIt = std::find(mEdges.begin(), mEdges.end(), newEdge);
        if (edgeIt == mEdges.end())
        {
            logWarning("RenderGraph::removeEdge() -  Unable to find edge to remove. No such connection exists within this graph.");
        }

        mEdges.erase(edgeIt, edgeIt + 1);

        mRecompile = true;
    }

    bool RenderGraph::isValid(std::string& log) const
    {
        bool valid = true;
        size_t logSize = log.size();
        for (const auto& pPass : mpPasses)
        {
            if (pPass->isValid(log) == false)
            {
                valid = false;
                if (log.size() != logSize && log.back() != '\n')
                {
                    log += '\n';
                    logSize = log.size();
                }
            }
        }
        return valid;
    }

    Texture::SharedPtr RenderGraph::createTextureForPass(const RenderPass::PassData::Field& field)
    {
        uint32_t width = field.width ? field.width : mSwapChainData.width;
        uint32_t height = field.height ? field.height : mSwapChainData.height;
        uint32_t depth = field.depth ? field.depth : 1;
        uint32_t sampleCount = field.sampleCount ? field.sampleCount : 1;
        ResourceFormat format = field.format == ResourceFormat::Unknown ? mSwapChainData.colorFormat : field.format;
        Texture::SharedPtr pTexture;

        if (depth > 1)
        {
            assert(sampleCount == 1);
            pTexture = Texture::create3D(width, height, depth, format, 1, nullptr, field.bindFlags | Resource::BindFlags::ShaderResource);
        }
        else if (height > 1 || sampleCount > 1)
        {
            if (sampleCount > 1)
            {
                pTexture = Texture::create2DMS(width, height, format, sampleCount, 1, field.bindFlags | Resource::BindFlags::ShaderResource);
            }
            else
            {
                pTexture = Texture::create2D(width, height, format, 1, 1, nullptr, field.bindFlags | Resource::BindFlags::ShaderResource);
            }
        }
        else
        {
            pTexture = Texture::create1D(width, format, 1, 1, nullptr, field.bindFlags | Resource::BindFlags::ShaderResource);
        }

        return pTexture;
    }

    void RenderGraph::compile()
    {
        if(mRecompile)
        {   
            // Allocate outputs
            for (const auto& e : mEdges)
            {
                const RenderPass::PassData& passData = e.pSrc->getRenderPassData();
                // Find the input
                bool found = false;
                for (const auto& src : passData.outputs)
                {
                    if(src.required || (src.name == e.srcField))
                    {
                        Texture::SharedPtr pTexture = createTextureForPass(src);
                        e.pSrc->setOutput(src.name, pTexture);

                        if (src.name == e.srcField)
                        {
                            e.pDst->setInput(e.dstField, pTexture);
                            found = true;
                        }
                    }
                }
                assert(found);
            }
        }
        mRecompile = false;
    }

    void RenderGraph::execute(RenderContext* pContext)
    {
        compile();

        std::string log;
        if (!isValid(log))
        {
            logWarning("Failed to compile RenderGraph\n" + log +"Ignoreing RenderGraph::execute() call");
            return;
        }

        for (auto& pPass : mpPasses)
        {
            pPass->execute(pContext);
        }
    }

    bool RenderGraph::setInput(const std::string& name, const std::shared_ptr<Resource>& pResource)
    {
        // GRAPH_TODO 
        std::string field;
        RenderPass* pPass = getRenderPassAndField<true>(this, name, "RenderGraph::setInput()", field);
        if (pPass == nullptr) return false;
        return pPass->setInput(field, pResource);
    }

    bool RenderGraph::setOutput(const std::string& name, const std::shared_ptr<Resource>& pResource)
    {
        std::string field;
        RenderPass* pPass = getRenderPassAndField<false>(this, name, "RenderGraph::setOutput()", field);
        if (pPass == nullptr) return false;
        if (pPass->setOutput(field, pResource) == false) return false;
        markGraphOutput(name);
        return true;
    }

    void RenderGraph::markGraphOutput(const std::string& name)
    {
        GraphOut newOut;
        newOut.pPass = getRenderPassAndField<false>(this, name, "RenderGraph::markGraphOutput()", newOut.field);
        if (newOut.pPass == nullptr) return;

        // Check that this is not already marked
        for (const auto& o : mOutputs)
        {
            if (newOut.pPass == o.pPass && newOut.field == o.field) return;
        }

        mOutputs.push_back(newOut);
        mRecompile = true;
    }

    void RenderGraph::unmarkGraphOutput(const std::string& name)
    {
        GraphOut removeMe;
        removeMe.pPass = getRenderPassAndField<false>(this, name, "RenderGraph::unmarkGraphOutput()", removeMe.field);
        if (removeMe.pPass == nullptr) return;

        for (size_t i = 0 ; i < mOutputs.size() ; i++)
        {
            if (mOutputs[i].pPass == removeMe.pPass && mOutputs[i].field == removeMe.field)
            {
                mOutputs.erase(mOutputs.begin() + i);
                mRecompile = true;
                return;
            }
        }
    }

    const Resource::SharedPtr RenderGraph::getOutput(const std::string& name)
    {
        static const Resource::SharedPtr pNull;
        std::string field;
        RenderPass* pPass = getRenderPassAndField<false>(this, name, "RenderGraph::getOutput()", field);
        
        return pPass ? pPass->getOutput(field) : pNull;
    }

    void RenderGraph::renderUI(Gui* pGui)
    {
        // To get some data displaying with what we want, start with raw IMGUI
        // TODO -- implement what we need into the actual gui class
        
        for (const auto& renderGraphPass : mpPasses)
        {
            renderGraphPass->renderUI(pGui);
        }

        // Connect the graph nodes for each of the edges
        for (const auto& renderGraphEdges : mEdges)
        {
        }
    }

    void RenderGraph::onResizeSwapChain(SampleCallbacks* pSample, uint32_t width, uint32_t height)
    {
        // Store the back-buffer values
        const Fbo* pFbo = pSample->getCurrentFbo().get();
        const Texture* pColor = pFbo->getColorTexture(0).get();
        const Texture* pDepth = pFbo->getDepthStencilTexture().get();
        assert(pColor && pDepth);

        // If the back-buffer values changed, recompile
        mRecompile = mRecompile || (mSwapChainData.colorFormat != pColor->getFormat());
        mRecompile = mRecompile || (mSwapChainData.depthFormat != pDepth->getFormat());
        mRecompile = mRecompile || (mSwapChainData.width != width);
        mRecompile = mRecompile || (mSwapChainData.height != height);

        // Store the values
        mSwapChainData.colorFormat = pColor->getFormat();
        mSwapChainData.depthFormat = pDepth->getFormat();
        mSwapChainData.width = width;
        mSwapChainData.height = height;

        // Invoke the passes' callback
        for (auto& pPass : mpPasses)
        {
            pPass->onResizeSwapChain(pSample, width, height);
        }
    }
}