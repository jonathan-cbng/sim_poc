#!/bin/bash

BASE_SUBNET=${BASE_SUBNET:-"2001:db8:abcd:1"}
NUM_RTS=${NUM_RTS:-150}
AP_ID=${AP_ID:-1}

echo "Using IPv6 prefix: ${BASE_SUBNET}"
echo "AP ${AP_ID}: Number of RTs: ${NUM_RTS}"

echo "Adding IPv6 addresses for AP ${AP_ID}"
for rt_id in $(seq 1 ${NUM_RTS}); do
  IPV6_ADDR="${BASE_SUBNET}::$(printf "%x" ${rt_id})"
  echo "Adding IPv6 address: ${IPV6_ADDR}"
  ip -6 addr add ${IPV6_ADDR}/64 dev eth0 || true
done

#ip addr
exec python main.py
