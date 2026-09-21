import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';

class DIYKitPlatform extends EventEmitter {
    constructor() {
        super();
        this.kits = new Map();
        this.kitCategories = new Map();
        this.buildInstructions = new Map();
        this.communityBuilds = new Map();
        this.skillAssessments = new Map();
        this.progressTracking = new Map();
        this.kitMetrics = {
            total_kits: 0,
            active_builds: 0,
            completion_rate: 0,
            community_contributions: 0
        };
        this.initializeKitCatalog();
        this.initializeKitCategories();
    }

    initializeKitCatalog() {
        const kits = [
            {
                id: 'activelog_starter_kit',
                name: 'ActiveLog IoT Starter Kit',
                category: 'beginner',
                subcategory: 'iot_basics',
                description: 'Complete beginner-friendly kit to start your IoT journey with ActiveLog',
                difficulty_level: 'beginner',
                estimated_build_time: '4-6 hours',
                age_range: '12+',
                included_components: [
                    { name: 'ActiveLog Core Module', quantity: 1, description: 'Main microcontroller with WiFi' },
                    { name: 'Breadboard', quantity: 1, description: '830-point solderless breadboard' },
                    { name: 'Jumper Wires', quantity: 40, description: 'Male-to-male jumper wires' },
                    { name: 'LED Assortment', quantity: 20, description: 'Various colored LEDs' },
                    { name: 'Resistor Pack', quantity: 100, description: 'Common resistor values' },
                    { name: 'Push Buttons', quantity: 4, description: 'Momentary push buttons' },
                    { name: 'Potentiometer', quantity: 2, description: '10K rotary potentiometers' },
                    { name: 'Temperature Sensor', quantity: 2, description: 'Digital temperature sensors' },
                    { name: 'Light Sensor', quantity: 1, description: 'Photoresistor light sensor' },
                    { name: 'Buzzer', quantity: 1, description: 'Piezo buzzer' },
                    { name: 'USB Cable', quantity: 1, description: 'USB-C programming cable' }
                ],
                learning_objectives: [
                    'Understand basic electronics concepts',
                    'Learn ActiveLog platform fundamentals',
                    'Build simple IoT sensors',
                    'Connect devices to the cloud',
                    'Create basic data visualizations'
                ],
                projects: [
                    {
                        name: 'Blinking LED',
                        difficulty: 'very_easy',
                        time_estimate: '30 minutes',
                        description: 'Your first electronics project'
                    },
                    {
                        name: 'Temperature Monitor',
                        difficulty: 'easy',
                        time_estimate: '1 hour',
                        description: 'Read and display temperature data'
                    },
                    {
                        name: 'Smart Night Light',
                        difficulty: 'easy',
                        time_estimate: '1.5 hours',
                        description: 'Light sensor controlled LED'
                    },
                    {
                        name: 'IoT Dashboard',
                        difficulty: 'medium',
                        time_estimate: '2 hours',
                        description: 'Web-based sensor monitoring'
                    },
                    {
                        name: 'Alert System',
                        difficulty: 'medium',
                        time_estimate: '2 hours',
                        description: 'Email/SMS notifications from sensors'
                    }
                ],
                pricing: {
                    kit_price: 89.99,
                    individual_component_total: 125.50,
                    savings: 35.51,
                    shipping: 'free',
                    international_shipping: 15.00
                },
                support_materials: {
                    printed_guide: 'Full-color 64-page instruction manual',
                    video_tutorials: '12 step-by-step video lessons',
                    online_simulator: 'Web-based circuit simulator',
                    community_forum: 'Dedicated support forum',
                    office_hours: 'Weekly live Q&A sessions'
                }
            },
            {
                id: 'solar_weather_station_kit',
                name: 'Solar-Powered Weather Station Kit',
                category: 'intermediate',
                subcategory: 'environmental_monitoring',
                description: 'Build a professional-grade solar weather station with wireless connectivity',
                difficulty_level: 'intermediate',
                estimated_build_time: '8-12 hours',
                age_range: '14+',
                included_components: [
                    { name: 'Weather-Resistant Enclosure', quantity: 1, description: 'IP65 rated outdoor enclosure' },
                    { name: 'Solar Panel', quantity: 1, description: '10W monocrystalline solar panel' },
                    { name: 'Battery Pack', quantity: 1, description: 'LiFePO4 battery with charge controller' },
                    { name: 'ActiveLog Pro Module', quantity: 1, description: 'Advanced microcontroller with LoRaWAN' },
                    { name: 'Temperature/Humidity Sensor', quantity: 1, description: 'High-precision SHT40 sensor' },
                    { name: 'Barometric Pressure Sensor', quantity: 1, description: 'BMP388 pressure sensor' },
                    { name: 'Wind Speed Anemometer', quantity: 1, description: 'Cup anemometer with hall sensor' },
                    { name: 'Wind Direction Vane', quantity: 1, description: 'Magnetic wind direction sensor' },
                    { name: 'Rain Gauge', quantity: 1, description: 'Tipping bucket rain gauge' },
                    { name: 'Light Sensor', quantity: 1, description: 'UV and visible light sensor' },
                    { name: 'Mounting Hardware', quantity: 1, description: 'Pole and ground mounting kit' },
                    { name: 'Waterproof Connectors', quantity: 10, description: 'IP68 rated cable connectors' }
                ],
                learning_objectives: [
                    'Solar power system design',
                    'Wireless sensor networks',
                    'Weather data analysis',
                    'Long-term outdoor deployments',
                    'Data logging and visualization'
                ],
                projects: [
                    {
                        name: 'Basic Weather Reading',
                        difficulty: 'easy',
                        time_estimate: '2 hours',
                        description: 'Read temperature, humidity, and pressure'
                    },
                    {
                        name: 'Solar Charging System',
                        difficulty: 'medium',
                        time_estimate: '3 hours',
                        description: 'Set up solar panel and battery management'
                    },
                    {
                        name: 'Wind Monitoring',
                        difficulty: 'medium',
                        time_estimate: '3 hours',
                        description: 'Install and calibrate wind sensors'
                    },
                    {
                        name: 'Precipitation Tracking',
                        difficulty: 'medium',
                        time_estimate: '2 hours',
                        description: 'Set up rain gauge with data logging'
                    },
                    {
                        name: 'Complete Weather Station',
                        difficulty: 'advanced',
                        time_estimate: '4 hours',
                        description: 'Integrate all sensors with wireless transmission'
                    }
                ],
                pricing: {
                    kit_price: 349.99,
                    individual_component_total: 425.75,
                    savings: 75.76,
                    shipping: 'free',
                    international_shipping: 45.00
                },
                support_materials: {
                    printed_guide: '96-page weatherproof instruction manual',
                    video_tutorials: '18 detailed assembly videos',
                    mobile_app: 'Weather station monitoring app',
                    calibration_service: 'Professional sensor calibration',
                    warranty: '2-year comprehensive warranty'
                }
            },
            {
                id: 'aquaponics_monitoring_kit',
                name: 'Smart Aquaponics Monitoring Kit',
                category: 'advanced',
                subcategory: 'agriculture_aquaculture',
                description: 'Complete aquaponics system monitoring with automated controls',
                difficulty_level: 'advanced',
                estimated_build_time: '12-20 hours',
                age_range: '16+',
                included_components: [
                    { name: 'Multi-Parameter Water Probe', quantity: 1, description: 'pH, DO, conductivity, temperature' },
                    { name: 'Peristaltic Pumps', quantity: 3, description: 'For automated dosing systems' },
                    { name: 'Water Level Sensors', quantity: 4, description: 'Ultrasonic level measurement' },
                    { name: 'LED Grow Lights', quantity: 2, description: 'Full-spectrum plant growth LEDs' },
                    { name: 'Air Pumps', quantity: 2, description: 'Aquarium air pumps with flow control' },
                    { name: 'Solenoid Valves', quantity: 6, description: 'Water flow control valves' },
                    { name: 'Temperature Controllers', quantity: 2, description: 'Heating/cooling controllers' },
                    { name: 'Camera Module', quantity: 1, description: 'Fish and plant monitoring camera' },
                    { name: 'Control Relays', quantity: 8, description: '120V/240V relay modules' },
                    { name: 'Power Supplies', quantity: 3, description: '12V, 24V, and 5V power supplies' },
                    { name: 'Waterproof Enclosures', quantity: 3, description: 'Electronics protection' },
                    { name: 'Sensor Cables', quantity: 20, description: 'Waterproof sensor connections' }
                ],
                learning_objectives: [
                    'Aquaponics system principles',
                    'Water quality management',
                    'Automated control systems',
                    'Machine vision for monitoring',
                    'Sustainable food production'
                ],
                projects: [
                    {
                        name: 'Water Quality Monitoring',
                        difficulty: 'medium',
                        time_estimate: '4 hours',
                        description: 'Set up multi-parameter water monitoring'
                    },
                    {
                        name: 'Automated pH Control',
                        difficulty: 'advanced',
                        time_estimate: '3 hours',
                        description: 'Build automated pH adjustment system'
                    },
                    {
                        name: 'Fish Tank Monitoring',
                        difficulty: 'advanced',
                        time_estimate: '4 hours',
                        description: 'Fish behavior and health monitoring'
                    },
                    {
                        name: 'Plant Growth Optimization',
                        difficulty: 'advanced',
                        time_estimate: '5 hours',
                        description: 'LED lighting and nutrient control'
                    },
                    {
                        name: 'Complete System Integration',
                        difficulty: 'expert',
                        time_estimate: '6 hours',
                        description: 'Full aquaponics automation system'
                    }
                ],
                pricing: {
                    kit_price: 899.99,
                    individual_component_total: 1150.00,
                    savings: 250.01,
                    shipping: 'free',
                    international_shipping: 85.00
                },
                support_materials: {
                    printed_guide: '128-page comprehensive manual',
                    video_tutorials: '24 expert-level tutorials',
                    system_software: 'Complete monitoring and control software',
                    expert_consultation: '2 hours of expert consultation',
                    ongoing_support: '6 months of technical support'
                }
            },
            {
                id: 'marine_research_kit',
                name: 'Marine Research Data Logger Kit',
                category: 'expert',
                subcategory: 'marine_science',
                description: 'Professional-grade marine data collection system for research applications',
                difficulty_level: 'expert',
                estimated_build_time: '20-30 hours',
                age_range: '18+',
                included_components: [
                    { name: 'Pressure-Rated Housing', quantity: 1, description: '200m depth rated titanium housing' },
                    { name: 'Multi-Beam Sonar', quantity: 1, description: 'Bathymetry mapping sonar' },
                    { name: 'CTD Sensor Suite', quantity: 1, description: 'Conductivity, Temperature, Depth sensors' },
                    { name: 'Dissolved Oxygen Sensor', quantity: 1, description: 'Optical DO sensor' },
                    { name: 'pH Sensor', quantity: 1, description: 'Seawater pH measurement' },
                    { name: 'Turbidity Sensor', quantity: 1, description: 'Water clarity measurement' },
                    { name: 'Current Meter', quantity: 1, description: '3D current velocity measurement' },
                    { name: 'Underwater Camera', quantity: 1, description: '4K underwater imaging system' },
                    { name: 'Data Logger', quantity: 1, description: 'Ruggedized data acquisition system' },
                    { name: 'Satellite Modem', quantity: 1, description: 'Iridium satellite communication' },
                    { name: 'Solar Charging System', quantity: 1, description: 'Marine-grade solar charging' },
                    { name: 'Deployment Hardware', quantity: 1, description: 'Anchoring and recovery systems' }
                ],
                learning_objectives: [
                    'Marine instrumentation principles',
                    'Deep-water sensor deployment',
                    'Satellite data transmission',
                    'Oceanographic data analysis',
                    'Research methodology'
                ],
                projects: [
                    {
                        name: 'Sensor Calibration',
                        difficulty: 'advanced',
                        time_estimate: '6 hours',
                        description: 'Calibrate all sensors for marine environment'
                    },
                    {
                        name: 'Data Logger Programming',
                        difficulty: 'expert',
                        time_estimate: '8 hours',
                        description: 'Program autonomous data collection'
                    },
                    {
                        name: 'Communication Setup',
                        difficulty: 'expert',
                        time_estimate: '4 hours',
                        description: 'Configure satellite data transmission'
                    },
                    {
                        name: 'System Integration',
                        difficulty: 'expert',
                        time_estimate: '6 hours',
                        description: 'Integrate all subsystems'
                    },
                    {
                        name: 'Field Deployment',
                        difficulty: 'expert',
                        time_estimate: '8 hours',
                        description: 'Deploy and test in marine environment'
                    }
                ],
                pricing: {
                    kit_price: 2499.99,
                    individual_component_total: 3200.00,
                    savings: 700.01,
                    shipping: 'free',
                    international_shipping: 150.00
                },
                support_materials: {
                    printed_guide: '200-page technical manual',
                    video_tutorials: '30+ professional tutorials',
                    data_analysis_software: 'Oceanographic analysis suite',
                    research_collaboration: 'Connect with marine research institutions',
                    certification: 'Certificate of completion for research applications'
                }
            },
            {
                id: 'kids_robot_builder_kit',
                name: 'Kids Robot Builder Kit',
                category: 'educational',
                subcategory: 'robotics_kids',
                description: 'Fun and educational robotics kit designed specifically for children',
                difficulty_level: 'beginner',
                estimated_build_time: '3-5 hours',
                age_range: '8-14',
                included_components: [
                    { name: 'Robot Chassis', quantity: 1, description: 'Colorful plastic robot frame' },
                    { name: 'Motors with Wheels', quantity: 2, description: 'Geared DC motors with rubber wheels' },
                    { name: 'Ultrasonic Sensor', quantity: 1, description: 'Distance sensing "eyes"' },
                    { name: 'LED Matrix Display', quantity: 1, description: '8x8 LED face display' },
                    { name: 'Sound Module', quantity: 1, description: 'Speaker for robot sounds' },
                    { name: 'Color Sensors', quantity: 2, description: 'Line following sensors' },
                    { name: 'Remote Control', quantity: 1, description: 'Wireless remote controller' },
                    { name: 'Battery Pack', quantity: 1, description: 'Rechargeable battery pack' },
                    { name: 'Screwdriver', quantity: 1, description: 'Child-safe screwdriver' },
                    { name: 'Stickers', quantity: 50, description: 'Robot decoration stickers' },
                    { name: 'Instruction Cards', quantity: 20, description: 'Visual programming cards' }
                ],
                learning_objectives: [
                    'Basic robotics concepts',
                    'Problem-solving skills',
                    'Sequential thinking',
                    'Hand-eye coordination',
                    'STEM fundamentals'
                ],
                projects: [
                    {
                        name: 'Build Your Robot',
                        difficulty: 'very_easy',
                        time_estimate: '1 hour',
                        description: 'Assemble the robot chassis and components'
                    },
                    {
                        name: 'Make It Move',
                        difficulty: 'easy',
                        time_estimate: '30 minutes',
                        description: 'Program basic movement commands'
                    },
                    {
                        name: 'Obstacle Avoidance',
                        difficulty: 'easy',
                        time_estimate: '45 minutes',
                        description: 'Teach robot to avoid obstacles'
                    },
                    {
                        name: 'Line Following',
                        difficulty: 'medium',
                        time_estimate: '1 hour',
                        description: 'Program robot to follow colored lines'
                    },
                    {
                        name: 'Dance Party',
                        difficulty: 'easy',
                        time_estimate: '30 minutes',
                        description: 'Create choreographed robot dances'
                    }
                ],
                pricing: {
                    kit_price: 129.99,
                    individual_component_total: 165.00,
                    savings: 35.01,
                    shipping: 'free',
                    international_shipping: 25.00
                },
                support_materials: {
                    printed_guide: 'Colorful comic-book style manual',
                    video_tutorials: '10 kid-friendly tutorial videos',
                    mobile_app: 'Drag-and-drop programming app',
                    parent_guide: 'Guide for parents and educators',
                    online_community: 'Safe kids robotics community'
                }
            }
        ];

        kits.forEach(kit => {
            kit.created_at = new Date();
            kit.total_components = kit.included_components.reduce((sum, comp) => sum + comp.quantity, 0);
            kit.completion_rate = 0.75 + Math.random() * 0.2; // 75-95% completion rate
            kit.community_builds = Math.floor(Math.random() * 500) + 100;
            kit.average_rating = 4.2 + Math.random() * 0.7;
            kit.reviews_count = Math.floor(Math.random() * 200) + 50;
            kit.inventory_status = 'in_stock';
            kit.estimated_shipping_days = Math.floor(Math.random() * 5) + 2;
            
            this.kits.set(kit.id, kit);
        });
    }

