add_renderpass(AdaptiveSampling)

target_sources(AdaptiveSampling PRIVATE
    AdaptiveSampling.cpp
    AdaptiveSampling.h
    Enums.h

    WeightEstimation.cs.slang
    Normalization.cs.slang
)

target_source_group(AdaptiveSampling "RenderPasses")
