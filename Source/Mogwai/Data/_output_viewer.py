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

# load reference images

# load source images
base_path = Path(__file__).parent/'Record'
reference_path = base_path/f'{scene_name}_iters({iters})'
reference_images = loadImageSequence(reference_path, '60fps.SVGFPass.Filtered image.{}.exr', MAX_FRAMES)
unweighted_path = base_path/f'{scene_name}_iters({iters})_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)'
# unweighted_path = base_path/f'{scene_name}_iters({iters})_Unweighted_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)'
weighted_path = base_path/f'{scene_name}_iters({iters})_Weighted_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)'
unweighted_images = loadImageSequence(unweighted_path, '60fps.SVGFPass.Filtered image.{}.exr', MAX_FRAMES)
weighted_images = loadImageSequence(weighted_path, '60fps.SVGFPass.Filtered image.{}.exr', MAX_FRAMES)
# gradient_images = loadImageSequence(weighted_path, '60fps.SVGFPass.OutGradient.{}.exr', MAX_FRAMES)
unweighted_illum_images = loadImageSequence(unweighted_path, '60fps.SVGFPass.Illumination_U.{}.exr', MAX_FRAMES)
weighted_illum_images = loadImageSequence(unweighted_path, '60fps.SVGFPass.Illumination_W.{}.exr', MAX_FRAMES)
filtered_unweighted_illum_images = loadImageSequence(unweighted_path, '60fps.SVGFPass.Filtered_Illumination_U.{}.exr', MAX_FRAMES)
filtered_weighted_illum_images = loadImageSequence(unweighted_path, '60fps.SVGFPass.Filtered_Illumination_W.{}.exr', MAX_FRAMES)
gamma_images = loadImageSequence(unweighted_path, '60fps.SVGFPass.OutGamma.{}.exr', MAX_FRAMES)

image_sequences = [
    ("reference", reference_images),
    ("unweighted", unweighted_images),
    ("weighted", weighted_images),
    ("unweighted_illum", unweighted_illum_images),
    ("weighted_illum", weighted_illum_images),
    ("filtered_unweighted_illum", filtered_unweighted_illum_images),
    ("filtered_weighted_illum", filtered_weighted_illum_images),
    ("gamma", gamma_images),
]

for name, images in image_sequences:
    print(f'{name}: {len(images)} images')

frame_id = 0
image_seq_index = 0
multplier = 1.0

while True:
    display_image = image_sequences[image_seq_index][1][frame_id]
    display_image_name = image_sequences[image_seq_index][0]

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
        image_seq_index = (image_seq_index + 1) % len(image_sequences)
    elif key == ord('s'):
        image_seq_index = (image_seq_index - 1) % len(image_sequences)
    elif key == ord('+'):
        multplier *= 1.1
    elif key == ord('-'):
        multplier /= 1.1
cv.destroyAllWindows()

