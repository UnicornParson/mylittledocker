# High-Level Design: crawler_endpoint

## 1. Overview

crawler_endpoint — локальный orchestration-сервис, промежуточный слой между:

- **SearXNG** — поиск и discovery URL
- **Web** — fetch страниц (HTTP / Playwright)
- **Storage** — локальное сохранение контента на диск
- **LLM Agents** — потребители данных через MCP

Сервис предоставляет **два независимых HTTP-сервера** в одном контейнере:

| Интерфейс      | Порт  | Технология | Транспорт        |
|----------------|-------|------------|------------------|
| Flask REST API | 8000  | gunicorn   | HTTP (запрос-ответ) |
| FastMCP SSE    | 8100  | uvicorn    | Server-Sent Events  |

Оба интерфейса используют общие внутренние сервисы через **Service Layer** (явный DI).

---

## 2. Goals

- Единая точка доступа к поиску + crawling
- Детерминированное сохранение всех результатов (sha256(content) — идемпотентность)
- Полная наблюдаемость (structured logs + persisted data + stderr логи вызовов)
- Поддержка LLM-агентов через MCP protocol (SSE transport)
- Простота расширения pipeline (rerank, embeddings, caching — pluggable steps)

---

## 3. System Architecture

```
┌────────────────────────────┐
│        LLM Agent           │
└────────────┬───────────────┘
             │
   ┌─────────┴──────────────────┐
   │     crawler_endpoint       │
   │   (два процесса)           │
   │                            │
   │  ┌──────────────────────┐ │
   │  │ Flask API (gunicorn) │ │
   │  │ порт 8000            │ │
   │  │ /api/*               │ │
   │  └──────────┬───────────┘ │
   │  ┌──────────▼───────────┐ │
   │  │ FastMCP SSE (uvicorn)│ │
   │  │ порт 8100            │ │
   │  │ Streaming HTTP       │ │
   │  └──────────┬───────────┘ │
   │             │              │
   │  ┌──────────▼────────────┐│
   │  │   Service Layer       ││
   │  │   (DI container)      ││
   │  └──────────┬────────────┘│
   │             │              │
   │  ┌──────────▼─────────┐  │
   │  │ SearchClient        │ ←── SearXNG
   │  └──────────┬─────────┘  │
   │             │              │
   │  ┌──────────▼─────────┐  │
   │  │ FetchEngine         │ ──→ HTTP / Playwright
   │  └──────────┬─────────┘  │
   │             │              │
   │  ┌──────────▼─────────┐  │
   │  │ Extractor            │  │
   │  │ (trafilatura)        │  │
   │  └──────────┬─────────┘  │
   │             │              │
   │  ┌──────────▼─────────┐  │
   │  │ StorageLayer        │ ──→ /data
   │  └────────────────────┘  │
   └──────────────────────────┘
```

---

## 4. Module Structure (Python package)

```
crawler_endpoint/
├── __init__.py
├── __main__.py              # gunicorn entrypoint для Flask API
├── run_mcp.py               # uvicorn entrypoint для FastMCP SSE
├── app.py                   # Flask app factory (create_app) — только /api/*
├── config.py                # pydantic-settings (load env → settings object)
├── di.py                    # simple DI container / service wiring
├── models.py                # dataclasses / pydantic models
├── routes/
│   ├── __init__.py
│   ├── api.py               # Flask blueprint /api/*
│   └── mcp.py               # FastMCP server с тремя инструментами
├── services/
│   ├── __init__.py
│   ├── search_client.py     # SearXNG HTTP client
│   ├── fetch_engine.py      # async fetch (httpx) + optional Playwright
│   ├── extractor.py         # trafilatura + readability fallback
│   ├── storage.py           # filesystem storage /data
│   └── logger.py            # structured logging
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_search.py
│   ├── test_fetch.py
│   ├── test_extractor.py
│   └── test_storage.py
└── requirements.txt
```

Также в корне crawler/:
- `entrypoint.sh` — запускает gunicorn + uvicorn параллельно
- `Dockerfile` — сборка образа, EXPOSE 8000 8100

---

## 5. Configuration (pydantic-settings)

| Variable             | Default               | Description                      |
|----------------------|-----------------------|----------------------------------|
| `SEARXNG_URL`        | `http://searxng:8080` | SearXNG internal endpoint        |
| `DATA_PATH`          | `/data`               | Storage root                     |
| `LOG_PATH`           | `/data/access.log`    | Path to access log               |
| `MAX_CONCURRENCY`    | `10`                  | Max parallel fetch workers       |
| `FETCH_TIMEOUT`      | `15`                  | HTTP timeout (seconds)           |
| `FETCH_RETRIES`      | `2`                   | Retry count                      |
| `PLAYWRIGHT_ENABLED` | `false`               | Enable Playwright fallback       |
| `LOG_LEVEL`          | `INFO`                | Logging level                    |
| `MCP_PORT`           | `8100`                | FastMCP SSE server port          |
| `CRAWLER_PORT`       | `8000`                | Flask REST API port              |
| `GUNICORN_WORKERS`   | `4`                   | Количество gunicorn-воркеров      |

---

## 6. Data Models

### SearchResult
```python
@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str
    engine: str
    score: float
```

