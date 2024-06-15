add_renderpass(ReprojectionPass)

target_sources(ReprojectionPass PRIVATE
    ReprojectionPass.cpp
    ReprojectionPass.h

    Reprojection.ps.slang
    ReflectTypes.cs.slang
    ReprojectionStruct.slang
)

target_source_group(ReprojectionPass "RenderPasses")
