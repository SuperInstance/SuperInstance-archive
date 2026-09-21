# Checkpoint/Restart Implementation Guide

## Overview

Checkpoint/restart enables saving the complete state of a running application and resuming it later, potentially on different hardware. This is critical for compute marketplaces to enable job preemption, migration, and fault tolerance. This guide focuses on DMTCP (Distributed MultiThreaded CheckPointing) and GPU checkpoint strategies.

**Estimated Implementation Time**: 3-4 weeks
**Required Skills**: Linux systems programming, process management, GPU architecture, distributed systems

**Important Note**: As of 2025, DMTCP does not natively support GPU checkpointing in production. This guide covers both DMTCP for CPU workloads and research approaches for GPU checkpoint/restart.

## Table of Contents

1. [Checkpoint/Restart Concepts](#checkpointrestart-concepts)
2. [DMTCP Installation](#dmtcp-installation)
3. [Basic DMTCP Usage](#basic-dmtcp-usage)
4. [Integration with Job Scheduler](#integration-with-job-scheduler)
5. [GPU Checkpoint Strategies](#gpu-checkpoint-strategies)
6. [Performance Characteristics](#performance-characteristics)
7. [Implementation Examples](#implementation-examples)
8. [Production Considerations](#production-considerations)
9. [Alternatives and Future Directions](#alternatives-and-future-directions)
10. [References](#references)

---

## Checkpoint/Restart Concepts

### What is Checkpoint/Restart?

**Checkpoint**: Capturing the complete state of a running process, including:
- Memory contents (heap, stack, data segments)
- Register values and instruction pointer
- Open file descriptors
- Network connections
- Process hierarchy and relationships

**Restart**: Restoring a checkpointed process to its saved state, allowing it to continue execution.

### Use Cases in Compute Marketplace

**1. Job Preemption**
```
High-priority job arrives → Checkpoint low-priority job →
Free resources → Run high-priority job →
Restart checkpointed job later
```

**2. Spot Instance Migration**
```
Spot instance termination warning → Checkpoint job →
Transfer checkpoint → Restart on new node
```

**3. Fault Tolerance**
```
Hardware failure detected → Restore from last checkpoint →
Continue execution with minimal loss
```

**4. Resource Optimization**
```
Idle GPU detected → Checkpoint CPU-bound phase →
Free GPU → Restart when GPU phase resumes
```

### Checkpoint Types

| Type | Description | Overhead | Use Case |
|------|-------------|----------|----------|
| **Full** | Complete process state | High (GB) | Long-running jobs |
| **Incremental** | Only changed memory pages | Medium | Frequent checkpoints |
| **Application-level** | App-managed state | Low | Framework-specific |
| **System-level** | OS-managed (DMTCP) | High | Transparent to app |

---

## DMTCP Installation

### System Requirements

- Linux kernel 3.x+ (4.x+ recommended)
- x86_64 or ARM64 architecture
- Python 2.7+ or 3.x
- GCC compiler

### Installation from Package Manager

**Ubuntu/Debian:**

```bash
sudo apt-get update
sudo apt-get install -y dmtcp
```

**RHEL/CentOS/Fedora:**

```bash
sudo dnf install -y dmtcp
```

**Verify Installation:**

```bash
dmtcp_command --version
# Should show: DMTCP version X.Y.Z
```

### Installation from Source

```bash
# Download latest release
DMTCP_VERSION="3.0.0"
wget https://github.com/dmtcp/dmtcp/archive/refs/tags/${DMTCP_VERSION}.tar.gz
tar -xzf ${DMTCP_VERSION}.tar.gz
cd dmtcp-${DMTCP_VERSION}

# Configure and build
./configure --prefix=/usr/local
make -j$(nproc)

# Test
make check

# Install
sudo make install

# Verify
dmtcp_command --version
```

### Configuration

```bash
# Optional: Configure default checkpoint directory
export DMTCP_CHECKPOINT_DIR=/var/lib/dmtcp/checkpoints

# Optional: Set checkpoint interval (seconds)
export DMTCP_CHECKPOINT_INTERVAL=3600

# Add to ~/.bashrc or /etc/environment for persistence
```

---

## Basic DMTCP Usage

### Simple Checkpoint Example

**Example 1: Long-Running Python Script**

```python
# test_checkpoint.py
import time
import sys

counter = 0
while True:
    counter += 1
    print(f"Counter: {counter}", flush=True)
    time.sleep(5)

    if counter >= 100:
        print("Completed!")
        sys.exit(0)
```

**Run with DMTCP:**

```bash
# Start coordinator
dmtcp_coordinator --daemon --port 7779

# Launch application
dmtcp_launch --interval 30 python3 test_checkpoint.py

# Application runs and checkpoints every 30 seconds
```

**Manual Checkpoint:**

```bash
# In another terminal
dmtcp_command --checkpoint

# Checkpoint files created in current directory:
# ckpt_*.dmtcp
```

**Kill and Restart:**

```bash
# Kill application
pkill -9 python3

# Restart from checkpoint
dmtcp_restart ckpt_*.dmtcp

# Application continues from checkpointed state
```

### Checkpoint with MPI Applications

```bash
# Launch MPI application with DMTCP
mpirun -np 4 dmtcp_launch ./mpi_application

# Checkpoint all processes
dmtcp_command --checkpoint

# Restart
dmtcp_restart ckpt_*.dmtcp
```

### Checkpoint Docker Containers

**Method 1: Checkpoint Process Inside Container**

```bash
# Start container with DMTCP
docker run -d --name my-app \
  -v /var/lib/dmtcp:/checkpoints \
  ubuntu:latest \
  dmtcp_launch --checkpoint-dir /checkpoints ./my-app

# Checkpoint from host
docker exec my-app dmtcp_command --checkpoint

# Restart
docker exec my-app dmtcp_restart /checkpoints/ckpt_*.dmtcp
```

**Method 2: Docker Checkpoint (Experimental)**

```bash
# Enable experimental features in /etc/docker/daemon.json
{
  "experimental": true
}

# Restart Docker
sudo systemctl restart docker

# Checkpoint container (uses CRIU internally)
docker checkpoint create my-app checkpoint1

# Stop container
docker stop my-app

# Restore
docker start --checkpoint checkpoint1 my-app
```

---

## Integration with Job Scheduler

### Checkpoint Manager Class

```python
#!/usr/bin/env python3
"""
Checkpoint manager for worker agent integration
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DMTCPCheckpointManager:
    """Manages DMTCP checkpointing for jobs"""

    def __init__(self, checkpoint_dir: str = "/var/lib/dmtcp"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.coordinator_port = 7779
        self.coordinator_process = None

    def start_coordinator(self) -> bool:
        """Start DMTCP coordinator daemon"""
        try:
            cmd = [
                "dmtcp_coordinator",
                "--daemon",
                "--port", str(self.coordinator_port),
                "--exit-on-last"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Failed to start coordinator: {result.stderr}")
                return False

            logger.info(f"DMTCP coordinator started on port {self.coordinator_port}")
            return True

        except Exception as e:
            logger.error(f"Exception starting coordinator: {e}")
            return False

    def launch_job(self, job_id: str, command: List[str],
                   checkpoint_interval: int = 3600) -> subprocess.Popen:
        """
        Launch job under DMTCP control

        Args:
            job_id: Unique job identifier
            command: Command and arguments to execute
            checkpoint_interval: Seconds between automatic checkpoints (0 = manual only)

        Returns:
            Popen object for the launched process
        """
        job_checkpoint_dir = self.checkpoint_dir / job_id
        job_checkpoint_dir.mkdir(parents=True, exist_ok=True)

        dmtcp_cmd = [
            "dmtcp_launch",
            "--port", str(self.coordinator_port),
            "--checkpoint-dir", str(job_checkpoint_dir),
        ]

        if checkpoint_interval > 0:
            dmtcp_cmd.extend(["--interval", str(checkpoint_interval)])

        dmtcp_cmd.extend(command)

        logger.info(f"Launching job {job_id}: {' '.join(dmtcp_cmd)}")

        process = subprocess.Popen(
            dmtcp_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(job_checkpoint_dir)
        )

        return process

    def checkpoint_job(self, job_id: str) -> bool:
        """
        Trigger manual checkpoint for job

        Args:
            job_id: Job identifier

        Returns:
            True if checkpoint succeeded
        """
        try:
            cmd = [
                "dmtcp_command",
                "--port", str(self.coordinator_port),
                "--checkpoint"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                logger.info(f"Checkpoint created for job {job_id}")
                return True
            else:
                logger.error(f"Checkpoint failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Checkpoint timeout")
            return False
        except Exception as e:
            logger.error(f"Checkpoint exception: {e}")
            return False

    def list_checkpoints(self, job_id: str) -> List[str]:
        """List available checkpoints for job"""
        job_checkpoint_dir = self.checkpoint_dir / job_id
        if not job_checkpoint_dir.exists():
            return []

        checkpoints = list(job_checkpoint_dir.glob("ckpt_*.dmtcp"))
        return [str(c) for c in sorted(checkpoints)]

    def restart_job(self, job_id: str, checkpoint_file: Optional[str] = None) -> subprocess.Popen:
        """
        Restart job from checkpoint

        Args:
            job_id: Job identifier
            checkpoint_file: Specific checkpoint file (None = latest)

        Returns:
            Popen object for restarted process
        """
        if checkpoint_file is None:
            checkpoints = self.list_checkpoints(job_id)
            if not checkpoints:
                raise ValueError(f"No checkpoints found for job {job_id}")
            checkpoint_file = checkpoints[-1]  # Latest checkpoint

        logger.info(f"Restarting job {job_id} from {checkpoint_file}")

        cmd = ["dmtcp_restart", checkpoint_file]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        return process

    def kill_job(self, job_id: str) -> bool:
        """Kill job (coordinator will handle cleanup)"""
        try:
            cmd = [
                "dmtcp_command",
                "--port", str(self.coordinator_port),
                "--kill"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to kill job: {e}")
            return False

    def cleanup_checkpoints(self, job_id: str, keep_latest: int = 3) -> None:
        """
        Clean up old checkpoints, keeping only the latest N

        Args:
            job_id: Job identifier
            keep_latest: Number of recent checkpoints to keep
        """
        checkpoints = self.list_checkpoints(job_id)
        if len(checkpoints) <= keep_latest:
            return

        to_delete = checkpoints[:-keep_latest]
        for checkpoint in to_delete:
            try:
                os.remove(checkpoint)
                logger.info(f"Deleted old checkpoint: {checkpoint}")
            except Exception as e:
                logger.error(f"Failed to delete checkpoint {checkpoint}: {e}")

    def get_checkpoint_info(self, checkpoint_file: str) -> dict:
        """Get information about a checkpoint"""
        if not os.path.exists(checkpoint_file):
            return {}

        stat = os.stat(checkpoint_file)
        return {
            "file": checkpoint_file,
            "size_mb": stat.st_size / (1024 * 1024),
            "created": time.ctime(stat.st_ctime),
            "modified": time.ctime(stat.st_mtime),
        }

    def stop_coordinator(self) -> None:
        """Stop DMTCP coordinator"""
        try:
            cmd = [
                "dmtcp_command",
                "--port", str(self.coordinator_port),
                "--quit"
            ]
            subprocess.run(cmd, capture_output=True)
            logger.info("DMTCP coordinator stopped")
        except Exception as e:
            logger.error(f"Failed to stop coordinator: {e}")


# Example usage
if __name__ == "__main__":
    manager = DMTCPCheckpointManager()

    # Start coordinator
    manager.start_coordinator()

    # Launch job
    job_id = "test-job-001"
    process = manager.launch_job(
        job_id=job_id,
        command=["python3", "long_running_script.py"],
        checkpoint_interval=60  # Checkpoint every minute
    )

    # Let it run for a while
    time.sleep(90)

    # Manual checkpoint
    manager.checkpoint_job(job_id)

    # List checkpoints
    checkpoints = manager.list_checkpoints(job_id)
    print(f"Checkpoints: {checkpoints}")

    # Kill job
    manager.kill_job(job_id)

    # Wait a bit
    time.sleep(5)

    # Restart from checkpoint
    restarted_process = manager.restart_job(job_id)

    # Cleanup
    time.sleep(10)
    manager.stop_coordinator()
```

### Worker Agent Integration

```go
// checkpoint_manager.go
package worker

import (
    "fmt"
    "os/exec"
    "path/filepath"
    "time"
)

type CheckpointManager struct {
    checkpointDir    string
    coordinatorPort  int
    checkpointPolicy CheckpointPolicy
}

type CheckpointPolicy struct {
    Interval    time.Duration // 0 = manual only
    MaxSize     int64         // Max checkpoint size in bytes
    KeepLatest  int           // Number of checkpoints to retain
}

func NewCheckpointManager(dir string, port int) *CheckpointManager {
    return &CheckpointManager{
        checkpointDir:   dir,
        coordinatorPort: port,
        checkpointPolicy: CheckpointPolicy{
            Interval:   time.Hour,
            MaxSize:    10 * 1024 * 1024 * 1024, // 10GB
            KeepLatest: 3,
        },
    }
}

func (cm *CheckpointManager) StartCoordinator() error {
    cmd := exec.Command(
        "dmtcp_coordinator",
        "--daemon",
        "--port", fmt.Sprintf("%d", cm.coordinatorPort),
        "--exit-on-last",
    )

    if err := cmd.Run(); err != nil {
        return fmt.Errorf("failed to start coordinator: %w", err)
    }

    return nil
}

func (cm *CheckpointManager) LaunchWithCheckpoint(jobID string, command []string) (*exec.Cmd, error) {
    jobDir := filepath.Join(cm.checkpointDir, jobID)

    args := []string{
        "--port", fmt.Sprintf("%d", cm.coordinatorPort),
        "--checkpoint-dir", jobDir,
    }

    if cm.checkpointPolicy.Interval > 0 {
        args = append(args, "--interval", fmt.Sprintf("%d", int(cm.checkpointPolicy.Interval.Seconds())))
    }

    args = append(args, command...)

    cmd := exec.Command("dmtcp_launch", args...)
    cmd.Dir = jobDir

    if err := cmd.Start(); err != nil {
        return nil, fmt.Errorf("failed to launch job: %w", err)
    }

    return cmd, nil
}

func (cm *CheckpointManager) Checkpoint(jobID string) error {
    cmd := exec.Command(
        "dmtcp_command",
        "--port", fmt.Sprintf("%d", cm.coordinatorPort),
        "--checkpoint",
    )

    if err := cmd.Run(); err != nil {
        return fmt.Errorf("checkpoint failed: %w", err)
    }

    return nil
}

func (cm *CheckpointManager) Restart(jobID string) (*exec.Cmd, error) {
    // Find latest checkpoint
    pattern := filepath.Join(cm.checkpointDir, jobID, "ckpt_*.dmtcp")
    matches, err := filepath.Glob(pattern)
    if err != nil || len(matches) == 0 {
        return nil, fmt.Errorf("no checkpoint found for job %s", jobID)
    }

    checkpointFile := matches[len(matches)-1] // Latest

    cmd := exec.Command("dmtcp_restart", checkpointFile)

    if err := cmd.Start(); err != nil {
        return nil, fmt.Errorf("restart failed: %w", err)
    }

    return cmd, nil
}
```

---

## GPU Checkpoint Strategies

### Current State of GPU Checkpointing

**DMTCP Limitation**: DMTCP cannot checkpoint GPU processes because:
- GPU memory is not in process address space
- CUDA driver state is opaque
- PCIe communications cannot be serialized

### Research Solutions

#### 1. CRAC (Checkpoint-Restart Architecture for CUDA)

**Concept**: Application-space checkpoint that replays CUDA calls.

**Approach**:
1. Intercept CUDA API calls
2. Log parameters and results
3. On checkpoint: Save CPU state (DMTCP) + CUDA log
4. On restart: Replay CUDA calls to rebuild GPU state

**Implementation** (Research prototype):

```python
#!/usr/bin/env python3
"""
Conceptual CUDA checkpoint wrapper (research-level)
"""

import pickle
import ctypes
from typing import List, Dict, Any

class CUDACheckpointWrapper:
    """
    Wrapper for CUDA applications to enable checkpoint/restart
    This is a conceptual implementation based on CRAC research
    """

    def __init__(self):
        self.cuda_calls: List[Dict[str, Any]] = []
        self.memory_allocations: Dict[int, bytes] = {}
        self.enabled = False

    def enable(self):
        """Enable CUDA call logging"""
        self.enabled = True

    def log_call(self, function: str, args: tuple, result: Any):
        """Log a CUDA call"""
        if not self.enabled:
            return

        self.cuda_calls.append({
            'function': function,
            'args': args,
            'result': result,
            'timestamp': time.time()
        })

    def save_checkpoint(self, filename: str):
        """Save CUDA state to checkpoint file"""
        checkpoint = {
            'cuda_calls': self.cuda_calls,
            'memory_allocations': self.memory_allocations,
        }

        with open(filename, 'wb') as f:
            pickle.dump(checkpoint, f)

    def restore_checkpoint(self, filename: str):
        """Restore CUDA state from checkpoint"""
        with open(filename, 'rb') as f:
            checkpoint = pickle.load(f)

        # Replay CUDA calls to rebuild state
        for call in checkpoint['cuda_calls']:
            self._replay_call(call)

        # Restore GPU memory
        for addr, data in checkpoint['memory_allocations'].items():
            self._restore_memory(addr, data)

    def _replay_call(self, call: Dict):
        """Replay a single CUDA call"""
        # This would call the actual CUDA function
        # Implementation depends on CUDA API interception
        pass

    def _restore_memory(self, addr: int, data: bytes):
        """Restore GPU memory contents"""
        # Copy data back to GPU
        pass
```

**Status**: Research prototype, not production-ready.

#### 2. Application-Level Checkpointing

**Best Practice**: Implement checkpointing in the application itself.

**PyTorch Example**:

```python
import torch
import os

class TrainingCheckpoint:
    """Checkpoint PyTorch training state"""

    def __init__(self, checkpoint_dir: str):
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True)

    def save(self, epoch: int, model: torch.nn.Module,
             optimizer: torch.optim.Optimizer,
             scheduler, metrics: dict):
        """Save training checkpoint"""
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'scheduler_state_dict': scheduler.state_dict() if scheduler else None,
            'metrics': metrics,
        }

        filename = os.path.join(self.checkpoint_dir, f'checkpoint_epoch_{epoch}.pt')
        torch.save(checkpoint, filename)
        print(f"Checkpoint saved: {filename}")

        # Also save as 'latest' for easy resumption
        latest = os.path.join(self.checkpoint_dir, 'checkpoint_latest.pt')
        torch.save(checkpoint, latest)

    def load(self, model: torch.nn.Module,
             optimizer: torch.optim.Optimizer,
             scheduler, filename: str = None):
        """Load training checkpoint"""
        if filename is None:
            filename = os.path.join(self.checkpoint_dir, 'checkpoint_latest.pt')

        checkpoint = torch.load(filename)

        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        if scheduler and checkpoint.get('scheduler_state_dict'):
            scheduler.load_state_dict(checkpoint['scheduler_state_dict'])

        print(f"Checkpoint loaded from epoch {checkpoint['epoch']}")
        return checkpoint['epoch'], checkpoint['metrics']


# Usage example
def train_with_checkpointing():
    model = MyModel().cuda()
    optimizer = torch.optim.Adam(model.parameters())
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10)
    checkpoint_mgr = TrainingCheckpoint('./checkpoints')

    # Try to resume from checkpoint
    start_epoch = 0
    if os.path.exists('./checkpoints/checkpoint_latest.pt'):
        start_epoch, metrics = checkpoint_mgr.load(model, optimizer, scheduler)
        start_epoch += 1

    # Training loop
    for epoch in range(start_epoch, 100):
        # Training code here
        train_loss = train_epoch(model, optimizer)
        val_loss = validate(model)

        # Checkpoint every N epochs
        if epoch % 5 == 0:
            checkpoint_mgr.save(epoch, model, optimizer, scheduler, {
                'train_loss': train_loss,
                'val_loss': val_loss
            })
```

**TensorFlow Example**:

```python
import tensorflow as tf

# Built-in checkpointing
checkpoint = tf.train.Checkpoint(
    model=model,
    optimizer=optimizer,
    step=tf.Variable(0)
)

manager = tf.train.CheckpointManager(
    checkpoint,
    directory='./checkpoints',
    max_to_keep=3
)

# Save
checkpoint.step.assign_add(1)
manager.save()

# Restore
checkpoint.restore(manager.latest_checkpoint)
```

#### 3. Hybrid Approach: CPU Checkpoint + GPU State Save

```python
def hybrid_checkpoint(job_id: str, dmtcp_mgr, gpu_state_saver):
    """
    Checkpoint CPU state with DMTCP and save GPU state separately
    """
    # 1. Pause GPU operations (application-specific)
    pause_gpu_operations()

    # 2. Save GPU state (model weights, optimizer state, etc.)
    gpu_checkpoint_file = f'/checkpoints/{job_id}/gpu_state.pt'
    gpu_state_saver.save(gpu_checkpoint_file)

    # 3. Checkpoint CPU process with DMTCP
    dmtcp_mgr.checkpoint_job(job_id)

    # 4. Resume GPU operations
    resume_gpu_operations()

def hybrid_restart(job_id: str, dmtcp_mgr, gpu_state_loader):
    """
    Restart from hybrid checkpoint
    """
    # 1. Restart CPU process
    dmtcp_mgr.restart_job(job_id)

    # 2. Wait for process to initialize
    time.sleep(5)

    # 3. Load GPU state (application handles this)
    # Application must be designed to check for GPU checkpoint on startup
```

---

## Performance Characteristics

### DMTCP Checkpoint Overhead

**Checkpoint Time**:
- Small processes (100MB): 0.1-0.5 seconds
- Medium processes (1GB): 1-3 seconds
- Large processes (10GB): 10-30 seconds
- Very large (100GB): 100-300 seconds

**Factors Affecting Performance**:
- Memory size
- Disk I/O speed
- Checkpoint compression (optional)
- Incremental vs. full checkpoint

### Checkpoint Frequency Trade-offs

```
Checkpoint Frequency:
┌──────────────────────────────────────────┐
│ Too Frequent (< 1 min)                   │
│ + Quick recovery                         │
│ - High overhead (pause time)             │
│ - Excessive disk usage                   │
└──────────────────────────────────────────┘
┌──────────────────────────────────────────┐
│ Optimal (5-60 min)                       │
│ + Balanced overhead                      │
│ + Reasonable recovery time               │
│ ~ Moderate disk usage                    │
└──────────────────────────────────────────┘
┌──────────────────────────────────────────┐
│ Too Infrequent (> 1 hour)                │
│ + Minimal overhead                       │
│ - Long recovery time (re-computation)    │
│ - Greater risk of lost work              │
└──────────────────────────────────────────┘
```

**Optimal Frequency Formula**:
```
optimal_interval = sqrt(2 * checkpoint_time / failure_rate)

Example:
- checkpoint_time = 30 seconds
- failure_rate = 1 failure per 100 hours = 0.01/hour
- optimal_interval = sqrt(2 * 30 / 0.01) = sqrt(6000) ≈ 77 seconds ≈ 1.3 minutes
```

### Benchmark Script

```bash
#!/bin/bash
# benchmark_checkpoint.sh

set -e

MEMORY_SIZES=(100 500 1000 5000 10000)  # MB
RESULTS_FILE="checkpoint_benchmark.csv"

echo "memory_mb,checkpoint_time_sec,restart_time_sec,checkpoint_size_mb" > $RESULTS_FILE

for MEM_SIZE in "${MEMORY_SIZES[@]}"; do
    echo "Benchmarking ${MEM_SIZE}MB process..."

    # Create test program that allocates memory
    cat > test_mem.py <<EOF
import time
import sys

# Allocate memory
mem_size = ${MEM_SIZE} * 1024 * 1024
data = bytearray(mem_size)

# Fill with data
for i in range(0, mem_size, 4096):
    data[i] = i % 256

print(f"Allocated {mem_size/(1024*1024)}MB", flush=True)

# Keep running
while True:
    time.sleep(1)
EOF

    # Start DMTCP coordinator
    dmtcp_coordinator --daemon --port 7779 &
    COORD_PID=$!
    sleep 2

    # Launch process
    dmtcp_launch --port 7779 python3 test_mem.py &
    APP_PID=$!
    sleep 5

    # Benchmark checkpoint
    START=$(date +%s.%N)
    dmtcp_command --port 7779 --checkpoint
    END=$(date +%s.%N)
    CHECKPOINT_TIME=$(echo "$END - $START" | bc)

    # Get checkpoint size
    CKPT_FILE=$(ls -t ckpt_*.dmtcp | head -1)
    CKPT_SIZE=$(du -m "$CKPT_FILE" | cut -f1)

    # Kill process
    kill $APP_PID 2>/dev/null || true
    sleep 2

    # Benchmark restart
    START=$(date +%s.%N)
    dmtcp_restart $CKPT_FILE &
    RESTART_PID=$!
    sleep 3
    END=$(date +%s.%N)
    RESTART_TIME=$(echo "$END - $START" | bc)

    # Clean up
    kill $RESTART_PID 2>/dev/null || true
    kill $COORD_PID 2>/dev/null || true
    rm -f ckpt_*.dmtcp test_mem.py

    # Record results
    echo "${MEM_SIZE},${CHECKPOINT_TIME},${RESTART_TIME},${CKPT_SIZE}" >> $RESULTS_FILE

    echo "Results: checkpoint=${CHECKPOINT_TIME}s, restart=${RESTART_TIME}s, size=${CKPT_SIZE}MB"
    sleep 5
done

echo "Benchmark complete. Results in $RESULTS_FILE"
```

---

## Implementation Examples

### Complete Checkpoint-Enabled Job Runner

```python
#!/usr/bin/env python3
"""
Production-ready checkpoint-enabled job runner
"""

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CheckpointConfig:
    enabled: bool = True
    interval: int = 3600  # seconds
    max_checkpoints: int = 3
    checkpoint_dir: str = "/var/lib/checkpoints"
    on_preempt: bool = True  # Checkpoint on SIGTERM


class CheckpointJobRunner:
    """Run jobs with automatic checkpointing"""

    def __init__(self, config: CheckpointConfig):
        self.config = config
        self.checkpoint_dir = Path(config.checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.coordinator_port = 7779
        self.process: Optional[subprocess.Popen] = None
        self.should_exit = False

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}")
            if self.config.on_preempt and signum in (signal.SIGTERM, signal.SIGINT):
                logger.info("Triggering checkpoint before exit...")
                self.checkpoint()
            self.should_exit = True

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def start_coordinator(self) -> bool:
        """Start DMTCP coordinator"""
        try:
            cmd = [
                "dmtcp_coordinator",
                "--daemon",
                "--port", str(self.coordinator_port),
                "--exit-on-last"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to start coordinator: {e}")
            return False

    def launch(self, job_id: str, command: list, resume: bool = False) -> int:
        """
        Launch job with checkpoint support

        Args:
            job_id: Unique job identifier
            command: Command to execute
            resume: Resume from checkpoint if available

        Returns:
            Exit code
        """
        job_checkpoint_dir = self.checkpoint_dir / job_id
        job_checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.setup_signal_handlers()

        # Check for existing checkpoint
        checkpoints = self.find_checkpoints(job_id)
        if resume and checkpoints:
            logger.info(f"Resuming from checkpoint: {checkpoints[-1]}")
            return self.restart(checkpoints[-1])

        # Start coordinator
        if not self.start_coordinator():
            logger.error("Failed to start coordinator")
            return 1

        # Launch with DMTCP
        dmtcp_cmd = [
            "dmtcp_launch",
            "--port", str(self.coordinator_port),
            "--checkpoint-dir", str(job_checkpoint_dir),
        ]

        if self.config.interval > 0:
            dmtcp_cmd.extend(["--interval", str(self.config.interval)])

        dmtcp_cmd.extend(command)

        logger.info(f"Launching: {' '.join(dmtcp_cmd)}")

        self.process = subprocess.Popen(
            dmtcp_cmd,
            stdout=sys.stdout,
            stderr=sys.stderr,
            cwd=str(job_checkpoint_dir)
        )

        # Monitor process
        while not self.should_exit:
            try:
                exit_code = self.process.wait(timeout=10)
                logger.info(f"Process exited with code {exit_code}")
                return exit_code
            except subprocess.TimeoutExpired:
                # Process still running
                continue
            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                self.checkpoint()
                self.process.terminate()
                return 130

        # Graceful shutdown requested
        logger.info("Initiating graceful shutdown...")
        self.process.terminate()
        try:
            self.process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            logger.warning("Process didn't terminate gracefully, killing...")
            self.process.kill()

        return 0

    def checkpoint(self) -> bool:
        """Trigger manual checkpoint"""
        try:
            cmd = [
                "dmtcp_command",
                "--port", str(self.coordinator_port),
                "--checkpoint"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                logger.info("Checkpoint created successfully")
                return True
            else:
                logger.error(f"Checkpoint failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Checkpoint error: {e}")
            return False

    def restart(self, checkpoint_file: str) -> int:
        """Restart from checkpoint"""
        logger.info(f"Restarting from: {checkpoint_file}")

        cmd = ["dmtcp_restart", checkpoint_file]

        self.process = subprocess.Popen(
            cmd,
            stdout=sys.stdout,
            stderr=sys.stderr
        )

        return self.process.wait()

    def find_checkpoints(self, job_id: str) -> list:
        """Find available checkpoints for job"""
        job_checkpoint_dir = self.checkpoint_dir / job_id
        if not job_checkpoint_dir.exists():
            return []

        checkpoints = list(job_checkpoint_dir.glob("ckpt_*.dmtcp"))
        return [str(c) for c in sorted(checkpoints)]

    def cleanup_old_checkpoints(self, job_id: str):
        """Remove old checkpoints, keeping only recent ones"""
        checkpoints = self.find_checkpoints(job_id)
        if len(checkpoints) <= self.config.max_checkpoints:
            return

        to_delete = checkpoints[:-self.config.max_checkpoints]
        for checkpoint in to_delete:
            try:
                os.remove(checkpoint)
                logger.info(f"Removed old checkpoint: {checkpoint}")
            except Exception as e:
                logger.error(f"Failed to remove {checkpoint}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Checkpoint-enabled job runner")
    parser.add_argument("--job-id", required=True, help="Unique job identifier")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint if available")
    parser.add_argument("--interval", type=int, default=3600, help="Checkpoint interval (seconds)")
    parser.add_argument("--checkpoint-dir", default="/var/lib/checkpoints", help="Checkpoint directory")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to execute")

    args = parser.parse_args()

    if not args.command:
        parser.error("No command specified")

    config = CheckpointConfig(
        interval=args.interval,
        checkpoint_dir=args.checkpoint_dir
    )

    runner = CheckpointJobRunner(config)
    exit_code = runner.launch(args.job_id, args.command, resume=args.resume)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
```

**Usage**:

```bash
# Run new job
./checkpoint_runner.py --job-id job-123 --interval 600 python3 train.py

# Resume from checkpoint
./checkpoint_runner.py --job-id job-123 --resume python3 train.py

# Job will automatically checkpoint on SIGTERM (preemption)
kill -TERM <pid>
```

---

## Production Considerations

### Storage Requirements

```
Checkpoint Size Estimation:
- Small CPU job (1GB RAM): ~1GB per checkpoint
- Medium CPU job (10GB RAM): ~10GB per checkpoint
- Large CPU job (100GB RAM): ~100GB per checkpoint

Storage needed = checkpoint_size × max_checkpoints × concurrent_jobs

Example:
- 10GB per checkpoint
- 3 checkpoints kept
- 100 concurrent jobs
= 3TB storage required
```

### Network Transfer for Migration

```python
def transfer_checkpoint_to_node(checkpoint_file: str, target_node: str,
                                target_path: str) -> bool:
    """Transfer checkpoint to another node"""
    import subprocess

    # Use rsync for reliable transfer with resume capability
    cmd = [
        "rsync",
        "-avz",
        "--progress",
        "--partial",  # Keep partial files for resume
        checkpoint_file,
        f"{target_node}:{target_path}"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Transfer failed: {e}")
        return False
```

### Monitoring and Alerts

```yaml
# Prometheus alerts for checkpointing
groups:
- name: checkpoint_alerts
  rules:
  - alert: CheckpointFailureRate
    expr: rate(checkpoint_failures_total[5m]) > 0.1
    for: 5m
    annotations:
      summary: "High checkpoint failure rate"

  - alert: CheckpointDuration
    expr: checkpoint_duration_seconds > 300
    for: 1m
    annotations:
      summary: "Checkpoint taking too long"

  - alert: CheckpointStorageFull
    expr: checkpoint_storage_used_percent > 90
    for: 5m
    annotations:
      summary: "Checkpoint storage nearly full"
```

---

## Alternatives and Future Directions

### 1. CRIU (Checkpoint/Restore In Userspace)

More advanced than DMTCP, but similar GPU limitations.

```bash
# Install CRIU
sudo apt-get install criu

# Checkpoint process
sudo criu dump -t <pid> --images-dir /checkpoints/job-123 --shell-job

# Restore
sudo criu restore --images-dir /checkpoints/job-123 --shell-job
```

### 2. Container-Native Checkpointing

Docker experimental feature:

```bash
# Enable experimental features
echo '{"experimental": true}' | sudo tee /etc/docker/daemon.json

# Checkpoint container
docker checkpoint create my-container checkpoint1

# Restore
docker start --checkpoint checkpoint1 my-container
```

### 3. Framework-Specific Solutions

- **PyTorch**: Built-in checkpointing
- **TensorFlow**: tf.train.Checkpoint
- **JAX**: jax.experimental.checkify
- **Ray**: ray.experimental.state.save/load

### 4. Future: True GPU Checkpoint/Restart

Research directions:
- **CUDA Multi-Process Service (MPS)** enhancements
- **Unified Memory** checkpoint support
- **GPU driver-level** checkpoint APIs (NVIDIA roadmap)
- **CXL memory** for faster checkpoint/restore

---

## References

### DMTCP
- **Official Website**: https://dmtcp.sourceforge.io/
- **Documentation**: https://github.com/dmtcp/dmtcp
- **NERSC Guide**: https://docs.nersc.gov/development/checkpoint-restart/dmtcp/

### GPU Checkpointing Research
- **CRAC Paper**: https://www.ccs.neu.edu/home/gene/papers/sc20.pdf
- **NVIDIA MPS**: https://docs.nvidia.com/deploy/mps/
- **GPU Checkpoint Survey**: https://dl.acm.org/doi/10.1145/3624062.3624254

### Alternative Technologies
- **CRIU**: https://criu.org/
- **Docker Checkpoint**: https://docs.docker.com/engine/reference/commandline/checkpoint/
- **Kubernetes Checkpoint**: https://kubernetes.io/blog/2022/12/05/forensic-container-checkpointing-alpha/

### Application-Level Checkpointing
- **PyTorch**: https://pytorch.org/tutorials/recipes/recipes/saving_and_loading_checkpoints_for_inference.html
- **TensorFlow**: https://www.tensorflow.org/guide/checkpoint
- **MLflow**: https://mlflow.org/docs/latest/tracking.html

---

## Team Requirements

**Systems Programmer** (Primary, 30 hours/week):
- C/Linux systems programming
- Process management and ptrace
- DMTCP internals

**ML/GPU Engineer** (Primary, 30 hours/week):
- CUDA programming
- Deep learning frameworks
- GPU architecture

**DevOps Engineer** (Secondary, 20 hours/week):
- Deployment automation
- Storage management
- Monitoring setup

**Researcher** (Consulting, 10 hours/week):
- GPU checkpoint research
- Novel solutions exploration
- Performance optimization

**Total Estimated Effort**: 3-4 weeks for DMTCP integration, ongoing research for GPU checkpointing

---

*Last Updated: 2025-10-14*
*Version: 1.0*
