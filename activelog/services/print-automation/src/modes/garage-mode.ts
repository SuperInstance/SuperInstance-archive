import { EventEmitter } from 'events';

export interface GarageConfiguration {
  maxConcurrentJobs: number;
  operatingHours: {
    start: string;
    end: string;
    timezone: string;
  };
  noiseThreshold: number;
  temperatureRange: {
    min: number;
    max: number;
  };
  humidityRange: {
    min: number;
    max: number;
  };
  powerConsumptionLimit: number;
  autoShutdownEnabled: boolean;
  quietHours: {
    start: string;
    end: string;
  };
  ventilationRequired: boolean;
  safetyMonitoring: boolean;
}

export interface GarageConstraints {
  spaceConstraints: {
    length: number;
    width: number;
    height: number;
    usableSpace: number;
  };
  electricalConstraints: {
    maxVoltage: number;
    maxCurrent: number;
    circuitCapacity: number;
    safetyMargin: number;
  };
  environmentalConstraints: {
    hasHVAC: boolean;
    insulation: 'poor' | 'moderate' | 'good' | 'excellent';
    dustLevel: 'low' | 'medium' | 'high';
    vibrationLevel: 'low' | 'medium' | 'high';
  };
  accessibilityConstraints: {
    pedestrianAccess: boolean;
    vehicleAccess: boolean;
    storageAccess: boolean;
    maintenanceAccess: 'limited' | 'moderate' | 'full';
  };
}

export interface GarageOperationLimits {
  maxPrintersPerShelf: number;
  maxShelvesPerUnit: number;
  maxOperatingUnits: number;
  materialStorageLimit: number;
  workspaceReservation: number;
  emergencyShutdownTime: number;
  maintenanceWindow: number;
  bufferSpaceRequired: number;
}

export interface SafetyProtocol {
  id: string;
  name: string;
  description: string;
  type: SafetyProtocolType;
  triggers: SafetyTrigger[];
  actions: SafetyAction[];
  priority: SafetyPriority;
  isActive: boolean;
  lastTriggered?: Date;
  triggerCount: number;
}

export enum SafetyProtocolType {
  FIRE_PREVENTION = 'fire_prevention',
  ELECTRICAL_SAFETY = 'electrical_safety',
  AIR_QUALITY = 'air_quality',
  TEMPERATURE_CONTROL = 'temperature_control',
  NOISE_CONTROL = 'noise_control',
  EMERGENCY_SHUTDOWN = 'emergency_shutdown'
}

export interface SafetyTrigger {
  parameter: string;
  condition: 'gt' | 'lt' | 'eq' | 'gte' | 'lte';
  threshold: number;
  duration: number;
  consecutiveReadings: number;
}

export interface SafetyAction {
  action: string;
  priority: number;
  delay: number;
  parameters: Record<string, any>;
  requiresConfirmation: boolean;
}

export enum SafetyPriority {
  CRITICAL = 'critical',
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low'
}

export interface GarageEnvironmentReading {
  timestamp: Date;
  temperature: number;
  humidity: number;
  airQuality: number;
  noiseLevel: number;
  co2Level: number;
  vocLevel: number;
  powerConsumption: number;
  vibrationLevel: number;
}

export interface GarageSchedule {
  operationMode: 'continuous' | 'scheduled' | 'manual';
  quietHoursEnabled: boolean;
  autoStartEnabled: boolean;
  autoShutdownEnabled: boolean;
  scheduledTasks: ScheduledTask[];
  maintenanceWindows: MaintenanceWindow[];
}

export interface ScheduledTask {
  id: string;
  name: string;
  type: 'print_job' | 'maintenance' | 'material_change' | 'cleanup';
  scheduledTime: Date;
  estimatedDuration: number;
  priority: number;
  dependencies: string[];
  constraints: TaskConstraint[];
}

export interface TaskConstraint {
  type: 'environmental' | 'resource' | 'safety' | 'operational';
  parameter: string;
  operator: 'gt' | 'lt' | 'eq' | 'gte' | 'lte';
  value: number;
  required: boolean;
}

