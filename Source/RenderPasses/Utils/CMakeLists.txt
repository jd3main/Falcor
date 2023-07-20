add_renderpass(Utils)

target_sources(Utils PRIVATE
    Utils.cpp

    Composite/Composite.cpp
    Composite/Composite.cs.slang
    Composite/Composite.h
    Composite/CompositeMode.slangh

    CountToColor/CountToColor.cpp
    CountToColor/CountToColor.h
    CountToColor/CountToColor.cs.slang

    GaussianBlur/GaussianBlur.cpp
    GaussianBlur/GaussianBlur.h
    GaussianBlur/GaussianBlur.ps.slang

    SharedBuffer/SharedBuffer.cpp
    SharedBuffer/SharedBuffer.h
)

target_copy_shaders(Utils RenderPasses/Utils)

target_compile_definitions(Utils PRIVATE BUILD_GAUSSIAN_PASS)

target_source_group(Utils "RenderPasses")
