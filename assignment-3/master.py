"""
MapReduce Master
"""
# pylint: disable=too-many-instance-attributes
from concurrent import futures
import threading
import grpc
import master_pb2_grpc
import master_pb2

import logger

MAX_WORKERS = 2


class Master(master_pb2_grpc.MasterServicesServicer):
    """MapReduce Master"""

    def __init__(self, **kwargs):
        # MapReduce configurations
        self.port = kwargs["port"]
        self.n_map = kwargs["n_map"]
        self.n_reduce = kwargs["n_reduce"]

        # K-means configurations
        self.n_centroids = kwargs["n_centroids"]
        self.n_iterations = kwargs["n_iterations"]
        self.ip_file = kwargs["ip_file"]

        # Job states
        self.job_done = False

        # Other states
        self.grpc_server = None
        self.mutex = threading.Lock()

    def start(self) -> None:
        """Start Services"""
        self.__serve()

    def stop(self) -> bool:
        """Stop"""
        self.grpc_server.stop(1).wait()
        return True

    def is_job_done(self) -> bool:
        """Returns is the job done"""
        with self.mutex:
            return self.job_done

    def __serve(self) -> None:
        """Start services"""
        self.grpc_server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=MAX_WORKERS),
            options=(("grpc.so_reuseport", 0),),
        )
        master_pb2_grpc.add_MasterServicesServicer_to_server(self, self.grpc_server)
        self.grpc_server.add_insecure_port("0.0.0.0" + ":" + self.port)
        self.grpc_server.start()
        logger.DUMP_LOGGER.info("Service Started at port %s", self.port)

    def GetJob(self, request: master_pb2.GetJobArgs, context) -> master_pb2.GetJobReply:
        """GetJob RPC"""
        logger.DUMP_LOGGER.info(
            "GetJob RPC from worker %s %s", request.worker_id, request.worker_addr
        )
        return master_pb2.GetJobReply(job_type=master_pb2.JobType.EXIT)
