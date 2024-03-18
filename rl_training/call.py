from datetime import datetime
import glob
import os
import random
import subprocess
import psutil

# trace type
# - static capacity: min, max
# - fluctuating capacity: fluctuation magnitude

class Call:
    def __init__(self, mode, is_gcc, trace_type, video_res):
        self.emu_gym_path = os.path.expandvars('$EMU_GYM_PATH')
        self.mode=mode
        self.is_gcc=is_gcc
        self.traces = self.get_traces(trace_type)
        self.trace_idx = 0
        self.receiver_app = None
        self.sender_app = None
        self.ports = self._generate_random_port()
        self.port_idx = 0
        self.video_res = video_res

    def get_video_res(self):
        return self.video_res

    def static_capacity(self, bw):
        # static BW 내놓는 mahimahi trace 만들어 리턴
        pass

    def fluct_capacity(self):
        pass

    def get_traces(self, trace_type):
        traces = []
        simple_trace = [f'{self.emu_gym_path}/rl_training/traces/300kbps']
        belgium_traces = sorted(glob.glob(f'{self.emu_gym_path}/rl_training/traces/{self.mode}/belgium_{self.mode}/*'))
        fcc_traces = sorted(glob.glob(f'{self.emu_gym_path}/rl_training/traces/{self.mode}/fcc_{self.mode}/*'))
        norway_traces = sorted(glob.glob(f'{self.emu_gym_path}/rl_training/traces/{self.mode}/norway_{self.mode}/*'))

        trace_type = trace_type

        # if trace_type == 'static':
        #     bw = trace_config['capacity']
        #     traces = self.static_capacity(bw)
        # if trace_type == 'fluct':
        #     traces = self.fluct_capacity()
        #     bw_fluct_dur = trace_config['capacity']['duration']
        #     bw_min = trace_config['capacity']['min']
        #     bw_max = trace_config['capacity']['max']
        #     bw_fluct = trace_config['capacity']['fluctuation']
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
            # random.shuffle(traces)
        elif trace_type == 'belgium+norway':
            traces = belgium_traces + norway_traces
            # random.shuffle(traces)
        elif trace_type == 'fcc+norway':
            traces = fcc_traces + norway_traces
            # random.shuffle(traces)
        elif trace_type == 'belgium+fcc+norway':
            traces = fcc_traces + norway_traces + belgium_traces
            # random.shuffle(traces)
        else:
            print(f'Unsupported trace type {trace_type}')

        # print(f'Traces {traces}')
        return traces


    '''
    Generate a random free tcp6 port.
    Goal: dynamically binding an unused port for e2e call
    '''
    def _generate_random_port(self):
        MIN_PORT = 1024
        MAX_PORT = 65535

        used_ports = []
        free_ports = []

        # Figure out all the used ports
        out = subprocess.check_output('netstat -tnlp | grep tcp6', shell=True)
        lines = out.decode("utf-8").split("\n")
        for line in lines:
            # Proto    Recv-Q    Send-Q    Local Address    Foreign Address    State    PID/Program name
            line_elements = line.split()
            if len(line_elements) > 4:
                local_address = line.split()[3] # e.g., ::1:39673 :::22
                port = int(local_address.split(':')[-1])
                used_ports.append(port)

        # 10 randomly selected free ports
        while len(free_ports) <= 10:
            free_port = random.randint(MIN_PORT, MAX_PORT)
            if free_port not in used_ports:
                free_ports.append(free_port)

        return free_ports


    # For each call, assign one of the 10 free ports by iterating `self.ports`
    def _select_port(self):
        free_port = self.ports[self.port_idx]
        print(f'EPISODE: Selected {free_port} among {self.ports}')
        # Write the free port to the designated port file
        with open(f'{self.emu_gym_path}/port.txt', "w") as out:
            out.write(str(free_port))
        self.port_idx += 1
        self.port_idx = self.port_idx % 10


    def _get_dest_ip(self):
        return os.popen('ifconfig | grep 147').read().strip().split()[1]


    # Create and run a single call.
    # We do sequential training of multiple traces, e.g. for trace 0~N, we run
    # call with trace 0 -> call with trace 1 -> ... -> call N -> call 0 -> ...
    def create_and_run_call(self):
        receiver_config = f'{self.emu_gym_path}/receiver_{self.video_res}.json'
        sender_config = f'{self.emu_gym_path}/sender_{self.video_res}.json'
        # if self.is_gcc:
        #     call_app = f'{self.emu_gym_path}/peerconnection_serverless.gcc'
        # else:
        #     call_app = f'{self.emu_gym_path}/peerconnection_serverless.origin'
        call_app = f'{self.emu_gym_path}/peerconnection_serverless.r3net'
        # Randomly assign different port for this video call
        self._select_port()

        # trace_file = self.traces[self.trace_idx % len(self.traces)]
        # self.trace_idx += 1
        loss = 0.0
        self.trace_idx = 0

        trace_file = self.traces[self.trace_idx]
        print(f'Trace to run idx {self.trace_idx} {trace_file}')

        # Run the video call (env) in separate processes
        dest_ip = self._get_dest_ip()
        receiver_cmd = f"{call_app} {receiver_config} {dest_ip} port.txt receiver.log"
        # sender_cmd = f"sleep 3; mm-loss uplink {loss} mm-link {trace_file} {trace_file} {call_app} {sender_config} {dest_ip} port.txt sender.log"
        sender_cmd = f"sleep 3; mm-link {trace_file} {trace_file} {call_app} {sender_config} {dest_ip} port.txt sender.log"

        # self.receiver_app = subprocess.Popen(receiver_cmd, shell=True)
        # self.sender_app = subprocess.Popen(sender_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

        self.receiver_app = subprocess.Popen(receiver_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
        self.sender_app = subprocess.Popen(sender_cmd, shell=True)

        return self.receiver_app, self.sender_app, trace_file, self.trace_idx, loss


    def kill_call(self):
        for app in [self.sender_app, self.receiver_app]:
            try:
                process = psutil.Process(app.pid)
            except psutil.NoSuchProcess:
                pass
            else:
                for proc in process.children(recursive=True):
                    proc.kill()
                process.kill()


def main():
    call = Call(mode='train', trace_type='fcc+norway')

if __name__ == '__main__':
    main()