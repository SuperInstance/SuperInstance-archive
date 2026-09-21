const EventEmitter = require('events');

class ResourceAnalytics extends EventEmitter {
  constructor() {
    super();
    this.metrics = new Map();
    this.usage = new Map();
    this.thresholds = {
      cpu: { warning: 70, critical: 90 },
      memory: { warning: 80, critical: 95 },
      disk: { warning: 85, critical: 95 },
      network: { warning: 80, critical: 95 }
    };
    this.collectionInterval = null;
  }

  startCollection(intervalMs = 60000) {
    if (this.collectionInterval) {
      clearInterval(this.collectionInterval);
    }

    this.collectionInterval = setInterval(() => {
      this.collectMetrics();
    }, intervalMs);

    this.collectMetrics();
  }

  stopCollection() {
    if (this.collectionInterval) {
      clearInterval(this.collectionInterval);
      this.collectionInterval = null;
    }
  }

  async collectMetrics() {
    const timestamp = new Date();
    const resourceId = 'system';

    try {
      const systemMetrics = await this.getSystemMetrics();
      this.recordMetrics(resourceId, timestamp, systemMetrics);
      this.analyzeUsagePatterns(resourceId, systemMetrics);
      this.checkThresholds(resourceId, systemMetrics);
    } catch (error) {
      this.emit('error', { type: 'collection_error', error: error.message });
    }
  }

  async getSystemMetrics() {
    const os = require('os');
    const fs = require('fs').promises;

    const cpus = os.cpus();
    const totalMem = os.totalmem();
    const freeMem = os.freemem();
    const usedMem = totalMem - freeMem;

    let diskUsage = { total: 0, used: 0, free: 0 };
    try {
      const stats = await fs.stat('/');
      diskUsage = {
        total: stats.size || 1000000000,
        used: (stats.size || 1000000000) * 0.3,
        free: (stats.size || 1000000000) * 0.7
      };
    } catch (error) {
      diskUsage = { total: 1000000000, used: 300000000, free: 700000000 };
    }

    const networkInterfaces = os.networkInterfaces();
    let networkStats = { bytesReceived: 0, bytesSent: 0, packetsReceived: 0, packetsSent: 0 };

    return {
      cpu: {
        cores: cpus.length,
        loadAverage: os.loadavg()[0],
        utilization: Math.min(100, (os.loadavg()[0] / cpus.length) * 100)
      },
      memory: {
        total: totalMem,
        used: usedMem,
        free: freeMem,
        utilization: (usedMem / totalMem) * 100
      },
      disk: {
        total: diskUsage.total,
        used: diskUsage.used,
        free: diskUsage.free,
        utilization: (diskUsage.used / diskUsage.total) * 100
      },
      network: {
        ...networkStats,
        utilization: Math.random() * 30
      },
      timestamp: new Date().toISOString()
    };
  }

  recordMetrics(resourceId, timestamp, metrics) {
    if (!this.metrics.has(resourceId)) {
      this.metrics.set(resourceId, []);
    }

    const resourceMetrics = this.metrics.get(resourceId);
    resourceMetrics.push({ timestamp, ...metrics });

    if (resourceMetrics.length > 1440) {
      resourceMetrics.shift();
    }

    this.emit('metrics_collected', { resourceId, metrics, timestamp });
  }

  analyzeUsagePatterns(resourceId, currentMetrics) {
    const history = this.metrics.get(resourceId) || [];
    if (history.length < 10) return;

    const recent = history.slice(-60);
    const patterns = {
      cpu: this.calculatePatterns(recent.map(m => m.cpu.utilization)),
      memory: this.calculatePatterns(recent.map(m => m.memory.utilization)),
      disk: this.calculatePatterns(recent.map(m => m.disk.utilization)),
      network: this.calculatePatterns(recent.map(m => m.network.utilization))
    };

    const analysis = {
      resourceId,
      timestamp: new Date().toISOString(),
      patterns,
      recommendations: this.generateRecommendations(patterns),
      efficiency: this.calculateEfficiency(patterns),
      waste: this.calculateWaste(patterns)
    };

    this.usage.set(resourceId, analysis);
    this.emit('usage_analyzed', analysis);
  }

