import cv2 as cv
import numpy as np
from pathlib import Path
from matplotlib import pyplot as plt
from enum import IntEnum

from _utils import *
from DynamicWeighting_Common import *

class ErrorType(IntEnum):
    L1 = 1
    L2 = 2
    RMSE = 2
    REL_MSE = 3


def loadError(path, field) -> np.ndarray:
    '''
    Load error from a file.
    '''
    path = Path(path)
    data = None
    full_path = path/f'{field}_{ErrorType.REL_MSE}.txt'
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


record_path = Path(__file__).parents[4]/'Record'

scene_name = 'VeachAjarAnimated'
# scene_name = 'VeachAjar'
# scene_name = 'BistroExterior'

iters = 2
feedback = -1
grad_iters = 0
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
        f'{scene_name}_iters({iters},{feedback})_Alpha({alpha})_{sampling}'
    ),
    Record(
        'Weighted',
        f'{scene_name}_iters({iters},{feedback})_Weighted_Alpha({alpha})_WAlpha({w_alpha})_{sampling}'
    ),
    Record(
        f'Selected({midpoint},{steepness})',
        f'{scene_name}_iters({iters},{feedback},{grad_iters})_{selection_func}({midpoint},{steepness})_Alpha({alpha})_WAlpha({w_alpha})_GAlpha({g_alpha})_Norm({normalization_mode.name})_{sampling}'
    ),
]


sequences = [loadError(record_path/record.folder_name, 'mean') for record in records]

plt.axes().set_yscale('log')
for i, record in enumerate(records):
    plt.plot(sequences[i], label=record.display_name)
plt.title(f'RelMSE of {scene_name}')
plt.ylabel('RelMSE')
plt.xlabel('Frame')
plt.legend()
plt.show()

