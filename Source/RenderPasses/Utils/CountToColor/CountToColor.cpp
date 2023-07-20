#include "CountToColor.h"
#include "RenderGraph/RenderPassLibrary.h"
#include "RenderGraph/RenderPassHelpers.h"

const RenderPass::Info CountToColor::kInfo { "CountToColor", "Vsualize Count" };

namespace
{
    const char kShaderFile[] = "RenderPasses/Utils/CountToColor/CountToColor.cs.slang";

    const char kMaxValue[] = "MaxValue";

    const char kInputCount[] = "Count";
    const char kOutputColor[] = "Color";
}


CountToColor::CountToColor(const Dictionary& dict)
    : RenderPass(kInfo)
{
    for (const auto& [key, value] : dict)
    {
        if (key == kMaxValue) mMaxValue = value;
        else
        {
            logWarning("Unknown field '{}' in ErrorMeasurePass dictionary.", key);
        }
    }
}

CountToColor::SharedPtr CountToColor::create(RenderContext* pRenderContext, const Dictionary& dict)
{
    return SharedPtr(new CountToColor(dict));
}

Dictionary CountToColor::getScriptingDictionary()
{
    Dictionary dict;
    dict[kMaxValue] = mMaxValue;
    return dict;
}

RenderPassReflection CountToColor::reflect(const CompileData& compileData)
{
    // Define the required resources here
    RenderPassReflection reflector;
    const uint2 sz = compileData.defaultTexDims;

    reflector.addInput(kInputCount, "Count")
        .bindFlags(ResourceBindFlags::ShaderResource);

    reflector.addOutput(kOutputColor, "Color")
        .bindFlags(ResourceBindFlags::RenderTarget | ResourceBindFlags::UnorderedAccess | ResourceBindFlags::ShaderResource)
        .format(ResourceFormat::RGBA32Float)
        .texture2D(sz.x, sz.y);
    return reflector;
}

void CountToColor::execute(RenderContext* pRenderContext, const RenderData& renderData)
{
    // renderData holds the requested resources
    auto& pInputCount = renderData.getTexture(kInputCount);
    auto& pOutputColor = renderData.getTexture(kOutputColor);
    FALCOR_ASSERT(pInputCount && pOutputColor);

    mFrameDim = { pInputCount->getWidth(), pInputCount->getHeight() };

    ResourceFormat format = pInputCount->getFormat();

    if (mpProgram == nullptr)
    {
        Program::DefineList defines;
        if (format == ResourceFormat::R8Uint)
            defines.add("_INPUT_FORMAT", "INPUT_FORMAT_R8UINT");
        else if (format == ResourceFormat::R16Uint)
            defines.add("_INPUT_FORMAT", "INPUT_FORMAT_R16UINT");
        else if (format == ResourceFormat::R32Uint)
            defines.add("_INPUT_FORMAT", "INPUT_FORMAT_R32UINT");

        mpProgram = ComputePass::create(kShaderFile, "main", defines);
    }


    // Set shader parameters
    mpProgram["CB"]["gResolution"] = uint2(pInputCount->getWidth(), pInputCount->getHeight());
    mpProgram["CB"]["gMaxValue"] = mMaxValue;
    mpProgram["gInputCount"] = pInputCount;
    mpProgram["gOutputColor"] = pOutputColor;

    mpProgram->execute(pRenderContext, mFrameDim.x, mFrameDim.y);
}

void CountToColor::renderUI(Gui::Widgets& widget)
{
    widget.var("Max Value", mMaxValue);
}
