FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y iproute2 curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt


COPY src/main.py main.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
