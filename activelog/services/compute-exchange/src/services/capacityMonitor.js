import { getDb } from '../database/init.js';
import { ProviderManager } from './providerManager.js';
import { getRedisClient } from '../utils/redis.js';
import { logger } from '../utils/logger.js';
import cron from 'node-cron';

export class CapacityMonitor {
  constructor() {
    this.providerManager = new ProviderManager();
    this.monitoringInterval = null;
    this.alertThresholds = {
      high_utilization: 0.85,
      critical_utilization: 0.95,
      low_spare_capacity: 0.15,
      critical_spare_capacity: 0.05
    };
  }

  async initialize() {
    try {
      await this.loadCapacityThresholds();
      this.startCapacityMonitoring();
      this.startSpareCapacityAnalyzer();
      this.startCapacityPrediction();
      logger.info('Capacity monitor initialized');
    } catch (error) {
      logger.error('Failed to initialize capacity monitor:', error);
      throw error;
    }
  }

  async loadCapacityThresholds() {
    // Load from environment or configuration
    this.alertThresholds = {
      high_utilization: parseFloat(process.env.HIGH_UTILIZATION_THRESHOLD) || 0.85,
      critical_utilization: parseFloat(process.env.CRITICAL_UTILIZATION_THRESHOLD) || 0.95,
      low_spare_capacity: parseFloat(process.env.LOW_SPARE_CAPACITY_THRESHOLD) || 0.15,
      critical_spare_capacity: parseFloat(process.env.CRITICAL_SPARE_CAPACITY_THRESHOLD) || 0.05
    };
    
    logger.info('Capacity thresholds loaded:', this.alertThresholds);
  }

  async collectCapacityData(providerId) {
    const db = getDb();
    
    try {
      // Get provider info
      const provider = await this.providerManager.getProvider(providerId);
      if (!provider || provider.status !== 'active') {
        return null;
      }

      // Get real-time capacity data based on provider type
      const capacityData = await this.getProviderCapacityData(provider);
      
      // Calculate utilization metrics
      const utilization = this.calculateUtilization(capacityData, provider);
      
      // Get current job statistics
      const jobStats = await this.getProviderJobStatistics(providerId);
      
      // Predict future capacity
      const prediction = await this.predictCapacity(providerId, capacityData);
      
      const monitoringData = {
        provider_id: providerId,
        timestamp: new Date().toISOString(),
        cpu_utilization: utilization.cpu,
        memory_utilization: utilization.memory,
        storage_utilization: utilization.storage,
        network_utilization: utilization.network || 0,
        active_jobs: jobStats.active_jobs,
        queued_jobs: jobStats.queued_jobs,
        avg_response_time_ms: jobStats.avg_response_time || 0,
        spare_capacity_percent: utilization.spare_capacity,
        predicted_capacity_1h: prediction.one_hour,
        predicted_capacity_24h: prediction.twenty_four_hour
      };

      // Store monitoring data
      await this.storeCapacityData(monitoringData);
      
      // Update provider capacity
      await this.providerManager.updateProviderCapacity(providerId, {
        available_cpu_cores: capacityData.available_cpu_cores,
        available_memory_gb: capacityData.available_memory_gb,
        available_storage_gb: capacityData.available_storage_gb,
        utilization_percent: Math.max(utilization.cpu, utilization.memory),
        ...utilization
      });

      // Check for capacity alerts
      await this.checkCapacityAlerts(providerId, monitoringData);

      return monitoringData;
    } catch (error) {
      logger.error(`Failed to collect capacity data for provider ${providerId}:`, error);
      return null;
    } finally {
      db.close();
    }
  }

  async getProviderCapacityData(provider) {
    try {
      switch (provider.type) {
        case 'slurm':
          return await this.getSlurmCapacity(provider);
        case 'kubernetes':
          return await this.getKubernetesCapacity(provider);
        case 'docker':
          return await this.getDockerCapacity(provider);
        case 'bare_metal':
          return await this.getBaremetalCapacity(provider);
        default:
          throw new Error(`Unsupported provider type: ${provider.type}`);
      }
    } catch (error) {
      logger.error(`Failed to get capacity for provider ${provider.id}:`, error);
      // Return fallback data
      return {
        available_cpu_cores: Math.max(0, provider.available_cpu_cores || 0),
        available_memory_gb: Math.max(0, provider.available_memory_gb || 0),
        available_storage_gb: Math.max(0, provider.available_storage_gb || 0),
        total_cpu_cores: provider.total_cpu_cores || 0,
        total_memory_gb: provider.total_memory_gb || 0,
        total_storage_gb: provider.total_storage_gb || 0
      };
    }
  }

