add_renderpass(DynamicWeightingSVGF)

target_sources(DynamicWeightingSVGF PRIVATE
    DynamicWeightingSVGF.cpp
    DynamicWeightingSVGF.h

    Common.slang

    DynamicWeighting.ps.slang
    Reprojection.ps.slang
    TemporalFilter.ps.slang
    ReflectTypes.cs.slang
)

target_source_group(DynamicWeightingSVGF "RenderPasses")
