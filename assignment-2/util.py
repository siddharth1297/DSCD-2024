"""
Helper functions
"""
import time


def current_time_millis() -> int:
    """Current time in MS"""
    return int(time.time() * 1000)


def current_time_second() -> int:
    """Current time in S"""
    return int(time.time())
