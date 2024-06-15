add_renderpass(ErrorMeasurePassEx)

target_sources(ErrorMeasurePassEx PRIVATE
    ErrorMeasurePassEx.cpp
    ErrorMeasurePassEx.h
    ErrorMeasurerEx.cs.slang
)

target_source_group(ErrorMeasurePassEx "RenderPasses")
