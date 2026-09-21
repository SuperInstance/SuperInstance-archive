import { ethers } from 'ethers';
import { Decimal } from 'decimal.js';
import axios from 'axios';

class NFTMarketplaceConnector {
    constructor(redisClient) {
        this.redis = redisClient;
        this.providers = {
            ethereum: new ethers.JsonRpcProvider(process.env.ETHEREUM_RPC_URL),
            polygon: new ethers.JsonRpcProvider(process.env.POLYGON_RPC_URL)
        };

        // Marketplace contracts and APIs
        this.marketplaces = {
            opensea: {
                name: 'OpenSea',
                apiUrl: 'https://api.opensea.io/api/v1',
                supported_networks: ['ethereum', 'polygon'],
                fee_percentage: 2.5
            },
            rarible: {
                name: 'Rarible',
                apiUrl: 'https://api.rarible.org/v0.1',
                supported_networks: ['ethereum', 'polygon'],
                fee_percentage: 2.5
            },
            looksrare: {
                name: 'LooksRare',
                apiUrl: 'https://api.looksrare.org/api/v1',
                supported_networks: ['ethereum'],
                fee_percentage: 2.0
            },
            foundation: {
                name: 'Foundation',
                apiUrl: 'https://api.foundation.app/v1',
                supported_networks: ['ethereum'],
                fee_percentage: 15.0
            }
        };

        // Standard NFT contract ABIs
        this.contractABIs = {
            ERC721: [
                'function ownerOf(uint256 tokenId) view returns (address)',
                'function tokenURI(uint256 tokenId) view returns (string)',
                'function approve(address to, uint256 tokenId)',
                'function getApproved(uint256 tokenId) view returns (address)',
                'function setApprovalForAll(address operator, bool approved)',
                'function isApprovedForAll(address owner, address operator) view returns (bool)',
                'function safeTransferFrom(address from, address to, uint256 tokenId)',
                'function balanceOf(address owner) view returns (uint256)',
                'function totalSupply() view returns (uint256)',
                'function name() view returns (string)',
                'function symbol() view returns (string)'
            ],
            ERC1155: [
                'function balanceOf(address account, uint256 id) view returns (uint256)',
                'function balanceOfBatch(address[] accounts, uint256[] ids) view returns (uint256[])',
                'function setApprovalForAll(address operator, bool approved)',
                'function isApprovedForAll(address account, address operator) view returns (bool)',
                'function safeTransferFrom(address from, address to, uint256 id, uint256 amount, bytes data)',
                'function safeBatchTransferFrom(address from, address to, uint256[] ids, uint256[] amounts, bytes data)',
                'function uri(uint256 id) view returns (string)'
            ]
        };
    }

    // Get user's NFT collection across marketplaces
    async getUserNFTCollection(userAddress, networks = ['ethereum', 'polygon']) {
        try {
            const collection = {
                owned: [],
                listed: [],
                totalValue: new Decimal(0),
                collections: new Map(),
                marketplaceBreakdown: {}
            };

            for (const network of networks) {
                try {
                    // Get NFTs from different marketplaces
                    const openSeaNFTs = await this.getOpenSeaNFTs(userAddress, network);
                    const raribleNFTs = await this.getRaribleNFTs(userAddress, network);

                    // Combine and deduplicate NFTs
                    const allNFTs = this.deduplicateNFTs([...openSeaNFTs, ...raribleNFTs]);

                    for (const nft of allNFTs) {
                        // Enrich NFT with additional data
                        const enrichedNFT = await this.enrichNFTData(nft, network);
                        
                        if (enrichedNFT.owner?.toLowerCase() === userAddress.toLowerCase()) {
                            collection.owned.push(enrichedNFT);
                        }

                        if (enrichedNFT.isListed) {
                            collection.listed.push(enrichedNFT);
                        }

                        // Update collection stats
                        const collectionKey = `${enrichedNFT.contractAddress}_${network}`;
                        if (!collection.collections.has(collectionKey)) {
                            collection.collections.set(collectionKey, {
                                name: enrichedNFT.collectionName,
                                contractAddress: enrichedNFT.contractAddress,
                                network,
                                count: 0,
                                floorPrice: null,
                                totalValue: new Decimal(0)
                            });
                        }

                        const collectionData = collection.collections.get(collectionKey);
                        collectionData.count += 1;
                        if (enrichedNFT.price) {
                            collectionData.totalValue = collectionData.totalValue.plus(enrichedNFT.price);
                        }
                    }
                } catch (networkError) {
                    console.error(`Error fetching NFTs for ${network}:`, networkError);
                }
            }

            // Calculate total portfolio value
            collection.totalValue = collection.owned.reduce(
                (sum, nft) => sum.plus(nft.estimatedValue || 0),
                new Decimal(0)
            );

            // Convert Map to Array for response
            collection.collections = Array.from(collection.collections.values());

            // Cache results
            await this.redis.setEx(
                `nft:collection:${userAddress}`,
                600, // 10 minutes cache
                JSON.stringify(collection, this.decimalReplacer)
            );

            return collection;
        } catch (error) {
            throw new Error(`Failed to get NFT collection: ${error.message}`);
        }
    }

