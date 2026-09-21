import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';

class SensorPackageConfigurator extends EventEmitter {
    constructor() {
        super();
        this.sensorCatalog = new Map();
        this.packageTemplates = new Map();
        this.customPackages = new Map();
        this.compatibilityMatrix = new Map();
        this.calibrationProfiles = new Map();
        this.integrationGuides = new Map();
        this.configuratorMetrics = {
            total_sensors: 0,
            package_templates: 0,
            custom_configurations: 0,
            successful_integrations: 0
        };
        this.initializeSensorCatalog();
        this.initializePackageTemplates();
        this.initializeCompatibilityMatrix();
    }

    initializeSensorCatalog() {
        const sensors = [
            {
                id: 'temp_humidity_sht40',
                name: 'SHT40 Temperature & Humidity Sensor',
                manufacturer: 'Sensirion',
                category: 'environmental',
                subcategory: 'temperature_humidity',
                description: 'High-accuracy digital temperature and humidity sensor',
                specifications: {
                    measurements: ['temperature', 'humidity'],
                    temperature_range: '-40°C to +125°C',
                    temperature_accuracy: '±0.2°C',
                    humidity_range: '0-100% RH',
                    humidity_accuracy: '±1.8% RH',
                    response_time: '8 seconds',
                    operating_voltage: '1.8V to 3.6V',
                    current_consumption: '0.4µA (sleep), 1.5mA (measurement)',
                    interface: 'I2C',
                    package: '2.5x2.5x0.9mm DFN',
                    ip_rating: 'None (requires housing)'
                },
                features: [
                    'Factory calibrated',
                    'Digital output',
                    'Low power consumption',
                    'High accuracy',
                    'Small form factor'
                ],
                pricing: {
                    unit_price: 4.50,
                    quantity_breaks: [
                        { min: 10, price: 4.00 },
                        { min: 100, price: 3.50 },
                        { min: 1000, price: 2.80 }
                    ]
                },
                applications: ['HVAC', 'Weather stations', 'Smart homes', 'Greenhouses'],
                datasheet_url: '/datasheets/sht40.pdf',
                sample_code: '/samples/sht40.py'
            },
            {
                id: 'air_quality_pms7003',
                name: 'PMS7003 Air Quality Sensor',
                manufacturer: 'Plantower',
                category: 'environmental',
                subcategory: 'air_quality',
                description: 'Laser-based particulate matter sensor for PM1.0, PM2.5, PM10',
                specifications: {
                    measurements: ['PM1.0', 'PM2.5', 'PM10'],
                    measurement_range: '0-500 µg/m³',
                    accuracy: '±10 µg/m³ @ 0-100 µg/m³',
                    resolution: '1 µg/m³',
                    response_time: '10 seconds',
                    operating_voltage: '4.5V to 5.5V',
                    current_consumption: '100mA typical',
                    interface: 'UART',
                    dimensions: '65x42x23mm',
                    operating_temperature: '-10°C to +60°C',
                    lifespan: '5 years'
                },
                features: [
                    'Laser scattering detection',
                    'Real-time measurement',
                    'Digital output',
                    'Long lifespan',
                    'Stable performance'
                ],
                pricing: {
                    unit_price: 22.00,
                    quantity_breaks: [
                        { min: 5, price: 20.00 },
                        { min: 25, price: 18.50 },
                        { min: 100, price: 16.00 }
                    ]
                },
                applications: ['Air quality monitoring', 'Smart cities', 'Indoor air quality', 'Industrial monitoring'],
                datasheet_url: '/datasheets/pms7003.pdf',
                sample_code: '/samples/pms7003.py'
            },
            {
                id: 'ph_sensor_dfrobot',
                name: 'DFRobot pH Sensor Kit',
                manufacturer: 'DFRobot',
                category: 'water_quality',
                subcategory: 'chemical',
                description: 'Industrial-grade pH sensor with temperature compensation',
                specifications: {
                    measurements: ['pH', 'temperature'],
                    ph_range: '0-14 pH',
                    ph_accuracy: '±0.1 pH',
                    temperature_range: '0-80°C',
                    temperature_accuracy: '±1°C',
                    operating_voltage: '3.3V to 5V',
                    current_consumption: '5mA',
                    interface: 'Analog (ADC required)',
                    probe_material: 'Glass electrode',
                    cable_length: '1m BNC cable',
                    ip_rating: 'IP68 (probe only)'
                },
                features: [
                    'Temperature compensation',
                    'Industrial-grade probe',
                    'Wide pH range',
                    'Waterproof probe',
                    'BNC connector'
                ],
                pricing: {
                    unit_price: 85.00,
                    quantity_breaks: [
                        { min: 3, price: 80.00 },
                        { min: 10, price: 75.00 },
                        { min: 25, price: 68.00 }
                    ]
                },
                applications: ['Water treatment', 'Aquaculture', 'Swimming pools', 'Environmental monitoring'],
                datasheet_url: '/datasheets/dfrobot_ph.pdf',
                sample_code: '/samples/ph_sensor.py'
            },
            {
                id: 'light_sensor_tsl2591',
                name: 'TSL2591 Light Sensor',
                manufacturer: 'AMS',
                category: 'environmental',
                subcategory: 'light',
                description: 'High dynamic range light sensor with IR compensation',
                specifications: {
                    measurements: ['visible_light', 'ir_light', 'full_spectrum'],
                    range: '0.1 to 88,000 lux',
                    resolution: '16-bit',
                    spectral_range: '300-1100nm',
                    operating_voltage: '3.3V',
                    current_consumption: '0.4mA active, 2.5µA sleep',
                    interface: 'I2C',
                    package: '3.8x2.6x0.7mm',
                    temperature_range: '-30°C to +80°C'
                },
                features: [
                    'High dynamic range',
                    'IR compensation',
                    'Programmable gain',
                    'Interrupt capability',
                    'Low power'
                ],
                pricing: {
                    unit_price: 6.75,
                    quantity_breaks: [
                        { min: 10, price: 6.25 },
                        { min: 100, price: 5.50 },
                        { min: 500, price: 4.80 }
                    ]
                },
                applications: ['Smart lighting', 'Display brightness control', 'Solar panel optimization', 'Agriculture'],
                datasheet_url: '/datasheets/tsl2591.pdf',
                sample_code: '/samples/tsl2591.py'
            },
            {
                id: 'accelerometer_mpu6050',
                name: 'MPU6050 6-Axis Motion Sensor',
                manufacturer: 'InvenSense',
                category: 'motion',
                subcategory: 'inertial',
                description: '6-axis accelerometer and gyroscope with motion processing',
                specifications: {
                    measurements: ['acceleration_xyz', 'angular_velocity_xyz', 'temperature'],
                    accelerometer_range: '±2g, ±4g, ±8g, ±16g',
                    gyroscope_range: '±250°/s, ±500°/s, ±1000°/s, ±2000°/s',
                    accelerometer_sensitivity: '16384 LSB/g @ ±2g',
                    gyroscope_sensitivity: '131 LSB/°/s @ ±250°/s',
                    operating_voltage: '2.375V to 3.46V',
                    current_consumption: '3.9mA normal, 0.5mA sleep',
                    interface: 'I2C',
                    package: '4x4x0.9mm QFN',
                    sample_rate: 'Up to 8kHz'
                },
                features: [
                    '6-axis sensing',
                    'On-chip motion processing',
                    'Digital motion processor',
                    'Low power modes',
                    'Programmable interrupts'
                ],
                pricing: {
                    unit_price: 3.25,
                    quantity_breaks: [
                        { min: 10, price: 2.95 },
                        { min: 100, price: 2.50 },
                        { min: 1000, price: 1.95 }
                    ]
                },
                applications: ['Wearables', 'Drones', 'Robotics', 'Gaming controllers'],
                datasheet_url: '/datasheets/mpu6050.pdf',
                sample_code: '/samples/mpu6050.py'
            },
            {
                id: 'pressure_bmp388',
                name: 'BMP388 Precision Barometric Pressure Sensor',
                manufacturer: 'Bosch',
                category: 'environmental',
                subcategory: 'pressure',
                description: 'High-precision barometric pressure sensor with altitude calculation',
                specifications: {
                    measurements: ['pressure', 'temperature', 'altitude'],
                    pressure_range: '300-1250 hPa',
                    pressure_accuracy: '±0.08 hPa (typical)',
                    altitude_accuracy: '±0.5m',
                    temperature_range: '-40°C to +85°C',
                    temperature_accuracy: '±0.5°C',
                    operating_voltage: '1.71V to 3.6V',
                    current_consumption: '3.4µA @ 1Hz',
                    interface: 'I2C/SPI',
                    package: '2.0x2.0x0.75mm LGA',
                    response_time: '5ms'
                },
                features: [
                    'High precision',
                    'Low power consumption',
                    'Temperature compensation',
                    'Altitude calculation',
                    'Water-resistant'
                ],
                pricing: {
                    unit_price: 8.95,
                    quantity_breaks: [
                        { min: 10, price: 8.25 },
                        { min: 100, price: 7.50 },
                        { min: 500, price: 6.75 }
                    ]
                },
                applications: ['Weather stations', 'Altimeters', 'Drones', 'Indoor navigation'],
                datasheet_url: '/datasheets/bmp388.pdf',
                sample_code: '/samples/bmp388.py'
            },
            {
                id: 'distance_vl53l1x',
                name: 'VL53L1X Time-of-Flight Distance Sensor',
                manufacturer: 'STMicroelectronics',
                category: 'proximity',
                subcategory: 'distance',
                description: 'Laser-ranging sensor with high accuracy up to 4 meters',
                specifications: {
                    measurements: ['distance'],
                    range: '40mm to 4000mm',
                    accuracy: '±25mm',
                    field_of_view: '27°',
                    ambient_light_immunity: '100k lux',
                    operating_voltage: '2.6V to 3.5V',
                    current_consumption: '20mA active, 5µA standby',
                    interface: 'I2C',
                    package: '4.9x2.5x1.56mm',
                    update_rate: 'Up to 100Hz'
                },
                features: [
                    'Long range detection',
                    'High accuracy',
                    'Immune to ambient light',
                    'Fast update rate',
                    'Eye-safe laser'
                ],
                pricing: {
                    unit_price: 12.50,
                    quantity_breaks: [
                        { min: 10, price: 11.75 },
                        { min: 100, price: 10.50 },
                        { min: 500, price: 9.25 }
                    ]
                },
                applications: ['Robotics', 'Drone landing', 'Level monitoring', 'Presence detection'],
                datasheet_url: '/datasheets/vl53l1x.pdf',
                sample_code: '/samples/vl53l1x.py'
            },
            {
                id: 'gps_neo8m',
                name: 'NEO-8M GPS Module',
                manufacturer: 'u-blox',
                category: 'positioning',
                subcategory: 'gnss',
                description: 'High-performance GPS/GLONASS receiver with external antenna',
                specifications: {
                    measurements: ['latitude', 'longitude', 'altitude', 'speed', 'heading'],
                    gnss_systems: ['GPS', 'GLONASS', 'Galileo', 'BeiDou'],
                    position_accuracy: '2.5m CEP',
                    altitude_accuracy: '5m',
                    velocity_accuracy: '0.05 m/s',
                    time_to_first_fix: '29s cold start',
                    update_rate: '1-18 Hz configurable',
                    operating_voltage: '2.7V to 3.6V',
                    current_consumption: '67mA acquisition, 24mA tracking',
                    interface: 'UART',
                    antenna: 'External ceramic patch antenna'
                },
                features: [
                    'Multi-GNSS support',
                    'High sensitivity',
                    'Low power consumption',
                    'Configurable update rate',
                    'External antenna'
                ],
                pricing: {
                    unit_price: 18.50,
                    quantity_breaks: [
                        { min: 5, price: 17.25 },
                        { min: 25, price: 16.00 },
                        { min: 100, price: 14.50 }
                    ]
                },
                applications: ['Asset tracking', 'Navigation', 'Survey equipment', 'Precision agriculture'],
                datasheet_url: '/datasheets/neo8m.pdf',
                sample_code: '/samples/neo8m.py'
            }
        ];

        sensors.forEach(sensor => {
            sensor.created_at = new Date();
            sensor.stock_status = 'in_stock';
            sensor.lead_time_days = Math.floor(Math.random() * 14) + 1;
            sensor.certification = ['CE', 'FCC', 'RoHS'];
            sensor.compatibility_tags = this.generateCompatibilityTags(sensor);
            sensor.integration_difficulty = this.calculateIntegrationDifficulty(sensor);
            
            this.sensorCatalog.set(sensor.id, sensor);
        });
    }

