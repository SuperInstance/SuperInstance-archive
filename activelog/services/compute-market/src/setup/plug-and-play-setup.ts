import { EventEmitter } from 'events';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export interface SetupConfiguration {
  id: string;
  name: string;
  description: string;
  version: string;
  platform: 'linux' | 'windows' | 'macos' | 'docker';
  architecture: 'x86_64' | 'arm64' | 'universal';
  requirements: SystemRequirements;
  components: SetupComponent[];
  settings: SetupSettings;
  autoStart: boolean;
  updateChannel: 'stable' | 'beta' | 'nightly';
  createdAt: Date;
  updatedAt: Date;
}

export interface SystemRequirements {
  os: {
    name: string;
    version: string;
    architecture: string[];
  };
  hardware: {
    cpu: {
      cores: number;
      frequency: number; // MHz
      features?: string[];
    };
    memory: {
      minimum: number; // GB
      recommended: number; // GB
    };
    storage: {
      minimum: number; // GB
      recommended: number; // GB
      type: 'any' | 'ssd' | 'nvme';
    };
    network: {
      bandwidth: number; // Mbps
      latency?: number; // ms
    };
    gpu?: {
      required: boolean;
      vram?: number; // GB
      compute?: string[];
    };
  };
  software: {
    runtime?: RuntimeRequirement[];
    dependencies?: SoftwareDependency[];
    conflicts?: string[];
  };
}

export interface RuntimeRequirement {
  name: string;
  version: string;
  optional: boolean;
  downloadUrl?: string;
  installCommand?: string;
}

export interface SoftwareDependency {
  name: string;
  version?: string;
  package?: string;
  repository?: string;
  critical: boolean;
}

export interface SetupComponent {
  id: string;
  name: string;
  description: string;
  type: 'service' | 'binary' | 'container' | 'package' | 'configuration';
  category: 'core' | 'monitoring' | 'security' | 'networking' | 'storage' | 'optional';
  required: boolean;
  installOrder: number;
  dependencies: string[];
  configuration: ComponentConfiguration;
  installation: InstallationMethod;
  verification: VerificationMethod;
  enabled: boolean;
}

export interface ComponentConfiguration {
  ports?: PortConfig[];
  environment?: EnvironmentConfig[];
  files?: FileConfig[];
  services?: ServiceConfig[];
  networking?: NetworkConfig;
  security?: SecurityConfig;
}

export interface PortConfig {
  port: number;
  protocol: 'tcp' | 'udp';
  bind: string;
  description: string;
  required: boolean;
}

export interface EnvironmentConfig {
  key: string;
  value?: string;
  required: boolean;
  secure: boolean;
  description: string;
  defaultValue?: string;
}

export interface FileConfig {
  path: string;
  content?: string;
  template?: string;
  permissions: string;
  owner?: string;
  group?: string;
  backup: boolean;
}

export interface ServiceConfig {
  name: string;
  type: 'systemd' | 'docker' | 'process' | 'cron';
  command: string;
  workingDirectory?: string;
  user?: string;
  environment?: Record<string, string>;
  restart: boolean;
  autoStart: boolean;
}

export interface NetworkConfig {
  interfaces?: string[];
  firewall?: FirewallConfig[];
  dns?: string[];
  hosts?: HostConfig[];
}

export interface FirewallConfig {
  port: number | string;
  protocol: 'tcp' | 'udp' | 'icmp' | 'any';
  source?: string;
  destination?: string;
  action: 'allow' | 'deny';
  direction: 'inbound' | 'outbound' | 'both';
}

export interface HostConfig {
  hostname: string;
  ip: string;
}

export interface SecurityConfig {
  certificates?: CertificateConfig[];
  keys?: KeyConfig[];
  users?: UserConfig[];
  permissions?: PermissionConfig[];
}

export interface CertificateConfig {
  name: string;
  type: 'ssl' | 'ssh' | 'gpg';
  path: string;
  autoGenerate: boolean;
  renewal?: string;
}

export interface KeyConfig {
  name: string;
  type: 'rsa' | 'ed25519' | 'ecdsa';
  size: number;
  path: string;
  usage: 'signing' | 'encryption' | 'authentication';
}

export interface UserConfig {
  username: string;
  uid?: number;
  gid?: number;
  groups?: string[];
  shell?: string;
  home?: string;
  system: boolean;
}

export interface PermissionConfig {
  path: string;
  owner: string;
  group: string;
  permissions: string;
  recursive: boolean;
}

export interface InstallationMethod {
  type: 'download' | 'package' | 'docker' | 'git' | 'npm' | 'pip' | 'manual' | 'script';
  source?: string;
  destination?: string;
  commands?: string[];
  options?: Record<string, any>;
  postInstall?: string[];
  preInstall?: string[];
  rollback?: string[];
}

export interface VerificationMethod {
  type: 'command' | 'file' | 'service' | 'http' | 'port' | 'process';
  target: string;
  expected?: string;
  timeout: number; // seconds
  retries: number;
  interval: number; // seconds
}

