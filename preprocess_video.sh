#!/bin/bash

# Function to display usage instructions
usage() {
    echo "Usage: $0 -i input_file -s start_frame -e end_frame -w width -h height -n frame_number_size -x x_offset -y y_offset -o output_file"
    exit 1
}

# Default values
start_frame=0
end_frame=100
width=1920
height=1080
frame_number_size=48
x_offset=50
y_offset=50

# Parse command line arguments
while getopts "i:s:e:w:h:n:x:y:o:" opt; do
    case $opt in
        i) input_file=$OPTARG ;;
        s) start_frame=$OPTARG ;;
        e) end_frame=$OPTARG ;;
        w) width=$OPTARG ;;
        h) height=$OPTARG ;;
        n) frame_number_size=$OPTARG ;;
        x) x_offset=$OPTARG ;;
        y) y_offset=$OPTARG ;;
        o) output_file=$OPTARG ;;
        *) usage ;;
    esac
done

# Check if input_file and output_file are provided
if [ -z "$input_file" ] || [ -z "$output_file" ]; then
    usage
fi

# Extract the video segment and convert to yuv format
ffmpeg -i "$input_file" \
    -vf "select='between(n,$start_frame,$end_frame)',scale=$width:$height" \
    -vsync 0  -f rawvideo temp.yuv

# Add frame numbers to the extracted frames
ffmpeg -f rawvideo -pixel_format yuv420p -video_size ${width}x${height} \
    -i temp.yuv \
    -vf "drawtext=text='%{n}':x=(w/2-${x_offset}):y=(h-${y_offset}):fontsize=${frame_number_size}:fontcolor=black:box=1:boxcolor=white@1:boxborderw=15" \
    -c:v rawvideo -pix_fmt yuv420p "$output_file"

# Clear temporary files
rm temp.yuv
echo "Processing complete. Output saved to ${output_file}_numbered.yuv"