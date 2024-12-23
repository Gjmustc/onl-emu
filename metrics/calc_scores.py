import os 
import re
import json
import argparse
import subprocess
from utils.preprocess import *

def calc_vmaf(origin_video, distorted_video, output_xml="vmaf.xml"):
    cmd_result = subprocess.run([
        "vmaf", "--reference", origin_video, "--distorted", distorted_video, "--output", output_xml
    ], capture_output=True, text=True)
    with open(output_xml, "r") as f:
        re_result = re.search(r'metric name="vmaf".*?mean="([\d]+\.[\d]+)"', f.read())
        if not re_result:
            raise ValueError("Can not get vmaf score from terminal output")
        vmaf_score = float(re_result.group(1))
    return vmaf_score

def calculate_psnr_ssim(origin_video, distorted_video):
    # PSNR
    result = subprocess.run([
        'ffmpeg', '-i', origin_video, '-i', distorted_video,
        '-lavfi', 'psnr', '-f', 'null', '-'
    ], capture_output=True, text=True)
    psnr_values = re.findall(r'average:(\d+\.\d+|inf)', result.stderr)
    if psnr_values and psnr_values[0] == 'inf':
        psnr_values[0] = float('inf')
    psnr_score = float(psnr_values[0]) if psnr_values else None
    # SSIM
    result = subprocess.run([
        'ffmpeg', '-i', origin_video, '-i', distorted_video,
        '-lavfi', 'ssim', '-f', 'null', '-'
    ], capture_output=True, text=True)
    ssim_values = re.findall(r'All:(\d+\.\d+)', result.stderr)
    ssim_score = float(ssim_values[0]) if ssim_values else None

    return psnr_score, ssim_score

def calculate_frame_loss_rate(original_frame_dir, distorted_frame_dir):
    original_frames = set(f for f in os.listdir(original_frame_dir) if f.endswith('.png'))
    distorted_frames = set(f for f in os.listdir(distorted_frame_dir) if f.endswith('.png'))
    
    lost_frames = original_frames - distorted_frames
    total_frames = len(original_frames)
    lost_frame_count = len(lost_frames)
    
    if total_frames == 0:
        return 0.0
    
    loss_rate = (lost_frame_count / total_frames) * 100
    return loss_rate

def calculate_metrics(original_video_path, distorted_video_path, origin_video_dir, distorted_video_dir, output_json,
                      video_width, video_height, video_fps, 
                      crop_width, crop_height, crop_x, crop_y,
                      israwvideo=True, supplement=True):
    
    extract_frames(original_video_path, origin_video_dir, width=video_width, height=video_height, fps=video_fps, israwvideo=israwvideo)
    extract_frames(distorted_video_path, distorted_video_dir,fps=video_fps)

    frame_loss_rate = calculate_frame_loss_rate(origin_video_dir, distorted_video_dir)
    print(f'Frame loss rate: {frame_loss_rate}%')
    
    recognize_frame_numbers(origin_video_dir, crop_width, crop_height, crop_x, crop_y)
    recognize_frame_numbers(distorted_video_dir, crop_width, crop_height, crop_x, crop_y)
    
    if supplement:
        supplement_align_frames(origin_video_dir, distorted_video_dir)
    else:
        retain_common_frames(origin_video_dir, distorted_video_dir)
        
    merge_frames(origin_video_dir, distorted_video_dir, video_fps)
    vmaf = calc_vmaf(f'{origin_video_dir}/original.y4m', f'{distorted_video_dir}/distorted.y4m')
    psnr, ssim = calculate_psnr_ssim(f'{origin_video_dir}/original.y4m', f'{distorted_video_dir}/distorted.y4m')
    
    print(f'VMAF score: {vmaf}')
    print(f'PSNR: {psnr}')
    print(f'SSIM: {ssim}')
    
    results = {
        "Frame loss rate": frame_loss_rate,
        "PSNR": psnr,
        "SSIM": ssim,
        "Vmaf score": vmaf,
    }

    with open(output_json, 'w') as f:
        json.dump(results, f)
        f.write('\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Calculate video quality scores.')
    parser.add_argument('--original_video_path', type=str, required=True, help='Path to the original video.')
    parser.add_argument('--distorted_video_path', type=str, required=True, help='Path to the distorted video.')
    parser.add_argument('--origin_video_dir', type=str, required=True, help='Directory to save frames from the original video.')
    parser.add_argument('--distorted_video_dir', type=str, required=True, help='Directory to save frames from the distorted video.')
    parser.add_argument('--output_json', type=str, required=True, help='Path to the output JSON file.')
    parser.add_argument('--video_width', type=int, required=True, help='Width of the video.')
    parser.add_argument('--video_height', type=int, required=True, help='Height of the video.')
    parser.add_argument('--video_fps', type=int, required=True, help='Frames per second of the video.')
    parser.add_argument('--crop_width', type=int, default=150, help='Width of the frame number area.')
    parser.add_argument('--crop_height', type=int, default=60, help='Height of the frame number area.')
    parser.add_argument('--crop_x', type=int, default=900, help='X coordinate of the frame number area.')
    parser.add_argument('--crop_y', type=int, default=1020, help='Y coordinate of the frame number area.')
    parser.add_argument('--israwvideo', action='store_true', help='Flag to indicate if the original video is raw YUV.')
    parser.add_argument('--supplement', action='store_true', help='Flag to indicate if the distorted video needs to be supplemented.')

    args = parser.parse_args()

    calculate_metrics(
        args.original_video_path, args.distorted_video_path, args.origin_video_dir, 
        args.distorted_video_dir, args.output_json, args.video_width, args.video_height, 
        args.video_fps, args.crop_width, args.crop_height, args.crop_x, args.crop_y,
        args.israwvideo, args.supplement
    )