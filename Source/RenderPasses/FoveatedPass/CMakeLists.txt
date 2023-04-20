add_renderpass(FoveatedPass)

target_sources(FoveatedPass PRIVATE
    FoveatedPass.cpp
    FoveatedPass.h
    FoveatedPass.3d.slang
)
target_copy_shaders(FoveatedPass RenderPasses/FoveatedPass)

target_source_group(FoveatedPass "RenderPasses")
