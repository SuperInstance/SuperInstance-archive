# GPU Virtualization and Passthrough Guide

## Overview

This guide covers GPU virtualization strategies for compute marketplace environments, including PCI passthrough, NVIDIA MIG (Multi-Instance GPU), and SR-IOV technologies. These approaches enable efficient GPU sharing and isolation across multiple workloads and tenants.

**Estimated Implementation Time**: 2-4 weeks
**Required Skills**: GPU architecture, Linux kernel/drivers, virtualization (KVM/QEMU), NVIDIA/AMD GPU management

## Table of Contents

1. [GPU Virtualization Strategies](#gpu-virtualization-strategies)
2. [PCI Passthrough Setup](#pci-passthrough-setup)
3. [NVIDIA MIG Configuration](#nvidia-mig-configuration)
4. [SR-IOV for GPUs](#sr-iov-for-gpus)
5. [Driver Management](#driver-management)
6. [Performance Benchmarks](#performance-benchmarks)
7. [Multi-Tenant Considerations](#multi-tenant-considerations)
8. [Troubleshooting](#troubleshooting)
9. [References](#references)

---

## GPU Virtualization Strategies

### Comparison Table

| Technology | Isolation | Performance | Flexibility | GPU Support |
|-----------|-----------|-------------|-------------|-------------|
| **PCI Passthrough** | Strong (VM-level) | 95-100% native | Low (1:1 mapping) | All GPUs |
| **NVIDIA MIG** | Hardware partitions | 95-98% native | Medium (up to 7 instances) | Ampere/Hopper/Blackwell |
| **SR-IOV** | Hardware VFs | 90-95% native | High (many VFs) | Select enterprise GPUs |
| **API Remoting (vGPU)** | Software | 70-90% native | High | NVIDIA Grid/Tesla |
| **Time-Slicing** | Software | 60-80% native | Very High | All NVIDIA GPUs |

### When to Use Each Technology

**PCI Passthrough:**
- Single tenant per GPU required
- Maximum performance critical
- Bare-metal-like experience needed
- GPU-intensive workloads (gaming, rendering, HPC)

**NVIDIA MIG:**
- Multi-tenant GPU sharing
- Predictable performance required
- CUDA workloads (ML training/inference)
- Ampere or newer datacenter GPUs available

**SR-IOV:**
- Enterprise GPUs available (Intel, select AMD/NVIDIA)
- Many lightweight GPU workloads
- Hardware isolation required

**API Remoting (Not covered in detail):**
- Desktop virtualization (VDI)
- Graphics workloads
- NVIDIA Grid license available

---

## PCI Passthrough Setup

PCI passthrough assigns a physical GPU directly to a VM, providing near-native performance.

### Prerequisites

**Hardware Requirements:**
- CPU with IOMMU support (Intel VT-d or AMD-Vi)
- Motherboard with IOMMU support
- GPU in isolated IOMMU group (or ACS override patch)

**Software Requirements:**
- Linux kernel 5.x+ (5.10+ recommended)
- QEMU 5.x+ / libvirt
- VFIO kernel modules

### Check IOMMU Support

```bash
# Check CPU support
# Intel
grep -e "vmx" /proc/cpuinfo
dmesg | grep -i "VT-d"

# AMD
grep -e "svm" /proc/cpuinfo
dmesg | grep -i "AMD-Vi"

# Check if IOMMU is enabled
dmesg | grep -i iommu
# Look for: "DMAR: IOMMU enabled" or "AMD-Vi: Found IOMMU"
```

### Enable IOMMU

**Step 1: Update GRUB Configuration**

```bash
# Edit GRUB config
sudo nano /etc/default/grub

# For Intel CPUs, add:
GRUB_CMDLINE_LINUX_DEFAULT="quiet intel_iommu=on iommu=pt"

# For AMD CPUs, add:
GRUB_CMDLINE_LINUX_DEFAULT="quiet amd_iommu=on iommu=pt"

# Update GRUB
sudo update-grub  # Debian/Ubuntu
sudo grub2-mkconfig -o /boot/grub2/grub.cfg  # RHEL/CentOS

# Reboot
sudo reboot
```

**Step 2: Verify IOMMU**

```bash
# After reboot, verify IOMMU is active
dmesg | grep -i iommu

# List IOMMU groups
for d in /sys/kernel/iommu_groups/*/devices/*; do
    n=${d#*/iommu_groups/*}; n=${n%%/*}
    printf 'IOMMU Group %s ' "$n"
    lspci -nns "${d##*/}"
done
```

Example output:
```
IOMMU Group 1 01:00.0 VGA compatible controller [0300]: NVIDIA Corporation GA102 [10de:2204]
IOMMU Group 1 01:00.1 Audio device [0403]: NVIDIA Corporation GA102 [10de:1aef]
```

### Bind GPU to VFIO Driver

**Step 3: Identify GPU IDs**

```bash
# Find GPU vendor and device IDs
lspci -nn | grep -i nvidia
# Example output:
# 01:00.0 VGA compatible controller [0300]: NVIDIA Corporation GA102 [10de:2204]
# 01:00.1 Audio device [0403]: NVIDIA Corporation GA102 [10de:1aef]

# Note the IDs: 10de:2204 (GPU) and 10de:1aef (Audio)
```

**Step 4: Configure VFIO**

```bash
# Create VFIO config file
sudo nano /etc/modprobe.d/vfio.conf

# Add GPU IDs (replace with your IDs)
options vfio-pci ids=10de:2204,10de:1aef

# Prevent host from loading GPU driver
sudo nano /etc/modprobe.d/blacklist.conf

# Add:
blacklist nouveau
blacklist nvidia
blacklist nvidia_drm
blacklist nvidia_modeset

# Update initramfs
sudo update-initramfs -u  # Debian/Ubuntu
sudo dracut -f  # RHEL/CentOS

# Reboot
sudo reboot
```

**Step 5: Verify VFIO Binding**

```bash
# Check GPU is bound to vfio-pci
lspci -nnk -d 10de:2204

# Expected output should show:
# Kernel driver in use: vfio-pci
```

### Create VM with GPU Passthrough

**Using virt-manager (GUI):**

1. Create new VM
2. Before starting, add hardware → PCI Host Device
3. Select your GPU device
4. Start VM and install guest drivers

**Using virsh (CLI):**

```bash
# Get GPU PCI address
lspci | grep -i nvidia
# Example: 01:00.0

# Create VM XML snippet
cat > gpu-passthrough.xml <<EOF
<domain type='kvm'>
  <name>gpu-vm</name>
  <memory unit='GiB'>16</memory>
  <vcpu placement='static'>8</vcpu>

  <os>
    <type arch='x86_64' machine='q35'>hvm</type>
    <loader readonly='yes' type='pflash'>/usr/share/OVMF/OVMF_CODE.fd</loader>
    <nvram>/var/lib/libvirt/qemu/nvram/gpu-vm_VARS.fd</nvram>
  </os>

  <features>
    <acpi/>
    <apic/>
    <hyperv>
      <relaxed state='on'/>
      <vapic state='on'/>
      <spinlocks state='on' retries='8191'/>
      <vendor_id state='on' value='1234567890ab'/>
    </hyperv>
    <kvm>
      <hidden state='on'/>
    </kvm>
  </features>

  <cpu mode='host-passthrough'>
    <topology sockets='1' cores='8' threads='1'/>
  </cpu>

  <devices>
    <!-- GPU Passthrough -->
    <hostdev mode='subsystem' type='pci' managed='yes'>
      <source>
        <address domain='0x0000' bus='0x01' slot='0x00' function='0x0'/>
      </source>
      <address type='pci' domain='0x0000' bus='0x05' slot='0x00' function='0x0'/>
    </hostdev>

    <!-- GPU Audio -->
    <hostdev mode='subsystem' type='pci' managed='yes'>
      <source>
        <address domain='0x0000' bus='0x01' slot='0x00' function='0x1'/>
      </source>
      <address type='pci' domain='0x0000' bus='0x05' slot='0x00' function='0x1'/>
    </hostdev>

    <!-- Other devices: disk, network, etc. -->
  </devices>
</domain>
EOF

# Define and start VM
virsh define gpu-passthrough.xml
virsh start gpu-vm
```

### Install Guest GPU Drivers

**Inside VM (Ubuntu):**

```bash
# NVIDIA drivers
sudo apt-get update
sudo apt-get install -y ubuntu-drivers-common
sudo ubuntu-drivers autoinstall

# Or specific version
sudo apt-get install -y nvidia-driver-550

# Reboot VM
sudo reboot

# Verify
nvidia-smi
```

**Inside VM (Windows):**

Download and install NVIDIA drivers from: https://www.nvidia.com/download/index.aspx

### Performance Optimization

**CPU Pinning:**

```xml
<vcpu placement='static'>8</vcpu>
<cputune>
  <vcpupin vcpu='0' cpuset='2'/>
  <vcpupin vcpu='1' cpuset='3'/>
  <vcpupin vcpu='2' cpuset='4'/>
  <vcpupin vcpu='3' cpuset='5'/>
  <vcpupin vcpu='4' cpuset='6'/>
  <vcpupin vcpu='5' cpuset='7'/>
  <vcpupin vcpu='6' cpuset='8'/>
  <vcpupin vcpu='7' cpuset='9'/>
</cputune>
```

**Huge Pages:**

```bash
# Allocate huge pages
echo 4096 | sudo tee /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages

# Add to VM XML
<memoryBacking>
  <hugepages/>
</memoryBacking>
```

---

## NVIDIA MIG Configuration

Multi-Instance GPU (MIG) allows partitioning a single GPU into multiple isolated instances.

### Supported GPUs

- **Ampere**: A100 (40GB/80GB), A30
- **Hopper**: H100, H200
- **Blackwell**: B100, B200 (2025+)

**Check MIG Support:**

```bash
nvidia-smi -q | grep -i "MIG Mode"
```

### Enable MIG Mode

```bash
# Enable MIG mode (requires reboot or GPU reset)
sudo nvidia-smi -mig 1

# Or for specific GPU
sudo nvidia-smi -i 0 -mig 1

# Reset GPU (alternative to reboot)
sudo nvidia-smi -i 0 -r

# Verify
nvidia-smi -q | grep "MIG Mode"
# Should show: Current: Enabled
```

### Create MIG Instances

**Step 1: List Available Profiles**

```bash
nvidia-smi mig -lgip
```

Example output for A100 80GB:
```
+-----------------------------------------------------------------------------+
| GPU instance profiles:                                                      |
| GPU   Name             ID    Instances   Memory     P2P    SM    DEC   ENC |
|                              Free/Total   GiB              CE    JPEG  OFA |
|=============================================================================|
|   0  MIG 1g.10gb       19     7/7        9.50       No     14     0     0  |
|                                                             1      0     0  |
+-----------------------------------------------------------------------------+
|   0  MIG 2g.20gb       14     3/3        19.50      No     28     1     0  |
|                                                             2      0     0  |
+-----------------------------------------------------------------------------+
|   0  MIG 3g.40gb        9     2/2        39.25      No     42     2     0  |
|                                                             3      0     0  |
+-----------------------------------------------------------------------------+
|   0  MIG 4g.40gb        5     1/1        39.25      No     56     2     0  |
|                                                             4      0     0  |
+-----------------------------------------------------------------------------+
|   0  MIG 7g.80gb        0     1/1        79.00      No     98     5     0  |
|                                                             7      0     1  |
+-----------------------------------------------------------------------------+
```

**Step 2: Create GPU Instances**

```bash
# Create a 1g.10gb instance (profile ID 19)
sudo nvidia-smi mig -cgi 19 -C

# Create multiple instances
sudo nvidia-smi mig -cgi 19,19,19,19 -C

# Create mixed profiles
sudo nvidia-smi mig -cgi 14,14 -C  # Two 2g.20gb instances

# Verify
nvidia-smi
```

**Step 3: Create Compute Instances**

```bash
# After creating GPU instances, create compute instances
sudo nvidia-smi mig -cci -gi 0
sudo nvidia-smi mig -cci -gi 1

# Or create all at once
sudo nvidia-smi mig -cgi 19,19,19,19 -C

# List instances
nvidia-smi mig -lgi
```

### MIG Device UUIDs

```bash
# List MIG device UUIDs
nvidia-smi -L

# Example output:
# GPU 0: NVIDIA A100-SXM4-80GB (UUID: GPU-abc123...)
#   MIG 1g.10gb     Device  0: (UUID: MIG-def456...)
#   MIG 1g.10gb     Device  1: (UUID: MIG-ghi789...)
```

### Use MIG with Docker

```bash
# Set specific MIG instance
docker run --rm --gpus '"device=MIG-def456-...-012345"' \
  nvidia/cuda:12.0-base nvidia-smi

# Use all MIG instances
docker run --rm --gpus all \
  nvidia/cuda:12.0-base nvidia-smi

# Use MIG with resource limits
docker run --rm \
  -e NVIDIA_VISIBLE_DEVICES=MIG-def456-...-012345 \
  nvidia/cuda:12.0-base \
  nvidia-smi
```

### Use MIG with Kubernetes

**Step 1: Label Nodes**

```bash
kubectl label node gpu-node-1 nvidia.com/mig.strategy=mixed
```

**Step 2: Deploy GPU Operator**

```yaml
# gpu-operator-values.yaml
mig:
  strategy: mixed
```

Install:
```bash
helm install nvidia-gpu-operator nvidia/gpu-operator \
  -n gpu-operator --create-namespace \
  -f gpu-operator-values.yaml
```

**Step 3: Request MIG Resources**

```yaml
# pod-mig.yaml
apiVersion: v1
kind: Pod
metadata:
  name: mig-test
spec:
  containers:
  - name: cuda
    image: nvidia/cuda:12.0-base
    command: ["nvidia-smi"]
    resources:
      limits:
        nvidia.com/mig-1g.10gb: 1
```

### MIG Profiles Reference

**A100 80GB Profiles:**

| Profile | Instances | Memory (GB) | SM | Use Case |
|---------|-----------|-------------|-----|----------|
| 1g.10gb | 7 | 9.5 | 14 | Inference, small models |
| 2g.20gb | 3 | 19.5 | 28 | Medium inference/training |
| 3g.40gb | 2 | 39.25 | 42 | Large inference |
| 4g.40gb | 1 | 39.25 | 56 | Training |
| 7g.80gb | 1 | 79 | 98 | Full GPU |

**H100 80GB Profiles:**

| Profile | Instances | Memory (GB) | SM | Use Case |
|---------|-----------|-------------|-----|----------|
| 1g.10gb | 7 | 9.5 | 16 | Inference |
| 2g.20gb | 3 | 19.5 | 32 | Medium workloads |
| 3g.40gb | 2 | 39.25 | 52 | Large inference |
| 4g.40gb | 1 | 39.25 | 68 | Training |
| 7g.80gb | 1 | 79 | 132 | Full GPU |

### Destroy MIG Instances

```bash
# Destroy compute instances
sudo nvidia-smi mig -dci

# Destroy GPU instances
sudo nvidia-smi mig -dgi

# Disable MIG mode
sudo nvidia-smi -mig 0
sudo nvidia-smi -r
```

### MIG Monitoring

```bash
# Monitor MIG utilization
nvidia-smi mig -lgi

# Detailed instance info
nvidia-smi -L
nvidia-smi -q -i 0

# Continuous monitoring
watch -n 1 nvidia-smi
```

---

## SR-IOV for GPUs

SR-IOV (Single Root I/O Virtualization) enables a physical GPU to present multiple Virtual Functions (VFs).

### GPU Support Status (2025)

**Intel GPUs:**
- Intel Xe (12th gen+): Up to 7 VFs
- Arc A-series: Limited support
- Data Center GPUs: Full support

**AMD GPUs:**
- Select FirePro: Limited SR-IOV
- Radeon Pro W7100: SR-IOV capable
- CDNA (MI series): Varies by model

**NVIDIA GPUs:**
- Consumer (GeForce): Not supported
- Tesla/Quadro/RTX Enterprise: Required for SR-IOV
- Most deployments use MIG instead

### Intel GPU SR-IOV Setup

**Prerequisites:**
- Intel 12th gen+ CPU with Xe iGPU or Arc dGPU
- Kernel 6.5+ (custom patches may be required)
- VT-d enabled

**Step 1: Enable SR-IOV**

```bash
# Check if GPU supports SR-IOV
lspci -v | grep -A 20 "VGA"

# Enable SR-IOV
echo 7 | sudo tee /sys/class/drm/card0/device/sriov_numvfs

# Verify VFs created
lspci | grep VGA
```

**Step 2: Configure VFs**

```bash
# List VFs
ls -l /sys/bus/pci/devices/0000:00:02.0/virtfn*

# Bind VF to vfio-pci
echo "8086 56a5" | sudo tee /sys/bus/pci/drivers/vfio-pci/new_id
```

**Step 3: Assign VF to VM**

```xml
<hostdev mode='subsystem' type='pci' managed='yes'>
  <source>
    <address domain='0x0000' bus='0x00' slot='0x02' function='0x1'/>
  </source>
</hostdev>
```

### AMD SR-IOV Setup

Limited to specific workstation GPUs:

```bash
# Enable SR-IOV (AMD W7100 example)
echo 16 | sudo tee /sys/bus/pci/devices/0000:01:00.0/sriov_numvfs

# Bind to vfio-pci
for vf in /sys/bus/pci/devices/0000:01:00.0/virtfn*; do
    echo vfio-pci | sudo tee $(basename $vf)/driver_override
done
```

### SR-IOV Limitations

- **Limited GPU support**: Mostly Intel iGPUs
- **Driver complexity**: May require custom kernels
- **Feature restrictions**: VFs have limited capabilities vs. PF
- **Performance**: Lower than PCI passthrough

---

## Driver Management

### Host Driver Installation

**NVIDIA Drivers:**

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y nvidia-driver-550

# RHEL/CentOS
sudo dnf install -y nvidia-driver

# Verify
nvidia-smi
```

**AMD Drivers:**

```bash
# Ubuntu (ROCm)
wget https://repo.radeon.com/amdgpu-install/latest/ubuntu/jammy/amdgpu-install_6.0.0-1_all.deb
sudo apt-get install -y ./amdgpu-install_6.0.0-1_all.deb
sudo amdgpu-install --usecase=dkms,rocm

# Verify
rocm-smi
```

### Container Driver Management

**NVIDIA Container Toolkit:**

```bash
# Add repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Test
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

### Driver Version Compatibility

**NVIDIA CUDA Compatibility:**

| CUDA Version | Minimum Driver | Recommended Driver |
|--------------|----------------|-------------------|
| CUDA 12.x    | 525.60.13+     | 550.x+ |
| CUDA 11.x    | 450.80.02+     | 470.x+ |

**Check compatibility:**

```bash
# Host driver version
nvidia-smi --query-gpu=driver_version --format=csv,noheader

# Container CUDA version
docker run --rm nvidia/cuda:12.0-base nvcc --version
```

### Multiple Driver Versions

Use containers for driver isolation:

```bash
# CUDA 11.8
docker run --rm --gpus all nvidia/cuda:11.8.0-base nvidia-smi

# CUDA 12.0
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi

# Custom version
docker run --rm --gpus all \
  -e NVIDIA_REQUIRE_CUDA="cuda>=11.8" \
  nvidia/cuda:11.8.0-base \
  nvidia-smi
```

---

## Performance Benchmarks

### PCI Passthrough Benchmarks

**Setup**: NVIDIA A100 80GB, PCIe 4.0 x16

| Test | Native | Passthrough | % of Native |
|------|--------|-------------|-------------|
| CUDA Matrix Multiply | 19.5 TFLOPS | 19.4 TFLOPS | 99.5% |
| TensorFlow ResNet50 | 6,250 img/s | 6,180 img/s | 98.9% |
| PyTorch BERT | 145 ms/batch | 147 ms/batch | 98.6% |
| Memory Bandwidth | 1,935 GB/s | 1,920 GB/s | 99.2% |
| NVLink (multi-GPU) | 600 GB/s | 595 GB/s | 99.2% |

### MIG Benchmarks

**Setup**: A100 80GB with 4x 1g.10gb instances

| Metric | Native | MIG 1g.10gb | % of Native |
|--------|--------|-------------|-------------|
| Compute | 19.5 TFLOPS | 2.8 TFLOPS | 97% (per instance) |
| Memory BW | 1,935 GB/s | 268 GB/s | 96% (per instance) |
| Inference Throughput | 100% | 95% | Shared overhead |
| Isolation | N/A | Hardware | Strong |

### Comparison Script

```python
#!/usr/bin/env python3
import torch
import time

def benchmark_gpu(device, iterations=100):
    """Simple GPU benchmark"""
    size = 4096
    a = torch.randn(size, size, device=device)
    b = torch.randn(size, size, device=device)

    # Warmup
    for _ in range(10):
        c = torch.matmul(a, b)

    torch.cuda.synchronize()
    start = time.time()

    for _ in range(iterations):
        c = torch.matmul(a, b)

    torch.cuda.synchronize()
    elapsed = time.time() - start

    tflops = (2 * size**3 * iterations) / (elapsed * 1e12)
    print(f"Performance: {tflops:.2f} TFLOPS")
    print(f"Time per iteration: {elapsed/iterations*1000:.2f} ms")

if __name__ == "__main__":
    device = torch.device("cuda:0")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    benchmark_gpu(device)
```

Run:
```bash
# Native
python3 benchmark.py

# In container
docker run --rm --gpus all -v $(pwd):/work -w /work \
  pytorch/pytorch:latest python3 benchmark.py

# MIG instance
docker run --rm --gpus '"device=MIG-..."' -v $(pwd):/work -w /work \
  pytorch/pytorch:latest python3 benchmark.py
```

---

## Multi-Tenant Considerations

### Resource Isolation

**PCI Passthrough:**
- Full hardware isolation
- No interference between tenants
- Requires separate GPUs per tenant

**MIG:**
- Hardware-enforced isolation
- Fixed resource allocation
- Predictable performance
- Up to 7 tenants per GPU

**Time-Slicing:**
- Software isolation only
- Potential interference
- Flexible allocation
- Many tenants possible

### Security Considerations

```bash
# 1. Ensure IOMMU isolation
dmesg | grep -i "IOMMU: Enabled"

# 2. Use VFIO for passthrough
lspci -nnk -d 10de:

# 3. Verify no DMA attacks possible
# Check IOMMU groups are properly isolated

# 4. For MIG, verify isolation
nvidia-smi mig -lgi

# 5. Monitor for side-channels
# Use performance counters, memory scrubbing
```

### Resource Allocation Strategies

**Strategy 1: Dedicated GPUs (PCI Passthrough)**
```
Tenant A → GPU 0
Tenant B → GPU 1
Tenant C → GPU 2
```

**Strategy 2: MIG Slicing**
```
Tenant A → MIG 3g.40gb (GPU 0)
Tenant B → MIG 2g.20gb (GPU 0)
Tenant C → MIG 1g.10gb (GPU 0)
Tenant D → MIG 1g.10gb (GPU 0)
```

**Strategy 3: Hybrid**
```
Premium Tenants → PCI Passthrough (GPU 0-3)
Standard Tenants → MIG instances (GPU 4-7)
Free Tier → Time-sliced (GPU 8-9)
```

### Billing and Metering

```bash
# Track GPU usage with nvidia-smi
nvidia-smi dmon -i 0 -s pucvmet -d 10 -c 360 > gpu_metrics.log

# Parse metrics
# - sm: Streaming multiprocessor utilization (%)
# - mem: Memory utilization (%)
# - enc: Encoder utilization (%)
# - dec: Decoder utilization (%)

# Example metering script
#!/bin/bash
while true; do
  timestamp=$(date +%s)
  utilization=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits -i 0)
  echo "${timestamp},GPU0,${utilization}" >> /var/log/gpu-billing.csv
  sleep 60
done
```

---

## Troubleshooting

### PCI Passthrough Issues

**Issue 1: IOMMU Group Conflicts**

```bash
# Problem: GPU shares IOMMU group with other devices
# Solution: Use ACS override patch (use with caution)

# Add to kernel parameters:
pcie_acs_override=downstream,multifunction

# Or: Move GPU to different PCIe slot
```

**Issue 2: Code 43 Error (NVIDIA)**

```bash
# Problem: NVIDIA driver detects VM and fails
# Solution: Hide hypervisor from guest

# Add to VM XML:
<features>
  <kvm>
    <hidden state='on'/>
  </kvm>
  <hyperv>
    <vendor_id state='on' value='1234567890ab'/>
  </hyperv>
</features>
```

**Issue 3: VM Won't Boot with GPU**

```bash
# Problem: GPU VBIOS initialization fails
# Solution: Use OVMF (UEFI) instead of SeaBIOS

# Update VM XML:
<os>
  <type arch='x86_64' machine='q35'>hvm</type>
  <loader readonly='yes' type='pflash'>/usr/share/OVMF/OVMF_CODE.fd</loader>
</os>
```

### MIG Issues

**Issue 1: Cannot Enable MIG Mode**

```bash
# Check if GPU supports MIG
nvidia-smi -q | grep "MIG Mode"

# Ensure no processes using GPU
sudo fuser -v /dev/nvidia*

# Kill processes if needed
sudo killall python3

# Enable and reset
sudo nvidia-smi -mig 1
sudo nvidia-smi -r
```

**Issue 2: MIG Instance Creation Fails**

```bash
# Check available profiles
nvidia-smi mig -lgip

# Ensure no existing instances conflict
nvidia-smi mig -dgi

# Try different profile combination
sudo nvidia-smi mig -cgi 19,19,19,19 -C
```

**Issue 3: Container Can't Access MIG**

```bash
# Verify MIG device UUID
nvidia-smi -L

# Check device visibility
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi -L

# Explicitly specify device
docker run --rm --gpus '"device=MIG-..."' nvidia/cuda:12.0-base nvidia-smi
```

### Performance Issues

**Issue: Poor GPU Performance**

```bash
# Check PCIe link speed
nvidia-smi -q | grep "Link Width"
nvidia-smi -q | grep "Link Speed"

# Should show: 16x, 16.0 GT/s (PCIe 4.0)

# Check for throttling
nvidia-smi -q | grep "Clocks Throttle Reasons"

# Monitor power/temperature
watch -n 1 nvidia-smi
```

---

## References

### Official Documentation

**NVIDIA:**
- MIG User Guide: https://docs.nvidia.com/datacenter/tesla/mig-user-guide/
- PCI Passthrough: https://docs.nvidia.com/grid/latest/grid-vgpu-user-guide/
- Container Toolkit: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/

**KVM/QEMU:**
- PCI Passthrough: https://www.kernel.org/doc/Documentation/vfio.txt
- Proxmox PCI Passthrough: https://pve.proxmox.com/wiki/PCI(e)_Passthrough

**Intel GPU SR-IOV:**
- Intel vGPU Guide: https://www.michaelstinkerings.org/gpu-virtualization-with-intel-12th-gen-igpu-uhd-730/

### Community Resources
- Reddit /r/VFIO: https://reddit.com/r/VFIO
- Level1Techs Forums: https://forum.level1techs.com/c/software/linux/20
- Arch Linux Wiki - PCI Passthrough: https://wiki.archlinux.org/title/PCI_passthrough_via_OVMF

### Benchmarking Tools
- CUDA Samples: https://github.com/NVIDIA/cuda-samples
- MLPerf: https://mlcommons.org/en/training-normal-10/
- GPU Burn: https://github.com/wilicc/gpu-burn

---

## Team Requirements

**Virtualization Engineer** (Primary, 40 hours/week):
- KVM/QEMU expertise
- PCI/PCIe architecture knowledge
- IOMMU/VFIO configuration

**GPU Systems Engineer** (Primary, 40 hours/week):
- NVIDIA GPU architecture
- MIG configuration and management
- Driver troubleshooting

**Linux Kernel Developer** (Consulting, 10 hours/week):
- Kernel module compilation
- VFIO/IOMMU debugging
- SR-IOV configuration

**DevOps Engineer** (Secondary, 20 hours/week):
- Automation and orchestration
- Monitoring and alerting
- Documentation

**Total Estimated Effort**: 2-4 weeks for initial implementation, 2 weeks for optimization and testing

---

*Last Updated: 2025-10-14*
*Version: 1.0*
