import os
os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"

from pathlib import Path
import json
import time
import typing
import re
from dataclasses import dataclass
from enum import IntEnum, auto
import argparse
import gc
import winsound

import numpy as np
import cupy as cp
import cv2 as cv
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import pandas as pd
import skimage as ski
from skimage.metrics import structural_similarity as ssim
from tqdm import tqdm

from _utils import *
from _log_utils import *
from DynamicWeighting_Common import *


USE_CUDA = True

class ErrorType(IntEnum):
    L1 = 1
    L2 = 2
    RMSE = 2
    REL_MSE = 3

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
    fovea_move_pattern: FoveaMovePattern = FoveaMovePattern.LISSAJOUS
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
        pattern = r'foveated\(([^_]+),([^_]+),([^_]+)\)'
        groups = re.findall(pattern, s)
        if len(groups) > 0:
            params.fovea_shape = FoveaShape[groups[0][0].upper()]
            params.fovea_move_pattern = FoveaMovePattern[groups[0][1].upper()]
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

def getErrFilename(field, err_type:ErrorType, use_no_filter_reference):
    if use_no_filter_reference:
        return f'{field}_{err_type.name}_NoFilterReference.txt'
    return f'{field}_{err_type.name}.txt'

xp = cp if USE_CUDA else np


### Default parameters
DEFAULT_PLOT_HISTO = False
DEFAULT_PLOT_ERROR_OVER_TIME = False
DEFAULT_FORCE_RECALCULATE = False

DEFAULT_SCENE_NAME = 'VeachAjarAnimated'
# DEFAULT_SCENE_NAME = 'VeachAjar'
# DEFAULT_SCENE_NAME = 'BistroExterior'
# DEFAULT_SCENE_NAME = 'BistroInterior'
# DEFAULT_SCENE_NAME = 'EmeraldSquare_Day'
# DEFAULT_SCENE_NAME = 'SunTemple'

DEFAULT_RECORD_PATH = Path(__file__).parents[4]/'Record'
DEFAULT_FPS = 30
DEFAULT_RECORD_SECONDS = 20
DEFAULT_ERR_TYPE = ErrorType.REL_MSE
REL_MSE_EPSILON = 1e-2

DEFAULT_SELECTION_FUNC = "Linear"
# DEFAULT_SELECTION_FUNC = "Step"
# DEFAULT_SELECTION_FUNC = "Logistic"

DEFAULT_NORMALZATION_MODE = NormalizationMode.STD
# DEFAULT_NORMALZATION_MODE = NormalizationMode.NONE
# DEFAULT_NORMALZATION_MODE = NormalizationMode.LUM

DEFAULT_ITER_PARAMS = [
    (2, -1, 0),
    (2, 0, 1),
    (2, 1, 2),
    (3, -1, 0),
    (3, 0, 1),
    (3, 1, 2),
    (4, 0, 1),
    (4, 1, 2),
]

DEFAULT_MIDPOINTS = [0.0, 0.05, 0.5, 1.0]
DEFAULT_STEEPNESSES = [0.1, 1.0, 10.0]

# DEFAULT_SAMPLING_METHOD = 'Foveated(SPLIT_HORIZONTALLY,SHM,8.0)'
# DEFAULT_SAMPLING_METHOD = 'Adaptive(2.0,0.0,10.0,1,1)'
DEFAULT_SAMPLING_METHOD = 'Foveated(CIRCLE,LISSAJOUS,8.0)_Lissajous([0.400000, 0.500000],[640.000000, 360.000000])'

