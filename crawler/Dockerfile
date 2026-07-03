FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    libnss3 \
    libnspr4 \
    libatk1.0-0t64 \
    libatk-bridge2.0-0t64 \
    libcups2t64 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2t64 \
    && rm -rf /var/lib/apt/lists/*

COPY crawler_endpoint/requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium
RUN playwright install-deps chromium

COPY crawler_endpoint/ /app/crawler_endpoint/
COPY local_test.py /app/local_test.py
COPY entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

ENV PYTHONPATH=/app

EXPOSE 8000
EXPOSE 8100

CMD ["/app/entrypoint.sh"]