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
import pandas as pd
import skimage as ski
from skimage.metrics import structural_similarity as ssim
from tqdm import tqdm

from _utils import *
from _log_utils import *
from DynamicWeighting_Common import *
from _animation_lengths import animation_lengths


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


def getErrFilename(field, err_type:ErrorType, ref_filter_mode:RefFilterMode, fast_mode=False, fovea=False):
    ref_filter_mode_str = ''
    if ref_filter_mode & RefFilterMode.TEMPORAL:
        ref_filter_mode_str += 'T'
    if ref_filter_mode & RefFilterMode.SPATIAL:
        ref_filter_mode_str += 'S'

    parts = []
    parts.append(f'{field}')
    parts.append(f'{err_type.name}')
    if fovea:
        parts.append('fovea')
    parts.append(ref_filter_mode_str)
    if fast_mode:
        parts.append('fast')
    return '_'.join(parts) + '.txt'




### Default parameters
DEFAULT_FORCE_RECALCULATE = False


DEFAULT_RECORD_PATH = Path(__file__).parents[4]/'Record'
DEFAULT_FPS = 30
DEFAULT_ERR_TYPE = ErrorType.REL_MSE
REL_MSE_EPSILON = 1e-2

DEFAULT_SELECTION_FUNC = "Linear"

DEFAULT_NORMALZATION_MODE = NormalizationMode.STD