    initializeKitCategories() {
        const categories = [
            {
                id: 'beginner',
                name: 'Beginner Kits',
                description: 'Perfect for getting started with electronics and IoT',
                difficulty_range: 'Very Easy to Easy',
                time_range: '2-8 hours',
                age_recommendation: '10+',
                skills_developed: ['Basic electronics', 'Simple programming', 'Following instructions']
            },
            {
                id: 'intermediate',
                name: 'Intermediate Kits',
                description: 'Build more complex projects with multiple sensors and systems',
                difficulty_range: 'Easy to Medium',
                time_range: '6-15 hours',
                age_recommendation: '14+',
                skills_developed: ['Circuit design', 'Sensor integration', 'Data analysis', 'System troubleshooting']
            },
            {
                id: 'advanced',
                name: 'Advanced Kits',
                description: 'Professional-grade projects for serious makers and students',
                difficulty_range: 'Medium to Hard',
                time_range: '12-25 hours',
                age_recommendation: '16+',
                skills_developed: ['System design', 'Automation', 'Advanced programming', 'Project management']
            },
            {
                id: 'expert',
                name: 'Expert Kits',
                description: 'Research-grade instruments for professional applications',
                difficulty_range: 'Hard to Expert',
                time_range: '20-40 hours',
                age_recommendation: '18+',
                skills_developed: ['Professional instrumentation', 'Research methods', 'Data validation', 'Scientific protocols']
            },
            {
                id: 'educational',
                name: 'Educational Kits',
                description: 'Designed specifically for classroom and home learning',
                difficulty_range: 'Very Easy to Medium',
                time_range: '2-10 hours',
                age_recommendation: '8-16',
                skills_developed: ['STEM concepts', 'Critical thinking', 'Creativity', 'Collaboration']
            }
        ];

        categories.forEach(category => {
            this.kitCategories.set(category.id, category);
        });
    }

