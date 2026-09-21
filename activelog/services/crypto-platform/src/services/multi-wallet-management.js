import { ethers } from 'ethers';
import Web3 from 'web3';
import { Connection, PublicKey, Keypair, LAMPORTS_PER_SOL } from '@solana/web3.js';
import bitcoin from 'bitcoinjs-lib';
import bip39 from 'bip39';
import HDKey from 'hdkey';
import { Decimal } from 'decimal.js';
import crypto from 'crypto';

class MultiWalletManager {
    constructor(redisClient) {
        this.redis = redisClient;
        this.providers = {
            ethereum: new ethers.JsonRpcProvider(process.env.ETHEREUM_RPC_URL || 'https://mainnet.infura.io/v3/YOUR-PROJECT-ID'),
            polygon: new ethers.JsonRpcProvider(process.env.POLYGON_RPC_URL || 'https://polygon-rpc.com'),
            bsc: new ethers.JsonRpcProvider(process.env.BSC_RPC_URL || 'https://bsc-dataseed.binance.org'),
            solana: new Connection(process.env.SOLANA_RPC_URL || 'https://api.mainnet-beta.solana.com'),
            bitcoin: process.env.BITCOIN_RPC_URL || 'https://blockstream.info/api'
        };
        
        this.supportedNetworks = {
            ethereum: { chainId: 1, name: 'Ethereum', symbol: 'ETH', decimals: 18 },
            polygon: { chainId: 137, name: 'Polygon', symbol: 'MATIC', decimals: 18 },
            bsc: { chainId: 56, name: 'Binance Smart Chain', symbol: 'BNB', decimals: 18 },
            solana: { chainId: 'solana-mainnet', name: 'Solana', symbol: 'SOL', decimals: 9 },
            bitcoin: { chainId: 'bitcoin-mainnet', name: 'Bitcoin', symbol: 'BTC', decimals: 8 }
        };
    }

    // Generate new wallet with mnemonic
    async generateWallet(userId, walletName = 'Default Wallet') {
        try {
            const mnemonic = bip39.generateMnemonic();
            const seed = bip39.mnemonicToSeedSync(mnemonic);
            const masterKey = HDKey.fromMasterSeed(seed);
            
            const walletId = crypto.randomUUID();
            const encryptedMnemonic = this.encrypt(mnemonic);
            
            // Generate addresses for different networks
            const addresses = await this.generateAddressesFromSeed(seed);
            
            const walletData = {
                walletId,
                userId,
                name: walletName,
                encryptedMnemonic,
                addresses,
                createdAt: new Date().toISOString(),
                isActive: true,
                balance: {}
            };
            
            await this.redis.hSet(`wallet:${walletId}`, walletData);
            await this.redis.sAdd(`user:${userId}:wallets`, walletId);
            
            return {
                walletId,
                name: walletName,
                addresses: this.sanitizeAddresses(addresses),
                mnemonic // Only return once for backup
            };
        } catch (error) {
            throw new Error(`Failed to generate wallet: ${error.message}`);
        }
    }

    // Generate addresses for all supported networks
    async generateAddressesFromSeed(seed) {
        const addresses = {};
        
        try {
            // Ethereum-based networks (Ethereum, Polygon, BSC)
            const ethWallet = ethers.Wallet.fromMnemonic(bip39.entropyToMnemonic(seed.slice(0, 16)));
            addresses.ethereum = ethWallet.address;
            addresses.polygon = ethWallet.address;
            addresses.bsc = ethWallet.address;
            
            // Solana
            const solanaKeypair = Keypair.fromSeed(seed.slice(0, 32));
            addresses.solana = solanaKeypair.publicKey.toString();
            
            // Bitcoin
            const bitcoinKey = HDKey.fromMasterSeed(seed).derive("m/44'/0'/0'/0/0");
            const { address } = bitcoin.payments.p2pkh({ 
                pubkey: bitcoinKey.publicKey,
                network: bitcoin.networks.bitcoin
            });
            addresses.bitcoin = address;
            
            return addresses;
        } catch (error) {
            throw new Error(`Failed to generate addresses: ${error.message}`);
        }
    }

