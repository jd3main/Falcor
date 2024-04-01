import cv2 as cv
import numpy as np
from pathlib import Path
from matplotlib import pyplot as plt
from enum import IntEnum
import argparse

from _utils import *
from DynamicWeighting_Common import *
from _error_measure import getErrFilename, ErrorType


def loadError(path, field, ref_temporal_filter_enabled, ref_spatial_filter_enabled, fast_mode=False) -> np.ndarray:
    '''
    Load error from a file.
    '''
    path = Path(path)
    data = None
    full_path = path/getErrFilename(field, ErrorType.REL_MSE, ref_temporal_filter_enabled, ref_spatial_filter_enabled, fast_mode)
    try:
        with open(full_path, 'r') as f:
            data = np.loadtxt(f)
    except Exception as e:
        logE(f'cannot load error from {full_path}')
        logE(e)
    return data

class Record:
    def __init__(self, display_name, folder_name):
        self.display_name = display_name
        self.folder_name = Path(folder_name)


if __name__ == '__main__':

    REF_TEMPORAL_FILTER_ENABLED = True
    REF_SPATIAL_FILTER_ENABLED = True

    DEFAULT_SCENE_NAME = 'VeachAjar'
    # DEFAULT_SCENE_NAME = 'VeachAjarAnimated'
    # DEFAULT_SCENE_NAME = 'BistroExterior'

    ### Argument parsing
    parser = argparse.ArgumentParser(description='Calculate errors')
    parser.add_argument('--scene_name', type=str, default=DEFAULT_SCENE_NAME, help='scene name')
    parser.add_argument('--fast', action='store_true', help='fast mode')
    args = parser.parse_args()


    record_path = Path(__file__).parents[4]/'Record'
    scene_name = args.scene_name
    fast_mode = args.fast

    iters = 2
    feedback = 0
    sampling = 'Foveated(CIRCLE,LISSAJOUS,8.0)_Lissajous([0.400000, 0.500000],[640.000000, 360.000000])'
    alpha = 0.05
    w_alpha = 0.05
    g_alpha = 0.2
    normalization_mode = NormalizationMode.STD

    selection_func = 'Linear'
    midpoint = 0.5
    steepness = 1.0

    records = [
        Record(
            'Unweighted',
            getSourceFolderNameUnweighted(scene_name, iters, feedback, alpha, sampling)
        ),
        Record(
            'Weighted',
            getSourceFolderNameWeighted(scene_name, iters, feedback, alpha, w_alpha, sampling)
        ),
        Record(
            f'Selected({midpoint},{steepness})',
            getSourceFolderNameLinear(scene_name, iters, feedback, midpoint, steepness, alpha, w_alpha, g_alpha, normalization_mode, sampling)
        ),
    ]



    for record in records:
        if not (record_path/record.folder_name).exists():
            logE(f'{record.folder_name} does not exist')
            continue

    sequences = [loadError(record_path/record.folder_name, 'mean', REF_TEMPORAL_FILTER_ENABLED, REF_SPATIAL_FILTER_ENABLED, fast_mode) for record in records]

    plt.axes().set_yscale('log')
    for i, record in enumerate(records):
        plt.plot(sequences[i], label=record.display_name)
    plt.title(f'relMSE of {scene_name}')
    plt.ylabel('relMSE')
    plt.xlabel('Frame')
    plt.legend()
    plt.show()

