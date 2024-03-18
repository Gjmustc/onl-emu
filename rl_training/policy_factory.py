import glob
import time
import logging

from stable_baselines3 import PPO, A2C, DQN, TD3, SAC

_logger = logging.getLogger(__name__)

class PolicyFactory:
    def __init__(self):
        self.policy = None


    def _create_a2c_policy(self, env, ckpt):
        if ckpt is not None:
            self.policy = A2C.load(ckpt, env=env)
        else:
            self.policy = A2C("MlpPolicy", env=env, device='cpu', verbose=1)


    def _create_ppo_policy(self, env, ckpt):
        if ckpt is not None:
            print(f'CKPT {ckpt}')
            self.policy = PPO.load(ckpt, env=env)
        else:
            self.policy = PPO("MlpPolicy", env=env, device='cpu', verbose=1)


    def _create_dqn_policy(self, env, ckpt):
        if ckpt is not None:
            self.policy = DQN.load(ckpt, env=env)
        else:
            self.policy = DQN("MlpPolicy", env=env, device='cpu', verbose=1)


    def _create_td3_policy(self, env, ckpt):
        if ckpt is not None:
            self.policy = TD3.load(ckpt, env=env)
        else:
            self.policy = TD3("MlpPolicy", env=env, device='cpu', verbose=1)


    def _create_sac_policy(self, env, ckpt):
        if ckpt is not None:
            self.policy = SAC.load(ckpt, env=env)
        else:
            self.policy = SAC("MlpPolicy", env=env, device='cpu', verbose=1)


    # Factory method that returns a requested RL algorithm-based policy
    def _create_policy(self, env, rl_algo='PPO', ckpt=None):
        if rl_algo == 'A2C':
            self._create_a2c_policy(env, ckpt)
        elif rl_algo == 'PPO':
            self._create_ppo_policy(env, ckpt)
        elif rl_algo == 'DQN':
            self._create_dqn_policy(env, ckpt)
        elif rl_algo == 'TD3':
            self._create_td3_policy(env, ckpt)
        elif rl_algo == 'SAC':
            self._create_sac_policy(env, ckpt)
        else:
            raise ValueError(f'{rl_algo} is not supported')


    # A wrapper of the factory method that adds exception handling
    def create_policy(self, env, rl_algo, ckpt=None):
        try:
            self._create_policy(env, rl_algo, ckpt)
            return self.policy
        except ValueError as e:
            print(f'PolicyFactory Error: {e}')
        return None