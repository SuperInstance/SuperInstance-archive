import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';

class ActiveLogDeviceCatalog extends EventEmitter {
    constructor() {
        super();
        this.devices = new Map();
        this.deviceCategories = new Map();
        this.compatibilityMatrix = new Map();
        this.certifiedDevices = new Map();
        this.deviceSpecs = new Map();
        this.integrationGuides = new Map();
        this.deviceMetrics = {
            total_devices: 0,
            certified_devices: 0,
            integration_ready: 0,
            monthly_downloads: 0
        };
        this.initializeDeviceCategories();
        this.initializeCertifiedDevices();
    }

    initializeDeviceCategories() {
        const categories = [
            {
                id: 'environmental_monitors',
                name: 'Environmental Monitors',
                description: 'Devices for environmental data collection and monitoring',
                subcategories: ['weather_stations', 'air_quality', 'water_quality', 'soil_sensors'],
                integration_complexity: 'beginner',
                typical_use_cases: ['Agriculture', 'Smart Cities', 'Research', 'Home Automation']
            },
            {
                id: 'security_systems',
                name: 'Security & Surveillance',
                description: 'Security cameras, motion sensors, and access control',
                subcategories: ['cameras', 'motion_sensors', 'door_sensors', 'alarm_systems'],
                integration_complexity: 'intermediate',
                typical_use_cases: ['Home Security', 'Business Security', 'Perimeter Monitoring']
            },
            {
                id: 'marine_devices',
                name: 'Marine & Aquatic',
                description: 'Waterproof sensors and monitoring systems for marine use',
                subcategories: ['fish_counters', 'depth_sensors', 'current_meters', 'ph_monitors'],
                integration_complexity: 'advanced',
                typical_use_cases: ['Aquaculture', 'Research', 'Fishing Industry', 'Marine Conservation']
            },
            {
                id: 'power_systems',
                name: 'Power & Energy',
                description: 'Solar panels, battery systems, and power management',
                subcategories: ['solar_panels', 'batteries', 'inverters', 'charge_controllers'],
                integration_complexity: 'intermediate',
                typical_use_cases: ['Off-grid Systems', 'Backup Power', 'Solar Installations']
            },
            {
                id: 'communication_modules',
                name: 'Communication Modules',
                description: 'WiFi, cellular, LoRa, and satellite communication devices',
                subcategories: ['wifi_modules', 'cellular_modems', 'lora_transceivers', 'satellite_modules'],
                integration_complexity: 'advanced',
                typical_use_cases: ['IoT Networks', 'Remote Monitoring', 'Emergency Communications']
            },
            {
                id: 'industrial_sensors',
                name: 'Industrial Sensors',
                description: 'Industrial-grade sensors for manufacturing and automation',
                subcategories: ['temperature_sensors', 'pressure_sensors', 'flow_meters', 'proximity_sensors'],
                integration_complexity: 'expert',
                typical_use_cases: ['Manufacturing', 'Process Control', 'Quality Assurance']
            }
        ];

        categories.forEach(category => {
            this.deviceCategories.set(category.id, category);
        });
    }

