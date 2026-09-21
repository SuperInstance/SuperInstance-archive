#!/bin/bash
# Install Local LLM for DMLog Cost Optimization
# Sets up Phi-2 model for basic D&D interactions

echo "🤖 Installing DMLog Local LLM..."

# Install Ollama (lightweight LLM runtime)
if ! command -v ollama &> /dev/null; then
    echo "📦 Installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh
else
    echo "✅ Ollama already installed"
fi

# Pull Phi-2 model (efficient for basic interactions)
echo "⬇️ Downloading Phi-2 model (2.7B parameters)..."
ollama pull phi:2.7b

# Configure for DMLog optimization
mkdir -p ~/.ollama
cat > ~/.ollama/config.json << 'CONFIG'
{
  "models": {
    "phi:2.7b": {
      "context_length": 2048,
      "temperature": 0.7,
      "max_tokens": 200,
      "use_case": "dmlog_gaming"
    }
  },
  "server": {
    "port": 8765,
    "host": "127.0.0.1",
    "timeout": 30
  }
}
CONFIG

# Create DMLog-specific model configuration
ollama create dmlog-phi -f - << 'MODELFILE'
FROM phi:2.7b

PARAMETER temperature 0.7
PARAMETER num_ctx 2048
PARAMETER stop "\nPlayer:"
PARAMETER stop "\nDM:"
PARAMETER stop "\nNarrator:"

SYSTEM You are a helpful D&D assistant. Keep responses concise and engaging. Stay in character when roleplayng. For complex requests, you can acknowledge limitations and suggest asking for enhanced AI help.

TEMPLATE """{{ .System }}

{{ .Prompt }}"""
MODELFILE

echo ""
echo "✅ Local LLM Installation Complete!"
echo ""
echo "📊 Model Details:"
echo "   • Model: Phi-2 (2.7B parameters)"
echo "   • Memory: ~2GB RAM usage"
echo "   • Speed: ~50-100 tokens/second"
echo "   • Cost: $0 (local processing)"
echo ""
echo "🎮 Usage in DMLog:"
echo "   • Basic NPC interactions: Local LLM (free)"
echo "   • Complex storytelling: Cloud LLM ($2-4/hour)"
echo "   • Fallback: OpenAI API (pay-per-use)"
echo ""
echo "🚀 To test local LLM:"
echo "   ollama run dmlog-phi 'You enter a tavern. What do you see?'"
echo ""
echo "⚡ DMLog will automatically use the most cost-effective AI for each request!"