    initializePackageTemplates() {
        const templates = [
            {
                id: 'weather_station_basic',
                name: 'Basic Weather Station Package',
                description: 'Complete weather monitoring solution for outdoor installations',
                category: 'environmental_monitoring',
                target_applications: ['Agriculture', 'Construction', 'Research', 'Home weather'],
                included_sensors: [
                    { sensor_id: 'temp_humidity_sht40', quantity: 1, purpose: 'Air temperature and humidity' },
                    { sensor_id: 'pressure_bmp388', quantity: 1, purpose: 'Barometric pressure and altitude' },
                    { sensor_id: 'light_sensor_tsl2591', quantity: 1, purpose: 'Solar radiation and light levels' }
                ],
                additional_components: [
                    { name: 'Solar radiation shield', description: 'Protects sensors from direct sunlight' },
                    { name: 'Weatherproof enclosure', description: 'IP65 rated enclosure' },
                    { name: 'Mounting hardware', description: 'Pole and wall mounting options' },
                    { name: 'Calibration certificate', description: 'Factory calibration documentation' }
                ],
                specifications: {
                    power_consumption: '15mA average',
                    operating_temperature: '-40°C to +80°C',
                    data_update_rate: '1 minute intervals',
                    wireless_range: '1km LoRaWAN',
                    battery_life: '2+ years with solar charging',
                    accuracy_class: 'Research grade'
                },
                pricing: {
                    package_price: 185.00,
                    individual_total: 210.00,
                    savings: 25.00,
                    installation_service: 150.00
                },
                estimated_setup_time: '2-4 hours',
                difficulty_level: 'beginner',
                documentation: {
                    assembly_guide: '/guides/weather_station_assembly.pdf',
                    programming_tutorial: '/tutorials/weather_station_code.html',
                    calibration_procedure: '/procedures/weather_calibration.pdf'
                }
            },
            {
                id: 'air_quality_monitor_pro',
                name: 'Professional Air Quality Monitor',
                description: 'Comprehensive air quality monitoring for indoor and outdoor environments',
                category: 'air_quality_monitoring',
                target_applications: ['Smart cities', 'Industrial monitoring', 'School campuses', 'Healthcare facilities'],
                included_sensors: [
                    { sensor_id: 'air_quality_pms7003', quantity: 1, purpose: 'Particulate matter PM1.0, PM2.5, PM10' },
                    { sensor_id: 'temp_humidity_sht40', quantity: 1, purpose: 'Environmental compensation' },
                    { sensor_id: 'pressure_bmp388', quantity: 1, purpose: 'Atmospheric pressure reference' }
                ],
                additional_components: [
                    { name: 'Air sampling pump', description: 'Ensures consistent airflow through sensors' },
                    { name: 'Particle filter', description: 'Pre-filter for large particles' },
                    { name: 'Heated inlet', description: 'Prevents condensation in humid conditions' },
                    { name: 'Data logger', description: '32GB storage with cellular connectivity' }
                ],
                specifications: {
                    power_consumption: '150mA average',
                    operating_temperature: '-20°C to +60°C',
                    data_update_rate: '1 second to 10 minutes configurable',
                    connectivity: '4G LTE, WiFi, Ethernet',
                    battery_life: '48 hours backup',
                    measurement_accuracy: '±5% of reading'
                },
                pricing: {
                    package_price: 485.00,
                    individual_total: 560.00,
                    savings: 75.00,
                    annual_data_plan: 180.00
                },
                estimated_setup_time: '4-6 hours',
                difficulty_level: 'intermediate',
                documentation: {
                    installation_manual: '/manuals/air_quality_installation.pdf',
                    software_configuration: '/software/air_quality_config.html',
                    maintenance_schedule: '/maintenance/air_quality_schedule.pdf'
                }
            },
            {
                id: 'water_quality_sensor_kit',
                name: 'Complete Water Quality Sensor Kit',
                description: 'Multi-parameter water quality monitoring for aquaculture and environmental applications',
                category: 'water_quality_monitoring',
                target_applications: ['Aquaculture', 'Water treatment', 'Environmental monitoring', 'Swimming pools'],
                included_sensors: [
                    { sensor_id: 'ph_sensor_dfrobot', quantity: 1, purpose: 'pH measurement' },
                    { sensor_id: 'temp_humidity_sht40', quantity: 1, purpose: 'Water temperature (waterproof version)' },
                    { sensor_id: 'pressure_bmp388', quantity: 1, purpose: 'Depth measurement in sealed housing' }
                ],
                additional_components: [
                    { name: 'Conductivity sensor', description: 'Measures water conductivity and TDS' },
                    { name: 'Dissolved oxygen sensor', description: 'Optical DO sensor with 2-year life' },
                    { name: 'Turbidity sensor', description: 'Nephelometric turbidity measurement' },
                    { name: 'Multi-parameter probe', description: 'All sensors integrated in single probe' },
                    { name: 'Calibration solutions', description: 'pH 4.0, 7.0, 10.0 buffer solutions' }
                ],
                specifications: {
                    power_consumption: '50mA measurement, 5mA standby',
                    operating_temperature: '0°C to +50°C',
                    depth_rating: '100m waterproof',
                    measurement_interval: '10 seconds to 1 hour',
                    data_storage: '1 year at 1-minute intervals',
                    calibration_stability: '±2% drift per month'
                },
                pricing: {
                    package_price: 750.00,
                    individual_total: 890.00,
                    savings: 140.00,
                    annual_calibration: 250.00
                },
                estimated_setup_time: '6-8 hours including calibration',
                difficulty_level: 'advanced',
                documentation: {
                    deployment_guide: '/guides/water_quality_deployment.pdf',
                    calibration_manual: '/manuals/water_sensor_calibration.pdf',
                    troubleshooting_guide: '/support/water_quality_troubleshooting.pdf'
                }
            },
            {
                id: 'iot_motion_security_kit',
                name: 'IoT Motion Security Package',
                description: 'Smart motion detection and security monitoring system',
                category: 'security_monitoring',
                target_applications: ['Home security', 'Warehouse monitoring', 'Perimeter security', 'Wildlife detection'],
                included_sensors: [
                    { sensor_id: 'accelerometer_mpu6050', quantity: 2, purpose: 'Vibration and tilt detection' },
                    { sensor_id: 'distance_vl53l1x', quantity: 1, purpose: 'Proximity detection' },
                    { sensor_id: 'light_sensor_tsl2591', quantity: 1, purpose: 'Ambient light monitoring' }
                ],
                additional_components: [
                    { name: 'PIR motion sensor', description: 'Passive infrared motion detection' },
                    { name: 'Sound level sensor', description: 'Acoustic monitoring and noise detection' },
                    { name: 'Magnetic door sensor', description: 'Door and window open/close detection' },
                    { name: 'Cellular modem', description: '4G connectivity for remote alerts' },
                    { name: 'Solar charging kit', description: '10W solar panel with battery backup' }
                ],
                specifications: {
                    power_consumption: '25mA active monitoring, 1mA sleep',
                    detection_range: '10m PIR, 4m ToF distance',
                    operating_temperature: '-20°C to +70°C',
                    alert_methods: 'SMS, email, push notifications, siren',
                    battery_life: '6 months with daily alerts',
                    false_alarm_rate: '<1% with AI filtering'
                },
                pricing: {
                    package_price: 320.00,
                    individual_total: 385.00,
                    savings: 65.00,
                    monthly_monitoring: 15.00
                },
                estimated_setup_time: '3-5 hours',
                difficulty_level: 'intermediate',
                documentation: {
                    setup_wizard: '/setup/security_system_wizard.html',
                    mobile_app_guide: '/apps/security_app_guide.pdf',
                    alert_configuration: '/config/alert_setup.pdf'
                }
            },
            {
                id: 'precision_agriculture_kit',
                name: 'Precision Agriculture Sensor Package',
                description: 'Advanced agricultural monitoring for crop optimization and yield improvement',
                category: 'agriculture_monitoring',
                target_applications: ['Crop monitoring', 'Greenhouse automation', 'Irrigation control', 'Soil analysis'],
                included_sensors: [
                    { sensor_id: 'temp_humidity_sht40', quantity: 2, purpose: 'Air and soil climate monitoring' },
                    { sensor_id: 'light_sensor_tsl2591', quantity: 1, purpose: 'Photosynthetically active radiation' },
                    { sensor_id: 'pressure_bmp388', quantity: 1, purpose: 'Weather monitoring' },
                    { sensor_id: 'gps_neo8m', quantity: 1, purpose: 'Field mapping and positioning' }
                ],
                additional_components: [
                    { name: 'Soil moisture sensors', description: '5x capacitive soil moisture sensors' },
                    { name: 'Soil pH probe', description: 'Direct soil pH measurement probe' },
                    { name: 'Leaf wetness sensor', description: 'Disease risk assessment' },
                    { name: 'Wind speed/direction', description: 'Anemometer with wind vane' },
                    { name: 'Rain gauge', description: 'Tipping bucket precipitation sensor' },
                    { name: 'Irrigation controller', description: 'Automated irrigation valve control' }
                ],
                specifications: {
                    power_consumption: '200mA peak, 20mA average',
                    monitoring_area: 'Up to 10 hectares',
                    data_resolution: '1-minute intervals',
                    connectivity: 'LoRaWAN mesh network',
                    battery_life: '1 year with solar supplement',
                    environmental_rating: 'IP67 weatherproof'
                },
                pricing: {
                    package_price: 1250.00,
                    individual_total: 1485.00,
                    savings: 235.00,
                    software_license: 480.00
                },
                estimated_setup_time: '8-12 hours field installation',
                difficulty_level: 'expert',
                documentation: {
                    field_installation_guide: '/agriculture/field_installation.pdf',
                    crop_specific_calibration: '/agriculture/crop_calibration.pdf',
                    irrigation_automation: '/agriculture/irrigation_control.pdf'
                }
            }
        ];

        templates.forEach(template => {
            template.created_at = new Date();
            template.popularity_score = Math.random() * 100;
            template.success_rate = 0.85 + Math.random() * 0.13;
            template.average_rating = 4.0 + Math.random();
            template.total_deployments = Math.floor(Math.random() * 500) + 100;
            
            this.packageTemplates.set(template.id, template);
        });
    }

