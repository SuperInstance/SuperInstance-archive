import EventEmitter from 'events';
import axios from 'axios';
import cheerio from 'cheerio';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default class PriceComparisonEngine extends EventEmitter {
    constructor(logger) {
        super();
        this.logger = logger;
        this.vendors = new Map();
        this.priceHistory = new Map();
        this.alertThresholds = new Map();
        this.scrapeConfigs = new Map();
        this.cacheTimeout = 15 * 60 * 1000; // 15 minutes
        this.priceCache = new Map();
        this.comparisonAlgorithms = new Map();
        this.marketTrends = new Map();
        this.pricingStrategies = new Map();
        
        this.initializeVendors();
        this.initializeComparisonAlgorithms();
        this.initializePricingStrategies();
    }

    async initializeVendors() {
        try {
            const vendorsPath = path.join(__dirname, '../data/vendors.json');
            const vendorsData = await fs.readFile(vendorsPath, 'utf8');
            const vendors = JSON.parse(vendorsData);
            
            for (const vendor of vendors) {
                this.vendors.set(vendor.id, vendor);
                if (vendor.scrape_config) {
                    this.scrapeConfigs.set(vendor.id, vendor.scrape_config);
                }
            }
            
            this.logger.info(`Loaded ${this.vendors.size} vendors for price comparison`);
        } catch (error) {
            this.logger.warn('Could not load vendors file, using defaults');
            this.loadDefaultVendors();
        }
    }

    loadDefaultVendors() {
        const defaultVendors = [
            {
                id: 'vendor_a',
                name: 'TechParts Direct',
                api_endpoint: 'https://api.techparts.com/v1/pricing',
                api_key: process.env.TECHPARTS_API_KEY,
                markup_percentage: 5,
                shipping_cost: 15.99,
                processing_time: '2-3 days',
                reliability_score: 0.92,
                bulk_discount_tiers: [
                    { min_quantity: 10, discount: 0.05 },
                    { min_quantity: 50, discount: 0.10 },
                    { min_quantity: 100, discount: 0.15 }
                ]
            },
            {
                id: 'vendor_b',
                name: 'Component Central',
                api_endpoint: 'https://api.componentcentral.com/prices',
                api_key: process.env.COMPONENT_API_KEY,
                markup_percentage: 8,
                shipping_cost: 12.50,
                processing_time: '1-2 days',
                reliability_score: 0.89,
                bulk_discount_tiers: [
                    { min_quantity: 25, discount: 0.08 },
                    { min_quantity: 100, discount: 0.12 }
                ]
            },
            {
                id: 'vendor_c',
                name: 'ElectroSupply Co',
                website_url: 'https://electrosupply.com',
                scrape_config: {
                    search_url: 'https://electrosupply.com/search?q={{part_number}}',
                    price_selector: '.price-current',
                    availability_selector: '.stock-status',
                    shipping_selector: '.shipping-cost'
                },
                markup_percentage: 12,
                shipping_cost: 8.99,
                processing_time: '3-5 days',
                reliability_score: 0.85
            }
        ];

        defaultVendors.forEach(vendor => {
            this.vendors.set(vendor.id, vendor);
            if (vendor.scrape_config) {
                this.scrapeConfigs.set(vendor.id, vendor.scrape_config);
            }
        });
    }

    initializeComparisonAlgorithms() {
        this.comparisonAlgorithms.set('total_cost', (prices) => {
            return prices.map(p => ({
                ...p,
                total_cost: p.unit_price + (p.shipping_cost || 0) + (p.handling_fee || 0),
                score: this.calculateTotalCostScore(p)
            })).sort((a, b) => a.total_cost - b.total_cost);
        });

        this.comparisonAlgorithms.set('value_score', (prices) => {
            return prices.map(p => ({
                ...p,
                value_score: this.calculateValueScore(p)
            })).sort((a, b) => b.value_score - a.value_score);
        });

        this.comparisonAlgorithms.set('delivery_time', (prices) => {
            return prices.map(p => ({
                ...p,
                delivery_score: this.calculateDeliveryScore(p)
            })).sort((a, b) => b.delivery_score - a.delivery_score);
        });

        this.comparisonAlgorithms.set('reliability', (prices) => {
            return prices.map(p => ({
                ...p,
                reliability_score: this.calculateReliabilityScore(p)
            })).sort((a, b) => b.reliability_score - a.reliability_score);
        });
    }

    initializePricingStrategies() {
        this.pricingStrategies.set('aggressive', {
            weight_price: 0.7,
            weight_delivery: 0.1,
            weight_reliability: 0.2,
            description: 'Prioritize lowest price'
        });

        this.pricingStrategies.set('balanced', {
            weight_price: 0.4,
            weight_delivery: 0.3,
            weight_reliability: 0.3,
            description: 'Balance price, delivery, and reliability'
        });

        this.pricingStrategies.set('premium', {
            weight_price: 0.2,
            weight_delivery: 0.4,
            weight_reliability: 0.4,
            description: 'Prioritize quality and speed'
        });

        this.pricingStrategies.set('bulk_optimized', {
            weight_price: 0.5,
            weight_delivery: 0.2,
            weight_reliability: 0.2,
            weight_bulk_discount: 0.1,
            description: 'Optimize for bulk purchases'
        });
    }

    async comparePrices(partNumber, quantity = 1, options = {}) {
        try {
            const cacheKey = `${partNumber}-${quantity}`;
            
            // Check cache first
            if (this.priceCache.has(cacheKey)) {
                const cached = this.priceCache.get(cacheKey);
                if (Date.now() - cached.timestamp < this.cacheTimeout) {
                    this.logger.debug(`Using cached prices for ${partNumber}`);
                    return this.processComparison(cached.prices, options);
                }
            }

            const prices = await this.fetchAllPrices(partNumber, quantity, options);
            
            // Cache the results
            this.priceCache.set(cacheKey, {
                prices,
                timestamp: Date.now()
            });

            // Update price history
            this.updatePriceHistory(partNumber, prices);

            // Check for price alerts
            this.checkPriceAlerts(partNumber, prices);

            const comparison = this.processComparison(prices, options);

            this.emit('price_comparison', {
                part_number: partNumber,
                quantity,
                comparison,
                options
            });

            this.logger.info(`Price comparison completed for ${partNumber}: ${prices.length} vendors`);
            
            return comparison;

        } catch (error) {
            this.logger.error('Price comparison failed:', error);
            throw error;
        }
    }

    async fetchAllPrices(partNumber, quantity, options) {
        const pricePromises = [];
        
        for (const [vendorId, vendor] of this.vendors) {
            if (options.exclude_vendors && options.exclude_vendors.includes(vendorId)) {
                continue;
            }

            if (vendor.api_endpoint) {
                pricePromises.push(this.fetchApiPrice(vendor, partNumber, quantity));
            } else if (vendor.website_url) {
                pricePromises.push(this.scrapePriceData(vendor, partNumber, quantity));
            }
        }

        const results = await Promise.allSettled(pricePromises);
        const prices = results
            .filter(result => result.status === 'fulfilled' && result.value)
            .map(result => result.value);

        return prices;
    }

    async fetchApiPrice(vendor, partNumber, quantity) {
        try {
            const response = await axios.get(vendor.api_endpoint, {
                params: {
                    part_number: partNumber,
                    quantity: quantity,
                    api_key: vendor.api_key
                },
                timeout: 10000
            });

            if (response.data && response.data.price) {
                return this.formatPriceData(vendor, response.data, quantity);
            }

            return null;
        } catch (error) {
            this.logger.warn(`API price fetch failed for ${vendor.name}:`, error.message);
            return null;
        }
    }

    async scrapePriceData(vendor, partNumber, quantity) {
        try {
            const scrapeConfig = this.scrapeConfigs.get(vendor.id);
            if (!scrapeConfig) return null;

            const searchUrl = scrapeConfig.search_url.replace('{{part_number}}', encodeURIComponent(partNumber));
            
            const response = await axios.get(searchUrl, {
                headers: {
                    'User-Agent': 'Mozilla/5.0 (compatible; ActiveLog Price Comparison Bot)'
                },
                timeout: 15000
            });

            const $ = cheerio.load(response.data);
            
            const priceElement = $(scrapeConfig.price_selector).first();
            const availabilityElement = $(scrapeConfig.availability_selector).first();
            const shippingElement = $(scrapeConfig.shipping_selector).first();

            if (!priceElement.length) return null;

            const priceText = priceElement.text().trim();
            const price = parseFloat(priceText.replace(/[^0-9.]/g, ''));

            if (isNaN(price)) return null;

            const availability = availabilityElement.text().trim();
            const shippingText = shippingElement.text().trim();
            const shippingCost = parseFloat(shippingText.replace(/[^0-9.]/g, '')) || vendor.shipping_cost;

            return this.formatPriceData(vendor, {
                price,
                availability,
                shipping_cost: shippingCost
            }, quantity);

        } catch (error) {
            this.logger.warn(`Web scraping failed for ${vendor.name}:`, error.message);
            return null;
        }
    }

    formatPriceData(vendor, data, quantity) {
        const unitPrice = data.price || data.unit_price;
        const basePrice = unitPrice * quantity;
        
        // Apply bulk discounts
        const discount = this.calculateBulkDiscount(vendor, quantity);
        const discountedPrice = basePrice * (1 - discount);
        
        return {
            vendor_id: vendor.id,
            vendor_name: vendor.name,
            part_number: data.part_number,
            unit_price: unitPrice,
            quantity: quantity,
            base_price: basePrice,
            bulk_discount: discount,
            discounted_price: discountedPrice,
            shipping_cost: data.shipping_cost || vendor.shipping_cost || 0,
            handling_fee: data.handling_fee || 0,
            tax_rate: data.tax_rate || 0,
            total_cost: discountedPrice + (data.shipping_cost || vendor.shipping_cost || 0),
            availability: data.availability || 'In Stock',
            lead_time: data.lead_time || vendor.processing_time,
            currency: data.currency || 'USD',
            valid_until: data.valid_until || new Date(Date.now() + 24 * 60 * 60 * 1000),
            reliability_score: vendor.reliability_score || 0.8,
            last_updated: new Date(),
            conditions: data.conditions || [],
            warranty: data.warranty || vendor.warranty,
            return_policy: data.return_policy || vendor.return_policy
        };
    }

    calculateBulkDiscount(vendor, quantity) {
        if (!vendor.bulk_discount_tiers) return 0;

        let applicableDiscount = 0;
        for (const tier of vendor.bulk_discount_tiers) {
            if (quantity >= tier.min_quantity) {
                applicableDiscount = Math.max(applicableDiscount, tier.discount);
            }
        }

        return applicableDiscount;
    }

    processComparison(prices, options) {
        if (prices.length === 0) {
            return {
                error: 'No prices found',
                recommendations: []
            };
        }

        const strategy = options.strategy || 'balanced';
        const algorithm = options.algorithm || 'value_score';

        // Apply comparison algorithm
        let processedPrices = prices;
        if (this.comparisonAlgorithms.has(algorithm)) {
            processedPrices = this.comparisonAlgorithms.get(algorithm)(prices);
        }

        // Calculate strategic scores
        processedPrices = this.applyPricingStrategy(processedPrices, strategy);

        // Generate recommendations
        const recommendations = this.generateRecommendations(processedPrices, options);

        // Calculate savings analysis
        const savings = this.calculateSavingsAnalysis(processedPrices);

        // Market analysis
        const marketAnalysis = this.performMarketAnalysis(processedPrices);

        return {
            strategy,
            algorithm,
            total_vendors: processedPrices.length,
            price_range: {
                lowest: Math.min(...processedPrices.map(p => p.total_cost)),
                highest: Math.max(...processedPrices.map(p => p.total_cost)),
                average: processedPrices.reduce((sum, p) => sum + p.total_cost, 0) / processedPrices.length
            },
            recommendations,
            all_prices: processedPrices,
            savings_analysis: savings,
            market_analysis: marketAnalysis,
            last_updated: new Date()
        };
    }

    calculateTotalCostScore(price) {
        // Lower total cost gets higher score
        const maxCost = 10000; // Arbitrary max for normalization
        return Math.max(0, 1 - (price.total_cost / maxCost));
    }

    calculateValueScore(price) {
        const priceScore = this.calculateTotalCostScore(price);
        const reliabilityScore = price.reliability_score || 0.8;
        const deliveryScore = this.calculateDeliveryScore(price);
        
        // Weighted combination
        return (priceScore * 0.4) + (reliabilityScore * 0.3) + (deliveryScore * 0.3);
    }

    calculateDeliveryScore(price) {
        const leadTime = price.lead_time;
        if (!leadTime) return 0.5;
        
        // Parse lead time (e.g., "2-3 days", "1 week")
        const days = this.parseLeadTimeToDays(leadTime);
        
        // Faster delivery gets higher score (inverse relationship)
        return Math.max(0, 1 - (days / 30)); // 30 days max
    }

    calculateReliabilityScore(price) {
        return price.reliability_score || 0.8;
    }

    parseLeadTimeToDays(leadTime) {
        if (!leadTime) return 7; // Default to 1 week
        
        const text = leadTime.toLowerCase();
        
        if (text.includes('same day') || text.includes('today')) return 0.5;
        if (text.includes('next day') || text.includes('1 day')) return 1;
        if (text.includes('2 days') || text.includes('2-3 days')) return 2.5;
        if (text.includes('3-5 days')) return 4;
        if (text.includes('1 week')) return 7;
        if (text.includes('2 weeks')) return 14;
        if (text.includes('1 month')) return 30;
        
        // Try to extract numbers
        const numbers = text.match(/\d+/g);
        if (numbers) {
            const num = parseInt(numbers[0]);
            if (text.includes('week')) return num * 7;
            if (text.includes('month')) return num * 30;
            return num; // Assume days
        }
        
        return 7; // Default
    }

    applyPricingStrategy(prices, strategy) {
        const strategyConfig = this.pricingStrategies.get(strategy);
        if (!strategyConfig) return prices;

        return prices.map(price => {
            let strategicScore = 0;
            
            // Price weight (inverse - lower price = higher score)
            const priceScore = this.calculateTotalCostScore(price);
            strategicScore += priceScore * strategyConfig.weight_price;
            
            // Delivery weight
            const deliveryScore = this.calculateDeliveryScore(price);
            strategicScore += deliveryScore * strategyConfig.weight_delivery;
            
            // Reliability weight
            const reliabilityScore = price.reliability_score || 0.8;
            strategicScore += reliabilityScore * strategyConfig.weight_reliability;
            
            // Bulk discount weight (if applicable)
            if (strategyConfig.weight_bulk_discount) {
                const bulkScore = price.bulk_discount || 0;
                strategicScore += bulkScore * strategyConfig.weight_bulk_discount;
            }

            return {
                ...price,
                strategic_score: strategicScore,
                strategy_used: strategy
            };
        }).sort((a, b) => b.strategic_score - a.strategic_score);
    }

    generateRecommendations(prices, options) {
        const recommendations = [];

        if (prices.length === 0) return recommendations;

        // Best overall value
        const bestValue = prices[0];
        recommendations.push({
            type: 'best_value',
            vendor: bestValue.vendor_name,
            price: bestValue,
            reason: `Best overall value with strategic score of ${bestValue.strategic_score?.toFixed(2)}`,
            confidence: 0.9
        });

        // Lowest price
        const lowestPrice = prices.reduce((min, p) => 
            p.total_cost < min.total_cost ? p : min
        );
        if (lowestPrice.vendor_id !== bestValue.vendor_id) {
            recommendations.push({
                type: 'lowest_price',
                vendor: lowestPrice.vendor_name,
                price: lowestPrice,
                reason: `Lowest total cost at $${lowestPrice.total_cost.toFixed(2)}`,
                savings: bestValue.total_cost - lowestPrice.total_cost,
                confidence: 0.95
            });
        }

        // Fastest delivery
        const fastestDelivery = prices.reduce((fastest, p) => {
            const currentDays = this.parseLeadTimeToDays(p.lead_time);
            const fastestDays = this.parseLeadTimeToDays(fastest.lead_time);
            return currentDays < fastestDays ? p : fastest;
        });
        if (fastestDelivery.vendor_id !== bestValue.vendor_id) {
            recommendations.push({
                type: 'fastest_delivery',
                vendor: fastestDelivery.vendor_name,
                price: fastestDelivery,
                reason: `Fastest delivery time: ${fastestDelivery.lead_time}`,
                confidence: 0.85
            });
        }

        // Most reliable
        const mostReliable = prices.reduce((reliable, p) => 
            (p.reliability_score || 0) > (reliable.reliability_score || 0) ? p : reliable
        );
        if (mostReliable.vendor_id !== bestValue.vendor_id) {
            recommendations.push({
                type: 'most_reliable',
                vendor: mostReliable.vendor_name,
                price: mostReliable,
                reason: `Highest reliability score: ${(mostReliable.reliability_score * 100).toFixed(0)}%`,
                confidence: 0.8
            });
        }

        // Bulk discount opportunity
        if (options.quantity && options.quantity > 1) {
            const bestBulkDiscount = prices.reduce((best, p) => 
                (p.bulk_discount || 0) > (best.bulk_discount || 0) ? p : best
            );
            if (bestBulkDiscount.bulk_discount > 0) {
                recommendations.push({
                    type: 'bulk_savings',
                    vendor: bestBulkDiscount.vendor_name,
                    price: bestBulkDiscount,
                    reason: `Best bulk discount: ${(bestBulkDiscount.bulk_discount * 100).toFixed(0)}% off`,
                    savings: bestBulkDiscount.base_price - bestBulkDiscount.discounted_price,
                    confidence: 0.85
                });
            }
        }

        return recommendations;
    }

    calculateSavingsAnalysis(prices) {
        if (prices.length < 2) return null;

        const costs = prices.map(p => p.total_cost).sort((a, b) => a - b);
        const lowest = costs[0];
        const highest = costs[costs.length - 1];
        const median = costs[Math.floor(costs.length / 2)];

        return {
            potential_savings: {
                vs_highest: highest - lowest,
                vs_median: median - lowest,
                percentage_vs_highest: ((highest - lowest) / highest) * 100,
                percentage_vs_median: ((median - lowest) / median) * 100
            },
            price_spread: highest - lowest,
            market_efficiency: 1 - ((highest - lowest) / highest), // Lower spread = higher efficiency
            recommendation: lowest === prices[0].total_cost ? 
                'Current best value is also lowest price' : 
                'Consider switching vendors for potential savings'
        };
    }

    performMarketAnalysis(prices) {
        const analysis = {
            vendor_count: prices.length,
            average_reliability: prices.reduce((sum, p) => sum + (p.reliability_score || 0), 0) / prices.length,
            delivery_time_range: {
                fastest: Math.min(...prices.map(p => this.parseLeadTimeToDays(p.lead_time))),
                slowest: Math.max(...prices.map(p => this.parseLeadTimeToDays(p.lead_time)))
            },
            price_volatility: this.calculatePriceVolatility(prices),
            market_trend: this.determineMarketTrend(prices),
            competitive_landscape: this.analyzeCompetitiveLandscape(prices)
        };

        return analysis;
    }

    calculatePriceVolatility(prices) {
        const costs = prices.map(p => p.total_cost);
        const mean = costs.reduce((sum, cost) => sum + cost, 0) / costs.length;
        const variance = costs.reduce((sum, cost) => sum + Math.pow(cost - mean, 2), 0) / costs.length;
        const standardDeviation = Math.sqrt(variance);
        
        return {
            standard_deviation: standardDeviation,
            coefficient_of_variation: standardDeviation / mean,
            volatility_level: standardDeviation / mean > 0.2 ? 'high' : 
                             standardDeviation / mean > 0.1 ? 'moderate' : 'low'
        };
    }

    determineMarketTrend(prices) {
        // This would typically use historical data
        // For now, return a mock trend based on current spread
        const costs = prices.map(p => p.total_cost);
        const spread = (Math.max(...costs) - Math.min(...costs)) / Math.min(...costs);
        
        return {
            direction: 'stable', // Mock - would be 'rising', 'falling', or 'stable'
            confidence: 0.6,
            price_spread_indicator: spread > 0.3 ? 'high_competition' : 'price_stable',
            recommendation: spread > 0.3 ? 
                'High price variation suggests shopping around could yield significant savings' :
                'Prices are relatively stable across vendors'
        };
    }

    analyzeCompetitiveLandscape(prices) {
        const tiers = {
            budget: prices.filter(p => p.total_cost <= prices[0].total_cost * 1.1),
            mid_range: prices.filter(p => p.total_cost > prices[0].total_cost * 1.1 && p.total_cost <= prices[0].total_cost * 1.3),
            premium: prices.filter(p => p.total_cost > prices[0].total_cost * 1.3)
        };

        return {
            price_tiers: {
                budget_options: tiers.budget.length,
                mid_range_options: tiers.mid_range.length,
                premium_options: tiers.premium.length
            },
            market_concentration: this.calculateMarketConcentration(prices),
            vendor_positioning: prices.map(p => ({
                vendor: p.vendor_name,
                position: p.total_cost <= prices[0].total_cost * 1.1 ? 'budget' :
                         p.total_cost <= prices[0].total_cost * 1.3 ? 'mid_range' : 'premium',
                competitive_advantage: this.identifyCompetitiveAdvantage(p)
            }))
        };
    }

    calculateMarketConcentration(prices) {
        // Simplified market concentration based on price clustering
        const totalCost = prices.reduce((sum, p) => sum + p.total_cost, 0);
        const topThreeShare = prices.slice(0, 3).reduce((sum, p) => sum + p.total_cost, 0) / totalCost;
        
        return {
            top_three_share: topThreeShare,
            concentration_level: topThreeShare > 0.7 ? 'concentrated' : 
                               topThreeShare > 0.5 ? 'moderate' : 'fragmented'
        };
    }

    identifyCompetitiveAdvantage(price) {
        const advantages = [];
        
        if (price.bulk_discount && price.bulk_discount > 0.1) {
            advantages.push('bulk_pricing');
        }
        
        if (this.parseLeadTimeToDays(price.lead_time) <= 2) {
            advantages.push('fast_delivery');
        }
        
        if (price.reliability_score && price.reliability_score > 0.9) {
            advantages.push('high_reliability');
        }
        
        if (price.total_cost === Math.min(...[price.total_cost])) {
            advantages.push('low_price');
        }

        return advantages.length > 0 ? advantages : ['standard_offering'];
    }

    updatePriceHistory(partNumber, prices) {
        if (!this.priceHistory.has(partNumber)) {
            this.priceHistory.set(partNumber, []);
        }

        const history = this.priceHistory.get(partNumber);
        const entry = {
            timestamp: new Date(),
            prices: prices.map(p => ({
                vendor_id: p.vendor_id,
                total_cost: p.total_cost,
                availability: p.availability
            }))
        };

        history.push(entry);

        // Keep only last 100 entries
        if (history.length > 100) {
            history.shift();
        }
    }

    checkPriceAlerts(partNumber, prices) {
        const thresholds = this.alertThresholds.get(partNumber);
        if (!thresholds) return;

        const lowestPrice = Math.min(...prices.map(p => p.total_cost));
        
        if (thresholds.target_price && lowestPrice <= thresholds.target_price) {
            this.emit('price_alert', {
                type: 'target_reached',
                part_number: partNumber,
                target_price: thresholds.target_price,
                current_price: lowestPrice,
                savings: thresholds.reference_price - lowestPrice
            });
        }

        if (thresholds.drop_percentage) {
            const history = this.priceHistory.get(partNumber);
            if (history && history.length > 0) {
                const lastEntry = history[history.length - 1];
                const previousLow = Math.min(...lastEntry.prices.map(p => p.total_cost));
                const dropPercentage = (previousLow - lowestPrice) / previousLow;
                
                if (dropPercentage >= thresholds.drop_percentage) {
                    this.emit('price_alert', {
                        type: 'significant_drop',
                        part_number: partNumber,
                        drop_percentage: dropPercentage * 100,
                        current_price: lowestPrice,
                        previous_price: previousLow
                    });
                }
            }
        }
    }

    async setPriceAlert(partNumber, thresholds) {
        this.alertThresholds.set(partNumber, {
            ...thresholds,
            created: new Date(),
            user_id: thresholds.user_id
        });

        this.logger.info(`Price alert set for ${partNumber}:`, thresholds);

        this.emit('alert_created', {
            part_number: partNumber,
            thresholds
        });
    }

    async getBulkPricing(partsList, quantity = 1) {
        const bulkResults = await Promise.all(
            partsList.map(async partNumber => {
                try {
                    const comparison = await this.comparePrices(partNumber, quantity, {
                        strategy: 'bulk_optimized',
                        algorithm: 'total_cost'
                    });
                    return {
                        part_number: partNumber,
                        comparison,
                        success: true
                    };
                } catch (error) {
                    return {
                        part_number: partNumber,
                        error: error.message,
                        success: false
                    };
                }
            })
        );

        const consolidatedRecommendations = this.consolidateBulkRecommendations(bulkResults);

        return {
            individual_results: bulkResults,
            consolidated_recommendations: consolidatedRecommendations,
            total_parts: partsList.length,
            successful_comparisons: bulkResults.filter(r => r.success).length,
            bulk_savings_opportunities: this.identifyBulkSavingsOpportunities(bulkResults)
        };
    }

    consolidateBulkRecommendations(bulkResults) {
        const vendorSummary = new Map();
        
        for (const result of bulkResults) {
            if (!result.success) continue;
            
            const bestRecommendation = result.comparison.recommendations[0];
            if (bestRecommendation) {
                const vendorId = bestRecommendation.price.vendor_id;
                
                if (!vendorSummary.has(vendorId)) {
                    vendorSummary.set(vendorId, {
                        vendor_id: vendorId,
                        vendor_name: bestRecommendation.vendor,
                        parts_count: 0,
                        total_cost: 0,
                        total_savings: 0,
                        parts: []
                    });
                }
                
                const summary = vendorSummary.get(vendorId);
                summary.parts_count++;
                summary.total_cost += bestRecommendation.price.total_cost;
                summary.total_savings += bestRecommendation.savings || 0;
                summary.parts.push({
                    part_number: result.part_number,
                    cost: bestRecommendation.price.total_cost
                });
            }
        }

        return Array.from(vendorSummary.values()).sort((a, b) => a.total_cost - b.total_cost);
    }

    identifyBulkSavingsOpportunities(bulkResults) {
        const opportunities = [];
        
        // Vendor consolidation opportunity
        const vendorFrequency = new Map();
        for (const result of bulkResults) {
            if (!result.success) continue;
            
            for (const recommendation of result.comparison.recommendations) {
                if (recommendation.type === 'bulk_savings') {
                    const vendorId = recommendation.price.vendor_id;
                    vendorFrequency.set(vendorId, (vendorFrequency.get(vendorId) || 0) + 1);
                }
            }
        }

        for (const [vendorId, frequency] of vendorFrequency) {
            if (frequency >= 3) {
                opportunities.push({
                    type: 'vendor_consolidation',
                    vendor_id: vendorId,
                    parts_count: frequency,
                    potential_benefit: 'Additional bulk discounts through vendor consolidation'
                });
            }
        }

        return opportunities;
    }

    async exportComparison(comparison, format = 'json') {
        switch (format) {
            case 'csv':
                return this.exportToCsv(comparison);
            case 'xlsx':
                return this.exportToExcel(comparison);
            case 'pdf':
                return this.exportToPdf(comparison);
            default:
                return JSON.stringify(comparison, null, 2);
        }
    }

    exportToCsv(comparison) {
        const headers = [
            'Vendor', 'Unit Price', 'Quantity', 'Total Cost', 'Shipping',
            'Lead Time', 'Reliability', 'Strategic Score', 'Availability'
        ];
        
        let csv = headers.join(',') + '\n';
        
        for (const price of comparison.all_prices) {
            const row = [
                price.vendor_name,
                price.unit_price,
                price.quantity,
                price.total_cost,
                price.shipping_cost,
                price.lead_time,
                price.reliability_score,
                price.strategic_score?.toFixed(3) || '',
                price.availability
            ];
            csv += row.join(',') + '\n';
        }
        
        return csv;
    }

    async exportToExcel(comparison) {
        // Mock Excel export - would use xlsx library
        return {
            filename: `price_comparison_${Date.now()}.xlsx`,
            data: 'Mock Excel data',
            format: 'xlsx'
        };
    }

    async exportToPdf(comparison) {
        // Mock PDF export - would use pdf-lib or similar
        return {
            filename: `price_comparison_${Date.now()}.pdf`,
            data: 'Mock PDF data',
            format: 'pdf'
        };
    }
}