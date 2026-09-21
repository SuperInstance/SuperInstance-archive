const Maker = require('../models/Maker');
const logger = require('../config/logger');
const redis = require('../config/redis');
const { getDistance, getCenter, isPointWithinRadius } = require('geolib');

class ProximityMatchingService {
  constructor() {
    this.defaultRadius = 100; // 100km default search radius
    this.maxRadius = 1000; // 1000km maximum search radius
    this.minMakersTarget = 5; // Try to find at least 5 makers
    this.maxMakersReturn = 20; // Return maximum 20 makers
    this.cacheTimeout = 3600; // Cache maker locations for 1 hour
  }

  /**
   * Find makers within proximity of customer location
   */
  async findMakersNearCustomer(customerLocation, orderSpecs, options = {}) {
    try {
      const {
        radius = this.defaultRadius,
        maxMakers = this.maxMakersReturn,
        minQuality = 3.0,
        urgentOnly = false
      } = options;

      logger.logBusinessEvent('proximity_matching_started', {
        customerLocation: `${customerLocation.latitude},${customerLocation.longitude}`,
        radius,
        material: orderSpecs.material.type
      });

      // First, try exact radius search
      let makers = await this.searchMakersInRadius(customerLocation, radius, orderSpecs);
      
      // If not enough makers found, expand search
      if (makers.length < this.minMakersTarget && radius < this.maxRadius) {
        makers = await this.expandSearch(customerLocation, orderSpecs, makers.length);
      }

      // Filter makers based on capability and quality
      const filteredMakers = await this.filterMakersByCapability(makers, orderSpecs, {
        minQuality,
        urgentOnly
      });

      // Rank makers by proximity and other factors
      const rankedMakers = this.rankMakers(filteredMakers, customerLocation, orderSpecs);

      // Limit results
      const finalMakers = rankedMakers.slice(0, maxMakers);

      logger.logBusinessEvent('proximity_matching_completed', {
        makersFound: finalMakers.length,
        averageDistance: this.calculateAverageDistance(finalMakers),
        searchRadius: radius
      });

      return {
        makers: finalMakers,
        searchRadius: radius,
        totalFound: makers.length,
        filteredCount: filteredMakers.length,
        centerPoint: customerLocation,
        searchStats: {
          averageDistance: this.calculateAverageDistance(finalMakers),
          maxDistance: Math.max(...finalMakers.map(m => m.distance)),
          minDistance: Math.min(...finalMakers.map(m => m.distance))
        }
      };
    } catch (error) {
      logger.error('Error in proximity matching:', error);
      throw error;
    }
  }

  /**
   * Search for makers within a specific radius
   */
  async searchMakersInRadius(centerPoint, radiusKm, orderSpecs) {
    try {
      // Use MongoDB geospatial query for initial filtering
      const query = {
        'location.coordinates': {
          $near: {
            $geometry: {
              type: 'Point',
              coordinates: [centerPoint.longitude, centerPoint.latitude]
            },
            $maxDistance: radiusKm * 1000 // Convert km to meters
          }
        },
        'verification.status': 'verified',
        'capacity.availability.acceptingOrders': true,
        'capabilities.materials.type': orderSpecs.material.type,
        'capabilities.materials.inStock': true
      };

      // Add urgency filter if rush order
      if (orderSpecs.requirements.urgency === 'rush') {
        query['pricing.rushPricing.available'] = true;
        query['capacity.availability.status'] = 'available';
      }

      const makers = await Maker.find(query).limit(50); // Initial limit

      // Calculate exact distances and add proximity data
      const makersWithDistance = makers.map(maker => {
        const distance = getDistance(
          centerPoint,
          {
            latitude: maker.location.coordinates.latitude,
            longitude: maker.location.coordinates.longitude
          }
        ) / 1000; // Convert to km

        return {
          ...maker.toObject(),
          distance: Math.round(distance * 100) / 100,
          proximityScore: this.calculateProximityScore(distance, maker)
        };
      });

      return makersWithDistance.filter(maker => maker.distance <= radiusKm);
    } catch (error) {
      logger.error('Error searching makers in radius:', error);
      throw error;
    }
  }

