import { v4 as uuidv4 } from 'uuid';
import Decimal from 'decimal.js';
import moment from 'moment';

export class IPLicensingService {
    constructor(redis, logger) {
        this.redis = redis;
        this.logger = logger;
        this.broadcast = null;
        
        // License types with different terms and pricing
        this.licenseTypes = {
            'personal': {
                name: 'Personal Use License',
                baseCost: new Decimal('9.99'),
                rights: {
                    personalUse: true,
                    commercialUse: false,
                    modification: true,
                    redistribution: false,
                    sublicensing: false,
                    attribution: true
                },
                restrictions: {
                    maxUsers: 1,
                    geographicScope: 'worldwide',
                    timeLimit: null,
                    industryRestrictions: []
                },
                description: 'For personal, non-commercial use only'
            },
            'commercial': {
                name: 'Commercial Use License',
                baseCost: new Decimal('49.99'),
                rights: {
                    personalUse: true,
                    commercialUse: true,
                    modification: true,
                    redistribution: false,
                    sublicensing: false,
                    attribution: true
                },
                restrictions: {
                    maxUsers: 10,
                    geographicScope: 'worldwide',
                    timeLimit: null,
                    industryRestrictions: []
                },
                description: 'For commercial use within your organization'
            },
            'enterprise': {
                name: 'Enterprise License',
                baseCost: new Decimal('199.99'),
                rights: {
                    personalUse: true,
                    commercialUse: true,
                    modification: true,
                    redistribution: true,
                    sublicensing: false,
                    attribution: false
                },
                restrictions: {
                    maxUsers: 100,
                    geographicScope: 'worldwide',
                    timeLimit: null,
                    industryRestrictions: []
                },
                description: 'For large organizations with redistribution rights'
            },
            'royalty_free': {
                name: 'Royalty-Free License',
                baseCost: new Decimal('299.99'),
                rights: {
                    personalUse: true,
                    commercialUse: true,
                    modification: true,
                    redistribution: true,
                    sublicensing: true,
                    attribution: false
                },
                restrictions: {
                    maxUsers: -1, // unlimited
                    geographicScope: 'worldwide',
                    timeLimit: null,
                    industryRestrictions: []
                },
                description: 'Full rights with no ongoing royalty payments'
            },
            'exclusive': {
                name: 'Exclusive License',
                baseCost: new Decimal('999.99'),
                rights: {
                    personalUse: true,
                    commercialUse: true,
                    modification: true,
                    redistribution: true,
                    sublicensing: true,
                    attribution: false,
                    exclusive: true
                },
                restrictions: {
                    maxUsers: -1,
                    geographicScope: 'worldwide',
                    timeLimit: null,
                    industryRestrictions: []
                },
                description: 'Exclusive rights - no one else can license this content'
            }
        };

        // Royalty models for ongoing payments
        this.royaltyModels = {
            'fixed_rate': {
                name: 'Fixed Rate Royalty',
                description: 'Fixed percentage of gross revenue'
            },
            'tiered_rate': {
                name: 'Tiered Royalty',
                description: 'Different rates based on revenue tiers'
            },
            'per_use': {
                name: 'Per-Use Royalty',
                description: 'Fixed amount per usage instance'
            },
            'minimum_guarantee': {
                name: 'Minimum Guarantee',
                description: 'Guaranteed minimum with additional royalties'
            }
        };
    }

    async createLicense(contentId, creatorId, licenseType, customTerms = null, royaltyModel = null) {
        try {
            const licenseId = uuidv4();
            const timestamp = Date.now();
            
            if (!this.licenseTypes[licenseType]) {
                throw new Error(`Invalid license type: ${licenseType}`);
            }

            const licenseConfig = this.licenseTypes[licenseType];
            const cost = await this.calculateLicenseCost(contentId, licenseType, customTerms);

            const licenseData = {
                id: licenseId,
                contentId,
                creatorId,
                licenseType,
                cost: cost.toString(),
                rights: JSON.stringify(licenseConfig.rights),
                restrictions: JSON.stringify(licenseConfig.restrictions),
                customTerms: customTerms ? JSON.stringify(customTerms) : null,
                royaltyModel: royaltyModel ? JSON.stringify(royaltyModel) : null,
                status: 'available',
                exclusive: licenseConfig.rights.exclusive || false,
                createdAt: timestamp,
                updatedAt: timestamp
            };

            await this.redis.hset(`ip_license:${licenseId}`, licenseData);
            await this.redis.sadd(`content_licenses:${contentId}`, licenseId);
            await this.redis.sadd(`creator_licenses:${creatorId}`, licenseId);

            this.logger.info(`Created IP license: ${licenseId} for content: ${contentId}`);
            return licenseData;
        } catch (error) {
            this.logger.error('Error creating IP license:', error);
            throw error;
        }
    }

