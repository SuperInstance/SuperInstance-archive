# Worker Node Agent Architecture

## Overview

The worker agent is a critical component that runs on each compute node in the marketplace, managing job execution, resource isolation, monitoring, and communication with the central orchestrator. This document outlines the architecture, technology stack, and implementation approach for a production-ready worker agent.

**Estimated Implementation Time**: 4-6 weeks
**Required Skills**: Systems programming (Go/Rust), distributed systems, containerization, Linux administration, network programming

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Component Breakdown](#component-breakdown)
3. [Technology Stack Recommendations](#technology-stack-recommendations)
4. [Communication Protocols](#communication-protocols)
5. [Job Lifecycle Management](#job-lifecycle-management)
6. [Resource Management](#resource-management)
7. [Security Considerations](#security-considerations)
8. [Implementation Examples](#implementation-examples)
9. [Deployment and Operations](#deployment-and-operations)
10. [References](#references)

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Central Orchestrator                         │
│                    (Job Scheduler / API Server)                     │
└─────────────────────────────┬───────────────────────────────────────┘
                              │ gRPC / WebSocket / REST
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
            ▼                 ▼                 ▼
  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
  │   Worker Node 1  │  │   Worker Node 2  │  │   Worker Node N  │
  │                 │  │                 │  │                 │
  │  ┌───────────┐  │  │  ┌───────────┐  │  │  ┌───────────┐  │
  │  │  Worker   │  │  │  │  Worker   │  │  │  │  Worker   │  │
  │  │  Agent    │  │  │  │  Agent    │  │  │  │  Agent    │  │
  │  └─────┬─────┘  │  │  └─────┬─────┘  │  │  └─────┬─────┘  │
  │        │        │  │        │        │  │        │        │
  │  ┌─────▼──────┐ │  │  ┌─────▼──────┐ │  │  ┌─────▼──────┐ │
  │  │ Sandbox    │ │  │  │ Sandbox    │ │  │  │ Sandbox    │ │
  │  │ Runtime    │ │  │  │ Runtime    │ │  │  │ Runtime    │ │
  │  │(Firecracker│ │  │  │(gVisor/    │ │  │  │(Docker/    │ │
  │  │ or Docker) │ │  │  │ Kata)      │ │  │  │ containerd)│ │
  │  └────────────┘ │  │  └────────────┘ │  │  └────────────┘ │
  │                 │  │                 │  │                 │
  │  [GPU] [CPU]    │  │  [GPU] [CPU]    │  │  [GPU] [CPU]    │
  │  [Memory] [Disk]│  │  [Memory] [Disk]│  │  [Memory] [Disk]│
  └─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Worker Agent Components

```
┌────────────────────────────────────────────────────────────┐
│                    Worker Agent Process                     │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Communication Module                       │  │
│  │  - gRPC Client/Server                               │  │
│  │  - Heartbeat Manager                                │  │
│  │  - Job Queue Handler                                │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                          │
│  ┌──────────────▼───────────────────────────────────────┐  │
│  │           Job Executor                               │  │
│  │  - Job Dispatcher                                    │  │
│  │  - Sandbox Manager (Firecracker/gVisor/Docker)      │  │
│  │  - Lifecycle Management (Start/Stop/Kill)           │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                          │
│  ┌──────────────▼───────────────────────────────────────┐  │
│  │       Resource Manager                               │  │
│  │  - CPU/Memory Monitor (cgroups)                     │  │
│  │  - GPU Monitor (nvidia-smi, MIG)                    │  │
│  │  - Disk I/O Tracker                                 │  │
│  │  - Network Bandwidth Monitor                        │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                          │
│  ┌──────────────▼───────────────────────────────────────┐  │
│  │       Monitoring & Logging                           │  │
│  │  - Metrics Exporter (Prometheus)                    │  │
│  │  - Log Aggregator (stdout/stderr capture)          │  │
│  │  - Health Checker                                   │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                          │
│  ┌──────────────▼───────────────────────────────────────┐  │
│  │       Storage Manager                                │  │
│  │  - Input Data Fetcher (S3/HTTP)                     │  │
│  │  - Output Data Uploader                             │  │
│  │  - Checkpoint Manager (DMTCP integration)           │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │       Security Module                              │   │
│  │  - Authentication (mTLS/API keys)                  │   │
│  │  - Sandbox Isolation Enforcement                   │   │
│  │  - Secret Management                               │   │
│  └────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Communication Module

**Responsibilities:**
- Maintain persistent connection to orchestrator
- Send periodic heartbeats with node status
- Receive job assignments
- Report job status updates

**Key Features:**
- Automatic reconnection on connection loss
- Request/response and streaming APIs
- Message queuing for offline scenarios
- TLS encryption

**Interface:**
```go
type CommunicationModule interface {
    Connect(orchestratorURL string) error
    SendHeartbeat(status NodeStatus) error
    PollJobs() ([]Job, error)
    ReportJobStatus(jobID string, status JobStatus) error
    StreamLogs(jobID string, reader io.Reader) error
    Disconnect() error
}
```

### 2. Job Executor

**Responsibilities:**
- Parse job specifications
- Prepare execution environment
- Launch jobs in isolated sandboxes
- Monitor job execution
- Handle job termination

**Key Features:**
- Multi-runtime support (Docker, Firecracker, gVisor)
- Resource limit enforcement
- Environment variable injection
- Volume mounting

**Interface:**
```go
type JobExecutor interface {
    PrepareJob(job Job) error
    StartJob(jobID string) error
    StopJob(jobID string, timeout time.Duration) error
    KillJob(jobID string) error
    GetJobStatus(jobID string) (JobStatus, error)
    CleanupJob(jobID string) error
}
```

### 3. Resource Manager

**Responsibilities:**
- Track available resources (CPU, memory, GPU)
- Monitor resource usage by running jobs
- Enforce resource limits via cgroups
- Report capacity to orchestrator

**Key Features:**
- Real-time monitoring
- cgroup integration for CPU/memory
- NVIDIA GPU tracking (nvidia-smi, NVML)
- Disk quota enforcement

**Interface:**
```go
type ResourceManager interface {
    GetAvailableResources() ResourceSpec
    GetUsedResources() ResourceSpec
    AllocateResources(jobID string, spec ResourceSpec) error
    ReleaseResources(jobID string) error
    MonitorResources(jobID string) (ResourceUsage, error)
}

type ResourceSpec struct {
    CPUCores     float64
    MemoryBytes  int64
    GPUCount     int
    GPUMemoryMB  int64
    DiskBytes    int64
    NetworkMbps  int64
}
```

### 4. Monitoring & Logging

**Responsibilities:**
- Export metrics to monitoring systems
- Capture and forward job logs
- Perform health checks
- Alert on anomalies

**Key Features:**
- Prometheus metrics endpoint
- Structured logging (JSON)
- Log streaming to orchestrator
- Self-health monitoring

**Interface:**
```go
type MonitoringModule interface {
    RecordMetric(name string, value float64, labels map[string]string)
    CaptureJobLogs(jobID string, logStream io.Reader) error
    HealthCheck() HealthStatus
    ExportMetrics() []Metric
}
```

### 5. Storage Manager

**Responsibilities:**
- Download job input data
- Upload job output data
- Manage temporary storage
- Handle checkpoints

**Key Features:**
- S3-compatible storage
- HTTP/HTTPS downloads
- Resume interrupted transfers
- Automatic cleanup

**Interface:**
```go
type StorageManager interface {
    DownloadInput(url string, dest string) error
    UploadOutput(src string, url string) error
    CreateCheckpoint(jobID string) (CheckpointID, error)
    RestoreCheckpoint(jobID string, checkpointID CheckpointID) error
    CleanupStorage(jobID string) error
}
```

### 6. Security Module

**Responsibilities:**
- Authenticate with orchestrator
- Manage secrets and credentials
- Enforce sandbox isolation
- Audit security events

**Key Features:**
- mTLS authentication
- Secret encryption at rest
- SELinux/AppArmor integration
- Audit logging

**Interface:**
```go
type SecurityModule interface {
    Authenticate() (Token, error)
    GetSecret(name string) (string, error)
    EnforceSandbox(jobID string) error
    AuditLog(event SecurityEvent) error
}
```

---

## Technology Stack Recommendations

### Programming Language: **Go**

**Why Go:**
- Excellent concurrency support (goroutines)
- Low memory footprint
- Fast compilation and deployment
- Strong ecosystem for cloud-native apps
- Built-in HTTP/gRPC support

**Alternative: Rust**
- Better performance and memory safety
- Steeper learning curve
- Growing ecosystem

### Communication: **gRPC**

**Why gRPC:**
- Efficient binary protocol (Protocol Buffers)
- Built-in streaming support
- Code generation for multiple languages
- Native HTTP/2 support

**Alternative: WebSocket**
- Simpler protocol
- Better for web-based clients

### Container Runtime: **containerd + runsc**

**Why containerd:**
- Industry standard (used by Kubernetes)
- Plugin architecture
- Multiple runtime support

**Why runsc (gVisor):**
- Strong isolation without VM overhead
- GPU support via nvproxy

**Alternative: Firecracker**
- Better isolation (full VM)
- Slightly higher overhead

### Monitoring: **Prometheus + Grafana**

**Why Prometheus:**
- Pull-based metrics
- Powerful query language (PromQL)
- Wide adoption

### Logging: **Fluentd or Vector**

**Why Fluentd:**
- Flexible log routing
- Many output plugins
- Low resource usage

### Storage: **MinIO (S3-compatible)**

**Why MinIO:**
- S3-compatible API
- Self-hosted option
- High performance

### Configuration: **YAML + Viper**

**Why YAML:**
- Human-readable
- Supports complex structures

**Why Viper:**
- Multiple config sources
- Environment variable override
- Live config reload

---

## Communication Protocols

### Protocol Definition (gRPC)

```protobuf
// worker.proto
syntax = "proto3";

package worker;

service WorkerService {
  // Bidirectional streaming for real-time communication
  rpc Stream(stream WorkerMessage) returns (stream OrchestratorMessage);

  // Unary RPCs
  rpc RegisterWorker(WorkerInfo) returns (RegistrationResponse);
  rpc Heartbeat(NodeStatus) returns (HeartbeatResponse);
  rpc ReportJobStatus(JobStatusReport) returns (Acknowledgment);
}

message WorkerInfo {
  string worker_id = 1;
  string hostname = 2;
  ResourceCapacity resources = 3;
  repeated string supported_runtimes = 4;
  map<string, string> labels = 5;
}

message ResourceCapacity {
  int32 cpu_cores = 1;
  int64 memory_bytes = 2;
  int32 gpu_count = 3;
  string gpu_model = 4;
  int64 gpu_memory_mb = 5;
  int64 disk_bytes = 6;
}

message NodeStatus {
  string worker_id = 1;
  ResourceUsage resource_usage = 2;
  repeated string running_jobs = 3;
  WorkerState state = 4;
  int64 timestamp = 5;
}

enum WorkerState {
  IDLE = 0;
  BUSY = 1;
  DRAINING = 2;
  OFFLINE = 3;
}

message ResourceUsage {
  double cpu_utilization = 1;  // 0.0 - 100.0
  int64 memory_used_bytes = 2;
  double gpu_utilization = 3;
  int64 gpu_memory_used_mb = 4;
  int64 disk_used_bytes = 5;
  int64 network_rx_bytes = 6;
  int64 network_tx_bytes = 7;
}

message JobAssignment {
  string job_id = 1;
  string image = 2;
  repeated string command = 3;
  map<string, string> environment = 4;
  ResourceSpec resources = 5;
  StorageSpec storage = 6;
  string runtime = 7;  // docker, firecracker, gvisor
  int32 timeout_seconds = 8;
}

message ResourceSpec {
  double cpu_cores = 1;
  int64 memory_bytes = 2;
  int32 gpu_count = 3;
  int64 disk_bytes = 4;
}

message StorageSpec {
  string input_url = 1;
  string output_url = 2;
  map<string, string> credentials = 3;
}

message JobStatusReport {
  string job_id = 1;
  JobState state = 2;
  string message = 3;
  int64 timestamp = 4;
  ResourceUsage resource_usage = 5;
  string exit_code = 6;
}

enum JobState {
  PENDING = 0;
  PULLING = 1;
  RUNNING = 2;
  COMPLETED = 3;
  FAILED = 4;
  KILLED = 5;
}

message WorkerMessage {
  oneof message {
    NodeStatus heartbeat = 1;
    JobStatusReport job_status = 2;
    LogChunk log_chunk = 3;
  }
}

message OrchestratorMessage {
  oneof message {
    JobAssignment job = 1;
    JobControl control = 2;
    ConfigUpdate config = 3;
  }
}

message JobControl {
  string job_id = 1;
  ControlAction action = 2;
}

enum ControlAction {
  STOP = 0;
  KILL = 1;
  CHECKPOINT = 2;
}

message LogChunk {
  string job_id = 1;
  string stream = 2;  // stdout or stderr
  bytes data = 3;
  int64 timestamp = 4;
}

message Acknowledgment {
  bool success = 1;
  string message = 2;
}
```

### REST API Alternative

```yaml
# REST endpoints for worker agent

# Worker registration
POST /api/v1/workers
Body: { worker_info }
Response: { worker_id, token }

# Heartbeat
POST /api/v1/workers/{worker_id}/heartbeat
Body: { node_status }
Response: { acknowledged }

# Poll for jobs
GET /api/v1/workers/{worker_id}/jobs
Response: { jobs: [...] }

# Report job status
POST /api/v1/workers/{worker_id}/jobs/{job_id}/status
Body: { job_status }
Response: { acknowledged }

# Stream logs (WebSocket)
WS /api/v1/workers/{worker_id}/jobs/{job_id}/logs
```

---

## Job Lifecycle Management

### Job State Machine

```
                     ┌──────────┐
                     │ RECEIVED │
                     └─────┬────┘
                           │
                           ▼
                     ┌──────────┐
                     │ PULLING  │ (Download image/data)
                     └─────┬────┘
                           │
                           ▼
                     ┌──────────┐
                     │ STARTING │ (Create sandbox)
                     └─────┬────┘
                           │
                           ▼
                     ┌──────────┐
         ┌───────────┤ RUNNING  │◄─────────┐
         │           └─────┬────┘          │
         │                 │               │
         ▼                 │               │
    ┌─────────┐            │          ┌─────────────┐
    │CHECKPNT │            │          │ CHECKPOINT  │
    │-ING     │────────────┘          │ RESTORE     │
    └─────────┘                       └─────────────┘
         │                 │
         │                 ▼
         │           ┌──────────┐
         │           │ STOPPING │ (Graceful shutdown)
         │           └─────┬────┘
         │                 │
         │                 ▼
         │           ┌──────────┐
         └──────────►│ CLEANING │ (Remove sandbox)
                     └─────┬────┘
                           │
                     ┌─────┴──────┐
                     │            │
                     ▼            ▼
              ┌───────────┐  ┌────────┐
              │ COMPLETED │  │ FAILED │
              └───────────┘  └────────┘
```

### Job Execution Pseudocode

```go
func (je *JobExecutor) ExecuteJob(job Job) error {
    // 1. Report PULLING state
    je.reportStatus(job.ID, PULLING, "Downloading container image")

    // 2. Pull container image
    if err := je.pullImage(job.Image); err != nil {
        je.reportStatus(job.ID, FAILED, err.Error())
        return err
    }

    // 3. Download input data
    if job.Storage.InputURL != "" {
        if err := je.storage.DownloadInput(job.Storage.InputURL, job.WorkDir); err != nil {
            je.reportStatus(job.ID, FAILED, err.Error())
            return err
        }
    }

    // 4. Allocate resources
    je.reportStatus(job.ID, STARTING, "Allocating resources")
    if err := je.resources.AllocateResources(job.ID, job.Resources); err != nil {
        je.reportStatus(job.ID, FAILED, err.Error())
        return err
    }
    defer je.resources.ReleaseResources(job.ID)

    // 5. Create sandbox
    sandbox, err := je.createSandbox(job)
    if err != nil {
        je.reportStatus(job.ID, FAILED, err.Error())
        return err
    }
    defer sandbox.Cleanup()

    // 6. Start job
    je.reportStatus(job.ID, RUNNING, "Job started")
    if err := sandbox.Start(); err != nil {
        je.reportStatus(job.ID, FAILED, err.Error())
        return err
    }

    // 7. Monitor execution
    go je.monitorJob(job.ID, sandbox)

    // 8. Wait for completion
    exitCode, err := sandbox.Wait(job.TimeoutSeconds)
    if err != nil {
        je.reportStatus(job.ID, FAILED, err.Error())
        return err
    }

    // 9. Upload output data
    je.reportStatus(job.ID, CLEANING, "Uploading results")
    if job.Storage.OutputURL != "" {
        if err := je.storage.UploadOutput(job.WorkDir, job.Storage.OutputURL); err != nil {
            je.reportStatus(job.ID, FAILED, err.Error())
            return err
        }
    }

    // 10. Report completion
    je.reportStatus(job.ID, COMPLETED, fmt.Sprintf("Exit code: %d", exitCode))
    return nil
}

func (je *JobExecutor) monitorJob(jobID string, sandbox Sandbox) {
    ticker := time.NewTicker(5 * time.Second)
    defer ticker.Stop()

    for range ticker.C {
        status, err := sandbox.GetStatus()
        if err != nil || !status.Running {
            return
        }

        usage := je.resources.MonitorResources(jobID)
        je.reportResourceUsage(jobID, usage)

        // Capture logs
        logs := sandbox.ReadLogs()
        je.streamLogs(jobID, logs)
    }
}
```

---

## Resource Management

### cgroup Integration

```go
package resources

import (
    "fmt"
    "os"
    "path/filepath"
    "strconv"
)

const cgroupRoot = "/sys/fs/cgroup"

type CgroupManager struct {
    cgroupPath string
}

func NewCgroupManager(jobID string) *CgroupManager {
    return &CgroupManager{
        cgroupPath: filepath.Join(cgroupRoot, "worker-agent", jobID),
    }
}

func (cm *CgroupManager) CreateCgroup() error {
    // Create cgroup directories
    subsystems := []string{"cpu", "memory", "blkio", "devices"}
    for _, subsystem := range subsystems {
        path := filepath.Join(cgroupRoot, subsystem, "worker-agent", cm.jobID)
        if err := os.MkdirAll(path, 0755); err != nil {
            return err
        }
    }
    return nil
}

func (cm *CgroupManager) SetCPULimit(cores float64) error {
    // CPU quota: cores * 100000 microseconds per 100ms period
    quota := int(cores * 100000)
    path := filepath.Join(cgroupRoot, "cpu", cm.cgroupPath, "cpu.cfs_quota_us")
    return os.WriteFile(path, []byte(strconv.Itoa(quota)), 0644)
}

func (cm *CgroupManager) SetMemoryLimit(bytes int64) error {
    path := filepath.Join(cgroupRoot, "memory", cm.cgroupPath, "memory.limit_in_bytes")
    return os.WriteFile(path, []byte(strconv.FormatInt(bytes, 10)), 0644)
}

func (cm *CgroupManager) AddProcess(pid int) error {
    subsystems := []string{"cpu", "memory", "blkio", "devices"}
    for _, subsystem := range subsystems {
        path := filepath.Join(cgroupRoot, subsystem, cm.cgroupPath, "cgroup.procs")
        if err := os.WriteFile(path, []byte(strconv.Itoa(pid)), 0644); err != nil {
            return err
        }
    }
    return nil
}

func (cm *CgroupManager) GetCPUUsage() (float64, error) {
    path := filepath.Join(cgroupRoot, "cpu", cm.cgroupPath, "cpuacct.usage")
    data, err := os.ReadFile(path)
    if err != nil {
        return 0, err
    }
    usage, err := strconv.ParseInt(string(data), 10, 64)
    if err != nil {
        return 0, err
    }
    // Convert nanoseconds to percentage
    return float64(usage) / 1e9, nil
}

func (cm *CgroupManager) GetMemoryUsage() (int64, error) {
    path := filepath.Join(cgroupRoot, "memory", cm.cgroupPath, "memory.usage_in_bytes")
    data, err := os.ReadFile(path)
    if err != nil {
        return 0, err
    }
    return strconv.ParseInt(string(data), 10, 64)
}

func (cm *CgroupManager) Cleanup() error {
    subsystems := []string{"cpu", "memory", "blkio", "devices"}
    for _, subsystem := range subsystems {
        path := filepath.Join(cgroupRoot, subsystem, cm.cgroupPath)
        if err := os.Remove(path); err != nil && !os.IsNotExist(err) {
            return err
        }
    }
    return nil
}
```

### GPU Resource Management

```go
package resources

import (
    "github.com/NVIDIA/go-nvml/pkg/nvml"
)

type GPUManager struct {
    allocations map[string][]int // jobID -> GPU indices
}

func NewGPUManager() (*GPUManager, error) {
    if ret := nvml.Init(); ret != nvml.SUCCESS {
        return nil, fmt.Errorf("failed to initialize NVML: %v", nvml.ErrorString(ret))
    }
    return &GPUManager{
        allocations: make(map[string][]int),
    }, nil
}

func (gm *GPUManager) GetAvailableGPUs() (int, error) {
    count, ret := nvml.DeviceGetCount()
    if ret != nvml.SUCCESS {
        return 0, fmt.Errorf("failed to get device count: %v", nvml.ErrorString(ret))
    }
    return count, nil
}

func (gm *GPUManager) AllocateGPU(jobID string, count int) ([]int, error) {
    allocated := make([]int, 0, count)

    // Find available GPUs
    deviceCount, _ := gm.GetAvailableGPUs()
    for i := 0; i < deviceCount && len(allocated) < count; i++ {
        if !gm.isGPUAllocated(i) {
            allocated = append(allocated, i)
        }
    }

    if len(allocated) < count {
        return nil, fmt.Errorf("insufficient GPUs available")
    }

    gm.allocations[jobID] = allocated
    return allocated, nil
}

func (gm *GPUManager) ReleaseGPU(jobID string) {
    delete(gm.allocations, jobID)
}

func (gm *GPUManager) GetGPUUtilization(index int) (float64, error) {
    device, ret := nvml.DeviceGetHandleByIndex(index)
    if ret != nvml.SUCCESS {
        return 0, fmt.Errorf("failed to get device handle: %v", nvml.ErrorString(ret))
    }

    utilization, ret := nvml.DeviceGetUtilizationRates(device)
    if ret != nvml.SUCCESS {
        return 0, fmt.Errorf("failed to get utilization: %v", nvml.ErrorString(ret))
    }

    return float64(utilization.Gpu), nil
}

func (gm *GPUManager) GetGPUMemory(index int) (used, total int64, err error) {
    device, ret := nvml.DeviceGetHandleByIndex(index)
    if ret != nvml.SUCCESS {
        return 0, 0, fmt.Errorf("failed to get device handle: %v", nvml.ErrorString(ret))
    }

    memInfo, ret := nvml.DeviceGetMemoryInfo(device)
    if ret != nvml.SUCCESS {
        return 0, 0, fmt.Errorf("failed to get memory info: %v", nvml.ErrorString(ret))
    }

    return int64(memInfo.Used), int64(memInfo.Total), nil
}

func (gm *GPUManager) isGPUAllocated(index int) bool {
    for _, gpus := range gm.allocations {
        for _, gpu := range gpus {
            if gpu == index {
                return true
            }
        }
    }
    return false
}

func (gm *GPUManager) Cleanup() {
    nvml.Shutdown()
}
```

---

## Security Considerations

### Authentication

**mTLS (Mutual TLS):**

```go
package security

import (
    "crypto/tls"
    "crypto/x509"
    "os"
)

func LoadTLSConfig(certFile, keyFile, caFile string) (*tls.Config, error) {
    // Load certificate and private key
    cert, err := tls.LoadX509KeyPair(certFile, keyFile)
    if err != nil {
        return nil, err
    }

    // Load CA certificate
    caCert, err := os.ReadFile(caFile)
    if err != nil {
        return nil, err
    }

    caCertPool := x509.NewCertPool()
    caCertPool.AppendCertsFromPEM(caCert)

    return &tls.Config{
        Certificates: []tls.Certificate{cert},
        ClientCAs:    caCertPool,
        ClientAuth:   tls.RequireAndVerifyClientCert,
        MinVersion:   tls.VersionTLS13,
    }, nil
}
```

### Secret Management

```go
package security

import (
    "crypto/aes"
    "crypto/cipher"
    "crypto/rand"
    "encoding/base64"
    "io"
)

type SecretManager struct {
    key []byte
}

func NewSecretManager(key []byte) *SecretManager {
    return &SecretManager{key: key}
}

func (sm *SecretManager) Encrypt(plaintext string) (string, error) {
    block, err := aes.NewCipher(sm.key)
    if err != nil {
        return "", err
    }

    gcm, err := cipher.NewGCM(block)
    if err != nil {
        return "", err
    }

    nonce := make([]byte, gcm.NonceSize())
    if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
        return "", err
    }

    ciphertext := gcm.Seal(nonce, nonce, []byte(plaintext), nil)
    return base64.StdEncoding.EncodeToString(ciphertext), nil
}

func (sm *SecretManager) Decrypt(encoded string) (string, error) {
    ciphertext, err := base64.StdEncoding.DecodeString(encoded)
    if err != nil {
        return "", err
    }

    block, err := aes.NewCipher(sm.key)
    if err != nil {
        return "", err
    }

    gcm, err := cipher.NewGCM(block)
    if err != nil {
        return "", err
    }

    nonceSize := gcm.NonceSize()
    nonce, ciphertext := ciphertext[:nonceSize], ciphertext[nonceSize:]

    plaintext, err := gcm.Open(nil, nonce, ciphertext, nil)
    if err != nil {
        return "", err
    }

    return string(plaintext), nil
}
```

### Sandbox Isolation

- Use Linux namespaces (PID, network, mount, IPC)
- Enable SELinux/AppArmor profiles
- Drop unnecessary capabilities
- Use read-only root filesystems where possible
- Implement seccomp filters

---

## Implementation Examples

### Complete Worker Agent (Simplified)

```go
// main.go
package main

import (
    "context"
    "log"
    "os"
    "os/signal"
    "syscall"
    "time"
)

type WorkerAgent struct {
    config      *Config
    comm        *CommunicationModule
    executor    *JobExecutor
    resources   *ResourceManager
    monitoring  *MonitoringModule
    storage     *StorageManager
    security    *SecurityModule
}

func NewWorkerAgent(configPath string) (*WorkerAgent, error) {
    config, err := LoadConfig(configPath)
    if err != nil {
        return nil, err
    }

    return &WorkerAgent{
        config:     config,
        comm:       NewCommunicationModule(config),
        executor:   NewJobExecutor(config),
        resources:  NewResourceManager(config),
        monitoring: NewMonitoringModule(config),
        storage:    NewStorageManager(config),
        security:   NewSecurityModule(config),
    }, nil
}

func (wa *WorkerAgent) Start(ctx context.Context) error {
    // Authenticate
    if err := wa.security.Authenticate(); err != nil {
        return err
    }

    // Connect to orchestrator
    if err := wa.comm.Connect(wa.config.OrchestratorURL); err != nil {
        return err
    }

    // Register worker
    if err := wa.registerWorker(); err != nil {
        return err
    }

    // Start background tasks
    go wa.heartbeatLoop(ctx)
    go wa.jobPollLoop(ctx)
    go wa.monitoringLoop(ctx)

    // Wait for shutdown
    <-ctx.Done()
    return wa.Shutdown()
}

func (wa *WorkerAgent) registerWorker() error {
    resources := wa.resources.GetAvailableResources()
    info := WorkerInfo{
        WorkerID: wa.config.WorkerID,
        Hostname: wa.config.Hostname,
        Resources: resources,
        SupportedRuntimes: wa.config.Runtimes,
    }
    return wa.comm.RegisterWorker(info)
}

func (wa *WorkerAgent) heartbeatLoop(ctx context.Context) {
    ticker := time.NewTicker(30 * time.Second)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            status := wa.getNodeStatus()
            if err := wa.comm.SendHeartbeat(status); err != nil {
                log.Printf("Failed to send heartbeat: %v", err)
            }
        }
    }
}

func (wa *WorkerAgent) jobPollLoop(ctx context.Context) {
    ticker := time.NewTicker(5 * time.Second)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            jobs, err := wa.comm.PollJobs()
            if err != nil {
                log.Printf("Failed to poll jobs: %v", err)
                continue
            }

            for _, job := range jobs {
                go wa.handleJob(ctx, job)
            }
        }
    }
}

func (wa *WorkerAgent) handleJob(ctx context.Context, job Job) {
    log.Printf("Received job: %s", job.ID)

    if err := wa.executor.ExecuteJob(job); err != nil {
        log.Printf("Job %s failed: %v", job.ID, err)
        wa.comm.ReportJobStatus(job.ID, JobStatus{
            State:   FAILED,
            Message: err.Error(),
        })
        return
    }

    log.Printf("Job %s completed successfully", job.ID)
}

func (wa *WorkerAgent) monitoringLoop(ctx context.Context) {
    ticker := time.NewTicker(10 * time.Second)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            metrics := wa.monitoring.ExportMetrics()
            for _, metric := range metrics {
                wa.monitoring.RecordMetric(metric.Name, metric.Value, metric.Labels)
            }
        }
    }
}

func (wa *WorkerAgent) getNodeStatus() NodeStatus {
    return NodeStatus{
        WorkerID:      wa.config.WorkerID,
        ResourceUsage: wa.resources.GetUsedResources(),
        RunningJobs:   wa.executor.GetRunningJobs(),
        State:         wa.getWorkerState(),
        Timestamp:     time.Now().Unix(),
    }
}

func (wa *WorkerAgent) getWorkerState() WorkerState {
    if len(wa.executor.GetRunningJobs()) == 0 {
        return IDLE
    }
    return BUSY
}

func (wa *WorkerAgent) Shutdown() error {
    log.Println("Shutting down worker agent...")

    // Stop accepting new jobs
    // Wait for running jobs to complete (with timeout)
    // Disconnect from orchestrator
    wa.comm.Disconnect()

    return nil
}

func main() {
    configPath := os.Getenv("WORKER_CONFIG")
    if configPath == "" {
        configPath = "/etc/worker-agent/config.yaml"
    }

    agent, err := NewWorkerAgent(configPath)
    if err != nil {
        log.Fatalf("Failed to create worker agent: %v", err)
    }

    ctx, cancel := context.WithCancel(context.Background())
    defer cancel()

    // Handle signals
    sigCh := make(chan os.Signal, 1)
    signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
    go func() {
        <-sigCh
        log.Println("Received shutdown signal")
        cancel()
    }()

    if err := agent.Start(ctx); err != nil {
        log.Fatalf("Worker agent failed: %v", err)
    }
}
```

---

## Deployment and Operations

### Systemd Service

```ini
# /etc/systemd/system/worker-agent.service
[Unit]
Description=Compute Marketplace Worker Agent
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=worker-agent
Group=worker-agent
ExecStart=/usr/local/bin/worker-agent --config /etc/worker-agent/config.yaml
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment="WORKER_CONFIG=/etc/worker-agent/config.yaml"

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/worker-agent /var/log/worker-agent

[Install]
WantedBy=multi-user.target
```

Usage:
```bash
sudo systemctl daemon-reload
sudo systemctl enable worker-agent
sudo systemctl start worker-agent
sudo systemctl status worker-agent
```

### Configuration File

```yaml
# /etc/worker-agent/config.yaml
worker:
  id: worker-node-001
  hostname: node001.example.com
  region: us-west-2
  labels:
    gpu: nvidia-a100
    tier: premium

orchestrator:
  url: grpc://orchestrator.example.com:50051
  tls:
    enabled: true
    cert: /etc/worker-agent/certs/client.crt
    key: /etc/worker-agent/certs/client.key
    ca: /etc/worker-agent/certs/ca.crt

resources:
  cpu_cores: 32
  memory_bytes: 137438953472  # 128 GB
  gpu_count: 4
  gpu_model: nvidia-a100-80gb
  disk_bytes: 1099511627776  # 1 TB

runtimes:
  - docker
  - gvisor
  - firecracker

storage:
  backend: s3
  endpoint: https://s3.amazonaws.com
  bucket: compute-marketplace-data
  credentials:
    access_key: ${AWS_ACCESS_KEY}
    secret_key: ${AWS_SECRET_KEY}

monitoring:
  prometheus:
    enabled: true
    port: 9090
  logging:
    level: info
    format: json
    output: /var/log/worker-agent/agent.log

security:
  secret_key: ${SECRET_ENCRYPTION_KEY}
  allowed_images:
    - "docker.io/*"
    - "gcr.io/*"
  sandbox:
    enforce_seccomp: true
    enforce_apparmor: true
```

### Monitoring Dashboards

**Prometheus Metrics:**
```
# Worker agent metrics
worker_agent_heartbeat_total
worker_agent_jobs_running
worker_agent_jobs_completed_total
worker_agent_jobs_failed_total

# Resource metrics
worker_agent_cpu_usage_percent
worker_agent_memory_used_bytes
worker_agent_gpu_utilization_percent
worker_agent_disk_used_bytes
worker_agent_network_rx_bytes_total
worker_agent_network_tx_bytes_total

# Job metrics
worker_agent_job_duration_seconds
worker_agent_job_resource_usage
```

---

## References

### Distributed Systems
- **gRPC Documentation**: https://grpc.io/docs/
- **Protocol Buffers**: https://protobuf.dev/
- **Kubernetes Worker Node Architecture**: https://kubernetes.io/docs/concepts/architecture/

### Container Runtimes
- **containerd**: https://containerd.io/
- **Docker Engine API**: https://docs.docker.com/engine/api/
- **OCI Runtime Spec**: https://github.com/opencontainers/runtime-spec

### Resource Management
- **cgroups v2**: https://www.kernel.org/doc/Documentation/cgroup-v2.txt
- **NVIDIA NVML**: https://docs.nvidia.com/deploy/nvml-api/
- **Linux Namespaces**: https://man7.org/linux/man-pages/man7/namespaces.7.html

### Monitoring
- **Prometheus Go Client**: https://github.com/prometheus/client_golang
- **Grafana Dashboards**: https://grafana.com/docs/

---

## Team Requirements

**Systems Engineer** (Primary, 40 hours/week):
- Go programming
- Distributed systems design
- Linux systems administration

**DevOps Engineer** (Primary, 30 hours/week):
- Container orchestration
- Deployment automation
- Monitoring and observability

**Network Engineer** (Secondary, 10 hours/week):
- gRPC and network protocols
- TLS/security
- Network troubleshooting

**Security Engineer** (Consulting, 10 hours/week):
- Authentication and authorization
- Secret management
- Security auditing

**Total Estimated Effort**: 4-6 weeks for core implementation, 2 weeks for testing and hardening

---

*Last Updated: 2025-10-14*
*Version: 1.0*
