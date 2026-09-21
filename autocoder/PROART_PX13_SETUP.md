# AutoCoder Configuration for ASUS ProArt PX13 HN7306WU
## Tailored Setup for Your Specific Hardware

**Last Updated:** October 2025

---

## Your Hardware Profile

```
Laptop: ASUS ProArt PX13 HN7306WU
CPU: AMD Ryzen AI 9 HX 370 (12 cores, 24 threads, up to 5.1GHz)
GPU: NVIDIA RTX 4050 (6GB GDDR6 VRAM)
NPU: AMD XDNA NPU (50 TOPS AI)
RAM: 32GB LPDDR5X-7500
Storage: 1TB PCIe SSD
OS: Windows 11 + WSL2 (Ubuntu)
```

---

## Hardware Analysis & Constraints

### ✅ Strengths
- **Excellent CPU**: 12 cores perfect for CPU-based inference fallback
- **Generous RAM**: 32GB allows large models on CPU
- **Fast Storage**: 1TB SSD good for model storage
- **NPU**: Potential for AI acceleration (experimental)
- **Portability**: Lightweight for a creator laptop

### ⚠️ Limitations
- **6GB VRAM**: Restricts GPU inference to small models only
- **Laptop thermal limits**: Can't sustain max power indefinitely
- **Battery life**: Local inference drains battery quickly
- **Single GPU**: Can't run multiple models simultaneously on GPU

### 🎯 Optimal Strategy

**Hybrid Approach:**
1. **Small GPU models** (Qwen 7B Q4) for quick simple tasks
2. **CPU inference** (Qwen 14B-32B) for moderate tasks when plugged in
3. **Cloud models** (Claude, GPT-4) for complex tasks
4. **Smart caching** to minimize repeated API calls

---

## Model Configuration for 6GB VRAM

### GPU-Compatible Models (RTX 4050 6GB)

| Model | Quantization | VRAM Usage | Speed | Quality | Use Case |
|-------|-------------|------------|-------|---------|----------|
| **Qwen2.5-Coder 7B** | Q4_K_M | 4.5GB | Fast | Excellent | Primary GPU model |
| **Qwen2.5-Coder 7B** | Q6_K | 6.0GB | Medium | Best | High quality mode |
| **Qwen2.5-Coder 3B** | Q6_K | 2.5GB | Very Fast | Good | Ultra-fast tasks |
| **DeepSeek-Coder 6.7B** | Q4_K_M | 4.2GB | Fast | Good | Alternative |
| **Phi-3.5-mini 3.8B** | Q6_K | 3.0GB | Very Fast | Fair | Backup |

**Recommendation**: Use **Qwen2.5-Coder 7B Q4_K_M** as your primary GPU model (4.5GB VRAM, excellent performance)

### CPU-Compatible Models (32GB System RAM)

When GPU is busy or task needs more capability:

| Model | RAM Usage | Speed (CPU) | Quality | Use Case |
|-------|-----------|-------------|---------|----------|
| **Qwen2.5-Coder 14B** | 9GB | Moderate | Excellent | Moderate tasks |
| **Qwen2.5-Coder 32B** | 20GB | Slow | Outstanding | Complex tasks (offline) |
| **DeepSeek-Coder-V2 Lite 16B** | 10GB | Moderate | Very Good | Large context |

**Note**: CPU inference is 5-10x slower than GPU but doesn't drain battery as fast

### Cloud Models (API)

For tasks beyond local capabilities:

| Model | Best For | Cost | When to Use |
|-------|----------|------|-------------|
| **Claude 4 Sonnet** | Complex reasoning, refactoring | $3/$15 | Mission-critical code |
| **Claude 3.5 Haiku** | Fast simple tasks | $0.80/$4 | When local is slow/busy |
| **GPT-4o-mini** | Budget-friendly | $0.15/$0.60 | High volume simple tasks |
| **DeepSeek V3 API** | Cost-effective | $0.55/$2.20 | Budget mode |

---

## Routing Strategy for Your Laptop

### Decision Tree

