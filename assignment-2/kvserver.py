"""
KV Server
"""
from concurrent import futures
import enum
import typing
import threading
import time
import grpc

import kv_pb2
import kv_pb2_grpc

import logger
import raft
import command
import util

MAX_WORKERS = 2

SET_TIMEOUT = 120  # Seconds
GET_TIMEOUT = 120  # Seconds


class KVErrors(enum.Enum):
    """Errors"""

    NO_ERROR = ""
    NOT_LEADER = "NOT_LEADER"  # leaderId is set.
    LEADER_UNKNOWN = "LEADER_UNKNOWN"  # leaderId is set to -1
    LEADER_WITHOUT_LEASE = "LEADER_WITHOUT_LEASE"  #
    RAFT_ERROR = "RAFT_ERROR"  # some error in the raft module.
    KEY_NOT_PRESENT = "KEY_NOT_PRESENT"
    OP_TIME_OUT = "OP_TIME_OUT"
    CMD_CHANGED = (
        "CMD_CHANGED"  # Happens while consolidating logs after network partition heals
    )


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
        self.server = None
        self.raft = None
        self.server_port = kv_cluster[self.my_id].split(":")[1]
        self.active = False

        self.apply_mutex = threading.Lock()
        self.applied_indices = {}  # Applied in Raft but not in the store

        self.mutex = threading.Lock()
        self.data_store = {}  # Actual kv store

    def set_state_machine(self, raft_obj: raft.Raft) -> None:
        """Sets raft"""
        self.raft = raft_obj

    def __serve(self) -> None:
        """start services"""
        self.active = True
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

    def apply(
        self, indices: typing.List[int], logs: typing.List[command.Command]
    ) -> bool:
        """Applies Raft's logs to the kv store"""
        with self.apply_mutex:
            new_logs = dict(zip(indices, logs))
            self.applied_indices.update(new_logs)
            new_logs_str = (
                "{"
                + ", ".join([f"'{key}': {value}" for key, value in new_logs.items()])
                + "}"
            )
            applied_logs_str = (
                "{"
                + ", ".join(
                    [f"'{key}': {value}" for key, value in self.applied_indices.items()]
                )
                + "}"
            )
            logger.DUMP_LOGGER.debug(
                "Logs applied. new_logs %s applied_logs %s",
                new_logs_str,
                applied_logs_str,
            )

            with self.mutex:
                for _, cmd in new_logs.items():
                    if cmd.cmd == command.CommandType.NOOP:
                        continue
                    if cmd.cmd == command.CommandType.SET:
                        self.data_store[cmd.key] = cmd.value
                logger.DUMP_LOGGER.debug(
                    "data_store: {%s}",
                    ", ".join(
                        [f"'{key}': {value}" for key, value in self.data_store.items()]
                    ),
                )

    def __is_command_applied(
        self, idx: int, cmd: command.Command
    ) -> typing.Tuple[bool, bool]:
        """Is the command applied by the Raft module. Returns (replicated, same command)"""
        with self.apply_mutex:
            for applied_idx, applied_cmd in self.applied_indices.items():
                if applied_idx == idx:
                    if cmd == applied_cmd:
                        return True, True
                    logger.DUMP_LOGGER.info(
                        "Command Missmatch idx %s originalCmd [%s] storedCmd [%s]",
                        idx,
                        str(cmd),
                        str(applied_cmd),
                    )
                    return True, False
        return False, False

    def __wait_for_apply(
        self, idx: int, cmd: command.Command
    ) -> typing.Tuple[bool, str]:
        """Wait for apply. Returns (status, error)"""
        start_time = util.current_time_second()
        err = KVErrors.OP_TIME_OUT.value
        while self.active:
            time.sleep(0.25)
            replicated, same_cmd = self.__is_command_applied(idx, cmd)
            if replicated:
                if same_cmd:
                    # TODO: Delete from applied_dict
                return (
                    same_cmd,
                    (KVErrors.NO_ERROR if same_cmd else KVErrors.CMD_CHANGED).value,
                )

            curr_time = util.current_time_second()
            if (start_time + SET_TIMEOUT) <= curr_time:
                break
        return False, err

    def __get_value(self, key: str) -> typing.Tuple[bool, str]:
        """Returns the value if present"""
        with self.mutex:
            if key in self.data_store:
                return True, self.data_store[key]
        return False, ""

    def Set(self, request: kv_pb2.SetArgs, context) -> kv_pb2.SetReply:
        """KV Set RPC"""
        logger.DUMP_LOGGER.info("START SET %s %s", request.key, request.value)
        cmd = command.Command(
            command.CommandType.SET, term=-1, key=request.key, value=request.value
        )
        log_idx, log_term, is_leader, has_lease, leader_id = self.raft.write_to_raft(
            cmd
        )
        # Update the term, as the write_to_raft clones the cmd
        cmd.set_term(log_term)
        if not is_leader:
            error = KVErrors.NOT_LEADER
            if leader_id == -1:
                error = KVErrors.LEADER_UNKNOWN
            return kv_pb2.SetReply(status=False, error=error.value, leaderId=leader_id)

        if not has_lease:
            error = KVErrors.LEADER_WITHOUT_LEASE
            return kv_pb2.SetReply(status=False, error=error.value, leader_id=leader_id)

        status, error = self.__wait_for_apply(log_idx, cmd)
        logger.DUMP_LOGGER.info(
            "END SET %s %s status %s error: %s",
            request.key,
            request.value,
            status,
            error,
        )
        return kv_pb2.SetReply(status=status, error=error)

    def Get(self, request: kv_pb2.GetArgs, context) -> kv_pb2.GetReply:
        """KV Get RPC"""
        is_leader, has_lease, leader_id = self.raft.is_leader_with_lease()
        value = None
        if is_leader and has_lease:
            logger.DUMP_LOGGER.debug("Get Request. key: %s", request.key)
            status, value = self.__get_value(request.key)
            logger.DUMP_LOGGER.debug(
                "Get Request. key: %s value: %s. status: %s", request.key, value, status
            )
            if status:
                return kv_pb2.GetReply(status=True, value=value)
            return kv_pb2.GetReply(status=False, error=KVErrors.KEY_NOT_PRESENT.value)

        error = KVErrors.NOT_LEADER
        if is_leader:
            if not has_lease:
                error = KVErrors.LEADER_WITHOUT_LEASE
        else:
            if leader_id == -1:
                error = KVErrors.LEADER_UNKNOWN
        return kv_pb2.GetReply(
            status=False, value="", error=error.value, leaderId=leader_id
        )

    def GetLeader(
        self, request: kv_pb2.GetLeaderArgs, context
    ) -> kv_pb2.GetLeaderReply:
        """KV GetLeader RPC"""
        return kv_pb2.GetLeaderReply(leaderId=self.raft.get_leader_id(), error="")
