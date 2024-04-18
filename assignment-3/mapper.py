"""
MapReduce Worker
"""

import os
import argparse
import logging
import time
from concurrent import futures
import typing
import grpc
import yaml

import logger

import mapper_pb2
import mapper_pb2_grpc

import common_messages_pb2

LOGGING_LEVEL = logging.DEBUG
MAX_WORKERS = 2

BASE_DIR = "Data/"


class ReduceTaskHandler:
    """Reduce Task"""

    def __init__(self, reduce_id: int, map_id: int):
        self.reduce_key = reduce_id
        self.map_id = map_id
        self.partition_file = f"M{self.map_id}/partition_{self.reduce_key}.txt"
        return cls(reduce_id = request.parition_key, map_id = request.map_id)

    def __str__(self):
        return f"[{self.reduce_key}: {self.map_id} {self.partition_file}]"

    @classmethod
    def from_pb_to_impl_GetDataArgs(cls, request: mapper_pb2.GetDataArgs):
        """Converts DoMapTaskArgs(pb format) to ReduceTask"""
        return cls(reduce_id = request.parition_key, map_id = request.map_id)

class MapTask:
    """MapTask structure"""

    def __init__(self, map_id, start_idx, end_idx, n_reduce, centroids, filename):
        self.map_id = map_id

        self.start_idx = start_idx
        self.end_idx = end_idx

        self.n_reduce = n_reduce

        self.centroids = centroids

        self.filename = filename
        self.output_file_path_list = []

        self.points = []
        self.points_list_clustered = []

    def __str__(self):
        return f"[{self.map_id}: ({self.start_idx}-{self.end_idx}) {self.centroids}]"

    def read_points_from_file(self) -> None:
        """Stores points in a list of tuples"""
        points = []
        with open(self.filename, "r", encoding="UTF-8") as file:
            for line in file:
                parts = line.strip().split(",")
                if len(parts) == 2:
                    x, y = parts
                    points.append((float(x), float(y)))
        self.points = points[self.start_idx : self.end_idx]

    def cluster_points(self) -> None:
        """Groups points into k clusters"""
        for point in self.points:
            min_distance = float("inf")
            closest_centroid_index = -1
            for idx, centroid in enumerate(self.centroids):
                distance = (point[0] - centroid[0]) ** 2 + (point[1] - centroid[1]) ** 2
                if distance < min_distance:
                    min_distance = distance
                    closest_centroid_index = idx
            self.points_list_clustered.append((closest_centroid_index, (point, 1)))

    def create_mappers_directory(self):
        """Create Mappers directory if not already created"""
        # Create Mappers directory
        data_directory = "Data"
        mappers_directory = os.path.join(data_directory, "Mappers")
        if not os.path.exists(mappers_directory):
            os.makedirs(mappers_directory)
            logger.DUMP_LOGGER.debug(f"Directory '{mappers_directory}' created.")
        else:
            logger.DUMP_LOGGER.debug(f"Directory '{mappers_directory}' already exists.")

        folder_name = os.path.join("Data", "Mappers", f"M{self.map_id}")
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
            logger.DUMP_LOGGER.debug(f"Folder '{folder_name}' created.")
        else:
            logger.DUMP_LOGGER.debug(f"Folder '{folder_name}' already exists.")

    def partition_points(self):
        """Partition the points into R buckets and write to files"""
        partitions = {}
        for i in range(self.n_reduce):
            partitions[i] = []
        for key, (point, frequency) in self.points_list_clustered:
            partition_key = key % self.n_reduce
            partitions[partition_key].append((key, (point, frequency)))

        file_namer = 0

        for partition_key, partition_points in partitions.items():
            partition_filename = (
                f"Data/Mappers/M{self.map_id}/partition_{file_namer}.txt"
            )
            self.output_file_path_list.append(partition_filename)
            file_namer += 1
            with open(partition_filename, "w", encoding="UTF-8") as partition_file:
                for key, ((x, y), frequency) in partition_points:
                    partition_file.write(f"({key},(({x},{y}), 1))\n")

    def do_map_task(self) -> None:
        """Do the map task as per the specificatio"""
        logger.DUMP_LOGGER.info("Got a map task: %s", str(self))
        self.read_points_from_file()
        self.cluster_points()
        self.create_mappers_directory()
        self.partition_points()
        logger.DUMP_LOGGER.info("Map task Done. task: %s.", str(self))

    @classmethod
    def from_pb_to_impl_DoMapTaskArgs(cls, request: mapper_pb2.DoMapTaskArgs):
        """Converts DoMapTaskArgs(pb format) to MapTask"""
        centroids = list(map(lambda x: (x.x, x.y), request.centroids))
        return cls(
            map_id=request.map_id,
            start_idx=request.start_idx,
            end_idx=request.end_idx,
            n_reduce=request.n_reduce,
            centroids=centroids,
            filename=request.filename,
        )


