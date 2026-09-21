class OptimizationRecommendations {
  constructor() {
    this.recommendations = new Map();
    this.rules = new Map();
    this.metrics = new Map();
    this.priorities = {
      LOW: { value: 1, label: 'Low' },
      MEDIUM: { value: 2, label: 'Medium' },
      HIGH: { value: 3, label: 'High' },
      CRITICAL: { value: 4, label: 'Critical' }
    };
    this.initializeRules();
  }

  initializeRules() {
    this.addRule('underutilized_cpu', {
      condition: (metrics) => metrics.cpu && metrics.cpu.average < 20,
      recommendation: 'rightsize_instance_down',
      priority: this.priorities.HIGH,
      savings: (metrics, cost) => cost * 0.3,
      description: 'CPU utilization is consistently low, consider downsizing instance'
    });

    this.addRule('underutilized_memory', {
      condition: (metrics) => metrics.memory && metrics.memory.average < 30,
      recommendation: 'reduce_memory_allocation',
      priority: this.priorities.MEDIUM,
      savings: (metrics, cost) => cost * 0.2,
      description: 'Memory utilization is low, consider reducing memory allocation'
    });

    this.addRule('overprovisioned_storage', {
      condition: (metrics) => metrics.disk && metrics.disk.average < 40,
      recommendation: 'optimize_storage',
      priority: this.priorities.MEDIUM,
      savings: (metrics, cost) => cost * 0.15,
      description: 'Storage utilization is low, consider storage optimization'
    });

    this.addRule('high_cpu_volatility', {
      condition: (metrics) => metrics.cpu && metrics.cpu.consistency === 'volatile',
      recommendation: 'enable_auto_scaling',
      priority: this.priorities.HIGH,
      savings: (metrics, cost) => cost * 0.25,
      description: 'CPU usage is volatile, auto-scaling could optimize costs'
    });

    this.addRule('spot_instance_candidate', {
      condition: (metrics) => metrics.cpu && metrics.cpu.consistency === 'stable',
      recommendation: 'migrate_to_spot',
      priority: this.priorities.HIGH,
      savings: (metrics, cost) => cost * 0.6,
      description: 'Workload is suitable for spot instances for significant savings'
    });

    this.addRule('reserved_instance_candidate', {
      condition: (metrics, context) => {
        return context && context.uptime > 0.8 && context.predictability > 0.7;
      },
      recommendation: 'purchase_reserved_instances',
      priority: this.priorities.MEDIUM,
      savings: (metrics, cost, context) => cost * (context.uptime * 0.4),
      description: 'Consistent usage pattern, reserved instances would reduce costs'
    });

    this.addRule('inefficient_storage_type', {
      condition: (metrics) => metrics.disk && metrics.disk.iops_utilization < 20,
      recommendation: 'downgrade_storage_type',
      priority: this.priorities.MEDIUM,
      savings: (metrics, cost) => cost * 0.4,
      description: 'IOPS utilization is low, consider standard storage tier'
    });

    this.addRule('idle_resources', {
      condition: (metrics) => {
        return metrics.cpu && metrics.memory && 
               metrics.cpu.average < 5 && metrics.memory.average < 10;
      },
      recommendation: 'shutdown_or_schedule',
      priority: this.priorities.HIGH,
      savings: (metrics, cost) => cost * 0.9,
      description: 'Resource appears idle, consider shutdown or scheduling'
    });
  }

  addRule(ruleId, rule) {
    this.rules.set(ruleId, {
      id: ruleId,
      ...rule,
      createdAt: new Date().toISOString()
    });
  }

  generateRecommendations(resourceId, metrics, cost, context = {}) {
    const recommendations = [];
    const timestamp = new Date().toISOString();

    for (const [ruleId, rule] of this.rules) {
      try {
        if (rule.condition(metrics, context)) {
          const potentialSavings = rule.savings(metrics, cost, context);
          const recommendation = {
            id: `${resourceId}_${ruleId}_${Date.now()}`,
            resourceId,
            ruleId,
            type: rule.recommendation,
            priority: rule.priority,
            description: rule.description,
            currentCost: cost,
            potentialSavings,
            newEstimatedCost: Math.max(0, cost - potentialSavings),
            savingsPercentage: (potentialSavings / cost) * 100,
            timestamp,
            metrics: { ...metrics },
            context: { ...context },
            status: 'active',
            confidence: this.calculateConfidence(metrics, rule),
            implementation: this.generateImplementationPlan(rule.recommendation, metrics, context)
          };

          recommendations.push(recommendation);
          this.recommendations.set(recommendation.id, recommendation);
        }
      } catch (error) {
        console.error(`Error evaluating rule ${ruleId}:`, error.message);
      }
    }

    return this.prioritizeRecommendations(recommendations);
  }

  calculateConfidence(metrics, rule) {
    let confidence = 0.5;

    if (metrics.cpu && metrics.cpu.standardDeviation < 10) confidence += 0.2;
    if (metrics.memory && metrics.memory.consistency === 'stable') confidence += 0.2;
    if (metrics.dataPoints && metrics.dataPoints > 100) confidence += 0.1;

    return Math.min(1.0, confidence);
  }

  generateImplementationPlan(recommendationType, metrics, context) {
    const plans = {
      rightsize_instance_down: {
        steps: [
          'Analyze current instance specifications',
          'Identify target instance size (reduce by 1-2 sizes)',
          'Schedule maintenance window',
          'Take snapshot/backup',
          'Resize instance',
          'Validate performance',
          'Monitor for 24-48 hours'
        ],
        estimatedTime: '2-4 hours',
        risk: 'medium',
        requirements: ['Maintenance window', 'Performance baseline']
      },
      reduce_memory_allocation: {
        steps: [
          'Review application memory requirements',
          'Test with reduced allocation in staging',
          'Gradually reduce memory allocation',
          'Monitor application performance',
          'Adjust based on performance metrics'
        ],
        estimatedTime: '1-2 hours',
        risk: 'low',
        requirements: ['Staging environment', 'Monitoring setup']
      },
      optimize_storage: {
        steps: [
          'Analyze storage usage patterns',
          'Identify unused or duplicate data',
          'Implement data lifecycle policies',
          'Consider storage tier changes',
          'Set up automated cleanup'
        ],
        estimatedTime: '4-8 hours',
        risk: 'low',
        requirements: ['Data backup', 'Usage analysis']
      },
      enable_auto_scaling: {
        steps: [
          'Define scaling metrics and thresholds',
          'Configure auto-scaling policies',
          'Set up monitoring and alerts',
          'Test scaling behavior',
          'Fine-tune scaling parameters'
        ],
        estimatedTime: '3-6 hours',
        risk: 'medium',
        requirements: ['Load testing', 'Monitoring dashboard']
      },
      migrate_to_spot: {
        steps: [
          'Assess workload interruption tolerance',
          'Implement graceful shutdown handling',
          'Set up spot instance requests',
          'Configure automatic failover',
          'Monitor spot price trends'
        ],
        estimatedTime: '6-12 hours',
        risk: 'high',
        requirements: ['Fault tolerance design', 'State management']
      },
      purchase_reserved_instances: {
        steps: [
          'Analyze usage patterns and commitment ability',
          'Compare pricing options (1yr vs 3yr)',
          'Select payment option (upfront vs monthly)',
          'Purchase reserved instances',
          'Monitor utilization and savings'
        ],
        estimatedTime: '1-2 hours',
        risk: 'low',
        requirements: ['Budget approval', 'Usage forecasting']
      },
      shutdown_or_schedule: {
        steps: [
          'Verify resource is truly idle',
          'Check for dependencies',
          'Implement scheduled start/stop',
          'Configure monitoring for unexpected usage',
          'Set up automated scheduling'
        ],
        estimatedTime: '2-3 hours',
        risk: 'high',
        requirements: ['Dependency analysis', 'Scheduling system']
      }
    };

    return plans[recommendationType] || {
      steps: ['Manual analysis required'],
      estimatedTime: 'varies',
      risk: 'unknown',
      requirements: ['Expert consultation']
    };
  }

  prioritizeRecommendations(recommendations) {
    return recommendations.sort((a, b) => {
      const priorityDiff = b.priority.value - a.priority.value;
      if (priorityDiff !== 0) return priorityDiff;
      
      const savingsDiff = b.potentialSavings - a.potentialSavings;
      if (savingsDiff !== 0) return savingsDiff;
      
      return b.confidence - a.confidence;
    });
  }

  getRecommendationsByResource(resourceId) {
    const resourceRecommendations = [];
    
    for (const [_, recommendation] of this.recommendations) {
      if (recommendation.resourceId === resourceId && recommendation.status === 'active') {
        resourceRecommendations.push(recommendation);
      }
    }
    
    return this.prioritizeRecommendations(resourceRecommendations);
  }

  getRecommendationsByPriority(priority) {
    const filteredRecommendations = [];
    
    for (const [_, recommendation] of this.recommendations) {
      if (recommendation.priority.value >= priority.value && recommendation.status === 'active') {
        filteredRecommendations.push(recommendation);
      }
    }
    
    return this.prioritizeRecommendations(filteredRecommendations);
  }

  implementRecommendation(recommendationId, options = {}) {
    const recommendation = this.recommendations.get(recommendationId);
    if (!recommendation) {
      throw new Error(`Recommendation ${recommendationId} not found`);
    }

    const implementation = {
      id: `impl_${recommendationId}`,
      recommendationId,
      startedAt: new Date().toISOString(),
      status: 'in_progress',
      options,
      steps: recommendation.implementation.steps.map(step => ({
        description: step,
        status: 'pending',
        startedAt: null,
        completedAt: null
      }))
    };

    recommendation.status = 'implementing';
    recommendation.implementation.active = implementation;

    return implementation;
  }

  updateImplementationStep(implementationId, stepIndex, status, notes = '') {
    for (const [_, recommendation] of this.recommendations) {
      if (recommendation.implementation.active && 
          recommendation.implementation.active.id === implementationId) {
        
        const step = recommendation.implementation.active.steps[stepIndex];
        if (step) {
          step.status = status;
          step.notes = notes;
          step.updatedAt = new Date().toISOString();
          
          if (status === 'in_progress' && !step.startedAt) {
            step.startedAt = new Date().toISOString();
          } else if (status === 'completed' && !step.completedAt) {
            step.completedAt = new Date().toISOString();
          }
        }
        break;
      }
    }
  }

  completeImplementation(implementationId, actualSavings, notes = '') {
    for (const [_, recommendation] of this.recommendations) {
      if (recommendation.implementation.active && 
          recommendation.implementation.active.id === implementationId) {
        
        recommendation.implementation.active.status = 'completed';
        recommendation.implementation.active.completedAt = new Date().toISOString();
        recommendation.implementation.active.actualSavings = actualSavings;
        recommendation.implementation.active.notes = notes;
        
        recommendation.status = 'implemented';
        recommendation.actualSavings = actualSavings;
        recommendation.implementedAt = new Date().toISOString();
        
        this.trackSavings(recommendation);
        break;
      }
    }
  }

  trackSavings(recommendation) {
    const savingsRecord = {
      recommendationId: recommendation.id,
      resourceId: recommendation.resourceId,
      type: recommendation.type,
      estimatedSavings: recommendation.potentialSavings,
      actualSavings: recommendation.actualSavings,
      variance: recommendation.actualSavings - recommendation.potentialSavings,
      timestamp: new Date().toISOString()
    };

    console.log(`Savings tracked: $${savingsRecord.actualSavings.toFixed(2)} for ${recommendation.resourceId}`);
  }

  generateOptimizationReport(options = {}) {
    const { includeImplemented = false, priorityFilter = null } = options;
    
    const activeRecommendations = [];
    const implementedRecommendations = [];
    let totalPotentialSavings = 0;
    let totalActualSavings = 0;

    for (const [_, recommendation] of this.recommendations) {
      if (priorityFilter && recommendation.priority.value < priorityFilter.value) {
        continue;
      }

      if (recommendation.status === 'active') {
        activeRecommendations.push(recommendation);
        totalPotentialSavings += recommendation.potentialSavings;
      } else if (recommendation.status === 'implemented' && includeImplemented) {
        implementedRecommendations.push(recommendation);
        totalActualSavings += recommendation.actualSavings || 0;
      }
    }

    const report = {
      generatedAt: new Date().toISOString(),
      summary: {
        activeRecommendations: activeRecommendations.length,
        implementedRecommendations: implementedRecommendations.length,
        totalPotentialSavings,
        totalActualSavings,
        averageSavingsPerRecommendation: activeRecommendations.length > 0 ? 
          totalPotentialSavings / activeRecommendations.length : 0
      },
      topRecommendations: this.prioritizeRecommendations(activeRecommendations).slice(0, 10),
      byCategory: this.groupRecommendationsByCategory(activeRecommendations),
      byPriority: this.groupRecommendationsByPriority(activeRecommendations)
    };

    if (includeImplemented) {
      report.implemented = implementedRecommendations;
      report.savingsAccuracy = this.calculateSavingsAccuracy(implementedRecommendations);
    }

    return report;
  }

  groupRecommendationsByCategory(recommendations) {
    const categories = {};
    
    recommendations.forEach(rec => {
      const category = this.categorizeRecommendation(rec.type);
      if (!categories[category]) {
        categories[category] = { count: 0, totalSavings: 0, recommendations: [] };
      }
      categories[category].count++;
      categories[category].totalSavings += rec.potentialSavings;
      categories[category].recommendations.push(rec);
    });

    return categories;
  }

  groupRecommendationsByPriority(recommendations) {
    const priorities = {};
    
    recommendations.forEach(rec => {
      const priority = rec.priority.label;
      if (!priorities[priority]) {
        priorities[priority] = { count: 0, totalSavings: 0, recommendations: [] };
      }
      priorities[priority].count++;
      priorities[priority].totalSavings += rec.potentialSavings;
      priorities[priority].recommendations.push(rec);
    });

    return priorities;
  }

  categorizeRecommendation(type) {
    const categories = {
      rightsize_instance_down: 'Rightsizing',
      reduce_memory_allocation: 'Rightsizing',
      optimize_storage: 'Storage',
      enable_auto_scaling: 'Automation',
      migrate_to_spot: 'Instance Type',
      purchase_reserved_instances: 'Commitment',
      downgrade_storage_type: 'Storage',
      shutdown_or_schedule: 'Lifecycle'
    };

    return categories[type] || 'Other';
  }

  calculateSavingsAccuracy(implementedRecommendations) {
    if (implementedRecommendations.length === 0) return null;

    let totalVariance = 0;
    let accurateCount = 0;
    
    implementedRecommendations.forEach(rec => {
      if (rec.actualSavings !== undefined && rec.potentialSavings > 0) {
        const accuracy = (rec.actualSavings / rec.potentialSavings) * 100;
        totalVariance += Math.abs(accuracy - 100);
        if (accuracy >= 80 && accuracy <= 120) accurateCount++;
      }
    });

    return {
      averageVariance: totalVariance / implementedRecommendations.length,
      accuracyRate: (accurateCount / implementedRecommendations.length) * 100,
      totalImplemented: implementedRecommendations.length
    };
  }

  dismissRecommendation(recommendationId, reason = '') {
    const recommendation = this.recommendations.get(recommendationId);
    if (recommendation) {
      recommendation.status = 'dismissed';
      recommendation.dismissedAt = new Date().toISOString();
      recommendation.dismissalReason = reason;
    }
  }

  reactivateRecommendation(recommendationId) {
    const recommendation = this.recommendations.get(recommendationId);
    if (recommendation && recommendation.status === 'dismissed') {
      recommendation.status = 'active';
      delete recommendation.dismissedAt;
      delete recommendation.dismissalReason;
    }
  }
}

module.exports = OptimizationRecommendations;