# Geekbench 6 Integration Guide

## Table of Contents
1. [Overview](#overview)
2. [Licensing and Access](#licensing-and-access)
3. [Installation](#installation)
4. [Automated Execution](#automated-execution)
5. [Result Parsing](#result-parsing)
6. [Score Interpretation](#score-interpretation)
7. [Integration Examples](#integration-examples)
8. [Advanced Configuration](#advanced-configuration)
9. [Troubleshooting](#troubleshooting)

---

## Overview

Geekbench 6 is a cross-platform benchmark tool that measures CPU and GPU performance using real-world workloads. It provides standardized scores that enable objective hardware comparison across different architectures and platforms.

### Why Geekbench 6?

- **Industry Standard**: Widely recognized benchmark used by hardware reviewers and manufacturers
- **Cross-Platform**: Consistent scoring across Windows, Linux, macOS, Android, and iOS
- **Real-World Workloads**: Tests include image processing, machine learning, cryptography, and more
- **Command-Line Interface**: Enables full automation for marketplace verification
- **GPU Support**: Separate GPU benchmarks for OpenCL, Vulkan, Metal, and CUDA
- **Quick Execution**: CPU tests complete in 5-15 minutes, GPU tests in 2-5 minutes

### Benchmark Internals

Geekbench 6 includes the following workloads:

**CPU Workloads**:
- File Compression (Zlib)
- Navigation (Dijkstra algorithm)
- HTML5 Browser (headless browser rendering)
- PDF Renderer (PDF parsing and rendering)
- Photo Library (face detection, horizon detection)
- Clang (code compilation)
- Text Processing (XML parsing, regular expressions)
- Asset Compression (texture compression)
- Object Detection (deep learning inference)
- Background Blur (computational photography)
- Horizon Detection (computer vision)
- Object Remover (image inpainting)
- HDR (high dynamic range imaging)
- Photo Filter (image filters and effects)
- Ray Tracer (3D ray tracing)
- Structure from Motion (3D reconstruction)

**GPU Workloads**:
- HDR
- Image Inpainting
- Depth of Field
- Face Detection
- Horizon Detection
- Background Blur
- Particle Physics

### Score Calculation

- **Single-Core Score**: Average performance of one CPU core across all workloads
- **Multi-Core Score**: Performance of all CPU cores working together
- **GPU Compute Score**: GPU performance across compute workloads
- Scores are normalized against a baseline system (Intel Core i7-12700)
- Higher scores indicate better performance
- Scores are directly comparable across different hardware

---

## Licensing and Access

### License Types

Geekbench 6 offers several licensing options:

#### 1. Free Version (Linux)
- **Cost**: Free
- **Platform**: Linux only
- **Features**: Full benchmark suite, manual execution
- **Limitations**: No command-line automation, no batch processing
- **Use Case**: Testing and evaluation

#### 2. Geekbench Pro
- **Cost**: $99.99 (perpetual license)
- **Platforms**: Windows, macOS
- **Features**:
  - Command-line automation
  - Offline results
  - Batch processing
  - No watermarks
  - Priority support
- **Use Case**: Production deployment for marketplace

#### 3. Enterprise License
- **Cost**: Custom pricing
- **Features**:
  - Volume licensing
  - Custom deployment
  - Extended support
  - White-label options
- **Use Case**: Large-scale marketplace deployment

#### 4. Geekbench ML (Separate Product)
- **Cost**: $129.99
- **Features**: Specialized ML inference benchmarks
- **Models**: TensorFlow Lite, CoreML
- **Use Case**: ML-specific performance validation

### Obtaining Licenses

1. **Purchase**: https://www.geekbench.com/editions/
2. **Download**: https://www.geekbench.com/download/
3. **Email License Key**: Sent to registered email after purchase
4. **Activation**: Use email and license key for activation

### Licensing for Marketplace

For a compute marketplace, recommended approach:

```
Option 1: Per-Provider Licensing
- Each provider obtains their own Geekbench Pro license
- Marketplace validates license presence before onboarding
- Provider responsible for compliance

Option 2: Marketplace-Wide Enterprise License
- Marketplace negotiates bulk licensing with Primate Labs
- Single license covers all provider benchmarks
- Marketplace maintains compliance
- Requires custom agreement for commercial redistribution

Option 3: Hybrid Approach
- Use free Linux version for initial screening
- Require Pro license for full provider onboarding
- Enterprise license for marketplace-initiated verification
```

### Legal Considerations

**Important**: Geekbench terms prohibit:
- Redistribution of benchmark binaries without permission
- Automated result submission without Pro license
- Commercial use of benchmark results without proper licensing

**Recommendation**: Contact Primate Labs (sales@primatelabs.com) to negotiate marketplace-specific licensing terms.

---

## Installation

### Linux Installation

#### Manual Installation

```bash
# Download Geekbench 6 for Linux
cd /opt
wget https://cdn.geekbench.com/Geekbench-6.3.0-Linux.tar.gz

# Extract
tar xzf Geekbench-6.3.0-Linux.tar.gz
cd Geekbench-6.3.0-Linux

# Verify executable
./geekbench6 --version
# Output: Geekbench 6.3.0

# Add to PATH
echo 'export PATH=$PATH:/opt/Geekbench-6.3.0-Linux' >> ~/.bashrc
source ~/.bashrc
```

#### Automated Installation Script

```bash
#!/bin/bash
# install_geekbench.sh

set -e

GEEKBENCH_VERSION="6.3.0"
INSTALL_DIR="/opt/geekbench"
DOWNLOAD_URL="https://cdn.geekbench.com/Geekbench-${GEEKBENCH_VERSION}-Linux.tar.gz"

echo "Installing Geekbench ${GEEKBENCH_VERSION}..."

# Create installation directory
sudo mkdir -p ${INSTALL_DIR}

# Download
echo "Downloading from ${DOWNLOAD_URL}..."
wget -O /tmp/geekbench.tar.gz ${DOWNLOAD_URL}

# Extract
echo "Extracting..."
sudo tar xzf /tmp/geekbench.tar.gz -C ${INSTALL_DIR} --strip-components=1

# Clean up
rm /tmp/geekbench.tar.gz

# Create symlinks
sudo ln -sf ${INSTALL_DIR}/geekbench6 /usr/local/bin/geekbench6
sudo ln -sf ${INSTALL_DIR}/geekbench_x86_64 /usr/local/bin/geekbench_x86_64

# Verify installation
echo "Verifying installation..."
geekbench6 --version

echo "Geekbench installed successfully!"
```

#### Docker Installation

```dockerfile
# Dockerfile
FROM ubuntu:22.04

ENV GEEKBENCH_VERSION=6.3.0
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Download and install Geekbench
WORKDIR /opt
RUN wget https://cdn.geekbench.com/Geekbench-${GEEKBENCH_VERSION}-Linux.tar.gz && \
    tar xzf Geekbench-${GEEKBENCH_VERSION}-Linux.tar.gz && \
    rm Geekbench-${GEEKBENCH_VERSION}-Linux.tar.gz && \
    mv Geekbench-${GEEKBENCH_VERSION}-Linux geekbench

ENV PATH="/opt/geekbench:${PATH}"

WORKDIR /benchmarks
CMD ["geekbench6", "--help"]
```

Build and run:

```bash
docker build -t geekbench:6.3.0 .
docker run --rm geekbench:6.3.0 geekbench6 --help
```

### GPU Support Setup

For GPU benchmarking, additional drivers are required:

#### NVIDIA GPU

```bash
# Install NVIDIA drivers
sudo apt-get install -y nvidia-driver-535

# Install CUDA toolkit
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.0-1_all.deb
sudo dpkg -i cuda-keyring_1.0-1_all.deb
sudo apt-get update
sudo apt-get install -y cuda

# Install OpenCL
sudo apt-get install -y nvidia-opencl-dev

# Verify GPU detection
nvidia-smi
```

#### AMD GPU

```bash
# Install AMD GPU drivers
wget https://repo.radeon.com/amdgpu-install/latest/ubuntu/jammy/amdgpu-install_*.deb
sudo apt-get install -y ./amdgpu-install_*.deb
sudo amdgpu-install -y --usecase=graphics,opencl

# Verify
clinfo
```

### License Activation

```bash
# Register with email and license key
geekbench6 --register email@example.com LICENSE-KEY-HERE

# Verify registration
geekbench6 --check-registration
```

---

## Automated Execution

### Command-Line Interface

#### Basic CPU Benchmark

```bash
# Run CPU benchmark with default settings
geekbench6 --output-format json --output-file /tmp/cpu_results.json

# Quick mode (faster, slightly less accurate)
geekbench6 --quick --output-format json --output-file /tmp/cpu_quick.json

# Specific workloads only
geekbench6 --workload crypto --output-format json --output-file /tmp/crypto.json
```

#### GPU Benchmark

```bash
# List available GPU APIs
geekbench6 --list-gpu-apis

# OpenCL GPU benchmark
geekbench6 --compute OpenCL --output-format json --output-file /tmp/gpu_opencl.json

# CUDA GPU benchmark (NVIDIA only)
geekbench6 --compute CUDA --output-format json --output-file /tmp/gpu_cuda.json

# Vulkan GPU benchmark
geekbench6 --compute Vulkan --output-format json --output-file /tmp/gpu_vulkan.json
```

#### Advanced Options

```bash
# No result upload (offline mode)
geekbench6 --no-upload --output-format json --output-file /tmp/results.json

# Specify number of threads
geekbench6 --threads 32 --output-format json --output-file /tmp/results.json

# Save intermediate results
geekbench6 --save-intermediate --output-format json --output-file /tmp/results.json

# Verbose output for debugging
geekbench6 --verbose --output-format json --output-file /tmp/results.json
```

### Python Wrapper

```python
# geekbench_runner.py
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, Optional

class GeekbenchRunner:
    def __init__(self, binary_path: str = "geekbench6"):
        self.binary_path = binary_path
        self.results_dir = Path("/var/benchmark/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def run_cpu_benchmark(
        self,
        quick_mode: bool = False,
        iterations: int = 1,
        no_upload: bool = True
    ) -> Dict:
        """Run CPU benchmark and return parsed results."""
        results = []

        for i in range(iterations):
            result_file = self.results_dir / f"cpu_run_{i}_{int(time.time())}.json"

            cmd = [
                self.binary_path,
                "--output-format", "json",
                "--output-file", str(result_file)
            ]

            if quick_mode:
                cmd.append("--quick")

            if no_upload:
                cmd.append("--no-upload")

            print(f"Running CPU benchmark (iteration {i+1}/{iterations})...")

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=900  # 15 minutes
                )

                if result.returncode != 0:
                    raise RuntimeError(f"Benchmark failed: {result.stderr}")

                # Parse results
                with open(result_file, 'r') as f:
                    benchmark_result = json.load(f)

                results.append(benchmark_result)

                print(f"Iteration {i+1} completed")
                print(f"Single-Core Score: {benchmark_result['score']}")
                print(f"Multi-Core Score: {benchmark_result['multicore_score']}")

            except subprocess.TimeoutExpired:
                print(f"Benchmark timed out on iteration {i+1}")
                raise

            except Exception as e:
                print(f"Error on iteration {i+1}: {e}")
                raise

        # Aggregate results if multiple iterations
        if len(results) > 1:
            aggregated = self._aggregate_results(results)
            return aggregated
        else:
            return results[0]

    def run_gpu_benchmark(
        self,
        api: str = "OpenCL",
        no_upload: bool = True
    ) -> Dict:
        """Run GPU benchmark and return parsed results."""
        result_file = self.results_dir / f"gpu_{api.lower()}_{int(time.time())}.json"

        cmd = [
            self.binary_path,
            "--compute", api,
            "--output-format", "json",
            "--output-file", str(result_file)
        ]

        if no_upload:
            cmd.append("--no-upload")

        print(f"Running GPU benchmark with {api}...")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes
            )

            if result.returncode != 0:
                raise RuntimeError(f"GPU benchmark failed: {result.stderr}")

            # Parse results
            with open(result_file, 'r') as f:
                benchmark_result = json.load(f)

            print(f"GPU Compute Score: {benchmark_result.get('score', 'N/A')}")

            return benchmark_result

        except subprocess.TimeoutExpired:
            print("GPU benchmark timed out")
            raise

        except Exception as e:
            print(f"Error running GPU benchmark: {e}")
            raise

    def get_system_info(self) -> Dict:
        """Get system information from Geekbench."""
        cmd = [self.binary_path, "--sysinfo", "--output-format", "json"]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to get system info: {result.stderr}")

        return json.loads(result.stdout)

    def _aggregate_results(self, results: list) -> Dict:
        """Aggregate multiple benchmark runs."""
        scores = [r['score'] for r in results]
        multicore_scores = [r['multicore_score'] for r in results]

        return {
            "runs": len(results),
            "single_core": {
                "scores": scores,
                "average": sum(scores) / len(scores),
                "min": min(scores),
                "max": max(scores),
                "std_dev": self._std_dev(scores)
            },
            "multi_core": {
                "scores": multicore_scores,
                "average": sum(multicore_scores) / len(multicore_scores),
                "min": min(multicore_scores),
                "max": max(multicore_scores),
                "std_dev": self._std_dev(multicore_scores)
            },
            "raw_results": results
        }

    @staticmethod
    def _std_dev(values: list) -> float:
        """Calculate standard deviation."""
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5


# Example usage
if __name__ == "__main__":
    runner = GeekbenchRunner()

    # Get system info
    sysinfo = runner.get_system_info()
    print(f"CPU: {sysinfo['cpu']['model']}")
    print(f"Cores: {sysinfo['cpu']['cores']}")
    print(f"Memory: {sysinfo['memory']['size_gb']} GB")

    # Run CPU benchmark (3 iterations)
    cpu_results = runner.run_cpu_benchmark(iterations=3)
    print(f"\nAverage Single-Core Score: {cpu_results['single_core']['average']:.0f}")
    print(f"Average Multi-Core Score: {cpu_results['multi_core']['average']:.0f}")

    # Run GPU benchmark
    try:
        gpu_results = runner.run_gpu_benchmark(api="OpenCL")
        print(f"\nGPU Score: {gpu_results['score']}")
    except Exception as e:
        print(f"GPU benchmark not available: {e}")
```

### Bash Automation Script

```bash
#!/bin/bash
# benchmark_automation.sh

set -e

RESULTS_DIR="/var/benchmark/results"
GEEKBENCH_BIN="/usr/local/bin/geekbench6"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p ${RESULTS_DIR}

echo "=== Geekbench 6 Automated Benchmark ==="
echo "Timestamp: ${TIMESTAMP}"
echo ""

# Function to run benchmark with retries
run_with_retry() {
    local cmd=$1
    local max_attempts=3
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        echo "Attempt $attempt of $max_attempts..."
        if eval "$cmd"; then
            echo "Success!"
            return 0
        else
            echo "Failed, retrying..."
            attempt=$((attempt + 1))
            sleep 10
        fi
    done

    echo "All attempts failed!"
    return 1
}

# CPU Benchmark
echo "Running CPU benchmark..."
CPU_RESULT="${RESULTS_DIR}/cpu_${TIMESTAMP}.json"
run_with_retry "${GEEKBENCH_BIN} --no-upload --output-format json --output-file ${CPU_RESULT}"

# Extract scores
SINGLE_CORE=$(jq -r '.score' ${CPU_RESULT})
MULTI_CORE=$(jq -r '.multicore_score' ${CPU_RESULT})
echo "Single-Core Score: ${SINGLE_CORE}"
echo "Multi-Core Score: ${MULTI_CORE}"
echo ""

# GPU Benchmark (if available)
echo "Checking for GPU..."
if ${GEEKBENCH_BIN} --list-gpu-apis 2>/dev/null | grep -q "OpenCL"; then
    echo "Running GPU benchmark..."
    GPU_RESULT="${RESULTS_DIR}/gpu_${TIMESTAMP}.json"
    run_with_retry "${GEEKBENCH_BIN} --compute OpenCL --no-upload --output-format json --output-file ${GPU_RESULT}"

    GPU_SCORE=$(jq -r '.score' ${GPU_RESULT})
    echo "GPU Score: ${GPU_SCORE}"
else
    echo "No GPU detected, skipping GPU benchmark"
fi

echo ""
echo "=== Benchmark Complete ==="
echo "Results saved to: ${RESULTS_DIR}"
```

---

## Result Parsing

### JSON Output Format

Geekbench 6 produces detailed JSON output:

```json
{
  "version": "6.3.0",
  "timestamp": "2025-10-14T10:30:00Z",
  "runtime": {
    "elapsed": 847.3
  },
  "system": {
    "os": "Ubuntu 22.04.3 LTS",
    "kernel": "5.15.0-91-generic",
    "model": "AMD EPYC 7763 64-Core Processor",
    "processor": {
      "frequency": 2450000000,
      "processors": 64,
      "cores": 64,
      "threads": 128
    },
    "memory": {
      "size": 274877906944
    }
  },
  "sections": [
    {
      "name": "Single-Core Performance",
      "id": "single-core",
      "score": 1523,
      "workloads": [
        {
          "name": "File Compression",
          "id": "file-compression",
          "score": 1678,
          "runtime": 45.3,
          "rate": 23451234
        },
        {
          "name": "Navigation",
          "id": "navigation",
          "score": 1542,
          "runtime": 32.1,
          "rate": 1234567
        }
      ]
    },
    {
      "name": "Multi-Core Performance",
      "id": "multi-core",
      "score": 18945,
      "workloads": [
        {
          "name": "File Compression",
          "id": "file-compression",
          "score": 21034,
          "runtime": 47.2,
          "rate": 456789012
        }
      ]
    }
  ],
  "score": 1523,
  "multicore_score": 18945
}
```

### Python Parser

```python
# geekbench_parser.py
import json
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class WorkloadResult:
    name: str
    id: str
    score: int
    runtime: float
    rate: Optional[int] = None

@dataclass
class SectionResult:
    name: str
    id: str
    score: int
    workloads: List[WorkloadResult]

@dataclass
class GeekbenchResult:
    version: str
    timestamp: str
    runtime_seconds: float
    system_info: Dict
    single_core_score: int
    multi_core_score: int
    sections: List[SectionResult]

class GeekbenchParser:
    @staticmethod
    def parse_result_file(file_path: str) -> GeekbenchResult:
        """Parse Geekbench JSON result file."""
        with open(file_path, 'r') as f:
            data = json.load(f)

        return GeekbenchParser.parse_result(data)

    @staticmethod
    def parse_result(data: Dict) -> GeekbenchResult:
        """Parse Geekbench result dictionary."""
        sections = []

        for section_data in data.get('sections', []):
            workloads = [
                WorkloadResult(
                    name=w['name'],
                    id=w['id'],
                    score=w['score'],
                    runtime=w['runtime'],
                    rate=w.get('rate')
                )
                for w in section_data.get('workloads', [])
            ]

            sections.append(SectionResult(
                name=section_data['name'],
                id=section_data['id'],
                score=section_data['score'],
                workloads=workloads
            ))

        return GeekbenchResult(
            version=data['version'],
            timestamp=data['timestamp'],
            runtime_seconds=data['runtime']['elapsed'],
            system_info=data['system'],
            single_core_score=data['score'],
            multi_core_score=data['multicore_score'],
            sections=sections
        )

    @staticmethod
    def extract_key_metrics(result: GeekbenchResult) -> Dict:
        """Extract key performance metrics."""
        return {
            "scores": {
                "single_core": result.single_core_score,
                "multi_core": result.multi_core_score,
                "scaling_efficiency": result.multi_core_score / (result.single_core_score * result.system_info['processor']['cores'])
            },
            "system": {
                "cpu_model": result.system_info['model'],
                "cores": result.system_info['processor']['cores'],
                "threads": result.system_info['processor']['threads'],
                "memory_gb": result.system_info['memory']['size'] / (1024**3)
            },
            "runtime": {
                "total_seconds": result.runtime_seconds,
                "minutes": result.runtime_seconds / 60
            },
            "timestamp": result.timestamp
        }

    @staticmethod
    def workload_breakdown(result: GeekbenchResult) -> Dict:
        """Get detailed breakdown by workload."""
        breakdown = {}

        for section in result.sections:
            for workload in section.workloads:
                key = f"{section.id}_{workload.id}"
                breakdown[key] = {
                    "name": workload.name,
                    "section": section.name,
                    "score": workload.score,
                    "runtime": workload.runtime
                }

        return breakdown


# Example usage
if __name__ == "__main__":
    parser = GeekbenchParser()

    # Parse result file
    result = parser.parse_result_file("/var/benchmark/results/cpu_result.json")

    # Extract key metrics
    metrics = parser.extract_key_metrics(result)
    print(f"Single-Core: {metrics['scores']['single_core']}")
    print(f"Multi-Core: {metrics['scores']['multi_core']}")
    print(f"Scaling Efficiency: {metrics['scores']['scaling_efficiency']:.2%}")

    # Get workload breakdown
    breakdown = parser.workload_breakdown(result)
    for workload_id, data in breakdown.items():
        print(f"{data['name']}: {data['score']} (runtime: {data['runtime']:.1f}s)")
```

---

## Score Interpretation

### Understanding Scores

Geekbench scores are calibrated against a baseline system:
- **Baseline**: Intel Core i7-12700 (score = 2,500)
- **Score of 5,000**: 2x faster than baseline
- **Score of 1,250**: 2x slower than baseline

### Score Ranges by Hardware Class

#### Consumer CPUs

| CPU Model | Single-Core | Multi-Core |
|-----------|-------------|------------|
| AMD Ryzen 9 7950X | 2,900-3,100 | 19,000-21,000 |
| Intel Core i9-13900K | 3,000-3,200 | 20,000-22,000 |
| AMD Ryzen 7 7700X | 2,700-2,900 | 14,000-16,000 |
| Intel Core i7-13700K | 2,800-3,000 | 17,000-19,000 |
| Apple M2 Max | 2,600-2,800 | 14,000-15,000 |

#### Server CPUs

| CPU Model | Single-Core | Multi-Core |
|-----------|-------------|------------|
| AMD EPYC 9654 (96-core) | 1,700-1,900 | 28,000-32,000 |
| AMD EPYC 7763 (64-core) | 1,400-1,600 | 18,000-20,000 |
| Intel Xeon Platinum 8380 (40-core) | 1,500-1,700 | 16,000-18,000 |
| AMD EPYC 7713 (64-core) | 1,350-1,550 | 17,000-19,000 |

#### GPUs (Compute Score)

| GPU Model | OpenCL Score | CUDA Score | Vulkan Score |
|-----------|--------------|------------|--------------|
| NVIDIA RTX 4090 | 320,000-350,000 | 420,000-450,000 | 300,000-330,000 |
| NVIDIA A100 (40GB) | 210,000-230,000 | 280,000-310,000 | N/A |
| AMD Radeon RX 7900 XTX | 190,000-210,000 | N/A | 180,000-200,000 |
| NVIDIA RTX A6000 | 180,000-200,000 | 240,000-270,000 | 170,000-190,000 |

### Performance Validation Rules

```python
# performance_validator.py
from typing import Dict, Tuple

class PerformanceValidator:
    # Expected score ranges (min, max) for common hardware
    CPU_RANGES = {
        "AMD EPYC 7763": {
            "single_core": (1400, 1650),
            "multi_core": (17000, 21000)
        },
        "AMD EPYC 9654": {
            "single_core": (1700, 2000),
            "multi_core": (27000, 33000)
        },
        "Intel Xeon Platinum 8380": {
            "single_core": (1500, 1750),
            "multi_core": (15000, 19000)
        }
    }

    GPU_RANGES = {
        "NVIDIA A100": {
            "opencl": (200000, 240000),
            "cuda": (270000, 320000)
        },
        "NVIDIA RTX 4090": {
            "opencl": (310000, 360000),
            "cuda": (410000, 460000)
        }
    }

    @staticmethod
    def validate_cpu_score(
        cpu_model: str,
        single_core: int,
        multi_core: int,
        tolerance: float = 0.15
    ) -> Tuple[bool, str]:
        """
        Validate CPU scores against expected ranges.

        Returns:
            (is_valid, message)
        """
        # Normalize CPU model name
        cpu_key = PerformanceValidator._normalize_cpu_name(cpu_model)

        if cpu_key not in PerformanceValidator.CPU_RANGES:
            return (True, f"No reference data for {cpu_model}")

        expected = PerformanceValidator.CPU_RANGES[cpu_key]

        # Check single-core with tolerance
        sc_min, sc_max = expected["single_core"]
        sc_min = sc_min * (1 - tolerance)
        sc_max = sc_max * (1 + tolerance)

        if not (sc_min <= single_core <= sc_max):
            return (
                False,
                f"Single-core score {single_core} outside expected range "
                f"[{sc_min:.0f}, {sc_max:.0f}]"
            )

        # Check multi-core with tolerance
        mc_min, mc_max = expected["multi_core"]
        mc_min = mc_min * (1 - tolerance)
        mc_max = mc_max * (1 + tolerance)

        if not (mc_min <= multi_core <= mc_max):
            return (
                False,
                f"Multi-core score {multi_core} outside expected range "
                f"[{mc_min:.0f}, {mc_max:.0f}]"
            )

        return (True, "Scores within expected range")

    @staticmethod
    def detect_virtualization(
        single_core: int,
        multi_core: int,
        cores: int
    ) -> Tuple[bool, str]:
        """
        Detect potential virtualization based on score patterns.

        Virtualized systems typically show:
        - Lower than expected multi-core scaling
        - Inconsistent per-core performance
        """
        # Calculate scaling efficiency
        expected_multi = single_core * cores * 0.85  # 85% scaling is good
        actual_scaling = multi_core / single_core / cores

        if actual_scaling < 0.60:  # Less than 60% scaling
            return (
                True,
                f"Poor multi-core scaling ({actual_scaling:.1%}) suggests "
                "virtualization or resource contention"
            )

        return (False, "No virtualization detected")

    @staticmethod
    def _normalize_cpu_name(cpu_model: str) -> str:
        """Normalize CPU model name for lookup."""
        # Remove extra whitespace and common suffixes
        normalized = cpu_model.strip()
        normalized = normalized.replace("  ", " ")
        normalized = normalized.replace("-Core Processor", "")
        normalized = normalized.replace("@", "").split()[0:3]
        return " ".join(normalized)


# Example usage
if __name__ == "__main__":
    validator = PerformanceValidator()

    # Validate CPU performance
    is_valid, message = validator.validate_cpu_score(
        cpu_model="AMD EPYC 7763",
        single_core=1523,
        multi_core=18945
    )
    print(f"CPU Validation: {is_valid}")
    print(f"Message: {message}")

    # Check for virtualization
    is_vm, vm_message = validator.detect_virtualization(
        single_core=1523,
        multi_core=18945,
        cores=64
    )
    print(f"Virtualization Detected: {is_vm}")
    print(f"Message: {vm_message}")
```

---

## Integration Examples

### Complete Marketplace Integration

```python
# marketplace_geekbench.py
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

class MarketplaceGeekbenchIntegration:
    def __init__(
        self,
        geekbench_binary: str = "/usr/local/bin/geekbench6",
        results_dir: str = "/var/benchmark/results"
    ):
        self.runner = GeekbenchRunner(geekbench_binary)
        self.parser = GeekbenchParser()
        self.validator = PerformanceValidator()
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    async def benchmark_provider(
        self,
        provider_id: str,
        claimed_specs: Dict,
        iterations: int = 3
    ) -> Dict:
        """
        Run comprehensive benchmark for provider onboarding.

        Args:
            provider_id: Unique provider identifier
            claimed_specs: Hardware specs claimed by provider
            iterations: Number of benchmark runs for accuracy

        Returns:
            Complete benchmark report with validation
        """
        print(f"Benchmarking provider: {provider_id}")
        print(f"Claimed CPU: {claimed_specs['cpu']}")
        print(f"Claimed Cores: {claimed_specs['cores']}")

        report = {
            "provider_id": provider_id,
            "timestamp": datetime.utcnow().isoformat(),
            "claimed_specs": claimed_specs,
            "benchmarks": {},
            "validation": {},
            "verdict": None
        }

        try:
            # Run CPU benchmark
            print("\n=== CPU Benchmark ===")
            cpu_result = self.runner.run_cpu_benchmark(
                iterations=iterations,
                no_upload=True
            )
            report["benchmarks"]["cpu"] = cpu_result

            # Validate CPU performance
            is_valid, message = self.validator.validate_cpu_score(
                cpu_model=claimed_specs["cpu"],
                single_core=cpu_result["single_core"]["average"],
                multi_core=cpu_result["multi_core"]["average"]
            )
            report["validation"]["cpu_performance"] = {
                "valid": is_valid,
                "message": message
            }

            # Check for virtualization
            is_vm, vm_message = self.validator.detect_virtualization(
                single_core=cpu_result["single_core"]["average"],
                multi_core=cpu_result["multi_core"]["average"],
                cores=claimed_specs["cores"]
            )
            report["validation"]["virtualization"] = {
                "detected": is_vm,
                "message": vm_message
            }

            # Run GPU benchmark if claimed
            if claimed_specs.get("gpu"):
                print("\n=== GPU Benchmark ===")
                try:
                    gpu_result = self.runner.run_gpu_benchmark(api="OpenCL")
                    report["benchmarks"]["gpu"] = gpu_result
                    report["validation"]["gpu_available"] = True
                except Exception as e:
                    print(f"GPU benchmark failed: {e}")
                    report["validation"]["gpu_available"] = False
                    report["validation"]["gpu_error"] = str(e)

            # Determine overall verdict
            verdict = self._determine_verdict(report)
            report["verdict"] = verdict

            # Save report
            report_file = self.results_dir / f"{provider_id}_report.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)

            print(f"\n=== Benchmark Complete ===")
            print(f"Verdict: {verdict['status']}")
            print(f"Report saved: {report_file}")

            return report

        except Exception as e:
            print(f"Benchmark failed: {e}")
            report["error"] = str(e)
            report["verdict"] = {"status": "ERROR", "reason": str(e)}
            return report

    def _determine_verdict(self, report: Dict) -> Dict:
        """Determine if provider passes validation."""
        validation = report["validation"]

        # Check CPU performance
        if not validation["cpu_performance"]["valid"]:
            return {
                "status": "REJECTED",
                "reason": "CPU performance below claimed specs",
                "details": validation["cpu_performance"]["message"]
            }

        # Check virtualization
        if validation["virtualization"]["detected"]:
            return {
                "status": "REJECTED",
                "reason": "Virtualization detected",
                "details": validation["virtualization"]["message"]
            }

        # Check GPU if claimed
        if report["claimed_specs"].get("gpu"):
            if not validation.get("gpu_available"):
                return {
                    "status": "REJECTED",
                    "reason": "GPU claimed but not detected",
                    "details": validation.get("gpu_error", "Unknown error")
                }

        # All checks passed
        return {
            "status": "APPROVED",
            "reason": "All benchmarks passed validation",
            "scores": {
                "single_core": report["benchmarks"]["cpu"]["single_core"]["average"],
                "multi_core": report["benchmarks"]["cpu"]["multi_core"]["average"]
            }
        }

    async def spot_check(self, provider_id: str) -> Dict:
        """Quick spot-check benchmark for continuous monitoring."""
        print(f"Running spot-check for provider: {provider_id}")

        cpu_result = self.runner.run_cpu_benchmark(
            quick_mode=True,
            iterations=1,
            no_upload=True
        )

        return {
            "provider_id": provider_id,
            "timestamp": datetime.utcnow().isoformat(),
            "type": "spot_check",
            "single_core_score": cpu_result["score"],
            "multi_core_score": cpu_result["multicore_score"]
        }


# CLI Interface
if __name__ == "__main__":
    import sys

    integration = MarketplaceGeekbenchIntegration()

    if len(sys.argv) < 2:
        print("Usage: python marketplace_geekbench.py <provider_id> [claimed_cpu] [cores]")
        sys.exit(1)

    provider_id = sys.argv[1]
    claimed_cpu = sys.argv[2] if len(sys.argv) > 2 else "AMD EPYC 7763"
    cores = int(sys.argv[3]) if len(sys.argv) > 3 else 64

    claimed_specs = {
        "cpu": claimed_cpu,
        "cores": cores,
        "memory_gb": 256
    }

    # Run benchmark
    asyncio.run(integration.benchmark_provider(
        provider_id=provider_id,
        claimed_specs=claimed_specs,
        iterations=3
    ))
```

---

## Advanced Configuration

### TEE Integration

For running Geekbench inside Intel SGX or AMD SEV-SNP:

```python
# tee_geekbench.py
import grpc
from typing import Dict

class TEEGeekbenchRunner:
    def __init__(self, enclave_path: str):
        self.enclave_path = enclave_path

    async def run_in_tee(self, benchmark_config: Dict) -> Dict:
        """Run Geekbench inside TEE and return attestation."""
        # This is a simplified example
        # Actual implementation depends on TEE framework (Gramine, Occlum, etc.)

        # 1. Start enclave
        enclave = await self._start_enclave()

        # 2. Generate attestation
        attestation = await enclave.get_attestation()

        # 3. Run benchmark inside enclave
        result = await enclave.execute({
            "command": "geekbench6",
            "args": ["--no-upload", "--output-format", "json"]
        })

        # 4. Sign result with enclave key
        signed_result = await enclave.sign(result)

        # 5. Stop enclave
        await enclave.stop()

        return {
            "result": result,
            "attestation": attestation,
            "signature": signed_result
        }
```

### Gramine Manifest for SGX

```toml
# geekbench.manifest.template
libos.entrypoint = "/usr/local/bin/geekbench6"

loader.env.LD_LIBRARY_PATH = "/lib:/usr/lib:/usr/lib/x86_64-linux-gnu"

fs.mounts = [
  { path = "/lib", uri = "file:/lib" },
  { path = "/usr", uri = "file:/usr" },
  { path = "/tmp", type = "tmpfs" },
  { path = "/results", uri = "file:/var/benchmark/results" },
]

sgx.debug = false
sgx.edmm_enable = false
sgx.enclave_size = "4G"
sgx.max_threads = 128

sgx.trusted_files = [
  "file:/usr/local/bin/geekbench6",
  "file:/usr/local/bin/geekbench_x86_64",
  "file:/lib/x86_64-linux-gnu/",
  "file:/usr/lib/x86_64-linux-gnu/",
]

sgx.allowed_files = [
  "file:/tmp",
  "file:/var/benchmark/results",
]
```

---

## Troubleshooting

### Common Issues

#### 1. Benchmark Crashes

**Symptom**: Geekbench exits with error code

**Solutions**:
```bash
# Check system resources
free -h
df -h

# Verify executable permissions
chmod +x /usr/local/bin/geekbench6

# Check for missing libraries
ldd /usr/local/bin/geekbench_x86_64

# Run with verbose output
geekbench6 --verbose
```

#### 2. GPU Not Detected

**Symptom**: GPU benchmark fails or GPU not listed

**Solutions**:
```bash
# Check GPU drivers
nvidia-smi  # For NVIDIA
rocm-smi    # For AMD

# Verify OpenCL
clinfo

# Check Vulkan
vulkaninfo

# Install missing runtime
sudo apt-get install -y ocl-icd-opencl-dev
```

#### 3. Low Scores

**Symptom**: Scores significantly lower than expected

**Investigation**:
```bash
# Check CPU frequency scaling
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
# Should be "performance", not "powersave"

# Set performance mode
sudo cpupower frequency-set -g performance

# Check thermal throttling
sensors

# Monitor during benchmark
watch -n1 "grep MHz /proc/cpuinfo | head -n 64"
```

#### 4. Result Upload Fails

**Symptom**: Cannot upload results to Geekbench Browser

**Solutions**:
```bash
# Use --no-upload for offline mode
geekbench6 --no-upload --output-format json --output-file result.json

# Check network connectivity
ping www.geekbench.com

# Use proxy if needed
export http_proxy=http://proxy.example.com:8080
export https_proxy=http://proxy.example.com:8080
```

---

## References

- [Geekbench Official Site](https://www.geekbench.com/)
- [Geekbench CLI Documentation](http://support.primatelabs.com/kb/geekbench/geekbench-6-command-line-tool)
- [Geekbench Browser](https://browser.geekbench.com/) - Compare scores
- [Geekbench Benchmark Internals PDF](https://www.geekbench.com/doc/geekbench6-benchmark-internals.pdf)
- [Primate Labs Support](http://support.primatelabs.com/)
