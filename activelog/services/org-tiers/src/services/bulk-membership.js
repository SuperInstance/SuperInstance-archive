import { v4 as uuidv4 } from 'uuid';
import Decimal from 'decimal.js';
import moment from 'moment';

export class BulkMembershipService {
    constructor(redis, logger) {
        this.redis = redis;
        this.logger = logger;
        this.broadcast = null;
    }

    async createBulkInvitation(orgId, inviterUserId, invitations, departmentId = null) {
        try {
            const invitationBatchId = uuidv4();
            const timestamp = Date.now();
            const processed = [];
            
            for (const invitation of invitations) {
                const inviteId = uuidv4();
                const inviteData = {
                    id: inviteId,
                    batchId: invitationBatchId,
                    orgId,
                    departmentId,
                    inviterUserId,
                    email: invitation.email,
                    firstName: invitation.firstName || '',
                    lastName: invitation.lastName || '',
                    role: invitation.role || 'member',
                    permissions: JSON.stringify(invitation.permissions || []),
                    status: 'pending',
                    createdAt: timestamp,
                    expiresAt: timestamp + (7 * 24 * 60 * 60 * 1000) // 7 days
                };
                
                await this.redis.hset(`bulk_invitation:${inviteId}`, inviteData);
                await this.redis.sadd(`org_invitations:${orgId}`, inviteId);
                await this.redis.sadd(`invitation_batch:${invitationBatchId}`, inviteId);
                
                processed.push(inviteData);
            }
            
            const batchData = {
                id: invitationBatchId,
                orgId,
                inviterUserId,
                totalInvitations: invitations.length,
                status: 'sent',
                createdAt: timestamp
            };
            
            await this.redis.hset(`invitation_batch:${invitationBatchId}`, batchData);
            
            // Send invitation emails (mock)
            await this.sendBulkInvitationEmails(processed);
            
            return { batchId: invitationBatchId, invitations: processed };
        } catch (error) {
            this.logger.error('Error creating bulk invitation:', error);
            throw error;
        }
    }

    async acceptInvitation(inviteId, userData) {
        const invitation = await this.redis.hgetall(`bulk_invitation:${inviteId}`);
        if (!invitation.id || invitation.status !== 'pending') {
            throw new Error('Invalid or expired invitation');
        }
        
        // Create user account and add to organization
        const userId = await this.createUserAccount(userData, invitation);
        
        await this.redis.hset(`bulk_invitation:${inviteId}`, {
            status: 'accepted',
            acceptedAt: Date.now(),
            userId
        });
        
        return { userId, orgId: invitation.orgId };
    }

    async createUserAccount(userData, invitation) {
        const userId = uuidv4();
        // Mock user creation - integrate with actual user service
        return userId;
    }

    async sendBulkInvitationEmails(invitations) {
        // Mock email sending
        this.logger.info(`Sent ${invitations.length} bulk invitation emails`);
    }

    async getBulkInvitationStatus(batchId) {
        const batch = await this.redis.hgetall(`invitation_batch:${batchId}`);
        const inviteIds = await this.redis.smembers(`invitation_batch:${batchId}`);
        
        let accepted = 0, pending = 0, expired = 0;
        
        for (const inviteId of inviteIds) {
            const invite = await this.redis.hgetall(`bulk_invitation:${inviteId}`);
            switch (invite.status) {
                case 'accepted': accepted++; break;
                case 'pending': pending++; break;
                case 'expired': expired++; break;
            }
        }
        
        return {
            ...batch,
            stats: { accepted, pending, expired, total: inviteIds.length }
        };
    }

    async getStats() {
        const batchKeys = await this.redis.keys('invitation_batch:*');
        let totalInvitations = 0, totalAccepted = 0;
        
        for (const key of batchKeys) {
            const batch = await this.redis.hgetall(key);
            totalInvitations += parseInt(batch.totalInvitations || 0);
        }
        
        const inviteKeys = await this.redis.keys('bulk_invitation:*');
        for (const key of inviteKeys) {
            const invite = await this.redis.hgetall(key);
            if (invite.status === 'accepted') totalAccepted++;
        }
        
        return {
            totalBatches: batchKeys.length,
            totalInvitations,
            totalAccepted,
            acceptanceRate: totalInvitations > 0 ? ((totalAccepted / totalInvitations) * 100).toFixed(1) : '0'
        };
    }
}