import cv2 as cv
import numpy as np
from pathlib import Path
from matplotlib import pyplot as plt
from enum import IntEnum
from _utils import *


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
        logErr(f'cannot load error from {full_path}')
        logErr(e)
    return data

class Record:
    def __init__(self, display_name, folder_name):
        self.display_name = display_name
        self.folder_name = Path(folder_name)


record_path = Path(__file__).parents[4]/'Record'

# scene_name = 'BistroExterior'
scene_name = 'VeachAjarAnimated'

iters = 2
feedback = -1
grad_iters = 0
sampling = 'Foveated(CIRCLE,LISSAJOUS,8.0)_Lissajous([0.400000, 0.500000],[640.000000, 360.000000])'


records = [
    Record(
        'Unweighted',
        f'{scene_name}_iters({iters},{feedback})_{sampling}'
    ),
    Record(
        'Weighted',
        f'{scene_name}_iters({iters},{feedback})_Weighted_{sampling}'
    ),
    Record(
        'Selected(0.05,10)',
        f'{scene_name}_iters({iters},{feedback},{grad_iters})_Linear(0.05,10.0)_GAlpha(0.2)_Norm(STANDARD_DEVIATION)_{sampling}'
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

