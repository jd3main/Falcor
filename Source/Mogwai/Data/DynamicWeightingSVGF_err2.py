from falcor import *
from pathlib import *

def render_graph_g():
    g = RenderGraph('g')
    loadRenderPassLibrary('DLSSPass.dll')
    loadRenderPassLibrary('AccumulatePass.dll')
    loadRenderPassLibrary('BSDFViewer.dll')
    loadRenderPassLibrary('Antialiasing.dll')
    loadRenderPassLibrary('BlitPass.dll')
    loadRenderPassLibrary('CSM.dll')
    loadRenderPassLibrary('DebugPasses.dll')
    loadRenderPassLibrary('PathTracer.dll')
    loadRenderPassLibrary('DepthPass.dll')
    loadRenderPassLibrary('DynamicWeightingSVGF.dll')
    loadRenderPassLibrary('ErrorMeasurePass.dll')
    loadRenderPassLibrary('SimplePostFX.dll')
    loadRenderPassLibrary('FLIPPass.dll')
    loadRenderPassLibrary('ForwardLightingPass.dll')
    loadRenderPassLibrary('FoveatedPass.dll')
    loadRenderPassLibrary('GBuffer.dll')
    loadRenderPassLibrary('WhittedRayTracer.dll')
    loadRenderPassLibrary('ImageLoader.dll')
    loadRenderPassLibrary('MinimalPathTracer.dll')
    loadRenderPassLibrary('ModulateIllumination.dll')
    loadRenderPassLibrary('MySVGFPass.dll')
    loadRenderPassLibrary('NRDPass.dll')
    loadRenderPassLibrary('PixelInspectorPass.dll')
    loadRenderPassLibrary('RecordPass.dll')
    loadRenderPassLibrary('SkyBox.dll')
    loadRenderPassLibrary('RTXDIPass.dll')
    loadRenderPassLibrary('RTXGIPass.dll')
    loadRenderPassLibrary('SceneDebugger.dll')
    loadRenderPassLibrary('SDFEditor.dll')
    loadRenderPassLibrary('SSAO.dll')
    loadRenderPassLibrary('SVGFPass.dll')
    loadRenderPassLibrary('TemporalDelayPass.dll')
    loadRenderPassLibrary('TestPasses.dll')
    loadRenderPassLibrary('ToneMapper.dll')
    loadRenderPassLibrary('TwoHistorySVGFPass.dll')
    loadRenderPassLibrary('Utils.dll')
    GBufferRaster = createPass('GBufferRaster', {'outputSize': IOSize.Default, 'samplePattern': SamplePattern.Center, 'sampleCount': 16, 'useAlphaTest': True, 'adjustShadingNormals': True, 'forceCullMode': False, 'cull': CullMode.CullBack})
    g.addPass(GBufferRaster, 'GBufferRaster')
    FoveatedPass = createPass('FoveatedPass', {'shape': 2, 'foveaInputType': 1, 'useHistory': False, 'alpha': 0.05000000074505806, 'foveaRadius': 200.0, 'foveaSampleCount': 8.0, 'periphSampleCount': 1.0, 'uniformSampleCount': 1.0, 'foveaMoveRadius': 300.0, 'foveaMoveFreq': 0.5, 'foveaMoveDirection': 0, 'useRealTime': False})
    g.addPass(FoveatedPass, 'FoveatedPass')
    Composite = createPass('Composite', {'mode': CompositeMode.Add, 'scaleA': 0.5, 'scaleB': 0.5, 'outputFormat': ResourceFormat.RGBA32Float})
    g.addPass(Composite, 'Composite')
    PathTracer = createPass('PathTracer', {'samplesPerPixel': 1, 'maxSurfaceBounces': 10, 'maxDiffuseBounces': 3, 'maxSpecularBounces': 3, 'maxTransmissionBounces': 10, 'sampleGenerator': 0, 'useBSDFSampling': True, 'useRussianRoulette': False, 'useNEE': True, 'useMIS': True, 'misHeuristic': MISHeuristic.Balance, 'misPowerExponent': 2.0, 'emissiveSampler': EmissiveLightSamplerType.LightBVH, 'lightBVHOptions': LightBVHSamplerOptions(buildOptions=LightBVHBuilderOptions(splitHeuristicSelection=SplitHeuristic.BinnedSAOH, maxTriangleCountPerLeaf=10, binCount=16, volumeEpsilon=0.0010000000474974513, splitAlongLargest=False, useVolumeOverSA=False, useLeafCreationCost=True, createLeavesASAP=True, allowRefitting=True, usePreintegration=True, useLightingCones=True), useBoundingCone=True, useLightingCone=True, disableNodeFlux=False, useUniformTriangleSampling=True, solidAngleBoundMethod=SolidAngleBoundMethod.Sphere), 'useRTXDI': False, 'RTXDIOptions': RTXDIOptions(mode=RTXDIMode.SpatiotemporalResampling, presampledTileCount=128, presampledTileSize=1024, storeCompactLightInfo=True, localLightCandidateCount=24, infiniteLightCandidateCount=8, envLightCandidateCount=8, brdfCandidateCount=1, brdfCutoff=0.0, testCandidateVisibility=True, biasCorrection=RTXDIBiasCorrection.Basic, depthThreshold=0.10000000149011612, normalThreshold=0.5, samplingRadius=30.0, spatialSampleCount=1, spatialIterations=5, maxHistoryLength=20, boilingFilterStrength=0.0, rayEpsilon=0.0010000000474974513, useEmissiveTextures=False, enableVisibilityShortcut=False, enablePermutationSampling=False), 'useAlphaTest': True, 'adjustShadingNormals': False, 'maxNestedMaterials': 2, 'useLightsInDielectricVolumes': False, 'disableCaustics': False, 'specularRoughnessThreshold': 0.25, 'primaryLodMode': TexLODMode.Mip0, 'lodBias': 0.0, 'useNRDDemodulation': True, 'outputSize': IOSize.Default, 'colorFormat': ColorFormat.LogLuvHDR})
    g.addPass(PathTracer, 'PathTracer')
    DynamicWeightingSVGF = createPass('DynamicWeightingSVGF', {'Enabled': True, 'DynamicWeighingEnabled': True, 'Iterations': 0, 'FeedbackTap': -1, 'GradientFilterIterations': 0, 'VarianceEpsilon': 9.999999747378752e-05, 'PhiColor': 10.0, 'PhiNormal': 128.0, 'Alpha': 0.05000000074505806, 'MomentsAlpha': 0.20000000298023224, 'GradientAlpha': 0.20000000298023224, 'GradientMidpoint': 0.004999999888241291, 'GammaSteepness': 300.0, 'SelectionMode': 4, 'SampleCountOverride': -1, 'NormalizationMode': 3})
    g.addPass(DynamicWeightingSVGF, 'DynamicWeightingSVGF')
    SVGFPass = createPass('DynamicWeightingSVGF', {'Enabled': True, 'DynamicWeighingEnabled': False, 'Iterations': 0, 'FeedbackTap': -1, 'GradientFilterIterations': 0, 'VarianceEpsilon': 9.999999747378752e-05, 'PhiColor': 10.0, 'PhiNormal': 128.0, 'Alpha': 0.05000000074505806, 'MomentsAlpha': 0.20000000298023224, 'GradientAlpha': 0.20000000298023224, 'GradientMidpoint': 0.009999999776482582, 'GammaSteepness': 100.0, 'SelectionMode': 0, 'SampleCountOverride': -1, 'NormalizationMode': 0})
    g.addPass(SVGFPass, 'SVGFPass')
    PathTracer0 = createPass('PathTracer', {'samplesPerPixel': 16, 'maxSurfaceBounces': 10, 'maxDiffuseBounces': 3, 'maxSpecularBounces': 3, 'maxTransmissionBounces': 10, 'sampleGenerator': 0, 'useBSDFSampling': True, 'useRussianRoulette': False, 'useNEE': True, 'useMIS': True, 'misHeuristic': MISHeuristic.Balance, 'misPowerExponent': 2.0, 'emissiveSampler': EmissiveLightSamplerType.LightBVH, 'lightBVHOptions': LightBVHSamplerOptions(buildOptions=LightBVHBuilderOptions(splitHeuristicSelection=SplitHeuristic.BinnedSAOH, maxTriangleCountPerLeaf=10, binCount=16, volumeEpsilon=0.0010000000474974513, splitAlongLargest=False, useVolumeOverSA=False, useLeafCreationCost=True, createLeavesASAP=True, allowRefitting=True, usePreintegration=True, useLightingCones=True), useBoundingCone=True, useLightingCone=True, disableNodeFlux=False, useUniformTriangleSampling=True, solidAngleBoundMethod=SolidAngleBoundMethod.Sphere), 'useRTXDI': False, 'RTXDIOptions': RTXDIOptions(mode=RTXDIMode.SpatiotemporalResampling, presampledTileCount=128, presampledTileSize=1024, storeCompactLightInfo=True, localLightCandidateCount=24, infiniteLightCandidateCount=8, envLightCandidateCount=8, brdfCandidateCount=1, brdfCutoff=0.0, testCandidateVisibility=True, biasCorrection=RTXDIBiasCorrection.Basic, depthThreshold=0.10000000149011612, normalThreshold=0.5, samplingRadius=30.0, spatialSampleCount=1, spatialIterations=5, maxHistoryLength=20, boilingFilterStrength=0.0, rayEpsilon=0.0010000000474974513, useEmissiveTextures=False, enableVisibilityShortcut=False, enablePermutationSampling=False), 'useAlphaTest': True, 'adjustShadingNormals': False, 'maxNestedMaterials': 2, 'useLightsInDielectricVolumes': False, 'disableCaustics': False, 'specularRoughnessThreshold': 0.25, 'primaryLodMode': TexLODMode.Mip0, 'lodBias': 0.0, 'useNRDDemodulation': True, 'outputSize': IOSize.Default, 'colorFormat': ColorFormat.LogLuvHDR})
    g.addPass(PathTracer0, 'PathTracer0')
    GroundTruthSVGFPass = createPass('DynamicWeightingSVGF', {'Enabled': True, 'DynamicWeighingEnabled': False, 'Iterations': 0, 'FeedbackTap': -1, 'GradientFilterIterations': 0, 'VarianceEpsilon': 9.999999747378752e-05, 'PhiColor': 10.0, 'PhiNormal': 128.0, 'Alpha': 0.05000000074505806, 'MomentsAlpha': 0.20000000298023224, 'GradientAlpha': 0.20000000298023224, 'GradientMidpoint': 0.009999999776482582, 'GammaSteepness': 100.0, 'SelectionMode': 0, 'SampleCountOverride': -1, 'NormalizationMode': 0})
    g.addPass(GroundTruthSVGFPass, 'GroundTruthSVGFPass')
    Composite0 = createPass('Composite', {'mode': CompositeMode.Add, 'scaleA': 0.5, 'scaleB': 0.5, 'outputFormat': ResourceFormat.RGBA32Float})
    g.addPass(Composite0, 'Composite0')
    ErrorMeasurePass = createPass('ErrorMeasurePass', {'ReferenceImagePath': WindowsPath('.'), 'MeasurementsFilePath': WindowsPath('C:/Users/jd3/Desktop/Code/Falcor/Source/Mogwai/Data/ErrorMeasure/DWeighted.csv'), 'IgnoreBackground': False, 'ComputeSquaredDifference': True, 'ComputeAverage': False, 'UseLoadedReference': False, 'ReportRunningError': True, 'RunningErrorSigma': 0.0, 'SelectedOutputId': OutputId.Source})
    g.addPass(ErrorMeasurePass, 'ErrorMeasurePass')
    ErrorMeasurePass0 = createPass('ErrorMeasurePass', {'ReferenceImagePath': WindowsPath('.'), 'MeasurementsFilePath': WindowsPath('C:/Users/jd3/Desktop/Code/Falcor/Source/Mogwai/Data/ErrorMeasure/Unweighted.csv'), 'IgnoreBackground': False, 'ComputeSquaredDifference': True, 'ComputeAverage': False, 'UseLoadedReference': False, 'ReportRunningError': True, 'RunningErrorSigma': 0.0, 'SelectedOutputId': OutputId.Source})
    g.addPass(ErrorMeasurePass0, 'ErrorMeasurePass0')
    RecordPass = createPass('RecordPass', {'StatistcsFilePath': WindowsPath('C:/Users/jd3/Desktop/Code/Falcor/Source/Mogwai/Data/ErrorMeasure/UnweightedIllumination.csv'), 'ReportRunningAverage': True, 'RunningAverageSigma': 0.0})
    g.addPass(RecordPass, 'RecordPass')
    RecordPass0 = createPass('RecordPass', {'StatistcsFilePath': WindowsPath('C:/Users/jd3/Desktop/Code/Falcor/Source/Mogwai/Data/ErrorMeasure/Gamma.csv'), 'ReportRunningAverage': True, 'RunningAverageSigma': 0.0})
    g.addPass(RecordPass0, 'RecordPass0')
    g.addEdge('GBufferRaster.viewW', 'PathTracer.viewW')
    g.addEdge('GBufferRaster.vbuffer', 'PathTracer.vbuffer')
    g.addEdge('GBufferRaster.mvec', 'PathTracer.mvec')
    g.addEdge('FoveatedPass.sampleCount', 'PathTracer.sampleCount')
    g.addEdge('PathTracer.albedo', 'Composite.A')
    g.addEdge('PathTracer.specularAlbedo', 'Composite.B')
    g.addEdge('Composite.out', 'DynamicWeightingSVGF.Albedo')
    g.addEdge('PathTracer.color', 'DynamicWeightingSVGF.Color')
    g.addEdge('PathTracer.nrdEmission', 'DynamicWeightingSVGF.Emission')
    g.addEdge('GBufferRaster.mvec', 'DynamicWeightingSVGF.MotionVec')
    g.addEdge('GBufferRaster.linearZ', 'DynamicWeightingSVGF.LinearZ')
    g.addEdge('GBufferRaster.pnFwidth', 'DynamicWeightingSVGF.PositionNormalFwidth')
    g.addEdge('GBufferRaster.normW', 'DynamicWeightingSVGF.WorldNormal')
    g.addEdge('GBufferRaster.posW', 'DynamicWeightingSVGF.WorldPosition')
    g.addEdge('FoveatedPass.sampleCount', 'DynamicWeightingSVGF.SampleCount')
    g.addEdge('PathTracer.color', 'SVGFPass.Color')
    g.addEdge('Composite.out', 'SVGFPass.Albedo')
    g.addEdge('PathTracer.nrdEmission', 'SVGFPass.Emission')
    g.addEdge('GBufferRaster.mvec', 'SVGFPass.MotionVec')
    g.addEdge('GBufferRaster.linearZ', 'SVGFPass.LinearZ')
    g.addEdge('GBufferRaster.pnFwidth', 'SVGFPass.PositionNormalFwidth')
    g.addEdge('GBufferRaster.posW', 'SVGFPass.WorldPosition')
    g.addEdge('GBufferRaster.normW', 'SVGFPass.WorldNormal')
    g.addEdge('GBufferRaster.mvec', 'PathTracer0.mvec')
    g.addEdge('GBufferRaster.vbuffer', 'PathTracer0.vbuffer')
    g.addEdge('GBufferRaster.viewW', 'PathTracer0.viewW')
    g.addEdge('PathTracer0.color', 'GroundTruthSVGFPass.Color')
    g.addEdge('PathTracer0.albedo', 'Composite0.A')
    g.addEdge('PathTracer0.specularAlbedo', 'Composite0.B')
    g.addEdge('Composite0.out', 'GroundTruthSVGFPass.Albedo')
    g.addEdge('PathTracer0.nrdEmission', 'GroundTruthSVGFPass.Emission')
    g.addEdge('GBufferRaster.linearZ', 'GroundTruthSVGFPass.LinearZ')
    g.addEdge('GBufferRaster.mvec', 'GroundTruthSVGFPass.MotionVec')
    g.addEdge('GBufferRaster.pnFwidth', 'GroundTruthSVGFPass.PositionNormalFwidth')
    g.addEdge('GBufferRaster.posW', 'GroundTruthSVGFPass.WorldPosition')
    g.addEdge('GBufferRaster.normW', 'GroundTruthSVGFPass.WorldNormal')
    g.addEdge('GroundTruthSVGFPass.Filtered image', 'ErrorMeasurePass.Reference')
    g.addEdge('GroundTruthSVGFPass.Filtered image', 'ErrorMeasurePass0.Reference')
    g.addEdge('DynamicWeightingSVGF.Filtered image', 'ErrorMeasurePass.Source')
    g.addEdge('SVGFPass.Filtered image', 'ErrorMeasurePass0.Source')
    g.addEdge('FoveatedPass.sampleCount', 'SVGFPass.SampleCount')
    g.addEdge('FoveatedPass.sampleCount', 'GroundTruthSVGFPass.SampleCount')
    g.addEdge('DynamicWeightingSVGF.Illumination_U', 'RecordPass.Input')
    g.addEdge('DynamicWeightingSVGF.OutGamma', 'RecordPass0.Input')
    g.markOutput('ErrorMeasurePass0.Output')
    g.markOutput('ErrorMeasurePass.Output')
    g.markOutput('RecordPass.Output')
    g.markOutput('RecordPass0.Output')
    return g

g = render_graph_g()
try: m.addGraph(g)
except NameError: None
