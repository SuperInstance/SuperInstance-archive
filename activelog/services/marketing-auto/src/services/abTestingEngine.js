const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');
const moment = require('moment');

class ABTestingEngine extends EventEmitter {
    constructor(redisClient, socketServer, logger) {
        super();
        this.redis = redisClient;
        this.io = socketServer;
        this.logger = logger;
        
        this.tests = new Map();
        this.variations = new Map();
        this.participants = new Map();
        this.results = new Map();
        this.segments = new Map();
        this.statisticalTests = new Map();
        
        this.setupEventHandlers();
        this.initializeStatisticalMethods();
        this.startTestMonitoring();
        this.startStatisticalAnalysis();
    }

    setupEventHandlers() {
        this.on('test_created', this.handleTestCreated.bind(this));
        this.on('participant_assigned', this.handleParticipantAssigned.bind(this));
        this.on('conversion_recorded', this.handleConversionRecorded.bind(this));
        this.on('test_completed', this.handleTestCompleted.bind(this));
        this.on('significant_result', this.handleSignificantResult.bind(this));
    }

    initializeStatisticalMethods() {
        this.statisticalMethods = {
            'two_sample_ttest': {
                name: 'Two-Sample T-Test',
                description: 'Compare means between two groups',
                minSampleSize: 30,
                calculate: this.calculateTTest.bind(this)
            },
            'chi_square': {
                name: 'Chi-Square Test',
                description: 'Compare conversion rates between groups',
                minSampleSize: 5,
                calculate: this.calculateChiSquare.bind(this)
            },
            'bayesian': {
                name: 'Bayesian A/B Test',
                description: 'Bayesian approach to A/B testing',
                minSampleSize: 10,
                calculate: this.calculateBayesian.bind(this)
            },
            'sequential': {
                name: 'Sequential Testing',
                description: 'Continuous monitoring with early stopping',
                minSampleSize: 10,
                calculate: this.calculateSequential.bind(this)
            }
        };
    }

    async createTest(testData) {
        try {
            const testId = uuidv4();
            const test = {
                id: testId,
                name: testData.name,
                description: testData.description || '',
                type: testData.type || 'ab', // ab, multivariate, split_url
                status: 'draft', // draft, running, paused, completed, archived
                hypothesis: testData.hypothesis || '',
                primaryMetric: testData.primaryMetric || 'conversion_rate',
                secondaryMetrics: testData.secondaryMetrics || [],
                statisticalMethod: testData.statisticalMethod || 'chi_square',
                targetingRules: {
                    trafficAllocation: testData.targetingRules?.trafficAllocation || 100, // percentage
                    audienceSegments: testData.targetingRules?.audienceSegments || [],
                    devices: testData.targetingRules?.devices || ['desktop', 'mobile', 'tablet'],
                    locations: testData.targetingRules?.locations || [],
                    newVisitorsOnly: testData.targetingRules?.newVisitorsOnly || false,
                    customConditions: testData.targetingRules?.customConditions || []
                },
                configuration: {
                    confidenceLevel: testData.configuration?.confidenceLevel || 95,
                    minimumDetectableEffect: testData.configuration?.minimumDetectableEffect || 10, // percentage
                    statisticalPower: testData.configuration?.statisticalPower || 80,
                    maxDuration: testData.configuration?.maxDuration || 30, // days
                    minSampleSize: testData.configuration?.minSampleSize || 100,
                    earlyStoppingEnabled: testData.configuration?.earlyStoppingEnabled || false
                },
                variations: [],
                createdAt: new Date(),
                createdBy: testData.createdBy,
                startDate: null,
                endDate: null,
                analytics: {
                    totalParticipants: 0,
                    totalConversions: 0,
                    overallConversionRate: 0,
                    variationPerformance: {},
                    statisticalSignificance: null,
                    winningVariation: null
                },
                settings: {
                    equalTrafficSplit: testData.settings?.equalTrafficSplit !== false,
                    stickyBucketing: testData.settings?.stickyBucketing !== false,
                    crossDeviceTracking: testData.settings?.crossDeviceTracking || false,
                    excludeBots: testData.settings?.excludeBots !== false,
                    qualityFilter: testData.settings?.qualityFilter || false
                }
            };

            // Create variations
            if (testData.variations && testData.variations.length >= 2) {
                for (let i = 0; i < testData.variations.length; i++) {
                    const variationData = testData.variations[i];
                    const variation = await this.createVariation(testId, {
                        ...variationData,
                        isControl: i === 0, // First variation is control
                        trafficWeight: test.settings.equalTrafficSplit ? 
                            100 / testData.variations.length : 
                            variationData.trafficWeight || 50
                    });
                    test.variations.push(variation.variationId);
                }
            }

            this.tests.set(testId, test);
            await this.redis.hset('ab_tests', testId, JSON.stringify(test));
            
            this.logger.info('A/B test created', { 
                testId, 
                name: test.name,
                variations: test.variations.length,
                type: test.type
            });
            
            this.io.emit('test_created', {
                testId,
                name: test.name,
                type: test.type,
                variations: test.variations.length,
                status: test.status
            });
            
            this.emit('test_created', test);
            
            return { success: true, testId, test: this.sanitizeTestData(test) };
        } catch (error) {
            this.logger.error('Failed to create A/B test', { error: error.message, testData });
            throw new Error(`A/B test creation failed: ${error.message}`);
        }
    }

