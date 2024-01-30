import subprocess
import sys
from pathlib import *

def install(package):
    python_path = Path(sys.executable).parent/'Python/python.exe'
    subprocess.check_call([str(python_path), '-m', 'pip', 'install', package])

install("numpy")

from falcor import *
from enum import IntEnum, auto
import json
from typing import Union
import numpy as np
from DynamicWeighting_Common import *

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
loadRenderPassLibrary('TemporalDelayPass.dll')
loadRenderPassLibrary('ErrorMeasurePassEx.dll')
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
loadRenderPassLibrary('TestPasses.dll')
loadRenderPassLibrary('ToneMapper.dll')
loadRenderPassLibrary('TwoHistorySVGFPass.dll')
loadRenderPassLibrary('Utils.dll')

class AllFrames:
    '''
    A class that represents all frames.
    '''
    def __contains__(self, item):
        return True
    def __str__(self) -> str:
        return "AllFrames"
    def __dict__(self) -> dict:
        return dict()
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)


def render_graph_g(iters, feedback, grad_iters, alpha=0.05,
                   dynamic_weighting_enabled=False, dynamic_weighting_params:dict={},
                   foveated_pass_enabled=False, foveated_pass_params:dict={}):
    g = RenderGraph('g')

    GBufferRaster = createPass('GBufferRaster', {'outputSize': IOSize.Default, 'samplePattern': SamplePattern.Center, 'sampleCount': 16, 'useAlphaTest': True, 'adjustShadingNormals': True, 'forceCullMode': False, 'cull': CullMode.CullBack})
    g.addPass(GBufferRaster, 'GBufferRaster')

    Composite = createPass('Composite', {'mode': CompositeMode.Add, 'scaleA': 0.5, 'scaleB': 0.5, 'outputFormat': ResourceFormat.RGBA32Float})
    g.addPass(Composite, 'Composite')

    if foveated_pass_enabled:
        FoveatedPass = createPass('FoveatedPass', {
            'shape': FoveaShape.SPLIT_HORIZONTALLY,   # SplitHorizontally
            'foveaInputType': FoveaInputType.SHM,    # SMH
            'useHistory': False,
            'alpha': alpha,
            'foveaRadius': 200.0,
            'foveaSampleCount': 8.0,
            'periphSampleCount': 1.0,
            'foveaMoveRadius': 300.0,
            'foveaMoveFreq': 0.5,
            'foveaMoveDirection': 0,
            'useRealTime': False,
            'flickerEnabled': False,
            'flickerBrightDurationMs': 1.0,
            'flickerDarkDurationMs': 1.0,
            **foveated_pass_params})
        g.addPass(FoveatedPass, 'FoveatedPass')
        PathTracer = createPass('PathTracer', {'samplesPerPixel': 1, 'maxSurfaceBounces': 10, 'maxDiffuseBounces': 3, 'maxSpecularBounces': 3, 'maxTransmissionBounces': 10, 'sampleGenerator': 0, 'useBSDFSampling': True, 'useRussianRoulette': False, 'useNEE': True, 'useMIS': True, 'misHeuristic': MISHeuristic.Balance, 'misPowerExponent': 2.0, 'emissiveSampler': EmissiveLightSamplerType.LightBVH, 'lightBVHOptions': LightBVHSamplerOptions(buildOptions=LightBVHBuilderOptions(splitHeuristicSelection=SplitHeuristic.BinnedSAOH, maxTriangleCountPerLeaf=10, binCount=16, volumeEpsilon=0.0010000000474974513, splitAlongLargest=False, useVolumeOverSA=False, useLeafCreationCost=True, createLeavesASAP=True, allowRefitting=True, usePreintegration=True, useLightingCones=True), useBoundingCone=True, useLightingCone=True, disableNodeFlux=False, useUniformTriangleSampling=True, solidAngleBoundMethod=SolidAngleBoundMethod.Sphere), 'useRTXDI': False, 'RTXDIOptions': RTXDIOptions(mode=RTXDIMode.SpatiotemporalResampling, presampledTileCount=128, presampledTileSize=1024, storeCompactLightInfo=True, localLightCandidateCount=24, infiniteLightCandidateCount=8, envLightCandidateCount=8, brdfCandidateCount=1, brdfCutoff=0.0, testCandidateVisibility=True, biasCorrection=RTXDIBiasCorrection.Basic, depthThreshold=0.10000000149011612, normalThreshold=0.5, samplingRadius=30.0, spatialSampleCount=1, spatialIterations=5, maxHistoryLength=20, boilingFilterStrength=0.0, rayEpsilon=0.0010000000474974513, useEmissiveTextures=False, enableVisibilityShortcut=False, enablePermutationSampling=False), 'useAlphaTest': True, 'adjustShadingNormals': False, 'maxNestedMaterials': 2, 'useLightsInDielectricVolumes': False, 'disableCaustics': False, 'specularRoughnessThreshold': 0.25, 'primaryLodMode': TexLODMode.Mip0, 'lodBias': 0.0, 'useNRDDemodulation': True, 'outputSize': IOSize.Default, 'colorFormat': ColorFormat.LogLuvHDR})
        g.addPass(PathTracer, 'PathTracer')
    else:
        FoveatedPass = createPass('FoveatedPass', {
            'shape': FoveaShape.UNIFORM,
            'foveaInputType': FoveaInputType.NONE,
            'useHistory': False,
            'alpha': alpha,
            'foveaSampleCount': 16.0,
            **foveated_pass_params})
        g.addPass(FoveatedPass, 'FoveatedPass')
        PathTracer = createPass('PathTracer', {'samplesPerPixel': 16, 'maxSurfaceBounces': 10, 'maxDiffuseBounces': 3, 'maxSpecularBounces': 3, 'maxTransmissionBounces': 10, 'sampleGenerator': 0, 'useBSDFSampling': True, 'useRussianRoulette': False, 'useNEE': True, 'useMIS': True, 'misHeuristic': MISHeuristic.Balance, 'misPowerExponent': 2.0, 'emissiveSampler': EmissiveLightSamplerType.LightBVH, 'lightBVHOptions': LightBVHSamplerOptions(buildOptions=LightBVHBuilderOptions(splitHeuristicSelection=SplitHeuristic.BinnedSAOH, maxTriangleCountPerLeaf=10, binCount=16, volumeEpsilon=0.0010000000474974513, splitAlongLargest=False, useVolumeOverSA=False, useLeafCreationCost=True, createLeavesASAP=True, allowRefitting=True, usePreintegration=True, useLightingCones=True), useBoundingCone=True, useLightingCone=True, disableNodeFlux=False, useUniformTriangleSampling=True, solidAngleBoundMethod=SolidAngleBoundMethod.Sphere), 'useRTXDI': False, 'RTXDIOptions': RTXDIOptions(mode=RTXDIMode.SpatiotemporalResampling, presampledTileCount=128, presampledTileSize=1024, storeCompactLightInfo=True, localLightCandidateCount=24, infiniteLightCandidateCount=8, envLightCandidateCount=8, brdfCandidateCount=1, brdfCutoff=0.0, testCandidateVisibility=True, biasCorrection=RTXDIBiasCorrection.Basic, depthThreshold=0.10000000149011612, normalThreshold=0.5, samplingRadius=30.0, spatialSampleCount=1, spatialIterations=5, maxHistoryLength=20, boilingFilterStrength=0.0, rayEpsilon=0.0010000000474974513, useEmissiveTextures=False, enableVisibilityShortcut=False, enablePermutationSampling=False), 'useAlphaTest': True, 'adjustShadingNormals': False, 'maxNestedMaterials': 2, 'useLightsInDielectricVolumes': False, 'disableCaustics': False, 'specularRoughnessThreshold': 0.25, 'primaryLodMode': TexLODMode.Mip0, 'lodBias': 0.0, 'useNRDDemodulation': True, 'outputSize': IOSize.Default, 'colorFormat': ColorFormat.LogLuvHDR})
        g.addPass(PathTracer, 'PathTracer')

    DynamicWeightingSVGF = createPass('DynamicWeightingSVGF', {'Enabled': True, 'DynamicWeighingEnabled': True, 'Iterations': 2, 'FeedbackTap': 0, 'GradientFilterIterations': 1, 'VarianceEpsilon': 9.999999747378752e-05, 'PhiColor': 10.0, 'PhiNormal': 128.0, 'Alpha': 0.05000000074505806, 'MomentsAlpha': 0.20000000298023224, 'GradientAlpha': 0.20000000298023224, 'GradientMidpoint': 0.004999999888241291, 'GammaSteepness': 300.0, 'SelectionMode': 4, 'SampleCountOverride': -1, 'NormalizationMode': 3})
    g.addPass(DynamicWeightingSVGF, 'DynamicWeightingSVGF')

    SVGFPass = createPass('DynamicWeightingSVGF', {
        'Enabled': True,
        'DynamicWeighingEnabled': dynamic_weighting_enabled,
        'Iterations': iters,
        'FeedbackTap': feedback,
        'GradientFilterIterations': grad_iters,
        'VarianceEpsilon': 0.0001,
        'PhiColor': 10.0,
        'PhiNormal': 128.0,
        'Alpha': alpha,
        'MomentsAlpha': 0.2,
        'GradientAlpha': 0.2,
        'GradientMidpoint': 0.01,
        'GammaSteepness': 100.0,
        'SelectionMode': SelectionMode.LOGISTIC,
        'SampleCountOverride': -1,
        'NormalizationMode': NormalizationMode.STANDARD_DEVIATION,
        **dynamic_weighting_params})
    g.addPass(SVGFPass, 'SVGFPass')

    Composite0 = createPass('Composite', {'mode': CompositeMode.Add, 'scaleA': 0.5, 'scaleB': 0.5, 'outputFormat': ResourceFormat.RGBA32Float})
    g.addPass(Composite0, 'Composite0')

    g.addEdge('GBufferRaster.viewW', 'PathTracer.viewW')
    g.addEdge('GBufferRaster.vbuffer', 'PathTracer.vbuffer')
    g.addEdge('GBufferRaster.mvec', 'PathTracer.mvec')
    g.addEdge('PathTracer.albedo', 'Composite.A')
    g.addEdge('PathTracer.specularAlbedo', 'Composite.B')
    g.addEdge('PathTracer.color', 'SVGFPass.Color')
    g.addEdge('Composite.out', 'SVGFPass.Albedo')
    g.addEdge('PathTracer.nrdEmission', 'SVGFPass.Emission')
    g.addEdge('GBufferRaster.mvec', 'SVGFPass.MotionVec')
    g.addEdge('GBufferRaster.linearZ', 'SVGFPass.LinearZ')
    g.addEdge('GBufferRaster.pnFwidth', 'SVGFPass.PositionNormalFwidth')
    g.addEdge('GBufferRaster.posW', 'SVGFPass.WorldPosition')
    g.addEdge('GBufferRaster.normW', 'SVGFPass.WorldNormal')
    if foveated_pass_enabled:
        g.addEdge('FoveatedPass.sampleCount', 'PathTracer.sampleCount')
        g.addEdge('FoveatedPass.sampleCount', 'SVGFPass.SampleCount')

    g.markOutput('SVGFPass.Filtered image')
    # if foveated_pass_enabled:
    #     g.markOutput('FoveatedPass.sampleCount')
    # g.markOutput('SVGFPass.OutGradient')
    # g.markOutput('SVGFPass.Illumination_U')
    # g.markOutput('SVGFPass.Illumination_W')
    # g.markOutput('SVGFPass.Filtered_Illumination_U')
    # g.markOutput('SVGFPass.Filtered_Illumination_W')
    # g.markOutput('SVGFPass.OutGamma')

    return g

