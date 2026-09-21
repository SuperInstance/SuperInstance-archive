import { EventEmitter } from 'events';
import crypto from 'crypto';

class RevenueSharingEngine extends EventEmitter {
    constructor() {
        super();
        this.agreements = new Map();
        this.transactions = new Map();
        this.payouts = new Map();
        this.affiliates = new Map();
        this.commissions = new Map();
        this.royalties = new Map();
        this.escrow = new Map();
        this.analytics = new Map();
        this.disputes = new Map();
        this.taxDocuments = new Map();
        
        this.initializeData();
    }

    initializeData() {
        // Initialize sample affiliate partners
        const sampleAffiliates = [
            {
                id: 'affiliate_001',
                name: 'TechReview Pro',
                type: 'content_creator',
                category: 'electronics_reviews',
                commission_tier: 'premium',
                base_commission: 8.5,
                performance_bonus: 2.0,
                minimum_payout: 100.0,
                payment_method: 'bank_transfer',
                tax_info: {
                    status: 'verified',
                    w9_submitted: true,
                    ein: 'XX-XXXXXXX'
                },
                metrics: {
                    total_sales: 45670.50,
                    conversions: 234,
                    click_through_rate: 4.2,
                    average_order_value: 195.17
                },
                contact: {
                    email: 'partnerships@techreviewpro.com',
                    phone: '+1-555-0156'
                },
                joined_date: new Date('2024-01-15'),
                status: 'active'
            },
            {
                id: 'affiliate_002',
                name: 'Marine Electronics Hub',
                type: 'retailer',
                category: 'marine_equipment',
                commission_tier: 'standard',
                base_commission: 6.0,
                performance_bonus: 1.5,
                minimum_payout: 250.0,
                payment_method: 'paypal',
                tax_info: {
                    status: 'pending',
                    w9_submitted: false,
                    ein: null
                },
                metrics: {
                    total_sales: 28340.75,
                    conversions: 89,
                    click_through_rate: 3.1,
                    average_order_value: 318.43
                },
                contact: {
                    email: 'sales@marinehub.com',
                    phone: '+1-555-0157'
                },
                joined_date: new Date('2024-03-22'),
                status: 'active'
            },
            {
                id: 'affiliate_003',
                name: 'DIY Electronics Community',
                type: 'community',
                category: 'diy_electronics',
                commission_tier: 'community',
                base_commission: 5.0,
                performance_bonus: 3.0,
                minimum_payout: 50.0,
                payment_method: 'crypto',
                tax_info: {
                    status: 'verified',
                    w9_submitted: true,
                    ein: 'XX-XXXXXXX'
                },
                metrics: {
                    total_sales: 67890.25,
                    conversions: 456,
                    click_through_rate: 6.8,
                    average_order_value: 148.87
                },
                contact: {
                    email: 'community@diyelectronics.org',
                    phone: '+1-555-0158'
                },
                joined_date: new Date('2023-11-10'),
                status: 'active'
            }
        ];

        sampleAffiliates.forEach(affiliate => {
            this.affiliates.set(affiliate.id, affiliate);
        });

        // Initialize sample revenue sharing agreements
        const sampleAgreements = [
            {
                id: 'agreement_001',
                title: 'Fish Counter Revenue Share',
                type: 'royalty_agreement',
                product_id: 'community_design_001',
                creator_id: 'user_003',
                revenue_share: {
                    creator_percentage: 60.0,
                    platform_percentage: 25.0,
                    affiliate_percentage: 15.0
                },
                tier_bonuses: {
                    tier1: { threshold: 1000, bonus: 5.0 },
                    tier2: { threshold: 5000, bonus: 10.0 },
                    tier3: { threshold: 10000, bonus: 15.0 }
                },
                payment_terms: {
                    frequency: 'monthly',
                    minimum_payout: 50.0,
                    payment_day: 15,
                    hold_period_days: 30
                },
                effective_date: new Date('2024-01-01'),
                expiry_date: new Date('2026-12-31'),
                status: 'active',
                total_revenue: 12450.75,
                total_payouts: 7470.45
            },
            {
                id: 'agreement_002',
                title: 'Solar Camera Partnership',
                type: 'partnership_agreement',
                product_id: 'community_design_002',
                creator_id: 'user_002',
                revenue_share: {
                    creator_percentage: 55.0,
                    platform_percentage: 30.0,
                    marketing_percentage: 15.0
                },
                tier_bonuses: {
                    tier1: { threshold: 2000, bonus: 3.0 },
                    tier2: { threshold: 8000, bonus: 7.0 },
                    tier3: { threshold: 15000, bonus: 12.0 }
                },
                payment_terms: {
                    frequency: 'bi_weekly',
                    minimum_payout: 100.0,
                    payment_day: 1,
                    hold_period_days: 14
                },
                effective_date: new Date('2024-02-15'),
                expiry_date: new Date('2027-02-14'),
                status: 'active',
                total_revenue: 18765.90,
                total_payouts: 10321.25
            }
        ];

        sampleAgreements.forEach(agreement => {
            this.agreements.set(agreement.id, agreement);
        });

        // Initialize sample transactions
        const sampleTransactions = [
            {
                id: 'txn_001',
                agreement_id: 'agreement_001',
                product_id: 'community_design_001',
                customer_id: 'customer_001',
                affiliate_id: 'affiliate_003',
                amount: 185.00,
                currency: 'USD',
                timestamp: new Date('2024-08-20T14:30:00Z'),
                status: 'completed',
                commission_breakdown: {
                    creator_amount: 111.00,
                    platform_amount: 46.25,
                    affiliate_amount: 27.75
                },
                payment_processor: 'stripe',
                transaction_fee: 5.55,
                net_amount: 179.45
            },
            {
                id: 'txn_002',
                agreement_id: 'agreement_002',
                product_id: 'community_design_002',
                customer_id: 'customer_002',
                affiliate_id: 'affiliate_001',
                amount: 295.00,
                currency: 'USD',
                timestamp: new Date('2024-08-22T09:15:00Z'),
                status: 'completed',
                commission_breakdown: {
                    creator_amount: 162.25,
                    platform_amount: 88.50,
                    marketing_amount: 44.25
                },
                payment_processor: 'paypal',
                transaction_fee: 8.85,
                net_amount: 286.15
            },
            {
                id: 'txn_003',
                agreement_id: 'agreement_001',
                product_id: 'community_design_001',
                customer_id: 'customer_003',
                affiliate_id: 'affiliate_002',
                amount: 185.00,
                currency: 'USD',
                timestamp: new Date('2024-08-23T16:45:00Z'),
                status: 'pending',
                commission_breakdown: {
                    creator_amount: 111.00,
                    platform_amount: 46.25,
                    affiliate_amount: 27.75
                },
                payment_processor: 'stripe',
                transaction_fee: 5.55,
                net_amount: 179.45
            }
        ];

        sampleTransactions.forEach(transaction => {
            this.transactions.set(transaction.id, transaction);
        });

        // Initialize sample payouts
        const samplePayouts = [
            {
                id: 'payout_001',
                recipient_id: 'user_003',
                recipient_type: 'creator',
                agreement_id: 'agreement_001',
                amount: 555.00,
                currency: 'USD',
                period: {
                    start: new Date('2024-07-01'),
                    end: new Date('2024-07-31')
                },
                status: 'completed',
                payment_method: 'bank_transfer',
                payment_date: new Date('2024-08-15'),
                transaction_ids: ['txn_004', 'txn_005', 'txn_006'],
                tax_withholding: 0.00,
                fees: 2.50,
                net_amount: 552.50,
                reference_number: 'PAY-2024-08-001'
            },
            {
                id: 'payout_002',
                recipient_id: 'affiliate_001',
                recipient_type: 'affiliate',
                agreement_id: null,
                amount: 234.75,
                currency: 'USD',
                period: {
                    start: new Date('2024-08-01'),
                    end: new Date('2024-08-15')
                },
                status: 'processing',
                payment_method: 'paypal',
                payment_date: null,
                transaction_ids: ['txn_007', 'txn_008'],
                tax_withholding: 23.48,
                fees: 7.04,
                net_amount: 204.23,
                reference_number: 'PAY-2024-08-002'
            }
        ];

        samplePayouts.forEach(payout => {
            this.payouts.set(payout.id, payout);
        });

        // Initialize commission tiers
        this.initializeCommissionTiers();
    }

