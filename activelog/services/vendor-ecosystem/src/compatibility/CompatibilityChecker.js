import EventEmitter from 'events';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default class CompatibilityChecker extends EventEmitter {
    constructor(logger) {
        super();
        this.logger = logger;
        this.compatibilityRules = new Map();
        this.partDatabase = new Map();
        this.dimensionTolerance = 0.1;
        this.electricalTolerance = 0.05;
        this.materialCompatibility = new Map();
        this.standardsDatabase = new Map();
        this.conflictResolution = {
            'dimension_mismatch': 'suggest_adapter',
            'electrical_incompatible': 'recommend_converter',
            'material_incompatible': 'warn_user',
            'standard_mismatch': 'check_certification'
        };

        this.initializeCompatibilityRules();
        this.initializeMaterialCompatibility();
        this.initializeStandards();
    }

    async initializeCompatibilityRules() {
        try {
            const rulesPath = path.join(__dirname, '../data/compatibility-rules.json');
            const rulesData = await fs.readFile(rulesPath, 'utf8');
            const rules = JSON.parse(rulesData);
            
            for (const rule of rules) {
                this.compatibilityRules.set(rule.id, rule);
            }
            
            this.logger.info(`Loaded ${this.compatibilityRules.size} compatibility rules`);
        } catch (error) {
            this.logger.warn('Could not load compatibility rules file, using defaults');
            this.loadDefaultRules();
        }
    }

    loadDefaultRules() {
        const defaultRules = [
            {
                id: 'electrical_voltage',
                category: 'electrical',
                description: 'Check voltage compatibility',
                condition: (part1, part2) => {
                    const voltage1 = part1.specifications?.voltage;
                    const voltage2 = part2.specifications?.voltage;
                    if (!voltage1 || !voltage2) return { compatible: true, confidence: 0.5 };
                    
                    const diff = Math.abs(voltage1 - voltage2) / Math.max(voltage1, voltage2);
                    return {
                        compatible: diff <= this.electricalTolerance,
                        confidence: diff <= this.electricalTolerance ? 0.95 : 0.1,
                        reason: diff > this.electricalTolerance ? `Voltage mismatch: ${voltage1}V vs ${voltage2}V` : null
                    };
                }
            },
            {
                id: 'mechanical_dimensions',
                category: 'mechanical',
                description: 'Check dimensional compatibility',
                condition: (part1, part2) => {
                    const dims1 = part1.specifications?.dimensions;
                    const dims2 = part2.specifications?.dimensions;
                    if (!dims1 || !dims2) return { compatible: true, confidence: 0.5 };
                    
                    const conflicts = [];
                    ['length', 'width', 'height', 'diameter'].forEach(dim => {
                        if (dims1[dim] && dims2[dim]) {
                            const diff = Math.abs(dims1[dim] - dims2[dim]) / Math.max(dims1[dim], dims2[dim]);
                            if (diff > this.dimensionTolerance) {
                                conflicts.push(`${dim}: ${dims1[dim]} vs ${dims2[dim]}`);
                            }
                        }
                    });
                    
                    return {
                        compatible: conflicts.length === 0,
                        confidence: conflicts.length === 0 ? 0.9 : 0.2,
                        reason: conflicts.length > 0 ? `Dimension conflicts: ${conflicts.join(', ')}` : null
                    };
                }
            },
            {
                id: 'connector_type',
                category: 'interface',
                description: 'Check connector compatibility',
                condition: (part1, part2) => {
                    const conn1 = part1.specifications?.connector_type;
                    const conn2 = part2.specifications?.connector_type;
                    if (!conn1 || !conn2) return { compatible: true, confidence: 0.6 };
                    
                    const compatible = conn1.toLowerCase() === conn2.toLowerCase();
                    return {
                        compatible,
                        confidence: compatible ? 0.95 : 0.1,
                        reason: !compatible ? `Connector mismatch: ${conn1} vs ${conn2}` : null
                    };
                }
            }
        ];

        defaultRules.forEach(rule => {
            this.compatibilityRules.set(rule.id, rule);
        });
    }

    initializeMaterialCompatibility() {
        const materialPairs = [
            { materials: ['steel', 'aluminum'], compatible: true, reason: 'Good mechanical compatibility' },
            { materials: ['copper', 'aluminum'], compatible: false, reason: 'Galvanic corrosion risk' },
            { materials: ['plastic', 'metal'], compatible: true, reason: 'Generally compatible' },
            { materials: ['rubber', 'oil'], compatible: false, reason: 'Chemical degradation' },
            { materials: ['glass', 'metal'], compatible: true, reason: 'Good thermal compatibility' }
        ];

        materialPairs.forEach(pair => {
            const key = pair.materials.sort().join('-');
            this.materialCompatibility.set(key, pair);
        });
    }

    initializeStandards() {
        const standards = [
            { id: 'ISO_9001', category: 'quality', compatible_with: ['ISO_14001', 'ISO_45001'] },
            { id: 'UL_Listed', category: 'electrical', compatible_with: ['CE_Marked', 'FCC_Certified'] },
            { id: 'ANSI_Standard', category: 'mechanical', compatible_with: ['DIN_Standard'] },
            { id: 'FDA_Approved', category: 'medical', compatible_with: ['CE_Medical'] }
        ];

        standards.forEach(std => {
            this.standardsDatabase.set(std.id, std);
        });
    }

    async checkCompatibility(part1, part2, context = {}) {
        try {
            const compatibility = {
                compatible: true,
                confidence: 1.0,
                issues: [],
                recommendations: [],
                alternatives: [],
                timestamp: new Date(),
                context
            };

            // Run all compatibility checks
            for (const [ruleId, rule] of this.compatibilityRules) {
                const result = await this.runCompatibilityRule(rule, part1, part2);
                
                if (!result.compatible) {
                    compatibility.compatible = false;
                    compatibility.issues.push({
                        rule: ruleId,
                        category: rule.category,
                        description: rule.description,
                        reason: result.reason,
                        severity: result.severity || 'medium'
                    });

                    const recommendation = await this.generateRecommendation(ruleId, result, part1, part2);
                    if (recommendation) {
                        compatibility.recommendations.push(recommendation);
                    }
                }
                
                compatibility.confidence = Math.min(compatibility.confidence, result.confidence);
            }

            // Check material compatibility
            const materialResult = await this.checkMaterialCompatibility(part1, part2);
            if (!materialResult.compatible) {
                compatibility.compatible = false;
                compatibility.issues.push(materialResult);
            }

            // Check standards compliance
            const standardsResult = await this.checkStandardsCompliance(part1, part2);
            if (!standardsResult.compatible) {
                compatibility.issues.push(standardsResult);
            }

            // Find alternatives if incompatible
            if (!compatibility.compatible && context.findAlternatives) {
                compatibility.alternatives = await this.findCompatibleAlternatives(part1, part2);
            }

            this.emit('compatibility_check', {
                part1: part1.id,
                part2: part2.id,
                result: compatibility
            });

            this.logger.info(`Compatibility check: ${part1.name} + ${part2.name} = ${compatibility.compatible ? 'COMPATIBLE' : 'INCOMPATIBLE'}`);
            
            return compatibility;

        } catch (error) {
            this.logger.error('Compatibility check failed:', error);
            throw error;
        }
    }

    async runCompatibilityRule(rule, part1, part2) {
        try {
            if (typeof rule.condition === 'function') {
                return rule.condition(part1, part2);
            }
            
            // If rule has script-based conditions
            if (rule.script) {
                return await this.executeCompatibilityScript(rule.script, part1, part2);
            }

            return { compatible: true, confidence: 0.5, reason: 'Unable to evaluate rule' };
        } catch (error) {
            this.logger.error(`Error running compatibility rule ${rule.id}:`, error);
            return { compatible: false, confidence: 0.1, reason: 'Rule evaluation failed' };
        }
    }

    async executeCompatibilityScript(script, part1, part2) {
        // Sandbox for executing compatibility scripts
        const context = {
            part1,
            part2,
            Math,
            console: { log: this.logger.info.bind(this.logger) }
        };

        try {
            const func = new Function('context', `
                with(context) {
                    ${script}
                }
            `);
            
            return func(context) || { compatible: true, confidence: 0.5 };
        } catch (error) {
            this.logger.error('Script execution failed:', error);
            return { compatible: false, confidence: 0.1, reason: 'Script execution error' };
        }
    }

    async checkMaterialCompatibility(part1, part2) {
        const material1 = part1.specifications?.material?.toLowerCase();
        const material2 = part2.specifications?.material?.toLowerCase();
        
        if (!material1 || !material2) {
            return { compatible: true, confidence: 0.5, category: 'material' };
        }

        const key = [material1, material2].sort().join('-');
        const compatibility = this.materialCompatibility.get(key);
        
        if (compatibility) {
            return {
                compatible: compatibility.compatible,
                confidence: 0.9,
                category: 'material',
                reason: compatibility.reason
            };
        }

        // Unknown material combination - assume compatible with low confidence
        return { compatible: true, confidence: 0.3, category: 'material' };
    }

    async checkStandardsCompliance(part1, part2) {
        const standards1 = part1.certifications || [];
        const standards2 = part2.certifications || [];
        
        if (standards1.length === 0 || standards2.length === 0) {
            return { compatible: true, confidence: 0.6 };
        }

        const conflicts = [];
        
        for (const std1 of standards1) {
            const standard1 = this.standardsDatabase.get(std1);
            if (!standard1) continue;
            
            for (const std2 of standards2) {
                if (std1 === std2) continue; // Same standard is always compatible
                
                const standard2 = this.standardsDatabase.get(std2);
                if (!standard2) continue;
                
                if (standard1.category === standard2.category && 
                    !standard1.compatible_with.includes(std2)) {
                    conflicts.push(`${std1} incompatible with ${std2}`);
                }
            }
        }

        return {
            compatible: conflicts.length === 0,
            confidence: conflicts.length === 0 ? 0.85 : 0.2,
            category: 'standards',
            reason: conflicts.length > 0 ? conflicts.join(', ') : null
        };
    }

    async generateRecommendation(ruleId, result, part1, part2) {
        const resolution = this.conflictResolution[ruleId] || this.conflictResolution['default'];
        
        switch (resolution) {
            case 'suggest_adapter':
                return {
                    type: 'adapter',
                    description: 'Use an adapter or coupling',
                    products: await this.findAdapters(part1, part2),
                    confidence: 0.8
                };
                
            case 'recommend_converter':
                return {
                    type: 'converter',
                    description: 'Use a signal/power converter',
                    products: await this.findConverters(part1, part2),
                    confidence: 0.7
                };
                
            case 'warn_user':
                return {
                    type: 'warning',
                    description: 'Proceed with caution - manual verification recommended',
                    confidence: 0.5
                };
                
            default:
                return {
                    type: 'alternative',
                    description: 'Consider alternative parts',
                    confidence: 0.6
                };
        }
    }

    async findAdapters(part1, part2) {
        // Mock adapter search - in real implementation, query product database
        return [
            {
                id: 'adapter_001',
                name: `${part1.specifications?.connector_type} to ${part2.specifications?.connector_type} Adapter`,
                price: 25.99,
                vendor: 'Universal Adapters Inc',
                compatibility_confidence: 0.9
            }
        ];
    }

    async findConverters(part1, part2) {
        // Mock converter search
        const voltage1 = part1.specifications?.voltage;
        const voltage2 = part2.specifications?.voltage;
        
        return [
            {
                id: 'converter_001',
                name: `${voltage1}V to ${voltage2}V Converter`,
                price: 89.99,
                vendor: 'Power Solutions Co',
                efficiency: 0.95,
                compatibility_confidence: 0.85
            }
        ];
    }

    async findCompatibleAlternatives(part1, part2) {
        // Mock alternative parts search
        const alternatives = {
            part1_alternatives: [
                {
                    id: 'alt_part1_001',
                    name: `Compatible alternative to ${part1.name}`,
                    price: part1.price * 1.1,
                    compatibility_score: 0.95,
                    vendor: 'Alternative Parts Inc'
                }
            ],
            part2_alternatives: [
                {
                    id: 'alt_part2_001',
                    name: `Compatible alternative to ${part2.name}`,
                    price: part2.price * 0.9,
                    compatibility_score: 0.92,
                    vendor: 'Better Parts LLC'
                }
            ]
        };

        return alternatives;
    }

    async checkBulkCompatibility(partsList) {
        const results = {
            compatible: true,
            issues: [],
            recommendations: [],
            compatibility_matrix: new Map()
        };

        // Check all part combinations
        for (let i = 0; i < partsList.length; i++) {
            for (let j = i + 1; j < partsList.length; j++) {
                const part1 = partsList[i];
                const part2 = partsList[j];
                
                const compatibility = await this.checkCompatibility(part1, part2, {
                    bulk_check: true,
                    findAlternatives: false
                });

                const key = `${part1.id}-${part2.id}`;
                results.compatibility_matrix.set(key, compatibility);

                if (!compatibility.compatible) {
                    results.compatible = false;
                    results.issues.push(...compatibility.issues.map(issue => ({
                        ...issue,
                        parts: [part1.id, part2.id],
                        part_names: [part1.name, part2.name]
                    })));
                    results.recommendations.push(...compatibility.recommendations);
                }
            }
        }

        return results;
    }

    async analyzeSystemCompatibility(system) {
        const analysis = {
            overall_compatible: true,
            confidence: 1.0,
            critical_paths: [],
            bottlenecks: [],
            optimization_suggestions: []
        };

        // Identify critical compatibility paths
        const criticalPairs = system.critical_connections || [];
        for (const pair of criticalPairs) {
            const part1 = system.parts.find(p => p.id === pair.part1);
            const part2 = system.parts.find(p => p.id === pair.part2);
            
            if (part1 && part2) {
                const compatibility = await this.checkCompatibility(part1, part2, {
                    critical_path: true
                });
                
                if (!compatibility.compatible) {
                    analysis.overall_compatible = false;
                    analysis.critical_paths.push({
                        parts: [part1.id, part2.id],
                        issues: compatibility.issues,
                        severity: 'critical'
                    });
                }
                
                analysis.confidence = Math.min(analysis.confidence, compatibility.confidence);
            }
        }

        return analysis;
    }

    async getCompatibilityHistory(partId) {
        // Mock compatibility history - in real implementation, query database
        return {
            part_id: partId,
            total_checks: 150,
            compatibility_rate: 0.78,
            common_issues: [
                { issue: 'voltage_mismatch', frequency: 25 },
                { issue: 'connector_incompatible', frequency: 18 },
                { issue: 'dimension_conflict', frequency: 12 }
            ],
            frequently_paired_with: [
                { part_id: 'part_123', compatibility_score: 0.95, frequency: 45 },
                { part_id: 'part_456', compatibility_score: 0.88, frequency: 32 }
            ]
        };
    }

    async updateCompatibilityRules(newRules) {
        try {
            for (const rule of newRules) {
                this.compatibilityRules.set(rule.id, rule);
            }

            // Save to file
            const rulesArray = Array.from(this.compatibilityRules.values());
            const rulesPath = path.join(__dirname, '../data/compatibility-rules.json');
            await fs.writeFile(rulesPath, JSON.stringify(rulesArray, null, 2));

            this.logger.info(`Updated ${newRules.length} compatibility rules`);
            
            this.emit('rules_updated', {
                count: newRules.length,
                total: this.compatibilityRules.size
            });

        } catch (error) {
            this.logger.error('Failed to update compatibility rules:', error);
            throw error;
        }
    }

    // Machine learning integration for compatibility prediction
    async trainCompatibilityModel(trainingData) {
        // Mock ML training - in real implementation, use TensorFlow.js
        this.logger.info(`Training compatibility model with ${trainingData.length} samples`);
        
        const modelMetrics = {
            accuracy: 0.89,
            precision: 0.87,
            recall: 0.91,
            training_samples: trainingData.length,
            features: ['voltage', 'dimensions', 'material', 'connector_type', 'power_rating']
        };

        this.emit('model_trained', modelMetrics);
        return modelMetrics;
    }

    async predictCompatibility(part1, part2) {
        // Mock ML prediction
        const features = this.extractFeatures(part1, part2);
        const prediction = {
            compatible: Math.random() > 0.3, // Mock prediction
            confidence: 0.75 + Math.random() * 0.2,
            model_version: '1.2.3',
            features_used: Object.keys(features)
        };

        return prediction;
    }

    extractFeatures(part1, part2) {
        return {
            voltage_diff: Math.abs((part1.specifications?.voltage || 0) - (part2.specifications?.voltage || 0)),
            connector_match: part1.specifications?.connector_type === part2.specifications?.connector_type ? 1 : 0,
            material_compatibility: this.getMaterialCompatibilityScore(
                part1.specifications?.material, 
                part2.specifications?.material
            ),
            dimension_fit: this.calculateDimensionFit(
                part1.specifications?.dimensions,
                part2.specifications?.dimensions
            ),
            power_match: this.calculatePowerMatch(
                part1.specifications?.power_rating,
                part2.specifications?.power_rating
            )
        };
    }

    getMaterialCompatibilityScore(material1, material2) {
        if (!material1 || !material2) return 0.5;
        
        const key = [material1.toLowerCase(), material2.toLowerCase()].sort().join('-');
        const compatibility = this.materialCompatibility.get(key);
        
        return compatibility ? (compatibility.compatible ? 1 : 0) : 0.5;
    }

    calculateDimensionFit(dims1, dims2) {
        if (!dims1 || !dims2) return 0.5;
        
        let totalFit = 0;
        let dimensions = 0;
        
        ['length', 'width', 'height', 'diameter'].forEach(dim => {
            if (dims1[dim] && dims2[dim]) {
                const diff = Math.abs(dims1[dim] - dims2[dim]) / Math.max(dims1[dim], dims2[dim]);
                totalFit += Math.max(0, 1 - diff);
                dimensions++;
            }
        });

        return dimensions > 0 ? totalFit / dimensions : 0.5;
    }

    calculatePowerMatch(power1, power2) {
        if (!power1 || !power2) return 0.5;
        
        const diff = Math.abs(power1 - power2) / Math.max(power1, power2);
        return Math.max(0, 1 - diff);
    }
}