class CostAllocation {
  constructor() {
    this.allocations = new Map();
    this.users = new Map();
    this.projects = new Map();
    this.tags = new Map();
    this.allocationType = {
      PROPORTIONAL: 'proportional',
      FIXED: 'fixed',
      USAGE_BASED: 'usage_based',
      TIME_BASED: 'time_based'
    };
  }

  registerUser(userId, metadata = {}) {
    this.users.set(userId, {
      id: userId,
      name: metadata.name || userId,
      department: metadata.department,
      costCenter: metadata.costCenter,
      email: metadata.email,
      createdAt: new Date().toISOString(),
      ...metadata
    });
  }

  registerProject(projectId, metadata = {}) {
    this.projects.set(projectId, {
      id: projectId,
      name: metadata.name || projectId,
      owner: metadata.owner,
      department: metadata.department,
      budget: metadata.budget || 0,
      priority: metadata.priority || 'medium',
      createdAt: new Date().toISOString(),
      tags: metadata.tags || [],
      ...metadata
    });
  }

  allocateCost(costData) {
    const {
      resourceId,
      totalCost,
      allocationType,
      allocations,
      tags = {},
      timestamp = new Date().toISOString()
    } = costData;

    const allocationId = `${resourceId}_${Date.now()}`;
    const allocation = {
      id: allocationId,
      resourceId,
      totalCost,
      allocationType,
      timestamp,
      tags,
      distributions: []
    };

    switch (allocationType) {
      case this.allocationType.PROPORTIONAL:
        allocation.distributions = this.allocateProportional(totalCost, allocations);
        break;
      case this.allocationType.FIXED:
        allocation.distributions = this.allocateFixed(totalCost, allocations);
        break;
      case this.allocationType.USAGE_BASED:
        allocation.distributions = this.allocateUsageBased(totalCost, allocations);
        break;
      case this.allocationType.TIME_BASED:
        allocation.distributions = this.allocateTimeBased(totalCost, allocations);
        break;
      default:
        throw new Error(`Unknown allocation type: ${allocationType}`);
    }

    this.allocations.set(allocationId, allocation);
    this.updateUserProjectCosts(allocation);
    
    return allocation;
  }

  allocateProportional(totalCost, allocations) {
    const totalWeight = allocations.reduce((sum, alloc) => sum + alloc.weight, 0);
    
    return allocations.map(alloc => ({
      userId: alloc.userId,
      projectId: alloc.projectId,
      weight: alloc.weight,
      percentage: (alloc.weight / totalWeight) * 100,
      allocatedCost: (totalCost * alloc.weight) / totalWeight,
      metadata: alloc.metadata || {}
    }));
  }

  allocateFixed(totalCost, allocations) {
    const totalFixed = allocations.reduce((sum, alloc) => sum + alloc.amount, 0);
    const remaining = totalCost - totalFixed;
    
    return allocations.map(alloc => ({
      userId: alloc.userId,
      projectId: alloc.projectId,
      fixedAmount: alloc.amount,
      allocatedCost: alloc.amount + (remaining > 0 ? (remaining / allocations.length) : 0),
      metadata: alloc.metadata || {}
    }));
  }

  allocateUsageBased(totalCost, allocations) {
    const totalUsage = allocations.reduce((sum, alloc) => sum + alloc.usage, 0);
    
    return allocations.map(alloc => ({
      userId: alloc.userId,
      projectId: alloc.projectId,
      usage: alloc.usage,
      usagePercentage: (alloc.usage / totalUsage) * 100,
      allocatedCost: (totalCost * alloc.usage) / totalUsage,
      metadata: alloc.metadata || {}
    }));
  }

  allocateTimeBased(totalCost, allocations) {
    const totalTime = allocations.reduce((sum, alloc) => sum + alloc.timeHours, 0);
    
    return allocations.map(alloc => ({
      userId: alloc.userId,
      projectId: alloc.projectId,
      timeHours: alloc.timeHours,
      timePercentage: (alloc.timeHours / totalTime) * 100,
      allocatedCost: (totalCost * alloc.timeHours) / totalTime,
      metadata: alloc.metadata || {}
    }));
  }

  updateUserProjectCosts(allocation) {
    allocation.distributions.forEach(dist => {
      if (dist.userId) {
        const user = this.users.get(dist.userId);
        if (user) {
          if (!user.totalCost) user.totalCost = 0;
          user.totalCost += dist.allocatedCost;
          user.lastUpdated = new Date().toISOString();
        }
      }

      if (dist.projectId) {
        const project = this.projects.get(dist.projectId);
        if (project) {
          if (!project.totalCost) project.totalCost = 0;
          project.totalCost += dist.allocatedCost;
          project.lastUpdated = new Date().toISOString();
          
          if (project.budget && project.totalCost > project.budget) {
            this.emitBudgetAlert(project, project.totalCost - project.budget);
          }
        }
      }
    });
  }

