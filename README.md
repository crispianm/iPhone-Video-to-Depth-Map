# iPhone/iPad Video Depth Extractor

## Overview
This small project contains a macOS/AVFoundation-based utility to extract iPhone depth (auxv) tracks from an Apple `.MOV` and save them as a compressed NumPy `.npz` file containing a float16 tensor of disparity values.

## Files
- `extract.py` - main extraction script (uses PyObjC + AVFoundation to request `kCVPixelFormatType_DisparityFloat16` and save a `(frames, height, width)` float16 tensor).
- `requirements.txt` — pip-installable packages (minimal list).
- `conda.yml` — conda environment spec (recommended for reproducibility).
- `README.md` — this file.
- `LICENSE` — Apache License 2.0.

### Obtaining the original video from an iOS/MacOS Device
To preserve the original `.MOV` (including the `auxv` depth track and original metadata), follow these simple options from iPhoneLife:

- From an iPhone (recommended when transferring between Apple devices):
	1. Open the Photos app and select the photo(s) or video(s).
	2. Tap the Share icon.
	3. Under the (Number) Photos Selected area, tap "Options".
	4. Toggle "All Photos Data" on to include original metadata and auxiliary tracks.
	5. Use AirDrop to send the original `.MOV` to a nearby Mac (this preserves the original file), or choose "iCloud Link" to share a link that preserves original dates when downloaded by recipients.

- From a Mac (if the video is already in the Photos app):
	1. Open the Photos app, select the item(s).
	2. Click File → Export → Export Unmodified Original(s).
	3. Choose a destination and export — this yields the original file with metadata intact.

Using one of these methods ensures you receive the original `.MOV` with its auxiliary depth track intact — which is required for `extract.py` to read native float16 disparity buffers.

## Reproducible setup (recommended)
### Using conda (preferred on macOS):

```bash
conda env create -f conda.yml
conda activate depthextract
python extract.py
```

Notes:
- This script requires macOS with AVFoundation (it uses PyObjC bindings). It will not work on Linux/Windows.
- The `depthextract` env name matches the original environment used when developing this script.

### Alternative pip-based setup
If you prefer a venv + pip:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python extract.py
```

## Usage
Place your `.MOV` (example `IMG_5333.MOV`) in the project folder and run `python extract.py`. The script prints progress and writes an `.npz` file (by default `./depths/IMG_5333_depth.npz`).

## Quick visual hack (lossy)
If you only need a quick visual depth map (not the calibrated float16 disparity tensor), you can remux and decode the `auxv` track using `MP4Box` and `ffmpeg`. This is lossy and intended for inspection only — it does not preserve the original disparity semantics.

Install the tools with Homebrew:

```bash
brew install ffmpeg gpac
```

Then run:

```bash
MP4Box -add self#2:hdlr=vide IMG_5333.MOV -out remux.mp4
ffmpeg -vcodec hevc -i remux.mp4 -map 0:1 map.mp4
```

`map.mp4` contains a viewable video track derived from the depth data; it is useful for quick checks but not for analysis that requires true disparity values.

### What this does (why it matters)
- AVFoundation decodes the depth/auxv track and can return native float16 disparity buffers (`kCVPixelFormatType_DisparityFloat16`).
- Extracting via AVFoundation preserves the float16 disparity semantics; remuxing and decoding with `ffmpeg` yields generic video pixels and loses the underlying depth semantics.

## Sharing and licensing
This repository is licensed under the Apache License 2.0. See the `LICENSE` file for the full text.