export interface SetupSettings {
  installation: {
    path: string;
    dataPath: string;
    logPath: string;
    configPath: string;
    backupPath: string;
    tmpPath: string;
  };
  network: {
    ports: {
      api: number;
      web: number;
      websocket: number;
      monitoring: number;
    };
    bindAddress: string;
    publicAddress?: string;
    ssl: {
      enabled: boolean;
      certPath?: string;
      keyPath?: string;
      autoGenerate: boolean;
    };
  };
  security: {
    authentication: {
      enabled: boolean;
      method: 'local' | 'oauth' | 'ldap' | 'saml';
      config?: Record<string, any>;
    };
    encryption: {
      enabled: boolean;
      algorithm: string;
      keyPath?: string;
    };
    firewall: {
      enabled: boolean;
      rules: FirewallConfig[];
    };
  };
  logging: {
    level: 'debug' | 'info' | 'warn' | 'error';
    format: 'json' | 'text';
    rotation: {
      enabled: boolean;
      maxSize: string;
      maxFiles: number;
      maxAge: string;
    };
  };
  monitoring: {
    enabled: boolean;
    metrics: {
      enabled: boolean;
      port: number;
      path: string;
    };
    healthCheck: {
      enabled: boolean;
      port: number;
      path: string;
      interval: number;
    };
  };
  updates: {
    autoUpdate: boolean;
    channel: 'stable' | 'beta' | 'nightly';
    checkInterval: number; // hours
    backupBeforeUpdate: boolean;
  };
}

export interface SetupProgress {
  id: string;
  configurationId: string;
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
  currentStep: number;
  totalSteps: number;
  currentComponent?: string;
  startedAt: Date;
  completedAt?: Date;
  elapsedTime: number; // seconds
  estimatedTimeRemaining?: number; // seconds
  steps: SetupStep[];
  logs: SetupLog[];
  errors: SetupError[];
  canPause: boolean;
  canResume: boolean;
  canRollback: boolean;
}

export interface SetupStep {
  id: string;
  name: string;
  description: string;
  componentId?: string;
  type: 'validation' | 'download' | 'install' | 'configure' | 'verify' | 'cleanup';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  startedAt?: Date;
  completedAt?: Date;
  duration?: number; // seconds
  progress: number; // 0-100
  output?: string;
  error?: string;
  retryCount: number;
  maxRetries: number;
  skippable: boolean;
}

export interface SetupLog {
  timestamp: Date;
  level: 'debug' | 'info' | 'warn' | 'error';
  component?: string;
  message: string;
  context?: Record<string, any>;
}

export interface SetupError {
  timestamp: Date;
  stepId: string;
  component?: string;
  type: 'validation' | 'download' | 'installation' | 'configuration' | 'verification' | 'system';
  code: string;
  message: string;
  details?: string;
  recoverable: boolean;
  suggestions: string[];
}

export interface SystemInfo {
  platform: string;
  architecture: string;
  version: string;
  hostname: string;
  cpu: {
    model: string;
    cores: number;
    frequency: number;
    features: string[];
  };
  memory: {
    total: number;
    available: number;
    used: number;
  };
  storage: {
    total: number;
    available: number;
    used: number;
    type: string;
  };
  network: {
    interfaces: NetworkInterface[];
    connectivity: boolean;
    bandwidth: number;
  };
  software: {
    docker?: string;
    nodejs?: string;
    python?: string;
    git?: string;
  };
  permissions: {
    root: boolean;
    sudo: boolean;
    docker: boolean;
  };
}

export interface NetworkInterface {
  name: string;
  type: string;
  address: string;
  netmask: string;
  gateway?: string;
  status: 'up' | 'down';
}

export interface SetupValidation {
  passed: boolean;
  warnings: ValidationWarning[];
  errors: ValidationError[];
  requirements: RequirementCheck[];
}

export interface ValidationWarning {
  component: string;
  message: string;
  suggestion: string;
  impact: 'low' | 'medium' | 'high';
}

export interface ValidationError {
  component: string;
  requirement: string;
  current: string;
  expected: string;
  blocking: boolean;
  solution: string;
}

export interface RequirementCheck {
  name: string;
  type: 'hardware' | 'software' | 'network' | 'permissions';
  status: 'pass' | 'warning' | 'fail';
  current: string;
  required: string;
  details?: string;
}

export class PlugAndPlaySetup extends EventEmitter {
  private configurations: Map<string, SetupConfiguration> = new Map();
  private progresses: Map<string, SetupProgress> = new Map();
  private systemInfo: SystemInfo | null = null;
  private currentSetup: string | null = null;

  constructor() {
    super();
    this.initializeDefaultConfigurations();
  }

  public async getSystemInfo(): Promise<SystemInfo> {
    if (!this.systemInfo) {
      this.systemInfo = await this.detectSystemInfo();
    }
    return this.systemInfo;
  }

  private async detectSystemInfo(): Promise<SystemInfo> {
    try {
      // Detect platform and architecture
      const platform = process.platform;
      const architecture = process.arch;
      
      // Get system information
      const { stdout: hostname } = await execAsync('hostname');
      const { stdout: meminfo } = await execAsync('cat /proc/meminfo').catch(() => ({ stdout: '' }));
      const { stdout: cpuinfo } = await execAsync('cat /proc/cpuinfo').catch(() => ({ stdout: '' }));
      const { stdout: df } = await execAsync('df -h /').catch(() => ({ stdout: '' }));
      
      // Parse memory information
      const memTotal = this.parseMemoryValue(meminfo, 'MemTotal');
      const memAvailable = this.parseMemoryValue(meminfo, 'MemAvailable');
      
      // Parse CPU information
      const cpuModel = this.parseCpuInfo(cpuinfo, 'model name');
      const cpuCores = this.parseCpuCores(cpuinfo);
      
      // Parse storage information
      const storage = this.parseStorageInfo(df);
      
      // Check software versions
      const software = await this.detectSoftware();
      
      // Check permissions
      const permissions = await this.checkPermissions();
      
      // Get network interfaces
      const interfaces = await this.getNetworkInterfaces();
      
      return {
        platform,
        architecture,
        version: process.version,
        hostname: hostname.trim(),
        cpu: {
          model: cpuModel,
          cores: cpuCores,
          frequency: 0, // Would need additional detection
          features: []
        },
        memory: {
          total: memTotal,
          available: memAvailable,
          used: memTotal - memAvailable
        },
        storage: {
          total: storage.total,
          available: storage.available,
          used: storage.used,
          type: 'unknown'
        },
        network: {
          interfaces: interfaces,
          connectivity: true, // Would need connectivity check
          bandwidth: 0 // Would need bandwidth test
        },
        software,
        permissions
      };
    } catch (error) {
      console.error('Failed to detect system info:', error);
      throw new Error('System detection failed');
    }
  }

