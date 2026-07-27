# imAdjust

A small package to deal with .nd2 files from the slide scanner.

## Installation

```bash
git clone 
pip install -e .
```

## Usage

```bash
imadjust -i "D:\Choc27_F\one_in" -o "D:\Choc27_F\one_out"
```

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `-i,--input-dir` | Input directory | `None` |
| `-o, --output-dir` | Output directory | `None` |
| `-down, --downFct` | Downsampling factor | `2` |


## Requirements
- Python ≥ 3.8
- nd2, opencv-python, scipy, numpy, pandas, matplotlib, tqdm