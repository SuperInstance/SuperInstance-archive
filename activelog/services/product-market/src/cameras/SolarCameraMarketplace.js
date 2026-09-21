import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';

class SolarCameraMarketplace extends EventEmitter {
    constructor() {
        super();
        this.cameras = new Map();
        this.cameraConfigurations = new Map();
        this.deploymentProfiles = new Map();
        this.powerManagement = new Map();
        this.videoAnalytics = new Map();
        this.installations = new Map();
        this.cameraMetrics = {
            total_cameras: 0,
            active_deployments: 0,
            total_recording_hours: 0,
            ai_detections: 0
        };
        this.initializeCameraModels();
        this.initializeDeploymentProfiles();
    }

    initializeCameraModels() {
        const cameraModels = [
            {
                id: 'solar_cam_4k_pro',
                name: 'Solar Camera 4K Pro',
                manufacturer: 'ActiveLog Surveillance',
                category: 'professional',
                description: 'Professional-grade 4K solar security camera with advanced AI analytics',
                specifications: {
                    video: {
                        resolution: '4K (3840x2160) @ 30fps',
                        night_vision: 'Color night vision with spotlight',
                        zoom: '4x digital zoom',
                        field_of_view: '110° diagonal',
                        video_formats: ['H.265', 'H.264', 'MJPEG']
                    },
                    solar: {
                        panel_wattage: '30W monocrystalline',
                        battery_capacity: '20,000mAh Li-ion',
                        charging_efficiency: '23%',
                        operating_days_cloudy: 15,
                        cold_weather_operation: '-20°C to +60°C'
                    },
                    ai_features: {
                        person_detection: true,
                        vehicle_detection: true,
                        animal_detection: true,
                        facial_recognition: true,
                        package_detection: true,
                        smart_alerts: true,
                        behavioral_analysis: true
                    },
                    connectivity: {
                        wifi: 'WiFi 6 (802.11ax)',
                        cellular: '4G LTE (optional)',
                        bluetooth: 'Bluetooth 5.2',
                        ethernet: 'None (wireless only)',
                        protocols: ['RTSP', 'ONVIF', 'WebRTC']
                    },
                    storage: {
                        local: 'microSD up to 512GB',
                        cloud: 'ActiveLog Cloud Storage',
                        edge_processing: '8GB eUFS',
                        retention: 'Configurable 1-365 days'
                    },
                    physical: {
                        dimensions: '320x240x180mm',
                        weight: '3.2kg',
                        weatherproof: 'IP67',
                        vandal_resistant: 'IK10',
                        mounting: 'Universal ball mount'
                    }
                },
                pricing: {
                    base_price: 599.00,
                    installation_fee: 150.00,
                    monthly_cloud: 9.99,
                    quantity_discounts: [
                        { min: 5, discount: 0.10 },
                        { min: 10, discount: 0.15 },
                        { min: 25, discount: 0.20 }
                    ]
                },
                use_cases: [
                    'Perimeter security',
                    'Construction site monitoring',
                    'Remote property surveillance',
                    'Wildlife monitoring',
                    'Parking lot security'
                ]
            },
            {
                id: 'solar_cam_hd_basic',
                name: 'Solar Camera HD Basic',
                manufacturer: 'ActiveLog Home',
                category: 'consumer',
                description: 'Affordable HD solar camera perfect for home security',
                specifications: {
                    video: {
                        resolution: '1080p (1920x1080) @ 30fps',
                        night_vision: 'IR night vision, 20m range',
                        zoom: '2x digital zoom',
                        field_of_view: '90° diagonal',
                        video_formats: ['H.264', 'MJPEG']
                    },
                    solar: {
                        panel_wattage: '15W polycrystalline',
                        battery_capacity: '10,000mAh Li-ion',
                        charging_efficiency: '20%',
                        operating_days_cloudy: 10,
                        cold_weather_operation: '-10°C to +50°C'
                    },
                    ai_features: {
                        person_detection: true,
                        vehicle_detection: true,
                        motion_zones: true,
                        smart_alerts: true
                    },
                    connectivity: {
                        wifi: 'WiFi 5 (802.11ac)',
                        cellular: 'Not available',
                        bluetooth: 'Bluetooth 5.0',
                        ethernet: 'None',
                        protocols: ['RTSP', 'WebRTC']
                    },
                    storage: {
                        local: 'microSD up to 128GB',
                        cloud: 'ActiveLog Basic Cloud',
                        edge_processing: '2GB eMMC',
                        retention: 'Up to 30 days local'
                    },
                    physical: {
                        dimensions: '260x180x140mm',
                        weight: '2.1kg',
                        weatherproof: 'IP65',
                        vandal_resistant: 'IK08',
                        mounting: 'Fixed mount'
                    }
                },
                pricing: {
                    base_price: 249.00,
                    installation_fee: 75.00,
                    monthly_cloud: 4.99,
                    quantity_discounts: [
                        { min: 3, discount: 0.05 },
                        { min: 6, discount: 0.10 },
                        { min: 12, discount: 0.15 }
                    ]
                },
                use_cases: [
                    'Home security',
                    'Driveway monitoring',
                    'Backyard surveillance',
                    'Small business security'
                ]
            },
            {
                id: 'solar_cam_ptz_advanced',
                name: 'Solar Camera PTZ Advanced',
                manufacturer: 'ActiveLog Security Pro',
                category: 'commercial',
                description: 'Pan-Tilt-Zoom solar camera with 360° coverage and auto-tracking',
                specifications: {
                    video: {
                        resolution: '4K (3840x2160) @ 60fps',
                        night_vision: 'Infrared + Color, 100m range',
                        zoom: '20x optical + 16x digital zoom',
                        field_of_view: '360° pan, 180° tilt',
                        video_formats: ['H.265+', 'H.264+', 'MJPEG']
                    },
                    solar: {
                        panel_wattage: '50W bifacial solar',
                        battery_capacity: '40,000mAh LiFePO4',
                        charging_efficiency: '25%',
                        operating_days_cloudy: 20,
                        cold_weather_operation: '-30°C to +70°C'
                    },
                    ai_features: {
                        auto_tracking: true,
                        intrusion_detection: true,
                        crowd_analysis: true,
                        license_plate_recognition: true,
                        behavior_analysis: true,
                        patrol_patterns: true,
                        smart_search: true
                    },
                    connectivity: {
                        wifi: 'WiFi 6E',
                        cellular: '5G (optional)',
                        bluetooth: 'Bluetooth 5.3',
                        ethernet: 'PoE+ (backup power)',
                        protocols: ['RTSP', 'ONVIF', 'WebRTC', 'SIP']
                    },
                    storage: {
                        local: 'SATA SSD up to 8TB',
                        cloud: 'Enterprise Cloud Storage',
                        edge_processing: '32GB eUFS + AI chip',
                        retention: 'Up to 180 days configurable'
                    },
                    physical: {
                        dimensions: '420x350x280mm',
                        weight: '8.5kg',
                        weatherproof: 'IP68',
                        vandal_resistant: 'IK10+',
                        mounting: 'Heavy-duty gimbal mount'
                    }
                },
                pricing: {
                    base_price: 1899.00,
                    installation_fee: 350.00,
                    monthly_cloud: 29.99,
                    quantity_discounts: [
                        { min: 3, discount: 0.08 },
                        { min: 8, discount: 0.12 },
                        { min: 15, discount: 0.18 }
                    ]
                },
                use_cases: [
                    'Large facility security',
                    'Critical infrastructure monitoring',
                    'Event security',
                    'Border surveillance',
                    'Industrial site monitoring'
                ]
            },
            {
                id: 'solar_cam_wildlife_stealth',
                name: 'Solar Camera Wildlife Stealth',
                manufacturer: 'ActiveLog Nature',
                category: 'specialty',
                description: 'Camouflaged solar camera designed for wildlife monitoring and research',
                specifications: {
                    video: {
                        resolution: '4K (3840x2160) @ 30fps',
                        night_vision: 'No-glow IR, 30m range',
                        zoom: '1x fixed (wide angle)',
                        field_of_view: '120° diagonal',
                        video_formats: ['H.265', 'H.264']
                    },
                    solar: {
                        panel_wattage: '20W flexible solar film',
                        battery_capacity: '15,000mAh Li-ion',
                        charging_efficiency: '21%',
                        operating_days_cloudy: 30,
                        cold_weather_operation: '-25°C to +55°C'
                    },
                    ai_features: {
                        animal_classification: true,
                        species_identification: true,
                        behavior_tracking: true,
                        migration_patterns: true,
                        sound_detection: true,
                        time_lapse: true
                    },
                    connectivity: {
                        wifi: 'WiFi 5 (long range)',
                        cellular: '4G LTE (low power)',
                        bluetooth: 'Bluetooth 5.1',
                        ethernet: 'None',
                        protocols: ['RTSP', 'FTP', 'Email']
                    },
                    storage: {
                        local: 'microSD up to 1TB',
                        cloud: 'Research Cloud Platform',
                        edge_processing: '4GB eMMC',
                        retention: 'Motion-triggered recording'
                    },
                    physical: {
                        dimensions: '280x200x150mm',
                        weight: '1.8kg',
                        weatherproof: 'IP68',
                        camouflage: 'Tree bark pattern',
                        mounting: 'Tree strap + ground stake'
                    }
                },
                pricing: {
                    base_price: 449.00,
                    installation_fee: 0.00,
                    monthly_cloud: 6.99,
                    research_discount: 0.25,
                    quantity_discounts: [
                        { min: 10, discount: 0.15 },
                        { min: 25, discount: 0.20 }
                    ]
                },
                use_cases: [
                    'Wildlife research',
                    'Conservation monitoring',
                    'Hunting trail cameras',
                    'Nature documentaries',
                    'Park ranger surveillance'
                ]
            }
        ];

        cameraModels.forEach(model => {
            model.created_at = new Date();
            model.firmware_version = '1.0.0';
            model.availability = {
                in_stock: true,
                stock_level: Math.floor(Math.random() * 100) + 20,
                lead_time_days: Math.floor(Math.random() * 7) + 1
            };
            model.metrics = {
                views: 0,
                orders: 0,
                reviews: [],
                average_rating: 4.0 + Math.random()
            };
            
            this.cameras.set(model.id, model);
        });
    }

