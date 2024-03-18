import numpy as np


UNIT_M = 1000000
MIN_ACTION = 0
MAX_ACTION = 1
MIN_BANDWIDTH_MBPS = 0.3
MAX_BANDWIDTH_MBPS = 6
LOG_MIN_BANDWIDTH_MBPS = np.log(MIN_BANDWIDTH_MBPS)
LOG_MAX_BANDWIDTH_MBPS = np.log(MAX_BANDWIDTH_MBPS)

def liner_to_log(value):
    # from min bw~max bw to 0~1
    value = np.clip(value / UNIT_M, MIN_BANDWIDTH_MBPS, MAX_BANDWIDTH_MBPS)
    log_value = np.log(value)
    return (log_value - LOG_MIN_BANDWIDTH_MBPS) / (LOG_MAX_BANDWIDTH_MBPS - LOG_MIN_BANDWIDTH_MBPS)


def log_to_linear(value):
    # from 0~1 to min bw~max bw
    value = np.clip(value, MIN_ACTION, MAX_ACTION)
    log_bwe = value * (LOG_MAX_BANDWIDTH_MBPS - LOG_MIN_BANDWIDTH_MBPS) + LOG_MIN_BANDWIDTH_MBPS
    return np.exp(log_bwe) * UNIT_M


if __name__  == '__main__':
    print(log_to_linear(0.87))