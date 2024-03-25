from enum import IntEnum, auto

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

    LUMINANCE = LUM
    VARIANCE = VAR
    STANDARD_DEVIATION = STD


def getSourceFolderNameLinear(scene_name,
                              iters, feedback, grad_iters,
                              midpoint, steepness,
                              alpha, w_alpha, g_alpha,
                              norm_mode:NormalizationMode,
                              sampling,
                              **kwargs):
    return f'{scene_name}_iters({iters},{feedback},{grad_iters})_Linear({midpoint},{steepness})_Alpha({alpha})_WAlpha({w_alpha})_GAlpha({g_alpha})_Norm({norm_mode.name})_{sampling}'

def getSourceFolderNameStep(scene_name,
                            iters, feedback, grad_iters,
                            midpoint,
                            alpha, w_alpha, g_alpha,
                            norm_mode:NormalizationMode,
                            sampling,
                            **kwargs):
    return f'{scene_name}_iters({iters},{feedback},{grad_iters})_Step({midpoint})_Alpha({alpha})_WAlpha({w_alpha})_GAlpha({g_alpha})_Norm({norm_mode.name})_{sampling}'

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
                        iters, feedback, grad_iters=None,
                        selection_func=None, midpoint=None, steepness=None,
                        alpha=None, w_alpha=None, g_alpha=None,
                        norm_mode:NormalizationMode=None,
                        sampling=None,
                        **kwargs):
    if selection_func == 'Linear':
        return getSourceFolderNameLinear(scene_name, iters, feedback, grad_iters, midpoint, steepness, alpha, w_alpha, g_alpha, norm_mode, sampling)
    elif selection_func == 'Step':
        return getSourceFolderNameStep(scene_name, iters, feedback, grad_iters, midpoint, alpha, w_alpha, g_alpha, norm_mode, sampling)
    elif selection_func == 'Weighted':
        return getSourceFolderNameWeighted(scene_name, iters, feedback, alpha, w_alpha, sampling)
    elif selection_func == 'Unweighted':
        return getSourceFolderNameUnweighted(scene_name, iters, feedback, alpha, sampling)
    else:
        raise ValueError(f'Invalid selection function: {selection_func}')