  private parseMemoryValue(meminfo: string, key: string): number {
    const regex = new RegExp(`${key}:\\s+(\\d+)\\s+kB`);
    const match = meminfo.match(regex);
    return match ? parseInt(match[1]) / 1024 / 1024 : 0; // Convert kB to GB
  }

  private parseCpuInfo(cpuinfo: string, key: string): string {
    const regex = new RegExp(`${key}\\s*:\\s*(.+)`);
    const match = cpuinfo.match(regex);
    return match ? match[1].trim() : 'Unknown';
  }

  private parseCpuCores(cpuinfo: string): number {
    const matches = cpuinfo.match(/processor\s*:/g);
    return matches ? matches.length : 1;
  }

  private parseStorageInfo(df: string): { total: number; available: number; used: number } {
    const lines = df.split('\n');
    const rootLine = lines.find(line => line.includes('/') && !line.includes('/proc'));
    
    if (!rootLine) {
      return { total: 0, available: 0, used: 0 };
    }
    
    const parts = rootLine.split(/\s+/);
    const total = this.parseStorageSize(parts[1] || '0');
    const used = this.parseStorageSize(parts[2] || '0');
    const available = this.parseStorageSize(parts[3] || '0');
    
    return { total, available, used };
  }

  private parseStorageSize(size: string): number {
    const match = size.match(/^(\d+(?:\.\d+)?)(K|M|G|T)?$/);
    if (!match) return 0;
    
    const value = parseFloat(match[1]);
    const unit = match[2] || '';
    
    switch (unit) {
      case 'K': return value / 1024 / 1024; // Convert to GB
      case 'M': return value / 1024; // Convert to GB
      case 'G': return value;
      case 'T': return value * 1024;
      default: return value / 1024 / 1024 / 1024; // Assume bytes
    }
  }

  private async detectSoftware(): Promise<Record<string, string | undefined>> {
    const software: Record<string, string | undefined> = {};
    
    try {
      const { stdout: dockerVersion } = await execAsync('docker --version').catch(() => ({ stdout: '' }));
      software.docker = dockerVersion.trim() || undefined;
    } catch {}
    
    try {
      const { stdout: nodeVersion } = await execAsync('node --version').catch(() => ({ stdout: '' }));
      software.nodejs = nodeVersion.trim() || undefined;
    } catch {}
    
    try {
      const { stdout: pythonVersion } = await execAsync('python3 --version').catch(() => ({ stdout: '' }));
      software.python = pythonVersion.trim() || undefined;
    } catch {}
    
    try {
      const { stdout: gitVersion } = await execAsync('git --version').catch(() => ({ stdout: '' }));
      software.git = gitVersion.trim() || undefined;
    } catch {}
    
    return software;
  }

  private async checkPermissions(): Promise<{ root: boolean; sudo: boolean; docker: boolean }> {
    const permissions = {
      root: process.getuid?.() === 0,
      sudo: false,
      docker: false
    };
    
    try {
      await execAsync('sudo -n true');
      permissions.sudo = true;
    } catch {}
    
    try {
      await execAsync('docker ps');
      permissions.docker = true;
    } catch {}
    
    return permissions;
  }

  private async getNetworkInterfaces(): Promise<NetworkInterface[]> {
    const interfaces: NetworkInterface[] = [];
    
    try {
      const { stdout: ifconfig } = await execAsync('ip addr show').catch(() => 
        execAsync('ifconfig').catch(() => ({ stdout: '' }))
      );
      
      // Parse network interfaces (simplified)
      const lines = ifconfig.split('\n');
      let currentInterface: Partial<NetworkInterface> = {};
      
      for (const line of lines) {
        if (line.match(/^\d+:/)) {
          if (currentInterface.name) {
            interfaces.push(currentInterface as NetworkInterface);
          }
          currentInterface = {
            name: line.split(':')[1]?.trim() || 'unknown',
            type: 'ethernet',
            status: line.includes('UP') ? 'up' : 'down'
          };
        } else if (line.includes('inet ') && currentInterface.name) {
          const match = line.match(/inet (\S+)/);
          if (match) {
            const [ip, netmask] = match[1].split('/');
            currentInterface.address = ip;
            currentInterface.netmask = netmask || '24';
          }
        }
      }
      
      if (currentInterface.name) {
        interfaces.push(currentInterface as NetworkInterface);
      }
    } catch (error) {
      console.error('Failed to get network interfaces:', error);
    }
    
    return interfaces;
  }

