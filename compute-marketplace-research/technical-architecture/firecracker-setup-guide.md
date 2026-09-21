# Firecracker MicroVM Setup and Integration Guide

## Overview

Firecracker is a Virtual Machine Monitor (VMM) that uses Linux Kernel-based Virtual Machine (KVM) to create and manage microVMs. It was developed by AWS to power their Lambda and Fargate services, offering minimal memory overhead and fast startup times (125ms boot time, 150 microVMs/second creation rate).

**Estimated Implementation Time**: 2-3 weeks
**Required Skills**: Linux systems administration, networking, KVM/virtualization, REST API integration

## Table of Contents

1. [Prerequisites and System Requirements](#prerequisites-and-system-requirements)
2. [Installation](#installation)
3. [Basic Firecracker API Usage](#basic-firecracker-api-usage)
4. [Network Configuration](#network-configuration)
5. [Storage Configuration](#storage-configuration)
6. [Example Configurations](#example-configurations)
7. [Performance Tuning](#performance-tuning)
8. [Monitoring and Management](#monitoring-and-management)
9. [Production Considerations](#production-considerations)
10. [References](#references)

---

## Prerequisites and System Requirements

### Hardware Requirements

**Required:**
- Intel CPU with VT-x or AMD CPU with AMD-V virtualization extensions
- KVM support enabled in BIOS/UEFI
- Minimum 2GB RAM (4GB+ recommended for production)
- Linux kernel 4.14 or later (5.10+ recommended)

**Verification Commands:**

```bash
# Check CPU virtualization support
egrep -c '(vmx|svm)' /proc/cpuinfo
# Output should be > 0

# Check KVM access
[ -r /dev/kvm ] && [ -w /dev/kvm ] && echo "KVM OK" || echo "KVM FAIL"

# Verify kernel version
uname -r
```

### Software Prerequisites

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
    curl \
    wget \
    kvm \
    qemu-kvm \
    libvirt-daemon \
    libvirt-clients \
    bridge-utils \
    iptables \
    jq

# RHEL/CentOS/Fedora
sudo dnf install -y \
    curl \
    wget \
    qemu-kvm \
    libvirt \
    virt-install \
    bridge-utils \
    iptables \
    jq
```

### User Permissions

```bash
# Add user to KVM group
sudo usermod -aG kvm ${USER}

# Verify permissions
ls -l /dev/kvm
# Should show: crw-rw----+ 1 root kvm
```

**Note**: Log out and back in for group changes to take effect.

---

## Installation

### Method 1: Binary Download (Recommended for Production)

```bash
# Set version (check latest at https://github.com/firecracker-microvm/firecracker/releases)
FIRECRACKER_VERSION="v1.9.1"

# Download Firecracker binary
wget https://github.com/firecracker-microvm/firecracker/releases/download/${FIRECRACKER_VERSION}/firecracker-${FIRECRACKER_VERSION}-x86_64.tgz

# Extract and install
tar -xzf firecracker-${FIRECRACKER_VERSION}-x86_64.tgz
sudo mv release-${FIRECRACKER_VERSION}-x86_64/firecracker-${FIRECRACKER_VERSION}-x86_64 /usr/local/bin/firecracker
sudo chmod +x /usr/local/bin/firecracker

# Verify installation
firecracker --version
```

### Method 2: Build from Source (Development)

```bash
# Install Rust toolchain
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Clone repository
git clone https://github.com/firecracker-microvm/firecracker.git
cd firecracker

# Build release binary
cargo build --release

# Install
sudo cp target/release/firecracker /usr/local/bin/
```

### Prepare Kernel and Rootfs

You need a Linux kernel and root filesystem to boot microVMs:

```bash
# Create working directory
mkdir -p ~/firecracker-demo
cd ~/firecracker-demo

# Download sample kernel (Ubuntu 22.04 compatible)
wget https://s3.amazonaws.com/spec.ccfc.min/firecracker-ci/v1.7/x86_64/vmlinux-5.10.217

# Download sample rootfs (Alpine Linux)
wget https://s3.amazonaws.com/spec.ccfc.min/firecracker-ci/v1.7/x86_64/ubuntu-22.04.ext4

# Alternatively, build custom rootfs
# See: https://github.com/firecracker-microvm/firecracker/blob/main/docs/rootfs-and-kernel-setup.md
```

---

## Basic Firecracker API Usage

Firecracker is controlled via a RESTful API over a Unix socket.

### Starting Firecracker

```bash
# Remove old socket if exists
rm -f /tmp/firecracker.socket

# Start Firecracker in background
firecracker --api-sock /tmp/firecracker.socket &

# Store PID for later
FIRECRACKER_PID=$!
```

### Configuration via API

#### 1. Configure Boot Source

```bash
curl --unix-socket /tmp/firecracker.socket -i \
  -X PUT 'http://localhost/boot-source' \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "kernel_image_path": "/home/user/firecracker-demo/vmlinux-5.10.217",
    "boot_args": "console=ttyS0 reboot=k panic=1 pci=off"
  }'
```

#### 2. Configure Root Filesystem

```bash
curl --unix-socket /tmp/firecracker.socket -i \
  -X PUT 'http://localhost/drives/rootfs' \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "drive_id": "rootfs",
    "path_on_host": "/home/user/firecracker-demo/ubuntu-22.04.ext4",
    "is_root_device": true,
    "is_read_only": false
  }'
```

#### 3. Configure Machine Resources

```bash
curl --unix-socket /tmp/firecracker.socket -i \
  -X PUT 'http://localhost/machine-config' \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "vcpu_count": 2,
    "mem_size_mib": 1024,
    "smt": false,
    "track_dirty_pages": false
  }'
```

#### 4. Start the MicroVM

```bash
curl --unix-socket /tmp/firecracker.socket -i \
  -X PUT 'http://localhost/actions' \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "action_type": "InstanceStart"
  }'
```

### Using Configuration File

For easier management, use a JSON configuration file:

```bash
cat > vm_config.json <<EOF
{
  "boot-source": {
    "kernel_image_path": "/home/user/firecracker-demo/vmlinux-5.10.217",
    "boot_args": "console=ttyS0 reboot=k panic=1 pci=off"
  },
  "drives": [
    {
      "drive_id": "rootfs",
      "path_on_host": "/home/user/firecracker-demo/ubuntu-22.04.ext4",
      "is_root_device": true,
      "is_read_only": false
    }
  ],
  "machine-config": {
    "vcpu_count": 2,
    "mem_size_mib": 1024,
    "smt": false
  },
  "network-interfaces": []
}
EOF

# Start with config file
firecracker --api-sock /tmp/firecracker.socket --config-file vm_config.json
```

---

## Network Configuration

### TAP Device Setup

TAP (Network Tap) devices enable network connectivity for microVMs.

#### Basic NAT Configuration

**Step 1: Create TAP Device**

```bash
#!/bin/bash
# setup_network.sh

TAP_DEV="tap0"
TAP_IP="172.16.0.1"
GUEST_IP="172.16.0.2"
MASK="/30"  # 4 addresses: .0, .1, .2, .3

# Create TAP device
sudo ip tuntap add dev ${TAP_DEV} mode tap

# Assign IP to TAP device
sudo ip addr add ${TAP_IP}${MASK} dev ${TAP_DEV}

# Bring up TAP device
sudo ip link set ${TAP_DEV} up

# Enable IP forwarding
sudo sh -c "echo 1 > /proc/sys/net/ipv4/ip_forward"

# Configure NAT (replace eth0 with your internet-facing interface)
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
sudo iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
sudo iptables -A FORWARD -i ${TAP_DEV} -o eth0 -j ACCEPT
```

**Step 2: Configure Firecracker Network Interface**

```bash
curl --unix-socket /tmp/firecracker.socket -i \
  -X PUT 'http://localhost/network-interfaces/eth0' \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "iface_id": "eth0",
    "guest_mac": "AA:FC:00:00:00:01",
    "host_dev_name": "tap0"
  }'
```

**Step 3: Configure Guest Network (Inside MicroVM)**

After booting into the microVM:

```bash
# Inside the guest
ip addr add 172.16.0.2/30 dev eth0
ip link set eth0 up
ip route add default via 172.16.0.1 dev eth0

# Set DNS
echo "nameserver 8.8.8.8" > /etc/resolv.conf

# Test connectivity
ping -c 3 google.com
```

#### Advanced: Bridge Configuration

For exposing microVMs to the LAN:

```bash
#!/bin/bash
# setup_bridge.sh

BRIDGE="br0"
HOST_IFACE="eth0"
TAP_DEV="tap0"

# Create bridge
sudo ip link add name ${BRIDGE} type bridge

# Add host interface to bridge
sudo ip link set ${HOST_IFACE} master ${BRIDGE}

# Create TAP device
sudo ip tuntap add dev ${TAP_DEV} mode tap

# Add TAP to bridge
sudo ip link set ${TAP_DEV} master ${BRIDGE}

# Bring up devices
sudo ip link set ${BRIDGE} up
sudo ip link set ${TAP_DEV} up

# Transfer IP from eth0 to bridge (if needed)
# sudo ip addr flush dev ${HOST_IFACE}
# sudo ip addr add <your_ip>/<subnet> dev ${BRIDGE}
```

#### Multiple MicroVMs Networking

```bash
#!/bin/bash
# setup_multi_vm_network.sh

NUM_VMS=5
SUBNET="172.16.0.0/24"
GATEWAY="172.16.0.1"

# Setup routing
sudo ip route add ${SUBNET} via ${GATEWAY}

for i in $(seq 1 ${NUM_VMS}); do
    TAP_DEV="tap${i}"

    # Create TAP device
    sudo ip tuntap add dev ${TAP_DEV} mode tap
    sudo ip link set ${TAP_DEV} up

    echo "Created ${TAP_DEV}"
done

# Configure iptables for all TAP devices
sudo iptables -t nat -A POSTROUTING -s ${SUBNET} -o eth0 -j MASQUERADE
```

### Network Rate Limiting

Firecracker supports traffic shaping:

```bash
curl --unix-socket /tmp/firecracker.socket -i \
  -X PUT 'http://localhost/network-interfaces/eth0' \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "iface_id": "eth0",
    "guest_mac": "AA:FC:00:00:00:01",
    "host_dev_name": "tap0",
    "rx_rate_limiter": {
      "bandwidth": {
        "size": 125000000,
        "refill_time": 1000
      },
      "ops": {
        "size": 10000,
        "refill_time": 1000
      }
    },
    "tx_rate_limiter": {
      "bandwidth": {
        "size": 125000000,
        "refill_time": 1000
      }
    }
  }'
```

Values:
- `bandwidth.size`: Bytes per `refill_time` period (125MB/s = ~1Gbps)
- `ops.size`: Operations per `refill_time` period
- `refill_time`: Milliseconds

---

## Storage Configuration

### Root Filesystem

#### Read-Only Root

```bash
curl --unix-socket /tmp/firecracker.socket -i \
  -X PUT 'http://localhost/drives/rootfs' \
  -H 'Content-Type: application/json' \
  -d '{
    "drive_id": "rootfs",
    "path_on_host": "/path/to/rootfs.ext4",
    "is_root_device": true,
    "is_read_only": true
  }'
```

#### Read-Write Root with Rate Limiting

```bash
curl --unix-socket /tmp/firecracker.socket -i \
  -X PUT 'http://localhost/drives/rootfs' \
  -H 'Content-Type: application/json' \
  -d '{
    "drive_id": "rootfs",
    "path_on_host": "/path/to/rootfs.ext4",
    "is_root_device": true,
    "is_read_only": false,
    "rate_limiter": {
      "bandwidth": {
        "size": 104857600,
        "refill_time": 1000
      },
      "ops": {
        "size": 1000,
        "refill_time": 1000
      }
    }
  }'
```

### Additional Block Devices

```bash
# Create additional disk
truncate -s 10G /path/to/data-disk.ext4
mkfs.ext4 /path/to/data-disk.ext4

# Attach to microVM
curl --unix-socket /tmp/firecracker.socket -i \
  -X PUT 'http://localhost/drives/data' \
  -H 'Content-Type: application/json' \
  -d '{
    "drive_id": "data",
    "path_on_host": "/path/to/data-disk.ext4",
    "is_root_device": false,
    "is_read_only": false
  }'
```

Inside the guest, the disk appears as `/dev/vdb`:

```bash
# Mount inside guest
mkdir /mnt/data
mount /dev/vdb /mnt/data
```

### Storage Performance Tuning

Use raw disk images instead of qcow2 for better performance:

```bash
# Convert qcow2 to raw
qemu-img convert -f qcow2 -O raw disk.qcow2 disk.raw

# Create sparse file (doesn't allocate space until written)
truncate -s 20G sparse-disk.raw
mkfs.ext4 sparse-disk.raw
```

### Overlay Filesystems (Copy-on-Write)

For ephemeral workloads, use device mapper snapshots:

```bash
# Create base image
dd if=/dev/zero of=base.img bs=1M count=2048
mkfs.ext4 base.img

# Create snapshot for each VM
sudo dmsetup create vm1-snapshot --table "0 $(blockdev --getsz /dev/loop0) snapshot /dev/loop0 /dev/loop1 P 8"

# Use snapshot as Firecracker drive
```

---

## Example Configurations

### Example 1: Minimal MicroVM

```json
{
  "boot-source": {
    "kernel_image_path": "/var/firecracker/vmlinux",
    "boot_args": "console=ttyS0 reboot=k panic=1 pci=off"
  },
  "drives": [
    {
      "drive_id": "rootfs",
      "path_on_host": "/var/firecracker/rootfs.ext4",
      "is_root_device": true,
      "is_read_only": false
    }
  ],
  "machine-config": {
    "vcpu_count": 1,
    "mem_size_mib": 512
  }
}
```

### Example 2: Compute-Optimized MicroVM

```json
{
  "boot-source": {
    "kernel_image_path": "/var/firecracker/vmlinux-5.10",
    "boot_args": "console=ttyS0 reboot=k panic=1 pci=off intel_pstate=disable"
  },
  "drives": [
    {
      "drive_id": "rootfs",
      "path_on_host": "/var/firecracker/compute-rootfs.ext4",
      "is_root_device": true,
      "is_read_only": true
    },
    {
      "drive_id": "scratch",
      "path_on_host": "/var/firecracker/scratch.ext4",
      "is_root_device": false,
      "is_read_only": false,
      "rate_limiter": {
        "bandwidth": {
          "size": 524288000,
          "refill_time": 1000
        }
      }
    }
  ],
  "machine-config": {
    "vcpu_count": 8,
    "mem_size_mib": 16384,
    "smt": false,
    "cpu_template": "C3"
  },
  "network-interfaces": [
    {
      "iface_id": "eth0",
      "guest_mac": "AA:FC:00:00:00:01",
      "host_dev_name": "tap-compute-1"
    }
  ]
}
```

### Example 3: Multi-Tenant with Resource Limits

```json
{
  "boot-source": {
    "kernel_image_path": "/var/firecracker/vmlinux",
    "boot_args": "console=ttyS0 reboot=k panic=1 pci=off"
  },
  "drives": [
    {
      "drive_id": "rootfs",
      "path_on_host": "/var/firecracker/tenant-123/rootfs.ext4",
      "is_root_device": true,
      "is_read_only": false,
      "rate_limiter": {
        "bandwidth": {
          "size": 52428800,
          "refill_time": 1000
        },
        "ops": {
          "size": 500,
          "refill_time": 1000
        }
      }
    }
  ],
  "machine-config": {
    "vcpu_count": 2,
    "mem_size_mib": 2048,
    "smt": false
  },
  "network-interfaces": [
    {
      "iface_id": "eth0",
      "guest_mac": "AA:FC:00:00:01:23",
      "host_dev_name": "tap-tenant-123",
      "rx_rate_limiter": {
        "bandwidth": {
          "size": 12500000,
          "refill_time": 1000
        }
      },
      "tx_rate_limiter": {
        "bandwidth": {
          "size": 12500000,
          "refill_time": 1000
        }
      }
    }
  ]
}
```

### Example 4: Production Script

```bash
#!/bin/bash
# launch_microvm.sh

set -e

VM_ID="$1"
VCPUS="${2:-2}"
MEM_MB="${3:-1024}"

SOCKET="/var/run/firecracker/${VM_ID}.socket"
KERNEL="/var/firecracker/vmlinux-5.10"
ROOTFS="/var/firecracker/vms/${VM_ID}/rootfs.ext4"
TAP_DEV="tap-${VM_ID}"
LOG_FILE="/var/log/firecracker/${VM_ID}.log"

# Create TAP device
sudo ip tuntap add dev ${TAP_DEV} mode tap
sudo ip link set ${TAP_DEV} up

# Start Firecracker
firecracker \
  --api-sock ${SOCKET} \
  --log-path ${LOG_FILE} \
  --level Info \
  --show-level \
  --show-log-origin &

FIRECRACKER_PID=$!
sleep 1

# Configure via API
curl -s --unix-socket ${SOCKET} -X PUT 'http://localhost/boot-source' \
  -H 'Content-Type: application/json' \
  -d "{\"kernel_image_path\":\"${KERNEL}\",\"boot_args\":\"console=ttyS0 reboot=k panic=1 pci=off\"}"

curl -s --unix-socket ${SOCKET} -X PUT 'http://localhost/drives/rootfs' \
  -H 'Content-Type: application/json' \
  -d "{\"drive_id\":\"rootfs\",\"path_on_host\":\"${ROOTFS}\",\"is_root_device\":true,\"is_read_only\":false}"

curl -s --unix-socket ${SOCKET} -X PUT 'http://localhost/machine-config' \
  -H 'Content-Type: application/json' \
  -d "{\"vcpu_count\":${VCPUS},\"mem_size_mib\":${MEM_MB}}"

curl -s --unix-socket ${SOCKET} -X PUT "http://localhost/network-interfaces/eth0" \
  -H 'Content-Type: application/json' \
  -d "{\"iface_id\":\"eth0\",\"guest_mac\":\"AA:FC:00:${VM_ID:0:2}:${VM_ID:2:2}:${VM_ID:4:2}\",\"host_dev_name\":\"${TAP_DEV}\"}"

# Start the VM
curl -s --unix-socket ${SOCKET} -X PUT 'http://localhost/actions' \
  -H 'Content-Type: application/json' \
  -d '{"action_type":"InstanceStart"}'

echo "MicroVM ${VM_ID} started with PID ${FIRECRACKER_PID}"
echo "Socket: ${SOCKET}"
echo "Log: ${LOG_FILE}"
```

---

## Performance Tuning

### CPU Pinning

Pin vCPUs to specific physical cores for better performance:

```bash
# Get Firecracker PID
FIRECRACKER_PID=$(pgrep firecracker)

# Find vCPU thread IDs
ps -T -p ${FIRECRACKER_PID}

# Pin vCPU threads to cores
taskset -pc 2 <vcpu_thread_id_1>
taskset -pc 3 <vcpu_thread_id_2>
```

Use `cgroup` cpusets for isolation:

```bash
# Create cgroup
sudo cgcreate -g cpuset:/microvm-1

# Assign cores
sudo cgset -r cpuset.cpus=2,3 microvm-1
sudo cgset -r cpuset.mems=0 microvm-1

# Move Firecracker to cgroup
sudo cgclassify -g cpuset:/microvm-1 ${FIRECRACKER_PID}
```

### Memory Configuration

**Huge Pages** reduce TLB misses:

```bash
# Configure huge pages
echo 512 | sudo tee /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages

# Mount hugetlbfs
sudo mkdir -p /mnt/huge
sudo mount -t hugetlbfs -o pagesize=2M none /mnt/huge

# Launch Firecracker with huge pages
firecracker --api-sock /tmp/fc.socket --huge-pages /mnt/huge
```

### I/O Optimization

**Use io_uring** (kernel 5.1+):

```bash
# Rebuild Firecracker with io_uring support
cargo build --release --features=io_uring
```

**Direct I/O**:

Ensure block devices use `O_DIRECT`:

```bash
# Check if enabled in Firecracker logs
grep "O_DIRECT" /var/log/firecracker/*.log
```

### Network Tuning

```bash
# Increase TAP device TX queue length
sudo ip link set tap0 txqueuelen 10000

# Enable multiqueue for TAP
# (Requires multiple queues configured in Firecracker)
sudo ip link set tap0 multiqueue on

# Optimize interrupt handling
echo "100" | sudo tee /sys/class/net/tap0/tx_queue_len
```

### Kernel Boot Arguments

Optimize guest kernel parameters:

```
console=ttyS0 reboot=k panic=1 pci=off \
quiet loglevel=3 \
mitigations=off \
intel_pstate=disable \
nohz=on nohz_full=1-N rcu_nocbs=1-N
```

Explanations:
- `mitigations=off`: Disable Spectre/Meltdown mitigations (use with caution)
- `intel_pstate=disable`: Disable Intel P-state driver for predictable performance
- `nohz=on nohz_full=1-N`: Tickless kernel for reduced overhead
- `rcu_nocbs=1-N`: Offload RCU callbacks

---

## Monitoring and Management

### Metrics API

Firecracker exposes metrics:

```bash
# Enable metrics
curl --unix-socket /tmp/firecracker.socket -X PUT 'http://localhost/metrics' \
  -H 'Content-Type: application/json' \
  -d '{"metrics_path": "/tmp/firecracker-metrics.json"}'

# View metrics
cat /tmp/firecracker-metrics.json | jq .
```

Sample output:

```json
{
  "utc_timestamp_ms": 1234567890,
  "api_server": {
    "process_startup_time_us": 12345,
    "process_startup_time_cpu_us": 5678
  },
  "block": {
    "drive_0": {
      "read_bytes": 1048576,
      "write_bytes": 524288,
      "read_ops": 100,
      "write_ops": 50
    }
  },
  "net": {
    "eth0": {
      "rx_bytes": 2097152,
      "tx_bytes": 1048576,
      "rx_packets": 1500,
      "tx_packets": 1000
    }
  },
  "vcpu": {
    "vcpu_0": {
      "exit_io_in": 50,
      "exit_io_out": 30
    }
  }
}
```

### Logging

Configure structured logging:

```bash
firecracker \
  --api-sock /tmp/fc.socket \
  --log-path /var/log/firecracker/vm-1.log \
  --level Debug \
  --show-level \
  --show-log-origin
```

Log levels: `Error`, `Warning`, `Info`, `Debug`, `Trace`

### Health Checks

```bash
#!/bin/bash
# health_check.sh

SOCKET="/tmp/firecracker.socket"

# Check if socket exists
if [ ! -S "${SOCKET}" ]; then
    echo "ERROR: Socket not found"
    exit 1
fi

# Check instance state
RESPONSE=$(curl -s --unix-socket ${SOCKET} http://localhost/vm)
STATE=$(echo ${RESPONSE} | jq -r '.state')

if [ "${STATE}" = "Running" ]; then
    echo "OK: MicroVM is running"
    exit 0
else
    echo "ERROR: MicroVM state is ${STATE}"
    exit 1
fi
```

---

## Production Considerations

### Security

**Jailer**: Firecracker's jailer provides additional isolation:

```bash
# Install jailer (included with Firecracker release)
sudo cp jailer /usr/local/bin/

# Run with jailer
sudo jailer \
  --id unique-vm-id \
  --exec-file /usr/local/bin/firecracker \
  --uid 123 \
  --gid 100 \
  --chroot-base-dir /srv/firecracker \
  --netns /var/run/netns/fc-net-123 \
  -- \
  --api-sock /run/firecracker.socket \
  --config-file /config.json
```

The jailer:
- Creates a new mount namespace
- Chroots the process
- Drops privileges
- Sets resource limits (cgroups)
- Moves to network namespace

### Resource Limits

Use cgroups to enforce limits:

```bash
# Create cgroup
sudo cgcreate -g memory,cpu:/firecracker/vm-1

# Set memory limit (2GB)
sudo cgset -r memory.limit_in_bytes=2147483648 firecracker/vm-1

# Set CPU quota (50% of 1 core)
sudo cgset -r cpu.cfs_period_us=100000 firecracker/vm-1
sudo cgset -r cpu.cfs_quota_us=50000 firecracker/vm-1

# Start Firecracker in cgroup
sudo cgexec -g memory,cpu:/firecracker/vm-1 firecracker --api-sock /tmp/fc.socket
```

### High Availability

**Snapshot and Restore**:

```bash
# Create snapshot
curl --unix-socket /tmp/fc.socket -X PUT 'http://localhost/snapshot/create' \
  -H 'Content-Type: application/json' \
  -d '{
    "snapshot_type": "Full",
    "snapshot_path": "/snapshots/vm-1.snap",
    "mem_file_path": "/snapshots/vm-1.mem"
  }'

# Restore from snapshot
firecracker --api-sock /tmp/fc-restore.socket &
sleep 1

curl --unix-socket /tmp/fc-restore.socket -X PUT 'http://localhost/snapshot/load' \
  -H 'Content-Type: application/json' \
  -d '{
    "snapshot_path": "/snapshots/vm-1.snap",
    "mem_backend": {
      "backend_type": "File",
      "backend_path": "/snapshots/vm-1.mem"
    }
  }'
```

### Automation and Orchestration

Integration with orchestration systems:

**Example: Systemd Service**

```ini
# /etc/systemd/system/firecracker@.service
[Unit]
Description=Firecracker MicroVM %i
After=network.target

[Service]
Type=simple
ExecStartPre=/usr/local/bin/setup-firecracker.sh %i
ExecStart=/usr/local/bin/firecracker --api-sock /var/run/firecracker/%i.socket --config-file /etc/firecracker/%i.json
ExecStop=/usr/local/bin/cleanup-firecracker.sh %i
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Usage:

```bash
sudo systemctl start firecracker@vm-001
sudo systemctl status firecracker@vm-001
```

---

## References

### Official Documentation
- **Firecracker GitHub**: https://github.com/firecracker-microvm/firecracker
- **Getting Started**: https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md
- **Production Setup**: https://github.com/firecracker-microvm/firecracker/blob/main/docs/prod-host-setup.md
- **Network Setup**: https://github.com/firecracker-microvm/firecracker/blob/main/docs/network-setup.md
- **API Reference**: https://github.com/firecracker-microvm/firecracker/blob/main/docs/api_requests

### Tutorials and Guides
- **Firecracker Official Site**: https://firecracker-microvm.github.io/
- **Better Programming Tutorial**: https://betterprogramming.pub/getting-started-with-firecracker-a88495d656d9
- **Tutorials Dojo (2025)**: https://tutorialsdojo.com/lets-learn-firecracker-microvm-with-go-firecracker-sdk/
- **WWT Tutorial**: https://www.wwt.com/blog/boot-a-vm-in-3-seconds-firecracker

### Community Resources
- **Firecracker Slack**: https://join.slack.com/t/firecracker-microvm/shared_invite/
- **GitHub Discussions**: https://github.com/firecracker-microvm/firecracker/discussions

### Related Technologies
- **KVM Documentation**: https://www.linux-kvm.org/page/Documents
- **TAP/TUN Tutorial**: https://www.kernel.org/doc/Documentation/networking/tuntap.txt
- **Linux Namespaces**: https://man7.org/linux/man-pages/man7/namespaces.7.html

---

## Team Requirements

**DevOps Engineer** (Primary, 40 hours/week):
- Linux systems administration
- Virtualization (KVM) experience
- Network configuration expertise
- API integration skills

**Backend Developer** (Secondary, 20 hours/week):
- REST API development
- Go/Rust (for SDK integration)
- System programming

**Security Engineer** (Consulting, 10 hours/week):
- Namespace/cgroup isolation
- Security hardening
- Audit and compliance

**Total Estimated Effort**: 2-3 weeks for initial implementation, 1 week for production hardening

---

*Last Updated: 2025-10-14*
*Version: 1.0*
