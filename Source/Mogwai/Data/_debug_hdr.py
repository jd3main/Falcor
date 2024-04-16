import os
os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"

import cv2 as cv
import numpy as np
from pathlib import Path
import json
import matplotlib.pyplot as plt
from enum import IntEnum, auto

from matplotlib import pyplot as plt

from _utils import *
from DynamicWeighting_Common import *

def ACESFilm(x:np.ndarray):
    x = x * 0.6
    a = 2.51
    b = 0.03
    c = 2.43
    d = 0.59
    e = 0.14
    return np.clip((x*(a*x+b))/(x*(c*x+d)+e), 0.0, 1.0)

def gammaCorrection(img: np.ndarray, gamma: float) -> np.ndarray:
    return np.power(img, gamma)

def toneMapping(img: np.ndarray, gamma=1/1.22) -> np.ndarray:
    img = ACESFilm(img)
    img = gammaCorrection(img, gamma)
    img = (img * 255).astype(np.uint8)
    return img

hdr_img = cv.imread('30fps.SVGFPass.Filtered image.2.exr', cv.IMREAD_ANYCOLOR | cv.IMREAD_ANYDEPTH | cv.IMREAD_UNCHANGED)
ldr_img = cv.imread('30fps.ToneMapper.dst.2.png')
# ldr_img = cv.imread('30fps.ToneMapper.dst.2.exr', cv.IMREAD_ANYCOLOR | cv.IMREAD_ANYDEPTH | cv.IMREAD_UNCHANGED)
tone_mapped = ACESFilm(hdr_img)
tone_mapped = gammaCorrection(tone_mapped, 1/2.2)
tone_mapped = (tone_mapped*255).astype(np.uint8)
cv.imwrite('test.png', tone_mapped)
tone_mapped = cv.imread('test.png')

# tone_mapped = cv.imread('30fps.ToneMapper.dst.2.exr', cv.IMREAD_ANYCOLOR | cv.IMREAD_ANYDEPTH | cv.IMREAD_UNCHANGED)
# tone_mapped = (tone_mapped*255).astype(np.uint8)
# cv.imwrite('test.exr', ldr_img)
# tone_mapped = cv.imread('test.exr', cv.IMREAD_ANYCOLOR | cv.IMREAD_ANYDEPTH | cv.IMREAD_UNCHANGED)


print(f'max: {np.max(hdr_img, axis=(0,1))}')
print(f'max: {np.max(ldr_img, axis=(0,1))}')
print(f'max: {np.max(tone_mapped, axis=(0,1))}')
print(f'mean: {np.mean(hdr_img, axis=(0,1))}')
print(f'mean: {np.mean(ldr_img, axis=(0,1))}')
print(f'mean: {np.mean(tone_mapped, axis=(0,1))}')

for p in [(0,0), (1,1), (2,2)]:
    # print(f'p: {hdr_img[p]}')
    print(f'ldr_img    : {ldr_img[p]}')
    print(f'tone_mapped: {tone_mapped[p]}')
    # print(f'p: {(tone_mapped*255)[p]}')
    # print(f'p: {(tone_mapped*255).astype(np.uint8)[p]}')

plt.scatter(hdr_img.flatten()[:5000], ldr_img.flatten()[:5000])
plt.scatter(hdr_img.flatten()[:5000], tone_mapped.flatten()[:5000])
plt.plot(np.arange(0, 10, 0.001), gammaCorrection(ACESFilm(np.arange(0, 10, 0.001)), 1/2.2)*255)
plt.show()

# cv.imshow('HDR', hdr_img)
cv.imshow('LDR', ldr_img)
cv.imshow('ToneMapped', tone_mapped)
cv.waitKey(0)