    async createVariation(testId, variationData) {
        try {
            const variationId = uuidv4();
            const variation = {
                id: variationId,
                testId,
                name: variationData.name,
                description: variationData.description || '',
                isControl: variationData.isControl || false,
                trafficWeight: variationData.trafficWeight || 50,
                changes: variationData.changes || [], // Array of DOM changes, URL changes, etc.
                content: {
                    html: variationData.content?.html || '',
                    css: variationData.content?.css || '',
                    javascript: variationData.content?.javascript || '',
                    url: variationData.content?.url || ''
                },
                targeting: variationData.targeting || {},
                createdAt: new Date(),
                performance: {
                    participants: 0,
                    conversions: 0,
                    conversionRate: 0,
                    revenue: 0,
                    averageOrderValue: 0,
                    bounceRate: 0,
                    timeOnSite: 0,
                    statisticalMetrics: {}
                }
            };

            this.variations.set(variationId, variation);
            await this.redis.hset('ab_variations', variationId, JSON.stringify(variation));
            
            this.logger.info('A/B test variation created', { 
                variationId,
                testId,
                name: variation.name,
                isControl: variation.isControl
            });
            
            return { success: true, variationId, variation };
        } catch (error) {
            this.logger.error('Failed to create variation', { error: error.message, variationData });
            throw error;
        }
    }

    async startTest(testId) {
        try {
            const test = this.tests.get(testId) || 
                JSON.parse(await this.redis.hget('ab_tests', testId));
            
            if (!test) {
                throw new Error(`Test ${testId} not found`);
            }
            
            if (test.status !== 'draft') {
                throw new Error(`Test ${testId} cannot be started from status ${test.status}`);
            }
            
            // Validate test configuration
            await this.validateTestConfiguration(test);
            
            // Calculate sample size requirements
            const sampleSizeCalculation = this.calculateRequiredSampleSize(test);
            test.analytics.requiredSampleSize = sampleSizeCalculation;
            
            test.status = 'running';
            test.startDate = new Date();
            test.endDate = moment().add(test.configuration.maxDuration, 'days').toDate();
            
            this.tests.set(testId, test);
            await this.redis.hset('ab_tests', testId, JSON.stringify(test));
            
            this.logger.info('A/B test started', { 
                testId,
                name: test.name,
                requiredSampleSize: sampleSizeCalculation.totalSampleSize,
                estimatedDuration: test.configuration.maxDuration
            });
            
            this.io.emit('test_started', {
                testId,
                name: test.name,
                startDate: test.startDate,
                estimatedEndDate: test.endDate
            });
            
            return { success: true, startDate: test.startDate };
        } catch (error) {
            this.logger.error('Failed to start A/B test', { error: error.message, testId });
            throw error;
        }
    }