    async purchaseLicense(licenseId, licenseeId, paymentDetails) {
        try {
            const licenseData = await this.redis.hgetall(`ip_license:${licenseId}`);
            if (!licenseData.id) {
                throw new Error(`License not found: ${licenseId}`);
            }

            if (licenseData.status !== 'available') {
                throw new Error(`License not available: ${licenseData.status}`);
            }

            // Check exclusivity
            if (licenseData.exclusive) {
                const existingPurchases = await this.redis.smembers(`license_purchases:${licenseId}`);
                if (existingPurchases.length > 0) {
                    throw new Error('Exclusive license already sold');
                }
            }

            const purchaseId = uuidv4();
            const timestamp = Date.now();

            const purchaseData = {
                id: purchaseId,
                licenseId,
                licenseeId,
                creatorId: licenseData.creatorId,
                contentId: licenseData.contentId,
                cost: licenseData.cost,
                purchaseDate: timestamp,
                status: 'active',
                rights: licenseData.rights,
                restrictions: licenseData.restrictions,
                customTerms: licenseData.customTerms,
                royaltyModel: licenseData.royaltyModel
            };

            // Process payment
            const paymentResult = await this.processLicensePayment(licenseData.cost, paymentDetails);
            if (!paymentResult.success) {
                throw new Error(`Payment failed: ${paymentResult.error}`);
            }

            purchaseData.paymentId = paymentResult.paymentId;

            await this.redis.hset(`license_purchase:${purchaseId}`, purchaseData);
            await this.redis.sadd(`license_purchases:${licenseId}`, purchaseId);
            await this.redis.sadd(`licensee_purchases:${licenseeId}`, purchaseId);

            // Update license status if exclusive
            if (licenseData.exclusive) {
                await this.redis.hset(`ip_license:${licenseId}`, {
                    status: 'sold',
                    soldTo: licenseeId,
                    soldAt: timestamp
                });
            }

            // Generate license certificate
            const certificate = await this.generateLicenseCertificate(purchaseData);
            
            this.logger.info(`License purchased: ${purchaseId}`);
            return { purchaseData, certificate };
        } catch (error) {
            this.logger.error('Error purchasing license:', error);
            throw error;
        }
    }

    async calculateLicenseCost(contentId, licenseType, customTerms) {
        let baseCost = this.licenseTypes[licenseType].baseCost;
        
        // Apply content-specific multipliers
        const contentValue = await this.getContentValue(contentId);
        if (contentValue.multiplier) {
            baseCost = baseCost.mul(new Decimal(contentValue.multiplier));
        }

        // Apply custom terms adjustments
        if (customTerms) {
            if (customTerms.geographicScope && customTerms.geographicScope !== 'worldwide') {
                baseCost = baseCost.mul(new Decimal('0.7')); // Regional discount
            }
            
            if (customTerms.timeLimit) {
                const years = customTerms.timeLimit / (365 * 24 * 60 * 60 * 1000);
                baseCost = baseCost.mul(new Decimal(Math.min(years, 10) / 10));
            }

            if (customTerms.industryRestrictions && customTerms.industryRestrictions.length > 0) {
                baseCost = baseCost.mul(new Decimal('0.8')); // Industry restriction discount
            }
        }

        return baseCost;
    }

    async getContentValue(contentId) {
        const value = await this.redis.hgetall(`content_ip_value:${contentId}`);
        return {
            multiplier: value.multiplier || '1.0',
            category: value.category || 'standard',
            rarity: value.rarity || 'common'
        };
    }

    async processLicensePayment(amount, paymentDetails) {
        // Mock payment processing
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        return {
            success: Math.random() > 0.05, // 95% success rate
            paymentId: `lic_pay_${uuidv4()}`,
            transactionId: `lic_txn_${uuidv4()}`
        };
    }

    async generateLicenseCertificate(purchaseData) {
        const certificateId = uuidv4();
        const rights = JSON.parse(purchaseData.rights || '{}');
        const restrictions = JSON.parse(purchaseData.restrictions || '{}');

        const certificate = {
            id: certificateId,
            purchaseId: purchaseData.id,
            licensee: purchaseData.licenseeId,
            creator: purchaseData.creatorId,
            content: purchaseData.contentId,
            grantedRights: Object.keys(rights).filter(right => rights[right] === true),
            restrictions: restrictions,
            issueDate: Date.now(),
            validFrom: Date.now(),
            validUntil: restrictions.timeLimit ? Date.now() + restrictions.timeLimit : null,
            certificateNumber: `CERT-${certificateId.substring(0, 8).toUpperCase()}`,
            digitalSignature: `SIG-${uuidv4()}`
        };

        await this.redis.hset(`license_certificate:${certificateId}`, certificate);
        return certificate;
    }

