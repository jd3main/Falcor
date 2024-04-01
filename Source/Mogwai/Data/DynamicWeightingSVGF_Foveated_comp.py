from falcor import *
from pathlib import *

def render_graph_g():
    g = RenderGraph('g')
    loadRenderPassLibrary('AccumulatePass.dll')
    loadRenderPassLibrary('BSDFViewer.dll')
    loadRenderPassLibrary('CSM.dll')
    loadRenderPassLibrary('MinimalPathTracer.dll')
    loadRenderPassLibrary('AdaptiveSampling.dll')
    loadRenderPassLibrary('Antialiasing.dll')
    loadRenderPassLibrary('BlitPass.dll')
    loadRenderPassLibrary('DebugPasses.dll')
    loadRenderPassLibrary('PathTracer.dll')
    loadRenderPassLibrary('DepthPass.dll')
    loadRenderPassLibrary('DLSSPass.dll')
    loadRenderPassLibrary('DynamicWeightingSVGF.dll')
    loadRenderPassLibrary('ErrorMeasurePass.dll')
    loadRenderPassLibrary('TemporalDelayPass.dll')
    loadRenderPassLibrary('ErrorMeasurePassEx.dll')
    loadRenderPassLibrary('SimplePostFX.dll')
    loadRenderPassLibrary('FLIPPass.dll')
    loadRenderPassLibrary('ForwardLightingPass.dll')
    loadRenderPassLibrary('FoveatedPass.dll')
    loadRenderPassLibrary('ReprojectionPass.dll')
    loadRenderPassLibrary('GBuffer.dll')
    loadRenderPassLibrary('WhittedRayTracer.dll')
    loadRenderPassLibrary('ImageLoader.dll')
    loadRenderPassLibrary('ModulateIllumination.dll')
    loadRenderPassLibrary('MySVGFPass.dll')
    loadRenderPassLibrary('NRDPass.dll')
    loadRenderPassLibrary('TwoHistorySVGFPass.dll')
    loadRenderPassLibrary('PathTracerEx.dll')
    loadRenderPassLibrary('PixelInspectorPass.dll')
    loadRenderPassLibrary('RecordPass.dll')
    loadRenderPassLibrary('SkyBox.dll')
    loadRenderPassLibrary('RTXDIPass.dll')
    loadRenderPassLibrary('RTXGIPass.dll')
    loadRenderPassLibrary('SceneDebugger.dll')
    loadRenderPassLibrary('SDFEditor.dll')
    loadRenderPassLibrary('SSAO.dll')
    loadRenderPassLibrary('SVGFPass.dll')
    loadRenderPassLibrary('TestPasses.dll')
    loadRenderPassLibrary('ToneMapper.dll')
    loadRenderPassLibrary('Utils.dll')
    SplitScreenPass = createPass('SplitScreenPass', {'splitLocation': 0.5, 'showTextLabels': False, 'leftLabel': 'Left side', 'rightLabel': 'Right side'})
    g.addPass(SplitScreenPass, 'SplitScreenPass')
    FoveatedPass = createPass('FoveatedPass', {'shape': 1, 'foveaInputType': 1, 'useHistory': False, 'alpha': 0.05000000074505806, 'foveaRadius': 200.0, 'foveaSampleCount': 8.0, 'periphSampleCount': 1.0, 'foveaMovePattern': 0, 'foveaMoveRadius': float2(200.000000,200.000000), 'foveaMoveFreq': float2(0.400000,0.500000), 'foveaMovePhase': float2(1.570796,0.000000), 'foveaMoveSpeed': 0.0, 'foveaMoveStayDuration': 0.0, 'useRealTime': False, 'flickerEnabled': False, 'flickerBrightDurationMs': 1.0, 'flickerDarkDurationMs': 1.0})
    g.addPass(FoveatedPass, 'FoveatedPass')
    ToneMapper = createPass('ToneMapper', {'outputSize': IOSize.Default, 'useSceneMetadata': True, 'exposureCompensation': 0.0, 'autoExposure': False, 'filmSpeed': 100.0, 'whiteBalance': False, 'whitePoint': 6500.0, 'operator': ToneMapOp.Aces, 'clamp': True, 'whiteMaxLuminance': 1.0, 'whiteScale': 11.199999809265137, 'fNumber': 1.0, 'shutter': 1.0, 'exposureMode': ExposureMode.AperturePriority})
    g.addPass(ToneMapper, 'ToneMapper')
    PathTracer = createPass('PathTracer', {'samplesPerPixel': 1, 'maxSurfaceBounces': 10, 'maxDiffuseBounces': 3, 'maxSpecularBounces': 3, 'maxTransmissionBounces': 10, 'sampleGenerator': 0, 'useBSDFSampling': True, 'useRussianRoulette': False, 'useNEE': True, 'useMIS': True, 'misHeuristic': MISHeuristic.Balance, 'misPowerExponent': 2.0, 'emissiveSampler': EmissiveLightSamplerType.LightBVH, 'lightBVHOptions': LightBVHSamplerOptions(buildOptions=LightBVHBuilderOptions(splitHeuristicSelection=SplitHeuristic.BinnedSAOH, maxTriangleCountPerLeaf=10, binCount=16, volumeEpsilon=0.0010000000474974513, splitAlongLargest=False, useVolumeOverSA=False, useLeafCreationCost=True, createLeavesASAP=True, allowRefitting=True, usePreintegration=True, useLightingCones=True), useBoundingCone=True, useLightingCone=True, disableNodeFlux=False, useUniformTriangleSampling=True, solidAngleBoundMethod=SolidAngleBoundMethod.Sphere), 'useRTXDI': False, 'RTXDIOptions': RTXDIOptions(mode=RTXDIMode.SpatiotemporalResampling, presampledTileCount=128, presampledTileSize=1024, storeCompactLightInfo=True, localLightCandidateCount=24, infiniteLightCandidateCount=8, envLightCandidateCount=8, brdfCandidateCount=1, brdfCutoff=0.0, testCandidateVisibility=True, biasCorrection=RTXDIBiasCorrection.Basic, depthThreshold=0.10000000149011612, normalThreshold=0.5, samplingRadius=30.0, spatialSampleCount=1, spatialIterations=5, maxHistoryLength=20, boilingFilterStrength=0.0, rayEpsilon=0.0010000000474974513, useEmissiveTextures=False, enableVisibilityShortcut=False, enablePermutationSampling=False), 'useAlphaTest': True, 'adjustShadingNormals': False, 'maxNestedMaterials': 2, 'useLightsInDielectricVolumes': False, 'disableCaustics': False, 'specularRoughnessThreshold': 0.25, 'primaryLodMode': TexLODMode.Mip0, 'lodBias': 0.0, 'useNRDDemodulation': True, 'outputSize': IOSize.Default, 'colorFormat': ColorFormat.LogLuvHDR})
    g.addPass(PathTracer, 'PathTracer')
    GBufferRaster = createPass('GBufferRaster', {'outputSize': IOSize.Default, 'samplePattern': SamplePattern.Center, 'sampleCount': 16, 'useAlphaTest': True, 'adjustShadingNormals': True, 'forceCullMode': False, 'cull': CullMode.CullBack})
    g.addPass(GBufferRaster, 'GBufferRaster')
    Composite = createPass('Composite', {'mode': CompositeMode.Add, 'scaleA': 1.0, 'scaleB': 1.0, 'outputFormat': ResourceFormat.RGBA32Float})
    g.addPass(Composite, 'Composite')
    DynamicWeightingSVGF = createPass('DynamicWeightingSVGF', {'Enabled': True, 'DynamicWeighingEnabled': True, 'Iterations': 2, 'FeedbackTap': 0, 'GradientFilterIterations': 1, 'VarianceEpsilon': 9.999999747378752e-05, 'PhiColor': 10.0, 'PhiNormal': 128.0, 'Alpha': 0.05000000074505806, 'WeightedAlpha': 0.05000000074505806, 'MomentsAlpha': 0.20000000298023224, 'GradientAlpha': 0.20000000298023224, 'MaxGradient': 1000000.0, 'GradientMidpoint': 0.5, 'GammaSteepness': 1.0, 'SelectionMode': 2, 'SampleCountOverride': -1, 'NormalizationMode': 3, 'UseInputReprojection': False, 'OutputPingPongAfterIters': 0, 'OutputPingPongIdx': 0, 'EnableDebugTag': False, 'EnableDebugOutput': False, 'EnableOutputVariance': False})
    g.addPass(DynamicWeightingSVGF, 'DynamicWeightingSVGF')
    DynamicWeightingSVGF0 = createPass('DynamicWeightingSVGF', {'Enabled': True, 'DynamicWeighingEnabled': False, 'Iterations': 2, 'FeedbackTap': 0, 'GradientFilterIterations': 2, 'VarianceEpsilon': 9.999999747378752e-05, 'PhiColor': 10.0, 'PhiNormal': 128.0, 'Alpha': 0.05000000074505806, 'WeightedAlpha': 0.05000000074505806, 'MomentsAlpha': 0.20000000298023224, 'GradientAlpha': 0.20000000298023224, 'MaxGradient': 1000000.0, 'GradientMidpoint': 0.019999999552965164, 'GammaSteepness': 10.0, 'SelectionMode': 0, 'SampleCountOverride': -1, 'NormalizationMode': 0, 'UseInputReprojection': False, 'OutputPingPongAfterIters': 0, 'OutputPingPongIdx': 0, 'EnableDebugTag': False, 'EnableDebugOutput': False, 'EnableOutputVariance': True})
    g.addPass(DynamicWeightingSVGF0, 'DynamicWeightingSVGF0')
    ToneMapper0 = createPass('ToneMapper', {'outputSize': IOSize.Default, 'useSceneMetadata': True, 'exposureCompensation': 0.0, 'autoExposure': False, 'filmSpeed': 100.0, 'whiteBalance': False, 'whitePoint': 6500.0, 'operator': ToneMapOp.Aces, 'clamp': True, 'whiteMaxLuminance': 1.0, 'whiteScale': 11.199999809265137, 'fNumber': 1.0, 'shutter': 1.0, 'exposureMode': ExposureMode.AperturePriority})
    g.addPass(ToneMapper0, 'ToneMapper0')
    VBufferRT = createPass('VBufferRT', {'outputSize': IOSize.Default, 'samplePattern': SamplePattern.Center, 'sampleCount': 16, 'useAlphaTest': True, 'adjustShadingNormals': True, 'forceCullMode': False, 'cull': CullMode.CullBack, 'useTraceRayInline': False, 'useDOF': True})
    g.addPass(VBufferRT, 'VBufferRT')
    g.addEdge('GBufferRaster.viewW', 'PathTracer.viewW')
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
    g.addEdge('DynamicWeightingSVGF.Filtered image', 'ToneMapper.src')
    g.addEdge('Composite.out', 'DynamicWeightingSVGF0.Albedo')
    g.addEdge('PathTracer.nrdEmission', 'DynamicWeightingSVGF0.Emission')
    g.addEdge('PathTracer.color', 'DynamicWeightingSVGF0.Color')
    g.addEdge('FoveatedPass.sampleCount', 'DynamicWeightingSVGF0.SampleCount')
    g.addEdge('GBufferRaster.pnFwidth', 'DynamicWeightingSVGF0.PositionNormalFwidth')
    g.addEdge('GBufferRaster.linearZ', 'DynamicWeightingSVGF0.LinearZ')
    g.addEdge('DynamicWeightingSVGF0.Filtered image', 'ToneMapper0.src')
    g.addEdge('GBufferRaster.posW', 'DynamicWeightingSVGF0.WorldPosition')
    g.addEdge('GBufferRaster.normW', 'DynamicWeightingSVGF0.WorldNormal')
    g.addEdge('GBufferRaster.mvec', 'DynamicWeightingSVGF0.MotionVec')
    g.addEdge('ToneMapper0.dst', 'SplitScreenPass.leftInput')
    g.addEdge('ToneMapper.dst', 'SplitScreenPass.rightInput')
    g.addEdge('VBufferRT.vbuffer', 'PathTracer.vbuffer')
    g.markOutput('SplitScreenPass.output')
    return g

g = render_graph_g()
try: m.addGraph(g)
except NameError: None
