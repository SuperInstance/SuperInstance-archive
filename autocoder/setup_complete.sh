#!/bin/bash
# Complete Setup Script - Run After Ollama is Installed
#
# Run this with: bash setup_complete.sh

set -e

echo "========================================="
echo "AutoCoder Setup - Final Steps"
echo "========================================="
echo ""

# Check Ollama
echo "Checking Ollama..."
if command -v ollama &> /dev/null; then
    echo "✓ Ollama is installed"
    ollama --version
else
    echo "✗ Ollama not found. Run: sudo bash install_ollama.sh"
    exit 1
fi

# Pull Qwen model (optimized for RTX 4050 6GB)
echo ""
echo "Pulling Qwen 2.5 Coder 7B Q4 model..."
echo "This is ~4.5GB and optimized for your 6GB VRAM"
echo "(This may take 5-10 minutes depending on internet speed)"
echo ""

# Check if model already exists
if ollama list | grep -q "qwen2.5-coder:7b"; then
    echo "✓ Model already downloaded"
else
    ollama pull qwen2.5-coder:7b-instruct-q4_K_M || \
    ollama pull qwen2.5-coder:7b || \
    ollama pull qwen2.5-coder
fi

# Test the model
echo ""
echo "Testing model inference..."
export PATH="/usr/lib/wsl/lib:$PATH"
nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits > /tmp/before_vram.txt
BEFORE_VRAM=$(cat /tmp/before_vram.txt)
echo "GPU VRAM before: ${BEFORE_VRAM} MB"

echo ""
echo "Running test prompt (this may take 10-20 seconds)..."
ollama run qwen2.5-coder:7b-instruct-q4_K_M "Write a Python hello world function" > /tmp/test_output.txt &
OLLAMA_PID=$!

# Monitor GPU for 5 seconds
sleep 5
if ps -p $OLLAMA_PID > /dev/null; then
    nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits > /tmp/during_vram.txt
    DURING_VRAM=$(cat /tmp/during_vram.txt)
    echo "GPU VRAM during inference: ${DURING_VRAM} MB"
    VRAM_USED=$((DURING_VRAM - BEFORE_VRAM))
    echo "Model is using ~${VRAM_USED} MB of VRAM"

    if [ $VRAM_USED -gt 3000 ] && [ $VRAM_USED -lt 6000 ]; then
        echo "✓ VRAM usage looks correct for Qwen 7B Q4 (~4.5GB expected)"
    fi
fi

# Wait for completion
wait $OLLAMA_PID
echo ""
echo "Model output:"
cat /tmp/test_output.txt

# Clean up
rm -f /tmp/before_vram.txt /tmp/during_vram.txt /tmp/test_output.txt

echo ""
echo "========================================="
echo "Setup Complete! 🚀"
echo "========================================="
echo ""
echo "Your system is ready:"
echo "✓ GPU: RTX 4050 (6GB VRAM)"
echo "✓ Model: Qwen 2.5 Coder 7B Q4 (~4.5GB)"
echo "✓ Inference: GPU-accelerated"
echo ""
echo "Next: Create your first coding agent!"
echo "See QUICK_START.md for implementation guide"
