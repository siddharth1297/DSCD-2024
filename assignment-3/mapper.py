"""
MapReduce Worker
"""

import os
import argparse
import logging
import time
from concurrent import futures
import grpc
import yaml

import logger

import mapper_pb2
import mapper_pb2_grpc


LOGGING_LEVEL = logging.INFO
MAX_WORKERS = 2


class MapTask:
    """MapTask structure"""

    def __init__(self, map_id, start_idx, end_idx, n_reduce, centroids, filename):
        self.map_id = map_id
        self.start_idx = start_idx
        self.end_idx = end_idx
        self.n_reduce = n_reduce
        self.centroids = centroids
        self.filename = filename
        self.output_file_list_path = []

        self.points = []
        self.points_list_clustered = []

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
        # TODO(@Arjun): Concat ids and whatever needed in the end
        directory = "Mappers"
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.DUMP_LOGGER.info(f"Directory '{directory}' created.")
        else:
            logger.DUMP_LOGGER.info(f"Directory '{directory}' already exists.")

    def create_map_folder(self):
        """Create Folder for the current Map Task"""
        folder_name = f"M{self.map_id}"
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
            logger.DUMP_LOGGER.info(f"Folder '{folder_name}' created.")
        else:
            logger.DUMP_LOGGER.info(f"Folder '{folder_name}' already exists.")

    def partition_points(self):
        """Partition the points into R buckets and write to files"""
        partitions = {}
        for key, (point, frequency) in self.points_list_clustered:
            partition_key = key % self.n_reduce
            if partition_key not in partitions:
                partitions[partition_key] = []
            partitions[partition_key].append((key, (point, frequency)))

        file_namer = 0

        for partition_key, partition_points in partitions.items():
            partition_filename = f"/Mappers/M{self.map_id}/partition_{file_namer}.txt"
            self.output_file_list_path.append(partition_filename)
            file_namer += 1
            with open(partition_filename, "w", encoding="UTF-8") as partition_file:
                for key, ((x, y), frequency) in partition_points:
                    partition_file.write(f"({key},(({x},{y}), 1))\n")

    def do_map_task(self) -> None:
        """Do the map task as per the specificatio"""
        self.read_points_from_file()
        self.cluster_points()
        self.create_mappers_directory()
        self.create_map_folder()
        self.partition_points()

    @classmethod
    def from_pb_to_impl_DoMapTaskArgs(cls, request: mapper_pb2.DoMapTaskArgs):
        """Converts DoMapTaskArgs(pb format) to MapTask"""
        return cls(
            map_id=request.map_id,
            start_idx=request.start_idx,
            end_idx=request.end_idx,
            n_reduce=request.n_reduce,
            centroids=request.centroids,
            filename=request.filename,
        )


class Mapper(mapper_pb2_grpc.MapperServicesServicer):
    """MapReduce Worker"""

    def __init__(self, **kwargs) -> None:
        self.worker_id = kwargs["worker_id"]
        self.worker_port = kwargs["worker_port"]
        self.grpc_server = None

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
            files=map_task.output_file_list_path, worker_id=self.worker_id
        )
        return response

    def GetData(
        self, request: mapper_pb2.GetDataArgs, context
    ) -> mapper_pb2.GetDataReply:
        """Implement the GetData RPC method"""
        # Your implementation here
        pass


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
    try:
        time.sleep(86400)  # Sleep for 24 hours or until interrupted
    except KeyboardInterrupt:
        pass
    mapper.stop()
