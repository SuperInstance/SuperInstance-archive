const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');
const geoip = require('geoip-lite');
const winston = require('winston');

class DataSovereigntyController {
    constructor(options = {}) {
        this.config = {
            allowedJurisdictions: options.allowedJurisdictions || ['US', 'CA', 'EU'],
            dataClassifications: options.dataClassifications || {
                'public': 1,
                'internal': 2,
                'confidential': 3,
                'restricted': 4,
                'top-secret': 5
            },
            encryptionRequired: options.encryptionRequired || true,
            auditRequired: options.auditRequired || true,
            dataRetentionPeriods: options.dataRetentionPeriods || {
                'public': 365 * 7, // 7 years
                'internal': 365 * 5, // 5 years
                'confidential': 365 * 3, // 3 years
                'restricted': 365 * 2, // 2 years
                'top-secret': 365 * 1 // 1 year
            },
            exportRestrictedCountries: options.exportRestrictedCountries || [
                'CN', 'RU', 'IR', 'KP', 'SY'
            ]
        };

        this.logger = winston.createLogger({
            level: 'info',
            format: winston.format.combine(
                winston.format.timestamp(),
                winston.format.errors({ stack: true }),
                winston.format.json()
            ),
            defaultMeta: { service: 'data-sovereignty' },
            transports: [
                new winston.transports.File({
                    filename: 'logs/data-sovereignty-error.log',
                    level: 'error'
                }),
                new winston.transports.File({
                    filename: 'logs/data-sovereignty.log'
                })
            ]
        });

        this.dataRegistry = new Map();
        this.locationCache = new Map();
        this.complianceRules = new Map();

        this.initializeComplianceRules();
    }

    initializeComplianceRules() {
        // GDPR compliance rules
        this.complianceRules.set('GDPR', {
            allowedJurisdictions: ['EU', 'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE'],
            dataProcessingLimitations: ['consent', 'contract', 'legal_obligation', 'vital_interests', 'public_task', 'legitimate_interests'],
            rightToErasure: true,
            dataPortability: true,
            privacyByDesign: true,
            maxDataRetention: 365 * 6 // 6 years max
        });

        // CCPA compliance rules
        this.complianceRules.set('CCPA', {
            allowedJurisdictions: ['US-CA'],
            dataProcessingLimitations: ['business_purpose', 'commercial_purpose'],
            rightToDelete: true,
            rightToKnow: true,
            rightToOptOut: true,
            maxDataRetention: 365 * 2 // 2 years for personal info
        });

        // HIPAA compliance rules
        this.complianceRules.set('HIPAA', {
            allowedJurisdictions: ['US'],
            encryptionRequired: true,
            accessLogsRequired: true,
            businessAssociateAgreementRequired: true,
            minPasswordComplexity: 'high',
            maxDataRetention: 365 * 6 // 6 years
        });

        // SOX compliance rules
        this.complianceRules.set('SOX', {
            allowedJurisdictions: ['US'],
            auditTrailRequired: true,
            immutableRecords: true,
            segregationOfDuties: true,
            maxDataRetention: 365 * 7 // 7 years
        });
    }

    async registerDataAsset(dataAsset) {
        const assetId = this.generateAssetId(dataAsset);
        
        const registryEntry = {
            id: assetId,
            name: dataAsset.name,
            type: dataAsset.type,
            classification: dataAsset.classification || 'internal',
            location: dataAsset.location,
            jurisdiction: await this.determineJurisdiction(dataAsset.location),
            owner: dataAsset.owner,
            custodian: dataAsset.custodian,
            createdAt: new Date(),
            lastAccessed: null,
            accessCount: 0,
            retentionPeriod: this.config.dataRetentionPeriods[dataAsset.classification] || this.config.dataRetentionPeriods['internal'],
            complianceRequirements: dataAsset.complianceRequirements || [],
            encryptionStatus: dataAsset.encrypted || false,
            backupLocations: dataAsset.backupLocations || [],
            accessControls: dataAsset.accessControls || {},
            metadata: dataAsset.metadata || {}
        };

        // Validate jurisdiction compliance
        const jurisdictionValid = await this.validateJurisdiction(registryEntry);
        if (!jurisdictionValid) {
            throw new Error(`Data asset cannot be stored in jurisdiction: ${registryEntry.jurisdiction}`);
        }

        // Validate compliance requirements
        for (const requirement of registryEntry.complianceRequirements) {
            const complianceValid = await this.validateCompliance(registryEntry, requirement);
            if (!complianceValid) {
                throw new Error(`Data asset does not meet ${requirement} compliance requirements`);
            }
        }

        this.dataRegistry.set(assetId, registryEntry);
        
        this.logger.info('Data asset registered', {
            assetId,
            jurisdiction: registryEntry.jurisdiction,
            classification: registryEntry.classification,
            compliance: registryEntry.complianceRequirements
        });

        return assetId;
    }

