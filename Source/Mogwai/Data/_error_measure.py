import os
os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"

import cv2 as cv
import numpy as np
from pathlib import Path
import json
import matplotlib.pyplot as plt


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
        print(e)
    return data

# scene_name = 'VeachAjarAnimated'
scene_name = 'BistroExterior'
# scene_name = 'EmeraldSquare_Day'
# scene_name = 'SunTemple'

def loadImage(path, filename_pattern:str, frame_id):
    path = Path(path)
    # metadata = loadMetadata(path)
    # print(metadata)

    img_path = path/filename_pattern.format(frame_id)
    if not img_path.exists():
        return None
    img = cv.imread(str(img_path), cv.IMREAD_ANYCOLOR | cv.IMREAD_ANYDEPTH | cv.IMREAD_UNCHANGED)
    return img

def loadImageSequence(path, filename_pattern:str, max_frame_id=None):
    path = Path(path)
    dataset = []
    frame_id = 1
    while (max_frame_id is None) or (frame_id <= max_frame_id):
        img = loadImage(path, filename_pattern, frame_id)
        if img is None:
            break
        dataset.append(img)
        frame_id += 1
    return dataset


MAX_FRAMES = 300
iters='2,1,2'

print(f'iters = {iters}')

# load reference data
print(f'loading reference data from {scene_name}_iters({iters})')
reference_path = Path(__file__).parent/'Record'/f'{scene_name}_iters({iters})'
reference_images = loadImageSequence(reference_path, '60fps.SVGFPass.Filtered image.{}.exr', MAX_FRAMES)
if len(reference_images) == 0:
    print(f'cannot load reference images')
    exit()
else:
    print(f'loaded reference images')

# setup target folders
base_path = Path(__file__).parent/'Record'
target_folders = []
for midpoint in [0.0001, 0.001, 0.01]:
    for steepness in [5.0, 50.0, 500.0]:
        folder_name = f'{scene_name}_iters({iters})_Logistic({midpoint},{steepness})_GAlpha(0.2)_Norm(STANDARD_DEVIATION)_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)'
        if (base_path/folder_name).exists():
            target_folders.append(base_path/folder_name)
target_folders.append(base_path/f'{scene_name}_iters({iters})_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)')
target_folders.append(base_path/f'{scene_name}_iters({iters})_Weighted_Foveated(SPLIT_HORIZONTALLY,SHM,8.0)')
print(f'found {len(target_folders)} target folders')

# load source data and calculate error

nrows = 2
ncols = 1

ax1 = plt.subplot(nrows, ncols, 1)
# ax1.legend(loc='upper left')
ax1.set_ylabel("Mean Error")
ax1.set_xlabel("Frame")

ax2 = plt.subplot(nrows, ncols, 2, sharex=ax1)
ax2.set_ylabel('Max Error')
# ax2.legend(loc='upper left')

for folder in target_folders:
    if not folder.exists():
        print(f'cannot find {folder}')
        continue
    # print(f'loading from {folder}')
    source_images = loadImageSequence(folder, '60fps.SVGFPass.Filtered image.{}.exr', MAX_FRAMES)
    # print(f'loaded {len(source_images)} source images')
    assert len(source_images) <= len(reference_images)

    # calculate mean square error
    mean_err = []
    max_err = []
    for i in range(len(reference_images)):
        err = np.square(reference_images[i] - source_images[i])
        mean_err.append(np.mean(err))
        max_err.append(np.max(err))
    short_name = folder.name.split('_')[2+scene_name.count('_')]
    ax1.plot(mean_err, label=f'{short_name}.mean')
    ax2.plot(max_err, label=f'{short_name}.max')

    print(f'mean({np.mean(mean_err):.6f}), max({np.mean(max_err):.4f}) {short_name}')


ax1.legend(loc='upper left')
ax2.legend(loc='upper left')
plt.show()


# preview
# for source_data in source_data_set:
#     print(f'source data: {len(source_data)} images')
#     dt = 1000 // 60
#     for img in source_data:
#         cv.imshow('img', img)
#         cv.waitKey(dt)
#     break
# cv.waitKey(0)
# cv.destroyAllWindows()
