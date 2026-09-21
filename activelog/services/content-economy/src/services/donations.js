import { v4 as uuidv4 } from 'uuid';
import Decimal from 'decimal.js';
import moment from 'moment';

export class DonationService {
    constructor(redis, logger) {
        this.redis = redis;
        this.logger = logger;
        this.broadcast = null;
        
        this.donationTypes = {
            'one_time': { name: 'One-Time Donation', recurring: false },
            'monthly': { name: 'Monthly Support', recurring: true, interval: 30 },
            'yearly': { name: 'Yearly Support', recurring: true, interval: 365 }
        };
        
        this.donationGoals = {
            'project': { name: 'Project Funding', hasTarget: true },
            'general': { name: 'General Support', hasTarget: false },
            'equipment': { name: 'Equipment Fund', hasTarget: true },
            'education': { name: 'Education Fund', hasTarget: true }
        };
    }

    async createDonation(donorId, creatorId, amount, type = 'one_time', message = '', goalId = null) {
        try {
            const donationId = uuidv4();
            const timestamp = Date.now();
            
            const donationData = {
                id: donationId,
                donorId,
                creatorId,
                amount: amount.toString(),
                type,
                message,
                goalId,
                status: 'pending',
                createdAt: timestamp
            };

            await this.redis.hset(`donation:${donationId}`, donationData);
            await this.redis.sadd(`donor_donations:${donorId}`, donationId);
            await this.redis.sadd(`creator_donations:${creatorId}`, donationId);
            
            if (goalId) {
                await this.redis.sadd(`goal_donations:${goalId}`, donationId);
            }

            return donationData;
        } catch (error) {
            this.logger.error('Error creating donation:', error);
            throw error;
        }
    }

    async processDonation(donationId, paymentDetails) {
        try {
            const donation = await this.redis.hgetall(`donation:${donationId}`);
            if (!donation.id) {
                throw new Error(`Donation not found: ${donationId}`);
            }

            const paymentResult = await this.processDonationPayment(donation.amount, paymentDetails);
            
            if (paymentResult.success) {
                await this.redis.hset(`donation:${donationId}`, {
                    status: 'completed',
                    paymentId: paymentResult.paymentId,
                    processedAt: Date.now()
                });

                // Update goal progress
                if (donation.goalId) {
                    await this.updateGoalProgress(donation.goalId, new Decimal(donation.amount));
                }

                // Broadcast to creator
                if (this.broadcast) {
                    this.broadcast(`earnings-${donation.creatorId}`, {
                        type: 'donation_received',
                        donationId,
                        amount: donation.amount,
                        message: donation.message
                    });
                }

                return { success: true, donationId, paymentId: paymentResult.paymentId };
            } else {
                await this.redis.hset(`donation:${donationId}`, {
                    status: 'failed',
                    error: paymentResult.error
                });
                return { success: false, error: paymentResult.error };
            }
        } catch (error) {
            this.logger.error('Error processing donation:', error);
            throw error;
        }
    }

    async processDonationPayment(amount, paymentDetails) {
        await new Promise(resolve => setTimeout(resolve, 800));
        return {
            success: Math.random() > 0.03,
            paymentId: `don_pay_${uuidv4()}`,
            transactionId: `don_txn_${uuidv4()}`
        };
    }

    async updateGoalProgress(goalId, amount) {
        const current = await this.redis.get(`goal_progress:${goalId}`) || '0';
        const newTotal = new Decimal(current).add(amount);
        await this.redis.set(`goal_progress:${goalId}`, newTotal.toString());
    }

    async getStats() {
        try {
            const donationKeys = await this.redis.keys('donation:*');
            let totalAmount = new Decimal('0');
            let completedCount = 0;
            const typeStats = {};

            for (const key of donationKeys) {
                const donation = await this.redis.hgetall(key);
                if (donation.status === 'completed') {
                    completedCount++;
                    totalAmount = totalAmount.add(new Decimal(donation.amount || '0'));
                    typeStats[donation.type] = (typeStats[donation.type] || 0) + 1;
                }
            }

            return {
                totalDonations: donationKeys.length,
                completedDonations: completedCount,
                totalAmount: totalAmount.toString(),
                averageAmount: completedCount > 0 ? totalAmount.div(completedCount).toString() : '0',
                typeStats
            };
        } catch (error) {
            this.logger.error('Error getting donation stats:', error);
            return {};
        }
    }
}