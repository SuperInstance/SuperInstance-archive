const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');
const moment = require('moment');

class ConversionOptimizer extends EventEmitter {
    constructor(redisClient, socketServer, logger) {
        super();
        this.redis = redisClient;
        this.io = socketServer;
        this.logger = logger;
        
        this.funnels = new Map();
        this.optimizationRules = new Map();
        this.userJourneys = new Map();
        this.heatmaps = new Map();
        this.experiments = new Map();
        this.triggers = new Map();
        
        this.setupEventHandlers();
        this.initializeOptimizationStrategies();
        this.startOptimizationEngine();
        this.startUserJourneyTracking();
    }

    setupEventHandlers() {
        this.on('funnel_created', this.handleFunnelCreated.bind(this));
        this.on('conversion_tracked', this.handleConversionTracked.bind(this));
        this.on('optimization_opportunity', this.handleOptimizationOpportunity.bind(this));
        this.on('experiment_completed', this.handleExperimentCompleted.bind(this));
    }

    initializeOptimizationStrategies() {
        this.optimizationStrategies = {
            'exit_intent': {
                name: 'Exit Intent Optimization',
                description: 'Trigger interventions when users show exit intent',
                triggers: ['mouse_leave', 'scroll_up', 'tab_switch'],
                actions: ['show_popup', 'display_offer', 'capture_email']
            },
            'cart_abandonment': {
                name: 'Cart Abandonment Recovery',
                description: 'Recover users who abandon their shopping cart',
                triggers: ['cart_idle', 'checkout_exit'],
                actions: ['send_email', 'show_discount', 'simplify_checkout']
            },
            'funnel_optimization': {
                name: 'Funnel Step Optimization',
                description: 'Optimize individual funnel steps based on drop-off rates',
                triggers: ['high_drop_off', 'long_dwell_time'],
                actions: ['simplify_form', 'add_social_proof', 'reduce_friction']
            },
            'personalization': {
                name: 'Dynamic Personalization',
                description: 'Personalize content based on user behavior and attributes',
                triggers: ['user_segment', 'behavior_pattern', 'returning_visitor'],
                actions: ['change_content', 'adjust_offers', 'modify_layout']
            }
        };
    }

    async createFunnel(funnelData) {
        try {
            const funnelId = uuidv4();
            const funnel = {
                id: funnelId,
                name: funnelData.name,
                description: funnelData.description || '',
                type: funnelData.type || 'conversion', // conversion, engagement, retention
                steps: funnelData.steps.map((step, index) => ({
                    id: uuidv4(),
                    order: index + 1,
                    name: step.name,
                    url: step.url,
                    eventType: step.eventType || 'page_view',
                    conditions: step.conditions || [],
                    goals: step.goals || [],
                    optimizations: []
                })),
                settings: {
                    attributionWindow: funnelData.settings?.attributionWindow || 30, // days
                    sessionTimeout: funnelData.settings?.sessionTimeout || 30, // minutes
                    allowBacktracking: funnelData.settings?.allowBacktracking !== false,
                    requireSequentialSteps: funnelData.settings?.requireSequentialSteps || false
                },
                segments: funnelData.segments || [],
                createdAt: new Date(),
                createdBy: funnelData.createdBy,
                status: 'active',
                analytics: {
                    totalSessions: 0,
                    completions: 0,
                    conversionRate: 0,
                    stepAnalytics: {},
                    dropOffPoints: []
                }
            };

            this.funnels.set(funnelId, funnel);
            await this.redis.hset('conversion_funnels', funnelId, JSON.stringify(funnel));
            
            // Initialize step analytics
            for (const step of funnel.steps) {
                funnel.analytics.stepAnalytics[step.id] = {
                    entries: 0,
                    exits: 0,
                    conversions: 0,
                    averageTime: 0,
                    dropOffRate: 0
                };
            }
            
            this.logger.info('Conversion funnel created', { 
                funnelId, 
                name: funnel.name,
                steps: funnel.steps.length 
            });
            
            this.io.emit('funnel_created', {
                funnelId,
                name: funnel.name,
                stepsCount: funnel.steps.length
            });
            
            this.emit('funnel_created', funnel);
            
            return { success: true, funnelId, funnel: this.sanitizeFunnelData(funnel) };
        } catch (error) {
            this.logger.error('Failed to create funnel', { error: error.message, funnelData });
            throw new Error(`Funnel creation failed: ${error.message}`);
        }
    }

