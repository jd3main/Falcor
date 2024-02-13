import os
os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"

from pathlib import Path
import json
import time
import typing
import re
from dataclasses import dataclass
from enum import IntEnum, auto

import numpy as np
import cupy as cp
import cv2 as cv
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import pandas as pd
import skimage as ski
from skimage.metrics import structural_similarity as ssim

from _utils import *
from DynamicWeighting_Common import *


USE_CUDA = True

class ErrorType(IntEnum):
    L1 = 1
    L2 = 2

class WeightingMode(IntEnum):
    UNWEIGHTED = 0
    WEIGHTED = 1
    DYNAMIC_WEIGHTING = 2

@dataclass
class RecordParams:
    scene_name: str
    iter_params: str = ''
    fps: int = 30

    weighting_mode: WeightingMode = WeightingMode.UNWEIGHTED
    selection_mode: SelectionMode = SelectionMode.UNWEIGHTED
    midpoint: float = float('nan')
    steepness: float = float('nan')
    grad_alpha: float = float('nan')
    norm_mode: NormalizationMode = NormalizationMode.NONE

    fovea_shape: FoveaShape = FoveaShape.UNIFORM
    fovea_input_type: FoveaInputType = FoveaInputType.NONE
    fovea_sample_count: int = 1

    def parse(s: str, scene_name: str) -> 'RecordParams':
        params = RecordParams(scene_name)

        s = s.lower()

        # parse iters
        pattern = r'iters\(([^_]+)\)'
        groups = re.findall(pattern, s)
        if len(groups) > 0:
            params.iter_params = groups[0]

        # parse fps
        pattern = fr'fps\(({RE_FLOAT})\)'
        groups = re.findall(pattern, s)
        if len(groups) > 0:
            params.fps = int(groups[0])

        # parse gradient alpha
        pattern = fr'galpha\(({RE_FLOAT})\)'
        groups = re.findall(pattern, s)
        if len(groups) > 0:
            params.grad_alpha = float(groups[0])

        # parse selection function
        if 'logistic' in s:
            pattern = fr'logistic\(({RE_FLOAT}),({RE_FLOAT})\)'
            midpoint, steepness = re.findall(pattern, s)[0]
            params.weighting_mode = WeightingMode.DYNAMIC_WEIGHTING
            params.selection_mode = SelectionMode.LOGISTIC
            params.midpoint = float(midpoint)
            params.steepness = float(steepness)
        elif 'linear' in s:
            pattern = fr'linear\(({RE_FLOAT}),({RE_FLOAT})\)'
            midpoint, steepness = re.findall(pattern, s)[0]
            params.weighting_mode = WeightingMode.DYNAMIC_WEIGHTING
            params.selection_mode = SelectionMode.LINEAR
            params.midpoint = float(midpoint)
            params.steepness = float(steepness)
        elif 'step' in s:
            pattern = r'step\(([^(]+)\)'
            midpoint = re.findall(pattern, s)[0]
            params.weighting_mode = WeightingMode.DYNAMIC_WEIGHTING
            params.selection_mode = SelectionMode.STEP
            params.midpoint = float(midpoint)
            params.steepness = float('inf')
        elif 'weighted' in s:
            params.weighting_mode = WeightingMode.WEIGHTED
            params.selection_mode = SelectionMode.WEIGHTED
            params.midpoint = 1.0
            params.steepness = float('inf')
        else: # Unweighted
            params.weighting_mode = WeightingMode.UNWEIGHTED
            params.selection_mode = SelectionMode.UNWEIGHTED
            params.midpoint = 0.0
            params.steepness = float('inf')

        # parse normalization mode
        pattern = r'norm\(([^(]+)\)'
        groups = re.findall(pattern, s)
        if len(groups) > 0:
            params.norm_mode = NormalizationMode[groups[0].upper()]

        # parse foveation mode
        pattern = r'foveated\((.+),(.+),(.+)\)'
        groups = re.findall(pattern, s)
        if len(groups) > 0:
            params.fovea_shape = FoveaShape[groups[0][0].upper()]
            params.fovea_input_type = FoveaInputType[groups[0][1].upper()]
            params.fovea_sample_count = int(float(groups[0][2]))

        return params


