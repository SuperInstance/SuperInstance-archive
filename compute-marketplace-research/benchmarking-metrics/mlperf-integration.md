# MLPerf Integration Guide

## Table of Contents
1. [Overview](#overview)
2. [Which Benchmarks to Use](#which-benchmarks-to-use)
3. [Dataset Management](#dataset-management)
4. [Execution Environment](#execution-environment)
5. [GPU Optimization](#gpu-optimization)
6. [Automated Execution](#automated-execution)
7. [Result Parsing](#result-parsing)
8. [Integration Examples](#integration-examples)
9. [Troubleshooting](#troubleshooting)

---

## Overview

MLPerf is an industry-standard benchmark suite for measuring machine learning performance across different hardware platforms. Maintained by MLCommons, it provides objective comparisons for training and inference workloads.

### Why MLPerf?

- **Industry Standard**: Used by NVIDIA, AMD, Intel, Google, and major cloud providers
- **Real-World Models**: Tests production-relevant models (ResNet, BERT, etc.)
- **Reproducible**: Standardized rules and datasets ensure fair comparison
- **Hardware Agnostic**: Runs on CPUs, GPUs, TPUs, and specialized accelerators
- **Open Source**: Freely available reference implementations
- **Continuous Evolution**: Regular updates with new models (LLMs added in v5.0)

### Benchmark Categories

#### 1. MLPerf Inference (Recommended for Marketplace)
- **Purpose**: Measure inference throughput and latency
- **Duration**: Minutes to hours per benchmark
- **Use Case**: Validate compute resources for ML workloads
- **Scenarios**:
  - **Server**: Maximum throughput with latency constraints
  - **Offline**: Maximum throughput without latency constraints
  - **Single Stream**: Minimal latency for one query at a time
  - **Multi-Stream**: Process fixed number of streams in parallel

#### 2. MLPerf Training
- **Purpose**: Measure training time to reach target accuracy
- **Duration**: Hours to days per benchmark
- **Use Case**: Validate training infrastructure
- **Complexity**: Higher (requires more datasets and longer execution)

**Recommendation**: Use MLPerf Inference for marketplace verification due to shorter execution time and relevance to most compute marketplace use cases.

### Latest Developments (2025)

- **MLPerf v5.1 (Released 2025)**: Added DeepSeek-R1 reasoning and Llama 3.1 405B
- **Enhanced LLM Tests**: Focus on reasoning capabilities and large language models
- **Improved Automation**: Better tooling for reproducible results
- **Cloud Provider Support**: AWS, Azure, GCP provide detailed setup guides

---

## Which Benchmarks to Use

### Recommended MLPerf Inference Benchmarks

For a compute marketplace, prioritize these benchmarks based on common workloads:

#### Tier 1: Essential Benchmarks (Always Run)

**1. ResNet-50 (Image Classification)**
- **Model**: ResNet-50 v1.5
- **Dataset**: ImageNet (50,000 validation images)
- **Task**: Image classification
- **Typical Throughput**: 1,000-50,000 images/sec depending on hardware
- **Why**: Baseline CV workload, fast execution (~5-10 minutes)
- **Use Case**: Computer vision, image processing

**2. BERT-Large (NLP)**
- **Model**: BERT-Large (Squad v1.1)
- **Dataset**: SQuAD v1.1 validation set
- **Task**: Question answering
- **Typical Throughput**: 100-5,000 queries/sec
- **Why**: Standard NLP benchmark, representative of language models
- **Use Case**: Natural language processing, chatbots

#### Tier 2: GPU-Specific Benchmarks (Run if GPU Present)

**3. DLRM (Recommendation)**
- **Model**: Deep Learning Recommendation Model
- **Dataset**: Criteo Terabyte dataset (subset)
- **Task**: Click-through rate prediction
- **Typical Throughput**: 10,000-1,000,000 samples/sec
- **Why**: Tests memory bandwidth and embedding operations
- **Use Case**: Recommendation systems, ad tech

**4. 3D U-Net (Medical Imaging)**
- **Model**: 3D U-Net (BraTS 2019)
- **Dataset**: BraTS 2019 validation set
- **Task**: Medical image segmentation
- **Typical Throughput**: 1-10 volumes/sec
- **Why**: Tests 3D convolutions and medical imaging workloads
- **Use Case**: Healthcare AI, medical imaging

#### Tier 3: Advanced Benchmarks (Optional, for Premium Validation)

**5. Llama 3.1 (Large Language Model)**
- **Model**: Llama 3.1 70B/405B
- **Dataset**: OpenOrca or custom prompts
- **Task**: Text generation
- **Typical Throughput**: 10-100 tokens/sec
- **Why**: Validates LLM inference capability
- **Use Case**: Large language model deployment
- **Note**: Requires significant memory (>40GB for 70B, >200GB for 405B)

**6. Stable Diffusion (Image Generation)**
- **Model**: Stable Diffusion XL
- **Dataset**: COCO validation prompts
- **Task**: Text-to-image generation
- **Typical Throughput**: 0.5-5 images/sec
- **Why**: Tests diffusion model performance
- **Use Case**: Generative AI, image synthesis

### Benchmark Selection Matrix

```
┌────────────────────┬──────────┬──────────┬───────────┬─────────────┐
│    Benchmark       │ Duration │ Hardware │ Dataset   │ Priority    │
│                    │          │ Required │ Size      │ for Market  │
├────────────────────┼──────────┼──────────┼───────────┼─────────────┤
│ ResNet-50          │ 5-10 min │ CPU/GPU  │ 6.5 GB    │ ESSENTIAL   │
│ BERT-Large         │ 10-15min │ GPU      │ 500 MB    │ ESSENTIAL   │
│ DLRM               │ 15-30min │ GPU      │ 1 TB*     │ RECOMMENDED │
│ 3D U-Net           │ 20-40min │ GPU      │ 5 GB      │ RECOMMENDED │
│ Llama 3.1 70B      │ 30-60min │ GPU+VRAM │ 10 GB     │ OPTIONAL    │
│ Stable Diffusion   │ 15-30min │ GPU      │ 2 GB      │ OPTIONAL    │
└────────────────────┴──────────┴──────────┴───────────┴─────────────┘

* Can use subset for faster execution
```

### Benchmark Selection Strategy

```python
# benchmark_selector.py
from typing import List, Dict

class MLPerfBenchmarkSelector:
    @staticmethod
    def select_benchmarks(hardware_specs: Dict) -> List[str]:
        """
        Select appropriate MLPerf benchmarks based on hardware.

        Args:
            hardware_specs: {
                'has_gpu': bool,
                'gpu_memory_gb': int,
                'cpu_cores': int,
                'system_memory_gb': int
            }

        Returns:
            List of benchmark names to run
        """
        benchmarks = []

        # Always run ResNet-50 (works on CPU or GPU)
        benchmarks.append('resnet50')

        if hardware_specs.get('has_gpu'):
            # Add BERT for any GPU
            benchmarks.append('bert')

            gpu_memory = hardware_specs.get('gpu_memory_gb', 0)

            # Add DLRM for GPUs with 16GB+
            if gpu_memory >= 16:
                benchmarks.append('dlrm')

            # Add 3D U-Net for GPUs with 24GB+
            if gpu_memory >= 24:
                benchmarks.append('3d-unet')

            # Add Llama for GPUs with 80GB+
            if gpu_memory >= 80:
                benchmarks.append('llama-70b')

            # Add Stable Diffusion for GPUs with 12GB+
            if gpu_memory >= 12:
                benchmarks.append('stable-diffusion')

        return benchmarks

# Example usage
hardware = {
    'has_gpu': True,
    'gpu_memory_gb': 40,
    'cpu_cores': 64,
    'system_memory_gb': 256
}

selector = MLPerfBenchmarkSelector()
benchmarks = selector.select_benchmarks(hardware)
print(f"Selected benchmarks: {benchmarks}")
# Output: ['resnet50', 'bert', 'dlrm', '3d-unet', 'stable-diffusion']
```

---

## Dataset Management

### Dataset Overview

MLPerf benchmarks require specific datasets. Proper management is crucial for efficient execution.

#### Dataset Sizes

| Benchmark | Dataset | Size | Download Time | Storage Type |
|-----------|---------|------|---------------|--------------|
| ResNet-50 | ImageNet 2012 | 6.5 GB | 10-30 min | SSD |
| BERT | SQuAD v1.1 | 500 MB | 1-5 min | Any |
| DLRM | Criteo (full) | 1 TB | Hours | Fast NVMe |
| DLRM | Criteo (subset) | 100 GB | 30-60 min | SSD |
| 3D U-Net | BraTS 2019 | 5 GB | 10-20 min | SSD |
| Llama | OpenOrca | 10 GB | 15-30 min | SSD |

### Dataset Storage Architecture

```
/data/mlperf/
├── datasets/
│   ├── imagenet/
│   │   ├── val/          # 50,000 validation images
│   │   └── calibration/  # For quantization
│   ├── squad/
│   │   ├── dev-v1.1.json
│   │   └── vocab.txt
│   ├── criteo/
│   │   ├── day_23.gz     # Validation data
│   │   └── preprocessed/ # Preprocessed embeddings
│   ├── brats/
│   │   └── BRATS_validation_data/
│   └── openorca/
│       └── prompts.json
├── models/
│   ├── resnet50/
│   │   └── resnet50_v1.onnx
│   ├── bert/
│   │   └── bert_large_v1_1_fake_quant.onnx
│   └── ...
└── preprocessed/
    └── cache/            # Cached preprocessing results
```

### Dataset Download Scripts

#### Automated Dataset Downloader

```python
# dataset_manager.py
import os
import hashlib
import requests
import tarfile
import gzip
from pathlib import Path
from typing import Optional
from tqdm import tqdm

class MLPerfDatasetManager:
    def __init__(self, data_root: str = "/data/mlperf"):
        self.data_root = Path(data_root)
        self.datasets_dir = self.data_root / "datasets"
        self.models_dir = self.data_root / "models"
        self.datasets_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def download_resnet50_dataset(self):
        """Download ImageNet validation set."""
        imagenet_dir = self.datasets_dir / "imagenet"
        imagenet_dir.mkdir(exist_ok=True)

        print("ImageNet dataset requires manual download due to licensing.")
        print("Please:")
        print("1. Register at https://image-net.org/download-images")
        print("2. Download ILSVRC2012_img_val.tar")
        print(f"3. Place it in {imagenet_dir}/")
        print("4. Run: tar xf ILSVRC2012_img_val.tar -C val/")

        # Check if already present
        val_dir = imagenet_dir / "val"
        if val_dir.exists() and len(list(val_dir.glob("*.JPEG"))) >= 50000:
            print("✓ ImageNet validation set already present")
            return True
        else:
            print("✗ ImageNet validation set not found")
            return False

    def download_squad_dataset(self):
        """Download SQuAD v1.1 dataset."""
        squad_dir = self.datasets_dir / "squad"
        squad_dir.mkdir(exist_ok=True)

        squad_file = squad_dir / "dev-v1.1.json"

        if squad_file.exists():
            print("✓ SQuAD dataset already present")
            return True

        print("Downloading SQuAD v1.1...")
        url = "https://rajpurkar.github.io/SQuAD-explorer/dataset/dev-v1.1.json"

        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(squad_file, 'wb') as f:
            for chunk in tqdm(response.iter_content(chunk_size=8192)):
                f.write(chunk)

        print("✓ SQuAD dataset downloaded")
        return True

    def download_criteo_dataset(self, subset: bool = True):
        """Download Criteo dataset."""
        criteo_dir = self.datasets_dir / "criteo"
        criteo_dir.mkdir(exist_ok=True)

        if subset:
            print("Downloading Criteo subset (100GB)...")
            # In practice, use preprocessed subset from MLCommons
            print("For full dataset, see: https://ailab.criteo.com/download-criteo-1tb-click-logs-dataset/")
        else:
            print("Full Criteo dataset (1TB) requires manual download")
            print("See: https://ailab.criteo.com/download-criteo-1tb-click-logs-dataset/")

    def download_brats_dataset(self):
        """Download BraTS 2019 dataset."""
        brats_dir = self.datasets_dir / "brats"
        brats_dir.mkdir(exist_ok=True)

        print("BraTS 2019 requires registration at:")
        print("https://www.med.upenn.edu/cbica/brats2019/data.html")
        print(f"Extract to: {brats_dir}/")

        # Check if present
        if (brats_dir / "BRATS_validation_data").exists():
            print("✓ BraTS dataset already present")
            return True
        else:
            print("✗ BraTS dataset not found")
            return False

    def download_model_files(self, benchmark: str):
        """Download pre-trained model files."""
        model_dir = self.models_dir / benchmark
        model_dir.mkdir(exist_ok=True)

        # Model URLs (example - actual URLs may vary)
        model_urls = {
            "resnet50": "https://zenodo.org/record/2535873/files/resnet50_v1.pb",
            "bert": "https://zenodo.org/record/3750364/files/bert_large_v1_1_fake_quant.onnx"
        }

        if benchmark in model_urls:
            model_file = model_dir / Path(model_urls[benchmark]).name

            if model_file.exists():
                print(f"✓ Model for {benchmark} already present")
                return True

            print(f"Downloading model for {benchmark}...")
            self._download_file(model_urls[benchmark], model_file)
            print(f"✓ Model downloaded")
            return True
        else:
            print(f"No automatic download for {benchmark}")
            return False

    def _download_file(self, url: str, dest: Path, chunk_size: int = 8192):
        """Download file with progress bar."""
        response = requests.get(url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))

        with open(dest, 'wb') as f, tqdm(
            total=total_size,
            unit='iB',
            unit_scale=True,
            desc=dest.name
        ) as pbar:
            for chunk in response.iter_content(chunk_size=chunk_size):
                size = f.write(chunk)
                pbar.update(size)

    def verify_dataset(self, benchmark: str) -> bool:
        """Verify dataset integrity."""
        dataset_checks = {
            "resnet50": self._verify_imagenet,
            "bert": self._verify_squad,
            "3d-unet": self._verify_brats
        }

        if benchmark in dataset_checks:
            return dataset_checks[benchmark]()
        else:
            print(f"No verification available for {benchmark}")
            return True

    def _verify_imagenet(self) -> bool:
        """Verify ImageNet dataset."""
        val_dir = self.datasets_dir / "imagenet" / "val"
        if not val_dir.exists():
            return False

        num_images = len(list(val_dir.glob("*.JPEG")))
        if num_images != 50000:
            print(f"Expected 50,000 images, found {num_images}")
            return False

        print("✓ ImageNet validation set verified")
        return True

    def _verify_squad(self) -> bool:
        """Verify SQuAD dataset."""
        squad_file = self.datasets_dir / "squad" / "dev-v1.1.json"
        if not squad_file.exists():
            return False

        # Verify file size (should be ~4.5MB)
        size_mb = squad_file.stat().st_size / (1024 * 1024)
        if size_mb < 4 or size_mb > 5:
            print(f"SQuAD file size unexpected: {size_mb:.1f} MB")
            return False

        print("✓ SQuAD dataset verified")
        return True

    def _verify_brats(self) -> bool:
        """Verify BraTS dataset."""
        brats_dir = self.datasets_dir / "brats" / "BRATS_validation_data"
        if not brats_dir.exists():
            return False

        # Should have multiple case folders
        cases = list(brats_dir.glob("*"))
        if len(cases) < 100:
            print(f"Expected 100+ cases, found {len(cases)}")
            return False

        print("✓ BraTS dataset verified")
        return True

    def get_dataset_path(self, benchmark: str) -> Optional[Path]:
        """Get path to dataset for given benchmark."""
        dataset_paths = {
            "resnet50": self.datasets_dir / "imagenet" / "val",
            "bert": self.datasets_dir / "squad",
            "dlrm": self.datasets_dir / "criteo",
            "3d-unet": self.datasets_dir / "brats"
        }

        return dataset_paths.get(benchmark)

    def setup_all_datasets(self, benchmarks: list):
        """Setup all required datasets."""
        print("=== MLPerf Dataset Setup ===\n")

        for benchmark in benchmarks:
            print(f"\n--- {benchmark.upper()} ---")

            if benchmark == "resnet50":
                self.download_resnet50_dataset()
                self.download_model_files("resnet50")
            elif benchmark == "bert":
                self.download_squad_dataset()
                self.download_model_files("bert")
            elif benchmark == "dlrm":
                self.download_criteo_dataset(subset=True)
            elif benchmark == "3d-unet":
                self.download_brats_dataset()

        print("\n=== Setup Complete ===")


# Example usage
if __name__ == "__main__":
    manager = MLPerfDatasetManager()

    # Setup datasets for selected benchmarks
    benchmarks = ["resnet50", "bert"]
    manager.setup_all_datasets(benchmarks)

    # Verify datasets
    for benchmark in benchmarks:
        print(f"\nVerifying {benchmark}...")
        is_valid = manager.verify_dataset(benchmark)
        print(f"Valid: {is_valid}")
```

### Dataset Preprocessing

Some benchmarks require preprocessing for optimal performance:

```python
# preprocess_datasets.py
import numpy as np
from PIL import Image
from pathlib import Path
import pickle

class DatasetPreprocessor:
    def __init__(self, data_root: str = "/data/mlperf"):
        self.data_root = Path(data_root)

    def preprocess_imagenet(self, output_format: str = "npy"):
        """
        Preprocess ImageNet for faster loading.

        Args:
            output_format: 'npy' or 'tfrecord'
        """
        imagenet_dir = self.data_root / "datasets" / "imagenet" / "val"
        preprocessed_dir = self.data_root / "preprocessed" / "imagenet"
        preprocessed_dir.mkdir(parents=True, exist_ok=True)

        print("Preprocessing ImageNet validation set...")

        images = sorted(imagenet_dir.glob("*.JPEG"))

        if output_format == "npy":
            # Convert to numpy arrays
            batch_size = 1000
            for i in range(0, len(images), batch_size):
                batch = images[i:i+batch_size]
                batch_array = []

                for img_path in batch:
                    img = Image.open(img_path).convert('RGB')
                    img = img.resize((224, 224))
                    img_array = np.array(img)
                    batch_array.append(img_array)

                batch_array = np.array(batch_array)
                output_file = preprocessed_dir / f"batch_{i//batch_size:04d}.npy"
                np.save(output_file, batch_array)

                print(f"Processed batch {i//batch_size + 1}/{len(images)//batch_size}")

        print("✓ Preprocessing complete")

    def create_calibration_set(self, benchmark: str, num_samples: int = 500):
        """Create calibration set for quantization."""
        dataset_dir = self.data_root / "datasets" / benchmark
        calibration_dir = dataset_dir / "calibration"
        calibration_dir.mkdir(exist_ok=True)

        print(f"Creating calibration set for {benchmark}...")

        # Implementation depends on benchmark
        # Typically select random subset of validation set

        print(f"✓ Calibration set created with {num_samples} samples")
```

---

## Execution Environment

### System Requirements

#### Minimum Requirements

- **OS**: Ubuntu 20.04/22.04, RHEL 8+, or compatible Linux
- **Python**: 3.8+
- **Disk**: 100GB+ free space (for datasets)
- **Memory**: 32GB+ RAM
- **CPU**: Modern x86_64 processor (AVX2 support)

#### GPU Requirements (for GPU benchmarks)

- **NVIDIA**: Driver 525.60.13+, CUDA 12.0+, cuDNN 8.9+
- **AMD**: ROCm 5.7+
- **Memory**: 16GB+ VRAM for basic benchmarks, 80GB+ for large models

### Software Stack

#### Core Dependencies

```bash
#!/bin/bash
# install_mlperf_deps.sh

set -e

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install build tools
sudo apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    python3-pip \
    python3-dev

# Install Python dependencies
pip3 install --upgrade pip
pip3 install \
    numpy \
    onnx \
    onnxruntime \
    onnxruntime-gpu \
    torch \
    torchvision \
    tensorflow \
    pybind11 \
    opencv-python \
    pillow \
    pycocotools \
    nvidia-pyindex \
    nvidia-tensorrt

# Install MLPerf loadgen
git clone https://github.com/mlcommons/inference.git /opt/mlperf-inference
cd /opt/mlperf-inference/loadgen
python3 setup.py install

echo "✓ MLPerf dependencies installed"
```

#### NVIDIA GPU Setup

```bash
#!/bin/bash
# setup_nvidia_gpu.sh

set -e

# Install NVIDIA drivers
sudo apt-get install -y nvidia-driver-535

# Add NVIDIA package repository
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.0-1_all.deb
sudo dpkg -i cuda-keyring_1.0-1_all.deb
sudo apt-get update

# Install CUDA Toolkit
sudo apt-get install -y cuda-toolkit-12-3

# Install cuDNN
sudo apt-get install -y libcudnn8 libcudnn8-dev

# Install TensorRT
sudo apt-get install -y tensorrt

# Verify installation
nvidia-smi
nvcc --version

echo "✓ NVIDIA GPU stack installed"
```

#### AMD GPU Setup

```bash
#!/bin/bash
# setup_amd_gpu.sh

set -e

# Add AMD repository
wget https://repo.radeon.com/amdgpu-install/latest/ubuntu/jammy/amdgpu-install_*.deb
sudo apt-get install -y ./amdgpu-install_*.deb

# Install ROCm
sudo amdgpu-install -y --usecase=rocm

# Install PyTorch with ROCm support
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/rocm5.7

# Verify installation
rocm-smi

echo "✓ AMD ROCm stack installed"
```

### Docker Environment (Recommended)

Docker provides consistent, reproducible environment:

```dockerfile
# Dockerfile.mlperf
FROM nvidia/cuda:12.3.0-cudnn9-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    wget \
    cmake \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip3 install --no-cache-dir \
    numpy \
    onnx \
    onnxruntime-gpu \
    torch \
    torchvision \
    tensorflow \
    transformers \
    pillow \
    opencv-python \
    tqdm

# Clone MLPerf inference
RUN git clone --recursive https://github.com/mlcommons/inference.git /workspace/mlperf-inference
WORKDIR /workspace/mlperf-inference

# Build loadgen
RUN cd loadgen && \
    python3 setup.py install

# Set up data directories
RUN mkdir -p /data/mlperf/datasets /data/mlperf/models /results

WORKDIR /workspace/mlperf-inference

CMD ["/bin/bash"]
```

Build and run:

```bash
# Build image
docker build -t mlperf:latest -f Dockerfile.mlperf .

# Run with GPU support
docker run --gpus all \
    -v /data/mlperf:/data/mlperf \
    -v /results:/results \
    -it mlperf:latest bash
```

### Virtual Environment Setup

For non-Docker deployments:

```bash
#!/bin/bash
# setup_venv.sh

set -e

# Create virtual environment
python3 -m venv /opt/mlperf-venv
source /opt/mlperf-venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install \
    numpy \
    onnx \
    onnxruntime-gpu \
    torch \
    torchvision \
    tensorflow-gpu \
    transformers \
    pillow \
    opencv-python \
    tqdm \
    pybind11

# Clone and install MLPerf
git clone https://github.com/mlcommons/inference.git /opt/mlperf-inference
cd /opt/mlperf-inference/loadgen
pip install .

echo "✓ Virtual environment setup complete"
echo "Activate with: source /opt/mlperf-venv/bin/activate"
```

---

## GPU Optimization

### CUDA Optimization

#### Enable GPU Persistence Mode

```bash
# Keep GPU initialized for faster subsequent runs
sudo nvidia-smi -pm 1

# Set GPU to max performance
sudo nvidia-smi -i 0 -pl 400  # Set power limit (adjust based on GPU)
sudo nvidia-smi -lgc 1410,1410  # Lock GPU clock (adjust based on GPU)
```

#### CUDA Environment Variables

```bash
# Enable TensorFloat-32 for faster performance on Ampere+ GPUs
export NVIDIA_TF32_OVERRIDE=1

# Optimize CUDA memory allocation
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=0  # Use specific GPU

# Enable CUDA graphs for reduced overhead
export CUDA_LAUNCH_BLOCKING=0
```

### TensorRT Optimization

TensorRT provides significant speedup for inference:

```python
# tensorrt_optimizer.py
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit

class TensorRTOptimizer:
    def __init__(self):
        self.logger = trt.Logger(trt.Logger.WARNING)
        self.builder = trt.Builder(self.logger)

    def convert_onnx_to_tensorrt(
        self,
        onnx_path: str,
        engine_path: str,
        precision: str = "fp16",
        max_batch_size: int = 32
    ):
        """
        Convert ONNX model to TensorRT engine.

        Args:
            onnx_path: Path to ONNX model
            engine_path: Output path for TensorRT engine
            precision: 'fp32', 'fp16', or 'int8'
            max_batch_size: Maximum batch size
        """
        network_flags = 1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
        network = self.builder.create_network(network_flags)
        parser = trt.OnnxParser(network, self.logger)

        # Parse ONNX
        print(f"Parsing ONNX model: {onnx_path}")
        with open(onnx_path, 'rb') as f:
            if not parser.parse(f.read()):
                for error in range(parser.num_errors):
                    print(parser.get_error(error))
                raise RuntimeError("Failed to parse ONNX model")

        # Configure builder
        config = self.builder.create_builder_config()
        config.max_workspace_size = 8 * (1 << 30)  # 8GB

        # Set precision
        if precision == "fp16":
            config.set_flag(trt.BuilderFlag.FP16)
            print("Using FP16 precision")
        elif precision == "int8":
            config.set_flag(trt.BuilderFlag.INT8)
            print("Using INT8 precision")
            # INT8 requires calibration - omitted for brevity
        else:
            print("Using FP32 precision")

        # Build engine
        print("Building TensorRT engine (this may take a while)...")
        engine = self.builder.build_engine(network, config)

        if engine is None:
            raise RuntimeError("Failed to build TensorRT engine")

        # Serialize engine
        print(f"Saving engine to: {engine_path}")
        with open(engine_path, 'wb') as f:
            f.write(engine.serialize())

        print("✓ TensorRT engine created successfully")

    def benchmark_engine(self, engine_path: str, num_iterations: int = 1000):
        """Benchmark TensorRT engine performance."""
        import time

        # Load engine
        with open(engine_path, 'rb') as f:
            runtime = trt.Runtime(self.logger)
            engine = runtime.deserialize_cuda_engine(f.read())

        context = engine.create_execution_context()

        # Allocate buffers (simplified - actual implementation more complex)
        # ...

        # Warm-up
        for _ in range(10):
            context.execute_v2(bindings=[])

        # Benchmark
        start = time.time()
        for _ in range(num_iterations):
            context.execute_v2(bindings=[])
        end = time.time()

        latency_ms = (end - start) / num_iterations * 1000
        throughput = 1000 / latency_ms

        print(f"Average latency: {latency_ms:.2f} ms")
        print(f"Throughput: {throughput:.0f} inferences/sec")


# Example usage
if __name__ == "__main__":
    optimizer = TensorRTOptimizer()

    # Convert ResNet-50 to TensorRT
    optimizer.convert_onnx_to_tensorrt(
        onnx_path="/data/mlperf/models/resnet50/resnet50_v1.onnx",
        engine_path="/data/mlperf/models/resnet50/resnet50_fp16.trt",
        precision="fp16",
        max_batch_size=32
    )
```

### Multi-GPU Configuration

```python
# multi_gpu_config.py
import torch

class MultiGPUConfig:
    @staticmethod
    def setup_multi_gpu():
        """Configure for multi-GPU execution."""
        if not torch.cuda.is_available():
            print("No CUDA GPUs available")
            return []

        num_gpus = torch.cuda.device_count()
        print(f"Found {num_gpus} CUDA GPUs")

        gpu_info = []
        for i in range(num_gpus):
            props = torch.cuda.get_device_properties(i)
            gpu_info.append({
                'id': i,
                'name': props.name,
                'memory_gb': props.total_memory / (1024**3),
                'compute_capability': f"{props.major}.{props.minor}"
            })

            print(f"GPU {i}: {props.name}, {props.total_memory / (1024**3):.1f} GB")

        return gpu_info

    @staticmethod
    def select_gpu(min_memory_gb: int = 16):
        """Select GPU with sufficient memory."""
        gpu_info = MultiGPUConfig.setup_multi_gpu()

        for gpu in gpu_info:
            if gpu['memory_gb'] >= min_memory_gb:
                torch.cuda.set_device(gpu['id'])
                print(f"Selected GPU {gpu['id']}: {gpu['name']}")
                return gpu['id']

        raise RuntimeError(f"No GPU found with {min_memory_gb}GB+ memory")
```

### Memory Optimization

```python
# memory_optimizer.py
import torch
import gc

class MemoryOptimizer:
    @staticmethod
    def clear_cache():
        """Clear PyTorch cache."""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        gc.collect()

    @staticmethod
    def enable_memory_efficient_mode():
        """Enable memory-efficient settings."""
        if torch.cuda.is_available():
            # Use TF32 for faster computation on Ampere GPUs
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True

            # Enable cuDNN autotuner
            torch.backends.cudnn.benchmark = True

            # Enable memory efficient attention (PyTorch 2.0+)
            if hasattr(torch.nn.functional, 'scaled_dot_product_attention'):
                torch.backends.cuda.enable_mem_efficient_sdp(True)

    @staticmethod
    def print_memory_stats():
        """Print current GPU memory usage."""
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                allocated = torch.cuda.memory_allocated(i) / (1024**3)
                reserved = torch.cuda.memory_reserved(i) / (1024**3)
                print(f"GPU {i} - Allocated: {allocated:.2f} GB, Reserved: {reserved:.2f} GB")
```

---

## Automated Execution

### MLPerf Loadgen Integration

MLPerf provides `loadgen` for standardized benchmark execution:

```python
# mlperf_runner.py
import mlperf_loadgen as lg
import array
import numpy as np
from typing import Dict, List
from pathlib import Path

class MLPerfRunner:
    def __init__(self, model, dataset, scenario: str = "Offline"):
        """
        Initialize MLPerf runner.

        Args:
            model: Model wrapper (must implement predict())
            dataset: Dataset (must implement get_item())
            scenario: MLPerf scenario ('Offline', 'Server', 'SingleStream', 'MultiStream')
        """
        self.model = model
        self.dataset = dataset
        self.scenario = scenario

        # Map scenario names to loadgen scenarios
        self.scenario_map = {
            "Offline": lg.TestScenario.Offline,
            "Server": lg.TestScenario.Server,
            "SingleStream": lg.TestScenario.SingleStream,
            "MultiStream": lg.TestScenario.MultiStream
        }

    def run_benchmark(
        self,
        duration_ms: int = 60000,
        min_queries: int = 1,
        max_queries: int = 0,
        output_dir: str = "/results"
    ) -> Dict:
        """
        Run MLPerf benchmark.

        Args:
            duration_ms: Minimum test duration (ms)
            min_queries: Minimum number of queries
            max_queries: Maximum queries (0 = unlimited)
            output_dir: Directory for results

        Returns:
            Dictionary with results
        """
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Configure loadgen settings
        settings = lg.TestSettings()
        settings.scenario = self.scenario_map[self.scenario]
        settings.mode = lg.TestMode.PerformanceOnly

        # Set duration and query counts
        settings.min_duration_ms = duration_ms
        settings.min_query_count = min_queries
        if max_queries > 0:
            settings.max_query_count = max_queries

        # Configure output
        settings.log_output_dir = output_dir
        settings.log_output_basename = f"{self.scenario.lower()}_results"

        # Create SUT (System Under Test)
        sut = lg.ConstructSUT(self.issue_query, self.flush_queries)

        # Create QSL (Query Sample Library)
        qsl = lg.ConstructQSL(
            len(self.dataset),
            self.dataset.get_total_sample_count(),
            self.dataset.load_samples_to_ram,
            self.dataset.unload_samples_from_ram
        )

        # Run benchmark
        print(f"Running {self.scenario} benchmark...")
        print(f"Duration: {duration_ms}ms, Min queries: {min_queries}")

        lg.StartTest(sut, qsl, settings)

        # Destroy objects
        lg.DestroyQSL(qsl)
        lg.DestroySUT(sut)

        # Parse results
        results = self.parse_results(output_dir)

        print("✓ Benchmark complete")
        return results

    def issue_query(self, query_samples):
        """Process query samples (called by loadgen)."""
        responses = []

        for sample in query_samples:
            # Get input data
            data = self.dataset.get_item(sample.index)

            # Run inference
            output = self.model.predict(data)

            # Create response
            response = lg.QuerySampleResponse(
                sample.id,
                output.data_ptr(),
                output.numel() * output.element_size()
            )
            responses.append(response)

        # Submit responses to loadgen
        lg.QuerySamplesComplete(responses)

    def flush_queries(self):
        """Flush any remaining queries."""
        pass

    def parse_results(self, output_dir: str) -> Dict:
        """Parse MLPerf results."""
        results_file = Path(output_dir) / "mlperf_log_summary.txt"

        if not results_file.exists():
            return {"error": "Results file not found"}

        results = {}

        with open(results_file, 'r') as f:
            for line in f:
                if "Samples per second" in line:
                    results['throughput'] = float(line.split(':')[1].strip())
                elif "Mean latency" in line:
                    results['latency_mean_ms'] = float(line.split(':')[1].strip())
                elif "99.00 percentile latency" in line:
                    results['latency_p99_ms'] = float(line.split(':')[1].strip())

        return results


# Example: ResNet-50 Runner
class ResNet50Runner(MLPerfRunner):
    def __init__(self, model_path: str, dataset_path: str):
        import torch
        import torchvision.models as models

        # Load model
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = models.resnet50(pretrained=False)
        self.model.load_state_dict(torch.load(model_path))
        self.model.to(self.device)
        self.model.eval()

        # Load dataset
        from dataset_imagenet import ImageNetDataset
        self.dataset = ImageNetDataset(dataset_path)

        super().__init__(self.model, self.dataset, scenario="Offline")


# Example usage
if __name__ == "__main__":
    runner = ResNet50Runner(
        model_path="/data/mlperf/models/resnet50/resnet50_v1.pth",
        dataset_path="/data/mlperf/datasets/imagenet/val"
    )

    results = runner.run_benchmark(
        duration_ms=60000,  # 1 minute
        min_queries=1024
    )

    print(f"Throughput: {results['throughput']:.0f} samples/sec")
    print(f"Mean latency: {results['latency_mean_ms']:.2f} ms")
    print(f"P99 latency: {results['latency_p99_ms']:.2f} ms")
```

### Simplified Automation Script

```bash
#!/bin/bash
# run_mlperf_benchmarks.sh

set -e

MLPERF_ROOT="/opt/mlperf-inference"
DATA_ROOT="/data/mlperf"
RESULTS_DIR="/results/mlperf_$(date +%Y%m%d_%H%M%S)"

mkdir -p ${RESULTS_DIR}

# Activate environment
source /opt/mlperf-venv/bin/activate

# Function to run benchmark
run_benchmark() {
    local benchmark=$1
    local scenario=$2

    echo "=== Running ${benchmark} (${scenario}) ==="

    cd ${MLPERF_ROOT}/vision/classification_and_detection

    python3 python/main.py \
        --backend pytorch \
        --model ${benchmark} \
        --scenario ${scenario} \
        --dataset-path ${DATA_ROOT}/datasets/imagenet/val \
        --model-path ${DATA_ROOT}/models/${benchmark}/${benchmark}.pth \
        --output ${RESULTS_DIR}/${benchmark}_${scenario} \
        --accuracy

    echo "✓ ${benchmark} (${scenario}) complete"
}

# Run ResNet-50
run_benchmark "resnet50" "Offline"

# Run BERT (if GPU available)
if command -v nvidia-smi &> /dev/null; then
    echo "=== Running BERT ==="

    cd ${MLPERF_ROOT}/language/bert

    python3 run.py \
        --backend pytorch \
        --scenario Offline \
        --model-path ${DATA_ROOT}/models/bert/bert-large.pth \
        --vocab-file ${DATA_ROOT}/datasets/squad/vocab.txt \
        --val-data ${DATA_ROOT}/datasets/squad/dev-v1.1.json \
        --output ${RESULTS_DIR}/bert_offline \
        --accuracy

    echo "✓ BERT complete"
fi

echo "=== All benchmarks complete ==="
echo "Results saved to: ${RESULTS_DIR}"

# Generate summary
python3 ${MLPERF_ROOT}/tools/submission/generate_final_report.py \
    --input ${RESULTS_DIR} \
    --output ${RESULTS_DIR}/summary.txt

cat ${RESULTS_DIR}/summary.txt
```

---

## Result Parsing

### MLPerf Result Format

MLPerf produces detailed logs in `mlperf_log_summary.txt`:

```
================================================
MLPerf Results Summary
================================================
SUT name : PyTorch ResNet50
Scenario : Offline
Mode     : PerformanceOnly
Samples per second: 3245.67
Result is : VALID
  Min duration satisfied : Yes
  Min queries satisfied : Yes
================================================

Latency Statistics (ms)
================================================
Mean latency: 28.45
Median latency: 27.89
50.00 percentile latency: 27.89
90.00 percentile latency: 32.14
95.00 percentile latency: 34.56
97.00 percentile latency: 36.12
99.00 percentile latency: 39.87
99.90 percentile latency: 45.23
================================================
```

### Result Parser

```python
# mlperf_result_parser.py
import re
from pathlib import Path
from typing import Dict, Optional

class MLPerfResultParser:
    @staticmethod
    def parse_summary_file(summary_path: str) -> Dict:
        """Parse MLPerf summary file."""
        with open(summary_path, 'r') as f:
            content = f.read()

        results = {
            "valid": False,
            "scenario": None,
            "throughput": None,
            "latency": {}
        }

        # Extract SUT name
        match = re.search(r"SUT name\s*:\s*(.+)", content)
        if match:
            results["sut_name"] = match.group(1).strip()

        # Extract scenario
        match = re.search(r"Scenario\s*:\s*(\w+)", content)
        if match:
            results["scenario"] = match.group(1)

        # Extract throughput
        match = re.search(r"Samples per second:\s*([\d.]+)", content)
        if match:
            results["throughput"] = float(match.group(1))

        # Extract validity
        match = re.search(r"Result is\s*:\s*(\w+)", content)
        if match:
            results["valid"] = (match.group(1) == "VALID")

        # Extract latency statistics
        latency_patterns = {
            "mean": r"Mean latency:\s*([\d.]+)",
            "median": r"Median latency:\s*([\d.]+)",
            "p50": r"50\.00 percentile latency:\s*([\d.]+)",
            "p90": r"90\.00 percentile latency:\s*([\d.]+)",
            "p95": r"95\.00 percentile latency:\s*([\d.]+)",
            "p99": r"99\.00 percentile latency:\s*([\d.]+)",
            "p99.9": r"99\.90 percentile latency:\s*([\d.]+)"
        }

        for key, pattern in latency_patterns.items():
            match = re.search(pattern, content)
            if match:
                results["latency"][key] = float(match.group(1))

        return results

    @staticmethod
    def parse_accuracy_file(accuracy_path: str) -> Dict:
        """Parse MLPerf accuracy file."""
        with open(accuracy_path, 'r') as f:
            content = f.read()

        accuracy = {}

        # Extract accuracy percentage
        match = re.search(r"accuracy=(\d+\.?\d*)%", content)
        if match:
            accuracy["percentage"] = float(match.group(1))

        return accuracy

    @staticmethod
    def generate_report(results_dir: str) -> Dict:
        """Generate comprehensive report from results directory."""
        results_path = Path(results_dir)

        report = {
            "benchmark": results_path.name,
            "timestamp": results_path.stat().st_mtime,
            "performance": None,
            "accuracy": None
        }

        # Parse performance results
        summary_file = results_path / "mlperf_log_summary.txt"
        if summary_file.exists():
            report["performance"] = MLPerfResultParser.parse_summary_file(str(summary_file))

        # Parse accuracy results
        accuracy_file = results_path / "mlperf_log_accuracy.json"
        if accuracy_file.exists():
            report["accuracy"] = MLPerfResultParser.parse_accuracy_file(str(accuracy_file))

        return report


# Example usage
if __name__ == "__main__":
    parser = MLPerfResultParser()

    # Parse results
    report = parser.generate_report("/results/mlperf_20251014/resnet50_offline")

    print(f"Benchmark: {report['benchmark']}")
    print(f"Valid: {report['performance']['valid']}")
    print(f"Throughput: {report['performance']['throughput']:.0f} samples/sec")
    print(f"P99 Latency: {report['performance']['latency']['p99']:.2f} ms")
    if report['accuracy']:
        print(f"Accuracy: {report['accuracy']['percentage']:.2f}%")
```

---

## Integration Examples

### Complete Marketplace Integration

```python
# marketplace_mlperf.py
from typing import Dict, List
import json
from pathlib import Path

class MarketplaceMLPerfIntegration:
    def __init__(self, data_root: str = "/data/mlperf"):
        self.dataset_manager = MLPerfDatasetManager(data_root)
        self.result_parser = MLPerfResultParser()

    def benchmark_provider(
        self,
        provider_id: str,
        hardware_specs: Dict,
        scenario: str = "Offline"
    ) -> Dict:
        """
        Run MLPerf benchmarks for provider verification.

        Args:
            provider_id: Provider identifier
            hardware_specs: Hardware capabilities
            scenario: MLPerf scenario

        Returns:
            Benchmark report
        """
        # Select appropriate benchmarks
        selector = MLPerfBenchmarkSelector()
        benchmarks = selector.select_benchmarks(hardware_specs)

        print(f"Selected benchmarks for {provider_id}: {benchmarks}")

        # Setup datasets
        self.dataset_manager.setup_all_datasets(benchmarks)

        # Run benchmarks
        results = {}
        for benchmark in benchmarks:
            print(f"\nRunning {benchmark}...")
            result = self._run_single_benchmark(provider_id, benchmark, scenario)
            results[benchmark] = result

        # Generate report
        report = {
            "provider_id": provider_id,
            "hardware_specs": hardware_specs,
            "benchmarks": results,
            "verdict": self._determine_verdict(results, hardware_specs)
        }

        # Save report
        report_file = f"/results/{provider_id}_mlperf_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        return report

    def _run_single_benchmark(
        self,
        provider_id: str,
        benchmark: str,
        scenario: str
    ) -> Dict:
        """Run single benchmark."""
        # Implementation depends on benchmark
        # This is a simplified example

        if benchmark == "resnet50":
            runner = ResNet50Runner(
                model_path=f"/data/mlperf/models/resnet50/resnet50.pth",
                dataset_path="/data/mlperf/datasets/imagenet/val"
            )
        elif benchmark == "bert":
            runner = BERTRunner(
                model_path="/data/mlperf/models/bert/bert-large.pth",
                dataset_path="/data/mlperf/datasets/squad"
            )
        else:
            raise ValueError(f"Unknown benchmark: {benchmark}")

        results = runner.run_benchmark(
            duration_ms=60000,
            output_dir=f"/results/{provider_id}/{benchmark}"
        )

        return results

    def _determine_verdict(
        self,
        results: Dict,
        hardware_specs: Dict
    ) -> Dict:
        """Determine if provider meets requirements."""
        # Check if all benchmarks passed
        all_valid = all(
            result.get('valid', False)
            for result in results.values()
        )

        if not all_valid:
            return {
                "status": "FAILED",
                "reason": "One or more benchmarks invalid"
            }

        # Check throughput meets minimum requirements
        # (requirements depend on claimed hardware)

        return {
            "status": "PASSED",
            "summary": {
                benchmark: {
                    "throughput": result['throughput'],
                    "latency_p99": result['latency']['p99']
                }
                for benchmark, result in results.items()
            }
        }


# CLI
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python marketplace_mlperf.py <provider_id>")
        sys.exit(1)

    provider_id = sys.argv[1]

    hardware_specs = {
        "has_gpu": True,
        "gpu_memory_gb": 80,
        "cpu_cores": 64,
        "system_memory_gb": 256
    }

    integration = MarketplaceMLPerfIntegration()
    report = integration.benchmark_provider(provider_id, hardware_specs)

    print(f"\n=== Benchmark Report ===")
    print(f"Verdict: {report['verdict']['status']}")
```

---

## Troubleshooting

### Common Issues

#### 1. CUDA Out of Memory

**Solution**:
```bash
# Reduce batch size in config
# Enable gradient checkpointing
# Use mixed precision (FP16)

# Clear cache before running
python3 -c "import torch; torch.cuda.empty_cache()"
```

#### 2. Dataset Not Found

**Solution**:
```bash
# Verify dataset paths
export DATA_DIR=/data/mlperf/datasets
ls -la ${DATA_DIR}/imagenet/val

# Re-download if necessary
python3 dataset_manager.py --download resnet50
```

#### 3. Low Throughput

**Solution**:
```bash
# Check GPU utilization
nvidia-smi dmon -s u

# Enable performance mode
sudo nvidia-smi -pm 1
sudo nvidia-smi -lgc 1410,1410

# Use TensorRT optimization
python3 tensorrt_optimizer.py --model resnet50
```

---

## References

- [MLCommons Official Site](https://mlcommons.org/)
- [MLPerf Inference GitHub](https://github.com/mlcommons/inference)
- [MLPerf Rules](https://github.com/mlcommons/inference_policies/blob/master/inference_rules.adoc)
- [NVIDIA MLPerf Guide](https://developer.nvidia.com/blog/nvidia-blackwell-ultra-sets-new-inference-records-in-mlperf-debut/)
- [AMD MLPerf Submission Guide](https://rocm.blogs.amd.com/artificial-intelligence/reproducing-amd-mlperf-inference-submission/README.html)
