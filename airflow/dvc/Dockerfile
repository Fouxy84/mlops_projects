FROM python:3.12-slim

WORKDIR /workspace

RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "dvc[http]" requests

CMD ["sleep", "infinity"]
