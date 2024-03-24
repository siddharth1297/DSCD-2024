"""
main entry point
"""
# pylint: disable=redefined-outer-name, global-statement
import os
import argparse
import logging
import sys
import typing
import signal
import yaml
import logger
import util

import raft
import kvserver

LOGGING_LEVEL = logging.DEBUG

RF = None
KV = None


def signal_handler(_sig, _frame):
    """Signal handler to close the app"""
    KV.stop()
    RF.stop()
    sys.exit(0)


def main(
    node_id: int, raft_cluster: typing.Dict[int, str], kv_cluster: typing.Dict[int, str], rejoin
) -> None:
    """main"""
    logger.set_logger(f"logs_node_{node_id}/", f"Node-{str(node_id)}", LOGGING_LEVEL)
    meta_fd = logger.create_manual_logger(f"logs_node_{node_id}/metadata.txt", rejoin)
    logs_fd = logger.create_manual_logger(f"logs_node_{node_id}/logs.txt", rejoin)
    logger.DUMP_LOGGER.info(
        "NodeId %s ProcessId %s Raft %s KV %s",
        node_id,
        os.getpid(),
        raft_cluster[node_id],
        kv_cluster[node_id],
    )
    global RF, KV
    KV = kvserver.KVServer(node_id, raft_cluster, kv_cluster)
    RF = raft.Raft(node_id, raft_cluster, KV, logs_fd=logs_fd, metadata_fd=meta_fd)
    KV.set_state_machine(RF)
    KV.start()
    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Raft",
        epilog="$ python3 main.py --config config.yaml [--rejoin] --id 0",
    )
    parser.add_argument('--rejoin', action='store_true', help='rejoin the cluster. It will read from the logs')
    parser.add_argument(
        "-c", "--config", help="cluster config", required=True, type=str
    )
    parser.add_argument("-i", "--id", help="node id", required=True, type=int)
    args = parser.parse_args()
    with open(args.config, "r", encoding="UTF-8") as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
        raft_cluster, kv_cluster = util.clusters_from_config(config)
    main(args.id, raft_cluster, kv_cluster, args.rejoin)