    // Get NFTs from OpenSea API
    async getOpenSeaNFTs(ownerAddress, network) {
        try {
            const apiKey = process.env.OPENSEA_API_KEY;
            const chainParam = network === 'polygon' ? 'matic' : 'ethereum';
            
            const response = await axios.get(`${this.marketplaces.opensea.apiUrl}/assets`, {
                params: {
                    owner: ownerAddress,
                    chain: chainParam,
                    limit: 200
                },
                headers: apiKey ? { 'X-API-KEY': apiKey } : {}
            });

            return response.data.assets.map(asset => ({
                tokenId: asset.token_id,
                contractAddress: asset.asset_contract.address,
                name: asset.name,
                description: asset.description,
                imageUrl: asset.image_url,
                animationUrl: asset.animation_url,
                externalUrl: asset.external_link,
                owner: ownerAddress,
                collectionName: asset.collection.name,
                collectionSlug: asset.collection.slug,
                contractType: asset.asset_contract.schema_name,
                network,
                marketplace: 'opensea',
                lastSale: asset.last_sale ? {
                    price: ethers.formatEther(asset.last_sale.total_price),
                    currency: asset.last_sale.payment_token.symbol,
                    date: asset.last_sale.event_timestamp
                } : null,
                traits: asset.traits || [],
                rarityRank: null,
                isListed: false
            }));
        } catch (error) {
            console.error('Error fetching OpenSea NFTs:', error);
            return [];
        }
    }

    // Get NFTs from Rarible API
    async getRaribleNFTs(ownerAddress, network) {
        try {
            const chainParam = network === 'polygon' ? 'POLYGON' : 'ETHEREUM';
            
            const response = await axios.get(`${this.marketplaces.rarible.apiUrl}/items/byOwner`, {
                params: {
                    owner: `${chainParam}:${ownerAddress}`,
                    size: 1000
                }
            });

            return response.data.items.map(item => ({
                tokenId: item.tokenId,
                contractAddress: item.contract,
                name: item.meta?.name,
                description: item.meta?.description,
                imageUrl: item.meta?.image,
                animationUrl: item.meta?.animation_url,
                externalUrl: item.meta?.external_url,
                owner: ownerAddress,
                collectionName: item.meta?.collection,
                contractType: 'ERC721', // Rarible API doesn't always specify
                network,
                marketplace: 'rarible',
                traits: item.meta?.attributes || [],
                rarityRank: null,
                isListed: false
            }));
        } catch (error) {
            console.error('Error fetching Rarible NFTs:', error);
            return [];
        }
    }

