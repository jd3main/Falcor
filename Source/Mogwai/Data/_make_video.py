import os
os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"

import numpy as np
import cv2 as cv
from pathlib import Path

from DynamicWeighting_Common import *
from _utils import *

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

def ACESFilm(x):
    a = 2.51
    b = 0.03
    c = 2.43
    d = 0.59
    e = 0.14
    return np.clip((x*(a*x+b))/(x*(c*x+d)+e), 0, 1)


params = {
    "scene_name": "VeachAjarAnimated",
    "iters": 4,
    "feedback": 0,
    "selection_func": "Weighted", # "Unweighted", "Weighted", "Linear", "Step"
    "midpoint": 0.5,
    "steepness": 1.0,
    "alpha": 0.05,
    "w_alpha": 0.05,
    "g_alpha": 0.2,
    "norm_mode": NormalizationMode.STD,
    "sampling": 'Foveated(CIRCLE,LISSAJOUS,8.0)_Lissajous([0.400000, 0.500000],[640.000000, 360.000000])',
}

record_path = Path(__file__).parents[4]/'Record'
folder_name = getSourceFolderName(**params)
file_pattern = '30fps.SVGFPass.Filtered image.{}.exr'

FPS = 30
DURATION = 20
N_FRAMES = FPS * DURATION
fovea_radius = 300.0

img_loader = imageSequenceLoader(record_path/folder_name, file_pattern, N_FRAMES)
fourcc = cv.VideoWriter_fourcc(*'XVID')
out = cv.VideoWriter('output.avi', fourcc, FPS, (1280, 720))
for i, img in enumerate(img_loader):
    t = (i+1) / float(FPS)
    print(f"Frame {i}: t = {t}")
    foveated_img = drawFoveaLissajous(img, fovea_radius, t, (0.4, 0.5), (640, 360), (np.pi/2, 0), color=(0, 0, 255), thickness=1)

    tone_mapped_img = ACESFilm(foveated_img)

    if tone_mapped_img.dtype != np.uint8:
        tone_mapped_img = (tone_mapped_img * 255).astype(np.uint8)
    out.write(tone_mapped_img)

    cv.imshow('Image', tone_mapped_img)
    key = cv.waitKey(1)
    if key == ord('q'):
        break