    async createCustomKit(kitRequest) {
        try {
            const customKit = {
                id: this.generateKitId(),
                name: kitRequest.name,
                description: kitRequest.description,
                category: kitRequest.category,
                difficulty_level: kitRequest.difficulty_level,
                created_by: kitRequest.user_id,
                created_at: new Date(),
                custom_kit: true,
                components: kitRequest.components || [],
                learning_objectives: kitRequest.learning_objectives || [],
                projects: kitRequest.projects || [],
                estimated_build_time: kitRequest.estimated_build_time,
                age_range: kitRequest.age_range,
                pricing: {
                    estimated_cost: 0,
                    component_breakdown: []
                },
                validation_status: 'pending',
                community_approved: false
            };

            await this.validateCustomKit(customKit);
            await this.calculateCustomKitPricing(customKit);
            
            this.kits.set(customKit.id, customKit);
            this.emit('customKitCreated', customKit);

            return customKit;
        } catch (error) {
            this.emit('kitError', { error: error.message, kitRequest });
            throw error;
        }
    }

    async validateCustomKit(customKit) {
        const validation = {
            component_validation: 'pending',
            safety_check: 'pending',
            educational_value: 'pending',
            feasibility_check: 'pending',
            issues: [],
            warnings: []
        };

        if (customKit.components.length === 0) {
            validation.issues.push('Kit must include at least one component');
        }

        if (customKit.components.length > 50) {
            validation.warnings.push('Kit has many components - consider breaking into multiple kits');
        }

        const hasHazardousComponents = customKit.components.some(comp => 
            comp.name.toLowerCase().includes('battery') && comp.description.toLowerCase().includes('lithium') ||
            comp.name.toLowerCase().includes('motor') && !comp.description.toLowerCase().includes('low voltage') ||
            comp.name.toLowerCase().includes('relay') && comp.description.toLowerCase().includes('mains')
        );

        if (hasHazardousComponents && customKit.age_range?.includes('8')) {
            validation.issues.push('Kit contains components not suitable for young children');
        }

        if (customKit.learning_objectives.length === 0) {
            validation.warnings.push('Consider adding specific learning objectives');
        }

        if (customKit.projects.length === 0) {
            validation.warnings.push('Kit should include at least one project');
        }

        validation.component_validation = validation.issues.length === 0 ? 'passed' : 'failed';
        validation.safety_check = !hasHazardousComponents || !customKit.age_range?.includes('8') ? 'passed' : 'review_required';
        validation.educational_value = customKit.learning_objectives.length > 0 ? 'good' : 'needs_improvement';
        validation.feasibility_check = 'passed'; // Simplified

        customKit.validation_results = validation;
        return validation;
    }