  async getSlurmCapacity(provider) {
    const connection = await this.providerManager.connectSSH(provider);
    
    try {
      // Get node information
      const nodeInfo = await connection.execCommand('sinfo -N -h --format="%N %C %m %T"');
      if (nodeInfo.code !== 0) {
        throw new Error(`sinfo command failed: ${nodeInfo.stderr}`);
      }

      let totalCpu = 0, availableCpu = 0, totalMemory = 0, availableMemory = 0;
      
      const lines = nodeInfo.stdout.trim().split('\n');
      for (const line of lines) {
        const parts = line.trim().split(/\s+/);
        if (parts.length >= 4) {
          const cpuInfo = parts[1]; // Format: allocated/idle/other/total
          const memInfo = parts[2]; // Memory in MB
          const state = parts[3];
          
          if (state.toLowerCase().includes('idle') || state.toLowerCase().includes('mixed')) {
            const cpuParts = cpuInfo.split('/');
            if (cpuParts.length >= 4) {
              totalCpu += parseInt(cpuParts[3]);
              availableCpu += parseInt(cpuParts[1]); // idle cores
            }
            
            const memMB = parseInt(memInfo);
            if (!isNaN(memMB)) {
              totalMemory += memMB / 1024; // Convert to GB
              // Estimate available memory (simplified)
              availableMemory += (memMB / 1024) * 0.8; // Assume 80% available
            }
          }
        }
      }

      return {
        available_cpu_cores: Math.max(0, availableCpu),
        available_memory_gb: Math.max(0, Math.round(availableMemory)),
        available_storage_gb: provider.available_storage_gb || 0, // SLURM doesn't track storage directly
        total_cpu_cores: Math.max(totalCpu, provider.total_cpu_cores),
        total_memory_gb: Math.max(Math.round(totalMemory), provider.total_memory_gb),
        total_storage_gb: provider.total_storage_gb || 0
      };
    } finally {
      await connection.dispose();
    }
  }

  async getKubernetesCapacity(provider) {
    // This would integrate with Kubernetes API
    // Simplified implementation for now
    return {
      available_cpu_cores: provider.available_cpu_cores || 0,
      available_memory_gb: provider.available_memory_gb || 0,
      available_storage_gb: provider.available_storage_gb || 0,
      total_cpu_cores: provider.total_cpu_cores || 0,
      total_memory_gb: provider.total_memory_gb || 0,
      total_storage_gb: provider.total_storage_gb || 0
    };
  }

  async getDockerCapacity(provider) {
    // This would integrate with Docker API
    // Simplified implementation for now
    return {
      available_cpu_cores: provider.available_cpu_cores || 0,
      available_memory_gb: provider.available_memory_gb || 0,
      available_storage_gb: provider.available_storage_gb || 0,
      total_cpu_cores: provider.total_cpu_cores || 0,
      total_memory_gb: provider.total_memory_gb || 0,
      total_storage_gb: provider.total_storage_gb || 0
    };
  }

  async getBaremetalCapacity(provider) {
    const connection = await this.providerManager.connectSSH(provider);
    
    try {
      // Get CPU information
      const cpuInfo = await connection.execCommand('nproc');
      const totalCpu = parseInt(cpuInfo.stdout.trim()) || provider.total_cpu_cores;
      
      // Get memory information
      const memInfo = await connection.execCommand('free -g | grep "Mem:"');
      const memParts = memInfo.stdout.trim().split(/\s+/);
      const totalMemory = parseInt(memParts[1]) || provider.total_memory_gb;
      const availableMemory = parseInt(memParts[6]) || Math.round(totalMemory * 0.8);
      
      // Get load average to estimate CPU availability
      const loadInfo = await connection.execCommand('uptime');
      const loadMatch = loadInfo.stdout.match(/load average: ([\d.]+)/);
      const loadAvg = loadMatch ? parseFloat(loadMatch[1]) : 0;
      const availableCpu = Math.max(0, totalCpu - Math.ceil(loadAvg));

      return {
        available_cpu_cores: availableCpu,
        available_memory_gb: availableMemory,
        available_storage_gb: provider.available_storage_gb || 0,
        total_cpu_cores: totalCpu,
        total_memory_gb: totalMemory,
        total_storage_gb: provider.total_storage_gb || 0
      };
    } finally {
      await connection.dispose();
    }
  }

