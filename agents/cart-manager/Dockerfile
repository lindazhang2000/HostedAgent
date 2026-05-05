# syntax=docker/dockerfile:1.6
FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm
WORKDIR /app
COPY shared/requirements-base.txt shared/requirements-af.txt ./
RUN pip install --no-cache-dir -r requirements-base.txt
RUN pip install --no-cache-dir --upgrade --force-reinstall -r requirements-af.txt
COPY shared /app/shared
COPY data /app/data
COPY agents/cart-manager/main.py /app/main.py
ENV PYTHONPATH=/app PORT=8088
EXPOSE 8088
CMD ["python", "-m", "main"]
