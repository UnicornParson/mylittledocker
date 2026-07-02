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
docker run --rm "${IMAGE_NAME}"