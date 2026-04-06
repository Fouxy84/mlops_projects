FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY src/inference/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/src/

ENV PYTHONPATH=/app
ENV MODEL_TYPE=svm

EXPOSE 8000

CMD ["uvicorn", "src.inference.main:app", "--host", "0.0.0.0", "--port", "8000"]
