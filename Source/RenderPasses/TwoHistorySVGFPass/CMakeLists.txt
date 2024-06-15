add_renderpass(TwoHistorySVGFPass)

target_sources(TwoHistorySVGFPass PRIVATE
    TwoHistorySVGFPass.cpp
    TwoHistorySVGFPass.h
    Enums.h

    Blending.ps.slang
    TemporalFilter.ps.slang
    Atrous.ps.slang
    FilterMoments.ps.slang
    FilterGradient.ps.slang
)

target_source_group(TwoHistorySVGFPass "RenderPasses")