### CrawlResult
```python
@dataclass
class CrawlResult:
    url: str
    title: str | None
    text: str
    html_path: str       # /data/pages/<sha256>.html
    text_path: str       # /data/pages/<sha256>.txt
    fetch_time_ms: int
    extracted_with: str  # "trafilatura" | "readability"
```

### ManifestEntry (manifest.json)
```json
{
  "url": "https://...",
  "hash": "sha256hex",
  "title": "...",
  "fetched_at": "2026-07-02T17:00:00Z",
  "fetch_time_ms": 1234,
  "extracted_with": "trafilatura",
  "text_bytes": 54321
}
```

---

## 7. API Design

### 7.1 Flask REST API

Base path: `/api` — порт 8000

#### `POST /api/crawl`
Поиск → fetch → extract → save → вернуть результаты.

```json
{
  "query": "linux kernel tuning",
  "top_k": 5
}
```

Response:
```json
{
  "query": "linux kernel tuning",
  "results": [...],
  "total_fetched": 5,
  "total_time_ms": 3450
}
```

#### `GET /api/search`
Прокси к SearXNG (format=json). Возвращает сырые URL без fetch.

#### `GET /api/fetch`
Fetch одного URL + extract.

### 7.2 FastMCP SSE (порт 8100)

Три инструмента, доступные через MCP protocol с SSE-транспортом:

| Tool         | Description                                      |
|--------------|--------------------------------------------------|
| `search`     | Поиск по SearXNG, без fetch                     |
| `crawl`      | Поиск → fetch всех результатов → extract → save |
| `fetch_page` | Fetch одного URL → extract → save               |

Каждый вызов логируется в stdout/stderr контейнера:

```
[2026-07-03T03:00:00] INFO [mcp.tools] tool=search query="linux kernel" top_k=5
[2026-07-03T03:00:01] INFO [mcp.tools] tool=search query="linux kernel" top_k=5 results=10 elapsed_ms=1234
```

---

## 8. Core Modules

### 8.1 SearchClient
- HTTP client к SearXNG (`httpx.AsyncClient`)
- Нормализация ответа: `SearchResult` list
- Дедупликация URL (canonicalization: strip tracking params)
- Timeout: 10s

### 8.2 FetchEngine
- `asyncio` + `httpx.AsyncClient` для параллельного fetch
- Semaphore: `MAX_CONCURRENCY` (default 10)
- Retry: `FETCH_RETRIES` attempts с exponential backoff
- Timeout: `FETCH_TIMEOUT` seconds
- Playwright fallback: если `PLAYWRIGHT_ENABLED=true`

### 8.3 Extractor
- Primary: `trafilatura.extract()`
- Fallback: `readability.Document.summary()` (html2text)

### 8.4 Storage Layer
```
/data/
  pages/
    <sha256(url)>.html    # raw HTML
    <sha256(url)>.txt     # extracted text
  manifest.json           # append-only log
```

### 8.5 Logger
- File-based structured logging (JSON lines)
- Log path: `LOG_PATH` (default `/data/access.log`)

---

## 9. Deployment

- **Container**: единый Docker-образ на базе `python:3.13-slim`
- **Entrypoint**: `entrypoint.sh` запускает gunicorn и uvicorn параллельно
- **Порты**: EXPOSE 8000 (REST API) и 8100 (MCP SSE)

```yaml
services:
  searxng: ...
  crawler_endpoint:
    build: .
    ports:
      - "${CRAWLER_PORT:-8000}:8000"
      - "${MCP_PORT:-8100}:8100"
    environment:
      - SEARXNG_URL=http://searxng:8080
      - DATA_PATH=/data
      - MCP_PORT=8100
    volumes:
      - crawler_data:/data
    depends_on:
      searxng:
        condition: service_healthy
```

---

## 10. Security Model

- **local-only trusted environment**
- **No auth** initially (служебный сервис внутри Docker network)
- MCP endpoint опубликован на отдельном порту — можно скрыть reverse-proxy

---

## 11. Future Extensions (Roadmap)

- Redis job queue для долгих crawl-задач
- Vector DB integration (Qdrant / Chroma) для RAG
- Embeddings pipeline (sentence-transformers)
- Reranking (cross-encoder)
- Caching layer для URL (TTL-based dedup)
- Web UI для просмотра результатов
- Rate limiter (per-agent)

---

## 12. Definition of Done (MVP)

- [x] SearXNG search работает через API
- [x] `POST /api/crawl` возвращает структурированные результаты
- [x] `GET /api/search` — прокси к SearXNG
- [x] `GET /api/fetch` — fetch одиночного URL + extract
- [x] Извлечённый текст сохраняется на диск
- [x] Raw HTML сохраняется
- [x] `manifest.json` обновляется
- [x] `access.log` заполняется структурированными записями
- [x] FastMCP SSE сервер на отдельном порту (8100)
- [x] Три MCP инструмента: search, crawl, fetch_page
- [x] Логирование всех вызовов MCP в stdout/stderr
- [x] gunicorn + uvicorn в одном контейнере через entrypoint.sh
- [x] Контейнер собирается и запускается через `docker-compose up`
- [x] Документация usage.md обновлена (LM Studio, SSE)