  public async validateSystem(configId: string): Promise<SetupValidation> {
    const config = this.configurations.get(configId);
    if (!config) {
      throw new Error('Configuration not found');
    }
    
    const systemInfo = await this.getSystemInfo();
    const validation: SetupValidation = {
      passed: true,
      warnings: [],
      errors: [],
      requirements: []
    };
    
    // Validate hardware requirements
    this.validateHardware(config.requirements.hardware, systemInfo, validation);
    
    // Validate software requirements
    await this.validateSoftware(config.requirements.software, systemInfo, validation);
    
    // Validate OS compatibility
    this.validateOperatingSystem(config.requirements.os, systemInfo, validation);
    
    // Validate permissions
    this.validatePermissions(systemInfo, validation);
    
    validation.passed = validation.errors.length === 0;
    
    this.emit('systemValidated', configId, validation);
    return validation;
  }

  private validateHardware(requirements: SystemRequirements['hardware'], systemInfo: SystemInfo, validation: SetupValidation): void {
    // CPU validation
    if (systemInfo.cpu.cores < requirements.cpu.cores) {
      validation.errors.push({
        component: 'CPU',
        requirement: 'cores',
        current: systemInfo.cpu.cores.toString(),
        expected: requirements.cpu.cores.toString(),
        blocking: true,
        solution: `Upgrade to a system with at least ${requirements.cpu.cores} CPU cores`
      });
    }
    
    validation.requirements.push({
      name: 'CPU Cores',
      type: 'hardware',
      status: systemInfo.cpu.cores >= requirements.cpu.cores ? 'pass' : 'fail',
      current: systemInfo.cpu.cores.toString(),
      required: requirements.cpu.cores.toString()
    });
    
    // Memory validation
    if (systemInfo.memory.total < requirements.memory.minimum) {
      validation.errors.push({
        component: 'Memory',
        requirement: 'minimum',
        current: `${systemInfo.memory.total.toFixed(1)}GB`,
        expected: `${requirements.memory.minimum}GB`,
        blocking: true,
        solution: `Upgrade system memory to at least ${requirements.memory.minimum}GB`
      });
    } else if (systemInfo.memory.total < requirements.memory.recommended) {
      validation.warnings.push({
        component: 'Memory',
        message: `System has ${systemInfo.memory.total.toFixed(1)}GB RAM, but ${requirements.memory.recommended}GB is recommended`,
        suggestion: `Consider upgrading to ${requirements.memory.recommended}GB RAM for optimal performance`,
        impact: 'medium'
      });
    }
    
    validation.requirements.push({
      name: 'System Memory',
      type: 'hardware',
      status: systemInfo.memory.total >= requirements.memory.minimum ? 
        (systemInfo.memory.total >= requirements.memory.recommended ? 'pass' : 'warning') : 'fail',
      current: `${systemInfo.memory.total.toFixed(1)}GB`,
      required: `${requirements.memory.minimum}GB (${requirements.memory.recommended}GB recommended)`
    });
    
    // Storage validation
    if (systemInfo.storage.available < requirements.storage.minimum) {
      validation.errors.push({
        component: 'Storage',
        requirement: 'minimum',
        current: `${systemInfo.storage.available.toFixed(1)}GB`,
        expected: `${requirements.storage.minimum}GB`,
        blocking: true,
        solution: `Free up disk space or add storage to have at least ${requirements.storage.minimum}GB available`
      });
    } else if (systemInfo.storage.available < requirements.storage.recommended) {
      validation.warnings.push({
        component: 'Storage',
        message: `Available storage is ${systemInfo.storage.available.toFixed(1)}GB, but ${requirements.storage.recommended}GB is recommended`,
        suggestion: `Consider freeing up disk space or adding storage`,
        impact: 'low'
      });
    }
    
    validation.requirements.push({
      name: 'Available Storage',
      type: 'hardware',
      status: systemInfo.storage.available >= requirements.storage.minimum ?
        (systemInfo.storage.available >= requirements.storage.recommended ? 'pass' : 'warning') : 'fail',
      current: `${systemInfo.storage.available.toFixed(1)}GB`,
      required: `${requirements.storage.minimum}GB (${requirements.storage.recommended}GB recommended)`
    });
  }

  private async validateSoftware(requirements: SystemRequirements['software'], systemInfo: SystemInfo, validation: SetupValidation): Promise<void> {
    if (!requirements.runtime && !requirements.dependencies) return;
    
    // Validate runtime requirements
    if (requirements.runtime) {
      for (const runtime of requirements.runtime) {
        const installed = systemInfo.software[runtime.name.toLowerCase()];
        const status = installed ? 'pass' : (runtime.optional ? 'warning' : 'fail');
        
        validation.requirements.push({
          name: runtime.name,
          type: 'software',
          status,
          current: installed || 'Not installed',
          required: runtime.version,
          details: runtime.optional ? 'Optional' : 'Required'
        });
        
        if (!installed && !runtime.optional) {
          validation.errors.push({
            component: 'Software',
            requirement: runtime.name,
            current: 'Not installed',
            expected: runtime.version,
            blocking: true,
            solution: runtime.installCommand || `Install ${runtime.name} ${runtime.version}`
          });
        } else if (!installed && runtime.optional) {
          validation.warnings.push({
            component: 'Software',
            message: `${runtime.name} is not installed but is recommended for optimal functionality`,
            suggestion: runtime.installCommand || `Consider installing ${runtime.name}`,
            impact: 'low'
          });
        }
      }
    }
    
    // Check for conflicting software
    if (requirements.conflicts) {
      for (const conflict of requirements.conflicts) {
        const installed = systemInfo.software[conflict.toLowerCase()];
        if (installed) {
          validation.warnings.push({
            component: 'Software',
            message: `Conflicting software detected: ${conflict}`,
            suggestion: `Consider removing or disabling ${conflict} before installation`,
            impact: 'high'
          });
        }
      }
    }
  }

