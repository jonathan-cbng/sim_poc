#!/usr/bin/env python3
import yaml

NUM_APS = 2
NUM_RTS = 10
BASE_IPV4 = "10.{}.0.2"
BASE_IPV4_SUBNET = "10.{}.0.0/16"
BASE_IPV6 = "2001:db8:abcd:{}::fffe"
BASE_IPV6_SUBNET = "2001:db8:abcd:{}::/64"

services = {}
networks = {}

for i in range(1, NUM_APS + 1):
    ap_name = f"ap{i}"
    net_name = f"apnet{i}"
    ipv4_addr = BASE_IPV4.format(i)
    ipv6_addr = BASE_IPV6.format(i)
    services[ap_name] = {
        "build": ".",
        "container_name": ap_name,
        "privileged": True,
        "environment": [f"BASE_SUBNET=2001:db8:abcd:{i}", f"AP_ID={i}", f"NUM_RTS={NUM_RTS}"],
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

docker_compose = {"version": "3.8", "services": services, "networks": networks}

with open("../docker-compose.generated.yaml", "w") as f:
    yaml.dump(docker_compose, f, sort_keys=False)

print(f"Generated docker-compose.generated.yaml with {NUM_APS} APs")
