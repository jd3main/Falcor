import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from _error_measure import RecordParams


scene_name = 'VeachAjarAnimated'
# scene_name = 'BistroExterior'
# scene_name = 'EmeraldSquare_Day'
# scene_name = 'SunTemple'


record_path = Path(__file__).parents[4]/'Record'
fps = 30
record_seconds = 20
n_frames = int(fps * record_seconds)
iters = '2,-1,2'
selection_func = "Logistic"
# selection_func = "Linear"
# selection_func = "Step"


# setup target folders
target_folders: list[Path] = []
for midpoint in [0.00001, 0.0001, 0.001, 0.01, 0.1]:
    for steepness in ([0,] if selection_func=='Step' else [0.5, 5.0, 50.0, 500.0, 5000.0]):
        if selection_func == 'Step':
            folder_name = f'{scene_name}_iters({iters})_{selection_func}({midpoint})_GAlpha(0.2)_Norm(STANDARD_DEVIATION)_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)'
        else:
            folder_name = f'{scene_name}_iters({iters})_{selection_func}({midpoint},{steepness})_GAlpha(0.2)_Norm(STANDARD_DEVIATION)_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)'
        if (record_path/folder_name).exists():
            target_folders.append(record_path/folder_name)
target_folders.append(record_path/f'{scene_name}_iters({iters})_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)')
target_folders.append(record_path/f'{scene_name}_iters({iters})_Weighted_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)')
print(f'found {len(target_folders)} target folders')