export interface MaintenanceWindow {
  id: string;
  start: Date;
  end: Date;
  type: 'routine' | 'deep_clean' | 'calibration' | 'repair';
  affectedPrinters: string[];
  requiredDowntime: number;
}

export class GarageOperationMode extends EventEmitter {
  private config: GarageConfiguration;
  private constraints: GarageConstraints;
  private operationLimits: GarageOperationLimits;
  private safetyProtocols: Map<string, SafetyProtocol> = new Map();
  private environmentalReadings: GarageEnvironmentReading[] = [];
  private schedule: GarageSchedule;
  private monitoringInterval?: NodeJS.Timeout;
  private isOperational = false;
  private activePrinters: Set<string> = new Set();
  private environmentalSensors: Map<string, any> = new Map();

  constructor(
    config: GarageConfiguration,
    constraints: GarageConstraints,
    operationLimits: GarageOperationLimits
  ) {
    super();
    
    this.config = config;
    this.constraints = constraints;
    this.operationLimits = operationLimits;
    
    this.schedule = {
      operationMode: 'scheduled',
      quietHoursEnabled: true,
      autoStartEnabled: false,
      autoShutdownEnabled: config.autoShutdownEnabled,
      scheduledTasks: [],
      maintenanceWindows: []
    };

    this.initializeSafetyProtocols();
    this.initializeEnvironmentalSensors();
  }

  private initializeSafetyProtocols(): void {
    const protocols: SafetyProtocol[] = [
      {
        id: 'fire_prevention_001',
        name: 'High Temperature Alert',
        description: 'Monitor for excessive temperatures that could indicate fire risk',
        type: SafetyProtocolType.FIRE_PREVENTION,
        triggers: [
          {
            parameter: 'temperature',
            condition: 'gt',
            threshold: this.config.temperatureRange.max + 10,
            duration: 300,
            consecutiveReadings: 3
          }
        ],
        actions: [
          {
            action: 'emergency_shutdown',
            priority: 1,
            delay: 0,
            parameters: { reason: 'high_temperature' },
            requiresConfirmation: false
          },
          {
            action: 'send_alert',
            priority: 2,
            delay: 0,
            parameters: { type: 'fire_risk', severity: 'critical' },
            requiresConfirmation: false
          }
        ],
        priority: SafetyPriority.CRITICAL,
        isActive: true,
        triggerCount: 0
      },
      {
        id: 'electrical_safety_001',
        name: 'Power Consumption Limit',
        description: 'Prevent electrical overload by monitoring power consumption',
        type: SafetyProtocolType.ELECTRICAL_SAFETY,
        triggers: [
          {
            parameter: 'powerConsumption',
            condition: 'gt',
            threshold: this.config.powerConsumptionLimit * 0.9,
            duration: 60,
            consecutiveReadings: 2
          }
        ],
        actions: [
          {
            action: 'reduce_load',
            priority: 1,
            delay: 30,
            parameters: { reduction_percentage: 25 },
            requiresConfirmation: false
          },
          {
            action: 'send_alert',
            priority: 2,
            delay: 0,
            parameters: { type: 'power_limit', severity: 'high' },
            requiresConfirmation: false
          }
        ],
        priority: SafetyPriority.HIGH,
        isActive: true,
        triggerCount: 0
      },
      {
        id: 'air_quality_001',
        name: 'Air Quality Monitor',
        description: 'Monitor air quality and activate ventilation when needed',
        type: SafetyProtocolType.AIR_QUALITY,
        triggers: [
          {
            parameter: 'vocLevel',
            condition: 'gt',
            threshold: 1000,
            duration: 900,
            consecutiveReadings: 3
          }
        ],
        actions: [
          {
            action: 'activate_ventilation',
            priority: 1,
            delay: 0,
            parameters: { duration: 1800 },
            requiresConfirmation: false
          },
          {
            action: 'pause_printing',
            priority: 2,
            delay: 300,
            parameters: { reason: 'air_quality' },
            requiresConfirmation: true
          }
        ],
        priority: SafetyPriority.MEDIUM,
        isActive: this.config.ventilationRequired,
        triggerCount: 0
      },
      {
        id: 'noise_control_001',
        name: 'Quiet Hours Enforcement',
        description: 'Enforce noise limits during quiet hours',
        type: SafetyProtocolType.NOISE_CONTROL,
        triggers: [
          {
            parameter: 'noiseLevel',
            condition: 'gt',
            threshold: this.config.noiseThreshold,
            duration: 300,
            consecutiveReadings: 2
          }
        ],
        actions: [
          {
            action: 'reduce_print_speed',
            priority: 1,
            delay: 0,
            parameters: { speed_reduction: 0.5 },
            requiresConfirmation: false
          },
          {
            action: 'pause_printing',
            priority: 2,
            delay: 600,
            parameters: { reason: 'noise_control' },
            requiresConfirmation: false
          }
        ],
        priority: SafetyPriority.MEDIUM,
        isActive: true,
        triggerCount: 0
      }
    ];

    protocols.forEach(protocol => {
      this.safetyProtocols.set(protocol.id, protocol);
    });
  }

