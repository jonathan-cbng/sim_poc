"""
Utility classes and functions for worker nodes (APs and RTs).
"""
#######################################################################################################################
# Imports
#######################################################################################################################

import asyncio
import contextlib
import functools
import ipaddress
import random
import time

import netifaces

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
                logger.warning(f"{tag}: Heartbeat loop missed deadline by {elapsed - duration:.2f}s. Resetting timer.")
            await asyncio.sleep(duration)
        else:
            await asyncio.sleep(duration - elapsed)


@functools.lru_cache(maxsize=1)
def get_ipv6_prefix():
    """
    Get the first global IPv6 address and return its network prefix as a string (no trailing colons,
    no '::'), using the actual prefix length, or a default link-local prefix if none found.

    Caches the result for efficiency.
    """

    for iface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(iface).get(netifaces.AF_INET6, [])
        for addr in addrs:
            ip = addr["addr"].split("%")[0]  # Remove zone index if present
            ip_obj = ipaddress.IPv6Address(ip)
            # Skip loopback and unspecified
            if ip_obj.is_loopback or ip_obj.is_unspecified:
                continue
            if ip_obj.is_global:
                len = addr["netmask"].split("/")[1]
                network = ipaddress.IPv6Network(f"{ip}/{len}", strict=False)
                return (str(network.network_address).rstrip(":"), network.prefixlen)

    return ("fe80", 64)  # Default to link-local


#######################################################################################################################
# End of file
#######################################################################################################################
