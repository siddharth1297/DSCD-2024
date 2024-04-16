"""
MapReduce Master
"""
# pylint: disable=too-many-instance-attributes
from concurrent import futures
import threading
import enum
import logging
import time
import grpc
import yaml

import master_pb2_grpc
import master_pb2

import mapper_pb2_grpc
import mapper_pb2

import logger

LOGGING_LEVEL = logging.DEBUG

MAX_WORKERS = 2
DEFAULT_MAP_TIMEOUT = 30 # second
DEFAULT_REDUCE_TIMEOUT = 30 # second


class TaskStatus(enum.Enum):
    """Task status of a task"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"

class Task:
    """Task structure"""
    def __init__(self, **kwargs):
        self.master = kwargs['master']
        self.inputfiles = [kwargs['inputfile']]
        self.ranges = []
        self.status = TaskStatus.PENDING

class Master(master_pb2_grpc.MasterServicesServicer):
    """MapReduce Master"""

    def __init__(self, **kwargs):
        # MapReduce configurations
        self.port = kwargs["addr"].split(':')[1]
        self.n_map = kwargs["M"]
        self.n_reduce = kwargs["R"]

        # K-means configurations
        self.n_centroids = kwargs["K"]
        self.n_iterations = kwargs["I"]
        self.ip_file = kwargs["inputfile"]

        self.mappers = kwargs['mappers']
        self.reducers = kwargs['reducers']

        # Job states
        self.job_done = False

        # Other states
        self.grpc_server = None
        self.mutex = threading.Lock()
        self.executor = futures.ThreadPoolExecutor(max(self.n_map, self.n_reduce))

    def start(self) -> None:
        """Start Services"""
        self.__serve()

    def stop(self) -> bool:
        """Stop"""
        self.grpc_server.stop(1).wait()
        self.executor.shutdown(wait=True) # cancel_futures=True is for >= Python-3.9
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

    def SubmitMapJob(self, request: master_pb2.SubmitMapJobArgs, context) -> master_pb2.SubmitMapReply:
        """SubmitMapJob RPC"""
        logger.DUMP_LOGGER.info("SubmitMapJob RPC from worker %s", request.worker_id)
        return master_pb2.SubmitMapReply()

    def SubmitReduceJob(self, request: master_pb2.SubmitReduceJobArgs, context) -> master_pb2.SubmitReduceReply:
        """SubmitReduceJob RPC"""
        logger.DUMP_LOGGER.info("SubmitMapJob RPC from worker %s", request.worker_id)
        return master_pb2.SubmitReduceReply()

    def __submit_map_task(self, task: Task, arg: mapper_pb2.DoMapTaskArgs, worker_id: int) -> None:
        """Submits mapper task to mapper"""
        reply, error = None, None
        try:
            with grpc.insecure_channel(self.mappers[worker_id]) as channel:
                stub = mapper_pb2_grpc.MapperServiceStub(channel)
                reply = stub.DoMap(arg, timeout=DEFAULT_MAP_TIMEOUT)
        except grpc.RpcError as err:
            error = "DOWN"
            if err.code() == grpc.StatusCode.UNAVAILABLE:
                logger.DUMP_LOGGER.error(
                    "Error occurred while sending DoMap RPC to Node %s. UNAVAILABLE",
                    worker_id,
                )
            elif err.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                logger.DUMP_LOGGER.error(
                    "Error occurred while sending DoMap RPC to Node %s. DEADLINE_EXCEEDED",
                    worker_id,
                )
            else:
                logger.DUMP_LOGGER.error(
                    "Error occurred while sending DoMap RPC to Node %s. Unknown. Error: %s",
                    worker_id,
                    str(err),
                )
        with self.mutex:
            if reply is None:
                # error must be non-None
                # Update in the tasks map that this job is failed
                task.status = TaskStatus.FAILED
                return
            # Update in the tasks map and store the results in necessary files
            task.status = TaskStatus.COMPLETED

    def __run_map(self, iter: int) -> None:
        """run map task"""
        # TODO: Divide the jobs between the mappers
        tasks = []
        while True:
            completed = False
            for i in range(len(self.n_map)):
                self.mutex.locked()
                if task.status in (TaskStatus.PENDING, TaskStatus.FAILED):
                    task = tasks[i]
                    arg = mapper_pb2.DoMapTaskArgs()
                    task.status = TaskStatus.RUNNING
                    self.executor.submit(self.__submit_map_task, task, arg, i)
                completed = completed and (task.tatus == TaskStatus.COMPLETED)
                self.mutex.release()
                if completed:
                    break
                time.sleep(2)



    def __run_reduce(self, iter: int) -> None:
        """run reduce task"""
        pass

    def run(self):
        """run job"""
        for i in range(self.n_iterations):
            
            logger.DUMP_LOGGER.info("Starting iteration %s MAP", i)
            self.__run_map(iter)
            

            
            logger.DUMP_LOGGER.info("Starting iteration %s Reduce", i)
            self.__run_reduce(iter)

                # TODO: Check convergence. If it converges, then stop
        # TODO: Print centroids
        self.stop()
    
            

if __name__ == "__main__":
    with open("config.yaml", "r", encoding="UTF-8") as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
        master_cfg = config['master']
        mappers = config['mappers']
        reducers = config['reducers']

    logger.set_logger("logs/", "master.txt", "master", LOGGING_LEVEL)
    master = Master(**master_cfg, mappers=mappers, reducers=reducers)
    master.start()
    master.run()
