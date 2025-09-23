"""
Utility classes and functions for worker nodes (APs and RTs).
"""
#######################################################################################################################
# Imports
#######################################################################################################################

import asyncio
import contextlib
import random
import time

#######################################################################################################################
# Globals
#######################################################################################################################


#######################################################################################################################
# Body
#######################################################################################################################


def zero_centred_rand(extent: float):
    """
    Generate a random float in the range [-extent, +extent].

    Args:
        extent (float): The maximum absolute value for the random float.

    Returns:
        float: A random float in the range [-extent, +extent].
    """

    return (random.random() * 2 * extent) - extent


@contextlib.asynccontextmanager
async def fix_execution_time(duration, tag="", logger=None):
    """
    Async context manager that ensures that the code block within it runs for a fixed duration.
    If the code block takes less time than the specified duration, it will sleep for the remaining
    time. If it takes longer, it will log a warning.

    Usage:
        async with heartbeat_timer(duration, tag, logger):
            ...
    """
    start = time.monotonic()
    try:
        yield
    finally:
        elapsed = time.monotonic() - start
        if elapsed > duration:
            if logger:
                logger.warning(f"{tag}: Heartbeat loop missed deadline by {elapsed - duration:.2f}s")
            await asyncio.sleep(0)
        else:
            await asyncio.sleep(duration - elapsed)


#######################################################################################################################
# End of file
#######################################################################################################################
