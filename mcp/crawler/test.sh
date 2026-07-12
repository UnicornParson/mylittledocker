#!/usr/bin/env bash
# test.sh — сборка и запуск контейнера для unit-тестов crawler_endpoint
#
# Usage:
#   ./test.sh

set -euo pipefail

IMAGE_NAME="crawler-endpoint-test"
DOCKERFILE="Dockerfile.test"
CONTEXT="."

echo "=== Building test image: ${IMAGE_NAME} ==="
docker build -t "${IMAGE_NAME}" -f "${DOCKERFILE}" "${CONTEXT}"

echo ""
echo "=== Running tests ==="
# Load environment variables from .env (skip empty lines and comments)
ENV_ARGS=()
while IFS='=' read -r key value; do
    # skip blank lines and comments
    if [[ -n "$key" && "$key" != \#* ]]; then
        ENV_ARGS+=("--env" "${key}=${value}")
    fi
done < .env

docker run --rm "${ENV_ARGS[@]}" "${IMAGE_NAME}"
