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
    FoveatedPass = createPass('FoveatedPass', {'shape': 2, 'foveaInputType': 0, 'useHistory': False, 'alpha': 0.05000000074505806, 'foveaRadius': 200.0, 'foveaSampleCount': 2.0, 'periphSampleCount': 1.0, 'uniformSampleCount': 1.0, 'foveaMoveRadius': 300.0, 'foveaMoveFreq': 0.5, 'foveaMoveDirection': 0})
    g.addPass(FoveatedPass, 'FoveatedPass')
    CountToColor0 = createPass('CountToColor', {'MaxValue': 16})
    g.addPass(CountToColor0, 'CountToColor0')
    CountToColor = createPass('CountToColor', {'MaxValue': 256})
    g.addPass(CountToColor, 'CountToColor')
    ToneMapper = createPass('ToneMapper', {'outputSize': IOSize.Default, 'useSceneMetadata': True, 'exposureCompensation': 0.0, 'autoExposure': False, 'filmSpeed': 100.0, 'whiteBalance': False, 'whitePoint': 6500.0, 'operator': ToneMapOp.Aces, 'clamp': True, 'whiteMaxLuminance': 1.0, 'whiteScale': 11.199999809265137, 'fNumber': 1.0, 'shutter': 1.0, 'exposureMode': ExposureMode.AperturePriority})
    g.addPass(ToneMapper, 'ToneMapper')
    PathTracer = createPass('PathTracer', {'samplesPerPixel': 1, 'maxSurfaceBounces': 10, 'maxDiffuseBounces': 3, 'maxSpecularBounces': 3, 'maxTransmissionBounces': 10, 'sampleGenerator': 0, 'useBSDFSampling': True, 'useRussianRoulette': False, 'useNEE': True, 'useMIS': True, 'misHeuristic': MISHeuristic.Balance, 'misPowerExponent': 2.0, 'emissiveSampler': EmissiveLightSamplerType.LightBVH, 'lightBVHOptions': LightBVHSamplerOptions(buildOptions=LightBVHBuilderOptions(splitHeuristicSelection=SplitHeuristic.BinnedSAOH, maxTriangleCountPerLeaf=10, binCount=16, volumeEpsilon=0.0010000000474974513, splitAlongLargest=False, useVolumeOverSA=False, useLeafCreationCost=True, createLeavesASAP=True, allowRefitting=True, usePreintegration=True, useLightingCones=True), useBoundingCone=True, useLightingCone=True, disableNodeFlux=False, useUniformTriangleSampling=True, solidAngleBoundMethod=SolidAngleBoundMethod.Sphere), 'useRTXDI': False, 'RTXDIOptions': RTXDIOptions(mode=RTXDIMode.SpatiotemporalResampling, presampledTileCount=128, presampledTileSize=1024, storeCompactLightInfo=True, localLightCandidateCount=24, infiniteLightCandidateCount=8, envLightCandidateCount=8, brdfCandidateCount=1, brdfCutoff=0.0, testCandidateVisibility=True, biasCorrection=RTXDIBiasCorrection.Basic, depthThreshold=0.10000000149011612, normalThreshold=0.5, samplingRadius=30.0, spatialSampleCount=1, spatialIterations=5, maxHistoryLength=20, boilingFilterStrength=0.0, rayEpsilon=0.0010000000474974513, useEmissiveTextures=False, enableVisibilityShortcut=False, enablePermutationSampling=False), 'useAlphaTest': True, 'adjustShadingNormals': False, 'maxNestedMaterials': 2, 'useLightsInDielectricVolumes': False, 'disableCaustics': False, 'specularRoughnessThreshold': 0.25, 'primaryLodMode': TexLODMode.Mip0, 'lodBias': 0.0, 'useNRDDemodulation': True, 'outputSize': IOSize.Default, 'colorFormat': ColorFormat.LogLuvHDR})
    g.addPass(PathTracer, 'PathTracer')
    GBufferRaster = createPass('GBufferRaster', {'outputSize': IOSize.Default, 'samplePattern': SamplePattern.Center, 'sampleCount': 16, 'useAlphaTest': True, 'adjustShadingNormals': True, 'forceCullMode': False, 'cull': CullMode.CullBack})
    g.addPass(GBufferRaster, 'GBufferRaster')
    SharedBuffer = createPass('SharedBuffer')
    g.addPass(SharedBuffer, 'SharedBuffer')
    Composite = createPass('Composite', {'mode': CompositeMode.Add, 'scaleA': 1.0, 'scaleB': 1.0, 'outputFormat': ResourceFormat.RGBA32Float})
    g.addPass(Composite, 'Composite')
    Composite0 = createPass('Composite', {'mode': CompositeMode.Add, 'scaleA': 1.0, 'scaleB': 1.0, 'outputFormat': ResourceFormat.RGBA32Float})
    g.addPass(Composite0, 'Composite0')
    AccumulatePass = createPass('AccumulatePass', {'enabled': False, 'outputSize': IOSize.Default, 'autoReset': True, 'precisionMode': AccumulatePrecision.Single, 'subFrameCount': 0, 'maxAccumulatedFrames': 0})
    g.addPass(AccumulatePass, 'AccumulatePass')
    TwoHistorySVGFPass = createPass('TwoHistorySVGFPass', {'Enabled': True, 'Iterations': 4, 'FeedbackTap': 1, 'VarianceEpsilon': 9.999999747378752e-05, 'PhiColor': 10.0, 'PhiNormal': 128.0, 'Alpha': 0.05000000074505806, 'MomentsAlpha': 0.20000000298023224, 'MaxHistoryWeight': 10.0, 'ShortHistoryMaxWeight': 8.0, 'LongHistoryMaxWeight': 40.0})
    g.addPass(TwoHistorySVGFPass, 'TwoHistorySVGFPass')
    SplitScreenPass = createPass('SplitScreenPass', {'splitLocation': 0.5, 'showTextLabels': False, 'leftLabel': 'Left side', 'rightLabel': 'Right side'})
    g.addPass(SplitScreenPass, 'SplitScreenPass')
    AccumulatePass0 = createPass('AccumulatePass', {'enabled': False, 'outputSize': IOSize.Default, 'autoReset': True, 'precisionMode': AccumulatePrecision.Single, 'subFrameCount': 0, 'maxAccumulatedFrames': 0})
    g.addPass(AccumulatePass0, 'AccumulatePass0')
    ToneMapper0 = createPass('ToneMapper', {'outputSize': IOSize.Default, 'useSceneMetadata': True, 'exposureCompensation': 0.0, 'autoExposure': False, 'filmSpeed': 100.0, 'whiteBalance': False, 'whitePoint': 6500.0, 'operator': ToneMapOp.Aces, 'clamp': True, 'whiteMaxLuminance': 1.0, 'whiteScale': 11.199999809265137, 'fNumber': 1.0, 'shutter': 1.0, 'exposureMode': ExposureMode.AperturePriority})
    g.addPass(ToneMapper0, 'ToneMapper0')
    MySVGFPass = createPass('MySVGFPass', {'Enabled': True, 'Iterations': 4, 'FeedbackTap': 1, 'VarianceEpsilon': 9.999999747378752e-05, 'PhiColor': 10.0, 'PhiNormal': 128.0, 'Alpha': 0.05000000074505806, 'MomentsAlpha': 0.20000000298023224, 'UseSampleCount': False, 'Boost': True})
    g.addPass(MySVGFPass, 'MySVGFPass')
    SharedBuffer0 = createPass('SharedBuffer')
    g.addPass(SharedBuffer0, 'SharedBuffer0')
    SharedBuffer1 = createPass('SharedBuffer')
    g.addPass(SharedBuffer1, 'SharedBuffer1')
    CountToColor1 = createPass('CountToColor', {'MaxValue': 256})
    g.addPass(CountToColor1, 'CountToColor1')
    CountToColor2 = createPass('CountToColor', {'MaxValue': 256})
    g.addPass(CountToColor2, 'CountToColor2')
    SplitScreenPass0 = createPass('SplitScreenPass', {'splitLocation': 0.5, 'showTextLabels': False, 'leftLabel': 'Left side', 'rightLabel': 'Right side'})
    g.addPass(SplitScreenPass0, 'SplitScreenPass0')
    SplitScreenPass1 = createPass('SplitScreenPass', {'splitLocation': 0.25, 'showTextLabels': False, 'leftLabel': 'Left side', 'rightLabel': 'Right side'})
    g.addPass(SplitScreenPass1, 'SplitScreenPass1')
    SplitScreenPass2 = createPass('SplitScreenPass', {'splitLocation': 0.75, 'showTextLabels': False, 'leftLabel': 'Left side', 'rightLabel': 'Right side'})
    g.addPass(SplitScreenPass2, 'SplitScreenPass2')
    SplitScreenPass3 = createPass('SplitScreenPass', {'splitLocation': 0.5, 'showTextLabels': False, 'leftLabel': 'Left side', 'rightLabel': 'Right side'})
    g.addPass(SplitScreenPass3, 'SplitScreenPass3')
    CountToColor3 = createPass('CountToColor', {'MaxValue': 16})
    g.addPass(CountToColor3, 'CountToColor3')
    SharedBuffer2 = createPass('SharedBuffer')
    g.addPass(SharedBuffer2, 'SharedBuffer2')
    g.addEdge('GBufferRaster.viewW', 'PathTracer.viewW')
    g.addEdge('GBufferRaster.vbuffer', 'PathTracer.vbuffer')
    g.addEdge('GBufferRaster.mvec', 'PathTracer.mvec')
    g.addEdge('FoveatedPass.sampleCount', 'PathTracer.sampleCount')
    g.addEdge('FoveatedPass.sampleCount', 'CountToColor0.Count')
    g.addEdge('PathTracer.albedo', 'Composite.A')
    g.addEdge('PathTracer.specularAlbedo', 'Composite.B')
    g.addEdge('Composite.out', 'Composite0.A')
    g.addEdge('PathTracer.indirectAlbedo', 'Composite0.B')
    g.addEdge('AccumulatePass.output', 'ToneMapper.src')
    g.addEdge('Composite0.out', 'TwoHistorySVGFPass.Albedo')
    g.addEdge('PathTracer.color', 'TwoHistorySVGFPass.Color')
    g.addEdge('PathTracer.nrdEmission', 'TwoHistorySVGFPass.Emission')
    g.addEdge('GBufferRaster.posW', 'TwoHistorySVGFPass.WorldPosition')
    g.addEdge('GBufferRaster.normW', 'TwoHistorySVGFPass.WorldNormal')
    g.addEdge('GBufferRaster.linearZ', 'TwoHistorySVGFPass.LinearZ')
    g.addEdge('GBufferRaster.pnFwidth', 'TwoHistorySVGFPass.PositionNormalFwidth')
    g.addEdge('GBufferRaster.mvec', 'TwoHistorySVGFPass.MotionVec')
    g.addEdge('FoveatedPass.sampleCount', 'TwoHistorySVGFPass.SampleCount')
    g.addEdge('TwoHistorySVGFPass.Filtered image', 'AccumulatePass.input')
    g.addEdge('TwoHistorySVGFPass.History Weight', 'CountToColor.Count')
    g.addEdge('SharedBuffer.buffer', 'TwoHistorySVGFPass.HistoryWeight')
    g.addEdge('ToneMapper.dst', 'SplitScreenPass.leftInput')
    g.addEdge('AccumulatePass0.output', 'ToneMapper0.src')
    g.addEdge('ToneMapper0.dst', 'SplitScreenPass.rightInput')
    g.addEdge('MySVGFPass.Filtered image', 'AccumulatePass0.input')
    g.addEdge('Composite0.out', 'MySVGFPass.Albedo')
    g.addEdge('PathTracer.color', 'MySVGFPass.Color')
    g.addEdge('FoveatedPass.sampleCount', 'MySVGFPass.SampleCount')
    g.addEdge('PathTracer.nrdEmission', 'MySVGFPass.Emission')
    g.addEdge('GBufferRaster.linearZ', 'MySVGFPass.LinearZ')
    g.addEdge('GBufferRaster.pnFwidth', 'MySVGFPass.PositionNormalFwidth')
    g.addEdge('GBufferRaster.posW', 'MySVGFPass.WorldPosition')
    g.addEdge('GBufferRaster.normW', 'MySVGFPass.WorldNormal')
    g.addEdge('GBufferRaster.mvec', 'MySVGFPass.MotionVec')
    g.addEdge('SharedBuffer0.buffer', 'TwoHistorySVGFPass.wShort')
    g.addEdge('SharedBuffer1.buffer', 'TwoHistorySVGFPass.wLong')
    g.addEdge('TwoHistorySVGFPass.wShort', 'CountToColor1.Count')
    g.addEdge('TwoHistorySVGFPass.wLong', 'CountToColor2.Count')
    g.addEdge('CountToColor1.Color', 'SplitScreenPass0.leftInput')
    g.addEdge('CountToColor2.Color', 'SplitScreenPass0.rightInput')
    g.addEdge('TwoHistorySVGFPass.Illumination (short)', 'SplitScreenPass1.leftInput')
    g.addEdge('TwoHistorySVGFPass.Illumination (long)', 'SplitScreenPass1.rightInput')
    g.addEdge('TwoHistorySVGFPass.Filtered (short)', 'SplitScreenPass2.leftInput')
    g.addEdge('TwoHistorySVGFPass.Filtered (long)', 'SplitScreenPass2.rightInput')
    g.addEdge('SplitScreenPass1.output', 'SplitScreenPass3.leftInput')
    g.addEdge('SplitScreenPass2.output', 'SplitScreenPass3.rightInput')
    g.addEdge('TwoHistorySVGFPass.Sample Count', 'CountToColor3.Count')
    g.addEdge('SharedBuffer2.buffer', 'FoveatedPass.historySampleCount')
    g.addEdge('SharedBuffer2.buffer', 'MySVGFPass.HistoryWeight')
    g.markOutput('CountToColor.Color')
    g.markOutput('CountToColor0.Color')
    g.markOutput('PathTracer.color')
    g.markOutput('SplitScreenPass.output')
    g.markOutput('SplitScreenPass0.output')
    g.markOutput('CountToColor1.Color')
    g.markOutput('CountToColor2.Color')
    g.markOutput('SplitScreenPass3.output')
    g.markOutput('CountToColor3.Color')
    return g

g = render_graph_g()
try: m.addGraph(g)
except NameError: None
