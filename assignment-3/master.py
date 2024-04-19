"""
MapReduce Master
"""
# pylint: disable=too-many-instance-attributes
from concurrent import futures
import math
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

import common_messages_pb2
import reducer_pb2
import reducer_pb2_grpc

import logger

LOGGING_LEVEL = logging.DEBUG

MAX_WORKERS = 2
DEFAULT_MAP_TIMEOUT = 30  # second
DEFAULT_REDUCE_TIMEOUT = 30  # second
SLEEP_TIME = 3


class TaskStatus(enum.Enum):
    """mapTask status of a task"""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


class WorkerStatus(enum.Enum):
    """Worker status"""

    FREE = "FREE"
    BUSY = "BUSY"
    DEAD = "DEAD"


class MapTask:
    """mapTask structure"""

    def __init__(self, **kwargs):
        self.task_id = kwargs["task_id"]
        self.start_idx = kwargs["start_idx"]  # inclusive
        self.end_idx = kwargs["end_idx"]  # exclusive
        self.status = kwargs["status"]
        self.mapper_id = -1

    def __str__(self):
        return f"[{self.task_id}:({self.start_idx} {self.end_idx}) {self.status.value} {self.mapper_id}]"


class ReduceTask:
    """reduceTask structure"""

    def __init__(self, **kwargs):
        self.reduce_id = kwargs["reduce_id"]  # this is partition key
        self.status = kwargs["status"]
        self.mapper_address = []

    def __str__(self):
        return f"[{self.reduce_id} : {self.status.value} {self.mapper_address}]"


class Worker:
    """Worker"""

    def __init__(self, **kwargs):
        self.worker_id = kwargs["worker_id"]
        self.addr = kwargs["addr"]
        self.status = kwargs["status"]

    def __str__(self):
        return f"[{self.worker_id}:{self.addr}-{self.status.value}]"