  private validateOperatingSystem(requirements: SystemRequirements['os'], systemInfo: SystemInfo, validation: SetupValidation): void {
    const platformMatch = requirements.name === 'any' || 
      systemInfo.platform.toLowerCase().includes(requirements.name.toLowerCase());
    
    validation.requirements.push({
      name: 'Operating System',
      type: 'software',
      status: platformMatch ? 'pass' : 'fail',
      current: `${systemInfo.platform} ${systemInfo.version}`,
      required: `${requirements.name} ${requirements.version}`
    });
    
    if (!platformMatch) {
      validation.errors.push({
        component: 'Operating System',
        requirement: 'platform',
        current: systemInfo.platform,
        expected: requirements.name,
        blocking: true,
        solution: `This software requires ${requirements.name} ${requirements.version}`
      });
    }
    
    // Architecture validation
    const archMatch = requirements.architecture.includes(systemInfo.architecture as any);
    
    validation.requirements.push({
      name: 'Architecture',
      type: 'hardware',
      status: archMatch ? 'pass' : 'fail',
      current: systemInfo.architecture,
      required: requirements.architecture.join(', ')
    });
    
    if (!archMatch) {
      validation.errors.push({
        component: 'Architecture',
        requirement: 'compatibility',
        current: systemInfo.architecture,
        expected: requirements.architecture.join(' or '),
        blocking: true,
        solution: `This software requires ${requirements.architecture.join(' or ')} architecture`
      });
    }
  }

  private validatePermissions(systemInfo: SystemInfo, validation: SetupValidation): void {
    validation.requirements.push({
      name: 'Root/Administrator',
      type: 'permissions',
      status: systemInfo.permissions.root || systemInfo.permissions.sudo ? 'pass' : 'warning',
      current: systemInfo.permissions.root ? 'Root' : (systemInfo.permissions.sudo ? 'Sudo' : 'User'),
      required: 'Root or Sudo access'
    });
    
    if (!systemInfo.permissions.root && !systemInfo.permissions.sudo) {
      validation.warnings.push({
        component: 'Permissions',
        message: 'Installation may require administrator privileges',
        suggestion: 'Run the installer with sudo or as administrator',
        impact: 'medium'
      });
    }
    
    validation.requirements.push({
      name: 'Docker Access',
      type: 'permissions',
      status: systemInfo.permissions.docker ? 'pass' : 'warning',
      current: systemInfo.permissions.docker ? 'Available' : 'Not available',
      required: 'Docker access recommended'
    });
  }

  public async startSetup(configId: string, customSettings?: Partial<SetupSettings>): Promise<string> {
    const config = this.configurations.get(configId);
    if (!config) {
      throw new Error('Configuration not found');
    }

    // Validate system first
    const validation = await this.validateSystem(configId);
    if (!validation.passed) {
      throw new Error('System validation failed. Please resolve errors before proceeding.');
    }

    const setupId = this.generateSetupId();
    const steps = this.generateSetupSteps(config);
    
    const progress: SetupProgress = {
      id: setupId,
      configurationId: configId,
      status: 'pending',
      currentStep: 0,
      totalSteps: steps.length,
      startedAt: new Date(),
      elapsedTime: 0,
      steps,
      logs: [],
      errors: [],
      canPause: true,
      canResume: false,
      canRollback: false
    };

    this.progresses.set(setupId, progress);
    this.currentSetup = setupId;

    // Apply custom settings if provided
    if (customSettings) {
      config.settings = { ...config.settings, ...customSettings };
    }

    // Start setup process
    process.nextTick(() => this.executeSetup(setupId));

    this.emit('setupStarted', setupId, progress);
    return setupId;
  }

  private generateSetupSteps(config: SetupConfiguration): SetupStep[] {
    const steps: SetupStep[] = [];
    let stepOrder = 0;

    // System validation step
    steps.push({
      id: `step_${stepOrder++}`,
      name: 'System Validation',
      description: 'Validating system requirements',
      type: 'validation',
      status: 'pending',
      progress: 0,
      retryCount: 0,
      maxRetries: 3,
      skippable: false
    });

    // Pre-installation preparation
    steps.push({
      id: `step_${stepOrder++}`,
      name: 'Preparation',
      description: 'Preparing installation environment',
      type: 'validation',
      status: 'pending',
      progress: 0,
      retryCount: 0,
      maxRetries: 3,
      skippable: false
    });

    // Component installation steps
    const sortedComponents = config.components
      .sort((a, b) => a.installOrder - b.installOrder);

    for (const component of sortedComponents) {
      if (!component.enabled) continue;

      // Download step
      if (component.installation.type === 'download') {
        steps.push({
          id: `step_${stepOrder++}`,
          name: `Download ${component.name}`,
          description: `Downloading ${component.name}`,
          componentId: component.id,
          type: 'download',
          status: 'pending',
          progress: 0,
          retryCount: 0,
          maxRetries: 3,
          skippable: !component.required
        });
      }

      // Install step
      steps.push({
        id: `step_${stepOrder++}`,
        name: `Install ${component.name}`,
        description: `Installing ${component.name}`,
        componentId: component.id,
        type: 'install',
        status: 'pending',
        progress: 0,
        retryCount: 0,
        maxRetries: 3,
        skippable: !component.required
      });

      // Configure step
      if (component.configuration) {
        steps.push({
          id: `step_${stepOrder++}`,
          name: `Configure ${component.name}`,
          description: `Configuring ${component.name}`,
          componentId: component.id,
          type: 'configure',
          status: 'pending',
          progress: 0,
          retryCount: 0,
          maxRetries: 3,
          skippable: false
        });
      }

      // Verification step
      if (component.verification) {
        steps.push({
          id: `step_${stepOrder++}`,
          name: `Verify ${component.name}`,
          description: `Verifying ${component.name} installation`,
          componentId: component.id,
          type: 'verify',
          status: 'pending',
          progress: 0,
          retryCount: 0,
          maxRetries: 3,
          skippable: true
        });
      }
    }

    // Final configuration and cleanup
    steps.push({
      id: `step_${stepOrder++}`,
      name: 'Final Configuration',
      description: 'Applying final system configuration',
      type: 'configure',
      status: 'pending',
      progress: 0,
      retryCount: 0,
      maxRetries: 3,
      skippable: false
    });

    steps.push({
      id: `step_${stepOrder++}`,
      name: 'Cleanup',
      description: 'Cleaning up temporary files',
      type: 'cleanup',
      status: 'pending',
      progress: 0,
      retryCount: 0,
      maxRetries: 1,
      skippable: true
    });

    return steps;
  }

