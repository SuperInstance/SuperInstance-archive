import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { CCreditSystem } from './core/CCreditSystem';
import { AdRevenueService } from './services/AdRevenueService';
import { PaymentGatewayService } from './services/PaymentGatewayService';
import { ExchangeRateService } from './services/ExchangeRateService';
import { AffiliateService } from './services/AffiliateService';
import { ActiveLedgerAPI } from './controllers/ActiveLedgerAPI';

dotenv.config();

const app = express();
const port = process.env.PORT || 3004;

// Middleware
app.use(cors());
app.use(express.json());

// Initialize services
const exchangeRateService = new ExchangeRateService();
const ccreditSystem = new CCreditSystem(exchangeRateService);
const adRevenueService = new AdRevenueService(ccreditSystem);
const affiliateService = new AffiliateService(ccreditSystem);

const paymentGatewayService = new PaymentGatewayService(
  process.env.STRIPE_SECRET_KEY || 'sk_test_mock',
  {
    clientId: process.env.PAYPAL_CLIENT_ID || 'mock',
    clientSecret: process.env.PAYPAL_CLIENT_SECRET || 'mock',
    environment: 'sandbox'
  }
);

// Initialize API controller
const apiController = new ActiveLedgerAPI({
  ccreditSystem,
  adRevenueService,
  paymentGatewayService,
  exchangeRateService,
  affiliateService
});

// Health check
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    service: 'activeledger',
    timestamp: new Date().toISOString()
  });
});

// API Routes
app.use('/api/v1', apiController.getRouter());

// Financial Integration Hub Routes
app.use('/api/v1/financial-hub', (req, res) => {
  // Proxy to Python financial integration service
  const axios = require('axios');
  const path = req.originalUrl.replace('/api/v1/financial-hub', '');
  const url = `http://localhost:8123${path}`;
  
  axios({
    method: req.method,
    url: url,
    data: req.body,
    headers: {
      'Content-Type': 'application/json'
    }
  }).then(response => {
    res.json(response.data);
  }).catch(error => {
    console.error('Financial hub proxy error:', error.message);
    res.status(error.response?.status || 500).json({
      error: 'Financial hub communication error',
      message: error.message
    });
  });
});

// Error handling
app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error(err.stack);
  res.status(500).json({ 
    success: false,
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : undefined
  });
});

// Start server
async function startServer() {
  try {
    console.log('🚀 Starting ActiveLedger Financial Platform...');
    
    // Initialize services
    await exchangeRateService.updateExchangeRates();
    console.log('✅ Exchange rates initialized');
    
    app.listen(port, () => {
      console.log(`🏦 ActiveLedger service listening on port ${port}`);
      console.log(`📊 Dashboard: http://localhost:${port}/dashboard`);
      console.log(`💳 CC Credits: http://localhost:${port}/api/v1/cc-credits`);
      console.log(`🛒 Marketplace: http://localhost:${port}/api/v1/marketplace`);
      console.log(`⚡ Compute: http://localhost:${port}/api/v1/compute`);
      console.log(`👥 Affiliates: http://localhost:${port}/api/v1/affiliates`);
    });
  } catch (error) {
    console.error('❌ Failed to start server:', error);
    process.exit(1);
  }
}

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('🛑 Received SIGTERM, shutting down gracefully...');
  exchangeRateService.destroy();
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('🛑 Received SIGINT, shutting down gracefully...');
  exchangeRateService.destroy();
  process.exit(0);
});

startServer();

export {
  ccreditSystem,
  adRevenueService,
  paymentGatewayService,
  exchangeRateService,
  affiliateService,
  apiController
};