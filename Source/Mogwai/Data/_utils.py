from pathlib import Path
import cv2 as cv
import numpy as np
from colorama import Fore, Back, Style
import sys
import json

from _log_utils import *

def ensurePath(path: str) -> None:
    """Ensures that the path exists.

    Args:
        path (str): The path to check/create.
    """
    Path(path).mkdir(parents=True, exist_ok=True)


def loadImage(path, filename_pattern:str, frame_id) -> np.ndarray:
    path = Path(path)

    img_path = path/filename_pattern.format(frame_id)
    if not img_path.exists():
        raise FileNotFoundError(img_path)
    img = cv.imread(str(img_path), cv.IMREAD_ANYCOLOR | cv.IMREAD_ANYDEPTH | cv.IMREAD_UNCHANGED)
    return img

def loadImageSequence(path, filename_pattern:str, max_frame_id=None) -> list:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    dataset = []
    frame_id = 1
    while (max_frame_id is None) or (frame_id <= max_frame_id):
        try:
            img = loadImage(path, filename_pattern, frame_id)
        except FileNotFoundError as e:
            break
        dataset.append(img)
        frame_id += 1
    return dataset

def imageSequenceLoader(path, filename_pattern:str, max_frame_id=None, n_retry=5):
    path = Path(path)
    frame_id = 1
    while (max_frame_id is None) or (frame_id <= max_frame_id):
        for i in range(n_retry):
            try:
                img = loadImage(path, filename_pattern, frame_id)
                if img is None:
                    logW(f"Image {frame_id} is empty. Retrying... ({i+1}/{n_retry})")
                    continue
                break
            except FileNotFoundError as e:
                raise e
            except Exception as e:
                if i < n_retry - 1:
                    logE(f"Error loading image {frame_id}: {e}. Retrying... ({i+1}/{n_retry})")
                else:
                    raise e
        yield img
        frame_id += 1

def getImageSequencePaths(path, filename_pattern:str, max_frame_id=None) -> list[Path]:
    path = Path(path)
    frame_id = 1
    result_paths = []
    while (max_frame_id is None) or (frame_id <= max_frame_id):
        img_path = path/filename_pattern.format(frame_id)
        if not img_path.exists():
            break
        result_paths.append(img_path)
        frame_id += 1
    return result_paths

def countImages(path, filename_pattern:str) -> int:
    path = Path(path)
    frame_id = 1
    while True:
        img_path = path/filename_pattern.format(frame_id)
        if not img_path.exists():
            break
        frame_id += 1
    return frame_id - 1


def fileModifiedLaterThan(file1: Path, file2: Path):
    '''
    Returns True if file1 was modified later than file2, False otherwise.
    '''
    return file1.stat().st_mtime > file2.stat().st_mtime

RE_STRING = r"\w+"
RE_FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"   # (?:...) non-capturing group
RE_WHITESPACES = r"\s*"



def drawFoveaLissajous(img, fovea_radius, t, freq, radius, phase, color=(0, 0, 255), thickness=1, **kargs) -> np.ndarray:
    """Draws a Lissajous curve on the image.

    Args:
        img (np.ndarray): The image to draw on.
        t (float): The time parameter.
        freq (tuple): The frequency of the Lissajous curve.
        radius (tuple): The radius of the Lissajous curve.
        phase (tuple): The phase of the Lissajous curve.
        color (tuple, optional): The color of the curve. Defaults to (0, 0, 255).
        thickness (int, optional): The thickness of the curve. Defaults to 1.
        **kargs: Additional arguments for cv.circle.

    Returns:
        np.ndarray: The image with the Lissajous curve drawn.
    """
    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    x = center[0] + radius[0] * np.sin(2 * np.pi * freq[0] * t + phase[0])
    y = center[1] + radius[1] * np.sin(2 * np.pi * freq[1] * t + phase[1])
    img = cv.circle(img, (int(x), int(y)), int(fovea_radius), color, thickness, **kargs)

    return img