    async participateInTest(testId, participantData) {
        try {
            const test = this.tests.get(testId) || 
                JSON.parse(await this.redis.hget('ab_tests', testId));
            
            if (!test || test.status !== 'running') {
                return { success: false, reason: 'Test not active' };
            }
            
            const userId = participantData.userId || this.generateAnonymousId();
            
            // Check if user already participated
            const existingParticipation = await this.getExistingParticipation(testId, userId);
            if (existingParticipation && test.settings.stickyBucketing) {
                return {
                    success: true,
                    variation: existingParticipation.variation,
                    assignment: 'existing',
                    participantId: existingParticipation.id
                };
            }
            
            // Check targeting rules
            const targetingResult = await this.checkTargeting(test.targetingRules, participantData);
            if (!targetingResult.eligible) {
                return { success: false, reason: targetingResult.reason };
            }
            
            // Assign to variation
            const assignment = await this.assignToVariation(test, userId, participantData);
            
            // Create participant record
            const participantId = uuidv4();
            const participant = {
                id: participantId,
                testId,
                userId,
                variationId: assignment.variationId,
                assignedAt: new Date(),
                context: {
                    userAgent: participantData.userAgent || '',
                    ipAddress: participantData.ipAddress || '',
                    referrer: participantData.referrer || '',
                    device: participantData.device || {},
                    location: participantData.location || {}
                },
                events: [],
                conversions: [],
                revenue: 0,
                sessionData: participantData.sessionData || {}
            };
            
            this.participants.set(participantId, participant);
            await this.redis.hset('ab_participants', participantId, JSON.stringify(participant));
            
            // Update test and variation analytics
            test.analytics.totalParticipants++;
            const variation = this.variations.get(assignment.variationId);
            if (variation) {
                variation.performance.participants++;
                await this.redis.hset('ab_variations', assignment.variationId, JSON.stringify(variation));
            }
            
            await this.redis.hset('ab_tests', testId, JSON.stringify(test));
            
            this.logger.info('Participant assigned to A/B test', { 
                testId,
                participantId,
                variationId: assignment.variationId,
                variationName: assignment.variationName
            });
            
            this.io.to(`test_${testId}`).emit('participant_assigned', {
                testId,
                variationId: assignment.variationId,
                totalParticipants: test.analytics.totalParticipants
            });
            
            this.emit('participant_assigned', {
                test,
                participant,
                variation: assignment
            });
            
            return {
                success: true,
                participantId,
                variation: {
                    id: assignment.variationId,
                    name: assignment.variationName,
                    changes: assignment.changes,
                    content: assignment.content
                },
                assignment: 'new'
            };
        } catch (error) {
            this.logger.error('Failed to assign participant to test', { 
                error: error.message, 
                testId, 
                participantData 
            });
            throw error;
        }
    }

    async recordConversion(conversionData) {
        try {
            const participant = this.participants.get(conversionData.participantId) ||
                JSON.parse(await this.redis.hget('ab_participants', conversionData.participantId));
            
            if (!participant) {
                return { success: false, reason: 'Participant not found' };
            }
            
            const test = this.tests.get(participant.testId);
            const variation = this.variations.get(participant.variationId);
            
            if (!test || !variation) {
                return { success: false, reason: 'Test or variation not found' };
            }
            
            const conversionId = uuidv4();
            const conversion = {
                id: conversionId,
                participantId: participant.id,
                testId: participant.testId,
                variationId: participant.variationId,
                metricName: conversionData.metricName || test.primaryMetric,
                value: conversionData.value || 1,
                revenue: conversionData.revenue || 0,
                timestamp: new Date(),
                properties: conversionData.properties || {}
            };
            
            // Add to participant's conversion history
            participant.conversions.push(conversion);
            participant.revenue += conversion.revenue;
            
            // Update variation performance
            variation.performance.conversions++;
            variation.performance.revenue += conversion.revenue;
            variation.performance.conversionRate = 
                variation.performance.conversions / Math.max(variation.performance.participants, 1);
            variation.performance.averageOrderValue = 
                variation.performance.revenue / Math.max(variation.performance.conversions, 1);
            
            // Update test analytics
            test.analytics.totalConversions++;
            test.analytics.overallConversionRate = 
                test.analytics.totalConversions / Math.max(test.analytics.totalParticipants, 1);
            
            // Store updates
            await this.redis.hset('ab_participants', participant.id, JSON.stringify(participant));
            await this.redis.hset('ab_variations', variation.id, JSON.stringify(variation));
            await this.redis.hset('ab_tests', test.id, JSON.stringify(test));
            
            // Check for statistical significance
            await this.updateStatisticalAnalysis(test);
            
            this.logger.info('A/B test conversion recorded', { 
                testId: test.id,
                participantId: participant.id,
                variationId: variation.id,
                metricName: conversion.metricName,
                value: conversion.value,
                revenue: conversion.revenue
            });
            
            this.io.to(`test_${test.id}`).emit('conversion_recorded', {
                testId: test.id,
                variationId: variation.id,
                conversionRate: variation.performance.conversionRate,
                totalConversions: test.analytics.totalConversions
            });
            
            this.emit('conversion_recorded', {
                test,
                participant,
                variation,
                conversion
            });
            
            return { success: true, conversionId, conversion };
        } catch (error) {
            this.logger.error('Failed to record conversion', { 
                error: error.message, 
                conversionData 
            });
            throw error;
        }
    }