    // Enrich NFT data with additional information
    async enrichNFTData(nft, network) {
        try {
            // Get floor price and collection stats
            const collectionStats = await this.getCollectionStats(nft.collectionSlug || nft.contractAddress, network);
            
            // Estimate NFT value based on floor price and rarity
            let estimatedValue = collectionStats.floorPrice || 0;
            if (nft.rarityRank && nft.rarityRank < 100) {
                // Premium for rare NFTs
                estimatedValue *= (1 + (100 - nft.rarityRank) / 100);
            }

            // Check if NFT is currently listed
            const listingInfo = await this.checkNFTListings(nft.contractAddress, nft.tokenId, network);

            return {
                ...nft,
                floorPrice: collectionStats.floorPrice,
                estimatedValue,
                volumeTraded: collectionStats.volumeTraded,
                isListed: listingInfo.isListed,
                currentListing: listingInfo.listing,
                marketplaceUrl: this.generateMarketplaceUrl(nft, network)
            };
        } catch (error) {
            console.error('Error enriching NFT data:', error);
            return nft;
        }
    }

    // Get collection statistics
    async getCollectionStats(collectionIdentifier, network) {
        try {
            // Try to get from cache first
            const cacheKey = `collection:stats:${collectionIdentifier}:${network}`;
            const cached = await this.redis.get(cacheKey);
            if (cached) {
                return JSON.parse(cached);
            }

            // Get stats from OpenSea
            const stats = await this.getOpenSeaCollectionStats(collectionIdentifier);
            
            // Cache for 1 hour
            await this.redis.setEx(cacheKey, 3600, JSON.stringify(stats));
            
            return stats;
        } catch (error) {
            console.error('Error getting collection stats:', error);
            return { floorPrice: 0, volumeTraded: 0 };
        }
    }

    // Get OpenSea collection statistics
    async getOpenSeaCollectionStats(collectionSlug) {
        try {
            const response = await axios.get(`${this.marketplaces.opensea.apiUrl}/collection/${collectionSlug}/stats`);
            const stats = response.data.stats;
            
            return {
                floorPrice: parseFloat(stats.floor_price || 0),
                totalVolume: parseFloat(stats.total_volume || 0),
                volumeTraded: parseFloat(stats.one_day_volume || 0),
                averagePrice: parseFloat(stats.average_price || 0),
                totalSupply: parseInt(stats.total_supply || 0),
                numOwners: parseInt(stats.num_owners || 0)
            };
        } catch (error) {
            console.error('Error getting OpenSea collection stats:', error);
            return { floorPrice: 0, volumeTraded: 0 };
        }
    }

    // Check if NFT is listed on marketplaces
    async checkNFTListings(contractAddress, tokenId, network) {
        try {
            // Check OpenSea listings
            const openSeaListing = await this.getOpenSeaListing(contractAddress, tokenId, network);
            
            return {
                isListed: openSeaListing !== null,
                listing: openSeaListing
            };
        } catch (error) {
            console.error('Error checking NFT listings:', error);
            return { isListed: false, listing: null };
        }
    }

    // Get OpenSea listing for specific NFT
    async getOpenSeaListing(contractAddress, tokenId, network) {
        try {
            const chainParam = network === 'polygon' ? 'matic' : 'ethereum';
            
            const response = await axios.get(`${this.marketplaces.opensea.apiUrl}/asset/${contractAddress}/${tokenId}/listings`, {
                params: { chain: chainParam }
            });

            if (response.data.listings && response.data.listings.length > 0) {
                const listing = response.data.listings[0];
                return {
                    marketplace: 'opensea',
                    price: ethers.formatEther(listing.current_price),
                    currency: listing.payment_token_contract.symbol,
                    expirationTime: listing.expiration_time,
                    listingUrl: `https://opensea.io/assets/${contractAddress}/${tokenId}`
                };
            }

            return null;
        } catch (error) {
            console.error('Error getting OpenSea listing:', error);
            return null;
        }
    }

