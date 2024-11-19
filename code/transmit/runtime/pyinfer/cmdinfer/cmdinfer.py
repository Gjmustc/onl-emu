#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import glob


RequestBandwidthCommand = "RequestBandwidth"

def fetch_stats(line: str)->dict:
    line = line.strip()
    try:
        stats = json.loads(line)
        return stats
    except json.decoder.JSONDecodeError:
        return None


def request_estimated_bandwidth(line: str, count):
    line = line.strip()
    if RequestBandwidthCommand == line:
        count += 1
        return True, count
    return False, count


def find_estimator_class():
    import BandwidthEstimator as BandwidthEstimator
    return BandwidthEstimator.Estimator


def main(ifd = sys.stdin, ofd = sys.stdout):
    estimator_class = find_estimator_class()
    estimator = estimator_class()
    count = 0
    while True:
        line = ifd.readline()
        if not line:
            break
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        stats = fetch_stats(line)
        if stats:
            estimator.report_states(stats)
            continue
        request, count = request_estimated_bandwidth(line, count)
        if request:
            sys.stdout.write(f"-------------------------RequestBandwidth Count:{count}-----------------")
            bandwidth = estimator.get_estimated_bandwidth()
            ofd.write("{}\n".format(int(bandwidth)).encode("utf-8"))
            ofd.flush()
            continue
        sys.stdout.write(line)
        sys.stdout.flush()

if __name__ == '__main__':
    main()