    async trackConversion(conversionData) {
        try {
            const conversionId = uuidv4();
            const timestamp = new Date();
            
            const conversion = {
                id: conversionId,
                userId: conversionData.userId || this.generateAnonymousId(),
                sessionId: conversionData.sessionId || uuidv4(),
                funnelId: conversionData.funnelId,
                stepId: conversionData.stepId,
                eventType: conversionData.eventType || 'conversion',
                value: conversionData.value || 0,
                currency: conversionData.currency || 'USD',
                properties: conversionData.properties || {},
                context: {
                    url: conversionData.url || '',
                    referrer: conversionData.referrer || '',
                    userAgent: conversionData.userAgent || '',
                    ipAddress: conversionData.ipAddress || '',
                    device: conversionData.device || {},
                    location: conversionData.location || {}
                },
                timestamp,
                journey: [], // Will be populated with user journey steps
                experiments: conversionData.experiments || [],
                attribution: {
                    source: conversionData.attribution?.source || '',
                    medium: conversionData.attribution?.medium || '',
                    campaign: conversionData.attribution?.campaign || '',
                    content: conversionData.attribution?.content || ''
                }
            };

            // Track user journey if funnel is specified
            if (conversion.funnelId) {
                await this.updateUserJourney(conversion);
            }
            
            // Store conversion
            await this.redis.hset('conversions', conversionId, JSON.stringify(conversion));
            
            // Update funnel analytics
            if (conversion.funnelId) {
                await this.updateFunnelAnalytics(conversion);
            }
            
            // Check for optimization opportunities
            await this.analyzeOptimizationOpportunities(conversion);
            
            this.logger.info('Conversion tracked', { 
                conversionId, 
                funnelId: conversion.funnelId,
                eventType: conversion.eventType,
                value: conversion.value
            });
            
            this.io.emit('conversion_tracked', {
                conversionId,
                funnelId: conversion.funnelId,
                eventType: conversion.eventType,
                value: conversion.value,
                timestamp
            });
            
            this.emit('conversion_tracked', conversion);
            
            return { success: true, conversionId, conversion: this.sanitizeConversionData(conversion) };
        } catch (error) {
            this.logger.error('Failed to track conversion', { error: error.message, conversionData });
            throw new Error(`Conversion tracking failed: ${error.message}`);
        }
    }

    async optimizeConversions(optimizationData) {
        try {
            const optimizationId = uuidv4();
            
            // Analyze current performance
            const analysis = await this.analyzeConversionPerformance(optimizationData);
            
            // Generate recommendations
            const recommendations = await this.generateOptimizationRecommendations(analysis);
            
            // Create optimization plan
            const optimization = {
                id: optimizationId,
                funnelId: optimizationData.funnelId,
                type: optimizationData.type || 'automatic',
                strategy: optimizationData.strategy || 'funnel_optimization',
                analysis,
                recommendations,
                implementations: [],
                status: 'planned',
                createdAt: new Date(),
                createdBy: optimizationData.createdBy,
                estimatedImpact: {
                    conversionRateIncrease: 0,
                    revenueIncrease: 0,
                    confidence: 0
                },
                timeline: {
                    startDate: optimizationData.timeline?.startDate || new Date(),
                    expectedDuration: optimizationData.timeline?.expectedDuration || 14 // days
                }
            };

            // Implement automatic optimizations if requested
            if (optimizationData.autoImplement) {
                await this.implementOptimizations(optimization);
            }
            
            await this.redis.hset('optimizations', optimizationId, JSON.stringify(optimization));
            
            this.logger.info('Conversion optimization created', {
                optimizationId,
                funnelId: optimization.funnelId,
                strategy: optimization.strategy,
                recommendationsCount: recommendations.length
            });
            
            return { 
                success: true, 
                optimizationId, 
                optimization: this.sanitizeOptimizationData(optimization) 
            };
        } catch (error) {
            this.logger.error('Failed to optimize conversions', { error: error.message, optimizationData });
            throw new Error(`Conversion optimization failed: ${error.message}`);
        }
    }

