import { EventEmitter } from 'events';

export interface PerformanceMetrics {
  timestamp: Date;
  nodeId: string;
  system: SystemMetrics;
  compute: ComputeMetrics;
  network: NetworkMetrics;
  storage: StorageMetrics;
  application: ApplicationMetrics;
}

export interface SystemMetrics {
  uptime: number; // seconds
  loadAverage: [number, number, number]; // 1min, 5min, 15min
  processes: {
    total: number;
    running: number;
    sleeping: number;
    zombie: number;
  };
  memory: {
    total: number; // bytes
    used: number;
    free: number;
    available: number;
    cached: number;
    buffers: number;
    swapTotal: number;
    swapUsed: number;
    swapFree: number;
  };
  cpu: {
    cores: number;
    usage: number; // percentage
    perCore: number[]; // per-core usage percentages
    temperature?: number; // Celsius
    frequency: number; // MHz
    utilization: CpuUtilization;
  };
}

export interface CpuUtilization {
  user: number;
  system: number;
  idle: number;
  iowait: number;
  interrupt: number;
  steal?: number;
}

export interface ComputeMetrics {
  gpu?: GpuMetrics[];
  accelerators?: AcceleratorMetrics[];
  containers: ContainerMetrics[];
  virtualMachines: VirtualMachineMetrics[];
}

export interface GpuMetrics {
  id: string;
  name: string;
  driver: string;
  usage: {
    gpu: number; // percentage
    memory: number; // percentage
    encoder: number;
    decoder: number;
  };
  memory: {
    total: number; // bytes
    used: number;
    free: number;
  };
  temperature: number; // Celsius
  powerDraw: number; // watts
  powerLimit: number; // watts
  clockSpeeds: {
    graphics: number; // MHz
    memory: number; // MHz
    shader: number; // MHz
  };
  processes: GpuProcess[];
}

export interface GpuProcess {
  pid: number;
  processName: string;
  memoryUsage: number; // bytes
  gpuUsage: number; // percentage
}

export interface AcceleratorMetrics {
  id: string;
  type: 'tpu' | 'fpga' | 'asic' | 'other';
  name: string;
  usage: number; // percentage
  temperature?: number;
  powerDraw?: number;
  memory?: {
    total: number;
    used: number;
  };
}

export interface ContainerMetrics {
  id: string;
  name: string;
  image: string;
  status: 'running' | 'stopped' | 'paused' | 'restarting';
  cpu: {
    usage: number; // percentage
    limit?: number;
    throttled: number;
  };
  memory: {
    usage: number; // bytes
    limit?: number;
    cache: number;
    rss: number;
  };
  network: {
    rxBytes: number;
    txBytes: number;
    rxPackets: number;
    txPackets: number;
  };
  storage: {
    readBytes: number;
    writeBytes: number;
    readOps: number;
    writeOps: number;
  };
  pids: number;
}

export interface VirtualMachineMetrics {
  id: string;
  name: string;
  status: 'running' | 'stopped' | 'paused' | 'suspended';
  cpu: {
    allocated: number; // cores
    usage: number; // percentage
  };
  memory: {
    allocated: number; // bytes
    usage: number;
    balloon?: number;
  };
  disk: {
    allocated: number; // bytes
    usage: number;
    readOps: number;
    writeOps: number;
  };
  network: {
    interfaces: NetworkInterface[];
  };
}

export interface NetworkInterface {
  name: string;
  rxBytes: number;
  txBytes: number;
  rxPackets: number;
  txPackets: number;
  errors: number;
  drops: number;
}

export interface NetworkMetrics {
  interfaces: NetworkInterface[];
  bandwidth: {
    total: number; // bps
    used: number; // bps
    available: number; // bps
  };
  latency: {
    local: number; // ms
    regional: number; // ms
    global: number; // ms
  };
  connections: {
    total: number;
    established: number;
    listening: number;
    timeWait: number;
  };
  throughput: {
    inbound: number; // bps
    outbound: number; // bps
  };
}

