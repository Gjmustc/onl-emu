from gymnasium.spaces import Box
import numpy as np
from rl_training.packet_record import PacketRecord
from rl_training.config import liner_to_log

class StateHelper:
    def __init__(self, step_time=60, record_dim=5):
        self.record_dim = record_dim
        self.state_dim = record_dim * 7
        self.state_record = None

        self.observation_space = Box(
            low=np.zeros(self.state_dim, dtype=np.float64),
            high=np.ones(self.state_dim, dtype=np.float64),
            dtype=np.float64)

        self.packet_record = PacketRecord()
        self.step_time = step_time

    def __call__(self, packet_infos, action):
        """Transform per packet information into observation.
        Accepts per packet info and returns a tuple of (observation, info).
        Args:
            packet_infos (list of PacketInfo): per packet information
        Returns:
            observation (object): agent's observation of the current env
            info (dict): contains auxiliary diagnostic information
                         (helpful for debugging, and sometimes learning)
        """
        for packet in packet_infos:
            self.packet_record.on_receive(packet)

        # print(f'action {action}')
        if type(action) != float:
            action = action[0]
        new_state = {
            'action': action,
            'receiving_rate': liner_to_log(self.packet_record.calculate_receiving_rate(self.step_time)),
            'longterm_receiving_rate': liner_to_log(self.packet_record.calculate_receiving_rate(self.step_time * 10)),
            'delay': min(1, self.packet_record.calculate_average_delay(self.step_time) / 1000),
            'longterm_delay': min(1, self.packet_record.calculate_average_delay(self.step_time * 10) / 1000),
            'loss_ratio': self.packet_record.calculate_loss_ratio(self.step_time),
            'longterm_loss_ratio': self.packet_record.calculate_loss_ratio(self.step_time * 10)
        }

        self.update_state(new_state)
        states_info = {
            'receiving_rate': self.packet_record.calculate_receiving_rate(self.step_time * 10), # bps
            'delay': self.packet_record.calculate_average_delay(self.step_time * 10), # ms
            'loss_ratio': self.packet_record.calculate_loss_ratio(self.step_time * 10)
        }
        return self.flatten_state(), states_info

    def reset(self):
        """Resets the state of the state helper and returns an initial obsersvation.
        Returns:
            observation (object): the initial observation.
        """
        self.packet_record.reset()
        self.state_record = {
            'action': [],
            'receiving_rate': [],
            'longterm_receiving_rate': [],
            'delay': [],
            'longterm_delay': [],
            'loss_ratio': [],
            'longterm_loss_ratio': [],
        }
        for key in self.state_record:
            for _ in range(self.record_dim):
                self.state_record[key].append(0)

        return self.flatten_state()

    def flatten_state(self):
        # print(self.state_record)
        l = [value for key in self.state_record for value in self.state_record[key]]
        # print(f'{l[0]}')
        if isinstance(l[0], np.ndarray):
            l[0] = l[0][0]
            # print(f'{l[0]}')
        # print(f'{l}')
        return np.array(l)
        # return np.array([value for key in self.state_record for value in self.state_record[key]])

    def update_state(self, new_state):
        for key in self.state_record:
            assert key in new_state
            self.state_record[key] =  [new_state[key]] + self.state_record[key][:-1]