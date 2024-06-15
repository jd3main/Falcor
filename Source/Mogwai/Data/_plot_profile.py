from matplotlib import pyplot as plt
import json
from pathlib import Path
from pprint import pprint
import argparse
import re

from _utils import *
from TwoHistory_Common import *
from _log_utils import *
from _animation_lengths import *


def plot_profile(ax:plt.Axes, data:dict, n_frames:int, title, xlabel, ylabel, colors=None):
    ax.stackplot(range(n_frames), data.values(), labels=data.keys(), colors=colors)

    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xlim(0, n_frames)
    ax.set_ylim(0, 5)
    ax.legend(loc='upper right')



DEFAULT_RECORD_PATH = Path(__file__).parents[4]/'Record'
DEFAULT_FPS = 30
DEFAULT_RECORD_SECONDS = -1

DEFAULT_SELECTION_FUNC = "Linear"
# DEFAULT_SELECTION_FUNC = "Step"
# DEFAULT_SELECTION_FUNC = "Logistic"

DEFAULT_NORMALZATION_MODE = NormalizationMode.STD
# DEFAULT_NORMALZATION_MODE = NormalizationMode.NONE
# DEFAULT_NORMALZATION_MODE = NormalizationMode.LUM


# DEFAULT_SAMPLING_METHOD = 'Foveated(SPLIT_HORIZONTALLY,SHM,8.0)'
# DEFAULT_SAMPLING_METHOD = 'Adaptive(2.0,0.0,10.0,1,1)'
DEFAULT_SAMPLING_METHOD = 'Foveated(CIRCLE,LISSAJOUS,8.0)_Circle(200)_Lissajous([0.4,0.5],[640,360])'

DEFALT_MIDPOINT = 0.5
DEFAULT_STEEPNESS = 1.0

scene_names = [
    # 'VeachAjar',
    'VeachAjarAnimated',
    # 'BistroExterior',
    # 'BistroInterior',
    # 'BistroInterior_Wine',
    # 'SunTemple',
    # 'EmeraldSquare_Day',
    # 'EmeraldSquare_Dusk',
    # 'MEASURE_ONE',
    # 'MEASURE_SEVEN',
]

### Argument parsing
parser = argparse.ArgumentParser(description='Plot profile')
parser.add_argument('-r', '--record_path', type=str, default=DEFAULT_RECORD_PATH, help='record path')
parser.add_argument('-f', '--fps', type=int, default=DEFAULT_FPS, help='fps')
parser.add_argument('-s', '--selection_func', type=str, default=DEFAULT_SELECTION_FUNC, help='selection function')
parser.add_argument('--midpoint', type=float, default=DEFALT_MIDPOINT, help='midpoint of selection function')
parser.add_argument('--steepness', type=float, default=DEFAULT_STEEPNESS, help='steepness of selection function')
parser.add_argument('-n', '--norm_mode', type=str, default=DEFAULT_NORMALZATION_MODE.name, help='normalization mode')
parser.add_argument('--sampling', type=str, default=DEFAULT_SAMPLING_METHOD, help='sampling method and params')
parser.add_argument('--fg', action='store_true', help='filter gradient')
parser.add_argument('--bg', action='store_true', help='best gamma')
args = parser.parse_args()

### Load parameters
record_path = Path(args.record_path)

fps = args.fps

selection_func = args.selection_func
midpoint = args.midpoint
steepness = args.steepness

normalization_mode = NormalizationMode[args.norm_mode.upper()]
sampling = args.sampling
filter_gradient = args.fg
best_gamma = args.bg

iters = 2
feedback = 0
alpha = 0.05
w_alpha = 0.05
g_alpha = 0.2


for scene_name in scene_names:
    duration = animation_lengths[scene_name]
    n_frames = int(fps * duration)

    print(f'scene_name:         {scene_name}')
    print(f'n_frames:           {n_frames}')
    print(f'selection_func:     {selection_func}')
    print(f'normalization_mode: {normalization_mode.name}')
    print(f'iter_params:        {iters}, {feedback}')
    print(f'midpoint:           {midpoint}')
    print(f'steepness:          {steepness}')
    print(f'sampling:           {sampling}')
    print(f'filter_gradient:    {filter_gradient}')
    print(f'best_gamma:         {best_gamma}')



    folder_names = [
        getSourceFolderNameLinear(scene_name, iters, feedback, midpoint, steepness, alpha, w_alpha, g_alpha, normalization_mode, sampling,
                                filter_gradient, best_gamma),
        getSourceFolderNameUnweighted(scene_name, iters, feedback, alpha, sampling),
    ]

    print(f'folder_names: {folder_names}')

    source_display_names = [
        f'{scene_name} - {iters} iters - Two-history',
        f'{scene_name} - {iters} iters - Unweighted',
        # f'{scene_name} - {iters} iters - Weighted',
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
            r'^.*/SVGFPass/[^/]*/gpuTime$',
            r'^.*/SVGFPass/computeAtrousDecomposition/dynamicWeighting/gpuTime$'
        ]

        RENDER_GRAPH_PREFIX = '/onFrameRender/RenderGraphExe::execute()'

        # print("Matching keys:")

        data = dict()
        for key in events:
            if any(re.match(pattern, key) for pattern in patterns):
                name = key.replace(RENDER_GRAPH_PREFIX,'').replace('/gpuTime','')
                data[name] = np.array(events[key]['records'])
            # else:
            #     if 'Others' not in data:
            #         data['Others'] = np.array(events[key]['records'])
            #     data['Others'] += np.array(events[key]['records'])

        if '/SVGFPass/computeAtrousDecomposition/dynamicWeighting' in data:
            data['/SVGFPass/computeAtrousDecomposition'] -= data['/SVGFPass/computeAtrousDecomposition/dynamicWeighting']

        total_time_data = events[f'{RENDER_GRAPH_PREFIX}/SVGFPass/gpuTime']['records']
        data['Others'] = total_time_data - np.sum(list(data.values()), axis=0)

        color_mapping = {
            '/SVGFPass/computeLinearZAndNormal': 'tab:blue',
            '/SVGFPass/computeTemporalFilter': 'tab:orange',
            '/SVGFPass/computeFilterGradient': 'tab:green',
            '/SVGFPass/computeFilteredMoments': 'tab:red',
            '/SVGFPass/computeAtrousDecomposition': 'tab:purple',
            '/SVGFPass/computeAtrousDecomposition/dynamicWeighting': 'tab:brown',
            '/SVGFPass/computeFinalModulate': 'tab:pink',
            'Others': 'tab:gray'
        }

        colors = []
        for key in data:
            colors.append(color_mapping[key])

        plot_profile(axs[i], data, n_frames, source_display_names[i], 'Frame', 'Time (Us)', colors)

        ### print data
        logI(f'{source_display_names[i]}:')
        logI(f'Total time: {np.mean(total_time_data[1:]):.3f} ms')
        for key, value in data.items():
            logI(f'{key}:\t{np.mean(value[1:]):.3f} ms')

        execution_times.append(np.mean(total_time_data[1:]))

    print()
    for i, folder_name in enumerate(folder_names):
        logI(f'{source_display_names[i]}:\t{execution_times[i]:.3f} ms')


    plt.tight_layout()
    plt.show()