    // Import wallet from mnemonic
    async importWallet(userId, mnemonic, walletName = 'Imported Wallet') {
        try {
            if (!bip39.validateMnemonic(mnemonic)) {
                throw new Error('Invalid mnemonic phrase');
            }
            
            const seed = bip39.mnemonicToSeedSync(mnemonic);
            const walletId = crypto.randomUUID();
            const encryptedMnemonic = this.encrypt(mnemonic);
            
            const addresses = await this.generateAddressesFromSeed(seed);
            
            const walletData = {
                walletId,
                userId,
                name: walletName,
                encryptedMnemonic,
                addresses,
                createdAt: new Date().toISOString(),
                isActive: true,
                imported: true,
                balance: {}
            };
            
            await this.redis.hSet(`wallet:${walletId}`, walletData);
            await this.redis.sAdd(`user:${userId}:wallets`, walletId);
            
            return {
                walletId,
                name: walletName,
                addresses: this.sanitizeAddresses(addresses)
            };
        } catch (error) {
            throw new Error(`Failed to import wallet: ${error.message}`);
        }
    }

    // Get wallet balances across all networks
    async getWalletBalances(walletId) {
        try {
            const walletData = await this.redis.hGetAll(`wallet:${walletId}`);
            if (!walletData.addresses) {
                throw new Error('Wallet not found');
            }
            
            const addresses = JSON.parse(walletData.addresses);
            const balances = {};
            
            // Get Ethereum balance
            const ethBalance = await this.providers.ethereum.getBalance(addresses.ethereum);
            balances.ethereum = {
                address: addresses.ethereum,
                balance: ethers.formatEther(ethBalance),
                symbol: 'ETH',
                usdValue: await this.getUSDValue('ethereum', ethers.formatEther(ethBalance))
            };
            
            // Get Polygon balance
            const polygonBalance = await this.providers.polygon.getBalance(addresses.polygon);
            balances.polygon = {
                address: addresses.polygon,
                balance: ethers.formatEther(polygonBalance),
                symbol: 'MATIC',
                usdValue: await this.getUSDValue('matic-network', ethers.formatEther(polygonBalance))
            };
            
            // Get BSC balance
            const bscBalance = await this.providers.bsc.getBalance(addresses.bsc);
            balances.bsc = {
                address: addresses.bsc,
                balance: ethers.formatEther(bscBalance),
                symbol: 'BNB',
                usdValue: await this.getUSDValue('binancecoin', ethers.formatEther(bscBalance))
            };
            
            // Get Solana balance
            const solanaBalance = await this.providers.solana.getBalance(new PublicKey(addresses.solana));
            balances.solana = {
                address: addresses.solana,
                balance: (solanaBalance / LAMPORTS_PER_SOL).toString(),
                symbol: 'SOL',
                usdValue: await this.getUSDValue('solana', (solanaBalance / LAMPORTS_PER_SOL).toString())
            };
            
            // Get Bitcoin balance (simplified)
            balances.bitcoin = {
                address: addresses.bitcoin,
                balance: '0.00000000', // Would need proper Bitcoin API integration
                symbol: 'BTC',
                usdValue: 0
            };
            
            // Update cached balances
            await this.redis.hSet(`wallet:${walletId}`, 'balance', JSON.stringify(balances));
            await this.redis.hSet(`wallet:${walletId}`, 'lastBalanceUpdate', new Date().toISOString());
            
            return balances;
        } catch (error) {
            throw new Error(`Failed to get wallet balances: ${error.message}`);
        }
    }