    async getTestResults(testId) {
        try {
            const test = this.tests.get(testId) || 
                JSON.parse(await this.redis.hget('ab_tests', testId));
            
            if (!test) {
                throw new Error(`Test ${testId} not found`);
            }
            
            // Get all variations for this test
            const variations = [];
            for (const variationId of test.variations) {
                const variation = this.variations.get(variationId) || 
                    JSON.parse(await this.redis.hget('ab_variations', variationId));
                if (variation) {
                    variations.push(variation);
                }
            }
            
            // Calculate statistical results
            const statisticalResults = await this.calculateStatisticalSignificance(test, variations);
            
            // Calculate confidence intervals
            const confidenceIntervals = this.calculateConfidenceIntervals(variations, test.configuration.confidenceLevel);
            
            // Determine winner
            const winner = this.determineWinner(variations, statisticalResults);
            
            // Calculate uplift
            const uplift = this.calculateUplift(variations);
            
            const results = {
                test: {
                    id: test.id,
                    name: test.name,
                    status: test.status,
                    startDate: test.startDate,
                    endDate: test.endDate,
                    duration: test.startDate ? moment().diff(moment(test.startDate), 'days') : 0
                },
                overview: {
                    totalParticipants: test.analytics.totalParticipants,
                    totalConversions: test.analytics.totalConversions,
                    overallConversionRate: test.analytics.overallConversionRate,
                    statistical: statisticalResults
                },
                variations: variations.map(variation => ({
                    id: variation.id,
                    name: variation.name,
                    isControl: variation.isControl,
                    performance: variation.performance,
                    confidenceInterval: confidenceIntervals[variation.id],
                    uplift: uplift[variation.id],
                    isWinner: winner && winner.id === variation.id
                })),
                insights: {
                    winner: winner,
                    recommendation: this.generateRecommendation(test, variations, statisticalResults),
                    keyFindings: this.generateKeyFindings(test, variations, statisticalResults),
                    nextSteps: this.generateNextSteps(test, statisticalResults)
                },
                analytics: {
                    sampleSizeProgress: test.analytics.requiredSampleSize ? 
                        test.analytics.totalParticipants / test.analytics.requiredSampleSize.totalSampleSize : 0,
                    timeProgress: test.startDate ? 
                        moment().diff(moment(test.startDate), 'days') / test.configuration.maxDuration : 0,
                    canStop: statisticalResults.canStop || false,
                    reasonToStop: statisticalResults.reasonToStop || null
                }
            };
            
            return results;
        } catch (error) {
            this.logger.error('Failed to get test results', { error: error.message, testId });
            throw error;
        }
    }

    async assignToVariation(test, userId, participantData) {
        // Use deterministic hashing for consistent assignment
        const hashInput = `${userId}:${test.id}`;
        const hash = this.hashCode(hashInput);
        const normalizedHash = Math.abs(hash) / Math.pow(2, 31);
        
        // Get variation weights
        const variations = [];
        for (const variationId of test.variations) {
            const variation = this.variations.get(variationId);
            if (variation) {
                variations.push(variation);
            }
        }
        
        // Calculate cumulative weights
        let cumulativeWeight = 0;
        const cumulativeWeights = variations.map(variation => {
            cumulativeWeight += variation.trafficWeight;
            return { variation, threshold: cumulativeWeight };
        });
        
        // Normalize to percentage
        const totalWeight = cumulativeWeight;
        const normalizedThreshold = normalizedHash * totalWeight;
        
        // Find matching variation
        const assignment = cumulativeWeights.find(item => normalizedThreshold <= item.threshold);
        const selectedVariation = assignment ? assignment.variation : variations[0]; // Fallback to first
        
        return {
            variationId: selectedVariation.id,
            variationName: selectedVariation.name,
            changes: selectedVariation.changes,
            content: selectedVariation.content
        };
    }

