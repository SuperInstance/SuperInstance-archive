import { ethers } from 'ethers';
import { Decimal } from 'decimal.js';
import crypto from 'crypto';
import QRCode from 'qrcode';

class CryptoPaymentGateway {
    constructor(redisClient) {
        this.redis = redisClient;
        this.providers = {
            ethereum: new ethers.JsonRpcProvider(process.env.ETHEREUM_RPC_URL),
            polygon: new ethers.JsonRpcProvider(process.env.POLYGON_RPC_URL),
            bsc: new ethers.JsonRpcProvider(process.env.BSC_RPC_URL)
        };

        // Supported payment tokens
        this.paymentTokens = {
            ethereum: {
                ETH: { address: null, decimals: 18, symbol: 'ETH' },
                USDC: { address: '0xA0b86a33E6741be32d01Ba9b94c7b6b7Ae0D91B0', decimals: 6, symbol: 'USDC' },
                USDT: { address: '0xdAC17F958D2ee523a2206206994597C13D831ec7', decimals: 6, symbol: 'USDT' },
                DAI: { address: '0x6B175474E89094C44Da98b954EedeAC495271d0F', decimals: 18, symbol: 'DAI' }
            },
            polygon: {
                MATIC: { address: null, decimals: 18, symbol: 'MATIC' },
                USDC: { address: '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174', decimals: 6, symbol: 'USDC' },
                USDT: { address: '0xc2132D05D31c914a87C6611C10748AEb04B58e8F', decimals: 6, symbol: 'USDT' }
            },
            bsc: {
                BNB: { address: null, decimals: 18, symbol: 'BNB' },
                USDT: { address: '0x55d398326f99059fF775485246999027B3197955', decimals: 18, symbol: 'USDT' },
                BUSD: { address: '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56', decimals: 18, symbol: 'BUSD' }
            }
        };

        // Merchant wallets for receiving payments
        this.merchantWallets = {
            ethereum: process.env.MERCHANT_ETH_ADDRESS,
            polygon: process.env.MERCHANT_POLYGON_ADDRESS,
            bsc: process.env.MERCHANT_BSC_ADDRESS
        };
    }

    // Create payment request
    async createPaymentRequest(merchantId, paymentData) {
        try {
            const {
                amount,
                currency = 'USD',
                description = '',
                expirationMinutes = 30,
                successUrl,
                cancelUrl,
                webhookUrl,
                metadata = {}
            } = paymentData;

            const paymentId = crypto.randomUUID();
            const expirationTime = new Date(Date.now() + (expirationMinutes * 60 * 1000));

            // Get crypto equivalent amounts for different networks
            const cryptoAmounts = await this.calculateCryptoAmounts(amount, currency);

            const payment = {
                paymentId,
                merchantId,
                amount: new Decimal(amount).toString(),
                currency,
                description,
                cryptoAmounts,
                status: 'pending',
                createdAt: new Date().toISOString(),
                expirationTime: expirationTime.toISOString(),
                successUrl,
                cancelUrl,
                webhookUrl,
                metadata,
                transactions: []
            };

            await this.redis.hSet(`payment:${paymentId}`, payment);
            await this.redis.expire(`payment:${paymentId}`, expirationMinutes * 60);
            await this.redis.lPush(`merchant:${merchantId}:payments`, paymentId);

            return {
                paymentId,
                amount,
                currency,
                cryptoAmounts,
                expirationTime,
                paymentUrl: `${process.env.FRONTEND_URL}/pay/${paymentId}`,
                status: 'pending'
            };
        } catch (error) {
            throw new Error(`Failed to create payment request: ${error.message}`);
        }
    }

    // Calculate crypto amounts for fiat amount
    async calculateCryptoAmounts(fiatAmount, fiatCurrency) {
        try {
            const cryptoAmounts = {};
            const usdAmount = await this.convertToUSD(fiatAmount, fiatCurrency);

            // Get current crypto prices (mock implementation)
            const cryptoPrices = await this.getCryptoPrices();

            for (const [network, tokens] of Object.entries(this.paymentTokens)) {
                cryptoAmounts[network] = {};
                
                for (const [tokenSymbol, tokenInfo] of Object.entries(tokens)) {
                    const price = cryptoPrices[tokenSymbol.toLowerCase()];
                    if (price) {
                        const cryptoAmount = new Decimal(usdAmount).div(price);
                        cryptoAmounts[network][tokenSymbol] = {
                            amount: cryptoAmount.toString(),
                            address: this.merchantWallets[network],
                            tokenAddress: tokenInfo.address,
                            decimals: tokenInfo.decimals,
                            qrCode: await this.generatePaymentQR(
                                this.merchantWallets[network],
                                cryptoAmount.toString(),
                                tokenInfo.address
                            )
                        };
                    }
                }
            }

            return cryptoAmounts;
        } catch (error) {
            throw new Error(`Failed to calculate crypto amounts: ${error.message}`);
        }
    }