    // Get token balances for ERC-20/BEP-20 tokens
    async getTokenBalances(walletId, network) {
        try {
            const walletData = await this.redis.hGetAll(`wallet:${walletId}`);
            const addresses = JSON.parse(walletData.addresses);
            const address = addresses[network];
            
            if (!address) {
                throw new Error('Address not found for network');
            }
            
            const provider = this.providers[network];
            const tokenBalances = [];
            
            // Common tokens to check (would be configurable)
            const commonTokens = {
                ethereum: [
                    { address: '0xA0b86a33E6741be32d01Ba9b94c7b6b7Ae0D91B0', symbol: 'USDC', decimals: 6 },
                    { address: '0xdAC17F958D2ee523a2206206994597C13D831ec7', symbol: 'USDT', decimals: 6 },
                    { address: '0x6B175474E89094C44Da98b954EedeAC495271d0F', symbol: 'DAI', decimals: 18 }
                ],
                bsc: [
                    { address: '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d', symbol: 'USDC', decimals: 18 },
                    { address: '0x55d398326f99059fF775485246999027B3197955', symbol: 'USDT', decimals: 18 }
                ],
                polygon: [
                    { address: '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174', symbol: 'USDC', decimals: 6 },
                    { address: '0xc2132D05D31c914a87C6611C10748AEb04B58e8F', symbol: 'USDT', decimals: 6 }
                ]
            };
            
            const tokens = commonTokens[network] || [];
            
            for (const token of tokens) {
                try {
                    const contract = new ethers.Contract(
                        token.address,
                        ['function balanceOf(address) view returns (uint256)'],
                        provider
                    );
                    
                    const balance = await contract.balanceOf(address);
                    const formattedBalance = ethers.formatUnits(balance, token.decimals);
                    
                    if (new Decimal(formattedBalance).gt(0)) {
                        tokenBalances.push({
                            symbol: token.symbol,
                            address: token.address,
                            balance: formattedBalance,
                            decimals: token.decimals,
                            usdValue: await this.getUSDValue(token.symbol.toLowerCase(), formattedBalance)
                        });
                    }
                } catch (tokenError) {
                    console.error(`Error getting balance for token ${token.symbol}:`, tokenError);
                }
            }
            
            return tokenBalances;
        } catch (error) {
            throw new Error(`Failed to get token balances: ${error.message}`);
        }
    }

    // Send transaction
    async sendTransaction(walletId, toAddress, amount, network, tokenAddress = null) {
        try {
            const walletData = await this.redis.hGetAll(`wallet:${walletId}`);
            const mnemonic = this.decrypt(walletData.encryptedMnemonic);
            const addresses = JSON.parse(walletData.addresses);
            
            let txHash;
            
            switch (network) {
                case 'ethereum':
                case 'polygon':
                case 'bsc':
                    txHash = await this.sendEthereumTransaction(
                        mnemonic, addresses[network], toAddress, amount, network, tokenAddress
                    );
                    break;
                    
                case 'solana':
                    txHash = await this.sendSolanaTransaction(
                        mnemonic, addresses.solana, toAddress, amount
                    );
                    break;
                    
                case 'bitcoin':
                    txHash = await this.sendBitcoinTransaction(
                        mnemonic, addresses.bitcoin, toAddress, amount
                    );
                    break;
                    
                default:
                    throw new Error('Unsupported network');
            }
            
            // Log transaction
            const transactionData = {
                walletId,
                txHash,
                from: addresses[network],
                to: toAddress,
                amount,
                network,
                tokenAddress,
                timestamp: new Date().toISOString(),
                status: 'pending'
            };
            
            await this.redis.hSet(`transaction:${txHash}`, transactionData);
            await this.redis.lPush(`wallet:${walletId}:transactions`, txHash);
            
            return {
                txHash,
                status: 'pending',
                network,
                amount,
                to: toAddress
            };
        } catch (error) {
            throw new Error(`Failed to send transaction: ${error.message}`);
        }
    }

    // Send Ethereum-based transaction
    async sendEthereumTransaction(mnemonic, fromAddress, toAddress, amount, network, tokenAddress) {
        const provider = this.providers[network];
        const wallet = ethers.Wallet.fromMnemonic(mnemonic).connect(provider);
        
        if (tokenAddress) {
            // Token transfer
            const contract = new ethers.Contract(
                tokenAddress,
                ['function transfer(address to, uint256 amount) returns (bool)'],
                wallet
            );
            
            const tx = await contract.transfer(toAddress, ethers.parseEther(amount));
            return tx.hash;
        } else {
            // Native token transfer
            const tx = await wallet.sendTransaction({
                to: toAddress,
                value: ethers.parseEther(amount)
            });
            return tx.hash;
        }
    }

    // Send Solana transaction
    async sendSolanaTransaction(mnemonic, fromAddress, toAddress, amount) {
        // Simplified Solana transaction - would need proper implementation
        throw new Error('Solana transactions not fully implemented');
    }

    // Send Bitcoin transaction
    async sendBitcoinTransaction(mnemonic, fromAddress, toAddress, amount) {
        // Simplified Bitcoin transaction - would need proper implementation
        throw new Error('Bitcoin transactions not fully implemented');
    }

    // Get transaction history
    async getTransactionHistory(walletId, limit = 50) {
        try {
            const txHashes = await this.redis.lRange(`wallet:${walletId}:transactions`, 0, limit - 1);
            const transactions = [];
            
            for (const txHash of txHashes) {
                const txData = await this.redis.hGetAll(`transaction:${txHash}`);
                if (txData.txHash) {
                    transactions.push(txData);
                }
            }
            
            return transactions;
        } catch (error) {
            throw new Error(`Failed to get transaction history: ${error.message}`);
        }
    }

