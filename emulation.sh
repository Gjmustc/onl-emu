#!/bin/bash

# Get the current terminal path
CURRENT_PATH=$(pwd)
echo "Current terminal path: $CURRENT_PATH"
# Get the current script path： emulation/emulation.sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

# Default parameter values
DEFAULT_AUTOCLOSE=120
DEFAULT_VIDEO_HEIGHT=1080
DEFAULT_VIDEO_WIDTH=1920
DEFAULT_VIDEO_FPS=30
DEFAULT_IF_SAVE_MEDIA=true
DEFAULT_RAMDISK_SIZE=24

# Patterns for compressing logs
RECEIVER_PATTERNS=(
    "\(remote_estimator_proxy\.cc:\d+\): (\{.*\})"\
)

SENDER_PATTERNS=(
    "\(rtp_transport_controller_send\.cc:\d+\): PostUpdates SetTargetRate: (\d+), PostUpdates SetTargetRate Time: (\d+)"\
    "\(rtp_sender_egress\.cc:\d+\): RtpSenderEgress::SendPacket: packet ssrc: (\d+), sequence number: (\d+), timestamp: \d+, payload type: \d+, payload size: (\d+), packet_sendtime: (\d+) ms, packet_type: (-?\d+)" \
    "\(video_stream_encoder\.cc:\d+\): Video frame parameters changed: dimensions=(\d+)x(\d+), texture=\d+ at time= (\d+)ms."
)
RECEIVER_PATTERNS_STR=$(printf "%s|" "${RECEIVER_PATTERNS[@]}")
SENDER_PATTERNS_STR=$(printf "%s|" "${SENDER_PATTERNS[@]}")
if [ -z "$RECEIVER_PATTERNS_STR" ] || [ -z "$SENDER_PATTERNS_STR" ]; then
    echo "Error: receiver_patterns or sender_patterns is empty."
    exit 1
fi

# Parse input parameters
while getopts "hm:v:a:t:c:W:H:f:s:l:d" opt; do
  case $opt in
    h) echo "Usage: `basename $0` [-m model] [-v video_file] [-a audio_file][-t trace_file] [-c autoclose] [-W video_width] [-H video_height] [-f video_fps] [-s if_save_media] [-l log_dir] [-d ramdisk_size_G]" >&2
       exit 0 ;;
    m) MODEL_DIR="$OPTARG" ;;
    v) VIDEO_FILE="$OPTARG" ;;
    a) AUDIO_FILE="$OPTARG" ;;
    t) TRACE_FILE="$OPTARG" ;;
    c) AUTOCLOSE="$OPTARG" ;;
    W) VIDEO_WIDTH="$OPTARG" ;;
    H) VIDEO_HEIGHT="$OPTARG" ;; 
    f) VIDEO_FPS="$OPTARG" ;;
    s) IF_SAVE_MEDIA="$OPTARG" ;;
    l) LOG_DIR="$OPTARG" ;;
    d) RAMDISK_SIZE="$OPTARG" ;;
    \?) echo "Invalid option: -$OPTARG" >&2
        exit 1 ;;
    :) echo "Option -$OPTARG requires an argument." >&2
       exit 1 ;;
  esac
done

# Set default values
AUTOCLOSE=${AUTOCLOSE:-$DEFAULT_AUTOCLOSE}
VIDEO_WIDTH=${VIDEO_WIDTH:-$DEFAULT_VIDEO_WIDTH}
VIDEO_HEIGHT=${VIDEO_HEIGHT:-$DEFAULT_VIDEO_HEIGHT}
VIDEO_FPS=${VIDEO_FPS:-$DEFAULT_VIDEO_FPS}
IF_SAVE_MEDIA=${IF_SAVE_MEDIA:-$DEFAULT_IF_SAVE_MEDIA}
RAMDISK_SIZE=${RAMDISK_SIZE:-$DEFAULT_RAMDISK_SIZE}