    async validateDataTransfer(fromLocation, toLocation, dataClassification, complianceRequirements = []) {
        const fromJurisdiction = await this.determineJurisdiction(fromLocation);
        const toJurisdiction = await this.determineJurisdiction(toLocation);

        // Check if destination jurisdiction is allowed
        if (!this.config.allowedJurisdictions.includes(toJurisdiction)) {
            return {
                allowed: false,
                reason: `Transfer to ${toJurisdiction} is not permitted`,
                violatedPolicies: ['jurisdiction-restriction']
            };
        }

        // Check export restrictions
        if (this.config.exportRestrictedCountries.includes(toJurisdiction)) {
            return {
                allowed: false,
                reason: `Export to ${toJurisdiction} is restricted`,
                violatedPolicies: ['export-restriction']
            };
        }

        // Check compliance requirements
        const violatedPolicies = [];
        for (const requirement of complianceRequirements) {
            const rules = this.complianceRules.get(requirement);
            if (rules && !rules.allowedJurisdictions.includes(toJurisdiction)) {
                violatedPolicies.push(`${requirement}-jurisdiction`);
            }
        }

        if (violatedPolicies.length > 0) {
            return {
                allowed: false,
                reason: `Transfer violates compliance requirements: ${violatedPolicies.join(', ')}`,
                violatedPolicies
            };
        }

        // Check classification level restrictions
        const classificationLevel = this.config.dataClassifications[dataClassification];
        if (classificationLevel >= 4 && fromJurisdiction !== toJurisdiction) {
            return {
                allowed: false,
                reason: `${dataClassification} data cannot cross jurisdictional boundaries`,
                violatedPolicies: ['classification-boundary']
            };
        }

        this.logger.info('Data transfer validated', {
            from: fromLocation,
            to: toLocation,
            fromJurisdiction,
            toJurisdiction,
            classification: dataClassification,
            compliance: complianceRequirements,
            result: 'allowed'
        });

        return {
            allowed: true,
            fromJurisdiction,
            toJurisdiction,
            transferId: this.generateTransferId()
        };
    }

    async enforceDataResidency(assetId, requiredJurisdiction) {
        const asset = this.dataRegistry.get(assetId);
        if (!asset) {
            throw new Error(`Data asset not found: ${assetId}`);
        }

        if (asset.jurisdiction !== requiredJurisdiction) {
            this.logger.warn('Data residency violation detected', {
                assetId,
                currentJurisdiction: asset.jurisdiction,
                requiredJurisdiction,
                assetName: asset.name
            });

            // Initiate data relocation if possible
            const relocationPlan = await this.planDataRelocation(asset, requiredJurisdiction);
            
            if (relocationPlan.feasible) {
                this.logger.info('Data relocation plan created', {
                    assetId,
                    plan: relocationPlan
                });
                return relocationPlan;
            } else {
                throw new Error(`Cannot relocate data asset to ${requiredJurisdiction}: ${relocationPlan.reason}`);
            }
        }

        return { compliant: true, jurisdiction: asset.jurisdiction };
    }