    async checkTargeting(targetingRules, participantData) {
        // Traffic allocation check
        if (targetingRules.trafficAllocation < 100) {
            const random = Math.random() * 100;
            if (random > targetingRules.trafficAllocation) {
                return { eligible: false, reason: 'Traffic allocation' };
            }
        }
        
        // Device check
        if (targetingRules.devices.length > 0) {
            const userDevice = participantData.device?.type || 'desktop';
            if (!targetingRules.devices.includes(userDevice)) {
                return { eligible: false, reason: 'Device not targeted' };
            }
        }
        
        // Location check
        if (targetingRules.locations.length > 0 && participantData.location) {
            const userCountry = participantData.location.country;
            const matchesLocation = targetingRules.locations.some(loc => 
                loc.country === userCountry || loc === userCountry
            );
            if (!matchesLocation) {
                return { eligible: false, reason: 'Location not targeted' };
            }
        }
        
        // New visitors only check
        if (targetingRules.newVisitorsOnly) {
            const isNewVisitor = !participantData.sessionData?.returningVisitor;
            if (!isNewVisitor) {
                return { eligible: false, reason: 'Returning visitor excluded' };
            }
        }
        
        return { eligible: true };
    }

    async calculateStatisticalSignificance(test, variations) {
        const method = this.statisticalMethods[test.statisticalMethod];
        if (!method) {
            throw new Error(`Statistical method ${test.statisticalMethod} not found`);
        }
        
        return await method.calculate(variations, test.configuration);
    }

    calculateTTest(variations, configuration) {
        if (variations.length !== 2) {
            throw new Error('T-test requires exactly 2 variations');
        }
        
        const [control, treatment] = variations;
        
        const controlRate = control.performance.conversionRate;
        const treatmentRate = treatment.performance.conversionRate;
        
        const controlSE = Math.sqrt((controlRate * (1 - controlRate)) / control.performance.participants);
        const treatmentSE = Math.sqrt((treatmentRate * (1 - treatmentRate)) / treatment.performance.participants);
        
        const pooledSE = Math.sqrt(controlSE * controlSE + treatmentSE * treatmentSE);
        const tStat = Math.abs(treatmentRate - controlRate) / pooledSE;
        
        const df = control.performance.participants + treatment.performance.participants - 2;
        const criticalValue = this.getTCriticalValue(configuration.confidenceLevel, df);
        
        const isSignificant = tStat > criticalValue;
        const pValue = this.calculatePValue(tStat, df);
        
        return {
            method: 't_test',
            isSignificant,
            pValue,
            confidenceLevel: configuration.confidenceLevel,
            testStatistic: tStat,
            criticalValue,
            canStop: isSignificant || pValue < (100 - configuration.confidenceLevel) / 100,
            reasonToStop: isSignificant ? 'Statistical significance achieved' : null
        };
    }

    calculateChiSquare(variations, configuration) {
        // Chi-square test for conversion rates
        const totalParticipants = variations.reduce((sum, v) => sum + v.performance.participants, 0);
        const totalConversions = variations.reduce((sum, v) => sum + v.performance.conversions, 0);
        const overallRate = totalConversions / totalParticipants;
        
        let chiSquare = 0;
        let df = variations.length - 1;
        
        for (const variation of variations) {
            const expected = variation.performance.participants * overallRate;
            const observed = variation.performance.conversions;
            
            if (expected > 0) {
                chiSquare += Math.pow(observed - expected, 2) / expected;
            }
        }
        
        const criticalValue = this.getChiSquareCriticalValue(configuration.confidenceLevel, df);
        const isSignificant = chiSquare > criticalValue;
        const pValue = this.calculateChiSquarePValue(chiSquare, df);
        
        return {
            method: 'chi_square',
            isSignificant,
            pValue,
            confidenceLevel: configuration.confidenceLevel,
            testStatistic: chiSquare,
            criticalValue,
            degreesOfFreedom: df,
            canStop: isSignificant,
            reasonToStop: isSignificant ? 'Statistical significance achieved' : null
        };
    }

