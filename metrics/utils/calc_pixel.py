import os
import subprocess
import re
import argparse

def calculate_metrics(original_frame, distorted_frame):
    metrics = {}

    # PSNR
    result = subprocess.run([
        'ffmpeg', '-i', original_frame, '-i', distorted_frame,
        '-lavfi', 'psnr', '-f', 'null', '-'
    ], capture_output=True, text=True)
    psnr_values = re.findall(r'average:(\d+\.\d+|inf)', result.stderr)
    if psnr_values and psnr_values[0] == 'inf':
        psnr_values[0] = float('inf')
    metrics['PSNR'] = float(psnr_values[0]) if psnr_values else None

    # SSIM
    result = subprocess.run([
        'ffmpeg', '-i', original_frame, '-i', distorted_frame,
        '-lavfi', 'ssim', '-f', 'null', '-'
    ], capture_output=True, text=True)
    ssim_values = re.findall(r'All:(\d+\.\d+)', result.stderr)
    metrics['SSIM'] = float(ssim_values[0]) if ssim_values else None

    return metrics

def calculate_average_metrics(original_frame_dir, distorted_frame_dir):
    original_frames = sorted([f for f in os.listdir(original_frame_dir) if f.endswith('.png')])
    distorted_frames = sorted([f for f in os.listdir(distorted_frame_dir) if f.endswith('.png')])

    psnr_total = 0
    ssim_total = 0
    count = 0

    for frame in original_frames:
        if frame in distorted_frames:
            original_frame_path = os.path.join(original_frame_dir, frame)
            distorted_frame_path = os.path.join(distorted_frame_dir, frame)
            metrics = calculate_metrics(original_frame_path, distorted_frame_path)
            print(f'Frame {frame}: PSNR={metrics["PSNR"]}, SSIM={metrics["SSIM"]}')
            if metrics['PSNR'] is not None and metrics['SSIM'] is not None:
                psnr_total += metrics['PSNR']
                ssim_total += metrics['SSIM']
                count += 1
    if count == 0:
        return {'PSNR': None, 'SSIM': None}
    average_psnr = psnr_total / count
    average_ssim = ssim_total / count
    return {'PSNR': average_psnr, 'SSIM': average_ssim}

if __name__ == '__main__':
    original_frame_dir = '/home/onl/onl-emu/metrics/tests/data/test_frames/original'
    distorted_frame_dir = '/home/onl/onl-emu/metrics/tests/data/test_frames/distorted'

    pixel_metrics = calculate_average_metrics(original_frame_dir, distorted_frame_dir)
    print(f'Average PSNR: {pixel_metrics["PSNR"]}')
    print(f'Average SSIM: {pixel_metrics["SSIM"]}')