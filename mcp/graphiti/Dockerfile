FROM python:3.12
RUN apt-get update && apt-get install -y --no-install-recommends  build-essential 
RUN pip install --no-cache-dir graphiti-core falkordb mcp httpx openai

EXPOSE 8000

# Запуск встроенного MCP-сервера Graphiti
ENTRYPOINT ["python", "-m", "graphiti_core.mcp", "--transport", "http", "--port", "8000"]
