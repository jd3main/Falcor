from pathlib import Path
import cv2 as cv
import numpy as np
from colorama import Fore, Back, Style
import sys
import json

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
            raise e
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
                    logWarn(f"Image {frame_id} is empty. Retrying... ({i+1}/{n_retry})")
                    continue
                break
            except FileNotFoundError as e:
                raise e
            except Exception as e:
                if i < n_retry - 1:
                    logErr(f"Error loading image {frame_id}: {e}. Retrying... ({i+1}/{n_retry})")
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

def logErr(*args, **kwargs):
    print(Fore.RED, file=sys.stderr, end='')
    print(*args, file=sys.stderr, **kwargs, end='')
    print(Style.RESET_ALL, file=sys.stderr, end=kwargs.get('end', '\n'))

def logWarn(*args, **kwargs):
    print(Fore.YELLOW, file=sys.stderr, end='')
    print(*args, file=sys.stderr, **kwargs, end='')
    print(Style.RESET_ALL, file=sys.stderr, end=kwargs.get('end', '\n'))


def fileModifiedLaterThan(file1: Path, file2: Path):
    '''
    Returns True if file1 was modified later than file2, False otherwise.
    '''
    return file1.stat().st_mtime > file2.stat().st_mtime

RE_STRING = r"\w+"
RE_FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"   # (?:...) non-capturing group
RE_WHITESPACES = r"\s*"