    // Generate payment QR code
    async generatePaymentQR(address, amount, tokenAddress = null) {
        try {
            let paymentUri;
            
            if (tokenAddress) {
                // ERC-20 token payment
                paymentUri = `ethereum:${tokenAddress}@1/transfer?address=${address}&uint256=${amount}`;
            } else {
                // Native token payment
                paymentUri = `ethereum:${address}@1?value=${amount}`;
            }

            return await QRCode.toDataURL(paymentUri);
        } catch (error) {
            console.error('Failed to generate QR code:', error);
            return null;
        }
    }

    // Process incoming payment
    async processPayment(paymentId, transactionHash, network) {
        try {
            const payment = await this.redis.hGetAll(`payment:${paymentId}`);
            if (!payment.paymentId) {
                throw new Error('Payment not found');
            }

            if (payment.status !== 'pending') {
                throw new Error('Payment already processed');
            }

            // Verify transaction on blockchain
            const txDetails = await this.verifyTransaction(transactionHash, network);
            if (!txDetails) {
                throw new Error('Transaction not found or invalid');
            }

            // Check if transaction is to correct address and amount
            const expectedAddress = this.merchantWallets[network].toLowerCase();
            if (txDetails.to.toLowerCase() !== expectedAddress) {
                throw new Error('Payment sent to wrong address');
            }

            const cryptoAmounts = JSON.parse(payment.cryptoAmounts);
            const expectedAmount = cryptoAmounts[network];
            
            // Verify amount (with some tolerance for gas/fees)
            const tolerance = 0.01; // 1% tolerance
            const receivedAmount = new Decimal(txDetails.value);
            let expectedTokenAmount;

            if (txDetails.tokenAddress) {
                expectedTokenAmount = new Decimal(expectedAmount[txDetails.tokenSymbol]?.amount || '0');
            } else {
                const nativeToken = Object.keys(expectedAmount)[0];
                expectedTokenAmount = new Decimal(expectedAmount[nativeToken]?.amount || '0');
            }

            const amountDiff = receivedAmount.minus(expectedTokenAmount).abs();
            const toleranceAmount = expectedTokenAmount.mul(tolerance);

            if (amountDiff.gt(toleranceAmount) && receivedAmount.lt(expectedTokenAmount)) {
                throw new Error('Insufficient payment amount');
            }

            // Update payment status
            const updatedPayment = {
                ...payment,
                status: 'completed',
                paidAt: new Date().toISOString(),
                transactionHash,
                network,
                actualAmount: receivedAmount.toString(),
                transactions: JSON.stringify([
                    ...JSON.parse(payment.transactions || '[]'),
                    {
                        hash: transactionHash,
                        network,
                        amount: receivedAmount.toString(),
                        timestamp: new Date().toISOString()
                    }
                ])
            };

            await this.redis.hSet(`payment:${paymentId}`, updatedPayment);

            // Send webhook notification
            if (payment.webhookUrl) {
                await this.sendWebhook(payment.webhookUrl, {
                    event: 'payment.completed',
                    paymentId,
                    transactionHash,
                    network,
                    amount: receivedAmount.toString(),
                    timestamp: new Date().toISOString()
                });
            }

            return {
                status: 'completed',
                transactionHash,
                network,
                amount: receivedAmount.toString()
            };
        } catch (error) {
            // Update payment with error status
            await this.redis.hSet(`payment:${paymentId}`, {
                status: 'failed',
                error: error.message,
                failedAt: new Date().toISOString()
            });
            
            throw new Error(`Failed to process payment: ${error.message}`);
        }
    }

