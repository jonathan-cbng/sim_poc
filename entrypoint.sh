#!/bin/bash

BASE_SUBNET=${BASE_SUBNET:-"2001:db8:abcd"}
NUM_RTS=${NUM_RTS:-150}
AP_ID=${AP_ID:-1}

echo "Using IPv6 prefix: ${BASE_SUBNET}"
echo "AP ${AP_ID}: Number of RTs: ${NUM_RTS}"

add_ip_addr() {
  local ip_addr=$1
  echo "Adding IPv6 address: ${ip_addr}"
  ip -6 addr add ${ip_addr}/64 dev eth0 || true
}

echo "Adding IPv6 addresses for AP ${AP_ID}"
add_ip_addr "${BASE_SUBNET}::1:1"

for rt_id in $(seq 1 ${NUM_RTS}); do
  IPV6_ADDR="${BASE_SUBNET}::2:$(printf "%x" ${rt_id})"
  add_ip_addr "${IPV6_ADDR}"
done

#ip addr
exec python main.py
