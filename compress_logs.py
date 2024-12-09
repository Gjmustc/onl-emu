import re
import sys
import argparse
import os

def compress_logs(log_file, patterns, output_path):
    patterns = [re.compile(pattern) for pattern in patterns]
    if os.path.exists(output_path):
        os.remove(output_path)
    with open(output_path, 'w') as outfile:
        with open(log_file, 'r') as infile:
            for line in infile:
                for pattern in patterns:
                    match = pattern.search(line)
                    if match:
                        outfile.write(line)
                        break

def get_output_path(input_path, base_input_dir, base_output_dir):
    relative_path = os.path.relpath(input_path, base_input_dir)
    return os.path.join(base_output_dir, relative_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process and compress log files.')
    parser.add_argument('--receiver_log', type=str, required=True, help='receiver log file path')
    parser.add_argument('--sender_log', type=str, required=True, help='sender log file path')
    parser.add_argument('--receiver_patterns', type=lambda s: [p for p in s.split('|') if p], help='pipe-separated list of receiver log regex patterns')
    parser.add_argument('--sender_patterns', type=lambda s: [p for p in s.split('|') if p], help='pipe-separated list of sender log regex patterns')
    parser.add_argument('--base_input_dir', type=str, required=True, help='Base input directory')
    parser.add_argument('--base_output_dir', type=str, required=True, help='Base output directory')

    args = parser.parse_args()

    receiver_log = args.receiver_log
    sender_log = args.sender_log
    receiver_patterns = args.receiver_patterns
    sender_patterns = args.sender_patterns
    base_input_dir = args.base_input_dir
    base_output_dir = args.base_output_dir

    output_path = get_output_path(receiver_log, base_input_dir, base_output_dir)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    compress_logs(receiver_log, receiver_patterns, output_path)

    output_path = get_output_path(sender_log, base_input_dir, base_output_dir)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    compress_logs(sender_log, sender_patterns, output_path)
