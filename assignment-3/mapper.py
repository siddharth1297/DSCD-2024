"""
MapReduce Worker
"""

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
    
    # def begin_map_task(self):

        
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

    def __str__(self):
        return f"MapTask(map_id={self.map_id}, start_idx={self.start_idx}, end_idx={self.end_idx}, n_reduce={self.n_reduce}, centroids={self.centroids}, filename={self.filename})"

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
        MapTask.begin_map_task(map_task)


        pass

    def GetData(self, request, context):
        """Implement the GetData RPC method"""
        # Your implementation here
        pass
    
    def serve(self) -> None:
        self.grpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        mapper_pb2_grpc.add_MapperServicesServicer_to_server(self, self.grpc_server)
        self.grpc_server.add_insecure_port("0.0.0.0" + ":" + self.worker_port)
        self.grpc_server.start()
        logger.DUMP_LOGGER.info("Mapper Worker %s started at port %s",self.worker_id, self.port)
        

    # def run(self) -> None:
    #     """Run indefinitely"""
    #     while True:
    #         job = self.__ask_for_job()
    #         if job.job_type == master_pb2.JobType.EXIT:
    #             logger.DUMP_LOGGER.info("Exiting")
    #             break
    #         if job.job_type == master_pb2.JobType.NO_JOB:
    #             logger.DUMP_LOGGER.info("No job")
    #             time.sleep(SLEEP_TIME)
    #             continue

    # def __ask_for_job(self) -> master_pb2.GetJobReply:
    #     """Asks master for job"""
    #     logger.DUMP_LOGGER.info("Asking master for job")
    #     args = master_pb2.GetJobArgs(
    #         worker_id=self.worker_id, worker_addr=self.server_addr
    #     )
    #     try:
    #         with grpc.insecure_channel(self.master_addr) as channel:
    #             stub = master_pb2_grpc.MasterServicesStub(channel)
    #             reply = stub.GetJob(args)
    #     except grpc.RpcError as err:
    #         if err.code() == grpc.StatusCode.UNAVAILABLE:
    #             logger.DUMP_LOGGER.error("Error RPC GetJob. UNAVAILABLE")
    #         else:
    #             logger.DUMP_LOGGER.error("Error RPC GetJob. Unknown. %s", str(err))
    #         return master_pb2.GetJobReply(job_type=master_pb2.JobType.EXIT)

    #     logger.DUMP_LOGGER.info("Got job of type %s.", reply.job_type)
    #     return reply


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