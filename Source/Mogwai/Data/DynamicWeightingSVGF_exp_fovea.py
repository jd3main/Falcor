import subprocess
import sys
from pathlib import *
import gc
import math
from pprint import pprint
import json

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
from _log_utils import *

class FalcorEnoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, float2):
            return { "__float2__": True, "x": o.x, "y": o.y }
        return super().default(o)

class FalcorDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, o):
        if '__float2__' in o:
            return float2(o['x'], o['y'])
        return o

def __eq__(self, other):
    """Overrides the default implementation"""
    if isinstance(other, float2):
        return self.x == other.x and self.y == other.y
    print(f"using fallback __eq__ for {type(self)} and {type(other)}")
    return False

float2.__eq__ = __eq__

loadRenderPassLibrary('DLSSPass.dll')
loadRenderPassLibrary('AccumulatePass.dll')
loadRenderPassLibrary('BSDFViewer.dll')
loadRenderPassLibrary('Antialiasing.dll')
loadRenderPassLibrary('BlitPass.dll')
loadRenderPassLibrary('CSM.dll')
loadRenderPassLibrary('DebugPasses.dll')
loadRenderPassLibrary('PathTracer.dll')
loadRenderPassLibrary('PathTracerEx.dll')
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

DEFAULT_GT_SAMPLE_COUNT = 64
DEFAULT_OUTPUT_PATH = Path(__file__).parent/"Output"
DEFAULT_BASE_FILENAME = "Mogwai"

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
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=2)


