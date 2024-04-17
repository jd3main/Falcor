from enum import IntEnum, IntFlag, auto
import numpy as np

class FoveaShape(IntEnum):
    UNIFORM = 0
    CIRCLE = auto()
    SPLIT_HORIZONTALLY = auto()
    SPLIT_VERTICALLY = auto()

class FoveaInputType(IntEnum):
    NONE = 0
    PROCEDURAL = auto()
    MOUSE = auto()

class FoveaMovePattern(IntEnum):
    LISSAJOUS = 0
    MOVE_AND_STAY = auto()

class SelectionMode(IntEnum):
    UNWEIGHTED = 0
    WEIGHTED = auto()
    LINEAR = auto()
    STEP = auto()
    LOGISTIC = auto()

class NormalizationMode(IntEnum):
    NONE = 0
    LUM = auto()
    VAR = auto()
    STD = auto()
    STD2 = auto()

    LUMINANCE = LUM
    VARIANCE = VAR
    STANDARD_DEVIATION = STD

class RefFilterMode(IntFlag):
    NONE = 0
    TEMPORAL = auto()
    SPATIAL = auto()

    SPATIAL_TEMPORAL = TEMPORAL | SPATIAL


def getReferenceFolderNameFiltered(scene_name, sample_count, alpha, iters=0, feedback=-1):
    return f'{scene_name}_iters({iters},{feedback})_Alpha({alpha})_{sample_count}'

def getReferenceFolderNameNonFiltered(scene_name, sample_count):
    return f'{scene_name}_{sample_count}'

def getSourceFolderNameLinear(scene_name,
                              iters, feedback,
                              midpoint, steepness,
                              alpha, w_alpha, g_alpha,
                              norm_mode:NormalizationMode,
                              sampling,
                              filter_gradient,
                              **kwargs):
    return f'{scene_name}_iters({iters},{feedback}){"_FG" if filter_gradient else ""}_Linear({midpoint},{steepness})_Alpha({alpha})_WAlpha({w_alpha})_GAlpha({g_alpha})_Norm({norm_mode.name})_{sampling}'

def getSourceFolderNameStep(scene_name,
                            iters, feedback,
                            midpoint,
                            alpha, w_alpha, g_alpha,
                            norm_mode:NormalizationMode,
                            sampling,
                            filter_gradient,
                            **kwargs):
    return f'{scene_name}_iters({iters},{feedback}){"_FG" if filter_gradient else ""}_Step({midpoint})_Alpha({alpha})_WAlpha({w_alpha})_GAlpha({g_alpha})_Norm({norm_mode.name})_{sampling}'

def getSourceFolderNameWeighted(scene_name,
                                iters, feedback,
                                alpha, w_alpha,
                                sampling,
                                **kwargs):
    return f'{scene_name}_iters({iters},{feedback})_Weighted_Alpha({alpha})_WAlpha({w_alpha})_{sampling}'

def getSourceFolderNameUnweighted(scene_name,
                                  iters, feedback,
                                  alpha,
                                  sampling,
                                  **kwargs):
    return f'{scene_name}_iters({iters},{feedback})_Alpha({alpha})_{sampling}'


def getSourceFolderName(scene_name,
                        iters, feedback,
                        selection_func=None, midpoint=None, steepness=None,
                        alpha=None, w_alpha=None, g_alpha=None,
                        norm_mode:NormalizationMode=None,
                        sampling=None,
                        filter_gradient=False,
                        **kwargs):
    if selection_func == 'Linear':
        return getSourceFolderNameLinear(scene_name, iters, feedback, midpoint, steepness, alpha, w_alpha, g_alpha, norm_mode, sampling, filter_gradient)
    elif selection_func == 'Step':
        return getSourceFolderNameStep(scene_name, iters, feedback, midpoint, alpha, w_alpha, g_alpha, norm_mode, sampling, filter_gradient)
    elif selection_func == 'Weighted':
        return getSourceFolderNameWeighted(scene_name, iters, feedback, alpha, w_alpha, sampling)
    elif selection_func == 'Unweighted':
        return getSourceFolderNameUnweighted(scene_name, iters, feedback, alpha, sampling)
    else:
        raise ValueError(f'Invalid selection function: {selection_func}')

def popKeys(d:dict, keys):
    for k in keys:
        if k in d:
            d.pop(k)

def normalizeGraphParams(graph_params: dict) -> dict:

    # set default values for missing keys
    default_params = {
        'svgf_enabled': True,
        'alpha': 0.05,
        'spatial_filter_enabled': True,
        'iters': 0,
        'feedback': -1,
        'dynamic_weighting_enabled': True,
        'dynamic_weighting_params': {},
        'foveated_pass_enabled': False,
        'foveated_pass_params': {},
        'adaptive_pass_enabled': False,
        'adaptive_pass_params': {},
        'output_sample_count': False,
        'sample_count': 1,
        'repeat_sample_count': 1,
        'debug_tag_enabled': False,
        'debug_output_enabled': False,
        'output_sample_count': False,
        'output_tone_mappped': False,
    }

    for key in default_params:
        if key not in graph_params:
            graph_params[key] = default_params[key]

    # remove outdated keys
    if 'weighted_alpha' in graph_params:
        graph_params['weighted_alpha'] = graph_params['alpha']

    if not graph_params['dynamic_weighting_enabled']:
        graph_params['grad_iters'] = 0
        if 'dynamic_weighting_params' in graph_params:
            pop_keys = ['SelectionMode', 'GradientMidpoint', 'GammaSteepness', 'WeightedAlpha', 'GradientAlpha', 'NormalizationMode']
            popKeys(graph_params['dynamic_weighting_params'], pop_keys)
    elif graph_params['dynamic_weighting_params']['SelectionMode'] == SelectionMode.UNWEIGHTED:
        graph_params['grad_iters'] = 0
        pop_keys = ['GradientMidpoint', 'GammaSteepness', 'WeightedAlpha', 'GradientAlpha', 'NormalizationMode']
        popKeys(graph_params['dynamic_weighting_params'], pop_keys)
    elif graph_params['dynamic_weighting_params']['SelectionMode'] == SelectionMode.WEIGHTED:
        graph_params['grad_iters'] = graph_params['feedback'] + 1
        pop_keys = ['GradientMidpoint', 'GammaSteepness', 'GradientAlpha', 'NormalizationMode']
        popKeys(graph_params['dynamic_weighting_params'], pop_keys)

    if not graph_params['foveated_pass_enabled']:
        graph_params['foveated_pass_params'] = {}

    if not graph_params['adaptive_pass_enabled']:
        graph_params['adaptive_pass_params'] = {}

    if 'alpha' not in graph_params:
        graph_params['alpha'] = 0.05

    return graph_params


def ACESFilm(x:np.ndarray):
    x = x * 0.6
    a = 2.51
    b = 0.03
    c = 2.43
    d = 0.59
    e = 0.14
    return np.clip((x*(a*x+b))/(x*(c*x+d)+e), 0.0, 1.0)


def gammaCorrection(img: np.ndarray, gamma: float) -> np.ndarray:
    return np.power(img, gamma)

def toneMapping(img: np.ndarray, gamma=1/1.22) -> np.ndarray:
    img = ACESFilm(img)
    img = gammaCorrection(img, gamma)
    img = (img * 255).astype(np.uint8)
    return img