    initializeCertifiedDevices() {
        const certifiedDevices = [
            {
                id: 'activelog_core_v2',
                name: 'ActiveLog Core Module v2.0',
                manufacturer: 'ActiveLog Systems',
                category: 'communication_modules',
                subcategory: 'wifi_modules',
                certification_level: 'platinum',
                description: 'Next-generation core module with enhanced processing and connectivity',
                specifications: {
                    processor: 'ARM Cortex-M4 @ 120MHz',
                    memory: '512KB Flash, 128KB RAM',
                    connectivity: ['WiFi 6', 'Bluetooth 5.2', 'LoRaWAN'],
                    interfaces: ['I2C', 'SPI', 'UART', '12x GPIO'],
                    power: '3.3V, 50mA typical',
                    dimensions: '25x15x3mm',
                    operating_temp: '-40°C to +85°C',
                    certifications: ['FCC', 'CE', 'IC']
                },
                pricing: {
                    unit_price: 45.00,
                    quantity_breaks: [
                        { min: 10, price: 42.00 },
                        { min: 100, price: 38.00 },
                        { min: 1000, price: 32.00 }
                    ]
                },
                availability: {
                    in_stock: true,
                    stock_level: 5000,
                    lead_time_days: 0,
                    next_restock: null
                },
                integration: {
                    sdk_version: '2.1.0',
                    documentation_url: '/docs/activelog-core-v2',
                    sample_code: '/samples/core-v2',
                    complexity: 'beginner',
                    setup_time_hours: 2
                }
            },
            {
                id: 'activelog_solar_panel_20w',
                name: 'ActiveLog Solar Panel 20W',
                manufacturer: 'ActiveLog Power',
                category: 'power_systems',
                subcategory: 'solar_panels',
                certification_level: 'gold',
                description: 'High-efficiency monocrystalline solar panel optimized for ActiveLog systems',
                specifications: {
                    power_output: '20W peak',
                    voltage: '12V nominal',
                    current: '1.67A max',
                    efficiency: '22.5%',
                    dimensions: '350x250x20mm',
                    weight: '1.2kg',
                    cell_type: 'Monocrystalline',
                    certifications: ['IEC 61215', 'IEC 61730']
                },
                pricing: {
                    unit_price: 85.00,
                    quantity_breaks: [
                        { min: 5, price: 80.00 },
                        { min: 25, price: 75.00 },
                        { min: 100, price: 68.00 }
                    ]
                },
                availability: {
                    in_stock: true,
                    stock_level: 200,
                    lead_time_days: 3,
                    next_restock: new Date('2024-02-15')
                },
                integration: {
                    compatible_controllers: ['activelog_charge_controller_v1'],
                    mounting_options: ['pole_mount', 'ground_mount', 'roof_mount'],
                    complexity: 'intermediate',
                    setup_time_hours: 4
                }
            },
            {
                id: 'activelog_env_sensor_pro',
                name: 'ActiveLog Environmental Sensor Pro',
                manufacturer: 'ActiveLog Sensors',
                category: 'environmental_monitors',
                subcategory: 'weather_stations',
                certification_level: 'platinum',
                description: 'Professional-grade multi-sensor environmental monitoring system',
                specifications: {
                    sensors: {
                        temperature: '±0.1°C accuracy',
                        humidity: '±1.5%RH accuracy',
                        pressure: '±0.5hPa accuracy',
                        light: '0-100,000 lux range',
                        uv_index: '0-15 range',
                        air_quality: 'PM1.0, PM2.5, PM10'
                    },
                    sampling_rate: '0.1Hz to 1Hz configurable',
                    data_storage: '1GB internal + microSD',
                    power: '3.3V, 25mA typical',
                    housing: 'IP65 weatherproof',
                    dimensions: '120x80x50mm'
                },
                pricing: {
                    unit_price: 165.00,
                    quantity_breaks: [
                        { min: 5, price: 155.00 },
                        { min: 20, price: 145.00 },
                        { min: 50, price: 135.00 }
                    ]
                },
                availability: {
                    in_stock: true,
                    stock_level: 150,
                    lead_time_days: 5,
                    next_restock: new Date('2024-02-20')
                },
                integration: {
                    protocols: ['I2C', 'Modbus RTU', 'MQTT'],
                    calibration_required: true,
                    complexity: 'intermediate',
                    setup_time_hours: 6
                }
            },
            {
                id: 'activelog_fish_counter_v3',
                name: 'ActiveLog Fish Counter v3.0',
                manufacturer: 'ActiveLog Marine',
                category: 'marine_devices',
                subcategory: 'fish_counters',
                certification_level: 'gold',
                description: 'Advanced underwater fish counting system with AI recognition',
                specifications: {
                    camera: '4K underwater camera',
                    ai_processing: 'Edge inference for fish detection',
                    depth_rating: '50m waterproof',
                    battery_life: '30 days typical',
                    data_transmission: 'WiFi surface buoy or cellular',
                    accuracy: '95%+ fish counting accuracy',
                    species_recognition: '50+ common species',
                    dimensions: '300x150x100mm',
                    weight: '2.5kg in air, neutral buoyancy'
                },
                pricing: {
                    unit_price: 1250.00,
                    quantity_breaks: [
                        { min: 3, price: 1150.00 },
                        { min: 10, price: 1050.00 },
                        { min: 25, price: 950.00 }
                    ]
                },
                availability: {
                    in_stock: false,
                    stock_level: 0,
                    lead_time_days: 21,
                    next_restock: new Date('2024-03-01')
                },
                integration: {
                    deployment_support: true,
                    training_required: true,
                    complexity: 'expert',
                    setup_time_hours: 16
                }
            },
            {
                id: 'activelog_security_cam_4k',
                name: 'ActiveLog Security Camera 4K',
                manufacturer: 'ActiveLog Security',
                category: 'security_systems',
                subcategory: 'cameras',
                certification_level: 'gold',
                description: '4K security camera with night vision and AI motion detection',
                specifications: {
                    resolution: '4K @ 30fps, 1080p @ 60fps',
                    lens: 'Fixed 2.8mm, 110° FOV',
                    night_vision: 'IR LEDs, 30m range',
                    ai_features: 'Person/vehicle detection, facial recognition',
                    storage: 'microSD + cloud storage',
                    power: '12V DC or PoE+',
                    housing: 'IP66 weatherproof',
                    dimensions: '180x90x90mm'
                },
                pricing: {
                    unit_price: 285.00,
                    quantity_breaks: [
                        { min: 4, price: 265.00 },
                        { min: 12, price: 245.00 },
                        { min: 25, price: 225.00 }
                    ]
                },
                availability: {
                    in_stock: true,
                    stock_level: 75,
                    lead_time_days: 2,
                    next_restock: new Date('2024-02-10')
                },
                integration: {
                    streaming_protocols: ['RTSP', 'WebRTC', 'HLS'],
                    mobile_app: 'ActiveLog Security App',
                    complexity: 'intermediate',
                    setup_time_hours: 3
                }
            }
        ];

        certifiedDevices.forEach(device => {
            device.certified_date = new Date('2024-01-01');
            device.certification_expires = new Date('2025-01-01');
            device.support_level = 'full';
            device.warranty_years = 2;
            
            this.certifiedDevices.set(device.id, device);
            this.devices.set(device.id, device);
        });
    }

