import numpy as np
import Foundation
import AVFoundation
import CoreMedia
import Quartz
from Quartz import CoreVideo 
import ctypes

def extract_depth_to_npz(mov_path, npz_path):
    print(f"Processing: {mov_path}...")
    url = Foundation.NSURL.fileURLWithPath_(mov_path)
    asset = AVFoundation.AVURLAsset.URLAssetWithURL_options_(url, None)
    
    depth_track = None
    
    # 1. Find the Depth Track
    for track in asset.tracks():
        media_type = track.mediaType()
        if media_type == 'auxv':
            depth_track = track
            print(f"Found depth track: {track.trackID()} (Type: auxv)")
            break
        
        for desc in track.formatDescriptions():
            subtype = CoreMedia.CMFormatDescriptionGetMediaSubType(desc)
            if subtype in [1684632424, 1684890161]: 
                depth_track = track
                print(f"Found depth track via subtype: {track.trackID()}")
                break
        if depth_track: break

    if not depth_track:
        print("Error: No depth track found. Make sure 'All Photos Data' was enabled on AirDrop.")
        return

    # 2. Force Decoding to Native 16-bit Float Disparity ('hdis')
    kCVPixelFormatType_DisparityFloat16 = 1751411059 
    
    output_settings = {
        str(CoreVideo.kCVPixelBufferPixelFormatTypeKey): kCVPixelFormatType_DisparityFloat16
    }
    
    reader, _ = AVFoundation.AVAssetReader.assetReaderWithAsset_error_(asset, None)
    output = AVFoundation.AVAssetReaderTrackOutput.assetReaderTrackOutputWithTrack_outputSettings_(depth_track, output_settings)
    
    # Inform AVAssetReader we don't need it to copy data unnecessarily 
    output.setAlwaysCopiesSampleData_(False)
    
    if not reader.canAddOutput_(output):
        print("Error: Cannot add output to reader.")
        return
        
    reader.addOutput_(output)
    reader.startReading()
    
    depth_frames = []
    print("Extracting frames...")
    
    # 3. Iterate and Extract
    while reader.status() == AVFoundation.AVAssetReaderStatusReading:
        sample_buffer = output.copyNextSampleBuffer()
        if not sample_buffer:
            break
            
        pixel_buffer = CoreMedia.CMSampleBufferGetImageBuffer(sample_buffer)
        if not pixel_buffer:
            continue
            
        # Lock memory
        CoreVideo.CVPixelBufferLockBaseAddress(pixel_buffer, CoreVideo.kCVPixelBufferLock_ReadOnly)
        
        width = CoreVideo.CVPixelBufferGetWidth(pixel_buffer)
        height = CoreVideo.CVPixelBufferGetHeight(pixel_buffer)
        bytes_per_row = CoreVideo.CVPixelBufferGetBytesPerRow(pixel_buffer)
        base_address = CoreVideo.CVPixelBufferGetBaseAddress(pixel_buffer)
        
        buffer_size = bytes_per_row * height
        
        # base_address is an objc.varlist; use as_buffer to get raw bytes
        raw_buf = base_address.as_buffer(buffer_size)
        raw_np = np.frombuffer(raw_buf, dtype=np.float16)
        
        stride_width = bytes_per_row // 2
        frame_reshaped = raw_np.reshape((height, stride_width))
        
        valid_frame = frame_reshaped[:, :width]
        depth_frames.append(valid_frame.copy())
        
        CoreVideo.CVPixelBufferUnlockBaseAddress(pixel_buffer, CoreVideo.kCVPixelBufferLock_ReadOnly)
        
    if reader.status() == AVFoundation.AVAssetReaderStatusCompleted:
        depth_tensor = np.stack(depth_frames, axis=0)
        np.savez_compressed(npz_path, depth=depth_tensor)
        print(f"Success! Saved {depth_tensor.shape} tensor to {npz_path}")
    else:
        print(f"Failed. Reader status: {reader.status()}")
        if reader.error():
            print(f"Error details: {reader.error()}")

extract_depth_to_npz('IMG_5333.MOV', './depths/IMG_5333_depth.npz')