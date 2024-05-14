import os
os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"

import numpy as np
import cv2 as cv
from pathlib import Path
import argparse
import imageio.v2 as iio
from tqdm import tqdm


from DynamicWeighting_Common import *
from _utils import *
from _error_measure import ErrorType
from _animation_lengths import animation_lengths


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


DEFAULT_RECORD_PATH = Path(__file__).parents[4]/'Record'
DEFAULT_SELECTION_FUNC = SelectionMode.LINEAR.name
DEFAULT_NORMALZATION_MODE = NormalizationMode.STD.name

DEFAULT_SCENE_NAME = 'VeachAjar'
# DEFAULT_SCENE_NAME = 'VeachAjarAnimated'
# DEFAULT_SCENE_NAME = 'VeachAjarAnimated2'
# DEFAULT_SCENE_NAME = 'BistroExterior'
# DEFAULT_SCENE_NAME = 'BistroInterior'
# DEFAULT_SCENE_NAME = 'BistroInterior_Wine'
# DEFAULT_SCENE_NAME = 'SunTemple'
# DEFAULT_SCENE_NAME = 'EmeraldSquare_Day'
# DEFAULT_SCENE_NAME = 'EmeraldSquare_Dusk'


parser = argparse.ArgumentParser(description='Make video')
parser.add_argument('-r', '--record_path', type=str, default=DEFAULT_RECORD_PATH, help='record path')
parser.add_argument('--scene_name', type=str, default=DEFAULT_SCENE_NAME, help='scene name')
parser.add_argument('--selection_func', type=str, default=DEFAULT_SELECTION_FUNC, help='selection function')
parser.add_argument('-n', '--norm_mode', type=str, default=DEFAULT_NORMALZATION_MODE, help='normalization mode')
parser.add_argument('--fg', action='store_true', help='filter gradient')
parser.add_argument('--bg', action='store_true', help='best gamma')
parser.add_argument('-s', '--sampling', type=str, default='f1', help='sampling preset')
parser.add_argument('-d', '--debug', action='store_true', help='debug mode')
parser.add_argument('--fovea', action='store_true', help='crop fovea')
parser.add_argument('--start', type=int, default=1, help='start frame')
parser.add_argument('--end', type=int, default=-1, help='end frame')
parser.add_argument('--output_format', type=str, default='mp4', help='output format')
args = parser.parse_args()

params = {
    'scene_name': args.scene_name,
    'iters': 2,
    'feedback': 0,
    'selection_func': SelectionMode[args.selection_func.upper()],
    'midpoint': 0.5,
    'steepness': 1.0,
    'alpha': 0.05,
    'w_alpha': 0.05,
    'g_alpha': 0.2,
    'norm_mode': NormalizationMode[args.norm_mode.upper()],
    'filter_gradient': args.fg,
    'best_gamma': args.bg,
    'sampling': getSamplingPreset(args.sampling),
    'debug': args.debug,
}

record_path = Path(__file__).parents[4]/'Record'
folder_name = getSourceFolderName(**params)
file_pattern = '30fps.SVGFPass.Filtered image.{}.exr'
crop_fovea = args.fovea
start_frame = args.start
end_frame = args.end
output_format = args.output_format

logI(f'folder_name: {folder_name}')


FPS = 30
duration = animation_lengths[params['scene_name']]
end_frame = FPS * duration if end_frame == -1 else end_frame
fovea_radius = 200.0

img_loader = imageSequenceLoader(record_path/folder_name, file_pattern, start_frame, end_frame)
output_filename = f'{params["scene_name"]}_{args.sampling}_{params["selection_func"].name}{"_fovea" if args.fovea else ""}.{output_format}'

if output_format == 'mp4':
    writer = iio.get_writer(output_filename,
                        format='FFMPEG',
                        mode='I',
                        fps=FPS,
                        codec='libx264',
                        output_params=[
                            '-crf', '0',
                        ],
        )

elif output_format == 'gif':
    writer = iio.get_writer(output_filename, format='GIF', mode='I', fps=FPS)

for i, img in tqdm(enumerate(img_loader), total=end_frame, ncols=80):
    t = (start_frame + i) / float(FPS)
    img = drawFoveaLissajous(img, fovea_radius, t, (0.4, 0.5), (640, 360), (np.pi/2, 0), color=(0, 0, 255), thickness=1)

    if crop_fovea:
        dx, dy = getLissajousPoint(t, (0.4, 0.5), (640, 360), (np.pi/2, 0))
        h, w = img.shape[:2]
        img_center = (w // 2, h // 2)
        fovea_center = (int(img_center[0] + dx), int(img_center[1] + dy))
        padding = 10
        crop_w = int(2 * fovea_radius) + padding
        crop_canvas = np.zeros((crop_w, crop_w, 3), dtype=img.dtype)
        crop_center = (crop_w // 2, crop_w // 2)
        img_crop_left = max(0, fovea_center[0] - crop_w // 2)
        img_crop_top = max(0, fovea_center[1] - crop_w // 2)
        img_crop_right = min(w, fovea_center[0] + crop_w // 2)
        img_crop_bottom = min(h, fovea_center[1] + crop_w // 2)
        canvas_crop_left = crop_center[0] - (fovea_center[0] - img_crop_left)
        canvas_crop_top = crop_center[1] - (fovea_center[1] - img_crop_top)
        canvas_crop_right = canvas_crop_left + (img_crop_right - img_crop_left)
        canvas_crop_bottom = canvas_crop_top + (img_crop_bottom - img_crop_top)
        crop_canvas[canvas_crop_top:canvas_crop_bottom, canvas_crop_left:canvas_crop_right] = img[img_crop_top:img_crop_bottom, img_crop_left:img_crop_right]
        img = crop_canvas

    if img.dtype != np.uint8:
        img = toneMapping(img)

    rgb_img = cv.cvtColor(img, cv.COLOR_BGR2RGB)
    writer.append_data(rgb_img)

    cv.imshow('Image', img)
    key = cv.waitKey(1)
    if key == ord('q'):
        break

writer.close()

logI(f'Witten to: {output_filename}')