    initializeDeploymentProfiles() {
        const profiles = [
            {
                id: 'residential_security',
                name: 'Residential Security',
                description: 'Standard home security monitoring setup',
                recommended_cameras: ['solar_cam_hd_basic', 'solar_cam_4k_pro'],
                configuration: {
                    recording_mode: 'motion_triggered',
                    sensitivity: 'medium',
                    alert_frequency: 'immediate',
                    retention_days: 30,
                    night_mode: 'auto',
                    privacy_zones: true
                },
                installation_notes: [
                    'Mount 8-12 feet high for optimal coverage',
                    'Ensure solar panel faces south (Northern Hemisphere)',
                    'Test WiFi signal strength at installation location',
                    'Configure motion detection zones to avoid false alarms'
                ]
            },
            {
                id: 'commercial_perimeter',
                name: 'Commercial Perimeter Security',
                description: 'Comprehensive perimeter monitoring for businesses',
                recommended_cameras: ['solar_cam_4k_pro', 'solar_cam_ptz_advanced'],
                configuration: {
                    recording_mode: 'continuous_with_motion_overlay',
                    sensitivity: 'high',
                    alert_frequency: 'immediate_with_escalation',
                    retention_days: 90,
                    night_mode: 'force_on',
                    privacy_zones: false,
                    patrol_patterns: true
                },
                installation_notes: [
                    'Create overlapping coverage zones',
                    'Install at varying heights to prevent blind spots',
                    'Use PTZ cameras for active monitoring areas',
                    'Integrate with existing security systems'
                ]
            },
            {
                id: 'wildlife_monitoring',
                name: 'Wildlife Monitoring',
                description: 'Non-intrusive wildlife observation and research',
                recommended_cameras: ['solar_cam_wildlife_stealth'],
                configuration: {
                    recording_mode: 'triggered_with_buffer',
                    sensitivity: 'very_high',
                    alert_frequency: 'summary_reports',
                    retention_days: 365,
                    night_mode: 'no_glow_ir',
                    time_lapse: true,
                    sound_recording: true
                },
                installation_notes: [
                    'Camouflage installation to minimize wildlife disturbance',
                    'Position for natural animal pathways',
                    'Use scent-free installation materials',
                    'Consider seasonal sun angle changes'
                ]
            },
            {
                id: 'construction_site',
                name: 'Construction Site Security',
                description: 'Temporary security for construction and remote sites',
                recommended_cameras: ['solar_cam_4k_pro', 'solar_cam_ptz_advanced'],
                configuration: {
                    recording_mode: 'continuous',
                    sensitivity: 'high',
                    alert_frequency: 'immediate_multi_channel',
                    retention_days: 60,
                    night_mode: 'spotlight_activated',
                    theft_detection: true,
                    equipment_monitoring: true
                },
                installation_notes: [
                    'Use portable mounting solutions',
                    'Position to monitor high-value equipment',
                    'Ensure cameras are secured against theft',
                    'Plan for site layout changes'
                ]
            }
        ];

        profiles.forEach(profile => {
            this.deploymentProfiles.set(profile.id, profile);
        });
    }

