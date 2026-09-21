import { EventEmitter } from 'events';
import { createHash } from 'crypto';
import { v4 as uuidv4 } from 'uuid';

class HardwareDesignSystem extends EventEmitter {
    constructor() {
        super();
        this.designs = new Map();
        this.designTemplates = new Map();
        this.designCategories = new Map();
        this.collaborations = new Map();
        this.designVersions = new Map();
        this.manufacturingPartners = new Map();
        this.designMetrics = {
            total_designs: 0,
            active_collaborations: 0,
            manufactured_designs: 0,
            revenue_generated: 0
        };
        this.initializeDesignTemplates();
        this.initializeDesignCategories();
    }

    initializeDesignTemplates() {
        const templates = [
            {
                id: 'iot_sensor_board',
                name: 'IoT Sensor Board',
                description: 'General purpose sensor board with ActiveLog integration',
                components: ['microcontroller', 'wifi_module', 'sensor_headers', 'power_management'],
                specifications: {
                    dimensions: '50x30x8mm',
                    power: '3.3V-5V',
                    connectivity: ['WiFi', 'Bluetooth'],
                    interfaces: ['I2C', 'SPI', 'UART', 'GPIO']
                },
                estimated_cost: 25.00,
                complexity: 'intermediate'
            },
            {
                id: 'solar_power_module',
                name: 'Solar Power Module',
                description: 'Efficient solar charging system for outdoor devices',
                components: ['solar_panel', 'charge_controller', 'battery_management', 'power_output'],
                specifications: {
                    dimensions: '100x60x15mm',
                    output: '5V 2A max',
                    battery: 'Li-ion 18650',
                    efficiency: '85%+'
                },
                estimated_cost: 45.00,
                complexity: 'advanced'
            },
            {
                id: 'camera_module',
                name: 'Smart Camera Module',
                description: 'High-resolution camera with edge AI processing',
                components: ['image_sensor', 'ai_processor', 'storage', 'streaming_chip'],
                specifications: {
                    resolution: '4K 30fps',
                    ai_processing: 'Edge inference',
                    storage: 'microSD + cloud',
                    streaming: 'RTSP/WebRTC'
                },
                estimated_cost: 85.00,
                complexity: 'expert'
            },
            {
                id: 'environmental_sensor',
                name: 'Environmental Sensor Package',
                description: 'Multi-sensor environmental monitoring system',
                components: ['temperature_sensor', 'humidity_sensor', 'air_quality', 'light_sensor'],
                specifications: {
                    sensors: 'Temperature, Humidity, CO2, PM2.5, Light',
                    accuracy: '±0.5°C, ±3%RH',
                    sampling: '1Hz-0.1Hz configurable',
                    interface: 'I2C/SPI'
                },
                estimated_cost: 35.00,
                complexity: 'beginner'
            },
            {
                id: 'marine_sensor',
                name: 'Marine Environmental Sensor',
                description: 'Waterproof sensor package for marine applications',
                components: ['ph_sensor', 'conductivity_sensor', 'temperature_probe', 'depth_sensor'],
                specifications: {
                    waterproof: 'IP68',
                    depth_rating: '100m',
                    sensors: 'pH, Conductivity, Temperature, Depth',
                    materials: 'Marine-grade aluminum'
                },
                estimated_cost: 120.00,
                complexity: 'expert'
            }
        ];

        templates.forEach(template => {
            this.designTemplates.set(template.id, template);
        });
    }

