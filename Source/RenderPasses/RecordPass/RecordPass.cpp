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
#include "RecordPass.h"
#include "RenderGraph/RenderPassLibrary.h"
#include <sstream>

const RenderPass::Info RecordPass::kInfo { "RecordPass", "Record average value of textures" };

namespace
{
    const std::string kConstantBufferName = "PerFrameCB";

    // Input buffers
    const std::string kInputBuffer = "Input";

    // Output buffers
    const std::string kOutputBuffer = "Output";

    // Serialized parameters
    const std::string kStatisticsFilePath = "StatistcsFilePath";
    const std::string kReportRunningAverage = "ReportRunningAverage";
    const std::string kRunningAverageSigma = "RunningAverageSigma";
}


float lerp(float a, float b, float r)
{
    return a * (1 - r) + b * r;
}


// Don't remove this. it's required for hot-reload to function properly
extern "C" FALCOR_API_EXPORT const char* getProjDir()
{
    return PROJECT_DIR;
}

extern "C" FALCOR_API_EXPORT void getPasses(Falcor::RenderPassLibrary& lib)
{
    lib.registerPass(RecordPass::kInfo, RecordPass::create);
}

RecordPass::SharedPtr RecordPass::create(RenderContext* pRenderContext, const Dictionary& dict)
{
    return SharedPtr(new RecordPass(dict));
}

RecordPass::RecordPass(const Dictionary& dict)
    : RenderPass(kInfo)
{
    for (const auto& [key, value] : dict)
    {
        if (key == kStatisticsFilePath) mOutputFilePath = value.operator std::filesystem::path();
        else if (key == kReportRunningAverage) mReportRunningAverage = value;
        else if (key == kRunningAverageSigma) mRunningAverageSigma = value;
        else
        {
            logWarning("Unknown field '{}' in RecordPass dictionary.", key);
        }
    }

    // Load/create files (if specified in config).
    openMeasurementsFile();

    mpParallelReduction = ComputeParallelReduction::create();
}

Dictionary RecordPass::getScriptingDictionary()
{
    Dictionary dict;
    dict[kStatisticsFilePath] = mOutputFilePath;
    dict[kReportRunningAverage] = mReportRunningAverage;
    dict[kRunningAverageSigma] = mRunningAverageSigma;
    return dict;
}

RenderPassReflection RecordPass::reflect(const CompileData& compileData)
{
    RenderPassReflection reflector;

    reflector.addInput(kInputBuffer, "Input image").flags(RenderPassReflection::Field::Flags::Optional);

    reflector.addOutput(kOutputBuffer, "Output image").bindFlags(Resource::BindFlags::RenderTarget);

    return reflector;
}

void RecordPass::execute(RenderContext* pRenderContext, const RenderData& renderData)
{
    Texture::SharedPtr pInputTexture = renderData.getTexture(kInputBuffer);
    Texture::SharedPtr pOutputTexture = renderData.getTexture(kOutputBuffer);


    runReductionPasses(pRenderContext, renderData, pInputTexture, mStatistics);

    pRenderContext->blit(pInputTexture->getSRV(), pOutputTexture->getRTV());

    saveMeasurementsToFile();
}

void RecordPass::runReductionPasses(RenderContext* pRenderContext, const RenderData& renderData, Texture::SharedPtr pInputTexture, Statistics &outStatistics)
{
    float4 sum;
    mpParallelReduction->execute(pRenderContext, pInputTexture, ComputeParallelReduction::Type::Sum, &sum);

    const float pixelCountf = static_cast<float>(pInputTexture->getWidth() * pInputTexture->getHeight());
    outStatistics.averageColor = sum / pixelCountf;
    outStatistics.meanAverage = (outStatistics.averageColor.x + outStatistics.averageColor.y + outStatistics.averageColor.z) / 3.f;
    outStatistics.valid = true;

    if (outStatistics.meanRunningAverage < 0)
    {
        // The running error values are invalid. Start them off with the current frame's error.
        outStatistics.runningAverageColor = outStatistics.averageColor;
        outStatistics.meanRunningAverage = outStatistics.meanAverage;
    }
    else
    {
        outStatistics.runningAverageColor = lerp(outStatistics.averageColor, outStatistics.runningAverageColor, mRunningAverageSigma);
        outStatistics.meanRunningAverage = lerp(outStatistics.meanAverage, outStatistics.meanRunningAverage, mRunningAverageSigma);
    }
}

