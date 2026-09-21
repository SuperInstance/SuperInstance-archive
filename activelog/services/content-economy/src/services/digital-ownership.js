import { v4 as uuidv4 } from 'uuid';
import Decimal from 'decimal.js';
import crypto from 'crypto';

export class DigitalOwnershipService {
    constructor(redis, logger) {
        this.redis = redis;
        this.logger = logger;
        this.broadcast = null;
        
        // NFT-style ownership without blockchain
        this.ownershipTypes = {
            'unique': {
                name: 'Unique Ownership',
                description: 'One-of-a-kind digital asset',
                transferable: true,
                resellable: true,
                maxSupply: 1
            },
            'limited': {
                name: 'Limited Edition',
                description: 'Limited quantity digital collectible',
                transferable: true,
                resellable: true,
                maxSupply: 100
            },
            'membership': {
                name: 'Membership Token',
                description: 'Access token with special privileges',
                transferable: false,
                resellable: false,
                maxSupply: 1000
            }
        };
    }

    async createDigitalAsset(contentId, creatorId, ownershipType, metadata, supply = 1) {
        try {
            const assetId = uuidv4();
            const timestamp = Date.now();
            
            const assetData = {
                id: assetId,
                contentId,
                creatorId,
                ownershipType,
                metadata: JSON.stringify(metadata),
                totalSupply: supply,
                currentSupply: 0,
                digitalFingerprint: this.generateFingerprint(contentId, assetId, timestamp),
                createdAt: timestamp
            };

            await this.redis.hset(`digital_asset:${assetId}`, assetData);
            await this.redis.sadd(`creator_assets:${creatorId}`, assetId);
            
            return assetData;
        } catch (error) {
            this.logger.error('Error creating digital asset:', error);
            throw error;
        }
    }

    generateFingerprint(contentId, assetId, timestamp) {
        const data = `${contentId}-${assetId}-${timestamp}`;
        return crypto.createHash('sha256').update(data).digest('hex');
    }

    async mintOwnership(assetId, ownerId, paymentDetails) {
        try {
            const asset = await this.redis.hgetall(`digital_asset:${assetId}`);
            if (!asset.id) {
                throw new Error(`Asset not found: ${assetId}`);
            }

            if (parseInt(asset.currentSupply) >= parseInt(asset.totalSupply)) {
                throw new Error('Asset supply exhausted');
            }

            const ownershipId = uuidv4();
            const timestamp = Date.now();
            
            const ownershipData = {
                id: ownershipId,
                assetId,
                ownerId,
                creatorId: asset.creatorId,
                tokenNumber: parseInt(asset.currentSupply) + 1,
                mintedAt: timestamp,
                status: 'active',
                transferHistory: JSON.stringify([{ from: null, to: ownerId, timestamp }])
            };

            await this.redis.hset(`ownership:${ownershipId}`, ownershipData);
            await this.redis.sadd(`owner_assets:${ownerId}`, ownershipId);
            await this.redis.incr(`digital_asset:${assetId}:currentSupply`);
            
            return ownershipData;
        } catch (error) {
            this.logger.error('Error minting ownership:', error);
            throw error;
        }
    }

    async transferOwnership(ownershipId, fromOwnerId, toOwnerId, price = null) {
        try {
            const ownership = await this.redis.hgetall(`ownership:${ownershipId}`);
            if (!ownership.id || ownership.ownerId !== fromOwnerId) {
                throw new Error('Invalid ownership transfer');
            }

            const asset = await this.redis.hgetall(`digital_asset:${ownership.assetId}`);
            const ownershipType = this.ownershipTypes[asset.ownershipType];
            
            if (!ownershipType.transferable) {
                throw new Error('Asset is not transferable');
            }

            const transferHistory = JSON.parse(ownership.transferHistory || '[]');
            transferHistory.push({
                from: fromOwnerId,
                to: toOwnerId,
                timestamp: Date.now(),
                price: price?.toString() || null
            });

            await this.redis.hset(`ownership:${ownershipId}`, {
                ownerId: toOwnerId,
                transferHistory: JSON.stringify(transferHistory),
                lastTransferAt: Date.now()
            });

            // Update owner indexes
            await this.redis.srem(`owner_assets:${fromOwnerId}`, ownershipId);
            await this.redis.sadd(`owner_assets:${toOwnerId}`, ownershipId);
            
            return { success: true, transferId: uuidv4() };
        } catch (error) {
            this.logger.error('Error transferring ownership:', error);
            throw error;
        }
    }

    async verifyOwnership(ownershipId, ownerId) {
        const ownership = await this.redis.hgetall(`ownership:${ownershipId}`);
        return ownership.ownerId === ownerId && ownership.status === 'active';
    }

    async getAssetHistory(assetId) {
        const ownershipIds = await this.redis.keys(`ownership:*`);
        const history = [];
        
        for (const key of ownershipIds) {
            const ownership = await this.redis.hgetall(key);
            if (ownership.assetId === assetId) {
                const transferHistory = JSON.parse(ownership.transferHistory || '[]');
                history.push({ ownership, transfers: transferHistory });
            }
        }
        
        return history;
    }

    async getStats() {
        const assetKeys = await this.redis.keys('digital_asset:*');
        const ownershipKeys = await this.redis.keys('ownership:*');
        
        let totalValue = new Decimal('0');
        const typeStats = {};
        
        for (const key of assetKeys) {
            const asset = await this.redis.hgetall(key);
            typeStats[asset.ownershipType] = (typeStats[asset.ownershipType] || 0) + 1;
        }
        
        return {
            totalAssets: assetKeys.length,
            totalOwnerships: ownershipKeys.length,
            typeDistribution: typeStats,
            totalMarketValue: totalValue.toString()
        };
    }
}