export interface StorageMetrics {
  filesystems: FilesystemMetrics[];
  disks: DiskMetrics[];
  raid?: RaidMetrics[];
}

export interface FilesystemMetrics {
  device: string;
  mountpoint: string;
  type: string;
  size: number; // bytes
  used: number;
  available: number;
  usage: number; // percentage
  inodes: {
    total: number;
    used: number;
    available: number;
  };
}

export interface DiskMetrics {
  device: string;
  model?: string;
  size: number; // bytes
  temperature?: number; // Celsius
  health: 'good' | 'warning' | 'critical';
  smart?: SmartData;
  io: {
    readOps: number;
    writeOps: number;
    readBytes: number;
    writeBytes: number;
    readTime: number; // ms
    writeTime: number; // ms
    utilization: number; // percentage
    queueDepth: number;
  };
}

export interface SmartData {
  overallHealth: 'PASSED' | 'FAILED';
  temperature: number;
  powerOnHours: number;
  powerCycles: number;
  reallocatedSectors: number;
  pendingSectors: number;
}

export interface RaidMetrics {
  device: string;
  level: string; // RAID0, RAID1, etc.
  status: 'clean' | 'degraded' | 'failed';
  devices: string[];
  activeDevices: number;
  totalDevices: number;
}

export interface ApplicationMetrics {
  processes: ProcessMetrics[];
  services: ServiceMetrics[];
  jobs: JobMetrics[];
}

export interface ProcessMetrics {
  pid: number;
  name: string;
  command: string;
  cpu: number; // percentage
  memory: number; // bytes
  threads: number;
  handles: number;
  startTime: Date;
  status: 'running' | 'sleeping' | 'stopped' | 'zombie';
}

export interface ServiceMetrics {
  name: string;
  status: 'active' | 'inactive' | 'failed' | 'activating';
  uptime: number; // seconds
  restarts: number;
  cpu: number;
  memory: number;
  ports: number[];
}

export interface JobMetrics {
  jobId: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  startTime: Date;
  endTime?: Date;
  duration: number; // seconds
  exitCode?: number;
  resourceUsage: {
    cpu: number;
    memory: number;
    gpu?: number;
    network: number;
    storage: number;
  };
  progress?: number; // percentage
}

export interface PerformanceAlert {
  id: string;
  timestamp: Date;
  nodeId: string;
  severity: 'info' | 'warning' | 'critical' | 'emergency';
  category: 'cpu' | 'memory' | 'disk' | 'network' | 'gpu' | 'temperature' | 'application';
  metric: string;
  value: number;
  threshold: number;
  description: string;
  resolved: boolean;
  resolvedAt?: Date;
}

export interface MonitoringConfig {
  collectInterval: number; // milliseconds
  retentionPeriod: number; // days
  aggregationLevels: AggregationLevel[];
  alertThresholds: AlertThreshold[];
  enabledCollectors: CollectorType[];
}

export interface AggregationLevel {
  interval: number; // seconds
  retention: number; // days
  metrics: string[];
}

export interface AlertThreshold {
  metric: string;
  operator: '>' | '<' | '>=' | '<=' | '==' | '!=';
  value: number;
  severity: PerformanceAlert['severity'];
  duration?: number; // seconds - sustained threshold
  description: string;
}

export type CollectorType = 
  | 'system' 
  | 'cpu' 
  | 'memory' 
  | 'disk' 
  | 'network' 
  | 'gpu' 
  | 'containers' 
  | 'processes' 
  | 'services';

export interface MetricsDatabase {
  store(metrics: PerformanceMetrics): Promise<void>;
  query(nodeId: string, startTime: Date, endTime: Date, metrics?: string[]): Promise<PerformanceMetrics[]>;
  aggregate(nodeId: string, interval: string, startTime: Date, endTime: Date): Promise<PerformanceMetrics[]>;
  cleanup(olderThan: Date): Promise<number>;
}