    // Verify blockchain transaction
    async verifyTransaction(txHash, network) {
        try {
            const provider = this.providers[network];
            if (!provider) {
                throw new Error(`Unsupported network: ${network}`);
            }

            const tx = await provider.getTransaction(txHash);
            const receipt = await provider.getTransactionReceipt(txHash);

            if (!tx || !receipt) {
                return null;
            }

            // Check if transaction is confirmed
            const currentBlock = await provider.getBlockNumber();
            const confirmations = currentBlock - receipt.blockNumber;
            
            if (confirmations < 3) { // Require 3 confirmations
                throw new Error('Transaction not yet confirmed');
            }

            let txDetails = {
                hash: txHash,
                from: tx.from,
                to: tx.to,
                value: ethers.formatEther(tx.value),
                gasUsed: receipt.gasUsed.toString(),
                blockNumber: receipt.blockNumber,
                confirmations,
                success: receipt.status === 1
            };

            // Check for token transfers in logs
            if (receipt.logs.length > 0) {
                const tokenTransfer = this.parseTokenTransfer(receipt.logs);
                if (tokenTransfer) {
                    txDetails = {
                        ...txDetails,
                        tokenAddress: tokenTransfer.tokenAddress,
                        tokenSymbol: tokenTransfer.symbol,
                        value: tokenTransfer.amount
                    };
                }
            }

            return txDetails;
        } catch (error) {
            console.error('Error verifying transaction:', error);
            return null;
        }
    }

    // Parse token transfer from transaction logs
    parseTokenTransfer(logs) {
        try {
            // ERC-20 Transfer event signature
            const transferSignature = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef';
            
            for (const log of logs) {
                if (log.topics[0] === transferSignature) {
                    // Decode transfer event
                    const tokenAddress = log.address;
                    const amount = ethers.formatUnits(log.data, 18); // Assume 18 decimals, should be dynamic
                    
                    return {
                        tokenAddress,
                        amount,
                        symbol: 'TOKEN' // Would need to fetch actual symbol
                    };
                }
            }
            return null;
        } catch (error) {
            console.error('Error parsing token transfer:', error);
            return null;
        }
    }

    // Get payment status
    async getPaymentStatus(paymentId) {
        try {
            const payment = await this.redis.hGetAll(`payment:${paymentId}`);
            if (!payment.paymentId) {
                throw new Error('Payment not found');
            }

            // Check if payment has expired
            const now = new Date();
            const expirationTime = new Date(payment.expirationTime);
            
            if (now > expirationTime && payment.status === 'pending') {
                await this.redis.hSet(`payment:${paymentId}`, 'status', 'expired');
                payment.status = 'expired';
            }

            return {
                paymentId: payment.paymentId,
                status: payment.status,
                amount: payment.amount,
                currency: payment.currency,
                createdAt: payment.createdAt,
                expirationTime: payment.expirationTime,
                paidAt: payment.paidAt,
                transactionHash: payment.transactionHash,
                network: payment.network,
                transactions: JSON.parse(payment.transactions || '[]')
            };
        } catch (error) {
            throw new Error(`Failed to get payment status: ${error.message}`);
        }
    }

    // Cancel payment
    async cancelPayment(paymentId, merchantId) {
        try {
            const payment = await this.redis.hGetAll(`payment:${paymentId}`);
            if (!payment.paymentId) {
                throw new Error('Payment not found');
            }

            if (payment.merchantId !== merchantId) {
                throw new Error('Unauthorized');
            }

            if (payment.status !== 'pending') {
                throw new Error('Can only cancel pending payments');
            }

            await this.redis.hSet(`payment:${paymentId}`, {
                status: 'cancelled',
                cancelledAt: new Date().toISOString()
            });

            return { status: 'cancelled' };
        } catch (error) {
            throw new Error(`Failed to cancel payment: ${error.message}`);
        }
    }

    // Get merchant payments
    async getMerchantPayments(merchantId, limit = 50, offset = 0) {
        try {
            const paymentIds = await this.redis.lRange(
                `merchant:${merchantId}:payments`,
                offset,
                offset + limit - 1
            );

            const payments = [];
            for (const paymentId of paymentIds) {
                const payment = await this.redis.hGetAll(`payment:${paymentId}`);
                if (payment.paymentId) {
                    payments.push({
                        paymentId: payment.paymentId,
                        amount: payment.amount,
                        currency: payment.currency,
                        status: payment.status,
                        createdAt: payment.createdAt,
                        paidAt: payment.paidAt,
                        description: payment.description
                    });
                }
            }

            return payments;
        } catch (error) {
            throw new Error(`Failed to get merchant payments: ${error.message}`);
        }
    }

