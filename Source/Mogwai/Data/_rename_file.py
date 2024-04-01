import os
from pathlib import Path
import re

def rename_files(directory:Path, pattern:str):

    for i in range(2, 10000):
        old_path = directory/pattern.format(i)
        new_path = directory/pattern.format(i-1)
        if not old_path.exists():
            break
        if new_path.exists():
            print(f"File {new_path} already exists")
            break
        print(f"Renamed {old_path} to {new_path}")
        old_path.rename(new_path)


# Replace 'directory_path' with the path to the directory containing the files

RECORD_PATH = Path(__file__).parents[4]/'Record'


dirs = os.listdir(RECORD_PATH)
for dir in dirs:
    directory_path = RECORD_PATH/dir
    print(directory_path)
    if not directory_path.is_dir():
        continue
    pattern = "30fps.SVGFPass.Filtered image.{}.exr"
    rename_files(directory_path, pattern)