```
User Request
    ↓
Is task trivial? (format, comment, simple function)
    YES → Qwen 7B GPU (Q4) — 2-3 seconds
    NO ↓

Is task simple? (basic function, small bug fix)
    YES → Is GPU available?
        YES → Qwen 7B GPU (Q4) — 3-5 seconds
        NO → Qwen 7B CPU — 10-20 seconds
    NO ↓

Is task moderate? (feature, tests, refactor single file)
    YES → Is plugged in + GPU free?
        YES → Qwen 7B GPU (Q6 for quality) — 5-10 seconds
        NO → Check budget
            Budget OK → Claude Haiku — 2-4 seconds
            Budget low → Qwen 14B CPU — 30-60 seconds
    NO ↓

Task is complex (multi-file, architecture, security)
    → Always use Claude 4 Sonnet — 5-15 seconds
```

### Power Mode Routing

**On Battery:**
- Avoid CPU inference (drains battery)
- Use GPU for quick tasks only
- Prefer cloud for moderate+ tasks
- Limit GPU power (reduce heat/battery drain)

**Plugged In:**
- Full GPU utilization
- CPU inference for parallel tasks
- Balanced approach

---

## Installation & Setup

### Step 1: Windows Setup (NVIDIA Drivers)

```powershell
# Open PowerShell as Administrator

# Check if NVIDIA drivers installed
nvidia-smi

# If not found, download from:
# https://www.nvidia.com/Download/index.aspx
# Select: RTX 4050 Laptop GPU → Windows 11 → Download

# Install NVIDIA CUDA Toolkit (required for GPU acceleration)
# https://developer.nvidia.com/cuda-downloads
# Choose Windows → x86_64 → 11 → exe (network)
```

### Step 2: WSL2 GPU Passthrough

```bash
# In WSL2 Ubuntu terminal

# Check if GPU accessible
nvidia-smi
# Should show RTX 4050 with 6GB memory

# If not working, install WSL NVIDIA drivers:
# https://developer.nvidia.com/cuda/wsl

# Install CUDA in WSL2
wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-keyring_1.0-1_all.deb
sudo dpkg -i cuda-keyring_1.0-1_all.deb
sudo apt-get update
sudo apt-get install cuda-toolkit-12-6
```

### Step 3: Install Ollama (Easiest for Laptops)

```bash
# Install Ollama in WSL2
curl -fsSL https://ollama.com/install.sh | sh

# Verify installation
ollama --version

# Pull optimized models for 6GB VRAM
ollama pull qwen2.5-coder:7b-instruct-q4_K_M    # 4.5GB - Primary
ollama pull qwen2.5-coder:3b                    # 2.5GB - Fast fallback

# Test GPU inference
ollama run qwen2.5-coder:7b-instruct-q4_K_M "Write a hello world function in Python"
```

### Step 4: Python Environment

```bash
# Create virtual environment
cd ~/autocoder
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install anthropic openai python-dotenv
pip install rich prompt_toolkit asyncio aiohttp aiofiles
pip install redis pyyaml psutil

# For CPU inference (optional, when GPU busy)
pip install llama-cpp-python
```

### Step 5: Monitor Setup

```bash
# Install monitoring tools
pip install py3nvml psutil

# Create monitoring script
cat > ~/autocoder/monitor.py << 'EOF'
import psutil
import py3nvml.py3nvml as nvml
from rich.console import Console
from rich.table import Table

nvml.nvmlInit()
handle = nvml.nvmlDeviceGetHandleByIndex(0)
console = Console()

def show_status():
    # GPU stats
    gpu_mem = nvml.nvmlDeviceGetMemoryInfo(handle)
    gpu_util = nvml.nvmlDeviceGetUtilizationRates(handle)
    power = nvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # Convert to watts
    temp = nvml.nvmlDeviceGetTemperature(handle, nvml.NVML_TEMPERATURE_GPU)

    # CPU/RAM stats
    cpu_percent = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()

    table = Table(title="ProArt PX13 System Status")
    table.add_column("Component", style="cyan")
    table.add_column("Usage", style="magenta")
    table.add_column("Details", style="green")

    table.add_row("GPU (RTX 4050)",
                  f"{gpu_mem.used/1e9:.1f}/{gpu_mem.total/1e9:.1f} GB",
                  f"{gpu_util.gpu}% util, {temp}°C, {power:.1f}W")
    table.add_row("CPU (Ryzen AI 9)",
                  f"{cpu_percent}%",
                  f"{psutil.cpu_count()} cores")
    table.add_row("RAM",
                  f"{ram.used/1e9:.1f}/{ram.total/1e9:.1f} GB",
                  f"{ram.percent}%")

    console.print(table)

if __name__ == "__main__":
    show_status()
EOF

# Run it
python monitor.py
```

