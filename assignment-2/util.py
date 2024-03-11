"""
Helper functions
"""
import time


def current_time_millis() -> int:
    """Current time in MS"""
    return int(time.time() * 1000)
