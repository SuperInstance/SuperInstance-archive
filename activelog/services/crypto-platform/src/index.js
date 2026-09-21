import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import rateLimit from 'express-rate-limit';
import { createServer } from 'http';
import { Server } from 'socket.io';
import Redis from 'redis';
import dotenv from 'dotenv';

// Import services
import MultiWalletManager from './services/multi-wallet-management.js';
import DeFiIntegration from './services/defi-integration.js';
import CryptoPaymentGateway from './services/crypto-payment-gateway.js';
import NFTMarketplaceConnector from './services/nft-marketplace-connector.js';
import YieldFarmingTracker from './services/yield-farming-tracker.js';

dotenv.config();

const app = express();
const server = createServer(app);
const io = new Server(server, {
    cors: {
        origin: process.env.ALLOWED_ORIGINS?.split(',') || ["http://localhost:3000"],
        methods: ["GET", "POST", "PUT", "DELETE"]
    }
});

// Redis client
const redis = Redis.createClient({
    url: process.env.REDIS_URL || 'redis://localhost:6379'
});

redis.on('error', (err) => console.error('Redis Client Error', err));
redis.on('connect', () => console.log('Redis Client Connected'));

// Initialize services
const multiWalletManager = new MultiWalletManager(redis);
const defiIntegration = new DeFiIntegration(redis);
const cryptoPaymentGateway = new CryptoPaymentGateway(redis);
const nftMarketplaceConnector = new NFTMarketplaceConnector(redis);
const yieldFarmingTracker = new YieldFarmingTracker(redis);

// Middleware
app.use(helmet());
app.use(cors());
app.use(morgan('combined'));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100, // Limit each IP to 100 requests per windowMs
    message: 'Too many requests from this IP, please try again later.'
});
app.use('/api/', limiter);

// Socket.io for real-time updates
io.on('connection', (socket) => {
    console.log('Client connected:', socket.id);

    socket.on('subscribe_wallet', (walletId) => {
        socket.join(`wallet_${walletId}`);
    });

    socket.on('subscribe_payment', (paymentId) => {
        socket.join(`payment_${paymentId}`);
    });

    socket.on('disconnect', () => {
        console.log('Client disconnected:', socket.id);
    });
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        version: process.env.npm_package_version || '1.0.0'
    });
});

