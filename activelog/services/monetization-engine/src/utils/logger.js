const winston = require('winston');
const DailyRotateFile = require('winston-daily-rotate-file');

// Custom format for logs
const logFormat = winston.format.combine(
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
  winston.format.errors({ stack: true }),
  winston.format.json(),
  winston.format.printf(({ timestamp, level, message, stack, ...meta }) => {
    let log = `${timestamp} [${level.toUpperCase()}]: ${message}`;
    
    if (Object.keys(meta).length > 0) {
      log += ` ${JSON.stringify(meta)}`;
    }
    
    if (stack) {
      log += `\n${stack}`;
    }
    
    return log;
  })
);

// Create logger instance
const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: logFormat,
  defaultMeta: { service: 'monetization-engine' },
  transports: [
    // Console transport
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        logFormat
      )
    }),

    // Daily rotate file for all logs
    new DailyRotateFile({
      filename: 'logs/monetization-%DATE%.log',
      datePattern: 'YYYY-MM-DD',
      zippedArchive: true,
      maxSize: '20m',
      maxFiles: '30d',
      createSymlink: true,
      symlinkName: 'monetization-current.log'
    }),

    // Separate file for errors
    new DailyRotateFile({
      filename: 'logs/monetization-error-%DATE%.log',
      datePattern: 'YYYY-MM-DD',
      zippedArchive: true,
      maxSize: '20m',
      maxFiles: '90d',
      level: 'error',
      createSymlink: true,
      symlinkName: 'monetization-error-current.log'
    })
  ]
});

// Create logs directory if it doesn't exist
const fs = require('fs');
const path = require('path');
const logsDir = path.join(__dirname, '../../logs');

if (!fs.existsSync(logsDir)) {
  fs.mkdirSync(logsDir, { recursive: true });
}

// Helper methods for different log levels with context
logger.audit = (message, meta = {}) => {
  logger.info(message, { ...meta, type: 'AUDIT' });
};

logger.payment = (message, meta = {}) => {
  logger.info(message, { ...meta, type: 'PAYMENT' });
};

logger.security = (message, meta = {}) => {
  logger.warn(message, { ...meta, type: 'SECURITY' });
};

logger.billing = (message, meta = {}) => {
  logger.info(message, { ...meta, type: 'BILLING' });
};

logger.subscription = (message, meta = {}) => {
  logger.info(message, { ...meta, type: 'SUBSCRIPTION' });
};

logger.affiliate = (message, meta = {}) => {
  logger.info(message, { ...meta, type: 'AFFILIATE' });
};

logger.marketplace = (message, meta = {}) => {
  logger.info(message, { ...meta, type: 'MARKETPLACE' });
};

// Request logging middleware
logger.requestMiddleware = (req, res, next) => {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = Date.now() - start;
    const logData = {
      method: req.method,
      url: req.originalUrl,
      status: res.statusCode,
      duration: `${duration}ms`,
      userAgent: req.get('User-Agent'),
      ip: req.ip || req.connection.remoteAddress,
      userId: req.user?.id || 'anonymous'
    };

    if (res.statusCode >= 400) {
      logger.warn('HTTP Request Error', logData);
    } else {
      logger.info('HTTP Request', logData);
    }
  });

  next();
};

module.exports = logger;