  calculateUtilization(capacityData, provider) {
    const cpuUtil = capacityData.total_cpu_cores > 0 
      ? ((capacityData.total_cpu_cores - capacityData.available_cpu_cores) / capacityData.total_cpu_cores) * 100
      : 0;
      
    const memUtil = capacityData.total_memory_gb > 0 
      ? ((capacityData.total_memory_gb - capacityData.available_memory_gb) / capacityData.total_memory_gb) * 100
      : 0;
      
    const storageUtil = capacityData.total_storage_gb > 0 
      ? ((capacityData.total_storage_gb - capacityData.available_storage_gb) / capacityData.total_storage_gb) * 100
      : 0;

    // Calculate overall spare capacity
    const spareCapacity = Math.min(
      (capacityData.available_cpu_cores / Math.max(capacityData.total_cpu_cores, 1)) * 100,
      (capacityData.available_memory_gb / Math.max(capacityData.total_memory_gb, 1)) * 100
    );

    return {
      cpu: Math.min(100, Math.max(0, cpuUtil)),
      memory: Math.min(100, Math.max(0, memUtil)),
      storage: Math.min(100, Math.max(0, storageUtil)),
      spare_capacity: Math.min(100, Math.max(0, spareCapacity))
    };
  }

  async getProviderJobStatistics(providerId) {
    const db = getDb();
    
    try {
      const stats = await new Promise((resolve, reject) => {
        db.get(`
          SELECT 
            COUNT(CASE WHEN status = 'running' THEN 1 END) as active_jobs,
            COUNT(CASE WHEN status = 'queued' THEN 1 END) as queued_jobs,
            AVG(CASE WHEN status = 'running' AND started_at IS NOT NULL 
                THEN (julianday('now') - julianday(started_at)) * 24 * 60 * 1000 
                ELSE NULL END) as avg_response_time
          FROM jobs 
          WHERE provider_id = ?
            AND created_at > datetime('now', '-1 hour')
        `, [providerId], (err, row) => {
          if (err) reject(err);
          else resolve(row || { active_jobs: 0, queued_jobs: 0, avg_response_time: 0 });
        });
      });

      return stats;
    } catch (error) {
      logger.error('Failed to get provider job statistics:', error);
      return { active_jobs: 0, queued_jobs: 0, avg_response_time: 0 };
    } finally {
      db.close();
    }
  }

