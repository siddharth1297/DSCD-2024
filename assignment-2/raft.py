"""
Raft
"""
from concurrent import futures
import enum
import random
import threading
import time
import typing
import grpc

import raft_pb2_grpc
import raft_pb2
import util

import command
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


class LogEntry:
    """Log Entry in Raft's log"""

    def __init__(self, term: int, cmd: str):
        self.term = term
        self.command = cmd

    def __str__(self):
        return f"{self.term}:{self.command}"


class Raft(raft_pb2_grpc.RaftServiceServicer):
    """Raft"""

    # pylint: disable=too-many-instance-attributes,invalid-name

    def __init__(self, node_id: int, peers: list[str], kv):
        self.my_id = node_id
        self.peers = peers
        self.server_port = peers[self.my_id].split(":")[1]
        self.mutex = threading.Lock()
        self.server = None
        self.kv = kv

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
        self.nextIndex = []
        self.matchIndex = [0] * len(self.logs)

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
        logger.DUMP_LOGGER.info("Raft Service Started for node %s", self.my_id)

    def stop(self) -> None:
        """stop raft"""
        self.active = False
        self.timer_thread.join()
        self.server.stop(1.5).wait()
        self.executor.shutdown(wait=True, cancel_futures=True)

    def get_leader_id(self) -> int:
        """Returns the leader id known to this node"""
        with self.mutex:
            return self.leaderId

    def write_to_raft(self, cmd: command.Command) -> typing.Tuple[int, int, bool]:
        """
        Writes to the state machine and replicates.
        Returns: (LogIndex, term, isLeader with Lease)
        """
        with self.mutex:
            if self.state == State.LEADER:
                # TODO: Add Lease
                return (*self.__append_entry(cmd), True)
        return (-1, -1, False)

    def __append_entry(self, cmd: command.Command) -> typing.Tuple[int, int]:
        """Appends command to log and returns log index and term number"""
        self.logs.append(command)
        term = self.currentTerm
        index = len(self.logs) - 1
        cmd.set_term(term)
        logger.DUMP_LOGGER.info(
            "Appended command [%s] at index %s term %s", cmd, index, term
        )
        # persists here
        return (index, term)

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

    def __acquire_lease(self, lease_acquire_time: int) -> None:
        """Acquire Lease"""
        logger.DUMP_LOGGER.info("New Leader %s acquired lease.", self.my_id)
        # TODO: Append NO-OP
        self.has_lease = True
        self.lease_access_time = lease_acquire_time
        self.leaseInterval = LEASE_TIMEOUT
        self.__send_heartbeat()

    def __renew_lease(self, lease_acquire_time) -> bool:
        """Renew Lease, if possible"""
        assert (
            self.state == State.LEADER
        ), f"State Must be leader. But it is {self.state} at node {self.my_id}"
        renewed = False
        if self.has_lease or (
            (lease_acquire_time - self.lease_access_time) > self.leaseInterval
        ):
            logger.DUMP_LOGGER.info("New Leader %s renewed lease.", self.my_id)
            self.__acquire_lease(lease_acquire_time)
            renewed = True
        else:
            logger.DUMP_LOGGER.info(
                "New Leader %s waiting for Old Leader Lease to timeout.", self.my_id
            )
        return renewed

    def __check_lease(self, curr_time) -> bool:
        """Updates lease, if conditions satisfy"""
        has_lease = False
        if self.state == State.LEADER:
            if self.has_lease:
                # Check if lease expired
                if (curr_time - self.lease_access_time) > self.leaseInterval:
                    self.has_lease = False
                    logger.DUMP_LOGGER.info(
                        "Leader %s lease renewal failed. Stepping Down.", self.my_id
                    )
                    self.__change_state_to_follower(
                        self.currentTerm, 0, "LeaseExapired"
                    )
            else:
                self.__renew_lease(curr_time)

        if (curr_time - self.lease_access_time) > self.leaseInterval:
            if self.state == State.LEADER:
                if self.has_lease:
                    self.has_lease = False
                    self.__change_state_to_follower(self.currentTerm, 0, "LeaseExapire")
                else:
                    self.__acquire_lease(curr_time)
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
        self.leaderId = self.my_id
        logger.DUMP_LOGGER.info(
            "Node %s became the leader for term %s.", self.my_id, self.currentTerm
        )
        self.__append_entry(command.Command(command.CommandType.NOOP))
        self.nextIndex = [len(self.logs)] * len(self.peers)
        # self.matchIndex =  TODO: Set it
        self.__send_heartbeat()
        # if not self.__renew_lease(util.current_time_second()):
        #    self.__send_heartbeat()

    def __change_state_to_follower(
        self, term: int, lease_remaining_duration: int, why: str
    ):
        """Change state to follower"""
        self.state = State.FOLLOWER
        self.currentTerm = term
        self.votedFor = -1
        self.leaderId = -1
        self.__update_lease(util.current_time_second(), lease_remaining_duration)
        self.__update_timer(self.__election_timeout())
        logger.DUMP_LOGGER.debug(
            "Changed state to Follower %s, term: %s", why, self.currentTerm
        )

    def __is_log_uptodate(self, last_log_index: int, last_log_term: int) -> bool:
        """
        Returns if log is up to date
        Returns true if
            If candidate's last term is more than my term
            or if last term matches, then candidate's log index is as large as mine
        """
        my_last_log_index = self.__get_last_log_index()
        my_last_log_term = self.__get_last_log_term()
        return (last_log_term > my_last_log_term) or (
            (last_log_term == my_last_log_term)
            and (last_log_index >= my_last_log_index)
        )

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
                logger.DUMP_LOGGER.info(
                    "Vote denied for Node %s in term %s. LowerTerm",
                    request.candidateId,
                    request.term,
                )
                return reply

            if request.term > self.currentTerm:
                # Higher term node is candidate
                self.__change_state_to_follower(
                    request.term, self.leaseInterval, "RequestVoteWithHigherTerm"
                )
                self.__update_timer(self.__election_timeout())

            if self.votedFor in (-1, request.candidateId) and self.__is_log_uptodate(
                request.lastLogIndex, request.lastLogTerm
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
                    "Vote denied for Node %s in term %s. AlreadyVotedFor: %s logUptodate: %s",
                    request.candidateId,
                    request.term,
                    self.votedFor,
                    self.__is_log_uptodate(request.lastLogIndex, request.lastLogTerm),
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
        logger.DUMP_LOGGER.info("APPENDENTRIES======")
        with self.mutex:
            reply = raft_pb2.AppendEntriesReply(
                term=self.currentTerm, success=False, conflictIndex=-1, conflictTerm=-1
            )
            if self.currentTerm > request.term:
                return reply

            if self.state == State.CANDIDATE:
                self.__change_state_to_follower(
                    request.term, request.leaseRemainingDuration, "HBTFromHigherTerm"
                )
            # Update the following
            self.leaderId = request.leaderId
            self.__update_timer(self.__election_timeout())

            logger.DUMP_LOGGER.info(
                "prevLogindex: %s term: %s", request.prevLogIndex, request.prevLogTerm
            )
            if request.prevLogIndex != -1 and request.prevLogTerm != -1:
                # TODO: Remove the above condition after implementing lease
                # 2. Reply false if log doesn’t contain an entry at prevLogIndex
                #  whose term matches prevLogTerm (§5.3)
                if len(self.logs) <= request.prevLogIndex:
                    reply.conflictIndex = len(self.logs)
                elif self.logs[request.prevLogIndex].term != request.prevLogTerm:
                    reply.conflictTerm = self.logs[request.prevLogIndex].term
                    idx = request.prevLogIndex
                    while idx >= 0 and self.logs[idx].term == reply.conflictTerm:
                        reply.conflictIndex = idx
                        idx -= 1

                if reply.conflictIndex != -1 or reply.conflictTerm != -1:
                    logger.DUMP_LOGGER.info(
                        "AppendEntries Index match Conflicting. Term: %s startIndex: %s",
                        reply.conflictTerm,
                        reply.conflictIndex,
                    )
                    reply.success = False
                    return reply
            """ 
            if (len(self.logs) <= request.prevLogIndex) or (self.logs[request.prevLogIndex].term != request.prevLogTerm):
                reply.conflictIndex = 0
                if len(self.logs) > 0:
                    reply.conflictTerm = self.logs[request.prevLogIndex].term if request.prevLogIndex
                    
                    idx = request.prevLogIndex
                    while idx>=0 and self.logs[idx].term == reply.conflictTerm:
                        reply.conflictIndex = idx
                        idx -= 1
                
                logger.DUMP_LOGGER.info("AppendEntries Index match Conflicting. Term: %s startIndex: %s", reply.conflictTerm, reply.conflictIndex)
                reply.success = False
                return reply
            """
            logger.DUMP_LOGGER.info("AppendEntryAccepted")
            reply.success = True
        return reply

    def send_append_entries(
        self, node_id: int, args: raft_pb2.AppendEntriesArgs, heartbeat: bool
    ) -> None:
        """Sends append entry messages"""
        success = False
        # retry, for lease interval
        while self.active and self.state == State.LEADER and not success:
            try:
                with grpc.insecure_channel(self.peers[node_id]) as channel:
                    stub = raft_pb2_grpc.RaftServiceStub(channel)
                    reply = stub.AppendEntries(args)
                    success = True
            except grpc.RpcError as err:
                logger.DUMP_LOGGER.error(
                    "Error occurred while sending RPC to Node %s. AppendEntries. Error: %s",
                    node_id,
                    str(err),
                    # str(err.args),
                )
                if heartbeat:
                    # Don't try for heartbeat message
                    return
        with self.mutex:
            if not self.active or self.state != State.LEADER:
                # Lease
                return
            if reply.success:
                logger.DUMP_LOGGER.debug(
                    "Success AppendEntries at %s from %s.", self.my_id, node_id
                )
                return

            if reply.term > self.currentTerm:
                logger.DUMP_LOGGER.debug(
                    "Fail AppendEntries at %s from %s. HigherTermThanMe",
                    self.my_id,
                    node_id,
                )
                self.__change_state_to_follower(
                    reply.term,
                    self.lease_access_time,
                    "AppendEntryResponseFromHigherTerm",
                )
                return

            logger.DUMP_LOGGER.debug(
                "Fail AppendEntries at %s from %s. ConflictIndex %s ConflictTerm %s",
                self.my_id,
                node_id,
                reply.conflictIndex,
                reply.conflictTerm,
            )

    def __send_heartbeat(self) -> None:
        """Sends heartbeat to peers"""
        logger.DUMP_LOGGER.info(
            "Leader %s sending heartbeat & Renewing Lease", self.my_id
        )
        for peer_id in range(len(self.peers)):
            if peer_id == self.my_id:
                continue
            # TODO: Add lease time
            # logger.DUMP_LOGGER.info("")
            prevLogIndex = self.nextIndex[peer_id] - 1
            prevLogTerm = (
                -1
                if ((self.nextIndex[peer_id] - 1) < 0)
                else self.logs[self.nextIndex[peer_id] - 1]
            )

            args = raft_pb2.AppendEntriesArgs(
                term=self.currentTerm,
                leaderId=self.my_id,
                prevLogIndex=prevLogIndex,
                prevLogTerm=prevLogTerm,
                leaderCommit=self.commitIndex,
            )

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
            time.sleep(1)  # Sleep for 1 S
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
