# Builder stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential cmake cppcheck clang-tidy \
    python3-dev pybind11-dev \
    iproute2 curl procps \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy source and build
COPY node_sim node_sim
WORKDIR /app/node_sim
RUN cmake -S . -B build && \
    cmake --build build --target cppcheck && \
    cmake --build build --config Release && \
    cmake --install build

# Runtime stage
FROM python:3.11-slim AS runtime

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy built extension from builder stage

RUN mkdir /app/node_sim
COPY --from=builder /app/node_sim/*.so node_sim
COPY --from=builder /app/node_sim/*.py node_sim
COPY src src
COPY utils utils
COPY entrypoint.sh entrypoint.sh
RUN chmod +x entrypoint.sh

EXPOSE 8000
ENV PYTHONPATH=/app

#ENTRYPOINT ["/app/entrypoint.sh"]
ENTRYPOINT ["python3", "utils/ap_demo.py"]