DEFAULT_OUTPUT_PATH = Path(__file__).parent/"Output"
DEFAULT_BASE_FILENAME = "Mogwai"



def recordImages(start_time, end_time, fps:int=60, frames=AllFrames(),
                 output_path=DEFAULT_OUTPUT_PATH, base_filename=DEFAULT_BASE_FILENAME):
    '''
    Record images from start_time to end_time at fps.
    '''

    print(f"output path: {output_path}")
    # ensure output path exists
    Path(output_path).mkdir(parents=True, exist_ok=True)

    # m.clock.pause()
    m.clock.framerate = fps
    m.clock.time = start_time
    m.frameCapture.outputDir = output_path
    m.frameCapture.baseFilename = base_filename

    renderFrame()

    start_frame = int(start_time * fps)
    end_frame = int(end_time * fps)
    for frame in range(start_frame, end_frame):
        print(f"frame={m.clock.frame} time={m.clock.time:.3f}")
        renderFrame()
        if frame in frames:
            m.frameCapture.baseFilename = base_filename
            m.frameCapture.capture()


def recordVideo(start_time, end_time, fps=60, codec="Raw", bitrate_mbps=4.0, gopSize=10,
                output_path=DEFAULT_OUTPUT_PATH, base_filename=DEFAULT_BASE_FILENAME, exit_on_done=True):
    '''
    This function is not tested.
    '''

    print(f"output path: {output_path}")
    # ensure output path exists
    Path(output_path).mkdir(parents=True, exist_ok=True)

    start_frame = start_time * fps
    end_frame = end_time * fps
    m.clock.time = start_time
    if exit_on_done:
        m.clock.exitFrame = end_frame+1
    m.clock.framerate = fps
    m.videoCapture.outputDir = output_path
    m.videoCapture.baseFilename = base_filename
    m.videoCapture.codec = codec
    m.videoCapture.fps = fps
    m.videoCapture.bitrate = bitrate_mbps
    m.videoCapture.gopSize = gopSize
    m.videoCapture.addRanges(m.activeGraph, [[start_frame, end_frame]])


