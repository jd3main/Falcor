add_renderpass(MySVGFPass)

target_sources(MySVGFPass PRIVATE
    MySVGFPass.cpp
    MySVGFPass.h
    MySVGFReproject.ps.slang
)

target_source_group(MySVGFPass "RenderPasses")