void RecordPass::renderUI(Gui::Widgets& widget)
{
    // std::cerr << "RecordPass::renderUI" << std::endl;
    const auto getFilename = [](const std::filesystem::path& path)
    {
        return path.empty() ? "N/A" : path.filename().string();
    };

    // Create a button for defining the measurements output file.
    if (widget.button("Set output data file"))
    {
        FileDialogFilterVec filters;
        filters.push_back({ "csv", "CSV Files" });
        std::filesystem::path path;
        if (saveFileDialog(filters, path))
        {
            mOutputFilePath = path;
            openMeasurementsFile();
        }
    }

    // Display the filename of the measurement file.
    const std::string outputText = "Output: " + getFilename(mOutputFilePath);
    widget.text(outputText);
    if (!mOutputFilePath.empty())
    {
        widget.tooltip(mOutputFilePath.string());
    }

    // Print numerical average (scalar and RGB).
    if (widget.checkbox("Report running average", mReportRunningAverage) && mReportRunningAverage)
    {
        mStatistics.meanRunningAverage = -1.f;
    }
    widget.tooltip("Exponential moving average, sigma = " + std::to_string(mRunningAverageSigma));
    widget.var("Running Error Sigma", mRunningAverageSigma, 0.f, 1.f, 0.01f, false);
    widget.tooltip("Larger values mean slower response");

    if (mStatistics.valid)
    {
        // Use stream so we can control formatting.
        std::ostringstream oss;
        oss << std::scientific;
        oss << "mean: " <<
        (mReportRunningAverage ? mStatistics.meanRunningAverage : mStatistics.meanAverage) << std::endl;
        oss << "rgb: " <<
        (mReportRunningAverage ? mStatistics.runningAverageColor.r : mStatistics.averageColor.r) << ", " <<
        (mReportRunningAverage ? mStatistics.runningAverageColor.g : mStatistics.averageColor.g) << ", " <<
        (mReportRunningAverage ? mStatistics.runningAverageColor.b : mStatistics.averageColor.b);
        widget.text(oss.str());
    }
    else
    {
        widget.text("N/A");
    }
}

void RecordPass::openMeasurementsFile()
{
    std::cerr << "RecordPass::openMeasurementsFile" << std::endl;
    if (mOutputFilePath.empty()) return;
    if (mOutputFilePath == ".") return;

    mMeasurementsFile = std::ofstream(mOutputFilePath, std::ios::trunc);
    if (!mMeasurementsFile)
    {
        reportError(fmt::format("Failed to open file '{}'.", mOutputFilePath));
        mOutputFilePath.clear();
    }
    else
    {
        std::string name = mStatistics.name;
        mMeasurementsFile << "average_" << name << ",r_" << name << ",g_" << name << ",b_" << name;
        mMeasurementsFile << std::endl;
        mMeasurementsFile << std::scientific;
    }
}

void RecordPass::saveMeasurementsToFile()
{
    std::cerr << "RecordPass::saveMeasurementsToFile" << std::endl;
    if (!mMeasurementsFile) return;

    FALCOR_ASSERT(mStatistics.valid);

    mMeasurementsFile << mStatistics.meanAverage << ",";
    mMeasurementsFile << mStatistics.averageColor.r << ',' << mStatistics.averageColor.g << ',' << mStatistics.averageColor.b;
    mMeasurementsFile << std::endl;
}

