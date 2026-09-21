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
import StockPortfolioTracker from './services/stock-portfolio-tracker.js';
import RealTimeQuotes from './services/real-time-quotes.js';
import RetirementPlanning from './services/retirement-planning.js';

// Import additional services (simplified implementations)
import DividendTracker from './services/dividend-tracker.js';
import OptionsAnalyzer from './services/options-analyzer.js';
import RiskAssessment from './services/risk-assessment.js';
import RebalancingEngine from './services/rebalancing-engine.js';
import TaxLossHarvesting from './services/tax-loss-harvesting.js';
import PerformanceAttribution from './services/performance-attribution.js';
import BenchmarkComparison from './services/benchmark-comparison.js';
import MonteCarloSimulator from './services/monte-carlo-simulator.js';
import ESGScoring from './services/esg-scoring.js';

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
const realTimeQuotes = new RealTimeQuotes(redis);
const stockPortfolioTracker = new StockPortfolioTracker(redis, realTimeQuotes);
const monteCarloSimulator = new MonteCarloSimulator(redis);
const retirementPlanning = new RetirementPlanning(redis, stockPortfolioTracker, monteCarloSimulator);
const dividendTracker = new DividendTracker(redis, realTimeQuotes);
const optionsAnalyzer = new OptionsAnalyzer(redis, realTimeQuotes);
const riskAssessment = new RiskAssessment(redis, stockPortfolioTracker);
const rebalancingEngine = new RebalancingEngine(redis, stockPortfolioTracker);
const taxLossHarvesting = new TaxLossHarvesting(redis, stockPortfolioTracker);
const performanceAttribution = new PerformanceAttribution(redis, stockPortfolioTracker);
const benchmarkComparison = new BenchmarkComparison(redis, stockPortfolioTracker, realTimeQuotes);
const esgScoring = new ESGScoring(redis);

// Middleware
app.use(helmet());
app.use(cors());
app.use(morgan('combined'));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 1000, // Higher limit for investment platform
    message: 'Too many requests from this IP, please try again later.'
});
app.use('/api/', limiter);

// Socket.io for real-time updates
io.on('connection', (socket) => {
    console.log('Client connected:', socket.id);

    socket.on('subscribe_quotes', (symbols) => {
        if (Array.isArray(symbols)) {
            symbols.forEach(symbol => {
                realTimeQuotes.subscribeToSymbol(symbol);
                socket.join(`quotes_${symbol}`);
            });
        }
    });

    socket.on('subscribe_portfolio', (portfolioId) => {
        socket.join(`portfolio_${portfolioId}`);
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
        version: process.env.npm_package_version || '1.0.0',
        services: {
            redis: 'connected',
            quotes: 'active',
            portfolios: 'active'
        }
    });
});

