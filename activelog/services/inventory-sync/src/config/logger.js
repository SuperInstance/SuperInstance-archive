const winston = require('winston');
const path = require('path');

// Define log levels
const logLevels = {
  error: 0,
  warn: 1,
  info: 2,
  http: 3,
  debug: 4
};

// Define colors for each level
const logColors = {
  error: 'red',
  warn: 'yellow',
  info: 'green',
  http: 'magenta',
  debug: 'blue'
};

winston.addColors(logColors);

// Custom format for console output
const consoleFormat = winston.format.combine(
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
  winston.format.colorize({ all: true }),
  winston.format.printf(({ timestamp, level, message, ...meta }) => {
    let log = `${timestamp} [${level}]: ${message}`;
    
    if (Object.keys(meta).length > 0) {
      log += `\n${JSON.stringify(meta, null, 2)}`;
    }
    
    return log;
  })
);

// Custom format for file output
const fileFormat = winston.format.combine(
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
  winston.format.errors({ stack: true }),
  winston.format.json(),
  winston.format.printf(({ timestamp, level, message, ...meta }) => {
    return JSON.stringify({
      timestamp,
      level,
      message,
      service: 'inventory-sync',
      ...meta
    });
  })
);

// Create logs directory if it doesn't exist
const logsDir = path.join(process.cwd(), 'logs');

const transports = [
  // Console transport
  new winston.transports.Console({
    level: process.env.LOG_LEVEL || 'info',
    format: consoleFormat
  }),
  
  // File transport for errors
  new winston.transports.File({
    filename: path.join(logsDir, 'error.log'),
    level: 'error',
    format: fileFormat,
    maxsize: 10 * 1024 * 1024, // 10MB
    maxFiles: 5
  }),
  
  // File transport for all logs
  new winston.transports.File({
    filename: path.join(logsDir, 'combined.log'),
    format: fileFormat,
    maxsize: 10 * 1024 * 1024, // 10MB
    maxFiles: 10
  })
];

// Create logger instance
const logger = winston.createLogger({
  levels: logLevels,
  level: process.env.LOG_LEVEL || 'info',
  transports,
  exitOnError: false,
  handleExceptions: true,
  handleRejections: true
});

// Add request logging middleware
logger.http = (req, res, next) => {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = Date.now() - start;
    const { method, url, ip, headers } = req;
    const { statusCode } = res;
    
    logger.log('http', `${method} ${url}`, {
      ip,
      method,
      url,
      statusCode,
      duration: `${duration}ms`,
      userAgent: headers['user-agent'],
      contentLength: res.get('content-length'),
      referrer: headers.referrer || headers.referer
    });
  });
  
  if (next) next();
};

// Error handling for logger
logger.on('error', (err) => {
  console.error('Logger error:', err);
});

// Add utility methods to logger
logger.logInventoryEvent = (event, locationId, itemId, data = {}) => {
  logger.info(`Inventory Event: ${event}`, {
    event,
    locationId,
    itemId,
    timestamp: new Date().toISOString(),
    ...data
  });
};

logger.logPOSTransaction = (transactionId, locationId, amount, data = {}) => {
  logger.info(`POS Transaction: ${transactionId}`, {
    transactionId,
    locationId,
    amount,
    timestamp: new Date().toISOString(),
    ...data
  });
};

logger.logSupplyChainEvent = (event, supplierId, data = {}) => {
  logger.info(`Supply Chain Event: ${event}`, {
    event,
    supplierId,
    timestamp: new Date().toISOString(),
    ...data
  });
};

logger.logReservationEvent = (event, reservationId, data = {}) => {
  logger.info(`Reservation Event: ${event}`, {
    event,
    reservationId,
    timestamp: new Date().toISOString(),
    ...data
  });
};

logger.logPriceOptimization = (event, itemId, oldPrice, newPrice, data = {}) => {
  logger.info(`Price Optimization: ${event}`, {
    event,
    itemId,
    oldPrice,
    newPrice,
    timestamp: new Date().toISOString(),
    ...data
  });
};

logger.logNotificationEvent = (type, recipient, message, data = {}) => {
  logger.info(`Notification: ${type}`, {
    type,
    recipient,
    message: message.substring(0, 100),
    timestamp: new Date().toISOString(),
    ...data
  });
};

logger.logPickupEvent = (event, pickupId, data = {}) => {
  logger.info(`Pickup Event: ${event}`, {
    event,
    pickupId,
    timestamp: new Date().toISOString(),
    ...data
  });
};

logger.logPerformance = (operation, duration, metadata = {}) => {
  const level = duration > 1000 ? 'warn' : 'debug';
  logger.log(level, `Performance: ${operation}`, {
    operation,
    duration: `${duration}ms`,
    ...metadata
  });
};

// Export logger
module.exports = logger;