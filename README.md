# sim_poc

Simple proof of concept for the AP/RT simulator - currently tested to 75000 nodes (50 APs with 1500 RTs each).

The docker-compose file `docker-compose.yaml` sets up a network with 10 containers. Each container simulates one AP with
2500 RTs by assinging a unique IP address to each node. Then a single fastapi server connects to all IP addresses in the
network and provides an endpoint `/which_ip` which returns the IP address on which the request was received.

In `utils` you can find two helper scripts:

- `gen_compose.py` generates the `docker-compose.yaml` file based on the number of APs and RTs you want to simulate.
- `test_ipv6_which_ip.py` is a simple test script that sends requests to all of the simulated APs to check that the
  `/which_ip` endpoint returns a 200 OK response and the correct IP address.

Note: To be able to handle the very large numbers of ipv6 addresse required (1 per RT+ 1 per AP), it is necessary to
increase the garbage collection thresholds for the IPv6 neighbor cache.

To do this, you can add the following lines to your `/etc/sysctl.conf` file:

```bash
net.ipv6.neigh.default.gc_thresh1 = 262144
net.ipv6.neigh.default.gc_thresh2 = 524288
net.ipv6.neigh.default.gc_thresh3 = 1048576
```

Alternatively, you can run the following commands:

```bash
sudo sysctl -w net.ipv6.neigh.default.gc_thresh1=262144
sudo sysctl -w net.ipv6.neigh.default.gc_thresh2=524288
sudo sysctl -w net.ipv6.neigh.default.gc_thresh3=1048576
```

## Performance considerations

Adding many IPv6 addresses to the system is not without its performance considerations. When using a large number of
IPv6 addresses the host kernel actually takes some time to honour the ip assignments requested by the guest containers.

The easiest way to see when the system is actually ready to handle requests is to look at the output of `top`. If you
see that the `kworker/u512:0-ipv6_addrconf` process is consuming a lot of CPU time, it means that the kernel is still
processing the IPv6 address assignments.