### Argument parsing
parser = argparse.ArgumentParser(description='Calculate errors')
parser.add_argument('--scene_name', type=str, default=DEFAULT_SCENE_NAME, help='scene name')
parser.add_argument('-r', '--record_path', type=str, default=DEFAULT_RECORD_PATH, help='record path')
parser.add_argument('-i', '--iters', type=str, help='iteration parameters, e.g. "2,-1,0"')
parser.add_argument('-f', '--fps', type=int, default=DEFAULT_FPS, help='fps')
parser.add_argument('-d', '--duration', type=int, default=DEFAULT_RECORD_SECONDS, help='duration in seconds')
parser.add_argument('-s', '--selection_func', type=str, default=DEFAULT_SELECTION_FUNC, help='selection function')
parser.add_argument('--midpoints', type=str, help='midpoints of selection function')
parser.add_argument('--steepnesses', type=str, help='steepnesses of selection function')
parser.add_argument('-n', '--norm_mode', type=str, default=DEFAULT_NORMALZATION_MODE.name, help='normalization mode')
parser.add_argument('-e', '--err_type', type=str, default=DEFAULT_ERR_TYPE.name, help='error type')
parser.add_argument('--sampling', type=str, default=DEFAULT_SAMPLING_METHOD, help='sampling method and params')
parser.add_argument('--force', action='store_true', help='force recalculate')
parser.add_argument('--plot_histo', action='store_true', help='plot histogram')
parser.add_argument('--plot_error_over_time', action='store_true', help='plot error over time')
parser.add_argument('--use_no_filter_reference', action='store_true', help='use no filter reference')
args = parser.parse_args()

### Load parameters
scene_name = args.scene_name
record_path = Path(args.record_path)
if args.iters is not None:
    iter_params = [tuple(map(int, args.iters.split(',')))]
else:
    iter_params = DEFAULT_ITER_PARAMS
fps = args.fps
duration = args.duration
n_frames = int(fps * duration)

selection_func = args.selection_func
if args.midpoints is not None:
    midpoints = list(map(float, args.midpoints.split(',')))
else:
    midpoints = DEFAULT_MIDPOINTS

if args.steepnesses is not None:
    steepnesses = list(map(float, args.steepnesses.split(',')))
else:
    steepnesses = ([0,] if selection_func=='Step' else DEFAULT_STEEPNESSES)

normalization_mode = NormalizationMode[args.norm_mode.upper()]
err_type = ErrorType[args.err_type.upper()]
sampling = args.sampling
force_recalculate = args.force
plot_histo = args.plot_histo
plot_error_over_time = args.plot_error_over_time
use_no_filter_reference = args.use_no_filter_reference

alpha = 0.05
w_alpha = 0.05

gt_sample_count = 64

print(f'scene_name:         {scene_name}')
print(f'n_frames:           {n_frames}')
print(f'selection_func:     {selection_func}')
print(f'normalization_mode: {normalization_mode.name}')
print(f'err_type:           {err_type.name}')
print(f'iter_params:        {iter_params}')
print(f'midpoints:          {midpoints}')
print(f'steepnesses:        {steepnesses}')
print(f'sampling:           {sampling}')
print(f'gt_sample_count:    {gt_sample_count}')


