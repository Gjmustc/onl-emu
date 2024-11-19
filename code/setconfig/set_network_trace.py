import json
import argparse

class NetworkTraceConfig:
    def __init__(self, trace_type, downlink, uplink):
        self.config = {
            "type": trace_type,
            "downlink": downlink,
            "uplink": uplink
        }

    def add_uplink_trace_pattern(self, duration, capacity, loss, rtt, jitter):
        pattern = {
            "duration": duration,
            "capacity": capacity,
            "loss": loss,
            "rtt": rtt,
            "jitter": jitter
        }
        self.config["uplink"]["trace_pattern"].append(pattern)

    def add_downlink_trace_pattern(self, duration, capacity, loss, rtt, jitter):
        pattern = {
            "duration": duration,
            "capacity": capacity,
            "loss": loss,
            "rtt": rtt,
            "jitter": jitter
        }
        self.config["downlink"]["trace_pattern"].append(pattern)
    
    def save_to_file(self, file_path):
        with open(file_path, 'w') as file:
            json.dump(self.config, file, indent=4)

def parse_args():
    parser = argparse.ArgumentParser(description='Generate network trace config JSON file.')
    parser.add_argument('--type', required=True, help='Type of the network trace')
    parser.add_argument('--downlink', default='{"trace_pattern": []}', type=json.loads, help='Downlink configuration in JSON format')
    parser.add_argument('--uplink', default='{"trace_pattern": []}', type=json.loads, help='Uplink configuration in JSON format')
    parser.add_argument('--output', required=True, help='Output file path')
    parser.add_argument('--patterns', nargs='+', help='Trace patterns in the format duration,capacity,loss,rtt,jitter')

    return parser.parse_args()

def main():
    args = parse_args()
    config = NetworkTraceConfig(args.type, args.downlink, args.uplink)

    if args.patterns:
        for pattern in args.patterns:
            for p in pattern.split():
                duration, capacity, loss, rtt, jitter = map(int, p.split(','))
                config.add_uplink_trace_pattern(duration, capacity, loss, rtt, jitter)

    config.save_to_file(args.output)

if __name__ == '__main__':
    main()
    
    