---

## Optimized Configuration

### config/proart_px13.yaml

```yaml
# ProArt PX13 Optimized Configuration

hardware:
  name: ASUS ProArt PX13 HN7306WU
  gpu_vram_gb: 6
  system_ram_gb: 32
  cpu_cores: 12
  is_laptop: true

power_management:
  battery_mode:
    prefer_cloud: true           # Minimize local inference on battery
    max_gpu_inference_time: 10   # Max 10s per GPU task
    disable_cpu_inference: true  # Too power hungry

  plugged_mode:
    prefer_local: true
    allow_cpu_inference: true
    gpu_power_limit: 60          # Watts (lower for thermals)

providers:
  ollama:
    base_url: http://localhost:11434
    models:
      primary:
        name: qwen2.5-coder:7b-instruct-q4_K_M
        vram_required: 4.5
        context_window: 32768
        use_for:
          - trivial_tasks
          - simple_tasks
          - moderate_tasks_when_fast

      fast:
        name: qwen2.5-coder:3b
        vram_required: 2.5
        context_window: 32768
        use_for:
          - formatting
          - quick_questions

      cpu_fallback:
        name: qwen2.5-coder:14b-instruct-q4_K_M
        ram_required: 9
        backend: cpu
        threads: 8  # Half of 12 cores (leave headroom)
        use_for:
          - moderate_tasks_when_gpu_busy
          - parallel_execution

  claude:
    api_key_env: ANTHROPIC_API_KEY
    models:
      primary:
        name: claude-sonnet-4-5-20250929
        use_for:
          - complex_tasks
          - multi_file_refactoring
          - architecture_decisions

      fast:
        name: claude-3-5-haiku-20250219
        use_for:
          - moderate_tasks_on_battery
          - when_local_too_slow

routing:
  strategy: hybrid  # GPU + CPU + Cloud

  task_routing:
    trivial:
      primary: ollama.primary     # Qwen 7B GPU
      fallback: claude.fast       # If GPU busy

    simple:
      primary: ollama.primary     # Qwen 7B GPU
      fallback: claude.fast

    moderate:
      battery: claude.fast        # Cloud when on battery
      plugged: ollama.primary     # GPU when plugged in
      fallback: ollama.cpu_fallback  # CPU if GPU busy

    complex:
      always: claude.primary      # Always cloud for complex

  quality_mode:
    enabled: false  # Set true for better quality (slower, uses Q6)
    gpu_model: qwen2.5-coder:7b-instruct-q6_K  # 6GB VRAM (full capacity)

budget:
  daily_limit: 5.00  # Lower than desktop version (more local usage)
  warning_threshold: 0.8
  emergency_mode: use_cpu  # Fall back to CPU, not cloud

caching:
  enabled: true
  max_cache_size_gb: 10  # Don't fill up SSD
  semantic_cache: true
  redis_url: redis://localhost:6379

thermal_management:
  max_gpu_temp: 80      # Throttle if exceeds
  max_continuous_minutes: 30  # Max GPU inference time
  cooldown_seconds: 60        # Cool down after intensive work
```

---

## Laptop-Specific Optimizations

### 1. Thermal Management

```python
# src/hardware/thermal.py
import py3nvml.py3nvml as nvml
import time
from datetime import datetime, timedelta

class ThermalManager:
    def __init__(self, max_temp=80, max_continuous_minutes=30):
        nvml.nvmlInit()
        self.handle = nvml.nvmlDeviceGetHandleByIndex(0)
        self.max_temp = max_temp
        self.max_continuous = timedelta(minutes=max_continuous_minutes)
        self.inference_start = None

    def check_thermal_throttle(self) -> bool:
        """Return True if should throttle"""
        temp = nvml.nvmlDeviceGetTemperature(self.handle, nvml.NVML_TEMPERATURE_GPU)

        # Check temperature
        if temp > self.max_temp:
            return True

        # Check continuous usage time
        if self.inference_start:
            duration = datetime.now() - self.inference_start
            if duration > self.max_continuous:
                return True

        return False

    def start_inference(self):
        """Mark start of GPU inference"""
        if not self.inference_start:
            self.inference_start = datetime.now()

    def end_inference(self):
        """Mark end of GPU inference"""
        self.inference_start = None

    async def cooldown(self, seconds=60):
        """Pause for cooldown"""
        print(f"⏸️  GPU cooling down for {seconds}s (temp: {self.get_temp()}°C)")
        await asyncio.sleep(seconds)
        self.inference_start = None

    def get_temp(self) -> int:
        return nvml.nvmlDeviceGetTemperature(self.handle, nvml.NVML_TEMPERATURE_GPU)
```