    initializeDesignCategories() {
        const categories = [
            {
                id: 'sensors',
                name: 'Sensors & Monitoring',
                subcategories: ['environmental', 'security', 'industrial', 'marine', 'agricultural'],
                description: 'Sensor systems for data collection and monitoring'
            },
            {
                id: 'power',
                name: 'Power Systems',
                subcategories: ['solar', 'battery', 'wireless_charging', 'energy_harvesting'],
                description: 'Power generation and management solutions'
            },
            {
                id: 'communication',
                name: 'Communication Modules',
                subcategories: ['wifi', 'cellular', 'lora', 'bluetooth', 'satellite'],
                description: 'Wireless and wired communication systems'
            },
            {
                id: 'processing',
                name: 'Processing Units',
                subcategories: ['microcontrollers', 'edge_ai', 'fpga', 'dsp'],
                description: 'Computing and processing modules'
            },
            {
                id: 'interfaces',
                name: 'User Interfaces',
                subcategories: ['displays', 'buttons', 'touch', 'voice', 'gesture'],
                description: 'Human-machine interface components'
            },
            {
                id: 'mechanical',
                name: 'Mechanical Systems',
                subcategories: ['enclosures', 'mounts', 'actuators', 'mechanisms'],
                description: 'Physical and mechanical design elements'
            }
        ];

        categories.forEach(category => {
            this.designCategories.set(category.id, category);
        });
    }

    async createDesign(designRequest) {
        try {
            const design = {
                id: this.generateDesignId(),
                name: designRequest.name,
                description: designRequest.description,
                designer_id: designRequest.designer_id,
                category: designRequest.category,
                subcategory: designRequest.subcategory,
                template_id: designRequest.template_id,
                version: '1.0.0',
                status: 'draft',
                visibility: designRequest.visibility || 'private',
                license: designRequest.license || 'proprietary',
                created_at: new Date(),
                updated_at: new Date(),
                specifications: designRequest.specifications || {},
                components: designRequest.components || [],
                materials: designRequest.materials || [],
                manufacturing: {
                    methods: designRequest.manufacturing?.methods || [],
                    constraints: designRequest.manufacturing?.constraints || {},
                    estimated_cost: designRequest.manufacturing?.estimated_cost || 0,
                    minimum_quantity: designRequest.manufacturing?.minimum_quantity || 1
                },
                files: {
                    schematics: [],
                    pcb_layouts: [],
                    gerber_files: [],
                    bom: [],
                    assembly_drawings: [],
                    3d_models: [],
                    documentation: []
                },
                testing: {
                    test_plan: '',
                    test_results: [],
                    validation_status: 'pending'
                },
                collaboration: {
                    contributors: [designRequest.designer_id],
                    permissions: {},
                    comments: [],
                    reviews: []
                },
                metrics: {
                    views: 0,
                    downloads: 0,
                    forks: 0,
                    stars: 0,
                    orders: 0
                }
            };

            if (designRequest.template_id && this.designTemplates.has(designRequest.template_id)) {
                const template = this.designTemplates.get(designRequest.template_id);
                design.specifications = { ...template.specifications, ...design.specifications };
                design.components = [...template.components, ...design.components];
                design.manufacturing.estimated_cost = template.estimated_cost;
            }

            design.design_hash = this.generateDesignHash(design);
            this.designs.set(design.id, design);

            await this.createDesignVersion(design.id, design, 'Initial design creation');
            this.emit('designCreated', design);

            return design;
        } catch (error) {
            this.emit('designError', { error: error.message, designRequest });
            throw error;
        }
    }

    async updateDesign(designId, updates, changeNote = '') {
        const design = this.designs.get(designId);
        if (!design) {
            throw new Error('Design not found');
        }

        const previousVersion = JSON.parse(JSON.stringify(design));
        
        Object.keys(updates).forEach(key => {
            if (key !== 'id' && key !== 'created_at' && key !== 'design_hash') {
                design[key] = updates[key];
            }
        });

        design.updated_at = new Date();
        design.version = this.incrementVersion(design.version);
        design.design_hash = this.generateDesignHash(design);

        this.designs.set(designId, design);
        await this.createDesignVersion(designId, design, changeNote, previousVersion);

        this.emit('designUpdated', { design, changes: updates });
        return design;
    }