def render_graph_g(iters, feedback, grad_iters, alpha=0.05,
                   dynamic_weighting_enabled=False, dynamic_weighting_params:dict={},
                   foveated_pass_enabled=False, foveated_pass_params:dict={},
                   output_sample_count=False,
                   sample_count=DEFAULT_GT_SAMPLE_COUNT,
                   debug_tag_enabled=False,
                   debug_output_enabled=False,
                   **kwargs):
    g = RenderGraph('g')

    GBufferRaster = createPass('GBufferRaster', {'outputSize': IOSize.Default, 'samplePattern': SamplePattern.Center, 'sampleCount': 16, 'useAlphaTest': True, 'adjustShadingNormals': True, 'forceCullMode': False, 'cull': CullMode.CullBack})
    g.addPass(GBufferRaster, 'GBufferRaster')

    VBufferRT = createPass('VBufferRT', {'outputSize': IOSize.Default, 'samplePattern': SamplePattern.Center, 'sampleCount': 16, 'useAlphaTest': True, 'adjustShadingNormals': True, 'forceCullMode': False, 'cull': CullMode.CullBack, 'useTraceRayInline': False, 'useDOF': True})
    g.addPass(VBufferRT, 'VBufferRT')

    Composite = createPass('Composite', {'mode': CompositeMode.Add, 'scaleA': 0.5, 'scaleB': 0.5, 'outputFormat': ResourceFormat.RGBA32Float})
    g.addPass(Composite, 'Composite')

    if foveated_pass_enabled:
        FoveatedPass = createPass('FoveatedPass', {
            'useHistory': False,
            'alpha': alpha,
            'foveaRadius': 300.0,
            'foveaSampleCount': 8.0,
            'periphSampleCount': 1.0,
            'shape': FoveaShape.CIRCLE,
            'foveaInputType': FoveaInputType.PROCEDURAL,
            'foveaMovePattern': FoveaMovePattern.LISSAJOUS,
            'foveaMoveRadius': float2(640.0, 360.0),
            'foveaMoveFreq': float2(0.4, 0.5),
            'foveaMovePhase': float2(math.pi/2, 0),
            'foveaMoveSpeed': 1000.0,
            'foveaMoveStayDuration': 0.5,
            'useRealTime': False,
            'flickerEnabled': False,
            'flickerBrightDurationMs': 1.0,
            'flickerDarkDurationMs': 1.0,
            **foveated_pass_params})
        g.addPass(FoveatedPass, 'FoveatedPass')
        PathTracer = createPass('PathTracer', {'samplesPerPixel': 1, 'maxSurfaceBounces': 10, 'maxDiffuseBounces': 3, 'maxSpecularBounces': 3, 'maxTransmissionBounces': 10, 'sampleGenerator': 0, 'useBSDFSampling': True, 'useRussianRoulette': False, 'useNEE': True, 'useMIS': True, 'misHeuristic': MISHeuristic.Balance, 'misPowerExponent': 2.0, 'emissiveSampler': EmissiveLightSamplerType.LightBVH, 'lightBVHOptions': LightBVHSamplerOptions(buildOptions=LightBVHBuilderOptions(splitHeuristicSelection=SplitHeuristic.BinnedSAOH, maxTriangleCountPerLeaf=10, binCount=16, volumeEpsilon=0.0010000000474974513, splitAlongLargest=False, useVolumeOverSA=False, useLeafCreationCost=True, createLeavesASAP=True, allowRefitting=True, usePreintegration=True, useLightingCones=True), useBoundingCone=True, useLightingCone=True, disableNodeFlux=False, useUniformTriangleSampling=True, solidAngleBoundMethod=SolidAngleBoundMethod.Sphere), 'useRTXDI': False, 'RTXDIOptions': RTXDIOptions(mode=RTXDIMode.SpatiotemporalResampling, presampledTileCount=128, presampledTileSize=1024, storeCompactLightInfo=True, localLightCandidateCount=24, infiniteLightCandidateCount=8, envLightCandidateCount=8, brdfCandidateCount=1, brdfCutoff=0.0, testCandidateVisibility=True, biasCorrection=RTXDIBiasCorrection.Basic, depthThreshold=0.10000000149011612, normalThreshold=0.5, samplingRadius=30.0, spatialSampleCount=1, spatialIterations=5, maxHistoryLength=20, boilingFilterStrength=0.0, rayEpsilon=0.0010000000474974513, useEmissiveTextures=False, enableVisibilityShortcut=False, enablePermutationSampling=False), 'useAlphaTest': True, 'adjustShadingNormals': False, 'maxNestedMaterials': 2, 'useLightsInDielectricVolumes': False, 'disableCaustics': False, 'specularRoughnessThreshold': 0.25, 'primaryLodMode': TexLODMode.Mip0, 'lodBias': 0.0, 'useNRDDemodulation': True, 'outputSize': IOSize.Default, 'colorFormat': ColorFormat.LogLuvHDR})
        g.addPass(PathTracer, 'PathTracer')
    else:
        PathTracer = createPass('PathTracerEx', {'samplesPerPixel': sample_count, 'maxSurfaceBounces': 10, 'maxDiffuseBounces': 3, 'maxSpecularBounces': 3, 'maxTransmissionBounces': 10, 'sampleGenerator': 0, 'useBSDFSampling': True, 'useRussianRoulette': False, 'useNEE': True, 'useMIS': True, 'misHeuristic': MISHeuristic.Balance, 'misPowerExponent': 2.0, 'emissiveSampler': EmissiveLightSamplerType.LightBVH, 'lightBVHOptions': LightBVHSamplerOptions(buildOptions=LightBVHBuilderOptions(splitHeuristicSelection=SplitHeuristic.BinnedSAOH, maxTriangleCountPerLeaf=10, binCount=16, volumeEpsilon=0.0010000000474974513, splitAlongLargest=False, useVolumeOverSA=False, useLeafCreationCost=True, createLeavesASAP=True, allowRefitting=True, usePreintegration=True, useLightingCones=True), useBoundingCone=True, useLightingCone=True, disableNodeFlux=False, useUniformTriangleSampling=True, solidAngleBoundMethod=SolidAngleBoundMethod.Sphere), 'useRTXDI': False, 'RTXDIOptions': RTXDIOptions(mode=RTXDIMode.SpatiotemporalResampling, presampledTileCount=128, presampledTileSize=1024, storeCompactLightInfo=True, localLightCandidateCount=24, infiniteLightCandidateCount=8, envLightCandidateCount=8, brdfCandidateCount=1, brdfCutoff=0.0, testCandidateVisibility=True, biasCorrection=RTXDIBiasCorrection.Basic, depthThreshold=0.10000000149011612, normalThreshold=0.5, samplingRadius=30.0, spatialSampleCount=1, spatialIterations=5, maxHistoryLength=20, boilingFilterStrength=0.0, rayEpsilon=0.0010000000474974513, useEmissiveTextures=False, enableVisibilityShortcut=False, enablePermutationSampling=False), 'useAlphaTest': True, 'adjustShadingNormals': False, 'maxNestedMaterials': 2, 'useLightsInDielectricVolumes': False, 'disableCaustics': False, 'specularRoughnessThreshold': 0.25, 'primaryLodMode': TexLODMode.Mip0, 'lodBias': 0.0, 'useNRDDemodulation': True, 'outputSize': IOSize.Default, 'colorFormat': ColorFormat.LogLuvHDR})
        g.addPass(PathTracer, 'PathTracer')

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
        'WeightedAlpha': alpha,
        'MomentsAlpha': 0.2,
        'GradientAlpha': 0.2,
        'GradientMidpoint': 0.01,
        'GammaSteepness': 100.0,
        'SelectionMode': SelectionMode.LOGISTIC,
        'SampleCountOverride': -1,
        'NormalizationMode': NormalizationMode.STANDARD_DEVIATION,
        'EnableDebugTag': debug_tag_enabled,
        'EnableDebugOutput': debug_output_enabled,
        **dynamic_weighting_params})
    g.addPass(SVGFPass, 'SVGFPass')

    g.addEdge('GBufferRaster.viewW', 'PathTracer.viewW')
    g.addEdge('VBufferRT.vbuffer', 'PathTracer.vbuffer')
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
    if output_sample_count and foveated_pass_enabled:
        g.markOutput('FoveatedPass.sampleCount')
    # g.markOutput('SVGFPass.OutGradient')
    # g.markOutput('SVGFPass.Illumination_U')
    # g.markOutput('SVGFPass.Illumination_W')
    # g.markOutput('SVGFPass.Filtered_Illumination_U')
    # g.markOutput('SVGFPass.Filtered_Illumination_W')
    # g.markOutput('SVGFPass.OutGamma')

    return g



