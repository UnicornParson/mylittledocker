# High-Level Design: Neo Forge Bridge (FastMCP)

## Архитектура

**Neo Forge Bridge** — MCP-сервер, предоставляющий инструменты для генерации изображений через Stable Diffusion WebUI API.

### Компоненты

1. **FastMCP Server** (`mcp`) — точка входа для MCP-клиентов (Claude Desktop и др.). Определяет инструменты и обрабатывает запросы.
2. **HTTP Client** (`get_http_client()`) — асинхронный httpx-клиент, выполняющий запросы к SD WebUI. Поддерживает Basic Auth, настраиваемый таймаут, и логирование запросов/ответов через event hooks.
3. **Хелперы** — функции для работы с изображениями (base64 encode/decode, сохранение с метаданными PNG).

### Внешние API

- **SD WebUI API** (`http://127.0.0.1:7860` по умолчанию) — REST API Stable Diffusion.
- **MCP Client** (любой MCP-совместимый клиент) — взаимодействует через Streamable HTTP transport.

### Запуск

```
python bridge2.py
```

Переменные окружения: см. `.env.example`.

### Инструменты

- `generate_image` — txt2img генерация.
- `get_sd_models` — список доступных моделей.
- `set_sd_model` — переключение активной модели.
- `get_sd_upscalers` — список апскейлеров.
- `upscale_images` — пакетный апскейл изображений.

### Логирование подключений

При каждом исходящем HTTP-запросе к SD WebUI в лог попадает:
- `Connection attempt: METHOD URL (base_url=...)` — перед отправкой запроса.
- `Connection result: METHOD URL -> STATUS REASON` — после получения ответа.