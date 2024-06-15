import cv2 as cv
import numpy as np
from pathlib import Path
from time import time

from _utils import *
from TwoHistory_Common import *


def calculate_masked_mean_1(img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Calculates the mean of the masked pixels in the image.

    Args:
        img (np.ndarray): The image.
        mask (np.ndarray): The mask.

    Returns:
        np.ndarray: The mean of the masked pixels in the image.
    """
    masked_pixels = img[mask > 0]
    return np.mean(masked_pixels)

def calculate_mask_mean_2(img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Calculates the mean of the masked pixels in the image.

    Args:
        img (np.ndarray): The image.
        mask (np.ndarray): The mask.

    Returns:
        np.ndarray: The mean of the masked pixels in the image.
    """
    mask_pix_count = np.count_nonzero(mask)
    return np.sum(img*mask)/mask_pix_count

if __name__ == "__main__":

    h = 720
    w = 1280
    img = np.random.randint(0, 255, (h, w), np.uint8)
    mask = np.zeros((h, w), np.uint8)

    t = 1
    mask = drawFoveaLissajous(mask, 200, t, (0.4, 0.5), (w//2, h//2), (np.pi/2, 0), 1, cv.FILLED)
    # mask = np.array([[0,1,0,1],[0,1,0,1],[0,1,0,1]], dtype=np.uint8)
    # print(mask)

    # cv.imshow("Mask", mask*255)
    # cv.waitKey(0)
    # cv.destroyAllWindows()

    masked_pixels = img[mask == 1]
    print(masked_pixels)

    st1 = time()
    mean1 = calculate_masked_mean_1(img, mask)
    dur1 = time() - st1
    print(f'{dur1} s')

    st2 = time()
    mean2 = calculate_mask_mean_2(img, mask)
    dur2 = time() - st2
    print(f'{dur2} s')

    assert mean1 == mean2



