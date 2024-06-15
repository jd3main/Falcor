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
iters='1,-1,1'
midpoint = 0.001
steepness = 50.0

# load source images
base_path = Path(__file__).parent/'Record'
paths = [
    base_path/f'{scene_name}_iters({iters})_Logistic({midpoint},{steepness})_GAlpha(0.2)_Norm(STANDARD_DEVIATION)_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)',
    base_path/f'{scene_name}_iters({iters})_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)'
]
image_sequences = [
    loadImageSequence(paths[0], '60fps.SVGFPass.Filtered image.{}.exr', MAX_FRAMES),
    loadImageSequence(paths[1], '60fps.SVGFPass.Filtered image.{}.exr', MAX_FRAMES)
]

n = min(len(image_sequences[0]), len(image_sequences[1]))

print(f'{len(image_sequences[0])} images loaded')
print(f'{len(image_sequences[1])} images loaded')
_img = image_sequences[0][0]
w, h = _img.shape[1], _img.shape[0]
size = (w, h)
print(f'size = {size}')

# output video
fps = 60
filename = f'split({paths[0].name},{paths[1].name})'
ext = '.mp4'
fourcc = cv.VideoWriter_fourcc(*'mp4v')

output_path = base_path/'Video'
ensurePath(output_path)
full_output_path = output_path/(filename+ext)
print(f'writing video to {full_output_path}')

out = cv.VideoWriter(str(full_output_path), fourcc, fps, size)
for i in range(n):
    left = (image_sequences[0][i]*255).clip(0,255).astype(np.uint8)
    right = (image_sequences[1][i]*255).clip(0,255).astype(np.uint8)
    split_img = np.zeros(left.shape, dtype=np.uint8)
    split_img[:,:w//2,:] = left[:,:w//2,:]
    split_img[:,w//2:,:] = right[:,w//2:,:]
    cv.line(split_img, (w//2,0), (w//2,h), (255,255,255), 1)
    out.write(split_img)
out.release()

print('done')

