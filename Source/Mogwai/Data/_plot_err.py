import cv2 as cv
import numpy as np
from pathlib import Path
from matplotlib import pyplot as plt
from enum import IntEnum
import argparse

from _utils import *
from DynamicWeighting_Common import *
from _error_measure import getErrFilename, ErrorType


def loadError(path, field, ref_filter_mode:RefFilterMode, fast_mode=False, fovea=False) -> np.ndarray:
    '''
    Load error from a file.
    '''
    path = Path(path)
    data = None
    full_path = path/getErrFilename(field, ErrorType.REL_MSE, ref_filter_mode, fast_mode, fovea)
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

    ref_filter_mode = RefFilterMode.SPATIAL_TEMPORAL

    # DEFAULT_SCENE_NAME = 'VeachAjar'
    # DEFAULT_SCENE_NAME = 'VeachAjarAnimated'
    # DEFAULT_SCENE_NAME = 'BistroExterior'
    # DEFAULT_SCENE_NAME = 'BistroInterior'
    # DEFAULT_SCENE_NAME = 'BistroInterior_Wine'
    DEFAULT_SCENE_NAME = 'SunTemple'

    ### Argument parsing
    parser = argparse.ArgumentParser(description='Calculate errors')
    parser.add_argument('--scene_name', type=str, default=DEFAULT_SCENE_NAME, help='scene name')
    parser.add_argument('--fast', action='store_true', help='fast mode')
    parser.add_argument('--fovea', action='store_true', help='fovea')
    args = parser.parse_args()


    record_path = Path(__file__).parents[4]/'Record'
    scene_name = args.scene_name
    fast_mode = args.fast
    fovea = args.fovea

    iters = 2
    feedback = 0
    # sampling = 'Foveated(CIRCLE,LISSAJOUS,8.0)_Circle(200)_Lissajous([0.4,0.5],[640,360])'
    sampling = 'Adaptive(2.0,10.0,1,1)'
    alpha = 0.05
    w_alpha = 0.05
    g_alpha = 0.2
    normalization_mode = NormalizationMode.STD

    selection_func = 'Linear'
    midpoint = 0.5
    steepness = 1.0

    err_fields = [
        'mean',
        'ssim',
    ]

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
            f'Two-history',
            getSourceFolderNameLinear(scene_name, iters, feedback, midpoint, steepness, alpha, w_alpha, g_alpha, normalization_mode, sampling)
        ),
    ]

    plot_colors = ['tab:orange', 'tab:red', 'tab:green']

    for record in records:
        if not (record_path/record.folder_name).exists():
            logE(f'{record.folder_name} does not exist')
            continue


    fig, axs = plt.subplots(len(err_fields), 1, sharex=True)
    if len(err_fields) == 1:
        axs = [axs]

    for field_idx, err_field in enumerate(err_fields):
        ax: plt.Axes = axs[field_idx]

        sequences = [loadError(record_path/record.folder_name, err_field, ref_filter_mode, fast_mode, fovea) for record in records]

        for i, record in enumerate(records):
            ax.plot(range(len(sequences[i])), sequences[i], label=record.display_name, color=plot_colors[i])

        if err_field == 'mean':
            ax.set_title(f'relMSE of {scene_name}')
            ax.set_ylabel('relMSE')
        elif err_field == 'ssim':
            ax.set_title(f'SSIM of {scene_name}')
            ax.set_ylabel('SSIM')
        ax.set_yscale('log')
        ax.set_xlabel('Frame')
        ax.set_xlim(0, len(sequences[0]))
        # ax.set_xlim(0, 250)
        ax.set_ylim(np.mean(sequences[0])/2, np.mean(sequences[0])*2)
        ax.legend(loc='upper right')
    plt.show()

