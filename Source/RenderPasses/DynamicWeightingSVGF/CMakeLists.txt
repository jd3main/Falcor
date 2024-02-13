add_renderpass(DynamicWeightingSVGF)

target_sources(DynamicWeightingSVGF PRIVATE
    DynamicWeightingSVGF.cpp
    DynamicWeightingSVGF.h
    Enums.h

    Common.slang

    DynamicWeighting.ps.slang
    Reprojection.ps.slang
    TemporalFilter.ps.slang
    ReflectTypes.cs.slang
    Atrous.ps.slang
)

target_source_group(DynamicWeightingSVGF "RenderPasses")