    initializeCompatibilityMatrix() {
        const compatibilityRules = [
            {
                sensor1: 'temp_humidity_sht40',
                sensor2: 'pressure_bmp388',
                compatibility: 'excellent',
                notes: 'Both use I2C, different addresses, complementary environmental data'
            },
            {
                sensor1: 'air_quality_pms7003',
                sensor2: 'temp_humidity_sht40',
                compatibility: 'excellent',
                notes: 'Temperature/humidity compensation improves air quality accuracy'
            },
            {
                sensor1: 'ph_sensor_dfrobot',
                sensor2: 'temp_humidity_sht40',
                compatibility: 'good',
                notes: 'Temperature compensation required for pH accuracy'
            },
            {
                sensor1: 'accelerometer_mpu6050',
                sensor2: 'distance_vl53l1x',
                compatibility: 'good',
                notes: 'Both use I2C, may need address modification'
            },
            {
                sensor1: 'gps_neo8m',
                sensor2: 'accelerometer_mpu6050',
                compatibility: 'excellent',
                notes: 'GPS uses UART, MPU6050 uses I2C, no interference'
            }
        ];

        compatibilityRules.forEach(rule => {
            const key = `${rule.sensor1}_${rule.sensor2}`;
            this.compatibilityMatrix.set(key, rule);
            
            const reverseKey = `${rule.sensor2}_${rule.sensor1}`;
            this.compatibilityMatrix.set(reverseKey, {
                ...rule,
                sensor1: rule.sensor2,
                sensor2: rule.sensor1
            });
        });
    }

