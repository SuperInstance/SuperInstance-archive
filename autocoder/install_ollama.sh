#!/bin/bash
# Ollama Installation Script for ProArt PX13
#
# Run this script with: bash install_ollama.sh

set -e  # Exit on error

echo "========================================="
echo "Installing Ollama for AutoCoder"
echo "========================================="
echo ""

# Check if running with sudo/root
if [ "$EUID" -eq 0 ]; then
    echo "✓ Running with sudo privileges"
else
    echo "⚠ This script needs sudo access"
    echo "Run with: sudo bash install_ollama.sh"
    exit 1
fi

# Install Ollama
echo "Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# Check installation
if command -v ollama &> /dev/null; then
    echo "✓ Ollama installed successfully"
    ollama --version
else
    echo "✗ Ollama installation failed"
    exit 1
fi

# Start Ollama service
echo ""
echo "Starting Ollama service..."
systemctl enable ollama
systemctl start ollama
sleep 2

# Check if service is running
if systemctl is-active --quiet ollama; then
    echo "✓ Ollama service is running"
else
    echo "⚠ Ollama service not running, trying to start..."
    systemctl restart ollama
    sleep 2
fi

echo ""
echo "========================================="
echo "Ollama Installation Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Exit sudo mode"
echo "2. Pull the model: ollama pull qwen2.5-coder:7b-instruct-q4_K_M"
echo "3. Test it: ollama run qwen2.5-coder:7b-instruct-q4_K_M 'Write hello world'"
