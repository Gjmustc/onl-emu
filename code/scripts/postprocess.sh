#!/bin/bash

# Get the current terminal path
CURRENT_PATH=$(pwd)
echo "Current terminal path: $CURRENT_PATH"
# Directories
RAW_LOGS_DIR="${CURRENT_PATH}/data/temp/raw_logs"
COMPRESSED_LOGS_DIR="${CURRENT_PATH}/data/output/util_logs"
FIGURES_DIR="${CURRENT_PATH}/data/output/results/figures"
PROCESS_DIR="${CURRENT_PATH}/code/postprocess"
# Patterns for compressing logs

RECEIVER_PATTERNS=(
    "\(remote_estimator_proxy\.cc:152\): (\{.*\})"\
)


SENDER_PATTERNS=(
    "\(rtp_transport_controller_send\.cc:\d+\): PostUpdates SetTargetRate: (\d+), PostUpdates SetTargetRate Time: (\d+)"\
    "\(rtp_sender_egress\.cc:\d+\): sendpacket sequence_number: (\d+), packet_sendtime: (\d+) ms, packet_capture_time: \d+ ms, packet_type: \d+, packet_payload_size: (\d+)"\
    "\(video_stream_encoder\.cc:\d+\): Video frame parameters changed: dimensions=(\d+)x(\d+), texture=\d+ at time= (\d+)ms."
)
# Create output directories if they don't exist
mkdir -p "$COMPRESSED_LOGS_DIR"
mkdir -p "$FIGURES_DIR"
# 将模式数组转换为以空格分隔的字符串，以便传递给Python脚本

RECEIVER_PATTERNS_STR=$(printf "%s|" "${RECEIVER_PATTERNS[@]}")
SENDER_PATTERNS_STR=$(printf "%s|" "${SENDER_PATTERNS[@]}")
if [ -z "$RECEIVER_PATTERNS_STR" ] || [ -z "$SENDER_PATTERNS_STR" ]; then
    echo "Error: receiver_patterns or sender_patterns is empty."
    exit 1
fi

# Function to process logs
process_logs() {
    local receiver_log=$1
    local sender_log=$2
    local base_input_dir=$3
    local base_output_dir_util=$4
    local base_output_dir_fig=$5

    # Compress logs
    python3 compress_logs.py \
            --receiver_log "$receiver_log" \
            --sender_log "$sender_log" \
            --receiver_patterns "$RECEIVER_PATTERNS_STR" \
            --sender_patterns "$SENDER_PATTERNS_STR" \
            --base_input_dir "$base_input_dir" \
            --base_output_dir "$base_output_dir_util"

    # Draw figures
    python3 draw.py \
            --receiver_log "$receiver_log" \
            --sender_log "$sender_log" \
            --receiver_patterns "$RECEIVER_PATTERNS_STR" \
            --sender_patterns "$SENDER_PATTERNS_STR" \
            --base_input_dir "$base_input_dir" \
            --base_output_dir "$base_output_dir_fig" \
            --verbose
}

cd "$PROCESS_DIR"
# Main loop to traverse raw logs directory
for video_dir in "$RAW_LOGS_DIR"/*; do
    for network_dir in "$video_dir"/*; do
        for model_dir in "$network_dir"/*; do
            receiver_log="$model_dir/receiver.log"
            sender_log="$model_dir/sender.log"
            if [ -f "$receiver_log" ] && [ -f "$sender_log" ]; then
                echo "Processing logs for video: $(basename "$video_dir"), network: $(basename "$network_dir"), model: $(basename "$model_dir")"
                process_logs "$receiver_log" "$sender_log" "$RAW_LOGS_DIR" "$COMPRESSED_LOGS_DIR" "$FIGURES_DIR"
            else
                echo "Skipping logs for video: $(basename "$video_dir"), network: $(basename "$network_dir"), model: $(basename "$model_dir") - Missing receiver or sender log"
            fi
        done
    done
done