def recordImages(start_time, end_time, fps:int=60, frames=AllFrames(),
                 output_path=DEFAULT_OUTPUT_PATH, base_filename=DEFAULT_BASE_FILENAME,
                 enable_profiler=True,
                 skip_capture_for_frames = 0):
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
    m.profiler.enabled = enable_profiler
    if enable_profiler:
        m.profiler.startCapture()
    start_frame = int(start_time * fps)
    end_frame = int(end_time * fps)
    for frame in range(start_frame, end_frame):
        print(f"frame={m.clock.frame} time={m.clock.time:.3f}")
        renderFrame()
        if frame in frames and frame >= skip_capture_for_frames:
            m.frameCapture.baseFilename = base_filename
            m.frameCapture.capture()
    if enable_profiler:
        capture = m.profiler.endCapture()
        m.profiler.enabled = False
        json.dump(capture, open(output_path/'profile.json', 'w'), indent=2)


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
        json.dump(data, f, cls=FalcorEnoder, indent=2)

def loadMetadata(path) -> dict:
    '''
    Load metadata from a file.
    '''
    path = Path(path)
    data = dict()
    try:
        with open(path/'metadata.txt', 'r') as f:
            data = dict(**json.load(f, cls=FalcorDecoder))
    except Exception as e:
        print(f'cannot load metadata from {path/"metadata.txt"}')
    return data

def countImages(path, filename_pattern:str) -> int:
    path = Path(path)
    frame_id = 1
    while True:
        img_path = path/filename_pattern.format(frame_id)
        if not img_path.exists():
            break
        frame_id += 1
    return frame_id - 1

scene_name: str = ''

def normalizeGraphParams(graph_params: dict) -> dict:
    if 'dynamic_weighting_enabled' in graph_params:
        if not graph_params['dynamic_weighting_enabled']:
            graph_params['grad_iters'] = 0
            graph_params['dynamic_weighting_params'] = {
                'SelectionMode': SelectionMode.UNWEIGHTED,
            }
        elif graph_params['dynamic_weighting_params']['SelectionMode'] == SelectionMode.UNWEIGHTED:
            graph_params['grad_iters'] = 0
            pop_keys = ['GradientMidpoint', 'GammaSteepness', 'WeightedAlpha', 'GradientAlpha']
            for k in pop_keys:
                if k in graph_params['dynamic_weighting_params']:
                    graph_params['dynamic_weighting_params'].pop(k)
        elif graph_params['dynamic_weighting_params']['SelectionMode'] == SelectionMode.WEIGHTED:
            graph_params['grad_iters'] = graph_params['feedback'] + 1
            pop_keys = ['GradientMidpoint', 'GammaSteepness', 'GradientAlpha']
            for k in pop_keys:
                if k in graph_params['dynamic_weighting_params']:
                    graph_params['dynamic_weighting_params'].pop(k)

        if 'weighted_alpha' not in graph_params and 'alpha' in graph_params:
            graph_params['weighted_alpha'] = graph_params['alpha']

    if 'foveated_pass_enabled' not in graph_params:
        graph_params['foveated_pass_enabled'] = False
    if not graph_params['foveated_pass_enabled']:
        graph_params['foveated_pass_params'] = {}

    if 'adaptive_pass_enabled' not in graph_params:
        graph_params['adaptive_pass_enabled'] = False
    if not graph_params['adaptive_pass_enabled']:
        graph_params['adaptive_pass_params'] = {}

    if 'alpha' not in graph_params:
        graph_params['alpha'] = 0.05


    return graph_params