    async auditDataLocations() {
        const auditReport = {
            timestamp: new Date(),
            totalAssets: this.dataRegistry.size,
            jurisdictionBreakdown: {},
            complianceViolations: [],
            classificationBreakdown: {},
            retentionViolations: []
        };

        for (const [assetId, asset] of this.dataRegistry) {
            // Jurisdiction breakdown
            if (!auditReport.jurisdictionBreakdown[asset.jurisdiction]) {
                auditReport.jurisdictionBreakdown[asset.jurisdiction] = 0;
            }
            auditReport.jurisdictionBreakdown[asset.jurisdiction]++;

            // Classification breakdown
            if (!auditReport.classificationBreakdown[asset.classification]) {
                auditReport.classificationBreakdown[asset.classification] = 0;
            }
            auditReport.classificationBreakdown[asset.classification]++;

            // Check compliance violations
            for (const requirement of asset.complianceRequirements) {
                const compliant = await this.validateCompliance(asset, requirement);
                if (!compliant) {
                    auditReport.complianceViolations.push({
                        assetId,
                        assetName: asset.name,
                        requirement,
                        violation: 'non-compliant-jurisdiction'
                    });
                }
            }

            // Check retention violations
            const daysSinceCreation = Math.floor((new Date() - asset.createdAt) / (1000 * 60 * 60 * 24));
            if (daysSinceCreation > asset.retentionPeriod) {
                auditReport.retentionViolations.push({
                    assetId,
                    assetName: asset.name,
                    daysPastRetention: daysSinceCreation - asset.retentionPeriod
                });
            }
        }

        this.logger.info('Data sovereignty audit completed', {
            totalAssets: auditReport.totalAssets,
            violationCount: auditReport.complianceViolations.length + auditReport.retentionViolations.length
        });

        return auditReport;
    }

    async determineJurisdiction(location) {
        if (this.locationCache.has(location)) {
            return this.locationCache.get(location);
        }

        let jurisdiction;

        // Try to parse as IP address
        if (this.isValidIP(location)) {
            const geo = geoip.lookup(location);
            jurisdiction = geo ? geo.country : 'UNKNOWN';
        } 
        // Try to parse as geographic location
        else if (location.includes(',')) {
            const [country] = location.split(',').map(s => s.trim());
            jurisdiction = this.normalizeCountryCode(country);
        }
        // Assume it's already a country code
        else {
            jurisdiction = this.normalizeCountryCode(location);
        }

        this.locationCache.set(location, jurisdiction);
        return jurisdiction;
    }

    async validateJurisdiction(asset) {
        return this.config.allowedJurisdictions.includes(asset.jurisdiction) &&
               !this.config.exportRestrictedCountries.includes(asset.jurisdiction);
    }

    async validateCompliance(asset, requirement) {
        const rules = this.complianceRules.get(requirement);
        if (!rules) return true;

        // Check jurisdiction compliance
        if (rules.allowedJurisdictions && !rules.allowedJurisdictions.includes(asset.jurisdiction)) {
            return false;
        }

        // Check encryption requirements
        if (rules.encryptionRequired && !asset.encryptionStatus) {
            return false;
        }

        // Check retention requirements
        if (rules.maxDataRetention && asset.retentionPeriod > rules.maxDataRetention) {
            return false;
        }

        return true;
    }

    async planDataRelocation(asset, targetJurisdiction) {
        const currentJurisdiction = asset.jurisdiction;
        
        // Check if relocation is allowed
        if (!this.config.allowedJurisdictions.includes(targetJurisdiction)) {
            return {
                feasible: false,
                reason: `Target jurisdiction ${targetJurisdiction} is not in allowed list`
            };
        }

        // Check classification restrictions
        const classificationLevel = this.config.dataClassifications[asset.classification];
        if (classificationLevel >= 4) {
            return {
                feasible: false,
                reason: `${asset.classification} data cannot be relocated across jurisdictions`
            };
        }

        return {
            feasible: true,
            currentJurisdiction,
            targetJurisdiction,
            estimatedDuration: this.calculateRelocationTime(asset),
            requiredApprovals: this.getRequiredApprovals(asset, targetJurisdiction),
            steps: [
                'Validate target infrastructure compliance',
                'Create encrypted backup in target jurisdiction',
                'Verify data integrity post-transfer',
                'Update registry with new location',
                'Securely delete data from source location',
                'Update access controls and routing'
            ]
        };
    }

