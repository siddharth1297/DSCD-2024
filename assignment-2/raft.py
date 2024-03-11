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
import util

MAX_WORKERS = 2

HEARTBEAT_TIMEOUT = 1  # Seconds
ELECTION_TIMEOUT_RANGE = (5, 10)  # Second
LEASE_TIMEOUT = 2.5  # Second


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
        self.__update_timer(self.__election_timeout())

        self.__serve()
        self.timer_thread = threading.Thread(target=self.__timer)
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

    def __initiate_election(self) -> None:
        """Initiates election"""
        return

    def __send_heartbeat(self) -> None:
        """Sends heartbeat to peers"""
        return

    def __election_timeout(self) -> int:
        """Election timeout duration"""
        return random.randint(ELECTION_TIMEOUT_RANGE[0], ELECTION_TIMEOUT_RANGE[1])

    def __update_timer(self, wait_duration: int) -> None:
        """Updates timer"""
        self.last_heartbeat = util.current_time_millis()
        self.wait_duration = wait_duration

    def __timer(self) -> None:
        """Timer"""
        # sleep_time = self.wait_duration
        while self.active:
            time.sleep(0.5)  # Sleep for 0.5 S
            if not self.active:
                break
            with self.mutex:
                if (
                    self.last_heartbeat + self.wait_duration
                    >= util.current_time_millis()
                ):
                    if self.state == State.LEADER:
                        self.__send_heartbeat()
                        self.__update_timer(HEARTBEAT_TIMEOUT)
                    else:
                        self.__initiate_election()
                        self.__update_timer(self.__election_timeout())
