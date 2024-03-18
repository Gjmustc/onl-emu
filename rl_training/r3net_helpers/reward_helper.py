import numpy as np
from rl_training.packet_record import PacketRecord

class RewardHelper:
    def __init__(self, step_time=60):
        self.packet_record = PacketRecord()
        self.step_time = step_time

    def __call__(self, packet_infos, bwe, env_info):
        """Transform per packet information into reward.
        Accepts per packet information and returns a tuple of (reward, info).
        Args:
            packet_infos (list of PacketInfo): per packet information
        Returns:
            reward (float) : amount of reward returned after previous action
            info (dict): contains auxiliary diagnostic information
                         (helpful for debugging, and sometimes learning)
        """
        for packet in packet_infos:
            self.packet_record.on_receive(packet)

        receiving_rate = self.packet_record.calculate_receiving_rate(self.step_time * 10)
        if env_info['loss'] == 1:
            r_reward = 0
        else:
            # recv_thp / (1-loss rate) / link capacity_bps 안되니까 recv_thp / (1-loss rate) / latest bwe
            # r_reward = receiving_rate / (1 - env_info['loss']) / (env_info['capacity'] * 1000)
            r_reward = receiving_rate / (1 - env_info['loss']) / bwe
            r_reward = np.clip(r_reward, 0, 1)

        delay = self.packet_record.calculate_average_delay(self.step_time * 10)
        # delay/1000 - (delay-min delay)/2000
        # d_reward = np.clip(delay / 1000 - env_info['relative_rtt'] / 2000, 0, 1)
        d_reward = np.clip(delay / 1000, 0, 1)
        d_reward = np.clip(d_reward, 0, 1)

        loss_ratio = self.packet_record.calculate_loss_ratio(self.step_time * 10)
        l_reward = np.clip(loss_ratio, 0, 1)

        # s_reward = 0
        # if self.previous_action is not None:
        #     s_reward = abs(action - self.previous_action)
        # self.previous_action = action
        # s_reward = np.clip(s_reward, 0, 1)

        reward = r_reward - d_reward - l_reward
        # reward = np.clip(reward, -1, 1)
        info = {
            'r_reward': r_reward,
            'd_reward': d_reward,
            'l_reward': l_reward,
            'reward': reward
        }
        return reward, info

    def reset(self):
        """Resets the state of the reward helper.
        No returns.
        """
        self.packet_record.reset()
        self.previous_action = None