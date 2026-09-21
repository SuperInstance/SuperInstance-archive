# gVisor Integration Guide

## Overview

gVisor is an application kernel written in Go that provides an additional layer of isolation between running applications and the host operating system. Unlike traditional VMs or containers, gVisor implements a significant portion of the Linux system interface in userspace, providing strong isolation while maintaining container-like resource efficiency.

**Key Benefits:**
- Strong isolation without VM overhead
- GPU support via nvproxy (NVIDIA GPUs)
- Compatible with Docker and Kubernetes
- Minimal performance overhead for most workloads

**Estimated Implementation Time**: 1-2 weeks
**Required Skills**: Container runtime administration, Linux systems, Docker/Kubernetes, GPU management (for GPU workloads)

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Docker Integration](#docker-integration)
5. [Containerd Integration](#containerd-integration)
6. [GPU Support with nvproxy](#gpu-support-with-nvproxy)
7. [Kubernetes Integration](#kubernetes-integration)
8. [Configuration Options](#configuration-options)
9. [Performance Considerations](#performance-considerations)
10. [Troubleshooting](#troubleshooting)
11. [References](#references)

---

## Architecture Overview

### How gVisor Works

```
┌─────────────────────────────────────────────────┐
│            Application Container                │
│  ┌─────────────────────────────────────────┐   │
│  │       Application Process               │   │
│  │    (syscalls intercepted by gVisor)     │   │
│  └─────────────────┬───────────────────────┘   │
│                    │ System Calls               │
│  ┌─────────────────▼───────────────────────┐   │
│  │          Sentry (gVisor Kernel)         │   │
│  │     (Implements Linux syscall API)      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌────────┐│   │
│  │  │ VFS      │  │ Network  │  │ nvproxy││   │
│  │  │ Gofer    │  │ Stack    │  │ (GPU)  ││   │
│  │  └──────────┘  └──────────┘  └────────┘│   │
│  └─────────────────┬───────────────────────┘   │
│                    │ Limited syscalls           │
└────────────────────┼───────────────────────────┘
                     │
         ┌───────────▼──────────────┐
         │     Host Linux Kernel    │
         │         (Minimal          │
         │      surface area)        │
         └──────────────────────────┘
```

**Components:**
- **Sentry**: Application kernel running in userspace
- **Gofer**: File system proxy for secure file access
- **runsc**: Runtime compatible with OCI (Docker/containerd)
- **nvproxy**: NVIDIA GPU driver proxy (for GPU workloads)

### Supported Platforms

- **Platform**: ptrace (default), kvm (better performance)
- **Architecture**: x86_64, ARM64
- **Container Runtimes**: Docker, containerd, CRI-O
- **Orchestrators**: Kubernetes, Nomad

---

## Prerequisites

### System Requirements

```bash
# Check kernel version (minimum 4.14, recommended 5.10+)
uname -r

# Verify KVM support (if using KVM platform)
lsmod | grep kvm
[ -r /dev/kvm ] && [ -w /dev/kvm ] && echo "KVM available" || echo "KVM not available"

# Check CPU features
lscpu | grep -i virtualization
```

### Install Dependencies

**Ubuntu/Debian:**

```bash
sudo apt-get update
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg
```

**RHEL/CentOS/Fedora:**

```bash
sudo dnf install -y \
    ca-certificates \
    curl \
    gnupg
```

---

## Installation

### Method 1: Install from Official Repository (Recommended)

**Ubuntu/Debian:**

```bash
# Add gVisor repository
curl -fsSL https://gvisor.dev/archive.key | sudo gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" | sudo tee /etc/apt/sources.list.d/gvisor.list > /dev/null

# Update and install
sudo apt-get update
sudo apt-get install -y runsc
```

**RHEL/CentOS/Fedora:**

```bash
# Add gVisor repository
cat <<EOF | sudo tee /etc/yum.repos.d/gvisor.repo
[gvisor]
name=gVisor
baseurl=https://storage.googleapis.com/gvisor/releases/release/rpm/\$basearch
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://gvisor.dev/archive.key
EOF

# Install
sudo dnf install -y runsc
```

### Method 2: Manual Download

```bash
# Determine architecture
ARCH=$(uname -m)

# Download latest release
(
  set -e
  RUNSC_URL=https://storage.googleapis.com/gvisor/releases/release/latest/${ARCH}
  wget ${RUNSC_URL}/runsc
  wget ${RUNSC_URL}/runsc.sha512
  wget ${RUNSC_URL}/containerd-shim-runsc-v1
  wget ${RUNSC_URL}/containerd-shim-runsc-v1.sha512

  # Verify checksums
  sha512sum -c runsc.sha512
  sha512sum -c containerd-shim-runsc-v1.sha512

  # Install binaries
  chmod +x runsc containerd-shim-runsc-v1
  sudo mv runsc /usr/local/bin/
  sudo mv containerd-shim-runsc-v1 /usr/local/bin/
)
```

### Verify Installation

```bash
# Check runsc version
runsc --version

# Expected output:
# runsc version release-20250101.0
# spec: 1.1.0-rc.1
```

---

## Docker Integration

### Configure Docker to Use runsc

**Step 1: Install Docker (if not already installed)**

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
```

**Step 2: Configure runsc Runtime**

```bash
# Register runsc with Docker
sudo runsc install

# Verify installation
docker info | grep -i runtime
```

Alternative manual configuration:

```bash
# Edit Docker daemon config
sudo tee /etc/docker/daemon.json <<EOF
{
  "runtimes": {
    "runsc": {
      "path": "/usr/local/bin/runsc",
      "runtimeArgs": [
        "--platform=ptrace"
      ]
    }
  }
}
EOF

# Restart Docker
sudo systemctl restart docker
```

**Step 3: Run Container with gVisor**

```bash
# Run container with runsc runtime
docker run --runtime=runsc hello-world

# Run interactive container
docker run --runtime=runsc -it ubuntu bash

# Inside container, verify you're in gVisor
uname -a
# Should show modified kernel information
```

### Docker Compose Integration

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    image: nginx:latest
    runtime: runsc
    ports:
      - "8080:80"
    volumes:
      - ./html:/usr/share/nginx/html:ro
```

Run with:

```bash
docker-compose up -d
```

---

## Containerd Integration

Containerd is the recommended runtime for production Kubernetes deployments.

### Install Containerd

**Ubuntu/Debian:**

```bash
sudo apt-get install -y containerd

# Create default configuration
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml
```

### Configure runsc with Containerd

**Step 1: Edit Containerd Configuration**

```bash
sudo nano /etc/containerd/config.toml
```

**Step 2: Add runsc Runtime**

For containerd 2.x (version 3 config):

```toml
version = 3

[plugins."io.containerd.grpc.v1.cri".containerd]
  [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
    runtime_type = "io.containerd.runc.v2"

  [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runsc]
    runtime_type = "io.containerd.runsc.v1"

    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runsc.options]
      TypeUrl = "io.containerd.runsc.v1.options"
      ConfigPath = "/etc/containerd/runsc.toml"
```

For containerd 1.x (version 2 config):

```toml
version = 2

[plugins."io.containerd.grpc.v1.cri".containerd]
  [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
    runtime_type = "io.containerd.runc.v2"

  [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runsc]
    runtime_type = "io.containerd.runsc.v1"
```

**Step 3: Create runsc Configuration (Optional)**

```bash
sudo tee /etc/containerd/runsc.toml <<EOF
[runsc_config]
  platform = "ptrace"
  debug_log = "/var/log/runsc/"
  file_access = "shared"
  network = "sandbox"
EOF
```

**Step 4: Restart Containerd**

```bash
sudo systemctl restart containerd

# Verify
sudo ctr version
```

**Step 5: Test with ctr**

```bash
# Pull image
sudo ctr image pull docker.io/library/nginx:latest

# Run with runsc
sudo ctr run --runtime io.containerd.runsc.v1 \
  docker.io/library/nginx:latest \
  test-nginx

# Check running containers
sudo ctr containers ls

# Cleanup
sudo ctr tasks kill test-nginx
sudo ctr containers rm test-nginx
```

---

## GPU Support with nvproxy

nvproxy enables NVIDIA GPU access in gVisor-sandboxed containers.

### Prerequisites

**Host Requirements:**
- NVIDIA GPU (compute capability 3.5+)
- NVIDIA drivers installed (version 515+)
- CUDA toolkit (optional, for testing)

**Verify GPU:**

```bash
# Check NVIDIA driver
nvidia-smi

# Verify device nodes
ls -l /dev/nvidia*
```

### Supported GPU Models

As of 2025, nvproxy supports:
- NVIDIA Ampere (A100, A30, A10, etc.)
- NVIDIA Hopper (H100, H200)
- NVIDIA Ada Lovelace (L40, L4)
- Select GeForce RTX 30/40 series
- NVIDIA Tesla T4, V100

Check current compatibility:
```bash
# Visit https://gvisor.dev/docs/user_guide/gpu/
```

### Enable nvproxy with Docker

**Step 1: Install NVIDIA Container Toolkit**

```bash
# Add NVIDIA repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sudo tee /etc/apt/sources.list.d/libnvidia-container.list

# Install toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
```

**Step 2: Configure runsc with nvproxy**

```bash
# Install runsc with GPU support
sudo runsc install --nvproxy=true --nvproxy-docker=true

# Or manually configure Docker daemon
sudo tee /etc/docker/daemon.json <<EOF
{
  "runtimes": {
    "runsc": {
      "path": "/usr/local/bin/runsc",
      "runtimeArgs": [
        "--nvproxy",
        "--nvproxy-docker"
      ]
    }
  }
}
EOF

# Restart Docker
sudo systemctl restart docker
```

**Step 3: Run GPU Container**

```bash
# Run with GPU access
docker run --runtime=runsc --gpus all nvidia/cuda:12.0-base nvidia-smi

# Run specific GPU
docker run --runtime=runsc --gpus '"device=0"' nvidia/cuda:12.0-base nvidia-smi

# Run with resource limits
docker run --runtime=runsc --gpus all \
  -e NVIDIA_VISIBLE_DEVICES=0 \
  -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
  nvidia/cuda:12.0-base \
  nvidia-smi
```

### Enable nvproxy with Containerd

**Step 1: Configure runsc**

```bash
sudo tee /etc/containerd/runsc.toml <<EOF
[runsc_config]
  platform = "systrap"
  nvproxy = true
  nvproxy-docker = false
  nvproxy-allowed-driver-capabilities = "compute,utility"
EOF
```

**Step 2: Update Containerd Configuration**

```toml
# /etc/containerd/config.toml
version = 3

[plugins."io.containerd.grpc.v1.cri".containerd]
  [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runsc-gpu]
    runtime_type = "io.containerd.runsc.v1"

    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runsc-gpu.options]
      TypeUrl = "io.containerd.runsc.v1.options"
      ConfigPath = "/etc/containerd/runsc.toml"
```

**Step 3: Restart and Test**

```bash
sudo systemctl restart containerd

# Run container with GPU
sudo ctr run --runtime io.containerd.runsc.v1 \
  --device /dev/nvidia0 \
  --device /dev/nvidia-uvm \
  --device /dev/nvidiactl \
  docker.io/nvidia/cuda:12.0-base \
  gpu-test \
  nvidia-smi
```

### nvproxy Driver Capabilities

Configure allowed GPU features:

```bash
# Available capabilities:
# - compute: CUDA/OpenCL compute
# - utility: nvidia-smi
# - graphics: OpenGL/Vulkan
# - video: Video encode/decode
# - display: X11/Wayland display

# Configure in runsc
runsc --nvproxy \
      --nvproxy-allowed-driver-capabilities=compute,utility,graphics,video \
      ...
```

### Testing GPU Workloads

**CUDA Test:**

```bash
docker run --runtime=runsc --gpus all nvidia/cuda:12.0-base \
  bash -c 'echo "GPU Test"; nvidia-smi'
```

**PyTorch Test:**

```bash
docker run --runtime=runsc --gpus all \
  pytorch/pytorch:latest \
  python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'GPU Count: {torch.cuda.device_count()}')"
```

**TensorFlow Test:**

```bash
docker run --runtime=runsc --gpus all \
  tensorflow/tensorflow:latest-gpu \
  python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

### Limitations

Current nvproxy limitations (as of 2025):
- No support for MIG (Multi-Instance GPU)
- Limited support for multi-GPU setups
- No direct rendering/display output
- Some CUDA features may not work (check documentation)

---

## Kubernetes Integration

### RuntimeClass Setup

**Step 1: Install gVisor on All Nodes**

```bash
# On each worker node
sudo apt-get install -y runsc

# Configure containerd (see Containerd Integration section)
```

**Step 2: Create RuntimeClass**

```yaml
# runtime-class-runsc.yaml
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: gvisor
handler: runsc
```

Apply:

```bash
kubectl apply -f runtime-class-runsc.yaml
```

**Step 3: Create RuntimeClass for GPU**

```yaml
# runtime-class-runsc-gpu.yaml
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: gvisor-gpu
handler: runsc-gpu
```

Apply:

```bash
kubectl apply -f runtime-class-runsc-gpu.yaml
```

### Deploy Workloads

**Example: Basic Pod**

```yaml
# pod-gvisor.yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx-gvisor
spec:
  runtimeClassName: gvisor
  containers:
  - name: nginx
    image: nginx:latest
    ports:
    - containerPort: 80
```

**Example: GPU Pod**

```yaml
# pod-gpu-gvisor.yaml
apiVersion: v1
kind: Pod
metadata:
  name: cuda-gvisor
spec:
  runtimeClassName: gvisor-gpu
  containers:
  - name: cuda
    image: nvidia/cuda:12.0-base
    command: ["nvidia-smi"]
    resources:
      limits:
        nvidia.com/gpu: 1
```

**Example: Deployment**

```yaml
# deployment-gvisor.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      runtimeClassName: gvisor
      containers:
      - name: app
        image: myapp:latest
        ports:
        - containerPort: 8080
```

Deploy:

```bash
kubectl apply -f deployment-gvisor.yaml
kubectl get pods -l app=web
```

### Node Selector for GPU Nodes

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-workload
spec:
  runtimeClassName: gvisor-gpu
  nodeSelector:
    accelerator: nvidia-gpu
  containers:
  - name: training
    image: pytorch/pytorch:latest
    resources:
      limits:
        nvidia.com/gpu: 2
```

---

## Configuration Options

### Platform Options

```bash
# ptrace (default): Most compatible, slower
runsc --platform=ptrace run <container>

# systrap: Better performance than ptrace
runsc --platform=systrap run <container>

# kvm: Best performance, requires KVM
runsc --platform=kvm run <container>
```

### File Access Modes

```bash
# exclusive: Each container has isolated filesystem (default)
runsc --file-access=exclusive run <container>

# shared: Better performance for read-heavy workloads
runsc --file-access=shared run <container>
```

### Network Options

```bash
# sandbox: Isolated network stack (default)
runsc --network=sandbox run <container>

# host: Use host network (less isolation)
runsc --network=host run <container>
```

### Debug Options

```bash
# Enable debug logging
runsc --debug --debug-log=/tmp/runsc.log run <container>

# Verbose system call logging
runsc --strace --log-fd=2 run <container>
```

### Complete Configuration File

```bash
# /etc/runsc/config.toml
[runsc_config]
  # Performance
  platform = "systrap"
  file_access = "shared"
  network = "sandbox"

  # GPU
  nvproxy = true
  nvproxy-docker = true
  nvproxy-allowed-driver-capabilities = "compute,utility,graphics"

  # Debugging
  debug = false
  debug_log = "/var/log/runsc/"
  strace = false

  # Resource limits
  num_network_channels = 1
  total_host_memory = 8589934592  # 8GB in bytes
```

---

## Performance Considerations

### Benchmarks (Relative to Native)

| Workload Type        | ptrace | systrap | kvm  |
|---------------------|--------|---------|------|
| CPU-bound           | 90%    | 95%     | 98%  |
| Network I/O         | 75%    | 85%     | 90%  |
| Disk I/O            | 80%    | 85%     | 88%  |
| System call heavy   | 50%    | 70%     | 85%  |
| GPU compute (CUDA)  | 95%    | 95%     | 95%  |

### Optimization Tips

**1. Use systrap or kvm Platform**

```bash
# Better performance than ptrace
runsc --platform=systrap run <container>
```

**2. Enable Shared File Access**

```bash
# For read-heavy workloads
runsc --file-access=shared run <container>
```

**3. Disable Debug Logging**

```bash
# In production
runsc --debug=false run <container>
```

**4. Use Host Network (when appropriate)**

```bash
# Less isolation but better performance
runsc --network=host run <container>
```

**5. GPU Workloads**

```bash
# Use systrap for GPU workloads
runsc --platform=systrap --nvproxy run <container>
```

### When to Use gVisor

**Good fit:**
- Multi-tenant environments
- Untrusted code execution
- Serverless/FaaS platforms
- Microservices with moderate I/O
- GPU compute workloads (CUDA/ML)

**Not ideal for:**
- Very high syscall rate workloads
- Latency-sensitive applications (<1ms requirements)
- Legacy applications with unusual syscalls
- Workloads requiring kernel modules

---

## Troubleshooting

### Common Issues

**Issue 1: runsc not found**

```bash
# Verify installation
which runsc

# Check PATH
echo $PATH

# Reinstall if needed
sudo apt-get install --reinstall runsc
```

**Issue 2: Permission Denied**

```bash
# Check user groups
groups

# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in
```

**Issue 3: Container Fails to Start**

```bash
# Check logs
docker logs <container_id>

# Enable debug logging
docker run --runtime=runsc --rm \
  --runtime-config-flags="--debug --debug-log=/tmp/runsc/" \
  ubuntu echo "test"

# View runsc logs
cat /tmp/runsc/*.log
```

**Issue 4: GPU Not Detected**

```bash
# Verify NVIDIA driver
nvidia-smi

# Check device permissions
ls -l /dev/nvidia*

# Verify nvproxy is enabled
docker info | grep nvproxy

# Test GPU access
docker run --runtime=runsc --gpus all nvidia/cuda:12.0-base nvidia-smi
```

**Issue 5: Network Issues**

```bash
# Test with host network
docker run --runtime=runsc --network=host alpine ping -c 3 google.com

# Check DNS
docker run --runtime=runsc alpine cat /etc/resolv.conf

# Verify iptables rules
sudo iptables -L -n
```

### Debug Commands

```bash
# Inspect runsc configuration
runsc --help

# Check runtime status
docker info | grep -A 20 Runtimes

# List containers with runtime
docker ps --filter "runtime=runsc"

# Attach to running container
docker exec -it <container_id> bash

# View system calls
runsc --strace --log-fd=2 run <container>
```

### Logging

```bash
# Enable comprehensive logging
mkdir -p /var/log/runsc
chmod 777 /var/log/runsc

# Configure in daemon.json
{
  "runtimes": {
    "runsc": {
      "path": "/usr/local/bin/runsc",
      "runtimeArgs": [
        "--debug",
        "--debug-log=/var/log/runsc/"
      ]
    }
  }
}

# View logs
tail -f /var/log/runsc/*.log
```

---

## References

### Official Documentation
- **gVisor Website**: https://gvisor.dev/
- **Installation Guide**: https://gvisor.dev/docs/user_guide/install/
- **GPU Support**: https://gvisor.dev/docs/user_guide/gpu/
- **Containerd Quick Start**: https://gvisor.dev/docs/user_guide/containerd/quick_start/
- **GitHub Repository**: https://github.com/google/gvisor

### Tutorials
- **DevOps Tales (2025)**: https://devopstales.github.io/kubernetes/gvisor-containerd/
- **Xelon Guide**: https://www.xelon.ch/knowledge-base/install-gvisor-on-kubernetes-cluster
- **Medium - Kubernetes Integration**: https://medium.com/@GiteshWadhwa/securing-kubernetes-workloads-implementing-gvisor-runtime-class-with-containerd

### GPU/nvproxy Resources
- **nvproxy Design Doc**: https://github.com/google/gvisor/blob/master/g3doc/proposals/nvidia_driver_proxy.md
- **Running Stable Diffusion**: https://gvisor.dev/blog/2023/06/20/gpu-pytorch-stable-diffusion/
- **nvproxy Package Docs**: https://pkg.go.dev/gvisor.dev/gvisor/pkg/sentry/devices/nvproxy

### Container Runtime Specs
- **OCI Runtime Spec**: https://github.com/opencontainers/runtime-spec
- **Containerd Documentation**: https://containerd.io/docs/
- **Docker Runtime Options**: https://docs.docker.com/engine/reference/commandline/dockerd/#daemon-configuration-file

---

## Team Requirements

**Container Platform Engineer** (Primary, 30 hours/week):
- Docker/Kubernetes expertise
- Container runtime configuration
- Linux containers and namespaces

**DevOps Engineer** (Secondary, 20 hours/week):
- CI/CD pipeline integration
- Deployment automation
- Monitoring and logging

**GPU/ML Engineer** (For GPU workloads, 10 hours/week):
- CUDA/GPU programming
- ML framework experience (PyTorch/TensorFlow)
- GPU driver management

**Total Estimated Effort**: 1-2 weeks for basic integration, additional 1 week for GPU setup

---

*Last Updated: 2025-10-14*
*Version: 1.0*
