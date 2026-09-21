# Running AutoCoder

## Prerequisites Complete

Before running, make sure you've completed setup:

```bash
# 1. Install Ollama (if not done)
sudo bash install_ollama.sh

# 2. Download model (if not done)
bash setup_complete.sh

# 3. Set API key (if not done)
export ANTHROPIC_API_KEY='sk-ant-your-key-here'
```

---

## Running AutoCoder

### Quick Start

```bash
cd ~/autocoder
python3 main.py
```

Or with API key inline:
```bash
ANTHROPIC_API_KEY='your-key' python3 main.py
```

### First Run

When you first run AutoCoder, you'll see:

```
🚀 Starting AutoCoder...
✓ Configuration loaded
✓ Cost tracker initialized
✓ State manager initialized
✓ Thermal/power management enabled
✓ Local model configured: qwen2.5-coder:7b-instruct-q4_K_M
✓ Claude Sonnet configured: claude-sonnet-4-5-20250929
✓ Claude Haiku configured: claude-3-5-haiku-20250219

✓ 3 model(s) ready
✓ Router initialized
✓ CLI initialized

╔══════════════════════════════════════════════════════════╗
║                                                          ║
║                  AutoCoder v0.1.0                        ║
║         Multi-Model Coding Assistant                     ║
║         Optimized for ProArt PX13                        ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
Type ':help' for commands, ':quit' to exit

You:
```

---

## Usage Examples

### Auto-Routing (Recommended)
Just type your request - the system will choose the best model:

```
You: Write a Python function to calculate fibonacci numbers
→ Routing to qwen2.5-coder:7b-instruct-q4_K_M (complexity: SIMPLE)
[Response from local model, FREE]

You: Design a microservices architecture for an e-commerce platform
→ Routing to claude-sonnet-4-5-20250929 (complexity: VERY_COMPLEX)
[Response from Claude 4, ~$0.50]
```

### Manual Model Selection

Force specific models with `@model` syntax:

```
You: @local Write a hello world function
[Uses local Qwen model]

You: @claude Explain this architecture
[Uses Claude 4 Sonnet]

You: @haiku Write unit tests
[Uses Claude 3.5 Haiku - faster, cheaper]
```

### Commands

```
You: :help         # Show all commands
You: :models       # List available models
You: :cost         # Show cost breakdown
You: :status       # Show system status
You: :quit         # Exit
```

---

## What Happens During a Request

1. **Task Analysis** - Analyzes your request to determine complexity
2. **Routing Decision** - Chooses optimal model based on:
   - Task complexity
   - Budget remaining
   - GPU temperature (if using local)
   - Power status (battery vs plugged)
3. **Inference** - Streams response in real-time
4. **Cost Tracking** - Records cost (if using paid model)
5. **State Saving** - Saves interaction to logs

---

## Monitoring

### Watch GPU (in another terminal)

```bash
export PATH="/usr/lib/wsl/lib:$PATH"
watch -n 1 nvidia-smi
```

You'll see:
- VRAM usage spike to ~4.5GB when using local model
- GPU utilization at 80-100%
- Temperature rise to 60-75°C
- Power draw increase to 40-60W

### Check Costs

```
You: :cost

Cost Summary:
  Session Total: $0.5234
  Today's Total: $2.15 / $5.00
  Remaining: $2.85

  Tokens Used: 12,345 in / 5,678 out
  Tasks Completed: 15
  Local Tasks (FREE): 12

  Savings from Local: $1.80
  Savings from Cache: $0.00
```

---

## Understanding Routing

### Complexity Levels

**TRIVIAL** (→ Local) - <500 tokens
- Format code
- Add comments
- Docstrings

**SIMPLE** (→ Local) - <2K tokens
- Simple functions
- Basic bug fixes
- Helper utilities

**MODERATE** (→ Local or Haiku) - <10K tokens
- Feature implementation
- Unit tests
- Single-file refactoring

**COMPLEX** (→ Claude Sonnet) - 10K+ tokens
- Multi-file refactoring
- Security implementations
- Performance optimization

**VERY_COMPLEX** (→ Claude Sonnet) - Always
- Architecture design
- System migration
- Distributed systems

### Routing Factors

The router considers:
1. **Task complexity** (from keywords and length)
2. **Budget remaining** (switches to local if low)
3. **GPU temperature** (uses cloud if overheating)
4. **Power status** (uses cloud on battery for moderate+)
5. **Manual override** (`@model` syntax)

---

## Performance Expectations

### Local Model (Qwen 7B on RTX 4050)
- **Latency**: 50-200ms to first token
- **Speed**: 15-25 tokens/second
- **VRAM**: ~4.5GB
- **Power**: 40-60W
- **Temperature**: 60-75°C
- **Cost**: $0 (FREE)

