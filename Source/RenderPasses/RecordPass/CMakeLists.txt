add_renderpass(RecordPass)

target_sources(RecordPass PRIVATE
    RecordPass.cpp
    RecordPass.h
)

target_source_group(RecordPass "RenderPasses")
