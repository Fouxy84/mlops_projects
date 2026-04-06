FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY src/gateway/requirements.txt .
RUN pip install --upgrade pip
RUN pip install --default-timeout=100 --no-cache-dir -r requirements.txt
#RUN pip install --no-cache-dir -r requirements.txt

#COPY src/gateway/ /app/gateway
COPY . /app


CMD ["uvicorn", "src.gateway.main:app", "--host", "0.0.0.0", "--port", "8003"]
