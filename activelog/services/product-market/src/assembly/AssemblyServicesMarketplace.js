import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';

class AssemblyServicesMarketplace extends EventEmitter {
    constructor() {
        super();
        this.assemblers = new Map();
        this.assemblyServices = new Map();
        this.assemblyProjects = new Map();
        this.skillVerifications = new Map();
        this.qualityStandards = new Map();
        this.pricingModels = new Map();
        this.assemblyMetrics = {
            total_assemblers: 0,
            active_projects: 0,
            completion_rate: 0,
            average_quality_score: 0
        };
        this.initializeAssemblers();
        this.initializeAssemblyServices();
        this.initializeQualityStandards();
    }

    initializeAssemblers() {
        const assemblers = [
            {
                id: 'tech_innovations_inc',
                business_name: 'Tech Innovations Inc.',
                contact_person: 'Sarah Chen',
                location: {
                    city: 'San Jose',
                    state: 'California',
                    country: 'USA',
                    zip_code: '95110'
                },
                business_type: 'professional_service',
                certifications: ['IPC-A-610', 'ISO 9001', 'J-STD-001', 'RoHS Compliance'],
                specializations: [
                    'PCB Assembly',
                    'Surface Mount Technology (SMT)',
                    'Through-hole assembly',
                    'Cable and harness assembly',
                    'Product testing and validation'
                ],
                equipment: [
                    'Pick and place machines',
                    'Reflow ovens',
                    'Wave soldering equipment',
                    'AOI (Automated Optical Inspection)',
                    'In-circuit testing equipment',
                    'Environmental test chambers'
                ],
                capacity: {
                    max_projects_concurrent: 25,
                    min_order_quantity: 10,
                    max_order_quantity: 10000,
                    lead_time_days: { min: 5, max: 30 },
                    rush_order_available: true
                },
                experience: {
                    years_in_business: 12,
                    projects_completed: 1500,
                    industries_served: ['Electronics', 'Medical Devices', 'Automotive', 'IoT', 'Aerospace']
                },
                quality_metrics: {
                    defect_rate: 0.002, // 0.2%
                    on_time_delivery: 0.98,
                    customer_satisfaction: 4.8,
                    first_pass_yield: 0.995
                },
                pricing: {
                    setup_fee: 150,
                    per_unit_base: 2.50,
                    rush_order_multiplier: 1.5,
                    volume_discounts: [
                        { min_quantity: 100, discount: 0.05 },
                        { min_quantity: 500, discount: 0.10 },
                        { min_quantity: 1000, discount: 0.15 },
                        { min_quantity: 5000, discount: 0.20 }
                    ]
                },
                availability_schedule: {
                    current_capacity_used: 0.75,
                    next_available_slot: '2024-02-15',
                    booking_lead_time_days: 14
                }
            },
            {
                id: 'makers_workshop_collective',
                business_name: 'Makers Workshop Collective',
                contact_person: 'Mike Rodriguez',
                location: {
                    city: 'Austin',
                    state: 'Texas',
                    country: 'USA',
                    zip_code: '78701'
                },
                business_type: 'maker_space',
                certifications: ['Arduino Certified', 'Raspberry Pi Approved', 'STEM Education Certified'],
                specializations: [
                    'Prototype assembly',
                    'Educational kits',
                    'Small batch production',
                    '3D printed enclosures',
                    'Custom modifications'
                ],
                equipment: [
                    '3D printers (FDM and SLA)',
                    'Laser cutting equipment',
                    'Soldering stations',
                    'Hot air rework stations',
                    'Basic testing equipment'
                ],
                capacity: {
                    max_projects_concurrent: 8,
                    min_order_quantity: 1,
                    max_order_quantity: 100,
                    lead_time_days: { min: 3, max: 14 },
                    rush_order_available: true
                },
                experience: {
                    years_in_business: 5,
                    projects_completed: 350,
                    industries_served: ['Education', 'Prototyping', 'Art Projects', 'Hobbyist']
                },
                quality_metrics: {
                    defect_rate: 0.01, // 1%
                    on_time_delivery: 0.92,
                    customer_satisfaction: 4.6,
                    first_pass_yield: 0.88
                },
                pricing: {
                    setup_fee: 50,
                    per_unit_base: 8.00,
                    rush_order_multiplier: 1.3,
                    hourly_rate: 45,
                    volume_discounts: [
                        { min_quantity: 10, discount: 0.05 },
                        { min_quantity: 50, discount: 0.10 }
                    ]
                },
                availability_schedule: {
                    current_capacity_used: 0.40,
                    next_available_slot: '2024-02-05',
                    booking_lead_time_days: 5
                }
            },
            {
                id: 'precision_assembly_solutions',
                business_name: 'Precision Assembly Solutions',
                contact_person: 'Dr. Emily Watson',
                location: {
                    city: 'Boston',
                    state: 'Massachusetts',
                    country: 'USA',
                    zip_code: '02101'
                },
                business_type: 'specialized_contractor',
                certifications: ['ISO 13485', 'FDA Registered', 'AS9100', 'IPC-A-620'],
                specializations: [
                    'Medical device assembly',
                    'Aerospace components',
                    'High-reliability systems',
                    'Micro-assembly',
                    'Clean room assembly'
                ],
                equipment: [
                    'Class 10,000 clean room',
                    'Microscopic assembly stations',
                    'Ultrasonic welding equipment',
                    'Precision torque tools',
                    'Environmental stress testing',
                    'X-ray inspection equipment'
                ],
                capacity: {
                    max_projects_concurrent: 5,
                    min_order_quantity: 5,
                    max_order_quantity: 1000,
                    lead_time_days: { min: 10, max: 60 },
                    rush_order_available: false
                },
                experience: {
                    years_in_business: 18,
                    projects_completed: 800,
                    industries_served: ['Medical', 'Aerospace', 'Defense', 'Scientific Instruments']
                },
                quality_metrics: {
                    defect_rate: 0.0005, // 0.05%
                    on_time_delivery: 0.995,
                    customer_satisfaction: 4.95,
                    first_pass_yield: 0.999
                },
                pricing: {
                    setup_fee: 500,
                    per_unit_base: 15.00,
                    rush_order_multiplier: 'not_available',
                    hourly_rate: 125,
                    volume_discounts: [
                        { min_quantity: 50, discount: 0.03 },
                        { min_quantity: 200, discount: 0.06 },
                        { min_quantity: 500, discount: 0.10 }
                    ]
                },
                availability_schedule: {
                    current_capacity_used: 0.95,
                    next_available_slot: '2024-03-15',
                    booking_lead_time_days: 30
                }
            },
            {
                id: 'rapid_prototype_assembly',
                business_name: 'Rapid Prototype Assembly',
                contact_person: 'James Liu',
                location: {
                    city: 'Shenzhen',
                    state: 'Guangdong',
                    country: 'China',
                    zip_code: '518000'
                },
                business_type: 'contract_manufacturer',
                certifications: ['ISO 9001', 'IATF 16949', 'RoHS', 'REACH'],
                specializations: [
                    'Rapid prototyping',
                    'Low-volume production',
                    'Consumer electronics',
                    'IoT devices',
                    'Cost optimization'
                ],
                equipment: [
                    'High-speed SMT lines',
                    'Automated assembly lines',
                    'Injection molding',
                    'CNC machining',
                    'Comprehensive testing labs'
                ],
                capacity: {
                    max_projects_concurrent: 50,
                    min_order_quantity: 50,
                    max_order_quantity: 50000,
                    lead_time_days: { min: 7, max: 45 },
                    rush_order_available: true
                },
                experience: {
                    years_in_business: 8,
                    projects_completed: 2500,
                    industries_served: ['Consumer Electronics', 'IoT', 'Automotive', 'Telecommunications']
                },
                quality_metrics: {
                    defect_rate: 0.003, // 0.3%
                    on_time_delivery: 0.94,
                    customer_satisfaction: 4.4,
                    first_pass_yield: 0.96
                },
                pricing: {
                    setup_fee: 200,
                    per_unit_base: 1.80,
                    rush_order_multiplier: 1.4,
                    tooling_fee: 1500,
                    volume_discounts: [
                        { min_quantity: 200, discount: 0.08 },
                        { min_quantity: 1000, discount: 0.15 },
                        { min_quantity: 5000, discount: 0.25 },
                        { min_quantity: 20000, discount: 0.35 }
                    ]
                },
                availability_schedule: {
                    current_capacity_used: 0.65,
                    next_available_slot: '2024-02-20',
                    booking_lead_time_days: 10
                }
            },
            {
                id: 'student_assembly_program',
                business_name: 'University Student Assembly Program',
                contact_person: 'Prof. Alexandra Kim',
                location: {
                    city: 'Seattle',
                    state: 'Washington',
                    country: 'USA',
                    zip_code: '98195'
                },
                business_type: 'educational_service',
                certifications: ['ABET Accredited Program', 'IPC Student Certification'],
                specializations: [
                    'Educational projects',
                    'Student training',
                    'Simple electronics assembly',
                    'Learning-focused builds',
                    'Mentoring programs'
                ],
                equipment: [
                    'Student workbenches',
                    'Basic soldering equipment',
                    'Educational testing tools',
                    '3D printers',
                    'Component sorting systems'
                ],
                capacity: {
                    max_projects_concurrent: 15,
                    min_order_quantity: 5,
                    max_order_quantity: 200,
                    lead_time_days: { min: 14, max: 45 },
                    rush_order_available: false
                },
                experience: {
                    years_in_business: 3,
                    projects_completed: 120,
                    industries_served: ['Education', 'Research', 'Non-profit', 'Community Projects']
                },
                quality_metrics: {
                    defect_rate: 0.05, // 5%
                    on_time_delivery: 0.85,
                    customer_satisfaction: 4.2,
                    first_pass_yield: 0.75,
                    educational_value: 4.8
                },
                pricing: {
                    setup_fee: 25,
                    per_unit_base: 12.00,
                    rush_order_multiplier: 'not_available',
                    educational_discount: 0.30,
                    student_labor_rate: 15
                },
                availability_schedule: {
                    current_capacity_used: 0.30,
                    next_available_slot: '2024-02-12',
                    booking_lead_time_days: 21,
                    semester_schedule: 'Available during academic terms only'
                }
            }
        ];

        assemblers.forEach(assembler => {
            assembler.created_at = new Date();
            assembler.verified_at = new Date();
            assembler.verification_status = 'verified';
            assembler.rating = assembler.quality_metrics.customer_satisfaction;
            assembler.total_reviews = Math.floor(Math.random() * 100) + 20;
            assembler.response_time_hours = Math.floor(Math.random() * 24) + 2;
            assembler.languages = ['English'];
            
            if (assembler.location.country === 'China') {
                assembler.languages.push('Mandarin');
            }
            
            this.assemblers.set(assembler.id, assembler);
        });
    }

