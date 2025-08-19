# Workbench Simulator: Multi-AP Single-Worker Prototype

A lightweight simulator that models multiple Access Points (APs) and their Remote Terminals (RTs) interacting with an
Application Under Test (AUT).

Technology stack:

- Control Plane: FastAPI
- Persistence: SQLite + SQLAlchemy (with dependency-injected session)
- Worker: Single process hosting many AP actors via asyncio
- IPC: In-memory multiprocessing queues (no external broker)
- Outbound HTTP: aiohttp sessions (per AP, optional IPv6 source binding)

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

| Method | Path               | Purpose                                            |
| ------ | ------------------ | -------------------------------------------------- |
| POST   | /aps               | Create & start an AP (optionally with initial RTs) |
| GET    | /aps               | List statuses of all APs                           |
| GET    | /aps/{ap_id}       | Get status for a single AP                         |
| POST   | /aps/{ap_id}/rts   | Add RTs to an existing AP                          |
| POST   | /aps/{ap_id}/alarm | Trigger AP-level or RT-level alarms                |
| DELETE | /aps/{ap_id}       | Stop and remove an AP                              |

### Example: Create an AP

```bash
curl -X POST http://localhost:8000/aps \
  -H "Content-Type: application/json" \
  -d '{
    "ap_id": "ap-1",
    "aut_base_url": "http://localhost:8080",
    "heartbeat_seconds": 10,
    "rt_count": 5
  }'
```

### Add RTs

```bash
curl -X POST http://localhost:8000/aps/ap-1/rts \
  -H "Content-Type: application/json" \
  -d '{"add": 3}'
```

### Trigger Alarms

AP-level:

```bash
curl -X POST http://localhost:8000/aps/ap-1/alarm \
  -H "Content-Type: application/json" \
  -d '{"target":"ap"}'
```

25% of RTs:

```bash
curl -X POST http://localhost:8000/aps/ap-1/alarm \
  -H "Content-Type: application/json" \
  -d '{"target":"rt","percent":25}'
```

Specific RT IDs:

```bash
curl -X POST http://localhost:8000/aps/ap-1/alarm \
  -H "Content-Type: application/json" \
  -d '{"target":"rt","rt_ids":[0,2,5]}'
```

### Delete AP

```bash
curl -X DELETE http://localhost:8000/aps/ap-1
```

## AUT Endpoint Expectations (Stubbed)

The simulator will attempt POST requests to (adjust or mock as needed):

- {aut_base_url}/ap/register
- {aut_base_url}/ap/heartbeat
- {aut_base_url}/ap/alarm
- {aut_base_url}/rt/register
- {aut_base_url}/rt/alarm

Return any 2xx to mark success.

## Testing: Overriding the DB

```python
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from control.app import app
from control.db import Base, get_db

engine = create_engine("sqlite:///./test_sim.db", connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base.metadata.create_all(bind=engine)


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_db
client = TestClient(app)
```

## Scaling Roadmap

1. Current: Single worker, many AP actors (sufficient for dev / moderate load).
2. Multi-worker: Shard APs across processes via hashing (extend WorkerManager).
3. External transport: Replace MP queues with Redis / NATS / RabbitMQ if multi-host.
4. Metrics: Add Prometheus exposition in control process.
5. Logging: Introduce structured JSON logs and correlation IDs.
6. High-scale timers: Move heartbeats to a central scheduler / timer wheel.

# Proof of Concept

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

The way we detect this is by setting the health check for each container to ping the `/which_ip` endpoint of the last IP
address assigned to the container (which is the last RT in the container).

## Pre-requisites

```bash
sudo apt install -y clang-format clang-tidy cppcheck pybind11-dev
```