    async analyzeConversionPerformance(data) {
        try {
            const funnel = this.funnels.get(data.funnelId);
            if (!funnel) {
                throw new Error(`Funnel ${data.funnelId} not found`);
            }
            
            // Get recent conversion data
            const conversions = await this.getRecentConversions(data.funnelId, 30); // Last 30 days
            const sessions = await this.getRecentSessions(data.funnelId, 30);
            
            // Calculate funnel metrics
            const funnelAnalytics = {
                totalSessions: sessions.length,
                totalConversions: conversions.length,
                overallConversionRate: conversions.length / Math.max(sessions.length, 1),
                averageSessionDuration: this.calculateAverageSessionDuration(sessions),
                bounceRate: this.calculateBounceRate(sessions)
            };
            
            // Analyze each step
            const stepAnalysis = [];
            for (let i = 0; i < funnel.steps.length; i++) {
                const step = funnel.steps[i];
                const stepSessions = sessions.filter(s => s.steps.some(st => st.stepId === step.id));
                const nextStepSessions = i < funnel.steps.length - 1 ? 
                    sessions.filter(s => s.steps.some(st => st.stepId === funnel.steps[i + 1].id)) : 
                    conversions;
                
                const dropOffRate = stepSessions.length > 0 ? 
                    1 - (nextStepSessions.length / stepSessions.length) : 0;
                
                stepAnalysis.push({
                    stepId: step.id,
                    stepName: step.name,
                    entries: stepSessions.length,
                    exits: stepSessions.length - nextStepSessions.length,
                    dropOffRate,
                    averageTimeOnStep: this.calculateAverageTimeOnStep(stepSessions, step.id),
                    issues: this.identifyStepIssues(step, dropOffRate, stepSessions)
                });
            }
            
            // Identify bottlenecks
            const bottlenecks = stepAnalysis
                .filter(step => step.dropOffRate > 0.3) // >30% drop-off
                .sort((a, b) => b.dropOffRate - a.dropOffRate);
            
            // Segment analysis
            const segmentAnalysis = await this.analyzeSegmentPerformance(data.funnelId, conversions, sessions);
            
            return {
                funnel: {
                    id: funnel.id,
                    name: funnel.name
                },
                overall: funnelAnalytics,
                steps: stepAnalysis,
                bottlenecks,
                segments: segmentAnalysis,
                trends: await this.analyzeTrends(data.funnelId),
                devices: this.analyzeDevicePerformance(sessions, conversions),
                trafficSources: this.analyzeTrafficSources(sessions, conversions)
            };
        } catch (error) {
            this.logger.error('Performance analysis failed', { error: error.message });
            throw error;
        }
    }

