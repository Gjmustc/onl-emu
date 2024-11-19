import json
import argparse
import os

AUTOCLOSE = 30
LISTENING_IP = "0.0.0.0"
LISTENING_PORT = 8000
BWE_FEEDBACK_DURATION = 200
BASE_INPUT_DIR = "./data/workdir"
BASE_OUTPUT_DIR = "./data/workdir"
INPUT_VIDEO_FILE = os.path.join(BASE_INPUT_DIR, "test.yuv")
INPUT_AUDIO_FILE = os.path.join(BASE_INPUT_DIR, "test.wav")
OUTPUT_VIDEO_FILE = os.path.join(BASE_OUTPUT_DIR, "outvideo.yuv")
OUTPUT_AUDIO_FILE = os.path.join(BASE_OUTPUT_DIR, "outaudio.wav")
RECEIVER_LOGGING = os.path.join(BASE_OUTPUT_DIR, "receiver.log")
SENDER_LOGGING = os.path.join(BASE_OUTPUT_DIR, "sender.log")
VIDEO_HEIGHT = 1080
VIDEO_WIDTH = 1920
VIDEO_FPS = 30

class MediaConfig:
    def __init__(self, 
        autoclose=AUTOCLOSE,
        listening_ip=LISTENING_IP,
        listening_port=LISTENING_PORT,
        bwe_feedback_duration=BWE_FEEDBACK_DURATION,
        video_file=INPUT_VIDEO_FILE,
        audio_file=INPUT_AUDIO_FILE,
        save_video=OUTPUT_VIDEO_FILE,
        save_audio=OUTPUT_AUDIO_FILE,
        receiver_logging=RECEIVER_LOGGING,
        sender_logging=SENDER_LOGGING,
        video_height=VIDEO_HEIGHT,
        video_width=VIDEO_WIDTH,
        video_fps=VIDEO_FPS,
        if_save_media=True
    ):
        self.autoclose = autoclose
        self.listening_ip = listening_ip
        self.listening_port = listening_port
        self.bwe_feedback_duration = bwe_feedback_duration
        self.video_file = video_file
        self.audio_file = audio_file
        self.save_video = save_video
        self.save_audio = save_audio
        self.receiver_logging = receiver_logging
        self.sender_logging = sender_logging
        self.video_height = video_height
        self.video_width = video_width
        self.video_fps = video_fps
        self.if_save_media = if_save_media

    def generate_receiver_config(self):
        config = {
            "serverless_connection": {
                "autoclose": self.autoclose,
                "sender": {
                    "enabled": False
                },
                "receiver": {
                    "enabled": True,
                    "listening_ip": self.listening_ip,
                    "listening_port": self.listening_port
                }
            },
            "bwe_feedback_duration": self.bwe_feedback_duration,
            "video_source": {
                "video_disabled": {
                    "enabled": True
                },
                "webcam": {
                    "enabled": False
                },
                "video_file": {
                    "enabled": False,
                    "height": self.video_height,
                    "width": self.video_width,
                    "fps": self.video_fps,
                    "file_path": self.video_file
                }
            },
            "audio_source": {
                "microphone": {
                    "enabled": False
                },
                "audio_file": {
                    "enabled": True,
                    "file_path": self.audio_file
                }
            },
            "save_to_file": {
                "enabled": self.if_save_media,
                "audio": {
                    "file_path": self.save_audio
                },
                "video": {
                    "width": self.video_width,
                    "height": self.video_height,
                    "fps": self.video_fps,
                    "file_path": self.save_video
                }
            },
            "logging": {
                "enabled": True,
                "log_output_path": self.receiver_logging
            }
        }
        return config

    def generate_sender_config(self):
        config = {
            "serverless_connection": {
                "autoclose": self.autoclose,
                "sender": {
                    "enabled": True,
                    "dest_ip": self.listening_ip,
                    "dest_port": self.listening_port
                },
                "receiver": {
                    "enabled": False
                }
            },
            "bwe_feedback_duration": self.bwe_feedback_duration,
            "video_source": {
                "video_disabled": {
                    "enabled": False
                },
                "webcam": {
                    "enabled": False
                },
                "video_file": {
                    "enabled": True,
                    "height": self.video_height,
                    "width": self.video_width,
                    "fps": self.video_fps,
                    "file_path": self.video_file
                }
            },
            "audio_source": {
                "microphone": {
                    "enabled": False
                },
                "audio_file": {
                    "enabled": True,
                    "file_path": self.audio_file
                }
            },
            "save_to_file": {
                "enabled": False
            },
            "logging": {
                "enabled": True,
                "log_output_path": self.sender_logging
            }
        }
        return config

    def save_config(self, config, path):
        with open(path, 'w') as f:
            json.dump(config, f, indent=4)

def main():
    parser = argparse.ArgumentParser(description="Generate media configuration files.")
    parser.add_argument('--autoclose', type=int, default=AUTOCLOSE, help='Autoclose duration')
    parser.add_argument('--listening_ip', type=str, default=LISTENING_IP, help='Listening IP address')
    parser.add_argument('--listening_port', type=int, default=LISTENING_PORT, help='Listening port')
    parser.add_argument('--bwe_feedback_duration', type=int, default=BWE_FEEDBACK_DURATION, help='BWE feedback duration')
    parser.add_argument('--video_file', type=str, default=INPUT_VIDEO_FILE, help='Path to the video file')
    parser.add_argument('--audio_file', type=str, default=INPUT_AUDIO_FILE, help='Path to the audio file')
    parser.add_argument('--save_video', type=str, default=OUTPUT_VIDEO_FILE, help='Path to save the video file')
    parser.add_argument('--save_audio', type=str, default=OUTPUT_AUDIO_FILE, help='Path to save the audio file')
    parser.add_argument('--receiver_logging', type=str, default=RECEIVER_LOGGING, help='Path to save the receiver log file')
    parser.add_argument('--sender_logging', type=str, default=SENDER_LOGGING, help='Path to save the sender log file')
    parser.add_argument('--receiver_output', type=str, default=os.path.join(BASE_OUTPUT_DIR, "receiver_config.json"), help='Path to save the receiver config file')
    parser.add_argument('--sender_output', type=str, default=os.path.join(BASE_OUTPUT_DIR, "sender_config.json"), help='Path to save the sender config file')
    parser.add_argument('--video_height', type=int, default=VIDEO_HEIGHT, help='Video height')
    parser.add_argument('--video_width', type=int, default=VIDEO_WIDTH, help='Video width')
    parser.add_argument('--video_fps', type=int, default=VIDEO_FPS, help='Video frames per second')
    parser.add_argument('--if_save_media', type=bool, default=True, help='Flag to save media')
    
    args = parser.parse_args()
    media_config = MediaConfig(
        autoclose=args.autoclose,
        listening_ip=args.listening_ip,
        listening_port=args.listening_port,
        bwe_feedback_duration=args.bwe_feedback_duration,
        video_file=args.video_file,
        audio_file=args.audio_file,
        save_video=args.save_video,
        save_audio=args.save_audio,
        receiver_logging=args.receiver_logging,
        sender_logging=args.sender_logging,
        video_height=args.video_height,
        video_width=args.video_width,
        video_fps=args.video_fps,
        if_save_media=args.if_save_media
    )
    receiver_config = media_config.generate_receiver_config()
    media_config.save_config(receiver_config, args.receiver_output)
    sender_config = media_config.generate_sender_config()
    media_config.save_config(sender_config, args.sender_output)
if __name__ == "__main__":
    main()
