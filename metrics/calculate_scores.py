# import debugpy
# debugpy.listen(5678)

import os
import json
import argparse
import subprocess
from utils.preprocess import *
from utils.calc_perception import *
from utils.calc_pixel import *
from utils.calc_transmit import *
cur_path=os.path.dirname(os.path.abspath(__file__))

def calculate_vmaf(src_video, dst_video, output_json, video_width, video_height, video_fps):
    cmd = [ \
        'python3', cur_path+'/eval_video.py', \
        '--src_video', src_video, \
        '--dst_video', dst_video, \
        '--output', output_json, \
        '--frame_align_method', 'ocr', \
        '--video_size', f'{video_width}x{video_height}', \
        '--pixel_format', '420', \
        '--bitdepth', '8', \
        '--fps', str(video_fps)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")
    with open(output_json, 'r') as f:
        video_score = json.load(f)['video']
    return video_score

def get_network_score(dst_network_log, output_json):
    cmd = [ \
        'python3', cur_path+'/eval_network.py', \
        '--dst_network_log', dst_network_log, \
        '--output', output_json
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")
    with open(output_json, 'r') as f:
        network_score = json.load(f)['network']
    return network_score

def calculate_metrics(original_video_path, distorted_video_path, original_frame_dir, distorted_frame_dir, output_json,
                      video_width, video_height, video_fps, israwvideo=True, useImageNet_norm=False):
    
    # Step 1: Calculate video and network scores using external scripts
    vmaf_score = calculate_vmaf(original_video_path, distorted_video_path, output_json, video_width, video_height, video_fps)
    print(f'VMAF score: {vmaf_score}')
    # network_score = get_network_score(distorted_frame_dir, output_json)
    # print(f'Network score: {network_score}')
    
    # Step 2: Extract frames from both videos
    extract_frames(original_video_path, original_frame_dir, israwvideo=israwvideo)
    extract_frames(distorted_video_path, distorted_frame_dir)

    # Step 3: Recognize frame numbers
    recognize_frame_numbers(original_frame_dir)
    recognize_frame_numbers(distorted_frame_dir)

    # Step 4: Calculate transmission metrics
    frame_loss_rate = calculate_frame_loss_rate(original_frame_dir, distorted_frame_dir)
    print(f'Frame loss rate: {frame_loss_rate}%')
    
    # Step 5: Retain common frames
    retain_common_frames(original_frame_dir, distorted_frame_dir)

    # Step 6: Calculate perception metrics
    fvd_score = calculate_fvd(original_frame_dir, distorted_frame_dir, useImageNet_norm=useImageNet_norm)
    print(f'FVD score: {fvd_score}')
    lpips_score = calculate_lpips(original_frame_dir, distorted_frame_dir)
    print(f'LPIPS score: {lpips_score}')

    # Step 7: Calculate average PSNR and SSIM
    pixel_metrics = calculate_average_metrics(original_frame_dir, distorted_frame_dir)
    print(f'Average PSNR: {pixel_metrics["PSNR"]}')
    print(f'Average SSIM: {pixel_metrics["SSIM"]}')

    # Step 8: Write results to JSON file
    results = {
        "Frame loss rate": frame_loss_rate,
        "Average PSNR": pixel_metrics["PSNR"],
        "Average SSIM": pixel_metrics["SSIM"],
        "FVD score": fvd_score,
        "LPIPS score": lpips_score,
        "Vmaf score": vmaf_score,
        # "Network score": network_score
    }

    with open(output_json, 'w') as f:
        json.dump(results, f)
        f.write('\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Calculate video quality scores.')
    parser.add_argument('--original_video_path', type=str, required=True, help='Path to the original video.')
    parser.add_argument('--distorted_video_path', type=str, required=True, help='Path to the distorted video.')
    parser.add_argument('--original_frame_dir', type=str, required=True, help='Directory to save frames from the original video.')
    parser.add_argument('--distorted_frame_dir', type=str, required=True, help='Directory to save frames from the distorted video.')
    parser.add_argument('--output_json', type=str, required=True, help='Path to the output JSON file.')
    parser.add_argument('--video_width', type=int, required=True, help='Width of the video.')
    parser.add_argument('--video_height', type=int, required=True, help='Height of the video.')
    parser.add_argument('--video_fps', type=int, required=True, help='Frames per second of the video.')
    parser.add_argument('--israwvideo', action='store_true', help='Flag to indicate if the original video is raw YUV.')
    parser.add_argument('--useImageNet_norm', action='store_true', help='Flag to indicate if ImageNet normalization should be used.')

    args = parser.parse_args()

    calculate_metrics(args.original_video_path, args.distorted_video_path, args.original_frame_dir, args.distorted_frame_dir, args.output_json, args.video_width, args.video_height, args.video_fps, args.israwvideo, args.useImageNet_norm)