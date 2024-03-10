"""
main entry point
"""
import argparse
import logging
import typing
import yaml
import logger

LOGGING_LEVEL = logging.INFO


def main(node_id: int, cluster: typing.Dict[int, str]) -> None:
    """main"""
    logger.set_logger(f"logs_node_{node_id}/", LOGGING_LEVEL)


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