    async forkDesign(designId, forkData) {
        const originalDesign = this.designs.get(designId);
        if (!originalDesign) {
            throw new Error('Original design not found');
        }

        if (originalDesign.visibility === 'private' && originalDesign.designer_id !== forkData.designer_id) {
            throw new Error('Cannot fork private design');
        }

        const forkedDesign = {
            ...JSON.parse(JSON.stringify(originalDesign)),
            id: this.generateDesignId(),
            name: forkData.name || `${originalDesign.name} (Fork)`,
            description: forkData.description || originalDesign.description,
            designer_id: forkData.designer_id,
            version: '1.0.0',
            status: 'draft',
            visibility: forkData.visibility || 'private',
            created_at: new Date(),
            updated_at: new Date(),
            parent_design: {
                id: originalDesign.id,
                version: originalDesign.version,
                designer_id: originalDesign.designer_id
            },
            metrics: {
                views: 0,
                downloads: 0,
                forks: 0,
                stars: 0,
                orders: 0
            }
        };

        forkedDesign.design_hash = this.generateDesignHash(forkedDesign);
        this.designs.set(forkedDesign.id, forkedDesign);

        originalDesign.metrics.forks += 1;
        this.designs.set(originalDesign.id, originalDesign);

        await this.createDesignVersion(forkedDesign.id, forkedDesign, 'Forked from original design');
        this.emit('designForked', { originalDesign, forkedDesign });

        return forkedDesign;
    }

    async addCollaborator(designId, collaboratorData) {
        const design = this.designs.get(designId);
        if (!design) {
            throw new Error('Design not found');
        }

        if (design.designer_id !== collaboratorData.requester_id && 
            !design.collaboration.contributors.includes(collaboratorData.requester_id)) {
            throw new Error('Permission denied');
        }

        const collaboration = {
            id: this.generateCollaborationId(),
            design_id: designId,
            collaborator_id: collaboratorData.collaborator_id,
            permissions: collaboratorData.permissions || ['view', 'comment'],
            invited_by: collaboratorData.requester_id,
            invited_at: new Date(),
            status: 'pending',
            contribution_type: collaboratorData.contribution_type || 'general',
            revenue_share: collaboratorData.revenue_share || 0
        };

        this.collaborations.set(collaboration.id, collaboration);
        design.collaboration.contributors.push(collaboratorData.collaborator_id);
        design.collaboration.permissions[collaboratorData.collaborator_id] = collaboration.permissions;

        this.emit('collaboratorAdded', { design, collaboration });
        return collaboration;
    }

    async uploadDesignFile(designId, fileData) {
        const design = this.designs.get(designId);
        if (!design) {
            throw new Error('Design not found');
        }

        const file = {
            id: this.generateFileId(),
            filename: fileData.filename,
            original_name: fileData.original_name,
            file_type: fileData.file_type,
            file_category: fileData.file_category,
            file_size: fileData.file_size,
            upload_date: new Date(),
            uploaded_by: fileData.uploaded_by,
            checksum: fileData.checksum,
            version: fileData.version || '1.0',
            description: fileData.description || '',
            metadata: fileData.metadata || {}
        };

        if (!design.files[fileData.file_category]) {
            design.files[fileData.file_category] = [];
        }

        design.files[fileData.file_category].push(file);
        design.updated_at = new Date();

        this.designs.set(designId, design);
        this.emit('fileUploaded', { design, file });

        return file;
    }