    initializeAssemblyServices() {
        const services = [
            {
                id: 'pcb_assembly_service',
                name: 'PCB Assembly Service',
                category: 'electronics_assembly',
                description: 'Professional PCB assembly with SMT and through-hole components',
                service_details: {
                    process_steps: [
                        'Design review and DFM analysis',
                        'Component procurement',
                        'Stencil creation',
                        'Solder paste application',
                        'Component placement',
                        'Reflow soldering',
                        'Through-hole insertion',
                        'Wave soldering',
                        'Cleaning and inspection',
                        'Testing and quality control'
                    ],
                    typical_lead_time: '5-20 business days',
                    minimum_quantity: 1,
                    maximum_quantity: 100000
                },
                pricing_structure: {
                    type: 'per_unit_plus_setup',
                    base_setup_cost: 150,
                    per_unit_cost_range: { min: 1.50, max: 25.00 },
                    factors_affecting_price: [
                        'Board complexity',
                        'Component count',
                        'Component types (SMT vs through-hole)',
                        'Order quantity',
                        'Lead time requirements',
                        'Testing requirements'
                    ]
                },
                quality_requirements: [
                    'IPC-A-610 Class 2 or 3 compliance',
                    'Visual inspection of all joints',
                    'In-circuit testing (if applicable)',
                    'Functional testing',
                    'Final quality audit'
                ],
                deliverables: [
                    'Assembled PCBs',
                    'Assembly documentation',
                    'Test reports',
                    'Certificate of conformance',
                    'Traceability records'
                ]
            },
            {
                id: 'mechanical_assembly_service',
                name: 'Mechanical Assembly Service',
                category: 'mechanical_assembly',
                description: 'Complete mechanical assembly of enclosures, brackets, and mechanical systems',
                service_details: {
                    process_steps: [
                        'Mechanical design review',
                        'Part preparation and sorting',
                        'Sub-assembly construction',
                        'Main assembly integration',
                        'Hardware installation',
                        'Adjustment and calibration',
                        'Functional testing',
                        'Final inspection'
                    ],
                    typical_lead_time: '3-15 business days',
                    minimum_quantity: 1,
                    maximum_quantity: 10000
                },
                pricing_structure: {
                    type: 'hourly_plus_materials',
                    hourly_rate_range: { min: 35, max: 85 },
                    material_markup: 0.15,
                    factors_affecting_price: [
                        'Assembly complexity',
                        'Number of parts',
                        'Tolerance requirements',
                        'Special tools required',
                        'Testing complexity'
                    ]
                },
                quality_requirements: [
                    'Dimensional verification',
                    'Torque specification compliance',
                    'Function testing',
                    'Visual inspection',
                    'Packaging requirements'
                ],
                deliverables: [
                    'Assembled products',
                    'Assembly procedures',
                    'Inspection records',
                    'Packaging and labeling'
                ]
            },
            {
                id: 'kit_fulfillment_service',
                name: 'DIY Kit Fulfillment Service',
                category: 'kit_assembly',
                description: 'Custom kit packaging and fulfillment for educational and hobbyist projects',
                service_details: {
                    process_steps: [
                        'Component sourcing',
                        'Inventory management',
                        'Kit specification review',
                        'Component counting and sorting',
                        'Custom packaging design',
                        'Assembly instruction creation',
                        'Quality control checking',
                        'Final packaging and shipping'
                    ],
                    typical_lead_time: '7-21 business days',
                    minimum_quantity: 10,
                    maximum_quantity: 50000
                },
                pricing_structure: {
                    type: 'per_kit_plus_setup',
                    setup_cost: 250,
                    per_kit_cost_range: { min: 2.00, max: 15.00 },
                    factors_affecting_price: [
                        'Number of components per kit',
                        'Component complexity',
                        'Custom packaging requirements',
                        'Documentation complexity',
                        'Order volume'
                    ]
                },
                quality_requirements: [
                    'Component count verification',
                    'Component quality inspection',
                    'Package integrity testing',
                    'Documentation accuracy',
                    'Random sampling inspection'
                ],
                deliverables: [
                    'Packaged kits',
                    'Assembly instructions',
                    'Component lists',
                    'Shipping documentation'
                ]
            },
            {
                id: 'prototype_assembly_service',
                name: 'Prototype Assembly Service',
                category: 'prototype_development',
                description: 'Rapid prototype assembly for product development and testing',
                service_details: {
                    process_steps: [
                        'Prototype design review',
                        'Component sourcing',
                        'Custom tooling/fixtures',
                        'Assembly process development',
                        'Prototype assembly',
                        'Initial testing',
                        'Design feedback',
                        'Documentation creation'
                    ],
                    typical_lead_time: '3-10 business days',
                    minimum_quantity: 1,
                    maximum_quantity: 50
                },
                pricing_structure: {
                    type: 'project_based',
                    project_cost_range: { min: 500, max: 5000 },
                    factors_affecting_price: [
                        'Prototype complexity',
                        'Custom tooling requirements',
                        'Testing requirements',
                        'Documentation needs',
                        'Rush delivery requirements'
                    ]
                },
                quality_requirements: [
                    'Prototype functionality verification',
                    'Design intent compliance',
                    'Assembly documentation',
                    'Test procedure development',
                    'Improvement recommendations'
                ],
                deliverables: [
                    'Assembled prototypes',
                    'Assembly procedures',
                    'Test results',
                    'Design recommendations',
                    'Process documentation'
                ]
            }
        ];

        services.forEach(service => {
            service.created_at = new Date();
            service.popularity_score = Math.random() * 100;
            service.average_rating = 4.0 + Math.random();
            service.total_orders = Math.floor(Math.random() * 1000) + 100;
            
            this.assemblyServices.set(service.id, service);
        });
    }