def getOutputFolderName(scene_name: str, graph_params: dict) -> Path:
    '''
    Get the output path from graph_params and scene_name.
    '''
    folder_name_parts = []
    folder_name_parts.append(scene_name)

    if (graph_params['dynamic_weighting_enabled']
        and graph_params['dynamic_weighting_params']['SelectionMode'] not in [SelectionMode.UNWEIGHTED, SelectionMode.WEIGHTED]):
        folder_name_parts.append('iters({},{},{})'.format(
            graph_params['iters'], graph_params['feedback'], graph_params['grad_iters']))
    else:
        folder_name_parts.append('iters({},{})'.format(
            graph_params['iters'],  graph_params['feedback']))


    if graph_params['dynamic_weighting_enabled']:
        dw_params = graph_params['dynamic_weighting_params']

        selection_mode = dw_params['SelectionMode']
        if selection_mode == SelectionMode.LINEAR:
            folder_name_parts.append('Linear({},{})'.format(
                dw_params['GradientMidpoint'],
                dw_params['GammaSteepness']))
        elif selection_mode == SelectionMode.STEP:
            folder_name_parts.append('Step({})'.format(
                dw_params['GradientMidpoint']))
        elif selection_mode == SelectionMode.LOGISTIC:
            folder_name_parts.append('Logistic({},{})'.format(
                dw_params['GradientMidpoint'],
                dw_params['GammaSteepness']))
        elif selection_mode == SelectionMode.WEIGHTED:
            folder_name_parts.append('Weighted')
        elif selection_mode == SelectionMode.UNWEIGHTED:
            folder_name_parts.append('Unweighted')

    folder_name_parts.append('Alpha({})'.format(graph_params['alpha']))

    if graph_params['dynamic_weighting_enabled']:
        if selection_mode not in [SelectionMode.UNWEIGHTED]:
            folder_name_parts.append('WAlpha({})'.format(
                dw_params['WeightedAlpha']))

        if selection_mode not in [SelectionMode.UNWEIGHTED, SelectionMode.WEIGHTED]:
            folder_name_parts.append('GAlpha({})'.format(
                dw_params['GradientAlpha']))
            folder_name_parts.append('Norm({})'.format(
                NormalizationMode(dw_params['NormalizationMode']).name))


    if graph_params['foveated_pass_enabled']:
        fovea_params = graph_params['foveated_pass_params']
        assert fovea_params['foveaInputType'] == FoveaInputType.PROCEDURAL
        folder_name_parts.append('Foveated({},{},{})'.format(
            FoveaShape(fovea_params['shape']).name,
            FoveaMovePattern(fovea_params['foveaMovePattern']).name,
            fovea_params['foveaSampleCount']))
        if fovea_params['foveaMovePattern'] == FoveaMovePattern.LISSAJOUS:
            folder_name_parts.append('Lissajous({},{})'.format(
                fovea_params['foveaMoveFreq'],
                fovea_params['foveaMoveRadius']))
        elif fovea_params['foveaMovePattern'] == FoveaMovePattern.MOVE_AND_STAY:
            folder_name_parts.append('MoveAndStay({},{})'.format(
                fovea_params['foveaMoveSpeed'],
                fovea_params['foveaMoveStayDuration']))
    else:
        folder_name_parts.append(f'{graph_params["sample_count"]}')

    folder_name = '_'.join(folder_name_parts)
    return folder_name