    initializeCommissionTiers() {
        this.commissionTiers = {
            'basic': { min_sales: 0, base_rate: 3.0, bonus: 0 },
            'standard': { min_sales: 1000, base_rate: 5.0, bonus: 1.0 },
            'premium': { min_sales: 5000, base_rate: 7.0, bonus: 2.0 },
            'elite': { min_sales: 15000, base_rate: 10.0, bonus: 3.0 },
            'enterprise': { min_sales: 50000, base_rate: 15.0, bonus: 5.0 }
        };
    }

    generateId(prefix) {
        return `${prefix}_${crypto.randomBytes(8).toString('hex')}`;
    }

    // Agreement Management
    async createRevenueAgreement(agreementData) {
        try {
            // Validate revenue percentages
            const totalPercentage = Object.values(agreementData.revenue_share)
                .reduce((sum, percentage) => sum + percentage, 0);
            
            if (Math.abs(totalPercentage - 100) > 0.01) {
                throw new Error('Revenue share percentages must sum to 100%');
            }

            const agreement = {
                id: this.generateId('agreement'),
                title: agreementData.title,
                type: agreementData.type || 'revenue_share',
                product_id: agreementData.product_id,
                creator_id: agreementData.creator_id,
                revenue_share: agreementData.revenue_share,
                tier_bonuses: agreementData.tier_bonuses || {},
                payment_terms: {
                    frequency: agreementData.payment_frequency || 'monthly',
                    minimum_payout: agreementData.minimum_payout || 50.0,
                    payment_day: agreementData.payment_day || 15,
                    hold_period_days: agreementData.hold_period || 30
                },
                effective_date: agreementData.effective_date || new Date(),
                expiry_date: agreementData.expiry_date,
                status: 'active',
                total_revenue: 0,
                total_payouts: 0,
                created_date: new Date(),
                terms_hash: this.generateTermsHash(agreementData)
            };

            this.agreements.set(agreement.id, agreement);
            this.emit('agreement_created', agreement);

            return {
                success: true,
                agreement_id: agreement.id,
                message: 'Revenue sharing agreement created successfully'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    generateTermsHash(agreementData) {
        const termsString = JSON.stringify({
            revenue_share: agreementData.revenue_share,
            payment_terms: agreementData.payment_terms,
            tier_bonuses: agreementData.tier_bonuses
        });
        return crypto.createHash('sha256').update(termsString).digest('hex').substring(0, 16);
    }

    async updateAgreement(agreementId, updates) {
        try {
            const agreement = this.agreements.get(agreementId);
            if (!agreement) {
                throw new Error('Agreement not found');
            }

            // Create version history
            if (!agreement.version_history) {
                agreement.version_history = [];
            }

            agreement.version_history.push({
                version: (agreement.version_history.length + 1),
                changes: updates,
                updated_date: new Date(),
                updated_by: updates.updated_by
            });

            // Apply updates
            Object.keys(updates).forEach(key => {
                if (key !== 'updated_by') {
                    agreement[key] = updates[key];
                }
            });

            agreement.last_updated = new Date();
            this.agreements.set(agreementId, agreement);

            this.emit('agreement_updated', { agreement_id: agreementId, updates });

            return {
                success: true,
                message: 'Agreement updated successfully'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    // Transaction Processing
    async processTransaction(transactionData) {
        try {
            const agreement = this.agreements.get(transactionData.agreement_id);
            if (!agreement) {
                throw new Error('Revenue sharing agreement not found');
            }

            const transaction = {
                id: this.generateId('txn'),
                agreement_id: transactionData.agreement_id,
                product_id: transactionData.product_id,
                customer_id: transactionData.customer_id,
                affiliate_id: transactionData.affiliate_id || null,
                amount: parseFloat(transactionData.amount),
                currency: transactionData.currency || 'USD',
                timestamp: new Date(),
                status: 'processing',
                payment_processor: transactionData.payment_processor || 'stripe',
                transaction_fee: this.calculateTransactionFee(transactionData.amount, transactionData.payment_processor),
                metadata: transactionData.metadata || {}
            };

            // Calculate commission breakdown
            transaction.commission_breakdown = this.calculateCommissionBreakdown(
                transaction.amount,
                agreement,
                transaction.affiliate_id
            );

            transaction.net_amount = transaction.amount - transaction.transaction_fee;
            transaction.status = 'completed';

            this.transactions.set(transaction.id, transaction);

            // Update agreement totals
            agreement.total_revenue += transaction.amount;
            this.agreements.set(transactionData.agreement_id, agreement);

            this.emit('transaction_processed', transaction);

            return {
                success: true,
                transaction_id: transaction.id,
                commission_breakdown: transaction.commission_breakdown,
                net_amount: transaction.net_amount
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    calculateTransactionFee(amount, processor) {
        const feeRates = {
            'stripe': 0.029 + 0.30,
            'paypal': 0.034 + 0.49,
            'square': 0.026 + 0.10,
            'bank_transfer': 1.50
        };

        const rate = feeRates[processor] || feeRates['stripe'];
        return Math.round((amount * (rate < 1 ? rate : 0) + (rate >= 1 ? rate : 0)) * 100) / 100;
    }

    calculateCommissionBreakdown(amount, agreement, affiliateId = null) {
        const breakdown = {};
        let remainingAmount = amount;

        // Apply tier bonuses if applicable
        const currentTier = this.getCurrentTier(agreement.total_revenue, agreement.tier_bonuses);
        const bonusMultiplier = currentTier ? (1 + currentTier.bonus / 100) : 1;

        // Calculate each party's share
        Object.entries(agreement.revenue_share).forEach(([party, percentage]) => {
            let partyAmount = (amount * percentage / 100) * bonusMultiplier;
            partyAmount = Math.round(partyAmount * 100) / 100;
            breakdown[`${party}_amount`] = partyAmount;
            remainingAmount -= partyAmount;
        });

        // Handle affiliate commission if present
        if (affiliateId && this.affiliates.has(affiliateId)) {
            const affiliate = this.affiliates.get(affiliateId);
            const affiliateCommission = this.calculateAffiliateCommission(amount, affiliate);
            breakdown['affiliate_amount'] = affiliateCommission;
            remainingAmount -= affiliateCommission;
        }

        // Add any rounding remainder to platform
        if (Math.abs(remainingAmount) > 0.01) {
            breakdown['platform_amount'] = (breakdown['platform_amount'] || 0) + remainingAmount;
        }

        return breakdown;
    }

    getCurrentTier(totalRevenue, tierBonuses) {
        let currentTier = null;
        Object.values(tierBonuses).forEach(tier => {
            if (totalRevenue >= tier.threshold && (!currentTier || tier.threshold > currentTier.threshold)) {
                currentTier = tier;
            }
        });
        return currentTier;
    }

    calculateAffiliateCommission(amount, affiliate) {
        const baseCommission = amount * (affiliate.base_commission / 100);
        const performanceBonus = baseCommission * (affiliate.performance_bonus / 100);
        return Math.round((baseCommission + performanceBonus) * 100) / 100;
    }

    // Payout Management
    async generatePayouts(period = 'monthly') {
        try {
            const now = new Date();
            let startDate, endDate;

            switch (period) {
                case 'weekly':
                    startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 7);
                    endDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
                    break;
                case 'bi_weekly':
                    startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 14);
                    endDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
                    break;
                case 'monthly':
                default:
                    startDate = new Date(now.getFullYear(), now.getMonth() - 1, 1);
                    endDate = new Date(now.getFullYear(), now.getMonth(), 0);
                    break;
            }

            const pendingPayouts = [];
            const transactions = Array.from(this.transactions.values())
                .filter(t => t.timestamp >= startDate && t.timestamp <= endDate && t.status === 'completed');

            // Group transactions by recipient
            const recipientGroups = {};

            transactions.forEach(transaction => {
                const agreement = this.agreements.get(transaction.agreement_id);
                if (agreement) {
                    // Creator payouts
                    const creatorId = agreement.creator_id;
                    if (!recipientGroups[creatorId]) {
                        recipientGroups[creatorId] = {
                            type: 'creator',
                            transactions: [],
                            total_amount: 0
                        };
                    }
                    recipientGroups[creatorId].transactions.push(transaction);
                    recipientGroups[creatorId].total_amount += transaction.commission_breakdown.creator_amount || 0;

                    // Affiliate payouts
                    if (transaction.affiliate_id) {
                        if (!recipientGroups[transaction.affiliate_id]) {
                            recipientGroups[transaction.affiliate_id] = {
                                type: 'affiliate',
                                transactions: [],
                                total_amount: 0
                            };
                        }
                        recipientGroups[transaction.affiliate_id].transactions.push(transaction);
                        recipientGroups[transaction.affiliate_id].total_amount += transaction.commission_breakdown.affiliate_amount || 0;
                    }
                }
            });

            // Create payout records
            Object.entries(recipientGroups).forEach(([recipientId, group]) => {
                if (group.total_amount >= this.getMinimumPayout(recipientId, group.type)) {
                    const payout = this.createPayoutRecord(recipientId, group, startDate, endDate);
                    pendingPayouts.push(payout);
                }
            });

            return {
                success: true,
                payouts_generated: pendingPayouts.length,
                total_payout_amount: pendingPayouts.reduce((sum, p) => sum + p.amount, 0),
                period: { start: startDate, end: endDate },
                payouts: pendingPayouts
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    getMinimumPayout(recipientId, type) {
        if (type === 'affiliate') {
            const affiliate = this.affiliates.get(recipientId);
            return affiliate ? affiliate.minimum_payout : 50.0;
        }
        return 50.0; // Default minimum for creators
    }

    createPayoutRecord(recipientId, group, startDate, endDate) {
        const taxWithholding = this.calculateTaxWithholding(recipientId, group.total_amount);
        const fees = this.calculatePayoutFees(group.total_amount);
        const netAmount = group.total_amount - taxWithholding - fees;

        const payout = {
            id: this.generateId('payout'),
            recipient_id: recipientId,
            recipient_type: group.type,
            amount: group.total_amount,
            currency: 'USD',
            period: { start: startDate, end: endDate },
            status: 'pending',
            payment_method: this.getPreferredPaymentMethod(recipientId, group.type),
            transaction_ids: group.transactions.map(t => t.id),
            tax_withholding: taxWithholding,
            fees: fees,
            net_amount: netAmount,
            reference_number: this.generatePayoutReference(),
            created_date: new Date()
        };

        this.payouts.set(payout.id, payout);
        return payout;
    }

    calculateTaxWithholding(recipientId, amount) {
        // Simplified tax calculation - in production, this would be more complex
        return 0; // No withholding by default
    }

    calculatePayoutFees(amount) {
        // Standard payout processing fee
        return Math.round(Math.max(2.50, amount * 0.01) * 100) / 100;
    }

    getPreferredPaymentMethod(recipientId, type) {
        if (type === 'affiliate') {
            const affiliate = this.affiliates.get(recipientId);
            return affiliate ? affiliate.payment_method : 'bank_transfer';
        }
        return 'bank_transfer';
    }

    generatePayoutReference() {
        const date = new Date();
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const counter = String(this.payouts.size + 1).padStart(3, '0');
        return `PAY-${year}-${month}-${counter}`;
    }

    // Affiliate Management
    async registerAffiliate(affiliateData) {
        try {
            const affiliate = {
                id: this.generateId('affiliate'),
                name: affiliateData.name,
                type: affiliateData.type || 'individual',
                category: affiliateData.category,
                commission_tier: this.determineTier(0),
                base_commission: this.commissionTiers[this.determineTier(0)].base_rate,
                performance_bonus: this.commissionTiers[this.determineTier(0)].bonus,
                minimum_payout: affiliateData.minimum_payout || 50.0,
                payment_method: affiliateData.payment_method || 'bank_transfer',
                tax_info: {
                    status: 'pending',
                    w9_submitted: false,
                    ein: null
                },
                metrics: {
                    total_sales: 0,
                    conversions: 0,
                    click_through_rate: 0,
                    average_order_value: 0
                },
                contact: affiliateData.contact,
                joined_date: new Date(),
                status: 'pending_approval',
                referral_code: this.generateReferralCode(),
                tracking_links: {}
            };

            this.affiliates.set(affiliate.id, affiliate);
            this.emit('affiliate_registered', affiliate);

            return {
                success: true,
                affiliate_id: affiliate.id,
                referral_code: affiliate.referral_code,
                message: 'Affiliate registration submitted successfully'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    determineTier(totalSales) {
        for (const [tier, requirements] of Object.entries(this.commissionTiers).reverse()) {
            if (totalSales >= requirements.min_sales) {
                return tier;
            }
        }
        return 'basic';
    }

    generateReferralCode() {
        return crypto.randomBytes(6).toString('hex').toUpperCase();
    }

    async updateAffiliateTier(affiliateId) {
        try {
            const affiliate = this.affiliates.get(affiliateId);
            if (!affiliate) {
                throw new Error('Affiliate not found');
            }

            const newTier = this.determineTier(affiliate.metrics.total_sales);
            if (newTier !== affiliate.commission_tier) {
                const oldTier = affiliate.commission_tier;
                affiliate.commission_tier = newTier;
                affiliate.base_commission = this.commissionTiers[newTier].base_rate;
                affiliate.performance_bonus = this.commissionTiers[newTier].bonus;

                this.affiliates.set(affiliateId, affiliate);
                this.emit('affiliate_tier_updated', { 
                    affiliate_id: affiliateId, 
                    old_tier: oldTier, 
                    new_tier: newTier 
                });
            }

            return {
                success: true,
                current_tier: affiliate.commission_tier,
                commission_rate: affiliate.base_commission
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    // Analytics and Reporting
    async getRevenueAnalytics(period = '30d', agreementId = null) {
        try {
            const now = new Date();
            let startDate;

            switch (period) {
                case '7d':
                    startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                    break;
                case '30d':
                    startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
                    break;
                case '90d':
                    startDate = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
                    break;
                case '1y':
                    startDate = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000);
                    break;
                default:
                    startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
            }

            let transactions = Array.from(this.transactions.values())
                .filter(t => t.timestamp >= startDate && t.timestamp <= now);

            if (agreementId) {
                transactions = transactions.filter(t => t.agreement_id === agreementId);
            }

            const analytics = {
                period: { start: startDate, end: now },
                total_transactions: transactions.length,
                total_revenue: transactions.reduce((sum, t) => sum + t.amount, 0),
                total_fees: transactions.reduce((sum, t) => sum + t.transaction_fee, 0),
                net_revenue: transactions.reduce((sum, t) => sum + t.net_amount, 0),
                average_transaction_value: transactions.length > 0 ? 
                    transactions.reduce((sum, t) => sum + t.amount, 0) / transactions.length : 0,
                commission_breakdown: this.calculatePeriodCommissions(transactions),
                daily_breakdown: this.generateDailyBreakdown(transactions, startDate, now),
                top_products: this.getTopProducts(transactions),
                top_affiliates: this.getTopAffiliates(transactions)
            };

            return {
                success: true,
                analytics: analytics
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    calculatePeriodCommissions(transactions) {
        const breakdown = {
            creator_total: 0,
            platform_total: 0,
            affiliate_total: 0,
            marketing_total: 0
        };

        transactions.forEach(transaction => {
            Object.entries(transaction.commission_breakdown || {}).forEach(([key, amount]) => {
                if (breakdown.hasOwnProperty(`${key.replace('_amount', '_total')}`)) {
                    breakdown[`${key.replace('_amount', '_total')}`] += amount;
                }
            });
        });

        return breakdown;
    }

    generateDailyBreakdown(transactions, startDate, endDate) {
        const dailyData = {};
        const currentDate = new Date(startDate);

        while (currentDate <= endDate) {
            const dateStr = currentDate.toISOString().split('T')[0];
            dailyData[dateStr] = {
                date: dateStr,
                transactions: 0,
                revenue: 0,
                conversions: 0
            };
            currentDate.setDate(currentDate.getDate() + 1);
        }

        transactions.forEach(transaction => {
            const dateStr = transaction.timestamp.toISOString().split('T')[0];
            if (dailyData[dateStr]) {
                dailyData[dateStr].transactions += 1;
                dailyData[dateStr].revenue += transaction.amount;
                dailyData[dateStr].conversions += 1;
            }
        });

        return Object.values(dailyData);
    }

    getTopProducts(transactions) {
        const productStats = {};

        transactions.forEach(transaction => {
            const productId = transaction.product_id;
            if (!productStats[productId]) {
                productStats[productId] = {
                    product_id: productId,
                    transactions: 0,
                    revenue: 0,
                    conversions: 0
                };
            }
            productStats[productId].transactions += 1;
            productStats[productId].revenue += transaction.amount;
            productStats[productId].conversions += 1;
        });

        return Object.values(productStats)
            .sort((a, b) => b.revenue - a.revenue)
            .slice(0, 10);
    }

    getTopAffiliates(transactions) {
        const affiliateStats = {};

        transactions.filter(t => t.affiliate_id).forEach(transaction => {
            const affiliateId = transaction.affiliate_id;
            if (!affiliateStats[affiliateId]) {
                affiliateStats[affiliateId] = {
                    affiliate_id: affiliateId,
                    transactions: 0,
                    revenue: 0,
                    commission_earned: 0
                };
            }
            affiliateStats[affiliateId].transactions += 1;
            affiliateStats[affiliateId].revenue += transaction.amount;
            affiliateStats[affiliateId].commission_earned += transaction.commission_breakdown.affiliate_amount || 0;
        });

        return Object.values(affiliateStats)
            .sort((a, b) => b.commission_earned - a.commission_earned)
            .slice(0, 10);
    }

    // Tax and Compliance
    async generateTaxDocuments(year, recipientId = null) {
        try {
            const startDate = new Date(year, 0, 1);
            const endDate = new Date(year, 11, 31);

            let payouts = Array.from(this.payouts.values())
                .filter(p => p.payment_date >= startDate && p.payment_date <= endDate);

            if (recipientId) {
                payouts = payouts.filter(p => p.recipient_id === recipientId);
            }

            const taxDocuments = [];

            // Group by recipient
            const recipientGroups = {};
            payouts.forEach(payout => {
                if (!recipientGroups[payout.recipient_id]) {
                    recipientGroups[payout.recipient_id] = [];
                }
                recipientGroups[payout.recipient_id].push(payout);
            });

            // Generate 1099s for qualifying recipients
            Object.entries(recipientGroups).forEach(([recipientId, recipientPayouts]) => {
                const totalAmount = recipientPayouts.reduce((sum, p) => sum + p.amount, 0);
                
                if (totalAmount >= 600) { // IRS threshold for 1099
                    const document = {
                        id: this.generateId('tax_doc'),
                        type: '1099-NEC',
                        year: year,
                        recipient_id: recipientId,
                        total_payments: totalAmount,
                        tax_withheld: recipientPayouts.reduce((sum, p) => sum + p.tax_withholding, 0),
                        generated_date: new Date(),
                        status: 'draft'
                    };

                    this.taxDocuments.set(document.id, document);
                    taxDocuments.push(document);
                }
            });

            return {
                success: true,
                documents_generated: taxDocuments.length,
                tax_documents: taxDocuments
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    // Escrow Management
    async createEscrowAccount(agreementId, amount, releaseConditions) {
        try {
            const escrow = {
                id: this.generateId('escrow'),
                agreement_id: agreementId,
                amount: amount,
                currency: 'USD',
                status: 'active',
                release_conditions: releaseConditions,
                created_date: new Date(),
                release_date: null,
                released_amount: 0,
                dispute_id: null
            };

            this.escrow.set(escrow.id, escrow);
            this.emit('escrow_created', escrow);

            return {
                success: true,
                escrow_id: escrow.id,
                message: 'Escrow account created successfully'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }
}

export default RevenueSharingEngine;