    initializeQualityStandards() {
        const standards = [
            {
                id: 'ipc_a_610_class2',
                name: 'IPC-A-610 Class 2',
                category: 'electronics_assembly',
                description: 'General electronic products acceptance standard',
                requirements: [
                    'Visual inspection criteria for solder joints',
                    'Component placement tolerances',
                    'Cleaning requirements',
                    'Marking and identification',
                    'Conformal coating application'
                ],
                applicable_services: ['pcb_assembly_service'],
                inspection_points: [
                    'Solder joint quality',
                    'Component alignment',
                    'Cleanliness',
                    'Mechanical damage',
                    'Missing components'
                ]
            },
            {
                id: 'iso_9001_quality',
                name: 'ISO 9001 Quality Management',
                category: 'general_quality',
                description: 'International standard for quality management systems',
                requirements: [
                    'Document control procedures',
                    'Quality planning',
                    'Process control',
                    'Corrective action procedures',
                    'Management review'
                ],
                applicable_services: ['pcb_assembly_service', 'mechanical_assembly_service'],
                inspection_points: [
                    'Process documentation',
                    'Quality records',
                    'Customer satisfaction',
                    'Continuous improvement',
                    'Management commitment'
                ]
            }
        ];

        standards.forEach(standard => {
            this.qualityStandards.set(standard.id, standard);
        });
    }

