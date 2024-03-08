add_renderpass(AdaptiveSampling)

target_sources(AdaptiveSampling PRIVATE
    AdaptiveSampling.cpp
    AdaptiveSampling.h
    Enums.h
    Configs.h

    WeightEstimation.ps.slang
    Normalization.ps.slang
)

target_source_group(AdaptiveSampling "RenderPasses")