export class PerformanceMonitor extends EventEmitter {
  private config: MonitoringConfig;
  private collectors: Map<CollectorType, MetricsCollector> = new Map();
  private database: MetricsDatabase;
  private alerts: Map<string, PerformanceAlert> = new Map();
  private activeAlerts: Map<string, PerformanceAlert> = new Map();
  private collectionTimer: NodeJS.Timeout | null = null;
  private aggregationTimer: NodeJS.Timeout | null = null;
  private cleanupTimer: NodeJS.Timeout | null = null;

  constructor(database: MetricsDatabase, config?: Partial<MonitoringConfig>) {
    super();
    this.database = database;
    this.config = this.mergeConfig(config);
    this.initializeCollectors();
    this.startMonitoring();
  }

  private mergeConfig(userConfig?: Partial<MonitoringConfig>): MonitoringConfig {
    const defaultConfig: MonitoringConfig = {
      collectInterval: 10000, // 10 seconds
      retentionPeriod: 30, // days
      aggregationLevels: [
        { interval: 60, retention: 7, metrics: ['cpu', 'memory', 'disk', 'network'] },
        { interval: 300, retention: 30, metrics: ['cpu', 'memory', 'disk'] },
        { interval: 3600, retention: 365, metrics: ['cpu', 'memory'] }
      ],
      alertThresholds: [
        { metric: 'cpu.usage', operator: '>', value: 90, severity: 'critical', duration: 300, description: 'High CPU usage' },
        { metric: 'memory.usage', operator: '>', value: 95, severity: 'critical', duration: 180, description: 'High memory usage' },
        { metric: 'disk.usage', operator: '>', value: 90, severity: 'warning', description: 'High disk usage' },
        { metric: 'gpu.temperature', operator: '>', value: 85, severity: 'warning', description: 'High GPU temperature' }
      ],
      enabledCollectors: ['system', 'cpu', 'memory', 'disk', 'network', 'gpu', 'containers', 'processes']
    };

    return { ...defaultConfig, ...userConfig };
  }

  private initializeCollectors(): void {
    this.config.enabledCollectors.forEach(type => {
      switch (type) {
        case 'system':
          this.collectors.set(type, new SystemCollector());
          break;
        case 'cpu':
          this.collectors.set(type, new CpuCollector());
          break;
        case 'memory':
          this.collectors.set(type, new MemoryCollector());
          break;
        case 'disk':
          this.collectors.set(type, new DiskCollector());
          break;
        case 'network':
          this.collectors.set(type, new NetworkCollector());
          break;
        case 'gpu':
          this.collectors.set(type, new GpuCollector());
          break;
        case 'containers':
          this.collectors.set(type, new ContainerCollector());
          break;
        case 'processes':
          this.collectors.set(type, new ProcessCollector());
          break;
      }
    });
  }

  public async collectMetrics(nodeId: string): Promise<PerformanceMetrics> {
    const timestamp = new Date();
    const metrics: Partial<PerformanceMetrics> = {
      timestamp,
      nodeId
    };

    // Collect metrics from all enabled collectors
    for (const [type, collector] of this.collectors) {
      try {
        const collectedMetrics = await collector.collect();
        
        switch (type) {
          case 'system':
          case 'cpu':
          case 'memory':
            metrics.system = { ...metrics.system, ...collectedMetrics };
            break;
          case 'gpu':
          case 'containers':
            metrics.compute = { ...metrics.compute, ...collectedMetrics };
            break;
          case 'network':
            metrics.network = collectedMetrics as NetworkMetrics;
            break;
          case 'disk':
            metrics.storage = collectedMetrics as StorageMetrics;
            break;
          case 'processes':
            metrics.application = { ...metrics.application, ...collectedMetrics };
            break;
        }
      } catch (error) {
        console.error(`Failed to collect ${type} metrics:`, error);
      }
    }

    const completeMetrics = metrics as PerformanceMetrics;
    
    // Store metrics
    await this.database.store(completeMetrics);
    
    // Check for alerts
    await this.checkAlerts(completeMetrics);
    
    this.emit('metricsCollected', completeMetrics);
    return completeMetrics;
  }

