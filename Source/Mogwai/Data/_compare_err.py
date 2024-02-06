import os
os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"

import cv2 as cv
import numpy as np
from pathlib import Path
import json
import matplotlib.pyplot as plt
from enum import IntEnum, auto
from _utils import *

scene_name = 'VeachAjarAnimated'
# scene_name = 'BistroExterior'
# scene_name = 'EmeraldSquare_Day'
# scene_name = 'SunTemple'


record_path = Path(__file__).parents[4]/'Record'
MAX_FRAMES = 30
fps = 30
iters = (2, -1, 0)
ref_iters = (iters[0], iters[1], iters[0])

iters = ','.join(map(str, iters))
ref_iters = ','.join(map(str, ref_iters))

# load reference images
reference_path = record_path/f'{scene_name}_iters({ref_iters})'
reference_images = loadImageSequence(reference_path, f'{fps}fps.SVGFPass.Filtered image.{{}}.exr', MAX_FRAMES)
if len(reference_images) == 0:
    print(f'cannot load reference images')
    exit()

# load source images
unweighted_path = record_path/f'{scene_name}_iters({iters})_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)'
weighted_path = record_path/f'{scene_name}_iters({iters})_Weighted_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)'

steepness = 50.0
midpoint = 0.01
dynamic_weighted_path = record_path/f'{scene_name}_iters({iters})_Linear({midpoint},{steepness})_GAlpha(0.2)_Norm(STANDARD_DEVIATION)_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)'

unweighted_images = loadImageSequence(unweighted_path, f'{fps}fps.SVGFPass.Filtered image.{{}}.exr', MAX_FRAMES)
weighted_images = loadImageSequence(weighted_path, f'{fps}fps.SVGFPass.Filtered image.{{}}.exr', MAX_FRAMES)
dynamic_weighted_images = loadImageSequence(dynamic_weighted_path, f'{fps}fps.SVGFPass.Filtered image.{{}}.exr', MAX_FRAMES)
# gradient_images = loadImageSequence(weighted_path, f'{fps}fps.SVGFPass.OutGradient.{{}}.exr', MAX_FRAMES)

print(f'{len(reference_images)} reference images')
print(f'{len(unweighted_images)} unweighted images')
print(f'{len(weighted_images)} weighted images')
print(f'{len(dynamic_weighted_images)} dynamic weighted images')

sources = [unweighted_images, weighted_images, dynamic_weighted_images]
sources_names = ['unweighted', 'weighted', 'dynamic weighted']

# calculate errors
mean_errs:list[float] = []
max_errs:list[float] = []
h, w = reference_images[0].shape[0:2]
print(f'images shape: h={h}, w={w}')
errs = np.empty((len(sources), len(reference_images), h, w), dtype=float)
for source_index, source_images in enumerate(sources):
    assert len(source_images) <= len(reference_images)

    # calculate mean square error
    mean_err = np.empty(len(source_images))
    max_err = np.empty(len(source_images))
    for i in range(len(source_images)):
        err = np.linalg.norm(reference_images[i] - source_images[i], axis=-1)
        errs[source_index, i, :, :] = err
        mean_err[i] = np.mean(err)
        max_err[i] = np.max(err)
    mean_errs.append(mean_err)
    max_errs.append(max_err)

assert (len(mean_errs) == len(sources)) and (len(max_errs) == len(sources))

def makeErrCompImage(err1:np.ndarray, err2:np.ndarray):
    n_frames, h, w = err1.shape
    err1_better_color = np.array([0, 0, 255], dtype=np.float32)
    err2_better_color = np.array([0, 255, 0], dtype=np.float32)
    err_same_color = np.array([255, 255, 255], dtype=np.float32)
    diff = (err1 - err2)
    diff_color = np.empty((n_frames, h, w, 3), dtype=np.float32)
    diff_color[diff < 0] = np.outer(-diff[diff < 0], err1_better_color)
    diff_color[diff > 0] = np.outer(diff[diff > 0], err2_better_color)
    # small_indices = np.absolute(diff) < 0.001
    diff_color[diff == 0] = err_same_color
    return diff_color

err_comp_sequences = [makeErrCompImage(errs[0,:,:,:], errs[i,:,:,:]) for i in range(len(sources))]

for i in range(len(sources)):
    print(f'{sources_names[i]} mean error: {np.mean(mean_errs[i])}')

class DisplayImageType(IntEnum):
    REFERENCE = 0
    SOURCE = auto()
    ERR_COMP = auto()
    GRADIENT = auto()
    MAX = auto()

display_image_type = DisplayImageType.SOURCE
frame_id = 0
source_id = 0
multplier = 1.0

while True:

    display_image = None
    display_image_name: str = None
    err_str: str = ''
    if display_image_type == DisplayImageType.REFERENCE:
        display_image = reference_images[frame_id]
        display_image_name = 'reference'
    elif display_image_type == DisplayImageType.SOURCE:
        display_image = sources[source_id][frame_id]
        display_image_name = sources_names[source_id]
        err_str = f'mean error: {mean_errs[source_id][frame_id]:.4f}'
    elif display_image_type == DisplayImageType.ERR_COMP:
        display_image = err_comp_sequences[source_id][frame_id]
        display_image_name = f'comp({sources_names[0]}, {sources_names[source_id]})'
        err_str = f'mean error: {mean_errs[0][frame_id]:.4f}, {mean_errs[source_id][frame_id]:.4f}'
    # elif display_image_type == DisplayImageType.GRADIENT:
    #     display_image = gradient_images[frame_id]
    #     display_image_name = 'gradient'
    display_image = cv.putText(display_image, f'frame {frame_id} {display_image_name}',
                               (10, 30), cv.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv.LINE_AA)
    display_image = cv.putText(display_image, err_str,
                               (10, 60), cv.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv.LINE_AA)
    cv.imshow('image', display_image * multplier)


    key = cv.waitKey(0)
    if key == ord('q'):
        break
    elif key == ord('a'):
        frame_id = (frame_id - 1) % len(reference_images)
    elif key == ord('d'):
        frame_id = (frame_id + 1) % len(reference_images)
    elif key == ord('w'):
        source_id = (source_id + 1) % len(sources)
    elif key == ord('s'):
        source_id = (source_id - 1) % len(sources)
    elif key == ord('1'):
        display_image_type = DisplayImageType.REFERENCE
    elif key == ord('2'):
        display_image_type = DisplayImageType.SOURCE
    elif key == ord('3'):
        display_image_type = DisplayImageType.ERR_COMP
    elif key == ord('+'):
        multplier *= 1.1
    elif key == ord('-'):
        multplier /= 1.1
cv.destroyAllWindows()
