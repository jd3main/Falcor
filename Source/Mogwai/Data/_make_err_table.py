from pathlib import Path
from pprint import pprint
import json
import re
import argparse

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from _utils import *
from DynamicWeighting_Common import *
from _error_measure import getErrFilename, ErrorType


RECORD_PATH = Path(__file__).parents[4]/'Record'
DEFAULT_NORMALZATION_MODE = NormalizationMode.STD

if __name__ == '__main__':

    ### Argument parsing
    parser = argparse.ArgumentParser(description='Calculate errors')
    parser.add_argument('--scene_name', type=str, default='', help='scene name')
    parser.add_argument('--fast', action='store_true', help='fast mode')
    parser.add_argument('--fovea', action='store_true', help='fovea')
    parser.add_argument('-n', '--norm_mode', type=str, default=DEFAULT_NORMALZATION_MODE.name, help='normalization mode')
    parser.add_argument('--fg', action='store_true', help='filter gradient')
    parser.add_argument('--bg', action='store_true', help='best gamma')
    parser.add_argument('-s', '--sampling', type=str, default='f1', help='sampling preset')
    args = parser.parse_args()


    iter_params = [
        # (0, -1),
        # (1, 0),
        (2, 0),
        # (3, 0),
        # (4, 0),
    ]

    scene_names = [
        'VeachAjar',
        'VeachAjarAnimated',
        'BistroExterior',
        'BistroInterior',
        'BistroInterior_Wine',
        'SunTemple',
        'EmeraldSquare_Day',
        'EmeraldSquare_Dusk',
        # 'MEASURE_ONE',
        # 'MEASURE_SEVEN',
        'ZeroDay_1',
        'ZeroDay_7',
        'ZeroDay_7c',
    ]

    scene_alter_names = {
        'MEASURE_ONE': 'ZeroDay_MEASURE_ONE',
        'MEASURE_SEVEN': 'ZeroDay_MEASURE_SEVEN',
    }

    if args.scene_name != '':
        scene_names = [args.scene_name]

    err_type = ErrorType.REL_MSE
    ref_filter_mode = RefFilterMode.SPATIAL_TEMPORAL
    norm_mode = NormalizationMode[args.norm_mode.upper()]
    filter_gradient = args.fg
    best_gamma = args.bg

    fields = ["mean", "ssim"]

    sampling = getSamplingPreset(args.sampling)

    if args.fovea:
        assert 'Foveated' in sampling

    # print settings
    print(f'scene_name:                     {scene_names}')
    print(f'iter_params:                    {iter_params}')
    print(f'sampling:                       {sampling}')
    print(f'norm_mode:                      {norm_mode}')
    print(f'filter_gradient:                {filter_gradient}')
    print(f'best_gamma:                     {best_gamma}')
    print(f'ref_filter_mode:                {ref_filter_mode}')

    configs = []
    for i, scene_name in enumerate(scene_names):
        for iters, feedback in iter_params:
            configs.append({
                "scene_name": scene_name,
                "iters": iters,
                "feedback": feedback,
                "selection_func": SelectionMode.LINEAR,
                "midpoint": 0.5,
                "steepness": 1.0,
                "alpha": 0.05,
                "w_alpha": 0.05,
                "g_alpha": 0.2,
                "norm_mode": norm_mode,
                "sampling": sampling,
            })



    # load data and make table
    table = pd.DataFrame(columns=['scene_name', 'iters', 'feedback', 'mean'])
    rows = []
    for cid, config in enumerate(configs):
        unweighted_folder = RECORD_PATH/getSourceFolderNameUnweighted(**config)
        weighted_folder = RECORD_PATH/getSourceFolderNameWeighted(**config)
        dynamic_folder = RECORD_PATH/getSourceFolderName(**config, filter_gradient=filter_gradient, best_gamma=best_gamma)

        source_folders = [unweighted_folder, weighted_folder, dynamic_folder]
        source_names = ['Unweighted', 'Weighted', 'Ours']


        for source_folder in source_folders:
            if not source_folder.exists():
                logE(f'{source_folder} does not exist')
                continue

        scene_name = config['scene_name']
        if scene_name in scene_alter_names:
            scene_name = scene_alter_names[scene_name]

        row = {}
        row['scene_name'] = scene_name
        row['iters'] = config['iters']
        row['feedback'] = config['feedback']
        for field in fields:
            filename = getErrFilename(field, err_type, ref_filter_mode, args.fast, args.fovea)
            for source_folder, source_name in zip(source_folders, source_names):
                full_path = source_folder/filename
                try:
                    with open(full_path, 'r') as f:
                        data = np.loadtxt(f)
                        avg = np.mean(data)
                        row[f'{field}_{source_name}'] = avg
                except Exception as e:
                    logE(f'cannot load from {full_path}')
                    logE(e)
        rows.append(row)

    table = pd.DataFrame(rows)
    print(table.to_string(index=False))
    output_path = Path(f'_err_table.txt')
    print(f'write to {output_path}')
    with open(output_path, 'w') as f:
        f.write(f'sampling: {sampling}\n')
        f.write(f'ref_filter_mode: {ref_filter_mode}\n')
        f.write('\n')

        csv = table.to_csv(index=False, sep='\t', lineterminator='\n')
        f.write(csv)
        f.write('\n')
        latex = table.to_latex(index=False)
        f.write(latex)
        f.write('\n')


        # without iters and feedback
        no_feedback_table = table.drop(columns=['feedback'])
        csv = no_feedback_table.to_csv(index=False, sep='\t', lineterminator='\n')
        f.write(csv)
        f.write('\n')
        latex = no_feedback_table.to_latex(index=False)
        f.write(latex)
        f.write('\n')

        # without iters and feedback
        no_iters_table = table.drop(columns=['iters', 'feedback'])
        csv = no_iters_table.to_csv(index=False, sep='\t', lineterminator='\n')
        f.write(csv)
        f.write('\n')
        latex = no_iters_table.to_latex(index=False)
        f.write(latex)
        f.write('\n')
    print('done')
