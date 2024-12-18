import os
import json
import unittest
import subprocess
cur_path=os.path.dirname(os.path.abspath(__file__))

class TestCalculateScores(unittest.TestCase):

    def setUp(self):
        self.original_video_path = cur_path + '/data/origin.yuv'
        self.distorted_video_dir = cur_path +  '/data/test_videos/distorted'
        self.original_frame_dir = cur_path + '/data/test_frames/original'
        self.distorted_frame_dir = cur_path + '/data/test_frames/distorted'
        self.output_dir = cur_path + '/data/test_output'
        self.output_json = cur_path + '/data/test_output/results.json'
        self.video_width = 1920
        self.video_height = 1080
        self.video_fps = 30

        # Create directories if they don't exist
        os.makedirs(self.distorted_video_dir, exist_ok=True)
        os.makedirs(self.original_frame_dir, exist_ok=True)
        os.makedirs(self.distorted_frame_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        with open(self.output_json, 'w') as f:
            f.write('')
        
        # Generate distorted videos with different levels of quality
        self.distorted_videos = self.generate_distorted_videos()

    def generate_distorted_videos(self):
        distorted_videos = []
        
        # not testing qualities and bitrates,because the result seems to be the same 
        qualities = []  # Different CRF values for different quality levels, lower is better, range is 18-51
        tgt_bitrates = [] #Different bitrates for different quality levels, higher is better, range is 600-4000
        
        noises = [2,5,8,10,15,20,25,30,35,40,50] # Different noise levels for different quality levels, higher is better

        for quality in qualities:
            distorted_video_path = os.path.join(self.distorted_video_dir, f'distorted_{quality}.yuv')
            cmd = [
                'ffmpeg', '-pix_fmt', 'yuv420p', '-s', f'{self.video_width}x{self.video_height}', '-r', str(self.video_fps),
                '-i', self.original_video_path, '-crf', str(quality), '-r', str(self.video_fps), '-f', 'yuv4mpegpipe','-y', distorted_video_path
            ]
            subprocess.run(cmd, capture_output=True)
            distorted_videos.append(distorted_video_path)
            
        for bitrate in tgt_bitrates:
            distorted_video_path = os.path.join(self.distorted_video_dir, f'distorted_{bitrate}.yuv')
            cmd = [
                'ffmpeg', '-pix_fmt', 'yuv420p', '-s', f'{self.video_width}x{self.video_height}', '-r', str(self.video_fps),
                '-i', self.original_video_path, '-b:v', str(bitrate)+'k', '-r', str(self.video_fps), '-f', 'yuv4mpegpipe', '-y', distorted_video_path
            ]
            subprocess.run(cmd, capture_output=True)
            distorted_videos.append(distorted_video_path)
            
        for noise in noises:
            distorted_video_path = os.path.join(self.distorted_video_dir, f'distorted_{noise}.yuv')
            cmd = [
                'ffmpeg', '-pix_fmt', 'yuv420p', '-s', f'{self.video_width}x{self.video_height}', '-r', str(self.video_fps),
                '-i', self.original_video_path, '-vf', f'noise=alls={noise}:allf=t+u', '-r', str(self.video_fps), '-f', 'yuv4mpegpipe', '-y', distorted_video_path
            ]
            subprocess.run(cmd, capture_output=True)
            distorted_videos.append(distorted_video_path)
        
        return distorted_videos

    def test_calculate_scores(self):
        for distorted_video in self.distorted_videos:
            output_json = self.output_json.replace('.json', f'_{os.path.basename(distorted_video).replace(".yuv", "")}.json')
            with open(output_json, 'w') as f:
                f.write('')
            
            cmd = [ \
                'python3', '../calculate_scores.py', \
                '--original_video_path', self.original_video_path, \
                '--distorted_video_path', distorted_video, \
                '--original_frame_dir', self.original_frame_dir, \
                '--distorted_frame_dir', self.distorted_frame_dir, \
                '--output_json', str(output_json), \
                '--video_width', str(self.video_width), \
                '--video_height', str(self.video_height), \
                '--video_fps', str(self.video_fps), \
                '--israwvideo', 
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf8")

            with open(output_json, 'r') as f:
                results = json.load(f)
                print(f'Results for {distorted_video}: {results}')

                # Check that the results contain the expected keys
                self.assertIn('Frame loss rate', results)
                self.assertIn('Average PSNR', results)
                self.assertIn('Average SSIM', results)
                self.assertIn('FVD score', results)
                self.assertIn('LPIPS score', results)
                self.assertIn('Vmaf score', results)
                # self.assertIn('Network score', results)

                # Check that the scores are within a reasonable range
                self.assertGreaterEqual(results['Average PSNR'], 0)
                self.assertGreaterEqual(results['Average SSIM'], 0)
                self.assertLessEqual(results['Average SSIM'], 1)
                self.assertGreaterEqual(results['FVD score'], 0)
                self.assertGreaterEqual(results['LPIPS score'], 0)
                self.assertLessEqual(results['LPIPS score'], 1)
                self.assertGreaterEqual(results['Vmaf score'], 0)
                self.assertLessEqual(results['Vmaf score'], 100)
                # self.assertGreaterEqual(results['Network score'], 0)

if __name__ == '__main__':
    unittest.main()