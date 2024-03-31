"""
Raft
"""
from concurrent import futures
import enum
import os
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

HEARTBEAT_TIMEOUT = 1  # Second
ELECTION_TIMEOUT_RANGE = (5, 10)  # Second
LEASE_TIMEOUT = 5  # Second
APPEND_ENTRY_TIMEOUT = 0.9  # Second
REQUEST_VOTE_TIMEOUT = 4  # Second


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

    def __init__(self, node_id: int, peers: list[str], kv, **kwargs):
        self.my_id = node_id
        self.peers = peers
        self.server_port = peers[self.my_id].split(":")[1]
        self.mutex = threading.Lock()
        self.server = None
        self.kv = kv

        ## Raft state
        # Persistent states on server
        self.currentTerm = 0
        self.votedFor = -1
        self.logs = []

        # Volatile states on all servers
        self.state = State.FOLLOWER
        self.commitIndex = 0  #  = commitLength
        self.lastApplied = 0  # Points to the index that is not commited yet

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
        # For a follower, it is the time when it received the last lease information, which has the maximum lease duration
        self.lease_access_time = 0
        self.reachability_nodes_cnt = (
            0  # No of nodes that are reachable while performing AppendEntry
        )

        self.leaderId = -1

        self.logs_fd = kwargs["logs_fd"]
        self.metadata_fd = kwargs["metadata_fd"]

        self.apply_thread = threading.Thread(target=self.__apply_logs)
        self.executor = futures.ThreadPoolExecutor(len(self.peers) - 1)
        self.timer_thread = threading.Thread(target=self.__timer)

        self.__replay()
        self.__change_state_to_follower(self.currentTerm, 0, "StartUp")
        self.apply_thread.start()
        time.sleep(1)  # Let apply the logs
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
        self.apply_thread.join()

        os.fsync(self.metadata_fd)
        os.fsync(self.logs_fd)
        self.metadata_fd.close()
        self.logs_fd.close()

    def get_leader_id(self) -> int:
        """Returns the leader id known to this node"""
        with self.mutex:
            return self.leaderId

    def is_leader_with_lease(self) -> typing.Tuple[bool, bool, int]:
        """Is leader and has lease"""
        with self.mutex:
            return self.state == State.LEADER, self.has_lease, self.leaderId

    def write_to_raft(
        self, cmd: command.Command
    ) -> typing.Tuple[int, int, bool, bool, int]:
        """
        Writes to the state machine and replicates.
        Returns: (LogIndex, term, isLeader, hasLease, leaderId)
        """
        # cmd = command.Command.deep_clone_command(cmd)
        with self.mutex:
            term = self.currentTerm
            leader_id = self.leaderId
            if self.state == State.LEADER:
                if self.has_lease:
                    cmd.set_term(self.currentTerm)
                    return (*self.__append_entry(cmd), True, True, leader_id)
                else:
                    logger.DUMP_LOGGER.debug("write_to_raft failed. No lease")
        return (-1, term, False, False, leader_id)

    def __append_entry(self, cmd: command.Command) -> typing.Tuple[int, int]:
        """Appends command to log and returns log index and term number"""
        self.logs.append(cmd)
        term = self.currentTerm
        index = len(self.logs) - 1
        self.nextIndex[
            self.my_id
        ] += 1  # Update it, as it will be used while counting majority
        self.__persist()
        logger.DUMP_LOGGER.debug(
            "Appended command [%s] at index %s term %s", cmd, index, term
        )
        return (index, term)

    def __replay(self) -> None:
        """Reads state from persistent storage"""
        dumped_meta = self.metadata_fd.read()
        dumped_meta_lines = dumped_meta.split("\n")
        for line in dumped_meta_lines:
            if line == "":
                continue
            words = line.split(" ")
            keyword, value = words[0], words[1]
            if keyword == "term":
                self.currentTerm = int(value)
            if keyword == "votedFor":
                self.votedFor = int(value)
            if keyword == "commitIndex":
                self.commitIndex = int(
                    value
                )  # Don't rely on the logs. Use it as commitIndex

        dumped_logs = self.logs_fd.read()
        dumped_logs_lines = dumped_logs.split("\n")
        for line in dumped_logs_lines:
            if line == "":
                continue
            words = line.split(" ")
            cmd_type = command.Command.command_type_from_str(words[0])
            if cmd_type == command.CommandType.NOOP:
                cmd = command.Command(command.CommandType.NOOP, int(words[1]))
            elif cmd_type == command.CommandType.SET:
                cmd = command.Command(
                    command.CommandType.SET, int(words[3]), key=words[1], value=words[2]
                )
            else:
                cmd = None
            if cmd is not None:
                self.logs.append(cmd)
        self.logs_fd.seek(0)
        self.metadata_fd.seek(0)
        logger.DUMP_LOGGER.info(
            "State: term %s votedFor %s commitIndex %s logs: [%s]",
            self.currentTerm,
            self.votedFor,
            self.commitIndex,
            "][".join(map(str, self.logs)),
        )

    def __persist(self) -> None:
        """Store non-volatile states to file"""
        # Just for simplicity
        logs_to_write = "\n".join(map(str, self.logs))
        metadata_to_write = f"term {self.currentTerm} \nvotedFor {self.votedFor} \ncommitIndex {self.commitIndex}"

        if len(logs_to_write) > 0:
            self.logs_fd.seek(0)
            self.logs_fd.truncate()
            self.logs_fd.write(logs_to_write)
            self.logs_fd.flush()

        if len(metadata_to_write) > 0:
            self.metadata_fd.seek(0)
            self.metadata_fd.truncate()
            self.metadata_fd.write(metadata_to_write)
            self.metadata_fd.flush()
        # Flush at stop

    def __update_lease(self, access_time: int, lease_interval: int) -> None:
        """Updates lease interval"""
        # For simplicity, avoid the network latency and drift
        last_lease_interval_remaining = self.__get_lease_duration()
        if lease_interval >= last_lease_interval_remaining:
            self.lease_access_time = access_time
            self.leaseInterval = lease_interval
        # self.lease_access_time = access_time
        # self.leaseInterval = max(self.leaseInterval, lease_interval)

    def __get_lease_duration(self):
        """Returns lease reamining duration"""
        return max(
            0,
            self.lease_access_time + self.leaseInterval - util.current_time_second(),
        )

    def __renew_lease(self) -> None:
        """Renew lease, because it can reach majority of the nodes"""
        self.lease_access_time = util.current_time_second()
        self.leaseInterval = LEASE_TIMEOUT

    def __acquire_lease(self, lease_acquire_time: int) -> None:
        """Acquire Lease"""
        self.has_lease = True
        logger.DUMP_LOGGER.info("New Leader %s acquired lease.", self.my_id)
        self.__append_entry(command.Command(command.CommandType.NOOP, self.currentTerm))
        self.lease_access_time = lease_acquire_time
        self.leaseInterval = LEASE_TIMEOUT
        self.__send_heartbeat()

    def __action_on_lease(self, curr_time) -> bool:
        """Updates lease, if conditions satisfy"""
        if (curr_time - self.lease_access_time) >= self.leaseInterval:
            if self.state == State.LEADER:
                if self.has_lease:
                    self.has_lease = False
                    logger.DUMP_LOGGER.info(
                        "Leader %s lease renewal failed. Stepping Down.", self.my_id
                    )
                    self.__change_state_to_follower(
                        self.currentTerm, 0, "UnableToRenewLease"
                    )
                else:
                    # Doesn't have the lease and lease expires => No one else has the lease => acquire the lease
                    self.__acquire_lease(curr_time)

        # For other states, no need to do anything
        return self.has_lease

    def __get_last_log_index(self) -> int:
        """Returns last log index"""
        return len(self.logs) - 1

    def __get_last_log_term(self) -> int:
        """Returns last log term"""
        last_index = self.__get_last_log_index()
        return -1 if last_index == -1 else self.logs[last_index].term

    def __change_state_to_leader(self):
        """Change state to leader"""
        # TODO: Pass lease information
        self.state = State.LEADER
        self.leaderId = self.my_id
        self.has_lease = False  # TODO: Change it while implementing lease
        logger.DUMP_LOGGER.info(
            "Node %s became the leader for term %s.", self.my_id, self.currentTerm
        )
        self.nextIndex = [len(self.logs)] * len(self.peers)
        # self.matchIndex =  TODO: Set it
        logger.DUMP_LOGGER.info(
            "New Leader waiting for Old Leader Lease to timeout. Duration: %s",
            self.__get_lease_duration(),
        )
        self.__action_on_lease(util.current_time_second())

    def __change_state_to_follower(
        self, term: int, lease_remaining_duration: int, why: str
    ):
        """Change state to follower"""
        self.state = State.FOLLOWER
        self.currentTerm = term
        self.votedFor = -1
        self.leaderId = -1
        self.__persist()
        self.__update_lease(util.current_time_second(), lease_remaining_duration)
        self.__update_timer(self.__election_timeout())
        logger.DUMP_LOGGER.info(
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

    def __apply_logs(self) -> None:
        """Apploes log"""
        while self.active:
            with self.mutex:
                if self.lastApplied < self.commitIndex:
                    logs_to_apply = self.logs[self.lastApplied : self.commitIndex]
                    indices = list(i for i in range(self.lastApplied, self.commitIndex))
                    logger.DUMP_LOGGER.info(
                        "Appying logs from %s to %s. indices [%s] logs [%s]",
                        self.lastApplied,
                        self.commitIndex,
                        " ".join(map(str, indices)),
                        " | ".join(map(str, logs_to_apply)),
                    )
                    self.kv.apply(indices, logs_to_apply)
                    self.lastApplied += len(logs_to_apply)
            time.sleep(0.5)  # TODO: Think about the condition variable option

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
                self.__persist()
                logger.DUMP_LOGGER.info(
                    "Vote granted for Node %s in term %s. LeaseDuration %s",
                    request.candidateId,
                    request.term, reply.leaseRemainingDuration
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
        self.__persist()
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
        try:
            with grpc.insecure_channel(self.peers[node_id]) as channel:
                stub = raft_pb2_grpc.RaftServiceStub(channel)
                reply = stub.RequestVote(args, timeout=REQUEST_VOTE_TIMEOUT)
        except grpc.RpcError as err:
            if err.code() == grpc.StatusCode.UNAVAILABLE:
                logger.DUMP_LOGGER.error(
                    "Error occurred while sending RequestVote RPC to Node %s. UNAVAILABLE",
                    node_id,
                )
            elif err.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                logger.DUMP_LOGGER.error(
                    "Error occurred while sending RequestVote RPC to Node %s. DEADLINE_EXCEEDED",
                    node_id,
                )
            else:
                logger.DUMP_LOGGER.error(
                    "Error occurred while sending RequestVote RPC to Node %s. Unknown. Error: %s",
                    node_id,
                    str(err),
                )
            return

        with self.mutex:
            if (self.state != State.CANDIDATE) or (self.currentTerm != args.term):
                # Reply comes after a long time
                return

            self.__update_lease(
                util.current_time_second(), reply.leaseRemainingDuration
            )
            if not reply.voteGranted:
                if self.currentTerm < reply.term:
                    # It is another term, so the other node has updated information about the lease
                    self.__change_state_to_follower(
                        reply.term, reply.leaseRemainingDuration, "HigherTermExists"
                    )
                return

            self.votes_received += 1
            if self.votes_received > (len(self.peers) / 2):
                self.__change_state_to_leader()

    def AppendEntries(
        self, request: raft_pb2.AppendEntriesArgs, context
    ) -> raft_pb2.AppendEntriesReply:
        """RPC AppendEntries"""

        with self.mutex:
            reply = raft_pb2.AppendEntriesReply(
                term=self.currentTerm, success=True, conflictIndex=-1, conflictTerm=-1
            )
            if self.currentTerm > request.term:
                reply.success = False
                reply.term = self.currentTerm
                return reply

            if self.state == State.CANDIDATE:
                self.__change_state_to_follower(
                    request.term, request.leaseRemainingDuration, "HBTFromHigherTerm"
                )
            # Update the following
            self.leaderId = request.leaderId
            self.__update_timer(self.__election_timeout())

            logger.DUMP_LOGGER.debug(
                "AppendEntries prevLogindex: %s term: %s commitIndex %s leaseRemaining %s",
                request.prevLogIndex,
                request.prevLogTerm,
                request.leaderCommit,
                request.leaseRemainingDuration,
            )
            # if request.prevLogIndex == -1 and request.prevLogTerm == -1:
            # This case arises, when the LEADER's log is empty.
            # With Lease mechanism, it is not possible, as the leader appends NO-OP.
            # TODO: emove it after implementing lease.
            # reply.success = True
            # logger.DUMP_LOGGER.debug("AppendEntryAccepted")
            # return reply

            # extract the log
            leader_logs = list(
                map(
                    lambda x: command.Command.cmd_from_pb2(x.command, x.term),
                    request.entries,
                )
            )

            # 2. Reply false if log doesn’t contain an entry at prevLogIndex
            #  whose term matches prevLogTerm (§5.3)
            if request.prevLogIndex < len(self.logs):
                # Log exists, so check if term is matching
                # Now, check if the entry at prevLogIndex has same term as prevLogTerm
                if request.prevLogIndex != -1 and (
                    self.logs[request.prevLogIndex].term != request.prevLogTerm
                ):
                    # term not matching, send ConflictIndex and ConflictTerm
                    reply.conflictTerm = self.logs[request.prevLogIndex].term
                    idx = request.prevLogIndex
                    while idx >= 0 and self.logs[idx].term == reply.conflictTerm:
                        reply.conflictIndex = idx
                        idx -= 1
                    reply.success = False
                    logger.DUMP_LOGGER.info(
                        "Node %s rejected AppendEntries RPC from %s. conflictIndex: %s conflictTerm: %s",
                        self.my_id,
                        self.leaderId,
                        reply.conflictIndex,
                        reply.conflictTerm,
                    )
                    return reply
                # Remove extra logs beyond leader's prevLogIndex
                # Scenario: follower log size = 10, client log size = 7. So drop the extra logs
                log_cut = False
                if (request.prevLogIndex + 1) != len(self.logs):
                    log_cut = True
                self.logs = self.logs[: request.prevLogIndex + 1]

                # Add/updates the logs
                self.logs[request.prevLogIndex + 1 :] = leader_logs
                if log_cut or (len(leader_logs) > 0):
                    self.__persist()
                    logger.DUMP_LOGGER.info(
                        "Node %s accepted AppendEntries RPC from %s. cut %s Logs: [%s]",
                        self.my_id,
                        self.leaderId,
                        log_cut,
                        "][".join(list(map(str, self.logs))),
                    )
                else:
                    logger.DUMP_LOGGER.debug("AppendEntry HB accepted")

                # TODO(VVI): In case of log_cut reduce the commitIndex
                # In case of log_cut, the log that are being cut are not committed yet. So no need of adjusting commitIndex

                if request.leaderCommit > self.commitIndex:
                    new_commit_idx = min(request.leaderCommit, len(self.logs))
                    if self.commitIndex != new_commit_idx:
                        committing_entries = self.logs[
                            self.commitIndex : new_commit_idx
                        ]
                        self.commitIndex = new_commit_idx
                        self.__persist()
                        logger.DUMP_LOGGER.info(
                            "Node %s (follower) committed the entry [%s] to the state machine.",
                            self.my_id,
                            "][".join(map(str, committing_entries)),
                        )
                reply.success = True
                return reply
            else:
                # Index not exist
                # The index next to the last entry, i.e. size
                logger.DUMP_LOGGER.info(
                    "Node %s rejected AppendEntries RPC from %s. conflictIndex: %s conflictTerm: %s",
                    self.my_id,
                    self.leaderId,
                    reply.conflictIndex,
                    reply.conflictTerm,
                )
                reply.conflictIndex = len(self.logs)
                reply.success = False
                return reply
        return reply

    def send_append_entries(
        self, node_id: int, args: raft_pb2.AppendEntriesArgs, heartbeat: bool
    ) -> None:
        """Sends append entry messages"""
        success = False
        # retry, for lease interval
        # TODO: Remove the below, don't try from here, because thread is already dedicated, and
        # in the next appendEntry this node may be assigned a new thread, and a node later to this node has to wait as pool is empty.
        # The other way to implement is store all the futures returned by the executor.submit().
        # Next time, if the future is value, then submit the job otherwise don't

        # Keep this comment even after implementing.

        # TODO: Take mutex and check
        while self.active and self.state == State.LEADER and not success:
            try:
                with grpc.insecure_channel(self.peers[node_id]) as channel:
                    stub = raft_pb2_grpc.RaftServiceStub(channel)
                    reply = stub.AppendEntries(args, timeout=APPEND_ENTRY_TIMEOUT)
                    success = True
            except grpc.RpcError as err:
                if err.code() == grpc.StatusCode.UNAVAILABLE:
                    logger.DUMP_LOGGER.error(
                        "Error occurred while sending AppendEntries RPC to Node %s. UNAVAILABLE",
                        node_id,
                    )
                elif err.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                    logger.DUMP_LOGGER.error(
                        "Error occurred while sending AppendEntries RPC to Node %s. DEADLINE_EXCEEDED",
                        node_id,
                    )
                else:
                    logger.DUMP_LOGGER.error(
                        "Error occurred while sending AppendEntries RPC to Node %s. Unknown. Error: %s",
                        node_id,
                        str(err),
                        # str(err.args),
                    )
                # Don't try here. Send on next message
                return

        with self.mutex:
            if not self.active or self.state != State.LEADER:
                # Lease
                return
            self.reachability_nodes_cnt += 1
            if self.reachability_nodes_cnt > (len(self.peers) / 2):
                self.__renew_lease()

            if reply.success:
                # TODO: ignore if it is an old rpc
                self.nextIndex[node_id] += len(args.entries)
                logger.DUMP_LOGGER.debug(
                    "Success AppendEntries from %s. nextIdx: %s",
                    node_id,
                    self.nextIndex[node_id],
                )
                logger.DUMP_LOGGER.debug(
                    "Next Idx: %s", " ".join(map(str, self.nextIndex))
                )
                # Find the indices to commit
                # Find the indices that are not yet commited
                # find_commitable_indices = lambda x: x>self.commitIndex
                # find_rep_cnt_commitable = lambda counts, item: {**counts, item[0]: counts.get(item[0], 0) + item[1]}
                # commit_factor_predicate = lambda tup: tup[1] > (len(self.peers) / 2)
                # idx_count_map = functools.reduce(lambda counts, item: {**counts, item[0]: counts.get(item[0], 0) + item[1]}, map(lambda x: x>self.commitIndex, self.nextIndex), {})
                # self.commitIndex = max(list(map(lambda x: x[1], filter(lambda tup: tup[1] > (len(self.peers) / 2), zip(idx_count_map.keys(), idx_count_map.values())))))

                # Find peers, whose nextIdx id more than commit Index
                uncommited_indices_list = list(
                    filter(lambda x: x > self.commitIndex, self.nextIndex)
                )
                if len(uncommited_indices_list) == 0:
                    return
                logger.DUMP_LOGGER.debug(
                    "uncommited_indices_list: %s",
                    " ".join(map(str, uncommited_indices_list)),
                )
                # Count no of times these indices are replicated
                count = {}
                for i in uncommited_indices_list:
                    count[i] = count.get(i, 0) + 1
                logger.DUMP_LOGGER.debug("MAP: len: %s %s", len(count), count)
                # filter out the indices that are replicated more than majority
                majority_indices = []
                for k, v in count.items():
                    if v > (len(self.peers) / 2):
                        majority_indices.append(k)
                # logger.DUMP_LOGGER.debug("MajorityIndices: len-> %s %s", len(majority_indices), " ".join(map(str, majority_indices)))
                # Take the max index
                if len(majority_indices) == 0:
                    return
                new_commit_idx = max(majority_indices)
                committing_entries = self.logs[self.commitIndex : new_commit_idx]
                self.commitIndex = new_commit_idx
                self.__persist()
                logger.DUMP_LOGGER.info(
                    "Node %s (leader) committed the entry [%s] to the state machine.",
                    self.my_id,
                    "][".join(map(str, committing_entries)),
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

            # Fail due to log missmatch
            logger.DUMP_LOGGER.debug(
                "Fail AppendEntries at %s from %s. ConflictIndex %s ConflictTerm %s",
                self.my_id,
                node_id,
                reply.conflictIndex,
                reply.conflictTerm,
            )
            self.nextIndex[node_id] = reply.conflictIndex
            # TODO: Handle conflictTerm

    def __send_heartbeat(self) -> None:
        """Sends heartbeat to peers"""
        if not self.has_lease:
            # Although it is a double check, but keep it.
            return

        # Reset lease counter
        self.reachability_nodes_cnt = 1  # can reach to self

        logger.DUMP_LOGGER.info(
            "Leader %s sending heartbeat & Renewing Lease", self.my_id
        )
        # logger.DUMP_LOGGER.debug("logs: [%s]", "][".join(map(str, self.logs)))
        for peer_id in range(len(self.peers)):
            if peer_id == self.my_id:
                continue

            prevIndex = self.nextIndex[peer_id] - 1
            prevTerm = -1 if prevIndex < 0 else self.logs[prevIndex].term

            args = raft_pb2.AppendEntriesArgs(
                term=self.currentTerm,
                leaderId=self.my_id,
                prevLogIndex=prevIndex,
                prevLogTerm=prevTerm,
                leaderCommit=self.commitIndex,
                leaseRemainingDuration=self.__get_lease_duration(),
            )

            logs_to_send = self.logs[prevIndex + 1 :]
            logs_in_pb2 = list(
                map(
                    lambda x: raft_pb2.Command(command=x.cmd_to_pb2(), term=x.term),
                    logs_to_send,
                )
            )
            args.entries.extend(logs_in_pb2)
            logger.DUMP_LOGGER.debug(
                "Sending HB to node %s, MyLoglen %s, nextIdx %s sendingLogs [%s]",
                peer_id,
                len(self.logs),
                self.nextIndex[peer_id],
                "][".join(map(str, logs_to_send)),
            )
            self.executor.submit(
                self.send_append_entries, peer_id, args, len(args.entries) > 0
            )
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
                self.__action_on_lease(curr_time)
                if (self.last_heartbeat + self.wait_duration) <= curr_time:
                    if self.state == State.LEADER:
                        if self.has_lease:
                            self.__send_heartbeat()
                            self.__update_timer(HEARTBEAT_TIMEOUT)
                    else:
                        self.__initiate_election()
                        self.__update_timer(self.__election_timeout())
