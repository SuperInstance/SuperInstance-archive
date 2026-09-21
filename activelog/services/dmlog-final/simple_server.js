#!/usr/bin/env node
// Simple DMLog Final Service - Working version
// Port: 8508

const express = require('express');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 8508;

// Middleware
app.use(cors());
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'dmlog-final',
    version: '1.0.0',
    port: PORT,
    timestamp: new Date().toISOString()
  });
});

// Root endpoint
app.get('/', (req, res) => {
  res.json({
    service: 'dmlog-final',
    description: 'DMLog Final - Advanced D&D Campaign Management',
    features: [
      'Campaign management',
      'Real-time multiplayer',
      'AI-powered storytelling',
      'Community marketplace'
    ],
    health: '/health',
    docs: '/docs'
  });
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`DMLog Final service listening on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
});

module.exports = app;