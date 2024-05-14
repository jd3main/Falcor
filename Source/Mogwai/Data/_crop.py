import os
os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"

import cv2 as cv
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from enum import IntEnum, auto
import argparse

from _utils import *
from DynamicWeighting_Common import *


DEFAULT_NORMALZATION_MODE = NormalizationMode.STD

# DEFAULT_SCENE_NAME = 'VeachAjar'
# DEFAULT_SCENE_NAME = 'VeachAjarAnimated'
# DEFAULT_SCENE_NAME = 'VeachAjarAnimated2'
# DEFAULT_SCENE_NAME = 'BistroExterior'
# DEFAULT_SCENE_NAME = 'BistroInterior'
# DEFAULT_SCENE_NAME = 'BistroInterior_Wine'
# DEFAULT_SCENE_NAME = 'EmeraldSquare_Day'
# DEFAULT_SCENE_NAME = 'SunTemple'
# DEFAULT_SCENE_NAME = 'MEASURE_ONE'
# DEFAULT_SCENE_NAME = 'MEASURE_SEVEN'
DEFAULT_SCENE_NAME = 'ZeroDay_1'
DEFAULT_SCENE_NAME = 'ZeroDay_7'
DEFAULT_SCENE_NAME = 'ZeroDay_7c'


### Argument parsing
parser = argparse.ArgumentParser(description='Compare and crop images')
parser.add_argument('-n', '--norm_mode', type=str, default=DEFAULT_NORMALZATION_MODE.name, help='normalization mode')
parser.add_argument('--scene_name', type=str, default=DEFAULT_SCENE_NAME, help='scene name')
parser.add_argument('--frame', type=int, default=1, help='frame id')
parser.add_argument('--fg', action='store_true', help='filter gradient')
parser.add_argument('--bg', action='store_true', help='best gamma')
parser.add_argument('-s', '--sampling', type=str, default='f1', help='sampling preset')
args = parser.parse_args()


record_path = Path(__file__).parents[4]/'Record'
scene_name = args.scene_name
MAX_FRAMES = 10000
fps = 30
iters = 2
feedback = 0
ref_sample_count = 128
alpha = 0.05
midpoint = 0.5
steepness = 1.0
g_alpha = 0.2
norm_mode = NormalizationMode[args.norm_mode.upper()]
filter_graidient = args.fg
best_gamma = args.bg

sampling = getSamplingPreset(args.sampling)

fovea_radius = 200.0


# setup paths
ref_folder_path = record_path/getReferenceFolderNameFiltered(scene_name, ref_sample_count, alpha, iters, feedback)
unweighted_path = record_path/getSourceFolderNameUnweighted(scene_name, iters, feedback, alpha, sampling)
weighted_path = record_path/getSourceFolderNameWeighted(scene_name, iters, feedback, alpha, alpha, sampling)
blended_path = record_path/getSourceFolderNameLinear(scene_name, iters, feedback, midpoint, steepness, alpha, alpha, g_alpha, NormalizationMode.STD, sampling, filter_graidient, best_gamma)
# blended2_path = record_path/getSourceFolderNameLinear(scene_name, iters, feedback, midpoint, steepness, alpha, alpha, g_alpha, NormalizationMode.STD, sampling, filter_graidient, not best_gamma)

pattern = f'{fps}fps.SVGFPass.Filtered image.{{}}.exr'

frame_id = args.frame
tone_mapping_enabled = True
draw_fovea = False
draw_crop = True

# cropping rect
# top, bottom, left, right = 0, 400, 900, 1200
top, bottom, left, right = 590, 690, 350, 450
speed = 50
display_src = 0

sample_count_scale = 256//16

fovea_color = (0,255,0)
line_color = (255,255,255)
box_color = (0,100,255)

refPt = []
cropping = False

def isValidRect(p1, p2):
    return p1[0] < p2[0] and p1[1] < p2[1]

def click_and_crop(image, event, x, y, flags, param):
    global refPt, cropping

    if event == cv.EVENT_LBUTTONDOWN:
        refPt = [(x, y)]
        cropping = True
    elif event == cv.EVENT_LBUTTONUP:
        if not isValidRect(refPt[0], (x, y)):
            refPt = []
            return
        refPt.append((x, y))
        cropping = False
        tmp_image = cv.rectangle(image.copy(), refPt[0], refPt[1], (0, 255, 0), 2)
        cv.imshow("src", tmp_image)
    elif cropping:
        tmp_image = cv.rectangle(image.copy(), refPt[0], (x, y), (0, 255, 0), 2)
        cv.imshow("src", tmp_image)


while True:
    width = right - left
    height = bottom - top

    t = (frame_id) / float(fps)
    print(f'Frame {frame_id}: t = {t}')
    print(f'Crop: ({left}, {top}) - ({right}, {bottom})')

    images = [
        loadImage(ref_folder_path, pattern, frame_id),
        loadImage(unweighted_path, pattern, frame_id),
        loadImage(weighted_path, pattern, frame_id),
        loadImage(blended_path, pattern, frame_id),
        # loadImage(blended2_path, pattern, frame_id),
        # loadImage(unweighted_path, '30fps.FoveatedPass.sampleCount.{}.png', frame_id),
        # loadImage(unweighted_path, '30fps.AdaptiveSampling.sampleCount.{}.png', frame_id) * sample_count_scale,
        # loadImage(weighted_path, '30fps.AdaptiveSampling.sampleCount.{}.png', frame_id) * sample_count_scale,
        # loadImage(blended_path, '30fps.AdaptiveSampling.sampleCount.{}.png', frame_id) * sample_count_scale,
    ]


    # crop
    canvas = np.zeros((height, width*len(images), 3), dtype=np.uint8)
    cur_src = None
    for i, src in enumerate(images):

        if tone_mapping_enabled and src.dtype != np.uint8:
            src = toneMapping(src)

        if draw_fovea:
            src = drawFoveaLissajous(src, fovea_radius, t, (0.4, 0.5), (640, 360), (np.pi/2, 0), thickness=2, color=fovea_color)
        if draw_crop:
            src = cv.rectangle(src, (left, top), (right, bottom), box_color, 3)

        if display_src == i:
            cur_src = src
            cv.imshow('src', src)
            cv.setMouseCallback("src", lambda event,x,y,flags,param,image=src: click_and_crop(image,event,x,y,flags,param))



        canvas[:, i*width:(i+1)*width] = src[top:bottom, left:right]

    # draw lines
    # for i in range(len(images)):
    #     cv.line(canvas, (i*width, 0), (i*width, height), line_color, 1)

    cv.imshow('cropped', canvas)
    key = cv.waitKey(1)
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
        right += width//4
        left -= width//4
        bottom += height//4
        top -= height//4
    elif key == ord('-'):
        right -= width//8
        left += width//8
        bottom -= height//8
        top += height//8
    elif key == ord(' '):
        cv.imwrite('cropped.png', canvas)
        cv.imwrite('src.png', cur_src)
    elif key == ord('c'):
        draw_crop = not draw_crop

    if len(refPt) == 2:
        logI("CROP")
        left, top = refPt[0]
        right, bottom = refPt[1]
        refPt = []


    left = np.clip(left, 0, 1280)
    right = np.clip(right, 0, 1280)
    top = np.clip(top, 0, 720)
    bottom = np.clip(bottom, 0, 720)
