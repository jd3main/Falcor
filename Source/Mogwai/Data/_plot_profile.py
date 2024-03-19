from matplotlib import pyplot as plt
import json
from pathlib import Path
from pprint import pprint
import argparse
import re

from _utils import *
from DynamicWeighting_Common import *


def plot_profile(data:dict, n_frames:int, title, xlabel, ylabel, save_path=None):
    fig, ax = plt.subplots()

    ax.stackplot(range(n_frames), data.values(), labels=data.keys())

    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()
    if save_path:
        plt.savefig(save_path)
        print(f'Saved to {save_path}')
    plt.show()


DEFAULT_SCENE_NAME = 'VeachAjarAnimated'
# DEFAULT_SCENE_NAME = 'BistroExterior'
# DEFAULT_SCENE_NAME = 'EmeraldSquare_Day'
# DEFAULT_SCENE_NAME = 'SunTemple'

DEFAULT_RECORD_PATH = Path(__file__).parents[4]/'Record'
DEFAULT_FPS = 30
DEFAULT_RECORD_SECONDS = 20

DEFAULT_SELECTION_FUNC = "Linear"
# DEFAULT_SELECTION_FUNC = "Step"
# DEFAULT_SELECTION_FUNC = "Logistic"

DEFAULT_NORMALZATION_MODE = NormalizationMode.STD
# DEFAULT_NORMALZATION_MODE = NormalizationMode.NONE
# DEFAULT_NORMALZATION_MODE = NormalizationMode.LUM

DEFAULT_ITER_PARAMS = (2, 0, 1)

# DEFAULT_SAMPLING_METHOD = 'Foveated(SPLIT_HORIZONTALLY,SHM,8.0)'
# DEFAULT_SAMPLING_METHOD = 'Adaptive(2.0,0.0,10.0,1,1)'
DEFAULT_SAMPLING_METHOD = 'Foveated(CIRCLE,LISSAJOUS,8.0)_Lissajous([0.400000, 0.500000],[640.000000, 360.000000])'

DEFALT_MIDPOINT = 0.05
DEFAULT_STEEPNESS = 1.0

### Argument parsing
parser = argparse.ArgumentParser(description='Calculate errors')
parser.add_argument('--scene_name', type=str, default=DEFAULT_SCENE_NAME, help='scene name')
parser.add_argument('-r', '--record_path', type=str, default=DEFAULT_RECORD_PATH, help='record path')
parser.add_argument('-i', '--iters', type=str, help='iteration parameters, e.g. "2,-1,0"')
parser.add_argument('-f', '--fps', type=int, default=DEFAULT_FPS, help='fps')
parser.add_argument('-d', '--duration', type=int, default=DEFAULT_RECORD_SECONDS, help='duration in seconds')
parser.add_argument('-s', '--selection_func', type=str, default=DEFAULT_SELECTION_FUNC, help='selection function')
parser.add_argument('--midpoint', type=float, default=DEFALT_MIDPOINT, help='midpoint of selection function')
parser.add_argument('--steepness', type=float, default=DEFAULT_STEEPNESS, help='steepness of selection function')
parser.add_argument('-n', '--norm_mode', type=str, default=DEFAULT_NORMALZATION_MODE.name, help='normalization mode')
parser.add_argument('--sampling', type=str, default=DEFAULT_SAMPLING_METHOD, help='sampling method and params')
args = parser.parse_args()

### Load parameters
scene_name = args.scene_name
record_path = Path(args.record_path)
if args.iters is not None:
    iter_params = tuple(map(int, args.iters.split(',')))
else:
    iter_params = DEFAULT_ITER_PARAMS
fps = args.fps
duration = args.duration
n_frames = int(fps * duration)

selection_func = args.selection_func
midpoint = args.midpoint
steepness = args.steepness

normalization_mode = NormalizationMode[args.norm_mode.upper()]
sampling = args.sampling
wAlpha = None
# wAlpha = 0.02

wAlpha_str = f'_wAlpha({wAlpha})' if wAlpha else ''

print(f'scene_name:         {scene_name}')
print(f'n_frames:           {n_frames}')
print(f'selection_func:     {selection_func}')
print(f'normalization_mode: {normalization_mode.name}')
print(f'iter_params:        {iter_params}')
print(f'midpoint:           {midpoint}')
print(f'steepness:          {steepness}')
print(f'sampling:           {sampling}')


iters, feedback, grad_iters = iter_params

folder_name = f'{scene_name}_iters({iters},{feedback},{grad_iters})_{selection_func}({midpoint},{steepness})_GAlpha(0.2)_Norm({normalization_mode.name}){wAlpha_str}_{sampling}'
# folder_name = f'{scene_name}_iters({iters},{feedback})_{sampling}'
# folder_name = f'{scene_name}_iters({iters},{feedback})_Weighted{wAlpha_str}_{sampling}'

full_folder_path = record_path/folder_name

### Load data
print(f'Loading from: {full_folder_path}')
if not full_folder_path.exists():
    logErr(f'Folder not found: \"{full_folder_path}\"')
    exit()
if not (full_folder_path/'profile.json').exists():
    logErr(f'profile.json not found in \"{full_folder_path}\"')
    exit()
profile = json.load(open(full_folder_path/'profile.json'))

### Plot
# pprint(profile)
n_frames = profile['frameCount']
events = profile['events']
print(f"{n_frames} frames")

print("Keys:")
for key in profile['events']:
    print(key)

patterns = [
    r'^.*/SVGFPass/[^/]*/gpuTime$'
]

print("Matching keys:")

data = dict()
for key in events:
    if any(re.match(pattern, key) for pattern in patterns):
        print(key)
        name = key.lstrip("/onFrameRender/RenderGraphExe::execute()")
        data[name] = events[key]['records']
    # else:
    #     if 'Others' not in data:
    #         data['Others'] = np.array(events[key]['records'])
    #     data['Others'] += np.array(events[key]['records'])



plot_profile(data, n_frames, 'Execution Time', 'Frame', 'Time (Us)', full_folder_path/f'error_over_time.png')

