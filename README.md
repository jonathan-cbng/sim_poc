# Workbench Simulator: Multi-AP Single-Worker Prototype

> **System Overview and Architecture**

## Purpose

Simulate a large, dynamic network of Networks, Hubs, Access Points (APs) and Remote Terminals (RTs) for testing and
validating control plane logic and API endpoints.

## Architecture

- **Control Plane:** FastAPI server managing Network/Hub/AP/RT lifecycle and exposing RESTful API. Networks/Hubs are
  managed here.
- **Worker Process:** Single Python process simulating multiple APs and their RTs using asyncio.
- **Inter-process Communication:** ZeroMQ for command and status messaging between Control Plane and Workers.
- **Data Storage:** In-memory for state persistence.

## Control Plane

- Support high scalability (50,000+ nodes) using multiple workers (future-proof).
- Dynamic AP/RT creation and deletion at runtime.
- Configurable heartbeat intervals per AP.
- Allow scripting and bulk configuration via API or config file (inc config saving from current state).
- Heirarchical data model:
  - Network
    - Hub
      - Access Point (AP)
        - Remote Terminal (RT)
  - All entities have unique IDs and indices within their parent scope. All entities are addressable via API using
    either ID or index.
  - Provides API endpoints for:
    - Creating/deleting Networks, Hubs, APs, RTs
    - Configuring heartbeat intervals
    - Triggering alarms at AP or RT level (specific IDs or percentage sampling)
    - Querying status of all entities
  - Provides zeroMQ PUB/SUB socket for sending commands to Worker process.
  - Provides zeroMQ PUSH/PULL socket for receiving status updates from Worker process.

## Worker Tasks

- Simulates one (or maybe more, TBC) APs and all associated RTs.
- Simulate node registration and AP/RT heartbeats and alarm events.
- Aggregate and report status for all APs and RTs at 1 Hz.
- Handle commands from Control Plane (create/delete APs/RTs, trigger alarms) sent via ZeroMQ subscription socket.
- Send status updates back to Control Plane via ZeroMQ push socket.
- (In future) Support simluated AP/RT web server endpoints for NMS to poll/query. Each AP/RT will have its own IPv6
  address, generated dynamically from a common prefix using network/hub/ap/rt index. Worker task will assign and manage
  these addresses.

## API Contract (examples)

- `POST /ap` — Create an AP (with optional RTs)
- `POST /ap/{ap_id}/rt` — Add RTs to an AP
- `POST /ap/{ap_id}/alarm` — Trigger alarms
- `GET /ap` — List all AP statuses
- `DELETE /ap/{ap_id}` — Remove an AP and its RTs

## Constraints

- All operations must be possible at runtime (no restarts).
- Heartbeat and status aggregation must not block other operations.
- System must be testable and scriptable (e.g., via Postman or pytest).
- Must support both local and remote AP simulation (future-proof).

## Testing

- Tests are run using `PYTHONPATH=. pytest --maxfail=3 -v`
- Unit tests for API endpoints and core logic.
- Integration tests simulating various scenarios (e.g., high load, alarm conditions).
- Performance tests to validate scalability.
- Code coverage target: 95%+.

## Example Scenario

1. User creates 10 APs, each with 64 RTs.
2. User triggers a 25% RT alarm on AP 3.
3. User deletes AP 5; all its RTs are removed.
4. System continues to aggregate and report status for remaining APs/RTs.

## Output

- All API responses must be JSON.
- Status endpoints must return up-to-date heartbeat and alarm state for each AP/RT.

______________________________________________________________________

A lightweight simulator that models multiple Access Points (APs) and their Remote Terminals (RTs) interacting with an
Application Under Test (AUT).

## Technology stack

- **Control Plane:** FastAPI (Python)
- **Process Management:**
  - Local: Python multiprocessing, 1 process per AP
  - Remote: paramiko/fabric (SSH-based process launch) (for future study)
- **Inter-process Communication:** ZeroMQ (PUB/SUB for commands, PUSH/PULL for responses), served from the control API
  server
- **AP Simulator:** Python process simulating a single AP and its RTs. Each AP process runs:
  - **Async Runtime:** asyncio event loop
  - **AP Actor:** Manages AP heartbeat, registration, and AP-level alarms
  - **RT Actors:** Each RT is an asyncio Task managed by the AP actor, handling registration, periodic status updates,
    and RT-level alarms
- **Outbound HTTP:** aiohttp sessions inside each AP simulator process

Scripting/configuration of this system should be possible using postman, but there should be a way of loading a
pre-defined configuration (e.g. JSON file) to create a large number of APs/RTs in one go.

## Capabilities

- Create / delete APs dynamically
- Configure per-AP heartbeat interval
- Create initial RTs with AP or add more later
- RT & AP registration logic stubs (POST to AUT endpoints)
- AP-level alarms
- RT-level alarms (specific IDs or percentage sampling)
- Status aggregation (1 Hz) from worker → control API
- Test-friendly DB session dependency for overrides

## Directory Layout