    calculateBayesian(variations, configuration) {
        // Simplified Bayesian approach
        const control = variations.find(v => v.isControl) || variations[0];
        const treatments = variations.filter(v => !v.isControl);
        
        const results = [];
        
        for (const treatment of treatments) {
            const controlAlpha = control.performance.conversions + 1;
            const controlBeta = control.performance.participants - control.performance.conversions + 1;
            
            const treatmentAlpha = treatment.performance.conversions + 1;
            const treatmentBeta = treatment.performance.participants - treatment.performance.conversions + 1;
            
            // Probability that treatment > control
            const probability = this.betaProbability(treatmentAlpha, treatmentBeta, controlAlpha, controlBeta);
            const isSignificant = probability > configuration.confidenceLevel / 100;
            
            results.push({
                variationId: treatment.id,
                probability,
                isSignificant,
                credibleInterval: this.calculateBayesianCredibleInterval(treatmentAlpha, treatmentBeta, 0.95)
            });
        }
        
        const hasSignificantResult = results.some(r => r.isSignificant);
        
        return {
            method: 'bayesian',
            isSignificant: hasSignificantResult,
            results,
            canStop: hasSignificantResult,
            reasonToStop: hasSignificantResult ? 'High probability of difference detected' : null
        };
    }

    calculateSequential(variations, configuration) {
        // Sequential probability ratio test (SPRT)
        if (variations.length !== 2) {
            throw new Error('Sequential testing requires exactly 2 variations');
        }
        
        const [control, treatment] = variations;
        
        const alpha = (100 - configuration.confidenceLevel) / 100 / 2; // Two-tailed
        const beta = (100 - configuration.statisticalPower) / 100;
        
        const upperBound = Math.log((1 - beta) / alpha);
        const lowerBound = Math.log(beta / (1 - alpha));
        
        const controlRate = control.performance.conversionRate;
        const treatmentRate = treatment.performance.conversionRate;
        const mde = configuration.minimumDetectableEffect / 100;
        
        // Log likelihood ratio
        let logLR = 0;
        if (controlRate > 0 && treatmentRate > 0) {
            logLR = treatment.performance.conversions * Math.log(treatmentRate / controlRate) +
                   (treatment.performance.participants - treatment.performance.conversions) * 
                   Math.log((1 - treatmentRate) / (1 - controlRate));
        }
        
        let decision = 'continue';
        let isSignificant = false;
        
        if (logLR >= upperBound) {
            decision = 'stop_treatment_wins';
            isSignificant = true;
        } else if (logLR <= lowerBound) {
            decision = 'stop_control_wins';
            isSignificant = false;
        }
        
        return {
            method: 'sequential',
            isSignificant,
            decision,
            logLikelihoodRatio: logLR,
            upperBound,
            lowerBound,
            canStop: decision !== 'continue',
            reasonToStop: decision !== 'continue' ? `Sequential boundary reached: ${decision}` : null
        };
    }

    calculateRequiredSampleSize(test) {
        const alpha = (100 - test.configuration.confidenceLevel) / 100;
        const beta = (100 - test.configuration.statisticalPower) / 100;
        const mde = test.configuration.minimumDetectableEffect / 100;
        const baselineRate = 0.05; // Assume 5% baseline conversion rate
        
        // Z-scores
        const zAlpha = this.getZScore(1 - alpha / 2);
        const zBeta = this.getZScore(1 - beta);
        
        // Effect size
        const p1 = baselineRate;
        const p2 = baselineRate * (1 + mde);
        const pooledP = (p1 + p2) / 2;
        
        // Sample size per variation
        const sampleSizePerVariation = Math.ceil(
            (Math.pow(zAlpha + zBeta, 2) * 2 * pooledP * (1 - pooledP)) / 
            Math.pow(p2 - p1, 2)
        );
        
        return {
            sampleSizePerVariation,
            totalSampleSize: sampleSizePerVariation * test.variations.length,
            baselineRate,
            detectionRate: p2,
            assumptions: {
                alpha,
                beta,
                minimumDetectableEffect: mde,
                power: test.configuration.statisticalPower
            }
        };
    }