    async addDevice(deviceData) {
        try {
            const device = {
                id: deviceData.id || this.generateDeviceId(),
                name: deviceData.name,
                manufacturer: deviceData.manufacturer,
                category: deviceData.category,
                subcategory: deviceData.subcategory,
                description: deviceData.description,
                specifications: deviceData.specifications || {},
                pricing: deviceData.pricing || {},
                availability: deviceData.availability || { in_stock: false },
                integration: deviceData.integration || {},
                certification_level: deviceData.certification_level || 'none',
                support_level: deviceData.support_level || 'community',
                warranty_years: deviceData.warranty_years || 1,
                created_at: new Date(),
                updated_at: new Date(),
                metrics: {
                    views: 0,
                    downloads: 0,
                    reviews: 0,
                    average_rating: 0
                }
            };

            this.devices.set(device.id, device);
            this.emit('deviceAdded', device);

            return device;
        } catch (error) {
            this.emit('deviceError', { error: error.message, deviceData });
            throw error;
        }
    }

    async updateDevice(deviceId, updates) {
        const device = this.devices.get(deviceId);
        if (!device) {
            throw new Error('Device not found');
        }

        Object.keys(updates).forEach(key => {
            if (key !== 'id' && key !== 'created_at') {
                device[key] = updates[key];
            }
        });

        device.updated_at = new Date();
        this.devices.set(deviceId, device);

        this.emit('deviceUpdated', { device, updates });
        return device;
    }