    async createAssemblyProject(projectRequest) {
        try {
            const project = {
                id: this.generateProjectId(),
                project_name: projectRequest.project_name,
                customer_id: projectRequest.customer_id,
                service_type: projectRequest.service_type,
                description: projectRequest.description,
                requirements: projectRequest.requirements || {},
                specifications: projectRequest.specifications || {},
                quantity: projectRequest.quantity,
                target_lead_time: projectRequest.target_lead_time,
                budget_range: projectRequest.budget_range,
                quality_standards: projectRequest.quality_standards || [],
                files: projectRequest.files || [],
                special_instructions: projectRequest.special_instructions || '',
                created_at: new Date(),
                status: 'quote_requested',
                quotes: [],
                selected_assembler: null,
                project_timeline: {
                    quote_deadline: this.addDays(new Date(), 3),
                    project_start: null,
                    estimated_completion: null,
                    actual_completion: null
                }
            };

            this.assemblyProjects.set(project.id, project);
            await this.requestQuotesFromAssemblers(project);
            
            this.emit('assemblyProjectCreated', project);
            return project;
        } catch (error) {
            this.emit('assemblyError', { error: error.message, projectRequest });
            throw error;
        }
    }

    async requestQuotesFromAssemblers(project) {
        const suitableAssemblers = this.findSuitableAssemblers(project);
        
        for (const assembler of suitableAssemblers) {
            const quote = await this.generateQuote(project, assembler);
            project.quotes.push(quote);
        }

        project.status = 'quotes_received';
        this.emit('quotesReceived', { project, quotes: project.quotes });
    }

