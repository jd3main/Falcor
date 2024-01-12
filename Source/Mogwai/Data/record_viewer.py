import os
os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"

import cv2 as cv
import numpy as np
from pathlib import Path


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
        print(f'cannot load metadata from {path/"metadata.txt"}')
    return data

scene_name = 'VeachAjarAnimated'



record_id = 1
record_path = Path(__file__).parent/'Record'/f'Record_{record_id}'
metadata = loadMetadata(record_path)
dt = 1000 // 60
print(metadata)
image_id = 1
while True:
    img_path = record_path/f'VeachAjarAnimated,0-1,60fps.SVGFPass.Filtered image.{image_id}.exr'
    if not img_path.exists():
        break
    img = cv.imread(str(img_path), cv.IMREAD_ANYCOLOR | cv.IMREAD_ANYDEPTH | cv.IMREAD_UNCHANGED)
    cv.imshow('img', img)
    cv.waitKey(dt)
    image_id += 1

cv.waitKey(0)
cv.destroyAllWindows()
