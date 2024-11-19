import json
import subprocess
import time
from datetime import datetime
import argparse

INTERFACE = "lo"  # Apply traffic control on the loopback interface

def current_time():
    """Returns the current time as a formatted string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def apply_network_config(config):
    duration_ms = config.get("duration", 60000)  # Duration in ms, defaulting to 60000 ms (60 seconds)
    capacity = config.get("capacity", 1000) / 1000  # Convert to Mbit
    loss = config.get("loss", 0)
    rtt = config.get("rtt", 0) / 2
    jitter = config.get("jitter", 0)

    print(f"{current_time()} - Applying: capacity={capacity}Mbit, loss={loss}%, rtt={rtt}ms, jitter={jitter}ms for {duration_ms}ms")

    # Delete any existing configuration on the loopback interface, ignoring errors if none exists
    del_command = f"sudo tc qdisc del dev {INTERFACE} root"
    print(f"{current_time()} - Executing: {del_command}")
    subprocess.run(del_command, shell=True, stderr=subprocess.DEVNULL)

    # Apply a netem qdisc directly with rate limiting, delay, and loss on the loopback interface
    netem_command = f"sudo tc qdisc add dev {INTERFACE} root netem rate {capacity}Mbit"

    # Add delay and jitter if specified
    if rtt > 0:
        netem_command += f" delay {rtt}ms"
        if jitter > 0:
            netem_command += f" {jitter}ms distribution normal"
    
    # Add packet loss if specified
    if loss > 0:
        netem_command += f" loss {loss}%"

    print(f"{current_time()} - Executing: {netem_command}")
    subprocess.run(netem_command, shell=True)

    # Maintain the configuration for the specified duration in milliseconds
    time.sleep(duration_ms / 1000)

    # Clear the configuration after the duration, ignoring errors if there's no existing qdisc
    print(f"{current_time()} - Executing: {del_command}")
    subprocess.run(del_command, shell=True, stderr=subprocess.DEVNULL)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Apply network configuration from a JSON file.")
    parser.add_argument("--config", type=str, required=True, help="Path to the JSON configuration file")
    args = parser.parse_args()

    # Path to the configuration file
    CONFIG_FILE = args.config
    # Load JSON configuration
    with open(CONFIG_FILE, 'r') as f:
        config_data = json.load(f)
    
    # Get the trace_pattern list
    trace_patterns = config_data.get("uplink", {}).get("trace_pattern", [])

    # Loop through the configuration patterns
    while True:
        for config in trace_patterns:
            apply_network_config(config)

if __name__ == "__main__":
    main()

