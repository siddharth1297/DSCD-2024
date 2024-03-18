"""
KV Server
"""
from concurrent import futures
import grpc

import kv_pb2
import kv_pb2_grpc

import logger
import raft

MAX_WORKERS = 2


class KVServer:
    """KV Server"""

    def __init__(
        self,
        node_id: int,
        raft_cluster: list[str],
        kv_cluster: list[str],
    ):
        self.my_id = node_id
        self.raft_cluster = raft_cluster
        self.kv_cluster = kv_cluster
        self.data_store = {}
        self.server = None
        self.raft = None
        self.server_port = kv_cluster[self.my_id].split(":")[1]

    def set_state_machine(self, raft_obj: raft.Raft) -> None:
        """Sets raft"""
        self.raft = raft_obj

    def __serve(self) -> None:
        """start services"""
        self.server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=MAX_WORKERS),
            options=(("grpc.so_reuseport", 0),),
        )
        kv_pb2_grpc.add_KVServiceServicer_to_server(self, self.server)
        self.server.add_insecure_port("0.0.0.0" + ":" + self.server_port)
        self.server.start()

    def start(self) -> bool:
        """Starts services"""
        self.__serve()
        logger.DUMP_LOGGER.info("KV Service Started for node %s", self.my_id)
        return True

    def stop(self) -> None:
        """stops KV service"""
        self.server.stop(1).wait()

    def Put(self, request: kv_pb2.PutArgs, context) -> kv_pb2.PutReply:
        """KV Put RPC"""
        return kv_pb2.PutReply()

    def Get(self, request: kv_pb2.GetArgs, context) -> kv_pb2.GetReply:
        """KV Get RPC"""
        return kv_pb2.GetReply()

    def GetLeader(
        self, request: kv_pb2.GetLeaderArgs, context
    ) -> kv_pb2.GetLeaderReply:
        """KV GetLeader RPC"""
        return kv_pb2.GetLeaderReply(leaderId=self.raft.get_leader_id(), error="")