  private async checkAlerts(metrics: PerformanceMetrics): Promise<void> {
    for (const threshold of this.config.alertThresholds) {
      const value = this.extractMetricValue(metrics, threshold.metric);
      if (value === undefined) continue;

      const alertKey = `${metrics.nodeId}_${threshold.metric}`;
      const shouldAlert = this.evaluateThreshold(value, threshold.operator, threshold.value);
      
      if (shouldAlert) {
        const existingAlert = this.activeAlerts.get(alertKey);
        
        if (!existingAlert) {
          // New alert
          const alert = this.createAlert(metrics.nodeId, threshold, value, metrics.timestamp);
          this.activeAlerts.set(alertKey, alert);
          this.alerts.set(alert.id, alert);
          this.emit('alertTriggered', alert);
        } else if (threshold.duration) {
          // Check if sustained threshold is met
          const sustainedDuration = metrics.timestamp.getTime() - existingAlert.timestamp.getTime();
          if (sustainedDuration >= threshold.duration * 1000) {
            existingAlert.severity = threshold.severity;
            this.emit('alertEscalated', existingAlert);
          }
        }
      } else {
        // Resolve active alert if exists
        const existingAlert = this.activeAlerts.get(alertKey);
        if (existingAlert) {
          existingAlert.resolved = true;
          existingAlert.resolvedAt = metrics.timestamp;
          this.activeAlerts.delete(alertKey);
          this.emit('alertResolved', existingAlert);
        }
      }
    }
  }

  private extractMetricValue(metrics: PerformanceMetrics, metricPath: string): number | undefined {
    const parts = metricPath.split('.');
    let current: any = metrics;
    
    for (const part of parts) {
      if (current && typeof current === 'object' && part in current) {
        current = current[part];
      } else {
        return undefined;
      }
    }
    
    return typeof current === 'number' ? current : undefined;
  }

  private evaluateThreshold(value: number, operator: string, threshold: number): boolean {
    switch (operator) {
      case '>': return value > threshold;
      case '<': return value < threshold;
      case '>=': return value >= threshold;
      case '<=': return value <= threshold;
      case '==': return value === threshold;
      case '!=': return value !== threshold;
      default: return false;
    }
  }

  private createAlert(
    nodeId: string, 
    threshold: AlertThreshold, 
    value: number, 
    timestamp: Date
  ): PerformanceAlert {
    return {
      id: this.generateAlertId(),
      timestamp,
      nodeId,
      severity: threshold.severity,
      category: this.getMetricCategory(threshold.metric),
      metric: threshold.metric,
      value,
      threshold: threshold.value,
      description: `${threshold.description}: ${value} ${threshold.operator} ${threshold.value}`,
      resolved: false
    };
  }

  private getMetricCategory(metric: string): PerformanceAlert['category'] {
    if (metric.startsWith('cpu')) return 'cpu';
    if (metric.startsWith('memory')) return 'memory';
    if (metric.startsWith('disk') || metric.startsWith('storage')) return 'disk';
    if (metric.startsWith('network')) return 'network';
    if (metric.startsWith('gpu')) return 'gpu';
    if (metric.includes('temperature')) return 'temperature';
    return 'application';
  }

  public async getMetrics(
    nodeId: string, 
    startTime: Date, 
    endTime: Date, 
    metrics?: string[]
  ): Promise<PerformanceMetrics[]> {
    return await this.database.query(nodeId, startTime, endTime, metrics);
  }

  public async getAggregatedMetrics(
    nodeId: string,
    interval: string,
    startTime: Date,
    endTime: Date
  ): Promise<PerformanceMetrics[]> {
    return await this.database.aggregate(nodeId, interval, startTime, endTime);
  }

