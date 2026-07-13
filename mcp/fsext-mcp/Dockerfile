FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
RUN mkdir -p /workspace
# OCR (можно убрать, если не нужен)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tesseract-ocr && \
    rm -rf /var/lib/apt/lists/*
COPY fsext-mcp-server-python-main /opt/fsext-mcp-server
RUN pip install --upgrade pip && \
    pip install /opt/fsext-mcp-server

RUN useradd -m -u 1000 mcp

USER mcp

WORKDIR /workspace

EXPOSE 8000

ENTRYPOINT ["fsext", "--transport", "http","--host", "0.0.0.0","--port", "8000","--lock-root", "/workspace"]