    findSuitableAssemblers(project) {
        return Array.from(this.assemblers.values()).filter(assembler => {
            // Check capacity
            if (project.quantity < assembler.capacity.min_order_quantity ||
                project.quantity > assembler.capacity.max_order_quantity) {
                return false;
            }

            // Check specializations
            const service = this.assemblyServices.get(project.service_type);
            if (service && service.category === 'electronics_assembly' && 
                !assembler.specializations.some(spec => spec.toLowerCase().includes('pcb'))) {
                return false;
            }

            // Check availability
            if (assembler.availability_schedule.current_capacity_used >= 1.0) {
                return false;
            }

            // Check if they meet quality standards
            if (project.quality_standards.length > 0) {
                const hasRequiredCertifications = project.quality_standards.every(standard =>
                    assembler.certifications.some(cert => cert.toLowerCase().includes(standard.toLowerCase()))
                );
                if (!hasRequiredCertifications) {
                    return false;
                }
            }

            return true;
        });
    }

    async generateQuote(project, assembler) {
        const basePrice = this.calculateBasePrice(project, assembler);
        const additionalCosts = this.calculateAdditionalCosts(project, assembler);
        const totalPrice = basePrice + additionalCosts.total;
        
        const quote = {
            id: this.generateQuoteId(),
            project_id: project.id,
            assembler_id: assembler.id,
            assembler_name: assembler.business_name,
            quoted_at: new Date(),
            expires_at: this.addDays(new Date(), 14),
            pricing: {
                base_price: basePrice,
                additional_costs: additionalCosts,
                total_price: totalPrice,
                per_unit_price: totalPrice / project.quantity,
                payment_terms: '50% upfront, 50% on completion'
            },
            timeline: {
                estimated_start_date: this.addDays(new Date(), assembler.availability_schedule.booking_lead_time_days),
                estimated_completion_date: this.addDays(
                    this.addDays(new Date(), assembler.availability_schedule.booking_lead_time_days),
                    assembler.capacity.lead_time_days.max
                ),
                total_lead_time_days: assembler.availability_schedule.booking_lead_time_days + assembler.capacity.lead_time_days.max
            },
            quality_assurance: {
                standards_compliance: project.quality_standards,
                testing_included: this.getIncludedTesting(project, assembler),
                warranty_period: '90 days',
                revision_policy: 'Up to 2 revisions included'
            },
            terms_and_conditions: {
                cancellation_policy: 'Cancellation allowed up to 24 hours before start',
                intellectual_property: 'Customer retains all IP rights',
                confidentiality: 'NDA required for proprietary designs'
            },
            status: 'submitted'
        };

        this.emit('quoteGenerated', { quote, project, assembler });
        return quote;
    }

