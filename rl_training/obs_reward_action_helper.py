import torch
import numpy as np


class ObsRewardActionHelper:
    def __init__(self, min_kbps, max_kbps, history_len, discrete_action_space_type, rtt_coeff):
        # Calculate a state with an average of stats from the latest 10 RTCP packets
        self.min_kbps = min_kbps
        self.max_kbps = max_kbps
        self.unit_k = 1000
        self.unit_m = 1000 * 1000
        self.history_len = history_len
        self.reward_formula_str = ''
        self.rtt_coeff = rtt_coeff
        self.discrete_action_space = self.init_discrete_action_space(discrete_action_space_type)


    def init_discrete_action_space(self, option):
        action_space = []
        if option == 'onrl':
            comdiff = 100 * self.unit_k # 100Kbps = 0.1Mbps
            for i in range(1, 26):
                # 0.1Mbps to 2.5Mbps
                action_space.append(i * comdiff)
        elif option == 'loki':
            comdiff = 130 * self.unit_k # 130Kbps = 0.13Mbps
            min_bps = 0.1 * self.unit_m
            for i in range(0, 23):
                # 0.1Mbps to 2.96Mbps
                action_space.append(min_bps + i * comdiff)
        else:
            print(f'Unsupported action space option {option}')

        print(f'Action space {action_space}')
        return action_space


    '''
    Compute obs and reward
    '''

    # Calulate average of latest history_len number of receiver-side throughputs (bps),
    # RTTs (ms) and loss rates (0-1).
    def calculate_obs(self, packet_record):
        loss_rate = self.zero_padding(packet_record.packet_stats_dict['loss_rate'])
        norm_rtt = self.zero_padding(packet_record.packet_stats_dict['norm_rtt'])
        norm_recv_thp = self.zero_padding(packet_record.packet_stats_dict['norm_recv_thp'])
        obs = [loss_rate, norm_rtt, norm_recv_thp]
        # 2-D tensor
        obs_tensor = torch.unsqueeze(torch.as_tensor(np.array(obs), device='cpu'), 0)
        return obs_tensor


    # Incentivize increase in receiver-side thp,
    # penalize increase in loss, RTT, and thp fluctuation.
    # Following the reward design of Loki.
    def calculate_reward(self, packet_record):
        loss_rate = sum(packet_record.packet_stats_dict['loss_rate'])
        norm_rtt = sum(packet_record.packet_stats_dict['norm_rtt'])
        norm_recv_thp = sum(packet_record.packet_stats_dict['norm_recv_thp'])
        norm_recv_thp_fluct = sum(packet_record.packet_stats_dict['norm_recv_thp_fluct'])
        reward = norm_recv_thp - norm_rtt
        self.reward_formula_str = f'{reward:.4f} = {norm_recv_thp:.4f} - {norm_rtt:.4f}'
        # if norm_rtt > 0:
        #     reward = 5 * norm_recv_thp/norm_rtt - 0.5 * norm_recv_thp_fluct
        # else:
        #     reward = 5 * norm_recv_thp - 0.5 * norm_recv_thp_fluct
        # self.reward_formula_str = f'{reward:.4f} = 5 * {norm_recv_thp:.4f}/{norm_rtt:.4f} - 0.5 * {norm_recv_thp_fluct}'
        return reward, self.reward_formula_str

    def zero_padding(self, q):
        if len(q) < self.history_len:
            num_stats = len(q)
            num_zero_padded_elems = self.history_len - num_stats
            for _ in range(0, num_zero_padded_elems):
                q.append(0.0)

        return list(q)


    '''
    Helper methods for action
    '''

    # Referred to https://stats.stackexchange.com/questions/178626/how-to-normalize-data-between-1-and-1
    def rescale_action_continuous(self, norm_action_kbps):
        rescaled_action_bps = ((self.max_kbps - self.min_kbps) * (norm_action_kbps + 1) / 2 + self.min_kbps) * self.unit_k
        print(f'Action: (-1~1) {norm_action_kbps} to ({self.min_kbps}Kbps-{self.max_kbps}Kbps) {rescaled_action_bps}')
        if type(rescaled_action_bps) is list or isinstance(rescaled_action_bps, np.ndarray):
            rescaled_action_bps = rescaled_action_bps[0]

        return rescaled_action_bps


    def get_discrete_action(self, action_idx):
        return self.discrete_action_space[action_idx]