  calculatePatterns(values) {
    const avg = values.reduce((sum, val) => sum + val, 0) / values.length;
    const max = Math.max(...values);
    const min = Math.min(...values);
    const variance = values.reduce((sum, val) => sum + Math.pow(val - avg, 2), 0) / values.length;
    const stdDev = Math.sqrt(variance);

    const trend = this.calculateTrend(values);
    const peaks = this.detectPeaks(values);
    const seasonality = this.detectSeasonality(values);

    return {
      average: Math.round(avg * 100) / 100,
      maximum: max,
      minimum: min,
      standardDeviation: Math.round(stdDev * 100) / 100,
      trend,
      peaks: peaks.length,
      seasonality,
      consistency: stdDev < 10 ? 'stable' : stdDev < 25 ? 'moderate' : 'volatile'
    };
  }

  calculateTrend(values) {
    if (values.length < 2) return 0;
    
    const n = values.length;
    const x = Array.from({ length: n }, (_, i) => i);
    const sumX = x.reduce((a, b) => a + b, 0);
    const sumY = values.reduce((a, b) => a + b, 0);
    const sumXY = x.reduce((sum, xi, i) => sum + xi * values[i], 0);
    const sumXX = x.reduce((sum, xi) => sum + xi * xi, 0);
    
    const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
    return Math.round(slope * 1000) / 1000;
  }

  detectPeaks(values, threshold = 20) {
    const peaks = [];
    const avg = values.reduce((sum, val) => sum + val, 0) / values.length;
    
    for (let i = 1; i < values.length - 1; i++) {
      if (values[i] > values[i - 1] && 
          values[i] > values[i + 1] && 
          values[i] > avg + threshold) {
        peaks.push({ index: i, value: values[i] });
      }
    }
    
    return peaks;
  }

  detectSeasonality(values) {
    if (values.length < 24) return 'insufficient_data';
    
    const periods = [24, 12, 8, 6];
    let bestPeriod = null;
    let bestCorrelation = 0;
    
    for (const period of periods) {
      if (values.length >= period * 2) {
        const correlation = this.calculateAutocorrelation(values, period);
        if (correlation > bestCorrelation) {
          bestCorrelation = correlation;
          bestPeriod = period;
        }
      }
    }
    
    return bestCorrelation > 0.3 ? `periodic_${bestPeriod}` : 'random';
  }

  calculateAutocorrelation(values, lag) {
    if (lag >= values.length) return 0;
    
    const n = values.length - lag;
    const mean1 = values.slice(0, n).reduce((a, b) => a + b, 0) / n;
    const mean2 = values.slice(lag).reduce((a, b) => a + b, 0) / n;
    
    let numerator = 0;
    let denom1 = 0;
    let denom2 = 0;
    
    for (let i = 0; i < n; i++) {
      const diff1 = values[i] - mean1;
      const diff2 = values[i + lag] - mean2;
      numerator += diff1 * diff2;
      denom1 += diff1 * diff1;
      denom2 += diff2 * diff2;
    }
    
    return numerator / Math.sqrt(denom1 * denom2);
  }

  generateRecommendations(patterns) {
    const recommendations = [];

    if (patterns.cpu.average < 30 && patterns.cpu.consistency === 'stable') {
      recommendations.push({
        type: 'rightsizing',
        resource: 'cpu',
        action: 'downsize',
        potential_savings: '20-40%',
        confidence: 'high'
      });
    }

    if (patterns.memory.average < 40) {
      recommendations.push({
        type: 'rightsizing',
        resource: 'memory',
        action: 'reduce_allocation',
        potential_savings: '15-30%',
        confidence: 'medium'
      });
    }

    if (patterns.cpu.peaks > 5 && patterns.cpu.consistency === 'volatile') {
      recommendations.push({
        type: 'scaling',
        resource: 'cpu',
        action: 'enable_auto_scaling',
        potential_savings: '10-25%',
        confidence: 'high'
      });
    }

    if (patterns.disk.average > 90) {
      recommendations.push({
        type: 'capacity',
        resource: 'disk',
        action: 'increase_storage',
        priority: 'high',
        confidence: 'high'
      });
    }

    return recommendations;
  }

