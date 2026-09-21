import { v4 as uuidv4 } from 'uuid';
import Decimal from 'decimal.js';
import moment from 'moment';

export class NonprofitPricingService {
    constructor(redis, logger) {
        this.redis = redis;
        this.logger = logger;
        this.broadcast = null;
        
        // Nonprofit verification requirements
        this.verificationRequirements = {
            'us_501c3': {
                name: 'US 501(c)(3) Organization',
                country: 'US',
                documents: ['irs_determination_letter', 'tax_exempt_certificate'],
                discount: new Decimal('0.50'), // 50% discount
                description: 'US-based 501(c)(3) tax-exempt organizations'
            },
            'us_501c4': {
                name: 'US 501(c)(4) Organization',
                country: 'US',
                documents: ['irs_determination_letter'],
                discount: new Decimal('0.30'), // 30% discount
                description: 'US-based 501(c)(4) social welfare organizations'
            },
            'international_ngo': {
                name: 'International NGO',
                country: 'international',
                documents: ['ngo_registration', 'tax_exempt_status'],
                discount: new Decimal('0.40'), // 40% discount
                description: 'Registered NGOs outside the United States'
            },
            'educational': {
                name: 'Educational Institution',
                country: 'any',
                documents: ['educational_accreditation', 'nonprofit_status'],
                discount: new Decimal('0.60'), // 60% discount
                description: 'Accredited educational institutions'
            },
            'religious': {
                name: 'Religious Organization',
                country: 'any',
                documents: ['religious_exemption', 'nonprofit_registration'],
                discount: new Decimal('0.45'), // 45% discount
                description: 'Religious organizations and places of worship'
            },
            'healthcare': {
                name: 'Healthcare Nonprofit',
                country: 'any',
                documents: ['healthcare_license', 'nonprofit_status'],
                discount: new Decimal('0.55'), // 55% discount
                description: 'Nonprofit hospitals and health organizations'
            }
        };

        // Nonprofit tiers with special features
        this.nonprofitTiers = {
            'community': {
                name: 'Community',
                basePrice: new Decimal('1.00'), // Before nonprofit discount
                maxUsers: 50,
                features: {
                    basicSSO: true,
                    communitySupport: true,
                    donorManagement: true,
                    volunteerTracking: true,
                    basicReporting: true,
                    grantsManagement: false
                },
                description: 'Perfect for small community organizations'
            },
            'organization': {
                name: 'Organization',
                basePrice: new Decimal('2.00'), // Before nonprofit discount
                maxUsers: 250,
                features: {
                    advancedSSO: true,
                    prioritySupport: true,
                    donorManagement: true,
                    volunteerTracking: true,
                    advancedReporting: true,
                    grantsManagement: true,
                    campaignTracking: true,
                    impactMeasurement: true
                },
                description: 'Comprehensive solution for established nonprofits'
            },
            'enterprise': {
                name: 'Enterprise',
                basePrice: new Decimal('2.00'), // Before nonprofit discount
                maxUsers: -1, // unlimited
                features: {
                    customSSO: true,
                    dedicatedSupport: true,
                    donorManagement: true,
                    volunteerTracking: true,
                    customReporting: true,
                    grantsManagement: true,
                    campaignTracking: true,
                    impactMeasurement: true,
                    multiSiteManagement: true,
                    customIntegrations: true,
                    complianceReporting: true
                },
                description: 'Full-featured solution for large nonprofit organizations'
            }
        };

        // Special nonprofit features
        this.nonprofitFeatures = {
            'donor_management': {
                name: 'Advanced Donor Management',
                included: true,
                description: 'Comprehensive donor tracking and engagement tools'
            },
            'grant_tracking': {
                name: 'Grant Application Tracking',
                included: true,
                description: 'Track grant applications and funding opportunities'
            },
            'volunteer_portal': {
                name: 'Volunteer Management Portal',
                included: true,
                description: 'Coordinate volunteers and track hours'
            },
            'impact_reporting': {
                name: 'Impact Measurement Tools',
                included: true,
                description: 'Measure and report on social impact'
            },
            'fundraising_campaigns': {
                name: 'Fundraising Campaign Tools',
                included: true,
                description: 'Manage fundraising campaigns and events'
            },
            'compliance_suite': {
                name: 'Nonprofit Compliance Suite',
                included: true,
                description: 'Tools for regulatory compliance and reporting'
            }
        };

        // Additional compute credits for nonprofits
        this.nonprofitComputeCredits = {
            'community': new Decimal('500'),
            'organization': new Decimal('2000'),
            'enterprise': new Decimal('5000')
        };
    }