if __name__ == '__main__':

    ### Argument parsing
    parser = argparse.ArgumentParser(description='Calculate errors')
    parser.add_argument('--scene_name', type=str, default='', help='scene name')
    parser.add_argument('-r', '--record_path', type=str, default=DEFAULT_RECORD_PATH, help='record path')
    parser.add_argument('-f', '--fps', type=int, default=DEFAULT_FPS, help='fps')
    parser.add_argument('--selection_func', type=str, default=DEFAULT_SELECTION_FUNC, help='selection function')
    parser.add_argument('-n', '--norm_mode', type=str, default=DEFAULT_NORMALZATION_MODE.name, help='normalization mode')
    parser.add_argument('-e', '--err_type', type=str, default=DEFAULT_ERR_TYPE.name, help='error type')
    parser.add_argument('--force', action='store_true', help='force recalculate')
    parser.add_argument('--fast', action='store_true', help='fast mode')
    parser.add_argument('--cuda', action='store_true', help='use cuda')
    parser.add_argument('--fovea', action='store_true', help='calculate error in foveated area only')
    parser.add_argument('--fg', action='store_true', help='filter gradient')
    parser.add_argument('--bg', action='store_true', help='best gamma')
    parser.add_argument('-s', '--sampling', type=str, default='f1', help='sampling preset')
    args = parser.parse_args()

    xp = cp if args.cuda else np

    logI(f'cuda: {bool(args.cuda)}')

    ### Load parameters
    record_path = Path(args.record_path)
    fps = args.fps
    fast_mode = args.fast

    normalization_mode = NormalizationMode[args.norm_mode.upper()]
    err_type = ErrorType[args.err_type.upper()]
    sampling = getSamplingPreset(args.sampling)
    force_recalculate = args.force
    selection_func = args.selection_func
    filter_gradient = args.fg
    best_gamma = args.bg

    alpha = 0.05
    w_alpha = 0.05
    g_alpha = 0.2

    scene_names = [
        'VeachAjar',
        'VeachAjarAnimated',
        # 'VeachAjarAnimated2',
        'BistroExterior',
        'BistroInterior',
        'BistroInterior_Wine',
        'SunTemple',
        'EmeraldSquare_Day',
        'EmeraldSquare_Dusk',
        'ZeroDay_1',
        'ZeroDay_7',
        'ZeroDay_7c',
    ]

    if args.scene_name != '':
        scene_names = [args.scene_name]



    iter_params = [
        # (0, -1),
        # (1, 0),
        (2, 0),
        # (3, 0),
        # (4, 0),
    ]

    # midpoints = [0.0, 0.05, 0.5, 1.0]
    # steepnesses = [0.1, 1.0, 10.0]
    # midpoints = [0.4, 0.45, 0.5, 0.55, 0.6]
    # steepnesses = [0.1, 0.5, 1.0, 1.5, 10.0, 20.0]
    # blending_func_params = [(m,s) for m in midpoints for s in steepnesses]
    blending_func_params = [(0.5, 1.0)]
    midpoints = [params[0] for params in blending_func_params]
    steepnesses = [params[1] for params in blending_func_params]

    ref_sample_count = 128
    ref_filter_mode = RefFilterMode.SPATIAL_TEMPORAL

    # spatial filter only not supported
    if ref_filter_mode & RefFilterMode.SPATIAL:
        assert ref_filter_mode & RefFilterMode.TEMPORAL

    for scene_name in scene_names:

        duration = animation_lengths[scene_name]
        n_frames = int(fps * duration)

        logI(f'scene_name:         {scene_name}')
        logI(f'duration:           {duration} ({n_frames} frames)')
        logI(f'selection_func:     {selection_func}')
        logI(f'normalization_mode: {normalization_mode.name}')
        logI(f'err_type:           {err_type.name}')
        logI(f'iter_params:        {iter_params}')
        logI(f'midpoints:          {midpoints}')
        logI(f'steepnesses:        {steepnesses}')
        logI(f'sampling:           {sampling}')
        logI(f'filter_gradient:    {filter_gradient}')
        logI(f'best_gamma:         {best_gamma}')
        logI(f'ref_sample_count:   {ref_sample_count}')
        logI(f'ref_filter_mode:    {ref_filter_mode}')

        iter_step = 1
        if fast_mode:
            logW('Fast mode is enabled. Some data may not be calculated.')
            iter_step = 15

        for iters, feedback in iter_params:
            print(f'iters: ({iters},{feedback})')

            # check reference data path
            if ref_filter_mode == RefFilterMode.SPATIAL_TEMPORAL:
                reference_path = record_path/getReferenceFolderNameFiltered(scene_name, ref_sample_count, alpha, iters, feedback)
            elif ref_filter_mode == RefFilterMode.TEMPORAL:
                reference_path = record_path/getReferenceFolderNameFiltered(scene_name, ref_sample_count, alpha)
            else: # NONE
                reference_path = record_path/getReferenceFolderNameNonFiltered(scene_name, ref_sample_count)

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
            for midpoint, steepness in blending_func_params:
                if selection_func == 'Linear':
                    folder_name = getSourceFolderNameLinear(scene_name,
                                                            iters, feedback, midpoint, steepness,
                                                            alpha, w_alpha, g_alpha,
                                                            normalization_mode,
                                                            sampling,
                                                            filter_gradient,
                                                            best_gamma)
                elif selection_func == 'Step':
                    folder_name = getSourceFolderNameStep(scene_name,
                                                        iters, feedback, midpoint,
                                                        alpha, w_alpha, g_alpha,
                                                        normalization_mode,
                                                        sampling,
                                                        filter_gradient,
                                                        best_gamma)

                source_folders.append(record_path/folder_name)

            folder_name = getSourceFolderNameWeighted(scene_name, iters, feedback, alpha, w_alpha, sampling)
            source_folders.append(record_path/folder_name)
            folder_name = getSourceFolderNameUnweighted(scene_name, iters, feedback, alpha, sampling)
            source_folders.append(record_path/folder_name)

            valid_folders = []
            for folder_name in source_folders:
                if folder_name.exists():
                    valid_folders.append(folder_name)
                else:
                    logW(f'[Warning] folder not found: {folder_name}')
            source_folders = valid_folders

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

            fields = [
                'mean',
                # '25-th percentile',
                # '50-th percentile',
                # '75-th percentile',
                # '99-th percentile',
                # 'top-1-percent',
                'ssim',
            ]
            results = xp.empty((len(source_folders), n_frames//iter_step, len(fields)), dtype=np.float32)
            avg_results = xp.empty((len(source_folders), len(fields)), dtype=np.float32)
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
                        load_path = folder/getErrFilename(field, err_type, ref_filter_mode, fast_mode, args.fovea)
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

                params = records_params[folder_index]
                steepness = params.steepness
                midpoint = params.midpoint

                # calculate errors

                for i in tqdm(range(0, n_frames, iter_step), ncols=80):
                    _reference_image = loadImage(reference_path, ref_images_pattern, i+1)
                    _source_image = loadImage(folder, f'{fps}fps.SVGFPass.Filtered image.{{}}.exr', i+1)
                    h,w = _reference_image.shape[:2]
                    pix_count = h*w
                    t = (i+1)/fps
                    if args.fovea:
                        _mask = drawFoveaLissajous(np.zeros((h,w)), 200, t, (0.4, 0.5), (640, 360), (np.pi/2, 0), 1, cv.FILLED)
                        mask_pix_count = xp.sum(_mask)
                        # cv.imshow('mask', _mask)
                        # _src = drawFoveaLissajous(toneMapping(_source_image), 200, t, (0.4, 0.5), (640, 360), (np.pi/2, 0), (0,0,255))
                        # cv.imshow('source', _src)

                    if args.cuda:
                        reference_image = cp.asarray(_reference_image)
                        source_image = cp.asarray(_source_image)
                        if args.fovea:
                            mask = cp.asarray(_mask)
                    else:
                        reference_image = _reference_image
                        source_image = _source_image
                        if args.fovea:
                            mask = _mask

                    if err_type == ErrorType.L1:
                        err = xp.sum(xp.abs(reference_image - source_image), axis=-1)
                    elif err_type == ErrorType.L2:
                        err = xp.linalg.norm(reference_image - source_image, axis=-1, ord=2)
                    elif err_type == ErrorType.REL_MSE:
                        err = xp.sum((reference_image - source_image)**2, axis=-1) / (xp.sum(reference_image**2, axis=-1) + REL_MSE_EPSILON)


                    if 'mean' in fields and not loaded['mean']:
                        if args.fovea:
                            results[folder_index, i//iter_step, fields.index('mean')] = xp.mean(err[mask>0])
                        else:
                            results[folder_index, i//iter_step, fields.index('mean')] = xp.mean(err)

                    if '25-th percentile' in fields and not loaded['25-th percentile']:
                        if args.fovea:
                            percentiles = xp.percentile(err[mask>0], [25, 50, 75, 99])
                        else:
                            percentiles = xp.percentile(err, [25, 50, 75, 99])
                        results[folder_index, i//iter_step, [fields.index(f) for f in fields if 'percentile' in f]] = percentiles

                    if 'top-1-percent' in fields and not loaded['top-1-percent']:
                        if args.fovea:
                            top_1_percent = xp.mean((err*mask)[xp.where(err > percentiles[-1])])
                        else:
                            top_1_percent = xp.mean(err[xp.where(err > percentiles[-1])])
                        results[folder_index, i//iter_step, fields.index('top-1-percent')] = top_1_percent

                    if 'ssim' in fields and not loaded['ssim']:
                        tone_mapped_reference = toneMapping(_reference_image)
                        tone_mapped_source = toneMapping(_source_image)
                        mssim, _ssim_img = ssim(tone_mapped_reference, tone_mapped_source,
                                                gaussian_weights = True,
                                                sigma = 1.5,
                                                use_sample_covariance = False,
                                                data_range = 255,
                                                channel_axis = -1,
                                                full = True)
                        if args.cuda:
                            ssim_img = cp.asarray(_ssim_img)
                        else:
                            ssim_img = _ssim_img
                        # cv.imshow('ssim', ssim_img)
                        if args.fovea:
                            mssim = xp.mean(ssim_img[mask>0])
                        results[folder_index, i//iter_step, fields.index('ssim')] = mssim

                    # cv.waitKey(1)
                gc.collect()


                short_name = folder.name.split('_')[2+scene_name.count('_')]

                avg_results[folder_index, :] = xp.mean(results[folder_index, :, :], axis=0)
                avg_mean_err = avg_results[folder_index, fields.index('mean')]

                print(f'mean({avg_mean_err:.7e}) \t{short_name}')

                # write to file
                for field_indx, field in enumerate(fields):
                    save_path = folder/getErrFilename(field, err_type, ref_filter_mode, fast_mode, args.fovea)
                    with open(save_path, 'w') as f:
                        xp.savetxt(f, results[folder_index, :, field_indx])

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
            table_file_name = f'iters({iters},{feedback})_fps({fps})_t({duration})_{selection_func}_Norm({normalization_mode.name})_Alpha({alpha})_wAlpha({w_alpha})_{err_type.name}_{ref_filter_mode}.txt'
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
                f.write(f'iters: {iters},{feedback}\n')
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
        logI(f'scene "{scene_name}" completed.')

    winsound.Beep(442, 100)
    winsound.Beep(442, 100)

    logI("All done.")