  private async executeSetup(setupId: string): Promise<void> {
    const progress = this.progresses.get(setupId);
    if (!progress) return;

    const config = this.configurations.get(progress.configurationId);
    if (!config) return;

    try {
      progress.status = 'running';
      progress.startedAt = new Date();
      this.progresses.set(setupId, progress);

      for (let i = 0; i < progress.steps.length; i++) {
        if (progress.status === 'paused') {
          break;
        }

        progress.currentStep = i;
        const step = progress.steps[i];
        
        this.addLog(progress, 'info', `Starting step: ${step.name}`, step.componentId);
        
        try {
          await this.executeStep(step, config, progress);
          step.status = 'completed';
          step.progress = 100;
          step.completedAt = new Date();
          
          if (step.startedAt) {
            step.duration = (step.completedAt.getTime() - step.startedAt.getTime()) / 1000;
          }
          
          this.addLog(progress, 'info', `Completed step: ${step.name}`, step.componentId);
          
        } catch (error) {
          const errorMessage = (error as Error).message;
          step.error = errorMessage;
          step.status = 'failed';
          
          this.addError(progress, step.id, step.componentId || 'system', 'installation', 
            'STEP_FAILED', errorMessage, errorMessage);
          
          if (step.retryCount < step.maxRetries) {
            step.retryCount++;
            step.status = 'pending';
            this.addLog(progress, 'warn', `Retrying step: ${step.name} (attempt ${step.retryCount + 1})`, step.componentId);
            i--; // Retry the same step
            continue;
          }
          
          if (!step.skippable) {
            throw error;
          } else {
            step.status = 'skipped';
            this.addLog(progress, 'warn', `Skipped step: ${step.name} due to error: ${errorMessage}`, step.componentId);
          }
        }
        
        this.emit('stepCompleted', setupId, step);
        this.progresses.set(setupId, progress);
      }

      if (progress.status === 'running') {
        progress.status = 'completed';
        progress.completedAt = new Date();
        progress.elapsedTime = (progress.completedAt.getTime() - progress.startedAt.getTime()) / 1000;
        
        this.addLog(progress, 'info', 'Setup completed successfully');
        this.emit('setupCompleted', setupId, progress);
      }

    } catch (error) {
      progress.status = 'failed';
      progress.completedAt = new Date();
      progress.elapsedTime = (progress.completedAt.getTime() - progress.startedAt.getTime()) / 1000;
      
      const errorMessage = (error as Error).message;
      this.addError(progress, 'setup', undefined, 'system', 'SETUP_FAILED', 'Setup failed', errorMessage);
      this.addLog(progress, 'error', `Setup failed: ${errorMessage}`);
      
      this.emit('setupFailed', setupId, progress, error);
    }

    this.progresses.set(setupId, progress);
    this.currentSetup = null;
  }

  private async executeStep(step: SetupStep, config: SetupConfiguration, progress: SetupProgress): Promise<void> {
    step.status = 'running';
    step.startedAt = new Date();
    step.progress = 0;

    const component = step.componentId ? 
      config.components.find(c => c.id === step.componentId) : null;

    switch (step.type) {
      case 'validation':
        await this.executeValidationStep(step, config);
        break;
      case 'download':
        if (component) await this.executeDownloadStep(step, component);
        break;
      case 'install':
        if (component) await this.executeInstallStep(step, component);
        break;
      case 'configure':
        await this.executeConfigureStep(step, component || config);
        break;
      case 'verify':
        if (component) await this.executeVerifyStep(step, component);
        break;
      case 'cleanup':
        await this.executeCleanupStep(step);
        break;
    }

    step.progress = 100;
  }

  private async executeValidationStep(step: SetupStep, config: SetupConfiguration): Promise<void> {
    step.progress = 25;
    
    // Re-validate system
    const validation = await this.validateSystem(config.id);
    step.progress = 75;
    
    if (!validation.passed) {
      throw new Error(`System validation failed: ${validation.errors.map(e => e.message).join(', ')}`);
    }
    
    step.progress = 100;
    step.output = 'System validation passed';
  }

  private async executeDownloadStep(step: SetupStep, component: SetupComponent): Promise<void> {
    const installation = component.installation;
    
    if (installation.type !== 'download' || !installation.source) {
      throw new Error('Invalid download configuration');
    }

    step.progress = 25;
    
    // Simulate download process
    // In a real implementation, this would actually download the file
    await new Promise(resolve => setTimeout(resolve, 2000));
    step.progress = 75;
    
    await new Promise(resolve => setTimeout(resolve, 1000));
    step.progress = 100;
    
    step.output = `Downloaded ${component.name} from ${installation.source}`;
  }