    async submitNonprofitApplication(orgId, nonprofitType, organizationInfo, documents) {
        try {
            const applicationId = uuidv4();
            const timestamp = Date.now();
            
            if (!this.verificationRequirements[nonprofitType]) {
                throw new Error(`Invalid nonprofit type: ${nonprofitType}`);
            }

            const requirements = this.verificationRequirements[nonprofitType];
            
            // Validate required documents
            const missingDocs = requirements.documents.filter(doc => !documents[doc]);
            if (missingDocs.length > 0) {
                throw new Error(`Missing required documents: ${missingDocs.join(', ')}`);
            }

            const applicationData = {
                id: applicationId,
                orgId,
                nonprofitType,
                organizationInfo: JSON.stringify(organizationInfo),
                documents: JSON.stringify(documents),
                status: 'pending_review',
                submittedAt: timestamp,
                reviewedAt: null,
                reviewedBy: null,
                reviewNotes: null,
                createdAt: timestamp,
                updatedAt: timestamp
            };

            await this.redis.hset(`nonprofit_application:${applicationId}`, applicationData);
            await this.redis.sadd(`org_applications:${orgId}`, applicationId);
            await this.redis.sadd('pending_nonprofit_applications', applicationId);

            // Send notification to review team
            await this.notifyReviewTeam(applicationId, nonprofitType, organizationInfo);

            this.logger.info(`Nonprofit application submitted: ${applicationId} for org: ${orgId}`);
            return applicationData;
        } catch (error) {
            this.logger.error('Error submitting nonprofit application:', error);
            throw error;
        }
    }

    async reviewNonprofitApplication(applicationId, reviewerId, decision, notes = null) {
        try {
            const applicationData = await this.redis.hgetall(`nonprofit_application:${applicationId}`);
            if (!applicationData.id) {
                throw new Error(`Application not found: ${applicationId}`);
            }

            if (applicationData.status !== 'pending_review') {
                throw new Error(`Cannot review application in status: ${applicationData.status}`);
            }

            const reviewTimestamp = Date.now();
            let newStatus;
            
            switch (decision) {
                case 'approved':
                    newStatus = 'approved';
                    await this.activateNonprofitStatus(applicationData.orgId, applicationData.nonprofitType);
                    break;
                case 'rejected':
                    newStatus = 'rejected';
                    break;
                case 'needs_more_info':
                    newStatus = 'needs_more_info';
                    break;
                default:
                    throw new Error(`Invalid review decision: ${decision}`);
            }

            await this.redis.hset(`nonprofit_application:${applicationId}`, {
                status: newStatus,
                reviewedAt: reviewTimestamp,
                reviewedBy: reviewerId,
                reviewNotes: notes || '',
                updatedAt: reviewTimestamp
            });

            await this.redis.srem('pending_nonprofit_applications', applicationId);

            // Notify organization of decision
            await this.notifyOrganization(applicationData.orgId, newStatus, applicationId);

            this.logger.info(`Nonprofit application ${applicationId} ${newStatus} by ${reviewerId}`);
            return { applicationId, status: newStatus, reviewedAt: reviewTimestamp };
        } catch (error) {
            this.logger.error('Error reviewing nonprofit application:', error);
            throw error;
        }
    }

    async activateNonprofitStatus(orgId, nonprofitType) {
        const verification = this.verificationRequirements[nonprofitType];
        const nonprofitData = {
            orgId,
            nonprofitType,
            discount: verification.discount.toString(),
            verifiedAt: Date.now(),
            status: 'active',
            renewalDate: moment().add(1, 'year').valueOf() // Annual renewal
        };

        await this.redis.hset(`nonprofit_status:${orgId}`, nonprofitData);
        await this.redis.sadd('verified_nonprofits', orgId);

        // Apply retroactive discounts to existing contracts
        await this.applyRetroactiveDiscounts(orgId, verification.discount);
    }

    async applyRetroactiveDiscounts(orgId, discount) {
        try {
            const contractIds = await this.redis.smembers(`org_contracts:${orgId}`);
            
            for (const contractId of contractIds) {
                const contract = await this.redis.hgetall(`enterprise_contract:${contractId}`);
                if (contract.status === 'active') {
                    await this.updateContractWithNonprofitDiscount(contractId, discount);
                }
            }
        } catch (error) {
            this.logger.error('Error applying retroactive discounts:', error);
        }
    }