    // Generate payment widget
    generatePaymentWidget(paymentId, options = {}) {
        const {
            width = '400px',
            height = '600px',
            theme = 'light',
            showQR = true,
            autoRefresh = true
        } = options;

        return {
            embedCode: `
                <iframe 
                    src="${process.env.FRONTEND_URL}/widget/${paymentId}" 
                    width="${width}" 
                    height="${height}"
                    frameborder="0"
                    data-theme="${theme}"
                    data-show-qr="${showQR}"
                    data-auto-refresh="${autoRefresh}">
                </iframe>
            `,
            directUrl: `${process.env.FRONTEND_URL}/pay/${paymentId}`,
            widgetConfig: {
                paymentId,
                width,
                height,
                theme,
                showQR,
                autoRefresh
            }
        };
    }

    // Webhook sender
    async sendWebhook(url, data) {
        try {
            const signature = this.generateWebhookSignature(JSON.stringify(data));
            
            await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Webhook-Signature': signature
                },
                body: JSON.stringify(data)
            });
        } catch (error) {
            console.error('Failed to send webhook:', error);
        }
    }

    // Generate webhook signature for verification
    generateWebhookSignature(payload) {
        const secret = process.env.WEBHOOK_SECRET || 'default-secret';
        return crypto.createHmac('sha256', secret)
            .update(payload)
            .digest('hex');
    }

    // Get supported payment methods
    getSupportedPaymentMethods() {
        const methods = [];

        for (const [network, tokens] of Object.entries(this.paymentTokens)) {
            for (const [symbol, info] of Object.entries(tokens)) {
                methods.push({
                    network,
                    symbol,
                    name: `${symbol} (${this.getNetworkName(network)})`,
                    address: info.address,
                    decimals: info.decimals,
                    isNative: !info.address
                });
            }
        }

        return methods;
    }

    // Utility functions
    getNetworkName(network) {
        const names = {
            ethereum: 'Ethereum',
            polygon: 'Polygon',
            bsc: 'Binance Smart Chain'
        };
        return names[network] || network;
    }

    async convertToUSD(amount, currency) {
        if (currency === 'USD') return amount;
        
        // Mock conversion - would integrate with forex API
        const rates = { EUR: 1.1, GBP: 1.3, JPY: 0.0068 };
        return new Decimal(amount).mul(rates[currency] || 1).toNumber();
    }

    async getCryptoPrices() {
        // Mock prices - would integrate with CoinGecko/CoinMarketCap API
        return {
            'eth': 2500,
            'matic': 0.85,
            'bnb': 320,
            'usdc': 1,
            'usdt': 1,
            'dai': 1,
            'busd': 1
        };
    }

    // Payment analytics
    async getPaymentAnalytics(merchantId, timeframe = '30d') {
        try {
            const paymentIds = await this.redis.lRange(`merchant:${merchantId}:payments`, 0, -1);
            const analytics = {
                totalPayments: 0,
                completedPayments: 0,
                totalVolume: new Decimal(0),
                averageAmount: new Decimal(0),
                topNetworks: {},
                topTokens: {},
                conversionRate: 0
            };

            let completedVolume = new Decimal(0);
            let completedCount = 0;

            for (const paymentId of paymentIds) {
                const payment = await this.redis.hGetAll(`payment:${paymentId}`);
                if (!payment.paymentId) continue;

                analytics.totalPayments++;

                if (payment.status === 'completed') {
                    analytics.completedPayments++;
                    completedCount++;
                    
                    const amount = new Decimal(payment.amount);
                    completedVolume = completedVolume.plus(amount);
                    
                    // Track networks and tokens
                    const network = payment.network;
                    if (network) {
                        analytics.topNetworks[network] = (analytics.topNetworks[network] || 0) + 1;
                    }
                }
            }

            analytics.totalVolume = completedVolume.toNumber();
            analytics.averageAmount = completedCount > 0 
                ? completedVolume.div(completedCount).toNumber() 
                : 0;
            analytics.conversionRate = analytics.totalPayments > 0
                ? (analytics.completedPayments / analytics.totalPayments) * 100
                : 0;

            return analytics;
        } catch (error) {
            throw new Error(`Failed to get payment analytics: ${error.message}`);
        }
    }
}

export default CryptoPaymentGateway;