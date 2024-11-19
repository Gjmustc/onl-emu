#!/bin/bash

# Get the current terminal path
CURRENT_PATH=$(pwd)
echo "Current terminal path: $CURRENT_PATH"
# Directories
input_dir="${CURRENT_PATH}/data/input/videos"
temp_dir="${CURRENT_PATH}/data/temp"
output_dir="${CURRENT_PATH}/data/output"
network_traces_dir="${CURRENT_PATH}/data/temp/network_traces"
models_dir="${CURRENT_PATH}/code/transmit/models"

# Function to create directory and handle errors
create_dir() {
    if [ ! -d "$1" ]; then
        mkdir -p "$1"
        if [ $? -ne 0 ]; then
            echo "Failed to create directory: $1"
            exit 1
        fi
    fi
}

rm -rf "$temp_dir/raw_logs"
rm -rf "$output_dir/util_logs"
rm -rf "$output_dir/results/figures"

# Iterate over each video in the input directory
for video in "$input_dir"/*; do
    video_name=$(basename "$video" | cut -d. -f1)

    # Create directories for each video
    create_dir "$temp_dir/raw_logs/$video_name"
    create_dir "$output_dir/util_logs/$video_name"
    create_dir "$output_dir/results/figures/$video_name"

    # Iterate over each network trace
    for network_trace in "$network_traces_dir"/*; do
        network_trace_name=$(basename "$network_trace" | cut -d. -f1)

        # Create network trace directories
        create_dir "$temp_dir/raw_logs/$video_name/$network_trace_name"
        create_dir "$output_dir/util_logs/$video_name/$network_trace_name"
        create_dir "$output_dir/results/figures/$video_name/$network_trace_name"

        # Iterate over each model
        for model in "$models_dir"/*; do
            model_name=$(basename "$model" | cut -d. -f1)

            # Create model directories
            create_dir "$temp_dir/raw_logs/$video_name/$network_trace_name/$model_name"
            create_dir "$output_dir/util_logs/$video_name/$network_trace_name/$model_name"
            create_dir "$output_dir/results/figures/$video_name/$network_trace_name/$model_name"
        done
    done
done

echo "Directory structure created successfully."