    async updateContractWithNonprofitDiscount(contractId, discount) {
        const contract = await this.redis.hgetall(`enterprise_contract:${contractId}`);
        const pricing = JSON.parse(contract.pricing);
        
        const originalTotal = new Decimal(pricing.totalPrice);
        const nonprofitDiscount = originalTotal.mul(discount);
        const newTotal = originalTotal.sub(nonprofitDiscount);

        const updatedPricing = {
            ...pricing,
            originalPrice: originalTotal.toString(),
            nonprofitDiscount: nonprofitDiscount.toString(),
            totalPrice: newTotal.toString()
        };

        await this.redis.hset(`enterprise_contract:${contractId}`, {
            pricing: JSON.stringify(updatedPricing),
            updatedAt: Date.now()
        });

        this.logger.info(`Applied nonprofit discount to contract ${contractId}: ${discount.mul(100)}% off`);
    }

    async createNonprofitContract(orgId, tier, userCount, specialRequirements = null) {
        try {
            // Verify nonprofit status
            const nonprofitStatus = await this.redis.hgetall(`nonprofit_status:${orgId}`);
            if (!nonprofitStatus.orgId) {
                throw new Error('Organization does not have verified nonprofit status');
            }

            if (nonprofitStatus.status !== 'active') {
                throw new Error('Nonprofit status is not active');
            }

            const contractId = uuidv4();
            const timestamp = Date.now();
            
            const tierConfig = this.nonprofitTiers[tier];
            if (!tierConfig) {
                throw new Error(`Invalid nonprofit tier: ${tier}`);
            }

            if (tierConfig.maxUsers > 0 && userCount > tierConfig.maxUsers) {
                throw new Error(`User count exceeds limit for ${tier} tier`);
            }

            // Calculate nonprofit pricing
            const pricing = await this.calculateNonprofitPricing(
                tier,
                userCount,
                nonprofitStatus.nonprofitType,
                specialRequirements
            );

            const contractData = {
                id: contractId,
                orgId,
                tier,
                userCount,
                nonprofitType: nonprofitStatus.nonprofitType,
                pricing: JSON.stringify(pricing),
                features: JSON.stringify({
                    ...tierConfig.features,
                    ...this.nonprofitFeatures
                }),
                specialRequirements: specialRequirements ? JSON.stringify(specialRequirements) : null,
                computeCredits: this.nonprofitComputeCredits[tier].toString(),
                status: 'draft',
                createdAt: timestamp,
                updatedAt: timestamp
            };

            await this.redis.hset(`nonprofit_contract:${contractId}`, contractData);
            await this.redis.sadd(`org_nonprofit_contracts:${orgId}`, contractId);

            this.logger.info(`Created nonprofit contract: ${contractId} for org: ${orgId}`);
            return {
                ...contractData,
                pricing: JSON.parse(contractData.pricing),
                features: JSON.parse(contractData.features)
            };
        } catch (error) {
            this.logger.error('Error creating nonprofit contract:', error);
            throw error;
        }
    }

    async calculateNonprofitPricing(tier, userCount, nonprofitType, specialRequirements = null) {
        const tierConfig = this.nonprofitTiers[tier];
        const verification = this.verificationRequirements[nonprofitType];
        
        // Base pricing calculation
        const basePrice = tierConfig.basePrice.mul(userCount);
        
        // Apply nonprofit discount
        const nonprofitDiscount = basePrice.mul(verification.discount);
        const discountedPrice = basePrice.sub(nonprofitDiscount);
        
        // Additional discounts for special circumstances
        let additionalDiscount = new Decimal('0');
        if (specialRequirements) {
            if (specialRequirements.emergencyResponse) {
                additionalDiscount = additionalDiscount.add(discountedPrice.mul(new Decimal('0.20'))); // 20% off for emergency response orgs
            }
            if (specialRequirements.smallBudget && discountedPrice.lt(new Decimal('100'))) {
                additionalDiscount = additionalDiscount.add(discountedPrice.mul(new Decimal('0.50'))); // Additional 50% off for small budget orgs
            }
        }

        const finalPrice = discountedPrice.sub(additionalDiscount);
        
        // Minimum price floor
        const minimumPrice = new Decimal('25.00'); // $25 minimum for sustainability
        const actualPrice = Decimal.max(finalPrice, minimumPrice);

        return {
            basePrice: basePrice.toString(),
            nonprofitDiscount: nonprofitDiscount.toString(),
            additionalDiscount: additionalDiscount.toString(),
            totalPrice: actualPrice.toString(),
            discountPercentage: verification.discount.mul(100).toString(),
            tier,
            userCount,
            nonprofitType
        };
    }

