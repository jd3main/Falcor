import subprocess
import sys
from pathlib import *
import gc
import math
from pprint import pprint
import json
from time import sleep
import argparse

def install(package):
    python_path = Path(sys.executable).parent/'Python/python.exe'
    subprocess.check_call([str(python_path), '-m', 'pip', 'install', package])

install("numpy")
install("tqdm")

from falcor import *
from enum import IntEnum, auto
import json
from typing import Union
import numpy as np
from tqdm import trange

from DynamicWeighting_Common import *
from _log_utils import *
from _animation_lengths import animation_lengths

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


def render_graph_g(iters, feedback, alpha=0.05,
                   svgf_enabled=True, spatial_filter_enabled=True,
                   dynamic_weighting_enabled=False, dynamic_weighting_params:dict={},
                   foveated_pass_enabled=False, foveated_pass_params:dict={},
                   output_sample_count=False,
                   sample_count=1,
                   repeat_sample_count=1,
                   debug_tag_enabled=False,
                   debug_output_enabled=False,
                   output_tone_mappped=False,
                   no_record=False,
                   **kwargs):

    if sample_count > 8:
        assert sample_count % 8 == 0
        repeat_sample_count = sample_count // 8
        sample_count = 8

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
        PathTracer = createPass('PathTracerEx', {'samplesPerPixel': sample_count, 'repeat': repeat_sample_count, 'maxSurfaceBounces': 10, 'maxDiffuseBounces': 3, 'maxSpecularBounces': 3, 'maxTransmissionBounces': 10, 'sampleGenerator': 0, 'useBSDFSampling': True, 'useRussianRoulette': False, 'useNEE': True, 'useMIS': True, 'misHeuristic': MISHeuristic.Balance, 'misPowerExponent': 2.0, 'emissiveSampler': EmissiveLightSamplerType.LightBVH, 'lightBVHOptions': LightBVHSamplerOptions(buildOptions=LightBVHBuilderOptions(splitHeuristicSelection=SplitHeuristic.BinnedSAOH, maxTriangleCountPerLeaf=10, binCount=16, volumeEpsilon=0.0010000000474974513, splitAlongLargest=False, useVolumeOverSA=False, useLeafCreationCost=True, createLeavesASAP=True, allowRefitting=True, usePreintegration=True, useLightingCones=True), useBoundingCone=True, useLightingCone=True, disableNodeFlux=False, useUniformTriangleSampling=True, solidAngleBoundMethod=SolidAngleBoundMethod.Sphere), 'useRTXDI': False, 'RTXDIOptions': RTXDIOptions(mode=RTXDIMode.SpatiotemporalResampling, presampledTileCount=128, presampledTileSize=1024, storeCompactLightInfo=True, localLightCandidateCount=24, infiniteLightCandidateCount=8, envLightCandidateCount=8, brdfCandidateCount=1, brdfCutoff=0.0, testCandidateVisibility=True, biasCorrection=RTXDIBiasCorrection.Basic, depthThreshold=0.10000000149011612, normalThreshold=0.5, samplingRadius=30.0, spatialSampleCount=1, spatialIterations=5, maxHistoryLength=20, boilingFilterStrength=0.0, rayEpsilon=0.0010000000474974513, useEmissiveTextures=False, enableVisibilityShortcut=False, enablePermutationSampling=False), 'useAlphaTest': True, 'adjustShadingNormals': False, 'maxNestedMaterials': 2, 'useLightsInDielectricVolumes': False, 'disableCaustics': False, 'specularRoughnessThreshold': 0.25, 'primaryLodMode': TexLODMode.Mip0, 'lodBias': 0.0, 'useNRDDemodulation': True, 'outputSize': IOSize.Default, 'colorFormat': ColorFormat.LogLuvHDR})
        g.addPass(PathTracer, 'PathTracer')

    SVGFPass = createPass('DynamicWeightingSVGF', {
        'Enabled': svgf_enabled,
        'SpatialFilterEnabled': spatial_filter_enabled,
        'DynamicWeighingEnabled': dynamic_weighting_enabled,
        'Iterations': iters,
        'FeedbackTap': feedback,
        'VarianceEpsilon': 0.0001,
        'PhiColor': 10.0,
        'PhiNormal': 128.0,
        'Alpha': alpha,
        'WeightedAlpha': alpha,
        'MomentsAlpha': 0.2,
        'GradientAlpha': 0.2,
        'GradientMidpoint': 0.5,
        'GammaSteepness': 1.0,
        'SelectionMode': SelectionMode.LINEAR,
        'SampleCountOverride': -1,
        'NormalizationMode': NormalizationMode.STD,
        'EnableDebugTag': debug_tag_enabled,
        'EnableDebugOutput': debug_output_enabled,
        **dynamic_weighting_params})
    g.addPass(SVGFPass, 'SVGFPass')

    if output_tone_mappped:
        ToneMapper = createPass('ToneMapper', {'outputSize': IOSize.Default, 'useSceneMetadata': True, 'exposureCompensation': 0.0, 'autoExposure': False, 'filmSpeed': 100.0, 'whiteBalance': False, 'whitePoint': 6500.0, 'operator': ToneMapOp.Aces, 'clamp': True, 'whiteMaxLuminance': 1.0, 'whiteScale': 11.199999809265137, 'fNumber': 1.0, 'shutter': 1.0, 'exposureMode': ExposureMode.AperturePriority})
        g.addPass(ToneMapper, 'ToneMapper')

    # Edges
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

    if output_tone_mappped:
        g.addEdge('SVGFPass.Filtered image', 'ToneMapper.src')


    # Outputs
    g.markOutput('SVGFPass.Filtered image')
    if output_sample_count and foveated_pass_enabled:
        g.markOutput('FoveatedPass.sampleCount')

    if output_tone_mappped:
        g.markOutput('ToneMapper.dst')

    # g.markOutput('SVGFPass.OutGradient')
    # g.markOutput('SVGFPass.Illumination_U')
    # g.markOutput('SVGFPass.Illumination_W')
    # g.markOutput('SVGFPass.Filtered_Illumination_U')
    # g.markOutput('SVGFPass.Filtered_Illumination_W')
    # g.markOutput('SVGFPass.OutGamma')

    return g