    async calculateCustomKitPricing(customKit) {
        let totalCost = 0;
        const componentBreakdown = [];

        customKit.components.forEach(component => {
            const estimatedCost = this.estimateComponentCost(component);
            totalCost += estimatedCost * (component.quantity || 1);
            
            componentBreakdown.push({
                name: component.name,
                quantity: component.quantity || 1,
                unit_cost: estimatedCost,
                total_cost: estimatedCost * (component.quantity || 1)
            });
        });

        const packagingCost = Math.min(totalCost * 0.1, 25); // 10% of component cost, max $25
        const supportMaterialsCost = customKit.difficulty_level === 'expert' ? 50 : 
                                   customKit.difficulty_level === 'advanced' ? 35 :
                                   customKit.difficulty_level === 'intermediate' ? 25 : 15;

        customKit.pricing = {
            estimated_cost: Math.round((totalCost + packagingCost + supportMaterialsCost) * 100) / 100,
            component_cost: totalCost,
            packaging_cost: packagingCost,
            support_materials_cost: supportMaterialsCost,
            component_breakdown: componentBreakdown,
            profit_margin: 0.25, // 25% margin
            suggested_retail_price: Math.round((totalCost + packagingCost + supportMaterialsCost) * 1.25 * 100) / 100
        };

        return customKit.pricing;
    }

