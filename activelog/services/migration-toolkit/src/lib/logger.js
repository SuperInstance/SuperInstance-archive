import winston from 'winston';
import path from 'path';
import fs from 'fs-extra';

// Ensure logs directory exists
const logsDir = path.join(process.cwd(), 'logs');
fs.ensureDirSync(logsDir);

// Custom format for console output
const consoleFormat = winston.format.combine(
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
  winston.format.colorize(),
  winston.format.printf(({ level, message, timestamp, ...meta }) => {
    let msg = `${timestamp} [${level}] ${message}`;
    
    // Add metadata if present
    if (Object.keys(meta).length > 0) {
      msg += ` ${JSON.stringify(meta)}`;
    }
    
    return msg;
  })
);

// Custom format for file output
const fileFormat = winston.format.combine(
  winston.format.timestamp(),
  winston.format.errors({ stack: true }),
  winston.format.json()
);

// Create logger instance
const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  defaultMeta: {
    service: 'migration-toolkit',
    pid: process.pid,
    hostname: require('os').hostname()
  },
  transports: [
    // Console transport
    new winston.transports.Console({
      format: consoleFormat,
      handleExceptions: true,
      handleRejections: true
    }),
    
    // Error file transport
    new winston.transports.File({
      filename: path.join(logsDir, 'error.log'),
      level: 'error',
      format: fileFormat,
      maxsize: 50 * 1024 * 1024, // 50MB
      maxFiles: 5,
      tailable: true
    }),
    
    // Combined file transport
    new winston.transports.File({
      filename: path.join(logsDir, 'combined.log'),
      format: fileFormat,
      maxsize: 100 * 1024 * 1024, // 100MB
      maxFiles: 5,
      tailable: true
    }),
    
    // Daily rotate file transport for audit logs
    new winston.transports.File({
      filename: path.join(logsDir, 'audit.log'),
      level: 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json(),
        winston.format((info) => {
          // Only log certain audit events
          const auditEvents = [
            'migration_started',
            'migration_completed', 
            'migration_failed',
            'rollback_initiated',
            'rollback_completed',
            'service_registered',
            'payment_processed',
            'ai_request',
            'storage_transfer'
          ];
          
          if (info.event && auditEvents.includes(info.event)) {
            return info;
          }
          
          return false;
        })()
      ),
      maxsize: 50 * 1024 * 1024, // 50MB
      maxFiles: 10,
      tailable: true
    })
  ],
  
  // Exit on error
  exitOnError: false
});

// Add custom logging methods
logger.audit = (message, meta = {}) => {
  logger.info(message, { 
    ...meta, 
    event: meta.event || 'audit',
    timestamp: new Date().toISOString()
  });
};

logger.performance = (message, duration, meta = {}) => {
  logger.info(message, {
    ...meta,
    duration,
    event: 'performance',
    timestamp: new Date().toISOString()
  });
};

logger.security = (message, meta = {}) => {
  logger.warn(message, {
    ...meta,
    event: 'security',
    timestamp: new Date().toISOString()
  });
};

logger.migration = (message, migrationId, meta = {}) => {
  logger.info(message, {
    ...meta,
    migrationId,
    event: 'migration',
    timestamp: new Date().toISOString()
  });
};

// Handle uncaught exceptions and rejections
logger.exceptions.handle(
  new winston.transports.File({
    filename: path.join(logsDir, 'exceptions.log'),
    format: fileFormat
  })
);

logger.rejections.handle(
  new winston.transports.File({
    filename: path.join(logsDir, 'rejections.log'),
    format: fileFormat
  })
);

// Add request logging helper
logger.request = (req, res, next) => {
  const startTime = Date.now();
  
  res.on('finish', () => {
    const duration = Date.now() - startTime;
    const logData = {
      method: req.method,
      url: req.url,
      status: res.statusCode,
      duration,
      ip: req.ip,
      userAgent: req.get('user-agent'),
      event: 'http_request'
    };
    
    if (res.statusCode >= 400) {
      logger.warn('HTTP Request', logData);
    } else {
      logger.info('HTTP Request', logData);
    }
  });
  
  if (next) next();
};

// Stream for Morgan HTTP logging
logger.stream = {
  write: (message) => {
    logger.info(message.trim());
  }
};

export default logger;