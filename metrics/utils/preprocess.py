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
    return
    
def recognize_frame_numbers(frame_dir, crop_width=150, crop_height=60, crop_x=900, crop_y=1020):
    recog_folder = os.path.join(frame_dir, 'recog')
    if not os.path.exists(recog_folder):
        os.makedirs(recog_folder)

    frames = sorted([f for f in os.listdir(frame_dir) if f.endswith('.png')])
    for frame in frames:
        frame_path = os.path.join(frame_dir, frame)
        recog_frame_path = os.path.join(recog_folder, f'recog_{frame}')
        
        # Crop the frame number area
        crop_value = f'{crop_width}x{crop_height}+{crop_x}+{crop_y}'
        crop_result = subprocess.run(['convert', frame_path, '-crop', crop_value, recog_frame_path])
        
        # Recognize the frame number using gocr
        result = subprocess.run(
            ['gocr', '-C', '0-9', recog_frame_path],
            capture_output=True,
            text=True
        )
        gocr_output = result.stdout

        # Use tr and sed to process the output
        tr_result = subprocess.run(
            ['tr', '-d', '[:space:]'],
            input=gocr_output,
            capture_output=True,
            text=True
        )
        sed_result = subprocess.run(
            ['sed', 's/[^0-9]//g'],
            input=tr_result.stdout,
            capture_output=True,
            text=True
        )

        # Get the final frame number
        frame_number = sed_result.stdout.strip()
        
        if frame_number.isdigit():
            new_frame_name = f'{int(frame_number):04d}.png'
            new_frame_path = os.path.join(recog_folder, new_frame_name)
            os.rename(frame_path, new_frame_path)
        else:
            print(f'Failed to recognize frame number for {frame_path}')
        os.remove(recog_frame_path)
    
    # Clear original frames in the directory
    for frame in os.listdir(frame_dir):
        if frame.endswith('.png'):
            os.remove(os.path.join(frame_dir, frame))
    
    # Move recognized frames back to the original directory
    for frame in os.listdir(recog_folder):
        os.rename(os.path.join(recog_folder, frame), os.path.join(frame_dir, frame))
    
    # Remove the recog folder
    os.rmdir(recog_folder)
    return 


def retain_common_frames(original_frame_dir, distorted_frame_dir):
    original_frames = set(f for f in os.listdir(original_frame_dir) if f.endswith('.png'))
    distorted_frames = set(f for f in os.listdir(distorted_frame_dir) if f.endswith('.png'))
    
    common_frames = original_frames & distorted_frames
    
    for frame in original_frames - common_frames:
        os.remove(os.path.join(original_frame_dir, frame))
    
    for frame in distorted_frames - common_frames:
        os.remove(os.path.join(distorted_frame_dir, frame))
        
    return

def supplement_align_frames(original_frame_dir, distorted_frame_dir):
    align_folder = os.path.join(distorted_frame_dir, 'align')
    if not os.path.exists(align_folder):
        os.makedirs(align_folder)
    
    distorted_frames = sorted([f for f in os.listdir(distorted_frame_dir) if f.endswith('.png')])
    original_frames = sorted([f for f in os.listdir(original_frame_dir) if f.endswith('.png')])
    supplement = 0

    for i in range(len(distorted_frames) - 1):
        current_frame = distorted_frames[i]
        next_frame = distorted_frames[i + 1]
        
        current_frame_number = int(current_frame.split('.')[0])
        next_frame_number = int(next_frame.split('.')[0])
        
        if next_frame_number - current_frame_number > 1:
            for j in range(1, next_frame_number - current_frame_number):
                new_frame_number = current_frame_number + j
                new_frame_name = f'{new_frame_number:04d}.png'
                # Check if the frame already exists in the original directory
                if os.path.exists(os.path.join(distorted_frame_dir, new_frame_name)):
                    print(f'Frame {new_frame_name} already exists. Stopping supplementation.')
                    break
                new_frame_path = os.path.join(align_folder, new_frame_name)
                current_frame_path = os.path.join(distorted_frame_dir, current_frame)
                res = subprocess.run(['cp', current_frame_path, new_frame_path])
                supplement += 1
    
    # Move supplemented frames back to the original directory
    for frame in os.listdir(align_folder):
        os.rename(os.path.join(align_folder, frame), os.path.join(distorted_frame_dir, frame))
    # Remove the align folder
    os.rmdir(align_folder)
    
    # Calculate the total number of frames in the original directory
    total_original_frames = len(original_frames)
    
    # Supplement distorted frames if they are less than original frames
    if len(distorted_frames) < total_original_frames:
        last_frame = distorted_frames[len(distorted_frames)-1]
        last_frame_number = int(last_frame.split('.')[0])
        for i in range(last_frame_number + 1, total_original_frames):
            new_frame_name = f'{i:04d}.png'
            new_frame_path = os.path.join(distorted_frame_dir, new_frame_name)
            last_frame_path = os.path.join(distorted_frame_dir, last_frame)
            res = subprocess.run(['cp', last_frame_path, new_frame_path])
            supplement += 1
    
    print(f'Supplemented {supplement} frames')
    return

def merge_frames(original_frame_dir, distorted_frame_dir, fps=30):
    
    # Convert original frames to y4m video, the frame number should be continuous
    def ensure_continuous_frames(frame_dir):
        frames = sorted([f for f in os.listdir(frame_dir) if f.endswith('.png')])
        for i, frame in enumerate(frames):
            expected_frame_name = f'{i:04d}.png'
            current_frame_path = os.path.join(frame_dir, frame)
            expected_frame_path = os.path.join(frame_dir, expected_frame_name)
            if frame != expected_frame_name:
                os.rename(current_frame_path, expected_frame_path)

    ensure_continuous_frames(original_frame_dir)
    ensure_continuous_frames(distorted_frame_dir)
    
    res = subprocess.run([
        "ffmpeg", "-r", str(fps), "-f", "image2", "-i", f"{original_frame_dir}/%04d.png",
        "-pix_fmt", "yuv420p", f"{original_frame_dir}/original.y4m"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")
    res = subprocess.run([
        "ffmpeg", "-r", str(fps), "-f", "image2", "-i", f"{distorted_frame_dir}/%04d.png",
        "-pix_fmt", "yuv420p", f"{distorted_frame_dir}/distorted.y4m"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")       
    return 