    async validateLicense(purchaseId, usage) {
        try {
            const purchaseData = await this.redis.hgetall(`license_purchase:${purchaseId}`);
            if (!purchaseData.id) {
                return { valid: false, reason: 'License not found' };
            }

            if (purchaseData.status !== 'active') {
                return { valid: false, reason: 'License not active' };
            }

            const rights = JSON.parse(purchaseData.rights || '{}');
            const restrictions = JSON.parse(purchaseData.restrictions || '{}');

            // Check usage against rights
            if (usage.commercial && !rights.commercialUse) {
                return { valid: false, reason: 'Commercial use not permitted' };
            }

            if (usage.modification && !rights.modification) {
                return { valid: false, reason: 'Modification not permitted' };
            }

            if (usage.redistribution && !rights.redistribution) {
                return { valid: false, reason: 'Redistribution not permitted' };
            }

            // Check restrictions
            if (restrictions.timeLimit && Date.now() > (parseInt(purchaseData.purchaseDate) + restrictions.timeLimit)) {
                return { valid: false, reason: 'License expired' };
            }

            if (restrictions.maxUsers > 0 && usage.userCount > restrictions.maxUsers) {
                return { valid: false, reason: 'User limit exceeded' };
            }

            return { valid: true, rights, restrictions };
        } catch (error) {
            this.logger.error('Error validating license:', error);
            return { valid: false, reason: 'Validation error' };
        }
    }

    async processRoyaltyPayment(purchaseId, usage, revenue) {
        try {
            const purchaseData = await this.redis.hgetall(`license_purchase:${purchaseId}`);
            const royaltyModel = JSON.parse(purchaseData.royaltyModel || '{}');
            
            if (!royaltyModel.type) {
                return { amount: new Decimal('0'), processed: false };
            }

            let royaltyAmount = new Decimal('0');

            switch (royaltyModel.type) {
                case 'fixed_rate':
                    royaltyAmount = new Decimal(revenue).mul(new Decimal(royaltyModel.rate));
                    break;
                case 'per_use':
                    royaltyAmount = new Decimal(royaltyModel.amountPerUse).mul(usage.count || 1);
                    break;
                case 'tiered_rate':
                    royaltyAmount = this.calculateTieredRoyalty(revenue, royaltyModel.tiers);
                    break;
            }

            // Record royalty payment
            const royaltyId = uuidv4();
            const royaltyRecord = {
                id: royaltyId,
                purchaseId,
                licenseeId: purchaseData.licenseeId,
                creatorId: purchaseData.creatorId,
                amount: royaltyAmount.toString(),
                revenue: revenue.toString(),
                usage: JSON.stringify(usage),
                processedAt: Date.now()
            };

            await this.redis.hset(`royalty_payment:${royaltyId}`, royaltyRecord);
            await this.redis.sadd(`creator_royalties:${purchaseData.creatorId}`, royaltyId);

            return { amount: royaltyAmount, processed: true, royaltyId };
        } catch (error) {
            this.logger.error('Error processing royalty payment:', error);
            throw error;
        }
    }

    calculateTieredRoyalty(revenue, tiers) {
        let totalRoyalty = new Decimal('0');
        let remaining = new Decimal(revenue);

        for (const tier of tiers.sort((a, b) => a.threshold - b.threshold)) {
            if (remaining.lte(0)) break;

            const tierAmount = tier.limit ? 
                Decimal.min(remaining, new Decimal(tier.limit)) : 
                remaining;
            
            const tierRoyalty = tierAmount.mul(new Decimal(tier.rate));
            totalRoyalty = totalRoyalty.add(tierRoyalty);
            remaining = remaining.sub(tierAmount);
        }

        return totalRoyalty;
    }

    async getStats() {
        try {
            const stats = {
                totalLicenses: 0,
                activeLicenses: 0,
                totalRevenue: new Decimal('0'),
                licensesByType: {},
                averageLicenseValue: new Decimal('0'),
                exclusiveLicensesSold: 0
            };

            const licenseKeys = await this.redis.keys('ip_license:*');
            const purchaseKeys = await this.redis.keys('license_purchase:*');

            stats.totalLicenses = licenseKeys.length;

            for (const key of licenseKeys) {
                const license = await this.redis.hgetall(key);
                stats.licensesByType[license.licenseType] = (stats.licensesByType[license.licenseType] || 0) + 1;
            }

            for (const key of purchaseKeys) {
                const purchase = await this.redis.hgetall(key);
                if (purchase.status === 'active') {
                    stats.activeLicenses++;
                    stats.totalRevenue = stats.totalRevenue.add(new Decimal(purchase.cost || '0'));
                }
            }

            stats.averageLicenseValue = stats.activeLicenses > 0 ? 
                stats.totalRevenue.div(stats.activeLicenses) : 
                new Decimal('0');

            return {
                ...stats,
                totalRevenue: stats.totalRevenue.toString(),
                averageLicenseValue: stats.averageLicenseValue.toString()
            };
        } catch (error) {
            this.logger.error('Error getting IP licensing stats:', error);
            return {};
        }
    }
}