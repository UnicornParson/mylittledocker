#!/usr/bin/env bash
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi
export SD_UPSCALER_1="R-ESRGAN 4x+"
# Build the image
docker build -t mcp-sd-bridge .

# Run the container interactively
# Map port 3000, mount output directory, pass environment variables
docker run -it --rm \
  -p 5103:3000 \
  -v "$(pwd)/output:/app/output" \
  -e SD_WEBUI_URL="$SD_WEBUI_URL" \
  -e SD_OUTPUT_DIR="$SD_OUTPUT_DIR" \
  -e REQUEST_TIMEOUT="$REQUEST_TIMEOUT" \
  -e SD_RESIZE_MODE="$SD_RESIZE_MODE" \
  -e SD_UPSCALE_MULTIPLIER="$SD_UPSCALE_MULTIPLIER" \
  -e SD_UPSCALE_WIDTH="$SD_UPSCALE_WIDTH" \
  -e SD_UPSCALE_HEIGHT="$SD_UPSCALE_HEIGHT" \
  -e SD_UPSCALER_1="$SD_UPSCALER_1" \
  -e SD_UPSCALER_2="$SD_UPSCALER_2" \
  -e HOST="$HOST" \
  -e PORT="$PORT" \
  mcp-sd-bridge