```
control/
  app.py          FastAPI endpoints and models
  db.py           DB engine & get_db dependency
worker/
  manager.py      WorkerManager (spawns and commands worker process)
  worker.py       Async worker (AP + RT actors)
Dockerfile
docker-compose.yml
requirements.txt
README.md
.env.example
.gitignore
```

## Quick Start (Local Dev)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn control.app:app --reload
```

Control API: http://localhost:8000

(Optional) Start a mock AUT (httpbin via docker-compose) for basic endpoint hit validation.

## Core Endpoints

| Method | Path              | Purpose                                            |
| ------ | ----------------- | -------------------------------------------------- |
| POST   | /ap               | Create & start an AP (optionally with initial RTs) |
| GET    | /ap               | List statuses of all APs                           |
| GET    | /ap/{ap_id}       | Get status for a single AP                         |
| POST   | /ap/{ap_id}/rt    | Add RTs to an existing AP                          |
| POST   | /ap/{ap_id}/alarm | Trigger AP-level or RT-level alarms                |
| DELETE | /ap/{ap_id}       | Stop and remove an AP and all underlying RTs       |

### Example: Create an AP

```bash
curl -X POST http://localhost:8000/ap \
  -H "Content-Type: application/json" \
  -d '{
    "ap_id": "1",
    "aut_base_url": "http://localhost:8080",
    "heartbeat_seconds": 10,
    "rt_count": 5
  }'
```

### Add RTs

```bash
curl -X POST http://localhost:8000/ap/{ap_id}/rts \
  -H "Content-Type: application/json" \
  -d '{"add": 3}'
```

### Trigger Alarms

AP-level:

```bash
curl -X POST http://localhost:8000/ap/{ap_id}/alarm \
  -H "Content-Type: application/json" \
  -d '{"target":"ap"}'
```

25% of RTs:

```bash
curl -X POST http://localhost:8000/ap/{ap_id}/alarm \
  -H "Content-Type: application/json" \
  -d '{"target":"rt","percent":25}'
```

Specific RT IDs:

```bash
curl -X POST http://localhost:8000/ap/{ap_id}/alarm \
  -H "Content-Type: application/json" \
  -d '{"target":"rt","rt_ids":[0,2,5]}'
```

### Delete AP

```bash
curl -X DELETE http://localhost:8000/ap/{ap_id}
```

## Scaling Roadmap

1. Current: Single worker, many AP actors (sufficient for dev / moderate load).
2. Multi-worker: Shard APs across processes via hashing (extend WorkerManager).
3. External transport: Replace MP queues with Redis / NATS / RabbitMQ if multi-host.
4. Metrics: Add Prometheus exposition in control process.
5. Logging: Introduce structured JSON logs and correlation IDs.
6. High-scale timers: Move heartbeats to a central scheduler / timer wheel.

# Experimental work

The `experimental/` folder contains two sub-projects:

## 1. multi-ip

This sub-project demonstrates large-scale AP/RT simulation using unique IPv6 addresses for each node. It includes:

- A `docker-compose.yaml` that sets up a network with multiple containers, each simulating one AP with many RTs (each RT
  and AP gets a unique IPv6 address).
- A FastAPI server that connects to all simulated IP addresses and provides a `/which_ip` endpoint to verify correct
  address assignment.
- Helper scripts:
  - `gen_compose.py`: Generates the `docker-compose.yaml` file based on the desired number of APs and RTs.
  - `test_ipv6_which_ip.py`: Sends requests to all simulated APs to check that the `/which_ip` endpoint returns the
    correct IP address.

**Performance Note:** Handling very large numbers of IPv6 addresses requires increasing the garbage collection
thresholds for the IPv6 neighbor cache. See the sysctl configuration below for details.

## 2. zmq

This sub-project provides a minimal demonstration of ZeroMQ-based communication, which is used for inter-process
messaging in the main simulator. It includes:

- `zmq_server.py`: A simple ZeroMQ server for receiving messages.
- `zmq_client.py`: A client for sending messages to the server.

These scripts can be used to test and validate the ZeroMQ PUB/SUB and PUSH/PULL patterns that are foundational to the
simulator's architecture.

______________________________________________________________________

**IPv6 Neighbor Cache Configuration:**

To handle large numbers of IPv6 addresses, add the following lines to your `/etc/sysctl.conf` file:

```bash
net.ipv6.neigh.default.gc_thresh1 = 262144
net.ipv6.neigh.default.gc_thresh2 = 524288
net.ipv6.neigh.default.gc_thresh3 = 1048576
```

Or apply them at runtime:

```bash
sudo sysctl -w net.ipv6.neigh.default.gc_thresh1=262144
sudo sysctl -w net.ipv6.neigh.default.gc_thresh2=524288
sudo sysctl -w net.ipv6.neigh.default.gc_thresh3=1048576
```

**Performance considerations:**

Adding many IPv6 addresses to the system is not without its performance considerations. When using a large number of
IPv6 addresses the host kernel actually takes some time to honour the IP assignments requested by the guest containers.

The way we detect this is by setting the health check for each container to ping the `/which_ip` endpoint of the last IP
address assigned to the container (which is the last RT in the container).

## Pre-requisites

```bash
sudo apt install -y clang-format clang-tidy cppcheck pybind11-dev
```