    calculateBasePrice(project, assembler) {
        let basePrice = 0;
        const pricing = assembler.pricing;

        if (pricing.setup_fee) {
            basePrice += pricing.setup_fee;
        }

        if (pricing.per_unit_base) {
            basePrice += pricing.per_unit_base * project.quantity;
        }

        if (pricing.hourly_rate && project.requirements.estimated_hours) {
            basePrice += pricing.hourly_rate * project.requirements.estimated_hours;
        }

        // Apply volume discounts
        if (pricing.volume_discounts) {
            const applicableDiscount = pricing.volume_discounts
                .filter(discount => project.quantity >= discount.min_quantity)
                .reduce((maxDiscount, discount) => 
                    discount.discount > maxDiscount.discount ? discount : maxDiscount, 
                    { discount: 0 }
                );
            
            if (applicableDiscount.discount > 0) {
                basePrice *= (1 - applicableDiscount.discount);
            }
        }

        return Math.round(basePrice * 100) / 100;
    }

    calculateAdditionalCosts(project, assembler) {
        const additionalCosts = {
            rush_order: 0,
            special_tooling: 0,
            testing: 0,
            documentation: 0,
            shipping: 0,
            total: 0
        };

        // Rush order fee
        if (project.target_lead_time && project.target_lead_time < assembler.capacity.lead_time_days.min) {
            if (assembler.capacity.rush_order_available && assembler.pricing.rush_order_multiplier !== 'not_available') {
                const basePrice = this.calculateBasePrice(project, assembler);
                additionalCosts.rush_order = basePrice * (assembler.pricing.rush_order_multiplier - 1);
            }
        }

        // Special tooling
        if (project.requirements.custom_tooling) {
            additionalCosts.special_tooling = assembler.pricing.tooling_fee || 500;
        }

        // Additional testing
        if (project.requirements.extended_testing) {
            additionalCosts.testing = 150;
        }

        // Documentation
        if (project.requirements.detailed_documentation) {
            additionalCosts.documentation = 75;
        }

        // Shipping
        additionalCosts.shipping = this.calculateShippingCost(project, assembler);

        additionalCosts.total = Object.values(additionalCosts).reduce((sum, cost) => sum + cost, 0) - additionalCosts.total;

        return additionalCosts;
    }

    calculateShippingCost(project, assembler) {
        const baseShippingRate = 15;
        const weightMultiplier = Math.max(1, Math.ceil(project.quantity / 100));
        return baseShippingRate * weightMultiplier;
    }

    getIncludedTesting(project, assembler) {
        const testing = ['Visual inspection', 'Basic functional testing'];
        
        if (assembler.equipment.includes('In-circuit testing equipment')) {
            testing.push('In-circuit testing');
        }
        
        if (assembler.equipment.includes('AOI (Automated Optical Inspection)')) {
            testing.push('Automated optical inspection');
        }
        
        if (project.service_type === 'pcb_assembly_service') {
            testing.push('Continuity testing', 'Power-on testing');
        }

        return testing;
    }

    async selectAssembler(projectId, quoteId, customerNotes = '') {
        const project = this.assemblyProjects.get(projectId);
        if (!project) {
            throw new Error('Project not found');
        }

        const selectedQuote = project.quotes.find(q => q.id === quoteId);
        if (!selectedQuote) {
            throw new Error('Quote not found');
        }

        const assembler = this.assemblers.get(selectedQuote.assembler_id);
        if (!assembler) {
            throw new Error('Assembler not found');
        }

        project.selected_assembler = selectedQuote.assembler_id;
        project.selected_quote = selectedQuote;
        project.status = 'assembler_selected';
        project.customer_notes = customerNotes;
        
        selectedQuote.status = 'accepted';
        
        // Mark other quotes as declined
        project.quotes.forEach(quote => {
            if (quote.id !== quoteId) {
                quote.status = 'declined';
            }
        });

        // Update assembler capacity
        assembler.availability_schedule.current_capacity_used += 0.1; // Rough estimate

        this.emit('assemblerSelected', { project, selectedQuote, assembler });
        return { project, selectedQuote };
    }

    async startAssemblyProject(projectId) {
        const project = this.assemblyProjects.get(projectId);
        if (!project) {
            throw new Error('Project not found');
        }

        if (project.status !== 'assembler_selected') {
            throw new Error('Project not ready to start - assembler not selected');
        }

        project.status = 'in_progress';
        project.project_timeline.project_start = new Date();
        project.project_timeline.estimated_completion = project.selected_quote.timeline.estimated_completion_date;

        // Create project milestones
        project.milestones = this.createProjectMilestones(project);

        this.emit('assemblyProjectStarted', project);
        return project;
    }

