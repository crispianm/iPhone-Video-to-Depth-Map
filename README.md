# iPhone/iPad Video Depth Extractor

## Overview
This small project contains a macOS/AVFoundation-based utility to extract iPhone depth (auxv) tracks from an Apple `.MOV` and save them as a compressed NumPy `.npz` file containing a float16 tensor of disparity values.

## Files
- `extract.py` - main extraction script (uses PyObjC + AVFoundation to request `kCVPixelFormatType_DisparityFloat16` and save a `(frames, height, width)` float16 tensor).
- `requirements.txt` — pip-installable packages (minimal list).
- `README.md` — this file.
- `LICENSE` — Apache License 2.0.

## Capturing a depth video on iPhone
`extract.py` only works on a video that actually contains a depth/disparity (`auxv`) track. **A normal video recording does _not_ include depth** — you have to record in **Cinematic mode** (or use a third‑party depth‑capture app).

### Cinematic mode (iPhone 13 and later, iOS 15+)
1. Open the **Camera** app.
2. Swipe the mode selector across to **Cinematic**.
3. (Optional) Tap a subject to lock focus; tap the *f*‑number at the top of the screen to change the depth‑of‑field strength.
4. Tap the shutter to start recording, and tap it again to stop.

Cinematic mode stores a per‑frame disparity map alongside the video as an `auxv` track — exactly what this tool extracts. Capture resolution is 1080p·30 fps on iPhone 13, and up to 4K·30 fps (HDR) on iPhone 14 Pro and later.

> **Calibration note:** on current iPhones the Cinematic disparity is estimated from the camera system and is *relative* — consistent ordering and gradients, but no fixed real‑world scale. Don't treat it as metric depth without independent calibration.

Alternatively, third‑party depth/LiDAR recording apps (e.g. Record3D) can produce a `.MOV` with a compatible depth track.

## Getting the original video onto your Mac
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

## Setup
Install the dependencies with [uv](https://docs.astral.sh/uv/) (fast and reproducible):

```bash
uv venv                               # create a local .venv
uv pip install -r requirements.txt    # install dependencies into it
uv run python extract.py --help       # verify the install
```

`uv run` executes inside the project's `.venv` automatically — no manual activation needed. If you prefer, run `source .venv/bin/activate` once and then drop the `uv run` prefix.

Note: this script requires macOS with AVFoundation (it uses PyObjC bindings). It will not work on Linux/Windows.

### Alternative: plain venv + pip
If you don't have uv installed:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python extract.py --help              # verify the install
```

## Usage

```bash
python extract.py INPUT.MOV [-o OUTPUT.npz] [--max-frames N] [-v]
```

(If you set up with uv and didn't activate the venv, prefix commands with `uv run`, e.g. `uv run python extract.py ...`.)

| Argument | Description |
| --- | --- |
| `INPUT.MOV` | Depth video to read (required). |
| `-o`, `--output` | Output `.npz` path. Defaults to `INPUT_depth.npz` next to the input file. |
| `--max-frames N` | Stop after `N` frames (handy for a quick test). |
| `-v`, `--verbose` | Print progress and the detected device model / codec. |

Example:

```bash
python extract.py IMG_5333.MOV -v
# → writes IMG_5333_depth.npz next to the input
```

### Output format
The `.npz` archive contains:

- `depth` — `(frames, height, width)` **float16** disparity tensor.
- `times` — per‑frame presentation timestamps in seconds (`float32`).
- `depth_codec`, `device_model` — provenance metadata strings.

Load it back with NumPy:

```python
import numpy as np

data = np.load("IMG_5333_depth.npz")
depth = data["depth"]          # (frames, H, W) float16 disparity
times = data["times"]          # (frames,) seconds
print(depth.shape, str(data["device_model"]))
```

## Sharing and licensing
This repository is licensed under the Apache License 2.0. See the `LICENSE` file for the full text.