### 2. Power-Aware Routing

```python
# src/orchestrator/power_aware_router.py
import psutil
from .router import Router

class PowerAwareRouter(Router):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.battery = psutil.sensors_battery()

    def is_on_battery(self) -> bool:
        battery = psutil.sensors_battery()
        return battery and not battery.power_plugged

    async def route(self, task: str, override: str = None):
        # Check power status
        on_battery = self.is_on_battery()

        if on_battery:
            # Battery mode: prefer cloud for moderate+ tasks
            analysis = self.analyzer.analyze(task)
            if analysis.complexity.value >= 3:  # Moderate or higher
                return self.providers["claude-fast"], analysis

        # Regular routing
        return await super().route(task, override)
```

### 3. Model Unloading (Free VRAM)

```python
# src/providers/ollama_optimized.py
import asyncio
import aiohttp

class OptimizedOllamaProvider:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
        self.loaded_model = None
        self.last_use = None
        self.auto_unload_minutes = 5

    async def chat(self, model, *args, **kwargs):
        # Load model if not loaded
        if self.loaded_model != model:
            await self.load_model(model)

        self.last_use = datetime.now()

        # Regular chat
        return await super().chat(model, *args, **kwargs)

    async def unload_model(self):
        """Free VRAM by unloading model"""
        if self.loaded_model:
            async with aiohttp.ClientSession() as session:
                await session.delete(f"{self.base_url}/api/delete/{self.loaded_model}")
            self.loaded_model = None
            print(f"♻️  Unloaded model to free VRAM")

    async def auto_unload_daemon(self):
        """Background task to auto-unload idle models"""
        while True:
            await asyncio.sleep(60)  # Check every minute

            if self.loaded_model and self.last_use:
                idle_time = datetime.now() - self.last_use
                if idle_time > timedelta(minutes=self.auto_unload_minutes):
                    await self.unload_model()
```

---

## Performance Expectations (Your Laptop)

### GPU Inference (Qwen 7B Q4 on RTX 4050)

| Task Type | Tokens | Time | Quality |
|-----------|--------|------|---------|
| Simple function | 200-500 | 5-10s | Excellent |
| Bug fix | 500-1000 | 10-20s | Excellent |
| Feature (single file) | 1000-2000 | 20-40s | Very Good |
| Code review | 500-1000 | 10-20s | Good |

**Speed**: ~15-25 tokens/second (RTX 4050 is slower than desktop RTX 4090)

### CPU Inference (Qwen 14B on Ryzen AI 9)

| Task Type | Tokens | Time | Quality |
|-----------|--------|------|---------|
| Feature implementation | 1000-2000 | 60-120s | Excellent |
| Refactoring | 1000-1500 | 60-90s | Excellent |

**Speed**: ~5-10 tokens/second (12 cores is decent)

### Cloud (Claude 4 Sonnet)

| Task Type | Tokens | Time | Cost |
|-----------|--------|------|------|
| Complex refactor | 2000-5000 | 10-20s | $0.20-0.50 |
| Architecture | 3000-8000 | 15-30s | $0.50-1.00 |

---

## Realistic Daily Usage Scenario

**Morning (Plugged In, 3 hours coding):**
- 20 simple tasks → Qwen 7B GPU → Free
- 5 moderate tasks → Qwen 7B GPU → Free
- 2 complex tasks → Claude 4 → $1.00
- **Cost**: $1.00

**Afternoon (On Battery, 2 hours):**
- 10 simple tasks → Claude Haiku → $0.40
- 2 moderate tasks → Claude Haiku → $0.20
- **Cost**: $0.60

**Evening (Plugged In, 2 hours):**
- 15 simple tasks → Qwen 7B GPU → Free
- 3 moderate tasks → Qwen 14B CPU (parallel) → Free
- 1 complex task → Claude 4 → $0.50
- **Cost**: $0.50

**Daily Total**: $2.10 (vs. $15-20 cloud-only)
**Monthly**: ~$60 (vs. $400+ cloud-only)
**Annual Savings**: ~$4,000

