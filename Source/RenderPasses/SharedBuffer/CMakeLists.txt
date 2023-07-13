add_renderpass(SharedBuffer)

target_sources(SharedBuffer PRIVATE
    SharedBuffer.cpp
    SharedBuffer.h
)

target_source_group(SharedBuffer "RenderPasses")
