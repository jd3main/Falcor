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
    ToneMapper = createPass('ToneMapper', {'outputSize': IOSize.Default, 'useSceneMetadata': True, 'exposureCompensation': 0.0, 'autoExposure': False, 'filmSpeed': 100.0, 'whiteBalance': False, 'whitePoint': 6500.0, 'operator': ToneMapOp.Aces, 'clamp': True, 'whiteMaxLuminance': 1.0, 'whiteScale': 11.199999809265137, 'fNumber': 1.0, 'shutter': 1.0, 'exposureMode': ExposureMode.AperturePriority})
    g.addPass(ToneMapper, 'ToneMapper')
    PathTracer = createPass('PathTracer', {'samplesPerPixel': 1, 'maxSurfaceBounces': 10, 'maxDiffuseBounces': 3, 'maxSpecularBounces': 3, 'maxTransmissionBounces': 10, 'sampleGenerator': 0, 'useBSDFSampling': True, 'useRussianRoulette': False, 'useNEE': True, 'useMIS': True, 'misHeuristic': MISHeuristic.Balance, 'misPowerExponent': 2.0, 'emissiveSampler': EmissiveLightSamplerType.LightBVH, 'lightBVHOptions': LightBVHSamplerOptions(buildOptions=LightBVHBuilderOptions(splitHeuristicSelection=SplitHeuristic.BinnedSAOH, maxTriangleCountPerLeaf=10, binCount=16, volumeEpsilon=0.0010000000474974513, splitAlongLargest=False, useVolumeOverSA=False, useLeafCreationCost=True, createLeavesASAP=True, allowRefitting=True, usePreintegration=True, useLightingCones=True), useBoundingCone=True, useLightingCone=True, disableNodeFlux=False, useUniformTriangleSampling=True, solidAngleBoundMethod=SolidAngleBoundMethod.Sphere), 'useRTXDI': False, 'RTXDIOptions': RTXDIOptions(mode=RTXDIMode.SpatiotemporalResampling, presampledTileCount=128, presampledTileSize=1024, storeCompactLightInfo=True, localLightCandidateCount=24, infiniteLightCandidateCount=8, envLightCandidateCount=8, brdfCandidateCount=1, brdfCutoff=0.0, testCandidateVisibility=True, biasCorrection=RTXDIBiasCorrection.Basic, depthThreshold=0.10000000149011612, normalThreshold=0.5, samplingRadius=30.0, spatialSampleCount=1, spatialIterations=5, maxHistoryLength=20, boilingFilterStrength=0.0, rayEpsilon=0.0010000000474974513, useEmissiveTextures=False, enableVisibilityShortcut=False, enablePermutationSampling=False), 'useAlphaTest': True, 'adjustShadingNormals': False, 'maxNestedMaterials': 2, 'useLightsInDielectricVolumes': False, 'disableCaustics': False, 'specularRoughnessThreshold': 0.25, 'primaryLodMode': TexLODMode.Mip0, 'lodBias': 0.0, 'useNRDDemodulation': True, 'outputSize': IOSize.Default, 'colorFormat': ColorFormat.LogLuvHDR})
    g.addPass(PathTracer, 'PathTracer')
    GBufferRaster = createPass('GBufferRaster', {'outputSize': IOSize.Default, 'samplePattern': SamplePattern.Center, 'sampleCount': 16, 'useAlphaTest': True, 'adjustShadingNormals': True, 'forceCullMode': False, 'cull': CullMode.CullBack})
    g.addPass(GBufferRaster, 'GBufferRaster')
    Composite = createPass('Composite', {'mode': CompositeMode.Add, 'scaleA': 1.0, 'scaleB': 1.0, 'outputFormat': ResourceFormat.RGBA32Float})
    g.addPass(Composite, 'Composite')
    DynamicWeightingSVGF = createPass('DynamicWeightingSVGF', {'Enabled': True, 'DynamicWeighingEnabled': True, 'Iterations': 2, 'FeedbackTap': -1, 'GradientFilterIterations': 0, 'VarianceEpsilon': 9.999999747378752e-05, 'PhiColor': 10.0, 'PhiNormal': 128.0, 'Alpha': 0.05000000074505806, 'MomentsAlpha': 0.20000000298023224, 'GradientAlpha': 0.20000000298023224, 'GradientMidpoint': 0.05000000074505806, 'GammaSteepness': 10.0, 'SelectionMode': 2, 'SampleCountOverride': -1, 'NormalizationMode': 3, 'UseInputReprojection': True, 'OutputPingPongAfterIters': 0, 'OutputPingPongIdx': 0, 'EnableDebugTag': False, 'EnableDebugOutput': False})
    g.addPass(DynamicWeightingSVGF, 'DynamicWeightingSVGF')
    ColorMapPass1 = createPass('ColorMapPass', {'colorMap': ColorMap.Jet, 'channel': 0, 'autoRange': True, 'minValue': 0.0, 'maxValue': 32.0})
    g.addPass(ColorMapPass1, 'ColorMapPass1')
    AdaptiveSampling = createPass('AdaptiveSampling', {'Enabled': True, 'AverageSampleCountBudget': 2.0, 'MinVariance': 0.0, 'MaxVariance': 100.0, 'MinSamplePerPixel': 1, 'MaxSamplePerPixel': 8})
    g.addPass(AdaptiveSampling, 'AdaptiveSampling')
    ReprojectionPass = createPass('ReprojectionPass')
    g.addPass(ReprojectionPass, 'ReprojectionPass')
    BlitToInputBuffer = createPass('BlitToInputBuffer')
    g.addPass(BlitToInputBuffer, 'BlitToInputBuffer')
    SharedBuffer0 = createPass('SharedBuffer')
    g.addPass(SharedBuffer0, 'SharedBuffer0')
    SharedBuffer1 = createPass('SharedBuffer')
    g.addPass(SharedBuffer1, 'SharedBuffer1')
    BlitToInputBuffer0 = createPass('BlitToInputBuffer')
    g.addPass(BlitToInputBuffer0, 'BlitToInputBuffer0')
    g.addEdge('GBufferRaster.viewW', 'PathTracer.viewW')
    g.addEdge('GBufferRaster.vbuffer', 'PathTracer.vbuffer')
    g.addEdge('GBufferRaster.mvec', 'PathTracer.mvec')
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
    g.addEdge('DynamicWeightingSVGF.HistLength', 'ColorMapPass1.input')
    g.addEdge('GBufferRaster.mvec', 'ReprojectionPass.MotionVec')
    g.addEdge('GBufferRaster.linearZ', 'ReprojectionPass.LinearZ')
    g.addEdge('GBufferRaster.pnFwidth', 'ReprojectionPass.PositionNormalFwidth')
    g.addEdge('DynamicWeightingSVGF.HistLength', 'BlitToInputBuffer.src')
    g.addEdge('SharedBuffer0.buffer', 'BlitToInputBuffer.dst')
    g.addEdge('SharedBuffer0.buffer', 'AdaptiveSampling.histLength')
    g.addEdge('AdaptiveSampling', 'BlitToInputBuffer')
    g.addEdge('DynamicWeightingSVGF.Variance', 'BlitToInputBuffer0.src')
    g.addEdge('SharedBuffer1.buffer', 'BlitToInputBuffer0.dst')
    g.addEdge('SharedBuffer1.buffer', 'AdaptiveSampling.var')
    g.addEdge('AdaptiveSampling', 'BlitToInputBuffer0')
    g.addEdge('AdaptiveSampling.sampleCount', 'PathTracer.sampleCount')
    g.addEdge('AdaptiveSampling.sampleCount', 'DynamicWeightingSVGF.SampleCount')
    g.addEdge('DynamicWeightingSVGF.Filtered image', 'ToneMapper.src')
    g.addEdge('ReprojectionPass.TapWidthAndPrevPos', 'AdaptiveSampling.TapWidthAndPrevPos')
    g.addEdge('ReprojectionPass.W0123', 'AdaptiveSampling.W0123')
    g.addEdge('ReprojectionPass.W4567', 'AdaptiveSampling.W4567')
    g.addEdge('ReprojectionPass.TapWidthAndPrevPos', 'DynamicWeightingSVGF.TapWidthAndPrevPos')
    g.addEdge('ReprojectionPass.W0123', 'DynamicWeightingSVGF.W0123')
    g.addEdge('ReprojectionPass.W4567', 'DynamicWeightingSVGF.W4567')
    g.markOutput('ToneMapper.dst')
    g.markOutput('DynamicWeightingSVGF.Filtered image')
    g.markOutput('DynamicWeightingSVGF.Variance')
    return g

g = render_graph_g()
try: m.addGraph(g)
except NameError: None
