"""
Raft
"""
from concurrent import futures
import enum
import random
import threading
import time
import grpc

import raft_pb2_grpc
import raft_pb2
import util

import logger

MAX_WORKERS = 2

HEARTBEAT_TIMEOUT = 1  # Seconds
ELECTION_TIMEOUT_RANGE = (5, 10)  # Second
LEASE_TIMEOUT = 10  # Second


class State(enum.Enum):
    """Raft State"""

    LEADER = "LEADER"
    FOLLOWER = "FOLLOWER"
    CANDIDATE = "CANDIDATE"


class Raft(raft_pb2_grpc.RaftServiceServicer):
    """Raft"""

    # pylint: disable=too-many-instance-attributes,invalid-name

    def __init__(self, node_id: int, peers: list[str]):
        self.my_id = node_id
        self.peers = peers
        self.server_port = peers[self.my_id].split(":")[1]
        self.mutex = threading.Lock()
        self.server = None

        ## Raft state
        # Persistent states on server
        self.state = State.FOLLOWER
        self.currentTerm = 0
        self.votedFor = -1
        self.logs = []

        # Volatile states on all servers
        self.commitIndex = 0
        self.lastApplied = 0

        # Volatile state on leadders
        self.nextIndex = 0
        self.matchIndex = []

        # Auxiliary data structures
        self.active = True
        self.last_heartbeat, self.wait_duration = 0, 0
        self.votes_received = 0

        self.has_lease = False  # If this node has lease
        self.leaseInterval = 0  # Lease expire time duration
        # For a leader, it is the time when it acquires the lease
        # For a follower, it is the time when it received the last lease information
        self.lease_access_time = 0

        self.leaderId = -1

        self.executor = futures.ThreadPoolExecutor(len(self.peers) - 1)
        self.timer_thread = threading.Thread(target=self.__timer)

        self.__change_state_to_follower(self.currentTerm, 0, "StartUp")
        self.__serve()
        self.timer_thread.start()

    def __serve(self) -> None:
        """start services"""
        self.server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=MAX_WORKERS),
            options=(("grpc.so_reuseport", 0),),
        )
        raft_pb2_grpc.add_RaftServiceServicer_to_server(self, self.server)
        self.server.add_insecure_port("0.0.0.0" + ":" + self.server_port)
        self.server.start()

    def stop(self) -> None:
        """stop raft"""
        self.active = False
        self.timer_thread.join()
        self.server.stop(1.5).wait()
        self.executor.shutdown(wait=True, cancel_futures=True)

    def __update_lease(self, access_time: int, lease_interval: int) -> None:
        """Updates lease interval"""
        self.lease_access_time = access_time
        self.leaseInterval = max(self.leaseInterval, lease_interval)

    def __get_lease_duration(self):
        """Returns lease reamining duration"""
        return (
            max(
                0,
                self.lease_access_time
                + self.leaseInterval
                - util.current_time_second(),
            )
            if self.has_lease
            else 0
        )

    def __check_lease(self, curr_time) -> bool:
        """Updates lease, if conditions satisfy"""
        has_lease = False
        if (curr_time - self.lease_access_time) > self.leaseInterval:
            if self.state == State.LEADER:
                if self.has_lease:
                    self.has_lease = False
                    self.__change_state_to_follower(self.currentTerm, 0, "LeaseExapire")
                else:
                    # Acquire lease
                    # TODO: Append NO-OP
                    self.has_lease = True
                    self.lease_access_time = curr_time
                    self.leaseInterval = LEASE_TIMEOUT
                    self.__send_heartbeat()
                    has_lease = True
            else:
                if self.has_lease:
                    self.has_lease = False
        return has_lease

    def __get_last_log_index(self) -> int:
        """Returns last log index"""
        return len(self.logs) - 1

    def __get_last_log_term(self) -> int:
        """Returns last log term"""
        last_index = self.__get_last_log_index()
        return -1 if last_index == -1 else self.logs[last_index].term

    def __change_state_to_leader(self):
        """Change state to leader"""
        self.state = State.LEADER
        logger.DUMP_LOGGER.info(
            "Node %s became the leader for term %s.", self.my_id, self.currentTerm
        )
        if not self.__check_lease(util.current_time_second()):
            self.__send_heartbeat()

    def __change_state_to_follower(
        self, term: int, lease_remaining_duration: int, why: str
    ):
        """Change state to follower"""
        self.state = State.FOLLOWER
        self.currentTerm = term
        self.__update_lease(util.current_time_second(), lease_remaining_duration)
        self.__update_timer(self.__election_timeout())
        logger.DUMP_LOGGER.debug(
            "Changed state to Follower %s, term: %s", why, self.currentTerm
        )

    def __is_log_uptodate(self, peer_id: int) -> bool:
        """Returns if log is uptodate"""
        return True

    def RequestVote(
        self, request: raft_pb2.RequestVoteArgs, context
    ) -> raft_pb2.RequestVoteReply:
        """RPC RequestVote"""

        with self.mutex:
            reply = raft_pb2.RequestVoteReply(
                voteGranted=False,
                term=-1,
                leaseRemainingDuration=self.__get_lease_duration(),
            )
            if request.term < self.currentTerm:
                reply.term = self.currentTerm
                logger.DUMP_LOGGER.error(
                    "Vote denied for Node %s in term %s. LowerTerm",
                    request.candidateId,
                    request.term,
                )
                return reply

            if self.votedFor in (-1, request.candidateId) and self.__is_log_uptodate(
                request.candidateId
            ):
                reply.voteGranted = True
                self.currentTerm = request.term
                self.votedFor = request.candidateId
                logger.DUMP_LOGGER.info(
                    "Vote granted for Node %s in term %s.",
                    request.candidateId,
                    request.term,
                )
                self.__update_timer(self.__election_timeout())
            else:
                logger.DUMP_LOGGER.error(
                    "Vote denied for Node %s in term %s.",
                    request.candidateId,
                    request.term,
                )
        return reply

    def __initiate_election(self) -> None:
        """Initiates election"""
        logger.DUMP_LOGGER.info(
            "Node %d election timer timed out, Starting election.", self.my_id
        )
        self.state = State.CANDIDATE
        self.currentTerm += 1
        self.votedFor = self.my_id
        self.votes_received = 1

        # pylint: disable=no-member
        args = raft_pb2.RequestVoteArgs()
        args.term = self.currentTerm
        args.candidateId = self.my_id
        args.lastLogIndex = self.__get_last_log_index()
        args.lastLogTerm = self.__get_last_log_term()

        # Broadcast
        for peer_id in range(len(self.peers)):
            if peer_id == self.my_id:
                continue
            self.executor.submit(self.__send_request_vote, peer_id, args)

    def __send_request_vote(self, node_id: int, args: raft_pb2.RequestVoteArgs) -> None:
        """Sends request vote"""
        logger.DUMP_LOGGER.info(
            "Sending RequestVote to id %s address %s",
            node_id,
            self.peers[node_id]
            # args,
        )
        try:
            with grpc.insecure_channel(self.peers[node_id]) as channel:
                stub = raft_pb2_grpc.RaftServiceStub(channel)
                reply = stub.RequestVote(args)
        except grpc.RpcError as err:
            logger.DUMP_LOGGER.error(
                "Error occurred while sending RPC to Node %s. RequestVote. Error: %s",
                node_id,
                str(err.args),
            )
            return
        with self.mutex:
            if (self.state != State.CANDIDATE) or (self.currentTerm != args.term):
                # Reply comes after a long time
                return

            if not reply.voteGranted:
                if self.currentTerm < reply.term:
                    # It is another term, so the other node has updated information about the lease
                    self.__change_state_to_follower(
                        reply.term, reply.leaseRemainingDuration, "HigherTermExists"
                    )
                else:
                    self.__update_lease(
                        util.current_time_second(),
                        max(self.leaseInterval, reply.leaseRemainingDuration),
                    )
                return
            self.__update_lease(
                util.current_time_second(),
                max(self.leaseInterval, reply.leaseRemainingDuration),
            )
            self.votes_received += 1
            if self.votes_received > (len(self.peers) / 2):
                self.__change_state_to_leader()

    def AppendEntries(
        self, request: raft_pb2.AppendEntriesArgs, context
    ) -> raft_pb2.AppendEntriesReply:
        """RPC AppendEntries"""
        with self.mutex:
            reply = raft_pb2.AppendEntriesReply(term=self.currentTerm, success=False)
            if self.currentTerm > request.term:
                return reply

            if self.state == State.CANDIDATE:
                self.__change_state_to_follower(
                    request.term, request.leaseRemainingDuration, "HBTFromHigherTerm"
                )
                self.leaderId = request.leaderId
            self.__update_timer(self.__election_timeout())
            reply.success = True
        return reply

    def send_append_entries(
        self, node_id: int, args: raft_pb2.AppendEntriesArgs, heartbeat: bool
    ) -> None:
        """Sends append entry messages"""
        success = False
        # retry, for non heartbeat messages
        while self.active and not success:
            try:
                with grpc.insecure_channel(self.peers[node_id]) as channel:
                    stub = raft_pb2_grpc.RaftServiceStub(channel)
                    reply = stub.AppendEntries(args)
                    success = True
            except grpc.RpcError as err:
                logger.DUMP_LOGGER.error(
                    "Error occurred while sending RPC to Node %s. AppendEntries. Error: %s",
                    node_id,
                    str(err.args),
                )
            if heartbeat:
                return

        if not self.active:
            return

    def __send_heartbeat(self) -> None:
        """Sends heartbeat to peers"""
        # TODO: Add lease time
        args = raft_pb2.AppendEntriesArgs(
            term=self.currentTerm,
            leaderId=self.my_id,
            prevLogIndex=self.__get_last_log_index(),
            prevLogTerm=self.__get_last_log_term(),
            leaderCommit=self.commitIndex,
        )
        # Broadcast
        for peer_id in range(len(self.peers)):
            if peer_id == self.my_id:
                continue
            self.executor.submit(self.send_append_entries, peer_id, args, True)
        self.__update_timer(HEARTBEAT_TIMEOUT)

    def __election_timeout(self) -> int:
        """Election timeout duration"""
        return random.randint(ELECTION_TIMEOUT_RANGE[0], ELECTION_TIMEOUT_RANGE[1])

    def __update_timer(self, wait_duration: int) -> None:
        """Updates timer"""
        self.last_heartbeat = util.current_time_second()
        self.wait_duration = wait_duration

    def __timer(self) -> None:
        """Timer"""
        # sleep_time = self.wait_duration
        while self.active:
            time.sleep(2)  # Sleep for 1 S
            if not self.active:
                break
            with self.mutex:
                curr_time = util.current_time_second()
                # self.__check_lease(curr_time)
                if (self.last_heartbeat + self.wait_duration) <= curr_time:
                    if self.state == State.LEADER:
                        self.__send_heartbeat()
                        self.__update_timer(HEARTBEAT_TIMEOUT)
                    else:
                        self.__initiate_election()
                        self.__update_timer(self.__election_timeout())
