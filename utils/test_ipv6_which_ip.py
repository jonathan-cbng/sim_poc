#!/usr/bin/env python3
import argparse
import asyncio
import logging
import sys
from pathlib import Path

import httpx
from fastapi import status

# Configure logging
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("test_ipv6_which_ip")

IPV6_PREFIX = "2001:db8:abcd"


async def check_which_ip(ipv6_addr: str, port: int = 8000, timeout: float = 2.0) -> bool:
    url = f"http://[{ipv6_addr}]:{port}/which_ip"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            if resp.status_code == status.HTTP_200_OK:
                logger.debug(f"Success: {url}")
                return True
            else:
                logger.warning(f"Non-200 response from {url}: {resp.status_code}")
                return False
    except Exception as e:
        logger.error(f"Failed to reach {url}: {e}")
        return False


async def main(num_aps: int, num_rts: int):
    ap_base_ipv6 = f"{IPV6_PREFIX}:{{}}::1:1"

    # Check AP addresses first
    ap_tasks = []
    for i in range(1, num_aps + 1):
        ipv6_addr = ap_base_ipv6.format(i)
        ap_tasks.append(check_which_ip(ipv6_addr))
    ap_results = await asyncio.gather(*ap_tasks)
    ap_success = sum(ap_results)
    logger.info(f"{ap_success}/{num_aps} AP addresses responded to /which_ip")

    # Then check RT addresses
    rt_tasks = []
    for i in range(1, num_aps + 1):
        base_subnet = f"{IPV6_PREFIX}:{i}"
        for rt_id in range(1, num_rts + 1):
            rt_addr = f"{base_subnet}::2:{rt_id:x}"
            rt_tasks.append(check_which_ip(rt_addr))
    rt_results = await asyncio.gather(*rt_tasks)
    rt_success = sum(rt_results)
    logger.info(f"{rt_success}/{num_aps * num_rts} RT addresses responded to /which_ip")

    num_total = num_aps + num_aps * num_rts
    success = ap_success + rt_success
    if success != num_total:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test all AP IPv6 addresses for /which_ip endpoint.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-a",
        "--num_aps",
        type=int,
        default=2,
        help="Number of Access Points (APs) to check.",
    )
    parser.add_argument(
        "-r",
        "--num_rts",
        type=int,
        default=10,
        help="Number of Routes (RTs) per AP (unused).",
    )
    parser.add_argument(
        "output_file",
        nargs="?",
        type=Path,
        default=Path("./docker-compose.yaml"),
        help="Docker Compose YAML file (unused).",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging.")
    args = parser.parse_args()
    logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    asyncio.run(main(args.num_aps, args.num_rts))