    // Helper statistical methods
    hashCode(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32bit integer
        }
        return hash;
    }

    getTCriticalValue(confidenceLevel, df) {
        // Simplified t-table lookup
        const alpha = (100 - confidenceLevel) / 100;
        if (df >= 30) return this.getZScore(1 - alpha / 2);
        
        // Approximate t-values for small df
        const tTable = {
            1: { 90: 6.314, 95: 12.706, 99: 63.657 },
            5: { 90: 2.015, 95: 2.571, 99: 4.032 },
            10: { 90: 1.812, 95: 2.228, 99: 3.169 },
            20: { 90: 1.725, 95: 2.086, 99: 2.845 },
            30: { 90: 1.697, 95: 2.042, 99: 2.750 }
        };
        
        const closestDf = Object.keys(tTable)
            .map(Number)
            .reduce((prev, curr) => 
                Math.abs(curr - df) < Math.abs(prev - df) ? curr : prev
            );
        
        return tTable[closestDf][confidenceLevel] || 2.0;
    }

    getZScore(probability) {
        // Approximate inverse normal distribution
        if (probability === 0.5) return 0;
        if (probability > 0.5) {
            return -this.getZScore(1 - probability);
        }
        
        const t = Math.sqrt(-2 * Math.log(probability));
        return -(t - (2.30753 + 0.27061 * t) / (1 + 0.99229 * t + 0.04481 * t * t));
    }

    startTestMonitoring() {
        // Monitor tests every hour
        setInterval(async () => {
            try {
                await this.monitorRunningTests();
            } catch (error) {
                this.logger.error('Test monitoring error', { error: error.message });
            }
        }, 60 * 60 * 1000);
    }

    startStatisticalAnalysis() {
        // Update statistical analysis every 15 minutes
        setInterval(async () => {
            try {
                await this.updateAllStatisticalAnalyses();
            } catch (error) {
                this.logger.error('Statistical analysis error', { error: error.message });
            }
        }, 15 * 60 * 1000);
    }

    generateAnonymousId() {
        return 'anon_' + uuidv4().substring(0, 8);
    }

    // Event handlers
    handleTestCreated(test) {
        this.logger.info('A/B test created and configured', {
            testId: test.id,
            name: test.name,
            variations: test.variations.length
        });
    }

    handleParticipantAssigned(data) {
        this.logger.info('Participant assigned to test variation', {
            testId: data.test.id,
            participantId: data.participant.id,
            variationId: data.variation.variationId
        });
    }

    handleConversionRecorded(data) {
        this.logger.info('Conversion recorded for A/B test', {
            testId: data.test.id,
            variationId: data.variation.id,
            conversionValue: data.conversion.value
        });
    }

    handleTestCompleted(test) {
        this.logger.info('A/B test completed', {
            testId: test.id,
            name: test.name,
            winner: test.analytics.winningVariation
        });
    }

    handleSignificantResult(data) {
        this.logger.info('Statistical significance achieved', data);
        
        this.io.emit('significant_result_detected', {
            testId: data.testId,
            significance: data.significance,
            winner: data.winner
        });
    }

    // Data sanitization
    sanitizeTestData(test) {
        return {
            ...test,
            // Remove sensitive configuration if needed
        };
    }

    async getOverallStats() {
        const totalTests = this.tests.size;
        const runningTests = Array.from(this.tests.values()).filter(t => t.status === 'running').length;
        const completedTests = Array.from(this.tests.values()).filter(t => t.status === 'completed').length;
        
        let totalParticipants = 0;
        let totalConversions = 0;
        
        for (const test of this.tests.values()) {
            totalParticipants += test.analytics.totalParticipants;
            totalConversions += test.analytics.totalConversions;
        }
        
        return {
            totalTests,
            runningTests,
            completedTests,
            totalParticipants,
            totalConversions,
            overallConversionRate: totalParticipants > 0 ? totalConversions / totalParticipants : 0
        };
    }
}

module.exports = ABTestingEngine;