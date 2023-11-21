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
    FoveatedPass = createPass('FoveatedPass', {'shape': 1, 'foveaInputType': 1, 'useHistory': False, 'alpha': 0.05000000074505806, 'foveaRadius': 200.0, 'foveaSampleCount': 4.0, 'periphSampleCount': 1.0, 'uniformSampleCount': 1.0, 'foveaMoveRadius': 300.0, 'foveaMoveFreq': 0.5, 'foveaMoveDirection': 0})
    g.addPass(FoveatedPass, 'FoveatedPass')
    CountToColor0 = createPass('CountToColor', {'MaxValue': 16})
    g.addPass(CountToColor0, 'CountToColor0')
    ToneMapper = createPass('ToneMapper', {'outputSize': IOSize.Default, 'useSceneMetadata': True, 'exposureCompensation': 0.0, 'autoExposure': False, 'filmSpeed': 100.0, 'whiteBalance': False, 'whitePoint': 6500.0, 'operator': ToneMapOp.Aces, 'clamp': True, 'whiteMaxLuminance': 1.0, 'whiteScale': 11.199999809265137, 'fNumber': 1.0, 'shutter': 1.0, 'exposureMode': ExposureMode.AperturePriority})
    g.addPass(ToneMapper, 'ToneMapper')
    PathTracer = createPass('PathTracer', {'samplesPerPixel': 1, 'maxSurfaceBounces': 10, 'maxDiffuseBounces': 3, 'maxSpecularBounces': 3, 'maxTransmissionBounces': 10, 'sampleGenerator': 0, 'useBSDFSampling': True, 'useRussianRoulette': False, 'useNEE': True, 'useMIS': True, 'misHeuristic': MISHeuristic.Balance, 'misPowerExponent': 2.0, 'emissiveSampler': EmissiveLightSamplerType.LightBVH, 'lightBVHOptions': LightBVHSamplerOptions(buildOptions=LightBVHBuilderOptions(splitHeuristicSelection=SplitHeuristic.BinnedSAOH, maxTriangleCountPerLeaf=10, binCount=16, volumeEpsilon=0.0010000000474974513, splitAlongLargest=False, useVolumeOverSA=False, useLeafCreationCost=True, createLeavesASAP=True, allowRefitting=True, usePreintegration=True, useLightingCones=True), useBoundingCone=True, useLightingCone=True, disableNodeFlux=False, useUniformTriangleSampling=True, solidAngleBoundMethod=SolidAngleBoundMethod.Sphere), 'useRTXDI': False, 'RTXDIOptions': RTXDIOptions(mode=RTXDIMode.SpatiotemporalResampling, presampledTileCount=128, presampledTileSize=1024, storeCompactLightInfo=True, localLightCandidateCount=24, infiniteLightCandidateCount=8, envLightCandidateCount=8, brdfCandidateCount=1, brdfCutoff=0.0, testCandidateVisibility=True, biasCorrection=RTXDIBiasCorrection.Basic, depthThreshold=0.10000000149011612, normalThreshold=0.5, samplingRadius=30.0, spatialSampleCount=1, spatialIterations=5, maxHistoryLength=20, boilingFilterStrength=0.0, rayEpsilon=0.0010000000474974513, useEmissiveTextures=False, enableVisibilityShortcut=False, enablePermutationSampling=False), 'useAlphaTest': True, 'adjustShadingNormals': False, 'maxNestedMaterials': 2, 'useLightsInDielectricVolumes': False, 'disableCaustics': False, 'specularRoughnessThreshold': 0.25, 'primaryLodMode': TexLODMode.Mip0, 'lodBias': 0.0, 'useNRDDemodulation': True, 'outputSize': IOSize.Default, 'colorFormat': ColorFormat.LogLuvHDR})
    g.addPass(PathTracer, 'PathTracer')
    GBufferRaster = createPass('GBufferRaster', {'outputSize': IOSize.Default, 'samplePattern': SamplePattern.Center, 'sampleCount': 16, 'useAlphaTest': True, 'adjustShadingNormals': True, 'forceCullMode': False, 'cull': CullMode.CullBack})
    g.addPass(GBufferRaster, 'GBufferRaster')
    Composite = createPass('Composite', {'mode': CompositeMode.Add, 'scaleA': 1.0, 'scaleB': 1.0, 'outputFormat': ResourceFormat.RGBA32Float})
    g.addPass(Composite, 'Composite')
    AccumulatePass = createPass('AccumulatePass', {'enabled': False, 'outputSize': IOSize.Default, 'autoReset': True, 'precisionMode': AccumulatePrecision.Single, 'subFrameCount': 0, 'maxAccumulatedFrames': 0})
    g.addPass(AccumulatePass, 'AccumulatePass')
    SplitScreenPass = createPass('SplitScreenPass', {'splitLocation': 0.25, 'showTextLabels': False, 'leftLabel': 'Left side', 'rightLabel': 'Right side'})
    g.addPass(SplitScreenPass, 'SplitScreenPass')
    SplitScreenPass0 = createPass('SplitScreenPass', {'splitLocation': 0.75, 'showTextLabels': False, 'leftLabel': 'Left side', 'rightLabel': 'Right side'})
    g.addPass(SplitScreenPass0, 'SplitScreenPass0')
    SplitScreenPass1 = createPass('SplitScreenPass', {'splitLocation': 0.5, 'showTextLabels': False, 'leftLabel': 'Left side', 'rightLabel': 'Right side'})
    g.addPass(SplitScreenPass1, 'SplitScreenPass1')
    SplitScreenPass2 = createPass('SplitScreenPass', {'splitLocation': 0.5, 'showTextLabels': False, 'leftLabel': 'Left side', 'rightLabel': 'Right side'})
    g.addPass(SplitScreenPass2, 'SplitScreenPass2')
    CountToColor1 = createPass('CountToColor', {'MaxValue': 256})
    g.addPass(CountToColor1, 'CountToColor1')
    CountToColor2 = createPass('CountToColor', {'MaxValue': 256})
    g.addPass(CountToColor2, 'CountToColor2')
    DynamicWeightingSVGF = createPass('DynamicWeightingSVGF', {'Enabled': True, 'DynamicWeighingEnabled': True, 'Iterations': 4, 'FeedbackTap': 2, 'GradientFilterIterations': 1, 'VarianceEpsilon': 9.999999747378752e-05, 'PhiColor': 10.0, 'PhiNormal': 128.0, 'Alpha': 0.05000000074505806, 'MomentsAlpha': 0.20000000298023224, 'GradientAlpha': 0.20000000298023224, 'GammaRatio': 1.0})
    g.addPass(DynamicWeightingSVGF, 'DynamicWeightingSVGF')
    ColorMapPass = createPass('ColorMapPass', {'colorMap': ColorMap.Jet, 'channel': 0, 'autoRange': False, 'minValue': -1.0, 'maxValue': 1.0})
    g.addPass(ColorMapPass, 'ColorMapPass')
    ColorMapPass0 = createPass('ColorMapPass', {'colorMap': ColorMap.Jet, 'channel': 0, 'autoRange': False, 'minValue': 0.0, 'maxValue': 1.0})
    g.addPass(ColorMapPass0, 'ColorMapPass0')
    ColorMapPass1 = createPass('ColorMapPass', {'colorMap': ColorMap.Jet, 'channel': 0, 'autoRange': True, 'minValue': 0.0, 'maxValue': 32.0})
    g.addPass(ColorMapPass1, 'ColorMapPass1')
    g.addEdge('GBufferRaster.viewW', 'PathTracer.viewW')
    g.addEdge('GBufferRaster.vbuffer', 'PathTracer.vbuffer')
    g.addEdge('GBufferRaster.mvec', 'PathTracer.mvec')
    g.addEdge('FoveatedPass.sampleCount', 'PathTracer.sampleCount')
    g.addEdge('FoveatedPass.sampleCount', 'CountToColor0.Count')
    g.addEdge('PathTracer.albedo', 'Composite.A')
    g.addEdge('PathTracer.specularAlbedo', 'Composite.B')
    g.addEdge('AccumulatePass.output', 'ToneMapper.src')
    g.addEdge('SplitScreenPass0.output', 'SplitScreenPass1.rightInput')
    g.addEdge('SplitScreenPass.output', 'SplitScreenPass1.leftInput')
    g.addEdge('CountToColor1.Color', 'SplitScreenPass2.leftInput')
    g.addEdge('CountToColor2.Color', 'SplitScreenPass2.rightInput')
    g.addEdge('Composite.out', 'DynamicWeightingSVGF.Albedo')
    g.addEdge('PathTracer.color', 'DynamicWeightingSVGF.Color')
    g.addEdge('DynamicWeightingSVGF.Filtered image', 'AccumulatePass.input')
    g.addEdge('PathTracer.nrdEmission', 'DynamicWeightingSVGF.Emission')
    g.addEdge('GBufferRaster.mvec', 'DynamicWeightingSVGF.MotionVec')
    g.addEdge('GBufferRaster.linearZ', 'DynamicWeightingSVGF.LinearZ')
    g.addEdge('GBufferRaster.pnFwidth', 'DynamicWeightingSVGF.PositionNormalFwidth')
    g.addEdge('GBufferRaster.normW', 'DynamicWeightingSVGF.WorldNormal')
    g.addEdge('GBufferRaster.posW', 'DynamicWeightingSVGF.WorldPosition')
    g.addEdge('DynamicWeightingSVGF.Weight_W', 'CountToColor2.Count')
    g.addEdge('DynamicWeightingSVGF.Weight_U', 'CountToColor1.Count')
    g.addEdge('DynamicWeightingSVGF.Illumination_U', 'SplitScreenPass.leftInput')
    g.addEdge('DynamicWeightingSVGF.Illumination_W', 'SplitScreenPass.rightInput')
    g.addEdge('DynamicWeightingSVGF.Filtered_U', 'SplitScreenPass0.leftInput')
    g.addEdge('DynamicWeightingSVGF.Filtered_W', 'SplitScreenPass0.rightInput')
    g.addEdge('FoveatedPass.sampleCount', 'DynamicWeightingSVGF.SampleCount')
    g.addEdge('DynamicWeightingSVGF.OutGradient', 'ColorMapPass.input')
    g.addEdge('DynamicWeightingSVGF.OutGamma', 'ColorMapPass0.input')
    g.addEdge('DynamicWeightingSVGF.HistLength', 'ColorMapPass1.input')
    g.markOutput('ToneMapper.dst')
    g.markOutput('SplitScreenPass1.output')
    g.markOutput('SplitScreenPass2.output')
    g.markOutput('ColorMapPass.output')
    g.markOutput('ColorMapPass0.output')
    g.markOutput('DynamicWeightingSVGF.OutGradient')
    return g

g = render_graph_g()
try: m.addGraph(g)
except NameError: None