    async searchDevices(searchCriteria) {
        const {
            query = '',
            category = '',
            subcategory = '',
            manufacturer = '',
            certification_level = '',
            in_stock_only = false,
            price_range = {},
            complexity = '',
            sort_by = 'name',
            sort_order = 'asc',
            page = 1,
            limit = 20
        } = searchCriteria;

        let devices = Array.from(this.devices.values());

        if (query) {
            const searchLower = query.toLowerCase();
            devices = devices.filter(device => 
                device.name.toLowerCase().includes(searchLower) ||
                device.description.toLowerCase().includes(searchLower) ||
                device.manufacturer.toLowerCase().includes(searchLower)
            );
        }

        if (category) {
            devices = devices.filter(device => device.category === category);
        }

        if (subcategory) {
            devices = devices.filter(device => device.subcategory === subcategory);
        }

        if (manufacturer) {
            devices = devices.filter(device => device.manufacturer === manufacturer);
        }

        if (certification_level) {
            devices = devices.filter(device => device.certification_level === certification_level);
        }

        if (in_stock_only) {
            devices = devices.filter(device => device.availability?.in_stock === true);
        }

        if (price_range.min !== undefined || price_range.max !== undefined) {
            devices = devices.filter(device => {
                const price = device.pricing?.unit_price || 0;
                if (price_range.min !== undefined && price < price_range.min) return false;
                if (price_range.max !== undefined && price > price_range.max) return false;
                return true;
            });
        }

        devices.sort((a, b) => {
            let aValue, bValue;
            
            switch (sort_by) {
                case 'name':
                    aValue = a.name.toLowerCase();
                    bValue = b.name.toLowerCase();
                    break;
                case 'price':
                    aValue = a.pricing?.unit_price || 0;
                    bValue = b.pricing?.unit_price || 0;
                    break;
                case 'rating':
                    aValue = a.metrics?.average_rating || 0;
                    bValue = b.metrics?.average_rating || 0;
                    break;
                case 'popularity':
                    aValue = a.metrics?.views || 0;
                    bValue = b.metrics?.views || 0;
                    break;
                default:
                    aValue = a.name.toLowerCase();
                    bValue = b.name.toLowerCase();
            }

            if (sort_order === 'desc') {
                return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
            } else {
                return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
            }
        });

        const startIndex = (page - 1) * limit;
        const endIndex = startIndex + limit;
        const paginatedDevices = devices.slice(startIndex, endIndex);

        return {
            devices: paginatedDevices,
            pagination: {
                current_page: page,
                total_pages: Math.ceil(devices.length / limit),
                total_devices: devices.length,
                has_next: endIndex < devices.length,
                has_prev: page > 1
            },
            categories: this.getAvailableCategories(devices),
            manufacturers: this.getAvailableManufacturers(devices),
            price_range: this.getPriceRange(devices)
        };
    }

    async checkCompatibility(deviceIds, systemRequirements = {}) {
        const devices = deviceIds.map(id => this.devices.get(id)).filter(Boolean);
        
        if (devices.length !== deviceIds.length) {
            throw new Error('Some devices not found');
        }

        const compatibility = {
            overall_compatible: true,
            issues: [],
            warnings: [],
            recommendations: [],
            device_interactions: []
        };

        for (let i = 0; i < devices.length; i++) {
            for (let j = i + 1; j < devices.length; j++) {
                const device1 = devices[i];
                const device2 = devices[j];
                
                const interaction = await this.checkDeviceInteraction(device1, device2);
                compatibility.device_interactions.push(interaction);
                
                if (!interaction.compatible) {
                    compatibility.overall_compatible = false;
                    compatibility.issues.push(...interaction.issues);
                }
                
                compatibility.warnings.push(...interaction.warnings);
            }
        }

        const powerAnalysis = this.analyzePowerRequirements(devices);
        if (!powerAnalysis.sufficient) {
            compatibility.overall_compatible = false;
            compatibility.issues.push('Insufficient power capacity');
            compatibility.recommendations.push('Add additional power source or upgrade existing one');
        }

        const communicationAnalysis = this.analyzeCommunicationRequirements(devices);
        if (communicationAnalysis.conflicts.length > 0) {
            compatibility.warnings.push('Communication protocol conflicts detected');
            compatibility.recommendations.push('Configure devices to use different channels or protocols');
        }

        return compatibility;
    }