    async createCameraListing(cameraData) {
        try {
            const camera = {
                id: cameraData.id || this.generateCameraId(),
                name: cameraData.name,
                manufacturer: cameraData.manufacturer,
                category: cameraData.category,
                description: cameraData.description,
                specifications: cameraData.specifications,
                pricing: cameraData.pricing,
                use_cases: cameraData.use_cases || [],
                availability: cameraData.availability || { in_stock: false },
                firmware_version: cameraData.firmware_version || '1.0.0',
                created_at: new Date(),
                updated_at: new Date(),
                metrics: {
                    views: 0,
                    orders: 0,
                    reviews: [],
                    average_rating: 0
                },
                seller_id: cameraData.seller_id,
                verification_status: 'pending'
            };

            this.cameras.set(camera.id, camera);
            await this.generateOptimalConfigurations(camera.id);
            
            this.emit('cameraListed', camera);
            return camera;
        } catch (error) {
            this.emit('cameraError', { error: error.message, cameraData });
            throw error;
        }
    }

    async generateOptimalConfigurations(cameraId) {
        const camera = this.cameras.get(cameraId);
        if (!camera) {
            throw new Error('Camera not found');
        }

        const configurations = [];

        for (const [profileId, profile] of this.deploymentProfiles) {
            if (profile.recommended_cameras.includes(cameraId)) {
                const config = {
                    id: this.generateConfigId(),
                    camera_id: cameraId,
                    profile_id: profileId,
                    profile_name: profile.name,
                    settings: this.optimizeSettingsForCamera(camera, profile),
                    power_profile: this.calculatePowerProfile(camera, profile),
                    performance_estimates: this.estimatePerformance(camera, profile),
                    created_at: new Date()
                };
                
                configurations.push(config);
                this.cameraConfigurations.set(config.id, config);
            }
        }

        return configurations;
    }