    // Get user's wallets
    async getUserWallets(userId) {
        try {
            const walletIds = await this.redis.sMembers(`user:${userId}:wallets`);
            const wallets = [];
            
            for (const walletId of walletIds) {
                const walletData = await this.redis.hGetAll(`wallet:${walletId}`);
                if (walletData.walletId) {
                    wallets.push({
                        walletId: walletData.walletId,
                        name: walletData.name,
                        addresses: this.sanitizeAddresses(JSON.parse(walletData.addresses)),
                        createdAt: walletData.createdAt,
                        isActive: walletData.isActive === 'true',
                        imported: walletData.imported === 'true'
                    });
                }
            }
            
            return wallets;
        } catch (error) {
            throw new Error(`Failed to get user wallets: ${error.message}`);
        }
    }

    // Update wallet name
    async updateWalletName(walletId, newName) {
        try {
            await this.redis.hSet(`wallet:${walletId}`, 'name', newName);
            return { success: true, message: 'Wallet name updated' };
        } catch (error) {
            throw new Error(`Failed to update wallet name: ${error.message}`);
        }
    }

    // Delete wallet
    async deleteWallet(walletId, userId) {
        try {
            // Remove from user's wallet list
            await this.redis.sRem(`user:${userId}:wallets`, walletId);
            
            // Delete wallet data
            await this.redis.del(`wallet:${walletId}`);
            
            // Clean up transaction history
            const txHashes = await this.redis.lRange(`wallet:${walletId}:transactions`, 0, -1);
            for (const txHash of txHashes) {
                await this.redis.del(`transaction:${txHash}`);
            }
            await this.redis.del(`wallet:${walletId}:transactions`);
            
            return { success: true, message: 'Wallet deleted successfully' };
        } catch (error) {
            throw new Error(`Failed to delete wallet: ${error.message}`);
        }
    }

    // Utility functions
    encrypt(text) {
        const algorithm = 'aes-256-gcm';
        const secretKey = process.env.WALLET_ENCRYPTION_KEY || 'default-encryption-key-change-in-production';
        const iv = crypto.randomBytes(16);
        const cipher = crypto.createCipher(algorithm, secretKey);
        
        let encrypted = cipher.update(text, 'utf8', 'hex');
        encrypted += cipher.final('hex');
        
        return iv.toString('hex') + ':' + encrypted;
    }

    decrypt(encryptedText) {
        const algorithm = 'aes-256-gcm';
        const secretKey = process.env.WALLET_ENCRYPTION_KEY || 'default-encryption-key-change-in-production';
        const [ivHex, encrypted] = encryptedText.split(':');
        const iv = Buffer.from(ivHex, 'hex');
        const decipher = crypto.createDecipher(algorithm, secretKey);
        
        let decrypted = decipher.update(encrypted, 'hex', 'utf8');
        decrypted += decipher.final('utf8');
        
        return decrypted;
    }

    sanitizeAddresses(addresses) {
        // Remove sensitive information and return only addresses
        return addresses;
    }

    async getUSDValue(coinId, amount) {
        try {
            // Mock USD value calculation - would integrate with CoinGecko API
            const mockPrices = {
                'ethereum': 2500,
                'matic-network': 0.85,
                'binancecoin': 320,
                'solana': 110,
                'bitcoin': 45000,
                'usdc': 1,
                'usdt': 1,
                'dai': 1
            };
            
            const price = mockPrices[coinId] || 0;
            return new Decimal(amount).mul(price).toNumber();
        } catch (error) {
            return 0;
        }
    }

    // Network status check
    async getNetworkStatus() {
        const status = {};
        
        for (const [network, provider] of Object.entries(this.providers)) {
            try {
                if (network === 'solana') {
                    const slot = await provider.getSlot();
                    status[network] = { connected: true, latestBlock: slot };
                } else if (network === 'bitcoin') {
                    status[network] = { connected: true, latestBlock: 'N/A' };
                } else {
                    const blockNumber = await provider.getBlockNumber();
                    status[network] = { connected: true, latestBlock: blockNumber };
                }
            } catch (error) {
                status[network] = { connected: false, error: error.message };
            }
        }
        
        return status;
    }
}

export default MultiWalletManager;