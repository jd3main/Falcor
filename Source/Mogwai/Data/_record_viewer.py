import os
os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"

from pathlib import Path
import cv2 as cv
import numpy as np
import json
from DynamicWeighting_Common import *
from _utils import *


def loadMetadata(path) -> dict:
    '''
    Load metadata from a file.
    '''
    path = Path(path)
    data = dict()
    try:
        with open(path/'metadata.txt', 'r') as f:
            data = dict(**json.load(f))
    except Exception as e:
        logE(f'cannot load metadata from {path/"metadata.txt"}')
        logE(e)
    return data

scene_name = 'VeachAjar'



record_id = 1
record_path = Path(__file__).parents[4]/'Record'/'VeachAjar_iters(0,-1)_Alpha(0.05)_128'
metadata = loadMetadata(record_path)
dt = 1000 // 60
print(metadata)
image_id = 1
while True:
    img_path = record_path/f'30fps.SVGFPass.Filtered image.{image_id}.exr'
    if not img_path.exists():
        break
    img = cv.imread(str(img_path), cv.IMREAD_ANYCOLOR | cv.IMREAD_ANYDEPTH | cv.IMREAD_UNCHANGED)
    cv.imshow('img', img)
    cv.waitKey(dt)
    image_id += 1

cv.waitKey(0)
cv.destroyAllWindows()