  private async executeInstallStep(step: SetupStep, component: SetupComponent): Promise<void> {
    const installation = component.installation;
    
    step.progress = 10;
    
    // Execute pre-install commands
    if (installation.preInstall) {
      for (const command of installation.preInstall) {
        await this.executeCommand(command);
        step.progress += 15;
      }
    }
    
    // Execute main installation commands
    if (installation.commands) {
      const progressPerCommand = 60 / installation.commands.length;
      for (const command of installation.commands) {
        await this.executeCommand(command);
        step.progress += progressPerCommand;
      }
    }
    
    // Execute post-install commands
    if (installation.postInstall) {
      for (const command of installation.postInstall) {
        await this.executeCommand(command);
        step.progress += 10;
      }
    }
    
    step.progress = 100;
    step.output = `Installed ${component.name}`;
  }

  private async executeConfigureStep(step: SetupStep, configurable: SetupComponent | SetupConfiguration): Promise<void> {
    step.progress = 20;
    
    if ('configuration' in configurable && configurable.configuration) {
      const config = configurable.configuration;
      
      // Configure files
      if (config.files) {
        for (const fileConfig of config.files) {
          await this.configureFile(fileConfig);
          step.progress += 15;
        }
      }
      
      // Configure services
      if (config.services) {
        for (const serviceConfig of config.services) {
          await this.configureService(serviceConfig);
          step.progress += 15;
        }
      }
      
      // Configure networking
      if (config.networking) {
        await this.configureNetworking(config.networking);
        step.progress += 20;
      }
      
      // Configure security
      if (config.security) {
        await this.configureSecurity(config.security);
        step.progress += 20;
      }
    }
    
    step.progress = 100;
    step.output = 'Configuration completed';
  }

  private async executeVerifyStep(step: SetupStep, component: SetupComponent): Promise<void> {
    const verification = component.verification;
    
    step.progress = 25;
    
    let verified = false;
    for (let attempt = 0; attempt < verification.retries; attempt++) {
      try {
        switch (verification.type) {
          case 'command':
            const { stdout } = await execAsync(verification.target);
            verified = !verification.expected || stdout.includes(verification.expected);
            break;
          case 'service':
            const { stdout: serviceStatus } = await execAsync(`systemctl is-active ${verification.target}`);
            verified = serviceStatus.trim() === 'active';
            break;
          case 'port':
            const port = parseInt(verification.target);
            verified = await this.checkPort(port);
            break;
          case 'http':
            verified = await this.checkHttp(verification.target);
            break;
          case 'file':
            verified = await this.checkFile(verification.target);
            break;
          case 'process':
            const { stdout: processes } = await execAsync(`pgrep ${verification.target}`);
            verified = processes.trim().length > 0;
            break;
        }
        
        if (verified) break;
        
      } catch (error) {
        // Continue to next attempt
      }
      
      if (attempt < verification.retries - 1) {
        await new Promise(resolve => setTimeout(resolve, verification.interval * 1000));
      }
      
      step.progress = 25 + ((attempt + 1) / verification.retries) * 50;
    }
    
    if (!verified) {
      throw new Error(`Verification failed for ${component.name}: ${verification.type} ${verification.target}`);
    }
    
    step.progress = 100;
    step.output = `Verified ${component.name}`;
  }

  private async executeCleanupStep(step: SetupStep): Promise<void> {
    step.progress = 50;
    
    // Clean up temporary files and directories
    // This would implement actual cleanup logic
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    step.progress = 100;
    step.output = 'Cleanup completed';
  }

  private async executeCommand(command: string): Promise<string> {
    try {
      const { stdout, stderr } = await execAsync(command, { timeout: 30000 });
      return stdout + stderr;
    } catch (error) {
      throw new Error(`Command failed: ${command}\n${(error as any).message}`);
    }
  }

  private async configureFile(fileConfig: FileConfig): Promise<void> {
    // File configuration implementation
    // This would create/modify files based on the configuration
  }

  private async configureService(serviceConfig: ServiceConfig): Promise<void> {
    // Service configuration implementation
    // This would configure systemd services, docker containers, etc.
  }

  private async configureNetworking(networkConfig: NetworkConfig): Promise<void> {
    // Network configuration implementation
    // This would configure firewall rules, DNS, etc.
  }

  private async configureSecurity(securityConfig: SecurityConfig): Promise<void> {
    // Security configuration implementation
    // This would configure certificates, users, permissions, etc.
  }

  private async checkPort(port: number): Promise<boolean> {
    try {
      const { stdout } = await execAsync(`netstat -tuln | grep :${port}`);
      return stdout.trim().length > 0;
    } catch {
      return false;
    }
  }

  private async checkHttp(url: string): Promise<boolean> {
    try {
      const { stdout } = await execAsync(`curl -s -o /dev/null -w "%{http_code}" ${url}`);
      const statusCode = parseInt(stdout.trim());
      return statusCode >= 200 && statusCode < 400;
    } catch {
      return false;
    }
  }

  private async checkFile(path: string): Promise<boolean> {
    try {
      await execAsync(`test -f ${path}`);
      return true;
    } catch {
      return false;
    }
  }

  private addLog(progress: SetupProgress, level: SetupLog['level'], message: string, component?: string): void {
    progress.logs.push({
      timestamp: new Date(),
      level,
      component,
      message
    });
    
    // Keep only last 1000 log entries
    if (progress.logs.length > 1000) {
      progress.logs = progress.logs.slice(-1000);
    }
  }