    async generateManufacturingQuote(designId, quantity, manufacturingOptions = {}) {
        const design = this.designs.get(designId);
        if (!design) {
            throw new Error('Design not found');
        }

        const baseEstimate = design.manufacturing.estimated_cost || 0;
        let unitCost = baseEstimate;
        let setupCost = 0;
        let totalCost = 0;

        const quantityMultipliers = [
            { min: 1, max: 10, multiplier: 1.5, setup: 200 },
            { min: 11, max: 100, multiplier: 1.2, setup: 500 },
            { min: 101, max: 1000, multiplier: 1.0, setup: 1000 },
            { min: 1001, max: 10000, multiplier: 0.8, setup: 2000 },
            { min: 10001, max: Infinity, multiplier: 0.6, setup: 5000 }
        ];

        const quantityTier = quantityMultipliers.find(tier => 
            quantity >= tier.min && quantity <= tier.max
        );

        if (quantityTier) {
            unitCost = baseEstimate * quantityTier.multiplier;
            setupCost = quantityTier.setup;
        }

        if (manufacturingOptions.expedited) {
            unitCost *= 1.5;
            setupCost *= 1.3;
        }

        if (manufacturingOptions.testing_required) {
            unitCost += baseEstimate * 0.2;
            setupCost += 300;
        }

        if (manufacturingOptions.certification_required) {
            setupCost += 2000;
        }

        totalCost = (unitCost * quantity) + setupCost;

        const quote = {
            id: this.generateQuoteId(),
            design_id: designId,
            quantity,
            unit_cost: Math.round(unitCost * 100) / 100,
            setup_cost: setupCost,
            total_cost: Math.round(totalCost * 100) / 100,
            options: manufacturingOptions,
            estimated_lead_time: this.calculateLeadTime(quantity, manufacturingOptions),
            valid_until: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000), // 14 days
            created_at: new Date(),
            status: 'draft'
        };