    optimizeSettingsForCamera(camera, profile) {
        const settings = { ...profile.configuration };
        
        const specs = camera.specifications;
        
        if (specs.video?.resolution === '4K (3840x2160) @ 30fps' && 
            profile.configuration.recording_mode === 'continuous') {
            settings.resolution_override = '1080p';
            settings.optimization_note = 'Reduced to 1080p for continuous recording battery efficiency';
        }

        if (specs.solar?.operating_days_cloudy < 10 && 
            profile.configuration.recording_mode === 'continuous') {
            settings.recording_mode = 'motion_triggered';
            settings.optimization_note = 'Changed to motion-triggered for better power efficiency';
        }

        if (specs.ai_features?.auto_tracking && 
            profile.configuration.patrol_patterns) {
            settings.auto_tracking_enabled = true;
            settings.patrol_priority = 'motion_first';
        }

        if (specs.physical?.weatherproof === 'IP68' && 
            profile.name.includes('Marine')) {
            settings.corrosion_protection = 'enabled';
            settings.humidity_compensation = true;
        }

        return settings;
    }

    calculatePowerProfile(camera, profile) {
        const solarWattage = this.extractWattage(camera.specifications.solar?.panel_wattage || '0W');
        const batteryCapacity = this.extractCapacity(camera.specifications.solar?.battery_capacity || '0mAh');
        const efficiency = (camera.specifications.solar?.charging_efficiency || '20%').replace('%', '') / 100;

        let dailyConsumption = 50; // Base consumption in Wh
        
        if (profile.configuration.recording_mode === 'continuous') {
            dailyConsumption *= 3;
        } else if (profile.configuration.recording_mode === 'motion_triggered') {
            dailyConsumption *= 1.2;
        }

        if (camera.specifications.video?.resolution?.includes('4K')) {
            dailyConsumption *= 1.8;
        }

        if (camera.specifications.ai_features?.auto_tracking) {
            dailyConsumption *= 1.4;
        }

        const dailyGeneration = solarWattage * 4 * efficiency; // 4 hours average sun
        const batteryDays = (batteryCapacity * 3.7 / 1000) / dailyConsumption; // Convert mAh to Wh

        return {
            daily_generation_wh: Math.round(dailyGeneration),
            daily_consumption_wh: Math.round(dailyConsumption),
            battery_runtime_days: Math.round(batteryDays * 10) / 10,
            power_balance: dailyGeneration >= dailyConsumption ? 'positive' : 'negative',
            recommended_backup_days: Math.min(Math.round(batteryDays), 30)
        };
    }