    async checkDeviceInteraction(device1, device2) {
        const interaction = {
            device1_id: device1.id,
            device2_id: device2.id,
            compatible: true,
            issues: [],
            warnings: []
        };

        if (device1.specifications?.power && device2.specifications?.power) {
            const voltage1 = this.extractVoltage(device1.specifications.power);
            const voltage2 = this.extractVoltage(device2.specifications.power);
            
            if (voltage1 && voltage2 && Math.abs(voltage1 - voltage2) > 0.5) {
                interaction.warnings.push('Different operating voltages may require level shifters');
            }
        }

        const interfaces1 = device1.specifications?.interfaces || [];
        const interfaces2 = device2.specifications?.interfaces || [];
        const commonInterfaces = interfaces1.filter(i => interfaces2.includes(i));
        
        if (commonInterfaces.length === 0 && interfaces1.length > 0 && interfaces2.length > 0) {
            interaction.compatible = false;
            interaction.issues.push('No compatible communication interfaces');
        }

        return interaction;
    }

    analyzePowerRequirements(devices) {
        let totalPowerConsumption = 0;
        let powerSources = 0;
        let powerCapacity = 0;

        devices.forEach(device => {
            if (device.category === 'power_systems') {
                powerSources++;
                if (device.specifications?.power_output) {
                    const watts = this.extractWattage(device.specifications.power_output);
                    if (watts) powerCapacity += watts;
                }
            } else if (device.specifications?.power) {
                const watts = this.extractWattage(device.specifications.power);
                if (watts) totalPowerConsumption += watts;
            }
        });

        return {
            total_consumption: totalPowerConsumption,
            total_capacity: powerCapacity,
            sufficient: powerCapacity >= totalPowerConsumption * 1.2, // 20% margin
            utilization: powerCapacity > 0 ? (totalPowerConsumption / powerCapacity) * 100 : 0
        };
    }

    analyzeCommunicationRequirements(devices) {
        const protocols = {};
        const conflicts = [];

        devices.forEach(device => {
            const interfaces = device.specifications?.interfaces || [];
            const protocols_used = device.integration?.protocols || [];
            
            [...interfaces, ...protocols_used].forEach(protocol => {
                if (!protocols[protocol]) protocols[protocol] = [];
                protocols[protocol].push(device.id);
            });
        });

        Object.keys(protocols).forEach(protocol => {
            if (protocols[protocol].length > 1) {
                const conflictingProtocols = ['I2C', 'SPI'];
                if (conflictingProtocols.includes(protocol) && protocols[protocol].length > 4) {
                    conflicts.push({
                        protocol,
                        devices: protocols[protocol],
                        issue: 'Too many devices on same bus'
                    });
                }
            }
        });

        return { protocols, conflicts };
    }