    estimateComponentCost(component) {
        const componentCosts = {
            'microcontroller': 15,
            'sensor': 8,
            'led': 0.25,
            'resistor': 0.05,
            'capacitor': 0.10,
            'wire': 0.50,
            'breadboard': 3,
            'button': 0.75,
            'motor': 12,
            'servo': 18,
            'camera': 25,
            'display': 20,
            'battery': 15,
            'solar': 30,
            'enclosure': 10
        };

        const componentName = component.name.toLowerCase();
        
        for (const [key, cost] of Object.entries(componentCosts)) {
            if (componentName.includes(key)) {
                return cost;
            }
        }

        return 5; // Default cost estimate
    }

    async startKitBuild(kitId, userId) {
        const kit = this.kits.get(kitId);
        if (!kit) {
            throw new Error('Kit not found');
        }

        const buildSession = {
            id: this.generateBuildId(),
            kit_id: kitId,
            user_id: userId,
            started_at: new Date(),
            status: 'in_progress',
            current_step: 0,
            completed_projects: [],
            time_spent: 0,
            progress_percentage: 0,
            notes: [],
            photos: [],
            help_requests: [],
            skill_assessments: []
        };

        if (!this.progressTracking.has(kitId)) {
            this.progressTracking.set(kitId, new Map());
        }
        
        this.progressTracking.get(kitId).set(userId, buildSession);
        this.emit('buildStarted', buildSession);

        return buildSession;
    }

