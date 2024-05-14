import os
os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"

import cv2 as cv
import numpy as np
# import OpenEXR
import Imath

from matplotlib import pyplot as plt

from DynamicWeighting_Common import *


filename = r'C:\Users\jd3\Desktop\Code\Record\ZeroDay_7_iters(2,0)_Alpha(0.05)_128\30fps.SVGFPass.Filtered image.1.exr'

# file = OpenEXR.InputFile(filename)
# print(type(file))
# print(file.__dir__)
# print(file.header())
# r = file.channel('R')
# print(type(r))
# print(r)

x = np.arange(0, 1, 0.01)
plt.plot(x, ACESFilm(x))
plt.show()

img = cv.imread(str(filename), cv.IMREAD_ANYCOLOR | cv.IMREAD_ANYDEPTH | cv.IMREAD_UNCHANGED)
cv.imshow("HDR",gammaCorrection(img, 1.0/2.2))
cv.imshow("1", gammaCorrection(ACESFilm(img), 1.0/2.2))
cv.imshow("2", ACESFilm(gammaCorrection(img, 1.0/2.2)))
cv.imshow("3", np.clip((ACESFilm(gammaCorrection(img, 1.0/2.2))*255),0,255).astype(np.uint8))
cv.imshow("4", toneMapping(img))
# img = img.astype(np.uint8)
cv.waitKey(0)
