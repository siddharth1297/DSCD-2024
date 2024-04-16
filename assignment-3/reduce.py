"""
MapReduce Reduce
"""

# pylint: disable=too-many-instance-attributes
from concurrent import futures

import grpc
import  reducer_service_pb2 as reducer_pb2
import reducer_service_pb2_grpc as reducer_pb2_grpc

from pathlib import Path
import datetime
import itertools
import os
import sys



class ReducerServiceServicer(reducer_pb2_grpc.ReducerServiceServicer):
    def __init__(self, reducer_name):
        self.reducer_name = reducer_name
        self.shuffled_and_sorted_data = {}
        self.path = ""
    


    def reduce(self, request, context):
        input_files = request.input_files
        output_path = request.reducer_output_path

        intermediate_data = {}
        for file_path in input_files:
            with open(file_path, "r") as file:
                for line in file:
                    centroid, point = line.split()
                    if centroid in intermediate_data:
                        intermediate_data[centroid].append(point)
                    else:
                        intermediate_data[centroid] = [point]

        updated_centroids = {}
        for centroid, points in intermediate_data:
            updated_centroid = self.update_centroid(centroid, points)
            updated_centroids[centroid] = updated_centroid

        with open(output_path, "w") as output_file:
            for centroid, updated_centroid in updated_centroids.items():
                output_file.write(f"{centroid} {updated_centroid}\n")

        return reducer_pb2.ReduceResponse(status=reducer_pb2.ReduceResponse.Status.SUCCESS)
    

    def update_centroid(self, centroid, points):
        points = [float(p) for p in points]
        if points:
            new_centroid = sum(points) / len(points)
        else: 
            new_centroid = centroid
        return new_centroid



class Reducer:

    def __init__(self, port, reducer_name):
        self.address = "localhost"
        self.port = port                       
        self.reducer_name = reducer_name
    
    def serve(self, reducer_name):

        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        reducer_pb2_grpc.add_ReducerServiceServicer_to_server(
            ReducerServiceServicer(reducer_name), server
        )
        server.add_insecure_port("[::]:" + self.port)
        server.start()
        server.wait_for_termination()


if __name__ == "__main__":
    # port = input("Enter port for server: ")
    port = sys.argv[1]
    reducer_name = sys.argv[2]
    myServer = Reducer(port, reducer_name)
    myServer.serve(reducer_name)