  private initializeEnvironmentalSensors(): void {
    // Simulate environmental sensors
    this.environmentalSensors.set('temperature', { location: 'main_area', calibrated: true });
    this.environmentalSensors.set('humidity', { location: 'main_area', calibrated: true });
    this.environmentalSensors.set('airQuality', { location: 'main_area', calibrated: true });
    this.environmentalSensors.set('noise', { location: 'main_area', calibrated: true });
    this.environmentalSensors.set('power', { location: 'electrical_panel', calibrated: true });
  }

  public startGarageOperation(): boolean {
    if (this.isOperational) {
      this.emit('warning', 'Garage operation already running');
      return false;
    }

    // Pre-operation checks
    if (!this.performPreOperationChecks()) {
      this.emit('error', 'Pre-operation checks failed');
      return false;
    }

    this.isOperational = true;
    this.startEnvironmentalMonitoring();
    
    this.emit('operationStarted', {
      timestamp: new Date(),
      mode: 'garage',
      config: this.config
    });

    return true;
  }

  private performPreOperationChecks(): boolean {
    const checks = [
      this.checkElectricalSafety(),
      this.checkEnvironmentalConditions(),
      this.checkSpaceConstraints(),
      this.checkSafetyProtocols()
    ];

    return checks.every(check => check);
  }

  private checkElectricalSafety(): boolean {
    const currentConsumption = this.getCurrentPowerConsumption();
    
    if (currentConsumption > this.config.powerConsumptionLimit * 0.8) {
      this.emit('safetyViolation', {
        type: 'electrical',
        message: 'Power consumption too high for safe operation',
        current: currentConsumption,
        limit: this.config.powerConsumptionLimit
      });
      return false;
    }

    return true;
  }

  private checkEnvironmentalConditions(): boolean {
    const currentReading = this.getEnvironmentalReading();
    
    const tempOk = currentReading.temperature >= this.config.temperatureRange.min &&
                   currentReading.temperature <= this.config.temperatureRange.max;
    
    const humidityOk = currentReading.humidity >= this.config.humidityRange.min &&
                       currentReading.humidity <= this.config.humidityRange.max;

    if (!tempOk || !humidityOk) {
      this.emit('environmentalAlert', {
        temperature: currentReading.temperature,
        humidity: currentReading.humidity,
        acceptable: { tempOk, humidityOk }
      });
      return false;
    }

    return true;
  }

  private checkSpaceConstraints(): boolean {
    const usableSpace = this.constraints.spaceConstraints.usableSpace;
    const requiredSpace = this.calculateRequiredSpace();
    
    if (requiredSpace > usableSpace) {
      this.emit('spaceConstraintViolation', {
        required: requiredSpace,
        available: usableSpace,
        message: 'Insufficient space for safe operation'
      });
      return false;
    }

    return true;
  }