def recordImages(start_time, end_time, fps:int=60, frames=AllFrames(),
                 output_path=DEFAULT_OUTPUT_PATH, base_filename=DEFAULT_BASE_FILENAME,
                 enable_profiler=False,
                 no_record=False,
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
    print()
    m.profiler.enabled = enable_profiler
    if enable_profiler:
        m.profiler.startCapture()
    start_frame = int(start_time * fps)
    end_frame = int(end_time * fps)
    t_range = trange(start_frame, end_frame, ncols=80)
    for frame in t_range:
        renderFrame()
        if frame in frames and frame >= skip_capture_for_frames:
            m.frameCapture.baseFilename = base_filename
            if not no_record:
                m.frameCapture.capture()
        t_range.set_postfix_str(f"frame={m.clock.frame} time={m.clock.time:.3f}")
    print()
    if enable_profiler:
        capture = m.profiler.endCapture()
        m.profiler.enabled = False
        json.dump(capture, open(output_path/'profile.json', 'w'), indent=2)
        print(f"Profiler data saved to {output_path/'profile.json'}")


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
        logE(f'cannot load metadata from {path/"metadata.txt"}')
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


def getOutputFolderName(scene_name: str, graph_params: dict, debug=False) -> Path:
    '''
    Get the output path from graph_params and scene_name.
    '''
    folder_name_parts = []
    folder_name_parts.append(scene_name)

    if graph_params['svgf_enabled']:
        folder_name_parts.append('iters({},{})'.format(
            graph_params['iters'],  graph_params['feedback']))

    if graph_params['dynamic_weighting_enabled']:
        dw_params = graph_params['dynamic_weighting_params']

        if 'FilterGradientEnabled' in dw_params and dw_params['FilterGradientEnabled']:
            folder_name_parts.append('FG')

        if 'BestGammaEnabled' in dw_params and dw_params['BestGammaEnabled']:
            folder_name_parts.append('BG')

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

    if graph_params['svgf_enabled']:
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

        if fovea_params['shape'] == FoveaShape.CIRCLE:
            folder_name_parts.append('Circle({:.6g})'.format(
                fovea_params['foveaRadius']))

        if fovea_params['foveaMovePattern'] == FoveaMovePattern.LISSAJOUS:
            folder_name_parts.append('Lissajous([{:.6g},{:.6g}],[{:.6g},{:.6g}])'.format(
                fovea_params['foveaMoveFreq'].x,
                fovea_params['foveaMoveFreq'].y,
                fovea_params['foveaMoveRadius'].x,
                fovea_params['foveaMoveRadius'].y))
        elif fovea_params['foveaMovePattern'] == FoveaMovePattern.MOVE_AND_STAY:
            folder_name_parts.append('MoveAndStay({:.6g},{:.6g})'.format(
                fovea_params['foveaMoveSpeed'],
                fovea_params['foveaMoveStayDuration']))
    else:
        folder_name_parts.append(f'{graph_params["sample_count"]}')

    if debug:
        folder_name_parts.append('d')

    folder_name = '_'.join(folder_name_parts)
    return folder_name


def run(graph_params:dict={}, record_params_override:dict={}, force_record=False, debug=False):

    graph_params = normalizeGraphParams(graph_params)

    record_params = {
        'start_time': 0,
        'end_time': 20,
        'fps': 30,
        'frames': AllFrames(),
        'enable_profiler': False,
        **record_params_override
    }

    output_path_base = Path(__file__).parents[4]/'Record'
    folder_name = getOutputFolderName(scene_name, graph_params, debug=debug)
    output_path = output_path_base / folder_name
    if output_path.exists() and not record_params['no_record']:
        if force_record:
            logW(f" Found existing record at \"{output_path}\".")
            print("Force continue recording.")
        else:
            existing_params = loadMetadata(output_path)
            if existing_params == {}:
                logW(f"Cannot load metadata from \"{output_path}\"")
                logW(f"Overwriting.")
            else:
                g_params = normalizeGraphParams(existing_params)
                n_frames = int(record_params['fps'] * (record_params['end_time'] - record_params['start_time']))
                filename_pattern = f'{record_params["fps"]}fps.SVGFPass.Filtered image.{{}}.exr'
                existing_frame_count = countImages(output_path, filename_pattern)
                if g_params != graph_params:
                    logW(f'[Warning] Found existing record with different parameters')
                    logW(f'\tat: "{output_path}"')
                    for k in g_params.keys():
                        if k not in graph_params:
                            print(f'key "{k}" not in graph_params')
                    for k in graph_params.keys():
                        if k not in g_params:
                            print(f'key "{k}" not in g_params')
                    for k in set(g_params.keys()).intersection(graph_params.keys()):
                        if g_params[k] != graph_params[k]:
                            print(f'{k}: {g_params[k]} != {graph_params[k]}')
                    logW(f"Overwriting.")
                elif n_frames < existing_frame_count:
                    logW(f'[Warning] Found existing record with {existing_frame_count} frames while {n_frames} frames are needed.')
                    logW(f'\tat: \"{output_path}\"')
                    logW(f'Removing extra frames.')
                    for i in range(n_frames+1, existing_frame_count+1):
                        img_path = output_path/filename_pattern.format(i)
                        print(f"removing {img_path}")
                        if img_path.exists():
                            img_path.unlink()
                    return
                elif n_frames > existing_frame_count:
                    logW(f'[Warning] Found existing record with {existing_frame_count} frames while {n_frames} frames are needed.')
                    logW(f'\tat: "{output_path}"')
                    logW(f'Overwriting.')
                else:
                    logW(f'[Warning] Found existing record with same parameters.')
                    logW(f'\tat "{output_path}".')
                    logW(f'Skip recoding.')
                    return

    base_filename = '{fps}fps'.format(
        fps = record_params['fps'])

    g = render_graph_g(**graph_params)
    try:
        m.addGraph(g)
    except Exception as e:
        print(f"Failed to add graph")
        print(e)
        raise e

    recordImages(**record_params, output_path=output_path, base_filename=base_filename)

    if not record_params['no_record']:
        storeMetadata(output_path, normalizeGraphParams({**graph_params}))

    m.removeGraph(g)
    gc.collect()

scene_paths = [
    # Path(__file__).parents[4]/'Scenes'/'VeachAjar'/'VeachAjar.pyscene',
    Path(__file__).parents[4]/'Scenes'/'VeachAjar'/'VeachAjarAnimated.pyscene',
    # Path(__file__).parents[4]/'Scenes'/'VeachAjar'/'VeachAjarAnimated2.pyscene',
    # Path(__file__).parents[4]/'Scenes'/'ORCA'/'Bistro'/'BistroExterior.pyscene',
    # Path(__file__).parents[4]/'Scenes'/'ORCA'/'Bistro'/'BistroInterior.fbx',
    # Path(__file__).parents[4]/'Scenes'/'ORCA'/'Bistro'/'BistroInterior_Wine.pyscene',
    # Path(__file__).parents[4]/'Scenes'/'ORCA'/'SunTemple'/'SunTemple.pyscene',
    # Path(__file__).parents[4]/'Scenes'/'ORCA'/'EmeraldSquare'/'EmeraldSquare_Day.pyscene',
    # Path(__file__).parents[4]/'Scenes'/'ORCA'/'EmeraldSquare'/'EmeraldSquare_Dusk.pyscene',
    # Path(__file__).parents[4]/'Scenes'/'ORCA'/'ZeroDay'/'MEASURE_ONE'/'MEASURE_ONE.fbx',
    # Path(__file__).parents[4]/'Scenes'/'ORCA'/'ZeroDay'/'MEASURE_SEVEN'/'MEASURE_SEVEN.fbx',
    # Path(__file__).parents[4]/'Scenes'/'ORCA'/'ZeroDay'/'ZeroDay_1.pyscene',
    # Path(__file__).parents[4]/'Scenes'/'ORCA'/'ZeroDay'/'ZeroDay_7.pyscene',
    # Path(__file__).parents[4]/'Scenes'/'ORCA'/'ZeroDay'/'ZeroDay_7c.pyscene',
]



### Argument parsing

argv = ' '.join([
    '-n STD',
    '--bg',
    '--fg',
    '--profile',
    '--no_record',
    '-s f1',
    # '--output_sample_count',
    # '--output_tone_mappped',
    # '--debug',
]).split(' ')

parser = argparse.ArgumentParser()
parser.add_argument('-n', '--norm_mode', type=str, default=NormalizationMode.STD.name, help='normalization mode')
parser.add_argument('--fg', action='store_true', help='filter gradient')
parser.add_argument('--bg', action='store_true', help='best gamma')
parser.add_argument('--profile', action='store_true', help='enable profiler')
parser.add_argument('--no_record', action='store_true', help='do not record')
parser.add_argument('--output_sample_count', action='store_true', help='output sample count')
parser.add_argument('--output_tone_mappped', action='store_true', help='output tone mapped')
parser.add_argument('-s', '--sampling', type=str, default='f1', help='sampling preset')
parser.add_argument('-d', '--debug', action='store_true', help='debug mode')
args = parser.parse_args(argv)


common_record_params = {
    'fps': 30,
    'start_time': 0,
    'end_time': 20,
    'no_record': args.no_record,
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

foveated_params_preset_1 = {
    'shape': FoveaShape.CIRCLE,
    'foveaRadius': 200.0,
    'foveaInputType': FoveaInputType.PROCEDURAL,
    'foveaSampleCount': 8.0,
    'foveaMovePattern': FoveaMovePattern.LISSAJOUS,
    'foveaMoveRadius': float2(1280/2, 720/2),
    # 'foveaMoveRadius': float2(640.0, 0.0),
    'foveaMoveFreq': float2(0.4, 0.5),
    'foveaMovePhase': float2(math.pi/2, 0),
    'foveaMoveSpeed': 1000.0,
    'foveaMoveStayDuration': 0.5,
}

foveated_params_preset_2 = {
    'shape': FoveaShape.CIRCLE,
    'foveaRadius': 200.0,
    'foveaInputType': FoveaInputType.PROCEDURAL,
    'foveaSampleCount': 8.0,
    'foveaMovePattern': FoveaMovePattern.MOVE_AND_STAY,
    'foveaMoveRadius': float2(1280/2, 720/2),
    # 'foveaMoveRadius': float2(640.0, 0.0),
    'foveaMoveFreq': float2(0.4, 0.5),
    'foveaMovePhase': float2(math.pi/2, 0),
    'foveaMoveSpeed': 1000.0,
    'foveaMoveStayDuration': 0.5,
}



if args.sampling == 'f1':
    foveated_params_override = foveated_params_preset_1
elif args.sampling == 'f2':
    foveated_params_override = foveated_params_preset_2


gt_sample_Count = 128

generate_raw_gt = False
generate_temporal_filtered_gt = False
generate_spatial_temporal_filtered_gt = True

# iters, feedback
iter_params = [
    # (0, -1),
    # (1, 0),
    (2, 0),
    # (3, 0),
    # (4, 0),
]
# midpoints = [0.45, 0.5, 0.55]
# steepnesses = [0.5, 1.0, 1.5]
# blending_func_params = [(m,s) for m in midpoints for s in steepnesses]
blending_func_params = [(0.5, 1.0)]
filter_gradient = args.fg
normalization_mode = NormalizationMode[args.norm_mode]
best_gamma_enabled = args.bg
optimal_weighting_enabled = False

force_record_selections = False
force_record_unweighted = False
force_record_weighted = False
force_record_ground_truth = False
no_recrod = args.no_record
debug_mode = args.debug

profiler_enabled = args.profile
output_sample_count = args.output_sample_count
output_tone_mappped = args.output_tone_mappped

if force_record_selections or force_record_unweighted or force_record_weighted or force_record_ground_truth:
    logW("Force record enabled.")

for scene_idx, scene_path in enumerate(scene_paths):

    scene_name = scene_path.stem
    common_record_params['end_time'] = animation_lengths[scene_name]

    try:
        m.loadScene(scene_path)
    except Exception as e:
        print(f"Failed to load scene: {scene_path}")
        print(e)
        raise e

    for iters, feedback in iter_params:

        # Try different parameters with dynamic weighting
        # for midpoint, steepness in blending_func_params:
        #     logI(f"Run Dynamic Weighting: iters={iters}, feedback={feedback}, midpoint={midpoint}, steepness={steepness}")
        #     run(graph_params = {
        #             'iters': iters,
        #             'feedback': feedback,
        #             'dynamic_weighting_enabled': True,
        #             'dynamic_weighting_params': {
        #                 'GradientMidpoint': float(midpoint),
        #                 'GammaSteepness': float(steepness),
        #                 'SelectionMode': SelectionMode.LINEAR,
        #                 'NormalizationMode': normalization_mode,
        #                 'FilterGradientEnabled': filter_gradient,
        #                 'BestGammaEnabled': best_gamma_enabled,
        #                 'OptimalWeightingEnabled': optimal_weighting_enabled,
        #                 **common_dynamic_weighting_params
        #             },
        #             'foveated_pass_enabled': True,
        #             'foveated_pass_params': foveated_params_override,
        #             'output_tone_mappped': output_tone_mappped,
        #             **common_graph_params
        #         },
        #         record_params_override={
        #             **common_record_params,
        #             'enable_profiler': profiler_enabled,
        #         },
        #         force_record=force_record_selections,
        #         debug=debug_mode)
        #     sleep(1)

        # # Unweighted
        logI("Run Unweighted")
        run(graph_params = {
                'iters': iters,
                'feedback': feedback,
                'dynamic_weighting_enabled': False,
                'dynamic_weighting_params': {
                    'SelectionMode': SelectionMode.UNWEIGHTED,
                    **common_dynamic_weighting_params
                },
                'foveated_pass_enabled': True,
                'foveated_pass_params': foveated_params_override,
                'output_sample_count': output_sample_count,
                'output_tone_mappped': output_tone_mappped,
                **common_graph_params
            },
            record_params_override={
                **common_record_params,
                'enable_profiler': profiler_enabled,
            },
            force_record=force_record_unweighted,
            debug=debug_mode
        )

        sleep(1)

    #     # Weighted
    #     logI("Run Weighted")
    #     run(graph_params = {
    #             'iters': iters,
    #             'feedback': feedback,
    #             'dynamic_weighting_enabled': True,
    #             'dynamic_weighting_params': {
    #                 'SelectionMode': SelectionMode.WEIGHTED,
    #                 'OptimalWeightingEnabled': optimal_weighting_enabled,
    #                 **common_dynamic_weighting_params
    #             },
    #             'foveated_pass_enabled': True,
    #             'foveated_pass_params': foveated_params_override,
    #             'output_tone_mappped': output_tone_mappped,
    #             **common_graph_params
    #         },
    #         record_params_override={
    #             **common_record_params,
    #             'enable_profiler': False,
    #         },
    #         force_record=force_record_weighted,
    #         debug=debug_mode
    #     )

    #     sleep(1)

    #     # Generate ground truth with spatial-temporal filter
    #     if generate_spatial_temporal_filtered_gt:
    #         logI("Run Ground Truth (Spatial-temporal filtered)")
    #         run(graph_params = {
    #                 'svgf_enabled': True,
    #                 'iters': iters,
    #                 'feedback': feedback,
    #                 'dynamic_weighting_enabled': False,
    #                 'foveated_pass_enabled': False,
    #                 'sample_count': gt_sample_Count,
    #                 **common_graph_params
    #             },
    #             record_params_override = {
    #                 **common_record_params,
    #                 'enable_profiler': False,
    #             },
    #             force_record=force_record_ground_truth,
    #             debug=debug_mode
    #         )

    # sleep(1)

    # # Generate ground truth without any filter
    # if generate_raw_gt:
    #     logI("Run Ground Truth (No filter)")
    #     run(graph_params = {
    #             'svgf_enabled': False,
    #             'iters': 0,
    #             'feedback': -1,
    #             'dynamic_weighting_enabled': False,
    #             'foveated_pass_enabled': False,
    #             'sample_count': gt_sample_Count,
    #             **common_graph_params
    #         },
    #         record_params_override = {
    #             **common_record_params,
    #             'enable_profiler': False,
    #         },
    #         force_record=force_record_ground_truth,
    #         debug=debug_mode
    #     )

    # # Generate ground truth with temporal filter
    # if generate_temporal_filtered_gt:
    #     logI("Run Ground Truth (Temporal and moment filtered)")
    #     run(graph_params = {
    #             'svgf_enabled': True,
    #             'spatial_filter_enabled': True,
    #             'iters': 0,
    #             'feedback': -1,
    #             'dynamic_weighting_enabled': False,
    #             'foveated_pass_enabled': False,
    #             'sample_count': gt_sample_Count,
    #             **common_graph_params
    #         },
    #         record_params_override = {
    #             **common_record_params,
    #             'enable_profiler': False,
    #         },
    #         force_record=force_record_ground_truth,
    #         debug=debug_mode
    #     )

    logI(f"Scene {scene_name} done.")

logI("All Done")
print('\a')
exit()