def loadMetadata(path) -> dict:
    '''
    Load metadata from a file.
    '''
    path = Path(path)
    data = dict()
    try:
        with open(path/'metadata.txt', 'r') as f:
            data = dict(**json.load(f))
    except Exception as e:
        print(f'cannot load metadata from {path/"metadata.txt"}')
        print(e)
    return data


PLOT_HISTO = False
PLOT_ERROR_OVER_TIME = False
FORCE_RECALCULATE = False

xp = cp if USE_CUDA else np

# scene_name = 'VeachAjarAnimated'
scene_name = 'BistroExterior'
# scene_name = 'EmeraldSquare_Day'
# scene_name = 'SunTemple'


record_path = Path(__file__).parents[4]/'Record'
fps = 30
record_seconds = 10
n_frames = int(fps * record_seconds)
selection_func = "Linear"
# selection_func = "Step"
# selection_func = "Logistic"
err_type = ErrorType.L2


print(f'scene_name = {scene_name}')
print(f'n_frames = {n_frames}')
print(f'selection_func = {selection_func}')

iter_params = [
    # (2, -1, 2),
    (2, -1, 0),
    # (2, 0, 1),
    # (2, 1, 2),
    # (3, 0, 1),
]


for iters, feedback, grad_iters in iter_params:
    print(f'iters = {iters}')
    print(f'feedback = {feedback}')
    print(f'grad_iters = {grad_iters}')

    # load reference data
    reference_path = record_path/f'{scene_name}_iters({iters},{feedback})'
    ## pre-check
    n_ref_images = countImages(reference_path, f'{fps}fps.SVGFPass.Filtered image.{{}}.exr')
    if n_ref_images < n_frames:
        logErr(f'[Error] reference images not enough')
        exit()
    elif n_ref_images > n_frames:
        logWarn(f'[Warning] reference images more than {n_frames}')

    print(f'loading reference data from "{reference_path}"')

    reference_images = []
    try:
        reference_images = loadImageSequence(reference_path, f'{fps}fps.SVGFPass.Filtered image.{{}}.exr', n_frames)
    except FileNotFoundError as e:
        logErr(f'[Error] FileNotFoundError: {e}')
        exit()

    if len(reference_images) == 0:
        logErr(f'[Error] No reference images loaded')
        exit()
    else:
        print(f'{len(reference_images)} reference images loaded')

    print(f'max value: {np.max(reference_images)}')

    # setup source folders
    source_folders: list[Path] = []
    midpoints = [0.0, 0.05, 0.5, 1.0]
    # steepnesses = ([0,] if selection_func=='Step' else [0.5, 1.0, 5.0, 50.0, 500.0, 5000.0])
    steepnesses = ([0,] if selection_func=='Step' else [1.0, 10.0, 100.0])
    # midpoints = [0.0, 0.01, 1.0]
    # steepnesses = [0.5]
    for midpoint in midpoints:
        for steepness in steepnesses:
            if selection_func == 'Step':
                folder_name = f'{scene_name}_iters({iters},{feedback},{grad_iters})_{selection_func}({midpoint})_GAlpha(0.2)_Norm(STANDARD_DEVIATION)_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)'
            else:
                folder_name = f'{scene_name}_iters({iters},{feedback},{grad_iters})_{selection_func}({midpoint},{steepness})_GAlpha(0.2)_Norm(STANDARD_DEVIATION)_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)'
            if (record_path/folder_name).exists():
                source_folders.append(record_path/folder_name)
    source_folders.append(record_path/f'{scene_name}_iters({iters},{feedback})_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)')
    source_folders.append(record_path/f'{scene_name}_iters({iters},{feedback})_Weighted_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)')
    print(f'found {len(source_folders)} source folders')

    records_params:list[RecordParams] = [RecordParams.parse(folder.name, scene_name) for folder in source_folders]
    steepnesses_ext = steepnesses + [float('inf')]

    # check source folders
    for folder in source_folders:
        if not folder.exists():
            logWarn(f'[Warning] folder not found: {folder}')
            continue
        n_images = countImages(folder, f'{fps}fps.SVGFPass.Filtered image.{{}}.exr')
        if n_images < n_frames:
            logErr(f'[Error] does not have enough images in: \"{folder}\"')
            logErr(f'found {n_images} images, expected {n_frames}')
            exit()
        elif n_images > n_frames:
            logWarn(f'[Warning] more than {n_frames} images found in: \"{folder}\"')

    # load source data and calculate error

    st = time.time()
    fields = [
        'mean',
        '25-th percentile',
        '50-th percentile',
        '75-th percentile',
        '99-th percentile',
        'top-1-percent',
        'ssim',
    ]
    results = xp.empty((len(source_folders), n_frames, len(fields)), dtype=np.float32)
    avg_results = xp.empty((len(source_folders), len(fields)), dtype=np.float32)
    if PLOT_HISTO:
        err_bins = xp.array(list(10.0**np.arange(-5, 1, 0.5)) + [float('inf')])
        err_histograms = xp.zeros((len(steepnesses_ext), len(midpoints), n_frames, len(err_bins)-1), dtype=np.float32)
        print(f'err_bins = {err_bins}')
    for folder_index, folder in enumerate(source_folders):
        if not folder.exists():
            logWarn(f'[Warning] folder not found: {folder}')
            continue

        print(f'# \"{folder.name}\"')

        # load from cache
        loaded = {}
        if not FORCE_RECALCULATE:
            all_valid = True
            for field_index, field in enumerate(fields): # check if all data exists and are modified later than metadata
                load_path = folder/f'{field}_{err_type}.txt'
                if (load_path.exists()
                    and fileModifiedLaterThan(load_path, folder/'metadata.txt')
                    and fileModifiedLaterThan(load_path, reference_path/'metadata.txt')):

                    results[folder_index, :, field_index] = xp.loadtxt(folder/f'{field}_{err_type}.txt')
                    avg_results[folder_index, :] = xp.mean(results[folder_index, :, :], axis=0)
                    loaded[field] = True
                else:
                    loaded[field] = False

            if all(loaded.values()):   # load data if all valid
                print(f'All {len(fields)} fields are loaded from cache')
                continue
            else:
                print(f'some data not exists or outdated, calculating...')

        # load source images
        source_images = imageSequenceLoader(folder, f'{fps}fps.SVGFPass.Filtered image.{{}}.exr', n_frames)
        params = records_params[folder_index]
        steepness = params.steepness
        midpoint = params.midpoint
        r = steepnesses_ext.index(steepness)
        c = midpoints.index(midpoint)

        # calculate errors
        for i, _source_image in enumerate(source_images):
            if USE_CUDA:
                reference_image = cp.asarray(reference_images[i])
                source_image = cp.asarray(_source_image)
            else:
                source_image = _source_image


            xp = cp.get_array_module(reference_image)

            if 'mean' in loaded and not loaded['mean']:
                err = xp.linalg.norm(reference_image - source_image, axis=-1, ord=err_type.value)
                results[folder_index, i, fields.index('mean')] = xp.mean(err)

            if '25-th percentile' in loaded and not loaded['25-th percentile']:
                percentiles = xp.percentile(err, [25, 50, 75, 99])
                results[folder_index, i, [fields.index(f) for f in fields if 'percentile' in f]] = percentiles

            if 'top-1-percent' in loaded and not loaded['top-1-percent']:
                top_1_percent = xp.mean(err[xp.where(err > percentiles[-1])])
                results[folder_index, i, fields.index('top-1-percent')] = top_1_percent

            if 'ssim' in loaded and not loaded['ssim']:
                mssim = ssim(reference_images[i], _source_image,
                             gaussian_weights = True,
                             sigma = 1.5,
                             use_sample_covariance = False,
                             data_range = 100,
                             channel_axis = -1)
                results[folder_index, i, fields.index('ssim')] = mssim

            if PLOT_HISTO:
                err_histograms[r, c, i, :] = xp.histogram(err, bins=err_bins)[0]


        short_name = folder.name.split('_')[2+scene_name.count('_')]

        avg_results[folder_index, :] = xp.mean(results[folder_index, :, :], axis=0)
        avg_mean_err = avg_results[folder_index, fields.index('mean')]

        print(f'mean({avg_mean_err:.7e}) \t{short_name}')

        # write to file
        for field_indx, field in enumerate(fields):
            save_path = folder/f'{field}_{err_type}.txt'
            with open(save_path, 'w') as f:
                xp.savetxt(f, results[folder_index, :, field_indx])
    ed = time.time()
    print(f'elapsed time: {ed-st:.2f}s')

    # make table
    tables:list[pd.DataFrame] = []
    table_index = sorted(list(set(params.steepness for params in records_params)))
    table_columns = sorted(list(set(params.midpoint for params in records_params)))
    for field in fields:
        table = pd.DataFrame(index=table_index, columns=table_columns, dtype=np.float32)
        tables.append(table)
    for folder_index, folder in enumerate(source_folders):
        steepness = records_params[folder_index].steepness
        midpoint = records_params[folder_index].midpoint
        for field_index, field in enumerate(fields):
            tables[field_index].loc[steepness, midpoint] = avg_results[folder_index, field_index]

    # print table
    for field_index, field in enumerate(fields):
        print(f'# {field}')
        print(tables[field_index].to_csv(sep='\t', lineterminator='\n'))

    # write tables to file
    save_path = Path(f'{scene_name}_iters({iters},{feedback},{grad_iters})_fps({fps})_t({record_seconds})_{selection_func}_ErrorMeasure.txt')
    with open(save_path, 'w') as f:
        f.write(f'# {scene_name}\n')
        for folder in source_folders:
            f.write(f'{folder.name}\n')
        f.write('\n')
        for field_index, field in enumerate(fields):
            f.write(f'# {field}\n')
            f.write(tables[field_index].to_csv(sep='\t', lineterminator='\n'))
            f.write('\n')
        print(f'Tables are saved to \"{save_path.absolute()}\"')

    # plot error histograms
    if PLOT_HISTO:
        nrows = len(steepnesses_ext)
        ncols = len(midpoints)
        fig, axs = plt.subplots(nrows, ncols, sharex=True, sharey=True)
        for c in range(ncols):
            axs[-1, c].set_xlabel(f'{midpoints[c]}')
        for r, steepness in enumerate(steepnesses_ext):
            axs[r, 0].set_ylabel(f'{steepness}')
            for c, midpoint in enumerate(midpoints):
                ax:Axes = axs[r, c]
                ax.set(xscale='log')
                ax.set_title(f'{steepness}, {midpoint}')
                params = records_params[folder_index]
                short_name = f'{params.selection_mode.name}({params.midpoint}, {params.steepness})'
                merged_histogram = xp.mean(err_histograms[r, c, :, :], axis=0)
                ax.bar(
                    cp.asnumpy(err_bins[:-1]),
                    cp.asnumpy(merged_histogram),
                    width = cp.asnumpy(xp.diff(err_bins)),
                    label = short_name,
                    edgecolor = "black",
                    align = "edge")
                ax.grid(True)
        plt.show()

    if PLOT_ERROR_OVER_TIME:
        nrows = len(fields)
        ncols = 1

        fig, axs = plt.subplots(nrows, ncols, sharex=True)

        for field_index, field in enumerate(fields):
            ax = axs[field_index]
            ax.set_ylabel(field)
            for folder_index, folder in enumerate(source_folders):
                params = records_params[folder_index]
                short_name = f'{params.selection_mode.name}({params.midpoint}, {params.steepness})'
                ax.plot(cp.asnumpy(results[folder_index, :, field_index]), label=short_name)

            ax.legend(loc='upper left')
        fig.set_label(f'{scene_name} iters({iters},{feedback},{grad_iters})')

        plt.show()