  public getActiveAlerts(): PerformanceAlert[] {
    return Array.from(this.activeAlerts.values());
  }

  public getAlertHistory(limit: number = 100): PerformanceAlert[] {
    return Array.from(this.alerts.values())
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
      .slice(0, limit);
  }

  private startMonitoring(): void {
    // Start metric collection
    this.collectionTimer = setInterval(async () => {
      try {
        await this.collectMetrics('default_node'); // This would be dynamic in a real implementation
      } catch (error) {
        console.error('Failed to collect metrics:', error);
      }
    }, this.config.collectInterval);

    // Start aggregation
    this.aggregationTimer = setInterval(async () => {
      await this.performAggregation();
    }, 60000); // Every minute

    // Start cleanup
    this.cleanupTimer = setInterval(async () => {
      await this.performCleanup();
    }, 24 * 60 * 60 * 1000); // Daily
  }

  private async performAggregation(): Promise<void> {
    // This would implement metric aggregation logic
    // For now, just emit an event
    this.emit('aggregationPerformed');
  }

  private async performCleanup(): Promise<void> {
    const cutoffDate = new Date(Date.now() - this.config.retentionPeriod * 24 * 60 * 60 * 1000);
    const deletedCount = await this.database.cleanup(cutoffDate);
    this.emit('cleanupPerformed', deletedCount);
  }

