class MultiCloudComparator {
  constructor() {
    this.providers = new Map();
    this.pricingCache = new Map();
    this.exchangeRates = new Map();
    this.regions = new Map();
    this.cacheTimeout = 3600000; // 1 hour
    
    this.initializeProviders();
    this.initializeRegions();
  }

  initializeProviders() {
    this.providers.set('aws', {
      name: 'Amazon Web Services',
      regions: ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1'],
      currency: 'USD',
      pricingAPI: 'https://pricing.us-east-1.amazonaws.com',
      instanceFamilies: ['t3', 'c5', 'm5', 'r5', 'i3'],
      storageTypes: ['gp3', 'gp2', 'io2', 'sc1', 'st1'],
      networkPricing: { outbound: 0.09, inbound: 0 }
    });

    this.providers.set('gcp', {
      name: 'Google Cloud Platform',
      regions: ['us-central1', 'us-west1', 'europe-west1', 'asia-southeast1'],
      currency: 'USD',
      pricingAPI: 'https://cloudbilling.googleapis.com/v1',
      instanceFamilies: ['e2', 'n1', 'n2', 'c2', 'm1'],
      storageTypes: ['pd-standard', 'pd-ssd', 'pd-balanced'],
      networkPricing: { outbound: 0.12, inbound: 0 }
    });

    this.providers.set('azure', {
      name: 'Microsoft Azure',
      regions: ['eastus', 'westus2', 'westeurope', 'southeastasia'],
      currency: 'USD',
      pricingAPI: 'https://prices.azure.com/api/retail/prices',
      instanceFamilies: ['B', 'D', 'F', 'E', 'M'],
      storageTypes: ['standard_lrs', 'premium_ssd', 'standard_ssd'],
      networkPricing: { outbound: 0.087, inbound: 0 }
    });
  }

  initializeRegions() {
    // AWS Regions
    this.regions.set('aws-us-east-1', {
      provider: 'aws',
      name: 'US East (N. Virginia)',
      location: 'Virginia, USA',
      priceMultiplier: 1.0
    });
    this.regions.set('aws-us-west-2', {
      provider: 'aws',
      name: 'US West (Oregon)',
      location: 'Oregon, USA',
      priceMultiplier: 1.0
    });
    this.regions.set('aws-eu-west-1', {
      provider: 'aws',
      name: 'Europe (Ireland)',
      location: 'Dublin, Ireland',
      priceMultiplier: 1.1
    });

    // GCP Regions
    this.regions.set('gcp-us-central1', {
      provider: 'gcp',
      name: 'Iowa',
      location: 'Iowa, USA',
      priceMultiplier: 1.0
    });
    this.regions.set('gcp-europe-west1', {
      provider: 'gcp',
      name: 'Belgium',
      location: 'St. Ghislain, Belgium',
      priceMultiplier: 1.05
    });

    // Azure Regions
    this.regions.set('azure-eastus', {
      provider: 'azure',
      name: 'East US',
      location: 'Virginia, USA',
      priceMultiplier: 1.0
    });
    this.regions.set('azure-westeurope', {
      provider: 'azure',
      name: 'West Europe',
      location: 'Netherlands',
      priceMultiplier: 1.08
    });
  }

  async compareWorkloadCosts(workloadSpec, options = {}) {
    const { regions = [], providers = ['aws', 'gcp', 'azure'], includeTaxes = false } = options;
    
    const comparisons = [];
    const targetProviders = providers.filter(p => this.providers.has(p));
    
    for (const provider of targetProviders) {
      const providerRegions = regions.length > 0 
        ? regions.filter(r => r.startsWith(provider))
        : this.getDefaultRegions(provider);
      
      for (const region of providerRegions) {
        try {
          const cost = await this.calculateWorkloadCost(workloadSpec, provider, region);
          comparisons.push({
            provider,
            region,
            ...cost,
            taxes: includeTaxes ? this.calculateTaxes(cost.totalCost, region) : 0
          });
        } catch (error) {
          console.warn(`Failed to get pricing for ${provider} in ${region}: ${error.message}`);
        }
      }
    }

    return this.analyzeComparisons(comparisons, workloadSpec);
  }

