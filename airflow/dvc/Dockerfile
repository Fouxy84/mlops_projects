FROM python:3.12-slim

WORKDIR /workspace

RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "dvc[s3]" requests beautifulsoup4

CMD ["sleep", "infinity"]
