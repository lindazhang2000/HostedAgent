# syntax=docker/dockerfile:1.6
# Built from the repo root so it can COPY both shared/ and agents/cora/.
FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm

WORKDIR /app
COPY shared/requirements-base.txt shared/requirements-af.txt ./
# Step 1: agentserver pulls in agent-framework-core==rc3
RUN pip install --no-cache-dir -r requirements-base.txt
# Step 2: rc6 packages override the rc3 pin
RUN pip install --no-cache-dir --upgrade --force-reinstall -r requirements-af.txt

COPY shared /app/shared
COPY data /app/data
COPY agents/cora/main.py /app/main.py

ENV PYTHONPATH=/app PORT=8088
EXPOSE 8088
CMD ["python", "-m", "main"]