def run(graph_params_override:dict={}, record_params_override:dict={}, force_record=False):
    graph_params = {
        'iters': 1,
        'feedback': 0,
        'grad_iters': 1,
        'alpha': 0.05,
        'dynamic_weighting_enabled': True,
        'dynamic_weighting_params': {},
        'foveated_pass_enabled': False,
        'foveated_pass_params': {},
        **graph_params_override
    }
    graph_params = normalizeGraphParams(graph_params)

    record_params = {
        'start_time': 0,
        'end_time': 20,
        'fps': 30,
        'frames': AllFrames(),
        'enable_profiler': True,
        **record_params_override
    }

    output_path_base = Path(__file__).parents[4]/'Record'
    folder_name = getOutputFolderName(scene_name, graph_params)
    output_path = output_path_base / folder_name
    if output_path.exists():
        if force_record:
            logW(f" Found existing record at \"{output_path}\".")
            print("Force continue recording.")
        else:
            g_params = normalizeGraphParams(loadMetadata(output_path))
            n_frames = int(record_params['fps'] * (record_params['end_time'] - record_params['start_time']))
            existing_frame_count = countImages(output_path, f'{record_params["fps"]}fps.SVGFPass.Filtered image.{{}}.exr')
            if g_params != graph_params:
                logW(f"[Warning] Found existing record with different parameters at: \"{output_path}\"")
                for k in g_params.keys():
                    if k not in graph_params:
                        print(f"key \"{k}\" not in graph_params")
                for k in graph_params.keys():
                    if k not in g_params:
                        print(f"key \"{k}\" not in g_params")
                for k in set(g_params.keys()).intersection(graph_params.keys()):
                    if g_params[k] != graph_params[k]:
                        print(f"{k}: {g_params[k]} != {graph_params[k]}")
                logW(f"Overwriting.")
            elif n_frames != existing_frame_count:
                logW(f"[Warning] Found existing record with different number of frames at: \"{output_path}\"")
                logW(f"Overwriting.")
            else:
                logW(f"[Warning] Found existing record with same parameters at \"{output_path}\".")
                logW(f"Skip recoding.")
                return

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
    storeMetadata(output_path, normalizeGraphParams({**graph_params}))

    m.removeGraph(g)
    gc.collect()


scene_path = Path(__file__).parents[4]/'Scenes'/'VeachAjar'/'VeachAjarAnimated.pyscene'
# scene_path = Path(__file__).parents[4]/'Scenes'/'VeachAjar'/'VeachAjar.pyscene'
# scene_path = Path(__file__).parents[4]/'Scenes'/'ORCA'/'Bistro'/'BistroExterior.pyscene'
# scene_path = Path(__file__).parents[4]/'Scenes'/'ORCA'/'Bistro'/'BistroInterior.fbx'
# scene_path = Path(__file__).parents[4]/'Scenes'/'ORCA'/'Bistro'/'BistroInterior_Wine.pyscene'
# scene_path = Path(__file__).parents[4]/'Scenes'/'ORCA'/'EmeraldSquare'/'EmeraldSquare_Day.pyscene'
# scene_path = Path(__file__).parents[4]/'Scenes'/'ORCA'/'SunTemple'/'SunTemple.pyscene'
scene_name = scene_path.stem

animation_lengths = {
    'VeachAjarAnimated': 20,
    'VeachAjar': 20,
    'BistroExterior': 100,
    'BistroInterior': 59.5,
    'BistroInterior_Wine': 59.5,
    'EmeraldSquare_Day': 10,
    'SunTemple': 20,
}

try:
    m.loadScene(scene_path)
except Exception as e:
    print(f"Failed to load scene: {scene_path}")
    print(e)
    raise e


common_record_params = {
    'fps': 30,
    'start_time': 0,
    'end_time': animation_lengths[scene_name],
    # 'end_time': 20,
}

common_graph_params = {
    'alpha': 0.05,
    'debug_tag_enabled': False,
    'debug_output_enabled': False,
}

common_dynamic_weighting_params = {
    'WeightedAlpha': 0.05,
    'GradientAlpha': 0.2,
}

foveated_params_override = {
    'shape': FoveaShape.CIRCLE,
    'foveaRadius': 300.0,
    'foveaInputType': FoveaInputType.PROCEDURAL,
    'foveaSampleCount': 8.0,
    'foveaMovePattern': FoveaMovePattern.LISSAJOUS,
    'foveaMoveRadius': float2(1280/2, 720/2),
    'foveaMoveFreq': float2(0.4, 0.5),
    'foveaMovePhase': float2(math.pi/2, 0),
    'foveaMoveSpeed': 1000.0,
    'foveaMoveStayDuration': 0.5,
}

