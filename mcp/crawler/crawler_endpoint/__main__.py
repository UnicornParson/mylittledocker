"""Entrypoint: gunicorn --bind 0.0.0.0:8000 crawler_endpoint.__main__:app"""

from crawler_endpoint.app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)