  getUserCosts(userId, options = {}) {
    const user = this.users.get(userId);
    if (!user) return null;

    const { startDate, endDate, includeDetails = false } = options;
    const userAllocations = [];

    for (const [_, allocation] of this.allocations) {
      if (startDate && new Date(allocation.timestamp) < new Date(startDate)) continue;
      if (endDate && new Date(allocation.timestamp) > new Date(endDate)) continue;

      const userDist = allocation.distributions.find(d => d.userId === userId);
      if (userDist) {
        userAllocations.push({
          allocationId: allocation.id,
          resourceId: allocation.resourceId,
          timestamp: allocation.timestamp,
          allocatedCost: userDist.allocatedCost,
          tags: allocation.tags,
          ...(includeDetails && { allocation })
        });
      }
    }

    return {
      user,
      totalCost: userAllocations.reduce((sum, alloc) => sum + alloc.allocatedCost, 0),
      allocations: userAllocations,
      summary: this.generateUserCostSummary(userAllocations)
    };
  }

  getProjectCosts(projectId, options = {}) {
    const project = this.projects.get(projectId);
    if (!project) return null;

    const { startDate, endDate, includeDetails = false } = options;
    const projectAllocations = [];

    for (const [_, allocation] of this.allocations) {
      if (startDate && new Date(allocation.timestamp) < new Date(startDate)) continue;
      if (endDate && new Date(allocation.timestamp) > new Date(endDate)) continue;

      const projectDists = allocation.distributions.filter(d => d.projectId === projectId);
      if (projectDists.length > 0) {
        projectAllocations.push({
          allocationId: allocation.id,
          resourceId: allocation.resourceId,
          timestamp: allocation.timestamp,
          allocatedCost: projectDists.reduce((sum, d) => sum + d.allocatedCost, 0),
          distributions: projectDists,
          tags: allocation.tags,
          ...(includeDetails && { allocation })
        });
      }
    }

    const totalCost = projectAllocations.reduce((sum, alloc) => sum + alloc.allocatedCost, 0);
    
    return {
      project,
      totalCost,
      budgetUtilization: project.budget ? (totalCost / project.budget) * 100 : null,
      budgetRemaining: project.budget ? Math.max(0, project.budget - totalCost) : null,
      allocations: projectAllocations,
      summary: this.generateProjectCostSummary(projectAllocations)
    };
  }

  generateUserCostSummary(allocations) {
    const summary = {
      totalAllocations: allocations.length,
      averageCost: allocations.length > 0 ? 
        allocations.reduce((sum, a) => sum + a.allocatedCost, 0) / allocations.length : 0,
      byResource: {},
      byTimeperiod: {}
    };

    allocations.forEach(alloc => {
      if (!summary.byResource[alloc.resourceId]) {
        summary.byResource[alloc.resourceId] = { count: 0, totalCost: 0 };
      }
      summary.byResource[alloc.resourceId].count++;
      summary.byResource[alloc.resourceId].totalCost += alloc.allocatedCost;

      const period = new Date(alloc.timestamp).toISOString().split('T')[0];
      if (!summary.byTimeperiod[period]) {
        summary.byTimeperiod[period] = { count: 0, totalCost: 0 };
      }
      summary.byTimeperiod[period].count++;
      summary.byTimeperiod[period].totalCost += alloc.allocatedCost;
    });

    return summary;
  }

  generateProjectCostSummary(allocations) {
    const summary = {
      totalAllocations: allocations.length,
      averageCost: allocations.length > 0 ? 
        allocations.reduce((sum, a) => sum + a.allocatedCost, 0) / allocations.length : 0,
      byResource: {},
      byUser: {},
      trend: this.calculateCostTrend(allocations)
    };

    allocations.forEach(alloc => {
      if (!summary.byResource[alloc.resourceId]) {
        summary.byResource[alloc.resourceId] = { count: 0, totalCost: 0 };
      }
      summary.byResource[alloc.resourceId].count++;
      summary.byResource[alloc.resourceId].totalCost += alloc.allocatedCost;

      alloc.distributions.forEach(dist => {
        if (dist.userId) {
          if (!summary.byUser[dist.userId]) {
            summary.byUser[dist.userId] = { count: 0, totalCost: 0 };
          }
          summary.byUser[dist.userId].count++;
          summary.byUser[dist.userId].totalCost += dist.allocatedCost;
        }
      });
    });

    return summary;
  }

