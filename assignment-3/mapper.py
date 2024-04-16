"""
MapReduce Worker
"""

import os
import argparse
import logging
import time
from concurrent import futures
import grpc
import master_pb2
import master_pb2_grpc
import mapper_pb2
import mapper_pb2_grpc

import logger

LOGGING_LEVEL = logging.INFO
SLEEP_TIME = 3

class MapTask:
    def __init__(self, map_id, start_idx, end_idx, n_reduce, centroids, filename):
        self.map_id = map_id
        self.start_idx = start_idx
        self.end_idx = end_idx
        self.n_reduce = n_reduce
        self.centroids = centroids
        self.filename = filename

        self.output_file_list_path = []

    '''Stores points in a list of tuples'''
    def read_points_from_file(self):
        points = []
        with open(self.filename, 'r') as file:
            for line in file:
                parts = line.strip().split(', ')
                if len(parts) == 2:
                    x, y = parts
                    points.append((float(x), float(y)))
        return points[self.start_idx: self.end_idx]
    
    '''Groups points into k clusters'''
    def cluster_points(self, points):
        points_list_clustered = []
        for point in self.points:
            min_distance = float('inf')
            closest_centroid_index = -1
            for idx, centroid in enumerate(self.centroids):
                distance = (point[0] - centroid[0]) ** 2 + (point[1] - centroid[1]) ** 2
                if distance < min_distance:
                    min_distance = distance
                    closest_centroid_index = idx
            points_list_clustered.append((closest_centroid_index, (point, 1)))
        return points_list_clustered
    
    '''Create Mappers directory if not already created'''
    def create_mappers_directory():
        directory = 'Mappers'
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.DUMP_LOGGER.info(f"Directory '{directory}' created.")
        else:
            logger.DUMP_LOGGER.info(f"Directory '{directory}' already exists.")
    
    '''Create Folder for the current Map Task'''
    def create_map_folder(self):
        folder_name = f"M{self.map_id}"
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
            logger.DUMP_LOGGER.info(f"Folder '{folder_name}' created.")
        else:
            logger.DUMP_LOGGER.info(f"Folder '{folder_name}' already exists.")
    
    '''Partition the points into R files'''
    def partition_points(self):
        partitions = {}
        for key, (point, frequency) in self.points_list_clustered:
            partition_key = key % self.n_reduce
            if partition_key not in partitions:
                partitions[partition_key] = []
            partitions[partition_key].append((key, (point, frequency)))
        
        file_namer=0
        
        for partition_key, partition_points in partitions.items():
            partition_filename = f"/Mappers/M{self.map_id}/partition_{file_namer}.txt"
            self.output_file_list_path.append(partition_filename)
            file_namer+=1
            with open(partition_filename, 'w') as partition_file:
                for key, ((x, y), frequency) in partition_points:
                    partition_file.write(f"({key},(({x},{y}), 1))\n")

    def begin_map_task(self):
        points_list = self.read_points_from_file()
        points_list_clustered = self.cluster_points(points_list)
        self.create_mappers_directory()
        self.create_map_folder()
        self.partition_points()

                
    @classmethod
    def from_request(cls, request):
        return cls(
            map_id=request.map_id,
            start_idx=request.start_idx,
            end_idx=request.end_idx,
            n_reduce=request.n_reduce,
            centroids=request.centroids,
            filename=request.filename
        )

    
class Mapper (mapper_pb2_grpc.MapperServicesServicer):
    """MapReduce Worker"""

    def __init__(self, **kwargs) -> None:
        self.worker_id = kwargs["worker_id"]
        self.worker_port = kwargs["worker_port"]
        # self.server_addr = f"0.0.0.0:{kwargs['server_port']}"
        self.grpc_server=None
    
    
    def DoMap(self, request, context):
        """Implement the DoMap RPC method"""
        
        
        map_task = MapTask.from_request(request)
        map_task.begin_map_task(map_task)
        
        response = mapper_pb2.DoMapTaskReply(files = map_task.output_file_list_path, worker_id = self.worker_id)
        context.send_response(response)

        pass

    def GetData(self, request, context):
        """Implement the GetData RPC method"""
        # Your implementation here
        pass
    
    def serve(self) -> None:
        self.grpc_server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=1),
            options=(("grpc.so_reuseport", 0),),
        )
        mapper_pb2_grpc.add_MapperServicesServicer_to_server(self, self.grpc_server)
        self.grpc_server.add_insecure_port("0.0.0.0" + ":" + str(self.worker_port))
        self.grpc_server.start()
        logger.DUMP_LOGGER.info("Mapper Worker %s started at port %s",self.worker_id, self.worker_port)

        try:
            while True:
                time.sleep(86400)  # Sleep for 24 hours or until interrupted
        except KeyboardInterrupt:
                self.grpc_server.stop(0)
        



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MapReduce Worker",
        #epilog="$ python3 mapper.py -M 127.0.0.1:8085 -I 0 -P 8090",
        epilog="$ python3 mapper.py -I 0 -P 8090",
    )
    parser.add_argument("-I", "--id", help="Worker ID", required=True, type=int)
    #parser.add_argument(
    #    "-M", "--master", help="master ip:port", required=True, type=str
    #)
    parser.add_argument("-P", "--port", help=" Worker Port", required=True, type=int)
    args = parser.parse_args()

    logger.set_logger(
        "logs/", f"map_worker_{args.id}.txt", f"worker-{args.id}", LOGGING_LEVEL
    )
    # Mapper(worker_id=args.id, master_addr=args.master, server_port=str(args.port)).run()
    Mapper(worker_id=args.id, worker_port=args.port).serve()