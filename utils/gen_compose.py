#!/usr/bin/env python3
import logging
from pathlib import Path

import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

NUM_APS = 2
NUM_RTS = 10
BASE_IPV4 = "10.{}.0.2"
BASE_IPV4_SUBNET = "10.{}.0.0/16"
BASE_IPV6 = "2001:db8:abcd:{}::fffe"
BASE_IPV6_SUBNET = "2001:db8:abcd:{}::/64"


def write_docker_compose(num_aps: int, num_rts: int, output_file: Path):
    """Generate a Docker Compose file with the specified number of Access Points (APs) and Routes (RTs)."""
    services = {}
    networks = {}

    for i in range(1, num_aps + 1):
        ap_name = f"ap{i}"
        net_name = f"apnet{i}"
        ipv4_addr = BASE_IPV4.format(i)
        ipv6_addr = BASE_IPV6.format(i)
        services[ap_name] = {
            "build": ".",
            "container_name": ap_name,
            "privileged": True,
            "environment": [f"BASE_SUBNET=2001:db8:abcd:{i}", f"AP_ID={i}", f"NUM_RTS={num_rts}"],
            "networks": {net_name: {"ipv4_address": ipv4_addr, "ipv6_address": ipv6_addr}},
            "healthcheck": {
                "test": f"curl -g --fail http://[{ipv6_addr}]:8000/which_ip",
                "interval": "10s",
                "timeout": "3s",
                "retries": 3,
                "start_period": "120s",
            },
        }
        networks[net_name] = {
            "driver": "bridge",
            "enable_ipv6": True,
            "ipam": {"config": [{"subnet": BASE_IPV4_SUBNET.format(i)}, {"subnet": BASE_IPV6_SUBNET.format(i)}]},
        }

    docker_compose = {"services": services, "networks": networks}

    with output_file.open("w") as f:
        yaml.dump(docker_compose, f, sort_keys=False)

    logging.info(f"Generated docker-compose.yaml with {num_aps} APs and {num_rts} RTs")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Docker Compose file for APs and RTs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-a", "--num_aps", type=int, default=NUM_APS, help="Number of Access Points (APs) to generate.")
    parser.add_argument("-r", "--num_rts", type=int, default=NUM_RTS, help="Number of Routes (RTs) to generate.")
    parser.add_argument(
        "output_file",
        nargs="?",
        type=Path,
        default=Path("./docker-compose.yaml"),
        help="Output file for Docker Compose YAML.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging.")
    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    write_docker_compose(args.num_aps, args.num_rts, args.output_file)