  calculateCostTrend(allocations) {
    if (allocations.length < 2) return 'insufficient_data';

    const sortedByDate = allocations.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    const recentHalf = sortedByDate.slice(Math.floor(sortedByDate.length / 2));
    const earlierHalf = sortedByDate.slice(0, Math.floor(sortedByDate.length / 2));

    const recentAvg = recentHalf.reduce((sum, a) => sum + a.allocatedCost, 0) / recentHalf.length;
    const earlierAvg = earlierHalf.reduce((sum, a) => sum + a.allocatedCost, 0) / earlierHalf.length;

    const change = ((recentAvg - earlierAvg) / earlierAvg) * 100;

    if (change > 10) return 'increasing';
    if (change < -10) return 'decreasing';
    return 'stable';
  }

  getDepartmentCosts(department, options = {}) {
    const departmentUsers = Array.from(this.users.values())
      .filter(user => user.department === department);
    
    const departmentProjects = Array.from(this.projects.values())
      .filter(project => project.department === department);

    let totalCost = 0;
    const details = { users: {}, projects: {} };

    departmentUsers.forEach(user => {
      const userCosts = this.getUserCosts(user.id, options);
      if (userCosts) {
        totalCost += userCosts.totalCost;
        details.users[user.id] = userCosts;
      }
    });

    departmentProjects.forEach(project => {
      const projectCosts = this.getProjectCosts(project.id, options);
      if (projectCosts) {
        details.projects[project.id] = projectCosts;
      }
    });

    return {
      department,
      totalCost,
      userCount: departmentUsers.length,
      projectCount: departmentProjects.length,
      details
    };
  }

  generateCostReport(options = {}) {
    const { 
      groupBy = 'project', 
      startDate, 
      endDate, 
      includeDetails = false,
      format = 'summary'
    } = options;

    const report = {
      generatedAt: new Date().toISOString(),
      period: { startDate, endDate },
      groupBy,
      totalAllocations: this.allocations.size,
      data: {}
    };

    let totalCost = 0;

    if (groupBy === 'project') {
      for (const [projectId, project] of this.projects) {
        const projectCosts = this.getProjectCosts(projectId, { startDate, endDate, includeDetails });
        if (projectCosts && projectCosts.totalCost > 0) {
          report.data[projectId] = format === 'detailed' ? projectCosts : {
            name: project.name,
            totalCost: projectCosts.totalCost,
            budgetUtilization: projectCosts.budgetUtilization
          };
          totalCost += projectCosts.totalCost;
        }
      }
    } else if (groupBy === 'user') {
      for (const [userId, user] of this.users) {
        const userCosts = this.getUserCosts(userId, { startDate, endDate, includeDetails });
        if (userCosts && userCosts.totalCost > 0) {
          report.data[userId] = format === 'detailed' ? userCosts : {
            name: user.name,
            totalCost: userCosts.totalCost,
            department: user.department
          };
          totalCost += userCosts.totalCost;
        }
      }
    }

    report.totalCost = totalCost;
    report.summary = this.generateReportSummary(report.data);

    return report;
  }

  generateReportSummary(data) {
    const values = Object.values(data);
    const costs = values.map(item => item.totalCost || 0);
    
    return {
      count: values.length,
      totalCost: costs.reduce((sum, cost) => sum + cost, 0),
      averageCost: costs.length > 0 ? costs.reduce((sum, cost) => sum + cost, 0) / costs.length : 0,
      maxCost: Math.max(...costs),
      minCost: Math.min(...costs),
      topSpenders: values
        .sort((a, b) => (b.totalCost || 0) - (a.totalCost || 0))
        .slice(0, 5)
        .map(item => ({ 
          id: item.id || item.name, 
          name: item.name, 
          cost: item.totalCost 
        }))
    };
  }

  emitBudgetAlert(project, overageAmount) {
    console.log(`Budget Alert: Project ${project.name} (${project.id}) is over budget by $${overageAmount.toFixed(2)}`);
  }

  exportCostData(format = 'json', options = {}) {
    const report = this.generateCostReport({ ...options, format: 'detailed' });
    
    if (format === 'json') {
      return JSON.stringify(report, null, 2);
    } else if (format === 'csv') {
      return this.convertReportToCSV(report);
    }
    
    return report;
  }

  convertReportToCSV(report) {
    const lines = ['id,name,type,total_cost,department,budget,budget_utilization'];
    
    Object.entries(report.data).forEach(([id, item]) => {
      const type = item.user ? 'user' : 'project';
      const entity = item.user || item.project || {};
      
      lines.push([
        id,
        entity.name || id,
        type,
        item.totalCost || 0,
        entity.department || '',
        entity.budget || '',
        item.budgetUtilization || ''
      ].join(','));
    });
    
    return lines.join('\n');
  }
}

module.exports = CostAllocation;