### Cloud Models (Claude via API)
- **Latency**: 200-500ms to first token
- **Speed**: 50-100 tokens/second
- **Cost**: $3-15 per 1M output tokens

### Typical Session (8 hours coding)
- 30 simple tasks → Local → FREE
- 8 moderate tasks → Local → FREE
- 3 complex tasks → Claude → $2.00
- **Total**: ~$2/day vs $20/day cloud-only

---

## Troubleshooting

### "No model providers available!"

**Problem**: Neither Ollama nor API key configured

**Fix**:
```bash
# Install Ollama
sudo bash install_ollama.sh

# OR set API key
export ANTHROPIC_API_KEY='your-key'
```

### "Local model not available"

**Problem**: Ollama not installed or not running

**Fix**:
```bash
# Install
sudo bash install_ollama.sh

# Check if running
systemctl status ollama

# Start if needed
sudo systemctl start ollama

# Pull model
ollama pull qwen2.5-coder:7b-instruct-q4_K_M
```

### "GPU CRITICAL" warning

**Problem**: GPU overheating

**Action**: System automatically:
1. Stops local inference
2. Initiates cooldown (60s)
3. Routes to cloud temporarily

**Prevention**:
- Ensure laptop has good ventilation
- Clean dust from vents
- Use cooling pad
- Lower max temperature in config

### Slow responses on local model

**Possible causes**:
1. Model not using GPU
2. GPU busy with other tasks
3. Thermal throttling

**Check**:
```bash
nvidia-smi  # Should show ~4.5GB usage during inference
```

---

## Configuration

Edit `config/proart_px13.yaml` to customize:

```yaml
# Budget limits
budget:
  daily_limit: 5.00      # Change daily budget
  monthly_limit: 150.00

# Thermal limits
thermal:
  max_temp: 80          # Lower if overheating
  max_continuous_minutes: 30

# Routing
routing:
  strategy: hybrid      # or 'local_first', 'cloud_first'
```

---

## Logs & History

### Conversation Logs
Saved to: `logs/autocoder_YYYY-MM-DD.jsonl`

Each line is a JSON interaction:
```json
{"id": "...", "timestamp": "...", "user_input": "...", "response": "...", "model": "...", "cost": 0.0}
```

### Export Session
On exit, you can export the entire session:
```
Export session? (y/n): y
✓ Session exported to: session_20251012_143022.json
```

---

## Tips for Best Results

### 1. Let Auto-Routing Work
- Don't always force `@local` or `@claude`
- The router learns what works best
- Trust the complexity analysis

### 2. Use Local for Simple Tasks
```
✓ "format this code"
✓ "add docstrings"
✓ "write a simple function"
✓ "fix this typo"
```

### 3. Use Cloud for Complex Tasks
```
✓ "design this system"
✓ "refactor across multiple files"
✓ "implement authentication"
✓ "optimize this algorithm"
```

### 4. Monitor Costs
Check `:cost` regularly to stay within budget

### 5. Keep Laptop Cool
- Use on flat surface
- Good ventilation
- Monitor temperature with `:status`

---

## Performance Tuning

### Faster Local Inference
```bash
# Use smaller model for speed
ollama pull qwen2.5-coder:3b  # Only 2.5GB, very fast

# Edit config to use it
nano config/proart_px13.yaml
```

### Reduce Costs
```bash
# Lower daily budget to force more local usage
You: :cost limit 2.00

# Use @local override for moderate tasks
You: @local implement this feature
```

### Better Thermal Management
```yaml
# In config/proart_px13.yaml
thermal:
  max_temp: 75              # Lower limit
  max_continuous_minutes: 20 # Shorter sessions
  cooldown_seconds: 90      # Longer cooldown
```

---

## Exit & Summary

When you quit (`:quit` or Ctrl+D), you'll see:

```
============================================================
Session Summary
============================================================
Cost Summary:
  Session Total: $1.2340
  Today's Total: $3.15
  Remaining: $1.85

  Tokens Used: 45,678 in / 23,456 out
  Tasks Completed: 38
  Local Tasks (FREE): 32

  Savings from Local: $4.80
  Savings from Cache: $0.50

Statistics:
  Total interactions: 38
  Models used: qwen2.5-coder:7b-instruct-q4_K_M, claude-sonnet-4-5-20250929

Export session? (y/n):
```

---

## Next Steps

Once comfortable with basics:
1. Read **QUICK_START.md** for advanced features
2. Implement tool calling (file operations, git, bash)
3. Add more model providers (OpenAI, Gemini)
4. Customize routing rules
5. Build task decomposition (multi-agent)

---

**Happy Coding! 🚀**

For issues, check:
- `STATUS.md` - Current setup status
- `PROART_PX13_SETUP.md` - Hardware troubleshooting
- `INSTALLATION_LOG.md` - Setup details