    async generateOptimizationRecommendations(analysis) {
        const recommendations = [];
        
        // Analyze bottlenecks
        for (const bottleneck of analysis.bottlenecks) {
            if (bottleneck.dropOffRate > 0.5) { // >50% drop-off
                recommendations.push({
                    id: uuidv4(),
                    type: 'critical',
                    category: 'funnel_optimization',
                    stepId: bottleneck.stepId,
                    issue: `High drop-off rate at ${bottleneck.stepName}`,
                    recommendation: this.generateStepOptimizationRecommendation(bottleneck),
                    priority: 'high',
                    estimatedImpact: {
                        conversionIncrease: Math.min(bottleneck.dropOffRate * 0.3, 0.2), // Up to 20% improvement
                        confidence: 0.7
                    },
                    effort: this.estimateImplementationEffort(bottleneck),
                    testable: true
                });
            }
        }
        
        // Device-specific recommendations
        if (analysis.devices.mobile.conversionRate < analysis.devices.desktop.conversionRate * 0.7) {
            recommendations.push({
                id: uuidv4(),
                type: 'device_optimization',
                category: 'mobile_optimization',
                issue: 'Poor mobile conversion rate',
                recommendation: 'Optimize mobile experience with responsive design and simplified forms',
                priority: 'medium',
                estimatedImpact: {
                    conversionIncrease: 0.15,
                    confidence: 0.6
                },
                effort: 'medium',
                testable: true
            });
        }
        
        // Traffic source recommendations
        const poorPerformingSources = Object.entries(analysis.trafficSources)
            .filter(([source, data]) => data.conversionRate < analysis.overall.overallConversionRate * 0.5)
            .map(([source]) => source);
        
        if (poorPerformingSources.length > 0) {
            recommendations.push({
                id: uuidv4(),
                type: 'traffic_optimization',
                category: 'source_optimization',
                issue: `Poor conversion from sources: ${poorPerformingSources.join(', ')}`,
                recommendation: 'Create landing pages tailored to specific traffic sources',
                priority: 'medium',
                estimatedImpact: {
                    conversionIncrease: 0.12,
                    confidence: 0.5
                },
                effort: 'high',
                testable: true
            });
        }
        
        // Form optimization recommendations
        const formSteps = analysis.steps.filter(step => step.issues.includes('form_abandonment'));
        if (formSteps.length > 0) {
            recommendations.push({
                id: uuidv4(),
                type: 'form_optimization',
                category: 'ux_optimization',
                issue: 'High form abandonment rates',
                recommendation: 'Simplify forms, add progress indicators, and implement smart defaults',
                priority: 'high',
                estimatedImpact: {
                    conversionIncrease: 0.18,
                    confidence: 0.8
                },
                effort: 'medium',
                testable: true
            });
        }
        
        // Sort by priority and estimated impact
        recommendations.sort((a, b) => {
            const priorityWeight = { high: 3, medium: 2, low: 1 };
            return (priorityWeight[b.priority] * b.estimatedImpact.conversionIncrease) - 
                   (priorityWeight[a.priority] * a.estimatedImpact.conversionIncrease);
        });
        
        return recommendations;
    }

    generateStepOptimizationRecommendation(bottleneck) {
        const recommendations = {
            'high_form_abandonment': 'Reduce form fields, add progress indicators, and implement field validation',
            'high_page_load_time': 'Optimize page performance, compress images, and minify resources',
            'high_bounce_rate': 'Improve page relevance, add compelling headlines, and ensure mobile optimization',
            'payment_issues': 'Add multiple payment options, display security badges, and simplify checkout',
            'pricing_concerns': 'Add pricing transparency, show value propositions, and offer guarantees',
            'trust_issues': 'Add testimonials, security badges, and contact information'
        };
        
        // Determine primary issue based on step characteristics
        let primaryIssue = 'high_bounce_rate'; // default
        
        if (bottleneck.averageTimeOnStep < 10) {
            primaryIssue = 'high_bounce_rate';
        } else if (bottleneck.averageTimeOnStep > 120) {
            primaryIssue = 'high_form_abandonment';
        }
        
        if (bottleneck.issues.includes('payment')) {
            primaryIssue = 'payment_issues';
        } else if (bottleneck.issues.includes('pricing')) {
            primaryIssue = 'pricing_concerns';
        }
        
        return recommendations[primaryIssue];
    }

    async updateUserJourney(conversion) {
        try {
            const journeyKey = `journey:${conversion.userId}:${conversion.sessionId}`;
            let journey = this.userJourneys.get(journeyKey);
            
            if (!journey) {
                journey = {
                    userId: conversion.userId,
                    sessionId: conversion.sessionId,
                    funnelId: conversion.funnelId,
                    startTime: conversion.timestamp,
                    steps: [],
                    currentStep: null,
                    completed: false
                };
            }
            
            // Add step to journey
            const journeyStep = {
                stepId: conversion.stepId,
                timestamp: conversion.timestamp,
                eventType: conversion.eventType,
                value: conversion.value,
                properties: conversion.properties,
                timeOnStep: journey.steps.length > 0 ? 
                    conversion.timestamp - journey.steps[journey.steps.length - 1].timestamp : 0
            };
            
            journey.steps.push(journeyStep);
            journey.currentStep = conversion.stepId;
            journey.lastActivity = conversion.timestamp;
            
            // Check if funnel is completed
            const funnel = this.funnels.get(conversion.funnelId);
            if (funnel && conversion.eventType === 'conversion') {
                journey.completed = true;
                journey.completedAt = conversion.timestamp;
                journey.totalTime = conversion.timestamp - journey.startTime;
            }
            
            this.userJourneys.set(journeyKey, journey);
            
            // Store journey step in Redis
            await this.redis.lpush(`user_journey:${journeyKey}`, JSON.stringify(journeyStep));
            await this.redis.expire(`user_journey:${journeyKey}`, 30 * 24 * 60 * 60); // 30 days
            
            conversion.journey = journey.steps;
            
        } catch (error) {
            this.logger.error('Failed to update user journey', { error: error.message });
        }
    }

