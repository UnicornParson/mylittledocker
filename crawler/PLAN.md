
---

# PLAN.md

```markdown
# Implementation Plan: crawler_endpoint

## Phase 0 — Environment Setup

- [ ] Create project structure
- [ ] Initialize Python environment
- [ ] Add dependencies:
  - flask
  - httpx
  - trafilatura
  - asyncio
  - uvicorn (optional MCP server)
- [ ] Create Dockerfile
- [ ] Add docker-compose service

---

## Phase 1 — Core HTTP Server

- [ ] Create Flask app entrypoint
- [ ] Define base routes:
  - /api/crawl
  - /api/search
  - /api/fetch
- [ ] Add request validation (pydantic or manual)

---

## Phase 2 — SearXNG Client

- [ ] Implement SearchClient
- [ ] Add method:
  - search(query, engines=None, top_k=None)
- [ ] Normalize response schema
- [ ] Deduplicate URLs
- [ ] Add timeout handling

---

## Phase 3 — Fetch Engine

- [ ] Implement async fetcher
- [ ] Add:
  - HTTP GET
  - retry logic
  - timeout handling
- [ ] Add optional Playwright fallback (disabled by default)

---

## Phase 4 — Content Extraction

- [ ] Implement Extractor
- [ ] Add trafilatura extraction
- [ ] Add fallback readability parser
- [ ] Normalize output:
  - title
  - text
  - metadata

---

## Phase 5 — Storage Layer

- [ ] Create directory structure in /data
- [ ] Implement:
  - save_html()
  - save_text()
  - save_manifest()
- [ ] Add content hashing (sha256 URL)

---

## Phase 6 — Logging System

- [ ] Implement access.log writer
- [ ] Log:
  - request start
  - search results count
  - fetch success/failure
  - latency
- [ ] Ensure log rotation readiness

---

## Phase 7 — MCP API Layer

- [ ] Create MCP router (/mcp)
- [ ] Implement tool schema:
  - search
  - crawl
  - fetch_page
- [ ] Map MCP calls → core engine functions

---

## Phase 8 — Integration Layer

- [ ] Connect Flask API → core engine
- [ ] Connect MCP API → core engine
- [ ] Ensure shared service layer

---

## Phase 9 — Concurrency & Performance

- [ ] Add asyncio task group for crawling
- [ ] Add semaphore (default 10)
- [ ] Optimize pipeline (search → fetch → extract)

---

## Phase 10 — Dockerization

- [ ] Build Docker image
- [ ] Mount volumes:
  - /data
  - /access.log
- [ ] Configure env vars:
  - SEARXNG_URL
  - DATA_PATH

---

## Phase 11 — Testing

- [ ] Test /api/search
- [ ] Test /api/fetch
- [ ] Test /api/crawl
- [ ] Test MCP tool calls
- [ ] Validate logging output
- [ ] Validate data persistence

---

## Phase 12 — Production Hardening (optional)

- [ ] Add rate limiting
- [ ] Add API key auth
- [ ] Add caching layer
- [ ] Add retry backoff tuning
- [ ] Add observability metrics

---

## Definition of Done

- SearXNG search works via API
- crawler_endpoint returns structured crawl results
- pages are saved to disk
- access.log is populated
- MCP endpoint is callable
- Flask API is functional on same port