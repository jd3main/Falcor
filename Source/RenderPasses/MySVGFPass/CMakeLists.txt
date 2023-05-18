add_renderpass(MySVGFPass)

target_sources(MySVGFPass PRIVATE
    MySVGFPass.cpp
    MySVGFPass.h
)

target_source_group(MySVGFPass "RenderPasses")