    estimatePerformance(camera, profile) {
        const baseAccuracy = 0.85;
        let motionAccuracy = baseAccuracy;
        let falseAlarmRate = 0.10;
        let detectionRange = 20; // meters

        if (camera.specifications.ai_features?.person_detection) {
            motionAccuracy += 0.10;
            falseAlarmRate -= 0.05;
        }

        if (camera.specifications.ai_features?.behavioral_analysis) {
            motionAccuracy += 0.08;
            falseAlarmRate -= 0.03;
        }

        if (camera.specifications.video?.field_of_view?.includes('110°')) {
            detectionRange += 5;
        }

        if (camera.specifications.video?.night_vision?.includes('Color')) {
            motionAccuracy += 0.05;
            const nightRange = this.extractRange(camera.specifications.video.night_vision);
            detectionRange = Math.max(detectionRange, nightRange || 20);
        }

        if (profile.configuration.sensitivity === 'high') {
            motionAccuracy += 0.03;
            falseAlarmRate += 0.02;
        } else if (profile.configuration.sensitivity === 'very_high') {
            motionAccuracy += 0.05;
            falseAlarmRate += 0.05;
        }

        return {
            motion_detection_accuracy: Math.min(0.99, Math.round(motionAccuracy * 100) / 100),
            false_alarm_rate: Math.max(0.01, Math.round(falseAlarmRate * 100) / 100),
            detection_range_meters: detectionRange,
            video_quality_score: this.calculateVideoQualityScore(camera),
            ai_processing_score: this.calculateAIScore(camera)
        };
    }

    calculateVideoQualityScore(camera) {
        let score = 5.0;
        
        if (camera.specifications.video?.resolution?.includes('4K')) score += 2.0;
        else if (camera.specifications.video?.resolution?.includes('1080p')) score += 1.0;
        
        if (camera.specifications.video?.night_vision?.includes('Color')) score += 1.5;
        else if (camera.specifications.video?.night_vision?.includes('IR')) score += 1.0;
        
        if (camera.specifications.video?.zoom?.includes('optical')) score += 1.0;
        
        const fov = this.extractFOV(camera.specifications.video?.field_of_view);
        if (fov > 100) score += 0.5;
        
        return Math.min(10.0, Math.round(score * 10) / 10);
    }

    calculateAIScore(camera) {
        let score = 0;
        const aiFeatures = camera.specifications.ai_features || {};
        
        Object.keys(aiFeatures).forEach(feature => {
            if (aiFeatures[feature] === true) {
                score += 1;
            }
        });
        
        return Math.min(10, score);
    }