    createProjectMilestones(project) {
        const service = this.assemblyServices.get(project.service_type);
        const totalDuration = project.selected_quote.timeline.total_lead_time_days;
        
        const milestones = service.service_details.process_steps.map((step, index) => {
            const stepDuration = Math.ceil(totalDuration / service.service_details.process_steps.length);
            const startDay = index * stepDuration;
            
            return {
                id: this.generateMilestoneId(),
                step_name: step,
                step_number: index + 1,
                estimated_start: this.addDays(project.project_timeline.project_start, startDay),
                estimated_completion: this.addDays(project.project_timeline.project_start, startDay + stepDuration - 1),
                status: 'pending',
                completion_percentage: 0,
                notes: '',
                photos: []
            };
        });

        return milestones;
    }

    async updateProjectProgress(projectId, milestoneId, progressUpdate) {
        const project = this.assemblyProjects.get(projectId);
        if (!project) {
            throw new Error('Project not found');
        }

        const milestone = project.milestones?.find(m => m.id === milestoneId);
        if (!milestone) {
            throw new Error('Milestone not found');
        }

        Object.keys(progressUpdate).forEach(key => {
            if (key !== 'id' && key !== 'step_number') {
                milestone[key] = progressUpdate[key];
            }
        });

        milestone.last_updated = new Date();

        if (progressUpdate.completion_percentage === 100) {
            milestone.status = 'completed';
            milestone.actual_completion = new Date();
        } else if (progressUpdate.completion_percentage > 0) {
            milestone.status = 'in_progress';
        }

        // Update overall project progress
        const completedMilestones = project.milestones.filter(m => m.status === 'completed').length;
        project.overall_progress = Math.round((completedMilestones / project.milestones.length) * 100);

        // Check if project is complete
        if (project.overall_progress === 100) {
            project.status = 'completed';
            project.project_timeline.actual_completion = new Date();
            await this.finalizeProject(project);
        }

        this.emit('projectProgressUpdated', { project, milestone, progressUpdate });
        return { project, milestone };
    }

    async finalizeProject(project) {
        // Generate completion documentation
        const completionReport = {
            id: this.generateReportId(),
            project_id: project.id,
            completed_at: new Date(),
            final_quality_check: 'passed',
            deliverables: this.generateDeliverablesList(project),
            assembly_time: this.calculateActualAssemblyTime(project),
            quality_metrics: {
                defect_rate: Math.random() * 0.01, // 0-1%
                first_pass_yield: 0.95 + Math.random() * 0.05,
                customer_satisfaction: 'pending'
            },
            warranty_info: {
                warranty_period: '90 days',
                warranty_start_date: new Date(),
                warranty_terms: 'Covers manufacturing defects only'
            }
        };

        project.completion_report = completionReport;

        // Update assembler metrics
        const assembler = this.assemblers.get(project.selected_assembler);
        if (assembler) {
            assembler.experience.projects_completed += 1;
            assembler.availability_schedule.current_capacity_used = Math.max(0, 
                assembler.availability_schedule.current_capacity_used - 0.1
            );
        }

        this.emit('projectFinalized', { project, completionReport });
        return completionReport;
    }

    generateDeliverablesList(project) {
        const service = this.assemblyServices.get(project.service_type);
        return service ? service.deliverables : ['Assembled products', 'Documentation'];
    }

    calculateActualAssemblyTime(project) {
        if (!project.project_timeline.project_start || !project.project_timeline.actual_completion) {
            return null;
        }

        const timeDifference = project.project_timeline.actual_completion - project.project_timeline.project_start;
        const daysDifference = Math.ceil(timeDifference / (1000 * 60 * 60 * 24));
        
        return {
            days: daysDifference,
            business_days: Math.ceil(daysDifference * 0.714), // Assume 5/7 business days
            vs_estimated: daysDifference - project.selected_quote.timeline.total_lead_time_days
        };
    }