  /**
   * Expand search radius if not enough makers found
   */
  async expandSearch(centerPoint, orderSpecs, currentCount) {
    let expandedMakers = [];
    let currentRadius = this.defaultRadius;
    
    while (expandedMakers.length < this.minMakersTarget && currentRadius <= this.maxRadius) {
      currentRadius += 100; // Expand by 100km each time
      
      logger.debug(`Expanding search radius to ${currentRadius}km`);
      
      expandedMakers = await this.searchMakersInRadius(centerPoint, currentRadius, orderSpecs);
      
      // Break if we've reached a reasonable number or maximum radius
      if (expandedMakers.length >= 10 || currentRadius >= this.maxRadius) {
        break;
      }
    }

    return expandedMakers;
  }

  /**
   * Filter makers by their capability to handle the order
   */
  async filterMakersByCapability(makers, orderSpecs, filters = {}) {
    const { minQuality = 3.0, urgentOnly = false } = filters;
    
    const filteredMakers = [];

    for (const maker of makers) {
      // Quality filter
      if (maker.performance.ratings.overall < minQuality) {
        continue;
      }

      // Urgent order filter
      if (urgentOnly && !maker.pricing.rushPricing.available) {
        continue;
      }

      // Check if maker can handle the specific order requirements
      if (!this.canMakerHandleOrder(maker, orderSpecs)) {
        continue;
      }

      // Check availability
      if (!this.isMakerAvailable(maker, orderSpecs)) {
        continue;
      }

      // Add capability scores
      maker.capabilityScore = this.calculateCapabilityScore(maker, orderSpecs);
      maker.availabilityScore = this.calculateAvailabilityScore(maker, orderSpecs);
      
      filteredMakers.push(maker);
    }

    return filteredMakers;
  }

  /**
   * Check if maker can handle specific order requirements
   */
  canMakerHandleOrder(maker, orderSpecs) {
    // Check dimensions
    const dimensions = orderSpecs.dimensions;
    const maxDims = maker.capabilities.printSpecs.maxDimensions;
    
    if (dimensions.length > maxDims.x || 
        dimensions.width > maxDims.y || 
        dimensions.height > maxDims.z) {
      return false;
    }

    // Check material availability
    const hasMaterial = maker.capabilities.materials.some(material => 
      material.type === orderSpecs.material.type && 
      material.inStock &&
      (!orderSpecs.material.color || material.colors.includes(orderSpecs.material.color))
    );

    if (!hasMaterial) {
      return false;
    }

    // Check post-processing capabilities
    const requiredProcessing = orderSpecs.requirements.postProcessing || [];
    const availableProcessing = maker.capabilities.postProcessing
      .filter(p => p.available)
      .map(p => p.service);

    const canDoPostProcessing = requiredProcessing.every(required => 
      availableProcessing.includes(required)
    );

    if (!canDoPostProcessing) {
      return false;
    }

    // Check quality capabilities
    const requiredLayerHeight = orderSpecs.quality.layerHeight;
    if (requiredLayerHeight < maker.capabilities.printSpecs.minLayerHeight ||
        requiredLayerHeight > maker.capabilities.printSpecs.maxLayerHeight) {
      return false;
    }

    return true;
  }

