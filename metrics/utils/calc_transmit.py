import os

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

def get_frame_interval(y4m_file):
    with open(y4m_file, 'rb') as file:
        header = file.readline().decode('ascii')
        # find frame rate
        frame_rate = None
        for part in header.split():
            if part.startswith('F'):
                frame_rate = part[1:]
                break
        
        if frame_rate:
            # calculate frame interval
            num, denom = map(int, frame_rate.split(':'))
            frame_interval = denom / num
            return frame_interval
        else:
            raise ValueError("Frame rate not found in Y4M header")