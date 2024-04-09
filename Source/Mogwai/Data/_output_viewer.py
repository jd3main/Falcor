import os
os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"

import cv2 as cv
import numpy as np
from pathlib import Path
import json
import matplotlib.pyplot as plt
from enum import IntEnum, auto

from _utils import *
from DynamicWeighting_Common import *

# scene_name = 'VeachAjar'
scene_name = 'VeachAjarAnimated'
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

sampling = 'Foveated(CIRCLE,LISSAJOUS,8.0)_Circle(200)_Lissajous([0.4,0.5],[640,360])'
# sampling = 'Foveated(CIRCLE,LISSAJOUS,8.0)_Circle(200)_Lissajous([0.4,0.5],[640,0])'
# sampling = 'Adaptive(2.0,10.0,1,1)'


# setup paths
ref_folder_path = record_path/getReferenceFolderNameFiltered(scene_name, ref_sample_count, alpha, iters, feedback)
unweighted_path = record_path/getSourceFolderNameUnweighted(scene_name, iters, feedback, alpha, sampling)
weighted_path = record_path/getSourceFolderNameWeighted(scene_name, iters, feedback, alpha, alpha, sampling)
blended_path = record_path/getSourceFolderNameLinear(scene_name, iters, feedback, midpoint, steepness, alpha, alpha, g_alpha, norm_mode, sampling)

# load images
pattern = f'{fps}fps.SVGFPass.Filtered image.{{}}.exr'

image_sequences = []

try:
    image_sequences.append(("Reference", loadImageSequence(ref_folder_path, pattern, MAX_FRAMES)))
    image_sequences.append(("Unweighted", loadImageSequence(unweighted_path, pattern, MAX_FRAMES)))
    image_sequences.append(("Weighted", loadImageSequence(weighted_path, pattern, MAX_FRAMES)))
    image_sequences.append(("Blended", loadImageSequence(blended_path, pattern, MAX_FRAMES)))
except FileNotFoundError as e:
    logE(e)
    exit()

for name, images in image_sequences:
    print(f'{name}: {len(images)} images')

frame_id = 0
image_seq_index = 0
multplier = 1.0
n_images = len(image_sequences[0][1])
tone_mapping_enabled = True
draw_fovea = False

while True:
    display_image = image_sequences[image_seq_index][1][frame_id]
    display_image_name = image_sequences[image_seq_index][0]

    if tone_mapping_enabled:
        display_image = toneMapping(display_image)
    if draw_fovea:
        t = (frame_id+1) / fps
        display_image = drawFoveaLissajous(display_image, 200, t, (0.4, 0.5), (display_image.shape[1]//2, display_image.shape[0]//2), (np.pi/2, 0))

    display_image = cv.putText(display_image, f'frame {frame_id} {display_image_name}', (10, 30), cv.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv.LINE_AA)
    cv.imshow('image', display_image)

    key = cv.waitKey(0)
    if key == ord('q'):
        break
    elif key == ord('a'):
        frame_id = (frame_id - 1) % n_images
    elif key == ord('d'):
        frame_id = (frame_id + 1) % n_images
    elif key == ord('w'):
        image_seq_index = (image_seq_index + 1) % len(image_sequences)
    elif key == ord('s'):
        image_seq_index = (image_seq_index - 1) % len(image_sequences)
    elif key == ord('t'):
        tone_mapping_enabled = not tone_mapping_enabled
    elif key == ord('f'):
        draw_fovea = not draw_fovea
cv.destroyAllWindows()

