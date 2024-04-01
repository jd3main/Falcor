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


if __name__ == '__main__':

    DEFAULT_SCENE_NAME = 'VeachAjar'
    # DEFAULT_SCENE_NAME = 'VeachAjarAnimated'

    ### Argument parsing
    parser = argparse.ArgumentParser(description='Calculate errors')
    parser.add_argument('--scene_name', type=str, default=DEFAULT_SCENE_NAME, help='scene name')
    parser.add_argument('--fast', action='store_true', help='fast mode')
    args = parser.parse_args()

    iter_params = [
        # (0, -1),
        (1, 0),
        # (2, 0),
        # (2, 1),
        # (3, 0),
        # (3, 1),
        (4, 0),
        # (4, 1),
    ]

    err_type = ErrorType.REL_MSE
    ref_temporal_filter_enabled = True
    ref_spatial_filter_enabled = True

    # print settings
    print(f'scene_name:                     {args.scene_name}')
    print(f'iter_params:                    {iter_params}')
    print(f'ref_temporal_filter_enabled:    {ref_temporal_filter_enabled}')
    print(f'ref_spatial_filter_enabled:     {ref_spatial_filter_enabled}')

    configs = []
    for iters, feedback in iter_params:
        configs.append({
            "scene_name": args.scene_name,
            "iters": iters,
            "feedback": feedback,
            "selection_func": "Linear",
            "midpoint": 0.5,
            "steepness": 1.0,
            "alpha": 0.05,
            "w_alpha": 0.05,
            "g_alpha": 0.2,
            "norm_mode": NormalizationMode.STD,
            "sampling": "Foveated(CIRCLE,LISSAJOUS,8.0)_Lissajous([0.400000, 0.500000],[640.000000, 360.000000])"
            # "sampling": "Adaptive(2.0,0.0,10.0,1,1)"
        })


    RECORD_PATH = Path(__file__).parents[4]/'Record'

    fields = ["mean", "ssim"]


    # load data and make table
    table = pd.DataFrame(columns=['iters', 'feedback', 'mean'])
    rows = []
    for cid, config in enumerate(configs):
        unweighted_folder = RECORD_PATH/getSourceFolderNameUnweighted(**config)
        weighted_folder = RECORD_PATH/getSourceFolderNameWeighted(**config)
        dynamic_folder = RECORD_PATH/getSourceFolderName(**config)

        source_folders = [unweighted_folder, weighted_folder, dynamic_folder]
        source_names = ['Unweighted', 'Weighted', 'Ours']


        for source_folder in source_folders:
            if not source_folder.exists():
                logE(f'{source_folder} does not exist')
                continue

        row = {}
        row['iters'] = config['iters']
        row['feedback'] = config['feedback']
        for field in fields:
            filename = getErrFilename(field, err_type, ref_temporal_filter_enabled, ref_spatial_filter_enabled, args.fast)
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
    print(f'write to _err_table.csv')
    table.to_csv('_err_table.csv', index=False, sep='\t')
    print('done')