  private calculateRequiredSpace(): number {
    const printerSpace = this.activePrinters.size * 0.5; // 0.5 m² per printer
    const workspaceSpace = this.operationLimits.workspaceReservation;
    const bufferSpace = this.operationLimits.bufferSpaceRequired;
    
    return printerSpace + workspaceSpace + bufferSpace;
  }

  private checkSafetyProtocols(): boolean {
    let allProtocolsOk = true;
    
    for (const [protocolId, protocol] of this.safetyProtocols) {
      if (!protocol.isActive) continue;
      
      if (!this.validateSafetyProtocol(protocol)) {
        this.emit('safetyProtocolFailure', {
          protocolId,
          protocolName: protocol.name,
          type: protocol.type
        });
        allProtocolsOk = false;
      }
    }

    return allProtocolsOk;
  }

  private validateSafetyProtocol(protocol: SafetyProtocol): boolean {
    // Validate that safety protocol can be executed
    for (const action of protocol.actions) {
      if (!this.canExecuteSafetyAction(action)) {
        return false;
      }
    }
    return true;
  }

  private canExecuteSafetyAction(action: SafetyAction): boolean {
    switch (action.action) {
      case 'emergency_shutdown':
        return this.activePrinters.size > 0;
      case 'activate_ventilation':
        return this.config.ventilationRequired;
      case 'reduce_load':
        return this.activePrinters.size > 1;
      default:
        return true;
    }
  }

  private startEnvironmentalMonitoring(): void {
    this.monitoringInterval = setInterval(() => {
      const reading = this.getEnvironmentalReading();
      this.environmentalReadings.push(reading);
      
      // Keep only last 1000 readings
      if (this.environmentalReadings.length > 1000) {
        this.environmentalReadings.shift();
      }
      
      this.checkSafetyTriggers(reading);
      this.checkQuietHours(reading);
      
      this.emit('environmentalUpdate', reading);
    }, 60000); // Every minute
  }

  private getEnvironmentalReading(): GarageEnvironmentReading {
    // Simulate sensor readings with realistic garage environment values
    const baseTemp = 20;
    const baseTempVariation = (Math.random() - 0.5) * 4;
    const heatFromPrinters = this.activePrinters.size * 2;
    
    return {
      timestamp: new Date(),
      temperature: baseTemp + baseTempVariation + heatFromPrinters,
      humidity: 40 + (Math.random() - 0.5) * 20,
      airQuality: 80 + (Math.random() - 0.5) * 30,
      noiseLevel: 35 + this.activePrinters.size * 5 + Math.random() * 10,
      co2Level: 400 + this.activePrinters.size * 50 + Math.random() * 200,
      vocLevel: 100 + this.activePrinters.size * 100 + Math.random() * 500,
      powerConsumption: this.getCurrentPowerConsumption(),
      vibrationLevel: this.activePrinters.size * 0.1 + Math.random() * 0.2
    };
  }

  private getCurrentPowerConsumption(): number {
    const basePower = 200; // Base garage power consumption in watts
    const printerPower = this.activePrinters.size * 300; // 300W per active printer
    const variablePower = Math.random() * 100;
    
    return basePower + printerPower + variablePower;
  }

  private checkSafetyTriggers(reading: GarageEnvironmentReading): void {
    for (const [protocolId, protocol] of this.safetyProtocols) {
      if (!protocol.isActive) continue;
      
      for (const trigger of protocol.triggers) {
        if (this.evaluateTrigger(trigger, reading)) {
          this.executeSafetyProtocol(protocol, reading);
          break;
        }
      }
    }
  }

