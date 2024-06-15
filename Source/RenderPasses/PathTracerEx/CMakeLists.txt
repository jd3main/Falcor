add_renderpass(PathTracerEx)

target_sources(PathTracerEx PRIVATE
    ColorType.slang
    GeneratePaths.cs.slang
    GuideData.slang
    LoadShadingData.slang
    NRDHelpers.slang
    Params.slang
    PathState.slang
    PathTracer.slang
    PathTracerEx.cpp
    PathTracerEx.h
    PathTracerNRD.slang
    ReflectTypes.cs.slang
    RepeatResolvePass.cs.slang
    StaticParams.slang
    TracePass.rt.slang
)

target_copy_shaders(PathTracerEx RenderPasses/PathTracerEx)

target_source_group(PathTracerEx "RenderPasses")
