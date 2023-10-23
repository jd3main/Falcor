add_renderpass(DynamicWeightingSVGF)

target_sources(DynamicWeightingSVGF PRIVATE
    DynamicWeightingSVGF.cpp
    DynamicWeightingSVGF.h
    DynamicWeightingSVGFReproject.ps.slang
)

target_source_group(DynamicWeightingSVGF "RenderPasses")