    async searchCameras(searchCriteria) {
        const {
            query = '',
            category = '',
            manufacturer = '',
            use_case = '',
            price_range = {},
            features = [],
            resolution = '',
            power_rating = '',
            sort_by = 'popularity',
            sort_order = 'desc',
            page = 1,
            limit = 20
        } = searchCriteria;

        let cameras = Array.from(this.cameras.values());

        if (query) {
            const searchLower = query.toLowerCase();
            cameras = cameras.filter(camera => 
                camera.name.toLowerCase().includes(searchLower) ||
                camera.description.toLowerCase().includes(searchLower) ||
                camera.use_cases.some(useCase => useCase.toLowerCase().includes(searchLower))
            );
        }

        if (category) {
            cameras = cameras.filter(camera => camera.category === category);
        }

        if (manufacturer) {
            cameras = cameras.filter(camera => camera.manufacturer === manufacturer);
        }

        if (use_case) {
            cameras = cameras.filter(camera => 
                camera.use_cases.some(uc => uc.toLowerCase().includes(use_case.toLowerCase()))
            );
        }

        if (price_range.min !== undefined || price_range.max !== undefined) {
            cameras = cameras.filter(camera => {
                const price = camera.pricing?.base_price || 0;
                if (price_range.min !== undefined && price < price_range.min) return false;
                if (price_range.max !== undefined && price > price_range.max) return false;
                return true;
            });
        }

        if (features.length > 0) {
            cameras = cameras.filter(camera => {
                return features.every(feature => {
                    return camera.specifications.ai_features?.[feature] === true ||
                           camera.specifications.connectivity?.[feature] ||
                           camera.specifications.video?.[feature];
                });
            });
        }

        if (resolution) {
            cameras = cameras.filter(camera => 
                camera.specifications.video?.resolution?.includes(resolution)
            );
        }

        cameras.sort((a, b) => {
            let aValue, bValue;
            
            switch (sort_by) {
                case 'price':
                    aValue = a.pricing?.base_price || 0;
                    bValue = b.pricing?.base_price || 0;
                    break;
                case 'rating':
                    aValue = a.metrics?.average_rating || 0;
                    bValue = b.metrics?.average_rating || 0;
                    break;
                case 'popularity':
                    aValue = (a.metrics?.views || 0) + (a.metrics?.orders || 0);
                    bValue = (b.metrics?.views || 0) + (b.metrics?.orders || 0);
                    break;
                case 'name':
                    aValue = a.name.toLowerCase();
                    bValue = b.name.toLowerCase();
                    break;
                default:
                    aValue = a.metrics?.average_rating || 0;
                    bValue = b.metrics?.average_rating || 0;
            }

            if (sort_order === 'desc') {
                return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
            } else {
                return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
            }
        });

        const startIndex = (page - 1) * limit;
        const endIndex = startIndex + limit;
        const paginatedCameras = cameras.slice(startIndex, endIndex);

        return {
            cameras: paginatedCameras,
            pagination: {
                current_page: page,
                total_pages: Math.ceil(cameras.length / limit),
                total_cameras: cameras.length,
                has_next: endIndex < cameras.length,
                has_prev: page > 1
            },
            facets: {
                categories: this.getFacetCounts(cameras, 'category'),
                manufacturers: this.getFacetCounts(cameras, 'manufacturer'),
                price_ranges: this.getPriceRanges(cameras),
                features: this.getFeatureFacets(cameras)
            }
        };
    }

    async generateInstallationPlan(cameraIds, siteInformation) {
        const cameras = cameraIds.map(id => this.cameras.get(id)).filter(Boolean);
        
        const plan = {
            id: this.generatePlanId(),
            cameras: cameras.map(c => ({ id: c.id, name: c.name })),
            site_info: siteInformation,
            created_at: new Date(),
            installation_steps: [],
            power_analysis: {},
            coverage_analysis: {},
            timeline: {},
            costs: {}
        };

        plan.power_analysis = await this.analyzeSitePowerRequirements(cameras, siteInformation);
        plan.coverage_analysis = await this.analyzeSiteCoverage(cameras, siteInformation);
        plan.installation_steps = await this.generateInstallationSteps(cameras, siteInformation);
        plan.timeline = await this.calculateInstallationTimeline(cameras, siteInformation);
        plan.costs = await this.calculateInstallationCosts(cameras, siteInformation);

        this.installations.set(plan.id, plan);
        return plan;
    }

    async analyzeSitePowerRequirements(cameras, siteInfo) {
        const totalPowerConsumption = cameras.reduce((total, camera) => {
            const profile = this.getRecommendedProfile(camera, siteInfo);
            const powerProfile = this.calculatePowerProfile(camera, profile);
            return total + powerProfile.daily_consumption_wh;
        }, 0);

        const totalPowerGeneration = cameras.reduce((total, camera) => {
            const solarWattage = this.extractWattage(camera.specifications.solar?.panel_wattage || '0W');
            const efficiency = (camera.specifications.solar?.charging_efficiency || '20%').replace('%', '') / 100;
            return total + (solarWattage * 4 * efficiency);
        }, 0);

        const sunHours = this.estimateSunHours(siteInfo.location, siteInfo.season);
        const weatherFactor = this.getWeatherFactor(siteInfo.climate);

        return {
            total_daily_consumption: totalPowerConsumption,
            total_daily_generation: totalPowerGeneration * weatherFactor,
            sun_hours_estimate: sunHours,
            power_balance: totalPowerGeneration * weatherFactor >= totalPowerConsumption ? 'sufficient' : 'insufficient',
            backup_recommendation: totalPowerConsumption > totalPowerGeneration * weatherFactor * 0.8,
            grid_tie_recommended: totalPowerConsumption > totalPowerGeneration * weatherFactor * 1.2
        };
    }