for iters, feedback, grad_iters in iter_params:
    print(f'iters: ({iters},{feedback},{grad_iters})')

    # check reference data path
    if use_no_filter_reference:
        reference_path = record_path/f'{scene_name}_iters(0,-1)_Alpha({alpha})_{gt_sample_count}'
    else:
        reference_path = record_path/f'{scene_name}_iters({iters},{feedback})_Alpha({alpha})_{gt_sample_count}'
    if not reference_path.exists():
        logE(f'[Error] reference folder not found: {reference_path}')
        exit()

    # check number of reference images
    ref_images_pattern = f'{fps}fps.SVGFPass.Filtered image.{{}}.exr'
    n_ref_images = countImages(reference_path, ref_images_pattern)
    if n_ref_images < n_frames:
        logE(f'[Error] {n_frames} reference images required but only {n_ref_images} found.')
        exit()
    elif n_ref_images > n_frames:
        logW(f'[Warning] {n_ref_images} reference images found, more than required ({n_frames})')

    # setup source folders
    source_folders: list[Path] = []
    for midpoint in midpoints:
        for steepness in steepnesses:
            if selection_func == 'Step':
                folder_name = f'{scene_name}_iters({iters},{feedback},{grad_iters})_{selection_func}({midpoint})_Alpha({alpha})_WAlpha({w_alpha})_GAlpha(0.2)_Norm({normalization_mode.name})_{sampling}'
            else:
                folder_name = f'{scene_name}_iters({iters},{feedback},{grad_iters})_{selection_func}({midpoint},{steepness})_Alpha({alpha})_WAlpha({w_alpha})_GAlpha(0.2)_Norm({normalization_mode.name})_{sampling}'
            if (record_path/folder_name).exists():
                source_folders.append(record_path/folder_name)
            else:
                logW(f'[Warning] folder not found: {folder_name}')
    source_folders.append(record_path/f'{scene_name}_iters({iters},{feedback})_Alpha({alpha})_{sampling}')
    source_folders.append(record_path/f'{scene_name}_iters({iters},{feedback})_Weighted_Alpha({alpha})_WAlpha({w_alpha})_{sampling}')
    print(f'found {len(source_folders)} source folders')

    records_params:list[RecordParams] = [RecordParams.parse(folder.name, scene_name) for folder in source_folders]
    steepnesses_ext = steepnesses + [float('inf')]

    # check source folders
    for folder in source_folders:
        if not folder.exists():
            logW(f'[Warning] folder not found: {folder}')
            continue
        n_images = countImages(folder, f'{fps}fps.SVGFPass.Filtered image.{{}}.exr')
        if n_images < n_frames:
            logE(f'[Error] does not have enough images in: \"{folder}\"')
            logE(f'found {n_images} images, expected {n_frames}')
            exit()
        elif n_images > n_frames:
            logW(f'[Warning] more than {n_frames} images found in: \"{folder}\"')

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
    if plot_histo:
        err_bins = xp.array(list(10.0**np.arange(-5, 1, 0.5)) + [float('inf')])
        err_histograms = xp.zeros((len(steepnesses_ext), len(midpoints), n_frames, len(err_bins)-1), dtype=np.float32)
        print(f'err_bins = {err_bins}')
    for folder_index, folder in enumerate(source_folders):
        if not folder.exists():
            logW(f'[Warning] folder not found: {folder}')
            continue

        print(f'# \"{folder.name}\"')

        # load from cache
        loaded = {field: False for field in fields}
        if not force_recalculate:
            all_valid = True
            for field_index, field in enumerate(fields): # check if all data exists and are modified later than metadata
                load_path = folder/getErrFilename(field, err_type, use_no_filter_reference)
                if (load_path.exists()
                    and fileModifiedLaterThan(load_path, folder/'metadata.txt')
                    and fileModifiedLaterThan(load_path, reference_path/'metadata.txt')):

                    results[folder_index, :, field_index] = xp.loadtxt(load_path)
                    avg_results[folder_index, :] = xp.mean(results[folder_index, :, :], axis=0)
                    loaded[field] = True
                else:
                    loaded[field] = False

            if all(loaded.values()):   # load data if all valid
                print(f'All {len(fields)} fields are loaded from cache')
                continue
            else:
                print(f'some data not exists or outdated, calculating...')

        # load reference images
        reference_images = imageSequenceLoader(reference_path, ref_images_pattern, n_frames)

        # load source images
        source_images = imageSequenceLoader(folder, f'{fps}fps.SVGFPass.Filtered image.{{}}.exr', n_frames)
        params = records_params[folder_index]
        steepness = params.steepness
        midpoint = params.midpoint
        r = steepnesses_ext.index(steepness)
        c = midpoints.index(midpoint)

        # calculate errors
        for i, (_reference_image, _source_image) in tqdm(enumerate(zip(reference_images, source_images)), total=n_frames):
            if USE_CUDA:
                reference_image = cp.asarray(_reference_image)
                source_image = cp.asarray(_source_image)
            else:
                reference_image = _reference_image
                source_image = _source_image

            if err_type == ErrorType.L1:
                err = xp.sum(xp.abs(reference_image - source_image), axis=-1)
            elif err_type == ErrorType.L2:
                err = xp.linalg.norm(reference_image - source_image, axis=-1, ord=2)
            elif err_type == ErrorType.REL_MSE:
                err = xp.sum((reference_image - source_image)**2, axis=-1) / (xp.sum(reference_image**2, axis=-1) + REL_MSE_EPSILON)

            if 'mean' in fields and not loaded['mean']:
                results[folder_index, i, fields.index('mean')] = xp.mean(err)

            if '25-th percentile' in fields and not loaded['25-th percentile']:
                percentiles = xp.percentile(err, [25, 50, 75, 99])
                results[folder_index, i, [fields.index(f) for f in fields if 'percentile' in f]] = percentiles

            if 'top-1-percent' in fields and not loaded['top-1-percent']:
                top_1_percent = xp.mean(err[xp.where(err > percentiles[-1])])
                results[folder_index, i, fields.index('top-1-percent')] = top_1_percent

            if 'ssim' in fields and not loaded['ssim']:
                mssim = ssim(_reference_image, _source_image,
                             gaussian_weights = True,
                             sigma = 1.5,
                             use_sample_covariance = False,
                             data_range = 10,
                             channel_axis = -1)
                results[folder_index, i, fields.index('ssim')] = mssim

            if plot_histo:
                err_histograms[r, c, i, :] = xp.histogram(err, bins=err_bins)[0]

            gc.collect()


        short_name = folder.name.split('_')[2+scene_name.count('_')]

        avg_results[folder_index, :] = xp.mean(results[folder_index, :, :], axis=0)
        avg_mean_err = avg_results[folder_index, fields.index('mean')]

        print(f'mean({avg_mean_err:.7e}) \t{short_name}')

        # write to file
        for field_indx, field in enumerate(fields):
            save_path = folder/getErrFilename(field, err_type, use_no_filter_reference)
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
    output_dir = Path(f'{sampling}/{scene_name}')
    ensurePath(output_dir)
    if use_no_filter_reference:
        table_file_name = f'iters({iters},{feedback},{grad_iters})_fps({fps})_t({duration})_{selection_func}_Norm({normalization_mode.name})_Alpha({alpha})_wAlpha({w_alpha})_Err({err_type.name})_NoFilterReference.txt'
    else:
        table_file_name = f'iters({iters},{feedback},{grad_iters})_fps({fps})_t({duration})_{selection_func}_Norm({normalization_mode.name})_Alpha({alpha})_wAlpha({w_alpha})_Err({err_type.name}).txt'
    save_path = output_dir/table_file_name
    with open(save_path, 'w') as f:
        f.write(f'# {scene_name}\n')
        for folder in source_folders:
            f.write(f'{folder.name}\n')
        f.write('\n')
        f.write(f'# reference\n')
        f.write(f'{reference_path}\n')
        f.write('\n')
        f.write(f'# parameters\n')
        f.write(f'iters: {iters},{feedback},{grad_iters}\n')
        f.write(f'fps: {fps}\n')
        f.write(f'duration: {duration}\n')
        f.write(f'selection_func: {selection_func}\n')
        f.write(f'err_type: {err_type.name}\n')
        f.write(f'normalization_mode: {normalization_mode.name}\n')
        f.write(f'sampling: {sampling}\n')
        f.write('\n')
        for field_index, field in enumerate(fields):
            f.write(f'# {field}\n')
            f.write(tables[field_index].to_csv(sep='\t', lineterminator='\n'))
            f.write('\n')
        print(f'Tables are saved to \"{save_path.absolute()}\"')

    winsound.Beep(442, 100)
    winsound.Beep(442, 100)

    # plot error histograms
    if plot_histo:
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

    if plot_error_over_time:
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