def storeMetadata(output_path: Union[str,Path], data):
    '''
    Store metadata to a file.
    '''
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    with open(output_path/'metadata.txt', 'w') as f:
        json.dump(data, f)

def loadMetadata(path) -> dict:
    '''
    Load metadata from a file.
    '''
    path = Path(path)
    data = dict()
    try:
        with open(path/'metadata.txt', 'r') as f:
            data = dict(**json.load(f))
    except Exception as e:
        print(f'cannot load metadata from {path/"metadata.txt"}')
    return data


scene_name: str = ''

def run(graph_params_override:dict={}, record_params_override:dict={}, force_record=False):
    graph_params = {
        'iters': 1,
        'feedback': 0,
        'grad_iters': 1,
        'alpha': 0.05,
        'dynamic_weighting_enabled': True,
        'dynamic_weighting_params': {},
        'foveated_pass_enabled': True,
        'foveated_pass_params': {},
        **graph_params_override
    }

    record_params = {
        'start_time': 0,
        'end_time': 20,
        'fps': 30,
        'frames': AllFrames(),
        **record_params_override
    }

    output_path_base = Path(__file__).parents[4]/'Record'
    while True:
        folder_name_parts = []
        folder_name_parts.append(scene_name)
        folder_name_parts.append('iters({},{},{})'.format(
            graph_params['iters'], graph_params['feedback'], graph_params['grad_iters']))
        if graph_params['dynamic_weighting_enabled']:
            selection_mode = graph_params['dynamic_weighting_params']['SelectionMode']
            if selection_mode == SelectionMode.LINEAR:
                folder_name_parts.append('Linear({},{})'.format(
                    graph_params['dynamic_weighting_params']['GradientMidpoint'],
                    graph_params['dynamic_weighting_params']['GammaSteepness']))
            elif selection_mode == SelectionMode.STEP:
                folder_name_parts.append('Step({})'.format(
                    graph_params['dynamic_weighting_params']['GradientMidpoint']))
            elif selection_mode == SelectionMode.LOGISTIC:
                folder_name_parts.append('Logistic({},{})'.format(
                    graph_params['dynamic_weighting_params']['GradientMidpoint'],
                    graph_params['dynamic_weighting_params']['GammaSteepness']))
            elif selection_mode == SelectionMode.WEIGHTED:
                folder_name_parts.append('Weighted')
            elif selection_mode == SelectionMode.UNWEIGHTED:
                folder_name_parts.append('Unweighted')

            if selection_mode not in [SelectionMode.UNWEIGHTED, SelectionMode.WEIGHTED]:
                folder_name_parts.append('GAlpha({})'.format(
                    graph_params['dynamic_weighting_params']['GradientAlpha']))
                folder_name_parts.append('Norm({})'.format(
                    NormalizationMode(graph_params['dynamic_weighting_params']['NormalizationMode']).name))

        if graph_params['foveated_pass_enabled']:
            folder_name_parts.append('Foveated({},{},{})'.format(
                FoveaShape(graph_params['foveated_pass_params']['shape']).name,
                FoveaInputType(graph_params['foveated_pass_params']['foveaInputType']).name,
                graph_params['foveated_pass_params']['foveaSampleCount']))

        # folder_name_parts.append(str(i))
        folder_name = '_'.join(folder_name_parts)
        output_path = output_path_base / folder_name
        if output_path.exists():
            if force_record:
                print(f"[Warning] Found existing record at \"{output_path}\". Force continue recording.")
                break
            g_params = loadMetadata(output_path)
            if g_params == graph_params:
                print(f"[Warning] Found existing record with same parameters at \"{output_path}\". Skip recording.")
                return
            else:
                print(f"[Warning] Found existing record with different parameters at \"{output_path}\". Continue recording.")
                break
        else:
            break

    base_filename = '{fps}fps'.format(
        fps = record_params['fps'])


    # import DynamicWeightingSVGF_err2
    # g = DynamicWeightingSVGF_err2.render_graph_g(graph_params['iters'], graph_params['feedback'], graph_params['grad_iters'])
    g = render_graph_g(**graph_params)
    try:
        m.addGraph(g)
    except Exception as e:
        print(f"Failed to add graph")
        print(e)
        raise e

    recordImages(**record_params, output_path=output_path, base_filename=base_filename)
    storeMetadata(output_path, {**graph_params})

    m.removeGraph(g)


