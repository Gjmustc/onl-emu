# User Guide

## File Structure

```bash
.
├── LICENSE
├── emulation.sh    # RTC transmission emulation script (including score calculation)
├── filter_logs.py  # Log filtering script
├── log             # Storage location for filtered transmission results
├── metrics
│   ├── calc_scores.py # Score calculation script
│   ├── eval_network.py # Network evaluation script (not used in transmission emulation)
│   ├── tests
│   │   ├── data  # Test data
│   └── utils
│       ├── net_eval_method.py  # Network evaluation script used in Challenge
│       ├── ocr_frame_align.sh  # Frame alignment script used in Challenge
│       ├── preprocess.py       # Video preprocessing script used in transmission emulation
│       ├── video_eval_method.py # Video evaluation script used in Challenge
├── preprocess_video.sh          # Video preprocessing script, including frame cropping, resolution adjustment, and frame number addition
├── readme.md
├── runtime                     # Transmission emulation runtime directory
│   ├── dll                     # Transmission emulation runtime libraries
│   ├── exe                     # Transmission emulation runtime executables
│   │   ├── peerconnection_gcc  # GCC baseline
│   │   ├── peerconnection_serverless_pyinfer # PyInfer executable
│   │   ├── peerconnection_serverless_pyinfer_nosend # Additional compiled PyInfer executable without sender log printing
│   │   └── peerconnection_serverless_pyinfer_withcodec # Additional compiled PyInfer executable with codec-related log printing
│   └── pyinfer
│       └── cmdinfer
│           ├── BandwidthEstimator.py   # Bandwidth estimator RL interface
│           ├── cmdinfer.cc
│           ├── cmdinfer.h
│           ├── cmdinfer.py
│           └── peerconnection_serverless # PyInfer python interface
├── set_media_config.py  # Script to set audio and video parameters for emulation
├── tc_setup.py          # Script to start network configuration
└── workdir              # Transmission emulation working directory, ramdisk mapping location
```

## Script Usage Instructions

### Video Dataset Preparation

```bash
./preprocess_video.sh -i input_file -s start_frame -e end_frame -w width -h height -n frame_number_size -x x_offset -y y_offset -o output_file
```

#### Parameter Description

- `-i`: Input MP4 video file path
- `-s`: Start frame number (default: 0)
- `-e`: End frame number (default: 100)
- `-w`: Video width (default: 1920)
- `-h`: Video height (default: 1080)
- `-n`: Frame number font size (default: 48)
- `-x`: X-axis offset of frame number (default: 50)
- `-y`: Y-axis offset of frame number (default: 50)
- `-o`: Output rawvideo format YUV video file path

#### Example

```bash
./preprocess_video.sh -i /home/onl/TestData/testmedia/src_videos/animation.mp4 -s 0 -e 300 -w 1280 -h 720 -n 48 -x 50 -y 50 -o output.yuv
```

### Transmission Emulation

```bash
./emulation.sh [-m model] [-v video_file] [-a audio_file] [-t trace_file] [-c autoclose] [-W video_width] [-H video_height] [-f video_fps] [-s if_save_media] [-l log_dir] [-d ramdisk_size_G] [-x crop_x] [-y crop_y] [-w crop_width] [-h crop_height]
```

#### Parameter Description

- `-m`: Model directory (containing BandwidthEstimator.py file) or `gcc` (to use GCC baseline transmission)
- `-v`: YUV video file path
- `-a`: WAV audio file path
- `-t`: TC network configuration file path
- `-c`: Transmission auto-close time (default: 120)
- `-W`: Video width (default: 1920)
- `-H`: Video height (default: 1080)
- `-f`: Video frame rate (default: 30)
- `-s`: Whether to save media files (default: true)
- `-l`: Log storage directory
- `-d`: RAM disk size (default: 24G)
- `-x`: X-axis offset of crop area (default: 900)
- `-y`: Y-axis offset of crop area (default: 1020)
- `-w`: Width of crop area (default: 150)
- `-h`: Height of crop area (default: 60)

#### Example

```bash
./emulation.sh -m /home/onl/test_metrics/1Mbps -v /home/onl/onl-emu/metrics/tests/data/animation_1200frame.yuv -a /home/onl/TestData/testmedia/audios/1080p_animation_1.wav -t /home/onl/LLMCC/traces/4M.json -c 40 -W 1920 -H 1080 -f 30 -s true -l /home/onl/onl-emu/log
```

## Current Issues

- The frame numbers on the video files in /home/onl/TestData/testmedia/videos are of the old specification and occupy a small portion of the frame, requiring re-framing
- The frame number specification for the video dataset needs to correspond one-to-one with the frame number recognition method for video evaluation
- VMAF evaluation scores are relatively low and need further tuning
- Delay burst phenomenon occurs during transmission emulation, currently suspected to be caused by inappropriate queue length settings in tc control, requiring further tuning
- ...
