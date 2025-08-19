# Builder stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential cmake cppcheck clang-tidy \
    python3-dev pybind11-dev \
    iproute2 curl procps \
    && rm -rf /var/lib/apt/lists/*

COPY nodes/requirements-dev.txt nodes/requirements-dev.txt
RUN pip install --upgrade pip && pip install -r nodes/requirements-dev.txt

COPY nodes nodes

# Copy source for nodes package and build wheel
WORKDIR /app/nodes
RUN python -m build --wheel

# Runtime stage
FROM python:3.11-slim AS runtime

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy built wheel from builder stage and install
COPY --from=builder /app/nodes/dist/*.whl /tmp/
RUN pip install /tmp/*.whl

COPY src src
COPY utils utils
COPY entrypoint.sh entrypoint.sh
RUN chmod +x entrypoint.sh

EXPOSE 8000
ENV PYTHONPATH=/app

#ENTRYPOINT ["/app/entrypoint.sh"]
ENTRYPOINT ["python3", "utils/ap_demo.py"]
