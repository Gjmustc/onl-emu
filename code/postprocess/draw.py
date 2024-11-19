import argparse
import re
import matplotlib.pyplot as plt
import os
import json
from collections import defaultdict
import itertools

def process_receiver_log(log_file, patterns, bitrate_interval=1000, loss_interval=1, delay_interval=20, first_delay_=200):

    bitrate = defaultdict(float)
    lossrate = defaultdict(float)
    delay = defaultdict(float)
    time_delta = defaultdict(float)
    payload_size_dict = defaultdict(int)
    
    first_packet_ = True
    first_packet_timestamp = 0
    loss_util_count = loss_interval
    ed_packet_arrivaltime = 0
    st_packet_sequencenum = 0
    ed_packet_sequencenum = 0
    first_packet_timediff = 0
    delay_util_count = delay_interval
    delay_cumulative = 0
    last_time = 0
    with open(log_file, 'r') as file:
        for line in file:
            for pattern in patterns:
                match = pattern.search(line)
                if match:
                    if pattern == patterns[0]:
                        # print("Matched receiver pattern 1")
                        log_dict = json.loads(match.group(1))
                        packet_info = log_dict.get('packetInfo',{})
                        arrival_time = packet_info.get('arrivalTimeMs',0)
                        payload_size = packet_info.get('payloadSize',0)
                        seqnum = packet_info.get('header').get('sequenceNumber', 0)
                        sendtime_stamp = packet_info.get('header').get('sendTimestamp', 0)
                        
                        loss_util_count -= 1
                        delay_util_count -= 1
                        if first_packet_:
                            st_packet_sequencenum = seqnum
                            first_packet_timediff = arrival_time - sendtime_stamp
                            first_packet_timestamp = arrival_time
                            first_packet_ = False
                        if loss_util_count == loss_interval -1:
                            st_packet_sequencenum = seqnum
                        if loss_util_count == 0:
                            ed_packet_arrivaltime = arrival_time
                            ed_packet_sequencenum = seqnum
                            lossrate[ed_packet_arrivaltime - first_packet_timestamp] = (ed_packet_sequencenum - st_packet_sequencenum +1 - loss_interval)/(ed_packet_sequencenum - st_packet_sequencenum+1)*100
                            loss_util_count = loss_interval
                        delay_cumulative += (arrival_time - sendtime_stamp - first_packet_timediff + first_delay_)
                        if delay_util_count == 0:
                            delay[arrival_time - first_packet_timestamp] = delay_cumulative / delay_interval
                            delay_util_count = delay_interval
                            delay_cumulative = 0
                        if last_time != 0:
                            time_delta[(arrival_time - first_packet_timestamp)/1000] = arrival_time - last_time
                        last_time = arrival_time
                        payload_size_dict[(arrival_time - first_packet_timestamp)/bitrate_interval] = payload_size
                        bitrate[(arrival_time - first_packet_timestamp)//bitrate_interval] += payload_size * 8
                        
                    else:
                        print("Invalid pattern")
                        pass
    for key in bitrate:
        bitrate[key] /= 1e6
    return bitrate, lossrate, delay, time_delta, payload_size_dict

def process_sender_log(log_file, patterns, bwe_interval=1000, bitrate_interval=1000):
    bandwidth_estimate = defaultdict(float)
    bitrate = defaultdict(float)
    time_delta = defaultdict(float)
    resolution_vary = {}
    first_packet_pattern1 = True
    first_packet_pattern2 = True
    first_packet_timestamp_pattern1 = 0
    first_packet_timestamp_pattern2 = 0
    last_time = 0
    with open(log_file, 'r') as file:
        for line in file:
            for pattern in patterns:
                match = pattern.search(line)
                if match:
                    if pattern == patterns[0]:
                        # print("Matched sender pattern 1")
                        sendtime = float(match.group(2))
                        bandwidth = float(match.group(1))
                        if first_packet_pattern1:
                            first_packet_timestamp_pattern1 = sendtime
                            first_packet_pattern1 = False                            
                        bandwidth_estimate[(sendtime - first_packet_timestamp_pattern1)/bwe_interval] = bandwidth/1e6 # convert to Mbps and seconds
                    elif pattern == patterns[1]:
                        # print("Matched sender pattern 2")
                        seqnum = int(match.group(1))
                        sendtime = float(match.group(2))
                        send_payload_size = float(match.group(3))
                        if first_packet_pattern2:
                            first_packet_timestamp_pattern2 = sendtime
                            first_packet_pattern2 = False
                        bitrate[(sendtime - first_packet_timestamp_pattern2)//bitrate_interval] += send_payload_size*8
                        if last_time != 0:
                            time_delta[(sendtime - first_packet_timestamp_pattern2)/1000] = sendtime - last_time
                        last_time = sendtime
                    elif pattern == patterns[2]:
                        # print("Matched sender pattern 3")
                        resolution_vary[(int(match.group(3))-first_packet_timestamp_pattern2)/1000] = (int(match.group(1)), int(match.group(2)))
                    else:
                        print("Invalid pattern")
                        pass
        for key in bitrate:
            bitrate[key] /= 1e6                 
    return bandwidth_estimate, bitrate, time_delta, resolution_vary                  
                                
                        
def draw(   receive_bitrate,
            receive_lossrate,
            receive_delay,
            receive_time_delta,
            receive_payload_size,
            send_bandwidth_estimate,
            send_bitrate,
            send_time_delta,
            send_resolution_vary,
            log_path,
            output_path,
            receive_bitrate_interval=1000,
            send_bitrate_interval=1000,
            duration=30):
    modelname = log_path.split('/')[-2]
    network = log_path.split('/')[-3]
    videoname = log_path.split('/')[-4]
    
    receive_bitrate = dict(sorted(receive_bitrate.items()))
    receive_lossrate = dict(sorted(receive_lossrate.items()))
    receive_delay = dict(sorted(receive_delay.items()))
    receive_time_delta = dict(sorted(receive_time_delta.items()))
    receive_payload_size = dict(sorted(receive_payload_size.items()))
    send_bandwidth_estimate = dict(sorted(send_bandwidth_estimate.items()))
    send_bitrate = dict(sorted(send_bitrate.items()))
    send_time_delta = dict(sorted(send_time_delta.items()))
    send_resolution_vary = dict(sorted(send_resolution_vary.items()))
    
    print(f"Drawing plot for {log_path}")
    fig, axs = plt.subplots(4, 2, figsize=(25, 20))
    fig.suptitle('Video Streaming Analysis', fontsize=20)
    axs[0, 0].scatter(send_bandwidth_estimate.keys(), send_bandwidth_estimate.values(), marker='o', label=modelname)
    axs[0, 0].set_title('Bandwidth Estimate of '+ network + ' on '+ videoname)
    axs[0, 0].set_xlabel(f'Time / s')
    axs[0, 0].set_ylabel(f'Bandwidth Estimate / Mbps')
    axs[0, 1].plot(send_bitrate.keys(), send_bitrate.values(), marker='o', label=modelname+'-Send')
    axs[0, 1].plot(receive_bitrate.keys(), receive_bitrate.values(),marker='o', label=modelname+'-Receive')
    axs[0, 1].set_title('Bitrate of '+ network + ' on '+ videoname)
    axs[0, 1].set_xlabel(f'Time / {receive_bitrate_interval} ms')
    axs[0, 1].set_ylabel(f'Bitrate / Mbps')
    axs[1, 0].scatter(receive_lossrate.keys(), receive_lossrate.values(), marker='o', label=modelname)
    axs[1, 0].set_title('Receiving Loss Rate of '+ network + ' on '+ videoname)
    axs[1, 0].set_xlabel(f'Time / ms')
    axs[1, 0].set_ylabel(f'Receiving Loss Ratio / %')
    axs[1, 1].scatter(receive_delay.keys(), receive_delay.values(), marker='o', label=modelname)
    axs[1, 1].set_title('Receiving Delay of '+ network + ' on '+ videoname)
    axs[1, 1].set_xlabel(f'Time / ms')
    axs[1, 1].set_ylabel(f'Receiving Delay / ms')
    axs[2, 0].scatter(receive_time_delta.keys(), receive_time_delta.values(), marker='o', label=modelname)
    axs[2, 0].set_title('Receiving Time Delta of '+ network + ' on '+ videoname)
    axs[2, 0].set_xlabel(f'Time / s')
    axs[2, 0].set_ylabel(f'Packet receiving Time Delta / ms')
    axs[2, 1].scatter(send_time_delta.keys(), send_time_delta.values(), marker='o', label=modelname)
    axs[2, 1].set_title('Sending Time Delta of '+ network + ' on '+ videoname)
    axs[2, 1].set_xlabel(f'Time / s')
    axs[2, 1].set_ylabel(f'Packet sending Time Delta / ms')
    axs[3, 0].scatter(receive_payload_size.keys(), receive_payload_size.values(), marker='o', label=modelname)
    axs[3, 0].set_title('Receiving Payload Size of '+ network + ' on '+ videoname)
    axs[3, 0].set_xlabel(f'Time / s')
    axs[3, 0].set_ylabel(f'Receiving Payload Size / Bytes')
    send_resolution_vary_y = {time: resolution[1] for time, resolution in send_resolution_vary.items()}
    axs[3, 1].scatter(send_resolution_vary.keys(), send_resolution_vary_y.values(), marker='o', label=modelname)
    for time, resolution in send_resolution_vary.items():
        axs[3, 1].annotate(f'({resolution[0]},{resolution[1]})', (time, resolution[1]), textcoords="offset points", xytext=(0,10), ha='center')
    axs[3, 1].set_title('Sending Resolution Vary of '+ network + ' on '+ videoname)
    axs[3, 1].set_xlabel(f'Time / s')
    axs[3, 1].set_xlim(0, duration)
    
    axs[3, 1].yaxis.set_ticks(list(send_resolution_vary_y.values()))
    axs[3, 1].set_ylabel(f'Sending Resolution / px')
    
    for ax in axs.flat:
        ax.legend()
        ax.grid(True)
    plt.tight_layout()
    print(f"Saving plot to {output_path}")
    plt.savefig(output_path)
        
def get_output_path(input_path, base_input_dir, base_output_dir):
    relative_path = os.path.relpath(input_path, base_input_dir)
    return os.path.join(base_output_dir, relative_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process and draw figures for log files.')
    parser.add_argument('--receiver_log', type=str, required=True, help='receiver log file path')
    parser.add_argument('--sender_log', type=str, required=True, help='sender log file path')
    parser.add_argument('--receiver_patterns', type=lambda s: [p for p in s.split('|') if p], help='pipe-separated list of receiver log regex patterns')
    parser.add_argument('--sender_patterns', type=lambda s: [p for p in s.split('|') if p], help='pipe-separated list of sender log regex patterns')
    parser.add_argument('--base_input_dir', type=str, required=True, help='Base input directory')
    parser.add_argument('--base_output_dir', type=str, required=True, help='Base output directory')
    parser.add_argument('--duration', type=int, default=30, help='Duration of the video')
    parser.add_argument('--receive_bitrate_interval', type=int, default=1000, help='Interval of receive bitrate')
    parser.add_argument('--send_bitrate_interval', type=int, default=1000, help='Interval of send bitrate')
    parser.add_argument('--first_delay', type=int, default=200, help='First delay of the video')
    parser.add_argument('--loss_interval', type=int, default=1, help='Interval of loss rate')
    parser.add_argument('--delay_interval', type=int, default=20, help='Interval of delay')
    parser.add_argument('--verbose', action='store_true', help='Print verbose output')
    
    args = parser.parse_args()
    if args.verbose:
        print(f"processing logs")
    
    receiver_log = args.receiver_log
    sender_log = args.sender_log
    receiver_patterns = args.receiver_patterns
    sender_patterns = args.sender_patterns
    base_input_dir = args.base_input_dir
    base_output_dir = args.base_output_dir
    duration = args.duration
    receive_bitrate_interval = args.receive_bitrate_interval
    send_bitrate_interval = args.send_bitrate_interval
    first_delay = args.first_delay
    loss_interval = args.loss_interval
    delay_interval = args.delay_interval
    
    receiver_patterns = [re.compile(pattern) for pattern in receiver_patterns]
    sender_patterns = [re.compile(pattern) for pattern in sender_patterns]

    if receiver_log and sender_log:
        if args.verbose:
            print(f"Processing receiver log: {receiver_log} and sender log: {sender_log}")
        
        receive_bitrate, receive_lossrate, receive_delay, receive_time_delta, receive_payload_size = process_receiver_log(
            receiver_log, receiver_patterns, bitrate_interval=receive_bitrate_interval, loss_interval=loss_interval, delay_interval=delay_interval, first_delay_=first_delay)
        
        send_bandwidth_estimate, send_bitrate, send_time_delta, send_resolution_vary = process_sender_log(
            sender_log, sender_patterns, bwe_interval=send_bitrate_interval, bitrate_interval=send_bitrate_interval)
        
        output_path = get_output_path(receiver_log, base_input_dir, base_output_dir).replace('.log', '.png')
        draw(receive_bitrate, receive_lossrate, receive_delay, receive_time_delta, receive_payload_size,
             send_bandwidth_estimate, send_bitrate, send_time_delta, send_resolution_vary,
             receiver_log, output_path, receive_bitrate_interval, send_bitrate_interval, duration)
    else:
        if args.verbose:
            print(f"Skipping unmatched logs: receiver_log={receiver_log}, sender_log={sender_log}")