    async renewNonprofitStatus(orgId, documents = null) {
        try {
            const nonprofitStatus = await this.redis.hgetall(`nonprofit_status:${orgId}`);
            if (!nonprofitStatus.orgId) {
                throw new Error('Organization does not have nonprofit status');
            }

            const renewalId = uuidv4();
            const renewalData = {
                id: renewalId,
                orgId,
                currentNonprofitType: nonprofitStatus.nonprofitType,
                documents: documents ? JSON.stringify(documents) : null,
                status: 'pending_review',
                submittedAt: Date.now(),
                createdAt: Date.now()
            };

            await this.redis.hset(`nonprofit_renewal:${renewalId}`, renewalData);
            await this.redis.sadd('pending_nonprofit_renewals', renewalId);

            // Extend current status by 30 days for review period
            const extensionDate = moment(parseInt(nonprofitStatus.renewalDate)).add(30, 'days').valueOf();
            await this.redis.hset(`nonprofit_status:${orgId}`, {
                renewalDate: extensionDate,
                renewalSubmitted: Date.now()
            });

            this.logger.info(`Nonprofit renewal submitted: ${renewalId} for org: ${orgId}`);
            return renewalData;
        } catch (error) {
            this.logger.error('Error renewing nonprofit status:', error);
            throw error;
        }
    }

    async notifyReviewTeam(applicationId, nonprofitType, organizationInfo) {
        // In production, this would send emails/notifications to review team
        this.logger.info(`Notification sent to review team for application: ${applicationId}, type: ${nonprofitType}`);
    }

    async notifyOrganization(orgId, status, applicationId) {
        if (this.broadcast) {
            this.broadcast(`org-analytics-${orgId}`, {
                type: 'nonprofit_application_update',
                applicationId,
                status,
                timestamp: Date.now()
            });
        }
    }

    async getPendingApplications() {
        const applicationIds = await this.redis.smembers('pending_nonprofit_applications');
        const applications = [];

        for (const applicationId of applicationIds) {
            const application = await this.redis.hgetall(`nonprofit_application:${applicationId}`);
            if (application.id) {
                applications.push({
                    ...application,
                    organizationInfo: JSON.parse(application.organizationInfo),
                    documents: JSON.parse(application.documents)
                });
            }
        }

        return applications.sort((a, b) => parseInt(a.submittedAt) - parseInt(b.submittedAt));
    }

    async getNonprofitStatus(orgId) {
        const status = await this.redis.hgetall(`nonprofit_status:${orgId}`);
        if (!status.orgId) {
            return null;
        }

        const verification = this.verificationRequirements[status.nonprofitType];
        return {
            ...status,
            discountPercentage: new Decimal(status.discount).mul(100).toString(),
            verificationDetails: verification,
            renewalDue: parseInt(status.renewalDate) < Date.now() + (90 * 24 * 60 * 60 * 1000) // Due within 90 days
        };
    }

    async getStats() {
        try {
            const stats = {
                totalApplications: 0,
                pendingApplications: await this.redis.scard('pending_nonprofit_applications'),
                verifiedNonprofits: await this.redis.scard('verified_nonprofits'),
                applicationsByType: {},
                totalDiscountGiven: new Decimal('0'),
                nonprofitContracts: 0
            };

            // Get application statistics
            const applicationKeys = await this.redis.keys('nonprofit_application:*');
            for (const key of applicationKeys) {
                const application = await this.redis.hgetall(key);
                stats.totalApplications++;
                stats.applicationsByType[application.nonprofitType] = (stats.applicationsByType[application.nonprofitType] || 0) + 1;
            }

            // Calculate total discount given
            const contractKeys = await this.redis.keys('nonprofit_contract:*');
            for (const key of contractKeys) {
                const contract = await this.redis.hgetall(key);
                if (contract.status === 'active') {
                    stats.nonprofitContracts++;
                    const pricing = JSON.parse(contract.pricing || '{}');
                    if (pricing.nonprofitDiscount) {
                        stats.totalDiscountGiven = stats.totalDiscountGiven.add(new Decimal(pricing.nonprofitDiscount));
                    }
                }
            }

            return {
                ...stats,
                totalDiscountGiven: stats.totalDiscountGiven.toString()
            };
        } catch (error) {
            this.logger.error('Error getting nonprofit pricing stats:', error);
            return {};
        }
    }
}