  async calculateWorkloadCost(workloadSpec, provider, region) {
    const { compute, storage, network, duration = 730 } = workloadSpec;
    
    let totalCost = 0;
    const breakdown = {};

    // Compute costs
    if (compute) {
      const computeCost = await this.calculateComputeCost(compute, provider, region, duration);
      totalCost += computeCost.total;
      breakdown.compute = computeCost;
    }

    // Storage costs
    if (storage) {
      const storageCost = await this.calculateStorageCost(storage, provider, region, duration);
      totalCost += storageCost.total;
      breakdown.storage = storageCost;
    }

    // Network costs
    if (network) {
      const networkCost = await this.calculateNetworkCost(network, provider, region);
      totalCost += networkCost.total;
      breakdown.network = networkCost;
    }

    return {
      totalCost: Math.round(totalCost * 100) / 100,
      breakdown,
      currency: this.providers.get(provider).currency,
      calculatedAt: new Date().toISOString()
    };
  }

  async calculateComputeCost(compute, provider, region, duration) {
    const instancePrice = await this.getInstancePrice(compute.instanceType, provider, region);
    const regionMultiplier = this.getRegionPriceMultiplier(provider, region);
    
    let hourlyCost = instancePrice * regionMultiplier;
    
    // Apply discounts
    if (compute.spot) {
      hourlyCost *= 0.4; // Average 60% discount for spot instances
    }
    
    if (compute.reserved) {
      const discount = compute.reserved.term === '3yr' ? 0.54 : 0.31;
      hourlyCost *= (1 - discount);
    }

    const totalCost = hourlyCost * duration;
    
    return {
      total: totalCost,
      hourly: hourlyCost,
      duration,
      instanceType: compute.instanceType,
      discounts: {
        spot: compute.spot ? 60 : 0,
        reserved: compute.reserved ? (compute.reserved.term === '3yr' ? 54 : 31) : 0
      }
    };
  }

  async calculateStorageCost(storage, provider, region, duration) {
    const storagePrice = await this.getStoragePrice(storage.type, provider, region);
    const regionMultiplier = this.getRegionPriceMultiplier(provider, region);
    
    let monthlyCostPerGB = storagePrice * regionMultiplier;
    
    // Apply lifecycle policies discount
    if (storage.lifecycle) {
      monthlyCostPerGB *= 0.7; // 30% average savings with lifecycle policies
    }
    
    const monthlyDuration = duration / 730 * 30; // Convert hours to months
    const totalCost = monthlyCostPerGB * storage.sizeGB * monthlyDuration;
    
    let iopsCharges = 0;
    if (storage.iops && provider === 'aws') {
      const baseIops = storage.type === 'gp3' ? 3000 : 0;
      const additionalIops = Math.max(0, storage.iops - baseIops);
      iopsCharges = additionalIops * 0.005 * monthlyDuration; // $0.005 per IOPS per month
    }
    
    return {
      total: totalCost + iopsCharges,
      monthly: monthlyCostPerGB * storage.sizeGB,
      sizeGB: storage.sizeGB,
      storageType: storage.type,
      iopsCharges,
      discounts: {
        lifecycle: storage.lifecycle ? 30 : 0
      }
    };
  }

  async calculateNetworkCost(network, provider, region) {
    const providerData = this.providers.get(provider);
    const outboundRate = providerData.networkPricing.outbound;
    
    let totalCost = 0;
    let breakdown = {};
    
    if (network.outboundGB) {
      const outboundCost = network.outboundGB * outboundRate;
      totalCost += outboundCost;
      breakdown.outbound = {
        gb: network.outboundGB,
        rate: outboundRate,
        cost: outboundCost
      };
    }
    
    // CDN costs (simplified)
    if (network.cdnGB) {
      let cdnRate = 0.085; // Average CDN rate
      if (provider === 'gcp') cdnRate = 0.08;
      else if (provider === 'azure') cdnRate = 0.087;
      
      const cdnCost = network.cdnGB * cdnRate;
      totalCost += cdnCost;
      breakdown.cdn = {
        gb: network.cdnGB,
        rate: cdnRate,
        cost: cdnCost
      };
    }
    
    return {
      total: totalCost,
      breakdown
    };
  }

  async getInstancePrice(instanceType, provider, region) {
    const cacheKey = `${provider}-${instanceType}-${region}`;
    const cached = this.pricingCache.get(cacheKey);
    
    if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
      return cached.price;
    }
    
    // Simulate API call with realistic pricing
    let price;
    
    switch (provider) {
      case 'aws':
        price = this.getAWSInstancePrice(instanceType);
        break;
      case 'gcp':
        price = this.getGCPInstancePrice(instanceType);
        break;
      case 'azure':
        price = this.getAzureInstancePrice(instanceType);
        break;
      default:
        throw new Error(`Unsupported provider: ${provider}`);
    }
    
    this.pricingCache.set(cacheKey, {
      price,
      timestamp: Date.now()
    });
    