    async updateBuildProgress(buildId, progressUpdate) {
        const buildSession = this.findBuildSession(buildId);
        if (!buildSession) {
            throw new Error('Build session not found');
        }

        Object.keys(progressUpdate).forEach(key => {
            if (key !== 'id' && key !== 'kit_id' && key !== 'user_id' && key !== 'started_at') {
                buildSession[key] = progressUpdate[key];
            }
        });

        buildSession.last_updated = new Date();
        buildSession.progress_percentage = this.calculateProgressPercentage(buildSession);

        if (progressUpdate.completed_project) {
            buildSession.completed_projects.push({
                project_name: progressUpdate.completed_project,
                completed_at: new Date(),
                time_spent: progressUpdate.project_time || 0
            });

            this.emit('projectCompleted', {
                buildSession,
                project: progressUpdate.completed_project
            });
        }

        if (buildSession.progress_percentage >= 100) {
            buildSession.status = 'completed';
            buildSession.completed_at = new Date();
            await this.generateCompletionCertificate(buildSession);
            this.emit('buildCompleted', buildSession);
        }

        return buildSession;
    }

    calculateProgressPercentage(buildSession) {
        const kit = this.kits.get(buildSession.kit_id);
        if (!kit) return 0;

        const totalProjects = kit.projects.length;
        const completedProjects = buildSession.completed_projects.length;
        
        if (totalProjects === 0) return 0;
        
        return Math.min(100, Math.round((completedProjects / totalProjects) * 100));
    }

    async submitHelpRequest(buildId, helpRequest) {
        const buildSession = this.findBuildSession(buildId);
        if (!buildSession) {
            throw new Error('Build session not found');
        }

        const request = {
            id: this.generateHelpId(),
            build_id: buildId,
            request_type: helpRequest.type, // 'technical', 'parts', 'concept', 'troubleshooting'
            subject: helpRequest.subject,
            description: helpRequest.description,
            current_step: helpRequest.current_step,
            photos: helpRequest.photos || [],
            priority: helpRequest.priority || 'medium',
            submitted_at: new Date(),
            status: 'open',
            responses: []
        };

        buildSession.help_requests.push(request);
        this.emit('helpRequested', request);

        return request;
    }

    async respondToHelpRequest(requestId, response) {
        const buildSession = this.findBuildSessionByHelpRequest(requestId);
        if (!buildSession) {
            throw new Error('Help request not found');
        }

        const helpRequest = buildSession.help_requests.find(req => req.id === requestId);
        if (!helpRequest) {
            throw new Error('Help request not found');
        }

        const helpResponse = {
            id: this.generateResponseId(),
            responder_type: response.responder_type, // 'expert', 'community', 'ai'
            responder_id: response.responder_id,
            response_text: response.response_text,
            attachments: response.attachments || [],
            helpful_links: response.helpful_links || [],
            responded_at: new Date()
        };

        helpRequest.responses.push(helpResponse);
        
        if (response.resolve_request) {
            helpRequest.status = 'resolved';
            helpRequest.resolved_at = new Date();
        }

        this.emit('helpResponseProvided', { helpRequest, response: helpResponse });
        return helpResponse;
    }

    async conductSkillAssessment(buildId, assessmentType) {
        const buildSession = this.findBuildSession(buildId);
        if (!buildSession) {
            throw new Error('Build session not found');
        }

        const kit = this.kits.get(buildSession.kit_id);
        const assessment = {
            id: this.generateAssessmentId(),
            build_id: buildId,
            assessment_type: assessmentType,
            conducted_at: new Date(),
            questions: this.generateAssessmentQuestions(kit, assessmentType),
            status: 'pending'
        };

        buildSession.skill_assessments.push(assessment);
        return assessment;
    }