    // Create NFT listing
    async createNFTListing(walletId, nftData, listingData) {
        try {
            const {
                contractAddress,
                tokenId,
                price,
                currency = 'ETH',
                marketplace = 'opensea',
                duration = 7 // days
            } = listingData;

            // Verify NFT ownership
            const isOwner = await this.verifyNFTOwnership(contractAddress, tokenId, walletId);
            if (!isOwner) {
                throw new Error('You do not own this NFT');
            }

            // Check if NFT is approved for marketplace
            const isApproved = await this.checkNFTApproval(contractAddress, tokenId, marketplace);
            if (!isApproved) {
                // Return approval transaction details
                return {
                    requiresApproval: true,
                    approvalTransaction: await this.generateApprovalTransaction(contractAddress, marketplace)
                };
            }

            // Generate listing transaction
            const listingTransaction = await this.generateListingTransaction({
                contractAddress,
                tokenId,
                price,
                currency,
                marketplace,
                duration
            });

            // Store listing intent
            const listingId = crypto.randomUUID();
            await this.redis.hSet(`listing:${listingId}`, {
                listingId,
                walletId,
                contractAddress,
                tokenId,
                price,
                currency,
                marketplace,
                status: 'pending_approval',
                createdAt: new Date().toISOString()
            });

            return {
                listingId,
                requiresApproval: false,
                listingTransaction
            };
        } catch (error) {
            throw new Error(`Failed to create NFT listing: ${error.message}`);
        }
    }

    // Cancel NFT listing
    async cancelNFTListing(walletId, contractAddress, tokenId, marketplace) {
        try {
            // Generate cancellation transaction
            const cancelTransaction = await this.generateCancelTransaction({
                contractAddress,
                tokenId,
                marketplace
            });

            return { cancelTransaction };
        } catch (error) {
            throw new Error(`Failed to cancel NFT listing: ${error.message}`);
        }
    }

    // Get NFT price history
    async getNFTPriceHistory(contractAddress, tokenId, network) {
        try {
            const cacheKey = `nft:history:${contractAddress}:${tokenId}:${network}`;
            const cached = await this.redis.get(cacheKey);
            if (cached) {
                return JSON.parse(cached);
            }

            // Get sales history from OpenSea
            const history = await this.getOpenSeaSalesHistory(contractAddress, tokenId, network);
            
            // Cache for 30 minutes
            await this.redis.setEx(cacheKey, 1800, JSON.stringify(history));
            
            return history;
        } catch (error) {
            throw new Error(`Failed to get NFT price history: ${error.message}`);
        }
    }

    // Get OpenSea sales history
    async getOpenSeaSalesHistory(contractAddress, tokenId, network) {
        try {
            const chainParam = network === 'polygon' ? 'matic' : 'ethereum';
            
            const response = await axios.get(`${this.marketplaces.opensea.apiUrl}/events`, {
                params: {
                    asset_contract_address: contractAddress,
                    token_id: tokenId,
                    event_type: 'successful',
                    chain: chainParam,
                    limit: 50
                }
            });

            return response.data.asset_events.map(event => ({
                price: ethers.formatEther(event.total_price),
                currency: event.payment_token.symbol,
                date: event.created_date,
                from: event.seller?.address,
                to: event.winner_account?.address,
                transactionHash: event.transaction?.transaction_hash,
                marketplace: 'opensea'
            }));
        } catch (error) {
            console.error('Error getting OpenSea sales history:', error);
            return [];
        }
    }

    // Bulk operations
    async bulkListNFTs(walletId, nfts, listingConfig) {
        const results = [];
        
        for (const nft of nfts) {
            try {
                const result = await this.createNFTListing(walletId, nft, {
                    ...listingConfig,
                    contractAddress: nft.contractAddress,
                    tokenId: nft.tokenId
                });
                results.push({ ...nft, result, success: true });
            } catch (error) {
                results.push({ ...nft, error: error.message, success: false });
            }
        }
        
        return results;
    }

    // NFT analytics and insights
    async getNFTAnalytics(userAddress, timeframe = '30d') {
        try {
            const analytics = {
                portfolioValue: new Decimal(0),
                totalNFTs: 0,
                collections: 0,
                topCollections: [],
                recentActivity: [],
                profitLoss: new Decimal(0),
                floorPriceChanges: []
            };

            const collection = await this.getUserNFTCollection(userAddress);
            
            analytics.portfolioValue = collection.totalValue;
            analytics.totalNFTs = collection.owned.length;
            analytics.collections = collection.collections.length;

            // Sort collections by value
            analytics.topCollections = collection.collections
                .sort((a, b) => b.totalValue - a.totalValue)
                .slice(0, 5);

            return analytics;
        } catch (error) {
            throw new Error(`Failed to get NFT analytics: ${error.message}`);
        }
    }

