const express = require('express');
const logger = require('./src/core/logger');

const app = express();
const port = process.env.PORT || 8370;

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    demoMode: process.env.DEMO_MODE === 'true'
  });
});

app.listen(port, '0.0.0.0', () => {
  logger.info(`🚀 Test server started on port ${port}`);
  console.log(`Server listening on http://0.0.0.0:${port}`);
});