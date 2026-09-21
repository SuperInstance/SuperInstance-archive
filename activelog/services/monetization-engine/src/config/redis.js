const redis = require('redis');
const logger = require('../utils/logger');

// Create Redis client
const client = redis.createClient({
  url: process.env.REDIS_URL || `redis://${process.env.REDIS_HOST || 'localhost'}:${process.env.REDIS_PORT || 6379}`,
  password: process.env.REDIS_PASSWORD,
  database: process.env.REDIS_DB || 0,
  socket: {
    reconnectStrategy: (retries) => Math.min(retries * 50, 500)
  }
});

client.on('connect', () => {
  logger.info('Redis connection established');
});

client.on('error', (err) => {
  logger.error('Redis connection error:', err);
});

client.on('end', () => {
  logger.warn('Redis connection closed');
});

client.on('reconnecting', () => {
  logger.info('Redis reconnecting...');
});

// Connect on startup
client.connect().catch(err => {
  logger.warn('Redis connection failed, running without Redis:', err.message);
});

module.exports = client;