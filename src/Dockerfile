# syntax=docker/dockerfile:1.6
FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Foundry runtime probes /healthz and routes traffic to port 8088.
ENV PORT=8088
EXPOSE 8088

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8088"]