    // Rarity analysis
    async analyzeNFTRarity(contractAddress, tokenId, network) {
        try {
            // Get NFT metadata and traits
            const metadata = await this.getNFTMetadata(contractAddress, tokenId, network);
            if (!metadata.traits) {
                return { rarityScore: 0, rank: null, percentile: null };
            }

            // Get collection trait statistics
            const traitStats = await this.getCollectionTraitStats(contractAddress, network);
            
            // Calculate rarity score
            let rarityScore = 0;
            for (const trait of metadata.traits) {
                const traitRarity = traitStats[trait.trait_type]?.[trait.value];
                if (traitRarity) {
                    rarityScore += 1 / (traitRarity.count / traitStats.totalSupply);
                }
            }

            return {
                rarityScore,
                rank: null, // Would need full collection analysis
                percentile: null,
                traitBreakdown: metadata.traits.map(trait => ({
                    ...trait,
                    rarity: traitStats[trait.trait_type]?.[trait.value]?.count || 0,
                    percentage: ((traitStats[trait.trait_type]?.[trait.value]?.count || 0) / traitStats.totalSupply) * 100
                }))
            };
        } catch (error) {
            throw new Error(`Failed to analyze NFT rarity: ${error.message}`);
        }
    }

    // Utility functions
    deduplicateNFTs(nfts) {
        const seen = new Set();
        return nfts.filter(nft => {
            const key = `${nft.contractAddress}:${nft.tokenId}:${nft.network}`;
            if (seen.has(key)) {
                return false;
            }
            seen.add(key);
            return true;
        });
    }

    generateMarketplaceUrl(nft, network) {
        const chainParam = network === 'polygon' ? 'matic' : 'ethereum';
        return `https://opensea.io/assets/${chainParam}/${nft.contractAddress}/${nft.tokenId}`;
    }

    async verifyNFTOwnership(contractAddress, tokenId, walletId) {
        // Would need to verify ownership on-chain
        return true; // Simplified
    }

    async checkNFTApproval(contractAddress, tokenId, marketplace) {
        // Would check if NFT is approved for marketplace contract
        return false; // Simplified - would require approval
    }

    async generateApprovalTransaction(contractAddress, marketplace) {
        // Generate approval transaction data
        return {
            to: contractAddress,
            data: '0x', // Encoded approval function call
            value: '0'
        };
    }

    async generateListingTransaction(listingData) {
        // Generate marketplace listing transaction
        return {
            to: this.getMarketplaceContract(listingData.marketplace),
            data: '0x', // Encoded listing function call
            value: '0'
        };
    }

    async generateCancelTransaction(cancelData) {
        // Generate cancellation transaction
        return {
            to: this.getMarketplaceContract(cancelData.marketplace),
            data: '0x', // Encoded cancel function call
            value: '0'
        };
    }

    getMarketplaceContract(marketplace) {
        const contracts = {
            opensea: '0x7Be8076f4EA4A4AD08075C2508e481d6C946D12b', // OpenSea Seaport
            rarible: '0x9757F2d2b135150BBeb65308D4a91804107cd8D6',
            looksrare: '0x59728544B08AB483533076417FbBB2fD0B17CE3a'
        };
        return contracts[marketplace.toLowerCase()] || contracts.opensea;
    }

    async getNFTMetadata(contractAddress, tokenId, network) {
        // Get NFT metadata from contract or IPFS
        return { traits: [] }; // Simplified
    }

    async getCollectionTraitStats(contractAddress, network) {
        // Get collection-wide trait statistics
        return { totalSupply: 10000 }; // Simplified
    }

    decimalReplacer(key, value) {
        return value instanceof Decimal ? value.toString() : value;
    }
}

export default NFTMarketplaceConnector;