// Real-time Quotes Routes
app.get('/api/quotes/:symbol', async (req, res) => {
    try {
        const { symbol } = req.params;
        const quote = await realTimeQuotes.getQuote(symbol.toUpperCase());
        
        if (!quote) {
            return res.status(404).json({ success: false, error: 'Quote not found' });
        }
        
        res.json({ success: true, data: quote });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.post('/api/quotes/batch', async (req, res) => {
    try {
        const { symbols } = req.body;
        
        if (!Array.isArray(symbols)) {
            return res.status(400).json({ success: false, error: 'Symbols must be an array' });
        }
        
        const quotes = await realTimeQuotes.getBatchQuotes(symbols);
        res.json({ success: true, data: quotes });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/quotes/:symbol/extended', async (req, res) => {
    try {
        const { symbol } = req.params;
        const extendedQuote = await realTimeQuotes.getExtendedQuote(symbol.toUpperCase());
        res.json({ success: true, data: extendedQuote });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/quotes/:symbol/historical', async (req, res) => {
    try {
        const { symbol } = req.params;
        const { period = '1y', interval = '1d' } = req.query;
        const data = await realTimeQuotes.getHistoricalData(symbol.toUpperCase(), period, interval);
        res.json({ success: true, data });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

// Portfolio Tracking Routes
app.post('/api/portfolios', async (req, res) => {
    try {
        const { userId, ...portfolioData } = req.body;
        const portfolio = await stockPortfolioTracker.createPortfolio(userId, portfolioData);
        res.json({ success: true, data: portfolio });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/users/:userId/portfolios', async (req, res) => {
    try {
        const { userId } = req.params;
        const portfolios = await stockPortfolioTracker.getUserPortfolios(userId);
        res.json({ success: true, data: portfolios });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/portfolios/:portfolioId', async (req, res) => {
    try {
        const { portfolioId } = req.params;
        const portfolio = await stockPortfolioTracker.getPortfolioWithMarketData(portfolioId);
        
        if (!portfolio) {
            return res.status(404).json({ success: false, error: 'Portfolio not found' });
        }
        
        res.json({ success: true, data: portfolio });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.post('/api/portfolios/:portfolioId/positions', async (req, res) => {
    try {
        const { portfolioId } = req.params;
        const position = await stockPortfolioTracker.addPosition(portfolioId, req.body);
        
        // Emit real-time update
        io.to(`portfolio_${portfolioId}`).emit('position_added', position);
        
        res.json({ success: true, data: position });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.put('/api/portfolios/:portfolioId/positions/:positionId', async (req, res) => {
    try {
        const { portfolioId, positionId } = req.params;
        const result = await stockPortfolioTracker.updatePosition(portfolioId, positionId, req.body);
        
        // Emit real-time update
        io.to(`portfolio_${portfolioId}`).emit('position_updated', result);
        
        res.json({ success: true, data: result });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/portfolios/:portfolioId/performance', async (req, res) => {
    try {
        const { portfolioId } = req.params;
        const { period = '1y' } = req.query;
        const performance = await stockPortfolioTracker.getPortfolioPerformance(portfolioId, period);
        res.json({ success: true, data: performance });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/portfolios/:portfolioId/analytics', async (req, res) => {
    try {
        const { portfolioId } = req.params;
        const analytics = await stockPortfolioTracker.getPortfolioAnalytics(portfolioId);
        res.json({ success: true, data: analytics });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

// Retirement Planning Routes
app.post('/api/retirement/plans', async (req, res) => {
    try {
        const { userId, ...planData } = req.body;
        const plan = await retirementPlanning.createRetirementPlan(userId, planData);
        res.json({ success: true, data: plan });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/users/:userId/retirement/plans', async (req, res) => {
    try {
        const { userId } = req.params;
        const plans = await retirementPlanning.getUserRetirementPlans(userId);
        res.json({ success: true, data: plans });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/retirement/plans/:planId', async (req, res) => {
    try {
        const { planId } = req.params;
        const plan = await retirementPlanning.getRetirementPlan(planId);
        
        if (!plan) {
            return res.status(404).json({ success: false, error: 'Retirement plan not found' });
        }
        
        res.json({ success: true, data: plan });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.put('/api/retirement/plans/:planId', async (req, res) => {
    try {
        const { planId } = req.params;
        const plan = await retirementPlanning.updateRetirementPlan(planId, req.body);
        res.json({ success: true, data: plan });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

// Dividend Tracking Routes
app.get('/api/portfolios/:portfolioId/dividends', async (req, res) => {
    try {
        const { portfolioId } = req.params;
        const { period = '1y' } = req.query;
        const dividends = await dividendTracker.getPortfolioDividends(portfolioId, period);
        res.json({ success: true, data: dividends });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/dividends/:symbol/calendar', async (req, res) => {
    try {
        const { symbol } = req.params;
        const calendar = await dividendTracker.getDividendCalendar(symbol);
        res.json({ success: true, data: calendar });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

// Options Strategy Analyzer Routes
app.post('/api/options/analyze', async (req, res) => {
    try {
        const analysis = await optionsAnalyzer.analyzeStrategy(req.body);
        res.json({ success: true, data: analysis });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/options/:symbol/chain', async (req, res) => {
    try {
        const { symbol } = req.params;
        const { expiration } = req.query;
        const chain = await optionsAnalyzer.getOptionsChain(symbol, expiration);
        res.json({ success: true, data: chain });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

// Risk Assessment Routes
app.get('/api/portfolios/:portfolioId/risk', async (req, res) => {
    try {
        const { portfolioId } = req.params;
        const riskMetrics = await riskAssessment.calculatePortfolioRisk(portfolioId);
        res.json({ success: true, data: riskMetrics });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.post('/api/risk/scenario-analysis', async (req, res) => {
    try {
        const analysis = await riskAssessment.runScenarioAnalysis(req.body);
        res.json({ success: true, data: analysis });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

// Rebalancing Recommendations Routes
app.get('/api/portfolios/:portfolioId/rebalance', async (req, res) => {
    try {
        const { portfolioId } = req.params;
        const recommendations = await rebalancingEngine.generateRebalanceRecommendations(portfolioId);
        res.json({ success: true, data: recommendations });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.post('/api/portfolios/:portfolioId/rebalance/execute', async (req, res) => {
    try {
        const { portfolioId } = req.params;
        const result = await rebalancingEngine.executeRebalance(portfolioId, req.body);
        res.json({ success: true, data: result });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

// Tax Loss Harvesting Routes
app.get('/api/portfolios/:portfolioId/tax-loss-harvest', async (req, res) => {
    try {
        const { portfolioId } = req.params;
        const opportunities = await taxLossHarvesting.findHarvestingOpportunities(portfolioId);
        res.json({ success: true, data: opportunities });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.post('/api/portfolios/:portfolioId/tax-loss-harvest/execute', async (req, res) => {
    try {
        const { portfolioId } = req.params;
        const result = await taxLossHarvesting.executeHarvesting(portfolioId, req.body);
        res.json({ success: true, data: result });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

// Performance Attribution Routes
app.get('/api/portfolios/:portfolioId/attribution', async (req, res) => {
    try {
        const { portfolioId } = req.params;
        const { period = '1y' } = req.query;
        const attribution = await performanceAttribution.calculateAttribution(portfolioId, period);
        res.json({ success: true, data: attribution });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

// Benchmark Comparison Routes
app.get('/api/portfolios/:portfolioId/benchmark/:benchmarkSymbol', async (req, res) => {
    try {
        const { portfolioId, benchmarkSymbol } = req.params;
        const { period = '1y' } = req.query;
        const comparison = await benchmarkComparison.comparePortfolio(portfolioId, benchmarkSymbol, period);
        res.json({ success: true, data: comparison });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

// Monte Carlo Simulation Routes
app.post('/api/monte-carlo/portfolio', async (req, res) => {
    try {
        const simulation = await monteCarloSimulator.runPortfolioSimulation(req.body);
        res.json({ success: true, data: simulation });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.post('/api/monte-carlo/retirement', async (req, res) => {
    try {
        const simulation = await monteCarloSimulator.runRetirementSimulation(req.body);
        res.json({ success: true, data: simulation });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

// ESG Scoring Routes
app.get('/api/esg/:symbol', async (req, res) => {
    try {
        const { symbol } = req.params;
        const esgScore = await esgScoring.getESGScore(symbol);
        res.json({ success: true, data: esgScore });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/portfolios/:portfolioId/esg', async (req, res) => {
    try {
        const { portfolioId } = req.params;
        const esgAnalysis = await esgScoring.analyzePortfolioESG(portfolioId);
        res.json({ success: true, data: esgAnalysis });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

// Market Data and Research Routes
app.get('/api/market/sectors', async (req, res) => {
    try {
        // Mock sector performance data
        const sectors = [
            { name: 'Technology', performance: 0.125, weight: 0.28 },
            { name: 'Healthcare', performance: 0.085, weight: 0.13 },
            { name: 'Financials', performance: 0.065, weight: 0.11 },
            { name: 'Consumer Discretionary', performance: 0.095, weight: 0.12 },
            { name: 'Industrials', performance: 0.075, weight: 0.08 }
        ];
        
        res.json({ success: true, data: sectors });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

app.get('/api/market/indices', async (req, res) => {
    try {
        const indices = ['SPY', 'QQQ', 'IWM', 'VTI', 'VXUS'];
        const quotes = await realTimeQuotes.getBatchQuotes(indices);
        res.json({ success: true, data: quotes });
    } catch (error) {
        res.status(400).json({ success: false, error: error.message });
    }
});

// Screening and Research Routes
app.get('/api/screen/dividend-aristocrats', async (req, res) => {
    try {
        // Mock dividend aristocrats data
        const aristocrats = [
            { symbol: 'KO', name: 'Coca-Cola', yield: 0.031, years: 58 },
            { symbol: 'JNJ', name: 'Johnson & Johnson', yield: 0.027, years: 59 },
            { symbol: 'PG', name: 'Procter & Gamble', yield: 0.025, years: 66 }
        ];
        
        res.json({ success: true, data: aristocrats });
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

// Background tasks
setInterval(async () => {
    try {
        // Update portfolio values with latest quotes
        const activePortfolios = await redis.sMembers('active_portfolios');
        for (const portfolioId of activePortfolios) {
            const portfolio = await stockPortfolioTracker.getPortfolioWithMarketData(portfolioId);
            if (portfolio) {
                io.to(`portfolio_${portfolioId}`).emit('portfolio_updated', portfolio);
            }
        }
    } catch (error) {
        console.error('Error in background portfolio updates:', error);
    }
}, 60000); // Update every minute

// Graceful shutdown
process.on('SIGTERM', async () => {
    console.log('SIGTERM received, shutting down gracefully');
    server.close(() => {
        redis.quit();
        process.exit(0);
    });
});

const PORT = process.env.PORT || 8353;

async function startServer() {
    try {
        await redis.connect();
        
        server.listen(PORT, () => {
            console.log(`🚀 Investment Manager Server running on port ${PORT}`);
            console.log(`📊 Dashboard: http://localhost:${PORT}/health`);
            console.log(`🔌 WebSocket: ws://localhost:${PORT}`);
            console.log(`📈 API Documentation: http://localhost:${PORT}/api/docs`);
            console.log(`📖 Environment: ${process.env.NODE_ENV || 'development'}`);
        });
    } catch (error) {
        console.error('Failed to start server:', error);
        process.exit(1);
    }
}

startServer();

export default app;