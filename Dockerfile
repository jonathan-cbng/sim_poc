# Builder stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    python3-dev \
    pybind11-dev \
    iproute2 curl procps \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy source and build
COPY . .
RUN cmake -S . -B build && cmake --build build --config Release && cmake --install build

# Runtime stage
FROM python:3.12-slim AS runtime

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy built extension from builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages/node_sim*.so /usr/local/lib/python3.12/site-packages/

COPY src_py .
COPY entrypoint.sh entrypoint.sh
RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
