import os
os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"

import numpy as np
import cv2 as cv
from pathlib import Path
import argparse
import imageio.v2 as iio2
import imageio.v3 as iio3
from tqdm import tqdm


from DynamicWeighting_Common import *
from _utils import *
from _error_measure import ErrorType
from _animation_lengths import animation_lengths


FOVEA_COLOR = (255, 0, 0)

parser = argparse.ArgumentParser(description='Make video with fovea')
parser.add_argument('input', type=str, help='input path')
parser.add_argument('--center', action='store_true', help='draw center')
parser.add_argument('--fps', type=int, default=30, help='fps')
parser.add_argument('-rx', '--radius_x', type=float, default=0.0, help='radius x')
parser.add_argument('-ry', '--radius_y', type=float, default=300.0, help='radius y')
parser.add_argument('-th', '--thickness', type=int, default=1, help='thickness')
args = parser.parse_args()

input_path = Path(args.input)
output_path = input_path.parent/(input_path.stem + '_fovea' + input_path.suffix)
move_radius = (args.radius_x, args.radius_y)
draw_center = args.center
thickness = args.thickness

frames = iio3.imread(str(input_path))

w = iio2.get_writer(output_path,
                    format='FFMPEG',
                    mode='I',
                    fps=args.fps,
                    codec='rawvideo',
                    output_params=[
                        '-pix_fmt', 'bgr24',
                        # '-crf', '0',
                    ],
    )

fovea_readius = 200

screen_center = (frames[0].shape[1]//2, frames[0].shape[0]//2)

for i, frame in tqdm(enumerate(frames), total=len(frames), ncols=80):
    t = (i+1) / float(args.fps)
    fovea_rel_pos = getLissajousPoint(t, (0.4,0.5), move_radius, (np.pi/2, 0))
    fovea_abs_pos = screen_center + np.array(fovea_rel_pos).astype(np.int32)
    frame = cv.circle(frame, fovea_abs_pos, fovea_readius, FOVEA_COLOR, thickness)
    if draw_center:
        frame = cv.circle(frame, fovea_abs_pos, 5, FOVEA_COLOR, -1)

    # cv.imshow('frame', frame)
    w.append_data(frame)
w.close()

logI(f'Written to {output_path}')