    async analyzeSiteCoverage(cameras, siteInfo) {
        const coverageZones = [];
        let totalCoverageArea = 0;
        const blindSpots = [];

        cameras.forEach((camera, index) => {
            const detectionRange = this.estimateDetectionRange(camera, siteInfo);
            const fov = this.extractFOV(camera.specifications.video?.field_of_view) || 90;
            
            const coverage = {
                camera_id: camera.id,
                camera_name: camera.name,
                position: siteInfo.camera_positions?.[index] || { x: 0, y: 0, height: 3 },
                detection_range: detectionRange,
                field_of_view: fov,
                coverage_area: Math.PI * Math.pow(detectionRange, 2) * (fov / 360)
            };
            
            coverageZones.push(coverage);
            totalCoverageArea += coverage.coverage_area;
        });

        return {
            coverage_zones: coverageZones,
            total_coverage_area: totalCoverageArea,
            site_area: siteInfo.site_dimensions?.area || 1000,
            coverage_percentage: Math.min(100, (totalCoverageArea / (siteInfo.site_dimensions?.area || 1000)) * 100),
            redundant_coverage: this.calculateRedundantCoverage(coverageZones),
            blind_spots: this.identifyBlindSpots(coverageZones, siteInfo)
        };
    }

    async generateInstallationSteps(cameras, siteInfo) {
        const steps = [
            {
                step: 1,
                title: 'Site Preparation',
                description: 'Prepare installation site and gather tools',
                duration_hours: 2,
                requirements: ['Site survey', 'Tool preparation', 'Safety equipment check'],
                personnel: 1
            },
            {
                step: 2,
                title: 'Mounting Installation',
                description: 'Install camera mounts and brackets',
                duration_hours: cameras.length * 1.5,
                requirements: ['Drill holes', 'Secure mounting hardware', 'Level and align'],
                personnel: 2
            },
            {
                step: 3,
                title: 'Solar Panel Positioning',
                description: 'Install and position solar panels for optimal sun exposure',
                duration_hours: cameras.length * 1,
                requirements: ['Solar angle calculation', 'Panel mounting', 'Cable routing'],
                personnel: 2
            },
            {
                step: 4,
                title: 'Camera Installation',
                description: 'Mount cameras and connect power/data cables',
                duration_hours: cameras.length * 0.5,
                requirements: ['Camera mounting', 'Cable connections', 'Weatherproofing'],
                personnel: 2
            },
            {
                step: 5,
                title: 'Network Configuration',
                description: 'Configure network connectivity and test communications',
                duration_hours: 2,
                requirements: ['WiFi setup', 'Network testing', 'Port configuration'],
                personnel: 1
            },
            {
                step: 6,
                title: 'System Configuration',
                description: 'Configure camera settings and optimize for site conditions',
                duration_hours: cameras.length * 0.5,
                requirements: ['Motion zones', 'Recording settings', 'Alert configuration'],
                personnel: 1
            },
            {
                step: 7,
                title: 'Testing and Validation',
                description: 'Test all systems and validate proper operation',
                duration_hours: 2,
                requirements: ['Motion testing', 'Night vision test', 'Alert verification'],
                personnel: 2
            }
        ];

        return steps;
    }

    getRecommendedProfile(camera, siteInfo) {
        const profileMap = {
            'residential': 'residential_security',
            'commercial': 'commercial_perimeter',
            'wildlife': 'wildlife_monitoring',
            'construction': 'construction_site'
        };
        
        const profileId = profileMap[siteInfo.site_type] || 'residential_security';
        return this.deploymentProfiles.get(profileId);
    }

    estimateSunHours(location, season) {
        const baseSunHours = 4.5;
        const seasonMultipliers = { spring: 1.1, summer: 1.3, fall: 0.9, winter: 0.7 };
        const latitudeAdjustment = Math.max(0.7, 1 - Math.abs(location?.latitude || 0) / 90 * 0.3);
        
        return baseSunHours * (seasonMultipliers[season] || 1) * latitudeAdjustment;
    }

    getWeatherFactor(climate) {
        const climateFactors = {
            'sunny': 1.0,
            'mostly_sunny': 0.9,
            'partly_cloudy': 0.8,
            'mostly_cloudy': 0.6,
            'rainy': 0.5
        };
        
        return climateFactors[climate] || 0.8;
    }

