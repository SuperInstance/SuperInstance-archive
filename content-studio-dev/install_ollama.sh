#!/bin/bash
# Script to install Ollama and download models in background

echo "=== Installing Ollama ==="
curl -fsSL https://ollama.com/install.sh | sh

echo ""
echo "=== Starting Ollama Service ==="
ollama serve > /tmp/ollama.log 2>&1 &
OLLAMA_PID=$!
echo "Ollama started with PID: $OLLAMA_PID"

echo "Waiting 5 seconds for Ollama to initialize..."
sleep 5

echo ""
echo "=== Starting Model Downloads in Background ==="
echo "This will download ~5.2GB total. Progress logged to /tmp/ollama_downloads.log"
echo ""

# Download models in background
(
  echo "$(date): Starting llama3.2:1b download (1.3GB)..." >> /tmp/ollama_downloads.log
  ollama pull llama3.2:1b >> /tmp/ollama_downloads.log 2>&1
  echo "$(date): llama3.2:1b complete!" >> /tmp/ollama_downloads.log

  echo "$(date): Starting llama3.2:3b download (2.0GB)..." >> /tmp/ollama_downloads.log
  ollama pull llama3.2:3b >> /tmp/ollama_downloads.log 2>&1
  echo "$(date): llama3.2:3b complete!" >> /tmp/ollama_downloads.log

  echo "$(date): Starting qwen2.5-coder:3b download (1.9GB)..." >> /tmp/ollama_downloads.log
  ollama pull qwen2.5-coder:3b >> /tmp/ollama_downloads.log 2>&1
  echo "$(date): qwen2.5-coder:3b complete!" >> /tmp/ollama_downloads.log

  echo "$(date): ALL MODELS DOWNLOADED!" >> /tmp/ollama_downloads.log
) &

DOWNLOAD_PID=$!
echo "Model downloads running in background (PID: $DOWNLOAD_PID)"
echo ""
echo "Check progress with: tail -f /tmp/ollama_downloads.log"
echo "Check what's downloaded: ollama list"
echo ""
echo "Installation complete! Models downloading in background..."
