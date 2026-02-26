"""Extract float16 disparity frames from an iPhone depth (`auxv`) track.

This script uses PyObjC / AVFoundation on macOS to request the
`kCVPixelFormatType_DisparityFloat16` pixel format and saves the
resulting `(frames, height, width)` float16 tensor to a compressed
NumPy `.npz` file. Designed for researchers who need the calibrated
disparity buffers rather than visualized video frames.

Usage (CLI):
  python extract.py input.mov -o output_depths.npz

Notes:
 - macOS only (requires AVFoundation).
 - Recommended to run inside the provided `conda` env or install the
   packages from `requirements.txt`.
"""

from pathlib import Path
import argparse
import os
import sys

import numpy as np
import Foundation
import AVFoundation
import CoreMedia
from Quartz import CoreVideo


def extract_depth_to_npz(mov_path: str, npz_path: str, max_frames: int = None, verbose: bool = False):
    """Extract depth (disparity) frames from `mov_path` and save to `npz_path`.

    Args:
        mov_path: Path to input .MOV file containing an `auxv` depth track.
        npz_path: Path to output .npz file.
        max_frames: Optional maximum number of frames to extract.
        verbose: Enable progress prints.
    """
    mov_path = str(mov_path)
    npz_path = str(npz_path)
    if verbose:
        print(f"Processing: {mov_path}...")

    url = Foundation.NSURL.fileURLWithPath_(mov_path)
    asset = AVFoundation.AVURLAsset.URLAssetWithURL_options_(url, None)

    # Find depth/auxv track
    depth_track = None
    for track in asset.tracks():
        try:
            media_type = track.mediaType()
        except Exception:
            media_type = None

        if media_type == 'auxv':
            depth_track = track
            if verbose:
                print(f"Found depth track: {track.trackID()} (Type: auxv)")
            break

        for desc in track.formatDescriptions():
            subtype = CoreMedia.CMFormatDescriptionGetMediaSubType(desc)
            # Known subtypes used historically; keep as fallback
            if subtype in [1684632424, 1684890161]:
                depth_track = track
                if verbose:
                    print(f"Found depth track via subtype: {track.trackID()}")
                break
        if depth_track:
            break

    if not depth_track:
        print("Error: No depth track found. Make sure 'All Photos Data' was enabled when sending the video.")
        return False

    # Request native 16-bit float disparity
    kCVPixelFormatType_DisparityFloat16 = 1751411059
    output_settings = {str(CoreVideo.kCVPixelBufferPixelFormatTypeKey): kCVPixelFormatType_DisparityFloat16}

    reader, _ = AVFoundation.AVAssetReader.assetReaderWithAsset_error_(asset, None)
    output = AVFoundation.AVAssetReaderTrackOutput.assetReaderTrackOutputWithTrack_outputSettings_(depth_track, output_settings)
    output.setAlwaysCopiesSampleData_(False)

    if not reader.canAddOutput_(output):
        print("Error: Cannot add AVAssetReader output for this track.")
        return False

    reader.addOutput_(output)
    reader.startReading()

    depth_frames = []
    frame_times = []
    last_width = None
    last_height = None

    if verbose:
        print("Extracting frames...")

    while reader.status() == AVFoundation.AVAssetReaderStatusReading:
        sample_buffer = output.copyNextSampleBuffer()
        if not sample_buffer:
            break

        pixel_buffer = CoreMedia.CMSampleBufferGetImageBuffer(sample_buffer)
        if not pixel_buffer:
            continue

        CoreVideo.CVPixelBufferLockBaseAddress(pixel_buffer, CoreVideo.kCVPixelBufferLock_ReadOnly)

        width = CoreVideo.CVPixelBufferGetWidth(pixel_buffer)
        height = CoreVideo.CVPixelBufferGetHeight(pixel_buffer)
        bytes_per_row = CoreVideo.CVPixelBufferGetBytesPerRow(pixel_buffer)
        base_address = CoreVideo.CVPixelBufferGetBaseAddress(pixel_buffer)

        buffer_size = bytes_per_row * height

        # base_address is typically an objc.varlist on PyObjC; use its as_buffer method
        raw_buf = base_address.as_buffer(buffer_size)
        raw_np = np.frombuffer(raw_buf, dtype=np.float16)

        stride_width = bytes_per_row // 2
        frame_reshaped = raw_np.reshape((height, stride_width))
        valid_frame = frame_reshaped[:, :width]
        depth_frames.append(valid_frame.copy())

        # capture presentation timestamp if available
        try:
            ts = CoreMedia.CMSampleBufferGetPresentationTimeStamp(sample_buffer)
            t_sec = CoreMedia.CMTimeGetSeconds(ts)
            frame_times.append(float(t_sec))
        except Exception:
            frame_times.append(float(len(depth_frames) - 1))

        last_width = width
        last_height = height

        CoreVideo.CVPixelBufferUnlockBaseAddress(pixel_buffer, CoreVideo.kCVPixelBufferLock_ReadOnly)

        if max_frames is not None and len(depth_frames) >= max_frames:
            break

    if reader.status() == AVFoundation.AVAssetReaderStatusCompleted or len(depth_frames) > 0:
        depth_tensor = np.stack(depth_frames, axis=0)
        out_dir = Path(npz_path).parent
        out_dir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(npz_path, depth=depth_tensor, times=np.array(frame_times, dtype=np.float32))
        if verbose:
            print(f"Success! Saved {depth_tensor.shape} tensor to {npz_path}")
        return True
    else:
        print(f"Failed. Reader status: {reader.status()}")
        if reader.error():
            print(f"Error details: {reader.error()}")
        return False


def _cli():
    p = argparse.ArgumentParser(description="Extract float16 disparity tensor from iPhone depth MOV.")
    p.add_argument("input", help="Input .MOV file")
    p.add_argument("-o", "--output", help="Output .npz file (defaults to INPUT_depth.npz)")
    p.add_argument("--max-frames", type=int, default=None, help="Maximum number of frames to extract")
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = p.parse_args()

    inp = Path(args.input)
    if not inp.exists():
        print(f"Error: input file does not exist: {inp}")
        sys.exit(2)

    out = Path(args.output) if args.output else inp.with_name(inp.stem + "_depth.npz")

    success = extract_depth_to_npz(str(inp), str(out), max_frames=args.max_frames, verbose=args.verbose)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    _cli()