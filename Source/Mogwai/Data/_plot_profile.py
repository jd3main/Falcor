from matplotlib import pyplot as plt
import json
from pathlib import Path
from pprint import pprint
import argparse
import re

from _utils import *
from DynamicWeighting_Common import *
from _log_utils import *


def plot_profile(ax, data:dict, n_frames:int, title, xlabel, ylabel):
    ax.stackplot(range(n_frames), data.values(), labels=data.keys())

    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_ylim(0, 5)
    ax.legend()


DEFAULT_SCENE_NAME = 'VeachAjarAnimated'
# DEFAULT_SCENE_NAME = 'VeachAjar'
# DEFAULT_SCENE_NAME = 'BistroExterior'
# DEFAULT_SCENE_NAME = 'EmeraldSquare_Day'
# DEFAULT_SCENE_NAME = 'SunTemple'

SCENE_DURATIONS = {
    'VeachAjarAnimated': 20,
    'VeachAjar': 20,
    'BistroExterior': 100,
    'EmeraldSquare_Day': 10,
    'SunTemple': 10,
}

DEFAULT_RECORD_PATH = Path(__file__).parents[4]/'Record'
DEFAULT_FPS = 30
DEFAULT_RECORD_SECONDS = -1

DEFAULT_SELECTION_FUNC = "Linear"
# DEFAULT_SELECTION_FUNC = "Step"
# DEFAULT_SELECTION_FUNC = "Logistic"

DEFAULT_NORMALZATION_MODE = NormalizationMode.STD
# DEFAULT_NORMALZATION_MODE = NormalizationMode.NONE
# DEFAULT_NORMALZATION_MODE = NormalizationMode.LUM

DEFAULT_ITER_PARAMS = (4, 0, 1)

# DEFAULT_SAMPLING_METHOD = 'Foveated(SPLIT_HORIZONTALLY,SHM,8.0)'
# DEFAULT_SAMPLING_METHOD = 'Adaptive(2.0,0.0,10.0,1,1)'
DEFAULT_SAMPLING_METHOD = 'Foveated(CIRCLE,LISSAJOUS,8.0)_Lissajous([0.400000, 0.500000],[640.000000, 360.000000])'

DEFALT_MIDPOINT = 0.5
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
if duration < 0:
    duration = SCENE_DURATIONS[scene_name]
n_frames = int(fps * duration)

selection_func = args.selection_func
midpoint = args.midpoint
steepness = args.steepness

normalization_mode = NormalizationMode[args.norm_mode.upper()]
sampling = args.sampling

alpha = 0.05
w_alpha = 0.05
g_alpha = 0.2

print(f'scene_name:         {scene_name}')
print(f'n_frames:           {n_frames}')
print(f'selection_func:     {selection_func}')
print(f'normalization_mode: {normalization_mode.name}')
print(f'iter_params:        {iter_params}')
print(f'midpoint:           {midpoint}')
print(f'steepness:          {steepness}')
print(f'sampling:           {sampling}')


iters, feedback, grad_iters = iter_params


folder_names = [
    f'{scene_name}_iters({iters},{feedback},{grad_iters})_{selection_func}({midpoint},{steepness})_Alpha({alpha})_WAlpha({w_alpha})_GAlpha({g_alpha})_Norm({normalization_mode.name})_{sampling}',
    f'{scene_name}_iters({iters},{feedback})_Alpha({alpha})_{sampling}',
    f'{scene_name}_iters({iters},{feedback})_Weighted_Alpha({alpha})_WAlpha({w_alpha})_{sampling}',
]

source_display_names = [
    f'{scene_name} - {iters} iters - Dynamic',
    f'{scene_name} - {iters} iters - Unweighted',
    f'{scene_name} - {iters} iters - Weighted',
]

fig, axs = plt.subplots(len(folder_names), 1, sharex=True, sharey=True)

execution_times = []

for i, folder_name in enumerate(folder_names):
    full_folder_path = record_path/folder_name

    ### Load data
    print(f'Loading from: {full_folder_path}')
    if not full_folder_path.exists():
        logE(f'Folder not found: \"{full_folder_path}\"')
        exit()
    if not (full_folder_path/'profile.json').exists():
        logE(f'profile.json not found in \"{full_folder_path}\"')
        exit()
    profile = json.load(open(full_folder_path/'profile.json'))

    ### Plot
    # pprint(profile)
    n_frames = profile['frameCount']
    events = profile['events']
    print(f"{n_frames} frames")

    # print("Keys:")
    # for key in profile['events']:
    #     print(key)

    patterns = [
        r'^.*/SVGFPass/[^/]*/gpuTime$'
    ]

    RENDER_GRAPH_PREFIX = '/onFrameRender/RenderGraphExe::execute()'

    # print("Matching keys:")

    data = dict()
    for key in events:
        if any(re.match(pattern, key) for pattern in patterns):
            # print(key)
            name = key.lstrip(RENDER_GRAPH_PREFIX)
            data[name] = events[key]['records']
        # else:
        #     if 'Others' not in data:
        #         data['Others'] = np.array(events[key]['records'])
        #     data['Others'] += np.array(events[key]['records'])

    plot_profile(axs[i], data, n_frames, source_display_names[i], 'Frame', 'Time (Us)')

    ### print data
    total_time_data = events[f'{RENDER_GRAPH_PREFIX}/SVGFPass/gpuTime']['records']
    logI(f'{source_display_names[i]}:')
    logI(f'Total time: {np.mean(total_time_data):.3f} ms')
    for key, value in data.items():
        logI(f'{key}:\t{np.mean(value):.3f} ms')

    execution_times.append(np.mean(total_time_data))

print()
for i, folder_name in enumerate(folder_names):
    logI(f'{source_display_names[i]}:\t{execution_times[i]:.3f} ms')


plt.tight_layout()
plt.show()
