"""
KV Server
"""
from concurrent import futures
import enum
import time
import grpc

import kv_pb2
import kv_pb2_grpc

import logger
import raft
import command

MAX_WORKERS = 2

class KVErrors(enum.Enum):
    """Errors"""

    NOT_LEADER = "NOT_LEADER"           # leaderId is set.
    LEADER_UNKNOWN = "LEADER_UNKNOWN"   # leaderId is set to -1
    LEADER_WITHOUT_LEASE = "LEADER_WITHOUT_LEASE" #
    RAFT_ERROR = "RAFT_ERROR"           # some error in the raft module.


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

    def Set(self, request: kv_pb2.SetArgs, context) -> kv_pb2.SetReply:
        """KV Set RPC"""
        logger.DUMP_LOGGER.info("START SET %s %s", request.key, request.value)
        cmd = command.Command(command.CommandType.SET, term=-1, key=request.key, value=request.value)
        log_idx, log_term, is_leader, has_lease, leader_id = self.raft.write_to_raft(cmd)
        if not is_leader:
            error = KVErrors.NOT_LEADER
            if leader_id == -1:
                error = KVErrors.LEADER_UNKNOWN
            return kv_pb2.SetReply(status=False, error=error.value, leader_id=leader_id)
        
        if not has_lease:
            error = KVErrors.LEADER_WITHOUT_LEASE
            return kv_pb2.SetReply(status=False, error=error.value, leader_id=leader_id)
        
        logger.DUMP_LOGGER.info("END SET %s %s", request.key, request.value)
        return kv_pb2.SetReply(status=True)

    def Get(self, request: kv_pb2.GetArgs, context) -> kv_pb2.GetReply:
        """KV Get RPC"""
        return kv_pb2.GetReply()

    def GetLeader(
        self, request: kv_pb2.GetLeaderArgs, context
    ) -> kv_pb2.GetLeaderReply:
        """KV GetLeader RPC"""
        return kv_pb2.GetLeaderReply(leaderId=self.raft.get_leader_id(), error="")