# Other directory settings
WORKDIR="${SCRIPT_DIR}/workdir"
DLL_PATH="${SCRIPT_DIR}/runtime/dll"
CMDINFER_PATH="${SCRIPT_DIR}/runtime/pyinfer/cmdinfer"
PYINFER_PATH="${SCRIPT_DIR}/runtime/pyinfer/cmdinfer/peerconnection_serverless"
GCC_PATH="${SCRIPT_DIR}/runtime/exe/peerconnection_gcc"
# Generate media config
generate_media_config() {
    local video_file=$1
    local audio_file=$2
    local save_video=$3
    local save_audio=$4
    local receiver_logging=$5
    local sender_logging=$6
    local receiver_output=$7
    local sender_output=$8
    local listening_port=$((RANDOM % 800 + 8000))

    python3 ${SCRIPT_DIR}/set_media_config.py \
            --autoclose "$AUTOCLOSE" \
            --listening_ip "0.0.0.0" \
            --listening_port "$listening_port" \
            --bwe_feedback_duration 200 \
            --video_file "$video_file" \
            --audio_file "$audio_file" \
            --save_video "$save_video" \
            --save_audio "$save_audio" \
            --receiver_logging "$receiver_logging" \
            --sender_logging "$sender_logging" \
            --receiver_output "$receiver_output" \
            --sender_output "$sender_output" \
            --video_height "$VIDEO_HEIGHT" \
            --video_width "$VIDEO_WIDTH" \
            --video_fps "$VIDEO_FPS" \
            --if_save_media "$IF_SAVE_MEDIA"
}

# Calculate score for video and network
calculate_score() {
    local receiver_log=$1
    local src_video=$2
    local dst_video=$3
    local output_file=$4

    python3 ${SCRIPT_DIR}/metrics/eval_video.py \
            --src_video "$src_video" \
            --dst_video "$dst_video" \
            --output "$output_file" \
            --frame_align_method "ocr" \
            --video_size "${VIDEO_WIDTH}x${VIDEO_HEIGHT}" \
            --pixel_format "420" \
            --bitdepth "8" \
            --fps "$VIDEO_FPS"

    python3 ${SCRIPT_DIR}/metrics/eval_network.py \
            --dst_network_log "$receiver_log" \
            --output "$output_file"
}

# Compress logs according to patterns
compress_logs() {
    local receiver_log=$1
    local sender_log=$2
    local base_input_dir=$3
    local base_output_dir=$4

    python3 ${SCRIPT_DIR}/compress_logs.py \
            --receiver_log "$receiver_log" \
            --sender_log "$sender_log" \
            --receiver_patterns "$RECEIVER_PATTERNS_STR" \
            --sender_patterns "$SENDER_PATTERNS_STR" \
            --base_input_dir "$base_input_dir" \
            --base_output_dir "$base_output_dir"
}

# Clean runtime directory after changing the run model
clean_runtime_dir() {
    find "$CMDINFER_PATH" -type f ! -name 'cmdinfer.cc' ! -name 'cmdinfer.h' ! -name 'cmdinfer.py' ! -name 'peerconnection_serverless' -delete
    find "$CMDINFER_PATH" -type d -mindepth 1 -exec rm -r {} +
}