  private addError(
    progress: SetupProgress,
    stepId: string,
    component: string | undefined,
    type: SetupError['type'],
    code: string,
    message: string,
    details: string
  ): void {
    progress.errors.push({
      timestamp: new Date(),
      stepId,
      component,
      type,
      code,
      message,
      details,
      recoverable: true,
      suggestions: ['Check system requirements', 'Review error logs', 'Contact support']
    });
  }

  public async pauseSetup(setupId: string): Promise<void> {
    const progress = this.progresses.get(setupId);
    if (!progress || !progress.canPause) {
      throw new Error('Setup cannot be paused');
    }

    progress.status = 'paused';
    progress.canPause = false;
    progress.canResume = true;
    this.progresses.set(setupId, progress);

    this.emit('setupPaused', setupId, progress);
  }

  public async resumeSetup(setupId: string): Promise<void> {
    const progress = this.progresses.get(setupId);
    if (!progress || !progress.canResume) {
      throw new Error('Setup cannot be resumed');
    }

    progress.status = 'running';
    progress.canPause = true;
    progress.canResume = false;
    this.progresses.set(setupId, progress);

    // Continue from current step
    this.currentSetup = setupId;
    process.nextTick(() => this.executeSetup(setupId));

    this.emit('setupResumed', setupId, progress);
  }

  public async cancelSetup(setupId: string): Promise<void> {
    const progress = this.progresses.get(setupId);
    if (!progress) {
      throw new Error('Setup not found');
    }

    progress.status = 'cancelled';
    progress.completedAt = new Date();
    progress.elapsedTime = (progress.completedAt.getTime() - progress.startedAt.getTime()) / 1000;
    this.progresses.set(setupId, progress);

    this.addLog(progress, 'info', 'Setup cancelled by user');
    this.emit('setupCancelled', setupId, progress);
  }

  public getSetupProgress(setupId: string): SetupProgress | undefined {
    return this.progresses.get(setupId);
  }

  public getConfiguration(configId: string): SetupConfiguration | undefined {
    return this.configurations.get(configId);
  }

  public getAllConfigurations(): SetupConfiguration[] {
    return Array.from(this.configurations.values());
  }

  private initializeDefaultConfigurations(): void {
    const defaultConfig: SetupConfiguration = {
      id: 'compute_market_standard',
      name: 'Compute Market - Standard Setup',
      description: 'Standard compute trading platform setup',
      version: '1.0.0',
      platform: 'linux',
      architecture: 'x86_64',
      requirements: {
        os: {
          name: 'linux',
          version: '18.04+',
          architecture: ['x86_64', 'arm64']
        },
        hardware: {
          cpu: { cores: 4, frequency: 2000 },
          memory: { minimum: 8, recommended: 16 },
          storage: { minimum: 50, recommended: 100, type: 'ssd' },
          network: { bandwidth: 100 }
        },
        software: {
          runtime: [
            { name: 'docker', version: '20.0+', optional: false },
            { name: 'nodejs', version: '18+', optional: false }
          ],
          dependencies: [
            { name: 'curl', critical: true },
            { name: 'git', critical: true }
          ]
        }
      },
      components: [
        {
          id: 'core_services',
          name: 'Core Services',
          description: 'Core compute market services',
          type: 'container',
          category: 'core',
          required: true,
          installOrder: 1,
          dependencies: [],
          configuration: {
            ports: [
              { port: 8310, protocol: 'tcp', bind: '0.0.0.0', description: 'API Server', required: true }
            ],
            environment: [
              { key: 'NODE_ENV', value: 'production', required: true, secure: false, description: 'Environment' }
            ]
          },
          installation: {
            type: 'docker',
            source: 'compute-market:latest',
            commands: ['docker run -d --name compute-market -p 8310:8310 compute-market:latest']
          },
          verification: {
            type: 'http',
            target: 'http://localhost:8310/health',
            timeout: 30,
            retries: 5,
            interval: 5
          },
          enabled: true
        }
      ],
      settings: {
        installation: {
          path: '/opt/compute-market',
          dataPath: '/var/lib/compute-market',
          logPath: '/var/log/compute-market',
          configPath: '/etc/compute-market',
          backupPath: '/var/backups/compute-market',
          tmpPath: '/tmp/compute-market'
        },
        network: {
          ports: { api: 8310, web: 8311, websocket: 8312, monitoring: 8313 },
          bindAddress: '0.0.0.0',
          ssl: { enabled: false, autoGenerate: false }
        },
        security: {
          authentication: { enabled: true, method: 'local' },
          encryption: { enabled: true, algorithm: 'AES-256' },
          firewall: { enabled: true, rules: [] }
        },
        logging: {
          level: 'info',
          format: 'json',
          rotation: { enabled: true, maxSize: '10MB', maxFiles: 10, maxAge: '30d' }
        },
        monitoring: {
          enabled: true,
          metrics: { enabled: true, port: 8313, path: '/metrics' },
          healthCheck: { enabled: true, port: 8310, path: '/health', interval: 30 }
        },
        updates: {
          autoUpdate: false,
          channel: 'stable',
          checkInterval: 24,
          backupBeforeUpdate: true
        }
      },
      autoStart: true,
      updateChannel: 'stable',
      createdAt: new Date(),
      updatedAt: new Date()
    };

    this.configurations.set(defaultConfig.id, defaultConfig);
  }

  private generateSetupId(): string {
    return `setup_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

export default PlugAndPlaySetup;