  /**
   * Check maker availability for the order timing
   */
  isMakerAvailable(maker, orderSpecs) {
    // Check overall availability status
    if (maker.capacity.availability.status !== 'available') {
      return false;
    }

    // Check vacation mode
    if (maker.capacity.availability.vacationMode.active) {
      const now = new Date();
      const vacationStart = new Date(maker.capacity.availability.vacationMode.startDate);
      const vacationEnd = new Date(maker.capacity.availability.vacationMode.endDate);
      
      if (now >= vacationStart && now <= vacationEnd) {
        return false;
      }
    }

    // Check rush availability for urgent orders
    if (orderSpecs.requirements.urgency === 'rush') {
      if (!maker.pricing.rushPricing.available) {
        return false;
      }
      
      // Check rush capacity
      const currentRushOrders = maker.capacity.availability.queueLength; // Simplified
      if (currentRushOrders >= maker.pricing.rushPricing.maxRushOrders) {
        return false;
      }
    }

    // Check queue capacity
    const maxQueue = maker.capacity.metrics.maxConcurrentJobs * 3; // Allow 3x queue
    if (maker.capacity.availability.queueLength >= maxQueue) {
      return false;
    }

    return true;
  }

  /**
   * Calculate proximity score based on distance and maker quality
   */
  calculateProximityScore(distance, maker) {
    // Base score decreases with distance
    let score = Math.max(0, 100 - (distance / 10)); // Decrease 10 points per 10km
    
    // Bonus for high quality makers
    const qualityBonus = (maker.performance.ratings.overall - 3) * 10; // 10 points per star above 3
    score += Math.max(0, qualityBonus);
    
    // Bonus for low queue
    const queuePenalty = maker.capacity.availability.queueLength * 2;
    score -= queuePenalty;
    
    // Bonus for experience
    const experienceBonus = Math.min(maker.performance.statistics.totalOrders / 10, 20);
    score += experienceBonus;

    return Math.max(0, Math.min(100, score));
  }

  /**
   * Calculate capability score for how well maker matches order requirements
   */
  calculateCapabilityScore(maker, orderSpecs) {
    let score = 70; // Base score

    // Material expertise bonus
    const materialExperience = maker.capabilities.materials.find(m => m.type === orderSpecs.material.type);
    if (materialExperience) {
      score += 10;
      if (materialExperience.brands && materialExperience.brands.length > 3) {
        score += 5; // Multiple brands available
      }
    }

    // Technology match bonus
    const requiredTech = this.inferRequiredTechnology(orderSpecs);
    const hasTech = maker.capabilities.technologies.some(t => t.type === requiredTech);
    if (hasTech) {
      score += 10;
      
      const techExperience = maker.capabilities.technologies.find(t => t.type === requiredTech);
      if (techExperience && techExperience.experience === 'expert') {
        score += 5;
      }
    }

    // Post-processing capabilities
    const requiredProcessing = orderSpecs.requirements.postProcessing || [];
    const availableProcessing = maker.capabilities.postProcessing.filter(p => p.available);
    
    if (requiredProcessing.length > 0) {
      const matchingProcessing = requiredProcessing.filter(req => 
        availableProcessing.some(avail => avail.service === req)
      );
      score += (matchingProcessing.length / requiredProcessing.length) * 15;
    }

    // Size handling capability
    const orderVolume = orderSpecs.dimensions.volume || 0;
    const maxVolume = maker.capabilities.printSpecs.maxDimensions.x * 
                     maker.capabilities.printSpecs.maxDimensions.y * 
                     maker.capabilities.printSpecs.maxDimensions.z;
    
    if (orderVolume / maxVolume < 0.8) { // Order uses less than 80% of capacity
      score += 5;
    }

    // Quality standards bonus
    if (orderSpecs.requirements.finishQuality === 'premium') {
      const hasQualityStandards = maker.capabilities.qualityStandards.some(q => q.certified);
      if (hasQualityStandards) {
        score += 10;
      }
    }

    return Math.max(0, Math.min(100, score));
  }