# Main loop
emulation(){

    printf "Starting transmission\n"
    # Ban other network access
    for iface in $(ls /sys/class/net/ | grep -vE '^(eth0|lo)$'); do
        sudo ifconfig $iface down
    done
    sudo iptables -A INPUT -i eth0 -s 10.0.0.0/8 -p udp -j DROP
    sudo iptables -A OUTPUT -o eth0 -d 10.0.0.0/8 -p udp -j DROP
    printf "Ban other network access\n"
    # Mount tmpfs for faster I/O read/write operations
    mkdir -p "$WORKDIR"
    while mountpoint -q media; do
        sudo umount media --force
    done
    printf "Successfully unmounted tmpfs\n"
    printf "Mounting tmpfs\n"
    sudo mount -t tmpfs -o size=${RAMDISK_SIZE}G media "$WORKDIR"

    rm -r "$WORKDIR"/*
    printf "Cleared workdir\n"

    if [ -f "$TRACE_FILE" ]; then
        trace_name=$(basename "$TRACE_FILE" .json)
        trace_dir="$WORKDIR/$trace_name"
        mkdir -p "$trace_dir"
        printf "Created trace directory\n"
        receiver_logging="$trace_dir/receiver.log"
        sender_logging="$trace_dir/sender.log"
        save_video="$trace_dir/outvideo.yuv"
        save_audio="$trace_dir/outaudio.wav"
        receiver_output="$trace_dir/receiver_config.json"
        sender_output="$trace_dir/sender_config.json"
        printf "Applying network configuration\n"
        python3 ${SCRIPT_DIR}/tc_setup.py --config "$TRACE_FILE" &
        network_pid=$!
        sleep 10
    fi
    if [ -f "$VIDEO_FILE" ] && [ -f "$AUDIO_FILE" ]; then
        base_name=$(basename "$VIDEO_FILE" .yuv)
        workdir_audio="$WORKDIR/$base_name.wav"
        cp "$AUDIO_FILE" "$workdir_audio"
    fi
    if [ "$MODEL_DIR" == "gcc" ]; then
        # Convert video file to y4m format using ffmpeg, because the original yuv format is not supported by the gcc_baseline
        ffmpeg -s ${VIDEO_WIDTH}x${VIDEO_HEIGHT} -pix_fmt yuv420p -r $VIDEO_FPS -i "$VIDEO_FILE" -vsync 0 "$WORKDIR/$base_name.y4m"
        workdir_video="$WORKDIR/$base_name.y4m"
        printf "Copied video and audio files\n"
        printf "Generated media config\n"
        generate_media_config "$workdir_video" "$workdir_audio" "$save_video" "$save_audio" "$receiver_logging" "$sender_logging" "$receiver_output" "$sender_output"

        printf "Starting transmission\n"
        printf "Running model: gcc, video: %s, trace: %s\n" "$base_name" "$trace_name"
        $GCC_PATH $receiver_output &
        receiver_pid=$!
        sleep 20
        $GCC_PATH $sender_output
        sender_pid=$!
        wait $receiver_pid
        printf "Transmission finished\n"

    elif [ -d "$MODEL_DIR" ]; then
        workdir_video="$WORKDIR/$base_name.yuv"
        cp "$VIDEO_FILE" "$workdir_video"
        printf "Copied video and audio files\n"
        printf "Generated media config\n"
        generate_media_config "$workdir_video" "$workdir_audio" "$save_video" "$save_audio" "$receiver_logging" "$sender_logging" "$receiver_output" "$sender_output"

        model_name=$(basename "$MODEL_DIR")
        clean_runtime_dir
        printf "Cleaned runtime directory\n"
        printf "Copying model files\n"
        cp -rf "$MODEL_DIR"/* "$CMDINFER_PATH"
        printf "Model files copied\n"
        cd $CMDINFER_PATH
        export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$DLL_PATH

        printf "Starting transmission\n"
        printf "Running model: %s, video: %s, trace: %s\n" "$model_name" "$base_name" "$trace_name"
        python3 $PYINFER_PATH $receiver_output &
        receiver_pid=$!
        sleep 20 # Wait for the receiver to set up
        python3 $PYINFER_PATH $sender_output
        sender_pid=$!
        wait $receiver_pid
        printf "Transmission finished\n"
    fi
    # Terminate network configuration process
    while kill -0 $network_pid 2>/dev/null; do
        sudo kill -9 $network_pid
    done
    echo "The network configuration process $network_pid has been terminated"
    sleep 10

    # Post-process logs: calculate score and compress logs
    printf "Calculating score\n"
    model_name=${model_name:-gcc}
    store_dir="$LOG_DIR/$base_name/$trace_name/$model_name"
    mkdir -p "$store_dir"
    rm -r "$store_dir"/*
    if [ -f "$store_dir/score.json" ]; then
        : > "$store_dir/score.json"
    else
        touch "$store_dir/score.json"
    fi
    calculate_score "$receiver_logging" "$workdir_video" "$save_video" "$store_dir/score.json"
    printf "Score calculated\n"
    printf "Compressing logs\n"
    compress_logs "$receiver_logging" "$sender_logging" "$trace_dir" "$store_dir"
    printf "Logs compressed and moved\n"

    # Clean up
    rm -r "$trace_dir"/*
    printf "Cleared transmission outputs\n"

    sudo umount media --force
    while mountpoint -q media; do
        sudo umount media --force
    done
    printf "Successfully unmounted tmpfs\n"
    printf "Transmission finished\n"
}

# Main function
main() {
    # Your main logic here
    echo "Running main function with the following parameters:"
    echo "MODEL_DIR: $MODEL_DIR"
    echo "VIDEO_FILE: $VIDEO_FILE"
    echo "AUDIO_FILE: $AUDIO_FILE"
    echo "TRACE_FILE: $TRACE_FILE"
    echo "AUTOCLOSE: $AUTOCLOSE"
    echo "VIDEO_WIDTH: $VIDEO_WIDTH"
    echo "VIDEO_HEIGHT: $VIDEO_HEIGHT"
    echo "VIDEO_FPS: $VIDEO_FPS"
    echo "IF_SAVE_MEDIA: $IF_SAVE_MEDIA"
    echo "LOG_DIR: $LOG_DIR"
    emulation
    # Add the rest of your script logic here
}

# Call main function if parameter parsing was successful
main