gt_sample_Count = 96
use_no_filter_gt = True

# iters, feedback, grad_iters
iter_params = [
    # (2, -1, 0),
    # (2, 0, 1),
    # (2, 1, 2),
    # (3, -1, 0),
    # (3, 0, 1),
    # (3, 1, 2),
    (4, 0, 1),
    # (4, 1, 2),
]
# midpoints = [0, 0.05, 0.5, 1.0]
# steepnesses = [0.1, 1, 10]
# blending_func_params = [(m,s) for m in midpoints for s in steepnesses]
blending_func_params = [(0.5, 1.0)]

force_record_selections = False
force_record_step = False
force_record_unweighted = True
force_record_weighted = True
force_record_ground_truth = False

for iters, feedback, grad_iters in iter_params:
    # Try different parameters with dynamic weighting
    for midpoint, steepness in blending_func_params:
        logI(f"Run Dynamic Weighting: iters={iters}, feedback={feedback}, grad_iters={grad_iters}, midpoint={midpoint}, steepness={steepness}")
        run(graph_params_override = {
                'iters': iters,
                'feedback': feedback,
                'grad_iters': grad_iters,
                'dynamic_weighting_enabled': True,
                'dynamic_weighting_params': {
                    'GradientMidpoint': float(midpoint),
                    'GammaSteepness': float(steepness),
                    'SelectionMode': SelectionMode.LINEAR,
                    'SampleCountOverride': -1,
                    'NormalizationMode': NormalizationMode.STD,
                    **common_dynamic_weighting_params
                },
                'foveated_pass_enabled': True,
                'foveated_pass_params': foveated_params_override,
                **common_graph_params
            },
            record_params_override={
                **common_record_params,
            },
            force_record=force_record_selections)


    # for midpoint in midpoints:
    #     run(graph_params_override = {
    #             'iters': iters,
    #             'feedback': feedback,
    #             'grad_iters': grad_iters,
    #             'dynamic_weighting_enabled': True,
    #             'dynamic_weighting_params': {
    #                 'GradientAlpha': 0.2,
    #                 'GradientMidpoint': float(midpoint),
    #                 'GammaSteepness': float('inf'),
    #                 'SelectionMode': SelectionMode.STEP,
    #                 'SampleCountOverride': -1,
    #                 'NormalizationMode': NormalizationMode.STANDARD_DEVIATION,
    #             },
    #             'foveated_pass_enabled': True,
    #             'foveated_pass_params': foveated_params_override,
    #             **common_graph_params
    #         },
    #         record_params_override={
    #             **common_record_params,
    #         },
    #         force_record=force_record_step)

    # Unweighted
    logI("Run Unweighted")
    run(graph_params_override = {
            'iters': iters,
            'feedback': feedback,
            'grad_iters': 0,
            'dynamic_weighting_enabled': False,
            'dynamic_weighting_params': {
                'SelectionMode': SelectionMode.UNWEIGHTED,
                **common_dynamic_weighting_params
            },
            'foveated_pass_enabled': True,
            'foveated_pass_params': foveated_params_override,
            'output_sample_count': True,
            **common_graph_params
        },
        record_params_override={
            **common_record_params,
        },
        force_record=force_record_unweighted
    )

    # Weighted
    logI("Run Weighted")
    run(graph_params_override = {
            'iters': iters,
            'feedback': feedback,
            'grad_iters': 0,
            'dynamic_weighting_enabled': True,
            'dynamic_weighting_params': {
                'SelectionMode': SelectionMode.WEIGHTED,
                **common_dynamic_weighting_params
            },
            'foveated_pass_enabled': True,
            'foveated_pass_params': foveated_params_override,
            **common_graph_params
        },
        record_params_override={
            **common_record_params,
        },
        force_record=force_record_weighted
    )


    # Generate ground truth
    logI("Run Ground Truth")
    run(graph_params_override = {
            'iters': 0 if use_no_filter_gt else iters,
            'feedback': -1 if use_no_filter_gt else feedback,
            'grad_iters': 0 if use_no_filter_gt else iters,
            'dynamic_weighting_enabled': False,
            'foveated_pass_enabled': False,
            'sample_count': gt_sample_Count,
            **common_graph_params
        },
        record_params_override = {
            **common_record_params,
            'enable_profiler': False,
        },
        force_record=force_record_ground_truth
    )

print("All Done")
exit()
