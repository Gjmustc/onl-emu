from datetime import datetime
import glob
import json
import os
import numpy as np
from gymnasium import Env
from gymnasium import spaces
import time

from rl_training.r3net_helpers.config import log_to_linear
from rl_training.packet_record import PacketRecord
from rl_training.r3net_helpers import ActionHelper, StateHelper, RewardHelper, PacketInfo
from rl_training.obs_reward_action_helper import ObsRewardActionHelper

import logging
LOG_FILE = os.path.join('/home/jeongyoon/onl-emu-gym/train.log')
logging.basicConfig(filename=LOG_FILE, level=logging.INFO)

RequestBandwidthCommand = "RequestBandwidth"


"""
Custom environment that follows OpenAI gym interface.
Must inherit from OpenAI Gym Class
and implement the following methods: step(), reset(), render(), close()
RTCEnv is a single environment that plays multiple video calls in parallel.
"""
class RTCEnv(Env):
    def __init__(self, mode, is_gcc, call, trace_type, \
        rl_algo, action_space_type, discrete_action_space_type, rtt_coeff, \
        total_episodes, ckpt_interval, ckpt_dir):
        super(RTCEnv, self).__init__()

        ### Training related
        # Set as process_interval_cnt_ in AlphaCC::OnProcessInterval
        # i.e. the number of packet stats received for the applied action
        self.emu_gym_path = os.path.expandvars('$EMU_GYM_PATH')
        self.mode = mode
        self.is_gcc=is_gcc
        self.history_len = 20
        self.kth_rollout_loop = 0
        self.num_timesteps = 0
        # Starts from 1 for logging :-)
        self.num_episodes = 1
        self.total_episodes = total_episodes
        self.ckpt_interval = ckpt_interval
        self.ckpt_dir = ckpt_dir
        self.trace_type = trace_type
        self.trace_file = None
        self.applied_action = -1
        self.applied_bwe = 0
        self.newly_computed_action = 0
        self.values = 0
        self.log_probs = 0
        # End of episode signal
        self.dones = np.zeros(1) # single env
        # For self.infos
        self.agg_episode_reward = 0.0
        self.episode_rewards = []
        self.norm_episode_rewards = []
        self.episode_len = 0
        self.infos = [{'episode': {'r': 0, 'l': 0}}] # List[Dict[str, Any]]
        self.packet_record = PacketRecord(min_kbps=100, max_kbps=3000, min_ms=1, max_ms=3000, history_len=self.history_len)
        self.helper = ObsRewardActionHelper(min_kbps=100, max_kbps=3000, history_len=self.history_len, discrete_action_space_type=discrete_action_space_type, rtt_coeff=rtt_coeff)
        # self.plotter = Plotter(is_gcc=is_gcc, mode=mode, rl_algo=rl_algo, trace_type=trace_type, discrete_action_space_type=discrete_action_space_type)
        # Used only in eval mode
        self.latest_obs = self.helper.calculate_obs(self.packet_record)
        self.call = call

        ### RL algorithm-related
        self.policy = None
        self.rl_algo = rl_algo
        self.action_space_type = action_space_type
        self.discrete_action_space_type = discrete_action_space_type
        self.on_or_off_policy = ''
        if self.rl_algo == 'PPO' or self.rl_algo == 'A2C':
            self.on_or_off_policy = 'On-Policy'
        else:
            self.on_or_off_policy = 'Off-Policy'

        self.latest_bwe = 300000
        self.action_helper = ActionHelper()
        self.action_space = self.action_helper.action_space
        self.state_helper = StateHelper(step_time=60)
        self.observation_space = self.state_helper.observation_space
        self.reward_helper = RewardHelper(step_time=60)

        # # Action space must be an gym.spaces object
        # if self.action_space_type == 'discrete':
        #     if discrete_action_space_type == 'loki':
        #         self.action_space = spaces.Discrete(11)
        #     else:
        #         self.action_space = spaces.Discrete(25)
        # # Best practice: action space normalized to [-1, 1], i.e. symmetric and has an interval range of 2,
        # # which is usually the same magnitude as the initial stdev of the Gaussian used to define the policy
        # # (e.g. unit initial stdev in SB3)
        # # Most RL algorithms (except DDPG or TD3) rely on a Gaussian distribution
        # # (initially centered at 0 with std 1) for continuous actions.
        # # So, if you forget to normalize the action space when using a custom environment,
        # # this can harm learning and be difficult to debug (cf attached image and issue #473).
        # else:
        #     self.action_space = spaces.Box(low=-1, high=1, shape=(1,), dtype=np.float32)
        # # Observation space must be an gym.spaces object
        # self.observation_space = spaces.Box(low = 0.0, high = 1.0, shape=(3, self.history_len), dtype=np.float64)

        # For logging
        self.algo_str = self.set_algo_str()


    def start(self, policy=None, starting_episode=0):
        if not self.is_gcc:
            self.policy = policy
            self.num_episodes += starting_episode
            if self.mode == 'train':
                self.policy._setup_learn(-1)
        while self.num_episodes <= self.total_episodes:
            fin_status = self.run_episode()
            self.post_episode(fin_status)
        self.post_start()


    def run_episode(self):
        # One episode = one call using one trace.
        receiver_app, sender_app, self.trace_file = self.call.create_and_run_call()
        fin_status = 'SUCCESS'
        logging.info(f'\n{self.algo_str} EPISODE {self.num_episodes}/{self.total_episodes}: Starting (trace: {self.trace_file})')

        is_sender_running = sender_app.poll() is None
        is_receiver_running = receiver_app.poll() is None
        if not is_sender_running or not is_receiver_running:
            logging.info(f'\n{self.algo_str} EPISODE {self.num_episodes}/{self.total_episodes}: is_sender_running {is_sender_running} is_receiver_running {is_receiver_running}, killing the call')
            self.call.kill_call()
            fin_status = 'KILLED'
            return fin_status

        # Init per-episode stats
        self.packet_record.init_episode()
        while True:
            line = receiver_app.stdout.readline()

            # Receiver completed: call ended
            if not line:
                break

            if isinstance(line, bytes):
                line = line.decode().strip()
            stats = self.fetch_stats(line)
            if stats:
                self.report_stats(stats)
                continue

            if RequestBandwidthCommand == line.strip():
                obs, states_info = self.state_helper.compute_obs(self.newly_computed_action)
                reward, reward_info = self.reward_helper.compute_reward(self.latest_bwe)
                if type(reward) is list or isinstance(reward, np.ndarray):
                    reward = reward[0]
                self.episode_rewards.append(reward)
                # self.info.update(states_info)
                # self.info.update(reward_info)
                logging.info(f'########################## OBS REWARD {obs} {reward}')

                #     action = session.run(["output"], {
                #         'obs': np.array([obs], dtype=np.float32),
                #         'state_ins': np.array([0.0], dtype=np.float32)})[0][0][0]
                bandwidth = self.get_estimated_bandwidth(obs)
                logging.info(f'########################## EPISODE {self.num_episodes} BANDWIDTH {bandwidth}')
                bandwidth_encoded = f'{float(bandwidth)}\n'.encode('utf-8')
                receiver_app.stdin.write(bandwidth_encoded)
                receiver_app.stdin.flush()
                self.num_timesteps += 1
                continue
        try:
            with open(f'status.txt', mode='w') as f:
                fin_t = datetime.now().timestamp()
                f.write(f'EPISODE {self.num_episodes} time {fin_t}\n')
            receiver_app.wait(timeout=35)
            sender_app.wait(timeout=35)
        except:
            self.call.kill_call()
            fin_status = 'KILLED'

        return fin_status

    def post_episode(self, fin_status):
        self.episode_len = self.num_timesteps
        if self.episode_len > 0:
            avg_episode_reward = np.mean(self.episode_rewards)
            stdev_episode_reward = np.std(self.episode_rewards)
            for r in self.episode_rewards:
                norm_r = (r - avg_episode_reward) / stdev_episode_reward
                self.norm_episode_rewards.append(norm_r)
            logging.info(f'{self.algo_str} EPISODE {self.num_episodes}/{self.total_episodes} Finished (avg. episode reward: {avg_episode_reward:.4f} episode len: {self.episode_len} status: {fin_status} trace: {self.trace_file})')
            logging.info(f'EPISODE {self.num_episodes} norm step rewards {self.norm_episode_rewards}')
            # Compute SSIM for this call
            # if self.mode == 'eval':
            #     self.compute_ssim()
            # Progress excludes calls that didn't even started
            self.num_episodes += 1
        else:
            avg_episode_reward = 0
        self.infos[0]['episode']['r'] = avg_episode_reward
        self.infos[0]['episode']['l'] = self.episode_len
        # Set the episode end signal.
        self.dones = np.ones(1)

        # Save checkpoint and plot learning curve
        if not self.is_gcc and self.mode == 'train' and self.num_episodes > 1 and self.num_episodes % self.ckpt_interval == 0:
            date_time_ymdhms = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            ckptname = f'{self.rl_algo_str()}-ckpt-{self.trace_type}-episode{self.num_episodes}-{date_time_ymdhms}'
            self.policy.save(f'{self.ckpt_dir}/{ckptname}')

        # Init progress-related metadata
        self.num_timesteps = 0
        self.agg_episode_reward = 0.0
        self.episode_len = 0


    def report_stats(self, pkt: dict):
        '''
        stats is a dict with the following items
        {
            "send_time_ms": uint,
            "arrival_time_ms": uint,
            "payload_type": int,
            "sequence_number": uint,
            "ssrc": int,
            "padding_length": uint,
            "header_length": uint,
            "payload_size": uint
        }
        '''
        packet_infos = []
        packet_info = PacketInfo()
        packet_info.payload_type = pkt["payload_type"]
        packet_info.ssrc = pkt["ssrc"]
        packet_info.sequence_number = pkt["sequence_number"]
        packet_info.send_timestamp = pkt["send_time_ms"]
        packet_info.receive_timestamp = pkt["arrival_time_ms"]
        packet_info.padding_length = pkt["padding_length"]
        packet_info.header_length = pkt["header_length"]
        packet_info.payload_size = pkt["payload_size"]
        packet_info.bandwidth_prediction = self.latest_bwe
        # print(f'PacketInfo {packet_info}')
        packet_infos.append(packet_info)

        self.state_helper.process_stats(packet_infos)
        self.reward_helper.process_stats(packet_infos)

    def fetch_stats(self, line: str)->dict:
        line = line.strip()
        try:
            stats = json.loads(line)
            return stats
        except json.decoder.JSONDecodeError:
            return None

    def get_estimated_bandwidth(self, obs)->int:
        # action = self.session.run(["output"], {
        #     'obs': np.array([obs], dtype=np.float32),
        #     'state_ins': np.array([0.0], dtype=np.float32)})[0][0][0]
        if self.mode == 'train':
            if self.is_on_policy():
                self.newly_computed_action, self.values, self.log_probs = self.policy.compute_actions()
            else:
                _, self.newly_computed_action = self.policy.sample_action()
        else:
            self.newly_computed_action, _ = self.policy.predict(obs)

        if type(self.newly_computed_action) is list or isinstance(self.newly_computed_action, np.ndarray):
            self.newly_computed_action = self.newly_computed_action[0]

        action = self.newly_computed_action
        action = np.clip(action, self.action_space.low, self.action_space.high)
        bandwidth_prediction, action_info = self.action_helper(action)
        # self.info.update(action_info)
        self.latest_bwe = bandwidth_prediction = log_to_linear(action)
        return bandwidth_prediction

    def request_estimated_bandwidth(self, line: str)->bool:
        line = line.strip()
        if RequestBandwidthCommand == line:
            return True
        return False

    '''
    One env step implemented in two parts:
    - Part 1. policy.sample/compute_actions() computes actions based on the latest previous obs
    - Part 2. policy.add_to_rollout/replay_buffer() add a trajectory to the rollout buffer
    '''
    def env_step(self):
        if self.is_gcc:
            self.compute_obs_reward()
        else:
            self.get_next_action()
            self.compute_obs_reward()
            self.return_next_action()

        self.num_timesteps += 1

    # Compute obs, reward as a result of applying the latest previous action, i.e. self.applied_action.
    # and add them to the rollout buffer
    def compute_obs_reward(self):
        if self.mode == 'train':
            new_obs = self.helper.calculate_obs(self.packet_record)
            rewards, reward_str = self.helper.calculate_reward(self.packet_record)
            self.agg_episode_reward += rewards

            if self.is_on_policy():
                if self.applied_action == -1:
                    is_full = self.policy.add_to_rollout_buffer(new_obs, self.newly_computed_action, rewards, self.values, self.log_probs, self.dones, self.infos)
                else:
                    is_full = self.policy.add_to_rollout_buffer(new_obs, self.applied_action, rewards, self.values, self.log_probs, self.dones, self.infos)
            else:
                if self.applied_action == -1:
                    rollout = self.policy.add_to_replay_buffer(new_obs, self.newly_computed_action, rewards, self.dones, self.infos)
                else:
                    rollout = self.policy.add_to_replay_buffer(new_obs, self.applied_action, rewards, self.dones, self.infos)

            if self.dones == np.ones(1):
                # dones == 1 means that it is set at the end of the previous episode,
                # and this is a new episode. Reset dones and infos.
                self.dones = np.zeros(1)
                self.infos = [{'episode': {'r': 0, 'l': 0}}]

            # New Obs: a new obs collected, as a result of the previously computed action
            # Reward: how good the previously computed action was
            # print(f'{self.algo_str} Episode {self.num_episodes} Step {self.num_timesteps} (2) compute_obs_reward(): Reward {reward_str} as a result of applying BWE {self.applied_bwe} from action {self.applied_action} New Obs {new_obs} (shape {new_obs.shape} [loss_rate, norm_rtt, norm_recv_thp]) {self.packet_record}')
            print(f'{self.algo_str} Episode {self.num_episodes} Step {self.num_timesteps} (2) compute_obs_reward(): Reward {reward_str} as a result of applying BWE {self.applied_bwe} from action {self.applied_action} RTT {new_obs} (shape {new_obs.shape} [loss_rate, norm_rtt, norm_recv_thp]) {self.packet_record}')

            if self.is_on_policy():
                # For on-policy algorithms, update the model when rollout buffer becomes full
                if is_full:
                    # One policy.collect_rollouts loop finished
                    self.kth_rollout_loop += 1
                    self.policy.collection_loop_fin(True)
                    # Do model update
                    self.policy.train()
                    print(f'{self.algo_str} Episode {self.num_episodes} Step {self.num_timesteps} (2) compute_obs_reward() Model Updated')
                    # init for the next rollout collection
                    self.policy.init_rollout_collection()
            else:
                # One policy.collect_rollouts loop finished
                if rollout is not None:
                    if rollout.continue_training:
                        self.policy.train(rollout)
                        print(f'{self.algo_str} Episode {self.num_episodes} Step {self.num_timesteps} (2) compute_obs_reward() Model Updated')
                        # init for the next rollout collection
                        self.policy.init_rollout_collection()
        else:
            self.latest_obs = self.helper.calculate_obs(self.packet_record)
            rewards, reward_str = self.helper.calculate_reward(self.packet_record)
            self.agg_episode_reward += rewards

            if self.dones == np.ones(1):
                # dones == 1 means that it is set at the end of the previous episode,
                # and this is a new episode. Reset dones and infos.
                self.dones = np.zeros(1)
                self.infos = [{'episode': {'r': 0, 'l': 0}}]

            # New Obs: a new obs collected, as a result of the previously computed action
            # Reward: how good the previously computed action was
            if self.is_gcc:
                print(f'[{self.algo_str}] Episode {self.num_episodes} Reward {reward_str} New Obs {self.latest_obs} (shape {self.latest_obs.shape} [loss_rate, norm_rtt, norm_recv_thp])')
            else:
                print(f'{self.algo_str} Episode {self.num_episodes} Step {self.num_timesteps} (2) compute_obs_reward(): Reward {reward_str} as a result of applying BWE {self.applied_bwe} from action {self.applied_action} New Obs {self.latest_obs} (shape {self.latest_obs.shape} [loss_rate, norm_rtt, norm_recv_thp])')


    def return_next_action(self):
        # Apply next action
        if self.action_space_type == 'continuous':
            bwe = self.helper.rescale_action_continuous(self.newly_computed_action)
        else:
            bwe = self.helper.get_discrete_action(self.newly_computed_action)
        with open(f'bwe.txt', mode='w') as f:
            f.write(f'{bwe}')

        # Update applied BWE and actions
        self.applied_action = self.newly_computed_action
        self.applied_bwe = bwe

        # print(f'[{self.on_or_off_policy} {self.rl_algo}] Episode {self.num_episodes} Step {self.num_timesteps} (3) return_next_action() updated BWE {bwe}')


    def is_on_policy(self):
        return 'On-Policy' in self.on_or_off_policy


    def rl_algo_str(self):
        if self.is_gcc:
            rl_algo_str = 'GCC'
        elif self.rl_algo == 'DQN':
            rl_algo_str = f'{self.rl_algo}-{self.discrete_action_space_type}'
        else:
            rl_algo_str = f'{self.rl_algo}'
        return rl_algo_str


    def set_algo_str(self):
        if self.is_gcc:
            return 'GCC'
        else:
            return f'[{self.mode}][{self.on_or_off_policy} {self.rl_algo}]'


    def post_start(self):
        self.save_log()


    def save_log(self):
        log_dir = self.create_log_dir()
        date_time_ymdhms = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        video_res = self.call.get_video_res()
        stdout_log = f'{self.rl_algo_str()}-stdout-log-{self.mode}-{self.trace_type}-{video_res}-{self.num_episodes}episodes-{date_time_ymdhms}.log'
        receiver_log = f'{self.rl_algo_str()}-receiver-log-{self.mode}-{self.trace_type}-{video_res}-{self.num_episodes}episodes-{date_time_ymdhms}.log'
        sender_log = f'{self.rl_algo_str()}-sender-log-{self.mode}-{self.trace_type}-{video_res}-{self.num_episodes}episodes-{date_time_ymdhms}.log'
        os.system(f'cp output {log_dir}/{stdout_log}')
        os.system(f'cp receiver.log {log_dir}/{receiver_log}')
        os.system(f'cp sender.log {log_dir}/{sender_log}')


    def create_log_dir(self):
        date_time_ymd = datetime.now().strftime("%Y-%m-%d")
        log_root_dir = f'{self.emu_gym_path}/rl_training/logs/'
        log_dir = f'{log_root_dir}/{date_time_ymd}'
        if not os.path.exists(log_root_dir):
            os.makedirs(log_root_dir)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        return log_dir


    def compute_ssim(self):
        for f in glob.glob("ffmpeg-*.log"):
            os.remove(f)

        # For every run, measure SSIM of the `output.yuv` and delete it
        cmd = f'ffmpeg -report -i {self.emu_gym_path}/outvideo.yuv -s 320x240 -i {self.emu_gym_path}/testmedia/test.yuv -s 320x240 -filter_complex "ssim" -f null /dev/null'
        os.system(cmd)

        for f in glob.glob(f'{self.emu_gym_path}/outvideo.yuv'):
            os.remove(f)


    '''
    Deprecated.
    Run one timestep of the environment's dynamics.
    When end of episode is reached, you are responsible for calling `reset()`
    to reset this environment's state.

    Args:
        action (object): an action provided by the agent

    Returns:
        observation (object): agent's observation of the current environment
        reward (float) : amount of reward returned after previous action
        done (bool): whether the episode has ended, in which case further step() calls will return undefined results
        info (dict): contains auxiliary diagnostic information (helpful for debugging, and sometimes learning)
    '''
    def step(self, action):
        print(f'env.step() is no more used!')

    '''
    Resets the environment to an initial state and returns an initial observation.

    Note that this function should not reset the environment's random number generator(s);
    random variables in the environment's state should be sampled independently
    between multiple calls to `reset()`.
    In other words, each call of `reset()` should yield an environment suitable for
    a new episode, independent of previous episodes.

    Returns:
        observation (object): the initial observation.
    '''
    def reset(self, seed):
        super().reset(seed=seed)

        # Reset internal states of the environment
        self.packet_record.reset()
        self.num_timesteps = 0
        self.agg_episode_reward = 0.0
        self.episode_len = 0
        self.dones = np.zeros(1)
        self.infos = [{'episode': {'r': 0, 'l': 0}}]

        # Produce initial observation
        # initial_obs = self.helper.calculate_obs(self.packet_record)

        initial_obs = self.state_helper.reset()
        self.reward_helper.reset()
        self.episode_rewards = []
        self.norm_episode_rewards = []

        logging.info(f'{self.algo_str} EPISODE {self.num_episodes}/{self.total_episodes} env reset done: an environment for a new episode is set')

        return initial_obs, None


    '''
    Renders the environment.
    Nothing to do.
    '''
    def render(self, mode='human'):
        pass

    '''
    Perform any necessary cleanup.
    Environments will automatically close() themselves
    when garbage collected or the program exits.
    Nothing to do.
    '''
    def close (self):
        pass
