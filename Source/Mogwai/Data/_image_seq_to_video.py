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

MAX_FRAMES = 60*20
iters='2,-1,2'
midpoint = 0.001
steepness = 50.0

# load source images
record_path = Path(__file__).parent/'Record'
paths = [
    record_path/f'{scene_name}_iters({iters})_Logistic({midpoint},{steepness})_GAlpha(0.2)_Norm(STANDARD_DEVIATION)_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)',
    record_path/f'{scene_name}_iters({iters})_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)'
]
for path in paths:
    images = loadImageSequence(path, '60fps.SVGFPass.Filtered image.{}.exr', MAX_FRAMES)

    print(f'{len(images)} images loaded')

    # output video
    size = (images[0].shape[1], images[0].shape[0])
    fps = 60
    filename = path.name
    ext = '.mp4'
    fourcc = cv.VideoWriter_fourcc(*'mp4v')

    output_path = record_path/'Video'
    ensurePath(output_path)
    full_output_path = output_path/(filename+ext)
    print(f'writing video to {full_output_path}')

    print(f'size = {size}')

    out = cv.VideoWriter(str(full_output_path), fourcc, fps, size)
    for img in images:
        # convert to 8-bit
        output_img = (img*255).clip(0,255).astype(np.uint8)
        # output_img = cv.cvtColor(output_img, cv.COLOR_RGB2BGR)
        # print(output_img)
        # output_img = cv.imread('test.png')
        # assert output_img.shape == (720, 1280, 3)

        out.write(output_img)
    out.release()

print('done')

