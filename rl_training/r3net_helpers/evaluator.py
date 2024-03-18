import onnxruntime
import numpy as np
import os
from gym_warpper import AlphaRTCEnv
from utils.record import Record


class Evaluator:
    def __init__(self, **config):
        self.env = AlphaRTCEnv(trace_dir=config["trace_dir"])
        self.record = Record()
        self.eval_num = config.get("eval_num", 10)

    def eval(self, model_path):
        model = os.path.join(model_path, "model.onnx")
        session = onnxruntime.InferenceSession(model)
        reward_list = []
        for i in range(self.eval_num):
            self.record.reset()

            obs, _ = self.env.reset()
            print(f'eval: obs {obs}')
            done = False
            episode_reward = 0
            while not done:
                action = session.run(["output"], {
                    'obs': np.array([obs], dtype=np.float32),
                    'state_ins': np.array([0.0], dtype=np.float32)})[0][0][0]
                obs, reward, done, _, info = self.env.step([action])
                episode_reward += reward
                self.record.update(info)

            reward_list.append(episode_reward)
            fig_path = os.path.join(model_path,
                f"{i}_{episode_reward.round(3)}.jpg")
            self.record.plot_record(fig_path)
        result = {
            "episode_reward_mean": np.mean(reward_list),
            "episode_reward_max": np.max(reward_list),
            "episode_reward_min": np.min(reward_list)
        }
        return result