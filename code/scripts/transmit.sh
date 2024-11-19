#!/bin/bash

# Get the current terminal path
CURRENT_PATH=$(pwd)
echo "Current terminal path: $CURRENT_PATH"
# Directories
MODEL_DIR="${CURRENT_PATH}/code/transmit/models"
WORKDIR="${CURRENT_PATH}/data/workdir"
INPUT_VIDEO_DIR="${CURRENT_PATH}/data/input/videos"
INPUT_AUDIO_DIR="${CURRENT_PATH}/data/input/audios"
NETWORK_TRACES_DIR="${CURRENT_PATH}/data/temp/network_traces"
RAW_LOGS_DIR="${CURRENT_PATH}/data/temp/raw_logs"
DLL_PATH="${CURRENT_PATH}/code/transmit/runtime/dll"
CMD_PATH="${CURRENT_PATH}/code/transmit/runtime/pyinfer/cmdinfer"
EXE_PATH="${CURRENT_PATH}/code/transmit/runtime/pyinfer/cmdinfer/peerconnection_serverless"
# Default values for media config
DEFAULT_AUTOCLOSE=30
DEFAULT_LISTENING_IP="0.0.0.0"
DEFAULT_LISTENING_PORT=8000
DEFAULT_BWE_FEEDBACK_DURATION=200
DEFAULT_VIDEO_HEIGHT=1080
DEFAULT_VIDEO_WIDTH=1920
DEFAULT_VIDEO_FPS=30
DEFAULT_IF_SAVE_MEDIA=true

# Function to generate media config
generate_media_config() {
    local video_file=$1
    local audio_file=$2
    local save_video=$3
    local save_audio=$4
    local receiver_logging=$5
    local sender_logging=$6
    local receiver_output=$7
    local sender_output=$8

    python3 ${CURRENT_PATH}/code/setconfig/set_media_config.py \
            --autoclose "$DEFAULT_AUTOCLOSE" \
            --listening_ip "$DEFAULT_LISTENING_IP" \
            --listening_port "$DEFAULT_LISTENING_PORT" \
            --bwe_feedback_duration "$DEFAULT_BWE_FEEDBACK_DURATION" \
            --video_file "$video_file" \
            --audio_file "$audio_file" \
            --save_video "$save_video" \
            --save_audio "$save_audio" \
            --receiver_logging "$receiver_logging" \
            --sender_logging "$sender_logging" \
            --receiver_output "$receiver_output" \
            --sender_output "$sender_output" \
            --video_height "$DEFAULT_VIDEO_HEIGHT" \
            --video_width "$DEFAULT_VIDEO_WIDTH" \
            --video_fps "$DEFAULT_VIDEO_FPS" \
            --if_save_media "$DEFAULT_IF_SAVE_MEDIA"
}

# Function to apply network configuration
apply_network_config() {
    local config_file=$1
    python3 ${CURRENT_PATH}/code/transmit/tc_setup.py --config "$config_file"
}

# Clean runtime directory
clean_runtime_dir() {
    find "$CMD_PATH" -type f ! -name 'cmdinfer.cc' ! -name 'cmdinfer.h' ! -name 'cmdinfer.py' ! -name 'peerconnection_serverless' -delete
}

# Main loop
printf "Starting transmission\n"
printf "Mounting tmpfs\n"
sudo mount -t tmpfs -o size=20G media "$WORKDIR"
for model in "$MODEL_DIR"/*; do
    if [ -d "$model" ]; then
        model_name=$(basename "$model")
        printf "Running model: %s\n" "$model_name"
        # Clean runtime directory and copy model files
        clean_runtime_dir
        printf "Cleaned runtime directory\n"
        printf "Copying model files\n"
        cp -r "$model"/* "$CMD_PATH"
        
        # Loop through each video and audio file
        for video_file in "$INPUT_VIDEO_DIR"/*.yuv; do
            base_name=$(basename "$video_file" .yuv)
            audio_file="$INPUT_AUDIO_DIR/$base_name.wav"
            if [ -f "$video_file" ] && [ -f "$audio_file" ]; then
                # Clear workdir
                rm -rf "$WORKDIR"/*
                printf "Cleared workdir\n"

                base_name=$(basename "$video_file" .yuv)
                workdir_video="$WORKDIR/$base_name.yuv"
                workdir_audio="$WORKDIR/$base_name.wav"
                cp "$video_file" "$workdir_video"
                cp "$audio_file" "$workdir_audio"
                printf "Copied video and audio files\n"
                # Loop through each network trace file
                for network_trace in "$NETWORK_TRACES_DIR"/*; do
                    if [ -f "$network_trace" ]; then
                        trace_name=$(basename "$network_trace" .json)
                        trace_dir="$WORKDIR/$trace_name"
                        mkdir -p "$trace_dir"
                        printf "Created trace directory\n"

                        receiver_logging="$trace_dir/receiver.log"
                        sender_logging="$trace_dir/sender.log"
                        save_video="$trace_dir/outvideo.yuv"
                        save_audio="$trace_dir/outaudio.wav"

                        receiver_output="$trace_dir/receiver_config.json"
                        sender_output="$trace_dir/sender_config.json"
                        
                        printf "Generated media config\n"
                        # Generate media config
                        generate_media_config "$workdir_video" "$workdir_audio" "$save_video" "$save_audio" "$receiver_logging" "$sender_logging" "$receiver_output" "$sender_output"
                        
                        # Apply network configuration
                        printf "Applying network configuration\n"
                        apply_network_config "$network_trace" &
                        network_pid=$!

                        # Terminate existing screen sessions with the same name
                        screen -ls | grep receiver_session | awk '{print $1}' | xargs -I {} screen -S {} -X quit
                        screen -ls | grep sender_session | awk '{print $1}' | xargs -I {} screen -S {} -X quit
                        
                        printf "Starting screen sessions\n"
                        # 注意这里要是端口被占用，会导致screen传输失败
                        screen -dmS receiver_session bash -c "cd $CURRENT_PATH; \
                            export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$DLL_PATH; \
                            python $EXE_PATH $receiver_output" &
                        screen -dmS sender_session bash -c "cd $CURRENT_PATH; \
                            export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$DLL_PATH; \
                            python $EXE_PATH $sender_output" &
                        printf "Running model: %s, video: %s, trace: %s\n" "$model_name" "$base_name" "$trace_name"
                        # Wait for both screen sessions to finish
                        while screen -list | grep -q "sender_session" || screen -list | grep -q "receiver_session"; do
                            sleep 1
                        done
                        printf "receive-send finished\n"
                        # Terminate the network configuration process

                        if kill -9 $network_pid; then
                            printf "network process killed finished\n"
                        else
                            printf "failed to kill network process with PID %s\n" "$network_pid"
                        fi
                        # wait
                        
                        # Copy logs to raw logs directory
                        printf "Copying logs to raw logs directory\n"
                        raw_log_dir="$RAW_LOGS_DIR/$base_name/$trace_name/$model_name"
                        mkdir -p "$raw_log_dir"
                        cp "$receiver_logging" "$raw_log_dir"
                        cp "$sender_logging" "$raw_log_dir"
                        printf "Logs copied\n"
                    fi
                done
            fi
        done
    fi
done
sudo umount media
if mountpoint -q media; then
    printf "Failed to unmount tmpfs\n"
else
    printf "Successfully unmounted tmpfs\n"
fi
printf "Transmission finished\n"