---

## Best Practices for Your Laptop

### ✅ DO:
- Keep laptop plugged in for intensive local inference
- Use GPU for quick tasks (<30s)
- Use cloud for complex tasks (cost-effective)
- Enable auto-sleep for models (free VRAM)
- Monitor temperatures (stay under 80°C)
- Use Q4 quantization (fast + fits in 6GB)

### ❌ DON'T:
- Don't run CPU inference on battery (drains fast)
- Don't run continuous GPU inference >30 minutes
- Don't use Q6/Q8 quantization unless necessary (slower, more VRAM)
- Don't try to load 14B+ models on GPU (won't fit)
- Don't run multiple models simultaneously on GPU

---

## NPU Usage (Experimental)

Your laptop has an **AMD XDNA NPU (50 TOPS)**. As of 2025, NPU support for LLMs is experimental:

### Current Status:
- **Windows Copilot+**: Uses NPU for Phi-3 mini (3.8B)
- **DirectML**: Enables NPU inference for some models
- **ONNX Runtime**: NPU support in preview

### Potential Future Use:
```python
# When ecosystem matures (2026+)
# Could offload small tasks to NPU while GPU handles main model

# Example (hypothetical):
npumodel = load_model_on_npu("phi-3-mini")  # Classifier, embeddings
gpu_model = load_model_on_gpu("qwen-7b")     # Main inference

# Route trivial tasks to NPU (free up GPU)
if task_complexity == TRIVIAL:
    return await npu_model.chat(task)
else:
    return await gpu_model.chat(task)
```

**Recommendation**: Ignore NPU for now, revisit in 6-12 months

---

## Next Steps

1. **Test GPU access in WSL2**:
   ```bash
   nvidia-smi  # Should show RTX 4050 6GB
   ```

2. **Install Ollama + pull model**:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull qwen2.5-coder:7b-instruct-q4_K_M
   ```

3. **Test inference speed**:
   ```bash
   time ollama run qwen2.5-coder:7b-instruct-q4_K_M "Write a Python function to calculate fibonacci numbers"
   # Should take 5-15 seconds for ~200 tokens
   ```

4. **Start building MVP** (follow QUICK_START.md with these config changes)

5. **Monitor performance**:
   ```bash
   watch -n 1 nvidia-smi  # Keep eye on VRAM/temp
   ```

---

## Troubleshooting

### GPU Not Detected in WSL2

```bash
# Update WSL
wsl --update

# Check WSL version (need 2)
wsl -l -v

# Install Windows NVIDIA driver (not WSL driver)
# Download from: https://www.nvidia.com/Download/index.aspx

# In WSL2, check again
nvidia-smi
```

### Ollama Using CPU Instead of GPU

```bash
# Check Ollama logs
journalctl -u ollama -f

# Ensure CUDA libraries present
ldconfig -p | grep cuda

# Force GPU usage
OLLAMA_GPU=1 ollama run qwen2.5-coder:7b-instruct-q4_K_M
```

### Out of VRAM Errors

```bash
# Use smaller quantization
ollama pull qwen2.5-coder:7b-instruct-q4_K_S  # Even smaller

# Or use 3B model
ollama pull qwen2.5-coder:3b

# Check what's using VRAM
nvidia-smi
```

### Laptop Overheating

```python
# Add thermal throttling to your config
thermal_management:
  enabled: true
  max_temp: 75  # Lower threshold
  auto_cooldown: true

# Use less aggressive settings
gpu_power_limit: 50  # Lower power = less heat
```

---

## Summary: Your Optimal Setup

**Hardware**: ProArt PX13 (6GB VRAM is limited but workable)

**Strategy**:
- GPU for simple/quick tasks (Qwen 7B Q4)
- Cloud for complex tasks (Claude)
- CPU fallback when GPU busy (Qwen 14B)

**Expected Performance**:
- 70% of tasks run locally (free)
- 30% use cloud ($2-3/day)
- 85% cost savings vs cloud-only

**Limitations**:
- Can't run large local models (32B won't fit)
- Thermals require careful management
- Battery life suffers during local inference

**Unique Advantages**:
- Portable (13.3" laptop)
- Strong CPU (12 cores)
- Ample RAM (32GB)
- NPU for future experimentation

---

**Ready to get started?** Run the test commands above to verify your GPU setup, then follow QUICK_START.md with this ProArt-specific config!