    async generateIntegrationGuide(deviceIds) {
        const devices = deviceIds.map(id => this.devices.get(id)).filter(Boolean);
        
        const guide = {
            id: this.generateGuideId(),
            title: `Integration Guide: ${devices.map(d => d.name).join(', ')}`,
            devices: devices.map(d => ({ id: d.id, name: d.name })),
            created_at: new Date(),
            sections: []
        };

        guide.sections.push({
            title: 'Overview',
            content: this.generateOverviewSection(devices)
        });

        guide.sections.push({
            title: 'Hardware Requirements',
            content: this.generateHardwareSection(devices)
        });

        guide.sections.push({
            title: 'Wiring Diagram',
            content: this.generateWiringSection(devices)
        });

        guide.sections.push({
            title: 'Software Setup',
            content: this.generateSoftwareSection(devices)
        });

        guide.sections.push({
            title: 'Configuration',
            content: this.generateConfigurationSection(devices)
        });

        guide.sections.push({
            title: 'Testing & Validation',
            content: this.generateTestingSection(devices)
        });

        guide.sections.push({
            title: 'Troubleshooting',
            content: this.generateTroubleshootingSection(devices)
        });

        this.integrationGuides.set(guide.id, guide);
        return guide;
    }

    generateOverviewSection(devices) {
        const categories = [...new Set(devices.map(d => d.category))];
        return {
            description: `This guide covers the integration of ${devices.length} ActiveLog devices across ${categories.length} categories.`,
            estimated_time: `${Math.max(2, devices.length * 2)} hours`,
            complexity: this.calculateOverallComplexity(devices),
            prerequisites: ['Basic electronics knowledge', 'ActiveLog development environment']
        };
    }

    generateHardwareSection(devices) {
        const components = [];
        const tools = ['Multimeter', 'Breadboard or prototyping board', 'Jumper wires'];
        
        devices.forEach(device => {
            components.push(`${device.name} (${device.id})`);
            if (device.specifications?.interfaces?.includes('I2C')) {
                tools.push('I2C pull-up resistors (4.7kΩ)');
            }
        });

        return {
            components_needed: components,
            tools_required: [...new Set(tools)],
            safety_notes: ['Ensure proper ESD protection', 'Verify voltage levels before connecting']
        };
    }

    generateWiringSection(devices) {
        const connections = [];
        const powerConnections = [];
        
        devices.forEach(device => {
            if (device.specifications?.interfaces) {
                device.specifications.interfaces.forEach(interface => {
                    connections.push({
                        device: device.name,
                        interface: interface,
                        pins: this.getInterfacePins(interface)
                    });
                });
            }
            
            if (device.specifications?.power) {
                powerConnections.push({
                    device: device.name,
                    power_requirement: device.specifications.power
                });
            }
        });

        return {
            signal_connections: connections,
            power_connections: powerConnections,
            diagram_notes: 'Refer to device datasheets for exact pin configurations'
        };
    }

    generateSoftwareSection(devices) {
        const libraries = [];
        const setup_steps = [];
        
        devices.forEach(device => {
            if (device.integration?.sdk_version) {
                libraries.push(`ActiveLog SDK v${device.integration.sdk_version}`);
            }
            
            setup_steps.push(`Initialize ${device.name}`);
            
            if (device.integration?.calibration_required) {
                setup_steps.push(`Calibrate ${device.name}`);
            }
        });

        return {
            required_libraries: [...new Set(libraries)],
            setup_sequence: setup_steps,
            code_examples: '/examples/multi-device-integration'
        };
    }

    generateConfigurationSection(devices) {
        const configurations = [];
        
        devices.forEach(device => {
            configurations.push({
                device: device.name,
                config_file: `${device.id}.json`,
                key_parameters: this.getKeyParameters(device)
            });
        });

        return {
            device_configurations: configurations,
            network_settings: 'Configure WiFi credentials and server endpoints',
            data_formats: 'JSON with timestamp and device metadata'
        };
    }

    generateTestingSection(devices) {
        const tests = [];
        
        devices.forEach(device => {
            tests.push({
                device: device.name,
                basic_tests: ['Power-on test', 'Communication test', 'Data reading test'],
                advanced_tests: device.category === 'environmental_monitors' ? 
                    ['Calibration verification', 'Long-term stability test'] :
                    ['Functional test', 'Performance test']
            });
        });

        return {
            device_tests: tests,
            integration_tests: ['Multi-device communication', 'Data synchronization', 'Error handling'],
            success_criteria: 'All devices report data successfully for 24 hours'
        };
    }

