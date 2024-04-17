import os
os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"

import cv2 as cv
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from enum import IntEnum, auto

from _utils import *
from DynamicWeighting_Common import *

scene_name = 'VeachAjar'
# scene_name = 'VeachAjarAnimated'
# scene_name = 'BistroExterior'
# scene_name = 'BistroInterior'
# scene_name = 'BistroInterior_Wine'
# scene_name = 'EmeraldSquare_Day'
# scene_name = 'SunTemple'

record_path = Path(__file__).parents[4]/'Record'
MAX_FRAMES = 10000
fps = 30
iters = 2
feedback = 0
ref_sample_count = 128
alpha = 0.05
midpoint = 0.5
steepness = 1.0
g_alpha = 0.2
norm_mode = NormalizationMode.STD
filter_graidient = True

sampling = 'Foveated(CIRCLE,LISSAJOUS,8.0)_Circle(200)_Lissajous([0.4,0.5],[640,360])'
# sampling = 'Adaptive(2.0,10.0,1,1)'

fovea_radius = 200.0


# setup paths
ref_folder_path = record_path/getReferenceFolderNameFiltered(scene_name, ref_sample_count, alpha, iters, feedback)
unweighted_path = record_path/getSourceFolderNameUnweighted(scene_name, iters, feedback, alpha, sampling)
weighted_path = record_path/getSourceFolderNameWeighted(scene_name, iters, feedback, alpha, alpha, sampling)
blended_path = record_path/getSourceFolderNameLinear(scene_name, iters, feedback, midpoint, steepness, alpha, alpha, g_alpha, norm_mode, sampling, filter_graidient)

pattern = f'{fps}fps.SVGFPass.Filtered image.{{}}.exr'

frame_id = 226
tone_mapping_enabled = True
draw_fovea = False

# cropping rect
# top, bottom, left, right = 0, 400, 900, 1200
top, bottom, left, right = 200, 600, 400, 600
speed = 50
display_src = 0

sample_count_scale = 256//16

while True:
    width = right - left
    height = bottom - top

    t = (frame_id) / float(fps)
    print(f'Frame {frame_id}: t = {t}')

    images = [
        loadImage(ref_folder_path, pattern, frame_id),
        loadImage(unweighted_path, pattern, frame_id),
        loadImage(weighted_path, pattern, frame_id),
        loadImage(blended_path, pattern, frame_id),
        # loadImage(unweighted_path, '30fps.FoveatedPass.sampleCount.{}.png', frame_id),
        # loadImage(unweighted_path, '30fps.AdaptiveSampling.sampleCount.{}.png', frame_id) * sample_count_scale,
        # loadImage(weighted_path, '30fps.AdaptiveSampling.sampleCount.{}.png', frame_id) * sample_count_scale,
        # loadImage(blended_path, '30fps.AdaptiveSampling.sampleCount.{}.png', frame_id) * sample_count_scale,
    ]


    # crop
    canvas = np.zeros((height, width*len(images), 3), dtype=np.uint8)
    for i, src in enumerate(images):

        if tone_mapping_enabled and src.dtype != np.uint8:
            src = toneMapping(src)

        if draw_fovea:
            src = drawFoveaLissajous(src, fovea_radius, t, (0.4, 0.5), (640, 360), (np.pi/2, 0), thickness=1)

        if display_src == i:
            cv.imshow('src', src)

        canvas[:, i*width:(i+1)*width] = src[top:bottom, left:right]


    cv.imshow('cropped', canvas)
    key = cv.waitKey(0)
    if key == ord('q'):
        break
    elif key == ord('a'):
        frame_id -= 1
    elif key == ord('d'):
        frame_id += 1
    elif key == ord('w'):
        display_src = (display_src + 1) % len(images)
    elif key == ord('s'):
        display_src = (display_src - 1) % len(images)
    elif key == ord('8'):
        top -= speed
        bottom -= speed
    elif key == ord('2'):
        top += speed
        bottom += speed
    elif key == ord('4'):
        left -= speed
        right -= speed
    elif key == ord('6'):
        left += speed
        right += speed
    elif key == ord('t'):
        tone_mapping_enabled = not tone_mapping_enabled
    elif key == ord('f'):
        draw_fovea = not draw_fovea
    elif key == ord('+'):
        right += width//2
        left -= width//2
        bottom += height//2
        top -= height//2
    elif key == ord('-'):
        right -= width//4
        left += width//4
        bottom -= height//4
        top += height//4


    left = np.clip(left, 0, 1280)
    right = np.clip(right, 0, 1280)
    top = np.clip(top, 0, 720)
    bottom = np.clip(bottom, 0, 720)
