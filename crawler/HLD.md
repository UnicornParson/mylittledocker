# High-Level Design: crawler_endpoint

## 1. Overview

crawler_endpoint — это локальный orchestration-сервис, работающий как промежуточный слой между:

- SearXNG (поиск и discovery URL)
- Web (fetch страниц)
- Storage (локальное сохранение контента)
- LLM Agents (потребители данных)

Сервис предоставляет два интерфейса на одном порту:

- HTTP REST API (Flask)
- MCP API (Model Context Protocol endpoint)

Оба интерфейса используют общие внутренние сервисы (search, fetch, storage).

---

## 2. Goals

- Единая точка доступа к поиску + crawling
- Детерминированное сохранение всех результатов
- Полная наблюдаемость (logs + persisted data)
- Поддержка LLM-агентов через MCP
- Простота расширения pipeline (rerank, embeddings, caching)

---

## 3. System Architecture
```
            ┌────────────────────────────┐
            │        LLM Agent           │
            └────────────┬───────────────┘
                         │
      ┌──────────────────┴──────────────────┐
      │     crawler_endpoint (1 port)       │
      │                                    │
      │  ┌──────────────┐   ┌────────────┐ │
      │  │ Flask API     │   │ MCP API     │ │
      │  │ /api/*        │   │ /mcp/*      │ │
      │  └──────┬───────┘   └─────┬───────┘ │
      │         │                 │          │
      │         └──────┬──────────┘          │
      │                Core Engine           │
      │                                      │
      │   ┌──────────────┐                   │
      │   │ Search Client │ (SearXNG)        │
      │   └──────┬───────┘                   │
      │          │                           │
      │   ┌──────▼───────┐                   │
      │   │ Fetch Engine  │ (HTTP/Playwright)│
      │   └──────┬───────┘                   │
      │          │                           │
      │   ┌──────▼───────┐                   │
      │   │ Extractor     │ (Trafilatura)    │
      │   └──────┬───────┘                   │
      │          │                           │
      │   ┌──────▼───────┐                   │
      │   │ Storage Layer │ (volume)         │
      │   └──────────────┘                   │
      └──────────────────────────────────────┘
```



---

## 4. API Design

### 4.1 Flask REST API

Base path: `/api`

#### POST /api/crawl
Input:
```json
{
  "query": "string",
  "top_k": 5
}

Output:

{
  "query": "...",
  "results": [
    {
      "url": "...",
      "text": "...",
      "path": "data/pages/xxx.txt"
    }
  ]
}
GET /api/search

Proxy to SearXNG (format=json)

GET /api/fetch

Fetch single URL and extract text

4.2 MCP API

Base path: /mcp

POST /mcp/tools/call

Tool schema:

search
crawl
fetch_page

Example:

{
  "tool": "crawl",
  "input": {
    "query": "linux",
    "top_k": 5
  }
}

Output:

{
  "content": "...",
  "artifacts": [
    {
      "type": "text",
      "path": "data/pages/abc.txt"
    }
  ]
}
5. Core Modules
5.1 SearchClient
wraps SearXNG API
normalizes results
removes duplicates
5.2 FetchEngine
async HTTP client
retry policy
timeout control
optional Playwright fallback
5.3 Extractor
Trafilatura primary
fallback: readability-lxml
outputs clean text
5.4 Storage Layer

Filesystem-based:

/data
  /pages
    <hash>.txt
    <hash>.html
  manifest.json
5.5 Logger

File-based:

/app/access.log

Logs:

query
urls
latency
errors
6. Deployment

Single container:

Flask app
MCP router
shared core engine

Volume mounts:

/data
/access.log
7. Concurrency Model
asyncio event loop
semaphore-limited fetch (default: 10)
non-blocking search pipeline
8. Failure Handling
retry fetch (2–3 times)
skip dead URLs
degrade gracefully if SearXNG unavailable
9. Security Model
local-only trusted environment
no auth initially
optional future: API key middleware
10. Future Extensions
Redis queue for jobs
vector DB (RAG layer)
embeddings pipeline
reranking (cross-encoder)
caching layer for URLs