    async createCustomPackage(packageRequest) {
        try {
            const customPackage = {
                id: this.generatePackageId(),
                name: packageRequest.name,
                description: packageRequest.description,
                created_by: packageRequest.user_id,
                created_at: new Date(),
                category: packageRequest.category,
                target_application: packageRequest.target_application,
                selected_sensors: packageRequest.sensors || [],
                configuration: {
                    power_budget: packageRequest.power_budget,
                    size_constraints: packageRequest.size_constraints,
                    environmental_requirements: packageRequest.environmental_requirements,
                    connectivity_requirements: packageRequest.connectivity_requirements,
                    data_requirements: packageRequest.data_requirements
                },
                validation_results: {},
                optimization_suggestions: [],
                estimated_costs: {},
                integration_complexity: 'pending',
                status: 'draft'
            };

            await this.validatePackageConfiguration(customPackage);
            await this.optimizePackageConfiguration(customPackage);
            await this.calculatePackageCosts(customPackage);
            await this.generateIntegrationPlan(customPackage);

            this.customPackages.set(customPackage.id, customPackage);
            this.emit('packageCreated', customPackage);

            return customPackage;
        } catch (error) {
            this.emit('packageError', { error: error.message, packageRequest });
            throw error;
        }
    }

    async validatePackageConfiguration(customPackage) {
        const validation = {
            compatibility_check: 'pending',
            power_analysis: 'pending',
            interface_conflicts: 'pending',
            environmental_compatibility: 'pending',
            overall_status: 'pending',
            issues: [],
            warnings: []
        };

        const sensors = customPackage.selected_sensors.map(sensorRef => 
            this.sensorCatalog.get(sensorRef.sensor_id)
        ).filter(Boolean);

        validation.compatibility_check = await this.checkSensorCompatibility(sensors);
        validation.power_analysis = await this.analyzePowerRequirements(sensors, customPackage.configuration);
        validation.interface_conflicts = await this.checkInterfaceConflicts(sensors);
        validation.environmental_compatibility = await this.checkEnvironmentalCompatibility(sensors, customPackage.configuration);

        const hasIssues = validation.compatibility_check.issues.length > 0 ||
                         validation.power_analysis.issues.length > 0 ||
                         validation.interface_conflicts.issues.length > 0 ||
                         validation.environmental_compatibility.issues.length > 0;

        validation.overall_status = hasIssues ? 'issues_found' : 'valid';
        validation.issues = [
            ...validation.compatibility_check.issues,
            ...validation.power_analysis.issues,
            ...validation.interface_conflicts.issues,
            ...validation.environmental_compatibility.issues
        ];

        customPackage.validation_results = validation;
        return validation;
    }

    async checkSensorCompatibility(sensors) {
        const compatibility = {
            status: 'compatible',
            issues: [],
            warnings: [],
            compatibility_matrix: []
        };

        for (let i = 0; i < sensors.length; i++) {
            for (let j = i + 1; j < sensors.length; j++) {
                const sensor1 = sensors[i];
                const sensor2 = sensors[j];
                const key = `${sensor1.id}_${sensor2.id}`;
                
                const compatibilityRule = this.compatibilityMatrix.get(key);
                
                if (compatibilityRule) {
                    compatibility.compatibility_matrix.push(compatibilityRule);
                    
                    if (compatibilityRule.compatibility === 'poor') {
                        compatibility.issues.push(
                            `Poor compatibility between ${sensor1.name} and ${sensor2.name}: ${compatibilityRule.notes}`
                        );
                        compatibility.status = 'issues_found';
                    } else if (compatibilityRule.compatibility === 'good') {
                        compatibility.warnings.push(
                            `Good compatibility with considerations: ${sensor1.name} and ${sensor2.name}: ${compatibilityRule.notes}`
                        );
                    }
                } else {
                    compatibility.warnings.push(
                        `Unknown compatibility between ${sensor1.name} and ${sensor2.name} - manual verification recommended`
                    );
                }
            }
        }

        return compatibility;
    }

