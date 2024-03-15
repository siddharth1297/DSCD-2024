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
        self.leaseInterval = 0
        self.votes_received = 0

        self.executor = futures.ThreadPoolExecutor(len(self.peers) - 1)
        self.timer_thread = threading.Thread(target=self.__timer)

        self.__serve()
        self.__update_timer(self.__election_timeout())
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
        self.executor.shutdown(wait=False, cancel_futures=True)

    def __get_last_log_index(self) -> int:
        """Returns last log index"""
        return len(self.logs) - 1

    def __get_last_log_term(self) -> int:
        """Returns last log term"""
        last_index = self.__get_last_log_index()
        return -1 if last_index == -1 else self.logs[last_index].term

    def __change_state_to_leader(self):
        """Change state to leader"""
        pass

    def __change_state_to_follower(self, term: int, lease_remaining_duration: int):
        """Change state to follower"""
        pass

    def RequestVote(
        self, request: raft_pb2.RequestVoteArgs, context
    ) -> raft_pb2.RequestVoteReply:
        """RPC RequestVote"""
        with self.mutex:
            reply = raft_pb2.RequestVoteReply(
                voteGranted=True, term=-1, leaseRemainingDuration=0
            )
            reply.voteGranted = True
            if reply.voteGranted:
                logger.DUMP_LOGGER.info(
                    "Vote granted for Node %s in term %s.",
                    request.candidateId,
                    request.term,
                )
                return reply
            logger.DUMP_LOGGER.error(
                "Vote denied for Node %s in term %s.", request.candidateId, request.term
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
        args.leaseIntervalDuration = self.leaseInterval

        # Broadcast
        for peer_id in range(len(self.peers)):
            if peer_id == self.my_id:
                continue
            self.executor.submit(self.__send_request_vote(peer_id, args))

    def __send_request_vote(self, node_id: int, args: raft_pb2.RequestVoteArgs) -> None:
        """Sends request vote"""
        logger.DUMP_LOGGER.info(
            "Sending RequestVote to id %s address %s args: %s",
            node_id,
            self.peers[node_id],
            args,
        )
        try:
            with grpc.insecure_channel(self.peers[node_id]) as channel:
                stub = raft_pb2_grpc.RaftServiceStub(channel)
                reply = stub.RequestVote(args)
        except grpc.RpcError as err:
            logger.DUMP_LOGGER.error(
                "Error occurred while sending RPC to Node %s. Error: %s",
                node_id,
                str(err),
            )
            return
        with self.mutex:
            if (self.state != State.CANDIDATE) or (self.currentTerm != args.term):
                # Reply comes after a long time
                return
            # TODO: Even if it is the LEADER, get the lease duration. So accept the lease values
            if not reply.voteGranted:
                self.__change_state_to_follower(
                    reply.term, reply.leaseRemainingDuration
                )
                return

            self.votes_received += 1
            if self.votes_received > (len(self.peers) / 2):
                self.__change_state_to_leader()
            # Update lease

    def __send_heartbeat(self) -> None:
        """Sends heartbeat to peers"""
        return

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
            time.sleep(1)  # Sleep for 1 S
            if not self.active:
                break
            with self.mutex:
                curr_time = util.current_time_second()
                if (self.last_heartbeat + self.wait_duration) <= curr_time:
                    if self.state == State.LEADER:
                        self.__send_heartbeat()
                        self.__update_timer(HEARTBEAT_TIMEOUT)
                    else:
                        self.__initiate_election()
                        self.__update_timer(self.__election_timeout())
