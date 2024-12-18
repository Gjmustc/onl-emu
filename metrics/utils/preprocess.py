import os
import ffmpeg
import subprocess

def extract_frames(video_path, output_dir, width=1920, height=1080, fps=30, israwvideo=False):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    try:
        if israwvideo:
            (
                ffmpeg
                .input(video_path, s='{}x{}'.format(width, height), pix_fmt='yuv420p', r=fps)
                .output(os.path.join(output_dir, '%04d.png'), start_number=0)
                .run()
            )
        else:
            (
                ffmpeg
                .input(video_path)
                .output(os.path.join(output_dir, '%04d.png'), r=fps, start_number=0)
                .run()
            )
    except ffmpeg.Error as e:
        print(e.stderr)
        raise e
    
def recognize_frame_numbers(frame_dir):
    cut_folder = os.path.join(frame_dir, 'cut')
    if not os.path.exists(cut_folder):
        os.makedirs(cut_folder)

    frames = sorted([f for f in os.listdir(frame_dir) if f.endswith('.png')])
    for frame in frames:
        frame_path = os.path.join(frame_dir, frame)
        cut_frame_path = os.path.join(cut_folder, f'cut_{frame}')
        
        # Crop the frame number area
        crop_value = '70x30+910+1030'  # Adjust this value based on your video resolution
        subprocess.run(['convert', frame_path, '-crop', crop_value, cut_frame_path])
        
        # Recognize the frame number using gocr
        result = subprocess.run(['gocr', '-C', '0-9', cut_frame_path], capture_output=True, text=True)
        frame_number = ''.join(filter(str.isdigit, result.stdout))
        
        if frame_number.isdigit():
            new_frame_name = f'{int(frame_number):04d}.png'
            new_frame_path = os.path.join(frame_dir, new_frame_name)
            os.rename(frame_path, new_frame_path)
        else:
            print(f'Failed to recognize frame number for {frame_path}')
            os.remove(cut_frame_path)

def retain_common_frames(original_frame_dir, distorted_frame_dir):
    original_frames = set(f for f in os.listdir(original_frame_dir) if f.endswith('.png'))
    distorted_frames = set(f for f in os.listdir(distorted_frame_dir) if f.endswith('.png'))
    
    common_frames = original_frames & distorted_frames
    
    for frame in original_frames - common_frames:
        os.remove(os.path.join(original_frame_dir, frame))
    
    for frame in distorted_frames - common_frames:
        os.remove(os.path.join(distorted_frame_dir, frame))

