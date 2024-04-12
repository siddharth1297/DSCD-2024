"""
MapReduce Master run
"""
import argparse
import logging
import time

import master
import logger

LOGGING_LEVEL = logging.INFO
SLEEP_TIME = 3  # second


def main(**kwargs) -> None:
    """main function"""
    logger.set_logger("logs/", "master.txt", "master", LOGGING_LEVEL)
    mr_master = master.Master(**kwargs)
    mr_master.start()

    while not mr_master.is_job_done():
        try:
            time.sleep(SLEEP_TIME)
        except KeyboardInterrupt:
            logger.DUMP_LOGGER.info("CTRL+C. Exiting")
            break
    mr_master.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MapReduce Master",
        epilog="$ python3 run_master.py --port 8085 -M 3 -R 2 -K 2 -I 3 -F centroid.txt",
    )
    parser.add_argument("-P", "--port", help="Port", required=True, type=int)
    parser.add_argument("-M", "--nmap", help="No of map jobs", required=True, type=int)
    parser.add_argument(
        "-R", "--nreduce", help="No of reduce jobs", required=True, type=int
    )
    parser.add_argument(
        "-K", "--ncentroids", help="No of centroids", required=True, type=int
    )
    parser.add_argument(
        "-I", "--niter", help="No of iterations", required=True, type=int
    )
    parser.add_argument("-F", "--file", help="Input file", required=True, type=str)

    args = parser.parse_args()

    main(
        port=str(args.port),
        n_map=args.nmap,
        n_reduce=args.nreduce,
        n_centroids=args.ncentroids,
        n_iterations=args.niter,
        ip_file=args.file,
    )
