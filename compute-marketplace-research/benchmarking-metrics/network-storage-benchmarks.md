# Network and Storage Benchmarking Guide

## Table of Contents
1. [Overview](#overview)
2. [iPerf3 Network Benchmarking](#iperf3-network-benchmarking)
3. [FIO Storage Benchmarking](#fio-storage-benchmarking)
4. [Automated Testing](#automated-testing)
5. [Result Interpretation](#result-interpretation)
6. [Integration Examples](#integration-examples)
7. [Troubleshooting](#troubleshooting)

---

## Overview

Network and storage performance are critical for compute marketplace providers. This guide covers comprehensive testing using industry-standard tools: iPerf3 for network and FIO (Flexible I/O Tester) for storage.

### Why Network and Storage Benchmarks?

**Network Performance Matters For:**
- Distributed training and inference
- Data transfer between nodes
- Remote storage access
- Multi-node HPC workloads
- Real-time streaming applications

**Storage Performance Matters For:**
- Dataset loading for ML training
- Database workloads
- Log aggregation
- Checkpoint/snapshot operations
- Large file processing

### Benchmark Tools

| Tool | Purpose | Metrics | Execution Time |
|------|---------|---------|----------------|
| iPerf3 | Network throughput/latency | Bandwidth, jitter, packet loss | 30-120 seconds |
| FIO | Storage I/O performance | IOPS, bandwidth, latency | 60-300 seconds |

---

## iPerf3 Network Benchmarking

### Overview

iPerf3 is the de facto standard for measuring TCP, UDP, and SCTP network bandwidth. It supports:
- TCP throughput testing
- UDP bandwidth, jitter, and packet loss testing
- Bidirectional testing
- Multiple parallel streams
- JSON output for automation

### Installation

#### Ubuntu/Debian

```bash
# Install from package manager
sudo apt-get update
sudo apt-get install -y iperf3

# Verify installation
iperf3 --version
# Output: iperf 3.14 (or later)
```

#### From Source

```bash
# Build latest version from source
wget https://downloads.es.net/pub/iperf/iperf-3.14.tar.gz
tar xzf iperf-3.14.tar.gz
cd iperf-3.14
./configure
make
sudo make install
sudo ldconfig
```

#### Docker

```dockerfile
FROM ubuntu:22.04

RUN apt-get update && \
    apt-get install -y iperf3 && \
    rm -rf /var/lib/apt/lists/*

# Server mode by default
CMD ["iperf3", "-s"]
```

### Server Setup

iPerf3 requires a server component to test against.

#### Basic Server Setup

```bash
# Start iPerf3 server
iperf3 -s

# Server on specific port
iperf3 -s -p 5201

# Server with JSON output
iperf3 -s --json

# Server as daemon
iperf3 -s -D

# Server with specific interface
iperf3 -s -B 192.168.1.100
```

#### Production Server Setup

```bash
#!/bin/bash
# setup_iperf3_server.sh

set -e

# Install iperf3
sudo apt-get install -y iperf3

# Create systemd service
cat <<'EOF' | sudo tee /etc/systemd/system/iperf3.service
[Unit]
Description=iPerf3 Server
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/iperf3 -s -p 5201
Restart=always
RestartSec=3
User=iperf3
Group=iperf3

[Install]
WantedBy=multi-user.target
EOF

# Create iperf3 user
sudo useradd -r -s /bin/false iperf3

# Start and enable service
sudo systemctl daemon-reload
sudo systemctl enable iperf3.service
sudo systemctl start iperf3.service

# Verify service is running
sudo systemctl status iperf3.service

echo "✓ iPerf3 server installed and running on port 5201"
```

#### Multi-Instance Server

For high-scale testing, run multiple server instances:

```bash
#!/bin/bash
# start_iperf3_multi_servers.sh

NUM_SERVERS=8
BASE_PORT=5201

for i in $(seq 0 $((NUM_SERVERS - 1))); do
    PORT=$((BASE_PORT + i))
    echo "Starting iPerf3 server on port $PORT"
    iperf3 -s -p $PORT -D --logfile /var/log/iperf3_server_${PORT}.log
done

echo "Started $NUM_SERVERS iPerf3 servers on ports ${BASE_PORT}-$((BASE_PORT + NUM_SERVERS - 1))"
```

### Client Testing

#### Basic TCP Throughput Test

```bash
# Test to server for 30 seconds
iperf3 -c SERVER_IP -t 30

# Output example:
# [  5]   0.00-30.00  sec  35.1 GBytes  10.1 Gbits/sec  receiver

# Test with multiple parallel streams (simulates concurrent connections)
iperf3 -c SERVER_IP -t 30 -P 8

# Bidirectional test (simultaneous send/receive)
iperf3 -c SERVER_IP -t 30 --bidir

# Reverse mode (server sends to client)
iperf3 -c SERVER_IP -t 30 -R
```

#### UDP Testing

```bash
# UDP test with 1 Gbps target bandwidth
iperf3 -c SERVER_IP -u -b 1G -t 30

# UDP with specific packet size
iperf3 -c SERVER_IP -u -b 1G -l 1400 -t 30

# UDP test shows packet loss and jitter
# Output example:
# [  5]   0.00-30.00  sec  3.57 GBytes  1.02 Gbits/sec  0.015 ms  0/261632 (0%)
#                           ^^^^^^^^^^  ^^^^^^^^^^^^^^  ^^^^^^^  ^^^^^^^^^^^
#                           Transferred Bandwidth       Jitter   Lost/Total (%)
```

#### JSON Output for Automation

```bash
# JSON output
iperf3 -c SERVER_IP -t 30 -J > results.json

# Pretty-print JSON
iperf3 -c SERVER_IP -t 30 -J | jq .

# Extract specific metrics
iperf3 -c SERVER_IP -t 30 -J | jq '.end.sum_sent.bits_per_second'
```

### Comprehensive Test Suite

```bash
#!/bin/bash
# comprehensive_network_test.sh

SERVER_IP=$1
DURATION=30
RESULTS_DIR="/var/benchmark/network"

if [ -z "$SERVER_IP" ]; then
    echo "Usage: $0 <server_ip>"
    exit 1
fi

mkdir -p ${RESULTS_DIR}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=== Comprehensive Network Benchmark ==="
echo "Server: ${SERVER_IP}"
echo "Duration: ${DURATION}s per test"
echo ""

# Test 1: Single stream TCP
echo "Test 1: Single stream TCP"
iperf3 -c ${SERVER_IP} -t ${DURATION} -J > ${RESULTS_DIR}/tcp_single_${TIMESTAMP}.json
RESULT=$(jq -r '.end.sum_sent.bits_per_second' ${RESULTS_DIR}/tcp_single_${TIMESTAMP}.json)
GBPS=$(echo "scale=2; $RESULT / 1000000000" | bc)
echo "  Throughput: ${GBPS} Gbps"
echo ""

# Test 2: Multiple parallel streams (8)
echo "Test 2: Multiple parallel streams (8)"
iperf3 -c ${SERVER_IP} -t ${DURATION} -P 8 -J > ${RESULTS_DIR}/tcp_parallel8_${TIMESTAMP}.json
RESULT=$(jq -r '.end.sum_sent.bits_per_second' ${RESULTS_DIR}/tcp_parallel8_${TIMESTAMP}.json)
GBPS=$(echo "scale=2; $RESULT / 1000000000" | bc)
echo "  Throughput: ${GBPS} Gbps"
echo ""

# Test 3: Bidirectional
echo "Test 3: Bidirectional (simultaneous send/receive)"
iperf3 -c ${SERVER_IP} -t ${DURATION} --bidir -J > ${RESULTS_DIR}/tcp_bidir_${TIMESTAMP}.json
SEND=$(jq -r '.end.sum_sent.bits_per_second' ${RESULTS_DIR}/tcp_bidir_${TIMESTAMP}.json)
RECV=$(jq -r '.end.sum_received.bits_per_second' ${RESULTS_DIR}/tcp_bidir_${TIMESTAMP}.json)
SEND_GBPS=$(echo "scale=2; $SEND / 1000000000" | bc)
RECV_GBPS=$(echo "scale=2; $RECV / 1000000000" | bc)
echo "  Send: ${SEND_GBPS} Gbps"
echo "  Receive: ${RECV_GBPS} Gbps"
echo ""

# Test 4: UDP bandwidth test
echo "Test 4: UDP (1 Gbps target)"
iperf3 -c ${SERVER_IP} -t ${DURATION} -u -b 1G -J > ${RESULTS_DIR}/udp_1g_${TIMESTAMP}.json
BW=$(jq -r '.end.sum.bits_per_second' ${RESULTS_DIR}/udp_1g_${TIMESTAMP}.json)
JITTER=$(jq -r '.end.sum.jitter_ms' ${RESULTS_DIR}/udp_1g_${TIMESTAMP}.json)
LOST=$(jq -r '.end.sum.lost_percent' ${RESULTS_DIR}/udp_1g_${TIMESTAMP}.json)
BW_MBPS=$(echo "scale=2; $BW / 1000000" | bc)
echo "  Bandwidth: ${BW_MBPS} Mbps"
echo "  Jitter: ${JITTER} ms"
echo "  Packet loss: ${LOST}%"
echo ""

# Test 5: Small packet latency (TCP)
echo "Test 5: Small packet latency"
iperf3 -c ${SERVER_IP} -t ${DURATION} -l 64 -J > ${RESULTS_DIR}/tcp_latency_${TIMESTAMP}.json
echo "  Complete (see detailed results in JSON)"
echo ""

echo "=== Tests Complete ==="
echo "Results saved to: ${RESULTS_DIR}"

# Generate summary report
cat > ${RESULTS_DIR}/summary_${TIMESTAMP}.txt <<EOF
Network Benchmark Summary
Generated: $(date)
Server: ${SERVER_IP}

Single Stream TCP: ${GBPS} Gbps
Parallel (8 streams): ${GBPS} Gbps
Bidirectional Send: ${SEND_GBPS} Gbps
Bidirectional Recv: ${RECV_GBPS} Gbps
UDP Bandwidth: ${BW_MBPS} Mbps
UDP Jitter: ${JITTER} ms
UDP Packet Loss: ${LOST}%
EOF

cat ${RESULTS_DIR}/summary_${TIMESTAMP}.txt
```

### Python Wrapper

```python
# iperf3_runner.py
import subprocess
import json
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class NetworkTestResult:
    bandwidth_gbps: float
    jitter_ms: Optional[float] = None
    packet_loss_percent: Optional[float] = None
    retransmits: Optional[int] = None

class IPerf3Runner:
    def __init__(self, server_ip: str, port: int = 5201):
        self.server_ip = server_ip
        self.port = port

    def run_tcp_test(
        self,
        duration: int = 30,
        parallel_streams: int = 1,
        bidirectional: bool = False,
        reverse: bool = False
    ) -> NetworkTestResult:
        """
        Run TCP bandwidth test.

        Args:
            duration: Test duration in seconds
            parallel_streams: Number of parallel streams
            bidirectional: Test both directions simultaneously
            reverse: Server sends to client

        Returns:
            NetworkTestResult with bandwidth and retransmit count
        """
        cmd = [
            "iperf3",
            "-c", self.server_ip,
            "-p", str(self.port),
            "-t", str(duration),
            "-J"
        ]

        if parallel_streams > 1:
            cmd.extend(["-P", str(parallel_streams)])

        if bidirectional:
            cmd.append("--bidir")

        if reverse:
            cmd.append("-R")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=duration + 30
            )

            if result.returncode != 0:
                raise RuntimeError(f"iPerf3 failed: {result.stderr}")

            data = json.loads(result.stdout)

            # Extract metrics
            bandwidth_bps = data["end"]["sum_sent"]["bits_per_second"]
            bandwidth_gbps = bandwidth_bps / 1e9

            retransmits = data["end"]["sum_sent"].get("retransmits", 0)

            return NetworkTestResult(
                bandwidth_gbps=bandwidth_gbps,
                retransmits=retransmits
            )

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Test timed out after {duration + 30} seconds")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse iPerf3 output: {e}")

    def run_udp_test(
        self,
        duration: int = 30,
        bandwidth: str = "1G",
        packet_size: int = 1400
    ) -> NetworkTestResult:
        """
        Run UDP test with specified bandwidth target.

        Args:
            duration: Test duration in seconds
            bandwidth: Target bandwidth (e.g., "1G", "100M")
            packet_size: UDP packet size in bytes

        Returns:
            NetworkTestResult with bandwidth, jitter, and packet loss
        """
        cmd = [
            "iperf3",
            "-c", self.server_ip,
            "-p", str(self.port),
            "-t", str(duration),
            "-u",
            "-b", bandwidth,
            "-l", str(packet_size),
            "-J"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=duration + 30
            )

            if result.returncode != 0:
                raise RuntimeError(f"iPerf3 UDP test failed: {result.stderr}")

            data = json.loads(result.stdout)

            # Extract UDP metrics
            end_sum = data["end"]["sum"]
            bandwidth_bps = end_sum["bits_per_second"]
            bandwidth_gbps = bandwidth_bps / 1e9
            jitter_ms = end_sum["jitter_ms"]
            packet_loss_percent = end_sum["lost_percent"]

            return NetworkTestResult(
                bandwidth_gbps=bandwidth_gbps,
                jitter_ms=jitter_ms,
                packet_loss_percent=packet_loss_percent
            )

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"UDP test timed out after {duration + 30} seconds")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse iPerf3 output: {e}")

    def comprehensive_test(self) -> Dict:
        """Run comprehensive network test suite."""
        results = {}

        print("Running comprehensive network tests...")

        # Single stream TCP
        print("  1. Single stream TCP...")
        results["tcp_single"] = self.run_tcp_test(duration=30)

        # Parallel streams TCP
        print("  2. Parallel streams (8)...")
        results["tcp_parallel"] = self.run_tcp_test(duration=30, parallel_streams=8)

        # Bidirectional TCP
        print("  3. Bidirectional...")
        results["tcp_bidir"] = self.run_tcp_test(duration=30, bidirectional=True)

        # UDP test
        print("  4. UDP test...")
        results["udp"] = self.run_udp_test(duration=30, bandwidth="1G")

        print("✓ All tests complete")

        return results

    def measure_latency(self, count: int = 100) -> float:
        """
        Measure network latency using ping.

        Args:
            count: Number of ping packets

        Returns:
            Average RTT in milliseconds
        """
        cmd = ["ping", "-c", str(count), "-q", self.server_ip]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Ping failed: {result.stderr}")

        # Parse output: "rtt min/avg/max/mdev = 0.123/0.456/0.789/0.012 ms"
        for line in result.stdout.split('\n'):
            if 'rtt' in line.lower():
                parts = line.split('=')[1].strip().split('/')
                avg_rtt = float(parts[1])
                return avg_rtt

        raise RuntimeError("Could not parse ping output")


# Example usage
if __name__ == "__main__":
    runner = IPerf3Runner(server_ip="10.0.0.100")

    # Run comprehensive tests
    results = runner.comprehensive_test()

    print("\n=== Results Summary ===")
    print(f"Single Stream: {results['tcp_single'].bandwidth_gbps:.2f} Gbps")
    print(f"Parallel (8): {results['tcp_parallel'].bandwidth_gbps:.2f} Gbps")
    print(f"Bidirectional: {results['tcp_bidir'].bandwidth_gbps:.2f} Gbps")
    print(f"UDP Bandwidth: {results['udp'].bandwidth_gbps:.2f} Gbps")
    print(f"UDP Jitter: {results['udp'].jitter_ms:.3f} ms")
    print(f"UDP Packet Loss: {results['udp'].packet_loss_percent:.2f}%")

    # Measure latency
    latency = runner.measure_latency(count=100)
    print(f"Average Latency: {latency:.3f} ms")
```

---

## FIO Storage Benchmarking

### Overview

FIO (Flexible I/O Tester) is the industry-standard tool for storage benchmarking. It supports:
- Multiple I/O engines (libaio, io_uring, sync, etc.)
- Random and sequential I/O patterns
- Read, write, and mixed workloads
- Customizable block sizes and queue depths
- Detailed latency histograms

### Installation

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y fio

# Verify installation
fio --version
# Output: fio-3.35 (or later)

# From source (for latest version)
git clone https://github.com/axboe/fio.git
cd fio
./configure
make
sudo make install
```

### Basic Usage

```bash
# Random read test
fio --name=randread --rw=randread --bs=4k --size=1G --numjobs=1 --runtime=60 --time_based

# Sequential write test
fio --name=seqwrite --rw=write --bs=1M --size=10G --numjobs=1 --runtime=60 --time_based

# Random write test (most common for benchmarking)
fio --name=randwrite --rw=randwrite --bs=4k --size=1G --numjobs=4 --runtime=60 --time_based
```

### Test Profiles

#### Profile 1: Random Read (IOPS)

Tests random read IOPS, common for databases and metadata operations.

```ini
# profile_randread.fio
[global]
ioengine=libaio
direct=1
size=10G
runtime=60
time_based
group_reporting

[randread-4k]
rw=randread
bs=4k
iodepth=32
numjobs=4
```

Run: `fio profile_randread.fio`

#### Profile 2: Random Write (IOPS)

Tests random write IOPS, critical for write-heavy workloads.

```ini
# profile_randwrite.fio
[global]
ioengine=libaio
direct=1
size=10G
runtime=60
time_based
group_reporting

[randwrite-4k]
rw=randwrite
bs=4k
iodepth=32
numjobs=4
```

#### Profile 3: Sequential Read (Throughput)

Tests sequential read bandwidth, important for large file reads.

```ini
# profile_seqread.fio
[global]
ioengine=libaio
direct=1
size=10G
runtime=60
time_based
group_reporting

[seqread-1m]
rw=read
bs=1M
iodepth=64
numjobs=1
```

#### Profile 4: Sequential Write (Throughput)

Tests sequential write bandwidth.

```ini
# profile_seqwrite.fio
[global]
ioengine=libaio
direct=1
size=10G
runtime=60
time_based
group_reporting

[seqwrite-1m]
rw=write
bs=1M
iodepth=64
numjobs=1
```

#### Profile 5: Mixed Random Read/Write (70/30)

Tests mixed workload, common for databases.

```ini
# profile_randrw.fio
[global]
ioengine=libaio
direct=1
size=10G
runtime=60
time_based
group_reporting

[randrw-70-30]
rw=randrw
rwmixread=70
bs=4k
iodepth=32
numjobs=4
```

### Comprehensive Test Suite

```bash
#!/bin/bash
# comprehensive_storage_test.sh

TEST_DIR=${1:-/mnt/test}
RESULTS_DIR="/var/benchmark/storage"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create directories
mkdir -p ${TEST_DIR}
mkdir -p ${RESULTS_DIR}

echo "=== Comprehensive Storage Benchmark ==="
echo "Test directory: ${TEST_DIR}"
echo "Results directory: ${RESULTS_DIR}"
echo ""

# Verify write permissions
if [ ! -w ${TEST_DIR} ]; then
    echo "Error: No write permission to ${TEST_DIR}"
    exit 1
fi

# Test 1: Random Read IOPS
echo "Test 1: Random Read IOPS (4K)"
fio --name=randread \
    --ioengine=libaio \
    --direct=1 \
    --rw=randread \
    --bs=4k \
    --size=10G \
    --numjobs=4 \
    --iodepth=32 \
    --runtime=60 \
    --time_based \
    --group_reporting \
    --directory=${TEST_DIR} \
    --output-format=json \
    --output=${RESULTS_DIR}/randread_${TIMESTAMP}.json

IOPS=$(jq -r '.jobs[0].read.iops' ${RESULTS_DIR}/randread_${TIMESTAMP}.json)
printf "  IOPS: %.0f\n\n" $IOPS

# Test 2: Random Write IOPS
echo "Test 2: Random Write IOPS (4K)"
fio --name=randwrite \
    --ioengine=libaio \
    --direct=1 \
    --rw=randwrite \
    --bs=4k \
    --size=10G \
    --numjobs=4 \
    --iodepth=32 \
    --runtime=60 \
    --time_based \
    --group_reporting \
    --directory=${TEST_DIR} \
    --output-format=json \
    --output=${RESULTS_DIR}/randwrite_${TIMESTAMP}.json

IOPS=$(jq -r '.jobs[0].write.iops' ${RESULTS_DIR}/randwrite_${TIMESTAMP}.json)
printf "  IOPS: %.0f\n\n" $IOPS

# Test 3: Sequential Read Throughput
echo "Test 3: Sequential Read Throughput (1M)"
fio --name=seqread \
    --ioengine=libaio \
    --direct=1 \
    --rw=read \
    --bs=1M \
    --size=10G \
    --numjobs=1 \
    --iodepth=64 \
    --runtime=60 \
    --time_based \
    --group_reporting \
    --directory=${TEST_DIR} \
    --output-format=json \
    --output=${RESULTS_DIR}/seqread_${TIMESTAMP}.json

BW=$(jq -r '.jobs[0].read.bw_bytes' ${RESULTS_DIR}/seqread_${TIMESTAMP}.json)
BW_GBPS=$(echo "scale=2; $BW / 1000000000" | bc)
echo "  Bandwidth: ${BW_GBPS} GB/s"
echo ""

# Test 4: Sequential Write Throughput
echo "Test 4: Sequential Write Throughput (1M)"
fio --name=seqwrite \
    --ioengine=libaio \
    --direct=1 \
    --rw=write \
    --bs=1M \
    --size=10G \
    --numjobs=1 \
    --iodepth=64 \
    --runtime=60 \
    --time_based \
    --group_reporting \
    --directory=${TEST_DIR} \
    --output-format=json \
    --output=${RESULTS_DIR}/seqwrite_${TIMESTAMP}.json

BW=$(jq -r '.jobs[0].write.bw_bytes' ${RESULTS_DIR}/seqwrite_${TIMESTAMP}.json)
BW_GBPS=$(echo "scale=2; $BW / 1000000000" | bc)
echo "  Bandwidth: ${BW_GBPS} GB/s"
echo ""

# Test 5: Mixed Random R/W (70/30)
echo "Test 5: Mixed Random R/W (70/30, 4K)"
fio --name=randrw \
    --ioengine=libaio \
    --direct=1 \
    --rw=randrw \
    --rwmixread=70 \
    --bs=4k \
    --size=10G \
    --numjobs=4 \
    --iodepth=32 \
    --runtime=60 \
    --time_based \
    --group_reporting \
    --directory=${TEST_DIR} \
    --output-format=json \
    --output=${RESULTS_DIR}/randrw_${TIMESTAMP}.json

READ_IOPS=$(jq -r '.jobs[0].read.iops' ${RESULTS_DIR}/randrw_${TIMESTAMP}.json)
WRITE_IOPS=$(jq -r '.jobs[0].write.iops' ${RESULTS_DIR}/randrw_${TIMESTAMP}.json)
printf "  Read IOPS: %.0f\n" $READ_IOPS
printf "  Write IOPS: %.0f\n\n" $WRITE_IOPS

# Clean up test files
echo "Cleaning up test files..."
rm -rf ${TEST_DIR}/randread.* ${TEST_DIR}/randwrite.* ${TEST_DIR}/seqread.* ${TEST_DIR}/seqwrite.* ${TEST_DIR}/randrw.*

echo "=== Tests Complete ==="
echo "Results saved to: ${RESULTS_DIR}"
```

### Python Wrapper

```python
# fio_runner.py
import subprocess
import json
from typing import Dict, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class StorageTestResult:
    iops: Optional[float] = None
    bandwidth_mbps: Optional[float] = None
    latency_avg_us: Optional[float] = None
    latency_p95_us: Optional[float] = None
    latency_p99_us: Optional[float] = None

class FIORunner:
    def __init__(self, test_dir: str = "/mnt/test"):
        self.test_dir = Path(test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)

        # Verify write permissions
        if not self.test_dir.is_dir() or not self.test_dir.exists():
            raise RuntimeError(f"Test directory {test_dir} not accessible")

    def run_test(
        self,
        test_name: str,
        rw_mode: str,
        block_size: str = "4k",
        size: str = "10G",
        iodepth: int = 32,
        numjobs: int = 4,
        runtime: int = 60,
        ioengine: str = "libaio",
        direct: bool = True
    ) -> StorageTestResult:
        """
        Run FIO test with specified parameters.

        Args:
            test_name: Name for the test
            rw_mode: I/O pattern (randread, randwrite, read, write, randrw)
            block_size: Block size (e.g., "4k", "1M")
            size: File size
            iodepth: I/O depth
            numjobs: Number of parallel jobs
            runtime: Runtime in seconds
            ioengine: I/O engine (libaio, io_uring, sync)
            direct: Use direct I/O (bypasses page cache)

        Returns:
            StorageTestResult with metrics
        """
        output_file = self.test_dir / f"{test_name}_result.json"

        cmd = [
            "fio",
            f"--name={test_name}",
            f"--ioengine={ioengine}",
            f"--rw={rw_mode}",
            f"--bs={block_size}",
            f"--size={size}",
            f"--numjobs={numjobs}",
            f"--iodepth={iodepth}",
            f"--runtime={runtime}",
            "--time_based",
            "--group_reporting",
            f"--directory={self.test_dir}",
            "--output-format=json",
            f"--output={output_file}"
        ]

        if direct:
            cmd.append("--direct=1")

        try:
            print(f"Running FIO test: {test_name}...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=runtime + 60
            )

            if result.returncode != 0:
                raise RuntimeError(f"FIO test failed: {result.stderr}")

            # Parse results
            with open(output_file, 'r') as f:
                data = json.load(f)

            return self._parse_fio_result(data, rw_mode)

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"FIO test timed out after {runtime + 60} seconds")
        except Exception as e:
            raise RuntimeError(f"FIO test error: {e}")
        finally:
            # Clean up test files
            self._cleanup_test_files(test_name)

    def _parse_fio_result(self, data: Dict, rw_mode: str) -> StorageTestResult:
        """Parse FIO JSON output."""
        job = data["jobs"][0]

        result = StorageTestResult()

        # Determine which metrics to extract based on rw_mode
        if "read" in rw_mode and "write" not in rw_mode:
            metrics = job["read"]
        elif "write" in rw_mode and "read" not in rw_mode:
            metrics = job["write"]
        else:
            # Mixed workload - use read metrics
            metrics = job["read"]

        result.iops = metrics.get("iops", 0)
        result.bandwidth_mbps = metrics.get("bw_bytes", 0) / (1024 * 1024)
        result.latency_avg_us = metrics.get("lat_ns", {}).get("mean", 0) / 1000
        result.latency_p95_us = metrics.get("clat_ns", {}).get("percentile", {}).get("95.000000", 0) / 1000
        result.latency_p99_us = metrics.get("clat_ns", {}).get("percentile", {}).get("99.000000", 0) / 1000

        return result

    def _cleanup_test_files(self, test_name: str):
        """Clean up FIO test files."""
        for file in self.test_dir.glob(f"{test_name}.*"):
            try:
                file.unlink()
            except:
                pass

    def run_comprehensive_tests(self) -> Dict:
        """Run comprehensive storage test suite."""
        results = {}

        print("Running comprehensive storage tests...")

        # Test 1: Random Read IOPS
        print("\n1. Random Read IOPS (4K)")
        results["randread_4k"] = self.run_test(
            test_name="randread",
            rw_mode="randread",
            block_size="4k",
            iodepth=32,
            numjobs=4,
            runtime=60
        )
        print(f"   IOPS: {results['randread_4k'].iops:.0f}")

        # Test 2: Random Write IOPS
        print("\n2. Random Write IOPS (4K)")
        results["randwrite_4k"] = self.run_test(
            test_name="randwrite",
            rw_mode="randwrite",
            block_size="4k",
            iodepth=32,
            numjobs=4,
            runtime=60
        )
        print(f"   IOPS: {results['randwrite_4k'].iops:.0f}")

        # Test 3: Sequential Read Throughput
        print("\n3. Sequential Read Throughput (1M)")
        results["seqread_1m"] = self.run_test(
            test_name="seqread",
            rw_mode="read",
            block_size="1M",
            iodepth=64,
            numjobs=1,
            runtime=60
        )
        print(f"   Bandwidth: {results['seqread_1m'].bandwidth_mbps:.0f} MB/s")

        # Test 4: Sequential Write Throughput
        print("\n4. Sequential Write Throughput (1M)")
        results["seqwrite_1m"] = self.run_test(
            test_name="seqwrite",
            rw_mode="write",
            block_size="1M",
            iodepth=64,
            numjobs=1,
            runtime=60
        )
        print(f"   Bandwidth: {results['seqwrite_1m'].bandwidth_mbps:.0f} MB/s")

        # Test 5: Mixed workload
        print("\n5. Mixed Random R/W (70/30, 4K)")
        results["randrw_7030"] = self.run_test(
            test_name="randrw",
            rw_mode="randrw",
            block_size="4k",
            iodepth=32,
            numjobs=4,
            runtime=60
        )
        print(f"   IOPS: {results['randrw_7030'].iops:.0f}")

        print("\n✓ All tests complete")

        return results


# Example usage
if __name__ == "__main__":
    import sys

    test_dir = sys.argv[1] if len(sys.argv) > 1 else "/mnt/test"

    runner = FIORunner(test_dir=test_dir)

    # Run comprehensive tests
    results = runner.run_comprehensive_tests()

    # Print summary
    print("\n=== Storage Benchmark Summary ===")
    print(f"Random Read (4K):     {results['randread_4k'].iops:>10.0f} IOPS")
    print(f"Random Write (4K):    {results['randwrite_4k'].iops:>10.0f} IOPS")
    print(f"Sequential Read (1M): {results['seqread_1m'].bandwidth_mbps:>10.0f} MB/s")
    print(f"Sequential Write (1M):{results['seqwrite_1m'].bandwidth_mbps:>10.0f} MB/s")
    print(f"Mixed R/W (70/30):    {results['randrw_7030'].iops:>10.0f} IOPS")
```

---

## Automated Testing

### Combined Network and Storage Test

```python
# combined_benchmark.py
from dataclasses import dataclass
from typing import Dict
import json
from datetime import datetime

@dataclass
class ProviderBenchmarkReport:
    provider_id: str
    timestamp: str
    network: Dict
    storage: Dict
    verdict: Dict

class CombinedBenchmark:
    def __init__(
        self,
        iperf_server: str,
        storage_test_dir: str = "/mnt/test"
    ):
        self.network_runner = IPerf3Runner(server_ip=iperf_server)
        self.storage_runner = FIORunner(test_dir=storage_test_dir)

    def benchmark_provider(self, provider_id: str) -> ProviderBenchmarkReport:
        """
        Run comprehensive network and storage benchmarks.

        Args:
            provider_id: Provider identifier

        Returns:
            Complete benchmark report
        """
        print(f"=== Benchmarking Provider: {provider_id} ===\n")

        timestamp = datetime.utcnow().isoformat()

        # Run network tests
        print("Running network tests...")
        network_results = self.network_runner.comprehensive_test()

        # Run storage tests
        print("\nRunning storage tests...")
        storage_results = self.storage_runner.run_comprehensive_tests()

        # Determine verdict
        verdict = self._determine_verdict(network_results, storage_results)

        report = ProviderBenchmarkReport(
            provider_id=provider_id,
            timestamp=timestamp,
            network={
                "tcp_single_gbps": network_results["tcp_single"].bandwidth_gbps,
                "tcp_parallel_gbps": network_results["tcp_parallel"].bandwidth_gbps,
                "udp_gbps": network_results["udp"].bandwidth_gbps,
                "udp_jitter_ms": network_results["udp"].jitter_ms,
                "udp_packet_loss_pct": network_results["udp"].packet_loss_percent
            },
            storage={
                "randread_iops": storage_results["randread_4k"].iops,
                "randwrite_iops": storage_results["randwrite_4k"].iops,
                "seqread_mbps": storage_results["seqread_1m"].bandwidth_mbps,
                "seqwrite_mbps": storage_results["seqwrite_1m"].bandwidth_mbps
            },
            verdict=verdict
        )

        # Save report
        self._save_report(report)

        return report

    def _determine_verdict(
        self,
        network_results: Dict,
        storage_results: Dict
    ) -> Dict:
        """Determine if provider meets minimum requirements."""
        verdict = {
            "status": "PASS",
            "issues": []
        }

        # Network requirements
        if network_results["tcp_single"].bandwidth_gbps < 1.0:
            verdict["status"] = "FAIL"
            verdict["issues"].append("Network bandwidth below 1 Gbps")

        if network_results["udp"].packet_loss_percent > 1.0:
            verdict["status"] = "WARNING"
            verdict["issues"].append("UDP packet loss exceeds 1%")

        # Storage requirements
        if storage_results["randread_4k"].iops < 1000:
            verdict["status"] = "FAIL"
            verdict["issues"].append("Random read IOPS below 1000")

        if storage_results["randwrite_4k"].iops < 500:
            verdict["status"] = "FAIL"
            verdict["issues"].append("Random write IOPS below 500")

        if storage_results["seqread_1m"].bandwidth_mbps < 100:
            verdict["status"] = "FAIL"
            verdict["issues"].append("Sequential read bandwidth below 100 MB/s")

        if not verdict["issues"]:
            verdict["message"] = "All benchmarks passed"
        else:
            verdict["message"] = f"{len(verdict['issues'])} issue(s) found"

        return verdict

    def _save_report(self, report: ProviderBenchmarkReport):
        """Save report to JSON file."""
        filename = f"/var/benchmark/reports/{report.provider_id}_{report.timestamp.replace(':', '-')}.json"

        Path(filename).parent.mkdir(parents=True, exist_ok=True)

        with open(filename, 'w') as f:
            json.dump(report.__dict__, f, indent=2)

        print(f"\nReport saved: {filename}")


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python combined_benchmark.py <provider_id> <iperf_server>")
        sys.exit(1)

    provider_id = sys.argv[1]
    iperf_server = sys.argv[2]

    benchmark = CombinedBenchmark(
        iperf_server=iperf_server,
        storage_test_dir="/mnt/test"
    )

    report = benchmark.benchmark_provider(provider_id)

    # Print summary
    print("\n=== Benchmark Summary ===")
    print(f"Provider: {report.provider_id}")
    print(f"Verdict: {report.verdict['status']}")
    print(f"\nNetwork:")
    print(f"  TCP Bandwidth: {report.network['tcp_single_gbps']:.2f} Gbps")
    print(f"  UDP Jitter: {report.network['udp_jitter_ms']:.3f} ms")
    print(f"  Packet Loss: {report.network['udp_packet_loss_pct']:.2f}%")
    print(f"\nStorage:")
    print(f"  Random Read: {report.storage['randread_iops']:.0f} IOPS")
    print(f"  Random Write: {report.storage['randwrite_iops']:.0f} IOPS")
    print(f"  Sequential Read: {report.storage['seqread_mbps']:.0f} MB/s")

    if report.verdict['issues']:
        print(f"\nIssues:")
        for issue in report.verdict['issues']:
            print(f"  - {issue}")
```

---

## Result Interpretation

### Network Performance Expectations

| Connection Type | Expected TCP Bandwidth | Latency | Packet Loss |
|-----------------|------------------------|---------|-------------|
| 1 GbE | 940 Mbps | <1 ms (local) | <0.1% |
| 10 GbE | 9.4 Gbps | <0.5 ms (local) | <0.01% |
| 25 GbE | 23.5 Gbps | <0.5 ms | <0.01% |
| 100 GbE | 94 Gbps | <0.3 ms | <0.001% |
| InfiniBand (100 Gbps) | 100 Gbps | <1 µs | Near zero |

### Storage Performance Expectations

| Storage Type | Random Read IOPS | Random Write IOPS | Sequential Read | Sequential Write |
|--------------|------------------|-------------------|-----------------|------------------|
| HDD (7200 RPM) | 100-200 | 100-200 | 150-200 MB/s | 150-200 MB/s |
| SATA SSD | 50K-90K | 30K-80K | 500-550 MB/s | 450-520 MB/s |
| NVMe SSD (Gen3) | 300K-500K | 200K-400K | 3.0-3.5 GB/s | 2.5-3.0 GB/s |
| NVMe SSD (Gen4) | 600K-1M | 400K-900K | 5.0-7.0 GB/s | 4.0-6.0 GB/s |
| NVMe SSD (Gen5) | 1M-1.5M | 800K-1.2M | 10-14 GB/s | 9-12 GB/s |

---

## Integration Examples

See `combined_benchmark.py` above for complete integration example.

---

## Troubleshooting

### iPerf3 Issues

#### Connection Refused

```bash
# Check if server is running
sudo systemctl status iperf3

# Check firewall
sudo ufw allow 5201/tcp

# Test with telnet
telnet <server_ip> 5201
```

#### Low Bandwidth

```bash
# Check network interface speed
ethtool eth0 | grep Speed

# Check for packet drops
netstat -i

# Monitor interface errors
ip -s link show eth0
```

### FIO Issues

#### Permission Denied

```bash
# Verify directory permissions
ls -la /mnt/test

# Run with sudo if needed
sudo fio ...
```

#### Disk Full

```bash
# Check disk space
df -h /mnt/test

# Use smaller test size
fio --size=1G ...
```

#### Low Performance

```bash
# Check if disk is under load
iostat -x 1

# Verify direct I/O is enabled
# Add --direct=1 to FIO command

# Check for RAID/LVM overhead
lsblk
```

---

## References

- [iPerf3 Official Documentation](https://iperf.fr/iperf-doc.php)
- [FIO Official Repository](https://github.com/axboe/fio)
- [FIO Documentation](https://fio.readthedocs.io/)
- [Linux Performance Analysis Tools](http://www.brendangregg.com/linuxperf.html)