    async analyzePowerRequirements(sensors, configuration) {
        const powerAnalysis = {
            total_power_consumption: 0,
            peak_power_consumption: 0,
            average_power_consumption: 0,
            power_breakdown: [],
            battery_life_estimate: 0,
            power_optimization_suggestions: [],
            issues: [],
            warnings: []
        };

        sensors.forEach(sensor => {
            const currentConsumption = this.extractCurrentConsumption(sensor.specifications.current_consumption);
            const sensorPower = {
                sensor_id: sensor.id,
                sensor_name: sensor.name,
                current_typical: currentConsumption.typical,
                current_peak: currentConsumption.peak,
                voltage: this.extractVoltage(sensor.specifications.operating_voltage),
                power_typical: currentConsumption.typical * this.extractVoltage(sensor.specifications.operating_voltage) / 1000,
                power_peak: currentConsumption.peak * this.extractVoltage(sensor.specifications.operating_voltage) / 1000
            };

            powerAnalysis.power_breakdown.push(sensorPower);
            powerAnalysis.average_power_consumption += sensorPower.power_typical;
            powerAnalysis.peak_power_consumption += sensorPower.power_peak;
        });

        powerAnalysis.total_power_consumption = powerAnalysis.average_power_consumption;

        if (configuration.power_budget && powerAnalysis.average_power_consumption > configuration.power_budget) {
            powerAnalysis.issues.push(
                `Power consumption (${powerAnalysis.average_power_consumption.toFixed(2)}mW) exceeds budget (${configuration.power_budget}mW)`
            );
        }

        const standardBattery = 3000; // mAh
        const averageCurrentDraw = powerAnalysis.average_power_consumption / 3.3; // Assuming 3.3V system
        powerAnalysis.battery_life_estimate = standardBattery / averageCurrentDraw;

        if (powerAnalysis.battery_life_estimate < 24) {
            powerAnalysis.warnings.push(
                `Estimated battery life is only ${powerAnalysis.battery_life_estimate.toFixed(1)} hours with standard battery`
            );
            powerAnalysis.power_optimization_suggestions.push('Consider adding solar charging or larger battery');
        }

        return powerAnalysis;
    }

    async checkInterfaceConflicts(sensors) {
        const interfaceAnalysis = {
            interfaces_used: {},
            potential_conflicts: [],
            address_conflicts: [],
            timing_conflicts: [],
            issues: [],
            recommendations: []
        };

        sensors.forEach(sensor => {
            const interface = sensor.specifications.interface;
            
            if (!interfaceAnalysis.interfaces_used[interface]) {
                interfaceAnalysis.interfaces_used[interface] = [];
            }
            
            interfaceAnalysis.interfaces_used[interface].push({
                sensor_id: sensor.id,
                sensor_name: sensor.name
            });
        });

        Object.entries(interfaceAnalysis.interfaces_used).forEach(([interface, sensorList]) => {
            if (interface === 'I2C' && sensorList.length > 1) {
                interfaceAnalysis.potential_conflicts.push({
                    interface: 'I2C',
                    sensors: sensorList,
                    issue: 'Multiple sensors on I2C bus - address conflicts possible',
                    solution: 'Verify each sensor has unique I2C address or use I2C multiplexer'
                });
            }
            
            if (interface === 'SPI' && sensorList.length > 4) {
                interfaceAnalysis.issues.push(
                    `Too many SPI devices (${sensorList.length}). Most microcontrollers support maximum 4 SPI devices.`
                );
            }
            
            if (interface === 'UART' && sensorList.length > 2) {
                interfaceAnalysis.issues.push(
                    `Multiple UART devices detected. Most microcontrollers have limited UART ports.`
                );
                interfaceAnalysis.recommendations.push('Consider using software UART or UART multiplexer');
            }
        });

        return interfaceAnalysis;
    }

    async checkEnvironmentalCompatibility(sensors, configuration) {
        const environmentalCheck = {
            temperature_range: { min: -100, max: 150 },
            humidity_compatibility: true,
            ip_rating_analysis: {},
            environmental_issues: [],
            protection_recommendations: []
        };

        sensors.forEach(sensor => {
            const tempRange = this.extractTemperatureRange(sensor.specifications.operating_temperature || sensor.specifications.temperature_range);
            
            if (tempRange.min > environmentalCheck.temperature_range.min) {
                environmentalCheck.temperature_range.min = tempRange.min;
            }
            if (tempRange.max < environmentalCheck.temperature_range.max) {
                environmentalCheck.temperature_range.max = tempRange.max;
            }

            if (sensor.specifications.ip_rating && sensor.specifications.ip_rating === 'None (requires housing)') {
                environmentalCheck.protection_recommendations.push(
                    `${sensor.name} requires protective housing for outdoor use`
                );
            }
        });

        if (configuration.environmental_requirements) {
            const reqTemp = configuration.environmental_requirements.temperature_range;
            
            if (reqTemp && (reqTemp.min < environmentalCheck.temperature_range.min || 
                           reqTemp.max > environmentalCheck.temperature_range.max)) {
                environmentalCheck.environmental_issues.push(
                    `Required temperature range (${reqTemp.min}°C to ${reqTemp.max}°C) exceeds sensor capabilities (${environmentalCheck.temperature_range.min}°C to ${environmentalCheck.temperature_range.max}°C)`
                );
            }
        }

        return environmentalCheck;
    }

    async optimizePackageConfiguration(customPackage) {
        const optimizations = {
            power_optimizations: [],
            cost_optimizations: [],
            performance_optimizations: [],
            integration_optimizations: []
        };

        const sensors = customPackage.selected_sensors.map(sensorRef => 
            this.sensorCatalog.get(sensorRef.sensor_id)
        ).filter(Boolean);

        optimizations.power_optimizations = await this.suggestPowerOptimizations(sensors, customPackage);
        optimizations.cost_optimizations = await this.suggestCostOptimizations(sensors, customPackage);
        optimizations.performance_optimizations = await this.suggestPerformanceOptimizations(sensors, customPackage);
        optimizations.integration_optimizations = await this.suggestIntegrationOptimizations(sensors, customPackage);

        customPackage.optimization_suggestions = optimizations;
        return optimizations;
    }

    async suggestPowerOptimizations(sensors, customPackage) {
        const suggestions = [];

        const highPowerSensors = sensors.filter(sensor => {
            const current = this.extractCurrentConsumption(sensor.specifications.current_consumption);
            return current.typical > 50; // mA
        });

        if (highPowerSensors.length > 0) {
            suggestions.push({
                type: 'power_scheduling',
                description: `Implement duty cycling for high-power sensors: ${highPowerSensors.map(s => s.name).join(', ')}`,
                potential_savings: '40-60% power reduction',
                implementation: 'Turn sensors on only when measurements are needed'
            });
        }

        if (sensors.some(s => s.specifications.interface === 'UART' && s.id === 'air_quality_pms7003')) {
            suggestions.push({
                type: 'sensor_scheduling',
                description: 'PMS7003 can be turned on/off between measurements',
                potential_savings: '80% power reduction',
                implementation: 'Power on for 30 seconds every 5 minutes'
            });
        }

        if (sensors.length > 3) {
            suggestions.push({
                type: 'system_optimization',
                description: 'Consider using a low-power microcontroller with deep sleep modes',
                potential_savings: '70% system power reduction',
                implementation: 'Use ESP32 or similar with deep sleep between measurement cycles'
            });
        }

        return suggestions;
    }

