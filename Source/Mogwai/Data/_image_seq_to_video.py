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


MAX_FRAMES = 10
iters='0,-1,0'

# load source images
base_path = Path(__file__).parent/'Record'
path = base_path/f'{scene_name}_iters({iters})_'
reference_images = loadImageSequence(reference_path, '60fps.SVGFPass.Filtered image.{}.exr', MAX_FRAMES)

cv.destroyAllWindows()

