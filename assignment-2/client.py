"""
Client
"""
# pylint: disable=redefined-outer-name
import os
import argparse
import logging
import typing
import yaml
import grpc

import util

import kv_pb2
import kv_pb2_grpc

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - [%(pathname)s:%(funcName)s:%(lineno)d] - %(message)s",
    level=logging.DEBUG,
)
logger = logging.getLogger()


class KVClient:
    """KV Client"""

    def __init__(self, raft_cluster: typing.List[str], kv_cluster: typing.List[str]):
        self.raft_cluster = raft_cluster
        self.kv_cluster = kv_cluster
        self.leader_id = -1

    def ask_for_leader(self, node_id) -> int:
        """Connects to the node_id and asks for the leader"""
        try:
            with grpc.insecure_channel(self.kv_cluster[node_id]) as channel:
                stub = kv_pb2_grpc.KVServiceStub(channel)
                # pylint: disable=no-member
                reply = stub.GetLeader(kv_pb2.GetLeaderArgs())
        except grpc.RpcError as err:
            logger.error(
                "Error occurred while sending RPC to Node %s. Error: %s",
                node_id,
                str(err.args),
            )
            return -1
        if reply.leaderId == -1:
            logger.error("Node %s doesn't know the leader. %s", node_id, reply.error)
        else:
            logger.info("Node %s. Leader is %s", node_id, reply.leaderId)
            self.leader_id = reply.leaderId
        return reply.leaderId

    def get_leader(self) -> int:
        """Connects to any random node and returns the leader id"""
        return -1

    def go_cmd_mode(self):
        """Command line"""
        while True:
            cmd = input("(cls-clear 0-Close 1-ClusterMembers 2-askForLeader: ")
            if cmd == "":
                continue
            if cmd == "cls":
                os.system("clear")
                continue
            cmd = int(cmd)
            if cmd == 0:
                break
            if cmd == 1:
                print("Raft Cluster:\t", str(self.raft_cluster))
                print("KV Cluster:\t", str(self.kv_cluster))
            if cmd == 2:
                node_id = input("Node: ")
                if (not node_id.isdigit()) or (
                    not (0 <= int(node_id) < len(self.kv_cluster))
                ):
                    continue
                node_id = int(node_id)
                self.ask_for_leader(node_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Raft",
        epilog="$ python3 main.py --config config.yaml --id 0",
    )
    parser.add_argument(
        "-c", "--config", help="cluster config", required=True, type=str
    )
    args = parser.parse_args()
    with open(args.config, "r", encoding="UTF-8") as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
        raft_cluster, kv_cluster = util.clusters_from_config(config)
    kv_client = KVClient(raft_cluster, kv_cluster)
    kv_client.go_cmd_mode()
