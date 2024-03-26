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

from kvserver import KVErrors, GET_TIMEOUT, SET_TIMEOUT

import kv_pb2
import kv_pb2_grpc


logging.basicConfig(
    format="%(asctime)s.%(msecs)03d - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s",
    datefmt="%H:%M:%S",
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
        logger.info("Asking for leader information to node %s", node_id)
        try:
            with grpc.insecure_channel(self.kv_cluster[node_id]) as channel:
                stub = kv_pb2_grpc.KVServiceStub(channel)
                # pylint: disable=no-member
                reply = stub.GetLeader(kv_pb2.GetLeaderArgs())
        except grpc.RpcError as err:
            if err.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                logger.error("RPC TIMEOUT")
            elif err.code() == grpc.StatusCode.UNAVAILABLE:
                logger.error("RPC Node %s unavailable", self.leader_id)
            else:
                logger.error(
                    "Error occurred while sending RPC to Node %s. Code: %s. Error: %s",
                    self.leader_id,
                    str(err.code()),
                    str(err),
                )
            return -1
        if reply.leaderId == -1:
            logger.error("Node %s doesn't know the leader. %s", node_id, reply.error)
        else:
            logger.info("Leader is %s", reply.leaderId)
            self.leader_id = reply.leaderId
        return reply.leaderId

    def get_leader(self) -> int:
        """Connects to any random node and returns the leader id"""
        for node_id in range(len(self.kv_cluster)):
            self.ask_for_leader(node_id)
            if self.leader_id != -1:
                break
        return self.leader_id

    def get(self, key: str) -> typing.Tuple[bool, str, str]:
        """Get value of the key. Returns (status, value, error)"""
        logger.info("Starting get %s", key)

        if self.leader_id == -1:
            logger.debug("Leader unknown. Trying to get leader")
            if self.get_leader() == -1:
                return (False, "", "No leader found")

        logger.info("Connecting to leader %s", self.leader_id)
        try:
            with grpc.insecure_channel(self.kv_cluster[self.leader_id]) as channel:
                stub = kv_pb2_grpc.KVServiceStub(channel)
                # pylint: disable=no-member
                reply = stub.Get(kv_pb2.GetArgs(key=key), timeout=GET_TIMEOUT)
        except grpc.RpcError as err:
            if err.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                logger.error("RPC TIMEOUT")
                return (False, "", "RPC TIMEOUT")
            if err.code() == grpc.StatusCode.UNAVAILABLE:
                logger.error("RPC Node %s unavailable", self.leader_id)
                self.leader_id = -1
                return self.get(key)

            logger.error(
                "Error occurred while sending RPC to Node %s. Code: %s. Error: %s",
                self.leader_id,
                str(err.code()),
                str(err),
            )
            return (False, "", str(err.args))

        if not reply.status:
            logger.error("Server Error. %s, leaderId %s", reply.error, reply.leaderId)
            if reply.error in (
                KVErrors.LEADER_UNKNOWN.value,
                KVErrors.RAFT_ERROR.value,
            ):
                return (False, "", reply.error)

            if reply.error == KVErrors.NOT_LEADER.value:
                logger.info(
                    "%s is not the leader. Leader is %s. Retrying..",
                    self.leader_id,
                    reply.leaderId,
                )
                self.leader_id = reply.leaderId
                return self.get(key)

            return (False, "", reply.error)

        if reply.status:
            logger.info(
                'Got Reply. key: %s value: "%s" error: %s',
                key,
                reply.value,
                reply.error,
            )
        return (reply.status, reply.value, reply.error)

    def set(self, key: str, value: str) -> typing.Tuple[bool, str]:
        """Set RPC client"""
        logger.info("Starting set %s %s", key, value)

        if self.leader_id == -1:
            logger.debug("Leader unknown. Trying to get leader")
            if self.get_leader() == -1:
                return (False, "No leader found")

        logger.info("Connecting to leader %s", self.leader_id)
        try:
            with grpc.insecure_channel(self.kv_cluster[self.leader_id]) as channel:
                stub = kv_pb2_grpc.KVServiceStub(channel)
                # pylint: disable=no-member
                reply = stub.Set(
                    kv_pb2.SetArgs(key=key, value=value), timeout=SET_TIMEOUT
                )
        except grpc.RpcError as err:
            if err.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                logger.error("RPC TIMEOUT")
                return (False, "RPC TIMEOUT")
            if err.code() == grpc.StatusCode.UNAVAILABLE:
                logger.error("RPC Node %s unavailable", self.leader_id)
                self.leader_id = -1
                return self.set(key, value)

            logger.error(
                "Error occurred while sending RPC to Node %s. Code: %s. Error: %s",
                self.leader_id,
                str(err.code()),
                str(err),
            )
            return (False, str(err.args))

        if not reply.status:
            logger.error("Server Error. %s, leaderId %s", reply.error, reply.leaderId)
            if reply.error in (KVErrors.LEADER_UNKNOWN, KVErrors.RAFT_ERROR):
                return (False, reply.error)

            if reply.error == KVErrors.NOT_LEADER:
                logger.info(
                    "%s is not the leader. Leader is %s. Retrying..",
                    self.leader_id,
                    reply.leaderId,
                )
                self.leader_id = reply.leaderId
                return self.set(key, value)
        return (reply.status, reply.error)

    def go_cmd_mode(self):
        """Command line"""
        while True:
            cmd = input(
                "\n(cls-clear 0-Close 1-ClusterMembers 2-askForLeader 3-setLeader set<k,v> get<k>: "
            )
            if cmd == "":
                continue
            if cmd == "cls":
                os.system("clear")
                continue

            if "set" in cmd:
                words = cmd.split(" ")
                if (
                    len(words) != 3
                    or words[0] != "set"
                    or words[1] == ""
                    or words[2] == ""
                ):
                    print(f"Invalid set command {words}")
                    continue
                key, value = words[1], words[2]
                res, err = self.set(key, value)
                if res:
                    print("SUCCESS")
                else:
                    print(f"FAILED. {err}")
                continue

            if "get" in cmd:
                words = cmd.split(" ")
                if len(words) != 2 or words[0] != "get" or words[1] == "":
                    print(f"Invalid get command {words}")
                    continue
                key = words[1]
                res, value, err = self.get(key)
                if res:
                    print(f'SUCCESS. {key} "{value}" {err}')
                else:
                    print(f"FAILED. {err}")
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
            if cmd == 3:
                node_id = input("Node: ")
                if (not node_id.isdigit()) or (
                    not (0 <= int(node_id) < len(self.kv_cluster))
                ):
                    continue
                self.leader_id = int(node_id)


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