scene_path = Path(__file__).parents[4]/'Scenes'/'VeachAjar'/'VeachAjarAnimated.pyscene'
# scene_path = Path(__file__).parents[4]/'Scenes'/'ORCA'/'Bistro'/'BistroExterior.pyscene'
# scene_path = Path(__file__).parents[4]/'Scenes'/'ORCA'/'EmeraldSquare'/'EmeraldSquare_Day.pyscene'
# scene_path = Path(__file__).parents[4]/'Scenes'/'ORCA'/'SunTemple'/'SunTemple.pyscene'
scene_name = scene_path.stem

try:
    m.loadScene(scene_path)
except Exception as e:
    print(f"Failed to load scene: {scene_path}")
    print(e)
    raise e


common_record_params = {
    'fps': 30,
    'start_time': 0,
    'end_time': 20,
}

common_graph_params = {
    'alpha': 0.05,
}

foveated_params_override = {
    'shape': FoveaShape.SPLIT_HORIZONTALLY,
    'foveaInputType': FoveaInputType.SHM,
    'foveaSampleCount': 8.0,
    'foveaMoveRadius': 300.0,
    'foveaMoveFreq': 0.5,
    'foveaMoveDirection': 0,
}

# iters, feedback, grad_iters
iter_params = [
    # (0, -1, 0),
    # (1, -1, 1),
    (2, -1, 2),
    # (3, -1, 3),
    # (4, -1, 4),
    # (1, 0, 1),
    # (2, 0, 2),
    # (2, 1, 2),
]

