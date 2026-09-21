import EventEmitter from 'events';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default class WarrantyManager extends EventEmitter {
    constructor(logger) {
        super();
        this.logger = logger;
        this.warranties = new Map();
        this.warrantyTypes = new Map();
        this.claims = new Map();
        this.coveragePolicies = new Map();
        this.vendors = new Map();
        this.notifications = new Map();
        this.analytics = new Map();
        this.automationRules = new Map();
        this.documentStorage = new Map();
        this.repairNetworks = new Map();
        this.extendedWarranties = new Map();
        this.transferHistory = new Map();

        this.initializeWarrantySystem();
        this.initializeWarrantyTypes();
        this.initializeCoveragePolicies();
        this.initializeRepairNetworks();
        this.initializeAutomationRules();
    }

    async initializeWarrantySystem() {
        try {
            const warrantyPath = path.join(__dirname, '../data/warranty-config.json');
            const warrantyData = await fs.readFile(warrantyPath, 'utf8');
            const config = JSON.parse(warrantyData);
            
            if (config.warranties) {
                for (const warranty of config.warranties) {
                    this.warranties.set(warranty.id, warranty);
                }
            }
            
            if (config.claims) {
                for (const claim of config.claims) {
                    this.claims.set(claim.id, claim);
                }
            }
            
            this.logger.info(`Loaded warranty system with ${this.warranties.size} warranties and ${this.claims.size} claims`);
        } catch (error) {
            this.logger.warn('Could not load warranty configuration, using defaults');
            this.initializeDefaultConfiguration();
        }
    }

    initializeDefaultConfiguration() {
        // Sample warranty data
        const sampleWarranty = {
            id: 'warranty_sample_001',
            product_id: 'pcb_assembly_001',
            customer_id: 'customer_001',
            vendor_id: 'techparts_direct',
            order_id: 'order_001',
            warranty_type: 'standard_product',
            coverage_start_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
            coverage_end_date: new Date(Date.now() + 335 * 24 * 60 * 60 * 1000),
            status: 'active',
            terms: {
                duration_months: 12,
                coverage_type: 'defects_only',
                transferable: true,
                international_coverage: false,
                repair_or_replace: 'vendor_choice'
            },
            created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
        };

        this.warranties.set(sampleWarranty.id, sampleWarranty);

        // Sample claim
        const sampleClaim = {
            id: 'claim_sample_001',
            warranty_id: 'warranty_sample_001',
            customer_id: 'customer_001',
            issue_description: 'Component failure after 2 months of use',
            claim_type: 'defect',
            status: 'investigating',
            priority: 'medium',
            submitted_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000),
            evidence: ['photo_001.jpg', 'test_report.pdf']
        };

        this.claims.set(sampleClaim.id, sampleClaim);
    }

    initializeWarrantyTypes() {
        const types = [
            {
                id: 'standard_product',
                name: 'Standard Product Warranty',
                description: 'Standard manufacturer warranty covering defects in materials and workmanship',
                default_duration_months: 12,
                coverage_includes: ['manufacturing_defects', 'material_defects', 'workmanship_issues'],
                coverage_excludes: ['wear_and_tear', 'misuse', 'environmental_damage', 'modification'],
                repair_options: ['repair', 'replace', 'refund'],
                cost: 0,
                transferable: true,
                international: false
            },
            {
                id: 'extended_coverage',
                name: 'Extended Coverage Warranty',
                description: 'Extended warranty with additional coverage beyond standard terms',
                default_duration_months: 24,
                coverage_includes: ['manufacturing_defects', 'material_defects', 'workmanship_issues', 'power_surge', 'component_failure'],
                coverage_excludes: ['intentional_damage', 'liquid_damage', 'theft'],
                repair_options: ['repair', 'replace'],
                cost: 0.15, // 15% of product value
                transferable: true,
                international: true
            },
            {
                id: 'premium_protection',
                name: 'Premium Protection Plan',
                description: 'Comprehensive protection including accidental damage and priority service',
                default_duration_months: 36,
                coverage_includes: ['manufacturing_defects', 'material_defects', 'accidental_damage', 'liquid_damage', 'power_issues'],
                coverage_excludes: ['intentional_damage', 'theft', 'loss'],
                repair_options: ['repair', 'replace', 'upgrade'],
                cost: 0.25, // 25% of product value
                transferable: false,
                international: true,
                premium_features: ['priority_support', 'expedited_repair', 'loaner_equipment']
            },
            {
                id: 'commercial_warranty',
                name: 'Commercial Use Warranty',
                description: 'Warranty designed for commercial and industrial applications',
                default_duration_months: 18,
                coverage_includes: ['manufacturing_defects', 'material_defects', 'performance_guarantee'],
                coverage_excludes: ['normal_wear', 'environmental_extremes'],
                repair_options: ['repair', 'replace'],
                cost: 0.10, // 10% of product value
                transferable: false,
                international: true,
                commercial_features: ['24_7_support', 'on_site_service', 'performance_sla']
            },
            {
                id: 'assembly_service',
                name: 'Assembly Service Warranty',
                description: 'Warranty covering assembly services and workmanship',
                default_duration_months: 6,
                coverage_includes: ['assembly_defects', 'component_placement_errors', 'soldering_issues'],
                coverage_excludes: ['component_defects', 'design_errors', 'customer_specifications'],
                repair_options: ['rework', 'reassemble'],
                cost: 0.05, // 5% of service value
                transferable: false,
                international: false
            },
            {
                id: 'custom_design',
                name: 'Custom Design Warranty',
                description: 'Warranty for custom designed products and solutions',
                default_duration_months: 24,
                coverage_includes: ['design_defects', 'specification_compliance', 'performance_guarantee'],
                coverage_excludes: ['scope_changes', 'external_dependencies'],
                repair_options: ['redesign', 'modify', 'refund'],
                cost: 0.20, // 20% of design value
                transferable: false,
                international: true,
                custom_features: ['design_consultation', 'revision_support']
            }
        ];

        types.forEach(type => {
            this.warrantyTypes.set(type.id, type);
        });

        this.logger.info(`Initialized ${types.length} warranty types`);
    }

    initializeCoveragePolicies() {
        const policies = [
            {
                id: 'defects_coverage',
                name: 'Manufacturing and Material Defects',
                description: 'Covers defects in materials and workmanship under normal use',
                covered_issues: [
                    'component_failure_premature',
                    'soldering_defects',
                    'material_degradation',
                    'assembly_errors',
                    'quality_control_failures'
                ],
                exclusions: [
                    'normal_wear_and_tear',
                    'user_induced_damage',
                    'environmental_damage',
                    'unauthorized_modifications'
                ],
                claim_requirements: [
                    'proof_of_purchase',
                    'detailed_description',
                    'failure_evidence',
                    'usage_conditions'
                ],
                resolution_options: ['repair', 'replace', 'partial_refund']
            },
            {
                id: 'performance_guarantee',
                name: 'Performance Guarantee Coverage',
                description: 'Guarantees product meets specified performance parameters',
                covered_issues: [
                    'performance_below_specification',
                    'functionality_issues',
                    'compatibility_problems',
                    'specification_non_compliance'
                ],
                exclusions: [
                    'specification_changes',
                    'environmental_factors',
                    'integration_issues',
                    'user_error'
                ],
                claim_requirements: [
                    'performance_test_results',
                    'specification_documentation',
                    'test_environment_details',
                    'measurement_methodology'
                ],
                resolution_options: ['redesign', 'modify', 'replace', 'full_refund']
            },
            {
                id: 'accidental_damage',
                name: 'Accidental Damage Protection',
                description: 'Covers accidental damage during normal handling and use',
                covered_issues: [
                    'drops_and_impacts',
                    'liquid_spills',
                    'power_surges',
                    'handling_accidents',
                    'transportation_damage'
                ],
                exclusions: [
                    'intentional_damage',
                    'gross_negligence',
                    'theft_or_loss',
                    'war_or_terrorism',
                    'natural_disasters'
                ],
                claim_requirements: [
                    'incident_report',
                    'damage_photos',
                    'witness_statements',
                    'police_report_if_applicable'
                ],
                resolution_options: ['repair', 'replace'],
                deductible: 50.00
            }
        ];

        policies.forEach(policy => {
            this.coveragePolicies.set(policy.id, policy);
        });
    }

    initializeRepairNetworks() {
        const networks = [
            {
                id: 'authorized_repair_network',
                name: 'Authorized Repair Network',
                description: 'Network of certified repair centers',
                locations: [
                    {
                        id: 'repair_center_west',
                        name: 'West Coast Repair Center',
                        address: '123 Tech Blvd, San Francisco, CA 94107',
                        phone: '+1-415-555-0123',
                        email: 'repairs@westcoast-tech.com',
                        specialties: ['electronics', 'pcb_repair', 'component_replacement'],
                        certifications: ['IPC_A_610', 'ISO_9001'],
                        turnaround_time: '3-5 business days',
                        coverage_area: ['CA', 'NV', 'OR', 'WA']
                    },
                    {
                        id: 'repair_center_east',
                        name: 'East Coast Service Center',
                        address: '456 Industrial Pkwy, Boston, MA 02101',
                        phone: '+1-617-555-0156',
                        email: 'service@eastcoast-repair.com',
                        specialties: ['mechanical_repair', 'precision_assembly', 'testing'],
                        certifications: ['AS9100', 'IPC_J_STD_001'],
                        turnaround_time: '2-4 business days',
                        coverage_area: ['MA', 'NY', 'NJ', 'CT', 'RI', 'VT', 'NH', 'ME']
                    },
                    {
                        id: 'repair_center_central',
                        name: 'Central Region Service Hub',
                        address: '789 Manufacturing Way, Chicago, IL 60601',
                        phone: '+1-312-555-0189',
                        email: 'support@central-service.com',
                        specialties: ['industrial_repair', 'custom_solutions', 'field_service'],
                        certifications: ['ISO_9001', 'NIST_Traceable'],
                        turnaround_time: '1-3 business days',
                        coverage_area: ['IL', 'IN', 'WI', 'MI', 'OH', 'IA', 'MN', 'MO']
                    }
                ],
                service_levels: [
                    {
                        name: 'standard',
                        description: 'Standard repair service',
                        turnaround: '3-5 days',
                        cost_multiplier: 1.0
                    },
                    {
                        name: 'expedited',
                        description: 'Expedited repair service',
                        turnaround: '1-2 days',
                        cost_multiplier: 1.5
                    },
                    {
                        name: 'emergency',
                        description: 'Emergency same-day service',
                        turnaround: 'same day',
                        cost_multiplier: 2.0
                    }
                ]
            }
        ];

        networks.forEach(network => {
            this.repairNetworks.set(network.id, network);
        });
    }

    initializeAutomationRules() {
        const rules = [
            {
                id: 'warranty_expiration_notice',
                name: 'Warranty Expiration Notice',
                description: 'Send notification before warranty expires',
                trigger: 'warranty_expiration_approaching',
                conditions: {
                    days_before_expiration: 30,
                    warranty_status: 'active'
                },
                actions: [
                    { type: 'send_notification', template: 'warranty_expiring' },
                    { type: 'offer_extension', if_available: true }
                ],
                enabled: true
            },
            {
                id: 'auto_approve_valid_claims',
                name: 'Auto-approve Valid Claims',
                description: 'Automatically approve claims that meet criteria',
                trigger: 'claim_submitted',
                conditions: {
                    warranty_active: true,
                    claim_value_under: 100,
                    customer_history_good: true,
                    evidence_provided: true
                },
                actions: [
                    { type: 'approve_claim', auto_approve: true },
                    { type: 'initiate_resolution', method: 'replace' },
                    { type: 'send_notification', template: 'claim_approved' }
                ],
                enabled: true
            },
            {
                id: 'escalate_complex_claims',
                name: 'Escalate Complex Claims',
                description: 'Escalate high-value or complex claims for manual review',
                trigger: 'claim_submitted',
                conditions: {
                    claim_value_over: 1000,
                    or: [
                        { claim_type: 'performance_issue' },
                        { claim_type: 'design_defect' },
                        { multiple_failures: true }
                    ]
                },
                actions: [
                    { type: 'escalate_to_specialist', department: 'engineering' },
                    { type: 'schedule_investigation', priority: 'high' },
                    { type: 'send_notification', template: 'claim_under_review' }
                ],
                enabled: true
            },
            {
                id: 'proactive_quality_alert',
                name: 'Proactive Quality Alert',
                description: 'Alert when multiple similar claims are received',
                trigger: 'pattern_detection',
                conditions: {
                    similar_claims_count: 3,
                    timeframe_days: 30,
                    same_product_batch: true
                },
                actions: [
                    { type: 'create_quality_alert', severity: 'medium' },
                    { type: 'notify_vendor', urgency: 'high' },
                    { type: 'investigate_batch', automated: true }
                ],
                enabled: true
            }
        ];

        rules.forEach(rule => {
            this.automationRules.set(rule.id, rule);
        });
    }

    async createWarranty(warrantyRequest) {
        try {
            const warrantyType = this.warrantyTypes.get(warrantyRequest.warranty_type);
            if (!warrantyType) {
                throw new Error(`Invalid warranty type: ${warrantyRequest.warranty_type}`);
            }

            const warranty = {
                id: this.generateWarrantyId(),
                product_id: warrantyRequest.product_id,
                customer_id: warrantyRequest.customer_id,
                vendor_id: warrantyRequest.vendor_id,
                assembler_id: warrantyRequest.assembler_id,
                order_id: warrantyRequest.order_id,
                warranty_type: warrantyRequest.warranty_type,
                warranty_type_details: warrantyType,
                product_details: {
                    name: warrantyRequest.product_name,
                    model: warrantyRequest.product_model,
                    serial_number: warrantyRequest.serial_number,
                    batch_number: warrantyRequest.batch_number,
                    purchase_price: warrantyRequest.purchase_price,
                    specifications: warrantyRequest.specifications
                },
                coverage_start_date: warrantyRequest.coverage_start_date || new Date(),
                coverage_end_date: this.calculateCoverageEndDate(
                    warrantyRequest.coverage_start_date || new Date(),
                    warrantyRequest.duration_months || warrantyType.default_duration_months
                ),
                status: 'active',
                terms: {
                    duration_months: warrantyRequest.duration_months || warrantyType.default_duration_months,
                    coverage_type: warrantyRequest.coverage_type || 'standard',
                    coverage_includes: warrantyType.coverage_includes,
                    coverage_excludes: warrantyType.coverage_excludes,
                    repair_options: warrantyType.repair_options,
                    transferable: warrantyType.transferable,
                    international_coverage: warrantyType.international,
                    deductible: warrantyRequest.deductible || 0,
                    coverage_limit: warrantyRequest.coverage_limit
                },
                premium_cost: this.calculatePremiumCost(warrantyRequest.purchase_price, warrantyType),
                registration: {
                    registered_at: new Date(),
                    registration_method: 'automatic',
                    registration_source: 'order_completion'
                },
                documents: [],
                claim_history: [],
                transfer_history: [],
                created_at: new Date(),
                updated_at: new Date(),
                metadata: warrantyRequest.metadata || {}
            };

            // Generate warranty certificate
            warranty.certificate = await this.generateWarrantyCertificate(warranty);

            // Store warranty
            this.warranties.set(warranty.id, warranty);

            // Send confirmation
            await this.sendWarrantyConfirmation(warranty);

            // Schedule expiration reminders
            await this.scheduleExpirationReminders(warranty);

            this.emit('warranty_created', {
                warranty_id: warranty.id,
                customer_id: warranty.customer_id,
                product_id: warranty.product_id,
                coverage_period: warranty.terms.duration_months
            });

            this.logger.info(`Warranty created: ${warranty.id} for product ${warranty.product_id}`);

            return warranty;

        } catch (error) {
            this.logger.error('Warranty creation failed:', error);
            throw error;
        }
    }

    calculateCoverageEndDate(startDate, durationMonths) {
        const endDate = new Date(startDate);
        endDate.setMonth(endDate.getMonth() + durationMonths);
        return endDate;
    }

    calculatePremiumCost(purchasePrice, warrantyType) {
        if (warrantyType.cost === 0) return 0;
        return purchasePrice * warrantyType.cost;
    }

    async generateWarrantyCertificate(warranty) {
        return {
            certificate_id: `cert_${warranty.id}`,
            issued_date: new Date(),
            warranty_id: warranty.id,
            product_info: warranty.product_details,
            coverage_period: {
                start: warranty.coverage_start_date,
                end: warranty.coverage_end_date
            },
            terms: warranty.terms,
            issuer: {
                name: warranty.vendor_id,
                contact: 'warranty@vendor.com'
            },
            verification_code: this.generateVerificationCode(),
            digital_signature: this.generateDigitalSignature(warranty),
            qr_code_url: `https://warranty.vendor-ecosystem.com/verify/${warranty.id}`,
            certificate_url: `https://warranty.vendor-ecosystem.com/certificate/${warranty.id}.pdf`
        };
    }

    async sendWarrantyConfirmation(warranty) {
        const notification = {
            id: this.generateNotificationId(),
            warranty_id: warranty.id,
            customer_id: warranty.customer_id,
            type: 'warranty_confirmation',
            template: 'warranty_registered',
            data: {
                warranty_id: warranty.id,
                product_name: warranty.product_details.name,
                coverage_end_date: warranty.coverage_end_date,
                certificate_url: warranty.certificate.certificate_url
            },
            status: 'sent',
            sent_at: new Date()
        };

        this.notifications.set(notification.id, notification);
        
        this.emit('notification_sent', notification);
    }

    async scheduleExpirationReminders(warranty) {
        const reminders = [
            { days_before: 30, template: 'warranty_expiring_30_days' },
            { days_before: 7, template: 'warranty_expiring_7_days' },
            { days_before: 1, template: 'warranty_expiring_tomorrow' }
        ];

        for (const reminder of reminders) {
            const reminderDate = new Date(warranty.coverage_end_date);
            reminderDate.setDate(reminderDate.getDate() - reminder.days_before);

            if (reminderDate > new Date()) {
                setTimeout(async () => {
                    await this.sendExpirationReminder(warranty.id, reminder.template);
                }, reminderDate.getTime() - Date.now());
            }
        }
    }

    async sendExpirationReminder(warrantyId, template) {
        const warranty = this.warranties.get(warrantyId);
        if (!warranty || warranty.status !== 'active') return;

        const notification = {
            id: this.generateNotificationId(),
            warranty_id: warrantyId,
            customer_id: warranty.customer_id,
            type: 'warranty_expiration_reminder',
            template: template,
            data: {
                warranty_id: warrantyId,
                product_name: warranty.product_details.name,
                coverage_end_date: warranty.coverage_end_date,
                days_remaining: Math.ceil((new Date(warranty.coverage_end_date) - new Date()) / (1000 * 60 * 60 * 24))
            },
            status: 'sent',
            sent_at: new Date()
        };

        this.notifications.set(notification.id, notification);
        
        this.emit('notification_sent', notification);
    }

    async submitClaim(claimRequest) {
        try {
            // Validate warranty
            const warranty = this.warranties.get(claimRequest.warranty_id);
            if (!warranty) {
                throw new Error(`Warranty ${claimRequest.warranty_id} not found`);
            }

            if (warranty.status !== 'active') {
                throw new Error(`Warranty is not active: ${warranty.status}`);
            }

            if (new Date() > new Date(warranty.coverage_end_date)) {
                throw new Error('Warranty has expired');
            }

            const claim = {
                id: this.generateClaimId(),
                warranty_id: claimRequest.warranty_id,
                customer_id: warranty.customer_id,
                vendor_id: warranty.vendor_id,
                claim_number: this.generateClaimNumber(),
                issue_description: claimRequest.issue_description,
                claim_type: claimRequest.claim_type, // 'defect', 'performance', 'damage', 'other'
                severity: claimRequest.severity || 'medium', // 'low', 'medium', 'high', 'critical'
                priority: this.calculateClaimPriority(claimRequest, warranty),
                status: 'submitted',
                estimated_value: claimRequest.estimated_value,
                failure_date: claimRequest.failure_date || new Date(),
                usage_conditions: claimRequest.usage_conditions,
                evidence: {
                    photos: claimRequest.photos || [],
                    videos: claimRequest.videos || [],
                    documents: claimRequest.documents || [],
                    test_results: claimRequest.test_results || []
                },
                customer_contact: {
                    preferred_method: claimRequest.preferred_contact || 'email',
                    phone: claimRequest.phone,
                    email: claimRequest.email,
                    best_time_to_call: claimRequest.best_time_to_call
                },
                resolution_preference: claimRequest.resolution_preference || 'repair', // 'repair', 'replace', 'refund'
                submitted_at: new Date(),
                updated_at: new Date(),
                timeline: [
                    {
                        status: 'submitted',
                        timestamp: new Date(),
                        action: 'Claim submitted by customer',
                        actor: 'customer',
                        automated: false
                    }
                ],
                internal_notes: [],
                external_communications: [],
                metadata: claimRequest.metadata || {}
            };

            // Initial validation
            const validationResult = await this.validateClaim(claim, warranty);
            if (!validationResult.valid) {
                claim.status = 'rejected';
                claim.rejection_reason = validationResult.reason;
                claim.timeline.push({
                    status: 'rejected',
                    timestamp: new Date(),
                    action: `Claim rejected: ${validationResult.reason}`,
                    actor: 'system',
                    automated: true
                });
            } else {
                claim.status = 'under_review';
                claim.timeline.push({
                    status: 'under_review',
                    timestamp: new Date(),
                    action: 'Claim validated and under review',
                    actor: 'system',
                    automated: true
                });
            }

            // Store claim
            this.claims.set(claim.id, claim);

            // Update warranty claim history
            warranty.claim_history.push({
                claim_id: claim.id,
                claim_date: claim.submitted_at,
                claim_type: claim.claim_type,
                status: claim.status
            });

            // Execute automation rules
            await this.executeClaimAutomation('claim_submitted', claim, warranty);

            // Send confirmation
            await this.sendClaimConfirmation(claim);

            this.emit('claim_submitted', {
                claim_id: claim.id,
                warranty_id: claim.warranty_id,
                customer_id: claim.customer_id,
                claim_type: claim.claim_type
            });

            this.logger.info(`Warranty claim submitted: ${claim.id} for warranty ${claim.warranty_id}`);

            return claim;

        } catch (error) {
            this.logger.error('Claim submission failed:', error);
            throw error;
        }
    }

    calculateClaimPriority(claimRequest, warranty) {
        let priority = 'medium';

        // High priority conditions
        if (claimRequest.severity === 'critical' ||
            claimRequest.claim_type === 'safety_issue' ||
            (warranty.warranty_type_details && warranty.warranty_type_details.commercial_features)) {
            priority = 'high';
        }

        // Low priority conditions
        if (claimRequest.severity === 'low' ||
            claimRequest.claim_type === 'cosmetic') {
            priority = 'low';
        }

        // Critical priority conditions
        if (claimRequest.claim_type === 'safety_hazard' ||
            claimRequest.business_impact === 'critical') {
            priority = 'critical';
        }

        return priority;
    }

    async validateClaim(claim, warranty) {
        const validation = { valid: true, reason: null, checks: [] };

        // Check warranty coverage
        const coverageCheck = await this.checkCoverageEligibility(claim, warranty);
        validation.checks.push(coverageCheck);
        if (!coverageCheck.passed) {
            validation.valid = false;
            validation.reason = coverageCheck.reason;
            return validation;
        }

        // Check evidence requirements
        const evidenceCheck = this.checkEvidenceRequirements(claim, warranty);
        validation.checks.push(evidenceCheck);
        if (!evidenceCheck.passed) {
            validation.valid = false;
            validation.reason = evidenceCheck.reason;
            return validation;
        }

        // Check for duplicate claims
        const duplicateCheck = this.checkDuplicateClaim(claim, warranty);
        validation.checks.push(duplicateCheck);
        if (!duplicateCheck.passed) {
            validation.valid = false;
            validation.reason = duplicateCheck.reason;
            return validation;
        }

        // Check fraud indicators
        const fraudCheck = await this.checkFraudIndicators(claim, warranty);
        validation.checks.push(fraudCheck);
        if (!fraudCheck.passed) {
            validation.valid = false;
            validation.reason = fraudCheck.reason;
        }

        return validation;
    }

    async checkCoverageEligibility(claim, warranty) {
        const check = { name: 'coverage_eligibility', passed: true, reason: null };

        const warrantyType = warranty.warranty_type_details;
        const claimType = claim.claim_type;

        // Check if claim type is covered
        const coveragePolicy = this.getCoveragePolicy(claimType, warrantyType);
        if (!coveragePolicy) {
            check.passed = false;
            check.reason = `Claim type '${claimType}' is not covered under this warranty`;
            return check;
        }

        // Check exclusions
        if (coveragePolicy.exclusions && this.matchesExclusion(claim, coveragePolicy.exclusions)) {
            check.passed = false;
            check.reason = 'Claim matches warranty exclusion criteria';
            return check;
        }

        // Check coverage limits
        if (warranty.terms.coverage_limit && claim.estimated_value > warranty.terms.coverage_limit) {
            check.passed = false;
            check.reason = `Claim value exceeds coverage limit of $${warranty.terms.coverage_limit}`;
            return check;
        }

        return check;
    }

    getCoveragePolicy(claimType, warrantyType) {
        // Map claim types to coverage policies
        const claimTypeMappings = {
            'defect': 'defects_coverage',
            'performance': 'performance_guarantee',
            'damage': 'accidental_damage'
        };

        const policyId = claimTypeMappings[claimType];
        return policyId ? this.coveragePolicies.get(policyId) : null;
    }

    matchesExclusion(claim, exclusions) {
        // Simple exclusion matching - in production would be more sophisticated
        const description = claim.issue_description.toLowerCase();
        const conditions = claim.usage_conditions ? claim.usage_conditions.toLowerCase() : '';

        return exclusions.some(exclusion => {
            const exclusionKey = exclusion.toLowerCase().replace(/_/g, ' ');
            return description.includes(exclusionKey) || conditions.includes(exclusionKey);
        });
    }

    checkEvidenceRequirements(claim, warranty) {
        const check = { name: 'evidence_requirements', passed: true, reason: null };

        const coveragePolicy = this.getCoveragePolicy(claim.claim_type, warranty.warranty_type_details);
        if (!coveragePolicy || !coveragePolicy.claim_requirements) {
            return check; // No specific requirements
        }

        const requirements = coveragePolicy.claim_requirements;
        const missing = [];

        for (const requirement of requirements) {
            switch (requirement) {
                case 'proof_of_purchase':
                    if (!warranty.order_id) missing.push('Proof of purchase');
                    break;
                case 'detailed_description':
                    if (!claim.issue_description || claim.issue_description.length < 20) {
                        missing.push('Detailed description of the issue');
                    }
                    break;
                case 'failure_evidence':
                    if (!claim.evidence.photos.length && !claim.evidence.documents.length) {
                        missing.push('Evidence of failure (photos or documents)');
                    }
                    break;
                case 'usage_conditions':
                    if (!claim.usage_conditions) missing.push('Usage conditions information');
                    break;
                case 'performance_test_results':
                    if (!claim.evidence.test_results.length) missing.push('Performance test results');
                    break;
            }
        }

        if (missing.length > 0) {
            check.passed = false;
            check.reason = `Missing required evidence: ${missing.join(', ')}`;
        }

        return check;
    }

    checkDuplicateClaim(claim, warranty) {
        const check = { name: 'duplicate_check', passed: true, reason: null };

        // Check for duplicate claims with similar descriptions
        const existingClaims = warranty.claim_history;
        const recentClaims = existingClaims.filter(c => {
            const claimAge = (Date.now() - new Date(c.claim_date).getTime()) / (1000 * 60 * 60 * 24);
            return claimAge < 30; // Within last 30 days
        });

        for (const existingClaim of recentClaims) {
            if (existingClaim.claim_type === claim.claim_type) {
                const existingClaimData = this.claims.get(existingClaim.claim_id);
                if (existingClaimData && 
                    this.calculateStringSimilarity(claim.issue_description, existingClaimData.issue_description) > 0.8) {
                    check.passed = false;
                    check.reason = `Similar claim already submitted: ${existingClaim.claim_id}`;
                    break;
                }
            }
        }

        return check;
    }

    async checkFraudIndicators(claim, warranty) {
        const check = { name: 'fraud_check', passed: true, reason: null, score: 0 };

        // Check multiple recent claims
        if (warranty.claim_history.length > 3) {
            const recentClaims = warranty.claim_history.filter(c => {
                const claimAge = (Date.now() - new Date(c.claim_date).getTime()) / (1000 * 60 * 60 * 24);
                return claimAge < 90;
            });
            if (recentClaims.length > 2) {
                check.score += 0.3;
            }
        }

        // Check high-value claim soon after warranty start
        if (claim.estimated_value && warranty.product_details.purchase_price) {
            const valueRatio = claim.estimated_value / warranty.product_details.purchase_price;
            const warrantyAge = (Date.now() - new Date(warranty.coverage_start_date).getTime()) / (1000 * 60 * 60 * 24);
            
            if (valueRatio > 0.8 && warrantyAge < 30) {
                check.score += 0.4;
            }
        }

        // Check suspicious failure timing
        if (claim.failure_date) {
            const timeSincePurchase = (new Date(claim.failure_date) - new Date(warranty.coverage_start_date)) / (1000 * 60 * 60 * 24);
            if (timeSincePurchase < 1) { // Failure within 1 day
                check.score += 0.2;
            }
        }

        // Overall fraud assessment
        if (check.score > 0.7) {
            check.passed = false;
            check.reason = 'High fraud risk indicators detected - manual review required';
        }

        return check;
    }

    calculateStringSimilarity(str1, str2) {
        const longer = str1.length > str2.length ? str1 : str2;
        const shorter = str1.length > str2.length ? str2 : str1;
        const editDistance = this.calculateEditDistance(longer, shorter);
        
        if (longer.length === 0) return 1.0;
        return (longer.length - editDistance) / longer.length;
    }

    calculateEditDistance(str1, str2) {
        const matrix = [];
        for (let i = 0; i <= str2.length; i++) {
            matrix[i] = [i];
        }
        for (let j = 0; j <= str1.length; j++) {
            matrix[0][j] = j;
        }
        for (let i = 1; i <= str2.length; i++) {
            for (let j = 1; j <= str1.length; j++) {
                if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
                    matrix[i][j] = matrix[i - 1][j - 1];
                } else {
                    matrix[i][j] = Math.min(
                        matrix[i - 1][j - 1] + 1,
                        matrix[i][j - 1] + 1,
                        matrix[i - 1][j] + 1
                    );
                }
            }
        }
        return matrix[str2.length][str1.length];
    }

    async executeClaimAutomation(trigger, claim, warranty) {
        for (const [ruleId, rule] of this.automationRules) {
            if (!rule.enabled || rule.trigger !== trigger) continue;

            const conditionsMet = await this.evaluateClaimConditions(rule.conditions, claim, warranty);
            if (!conditionsMet) continue;

            for (const action of rule.actions) {
                try {
                    await this.executeClaimAction(action, claim, warranty);
                } catch (error) {
                    this.logger.error(`Claim automation action failed for rule ${ruleId}:`, error);
                }
            }

            this.logger.info(`Executed claim automation rule: ${ruleId} for claim ${claim.id}`);
        }
    }

    async evaluateClaimConditions(conditions, claim, warranty) {
        for (const [key, value] of Object.entries(conditions)) {
            switch (key) {
                case 'warranty_active':
                    if (warranty.status !== 'active' && value) return false;
                    break;
                case 'claim_value_under':
                    if (claim.estimated_value > value) return false;
                    break;
                case 'claim_value_over':
                    if (claim.estimated_value <= value) return false;
                    break;
                case 'customer_history_good':
                    const historyGood = warranty.claim_history.length < 3;
                    if (!historyGood && value) return false;
                    break;
                case 'evidence_provided':
                    const hasEvidence = claim.evidence.photos.length > 0 || 
                                       claim.evidence.documents.length > 0;
                    if (!hasEvidence && value) return false;
                    break;
                case 'claim_type':
                    if (claim.claim_type !== value) return false;
                    break;
                case 'multiple_failures':
                    const multipleFailures = warranty.claim_history.length > 2;
                    if (!multipleFailures && value) return false;
                    break;
            }
        }
        return true;
    }

    async executeClaimAction(action, claim, warranty) {
        switch (action.type) {
            case 'approve_claim':
                await this.updateClaimStatus(claim.id, 'approved', {
                    automated: action.auto_approve,
                    reason: 'Automatically approved based on validation criteria'
                });
                break;

            case 'initiate_resolution':
                await this.initiateClaimResolution(claim.id, action.method);
                break;

            case 'send_notification':
                await this.sendClaimNotification(claim, action.template);
                break;

            case 'escalate_to_specialist':
                await this.escalateClaimToSpecialist(claim.id, action.department);
                break;

            case 'schedule_investigation':
                await this.scheduleClaimInvestigation(claim.id, action.priority);
                break;

            case 'create_quality_alert':
                await this.createQualityAlert(claim, action.severity);
                break;

            case 'notify_vendor':
                await this.notifyVendorOfClaim(claim, warranty, action.urgency);
                break;

            case 'investigate_batch':
                await this.investigateProductBatch(warranty.product_details.batch_number);
                break;
        }
    }

    async updateClaimStatus(claimId, newStatus, updateData = {}) {
        const claim = this.claims.get(claimId);
        if (!claim) return;

        const previousStatus = claim.status;
        claim.status = newStatus;
        claim.updated_at = new Date();

        claim.timeline.push({
            status: newStatus,
            previous_status: previousStatus,
            timestamp: new Date(),
            action: updateData.reason || `Status updated to ${newStatus}`,
            actor: updateData.automated ? 'system' : 'agent',
            automated: updateData.automated || false,
            details: updateData.details || {}
        });

        this.claims.set(claimId, claim);

        this.emit('claim_status_updated', {
            claim_id: claimId,
            previous_status: previousStatus,
            new_status: newStatus
        });
    }

    async initiateClaimResolution(claimId, method) {
        const claim = this.claims.get(claimId);
        if (!claim) return;

        const resolution = {
            id: this.generateResolutionId(),
            claim_id: claimId,
            method: method, // 'repair', 'replace', 'refund', 'partial_refund'
            status: 'initiated',
            initiated_at: new Date(),
            estimated_completion: this.calculateResolutionTime(method),
            cost_estimate: await this.calculateResolutionCost(claim, method)
        };

        claim.resolution = resolution;
        await this.updateClaimStatus(claimId, 'resolution_in_progress', {
            reason: `${method} resolution initiated`,
            details: { resolution_id: resolution.id }
        });

        // Execute resolution-specific actions
        switch (method) {
            case 'repair':
                await this.arrangeRepairService(claim, resolution);
                break;
            case 'replace':
                await this.arrangeReplacement(claim, resolution);
                break;
            case 'refund':
                await this.processRefund(claim, resolution);
                break;
        }
    }

    async arrangeRepairService(claim, resolution) {
        const warranty = this.warranties.get(claim.warranty_id);
        const repairCenter = await this.findNearestRepairCenter(warranty.customer_id);

        if (repairCenter) {
            resolution.repair_details = {
                repair_center_id: repairCenter.id,
                repair_center_name: repairCenter.name,
                service_level: 'standard',
                estimated_turnaround: repairCenter.turnaround_time,
                shipping_label_provided: true
            };

            await this.sendClaimNotification(claim, 'repair_arranged', {
                repair_center: repairCenter
            });
        }
    }

    async arrangeReplacement(claim, resolution) {
        const warranty = this.warranties.get(claim.warranty_id);
        
        resolution.replacement_details = {
            replacement_type: 'new_unit',
            expedited_shipping: claim.priority === 'critical',
            estimated_delivery: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000),
            return_label_provided: true
        };

        await this.sendClaimNotification(claim, 'replacement_arranged');
    }

    async processRefund(claim, resolution) {
        const warranty = this.warranties.get(claim.warranty_id);
        
        resolution.refund_details = {
            refund_amount: warranty.product_details.purchase_price,
            refund_method: 'original_payment',
            processing_time: '5-7 business days',
            requires_product_return: true
        };

        await this.sendClaimNotification(claim, 'refund_approved');
    }

    async findNearestRepairCenter(customerId) {
        // Mock implementation - find nearest authorized repair center
        const network = this.repairNetworks.get('authorized_repair_network');
        if (network && network.locations.length > 0) {
            return network.locations[0]; // Return first available center
        }
        return null;
    }

    calculateResolutionTime(method) {
        const timeframes = {
            'repair': new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days
            'replace': new Date(Date.now() + 3 * 24 * 60 * 60 * 1000), // 3 days
            'refund': new Date(Date.now() + 5 * 24 * 60 * 60 * 1000), // 5 days
            'partial_refund': new Date(Date.now() + 3 * 24 * 60 * 60 * 1000) // 3 days
        };

        return timeframes[method] || new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
    }

    async calculateResolutionCost(claim, method) {
        const warranty = this.warranties.get(claim.warranty_id);
        const purchasePrice = warranty.product_details.purchase_price || 100;

        const costMultipliers = {
            'repair': 0.3,
            'replace': 1.0,
            'refund': 1.0,
            'partial_refund': 0.5
        };

        return purchasePrice * (costMultipliers[method] || 0.5);
    }

    async sendClaimConfirmation(claim) {
        await this.sendClaimNotification(claim, 'claim_submitted');
    }

    async sendClaimNotification(claim, template, additionalData = {}) {
        const notification = {
            id: this.generateNotificationId(),
            claim_id: claim.id,
            customer_id: claim.customer_id,
            type: 'claim_notification',
            template: template,
            data: {
                ...additionalData,
                claim_id: claim.id,
                claim_number: claim.claim_number,
                claim_type: claim.claim_type,
                status: claim.status
            },
            status: 'sent',
            sent_at: new Date()
        };

        this.notifications.set(notification.id, notification);
        
        this.emit('notification_sent', notification);
    }

    async transferWarranty(warrantyId, transferRequest) {
        const warranty = this.warranties.get(warrantyId);
        if (!warranty) {
            throw new Error(`Warranty ${warrantyId} not found`);
        }

        if (!warranty.terms.transferable) {
            throw new Error('This warranty is not transferable');
        }

        const transfer = {
            id: this.generateTransferId(),
            warranty_id: warrantyId,
            from_customer_id: warranty.customer_id,
            to_customer_id: transferRequest.new_customer_id,
            transfer_date: new Date(),
            transfer_reason: transferRequest.reason,
            transfer_fee: transferRequest.transfer_fee || 0,
            verification_required: transferRequest.verification_required || true,
            status: 'pending_verification'
        };

        // Update warranty
        warranty.customer_id = transferRequest.new_customer_id;
        warranty.transfer_history.push(transfer);

        this.transferHistory.set(transfer.id, transfer);

        this.emit('warranty_transferred', {
            warranty_id: warrantyId,
            from_customer: transfer.from_customer_id,
            to_customer: transfer.to_customer_id
        });

        return transfer;
    }

    async extendWarranty(warrantyId, extensionRequest) {
        const warranty = this.warranties.get(warrantyId);
        if (!warranty) {
            throw new Error(`Warranty ${warrantyId} not found`);
        }

        const currentEndDate = new Date(warranty.coverage_end_date);
        const newEndDate = new Date(currentEndDate);
        newEndDate.setMonth(newEndDate.getMonth() + extensionRequest.extension_months);

        const extension = {
            id: this.generateExtensionId(),
            warranty_id: warrantyId,
            original_end_date: currentEndDate,
            new_end_date: newEndDate,
            extension_months: extensionRequest.extension_months,
            extension_cost: extensionRequest.extension_cost || 0,
            extended_at: new Date(),
            extended_by: extensionRequest.extended_by || 'customer'
        };

        warranty.coverage_end_date = newEndDate;
        warranty.extensions = warranty.extensions || [];
        warranty.extensions.push(extension);

        this.extendedWarranties.set(extension.id, extension);

        // Reschedule expiration reminders
        await this.scheduleExpirationReminders(warranty);

        this.emit('warranty_extended', {
            warranty_id: warrantyId,
            new_end_date: newEndDate,
            extension_months: extensionRequest.extension_months
        });

        return extension;
    }

    async getWarrantyStatus(warrantyId) {
        const warranty = this.warranties.get(warrantyId);
        if (!warranty) {
            throw new Error(`Warranty ${warrantyId} not found`);
        }

        const now = new Date();
        const daysRemaining = Math.ceil((new Date(warranty.coverage_end_date) - now) / (1000 * 60 * 60 * 24));

        return {
            warranty_id: warrantyId,
            status: warranty.status,
            coverage_active: warranty.status === 'active' && daysRemaining > 0,
            days_remaining: Math.max(0, daysRemaining),
            coverage_start: warranty.coverage_start_date,
            coverage_end: warranty.coverage_end_date,
            warranty_type: warranty.warranty_type,
            claims_count: warranty.claim_history.length,
            transferable: warranty.terms.transferable,
            can_extend: warranty.status === 'active' && daysRemaining > -30, // Can extend up to 30 days after expiration
            certificate_url: warranty.certificate?.certificate_url
        };
    }

    async getWarrantyAnalytics(filters = {}) {
        const analytics = {
            total_warranties: this.warranties.size,
            active_warranties: 0,
            expired_warranties: 0,
            claims_submitted: this.claims.size,
            claims_by_status: {},
            average_claim_resolution_time: 0,
            warranty_types_distribution: {},
            claim_types_distribution: {},
            generated_at: new Date()
        };

        // Filter warranties
        let warranties = Array.from(this.warranties.values());
        let claims = Array.from(this.claims.values());

        if (filters.vendor_id) {
            warranties = warranties.filter(w => w.vendor_id === filters.vendor_id);
            claims = claims.filter(c => {
                const warranty = this.warranties.get(c.warranty_id);
                return warranty && warranty.vendor_id === filters.vendor_id;
            });
        }

        if (filters.date_range) {
            const startDate = new Date(filters.date_range.start);
            const endDate = new Date(filters.date_range.end);
            
            warranties = warranties.filter(w => {
                const createdDate = new Date(w.created_at);
                return createdDate >= startDate && createdDate <= endDate;
            });
        }

        // Calculate analytics
        const now = new Date();
        warranties.forEach(warranty => {
            if (warranty.status === 'active' && new Date(warranty.coverage_end_date) > now) {
                analytics.active_warranties++;
            } else {
                analytics.expired_warranties++;
            }

            analytics.warranty_types_distribution[warranty.warranty_type] = 
                (analytics.warranty_types_distribution[warranty.warranty_type] || 0) + 1;
        });

        // Claims analytics
        claims.forEach(claim => {
            analytics.claims_by_status[claim.status] = 
                (analytics.claims_by_status[claim.status] || 0) + 1;

            analytics.claim_types_distribution[claim.claim_type] = 
                (analytics.claim_types_distribution[claim.claim_type] || 0) + 1;
        });

        // Average resolution time
        const resolvedClaims = claims.filter(c => c.status === 'resolved');
        if (resolvedClaims.length > 0) {
            const totalResolutionTime = resolvedClaims.reduce((sum, claim) => {
                const resolution = claim.timeline.find(t => t.status === 'resolved');
                if (resolution) {
                    return sum + (new Date(resolution.timestamp) - new Date(claim.submitted_at));
                }
                return sum;
            }, 0);

            analytics.average_claim_resolution_time = 
                totalResolutionTime / resolvedClaims.length / (1000 * 60 * 60 * 24); // Convert to days
        }

        return analytics;
    }

    // Utility methods
    generateWarrantyId() {
        return `warranty_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateClaimId() {
        return `claim_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateClaimNumber() {
        const timestamp = Date.now().toString().slice(-8);
        const random = Math.random().toString(36).substr(2, 4).toUpperCase();
        return `WC-${timestamp}-${random}`;
    }

    generateNotificationId() {
        return `notification_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateResolutionId() {
        return `resolution_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateTransferId() {
        return `transfer_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateExtensionId() {
        return `extension_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateVerificationCode() {
        return Math.random().toString(36).substr(2, 12).toUpperCase();
    }

    generateDigitalSignature(warranty) {
        // Mock digital signature
        return `DS_${warranty.id}_${Date.now()}`;
    }

    async getWarranty(warrantyId) {
        const warranty = this.warranties.get(warrantyId);
        if (!warranty) {
            throw new Error(`Warranty ${warrantyId} not found`);
        }
        return warranty;
    }

    async getClaim(claimId) {
        const claim = this.claims.get(claimId);
        if (!claim) {
            throw new Error(`Claim ${claimId} not found`);
        }
        return claim;
    }

    async searchWarranties(searchCriteria) {
        let warranties = Array.from(this.warranties.values());

        if (searchCriteria.customer_id) {
            warranties = warranties.filter(w => w.customer_id === searchCriteria.customer_id);
        }

        if (searchCriteria.product_id) {
            warranties = warranties.filter(w => w.product_id === searchCriteria.product_id);
        }

        if (searchCriteria.vendor_id) {
            warranties = warranties.filter(w => w.vendor_id === searchCriteria.vendor_id);
        }

        if (searchCriteria.status) {
            warranties = warranties.filter(w => w.status === searchCriteria.status);
        }

        return warranties;
    }
}