  private evaluateTrigger(trigger: SafetyTrigger, reading: GarageEnvironmentReading): boolean {
    const value = this.getParameterValue(trigger.parameter, reading);
    
    switch (trigger.condition) {
      case 'gt':
        return value > trigger.threshold;
      case 'lt':
        return value < trigger.threshold;
      case 'gte':
        return value >= trigger.threshold;
      case 'lte':
        return value <= trigger.threshold;
      case 'eq':
        return Math.abs(value - trigger.threshold) < 0.01;
      default:
        return false;
    }
  }

  private getParameterValue(parameter: string, reading: GarageEnvironmentReading): number {
    switch (parameter) {
      case 'temperature':
        return reading.temperature;
      case 'humidity':
        return reading.humidity;
      case 'noiseLevel':
        return reading.noiseLevel;
      case 'powerConsumption':
        return reading.powerConsumption;
      case 'vocLevel':
        return reading.vocLevel;
      case 'co2Level':
        return reading.co2Level;
      default:
        return 0;
    }
  }

  private executeSafetyProtocol(protocol: SafetyProtocol, reading: GarageEnvironmentReading): void {
    protocol.lastTriggered = new Date();
    protocol.triggerCount++;
    
    this.emit('safetyProtocolTriggered', {
      protocol,
      reading,
      timestamp: new Date()
    });

    // Execute actions in priority order
    const sortedActions = protocol.actions.sort((a, b) => a.priority - b.priority);
    
    for (const action of sortedActions) {
      setTimeout(() => {
        this.executeSafetyAction(action, protocol, reading);
      }, action.delay * 1000);
    }
  }

  private executeSafetyAction(
    action: SafetyAction, 
    protocol: SafetyProtocol, 
    reading: GarageEnvironmentReading
  ): void {
    this.emit('safetyActionExecuted', {
      action: action.action,
      protocol: protocol.name,
      parameters: action.parameters,
      timestamp: new Date()
    });

    switch (action.action) {
      case 'emergency_shutdown':
        this.emergencyShutdown(action.parameters.reason);
        break;
      case 'reduce_load':
        this.reduceElectricalLoad(action.parameters.reduction_percentage);
        break;
      case 'activate_ventilation':
        this.activateVentilation(action.parameters.duration);
        break;
      case 'pause_printing':
        this.pauseAllPrinting(action.parameters.reason);
        break;
      case 'reduce_print_speed':
        this.reducePrintSpeed(action.parameters.speed_reduction);
        break;
      case 'send_alert':
        this.sendSafetyAlert(action.parameters.type, action.parameters.severity, protocol, reading);
        break;
    }
  }