// Multi-Wallet Management Routes
app.post('/api/wallets/generate', async (req, res) => {
    try {
        const { userId, walletName } = req.body;
        const result = await multiWalletManager.generateWallet(userId, walletName);
        res.json({ success: true, data: result });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.post('/api/wallets/import', async (req, res) => {
    try {
        const { userId, mnemonic, walletName } = req.body;
        const result = await multiWalletManager.importWallet(userId, mnemonic, walletName);
        res.json({ success: true, data: result });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/wallets/:walletId/balances', async (req, res) => {
    try {
        const { walletId } = req.params;
        const balances = await multiWalletManager.getWalletBalances(walletId);
        res.json({ success: true, data: balances });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/wallets/:walletId/tokens/:network', async (req, res) => {
    try {
        const { walletId, network } = req.params;
        const tokens = await multiWalletManager.getTokenBalances(walletId, network);
        res.json({ success: true, data: tokens });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.post('/api/wallets/:walletId/send', async (req, res) => {
    try {
        const { walletId } = req.params;
        const { toAddress, amount, network, tokenAddress } = req.body;
        const result = await multiWalletManager.sendTransaction(walletId, toAddress, amount, network, tokenAddress);
        
        // Emit real-time update
        io.to(`wallet_${walletId}`).emit('transaction_initiated', result);
        
        res.json({ success: true, data: result });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/users/:userId/wallets', async (req, res) => {
    try {
        const { userId } = req.params;
        const wallets = await multiWalletManager.getUserWallets(userId);
        res.json({ success: true, data: wallets });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

// DeFi Integration Routes
app.get('/api/defi/positions/:walletAddress', async (req, res) => {
    try {
        const { walletAddress } = req.params;
        const { networks } = req.query;
        const networkList = networks ? networks.split(',') : undefined;
        const positions = await defiIntegration.getDeFiPositions(walletAddress, networkList);
        res.json({ success: true, data: positions });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/defi/health/:walletAddress', async (req, res) => {
    try {
        const { walletAddress } = req.params;
        const health = await defiIntegration.calculatePortfolioHealth(walletAddress);
        res.json({ success: true, data: health });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/defi/opportunities/:walletAddress', async (req, res) => {
    try {
        const { walletAddress } = req.params;
        const opportunities = await defiIntegration.getDeFiOpportunities(walletAddress);
        res.json({ success: true, data: opportunities });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.post('/api/defi/execute', async (req, res) => {
    try {
        const { walletId, transaction } = req.body;
        const result = await defiIntegration.executeDeFiTransaction(walletId, transaction);
        res.json({ success: true, data: result });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

// Crypto Payment Gateway Routes
app.post('/api/payments/create', async (req, res) => {
    try {
        const { merchantId, paymentData } = req.body;
        const payment = await cryptoPaymentGateway.createPaymentRequest(merchantId, paymentData);
        res.json({ success: true, data: payment });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/payments/:paymentId/status', async (req, res) => {
    try {
        const { paymentId } = req.params;
        const status = await cryptoPaymentGateway.getPaymentStatus(paymentId);
        res.json({ success: true, data: status });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.post('/api/payments/:paymentId/process', async (req, res) => {
    try {
        const { paymentId } = req.params;
        const { transactionHash, network } = req.body;
        const result = await cryptoPaymentGateway.processPayment(paymentId, transactionHash, network);
        
        // Emit real-time update
        io.to(`payment_${paymentId}`).emit('payment_completed', result);
        
        res.json({ success: true, data: result });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/merchants/:merchantId/payments', async (req, res) => {
    try {
        const { merchantId } = req.params;
        const { limit = 50, offset = 0 } = req.query;
        const payments = await cryptoPaymentGateway.getMerchantPayments(merchantId, parseInt(limit), parseInt(offset));
        res.json({ success: true, data: payments });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/payments/methods', async (req, res) => {
    try {
        const methods = cryptoPaymentGateway.getSupportedPaymentMethods();
        res.json({ success: true, data: methods });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

// NFT Marketplace Connector Routes
app.get('/api/nft/collection/:userAddress', async (req, res) => {
    try {
        const { userAddress } = req.params;
        const { networks } = req.query;
        const networkList = networks ? networks.split(',') : undefined;
        const collection = await nftMarketplaceConnector.getUserNFTCollection(userAddress, networkList);
        res.json({ success: true, data: collection });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.post('/api/nft/list', async (req, res) => {
    try {
        const { walletId, nftData, listingData } = req.body;
        const result = await nftMarketplaceConnector.createNFTListing(walletId, nftData, listingData);
        res.json({ success: true, data: result });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/nft/:contractAddress/:tokenId/history/:network', async (req, res) => {
    try {
        const { contractAddress, tokenId, network } = req.params;
        const history = await nftMarketplaceConnector.getNFTPriceHistory(contractAddress, tokenId, network);
        res.json({ success: true, data: history });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/nft/analytics/:userAddress', async (req, res) => {
    try {
        const { userAddress } = req.params;
        const { timeframe } = req.query;
        const analytics = await nftMarketplaceConnector.getNFTAnalytics(userAddress, timeframe);
        res.json({ success: true, data: analytics });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

// Yield Farming Tracker Routes
app.get('/api/yield/positions/:userAddress', async (req, res) => {
    try {
        const { userAddress } = req.params;
        const { networks } = req.query;
        const networkList = networks ? networks.split(',') : undefined;
        const positions = await yieldFarmingTracker.getYieldFarmingPositions(userAddress, networkList);
        res.json({ success: true, data: positions });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/yield/opportunities', async (req, res) => {
    try {
        const { amount, token, networks } = req.query;
        const networkList = networks ? networks.split(',') : undefined;
        const opportunities = await yieldFarmingTracker.getBestYieldOpportunities(amount, token, networkList);
        res.json({ success: true, data: opportunities });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.post('/api/yield/stake', async (req, res) => {
    try {
        const { walletId, farmData } = req.body;
        const result = await yieldFarmingTracker.stakeLPTokens(walletId, farmData);
        res.json({ success: true, data: result });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.post('/api/yield/unstake', async (req, res) => {
    try {
        const { walletId, farmData } = req.body;
        const result = await yieldFarmingTracker.unstakeLPTokens(walletId, farmData);
        res.json({ success: true, data: result });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.post('/api/yield/claim', async (req, res) => {
    try {
        const { walletId, farmData } = req.body;
        const result = await yieldFarmingTracker.claimRewards(walletId, farmData);
        res.json({ success: true, data: result });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/yield/analytics/:userAddress', async (req, res) => {
    try {
        const { userAddress } = req.params;
        const { timeframe } = req.query;
        const analytics = await yieldFarmingTracker.getYieldAnalytics(userAddress, timeframe);
        res.json({ success: true, data: analytics });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/yield/impermanent-loss/:lpTokenAddress/:network', async (req, res) => {
    try {
        const { lpTokenAddress, network } = req.params;
        const { timeframe } = req.query;
        const loss = await yieldFarmingTracker.calculateImpermanentLoss(lpTokenAddress, network, timeframe);
        res.json({ success: true, data: loss });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

// Network status endpoints
app.get('/api/networks/status', async (req, res) => {
    try {
        const status = await multiWalletManager.getNetworkStatus();
        res.json({ success: true, data: status });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

// Error handling middleware
app.use((error, req, res, next) => {
    console.error('Error:', error);
    res.status(500).json({
        success: false,
        error: process.env.NODE_ENV === 'production' ? 'Internal server error' : error.message
    });
});

// 404 handler
app.use('*', (req, res) => {
    res.status(404).json({
        success: false,
        error: 'Endpoint not found'
    });
});

// Graceful shutdown
process.on('SIGTERM', async () => {
    console.log('SIGTERM received, shutting down gracefully');
    server.close(() => {
        redis.quit();
        process.exit(0);
    });
});

const PORT = process.env.PORT || 8352;

async function startServer() {
    try {
        await redis.connect();
        
        server.listen(PORT, () => {
            console.log(`🚀 Crypto Platform Server running on port ${PORT}`);
            console.log(`📊 Dashboard: http://localhost:${PORT}/health`);
            console.log(`🔌 WebSocket: ws://localhost:${PORT}`);
            console.log(`📖 Environment: ${process.env.NODE_ENV || 'development'}`);
        });
    } catch (error) {
        console.error('Failed to start server:', error);
        process.exit(1);
    }
}

startServer();

export default app;