  async predictCapacity(providerId, currentCapacity) {
    const db = getDb();
    
    try {
      // Get historical capacity data for trend analysis
      const history = await new Promise((resolve, reject) => {
        db.all(`
          SELECT cpu_utilization, memory_utilization, spare_capacity_percent, timestamp
          FROM capacity_monitoring 
          WHERE provider_id = ?
            AND timestamp > datetime('now', '-24 hours')
          ORDER BY timestamp DESC
          LIMIT 24
        `, [providerId], (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });

      if (history.length < 3) {
        // Not enough data for prediction, return current values
        return {
          one_hour: currentCapacity.spare_capacity_percent || 50,
          twenty_four_hour: currentCapacity.spare_capacity_percent || 50
        };
      }

      // Simple linear trend analysis
      const recentData = history.slice(0, 6); // Last 6 data points
      const avgUtilization = recentData.reduce((sum, point) => 
        sum + Math.max(point.cpu_utilization, point.memory_utilization), 0) / recentData.length;
      
      // Calculate trend (simplified)
      const firstUtil = Math.max(history[0].cpu_utilization, history[0].memory_utilization);
      const lastUtil = Math.max(history[history.length - 1].cpu_utilization, history[history.length - 1].memory_utilization);
      const trend = (firstUtil - lastUtil) / history.length; // Positive trend = decreasing utilization

      // Predict capacity (simplified linear extrapolation)
      const oneHourPrediction = Math.min(100, Math.max(0, 
        100 - (avgUtilization + (trend * 1)))); // 1 hour ahead
      const twentyFourHourPrediction = Math.min(100, Math.max(0, 
        100 - (avgUtilization + (trend * 24)))); // 24 hours ahead

      return {
        one_hour: Math.round(oneHourPrediction),
        twenty_four_hour: Math.round(twentyFourHourPrediction)
      };
    } catch (error) {
      logger.error('Failed to predict capacity:', error);
      return { one_hour: 50, twenty_four_hour: 50 };
    } finally {
      db.close();
    }
  }

  async storeCapacityData(monitoringData) {
    const db = getDb();
    
    try {
      await new Promise((resolve, reject) => {
        db.run(`
          INSERT INTO capacity_monitoring (
            provider_id, timestamp, cpu_utilization, memory_utilization,
            storage_utilization, network_utilization, active_jobs, queued_jobs,
            avg_response_time_ms, spare_capacity_percent, predicted_capacity_1h,
            predicted_capacity_24h
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `, [
          monitoringData.provider_id,
          monitoringData.timestamp,
          monitoringData.cpu_utilization,
          monitoringData.memory_utilization,
          monitoringData.storage_utilization,
          monitoringData.network_utilization,
          monitoringData.active_jobs,
          monitoringData.queued_jobs,
          monitoringData.avg_response_time_ms,
          monitoringData.spare_capacity_percent,
          monitoringData.predicted_capacity_1h,
          monitoringData.predicted_capacity_24h
        ], (err) => {
          if (err) reject(err);
          else resolve();
        });
      });

      // Also cache in Redis for fast access
      const redis = getRedisClient();
      await redis.setex(
        `capacity:${monitoringData.provider_id}`, 
        300, // 5 minute expiration
        JSON.stringify(monitoringData)
      );
    } catch (error) {
      logger.error('Failed to store capacity data:', error);
    } finally {
      db.close();
    }
  }

  async checkCapacityAlerts(providerId, monitoringData) {
    const alerts = [];
    
    // High utilization alerts
    if (monitoringData.cpu_utilization >= this.alertThresholds.critical_utilization * 100) {
      alerts.push({
        type: 'critical',
        metric: 'cpu_utilization',
        value: monitoringData.cpu_utilization,
        threshold: this.alertThresholds.critical_utilization * 100,
        message: `Critical CPU utilization: ${monitoringData.cpu_utilization.toFixed(1)}%`
      });
    } else if (monitoringData.cpu_utilization >= this.alertThresholds.high_utilization * 100) {
      alerts.push({
        type: 'warning',
        metric: 'cpu_utilization',
        value: monitoringData.cpu_utilization,
        threshold: this.alertThresholds.high_utilization * 100,
        message: `High CPU utilization: ${monitoringData.cpu_utilization.toFixed(1)}%`
      });
    }

    // Memory utilization alerts
    if (monitoringData.memory_utilization >= this.alertThresholds.critical_utilization * 100) {
      alerts.push({
        type: 'critical',
        metric: 'memory_utilization',
        value: monitoringData.memory_utilization,
        threshold: this.alertThresholds.critical_utilization * 100,
        message: `Critical memory utilization: ${monitoringData.memory_utilization.toFixed(1)}%`
      });
    } else if (monitoringData.memory_utilization >= this.alertThresholds.high_utilization * 100) {
      alerts.push({
        type: 'warning',
        metric: 'memory_utilization',
        value: monitoringData.memory_utilization,
        threshold: this.alertThresholds.high_utilization * 100,
        message: `High memory utilization: ${monitoringData.memory_utilization.toFixed(1)}%`
      });
    }

    // Low spare capacity alerts
    if (monitoringData.spare_capacity_percent <= this.alertThresholds.critical_spare_capacity * 100) {
      alerts.push({
        type: 'critical',
        metric: 'spare_capacity',
        value: monitoringData.spare_capacity_percent,
        threshold: this.alertThresholds.critical_spare_capacity * 100,
        message: `Critical spare capacity: ${monitoringData.spare_capacity_percent.toFixed(1)}%`
      });
    } else if (monitoringData.spare_capacity_percent <= this.alertThresholds.low_spare_capacity * 100) {
      alerts.push({
        type: 'warning',
        metric: 'spare_capacity',
        value: monitoringData.spare_capacity_percent,
        threshold: this.alertThresholds.low_spare_capacity * 100,
        message: `Low spare capacity: ${monitoringData.spare_capacity_percent.toFixed(1)}%`
      });
    }

    // Log alerts
    if (alerts.length > 0) {
      for (const alert of alerts) {
        if (alert.type === 'critical') {
          logger.error(`Provider ${providerId} - ${alert.message}`);
        } else {
          logger.warn(`Provider ${providerId} - ${alert.message}`);
        }
      }
    }

    return alerts;
  }

  async getSpareCapacitySummary() {
    const db = getDb();
    
    try {
      const summary = await new Promise((resolve, reject) => {
        db.all(`
          SELECT 
            p.id, p.name, p.type, p.university_id,
            cm.spare_capacity_percent, cm.cpu_utilization, cm.memory_utilization,
            cm.active_jobs, cm.queued_jobs, cm.timestamp,
            cm.predicted_capacity_1h, cm.predicted_capacity_24h
          FROM providers p
          LEFT JOIN capacity_monitoring cm ON p.id = cm.provider_id
          WHERE p.status = 'active'
            AND cm.timestamp = (
              SELECT MAX(timestamp) 
              FROM capacity_monitoring cm2 
              WHERE cm2.provider_id = p.id
            )
          ORDER BY cm.spare_capacity_percent DESC
        `, (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });

      return summary.map(provider => ({
        ...provider,
        last_updated: provider.timestamp,
        capacity_status: this.getCapacityStatus(provider)
      }));
    } catch (error) {
      logger.error('Failed to get spare capacity summary:', error);
      return [];
    } finally {
      db.close();
    }
  }

  getCapacityStatus(provider) {
    const spareCapacity = provider.spare_capacity_percent || 0;
    
    if (spareCapacity <= this.alertThresholds.critical_spare_capacity * 100) {
      return { status: 'critical', color: 'red' };
    } else if (spareCapacity <= this.alertThresholds.low_spare_capacity * 100) {
      return { status: 'warning', color: 'yellow' };
    } else if (spareCapacity >= 75) {
      return { status: 'abundant', color: 'green' };
    } else {
      return { status: 'normal', color: 'blue' };
    }
  }

  startCapacityMonitoring() {
    const interval = parseInt(process.env.CAPACITY_CHECK_INTERVAL) * 1000 || 60000; // Default 1 minute
    
    this.monitoringInterval = setInterval(async () => {
      try {
        const providers = await this.providerManager.getActiveProviders();
        
        const monitoringPromises = providers.map(provider => 
          this.collectCapacityData(provider.id)
        );
        
        await Promise.allSettled(monitoringPromises);
        
        logger.debug(`Capacity monitoring completed for ${providers.length} providers`);
      } catch (error) {
        logger.error('Capacity monitoring error:', error);
      }
    }, interval);
    
    logger.info('Capacity monitoring started');
  }

  startSpareCapacityAnalyzer() {
    // Run spare capacity analysis every 5 minutes
    cron.schedule('*/5 * * * *', async () => {
      try {
        const summary = await this.getSpareCapacitySummary();
        const totalProviders = summary.length;
        const criticalProviders = summary.filter(p => 
          p.capacity_status?.status === 'critical').length;
        
        if (criticalProviders > 0) {
          logger.warn(`Spare capacity alert: ${criticalProviders}/${totalProviders} providers have critical capacity`);
        }
      } catch (error) {
        logger.error('Spare capacity analysis error:', error);
      }
    });
    
    logger.info('Spare capacity analyzer started');
  }

  startCapacityPrediction() {
    // Update capacity predictions every hour
    cron.schedule('0 * * * *', async () => {
      try {
        const providers = await this.providerManager.getActiveProviders();
        
        for (const provider of providers) {
          const capacityData = await this.getProviderCapacityData(provider);
          const prediction = await this.predictCapacity(provider.id, capacityData);
          
          // Log significant capacity changes
          if (prediction.twenty_four_hour < 20) {
            logger.warn(`Provider ${provider.id} predicted to have low capacity in 24h: ${prediction.twenty_four_hour}%`);
          }
        }
      } catch (error) {
        logger.error('Capacity prediction error:', error);
      }
    });
    
    logger.info('Capacity prediction started');
  }

  stop() {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = null;
    }
    logger.info('Capacity monitor stopped');
  }
}