    async suggestCostOptimizations(sensors, customPackage) {
        const suggestions = [];
        const totalCost = sensors.reduce((sum, sensor) => sum + sensor.pricing.unit_price, 0);

        if (totalCost > 200) {
            suggestions.push({
                type: 'bulk_purchasing',
                description: 'Consider bulk purchasing to reduce per-unit costs',
                potential_savings: '15-25% cost reduction',
                minimum_quantity: 10
            });
        }

        const expensiveSensors = sensors.filter(s => s.pricing.unit_price > 50);
        if (expensiveSensors.length > 0) {
            suggestions.push({
                type: 'alternative_sensors',
                description: `Consider lower-cost alternatives for: ${expensiveSensors.map(s => s.name).join(', ')}`,
                potential_savings: '20-40% cost reduction',
                trade_offs: 'May reduce accuracy or features'
            });
        }

        return suggestions;
    }

    async suggestPerformanceOptimizations(sensors, customPackage) {
        const suggestions = [];

        if (sensors.some(s => s.category === 'environmental' && s.subcategory === 'temperature_humidity')) {
            suggestions.push({
                type: 'temperature_compensation',
                description: 'Use temperature sensor data to compensate other sensor readings',
                benefit: 'Improved accuracy across all environmental sensors',
                implementation: 'Apply temperature correction factors in firmware'
            });
        }

        const i2cSensors = sensors.filter(s => s.specifications.interface === 'I2C');
        if (i2cSensors.length > 2) {
            suggestions.push({
                type: 'i2c_optimization',
                description: 'Optimize I2C bus speed and timing for multiple sensors',
                benefit: 'Reduced measurement latency and improved reliability',
                implementation: 'Use 400kHz I2C speed with proper pull-up resistors'
            });
        }

        return suggestions;
    }

    async suggestIntegrationOptimizations(sensors, customPackage) {
        const suggestions = [];

        if (sensors.length > 4) {
            suggestions.push({
                type: 'modular_design',
                description: 'Consider breaking into multiple sensor modules',
                benefit: 'Easier troubleshooting and maintenance',
                implementation: 'Group sensors by function or interface type'
            });
        }

        const outdoorSensors = sensors.filter(s => 
            s.applications.some(app => app.toLowerCase().includes('outdoor') || 
                               app.toLowerCase().includes('weather') ||
                               app.toLowerCase().includes('environmental'))
        );
        
        if (outdoorSensors.length > 0) {
            suggestions.push({
                type: 'enclosure_design',
                description: 'Design weatherproof enclosure with proper ventilation',
                benefit: 'Long-term reliability in outdoor environments',
                implementation: 'IP65+ rated enclosure with Gore-Tex vents'
            });
        }

        return suggestions;
    }

    async calculatePackageCosts(customPackage) {
        const costs = {
            sensor_costs: 0,
            additional_components: 0,
            development_costs: 0,
            integration_costs: 0,
            testing_costs: 0,
            documentation_costs: 0,
            total_cost: 0,
            cost_breakdown: []
        };

        const sensors = customPackage.selected_sensors.map(sensorRef => {
            const sensor = this.sensorCatalog.get(sensorRef.sensor_id);
            const quantity = sensorRef.quantity || 1;
            const unitCost = sensor.pricing.unit_price;
            const totalCost = unitCost * quantity;
            
            costs.sensor_costs += totalCost;
            costs.cost_breakdown.push({
                item: sensor.name,
                unit_cost: unitCost,
                quantity: quantity,
                total_cost: totalCost,
                type: 'sensor'
            });
            
            return { sensor, quantity, cost: totalCost };
        });

        costs.additional_components = this.estimateAdditionalComponents(sensors, customPackage);
        costs.development_costs = this.estimateDevelopmentCosts(customPackage);
        costs.integration_costs = this.estimateIntegrationCosts(customPackage);
        costs.testing_costs = this.estimateTestingCosts(customPackage);
        costs.documentation_costs = this.estimateDocumentationCosts(customPackage);

        costs.total_cost = costs.sensor_costs + 
                          costs.additional_components + 
                          costs.development_costs + 
                          costs.integration_costs + 
                          costs.testing_costs + 
                          costs.documentation_costs;

        customPackage.estimated_costs = costs;
        return costs;
    }

    estimateAdditionalComponents(sensors, customPackage) {
        let additionalCost = 0;

        additionalCost += 25; // Basic PCB and connectors
        
        const powerConsumption = sensors.reduce((sum, sensorData) => {
            const current = this.extractCurrentConsumption(sensorData.sensor.specifications.current_consumption);
            return sum + current.typical * sensorData.quantity;
        }, 0);

        if (powerConsumption > 100) {
            additionalCost += 45; // Larger power supply
        } else {
            additionalCost += 25; // Basic power supply
        }

        if (sensors.some(sensorData => sensorData.sensor.specifications.interface === 'I2C') && sensors.length > 4) {
            additionalCost += 15; // I2C multiplexer
        }

        if (customPackage.configuration.environmental_requirements?.outdoor) {
            additionalCost += 85; // Weatherproof enclosure
        } else {
            additionalCost += 35; // Basic enclosure
        }

        if (customPackage.configuration.connectivity_requirements?.wireless) {
            additionalCost += 65; // WiFi/cellular module
        }

        return additionalCost;
    }

    estimateDevelopmentCosts(customPackage) {
        const baseDevelopmentCost = 150;
        const complexityMultiplier = customPackage.selected_sensors.length > 5 ? 1.5 : 1.0;
        const customCodeMultiplier = customPackage.configuration.data_requirements?.custom_algorithms ? 1.8 : 1.0;
        
        return baseDevelopmentCost * complexityMultiplier * customCodeMultiplier;
    }

    estimateIntegrationCosts(customPackage) {
        const baseIntegrationCost = 75;
        const sensorCount = customPackage.selected_sensors.length;
        const interfaceComplexity = this.calculateInterfaceComplexity(customPackage);
        
        return baseIntegrationCost + (sensorCount * 15) + (interfaceComplexity * 25);
    }

    estimateTestingCosts(customPackage) {
        return 50 + (customPackage.selected_sensors.length * 10);
    }

    estimateDocumentationCosts(customPackage) {
        return 40 + (customPackage.selected_sensors.length * 5);
    }