    generateAssessmentQuestions(kit, assessmentType) {
        const questionPools = {
            'electronics_basics': [
                {
                    question: 'What is the purpose of a resistor in a circuit?',
                    type: 'multiple_choice',
                    options: ['To store energy', 'To limit current flow', 'To amplify signals', 'To switch circuits'],
                    correct_answer: 'To limit current flow'
                },
                {
                    question: 'What does LED stand for?',
                    type: 'text_input',
                    correct_answer: 'Light Emitting Diode'
                },
                {
                    question: 'Which component is used to temporarily store electrical charge?',
                    type: 'multiple_choice',
                    options: ['Resistor', 'Capacitor', 'Inductor', 'Transistor'],
                    correct_answer: 'Capacitor'
                }
            ],
            'programming_concepts': [
                {
                    question: 'What is a variable in programming?',
                    type: 'text_input',
                    correct_answer: 'A container for storing data values'
                },
                {
                    question: 'Which of these is a programming loop?',
                    type: 'multiple_choice',
                    options: ['if statement', 'for loop', 'function', 'variable'],
                    correct_answer: 'for loop'
                }
            ],
            'problem_solving': [
                {
                    question: 'Your LED is not lighting up. What should you check first?',
                    type: 'multiple_choice',
                    options: ['Replace the LED', 'Check the power supply', 'Rewrite the code', 'Buy new components'],
                    correct_answer: 'Check the power supply'
                }
            ]
        };

        const questions = questionPools[assessmentType] || questionPools['electronics_basics'];
        return questions.slice(0, Math.min(5, questions.length)); // Return up to 5 questions
    }

    async submitSkillAssessment(assessmentId, answers) {
        const buildSession = this.findBuildSessionByAssessment(assessmentId);
        if (!buildSession) {
            throw new Error('Assessment not found');
        }

        const assessment = buildSession.skill_assessments.find(a => a.id === assessmentId);
        if (!assessment) {
            throw new Error('Assessment not found');
        }

        let correctAnswers = 0;
        const results = [];

        assessment.questions.forEach((question, index) => {
            const userAnswer = answers[index];
            const isCorrect = userAnswer === question.correct_answer;
            
            if (isCorrect) correctAnswers++;
            
            results.push({
                question: question.question,
                user_answer: userAnswer,
                correct_answer: question.correct_answer,
                is_correct: isCorrect
            });
        });

        const score = Math.round((correctAnswers / assessment.questions.length) * 100);
        
        assessment.answers = answers;
        assessment.results = results;
        assessment.score = score;
        assessment.status = 'completed';
        assessment.completed_at = new Date();

        this.emit('assessmentCompleted', { assessment, score });
        return { assessment, score, results };
    }

    async generateCompletionCertificate(buildSession) {
        const kit = this.kits.get(buildSession.kit_id);
        const totalTimeHours = Math.round(buildSession.time_spent / 60 * 10) / 10;

        const certificate = {
            id: this.generateCertificateId(),
            build_session_id: buildSession.id,
            user_id: buildSession.user_id,
            kit_name: kit.name,
            completion_date: new Date(),
            time_spent_hours: totalTimeHours,
            projects_completed: buildSession.completed_projects.length,
            skill_assessments_passed: buildSession.skill_assessments.filter(a => a.score >= 70).length,
            certificate_url: `/certificates/${buildSession.user_id}/${buildSession.id}.pdf`,
            verification_code: this.generateVerificationCode(),
            digital_badge_url: `/badges/${buildSession.kit_id}_completion.png`
        };

        buildSession.completion_certificate = certificate;
        this.emit('certificateGenerated', certificate);

        return certificate;
    }