    async createOptimizationRule(ruleData) {
        try {
            const ruleId = uuidv4();
            const rule = {
                id: ruleId,
                name: ruleData.name,
                description: ruleData.description || '',
                type: ruleData.type || 'behavioral', // behavioral, demographic, temporal
                conditions: ruleData.conditions || [],
                actions: ruleData.actions || [],
                priority: ruleData.priority || 1,
                status: 'active',
                targeting: {
                    segments: ruleData.targeting?.segments || [],
                    devices: ruleData.targeting?.devices || [],
                    locations: ruleData.targeting?.locations || [],
                    timeWindows: ruleData.targeting?.timeWindows || []
                },
                performance: {
                    triggers: 0,
                    conversions: 0,
                    conversionRate: 0,
                    averageOrderValue: 0
                },
                createdAt: new Date(),
                createdBy: ruleData.createdBy,
                lastTriggered: null
            };

            this.optimizationRules.set(ruleId, rule);
            await this.redis.hset('optimization_rules', ruleId, JSON.stringify(rule));
            
            this.logger.info('Optimization rule created', { 
                ruleId, 
                name: rule.name,
                type: rule.type 
            });
            
            return { success: true, ruleId, rule };
        } catch (error) {
            this.logger.error('Failed to create optimization rule', { error: error.message, ruleData });
            throw error;
        }
    }

    async createTrigger(triggerData) {
        try {
            const triggerId = uuidv4();
            const trigger = {
                id: triggerId,
                name: triggerData.name,
                type: triggerData.type, // exit_intent, time_based, scroll_based, click_based
                conditions: triggerData.conditions || [],
                actions: triggerData.actions || [],
                frequency: triggerData.frequency || 'once_per_session', // once_per_session, once_per_user, always
                delay: triggerData.delay || 0, // seconds
                priority: triggerData.priority || 1,
                status: 'active',
                performance: {
                    triggers: 0,
                    interactions: 0,
                    conversions: 0,
                    interactionRate: 0,
                    conversionRate: 0
                },
                createdAt: new Date(),
                lastTriggered: null
            };

            this.triggers.set(triggerId, trigger);
            await this.redis.hset('optimization_triggers', triggerId, JSON.stringify(trigger));
            
            this.logger.info('Optimization trigger created', { 
                triggerId, 
                name: trigger.name,
                type: trigger.type 
            });
            
            return { success: true, triggerId, trigger };
        } catch (error) {
            this.logger.error('Failed to create trigger', { error: error.message, triggerData });
            throw error;
        }
    }

    // Analytics and helper methods
    calculateAverageSessionDuration(sessions) {
        if (sessions.length === 0) return 0;
        const totalDuration = sessions.reduce((sum, session) => sum + (session.duration || 0), 0);
        return totalDuration / sessions.length;
    }

    calculateBounceRate(sessions) {
        if (sessions.length === 0) return 0;
        const bouncedSessions = sessions.filter(session => session.pageViews <= 1).length;
        return bouncedSessions / sessions.length;
    }

    calculateAverageTimeOnStep(sessions, stepId) {
        const stepTimes = sessions
            .map(session => {
                const stepData = session.steps.find(s => s.stepId === stepId);
                return stepData ? stepData.timeOnStep : 0;
            })
            .filter(time => time > 0);
        
        return stepTimes.length > 0 ? 
            stepTimes.reduce((sum, time) => sum + time, 0) / stepTimes.length : 0;
    }

    identifyStepIssues(step, dropOffRate, sessions) {
        const issues = [];
        
        if (dropOffRate > 0.5) issues.push('high_drop_off');
        if (step.url.includes('checkout') || step.url.includes('payment')) issues.push('payment');
        if (step.url.includes('pricing') || step.url.includes('plan')) issues.push('pricing');
        if (sessions.some(s => s.averageLoadTime > 3000)) issues.push('slow_loading');
        
        return issues;
    }

