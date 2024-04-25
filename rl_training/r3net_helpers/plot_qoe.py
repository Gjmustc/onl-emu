from statistics import mean, stdev
import matplotlib.pyplot as plt
from datetime import datetime


class Plotter:
    def __init__(self, is_gcc, rl_algo, trace_type, discrete_action_space_type):
        self.is_gcc=is_gcc
        self.rl_algo=rl_algo
        self.trace=trace_type
        self.discrete_action_space_type=discrete_action_space_type
        self.qoe_stubs = [
            # Delays
            'JitterBufferDelayInMs '
            'EndToEndDelayInMs ',
            'EndToEndDelayMaxInMs ',

            # Frame size
            'ReceivedWidthInPixels ',
            'ReceivedHeightInPixels ',

            # Frame rate
            'DecodedFramesPerSecond ',
            'HarmonicFrameRate ',

            # Media bitrate
            'MediaBitrateReceivedInKbps ',

            # Frame delay
            'InterframeDelayInMs ',
            'InterframeDelay95PercentileInMs ',
            'InterframeDelayMaxInMs ',

            # Decoder QP
            'Decoded.Vp8.Qp ',

            # Video Quality Metrics
            'MeanTimeBetweenFreezesMs ',
            'TimeInBlockyVideoPercentage ',
            'NumberResolutionDownswitchesPerMinute ',
            'NumberFreezesPerMinute ',
            'DroppedFrames.Receiver ',
        ]

    def plot_ssim(self, log_path):
        x_axis = []
        y_axis = []
        num_episodes = 1
        with open(log_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and 'Parsed_ssim_' in line and 'SSIM' in line:
                    y_axis.append(float(line.split('All:')[1].split('(')[1].split(')')[0]))
                    x_axis.append(num_episodes)
                    num_episodes += 1
        print(f'SSIM: {x_axis} {y_axis}')
        if len(y_axis) > 0:
            self.plot(stat_type='SSIM', graph_type='scatter', x_axis=x_axis, y_axis=y_axis, xlabel='Episode', ylabel='SSIM')


    def plot_qoe(self, log_path):
        x_axis = []
        y_axis = []
        num_episodes = 1
        for stub in self.qoe_stubs:
            with open(log_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and stub in line:
                        print(line)
                        y_axis.append(float(line.split(stub)[1].strip()))
                        x_axis.append(num_episodes)
                        num_episodes += 1
            print(f'{stub}: {x_axis} {y_axis}')
            if len(y_axis) > 0:
                self.plot(stat_type=stub, graph_type='scatter', x_axis=x_axis, y_axis=y_axis, xlabel='Episode', ylabel=stub)
            x_axis = []
            y_axis = []
            num_episodes = 1


    def set_color(self, algo):
        # blue
        c = '#005ab5'
        if 'GCC' in algo:
            c = 'black'
        elif 'PPO' in algo:
            c = 'red'
        elif 'A2C' in algo:
            # pale pink
            c = '#de5d83'
        elif 'DQN' in algo:
            # blue
            c = '#005ab5'
        elif 'SAC' in algo:
            # pale blue
            c = '#4682b4'
        return c


    def rl_algo_str(self):
        if self.is_gcc:
            rl_algo_str = 'GCC'
        elif self.rl_algo == 'DQN':
            rl_algo_str = f'{self.rl_algo}-{self.discrete_action_space_type}'
        else:
            rl_algo_str = f'{self.rl_algo}'
        return rl_algo_str


    def plot(self, stat_type, graph_type, x_axis, y_axis, xlabel, ylabel):
        average = "{:.4f}".format(mean(y_axis))
        standard_dev = "{:.4f}".format(stdev(y_axis))
        stat_type = stat_type.strip()
        # figname
        date_time_ymdhms = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        rl_algo_str = self.rl_algo_str()
        figname = f'{rl_algo_str}-{stat_type}-{self.trace}-{date_time_ymdhms}.pdf'
        print(f'Saving figure to {figname}')
        title = f'{rl_algo_str} {stat_type} {self.trace} Avg {average} Stdev {standard_dev}'

        c = self.set_color(rl_algo_str)
        plt.figure(figsize=(8, 4))
        plt.subplot(111)
        if graph_type == 'line':
            plt.plot(y_axis, color=c)
        elif graph_type == 'scatter':
            plt.scatter(x_axis, y_axis, color=c)
        plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        # plt.ylim(top=self.get_ylim_top(stat_type))
        plt.savefig(f'{figname}', bbox_inches='tight')


def main():
    # rl_algo, trace, discrete_action_space_type):
    ppo_log = f'PPO-eval/PPO-stdout-log-eval-belgium-2023-06-09-15-00-12.log'

    plotter = Plotter(is_gcc=False, rl_algo='PPO', trace_type='belgium', discrete_action_space_type='loki')
    plotter.plot_qoe(f'{ppo_log}')
    plotter.plot_ssim(f'{ppo_log}')

if __name__ == '__main__':
    main()