    calculateInterfaceComplexity(customPackage) {
        const sensors = customPackage.selected_sensors.map(sensorRef => 
            this.sensorCatalog.get(sensorRef.sensor_id)
        ).filter(Boolean);

        const interfaces = [...new Set(sensors.map(s => s.specifications.interface))];
        let complexity = 0;

        if (interfaces.includes('I2C') && sensors.filter(s => s.specifications.interface === 'I2C').length > 2) {
            complexity += 2; // I2C address management
        }
        
        if (interfaces.includes('SPI')) {
            complexity += 1; // SPI chip select management
        }
        
        if (interfaces.includes('UART')) {
            complexity += 1; // Serial communication
        }
        
        if (interfaces.includes('Analog')) {
            complexity += 1; // ADC configuration
        }

        return complexity;
    }

    async generateIntegrationPlan(customPackage) {
        const integrationPlan = {
            id: this.generateIntegrationId(),
            package_id: customPackage.id,
            phases: [],
            estimated_duration: 0,
            required_skills: [],
            tools_required: [],
            documentation_deliverables: []
        };

        integrationPlan.phases.push({
            phase: 1,
            name: 'Hardware Assembly',
            description: 'Assemble sensors and connect to controller',
            duration_hours: 4 + (customPackage.selected_sensors.length * 0.5),
            tasks: [
                'Prepare work area and tools',
                'Mount sensors in enclosure',
                'Wire sensors to microcontroller',
                'Install power management',
                'Basic connectivity test'
            ],
            deliverables: ['Assembled hardware', 'Wiring diagram', 'Initial test results']
        });

        integrationPlan.phases.push({
            phase: 2,
            name: 'Software Development',
            description: 'Develop firmware for sensor integration',
            duration_hours: 8 + (customPackage.selected_sensors.length * 1.5),
            tasks: [
                'Initialize sensor libraries',
                'Implement sensor reading functions',
                'Develop data aggregation logic',
                'Implement communication protocols',
                'Add error handling and recovery'
            ],
            deliverables: ['Firmware source code', 'Sensor calibration data', 'API documentation']
        });

        integrationPlan.phases.push({
            phase: 3,
            name: 'System Testing',
            description: 'Comprehensive testing and validation',
            duration_hours: 6 + (customPackage.selected_sensors.length * 0.75),
            tasks: [
                'Individual sensor validation',
                'System integration testing',
                'Environmental stress testing',
                'Long-term stability testing',
                'Performance benchmarking'
            ],
            deliverables: ['Test reports', 'Performance metrics', 'Calibration certificates']
        });

        integrationPlan.phases.push({
            phase: 4,
            name: 'Documentation and Deployment',
            description: 'Create documentation and deploy system',
            duration_hours: 4,
            tasks: [
                'Create user manual',
                'Document installation procedures',
                'Prepare maintenance guidelines',
                'Deploy and configure system',
                'Train end users'
            ],
            deliverables: ['User manual', 'Installation guide', 'Maintenance schedule', 'Training materials']
        });

        integrationPlan.estimated_duration = integrationPlan.phases.reduce((total, phase) => 
            total + phase.duration_hours, 0
        );

        integrationPlan.required_skills = [
            'Electronics assembly',
            'Microcontroller programming',
            'I2C/SPI communication protocols',
            'Data analysis and calibration',
            'Technical documentation'
        ];

        integrationPlan.tools_required = [
            'Soldering equipment',
            'Multimeter and oscilloscope',
            'Programming environment (Arduino/PlatformIO)',
            'Calibration standards',
            'Environmental test chamber (optional)'
        ];

        customPackage.integration_plan = integrationPlan;
        this.integrationGuides.set(integrationPlan.id, integrationPlan);
        
        return integrationPlan;
    }