  /**
   * Calculate availability score based on timing and capacity
   */
  calculateAvailabilityScore(maker, orderSpecs) {
    let score = 50; // Base score

    // Queue length impact
    const queueLength = maker.capacity.availability.queueLength;
    score -= queueLength * 5; // Penalty for queue

    // Rush availability bonus
    if (orderSpecs.requirements.urgency === 'rush' && maker.pricing.rushPricing.available) {
      score += 20;
    }

    // Capacity utilization factor
    const utilization = maker.capacity.metrics.currentUtilization || 0;
    if (utilization < 70) {
      score += 15; // Bonus for available capacity
    } else if (utilization > 90) {
      score -= 10; // Penalty for high utilization
    }

    // Time zone alignment (if business hours matter)
    const customerTz = this.inferTimezone(orderSpecs);
    const makerTz = maker.contact.timezone;
    if (customerTz && makerTz && Math.abs(customerTz - makerTz) <= 2) {
      score += 5; // Bonus for similar time zones
    }

    return Math.max(0, Math.min(100, score));
  }

  /**
   * Rank makers by combining multiple scores
   */
  rankMakers(makers, customerLocation, orderSpecs) {
    return makers.map(maker => {
      // Calculate combined score
      const proximityWeight = 0.4;
      const capabilityWeight = 0.35;
      const availabilityWeight = 0.15;
      const ratingWeight = 0.1;

      const combinedScore = 
        (maker.proximityScore * proximityWeight) +
        (maker.capabilityScore * capabilityWeight) +
        (maker.availabilityScore * availabilityWeight) +
        (maker.performance.ratings.overall * 20 * ratingWeight); // Convert 5-star to 100-point scale

      maker.combinedScore = Math.round(combinedScore * 100) / 100;
      
      return maker;
    }).sort((a, b) => b.combinedScore - a.combinedScore);
  }

  /**
   * Find optimal service areas for new makers
   */
  async findOptimalServiceAreas(makerLocation, capabilities) {
    try {
      // Analyze demand density around maker location
      const demandAnalysis = await this.analyzeDemandDensity(makerLocation, capabilities);
      
      // Find underserved areas within reasonable distance
      const underservedAreas = await this.findUnderservedAreas(makerLocation, capabilities);
      
      // Calculate optimal radius based on competition and demand
      const optimalRadius = this.calculateOptimalServiceRadius(
        makerLocation, 
        demandAnalysis, 
        underservedAreas
      );

      return {
        recommendedRadius: optimalRadius,
        demandAnalysis,
        underservedAreas,
        competitionLevel: demandAnalysis.competitionLevel,
        potentialCustomers: demandAnalysis.potentialCustomers
      };
    } catch (error) {
      logger.error('Error finding optimal service areas:', error);
      throw error;
    }
  }

  /**
   * Analyze demand density around a location
   */
  async analyzeDemandDensity(centerPoint, capabilities, radiusKm = 100) {
    // This would analyze historical orders in the area
    // For now, return a simplified analysis
    
    const nearbyCompetitors = await this.searchMakersInRadius(
      centerPoint, 
      radiusKm, 
      { material: { type: capabilities.materials[0] } }
    );

    return {
      competitionLevel: nearbyCompetitors.length > 10 ? 'high' : 
                       nearbyCompetitors.length > 5 ? 'medium' : 'low',
      competitorCount: nearbyCompetitors.length,
      potentialCustomers: Math.max(0, 100 - nearbyCompetitors.length * 5), // Simplified
      recommendedFocus: this.getRecommendedFocus(capabilities, nearbyCompetitors)
    };
  }

  /**
   * Find underserved areas within maker's potential service range
   */
  async findUnderservedAreas(makerLocation, capabilities) {
    // Simplified implementation - in reality would use more complex analysis
    const underservedAreas = [];
    
    // Check major cities within range
    const majorCities = [
      { name: 'Downtown', coords: { latitude: makerLocation.latitude + 0.1, longitude: makerLocation.longitude + 0.1 }},
      { name: 'Suburbs', coords: { latitude: makerLocation.latitude - 0.1, longitude: makerLocation.longitude - 0.1 }},
      { name: 'Tech District', coords: { latitude: makerLocation.latitude + 0.05, longitude: makerLocation.longitude - 0.05 }}
    ];

    for (const city of majorCities) {
      const nearby = await this.searchMakersInRadius(
        city.coords, 
        25, // 25km radius around city
        { material: { type: capabilities.materials[0] } }
      );

      if (nearby.length < 3) { // Less than 3 makers = underserved
        underservedAreas.push({
          name: city.name,
          location: city.coords,
          currentMakers: nearby.length,
          opportunity: 'high'
        });
      }
    }

    return underservedAreas;
  }