class Mapper(mapper_pb2_grpc.MapperServicesServicer):
    """MapReduce Worker"""

    def __init__(self, **kwargs) -> None:
        self.worker_id = kwargs["worker_id"]
        self.worker_port = kwargs["worker_port"]
        self.grpc_server = None
        self.reduce_task_handler = []

    def __serve(self) -> None:
        """Start services"""
        self.grpc_server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=MAX_WORKERS),
            options=(("grpc.so_reuseport", 0),),
        )
        mapper_pb2_grpc.add_MapperServicesServicer_to_server(self, self.grpc_server)
        self.grpc_server.add_insecure_port("0.0.0.0" + ":" + str(self.worker_port))
        self.grpc_server.start()
        logger.DUMP_LOGGER.info("started at port %s", self.worker_port)

    def start(self) -> None:
        """Start mapper"""
        self.__serve()

    def stop(self) -> None:
        """Stop"""
        self.grpc_server.stop(1.5).wait()

    def DoMap(
        self, request: mapper_pb2.DoMapTaskArgs, context
    ) -> mapper_pb2.DoMapTaskReply:
        """Implement the DoMap RPC method"""
        map_task = MapTask.from_pb_to_impl_DoMapTaskArgs(request)
        map_task.do_map_task()
        response = mapper_pb2.DoMapTaskReply(
            files=map_task.output_file_path_list, worker_id=self.worker_id
        )
        return response
    
    
    def dummy_DoMap(self):
        m = MapTask(
            0,
            0,
            32,
            3,
            [(0.4, 7.2), (0.8, 9.8), (-1.5, 7.3), (8.1, 3.4), (7.3, 2.3)],
            "./Data/inputs/points.txt",
        )
        m.do_map_task()

    def __get_data(self, reduce_key: int, map_id: int) -> typing.List[typing.Tuple[int, typing.Tuple[float, int]]]:
        """Get the data from fs"""
        partition_file = f"M{map_id}/partition_{reduce_key}.txt"
        data = []
        with open(partition_file, "r", encoding="UTF-8") as file:
            for line in file:
                if line == "":
                    continue
                comma_separated = line.replace('(', '').replace(')', '')
                values = comma_separated.split(',')
                if len(values) != 4:
                    print("Error while parssing file. Line: ", line)
                item = (int(values[0]), ((float(values[1]), float(values[2])), int(values[3])))
                data.append(item)
        print(data)
        exit(1)
        return data

    def GetData(
        self, request: mapper_pb2.GetDataArgs, context
    ) -> mapper_pb2.GetDataReply:
        """Implement the GetData RPC method"""
        data = self.__get_data(request.parition_key, request.map_id)
        


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MapReduce Mapper",
        epilog="$ python3 mapper.py -I 0",
    )
    parser.add_argument("-I", "--id", help="Worker ID", required=True, type=int)
    args = parser.parse_args()
    with open("config.yaml", "r", encoding="UTF-8") as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
        mappers = config["mappers"]
        this_mapper_addr = config["mappers"][args.id]
    logger.set_logger(
        "logs/", f"mapper_{args.id}.txt", f"mapper-{args.id}", LOGGING_LEVEL
    )
    mapper = Mapper(worker_id=args.id, worker_port=this_mapper_addr.split(":")[1])
    mapper.start()

    # mapper.dummy_DoMap()

    try:
        time.sleep(86400)  # Sleep for 24 hours or until interrupted
    except KeyboardInterrupt:
        pass
    mapper.stop()
