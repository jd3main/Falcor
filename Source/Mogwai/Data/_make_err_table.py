from pathlib import Path
from pprint import pprint
import json
import re

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from _utils import *
from DynamicWeighting_Common import *
from _error_measure import getErrFilename, ErrorType


if __name__ == '__main__':
    # scene_name = 'VeachAjarAnimated'
    scene_name = 'VeachAjar'

    iter_params = [
        (2, -1, 0),
        (2, 0, 1),
        (2, 1, 2),
        (3, -1, 0),
        (3, 0, 1),
        (3, 1, 2),
        (4, 0, 1),
        (4, 1, 2),
    ]

    configs = []

    for iters, feedback, grad_iters in iter_params:
        configs.append({
            "scene_name": scene_name,
            "iters": iters,
            "feedback": feedback,
            "grad_iters": grad_iters,
            "selection_func": "Linear",
            "midpoint": 0.5,
            "steepness": 1.0,
            "alpha": 0.05,
            "w_alpha": 0.05,
            "g_alpha": 0.2,
            "norm_mode": NormalizationMode.STD,
            "sampling": "Foveated(CIRCLE,LISSAJOUS,8.0)_Lissajous([0.400000, 0.500000],[640.000000, 360.000000])"
        })


    RECORD_PATH = Path(__file__).parents[4]/'Record'

    fields = ["mean", "ssim"]
    err_type = ErrorType.REL_MSE
    use_no_filter_reference = True

    table = pd.DataFrame(columns=['iters', 'feedback', 'grad_iters', 'mean'])
    rows = []
    for cid, config in enumerate(configs):
        unweighted_folder = RECORD_PATH/getSourceFolderNameUnweighted(**config)
        weighted_folder = RECORD_PATH/getSourceFolderNameWeighted(**config)
        dynamic_folder = RECORD_PATH/getSourceFolderName(**config)

        source_folders = [unweighted_folder, weighted_folder, dynamic_folder]
        source_names = ['unweighted', 'weighted', 'dynamic']


        for source_folder in source_folders:
            if not source_folder.exists():
                logE(f'{source_folder} does not exist')
                continue

        row = {}
        row['iters'] = f'({config["iters"]},{config["feedback"]},{config["grad_iters"]})'
        for field in fields:
            filename = getErrFilename(field, err_type, use_no_filter_reference)
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

    table.to_csv('_err_table.csv', index=False, sep='\t')
