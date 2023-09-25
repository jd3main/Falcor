add_renderpass(TwoHistorySVGFPass)

target_sources(TwoHistorySVGFPass PRIVATE
    TwoHistorySVGFPass.cpp
    TwoHistorySVGFPass.h
    TwoHistorySVGFReproject.ps.slang
)

target_source_group(TwoHistorySVGFPass "RenderPasses")
