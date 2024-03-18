#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from datetime import datetime
import glob
import os
import random
import subprocess
import psutil

emu_gym_path = os.path.expandvars('$EMU_GYM_PATH')


def parse_args():
    parser = argparse.ArgumentParser(description='Emulator-based evaluation of GCC')

    parser.add_argument('--trace-type', type=str, default='belgium', choices=['belgium', 'fcc', 'norway', 'belgium+fcc', 'belgium+norway', 'fcc+norway', 'belgium+fcc+norway', 'simple'],
                        help='Type of mahimahi trace set to use in training')
    parser.add_argument('--num-traces', type=int, default=1,
                        help='Number of traces to run')
    return parser.parse_args()


def cleanup():
    for f in glob.glob("*.log"):
        os.remove(f)


'''
Generate a random free tcp6 port.
Goal: dynamically binding an unused port for e2e call
'''
def generate_random_port():
    MIN_PORT = 1024
    MAX_PORT = 65535

    used_ports = []
    free_port = -1

    out = subprocess.check_output('netstat -tnlp | grep tcp6', shell=True)
    lines = out.decode("utf-8").split("\n")
    # Figure out all the used ports
    for line in lines:
        # Proto    Recv-Q    Send-Q    Local Address    Foreign Address    State    PID/Program name
        line_elements = line.split()
        if len(line_elements) > 4:
            local_address = line.split()[3] # e.g., ::1:39673 :::22
            port = int(local_address.split(':')[-1])
            used_ports.append(port)

    while(free_port < 0 or free_port in used_ports):
        free_port = random.randint(MIN_PORT, MAX_PORT)

    # Write the free port to the designated port file
    with open(f'{emu_gym_path}/port.txt', "w") as out:
        out.write(str(free_port))


def get_traces(trace_type):
    traces = []
    simple_trace = [f'{emu_gym_path}/traces/6mbps']
    belgium_traces = sorted(glob.glob(f'{emu_gym_path}/traces/eval/belgium_eval/*'))
    fcc_traces = sorted(glob.glob(f'{emu_gym_path}/traces/eval/fcc_eval/*'))
    norway_traces = sorted(glob.glob(f'{emu_gym_path}/traces/eval/norway_eval/*'))

    if trace_type == 'simple':
        traces = simple_trace
    elif trace_type == 'belgium':
        traces = belgium_traces
    elif trace_type == 'fcc':
        traces = fcc_traces
    elif trace_type == 'norway':
        traces = norway_traces
    elif trace_type == 'belgium+fcc':
        traces = belgium_traces + fcc_traces
        random.shuffle(traces)
    elif trace_type == 'belgium+norway':
        traces = belgium_traces + norway_traces
        random.shuffle(traces)
    elif trace_type == 'fcc+norway':
        traces = fcc_traces + norway_traces
        random.shuffle(traces)
    elif trace_type == 'belgium+fcc+norway':
        traces = fcc_traces + norway_traces + belgium_traces
        random.shuffle(traces)
    else:
        print(f'Unsupported trace type {trace_type}')

    print(f'Traces {trace_type} {traces}')
    return traces


def get_dest_ip():
    return os.popen('ifconfig | grep 147').read().strip().split()[1]

def kill_call(receiver_app, sender_app):
    for c in [receiver_app, sender_app]:
        process = psutil.Process(c.pid)
        for proc in process.children(recursive=True):
            proc.kill()
        process.kill()


def main(args):
    cleanup()

    traces = get_traces(args.trace_type)
    trace_idx = 0

    while trace_idx < args.num_traces:
        fin_status = 'SUCCESS'
        trace_file = traces[trace_idx]

        date_time_ymdhms = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        receiver_log = f'{emu_gym_path}/logs/GCC-receiver-log-{args.trace_type}-{date_time_ymdhms}.log'
        sender_log = f'{emu_gym_path}/logs/GCC-sender-log-{args.trace_type}-{date_time_ymdhms}.log'
        receiver_config = f'{emu_gym_path}/receiver_pyinfer.json'
        sender_config = f'{emu_gym_path}/sender_pyinfer.json'
        call_app = f'{emu_gym_path}/peerconnection_serverless.gcc'

        # Randomly assign different port for this video call
        generate_random_port()

        # Run the video call (env) in separate processes
        dest_ip = get_dest_ip()
        receiver_cmd = f"{call_app} {receiver_config} {dest_ip} port.txt {receiver_log}"
        sender_cmd = f"sleep 5; mm-link {trace_file} {trace_file} {call_app} {sender_config} {dest_ip} port.txt {sender_log}"

        receiver_app = subprocess.Popen(receiver_cmd, shell=True)
        sender_app = subprocess.Popen(sender_cmd, shell=True)

        try:
            receiver_app.wait(timeout=40)
            sender_app.wait(timeout=40)
        except:
            kill_call(receiver_app, sender_app)
            fin_status = 'TIMEOUT'

        trace_idx += 1

        print(f'[GCC] (trace {trace_file}) ended, status: {fin_status}')


if __name__ == "__main__":
    args = parse_args()
    main(args)
