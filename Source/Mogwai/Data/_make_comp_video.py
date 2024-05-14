import os
os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"

import numpy as np
import cv2 as cv
from pathlib import Path
import argparse
import imageio.v2 as iio2
import imageio.v3 as iio3
from tqdm import tqdm


from DynamicWeighting_Common import *
from _utils import *
from _error_measure import ErrorType


def makeSplitView(img1: np.ndarray, img2: np.ndarray, split_width=1, split_color=(0, 0, 0)) -> np.ndarray:
    """Creates a split view of two images.

    Args:
        img1 (np.ndarray): The first image.
        img2 (np.ndarray): The second image.
        split_width (int, optional): The width of the split line. Defaults to 1.
        split_color (tuple, optional): The color of the split line. Defaults to (0, 0, 0).

    Returns:
        np.ndarray: The split view.
    """
    if img1.shape != img2.shape:
        raise ValueError(f"Image shapes do not match: {img1.shape} != {img2.shape}")

    h, w, c = img1.shape
    half_width = w // 2
    split_view = np.empty((h, w, c), dtype=np.uint8)
    split_view[:, :half_width] = img1[:, :half_width]
    split_view[:, half_width:] = img2[:, half_width:]
    split_view[:, half_width - split_width:half_width + split_width] = split_color

    return split_view

def makeConcatView(img1: np.ndarray, img2: np.ndarray) -> np.ndarray:
    """Creates a concatenated view of two images.

    Args:
        img1 (np.ndarray): The first image.
        img2 (np.ndarray): The second image.

    Returns:
        np.ndarray: The concatenated view.
    """
    if img1.shape[0] != img2.shape[0]:
        raise ValueError(f"Image heights do not match: {img1.shape[0]} != {img2.shape[0]}")
    return np.concatenate([img1, img2], axis=1)



parser = argparse.ArgumentParser(description='Make comparison video')
parser.add_argument('mode', type=str, choices=['split', 'concat'], help='mode')
parser.add_argument('--scene_name', type=str, default='', help='scene name')
parser.add_argument('--split_width', type=int, default=1, help='split width')
parser.add_argument('--fps', type=int, default=30, help='fps')
parser.add_argument('-s', '--sampling', type=str, default='f1', help='sampling preset')
parser.add_argument('--selection_func_1', type=str, default='UNWEIGHTED', help='selection function 1')
parser.add_argument('--selection_func_2', type=str, default='LINEAR', help='selection function 2')
args = parser.parse_args()

scene_name = args.scene_name
sampling = args.sampling
selection_func_1 = SelectionMode[args.selection_func_1.upper()]
selection_func_2 = SelectionMode[args.selection_func_2.upper()]

input_1 = f'{scene_name}_{sampling}_{selection_func_1.name}.mp4'
input_2 = f'{scene_name}_{sampling}_{selection_func_2.name}.mp4'
output = f'{scene_name}_{sampling}_{selection_func_1.name}_vs_{selection_func_2.name}.mp4'

frames1 = iio3.imread(input_1)
frames2 = iio3.imread(input_2)

w = iio2.get_writer(output,
                    format='FFMPEG',
                    mode='I',
                    fps=args.fps,
                    codec='libx264',
                    output_params=[
                        '-pix_fmt', 'yuv444p',
                        '-crf', '0',
                    ],
    )

for frame1, frame2 in tqdm(zip(frames1, frames2), total=len(frames1), ncols=80):
    if args.mode == 'split':
        frame = makeSplitView(frame1, frame2, args.split_width)
    elif args.mode == 'concat':
        frame = makeConcatView(frame1, frame2)
    w.append_data(frame)
w.close()

logI(f'Written to {output}')
