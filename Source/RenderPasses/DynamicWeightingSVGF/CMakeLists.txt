add_renderpass(DynamicWeightingSVGF)

target_sources(DynamicWeightingSVGF PRIVATE
    DynamicWeightingSVGF.cpp
    DynamicWeightingSVGF.h
    Enums.h
    Configs.h

    DynamicWeighting.ps.slang
    TemporalFilter.ps.slang
    Atrous.ps.slang
)

target_source_group(DynamicWeightingSVGF "RenderPasses")
