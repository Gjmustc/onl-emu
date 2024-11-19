#!/bin/bash

# Get the current terminal path
CURRENT_PATH=$(pwd)
echo "Current terminal path: $CURRENT_PATH"
# Directory to save the generated network traces
OUTPUT_DIR="${CURRENT_PATH}/data/temp/network_traces"
OUTPUT_DIR="${CURRENT_PATH}/data/temp/network_traces"
SETNETWORK_DIR="${CURRENT_PATH}/code/setconfig"
# Check if the output directory exists, if not, create it
if [ ! -d "$OUTPUT_DIR" ]; then
    mkdir -p "$OUTPUT_DIR"
fi

# Function to generate network trace
generate_trace() {
    local trace_type=$1
    local downlink=$2
    local uplink=$3
    local output_file=$4
    local patterns=$5

    python3 set_network_trace.py \
        --type "$trace_type" --downlink "$downlink" --uplink "$uplink" \
        --output "$output_file" --patterns "$patterns"
}

# Example usage of the function
# You can modify the parameters as needed
trace_type="video"
downlink='{"trace_pattern": []}'
uplink='{"trace_pattern": []}'

# Array of different patterns configurations
patterns_array=(
    "60000,100000,0,0,0"
    # "60000,400,0,0,0"
    # "60000,1000,0,0,0"
    # "60000,2000,0,0,0"
    # "60000,1000,2,0,0"
    # "60000,1000,5,0,0"
    # "60000,1000,10,0,0"
    # "60000,1000,20,0,0"
    # "60000,1000,0,50,0"
    # "60000,1000,0,100,0"
    # "60000,1000,0,200,0"
    # "60000,1000,0,400,0"
    # "60000,1000,0,1000,0"
    # "60000,100,0,0,0 60000,400,0,0,0"
    # "60000,100,0,0,0 60000,1000,0,0,0"
    # "60000,100,0,0,0 60000,2000,0,0,0"
    # "60000,400,0,0,0 60000,1000,0,0,0"
    # "60000,400,0,0,0 60000,2000,0,0,0"
    # "60000,1000,0,0,0 60000,2000,0,0,0"
)

rm -rf "$OUTPUT_DIR"/*
cd $SETNETWORK_DIR
# Loop to generate multiple traces with different patterns
for i in {1..1}; do
    output_file="$OUTPUT_DIR/trace_$i.json"
    patterns="${patterns_array[$((i-1))]}"
    echo "Generating trace $i with patterns: $patterns..."
    if ! generate_trace "$trace_type" "$downlink" "$uplink" "$output_file" "$patterns"; then
        echo "Error generating trace $i" >&2
    else
        echo "Trace $i generated successfully"
    fi
done