    async searchSensors(searchCriteria) {
        const {
            query = '',
            category = '',
            subcategory = '',
            manufacturer = '',
            interface = '',
            measurement_type = '',
            price_range = {},
            accuracy_requirements = {},
            power_constraints = {},
            sort_by = 'name',
            sort_order = 'asc',
            page = 1,
            limit = 20
        } = searchCriteria;

        let sensors = Array.from(this.sensorCatalog.values());

        if (query) {
            const searchLower = query.toLowerCase();
            sensors = sensors.filter(sensor => 
                sensor.name.toLowerCase().includes(searchLower) ||
                sensor.description.toLowerCase().includes(searchLower) ||
                sensor.specifications.measurements.some(measurement => 
                    measurement.toLowerCase().includes(searchLower)
                ) ||
                sensor.applications.some(app => 
                    app.toLowerCase().includes(searchLower)
                )
            );
        }

        if (category) sensors = sensors.filter(sensor => sensor.category === category);
        if (subcategory) sensors = sensors.filter(sensor => sensor.subcategory === subcategory);
        if (manufacturer) sensors = sensors.filter(sensor => sensor.manufacturer === manufacturer);
        if (interface) sensors = sensors.filter(sensor => sensor.specifications.interface === interface);
        
        if (measurement_type) {
            sensors = sensors.filter(sensor => 
                sensor.specifications.measurements.includes(measurement_type)
            );
        }

        if (price_range.min !== undefined || price_range.max !== undefined) {
            sensors = sensors.filter(sensor => {
                const price = sensor.pricing.unit_price;
                if (price_range.min !== undefined && price < price_range.min) return false;
                if (price_range.max !== undefined && price > price_range.max) return false;
                return true;
            });
        }

        if (power_constraints.max_current) {
            sensors = sensors.filter(sensor => {
                const current = this.extractCurrentConsumption(sensor.specifications.current_consumption);
                return current.typical <= power_constraints.max_current;
            });
        }

        sensors.sort((a, b) => {
            let aValue, bValue;
            
            switch (sort_by) {
                case 'price':
                    aValue = a.pricing.unit_price;
                    bValue = b.pricing.unit_price;
                    break;
                case 'accuracy':
                    aValue = this.calculateAccuracyScore(a);
                    bValue = this.calculateAccuracyScore(b);
                    break;
                case 'power':
                    aValue = this.extractCurrentConsumption(a.specifications.current_consumption).typical;
                    bValue = this.extractCurrentConsumption(b.specifications.current_consumption).typical;
                    break;
                case 'name':
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
        const paginatedSensors = sensors.slice(startIndex, endIndex);

        return {
            sensors: paginatedSensors,
            pagination: {
                current_page: page,
                total_pages: Math.ceil(sensors.length / limit),
                total_sensors: sensors.length,
                has_next: endIndex < sensors.length,
                has_prev: page > 1
            },
            facets: {
                categories: this.calculateFacets(sensors, 'category'),
                manufacturers: this.calculateFacets(sensors, 'manufacturer'),
                interfaces: this.calculateFacets(sensors, s => s.specifications.interface),
                price_ranges: this.calculatePriceRangeFacets(sensors)
            }
        };
    }

    async searchPackageTemplates(searchCriteria) {
        const {
            query = '',
            category = '',
            application = '',
            difficulty_level = '',
            price_range = {},
            sort_by = 'popularity',
            sort_order = 'desc',
            page = 1,
            limit = 10
        } = searchCriteria;

        let templates = Array.from(this.packageTemplates.values());

        if (query) {
            const searchLower = query.toLowerCase();
            templates = templates.filter(template => 
                template.name.toLowerCase().includes(searchLower) ||
                template.description.toLowerCase().includes(searchLower) ||
                template.target_applications.some(app => 
                    app.toLowerCase().includes(searchLower)
                )
            );
        }

        if (category) templates = templates.filter(template => template.category === category);
        if (difficulty_level) templates = templates.filter(template => template.difficulty_level === difficulty_level);
        
        if (application) {
            templates = templates.filter(template => 
                template.target_applications.some(app => 
                    app.toLowerCase().includes(application.toLowerCase())
                )
            );
        }

        if (price_range.min !== undefined || price_range.max !== undefined) {
            templates = templates.filter(template => {
                const price = template.pricing.package_price;
                if (price_range.min !== undefined && price < price_range.min) return false;
                if (price_range.max !== undefined && price > price_range.max) return false;
                return true;
            });
        }

        templates.sort((a, b) => {
            let aValue, bValue;
            
            switch (sort_by) {
                case 'price':
                    aValue = a.pricing.package_price;
                    bValue = b.pricing.package_price;
                    break;
                case 'rating':
                    aValue = a.average_rating || 0;
                    bValue = b.average_rating || 0;
                    break;
                case 'complexity':
                    aValue = ['beginner', 'intermediate', 'advanced', 'expert'].indexOf(a.difficulty_level);
                    bValue = ['beginner', 'intermediate', 'advanced', 'expert'].indexOf(b.difficulty_level);
                    break;
                case 'popularity':
                default:
                    aValue = a.popularity_score || 0;
                    bValue = b.popularity_score || 0;
            }

            if (sort_order === 'desc') {
                return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
            } else {
                return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
            }
        });

        const startIndex = (page - 1) * limit;
        const endIndex = startIndex + limit;
        const paginatedTemplates = templates.slice(startIndex, endIndex);

        return {
            templates: paginatedTemplates,
            pagination: {
                current_page: page,
                total_pages: Math.ceil(templates.length / limit),
                total_templates: templates.length,
                has_next: endIndex < templates.length,
                has_prev: page > 1
            },
            facets: {
                categories: this.calculateFacets(templates, 'category'),
                difficulty_levels: this.calculateFacets(templates, 'difficulty_level'),
                applications: this.calculateApplicationFacets(templates)
            }
        };
    }

    generateCompatibilityTags(sensor) {
        const tags = [];
        
        tags.push(`interface:${sensor.specifications.interface}`);
        tags.push(`category:${sensor.category}`);
        tags.push(`voltage:${this.extractVoltage(sensor.specifications.operating_voltage)}V`);
        
        const currentConsumption = this.extractCurrentConsumption(sensor.specifications.current_consumption);
        if (currentConsumption.typical < 1) tags.push('ultra_low_power');
        else if (currentConsumption.typical < 10) tags.push('low_power');
        else if (currentConsumption.typical < 100) tags.push('moderate_power');
        else tags.push('high_power');

        sensor.specifications.measurements.forEach(measurement => {
            tags.push(`measures:${measurement}`);
        });

        return tags;
    }

    calculateIntegrationDifficulty(sensor) {
        let difficulty = 0;
        
        if (sensor.specifications.interface === 'I2C') difficulty += 1;
        else if (sensor.specifications.interface === 'SPI') difficulty += 2;
        else if (sensor.specifications.interface === 'UART') difficulty += 1;
        else if (sensor.specifications.interface === 'Analog') difficulty += 3;

        if (sensor.specifications.current_consumption.includes('calibration') || 
            sensor.description.toLowerCase().includes('calibration')) {
            difficulty += 2;
        }

        if (sensor.pricing.unit_price > 50) difficulty += 1; // Expensive sensors often need more careful handling

        if (difficulty <= 2) return 'beginner';
        else if (difficulty <= 4) return 'intermediate';
        else if (difficulty <= 6) return 'advanced';
        else return 'expert';
    }

    extractCurrentConsumption(currentSpec) {
        if (!currentSpec) return { typical: 10, peak: 20 }; // Default values

        const typical = currentSpec.match(/(\d+(?:\.\d+)?)(?:µA|mA)/);
        const peak = currentSpec.match(/(\d+(?:\.\d+)?)(?:µA|mA).*(?:peak|max|active)/);
        
        let typicalValue = typical ? parseFloat(typical[1]) : 10;
        let peakValue = peak ? parseFloat(peak[1]) : typicalValue * 2;

        if (currentSpec.includes('µA')) {
            typicalValue /= 1000; // Convert µA to mA
            peakValue /= 1000;
        }

        return { typical: typicalValue, peak: peakValue };
    }

    extractVoltage(voltageSpec) {
        if (!voltageSpec) return 3.3;
        const match = voltageSpec.match(/(\d+(?:\.\d+)?)V/);
        return match ? parseFloat(match[1]) : 3.3;
    }

    extractTemperatureRange(tempSpec) {
        if (!tempSpec) return { min: -10, max: 50 };
        
        const match = tempSpec.match(/(-?\d+)°C.*?(\+?\d+)°C/);
        if (match) {
            return { min: parseInt(match[1]), max: parseInt(match[2]) };
        }
        return { min: -10, max: 50 };
    }

    calculateAccuracyScore(sensor) {
        let score = 5; // Base score
        
        const specs = sensor.specifications;
        Object.keys(specs).forEach(key => {
            if (key.includes('accuracy') && typeof specs[key] === 'string') {
                const accuracy = specs[key].match(/±?(\d+(?:\.\d+)?)/);
                if (accuracy) {
                    const value = parseFloat(accuracy[1]);
                    score += Math.max(0, 10 - value); // Lower accuracy value = higher score
                }
            }
        });

        return Math.min(10, score);
    }

    calculateFacets(items, fieldOrFunction) {
        const counts = {};
        items.forEach(item => {
            const value = typeof fieldOrFunction === 'function' ? fieldOrFunction(item) : item[fieldOrFunction];
            counts[value] = (counts[value] || 0) + 1;
        });
        return counts;
    }

    calculateApplicationFacets(templates) {
        const counts = {};
        templates.forEach(template => {
            template.target_applications.forEach(app => {
                counts[app] = (counts[app] || 0) + 1;
            });
        });
        return counts;
    }

    calculatePriceRangeFacets(sensors) {
        const ranges = [
            { label: '$0-$10', min: 0, max: 10 },
            { label: '$10-$25', min: 10, max: 25 },
            { label: '$25-$50', min: 25, max: 50 },
            { label: '$50-$100', min: 50, max: 100 },
            { label: '$100+', min: 100, max: 99999 }
        ];

        return ranges.map(range => ({
            ...range,
            count: sensors.filter(sensor => 
                sensor.pricing.unit_price >= range.min && 
                sensor.pricing.unit_price < range.max
            ).length
        }));
    }

    generatePackageId() {
        return `package_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateIntegrationId() {
        return `integration_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    getSystemStats() {
        return {
            total_sensors: this.sensorCatalog.size,
            package_templates: this.packageTemplates.size,
            custom_packages: this.customPackages.size,
            compatibility_rules: this.compatibilityMatrix.size,
            integration_guides: this.integrationGuides.size,
            metrics: this.configuratorMetrics
        };
    }
}

export default SensorPackageConfigurator;