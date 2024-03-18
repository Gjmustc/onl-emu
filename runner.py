import argparse
import glob
import os

from rl_training.call import Call
from rl_training.policy_factory import PolicyFactory
from rl_training.rtc_env2 import RTCEnv2

emu_gym_path = os.path.expandvars('$EMU_GYM_PATH')


def _parse_args():
    parser = argparse.ArgumentParser(description='Emulator-based training of RL-based bitrate controller for RTC')

    parser.add_argument('--mode', type=str, default='train', choices=['train', 'eval'],
                        help='Training or evaluation mode')
    parser.add_argument('--trace-type', type=str, default='belgium', choices=['belgium', 'fcc', 'norway', 'belgium+fcc', 'belgium+norway', 'fcc+norway', 'belgium+fcc+norway', 'simple', 'static'],
                        help='Type of mahimahi trace set to use in training')
    parser.add_argument('--rl-algo', type=str, default='PPO',
                        help='RL algorithm to use to train the RL-based bitrate controller')
    parser.add_argument('--action-space-type', type=str, default='continuous', choices=['continuous', 'discrete'],
                        help='Action space type: continuous or discrete')
    parser.add_argument('--discrete-action-space-type', type=str, default='loki', choices=['onrl', 'loki'],
                        help='Which discrete action space type to use: MobiCom20 OnRL or MobiCom21 Loki')
    parser.add_argument('--total-episodes', type=int, default=1,
                        help='Total number of episodes to train')
    parser.add_argument('--ckpt-interval', type=int, default=2,
                        help='Save ckpt at every N number of episodes')
    parser.add_argument("--ckpt-dir", default=f'{emu_gym_path}/rl_training/checkpoints', type=str,
                        help="Path to store policy checkpoints")
    parser.add_argument('--rtt-coeff', type=float, default=1.0,
                        help='Coefficient to RTT term in the reward')
    # args for eval
    parser.add_argument("--ckpt", default='', type=str,
                        help="Path to the policy checkpoint to evaluate")
    parser.add_argument("--gcc", action='store_true',
                        help="Run GCC")
    # args for media type
    parser.add_argument('--video-res', type=str, default='360p', choices=['360p', '720p', '1080p'],
                        help='Video resolution to use')

    return parser.parse_args()


def init():
    for f in glob.glob(".log"):
        os.remove(f)
    with open('bwe.txt', "w") as f:
        f.write(f'300000')
    with open('recv-thp.txt', "w") as f:
        f.write(f'300000')


def parse_episode_from_ckpt(ckpt):
    # A2C-ckpt-belgium+norway-episode800-2023-05-24-00-52-10.zip
    _, l1 = ckpt.split('episode')
    trained_episode = int(l1.split('-')[0])
    return trained_episode


def create_call(args):
    return Call(mode=args.mode, is_gcc=args.gcc, trace_type=args.trace_type, video_res=args.video_res)


def create_env(call, args):
    return RTCEnv2(mode=args.mode, is_gcc=args.gcc, call=call, trace_type=args.trace_type, \
        rl_algo=args.rl_algo, action_space_type=args.action_space_type, discrete_action_space_type=args.discrete_action_space_type, rtt_coeff=args.rtt_coeff, \
        total_episodes=args.total_episodes, ckpt_interval=args.ckpt_interval, ckpt_dir=args.ckpt_dir)


def create_policy(args, env):
    policy = None
    starting_episode = 0
    if args.mode == 'train':
        if args.ckpt != '':
            ckpt_path = f'{args.ckpt_dir}/{args.ckpt}'
            starting_episode = parse_episode_from_ckpt(args.ckpt) + 1
            policy = PolicyFactory().create_policy(env, args.rl_algo, ckpt_path)
        else:
            policy = PolicyFactory().create_policy(env, args.rl_algo)
    elif args.mode == 'eval' and not args.gcc:
        ckpt_path = f'{args.ckpt_dir}/{args.ckpt}'
        policy = PolicyFactory().create_policy(env, args.rl_algo, ckpt_path)
    elif args.mode == 'eval' and args.gcc:
        policy = None
        starting_episode = 0
    else:
        print(f'Unsupported mode {args.mode}')

    return policy, starting_episode


def main(args):
    init()
    call = create_call(args)
    env = create_env(call, args)
    # policy, starting_episode = create_policy(args, env)
    env.start(None, 0)


if __name__ == "__main__":
    args = _parse_args()
    main(args)