    generateTroubleshootingSection(devices) {
        const commonIssues = [
            {
                problem: 'Device not responding',
                solutions: ['Check power connections', 'Verify I2C address conflicts', 'Reset device']
            },
            {
                problem: 'Inconsistent readings',
                solutions: ['Check calibration', 'Verify environmental conditions', 'Update firmware']
            },
            {
                problem: 'Communication errors',
                solutions: ['Check wiring', 'Verify protocol settings', 'Reduce bus speed']
            }
        ];

        return {
            common_issues: commonIssues,
            diagnostic_tools: ['ActiveLog Device Scanner', 'I2C Bus Analyzer', 'Logic Analyzer'],
            support_contacts: 'support@activelog.com'
        };
    }

    calculateOverallComplexity(devices) {
        const complexities = { beginner: 1, intermediate: 2, advanced: 3, expert: 4 };
        const avgComplexity = devices.reduce((sum, device) => {
            return sum + (complexities[device.integration?.complexity] || 1);
        }, 0) / devices.length;

        if (avgComplexity <= 1.5) return 'beginner';
        if (avgComplexity <= 2.5) return 'intermediate';
        if (avgComplexity <= 3.5) return 'advanced';
        return 'expert';
    }

    getInterfacePins(interface) {
        const pinMappings = {
            'I2C': ['SDA', 'SCL', 'VCC', 'GND'],
            'SPI': ['MISO', 'MOSI', 'SCK', 'CS', 'VCC', 'GND'],
            'UART': ['TX', 'RX', 'VCC', 'GND'],
            'GPIO': ['Digital I/O', 'VCC', 'GND']
        };
        return pinMappings[interface] || ['VCC', 'GND'];
    }

    getKeyParameters(device) {
        const categoryParams = {
            'environmental_monitors': ['sampling_rate', 'calibration_offset', 'averaging_window'],
            'security_systems': ['sensitivity', 'recording_quality', 'motion_threshold'],
            'marine_devices': ['depth_offset', 'species_filter', 'counting_threshold'],
            'power_systems': ['charge_voltage', 'current_limit', 'protection_settings']
        };
        
        return categoryParams[device.category] || ['device_id', 'update_interval', 'data_format'];
    }

    getAvailableCategories(devices) {
        const categories = {};
        devices.forEach(device => {
            if (!categories[device.category]) {
                categories[device.category] = 0;
            }
            categories[device.category]++;
        });
        return categories;
    }

    getAvailableManufacturers(devices) {
        const manufacturers = {};
        devices.forEach(device => {
            if (!manufacturers[device.manufacturer]) {
                manufacturers[device.manufacturer] = 0;
            }
            manufacturers[device.manufacturer]++;
        });
        return manufacturers;
    }

    getPriceRange(devices) {
        const prices = devices
            .map(device => device.pricing?.unit_price)
            .filter(price => price !== undefined);
        
        if (prices.length === 0) return { min: 0, max: 0 };
        
        return {
            min: Math.min(...prices),
            max: Math.max(...prices)
        };
    }

    extractVoltage(powerSpec) {
        const match = powerSpec.match(/(\d+\.?\d*)V/);
        return match ? parseFloat(match[1]) : null;
    }

    extractWattage(powerSpec) {
        const match = powerSpec.match(/(\d+\.?\d*)W/);
        return match ? parseFloat(match[1]) : null;
    }

    generateDeviceId() {
        return `device_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateGuideId() {
        return `guide_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    getSystemStats() {
        return {
            total_devices: this.devices.size,
            certified_devices: this.certifiedDevices.size,
            device_categories: this.deviceCategories.size,
            integration_guides: this.integrationGuides.size,
            metrics: this.deviceMetrics
        };
    }
}

export default ActiveLogDeviceCatalog;