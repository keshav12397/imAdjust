# imAdjust

A small package to deal with .nd2 files from the slide scanner.

## Installation

```bash
git clone https://github.com/keshav12397/imAdjust.git
cd ./imAdjust
pip install -e .
```

## Usage

```bash
imadjust -i "D:\Choc27_F\one_in" -o "D:\Choc27_F\one_out" -down 2
```

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `-i,--input-dir` | Input directory | `None` |
| `-o, --output-dir` | Output directory | `None` |
| `-down, --downFct` | Downsampling factor | `2` |

## Description

The slide scanner outputs all images into a folder with a random name (i.e. `/20260724_190203_378`). You want to put this into a parent folder with the name of the bird (i.e. `/Choc27_F/20260724_190203_378`) and pass the bird directory as input. This will handle the case where you split up imaging a bird over multiple slide scanner runs.

This will then traverse through all files, first pull out all the prescans, outline the ROIs that were automatically detected and their numbers, and stack them to save one image.

Then it will go through all the individual ND2 files, apply a local contrast adjustment per channel (*cv2.CLAHE*), stack the colors, downsample and save as .png.  

## Requirements

- Python ≥ 3.8
- nd2, opencv-python, scipy, numpy, pandas, matplotlib, tqdm