        this.emit('quoteGenerated', { design, quote });
        return quote;
    }

    calculateLeadTime(quantity, options) {
        let baseDays = 14;
        
        if (quantity <= 10) baseDays = 7;
        else if (quantity <= 100) baseDays = 14;
        else if (quantity <= 1000) baseDays = 21;
        else baseDays = 35;

        if (options.expedited) baseDays = Math.ceil(baseDays * 0.6);
        if (options.testing_required) baseDays += 3;
        if (options.certification_required) baseDays += 14;

        return baseDays;
    }

    async validateDesign(designId, validationCriteria = {}) {
        const design = this.designs.get(designId);
        if (!design) {
            throw new Error('Design not found');
        }

        const validation = {
            id: this.generateValidationId(),
            design_id: designId,
            validation_date: new Date(),
            criteria: validationCriteria,
            results: {
                overall_score: 0,
                passed: false,
                issues: [],
                recommendations: []
            }
        };

        const checks = await Promise.all([
            this.validateDesignCompleteness(design),
            this.validateManufacturability(design),
            this.validateComponentAvailability(design),
            this.validateCostTargets(design, validationCriteria.target_cost),
            this.validateCompliance(design, validationCriteria.compliance_standards)
        ]);

        let totalScore = 0;
        let maxScore = checks.length * 100;
        
        checks.forEach(check => {
            totalScore += check.score;
            if (check.issues) validation.results.issues.push(...check.issues);
            if (check.recommendations) validation.results.recommendations.push(...check.recommendations);
        });

        validation.results.overall_score = Math.round((totalScore / maxScore) * 100);
        validation.results.passed = validation.results.overall_score >= 70;

        design.testing.validation_status = validation.results.passed ? 'passed' : 'failed';
        this.designs.set(designId, design);

        this.emit('designValidated', { design, validation });
        return validation;
    }

    async searchDesigns(searchCriteria) {
        const {
            query = '',
            category = '',
            subcategory = '',
            license = '',
            visibility = 'public',
            designer_id = '',
            tags = [],
            complexity = '',
            cost_range = {},
            sort_by = 'updated_at',
            sort_order = 'desc',
            page = 1,
            limit = 20
        } = searchCriteria;

        let designs = Array.from(this.designs.values());

        if (visibility !== 'all') {
            designs = designs.filter(design => {
                if (visibility === 'public') return design.visibility === 'public';
                if (visibility === 'private') return design.designer_id === designer_id;
                return true;
            });
        }

        if (query) {
            const searchLower = query.toLowerCase();
            designs = designs.filter(design => 
                design.name.toLowerCase().includes(searchLower) ||
                design.description.toLowerCase().includes(searchLower) ||
                (design.components && design.components.some(comp => 
                    comp.toLowerCase().includes(searchLower)
                ))
            );
        }

        if (category) {
            designs = designs.filter(design => design.category === category);
        }

        if (subcategory) {
            designs = designs.filter(design => design.subcategory === subcategory);
        }

        if (license) {
            designs = designs.filter(design => design.license === license);
        }

        if (complexity) {
            designs = designs.filter(design => design.complexity === complexity);
        }

        if (cost_range.min !== undefined || cost_range.max !== undefined) {
            designs = designs.filter(design => {
                const cost = design.manufacturing?.estimated_cost || 0;
                if (cost_range.min !== undefined && cost < cost_range.min) return false;
                if (cost_range.max !== undefined && cost > cost_range.max) return false;
                return true;
            });
        }

        designs.sort((a, b) => {
            let aValue, bValue;
            
            switch (sort_by) {
                case 'name':
                    aValue = a.name.toLowerCase();
                    bValue = b.name.toLowerCase();
                    break;
                case 'created_at':
                    aValue = new Date(a.created_at);
                    bValue = new Date(b.created_at);
                    break;
                case 'updated_at':
                    aValue = new Date(a.updated_at);
                    bValue = new Date(b.updated_at);
                    break;
                case 'stars':
                    aValue = a.metrics?.stars || 0;
                    bValue = b.metrics?.stars || 0;
                    break;
                case 'cost':
                    aValue = a.manufacturing?.estimated_cost || 0;
                    bValue = b.manufacturing?.estimated_cost || 0;
                    break;
                default:
                    aValue = a.updated_at;
                    bValue = b.updated_at;
            }

            if (sort_order === 'desc') {
                return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
            } else {
                return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
            }
        });

        const startIndex = (page - 1) * limit;
        const endIndex = startIndex + limit;
        const paginatedDesigns = designs.slice(startIndex, endIndex);

        return {
            designs: paginatedDesigns,
            pagination: {
                current_page: page,
                total_pages: Math.ceil(designs.length / limit),
                total_designs: designs.length,
                has_next: endIndex < designs.length,
                has_prev: page > 1
            },
            filters_applied: {
                query: !!query,
                category: !!category,
                subcategory: !!subcategory,
                license: !!license,
                complexity: !!complexity,
                cost_range: !!(cost_range.min || cost_range.max)
            }
        };
    }

    async createDesignVersion(designId, designData, changeNote, previousVersion = null) {
        const version = {
            id: this.generateVersionId(),
            design_id: designId,
            version_number: designData.version,
            created_at: new Date(),
            change_note: changeNote,
            design_snapshot: JSON.parse(JSON.stringify(designData)),
            diff: previousVersion ? this.calculateDiff(previousVersion, designData) : null
        };

        const designVersions = this.designVersions.get(designId) || [];
        designVersions.push(version);
        this.designVersions.set(designId, designVersions);

        return version;
    }

    calculateDiff(oldDesign, newDesign) {
        const diff = {
            added: {},
            modified: {},
            removed: {}
        };

        const compareObjects = (obj1, obj2, path = '') => {
            Object.keys(obj2).forEach(key => {
                const currentPath = path ? `${path}.${key}` : key;
                
                if (!(key in obj1)) {
                    diff.added[currentPath] = obj2[key];
                } else if (JSON.stringify(obj1[key]) !== JSON.stringify(obj2[key])) {
                    diff.modified[currentPath] = {
                        old: obj1[key],
                        new: obj2[key]
                    };
                }
            });

            Object.keys(obj1).forEach(key => {
                if (!(key in obj2)) {
                    const currentPath = path ? `${path}.${key}` : key;
                    diff.removed[currentPath] = obj1[key];
                }
            });
        };

        compareObjects(oldDesign, newDesign);
        return diff;
    }

    async validateDesignCompleteness(design) {
        const requiredFields = ['name', 'description', 'category', 'specifications', 'components'];
        const requiredFiles = ['schematics'];
        
        let score = 100;
        const issues = [];
        const recommendations = [];

        requiredFields.forEach(field => {
            if (!design[field] || (Array.isArray(design[field]) && design[field].length === 0)) {
                score -= 15;
                issues.push(`Missing required field: ${field}`);
            }
        });

        requiredFiles.forEach(fileType => {
            if (!design.files[fileType] || design.files[fileType].length === 0) {
                score -= 20;
                issues.push(`Missing required files: ${fileType}`);
                recommendations.push(`Upload ${fileType} files to complete the design`);
            }
        });

        if (!design.manufacturing?.estimated_cost) {
            score -= 10;
            issues.push('Missing manufacturing cost estimate');
            recommendations.push('Add manufacturing cost estimate for better quotes');
        }

        return { score: Math.max(0, score), issues, recommendations };
    }

    async validateManufacturability(design) {
        let score = 100;
        const issues = [];
        const recommendations = [];

        if (!design.manufacturing?.methods || design.manufacturing.methods.length === 0) {
            score -= 30;
            issues.push('No manufacturing methods specified');
            recommendations.push('Specify compatible manufacturing methods');
        }

        if (!design.materials || design.materials.length === 0) {
            score -= 20;
            issues.push('No materials specified');
            recommendations.push('Add bill of materials for accurate manufacturing');
        }

        if (design.components && design.components.length > 50) {
            score -= 15;
            issues.push('High component count may increase complexity');
            recommendations.push('Consider modular design to reduce complexity');
        }

        return { score: Math.max(0, score), issues, recommendations };
    }

    async validateComponentAvailability(design) {
        let score = 100;
        const issues = [];
        const recommendations = [];

        if (design.components) {
            const unavailableComponents = design.components.filter(comp => 
                comp.includes('obsolete') || comp.includes('discontinued')
            );
            
            if (unavailableComponents.length > 0) {
                score -= unavailableComponents.length * 15;
                issues.push(`Obsolete components detected: ${unavailableComponents.join(', ')}`);
                recommendations.push('Update to current generation components');
            }
        }

        return { score: Math.max(0, score), issues, recommendations };
    }

    async validateCostTargets(design, targetCost) {
        let score = 100;
        const issues = [];
        const recommendations = [];

        if (targetCost && design.manufacturing?.estimated_cost) {
            const actualCost = design.manufacturing.estimated_cost;
            const variance = Math.abs(actualCost - targetCost) / targetCost;
            
            if (variance > 0.5) {
                score -= 40;
                issues.push(`Cost significantly over target: $${actualCost} vs $${targetCost}`);
                recommendations.push('Review component selection and manufacturing methods');
            } else if (variance > 0.2) {
                score -= 20;
                issues.push(`Cost moderately over target: $${actualCost} vs $${targetCost}`);
                recommendations.push('Consider cost optimization opportunities');
            }
        }

        return { score: Math.max(0, score), issues, recommendations };
    }

    async validateCompliance(design, standards = []) {
        let score = 100;
        const issues = [];
        const recommendations = [];

        if (standards.length > 0 && (!design.compliance || design.compliance.length === 0)) {
            score -= 30;
            issues.push('No compliance standards specified');
            recommendations.push(`Ensure compliance with: ${standards.join(', ')}`);
        }

        return { score: Math.max(0, score), issues, recommendations };
    }

    generateDesignId() {
        return `design_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateCollaborationId() {
        return `collab_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateFileId() {
        return `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateQuoteId() {
        return `quote_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateValidationId() {
        return `validation_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateVersionId() {
        return `version_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateDesignHash(design) {
        const hashContent = JSON.stringify({
            name: design.name,
            specifications: design.specifications,
            components: design.components,
            materials: design.materials
        });
        return createHash('sha256').update(hashContent).digest('hex').substr(0, 16);
    }

    incrementVersion(currentVersion) {
        const parts = currentVersion.split('.');
        parts[2] = parseInt(parts[2]) + 1;
        return parts.join('.');
    }

    getSystemStats() {
        return {
            total_designs: this.designs.size,
            design_templates: this.designTemplates.size,
            design_categories: this.designCategories.size,
            active_collaborations: this.collaborations.size,
            metrics: this.designMetrics
        };
    }
}

export default HardwareDesignSystem;