class Master(master_pb2_grpc.MasterServicesServicer):
    """MapReduce Master"""

    def __init__(self, **kwargs):
        # MapReduce configurations
        self.port = kwargs["addr"].split(":")[1]
        self.n_map = kwargs["M"]
        self.n_reduce = kwargs["R"]

        self.mappers = list(
            map(
                lambda x: Worker(worker_id=x[0], addr=x[1], status=WorkerStatus.FREE),
                enumerate(kwargs["mappers"]),
            )
        )
        self.reducers = list(
            map(
                lambda x: Worker(worker_id=x[0], addr=x[1], status=WorkerStatus.FREE),
                enumerate(kwargs["reducers"]),
            )
        )

        self.map_tasks = []
        self.reduce_tasks = []

        self.mapper_file_output = {}
        # K-means configurations
        self.n_centroids = kwargs["K"]
        self.n_iterations = kwargs["I"]
        self.ip_file = kwargs["inputfile"]
        self.n_points = 0
        self.splits = []
        self.new_centroids = [0] * self.n_centroids
        self.centroids = []
        self.__init_clustering_params()

        logger.DUMP_LOGGER.info(
            "NPoints: %s Centroids: [%s]\tSplit_ranges: [%s]",
            self.n_points,
            " ".join(map(str, self.centroids)),
            " ".join(map(lambda x: f"{x[0]}-{x[1]}", self.splits)),
        )

        self.__create_map_tasks()

        # Job states
        self.job_done = False

        # Other states
        self.grpc_server = None
        self.mutex = threading.Lock()
        self.executor = futures.ThreadPoolExecutor(max(self.n_map, self.n_reduce))

    def __create_map_tasks(self) -> None:
        """Creates map tasks"""
        for i in range(self.n_map):
            task = MapTask(
                task_id=i,
                start_idx=self.splits[i][0],
                end_idx=self.splits[i][1],
                status=TaskStatus.PENDING,
            )
            self.map_tasks.append(task)

    def __create_reduce_tasks(self) -> None:
        """Creates reduce tasks"""
        for i in range(self.n_reduce):
            task = ReduceTask(
                task_id=i,
                status=TaskStatus.PENDING,
            )
            self.reduce_tasks.append(task)

    def __init_clustering_params(self) -> None:
        """Initialise clustering algorithm params. centroids, split ranges"""
        points = []
        self.n_points = 0
        with open(self.ip_file, "r", encoding="UTF-8") as file:
            for line in file:
                parts = line.strip().split(",")
                if len(parts) == 2:
                    self.n_points += 1
                    x, y = parts
                    points.append((float(x), float(y)))
        split_size = math.ceil(self.n_points / self.n_map)
        start = 0
        self.centroids = points[0 : self.n_centroids]
        self.centroids = [round(i, 4) for i in self.centroids]
        while start < self.n_points:
            end = min(start + split_size, self.n_points)
            self.splits.append([start, end])
            # self.centroids.append(points[int((start + end) / 2)])
            # self.centroids.append(points[0:self.n_centroids])
            start += split_size

        assert len(self.splits) == self.n_map
        assert len(self.centroids) == self.n_centroids

    def start(self) -> None:
        """Start Services"""
        self.__serve()

    def stop(self) -> bool:
        """Stop"""
        self.grpc_server.stop(1).wait()
        self.executor.shutdown(wait=True)  # cancel_futures=True is for >= Python-3.9
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

    def SubmitMapJob(
        self, request: master_pb2.SubmitMapJobArgs, context
    ) -> master_pb2.SubmitMapReply:
        """SubmitMapJob RPC"""
        logger.DUMP_LOGGER.info("SubmitMapJob RPC from worker %s", request.worker_id)
        return master_pb2.SubmitMapReply()

    def SubmitReduceJob(
        self, request: master_pb2.SubmitReduceJobArgs, context
    ) -> master_pb2.SubmitReduceReply:
        """SubmitReduceJob RPC"""
        logger.DUMP_LOGGER.info("SubmitMapJob RPC from worker %s", request.worker_id)
        return master_pb2.SubmitReduceReply()

    def __submit_reduce_task(
        self, task: ReduceTask, arg: reducer_pb2.DoReduceTaskArgs, worker: Worker
    ) -> None:
        """Submits reducer task to reducer"""
        reply, error = None, None
        try:
            with grpc.insecure_channel(worker.addr) as channel:
                stub = reducer_pb2_grpc.ReducerServiceStub(channel)
                reply = stub.DoReduce(arg, timeout=DEFAULT_REDUCE_TIMEOUT)

        except grpc.RpcError as err:
            error = (
                WorkerStatus.DEAD
            )  # Anything bad happens, consider the worker as down
            if err.code() == grpc.StatusCode.UNAVAILABLE:
                logger.DUMP_LOGGER.error(
                    "Error occurred while sending DoReduce RPC to Node %s. UNAVAILABLE",
                    str(worker),
                )
            elif err.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                logger.DUMP_LOGGER.error(
                    "Error occurred while sending DoReduce RPC to Node %s. DEADLINE_EXCEEDED",
                    str(worker),
                )
            else:
                logger.DUMP_LOGGER.error(
                    "Error occurred while sending DoReduce RPC to Node %s. Unknown. Error: %s",
                    str(worker),
                    str(err),
                )

        with self.mutex:
            if reply is None:
                assert error is not None
                # Update in the tasks reduce that this job is failed
                task.status = TaskStatus.FAILED
                worker.status = error
                logger.DUMP_LOGGER.error(
                    "REDUCE task FAILED. task: %s worker: %s", task, worker
                )
                return

            for centroid in reply.updated_centroids:
                logger.DUMP_LOGGER.info(" abcd %s %s %s %s ",centroid.centroid.x, centroid.centroid.y, round(centroid.centroid.x, 4), round(centroid.centroid.y, 4) )
                self.new_centroids[centroid.index] = (
                    round(centroid.centroid.x, 4),
                    round(centroid.centroid.y, 4) ,
                )

            # logger.DUMP_LOGGER.info("New centroids %s", str(self.centroids[0:self.n_centroids]))

            # Update in the tasks reduce and store the results in necessary files
            task.status = TaskStatus.COMPLETED
            worker.status = WorkerStatus.FREE
            logger.DUMP_LOGGER.info(
                "REDUCE task COMPLETED. task: %s worker: %s", task, worker
            )

    def __submit_map_task(
        self, task: MapTask, arg: mapper_pb2.DoMapTaskArgs, worker: Worker
    ) -> None:
        """Submits mapper task to mapper"""
        reply, error = None, None
        try:
            with grpc.insecure_channel(worker.addr) as channel:
                stub = mapper_pb2_grpc.MapperServicesStub(channel)
                reply = stub.DoMap(arg, timeout=DEFAULT_MAP_TIMEOUT)
        except grpc.RpcError as err:
            error = (
                WorkerStatus.DEAD
            )  # Anything bad happens, consiser the worker as down
            if err.code() == grpc.StatusCode.UNAVAILABLE:
                logger.DUMP_LOGGER.error(
                    "Error occurred while sending DoMap RPC to Node %s. UNAVAILABLE",
                    str(worker),
                )
            elif err.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                logger.DUMP_LOGGER.error(
                    "Error occurred while sending DoMap RPC to Node %s. DEADLINE_EXCEEDED",
                    str(worker),
                )
            else:
                logger.DUMP_LOGGER.error(
                    "Error occurred while sending DoMap RPC to Node %s. Unknown. Error: %s",
                    str(worker),
                    str(err),
                )
        with self.mutex:
            if reply is None:
                assert error is not None
                # Update in the tasks map that this job is failed
                task.status = TaskStatus.FAILED
                worker.status = error
                logger.DUMP_LOGGER.error(
                    "Map task FAILED. task: %s worker: %s", task, worker
                )
                return
            # Update in the tasks map and store the results in necessary files
            task.status = TaskStatus.COMPLETED
            task.mapper_id = worker.worker_id
            worker.status = WorkerStatus.FREE
            logger.DUMP_LOGGER.info(
                "Map task COMPLETED. task: %s worker: %s", task, worker
            )

    def __run_map(self, iteration: int) -> None:
        """run map task"""
        while True:
            completed = True
            self.mutex.acquire()
            for i in range(self.n_map):
                task = self.map_tasks[i]
                if task.status in (TaskStatus.PENDING, TaskStatus.FAILED):
                    task = self.map_tasks[i]
                    # Find a FREE worker
                    free_workers = list(
                        filter(lambda x: x.status == WorkerStatus.FREE, self.mappers)
                    )
                    if len(free_workers) == 0:
                        logger.DUMP_LOGGER.error(
                            "No worker found for the task %s: %s.", i, str(task)
                        )
                    else:
                        worker = free_workers[0]
                        arg = mapper_pb2.DoMapTaskArgs(
                            map_id=i,
                            start_idx=task.start_idx,
                            end_idx=task.end_idx,
                            n_reduce=self.n_reduce,
                            # centroids=self.centroids,
                            filename=self.ip_file,
                        )
                        centroids_pb2 = list(
                            map(
                                lambda x: common_messages_pb2.Point(x=x[0], y=x[1]),
                                self.centroids,
                            )
                        )
                        arg.centroids.extend(centroids_pb2[: self.n_centroids])
                        logger.DUMP_LOGGER.info(
                            "Assigning map task %s: %s to worker %s",
                            i,
                            str(task),
                            str(worker),
                        )

                        task.status = TaskStatus.RUNNING
                        worker.status = WorkerStatus.BUSY
                        self.executor.submit(self.__submit_map_task, task, arg, worker)

                completed = completed and (task.status == TaskStatus.COMPLETED)
            self.mutex.release()
            if completed:
                logger.DUMP_LOGGER.info(
                    "ALL MAP tasks are finished for iter: %s", iteration
                )
                break
            time.sleep(SLEEP_TIME)

    def __run_reduce(self, iteration: int) -> None:
        """run reduce task"""
        while True:
            completed = True
            self.mutex.acquire()
            for i in range(self.n_reduce):
                task = self.reduce_tasks[i]
                if task.status in (TaskStatus.PENDING, TaskStatus.FAILED):
                    task = self.reduce_tasks[i]
                    # Find a FREE worker
                    free_workers = list(
                        filter(lambda x: x.status == WorkerStatus.FREE, self.reducers)
                    )
                    if len(free_workers) == 0:
                        logger.DUMP_LOGGER.error(
                            "No worker found for the task %s: %s.", i, str(task)
                        )
                    else:
                        worker = free_workers[0]
                        arg = reducer_pb2.DoReduceTaskArgs(reduce_id=task.reduce_id)
                        arg.mapper_address.extend(task.mapper_address)

                        # arg.mapper_address.

                        logger.DUMP_LOGGER.info(
                            "Assigning reduce task %s: %s to worker %s",
                            i,
                            str(task),
                            str(worker),
                        )
                        task.status = TaskStatus.RUNNING
                        worker.status = WorkerStatus.BUSY
                        self.executor.submit(
                            self.__submit_reduce_task, task, arg, worker
                        )

                completed = completed and (task.status == TaskStatus.COMPLETED)
            self.mutex.release()
            if completed:
                logger.DUMP_LOGGER.info(
                    "ALL REDUCE tasks are finished for iter: %s ", iteration
                )
                self.centroids = self.new_centroids + self.centroids
                logger.DUMP_LOGGER.info(
                    "New centroids for iter: %s are: %s ",
                    iteration,
                    self.centroids[0 : self.n_centroids],
                )
                break
            time.sleep(SLEEP_TIME)

    def run(self):
        """run job"""
        for i in range(self.n_iterations):
            logger.DUMP_LOGGER.info("Starting iteration %s MAP", i)
            self.__run_map(i)

            self.mutex.acquire()
            self.reduce_tasks = [
                ReduceTask(reduce_id=i, status=TaskStatus.PENDING)
                for i in range(self.n_reduce)
            ]
            for task in self.reduce_tasks:
                task.mapper_address = list(
                    map(lambda x: self.mappers[x.mapper_id].addr, self.map_tasks)
                )  # task.mapper_address [map_id] = host_ip:port
                # logger.DUMP_LOGGER.info("Mapper Addrs: %s", task.mapper_address)

            logger.DUMP_LOGGER.info(
                "Reduce Tasks: [%s]", "][".join(map(str, self.reduce_tasks))
            )

            # Clean the last map task
            for task in self.map_tasks:
                task.status = TaskStatus.PENDING
            self.mutex.release()

            logger.DUMP_LOGGER.info("Starting iteration %s Reduce", i)
            self.__run_reduce(i)

            # TODO: Check convergence. If it converges, then stop

        with open('Data/centroid.txt', "w", encoding="UTF-8") as file:
            # file.write(str(self.centroids[0:self.n_centroids]))
            file.write(str(self.centroids))
        self.stop()


if __name__ == "__main__":
    with open("config.yaml", "r", encoding="UTF-8") as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
        master_cfg = config["master"]
        mappers = config["mappers"]
        reducers = config["reducers"]

    logger.set_logger("logs/", "master.txt", "master", LOGGING_LEVEL)
    master = Master(**master_cfg, mappers=mappers, reducers=reducers)
    master.start()
    master.run()
    master.stop()