  /**
   * Calculate optimal service radius for a maker
   */
  calculateOptimalServiceRadius(makerLocation, demandAnalysis, underservedAreas) {
    let baseRadius = 50; // 50km base radius

    // Adjust based on competition
    if (demandAnalysis.competitionLevel === 'low') {
      baseRadius += 30; // Can serve wider area
    } else if (demandAnalysis.competitionLevel === 'high') {
      baseRadius -= 20; // Focus on closer area
    }

    // Adjust based on underserved areas
    if (underservedAreas.length > 0) {
      const maxDistance = Math.max(...underservedAreas.map(area => 
        getDistance(makerLocation, area.location) / 1000
      ));
      baseRadius = Math.max(baseRadius, maxDistance + 10);
    }

    // Cap at reasonable maximum
    return Math.min(baseRadius, 150);
  }

  /**
   * Get maker density in an area
   */
  async getMakerDensity(centerPoint, radiusKm = 50) {
    try {
      const cacheKey = `maker_density:${centerPoint.latitude}:${centerPoint.longitude}:${radiusKm}`;
      const cached = await redis.get(cacheKey);
      
      if (cached) {
        return JSON.parse(cached);
      }

      const totalMakers = await Maker.countDocuments({
        'location.coordinates': {
          $near: {
            $geometry: {
              type: 'Point',
              coordinates: [centerPoint.longitude, centerPoint.latitude]
            },
            $maxDistance: radiusKm * 1000
          }
        },
        'verification.status': 'verified'
      });

      const area = Math.PI * radiusKm * radiusKm; // km²
      const density = totalMakers / area;

      const result = {
        totalMakers,
        area,
        density: Math.round(density * 10000) / 10000, // Round to 4 decimal places
        level: density > 0.1 ? 'high' : density > 0.05 ? 'medium' : 'low'
      };

      await redis.set(cacheKey, JSON.stringify(result), this.cacheTimeout);
      
      return result;
    } catch (error) {
      logger.error('Error calculating maker density:', error);
      throw error;
    }
  }

  /**
   * Utility functions
   */
  calculateAverageDistance(makers) {
    if (makers.length === 0) return 0;
    const total = makers.reduce((sum, maker) => sum + maker.distance, 0);
    return Math.round((total / makers.length) * 100) / 100;
  }

  inferRequiredTechnology(orderSpecs) {
    // Simple technology inference based on material and quality
    const material = orderSpecs.material.type;
    const layerHeight = orderSpecs.quality.layerHeight;
    
    if (['Resin'].includes(material)) return 'SLA';
    if (layerHeight < 0.15) return 'SLA'; // High resolution usually requires SLA
    if (['Nylon', 'Metal'].includes(material)) return 'SLS';
    
    return 'FDM'; // Default to FDM
  }

  inferTimezone(orderSpecs) {
    // Simplified timezone inference - would use actual geolocation
    return 0; // UTC for now
  }

  getRecommendedFocus(capabilities, competitors) {
    // Analyze what competitors are missing and recommend focus areas
    const focusAreas = [];
    
    // Check material gaps
    const competitorMaterials = new Set();
    competitors.forEach(comp => {
      comp.capabilities.materials.forEach(mat => competitorMaterials.add(mat.type));
    });

    capabilities.materials.forEach(material => {
      if (!competitorMaterials.has(material)) {
        focusAreas.push(`Specialize in ${material} - low competition`);
      }
    });

    if (focusAreas.length === 0) {
      focusAreas.push('Focus on premium quality and fast delivery');
    }

    return focusAreas;
  }
}

module.exports = new ProximityMatchingService();