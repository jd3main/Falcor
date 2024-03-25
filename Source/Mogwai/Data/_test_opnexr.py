# import os
# os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"

import cv2 as cv
import numpy as np
import OpenEXR
import Imath

filename = r'C:\Users\jd3\Desktop\Code\Record\BistroExterior_iters(2,-1,0)_Linear(0.0,0.1)_GAlpha(0.2)_Norm(STANDARD_DEVIATION)_Foveated(CIRCLE,LISSAJOUS,8.0)_Lissajous([0.400000, 0.500000],[640.000000, 360.000000])\30fps.SVGFPass.Filtered image.237.exr'

file = OpenEXR.InputFile(filename)
print(type(file))
print(file.__dir__)
print(file.header())
r = file.channel('R')
print(type(r))
print(r)
