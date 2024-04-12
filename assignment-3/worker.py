"""
MapReduce Worker
"""
import argparse
import logging
import time

import grpc
import master_pb2
import master_pb2_grpc

import logger

LOGGING_LEVEL = logging.INFO
SLEEP_TIME = 3


class Worker:
    """MapReduce Worker"""

    def __init__(self, **kwargs) -> None:
        self.worker_id = kwargs["worker_id"]
        self.master_addr = kwargs["master_addr"]
        self.server_addr = f"0.0.0.0:{kwargs['server_port']}"

    def run(self) -> None:
        """Run indefinitely"""
        while True:
            job = self.__ask_for_job()
            if job.job_type == master_pb2.JobType.EXIT:
                logger.DUMP_LOGGER.info("Exiting")
                break
            if job.job_type == master_pb2.JobType.NO_JOB:
                logger.DUMP_LOGGER.info("No job")
                time.sleep(SLEEP_TIME)
                continue

    def __ask_for_job(self) -> master_pb2.GetJobReply:
        """Asks master for job"""
        logger.DUMP_LOGGER.info("Asking master for job")
        args = master_pb2.GetJobArgs(
            worker_id=self.worker_id, worker_addr=self.server_addr
        )
        try:
            with grpc.insecure_channel(self.master_addr) as channel:
                stub = master_pb2_grpc.MasterServicesStub(channel)
                reply = stub.GetJob(args)
        except grpc.RpcError as err:
            if err.code() == grpc.StatusCode.UNAVAILABLE:
                logger.DUMP_LOGGER.error("Error RPC GetJob. UNAVAILABLE")
            else:
                logger.DUMP_LOGGER.error("Error RPC GetJob. Unknown. %s", str(err))
            return master_pb2.GetJobReply(job_type=master_pb2.JobType.EXIT)

        logger.DUMP_LOGGER.info("Got job of type %s.", reply.job_type)
        return reply


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MapReduce Worker",
        epilog="$ python3 worker.py -M 127.0.0.1:8085 -I 0 -P 8090",
    )
    parser.add_argument("-I", "--id", help="Worker ID", required=True, type=int)
    parser.add_argument(
        "-M", "--master", help="master ip:port", required=True, type=str
    )
    parser.add_argument("-P", "--port", help=" Worker Port", required=True, type=int)
    args = parser.parse_args()

    logger.set_logger(
        "logs/", f"worker_{args.id}.txt", f"worker-{args.id}", LOGGING_LEVEL
    )
    Worker(worker_id=args.id, master_addr=args.master, server_port=str(args.port)).run()