    async searchKits(searchCriteria) {
        const {
            query = '',
            category = '',
            difficulty_level = '',
            age_range = '',
            build_time_max = null,
            price_range = {},
            in_stock_only = false,
            sort_by = 'popularity',
            sort_order = 'desc',
            page = 1,
            limit = 20
        } = searchCriteria;

        let kits = Array.from(this.kits.values());

        if (query) {
            const searchLower = query.toLowerCase();
            kits = kits.filter(kit => 
                kit.name.toLowerCase().includes(searchLower) ||
                kit.description.toLowerCase().includes(searchLower) ||
                kit.learning_objectives.some(obj => obj.toLowerCase().includes(searchLower))
            );
        }

        if (category) kits = kits.filter(kit => kit.category === category);
        if (difficulty_level) kits = kits.filter(kit => kit.difficulty_level === difficulty_level);
        
        if (age_range) {
            kits = kits.filter(kit => {
                const kitAgeRange = kit.age_range;
                return kitAgeRange && kitAgeRange.includes(age_range);
            });
        }

        if (build_time_max) {
            kits = kits.filter(kit => {
                const maxHours = parseInt(kit.estimated_build_time.split('-')[1]) || 100;
                return maxHours <= build_time_max;
            });
        }

        if (price_range.min !== undefined || price_range.max !== undefined) {
            kits = kits.filter(kit => {
                const price = kit.pricing?.kit_price || 0;
                if (price_range.min !== undefined && price < price_range.min) return false;
                if (price_range.max !== undefined && price > price_range.max) return false;
                return true;
            });
        }

        if (in_stock_only) {
            kits = kits.filter(kit => kit.inventory_status === 'in_stock');
        }

        kits.sort((a, b) => {
            let aValue, bValue;
            
            switch (sort_by) {
                case 'price':
                    aValue = a.pricing?.kit_price || 0;
                    bValue = b.pricing?.kit_price || 0;
                    break;
                case 'difficulty':
                    const difficultyOrder = ['beginner', 'intermediate', 'advanced', 'expert'];
                    aValue = difficultyOrder.indexOf(a.difficulty_level);
                    bValue = difficultyOrder.indexOf(b.difficulty_level);
                    break;
                case 'build_time':
                    aValue = parseInt(a.estimated_build_time.split('-')[0]) || 0;
                    bValue = parseInt(b.estimated_build_time.split('-')[0]) || 0;
                    break;
                case 'rating':
                    aValue = a.average_rating || 0;
                    bValue = b.average_rating || 0;
                    break;
                case 'popularity':
                default:
                    aValue = a.community_builds || 0;
                    bValue = b.community_builds || 0;
            }

            if (sort_order === 'desc') {
                return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
            } else {
                return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
            }
        });

        const startIndex = (page - 1) * limit;
        const endIndex = startIndex + limit;
        const paginatedKits = kits.slice(startIndex, endIndex);

        return {
            kits: paginatedKits,
            pagination: {
                current_page: page,
                total_pages: Math.ceil(kits.length / limit),
                total_kits: kits.length,
                has_next: endIndex < kits.length,
                has_prev: page > 1
            },
            facets: {
                categories: this.calculateFacets(kits, 'category'),
                difficulty_levels: this.calculateFacets(kits, 'difficulty_level'),
                age_ranges: this.calculateFacets(kits, 'age_range'),
                price_ranges: this.calculatePriceRangeFacets(kits)
            }
        };
    }

    findBuildSession(buildId) {
        for (const [kitId, userSessions] of this.progressTracking) {
            for (const [userId, session] of userSessions) {
                if (session.id === buildId) {
                    return session;
                }
            }
        }
        return null;
    }

    findBuildSessionByHelpRequest(requestId) {
        for (const [kitId, userSessions] of this.progressTracking) {
            for (const [userId, session] of userSessions) {
                if (session.help_requests.some(req => req.id === requestId)) {
                    return session;
                }
            }
        }
        return null;
    }

    findBuildSessionByAssessment(assessmentId) {
        for (const [kitId, userSessions] of this.progressTracking) {
            for (const [userId, session] of userSessions) {
                if (session.skill_assessments.some(assessment => assessment.id === assessmentId)) {
                    return session;
                }
            }
        }
        return null;
    }

    calculateFacets(items, fieldOrFunction) {
        const counts = {};
        items.forEach(item => {
            const value = typeof fieldOrFunction === 'function' ? fieldOrFunction(item) : item[fieldOrFunction];
            if (value) {
                counts[value] = (counts[value] || 0) + 1;
            }
        });
        return counts;
    }

    calculatePriceRangeFacets(kits) {
        const ranges = [
            { label: '$0-$50', min: 0, max: 50 },
            { label: '$50-$150', min: 50, max: 150 },
            { label: '$150-$300', min: 150, max: 300 },
            { label: '$300-$500', min: 300, max: 500 },
            { label: '$500+', min: 500, max: 99999 }
        ];

        return ranges.map(range => ({
            ...range,
            count: kits.filter(kit => {
                const price = kit.pricing?.kit_price || 0;
                return price >= range.min && price < range.max;
            }).length
        }));
    }

    generateKitId() {
        return `kit_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateBuildId() {
        return `build_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateHelpId() {
        return `help_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateResponseId() {
        return `response_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateAssessmentId() {
        return `assessment_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateCertificateId() {
        return `cert_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateVerificationCode() {
        return Math.random().toString(36).substr(2, 12).toUpperCase();
    }

    getSystemStats() {
        const totalBuilds = Array.from(this.progressTracking.values()).reduce((total, userSessions) => 
            total + userSessions.size, 0
        );

        const completedBuilds = Array.from(this.progressTracking.values()).reduce((total, userSessions) => {
            let completed = 0;
            userSessions.forEach(session => {
                if (session.status === 'completed') completed++;
            });
            return total + completed;
        }, 0);

        return {
            total_kits: this.kits.size,
            kit_categories: this.kitCategories.size,
            total_builds: totalBuilds,
            completed_builds: completedBuilds,
            completion_rate: totalBuilds > 0 ? completedBuilds / totalBuilds : 0,
            metrics: this.kitMetrics
        };
    }
}

export default DIYKitPlatform;