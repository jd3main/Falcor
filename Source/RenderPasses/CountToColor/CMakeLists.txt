add_renderpass(CountToColor)

target_sources(CountToColor PRIVATE
    CountToColor.cpp
    CountToColor.h
    CountToColor.cs.slang
)

target_source_group(CountToColor "RenderPasses")
