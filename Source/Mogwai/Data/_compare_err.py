import os
os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"

import cv2 as cv
import numpy as np
from pathlib import Path
import json
import matplotlib.pyplot as plt
from enum import IntEnum, auto

# scene_name = 'VeachAjarAnimated'
scene_name = 'BistroExterior'
# scene_name = 'EmeraldSquare_Day'
# scene_name = 'SunTemple'

def loadImage(path, filename_pattern:str, frame_id):
    path = Path(path)

    img_path = path/filename_pattern.format(frame_id)
    if not img_path.exists():
        return None
    img = cv.imread(str(img_path), cv.IMREAD_ANYCOLOR | cv.IMREAD_ANYDEPTH | cv.IMREAD_UNCHANGED)
    return img

def loadImageSequence(path, filename_pattern:str, max_frame_id=None):
    path = Path(path)
    dataset = []
    frame_id = 1
    while (max_frame_id is None) or (frame_id < max_frame_id):
        img = loadImage(path, filename_pattern, frame_id)
        if img is None:
            break
        dataset.append(img)
        frame_id += 1
    return dataset

record_path = Path(__file__).parents[4]/'Record'
MAX_FRAMES = 120
iters='1,-1,1'

# load reference images
reference_path = record_path/f'{scene_name}_iters({iters})'
reference_images = loadImageSequence(reference_path, '60fps.SVGFPass.Filtered image.{}.exr', MAX_FRAMES)
if len(reference_images) == 0:
    print(f'cannot load reference images')
    exit()

# load source images
unweighted_path = record_path/f'{scene_name}_iters({iters})_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)'
weighted_path = record_path/f'{scene_name}_iters({iters})_Weighted_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)'
unweighted_images = loadImageSequence(unweighted_path, '60fps.SVGFPass.Filtered image.{}.exr', MAX_FRAMES)
weighted_images = loadImageSequence(weighted_path, '60fps.SVGFPass.Filtered image.{}.exr', MAX_FRAMES)
# gradient_images = loadImageSequence(weighted_path, '60fps.SVGFPass.OutGradient.{}.exr', MAX_FRAMES)

print(f'{len(reference_images)} reference images')
print(f'{len(unweighted_images)} unweighted images')
print(f'{len(weighted_images)} weighted images')

# calculate errors
mean_errs = []
max_errs = []
errs = [[],[]]
for image_set_index, source_images in enumerate([unweighted_images, weighted_images]):
    assert len(source_images) <= len(reference_images)

    # calculate mean square error
    mean_err = np.empty(len(source_images))
    max_err = np.empty(len(source_images))
    for i in range(len(source_images)):
        err = np.square(reference_images[i] - source_images[i])
        errs[image_set_index].append(err)
        mean_err[i] = np.mean(err)
        max_err[i] = np.max(err)
    mean_errs.append(mean_err)
    max_errs.append(max_err)

assert (len(mean_errs) == 2) and (len(max_errs) == 2)

print(f'average unweighted mean error: {np.mean(mean_errs[0])}')
print(f'average weighted mean error: {np.mean(mean_errs[1])}')

frame_id = 0
class DisplayImageType(IntEnum):
    DIFF = 0
    WEIGHTED = 1
    UNWEIGHTED = 2
    REFERENCE = 3
    # GRADIENT = 4,
    MAX = auto()
display_image_type = DisplayImageType.DIFF
multplier = 1.0

while True:
    weighted_better_color = np.array([0, 255, 0], dtype=np.float32)
    unweighted_better_color = np.array([0, 0, 255], dtype=np.float32)
    same_color = np.array([255, 255, 255], dtype=np.float32)
    diff = np.mean(errs[0][frame_id] - errs[1][frame_id], axis=2)
    diff_color = np.full((diff.shape[0], diff.shape[1], 3), 255, dtype=np.float32)
    diff_color[diff > 0] = np.outer(diff[diff > 0], weighted_better_color)
    diff_color[diff < 0] = np.outer(-diff[diff < 0], unweighted_better_color)

    small_indices = np.absolute(diff) < 0.001
    diff_color[diff == 0] = same_color

    display_image = None
    display_image_name = None
    if display_image_type == DisplayImageType.DIFF:
        display_image = diff_color
        display_image_name = 'diff'
    elif display_image_type == DisplayImageType.WEIGHTED:
        display_image = weighted_images[frame_id]
        display_image_name = 'weighted'
    elif display_image_type == DisplayImageType.UNWEIGHTED:
        display_image = unweighted_images[frame_id]
        display_image_name = 'unweighted'
    elif display_image_type == DisplayImageType.REFERENCE:
        display_image = reference_images[frame_id]
        display_image_name = 'reference'
    # elif display_image_type == DisplayImageType.GRADIENT:
    #     display_image = gradient_images[frame_id]
    #     display_image_name = 'gradient'
    display_image = cv.putText(display_image, f'frame {frame_id} {display_image_name}', (10, 30), cv.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv.LINE_AA)
    cv.imshow('image', display_image * multplier)


    key = cv.waitKey(0)
    if key == ord('q'):
        break
    elif key == ord('a'):
        frame_id = (frame_id - 1) % len(reference_images)
    elif key == ord('d'):
        frame_id = (frame_id + 1) % len(reference_images)
    elif key == ord('w'):
        display_image_type = (display_image_type + 1) % DisplayImageType.MAX
    elif key == ord('s'):
        display_image_type = (display_image_type - 1) % DisplayImageType.MAX
    elif key == ord('+'):
        multplier *= 1.1
    elif key == ord('-'):
        multplier /= 1.1
cv.destroyAllWindows()
