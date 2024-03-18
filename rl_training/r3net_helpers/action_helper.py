import numpy as np
from gymnasium.spaces import Box
from .config import MIN_ACTION, MAX_ACTION, log_to_linear

class ActionHelper:
    def __init__(self):
        self.action_space = Box(low=float(MIN_ACTION),
                                       high=float(MAX_ACTION),
                                       shape=(1,),
                                       dtype=np.float64)

    def __call__(self, raw_action):
        """Transform model's raw action to bandwidth prediction (in bps).
        Accepts a raw action and returns a tuple of (action, info).
        Args:
            raw_action (object): an action provided by the agent.
        Returns:
            action (int): predicted bandwidth in bps.
            info (dict): contains auxiliary diagnostic information
                         (helpful for debugging, and sometimes learning)
        """
        bandwidth_prediction = log_to_linear(raw_action)
        # print(f'raw action {raw_action} bandwidth prediction {bandwidth_prediction}')
        return bandwidth_prediction, {"bandwidth_prediction": bandwidth_prediction[0]}

    def reset(self):
        """Resets the state of the action helper.
        No returns.
        """
        pass