    generateAssetId(dataAsset) {
        const hash = crypto.createHash('sha256');
        hash.update(`${dataAsset.name}-${dataAsset.type}-${Date.now()}-${Math.random()}`);
        return hash.digest('hex').substring(0, 16);
    }

    generateTransferId() {
        return crypto.randomBytes(16).toString('hex');
    }

    isValidIP(str) {
        return /^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/.test(str) || 
               /^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$/.test(str);
    }

    normalizeCountryCode(country) {
        const countryMap = {
            'United States': 'US',
            'Canada': 'CA',
            'United Kingdom': 'GB',
            'European Union': 'EU',
            'Germany': 'DE',
            'France': 'FR',
            'China': 'CN',
            'Russia': 'RU',
            'Iran': 'IR',
            'North Korea': 'KP',
            'Syria': 'SY'
        };

        return countryMap[country] || country.toUpperCase();
    }

    calculateRelocationTime(asset) {
        const baseTime = 24; // 24 hours base
        const classificationMultiplier = this.config.dataClassifications[asset.classification] || 1;
        const complianceMultiplier = asset.complianceRequirements.length * 0.5 + 1;
        
        return Math.ceil(baseTime * classificationMultiplier * complianceMultiplier);
    }

    getRequiredApprovals(asset, targetJurisdiction) {
        const approvals = ['data-custodian'];
        
        const classificationLevel = this.config.dataClassifications[asset.classification];
        if (classificationLevel >= 3) {
            approvals.push('security-officer');
        }
        if (classificationLevel >= 4) {
            approvals.push('chief-security-officer', 'legal-counsel');
        }

        if (asset.complianceRequirements.includes('GDPR')) {
            approvals.push('data-protection-officer');
        }
        if (asset.complianceRequirements.includes('HIPAA')) {
            approvals.push('privacy-officer');
        }

        return approvals;
    }

    async getDataInventory() {
        const inventory = [];
        
        for (const [assetId, asset] of this.dataRegistry) {
            inventory.push({
                id: assetId,
                name: asset.name,
                type: asset.type,
                classification: asset.classification,
                jurisdiction: asset.jurisdiction,
                complianceRequirements: asset.complianceRequirements,
                createdAt: asset.createdAt,
                retentionPeriod: asset.retentionPeriod,
                encrypted: asset.encryptionStatus
            });
        }

        return inventory.sort((a, b) => b.createdAt - a.createdAt);
    }

    async exportComplianceReport(format = 'json') {
        const auditReport = await this.auditDataLocations();
        const inventory = await this.getDataInventory();
        
        const report = {
            generatedAt: new Date(),
            summary: auditReport,
            detailedInventory: inventory,
            complianceStatus: {
                totalAssets: inventory.length,
                compliantAssets: inventory.length - auditReport.complianceViolations.length,
                violationRate: (auditReport.complianceViolations.length / inventory.length * 100).toFixed(2) + '%'
            }
        };

        if (format === 'json') {
            return JSON.stringify(report, null, 2);
        } else if (format === 'csv') {
            return this.convertToCSV(inventory);
        }

        return report;
    }

    convertToCSV(inventory) {
        const headers = ['ID', 'Name', 'Type', 'Classification', 'Jurisdiction', 'Compliance', 'Created', 'Retention Days', 'Encrypted'];
        const rows = inventory.map(asset => [
            asset.id,
            asset.name,
            asset.type,
            asset.classification,
            asset.jurisdiction,
            asset.complianceRequirements.join(';'),
            asset.createdAt.toISOString(),
            asset.retentionPeriod,
            asset.encrypted
        ]);

        return [headers, ...rows].map(row => row.map(field => `"${field}"`).join(',')).join('\n');
    }
}

module.exports = DataSovereigntyController;