  private generateAlertId(): string {
    return `alert_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  public stop(): void {
    if (this.collectionTimer) {
      clearInterval(this.collectionTimer);
      this.collectionTimer = null;
    }
    if (this.aggregationTimer) {
      clearInterval(this.aggregationTimer);
      this.aggregationTimer = null;
    }
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = null;
    }
  }
}

// Abstract base class for metrics collectors
abstract class MetricsCollector {
  abstract collect(): Promise<any>;
}

class SystemCollector extends MetricsCollector {
  async collect(): Promise<Partial<SystemMetrics>> {
    // This would use system APIs to collect real metrics
    return {
      uptime: process.uptime(),
      loadAverage: [0.5, 0.3, 0.2] as [number, number, number],
      processes: {
        total: 150,
        running: 2,
        sleeping: 145,
        zombie: 3
      }
    };
  }
}

class CpuCollector extends MetricsCollector {
  async collect(): Promise<any> {
    return {
      cpu: {
        cores: 8,
        usage: Math.random() * 100,
        perCore: Array(8).fill(0).map(() => Math.random() * 100),
        temperature: 45 + Math.random() * 20,
        frequency: 2400,
        utilization: {
          user: Math.random() * 50,
          system: Math.random() * 30,
          idle: Math.random() * 80,
          iowait: Math.random() * 10,
          interrupt: Math.random() * 5
        }
      }
    };
  }
}

class MemoryCollector extends MetricsCollector {
  async collect(): Promise<any> {
    const total = 16 * 1024 * 1024 * 1024; // 16GB
    const used = total * (0.3 + Math.random() * 0.4);
    
    return {
      memory: {
        total,
        used,
        free: total - used,
        available: total - used,
        cached: used * 0.2,
        buffers: used * 0.1,
        swapTotal: 4 * 1024 * 1024 * 1024,
        swapUsed: Math.random() * 1024 * 1024 * 1024,
        swapFree: 3 * 1024 * 1024 * 1024
      }
    };
  }
}

class DiskCollector extends MetricsCollector {
  async collect(): Promise<StorageMetrics> {
    return {
      filesystems: [
        {
          device: '/dev/sda1',
          mountpoint: '/',
          type: 'ext4',
          size: 500 * 1024 * 1024 * 1024,
          used: 200 * 1024 * 1024 * 1024,
          available: 300 * 1024 * 1024 * 1024,
          usage: 40,
          inodes: {
            total: 1000000,
            used: 100000,
            available: 900000
          }
        }
      ],
      disks: [
        {
          device: '/dev/sda',
          model: 'Samsung SSD',
          size: 500 * 1024 * 1024 * 1024,
          temperature: 35,
          health: 'good',
          io: {
            readOps: 1000,
            writeOps: 500,
            readBytes: 1024 * 1024,
            writeBytes: 512 * 1024,
            readTime: 10,
            writeTime: 15,
            utilization: 25,
            queueDepth: 2
          }
        }
      ]
    };
  }
}

class NetworkCollector extends MetricsCollector {
  async collect(): Promise<NetworkMetrics> {
    return {
      interfaces: [
        {
          name: 'eth0',
          rxBytes: Math.random() * 1024 * 1024 * 1024,
          txBytes: Math.random() * 1024 * 1024 * 1024,
          rxPackets: Math.random() * 1000000,
          txPackets: Math.random() * 1000000,
          errors: 0,
          drops: 0
        }
      ],
      bandwidth: {
        total: 1000 * 1000 * 1000, // 1Gbps
        used: Math.random() * 100 * 1000 * 1000,
        available: 900 * 1000 * 1000
      },
      latency: {
        local: 1,
        regional: 50,
        global: 150
      },
      connections: {
        total: 100,
        established: 80,
        listening: 10,
        timeWait: 10
      },
      throughput: {
        inbound: Math.random() * 50 * 1000 * 1000,
        outbound: Math.random() * 50 * 1000 * 1000
      }
    };
  }
}

class GpuCollector extends MetricsCollector {
  async collect(): Promise<any> {
    return {
      gpu: [
        {
          id: 'gpu0',
          name: 'NVIDIA GeForce RTX 4090',
          driver: '525.60',
          usage: {
            gpu: Math.random() * 100,
            memory: Math.random() * 100,
            encoder: Math.random() * 50,
            decoder: Math.random() * 30
          },
          memory: {
            total: 24 * 1024 * 1024 * 1024,
            used: Math.random() * 12 * 1024 * 1024 * 1024,
            free: 12 * 1024 * 1024 * 1024
          },
          temperature: 65 + Math.random() * 20,
          powerDraw: 250 + Math.random() * 100,
          powerLimit: 450,
          clockSpeeds: {
            graphics: 1500,
            memory: 10000,
            shader: 1800
          },
          processes: []
        }
      ]
    };
  }
}

class ContainerCollector extends MetricsCollector {
  async collect(): Promise<any> {
    return {
      containers: [
        {
          id: 'container_123',
          name: 'compute_worker',
          image: 'ubuntu:20.04',
          status: 'running' as const,
          cpu: {
            usage: Math.random() * 100,
            throttled: 0
          },
          memory: {
            usage: Math.random() * 2 * 1024 * 1024 * 1024,
            cache: Math.random() * 512 * 1024 * 1024,
            rss: Math.random() * 1024 * 1024 * 1024
          },
          network: {
            rxBytes: Math.random() * 1024 * 1024,
            txBytes: Math.random() * 1024 * 1024,
            rxPackets: Math.random() * 1000,
            txPackets: Math.random() * 1000
          },
          storage: {
            readBytes: Math.random() * 1024 * 1024,
            writeBytes: Math.random() * 1024 * 1024,
            readOps: Math.random() * 100,
            writeOps: Math.random() * 100
          },
          pids: 5
        }
      ]
    };
  }
}

class ProcessCollector extends MetricsCollector {
  async collect(): Promise<any> {
    return {
      processes: [
        {
          pid: 1234,
          name: 'compute_process',
          command: 'python compute_job.py',
          cpu: Math.random() * 50,
          memory: Math.random() * 1024 * 1024 * 1024,
          threads: 4,
          handles: 100,
          startTime: new Date(Date.now() - 3600000),
          status: 'running' as const
        }
      ]
    };
  }
}

export default PerformanceMonitor;