    async searchAssemblers(searchCriteria) {
        const {
            location = '',
            specializations = [],
            certifications = [],
            capacity_min = 0,
            capacity_max = Infinity,
            quality_rating_min = 0,
            availability_only = false,
            sort_by = 'rating',
            sort_order = 'desc',
            page = 1,
            limit = 10
        } = searchCriteria;

        let assemblers = Array.from(this.assemblers.values());

        if (location) {
            assemblers = assemblers.filter(assembler =>
                assembler.location.city.toLowerCase().includes(location.toLowerCase()) ||
                assembler.location.state.toLowerCase().includes(location.toLowerCase()) ||
                assembler.location.country.toLowerCase().includes(location.toLowerCase())
            );
        }

        if (specializations.length > 0) {
            assemblers = assemblers.filter(assembler =>
                specializations.some(spec =>
                    assembler.specializations.some(assemblerSpec =>
                        assemblerSpec.toLowerCase().includes(spec.toLowerCase())
                    )
                )
            );
        }

        if (certifications.length > 0) {
            assemblers = assemblers.filter(assembler =>
                certifications.some(cert =>
                    assembler.certifications.some(assemblerCert =>
                        assemblerCert.toLowerCase().includes(cert.toLowerCase())
                    )
                )
            );
        }

        if (capacity_min > 0 || capacity_max < Infinity) {
            assemblers = assemblers.filter(assembler =>
                assembler.capacity.max_order_quantity >= capacity_min &&
                assembler.capacity.min_order_quantity <= capacity_max
            );
        }

        if (quality_rating_min > 0) {
            assemblers = assemblers.filter(assembler =>
                assembler.quality_metrics.customer_satisfaction >= quality_rating_min
            );
        }

        if (availability_only) {
            assemblers = assemblers.filter(assembler =>
                assembler.availability_schedule.current_capacity_used < 0.9
            );
        }

        assemblers.sort((a, b) => {
            let aValue, bValue;
            
            switch (sort_by) {
                case 'price':
                    aValue = a.pricing.per_unit_base || 0;
                    bValue = b.pricing.per_unit_base || 0;
                    break;
                case 'lead_time':
                    aValue = a.capacity.lead_time_days.min;
                    bValue = b.capacity.lead_time_days.min;
                    break;
                case 'capacity':
                    aValue = a.capacity.max_order_quantity;
                    bValue = b.capacity.max_order_quantity;
                    break;
                case 'experience':
                    aValue = a.experience.projects_completed;
                    bValue = b.experience.projects_completed;
                    break;
                case 'rating':
                default:
                    aValue = a.quality_metrics.customer_satisfaction;
                    bValue = b.quality_metrics.customer_satisfaction;
            }

            if (sort_order === 'desc') {
                return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
            } else {
                return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
            }
        });

        const startIndex = (page - 1) * limit;
        const endIndex = startIndex + limit;
        const paginatedAssemblers = assemblers.slice(startIndex, endIndex);

        return {
            assemblers: paginatedAssemblers,
            pagination: {
                current_page: page,
                total_pages: Math.ceil(assemblers.length / limit),
                total_assemblers: assemblers.length,
                has_next: endIndex < assemblers.length,
                has_prev: page > 1
            },
            facets: {
                locations: this.calculateLocationFacets(assemblers),
                specializations: this.calculateSpecializationFacets(assemblers),
                certifications: this.calculateCertificationFacets(assemblers),
                business_types: this.calculateFacets(assemblers, 'business_type')
            }
        };
    }

    calculateLocationFacets(assemblers) {
        const locations = {};
        assemblers.forEach(assembler => {
            const location = `${assembler.location.city}, ${assembler.location.state}`;
            locations[location] = (locations[location] || 0) + 1;
        });
        return locations;
    }

    calculateSpecializationFacets(assemblers) {
        const specializations = {};
        assemblers.forEach(assembler => {
            assembler.specializations.forEach(spec => {
                specializations[spec] = (specializations[spec] || 0) + 1;
            });
        });
        return specializations;
    }

    calculateCertificationFacets(assemblers) {
        const certifications = {};
        assemblers.forEach(assembler => {
            assembler.certifications.forEach(cert => {
                certifications[cert] = (certifications[cert] || 0) + 1;
            });
        });
        return certifications;
    }

    calculateFacets(items, field) {
        const counts = {};
        items.forEach(item => {
            const value = item[field];
            if (value) {
                counts[value] = (counts[value] || 0) + 1;
            }
        });
        return counts;
    }

    addDays(date, days) {
        const result = new Date(date);
        result.setDate(result.getDate() + days);
        return result;
    }

    generateProjectId() {
        return `project_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateQuoteId() {
        return `quote_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateMilestoneId() {
        return `milestone_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateReportId() {
        return `report_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    getSystemStats() {
        const totalProjects = this.assemblyProjects.size;
        const completedProjects = Array.from(this.assemblyProjects.values())
            .filter(project => project.status === 'completed').length;

        return {
            total_assemblers: this.assemblers.size,
            assembly_services: this.assemblyServices.size,
            total_projects: totalProjects,
            completed_projects: completedProjects,
            completion_rate: totalProjects > 0 ? completedProjects / totalProjects : 0,
            quality_standards: this.qualityStandards.size,
            metrics: this.assemblyMetrics
        };
    }
}

export default AssemblyServicesMarketplace;