  private emergencyShutdown(reason: string): void {
    this.emit('emergencyShutdown', {
      reason,
      timestamp: new Date(),
      activePrinters: Array.from(this.activePrinters)
    });

    // Shutdown all printers immediately
    this.activePrinters.clear();
    this.isOperational = false;
    
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
    }
  }

  private reduceElectricalLoad(reductionPercentage: number): void {
    const printersToShutdown = Math.ceil(this.activePrinters.size * (reductionPercentage / 100));
    const printerArray = Array.from(this.activePrinters);
    
    for (let i = 0; i < printersToShutdown && i < printerArray.length; i++) {
      this.activePrinters.delete(printerArray[i]);
      this.emit('printerShutdownForSafety', {
        printerId: printerArray[i],
        reason: 'electrical_load_reduction'
      });
    }
  }

  private activateVentilation(duration: number): void {
    this.emit('ventilationActivated', {
      duration,
      timestamp: new Date()
    });
    
    // Simulate ventilation system activation
    setTimeout(() => {
      this.emit('ventilationDeactivated', {
        timestamp: new Date()
      });
    }, duration * 1000);
  }

  private pauseAllPrinting(reason: string): void {
    this.emit('allPrintingPaused', {
      reason,
      timestamp: new Date(),
      affectedPrinters: Array.from(this.activePrinters)
    });
  }

  private reducePrintSpeed(speedReduction: number): void {
    this.emit('printSpeedReduced', {
      speedReduction,
      timestamp: new Date(),
      affectedPrinters: Array.from(this.activePrinters)
    });
  }

  private sendSafetyAlert(type: string, severity: string, protocol: SafetyProtocol, reading: GarageEnvironmentReading): void {
    this.emit('safetyAlert', {
      type,
      severity,
      protocol: protocol.name,
      reading,
      timestamp: new Date(),
      message: `Safety alert: ${protocol.description}`
    });
  }

  private checkQuietHours(reading: GarageEnvironmentReading): void {
    if (!this.schedule.quietHoursEnabled) return;
    
    const now = new Date();
    const currentTime = now.getHours() * 60 + now.getMinutes();
    
    const [quietStartHour, quietStartMin] = this.config.quietHours.start.split(':').map(Number);
    const [quietEndHour, quietEndMin] = this.config.quietHours.end.split(':').map(Number);
    
    const quietStart = quietStartHour * 60 + quietStartMin;
    const quietEnd = quietEndHour * 60 + quietEndMin;
    
    const isQuietTime = (quietStart <= quietEnd) 
      ? (currentTime >= quietStart && currentTime <= quietEnd)
      : (currentTime >= quietStart || currentTime <= quietEnd);
    
    if (isQuietTime && reading.noiseLevel > this.config.noiseThreshold * 0.7) {
      this.emit('quietHoursViolation', {
        currentNoiseLevel: reading.noiseLevel,
        threshold: this.config.noiseThreshold * 0.7,
        timestamp: new Date()
      });
    }
  }

  public addPrinterToOperation(printerId: string): boolean {
    if (this.activePrinters.size >= this.config.maxConcurrentJobs) {
      this.emit('warning', `Cannot add printer ${printerId}: max concurrent jobs reached`);
      return false;
    }

    if (this.getCurrentPowerConsumption() + 300 > this.config.powerConsumptionLimit) {
      this.emit('warning', `Cannot add printer ${printerId}: power limit exceeded`);
      return false;
    }

    this.activePrinters.add(printerId);
    this.emit('printerAddedToOperation', { printerId, totalActive: this.activePrinters.size });
    return true;
  }

  public removePrinterFromOperation(printerId: string): boolean {
    if (!this.activePrinters.has(printerId)) {
      return false;
    }

    this.activePrinters.delete(printerId);
    this.emit('printerRemovedFromOperation', { printerId, totalActive: this.activePrinters.size });
    return true;
  }

  public getOperationStatus(): {
    isOperational: boolean;
    activePrinters: number;
    maxPrinters: number;
    powerConsumption: number;
    powerLimit: number;
    environmentalStatus: 'good' | 'warning' | 'critical';
    lastReading?: GarageEnvironmentReading;
  } {
    const lastReading = this.environmentalReadings[this.environmentalReadings.length - 1];
    
    let environmentalStatus: 'good' | 'warning' | 'critical' = 'good';
    
    if (lastReading) {
      const tempOk = lastReading.temperature <= this.config.temperatureRange.max;
      const humidityOk = lastReading.humidity <= this.config.humidityRange.max;
      const noiseOk = lastReading.noiseLevel <= this.config.noiseThreshold;
      const powerOk = lastReading.powerConsumption <= this.config.powerConsumptionLimit * 0.9;
      
      if (!tempOk || !powerOk) {
        environmentalStatus = 'critical';
      } else if (!humidityOk || !noiseOk) {
        environmentalStatus = 'warning';
      }
    }

    return {
      isOperational: this.isOperational,
      activePrinters: this.activePrinters.size,
      maxPrinters: this.config.maxConcurrentJobs,
      powerConsumption: this.getCurrentPowerConsumption(),
      powerLimit: this.config.powerConsumptionLimit,
      environmentalStatus,
      lastReading
    };
  }

  public shutdown(): void {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
    }
    
    this.isOperational = false;
    this.activePrinters.clear();
    
    this.emit('operationShutdown', {
      timestamp: new Date(),
      reason: 'manual_shutdown'
    });
  }
}