  calculateEfficiency(patterns) {
    const weights = { cpu: 0.3, memory: 0.3, disk: 0.2, network: 0.2 };
    let totalEfficiency = 0;

    for (const [resource, pattern] of Object.entries(patterns)) {
      let efficiency = 100;
      
      if (pattern.average < 20) efficiency -= 40;
      else if (pattern.average < 40) efficiency -= 20;
      else if (pattern.average > 90) efficiency -= 30;
      
      if (pattern.consistency === 'volatile') efficiency -= 15;
      if (pattern.peaks > 10) efficiency -= 10;
      
      totalEfficiency += efficiency * weights[resource];
    }

    return {
      overall: Math.round(totalEfficiency),
      breakdown: Object.keys(patterns).reduce((acc, resource) => {
        acc[resource] = Math.max(0, Math.min(100, 
          100 - (patterns[resource].average < 30 ? 30 : 0) - 
          (patterns[resource].consistency === 'volatile' ? 15 : 0)
        ));
        return acc;
      }, {})
    };
  }

  calculateWaste(patterns) {
    const waste = {};
    
    Object.entries(patterns).forEach(([resource, pattern]) => {
      let wastePercentage = 0;
      
      if (pattern.average < 20) wastePercentage = 60;
      else if (pattern.average < 40) wastePercentage = 30;
      else if (pattern.average < 60) wastePercentage = 10;
      
      waste[resource] = {
        percentage: wastePercentage,
        cost_impact: this.estimateWasteCost(resource, wastePercentage)
      };
    });
    
    return waste;
  }

  estimateWasteCost(resource, wastePercentage) {
    const baseCosts = {
      cpu: 50,
      memory: 30,
      disk: 10,
      network: 20
    };
    
    return Math.round((baseCosts[resource] || 0) * (wastePercentage / 100) * 100) / 100;
  }

  checkThresholds(resourceId, metrics) {
    const alerts = [];

    Object.entries(this.thresholds).forEach(([resource, thresholds]) => {
      const utilization = metrics[resource]?.utilization;
      if (utilization !== undefined) {
        if (utilization >= thresholds.critical) {
          alerts.push({
            level: 'critical',
            resource,
            value: utilization,
            threshold: thresholds.critical,
            message: `${resource} utilization is critically high: ${utilization.toFixed(1)}%`
          });
        } else if (utilization >= thresholds.warning) {
          alerts.push({
            level: 'warning',
            resource,
            value: utilization,
            threshold: thresholds.warning,
            message: `${resource} utilization is high: ${utilization.toFixed(1)}%`
          });
        }
      }
    });

    if (alerts.length > 0) {
      this.emit('threshold_alert', { resourceId, alerts, timestamp: new Date().toISOString() });
    }
  }

  getResourceMetrics(resourceId, limit = 100) {
    const metrics = this.metrics.get(resourceId) || [];
    return metrics.slice(-limit);
  }

  getUsageAnalysis(resourceId) {
    return this.usage.get(resourceId);
  }

  getAllResourcesAnalysis() {
    const analysis = {};
    for (const [resourceId, data] of this.usage.entries()) {
      analysis[resourceId] = data;
    }
    return analysis;
  }

  exportMetrics(format = 'json') {
    const data = {
      timestamp: new Date().toISOString(),
      metrics: Object.fromEntries(this.metrics),
      analysis: Object.fromEntries(this.usage)
    };

    if (format === 'json') {
      return JSON.stringify(data, null, 2);
    } else if (format === 'csv') {
      return this.convertToCSV(data);
    }
    
    return data;
  }

  convertToCSV(data) {
    const lines = ['timestamp,resource,cpu_util,memory_util,disk_util,network_util'];
    
    Object.entries(data.metrics).forEach(([resourceId, metrics]) => {
      metrics.forEach(metric => {
        lines.push([
          metric.timestamp,
          resourceId,
          metric.cpu.utilization,
          metric.memory.utilization,
          metric.disk.utilization,
          metric.network.utilization
        ].join(','));
      });
    });
    
    return lines.join('\n');
  }
}

module.exports = ResourceAnalytics;