for iters, feedback, grad_iters in iter_params:
    # Try different parameters with dynamic weighting
    for midpoint in [0.0, 0.00001, 0.0001, 0.001, 0.01, 0.1, 1.0]:
        for steepness in [0.5, 5.0, 50.0, 500.0, 5000.0]:
            run(graph_params_override = {
                    'iters': iters,
                    'feedback': feedback,
                    'grad_iters': grad_iters,
                    'dynamic_weighting_enabled': True,
                    'dynamic_weighting_params': {
                        'GradientAlpha': 0.2,
                        'GradientMidpoint': float(midpoint),
                        'GammaSteepness': float(steepness),
                        'SelectionMode': SelectionMode.LINEAR,
                        'SampleCountOverride': -1,
                        'NormalizationMode': NormalizationMode.STANDARD_DEVIATION,
                    },
                    'foveated_pass_enabled': True,
                    'foveated_pass_params': foveated_params_override,
                    **common_graph_params
                },
                record_params_override={
                    **common_record_params,
                },
                force_record=False)

    # Unweighted
    print("Run Unweighted")
    run(graph_params_override = {
            'iters': iters,
            'feedback': feedback,
            'grad_iters': grad_iters,
            'dynamic_weighting_enabled': False,
            'dynamic_weighting_params': {
                'SelectionMode': SelectionMode.UNWEIGHTED,
            },
            'foveated_pass_enabled': True,
            'foveated_pass_params': foveated_params_override,
            **common_graph_params
        },
        record_params_override={
            **common_record_params,
        },
        force_record=False
    )

    # Weighted
    print("Run Weighted")
    run(graph_params_override = {
            'iters': iters,
            'feedback': feedback,
            'grad_iters': grad_iters,
            'dynamic_weighting_enabled': True,
            'dynamic_weighting_params': {
                'SelectionMode': SelectionMode.WEIGHTED,
            },
            'foveated_pass_enabled': True,
            'foveated_pass_params': foveated_params_override,
            **common_graph_params
        },
        record_params_override={
            **common_record_params,
        },
        force_record=False
    )


    # Generate ground truth
    print("Run Ground Truth")
    run(graph_params_override = {
            'iters': iters,
            'feedback': feedback,
            'grad_iters': grad_iters,
            'dynamic_weighting_enabled': False,
            'foveated_pass_enabled': False,
            **common_graph_params
        },
        record_params_override={
            **common_record_params,
        },
        force_record=False
    )

    print("All Done")
exit()