    estimateDetectionRange(camera, siteInfo) {
        let baseRange = 20;
        
        if (camera.specifications.video?.resolution?.includes('4K')) baseRange *= 1.5;
        if (camera.specifications.video?.zoom?.includes('optical')) baseRange *= 1.3;
        
        const lightingFactor = siteInfo.lighting_conditions === 'well_lit' ? 1.2 : 
                             siteInfo.lighting_conditions === 'poor' ? 0.8 : 1.0;
        
        return Math.round(baseRange * lightingFactor);
    }

    calculateRedundantCoverage(coverageZones) {
        return 15; // Simplified calculation
    }

    identifyBlindSpots(coverageZones, siteInfo) {
        return []; // Simplified - would need complex geometric calculations
    }

    calculateInstallationTimeline(cameras, siteInfo) {
        const baseHours = 8 + cameras.length * 3;
        const complexity = siteInfo.installation_complexity || 'medium';
        const complexityMultipliers = { easy: 0.8, medium: 1.0, hard: 1.3 };
        
        const totalHours = baseHours * complexityMultipliers[complexity];
        
        return {
            total_hours: totalHours,
            estimated_days: Math.ceil(totalHours / 8),
            crew_size: Math.max(1, Math.ceil(cameras.length / 3)),
            weather_buffer_days: 1
        };
    }

    calculateInstallationCosts(cameras, siteInfo) {
        const baseLaborRate = 75; // per hour
        const timeline = this.calculateInstallationTimeline(cameras, siteInfo);
        const equipmentCost = cameras.reduce((sum, camera) => sum + (camera.pricing?.installation_fee || 0), 0);
        
        return {
            labor_cost: timeline.total_hours * baseLaborRate,
            equipment_cost: equipmentCost,
            material_cost: cameras.length * 50, // mounting hardware, cables, etc.
            total_cost: (timeline.total_hours * baseLaborRate) + equipmentCost + (cameras.length * 50)
        };
    }

    getFacetCounts(items, field) {
        const counts = {};
        items.forEach(item => {
            const value = item[field];
            counts[value] = (counts[value] || 0) + 1;
        });
        return counts;
    }

    getPriceRanges(cameras) {
        const prices = cameras.map(c => c.pricing?.base_price || 0);
        const min = Math.min(...prices);
        const max = Math.max(...prices);
        
        return {
            min,
            max,
            ranges: [
                { label: '$0-$100', min: 0, max: 100, count: prices.filter(p => p <= 100).length },
                { label: '$101-$300', min: 101, max: 300, count: prices.filter(p => p > 100 && p <= 300).length },
                { label: '$301-$600', min: 301, max: 600, count: prices.filter(p => p > 300 && p <= 600).length },
                { label: '$601+', min: 601, max: 99999, count: prices.filter(p => p > 600).length }
            ]
        };
    }

    getFeatureFacets(cameras) {
        const features = {};
        cameras.forEach(camera => {
            Object.keys(camera.specifications.ai_features || {}).forEach(feature => {
                if (camera.specifications.ai_features[feature] === true) {
                    features[feature] = (features[feature] || 0) + 1;
                }
            });
        });
        return features;
    }

    extractWattage(powerSpec) {
        const match = powerSpec.match(/(\d+)W/);
        return match ? parseInt(match[1]) : 0;
    }

    extractCapacity(capacitySpec) {
        const match = capacitySpec.match(/(\d+,?\d*)mAh/);
        return match ? parseInt(match[1].replace(',', '')) : 0;
    }

    extractFOV(fovSpec) {
        const match = fovSpec?.match(/(\d+)°/);
        return match ? parseInt(match[1]) : 90;
    }

    extractRange(rangeSpec) {
        const match = rangeSpec?.match(/(\d+)m/);
        return match ? parseInt(match[1]) : null;
    }

    generateCameraId() {
        return `camera_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateConfigId() {
        return `config_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generatePlanId() {
        return `plan_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    getSystemStats() {
        return {
            total_cameras: this.cameras.size,
            deployment_profiles: this.deploymentProfiles.size,
            configurations: this.cameraConfigurations.size,
            installations: this.installations.size,
            metrics: this.cameraMetrics
        };
    }
}

export default SolarCameraMarketplace;