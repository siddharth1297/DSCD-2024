"""
Helper functions
"""
import time


def current_time_millis() -> int:
    """Current time in MS"""
    return int(time.time() * 1000)


def current_time_second() -> int:
    """Current time in Second"""
    return int(time.time())


def clusters_from_config(config):
    """Returns raft and kv clusters in form of list"""
    nodes = list(config.values())[0]
    raft_cluster = list(map(lambda x: f"{x[0]}:{x[1]}", nodes))
    kv_cluster = list(map(lambda x: f"{x[0]}:{x[2]}", nodes))
    return raft_cluster, kv_cluster