    return price;
  }

  getAWSInstancePrice(instanceType) {
    const prices = {
      't3.micro': 0.0104,
      't3.small': 0.0208,
      't3.medium': 0.0416,
      't3.large': 0.0832,
      'c5.large': 0.085,
      'c5.xlarge': 0.17,
      'm5.large': 0.096,
      'm5.xlarge': 0.192,
      'r5.large': 0.126,
      'r5.xlarge': 0.252
    };
    return prices[instanceType] || 0.1;
  }

  getGCPInstancePrice(instanceType) {
    const prices = {
      'e2-micro': 0.00668,
      'e2-small': 0.01336,
      'e2-medium': 0.02672,
      'e2-standard-2': 0.05344,
      'e2-standard-4': 0.10688,
      'n1-standard-1': 0.0475,
      'n1-standard-2': 0.095,
      'n1-standard-4': 0.19,
      'n2-standard-2': 0.0776,
      'n2-standard-4': 0.1552
    };
    return prices[instanceType] || 0.08;
  }

  getAzureInstancePrice(instanceType) {
    const prices = {
      'B1S': 0.0146,
      'B1MS': 0.0292,
      'B2S': 0.0584,
      'B2MS': 0.1168,
      'D2s_v3': 0.096,
      'D4s_v3': 0.192,
      'D8s_v3': 0.384,
      'F2s_v2': 0.0836,
      'F4s_v2': 0.1672
    };
    return prices[instanceType] || 0.09;
  }

  async getStoragePrice(storageType, provider, region) {
    const cacheKey = `storage-${provider}-${storageType}-${region}`;
    const cached = this.pricingCache.get(cacheKey);
    
    if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
      return cached.price;
    }
    
    let price;
    
    switch (provider) {
      case 'aws':
        price = { gp3: 0.08, gp2: 0.10, io2: 0.125, sc1: 0.025, st1: 0.045 }[storageType] || 0.08;
        break;
      case 'gcp':
        price = { 'pd-standard': 0.04, 'pd-ssd': 0.17, 'pd-balanced': 0.1 }[storageType] || 0.08;
        break;
      case 'azure':
        price = { 'standard_lrs': 0.045, 'premium_ssd': 0.135, 'standard_ssd': 0.075 }[storageType] || 0.08;
        break;
      default:
        throw new Error(`Unsupported provider: ${provider}`);
    }
    
    this.pricingCache.set(cacheKey, {
      price,
      timestamp: Date.now()
    });
    
    return price;
  }

  getRegionPriceMultiplier(provider, region) {
    const regionKey = `${provider}-${region}`;
    const regionData = this.regions.get(regionKey);
    return regionData ? regionData.priceMultiplier : 1.0;
  }

  getDefaultRegions(provider) {
    const providerData = this.providers.get(provider);
    return providerData ? providerData.regions.map(r => `${provider}-${r}`) : [];
  }

  analyzeComparisons(comparisons, workloadSpec) {
    if (comparisons.length === 0) {
      return {
        error: 'No pricing data available for comparison',
        comparisons: []
      };
    }

    // Sort by total cost
    const sortedComparisons = comparisons.sort((a, b) => a.totalCost - b.totalCost);
    
    const cheapest = sortedComparisons[0];
    const mostExpensive = sortedComparisons[sortedComparisons.length - 1];
    
    // Calculate savings opportunities
    const savings = sortedComparisons.map(comparison => ({
      ...comparison,
      savingsVsCheapest: {
        amount: Math.round((comparison.totalCost - cheapest.totalCost) * 100) / 100,
        percentage: cheapest.totalCost > 0 ? 
          Math.round(((comparison.totalCost - cheapest.totalCost) / cheapest.totalCost) * 10000) / 100 : 0
      },
      savingsVsMostExpensive: {
        amount: Math.round((mostExpensive.totalCost - comparison.totalCost) * 100) / 100,
        percentage: mostExpensive.totalCost > 0 ? 
          Math.round(((mostExpensive.totalCost - comparison.totalCost) / mostExpensive.totalCost) * 10000) / 100 : 0
      }
    }));

    return {
      workload: workloadSpec,
      comparisonCount: comparisons.length,
      cheapestOption: cheapest,
      mostExpensiveOption: mostExpensive,
      maxSavings: {
        amount: Math.round((mostExpensive.totalCost - cheapest.totalCost) * 100) / 100,
        percentage: mostExpensive.totalCost > 0 ? 
          Math.round(((mostExpensive.totalCost - cheapest.totalCost) / mostExpensive.totalCost) * 10000) / 100 : 0
      },
      comparisons: savings,
      recommendations: this.generateMigrationRecommendations(savings),
      summary: this.generateComparisonSummary(savings)
    };
  }

  generateMigrationRecommendations(comparisons) {
    const recommendations = [];
    const cheapest = comparisons[0];
    
    // Cost optimization recommendations
    const significantSavings = comparisons.filter(c => 
      c.savingsVsCheapest.percentage > 20 && c.savingsVsCheapest.amount > 50
    );
    
    if (significantSavings.length > 0) {
      recommendations.push({
        type: 'cost_optimization',
        priority: 'high',
        description: `Consider migrating to ${cheapest.provider} (${cheapest.region}) for significant cost savings`,
        potentialSavings: significantSavings[significantSavings.length - 1].savingsVsCheapest
      });
    }
    
    // Multi-region deployment recommendations
    const regionAnalysis = this.analyzeRegionalPricing(comparisons);
    if (regionAnalysis.recommendation) {
      recommendations.push(regionAnalysis.recommendation);
    }
    
    // Provider-specific optimizations
    const providerOptimizations = this.analyzeProviderOptimizations(comparisons);
    recommendations.push(...providerOptimizations);
    
    return recommendations;
  }

  analyzeRegionalPricing(comparisons) {
    const byProvider = {};
    
    comparisons.forEach(comp => {
      if (!byProvider[comp.provider]) byProvider[comp.provider] = [];
      byProvider[comp.provider].push(comp);
    });
    
    let bestRegionalStrategy = null;
    let maxSavings = 0;
    
    Object.entries(byProvider).forEach(([provider, regions]) => {
      if (regions.length > 1) {
        const cheapestRegion = regions.reduce((min, region) => 
          region.totalCost < min.totalCost ? region : min
        );
        const mostExpensiveRegion = regions.reduce((max, region) => 
          region.totalCost > max.totalCost ? region : max
        );
        
        const savings = mostExpensiveRegion.totalCost - cheapestRegion.totalCost;
        if (savings > maxSavings) {
          maxSavings = savings;
          bestRegionalStrategy = {
            type: 'regional_optimization',
            priority: 'medium',
            description: `Within ${provider}, choose ${cheapestRegion.region} over ${mostExpensiveRegion.region}`,
            potentialSavings: {
              amount: Math.round(savings * 100) / 100,
              percentage: Math.round((savings / mostExpensiveRegion.totalCost) * 10000) / 100
            }
          };
        }
      }
    });
    
    return {
      recommendation: bestRegionalStrategy
    };
  }

  analyzeProviderOptimizations(comparisons) {
    const optimizations = [];
    
    // Look for spot instance opportunities
    const highComputeCostComparisons = comparisons.filter(c => 
      c.breakdown.compute && c.breakdown.compute.total / c.totalCost > 0.6
    );
    
    if (highComputeCostComparisons.length > 0) {
      optimizations.push({
        type: 'spot_instances',
        priority: 'high',
        description: 'Consider spot instances for compute-heavy workloads (up to 60% savings)',
        applicableProviders: ['aws', 'gcp', 'azure']
      });
    }
    
    // Storage optimization opportunities
    const highStorageCostComparisons = comparisons.filter(c => 
      c.breakdown.storage && c.breakdown.storage.total / c.totalCost > 0.3
    );
    
    if (highStorageCostComparisons.length > 0) {
      optimizations.push({
        type: 'storage_optimization',
        priority: 'medium',
        description: 'Implement storage lifecycle policies and choose appropriate storage tiers',
        applicableProviders: ['aws', 'gcp', 'azure']
      });
    }
    
    return optimizations;
  }

  generateComparisonSummary(comparisons) {
    const providers = [...new Set(comparisons.map(c => c.provider))];
    const regions = [...new Set(comparisons.map(c => c.region))];
    
    const avgCostByProvider = {};
    providers.forEach(provider => {
      const providerComparisons = comparisons.filter(c => c.provider === provider);
      avgCostByProvider[provider] = {
        averageCost: providerComparisons.reduce((sum, c) => sum + c.totalCost, 0) / providerComparisons.length,
        minCost: Math.min(...providerComparisons.map(c => c.totalCost)),
        maxCost: Math.max(...providerComparisons.map(c => c.totalCost)),
        regionCount: providerComparisons.length
      };
    });
    
    return {
      totalComparisons: comparisons.length,
      providersAnalyzed: providers.length,
      regionsAnalyzed: regions.length,
      costRange: {
        min: Math.min(...comparisons.map(c => c.totalCost)),
        max: Math.max(...comparisons.map(c => c.totalCost))
      },
      averageCostByProvider: avgCostByProvider,
      generatedAt: new Date().toISOString()
    };
  }

  calculateTaxes(cost, region) {
    // Simplified tax calculation based on region
    const taxRates = {
      'aws-us-east-1': 0.0, // No tax for AWS US regions
      'aws-eu-west-1': 0.21, // EU VAT
      'gcp-us-central1': 0.0,
      'gcp-europe-west1': 0.21,
      'azure-eastus': 0.0,
      'azure-westeurope': 0.21
    };
    
    const taxRate = taxRates[region] || 0;
    return Math.round(cost * taxRate * 100) / 100;
  }

  async compareInstanceTypes(baseInstanceType, provider, region, targetProviders = []) {
    const comparisons = [];
    const providers = targetProviders.length > 0 ? targetProviders : ['aws', 'gcp', 'azure'];
    
    // Get equivalent instance types across providers
    const equivalents = this.getEquivalentInstanceTypes(baseInstanceType, provider);
    
    for (const targetProvider of providers) {
      const equivalentTypes = equivalents[targetProvider] || [];
      
      for (const instanceType of equivalentTypes) {
        try {
          const price = await this.getInstancePrice(instanceType, targetProvider, region);
          comparisons.push({
            provider: targetProvider,
            instanceType,
            hourlyPrice: price,
            monthlyCost: price * 730,
            specifications: this.getInstanceSpecifications(instanceType, targetProvider)
          });
        } catch (error) {
          console.warn(`Failed to get price for ${instanceType} on ${targetProvider}: ${error.message}`);
        }
      }
    }
    
    return comparisons.sort((a, b) => a.hourlyPrice - b.hourlyPrice);
  }

  getEquivalentInstanceTypes(instanceType, sourceProvider) {
    // Simplified equivalent mapping
    const equivalents = {
      't3.small': {
        aws: ['t3.small', 't3a.small'],
        gcp: ['e2-small', 'n1-standard-1'],
        azure: ['B1S', 'D2s_v3']
      },
      't3.medium': {
        aws: ['t3.medium', 't3a.medium'],
        gcp: ['e2-medium', 'n1-standard-2'],
        azure: ['B1MS', 'D2s_v3']
      },
      'e2-small': {
        aws: ['t3.small', 't3.nano'],
        gcp: ['e2-small', 'e2-micro'],
        azure: ['B1S']
      }
    };
    
    return equivalents[instanceType] || { aws: [instanceType], gcp: [instanceType], azure: [instanceType] };
  }

  getInstanceSpecifications(instanceType, provider) {
    // Simplified specifications mapping
    const specs = {
      aws: {
        't3.small': { vcpu: 2, memory: 2, network: 'Up to 5 Gbps' },
        't3.medium': { vcpu: 2, memory: 4, network: 'Up to 5 Gbps' }
      },
      gcp: {
        'e2-small': { vcpu: 2, memory: 2, network: '4 Gbps' },
        'e2-medium': { vcpu: 2, memory: 4, network: '4 Gbps' }
      },
      azure: {
        'B1S': { vcpu: 1, memory: 1, network: '750 Mbps' },
        'B1MS': { vcpu: 1, memory: 2, network: '750 Mbps' }
      }
    };
    
    return specs[provider]?.[instanceType] || { vcpu: 'N/A', memory: 'N/A', network: 'N/A' };
  }

  exportComparison(comparison, format = 'json') {
    if (format === 'json') {
      return JSON.stringify(comparison, null, 2);
    } else if (format === 'csv') {
      return this.convertComparisonToCSV(comparison);
    }
    
    return comparison;
  }

  convertComparisonToCSV(comparison) {
    const lines = ['provider,region,total_cost,compute_cost,storage_cost,network_cost,savings_vs_cheapest'];
    
    comparison.comparisons.forEach(comp => {
      lines.push([
        comp.provider,
        comp.region,
        comp.totalCost,
        comp.breakdown.compute?.total || 0,
        comp.breakdown.storage?.total || 0,
        comp.breakdown.network?.total || 0,
        comp.savingsVsCheapest?.amount || 0
      ].join(','));
    });
    
    return lines.join('\n');
  }

  clearCache() {
    this.pricingCache.clear();
  }

  getCacheStats() {
    return {
      size: this.pricingCache.size,
      providers: this.providers.size,
      regions: this.regions.size,
      lastCleared: new Date().toISOString()
    };
  }
}

module.exports = MultiCloudComparator;