    analyzeDevicePerformance(sessions, conversions) {
        const devices = { desktop: { sessions: 0, conversions: 0 }, mobile: { sessions: 0, conversions: 0 }, tablet: { sessions: 0, conversions: 0 } };
        
        sessions.forEach(session => {
            const deviceType = session.device?.type || 'desktop';
            devices[deviceType] = devices[deviceType] || { sessions: 0, conversions: 0 };
            devices[deviceType].sessions++;
        });
        
        conversions.forEach(conversion => {
            const deviceType = conversion.context?.device?.type || 'desktop';
            devices[deviceType] = devices[deviceType] || { sessions: 0, conversions: 0 };
            devices[deviceType].conversions++;
        });
        
        // Calculate conversion rates
        Object.keys(devices).forEach(deviceType => {
            devices[deviceType].conversionRate = 
                devices[deviceType].conversions / Math.max(devices[deviceType].sessions, 1);
        });
        
        return devices;
    }

    analyzeTrafficSources(sessions, conversions) {
        const sources = {};
        
        sessions.forEach(session => {
            const source = session.attribution?.source || 'direct';
            sources[source] = sources[source] || { sessions: 0, conversions: 0 };
            sources[source].sessions++;
        });
        
        conversions.forEach(conversion => {
            const source = conversion.attribution?.source || 'direct';
            sources[source] = sources[source] || { sessions: 0, conversions: 0 };
            sources[source].conversions++;
        });
        
        // Calculate conversion rates
        Object.keys(sources).forEach(source => {
            sources[source].conversionRate = 
                sources[source].conversions / Math.max(sources[source].sessions, 1);
        });
        
        return sources;
    }

    startOptimizationEngine() {
        // Run optimization analysis every hour
        setInterval(async () => {
            try {
                await this.runOptimizationAnalysis();
            } catch (error) {
                this.logger.error('Optimization analysis error', { error: error.message });
            }
        }, 60 * 60 * 1000);
    }

    startUserJourneyTracking() {
        // Clean up old user journeys every 6 hours
        setInterval(async () => {
            try {
                await this.cleanupOldJourneys();
            } catch (error) {
                this.logger.error('Journey cleanup error', { error: error.message });
            }
        }, 6 * 60 * 60 * 1000);
    }

    async getOverallStats() {
        const totalFunnels = this.funnels.size;
        const totalOptimizations = this.optimizationRules.size;
        const totalTriggers = this.triggers.size;
        
        // Calculate aggregate conversion rate
        let totalSessions = 0;
        let totalConversions = 0;
        
        for (const funnel of this.funnels.values()) {
            totalSessions += funnel.analytics.totalSessions;
            totalConversions += funnel.analytics.completions;
        }
        
        return {
            totalFunnels,
            totalOptimizations,
            totalTriggers,
            overallConversionRate: totalSessions > 0 ? totalConversions / totalSessions : 0,
            totalSessions,
            totalConversions
        };
    }

    // Event handlers
    handleFunnelCreated(funnel) {
        this.logger.info('Funnel created and ready for optimization', {
            funnelId: funnel.id,
            name: funnel.name
        });
    }

    handleConversionTracked(conversion) {
        this.logger.info('Conversion tracked for optimization analysis', {
            conversionId: conversion.id,
            funnelId: conversion.funnelId
        });
    }

    handleOptimizationOpportunity(opportunity) {
        this.logger.info('Optimization opportunity identified', opportunity);
    }

    handleExperimentCompleted(experiment) {
        this.logger.info('Optimization experiment completed', {
            experimentId: experiment.id,
            result: experiment.result
        });
    }

    // Data sanitization
    sanitizeFunnelData(funnel) {
        return funnel; // No sensitive data to remove
    }

    sanitizeConversionData(conversion) {
        return {
            ...conversion,
            // Remove sensitive user data if needed
        };
    }

    sanitizeOptimizationData(optimization) {
        return optimization;
    }

    generateAnonymousId() {
        return 'anon_' + uuidv4().substring(0, 8);
    }
}

module.exports = ConversionOptimizer;