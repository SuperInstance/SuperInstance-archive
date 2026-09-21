import EventEmitter from 'events';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default class AssemblerMatcher extends EventEmitter {
    constructor(logger) {
        super();
        this.logger = logger;
        this.assemblers = new Map();
        this.skillDatabase = new Map();
        this.certificationRequirements = new Map();
        this.projectHistory = new Map();
        this.ratingSystem = new Map();
        this.availabilityCalendar = new Map();
        this.matchingAlgorithms = new Map();
        this.pricingModels = new Map();
        this.qualityMetrics = new Map();
        
        this.initializeAssemblers();
        this.initializeSkillDatabase();
        this.initializeCertificationRequirements();
        this.initializeMatchingAlgorithms();
        this.initializePricingModels();
    }

    async initializeAssemblers() {
        try {
            const assemblersPath = path.join(__dirname, '../data/assemblers.json');
            const assemblersData = await fs.readFile(assemblersPath, 'utf8');
            const assemblers = JSON.parse(assemblersData);
            
            for (const assembler of assemblers) {
                this.assemblers.set(assembler.id, assembler);
                this.initializeAssemblerMetrics(assembler);
            }
            
            this.logger.info(`Loaded ${this.assemblers.size} assemblers`);
        } catch (error) {
            this.logger.warn('Could not load assemblers file, using defaults');
            this.loadDefaultAssemblers();
        }
    }

    loadDefaultAssemblers() {
        const defaultAssemblers = [
            {
                id: 'assembler_001',
                name: 'TechCraft Solutions',
                type: 'professional_service',
                location: {
                    address: '123 Industrial Ave',
                    city: 'San Jose',
                    state: 'CA',
                    zip_code: '95110',
                    coordinates: { lat: 37.3541, lng: -121.9552 }
                },
                contact: {
                    phone: '+1-408-555-0123',
                    email: 'info@techcraft.com',
                    website: 'https://techcraft.com',
                    business_hours: '8:00 AM - 6:00 PM PST'
                },
                specialties: ['electronics', 'pcb_assembly', 'prototype_development', 'small_batch_production'],
                skills: ['smt_assembly', 'through_hole_soldering', 'bga_rework', 'ict_testing', 'functional_testing'],
                certifications: ['IPC_A_610', 'ISO_9001', 'IPC_J_STD_001', 'UL_Listed_Shop'],
                equipment: [
                    'pick_and_place_machines',
                    'reflow_ovens',
                    'wave_soldering',
                    'aoi_systems',
                    'x_ray_inspection'
                ],
                capacity: {
                    simultaneous_projects: 15,
                    monthly_volume: 10000,
                    min_order_quantity: 1,
                    max_order_quantity: 50000
                },
                pricing: {
                    setup_fee: 150,
                    per_unit_base: 2.50,
                    rush_multiplier: 1.75,
                    complexity_factors: {
                        simple: 1.0,
                        moderate: 1.4,
                        complex: 2.1,
                        highly_complex: 3.2
                    }
                },
                lead_times: {
                    prototype: '3-5 days',
                    small_batch: '1-2 weeks',
                    production: '2-4 weeks',
                    rush: '24-48 hours'
                },
                quality_ratings: {
                    overall: 4.8,
                    timeliness: 4.9,
                    communication: 4.7,
                    technical_quality: 4.9,
                    pricing_fairness: 4.6
                },
                availability_status: 'available',
                current_workload: 0.75
            },
            {
                id: 'assembler_002',
                name: 'Precision Assembly Works',
                type: 'specialty_manufacturer',
                location: {
                    address: '456 Manufacturing Blvd',
                    city: 'Austin',
                    state: 'TX',
                    zip_code: '78701',
                    coordinates: { lat: 30.2672, lng: -97.7431 }
                },
                contact: {
                    phone: '+1-512-555-0156',
                    email: 'orders@precisionworks.com',
                    website: 'https://precisionworks.com',
                    business_hours: '7:00 AM - 7:00 PM CST'
                },
                specialties: ['mechanical_assembly', 'precision_machining', 'custom_enclosures', 'cable_harnesses'],
                skills: ['cnc_machining', 'precision_drilling', 'mechanical_fitting', 'quality_inspection', 'custom_tooling'],
                certifications: ['AS9100', 'ISO_9001', 'ITAR_Registered', 'NIST_Traceable'],
                equipment: [
                    'cnc_mills',
                    'cnc_lathes',
                    'coordinate_measuring_machines',
                    'laser_cutting',
                    'waterjet_cutting'
                ],
                capacity: {
                    simultaneous_projects: 8,
                    monthly_volume: 5000,
                    min_order_quantity: 1,
                    max_order_quantity: 25000
                },
                pricing: {
                    setup_fee: 300,
                    per_unit_base: 8.75,
                    rush_multiplier: 2.0,
                    complexity_factors: {
                        simple: 1.0,
                        moderate: 1.6,
                        complex: 2.5,
                        highly_complex: 4.0
                    }
                },
                lead_times: {
                    prototype: '5-7 days',
                    small_batch: '2-3 weeks',
                    production: '4-6 weeks',
                    rush: '2-3 days'
                },
                quality_ratings: {
                    overall: 4.9,
                    timeliness: 4.8,
                    communication: 4.9,
                    technical_quality: 5.0,
                    pricing_fairness: 4.7
                },
                availability_status: 'limited',
                current_workload: 0.85
            },
            {
                id: 'assembler_003',
                name: 'QuickTurn Electronics',
                type: 'rapid_prototyping',
                location: {
                    address: '789 Tech Park Dr',
                    city: 'Seattle',
                    state: 'WA',
                    zip_code: '98101',
                    coordinates: { lat: 47.6062, lng: -122.3321 }
                },
                contact: {
                    phone: '+1-206-555-0189',
                    email: 'rapid@quickturn.com',
                    website: 'https://quickturn.com',
                    business_hours: '24/7 Support Available'
                },
                specialties: ['rapid_prototyping', 'same_day_assembly', 'pcb_prototyping', 'design_consultation'],
                skills: ['rapid_assembly', 'prototype_debugging', 'design_review', 'quick_turnaround'],
                certifications: ['IPC_A_610', 'ISO_14001', 'RoHS_Compliant'],
                equipment: [
                    'desktop_pick_place',
                    'desktop_reflow',
                    'hand_soldering_stations',
                    'microscopes',
                    'basic_test_equipment'
                ],
                capacity: {
                    simultaneous_projects: 25,
                    monthly_volume: 2000,
                    min_order_quantity: 1,
                    max_order_quantity: 100
                },
                pricing: {
                    setup_fee: 75,
                    per_unit_base: 15.00,
                    rush_multiplier: 1.5,
                    complexity_factors: {
                        simple: 1.0,
                        moderate: 1.3,
                        complex: 1.8,
                        highly_complex: 2.5
                    }
                },
                lead_times: {
                    prototype: '4-8 hours',
                    small_batch: '1-2 days',
                    production: '1 week',
                    rush: '2-4 hours'
                },
                quality_ratings: {
                    overall: 4.5,
                    timeliness: 4.9,
                    communication: 4.6,
                    technical_quality: 4.3,
                    pricing_fairness: 4.2
                },
                availability_status: 'available',
                current_workload: 0.45,
                rush_capable: true
            },
            {
                id: 'assembler_004',
                name: 'Industrial Assembly Co',
                type: 'high_volume_manufacturer',
                location: {
                    address: '321 Factory Row',
                    city: 'Detroit',
                    state: 'MI',
                    zip_code: '48201',
                    coordinates: { lat: 42.3314, lng: -83.0458 }
                },
                contact: {
                    phone: '+1-313-555-0245',
                    email: 'production@industrial-asm.com',
                    website: 'https://industrial-asm.com',
                    business_hours: '6:00 AM - 10:00 PM EST'
                },
                specialties: ['high_volume_production', 'automotive_assembly', 'industrial_controls', 'supply_chain_management'],
                skills: ['mass_production', 'lean_manufacturing', 'six_sigma', 'supply_chain', 'quality_systems'],
                certifications: ['TS_16949', 'ISO_9001', 'ISO_14001', 'OHSAS_18001'],
                equipment: [
                    'automated_assembly_lines',
                    'industrial_robots',
                    'conveyor_systems',
                    'automated_testing',
                    'packaging_automation'
                ],
                capacity: {
                    simultaneous_projects: 5,
                    monthly_volume: 100000,
                    min_order_quantity: 1000,
                    max_order_quantity: 1000000
                },
                pricing: {
                    setup_fee: 5000,
                    per_unit_base: 0.85,
                    rush_multiplier: 1.25,
                    volume_discounts: {
                        tier_10k: 0.9,
                        tier_50k: 0.75,
                        tier_100k: 0.65,
                        tier_500k: 0.55
                    }
                },
                lead_times: {
                    prototype: '2-3 weeks',
                    small_batch: '4-6 weeks',
                    production: '8-12 weeks',
                    rush: '50% time reduction'
                },
                quality_ratings: {
                    overall: 4.7,
                    timeliness: 4.6,
                    communication: 4.5,
                    technical_quality: 4.8,
                    pricing_fairness: 4.8
                },
                availability_status: 'busy',
                current_workload: 0.95,
                high_volume_specialist: true
            }
        ];

        defaultAssemblers.forEach(assembler => {
            this.assemblers.set(assembler.id, assembler);
            this.initializeAssemblerMetrics(assembler);
        });
    }

    initializeAssemblerMetrics(assembler) {
        this.ratingSystem.set(assembler.id, {
            total_projects: Math.floor(Math.random() * 500) + 100,
            completed_on_time: Math.floor(Math.random() * 90) + 85,
            customer_satisfaction: assembler.quality_ratings.overall,
            repeat_customers: Math.floor(Math.random() * 40) + 60,
            defect_rate: Math.random() * 0.05,
            rework_rate: Math.random() * 0.03
        });

        this.availabilityCalendar.set(assembler.id, this.generateAvailabilityCalendar());
    }

    generateAvailabilityCalendar() {
        const calendar = new Map();
        const today = new Date();
        
        for (let i = 0; i < 90; i++) {
            const date = new Date(today);
            date.setDate(today.getDate() + i);
            
            calendar.set(date.toISOString().split('T')[0], {
                available_capacity: Math.random() * 0.8 + 0.2,
                booked_hours: Math.floor(Math.random() * 16),
                rush_available: Math.random() > 0.7
            });
        }
        
        return calendar;
    }

    initializeSkillDatabase() {
        const skills = [
            {
                id: 'smt_assembly',
                name: 'Surface Mount Technology Assembly',
                category: 'electronics',
                difficulty: 'intermediate',
                required_certifications: ['IPC_A_610'],
                typical_hourly_rate: 45
            },
            {
                id: 'through_hole_soldering',
                name: 'Through-Hole Soldering',
                category: 'electronics',
                difficulty: 'beginner',
                required_certifications: ['IPC_J_STD_001'],
                typical_hourly_rate: 35
            },
            {
                id: 'bga_rework',
                name: 'Ball Grid Array Rework',
                category: 'electronics',
                difficulty: 'expert',
                required_certifications: ['IPC_A_610', 'IPC_7711'],
                typical_hourly_rate: 85
            },
            {
                id: 'cnc_machining',
                name: 'CNC Machining',
                category: 'mechanical',
                difficulty: 'advanced',
                required_certifications: ['NIMS_Certified'],
                typical_hourly_rate: 65
            },
            {
                id: 'precision_drilling',
                name: 'Precision Drilling',
                category: 'mechanical',
                difficulty: 'intermediate',
                required_certifications: [],
                typical_hourly_rate: 50
            },
            {
                id: 'quality_inspection',
                name: 'Quality Inspection',
                category: 'quality_control',
                difficulty: 'intermediate',
                required_certifications: ['ASQ_CQI'],
                typical_hourly_rate: 55
            }
        ];

        skills.forEach(skill => {
            this.skillDatabase.set(skill.id, skill);
        });
    }

    initializeCertificationRequirements() {
        const certifications = [
            {
                id: 'IPC_A_610',
                name: 'IPC-A-610 Acceptability of Electronic Assemblies',
                category: 'electronics',
                renewal_period: '24 months',
                skill_areas: ['smt_assembly', 'through_hole_soldering', 'inspection']
            },
            {
                id: 'IPC_J_STD_001',
                name: 'IPC J-STD-001 Soldering Requirements',
                category: 'electronics',
                renewal_period: '24 months',
                skill_areas: ['soldering', 'rework', 'quality_control']
            },
            {
                id: 'AS9100',
                name: 'AS9100 Aerospace Quality Management',
                category: 'quality',
                renewal_period: '36 months',
                skill_areas: ['aerospace_assembly', 'quality_systems', 'documentation']
            },
            {
                id: 'ISO_9001',
                name: 'ISO 9001 Quality Management',
                category: 'quality',
                renewal_period: '36 months',
                skill_areas: ['quality_systems', 'process_control', 'continuous_improvement']
            }
        ];

        certifications.forEach(cert => {
            this.certificationRequirements.set(cert.id, cert);
        });
    }

    initializeMatchingAlgorithms() {
        this.matchingAlgorithms.set('skill_based', (project, assemblers) => {
            return assemblers.map(assembler => {
                const skillMatch = this.calculateSkillMatch(project.required_skills, assembler.skills);
                const certMatch = this.calculateCertificationMatch(project.required_certifications, assembler.certifications);
                const score = (skillMatch * 0.7) + (certMatch * 0.3);
                
                return {
                    assembler,
                    match_score: score,
                    skill_match: skillMatch,
                    certification_match: certMatch
                };
            }).sort((a, b) => b.match_score - a.match_score);
        });

        this.matchingAlgorithms.set('geographic', (project, assemblers) => {
            const projectLocation = project.preferred_location || project.shipping_address;
            
            return assemblers.map(assembler => {
                const distance = this.calculateDistance(projectLocation, assembler.location);
                const proximityScore = Math.max(0, 1 - (distance / 1000)); // Normalize to 1000 miles
                
                return {
                    assembler,
                    match_score: proximityScore,
                    distance_miles: distance
                };
            }).sort((a, b) => b.match_score - a.match_score);
        });

        this.matchingAlgorithms.set('cost_optimized', (project, assemblers) => {
            return assemblers.map(assembler => {
                const estimatedCost = this.estimateProjectCost(project, assembler);
                const maxCost = Math.max(...assemblers.map(a => this.estimateProjectCost(project, a)));
                const costScore = 1 - (estimatedCost / maxCost);
                
                return {
                    assembler,
                    match_score: costScore,
                    estimated_cost: estimatedCost
                };
            }).sort((a, b) => b.match_score - a.match_score);
        });

        this.matchingAlgorithms.set('timeline_optimized', (project, assemblers) => {
            return assemblers.map(assembler => {
                const estimatedLeadTime = this.estimateLeadTime(project, assembler);
                const maxLeadTime = Math.max(...assemblers.map(a => this.estimateLeadTime(project, a)));
                const timeScore = 1 - (estimatedLeadTime / maxLeadTime);
                
                return {
                    assembler,
                    match_score: timeScore,
                    estimated_lead_time_days: estimatedLeadTime
                };
            }).sort((a, b) => b.match_score - a.match_score);
        });

        this.matchingAlgorithms.set('quality_focused', (project, assemblers) => {
            return assemblers.map(assembler => {
                const qualityScore = this.calculateQualityScore(assembler);
                
                return {
                    assembler,
                    match_score: qualityScore,
                    quality_metrics: this.ratingSystem.get(assembler.id)
                };
            }).sort((a, b) => b.match_score - a.match_score);
        });
    }

    initializePricingModels() {
        this.pricingModels.set('per_unit', (project, assembler) => {
            const basePrice = assembler.pricing.per_unit_base;
            const complexity = project.complexity || 'moderate';
            const complexityMultiplier = assembler.pricing.complexity_factors[complexity] || 1.4;
            const rushMultiplier = project.rush_order ? assembler.pricing.rush_multiplier : 1.0;
            
            return {
                unit_cost: basePrice * complexityMultiplier * rushMultiplier,
                setup_fee: assembler.pricing.setup_fee || 0,
                total_cost: (basePrice * complexityMultiplier * rushMultiplier * project.quantity) + (assembler.pricing.setup_fee || 0)
            };
        });

        this.pricingModels.set('hourly_rate', (project, assembler) => {
            const estimatedHours = this.estimateAssemblyHours(project, assembler);
            const hourlyRate = this.calculateHourlyRate(assembler, project);
            
            return {
                hourly_rate: hourlyRate,
                estimated_hours: estimatedHours,
                total_cost: estimatedHours * hourlyRate
            };
        });

        this.pricingModels.set('fixed_project', (project, assembler) => {
            const baseProjectCost = this.calculateBaseProjectCost(project, assembler);
            const complexityAdjustment = this.getComplexityAdjustment(project.complexity);
            
            return {
                base_cost: baseProjectCost,
                complexity_adjustment: complexityAdjustment,
                total_cost: baseProjectCost * complexityAdjustment
            };
        });
    }

    async findAssemblers(projectRequirements, options = {}) {
        try {
            const {
                algorithm = 'skill_based',
                max_results = 10,
                location_preference,
                budget_limit,
                timeline_requirement,
                quality_minimum = 4.0
            } = options;

            // Filter assemblers based on basic criteria
            let eligibleAssemblers = Array.from(this.assemblers.values()).filter(assembler => {
                // Quality filter
                if (assembler.quality_ratings.overall < quality_minimum) return false;
                
                // Capacity filter
                if (projectRequirements.quantity > assembler.capacity.max_order_quantity) return false;
                if (projectRequirements.quantity < assembler.capacity.min_order_quantity) return false;
                
                // Availability filter
                if (assembler.availability_status === 'unavailable') return false;
                
                // Timeline filter
                if (timeline_requirement) {
                    const estimatedTime = this.estimateLeadTime(projectRequirements, assembler);
                    if (estimatedTime > this.parseTimeRequirement(timeline_requirement)) return false;
                }
                
                return true;
            });

            // Apply matching algorithm
            const matchingAlgorithm = this.matchingAlgorithms.get(algorithm);
            if (!matchingAlgorithm) {
                throw new Error(`Unknown matching algorithm: ${algorithm}`);
            }

            let matches = matchingAlgorithm(projectRequirements, eligibleAssemblers);

            // Apply budget filter if specified
            if (budget_limit) {
                matches = matches.filter(match => {
                    const estimatedCost = this.estimateProjectCost(projectRequirements, match.assembler);
                    return estimatedCost <= budget_limit;
                });
            }

            // Limit results
            matches = matches.slice(0, max_results);

            // Enhance matches with additional information
            const enhancedMatches = await Promise.all(matches.map(async match => {
                return await this.enhanceMatch(match, projectRequirements, options);
            }));

            const result = {
                total_found: eligibleAssemblers.length,
                matches: enhancedMatches,
                search_criteria: {
                    algorithm,
                    project_requirements: projectRequirements,
                    options
                },
                timestamp: new Date()
            };

            this.emit('assemblers_matched', {
                project_id: projectRequirements.project_id,
                matches_found: enhancedMatches.length,
                algorithm_used: algorithm
            });

            this.logger.info(`Found ${enhancedMatches.length} assembler matches using ${algorithm} algorithm`);

            return result;

        } catch (error) {
            this.logger.error('Assembler matching failed:', error);
            throw error;
        }
    }

    async enhanceMatch(match, projectRequirements, options) {
        const assembler = match.assembler;
        
        const enhancedMatch = {
            ...match,
            cost_estimate: this.estimateProjectCost(projectRequirements, assembler),
            timeline_estimate: this.estimateLeadTime(projectRequirements, assembler),
            availability: await this.checkAvailability(assembler.id, projectRequirements.timeline),
            capabilities_analysis: this.analyzeCapabilities(assembler, projectRequirements),
            risk_assessment: this.assessRisks(assembler, projectRequirements),
            recommendations: this.generateRecommendations(assembler, projectRequirements),
            contact_information: this.getContactInfo(assembler),
            portfolio_samples: await this.getPortfolioSamples(assembler.id, projectRequirements.type)
        };

        return enhancedMatch;
    }

    calculateSkillMatch(requiredSkills, assemblerSkills) {
        if (!requiredSkills || requiredSkills.length === 0) return 1.0;
        
        const matchedSkills = requiredSkills.filter(skill => assemblerSkills.includes(skill));
        return matchedSkills.length / requiredSkills.length;
    }

    calculateCertificationMatch(requiredCerts, assemblerCerts) {
        if (!requiredCerts || requiredCerts.length === 0) return 1.0;
        
        const matchedCerts = requiredCerts.filter(cert => assemblerCerts.includes(cert));
        return matchedCerts.length / requiredCerts.length;
    }

    calculateDistance(location1, location2) {
        if (!location1 || !location2) return 1000; // Default high distance
        
        // Use coordinates if available, otherwise fall back to ZIP code estimation
        if (location1.coordinates && location2.coordinates) {
            return this.calculateHaversineDistance(location1.coordinates, location2.coordinates);
        } else {
            return this.estimateDistanceFromZip(location1.zip_code, location2.zip_code);
        }
    }

    calculateHaversineDistance(coord1, coord2) {
        const R = 3959; // Earth's radius in miles
        const dLat = this.toRadians(coord2.lat - coord1.lat);
        const dLng = this.toRadians(coord2.lng - coord1.lng);
        
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                  Math.cos(this.toRadians(coord1.lat)) * Math.cos(this.toRadians(coord2.lat)) *
                  Math.sin(dLng / 2) * Math.sin(dLng / 2);
        
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }

    toRadians(degrees) {
        return degrees * (Math.PI / 180);
    }

    estimateDistanceFromZip(zip1, zip2) {
        if (!zip1 || !zip2) return 1000;
        
        const zipNum1 = parseInt(zip1.replace(/\D/g, ''));
        const zipNum2 = parseInt(zip2.replace(/\D/g, ''));
        
        return Math.abs(zipNum1 - zipNum2) / 100; // Rough estimation
    }

    estimateProjectCost(project, assembler) {
        const pricingModel = assembler.pricing_model || 'per_unit';
        const calculator = this.pricingModels.get(pricingModel);
        
        if (calculator) {
            return calculator(project, assembler).total_cost;
        }
        
        // Fallback calculation
        const baseUnitCost = assembler.pricing.per_unit_base || 5.00;
        const complexity = project.complexity || 'moderate';
        const complexityMultiplier = assembler.pricing.complexity_factors?.[complexity] || 1.4;
        const setupFee = assembler.pricing.setup_fee || 0;
        
        return (baseUnitCost * complexityMultiplier * project.quantity) + setupFee;
    }

    estimateLeadTime(project, assembler) {
        const projectType = project.type || 'small_batch';
        const baseLeadTime = assembler.lead_times[projectType] || assembler.lead_times.small_batch || '1-2 weeks';
        
        let days = this.parseLeadTimeToDays(baseLeadTime);
        
        // Adjust for current workload
        const workloadMultiplier = 1 + (assembler.current_workload * 0.5);
        days *= workloadMultiplier;
        
        // Adjust for complexity
        const complexityAdjustment = this.getComplexityTimeAdjustment(project.complexity);
        days *= complexityAdjustment;
        
        // Adjust for rush orders
        if (project.rush_order && assembler.rush_capable) {
            days *= 0.5;
        }
        
        return Math.ceil(days);
    }

    parseLeadTimeToDays(leadTime) {
        if (!leadTime) return 7;
        
        const text = leadTime.toLowerCase();
        
        if (text.includes('hours')) {
            const hours = parseInt(text.match(/\d+/)?.[0] || '8');
            return Math.ceil(hours / 8);
        }
        
        if (text.includes('same day')) return 1;
        if (text.includes('1-2 days')) return 1.5;
        if (text.includes('3-5 days')) return 4;
        if (text.includes('1-2 weeks')) return 10;
        if (text.includes('2-3 weeks')) return 17;
        if (text.includes('2-4 weeks')) return 21;
        if (text.includes('4-6 weeks')) return 35;
        if (text.includes('8-12 weeks')) return 70;
        
        // Try to extract number of weeks/days
        const weekMatch = text.match(/(\d+)(?:-(\d+))?\s*weeks?/);
        if (weekMatch) {
            const minWeeks = parseInt(weekMatch[1]);
            const maxWeeks = parseInt(weekMatch[2]) || minWeeks;
            return (minWeeks + maxWeeks) / 2 * 7;
        }
        
        const dayMatch = text.match(/(\d+)(?:-(\d+))?\s*days?/);
        if (dayMatch) {
            const minDays = parseInt(dayMatch[1]);
            const maxDays = parseInt(dayMatch[2]) || minDays;
            return (minDays + maxDays) / 2;
        }
        
        return 7; // Default to 1 week
    }

    getComplexityTimeAdjustment(complexity) {
        const adjustments = {
            simple: 0.8,
            moderate: 1.0,
            complex: 1.4,
            highly_complex: 2.0
        };
        
        return adjustments[complexity] || 1.0;
    }

    parseTimeRequirement(requirement) {
        // Convert various time requirements to days
        if (typeof requirement === 'number') return requirement;
        
        const text = requirement.toLowerCase();
        if (text.includes('asap') || text.includes('urgent')) return 1;
        if (text.includes('rush')) return 3;
        if (text.includes('week')) {
            const weeks = parseInt(text.match(/\d+/)?.[0] || '1');
            return weeks * 7;
        }
        if (text.includes('day')) {
            return parseInt(text.match(/\d+/)?.[0] || '7');
        }
        
        return 30; // Default to 30 days
    }

    calculateQualityScore(assembler) {
        const ratings = assembler.quality_ratings;
        const metrics = this.ratingSystem.get(assembler.id);
        
        if (!ratings || !metrics) return 0.5;
        
        const overallRating = ratings.overall / 5.0;
        const onTimePerformance = metrics.completed_on_time / 100.0;
        const defectScore = 1 - (metrics.defect_rate * 10); // Assume defect rate is small percentage
        const reworkScore = 1 - (metrics.rework_rate * 10);
        
        return (overallRating * 0.4) + (onTimePerformance * 0.3) + (defectScore * 0.15) + (reworkScore * 0.15);
    }

    async checkAvailability(assemblerId, timeline) {
        const calendar = this.availabilityCalendar.get(assemblerId);
        const assembler = this.assemblers.get(assemblerId);
        
        if (!calendar || !assembler) return { available: false, reason: 'Assembler not found' };
        
        const startDate = new Date();
        const timelineDays = this.parseTimeRequirement(timeline || '2 weeks');
        const endDate = new Date(startDate.getTime() + (timelineDays * 24 * 60 * 60 * 1000));
        
        let totalCapacityNeeded = 0;
        let availableCapacity = 0;
        let conflictDates = [];
        
        for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
            const dateKey = d.toISOString().split('T')[0];
            const dayCapacity = calendar.get(dateKey);
            
            if (dayCapacity) {
                totalCapacityNeeded += 1;
                if (dayCapacity.available_capacity > 0.3) {
                    availableCapacity += dayCapacity.available_capacity;
                } else {
                    conflictDates.push(dateKey);
                }
            }
        }
        
        const capacityRatio = availableCapacity / totalCapacityNeeded;
        
        return {
            available: capacityRatio > 0.6,
            capacity_ratio: capacityRatio,
            conflict_dates: conflictDates,
            earliest_start: startDate.toISOString().split('T')[0],
            estimated_completion: endDate.toISOString().split('T')[0],
            current_workload: assembler.current_workload
        };
    }

    analyzeCapabilities(assembler, projectRequirements) {
        const analysis = {
            skill_coverage: this.calculateSkillCoverage(assembler.skills, projectRequirements.required_skills),
            equipment_match: this.analyzeEquipmentMatch(assembler.equipment, projectRequirements.required_equipment),
            capacity_fit: this.analyzeCapacityFit(assembler.capacity, projectRequirements),
            specialty_alignment: this.analyzeSpecialtyAlignment(assembler.specialties, projectRequirements.project_type),
            certification_compliance: this.analyzeCertificationCompliance(assembler.certifications, projectRequirements.required_certifications)
        };

        analysis.overall_capability_score = this.calculateOverallCapabilityScore(analysis);
        
        return analysis;
    }

    calculateSkillCoverage(assemblerSkills, requiredSkills) {
        if (!requiredSkills || requiredSkills.length === 0) {
            return { coverage: 1.0, missing_skills: [], extra_skills: assemblerSkills };
        }
        
        const missingSkills = requiredSkills.filter(skill => !assemblerSkills.includes(skill));
        const extraSkills = assemblerSkills.filter(skill => !requiredSkills.includes(skill));
        const coverage = (requiredSkills.length - missingSkills.length) / requiredSkills.length;
        
        return {
            coverage,
            missing_skills: missingSkills,
            extra_skills: extraSkills,
            skill_gaps: missingSkills.map(skill => ({
                skill,
                criticality: this.getSkillCriticality(skill),
                alternatives: this.findSkillAlternatives(skill, assemblerSkills)
            }))
        };
    }

    analyzeEquipmentMatch(assemblerEquipment, requiredEquipment) {
        if (!requiredEquipment || requiredEquipment.length === 0) {
            return { match: 1.0, missing_equipment: [], extra_equipment: assemblerEquipment };
        }
        
        const missingEquipment = requiredEquipment.filter(equip => !assemblerEquipment.includes(equip));
        const match = (requiredEquipment.length - missingEquipment.length) / requiredEquipment.length;
        
        return {
            match,
            missing_equipment: missingEquipment,
            equipment_gaps: missingEquipment.map(equip => ({
                equipment: equip,
                alternatives: this.findEquipmentAlternatives(equip, assemblerEquipment),
                outsourcing_options: this.findOutsourcingOptions(equip)
            }))
        };
    }

    analyzeCapacityFit(assemblerCapacity, projectRequirements) {
        const quantity = projectRequirements.quantity || 1;
        const timeline = this.parseTimeRequirement(projectRequirements.timeline || '2 weeks');
        
        return {
            quantity_fit: {
                within_range: quantity >= assemblerCapacity.min_order_quantity && quantity <= assemblerCapacity.max_order_quantity,
                min_quantity: assemblerCapacity.min_order_quantity,
                max_quantity: assemblerCapacity.max_order_quantity,
                requested_quantity: quantity
            },
            volume_capacity: {
                monthly_capacity: assemblerCapacity.monthly_volume,
                project_percentage: (quantity / assemblerCapacity.monthly_volume) * 100,
                capacity_utilization: 'low' // Would calculate based on current bookings
            },
            timeline_feasibility: {
                requested_timeline_days: timeline,
                capacity_available: assemblerCapacity.simultaneous_projects > 1,
                concurrent_project_impact: this.calculateConcurrentProjectImpact(assemblerCapacity)
            }
        };
    }

    analyzeSpecialtyAlignment(assemblerSpecialties, projectType) {
        const relevantSpecialties = assemblerSpecialties.filter(specialty => 
            this.isSpecialtyRelevant(specialty, projectType)
        );
        
        return {
            relevant_specialties: relevantSpecialties,
            specialty_match_score: relevantSpecialties.length / Math.max(assemblerSpecialties.length, 1),
            primary_specialty_match: assemblerSpecialties[0] === projectType,
            specialty_recommendations: this.getSpecialtyRecommendations(assemblerSpecialties, projectType)
        };
    }

    analyzeCertificationCompliance(assemblerCerts, requiredCerts) {
        if (!requiredCerts || requiredCerts.length === 0) {
            return { compliant: true, missing_certifications: [] };
        }
        
        const missingCerts = requiredCerts.filter(cert => !assemblerCerts.includes(cert));
        
        return {
            compliant: missingCerts.length === 0,
            missing_certifications: missingCerts,
            compliance_score: (requiredCerts.length - missingCerts.length) / requiredCerts.length,
            certification_gaps: missingCerts.map(cert => ({
                certification: cert,
                criticality: this.getCertificationCriticality(cert),
                acquisition_timeline: this.getCertificationAcquisitionTime(cert),
                alternatives: this.findCertificationAlternatives(cert, assemblerCerts)
            }))
        };
    }

    calculateOverallCapabilityScore(analysis) {
        const weights = {
            skill_coverage: 0.30,
            equipment_match: 0.25,
            capacity_fit: 0.20,
            specialty_alignment: 0.15,
            certification_compliance: 0.10
        };
        
        let totalScore = 0;
        totalScore += analysis.skill_coverage.coverage * weights.skill_coverage;
        totalScore += analysis.equipment_match.match * weights.equipment_match;
        totalScore += (analysis.capacity_fit.quantity_fit.within_range ? 1 : 0.5) * weights.capacity_fit;
        totalScore += analysis.specialty_alignment.specialty_match_score * weights.specialty_alignment;
        totalScore += analysis.certification_compliance.compliance_score * weights.certification_compliance;
        
        return Math.min(1.0, totalScore);
    }

    assessRisks(assembler, projectRequirements) {
        const risks = [];
        
        // Capacity risk
        if (assembler.current_workload > 0.8) {
            risks.push({
                type: 'capacity_overload',
                severity: 'medium',
                description: 'High current workload may impact timeline',
                mitigation: 'Consider rush fees or extended timeline'
            });
        }
        
        // Quality risk based on complexity mismatch
        const complexityRisk = this.assessComplexityRisk(assembler, projectRequirements.complexity);
        if (complexityRisk) risks.push(complexityRisk);
        
        // Geographic risk
        const distance = this.calculateDistance(projectRequirements.shipping_address, assembler.location);
        if (distance > 500) {
            risks.push({
                type: 'logistics',
                severity: 'low',
                description: 'Long shipping distance may increase costs and transit time',
                mitigation: 'Consider regional alternatives or bulk shipping'
            });
        }
        
        // Skill gap risk
        const skillGaps = this.analyzeCapabilities(assembler, projectRequirements).skill_coverage.missing_skills;
        if (skillGaps.length > 0) {
            risks.push({
                type: 'skill_gap',
                severity: skillGaps.length > 2 ? 'high' : 'medium',
                description: `Missing ${skillGaps.length} required skills`,
                mitigation: 'Outsourcing or partner collaboration may be needed'
            });
        }
        
        return {
            total_risks: risks.length,
            risk_score: this.calculateRiskScore(risks),
            risks: risks,
            overall_risk_level: this.determineOverallRiskLevel(risks)
        };
    }

    generateRecommendations(assembler, projectRequirements) {
        const recommendations = [];
        
        // Cost optimization recommendations
        if (assembler.pricing.volume_discounts) {
            const currentTier = this.getCurrentPricingTier(projectRequirements.quantity, assembler);
            const nextTier = this.getNextPricingTier(projectRequirements.quantity, assembler);
            
            if (nextTier) {
                recommendations.push({
                    type: 'cost_optimization',
                    suggestion: `Increase quantity to ${nextTier.min_quantity} for ${((1 - nextTier.discount) * 100).toFixed(1)}% unit price`,
                    impact: 'Potential cost savings through volume discount',
                    action: 'Consider increasing order quantity'
                });
            }
        }
        
        // Timeline optimization recommendations
        if (projectRequirements.rush_order && assembler.rush_capable) {
            recommendations.push({
                type: 'timeline_optimization',
                suggestion: 'Rush processing available',
                impact: `Reduce timeline by up to 50% for ${assembler.pricing.rush_multiplier}x cost`,
                action: 'Evaluate rush order cost vs benefit'
            });
        }
        
        // Quality enhancement recommendations
        if (assembler.certifications.includes('ISO_9001')) {
            recommendations.push({
                type: 'quality_assurance',
                suggestion: 'ISO 9001 certified quality management',
                impact: 'Enhanced quality control and documentation',
                action: 'Request quality documentation package'
            });
        }
        
        return recommendations;
    }

    getContactInfo(assembler) {
        return {
            primary_contact: assembler.contact,
            business_hours: assembler.contact.business_hours,
            response_time: this.getTypicalResponseTime(assembler.id),
            preferred_communication: this.getPreferredCommunication(assembler.id),
            quote_request_process: this.getQuoteRequestProcess(assembler.id)
        };
    }

    async getPortfolioSamples(assemblerId, projectType) {
        // Mock portfolio samples - in real implementation, would query database
        const samples = [
            {
                project_id: 'sample_001',
                title: 'Similar Electronic Assembly Project',
                description: 'PCB assembly with SMT components',
                images: ['sample1.jpg', 'sample2.jpg'],
                complexity: 'moderate',
                quantity: 500,
                completion_time: '2 weeks'
            },
            {
                project_id: 'sample_002',
                title: 'Custom Enclosure Assembly',
                description: 'Precision mechanical assembly',
                images: ['sample3.jpg'],
                complexity: 'complex',
                quantity: 100,
                completion_time: '3 weeks'
            }
        ];
        
        return samples.filter(sample => sample.title.toLowerCase().includes(projectType?.toLowerCase() || ''));
    }

    // Helper methods for risk assessment and recommendations
    assessComplexityRisk(assembler, projectComplexity) {
        if (!projectComplexity) return null;
        
        const assemblerExperience = this.getComplexityExperience(assembler);
        const complexityScale = { simple: 1, moderate: 2, complex: 3, highly_complex: 4 };
        
        const projectLevel = complexityScale[projectComplexity] || 2;
        const assemblerLevel = complexityScale[assemblerExperience] || 2;
        
        if (projectLevel > assemblerLevel + 1) {
            return {
                type: 'complexity_mismatch',
                severity: 'high',
                description: 'Project complexity exceeds assembler typical experience level',
                mitigation: 'Request detailed capability assessment and references'
            };
        }
        
        return null;
    }

    getComplexityExperience(assembler) {
        // Determine assembler's typical complexity level based on equipment and certifications
        if (assembler.equipment.includes('automated_assembly_lines')) return 'highly_complex';
        if (assembler.certifications.includes('AS9100')) return 'complex';
        if (assembler.equipment.includes('pick_and_place_machines')) return 'moderate';
        return 'simple';
    }

    calculateRiskScore(risks) {
        const severityWeights = { low: 1, medium: 3, high: 9 };
        const totalRiskScore = risks.reduce((sum, risk) => sum + severityWeights[risk.severity], 0);
        return Math.min(1.0, totalRiskScore / 20); // Normalize to 0-1 scale
    }

    determineOverallRiskLevel(risks) {
        const highRisks = risks.filter(r => r.severity === 'high').length;
        const mediumRisks = risks.filter(r => r.severity === 'medium').length;
        
        if (highRisks > 0) return 'high';
        if (mediumRisks > 1) return 'medium';
        if (risks.length > 0) return 'low';
        return 'minimal';
    }

    // Helper methods for various calculations
    getSkillCriticality(skill) {
        const criticalSkills = ['bga_rework', 'precision_drilling', 'quality_inspection'];
        return criticalSkills.includes(skill) ? 'high' : 'medium';
    }

    findSkillAlternatives(skill, availableSkills) {
        const alternatives = {
            'bga_rework': ['fine_pitch_soldering', 'rework_specialist'],
            'cnc_machining': ['precision_drilling', 'manual_machining'],
            'smt_assembly': ['pick_place_operation', 'surface_mount']
        };
        
        return alternatives[skill]?.filter(alt => availableSkills.includes(alt)) || [];
    }

    findEquipmentAlternatives(equipment, availableEquipment) {
        const alternatives = {
            'pick_and_place_machines': ['manual_placement', 'semi_automated_placement'],
            'automated_testing': ['manual_testing', 'bench_testing'],
            'cnc_mills': ['manual_mills', 'machining_centers']
        };
        
        return alternatives[equipment]?.filter(alt => availableEquipment.includes(alt)) || [];
    }

    findOutsourcingOptions(equipment) {
        return [`Outsource ${equipment} operations to specialized vendor`];
    }

    calculateConcurrentProjectImpact(capacity) {
        if (capacity.simultaneous_projects <= 1) return 'high_impact';
        if (capacity.simultaneous_projects <= 5) return 'medium_impact';
        return 'low_impact';
    }

    isSpecialtyRelevant(specialty, projectType) {
        const relevanceMap = {
            'electronics': ['pcb_assembly', 'electronics', 'prototype_development'],
            'mechanical_assembly': ['mechanical', 'assembly', 'machining'],
            'rapid_prototyping': ['prototype', 'rapid', 'development']
        };
        
        return relevanceMap[specialty]?.some(keyword => 
            projectType?.toLowerCase().includes(keyword)) || false;
    }

    getSpecialtyRecommendations(assemblerSpecialties, projectType) {
        return assemblerSpecialties.map(specialty => ({
            specialty,
            relevance: this.isSpecialtyRelevant(specialty, projectType) ? 'high' : 'low',
            description: this.getSpecialtyDescription(specialty)
        }));
    }

    getSpecialtyDescription(specialty) {
        const descriptions = {
            'electronics': 'Electronic component assembly and PCB manufacturing',
            'mechanical_assembly': 'Precision mechanical parts assembly and fitting',
            'rapid_prototyping': 'Fast turnaround prototype development and testing',
            'high_volume_production': 'Large scale manufacturing with automated processes'
        };
        
        return descriptions[specialty] || 'Specialized manufacturing capability';
    }

    getCertificationCriticality(certification) {
        const criticalCertifications = ['AS9100', 'ITAR_Registered', 'FDA_Approved'];
        return criticalCertifications.includes(certification) ? 'high' : 'medium';
    }

    getCertificationAcquisitionTime(certification) {
        const timeframes = {
            'IPC_A_610': '2-4 weeks',
            'IPC_J_STD_001': '2-4 weeks',
            'ISO_9001': '3-6 months',
            'AS9100': '6-12 months'
        };
        
        return timeframes[certification] || '1-3 months';
    }

    findCertificationAlternatives(certification, availableCerts) {
        const alternatives = {
            'AS9100': ['ISO_9001'],
            'IPC_A_610': ['IPC_J_STD_001'],
            'ITAR_Registered': ['Export_Control_Compliant']
        };
        
        return alternatives[certification]?.filter(alt => availableCerts.includes(alt)) || [];
    }

    getCurrentPricingTier(quantity, assembler) {
        if (!assembler.pricing.volume_discounts) return null;
        
        let currentTier = null;
        for (const [tierName, tierDiscount] of Object.entries(assembler.pricing.volume_discounts)) {
            const minQuantity = parseInt(tierName.split('_')[1].replace('k', '000'));
            if (quantity >= minQuantity) {
                currentTier = { name: tierName, min_quantity: minQuantity, discount: tierDiscount };
            }
        }
        
        return currentTier;
    }

    getNextPricingTier(quantity, assembler) {
        if (!assembler.pricing.volume_discounts) return null;
        
        const tiers = Object.entries(assembler.pricing.volume_discounts)
            .map(([name, discount]) => ({
                name,
                min_quantity: parseInt(name.split('_')[1].replace('k', '000')),
                discount
            }))
            .sort((a, b) => a.min_quantity - b.min_quantity);
        
        return tiers.find(tier => tier.min_quantity > quantity);
    }

    getTypicalResponseTime(assemblerId) {
        // Mock response times based on assembler characteristics
        const assembler = this.assemblers.get(assemblerId);
        if (assembler?.type === 'rapid_prototyping') return '1-2 hours';
        if (assembler?.current_workload < 0.5) return '2-4 hours';
        if (assembler?.current_workload < 0.8) return '4-8 hours';
        return '1-2 business days';
    }

    getPreferredCommunication(assemblerId) {
        return ['email', 'phone', 'project_portal'];
    }

    getQuoteRequestProcess(assemblerId) {
        return {
            required_information: [
                'technical_drawings',
                'bill_of_materials',
                'quantity_requirements',
                'timeline_requirements',
                'quality_specifications'
            ],
            typical_quote_time: '24-48 hours',
            quote_validity: '30 days',
            revision_policy: 'Free revisions for specification changes'
        };
    }

    // Additional utility methods for pricing calculations
    estimateAssemblyHours(project, assembler) {
        const baseHours = project.quantity * 0.5; // Base 30 minutes per unit
        const complexityMultiplier = this.getComplexityTimeAdjustment(project.complexity);
        const efficiencyFactor = this.getAssemblerEfficiency(assembler);
        
        return Math.ceil(baseHours * complexityMultiplier / efficiencyFactor);
    }

    calculateHourlyRate(assembler, project) {
        const baseRate = assembler.hourly_rate || 45;
        const skillPremium = this.calculateSkillPremium(assembler.skills, project.required_skills);
        const certificationPremium = this.calculateCertificationPremium(assembler.certifications);
        
        return baseRate * (1 + skillPremium + certificationPremium);
    }

    calculateBaseProjectCost(project, assembler) {
        const complexity = project.complexity || 'moderate';
        const baseCosts = {
            simple: 500,
            moderate: 1500,
            complex: 4000,
            highly_complex: 10000
        };
        
        return baseCosts[complexity] * (assembler.cost_multiplier || 1.0);
    }

    getComplexityAdjustment(complexity) {
        const adjustments = {
            simple: 0.8,
            moderate: 1.0,
            complex: 1.5,
            highly_complex: 2.2
        };
        
        return adjustments[complexity] || 1.0;
    }

    getAssemblerEfficiency(assembler) {
        // Calculate efficiency based on ratings and equipment
        const baseEfficiency = assembler.quality_ratings?.overall / 5 || 0.8;
        const equipmentBonus = assembler.equipment.includes('automated_assembly_lines') ? 0.3 : 0;
        
        return Math.min(1.5, baseEfficiency + equipmentBonus);
    }

    calculateSkillPremium(assemblerSkills, requiredSkills) {
        if (!requiredSkills) return 0;
        
        const expertSkills = ['bga_rework', 'precision_machining', 'aerospace_assembly'];
        const expertSkillCount = assemblerSkills.filter(skill => expertSkills.includes(skill)).length;
        
        return expertSkillCount * 0.15; // 15% premium per expert skill
    }

    calculateCertificationPremium(certifications) {
        const premiumCerts = ['AS9100', 'ITAR_Registered', 'FDA_Approved'];
        const premiumCertCount = certifications.filter(cert => premiumCerts.includes(cert)).length;
        
        return premiumCertCount * 0.1; // 10% premium per premium certification
    }
}