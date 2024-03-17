"""
main entry point
"""
import os
import argparse
import logging
import sys
import typing
import signal
import yaml
import logger
import raft

LOGGING_LEVEL = logging.DEBUG

RF = None


def signal_handler(_sig, _frame):
    """Signal handler to close the app"""
    RF.stop()
    sys.exit(0)


def main(node_id: int, cluster: typing.Dict[int, str]) -> None:
    """main"""
    logger.set_logger(f"logs_node_{node_id}/", "Node: " + str(node_id), LOGGING_LEVEL)
    # pylint: disable=global-statement
    logger.DUMP_LOGGER.info("ProcessId %s", os.getpid())
    global RF
    RF = raft.Raft(node_id, list(cluster["cluster"].values()))
    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Raft",
        epilog="$ python3 main.py --config config.yaml --id 0",
    )
    parser.add_argument(
        "-c", "--config", help="cluster config", required=True, type=str
    )
    parser.add_argument("-i", "--id", help="node id", required=True, type=int)
    args = parser.parse_args()
    with open(args.config, "r", encoding="UTF-8") as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
    main(args.id, config)
