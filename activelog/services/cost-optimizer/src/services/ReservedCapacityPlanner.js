class ReservedCapacityPlanner {
  constructor() {
    this.reservations = new Map();
    this.usageHistory = new Map();
    this.recommendations = new Map();
    this.commitmentTerms = {
      '1yr': { discountRate: 0.31, upfrontOptions: ['none', 'partial', 'full'] },
      '3yr': { discountRate: 0.54, upfrontOptions: ['none', 'partial', 'full'] }
    };
    this.paymentOptions = {
      'none': { upfrontPercent: 0, monthlyPercent: 1 },
      'partial': { upfrontPercent: 0.3, monthlyPercent: 0.7 },
      'full': { upfrontPercent: 1, monthlyPercent: 0 }
    };
  }

  analyzeUsagePatterns(resourceId, historicalData) {
    if (!historicalData || historicalData.length < 30) {
      throw new Error('Insufficient historical data for analysis (minimum 30 days required)');
    }

    const analysis = {
      resourceId,
      analyzedAt: new Date().toISOString(),
      dataPoints: historicalData.length,
      usage: this.calculateUsageMetrics(historicalData),
      patterns: this.identifyUsagePatterns(historicalData),
      stability: this.assessStability(historicalData),
      seasonality: this.detectSeasonality(historicalData),
      growth: this.calculateGrowthTrend(historicalData)
    };

    this.usageHistory.set(resourceId, analysis);
    return analysis;
  }

  calculateUsageMetrics(data) {
    const sortedByHours = data.map(d => d.hours).sort((a, b) => a - b);
    const totalHours = data.reduce((sum, d) => sum + d.hours, 0);
    const avgHours = totalHours / data.length;
    const maxHours = Math.max(...sortedByHours);
    const minHours = Math.min(...sortedByHours);

    const q1Index = Math.floor(sortedByHours.length * 0.25);
    const q3Index = Math.floor(sortedByHours.length * 0.75);
    const medianIndex = Math.floor(sortedByHours.length * 0.5);

    return {
      total: totalHours,
      average: Math.round(avgHours * 100) / 100,
      median: sortedByHours[medianIndex],
      minimum: minHours,
      maximum: maxHours,
      q1: sortedByHours[q1Index],
      q3: sortedByHours[q3Index],
      standardDeviation: this.calculateStandardDeviation(data.map(d => d.hours)),
      utilizationRate: avgHours / Math.max(maxHours, 24)
    };
  }

  calculateStandardDeviation(values) {
    const avg = values.reduce((sum, val) => sum + val, 0) / values.length;
    const variance = values.reduce((sum, val) => sum + Math.pow(val - avg, 2), 0) / values.length;
    return Math.sqrt(variance);
  }

  identifyUsagePatterns(data) {
    const hourlyPattern = this.analyzeHourlyPattern(data);
    const dailyPattern = this.analyzeDailyPattern(data);
    const weeklyPattern = this.analyzeWeeklyPattern(data);
    const monthlyPattern = this.analyzeMonthlyPattern(data);

    return {
      hourly: hourlyPattern,
      daily: dailyPattern,
      weekly: weeklyPattern,
      monthly: monthlyPattern,
      predictability: this.calculatePredictability([hourlyPattern, dailyPattern, weeklyPattern])
    };
  }

  analyzeHourlyPattern(data) {
    const hourlyUsage = Array(24).fill(0);
    const hourlyCounts = Array(24).fill(0);

    data.forEach(entry => {
      const hour = new Date(entry.timestamp).getHours();
      hourlyUsage[hour] += entry.hours;
      hourlyCounts[hour]++;
    });

    const hourlyAverages = hourlyUsage.map((usage, i) => 
      hourlyCounts[i] > 0 ? usage / hourlyCounts[i] : 0
    );

    return {
      averages: hourlyAverages,
      peakHour: hourlyAverages.indexOf(Math.max(...hourlyAverages)),
      lowHour: hourlyAverages.indexOf(Math.min(...hourlyAverages)),
      variance: this.calculateStandardDeviation(hourlyAverages)
    };
  }

  analyzeDailyPattern(data) {
    const dailyUsage = Array(7).fill(0);
    const dailyCounts = Array(7).fill(0);

    data.forEach(entry => {
      const day = new Date(entry.timestamp).getDay();
      dailyUsage[day] += entry.hours;
      dailyCounts[day]++;
    });

    const dailyAverages = dailyUsage.map((usage, i) => 
      dailyCounts[i] > 0 ? usage / dailyCounts[i] : 0
    );

    return {
      averages: dailyAverages,
      weekdayAvg: (dailyAverages.slice(1, 6).reduce((a, b) => a + b, 0) / 5),
      weekendAvg: ((dailyAverages[0] + dailyAverages[6]) / 2),
      variance: this.calculateStandardDeviation(dailyAverages)
    };
  }

  analyzeWeeklyPattern(data) {
    const weeklyUsage = new Map();
    
    data.forEach(entry => {
      const week = this.getWeekNumber(new Date(entry.timestamp));
      if (!weeklyUsage.has(week)) weeklyUsage.set(week, []);
      weeklyUsage.get(week).push(entry.hours);
    });

    const weeklyTotals = Array.from(weeklyUsage.values()).map(week => 
      week.reduce((sum, hours) => sum + hours, 0)
    );

    return {
      totalWeeks: weeklyTotals.length,
      averageWeekly: weeklyTotals.reduce((a, b) => a + b, 0) / weeklyTotals.length,
      variance: this.calculateStandardDeviation(weeklyTotals),
      trend: this.calculateTrend(weeklyTotals)
    };
  }

  analyzeMonthlyPattern(data) {
    const monthlyUsage = new Map();
    
    data.forEach(entry => {
      const month = new Date(entry.timestamp).getMonth();
      if (!monthlyUsage.has(month)) monthlyUsage.set(month, []);
      monthlyUsage.get(month).push(entry.hours);
    });

    const monthlyTotals = Array.from(monthlyUsage.values()).map(month => 
      month.reduce((sum, hours) => sum + hours, 0)
    );

    return {
      totalMonths: monthlyTotals.length,
      averageMonthly: monthlyTotals.reduce((a, b) => a + b, 0) / monthlyTotals.length,
      variance: this.calculateStandardDeviation(monthlyTotals),
      seasonality: this.detectMonthlyCycles(monthlyUsage)
    };
  }

  getWeekNumber(date) {
    const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
    const dayNum = d.getUTCDay() || 7;
    d.setUTCDate(d.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    return Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
  }

  calculateTrend(values) {
    if (values.length < 2) return 0;
    
    const n = values.length;
    const x = Array.from({ length: n }, (_, i) => i);
    const sumX = x.reduce((a, b) => a + b, 0);
    const sumY = values.reduce((a, b) => a + b, 0);
    const sumXY = x.reduce((sum, xi, i) => sum + xi * values[i], 0);
    const sumXX = x.reduce((sum, xi) => sum + xi * xi, 0);
    
    return (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
  }

  calculatePredictability(patterns) {
    let predictabilityScore = 0;
    let totalWeight = 0;

    patterns.forEach((pattern, index) => {
      const weight = [0.3, 0.4, 0.3][index] || 0.3;
      const variance = pattern.variance || 0;
      const score = Math.max(0, 1 - (variance / 100));
      
      predictabilityScore += score * weight;
      totalWeight += weight;
    });

    return predictabilityScore / totalWeight;
  }

  assessStability(data) {
    const recentData = data.slice(-30);
    const olderData = data.slice(0, -30);
    
    if (olderData.length === 0) {
      return { score: 0.5, reason: 'Insufficient historical data' };
    }

    const recentAvg = recentData.reduce((sum, d) => sum + d.hours, 0) / recentData.length;
    const olderAvg = olderData.reduce((sum, d) => sum + d.hours, 0) / olderData.length;
    
    const stability = 1 - Math.abs(recentAvg - olderAvg) / Math.max(recentAvg, olderAvg, 1);
    
    let reason = '';
    if (stability > 0.9) reason = 'Very stable usage pattern';
    else if (stability > 0.7) reason = 'Stable usage with minor variations';
    else if (stability > 0.5) reason = 'Moderate stability';
    else reason = 'Unstable usage pattern';

    return { score: stability, reason };
  }

  detectSeasonality(data) {
    if (data.length < 84) {
      return { detected: false, reason: 'Insufficient data for seasonality detection' };
    }

    const monthlyAverages = this.calculateMonthlyAverages(data);
    const seasonalVariance = this.calculateStandardDeviation(Object.values(monthlyAverages));
    const overallAverage = Object.values(monthlyAverages).reduce((a, b) => a + b) / 12;
    
    const seasonalityStrength = seasonalVariance / overallAverage;
    const isSeasonable = seasonalityStrength > 0.2;

    return {
      detected: isSeasonable,
      strength: seasonalityStrength,
      monthlyAverages,
      peakMonth: Object.keys(monthlyAverages).reduce((a, b) => 
        monthlyAverages[a] > monthlyAverages[b] ? a : b
      ),
      lowMonth: Object.keys(monthlyAverages).reduce((a, b) => 
        monthlyAverages[a] < monthlyAverages[b] ? a : b
      )
    };
  }

  calculateMonthlyAverages(data) {
    const monthlyData = {};
    
    data.forEach(entry => {
      const month = new Date(entry.timestamp).getMonth();
      if (!monthlyData[month]) monthlyData[month] = [];
      monthlyData[month].push(entry.hours);
    });

    return Object.keys(monthlyData).reduce((acc, month) => {
      acc[month] = monthlyData[month].reduce((sum, hours) => sum + hours, 0) / monthlyData[month].length;
      return acc;
    }, {});
  }

  calculateGrowthTrend(data) {
    if (data.length < 60) {
      return { trend: 'insufficient_data', rate: 0 };
    }

    const firstHalf = data.slice(0, Math.floor(data.length / 2));
    const secondHalf = data.slice(Math.floor(data.length / 2));

    const firstAvg = firstHalf.reduce((sum, d) => sum + d.hours, 0) / firstHalf.length;
    const secondAvg = secondHalf.reduce((sum, d) => sum + d.hours, 0) / secondHalf.length;

    const growthRate = ((secondAvg - firstAvg) / firstAvg) * 100;
    
    let trend;
    if (Math.abs(growthRate) < 5) trend = 'stable';
    else if (growthRate > 0) trend = 'growing';
    else trend = 'declining';

    return { trend, rate: growthRate };
  }

  generateReservationRecommendations(resourceId, costData) {
    const analysis = this.usageHistory.get(resourceId);
    if (!analysis) {
      throw new Error(`No usage analysis found for resource ${resourceId}`);
    }

    const recommendations = [];
    const { onDemandPrice, currentMonthlyCost } = costData;

    Object.entries(this.commitmentTerms).forEach(([term, termData]) => {
      Object.keys(this.paymentOptions).forEach(paymentOption => {
        const recommendation = this.calculateReservationBenefit(
          analysis, 
          term, 
          paymentOption, 
          onDemandPrice, 
          currentMonthlyCost
        );

        if (recommendation.beneficial) {
          recommendations.push(recommendation);
        }
      });
    });

    const sortedRecommendations = recommendations.sort((a, b) => b.totalSavings - a.totalSavings);
    
    const finalRecommendation = {
      resourceId,
      generatedAt: new Date().toISOString(),
      usageAnalysis: analysis,
      recommendations: sortedRecommendations,
      topRecommendation: sortedRecommendations[0] || null,
      riskAssessment: this.assessReservationRisk(analysis),
      implementation: sortedRecommendations[0] ? 
        this.generateImplementationPlan(sortedRecommendations[0]) : null
    };

    this.recommendations.set(resourceId, finalRecommendation);
    return finalRecommendation;
  }

  calculateReservationBenefit(analysis, term, paymentOption, onDemandPrice, currentMonthlyCost) {
    const termData = this.commitmentTerms[term];
    const paymentData = this.paymentOptions[paymentOption];
    
    const reservedPrice = onDemandPrice * (1 - termData.discountRate);
    const termMonths = term === '1yr' ? 12 : 36;
    
    const baselineHours = Math.min(analysis.usage.average * 30, 730);
    const reservationUtilization = Math.min(analysis.usage.utilizationRate, 1);
    
    const reservedMonthlyCost = reservedPrice * baselineHours;
    const upfrontCost = reservedMonthlyCost * termMonths * paymentData.upfrontPercent;
    const recurringMonthlyCost = reservedMonthlyCost * paymentData.monthlyPercent;
    
    const totalReservedCost = upfrontCost + (recurringMonthlyCost * termMonths);
    const totalOnDemandCost = currentMonthlyCost * termMonths;
    const totalSavings = totalOnDemandCost - totalReservedCost;
    
    const breakEvenMonths = upfrontCost > 0 ? 
      upfrontCost / (currentMonthlyCost - recurringMonthlyCost) : 0;

    const beneficial = totalSavings > 0 && reservationUtilization > 0.7;

    return {
      term,
      paymentOption,
      beneficial,
      reservedPrice,
      baselineHours,
      reservationUtilization,
      costs: {
        upfront: Math.round(upfrontCost * 100) / 100,
        monthlyRecurring: Math.round(recurringMonthlyCost * 100) / 100,
        totalReserved: Math.round(totalReservedCost * 100) / 100,
        totalOnDemand: Math.round(totalOnDemandCost * 100) / 100
      },
      savings: {
        total: Math.round(totalSavings * 100) / 100,
        monthly: Math.round((totalSavings / termMonths) * 100) / 100,
        percentage: Math.round((totalSavings / totalOnDemandCost) * 10000) / 100
      },
      breakEvenMonths: Math.round(breakEvenMonths * 10) / 10,
      confidence: this.calculateConfidence(analysis, reservationUtilization)
    };
  }

  calculateConfidence(analysis, utilization) {
    let confidence = 0.5;
    
    if (analysis.stability.score > 0.8) confidence += 0.2;
    else if (analysis.stability.score > 0.6) confidence += 0.1;
    
    if (analysis.patterns.predictability > 0.8) confidence += 0.2;
    else if (analysis.patterns.predictability > 0.6) confidence += 0.1;
    
    if (utilization > 0.9) confidence += 0.1;
    else if (utilization > 0.7) confidence += 0.05;
    
    if (analysis.dataPoints > 90) confidence += 0.1;
    else if (analysis.dataPoints > 60) confidence += 0.05;
    
    return Math.min(1.0, confidence);
  }

  assessReservationRisk(analysis) {
    const risks = [];
    let overallRisk = 'low';

    if (analysis.stability.score < 0.6) {
      risks.push({
        type: 'usage_instability',
        level: 'high',
        description: 'Usage patterns are unstable, reservation may not be fully utilized'
      });
      overallRisk = 'high';
    }

    if (analysis.growth.trend === 'declining' && Math.abs(analysis.growth.rate) > 10) {
      risks.push({
        type: 'declining_usage',
        level: 'medium',
        description: 'Usage is declining, reservation may exceed future needs'
      });
      if (overallRisk === 'low') overallRisk = 'medium';
    }

    if (analysis.patterns.predictability < 0.5) {
      risks.push({
        type: 'unpredictable_usage',
        level: 'medium',
        description: 'Usage patterns are unpredictable, making capacity planning difficult'
      });
      if (overallRisk === 'low') overallRisk = 'medium';
    }

    if (analysis.seasonality.detected && analysis.seasonality.strength > 0.4) {
      risks.push({
        type: 'high_seasonality',
        level: 'medium',
        description: 'High seasonal variation may lead to under-utilization during low seasons'
      });
      if (overallRisk === 'low') overallRisk = 'medium';
    }

    return {
      overall: overallRisk,
      risks,
      mitigations: this.generateRiskMitigations(risks)
    };
  }

  generateRiskMitigations(risks) {
    const mitigations = [];

    risks.forEach(risk => {
      switch (risk.type) {
        case 'usage_instability':
          mitigations.push('Consider shorter-term reservations or convertible reservations');
          break;
        case 'declining_usage':
          mitigations.push('Monitor usage trends closely and consider selling unused reservations');
          break;
        case 'unpredictable_usage':
          mitigations.push('Start with partial capacity reservation and monitor utilization');
          break;
        case 'high_seasonality':
          mitigations.push('Reserve for baseline usage and use on-demand for seasonal peaks');
          break;
      }
    });

    return mitigations;
  }

  generateImplementationPlan(recommendation) {
    return {
      steps: [
        'Review and approve reservation purchase',
        'Determine exact capacity requirements',
        'Select appropriate instance family and size',
        'Choose availability zones for reservation',
        'Execute reservation purchase',
        'Monitor utilization and track savings',
        'Set up alerts for low utilization'
      ],
      timeline: '1-2 weeks',
      requirements: [
        'Budget approval for upfront costs',
        'Capacity planning validation',
        'Monitoring setup'
      ],
      firstMonthActions: [
        'Track actual vs. predicted utilization',
        'Validate savings calculations',
        'Adjust future reservations based on learnings'
      ],
      kpis: [
        'Reservation utilization rate',
        'Actual vs. predicted savings',
        'Cost per unit reduction'
      ]
    };
  }

  createReservation(config) {
    const reservationId = `ri_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const reservation = {
      id: reservationId,
      resourceId: config.resourceId,
      instanceType: config.instanceType,
      term: config.term,
      paymentOption: config.paymentOption,
      quantity: config.quantity,
      upfrontCost: config.upfrontCost,
      recurringCost: config.recurringCost,
      startDate: config.startDate || new Date().toISOString(),
      endDate: this.calculateEndDate(config.startDate || new Date().toISOString(), config.term),
      status: 'active',
      utilizationTracking: {
        totalHours: 0,
        utilizationRate: 0,
        lastUpdated: new Date().toISOString()
      },
      createdAt: new Date().toISOString()
    };

    this.reservations.set(reservationId, reservation);
    return reservation;
  }

  calculateEndDate(startDate, term) {
    const start = new Date(startDate);
    const months = term === '1yr' ? 12 : 36;
    start.setMonth(start.getMonth() + months);
    return start.toISOString();
  }

  trackReservationUtilization(reservationId, usageHours) {
    const reservation = this.reservations.get(reservationId);
    if (!reservation) {
      throw new Error(`Reservation ${reservationId} not found`);
    }

    const termHours = reservation.term === '1yr' ? 8760 : 26280;
    const elapsedHours = (Date.now() - new Date(reservation.startDate).getTime()) / (1000 * 60 * 60);
    
    reservation.utilizationTracking.totalHours += usageHours;
    reservation.utilizationTracking.utilizationRate = 
      (reservation.utilizationTracking.totalHours / Math.min(elapsedHours, termHours)) * 100;
    reservation.utilizationTracking.lastUpdated = new Date().toISOString();

    if (reservation.utilizationTracking.utilizationRate < 70) {
      console.warn(`Low utilization warning: Reservation ${reservationId} at ${reservation.utilizationTracking.utilizationRate.toFixed(1)}%`);
    }

    return reservation;
  }

  getReservationReport(reservationId) {
    const reservation = this.reservations.get(reservationId);
    if (!reservation) {
      throw new Error(`Reservation ${reservationId} not found`);
    }

    const elapsedMonths = (Date.now() - new Date(reservation.startDate).getTime()) / (1000 * 60 * 60 * 24 * 30);
    const totalMonths = reservation.term === '1yr' ? 12 : 36;
    const remainingMonths = Math.max(0, totalMonths - elapsedMonths);

    return {
      reservation,
      utilization: reservation.utilizationTracking,
      timeline: {
        elapsedMonths: Math.round(elapsedMonths * 10) / 10,
        remainingMonths: Math.round(remainingMonths * 10) / 10,
        progressPercentage: Math.round((elapsedMonths / totalMonths) * 10000) / 100
      },
      financials: this.calculateReservationSavings(reservation)
    };
  }

  calculateReservationSavings(reservation) {
    const onDemandPrice = this.getOnDemandPrice(reservation.instanceType);
    const actualSavings = reservation.utilizationTracking.totalHours * 
      (onDemandPrice - (reservation.recurringCost / 730));

    return {
      projectedSavings: reservation.projectedSavings,
      actualSavings: Math.round(actualSavings * 100) / 100,
      savingsVariance: actualSavings - (reservation.projectedSavings || 0)
    };
  }

  getOnDemandPrice(instanceType) {
    const prices = {
      't3.micro': 0.0104,
      't3.small': 0.0208,
      't3.medium': 0.0416,
      'c5.large': 0.085,
      'm5.large': 0.096
    };
    return prices[instanceType] || 0.1;
  }

  getAllReservations() {
    return Array.from(this.reservations.values());
  }

  getRecommendations(resourceId) {
    return this.recommendations.get(resourceId);
  }
}

module.exports = ReservedCapacityPlanner;