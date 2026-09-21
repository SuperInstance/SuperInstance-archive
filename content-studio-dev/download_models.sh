#!/bin/bash
# Download Ollama models in background
# Run this AFTER Ollama is installed and running

echo "=== Checking Ollama is running ==="
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "ERROR: Ollama is not running!"
    echo "Start it with: ollama serve &"
    exit 1
fi

echo "✓ Ollama is running"
echo ""
echo "=== Starting Model Downloads in Background ==="
echo "Total download: ~5.2GB"
echo "Progress logged to: /tmp/ollama_downloads.log"
echo ""

# Start downloads in background
(
  echo "$(date): Starting model downloads..." > /tmp/ollama_downloads.log

  echo "$(date): Downloading llama3.2:1b (1.3GB)..." | tee -a /tmp/ollama_downloads.log
  ollama pull llama3.2:1b >> /tmp/ollama_downloads.log 2>&1
  echo "$(date): ✓ llama3.2:1b complete!" | tee -a /tmp/ollama_downloads.log

  echo "$(date): Downloading llama3.2:3b (2.0GB)..." | tee -a /tmp/ollama_downloads.log
  ollama pull llama3.2:3b >> /tmp/ollama_downloads.log 2>&1
  echo "$(date): ✓ llama3.2:3b complete!" | tee -a /tmp/ollama_downloads.log

  echo "$(date): Downloading qwen2.5-coder:3b (1.9GB)..." | tee -a /tmp/ollama_downloads.log
  ollama pull qwen2.5-coder:3b >> /tmp/ollama_downloads.log 2>&1
  echo "$(date): ✓ qwen2.5-coder:3b complete!" | tee -a /tmp/ollama_downloads.log

  echo "$(date): ALL DOWNLOADS COMPLETE!" | tee -a /tmp/ollama_downloads.log
  echo ""
  echo "Verify with: ollama list"
) &

DOWNLOAD_PID=$!
echo "✓ Downloads started in background (PID: $DOWNLOAD_PID)"
echo ""
echo "Monitor progress:"
echo "  tail -f /tmp/ollama_downloads.log"
echo ""
echo "Check downloaded models:"
echo "  ollama list"
echo ""
echo "You can continue working while these download..."
