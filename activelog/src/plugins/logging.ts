import { ApolloServerPlugin, GraphQLRequestListener } from '@apollo/server';
import { GraphQLError } from 'graphql';

interface LogEntry {
  timestamp: string;
  requestId: string;
  userId?: string;
  operation?: string;
  operationType?: string;
  variables?: any;
  duration?: number;
  complexity?: number;
  errors?: any[];
  ip?: string;
  userAgent?: string;
}

export const loggingPlugin = (): ApolloServerPlugin => {
  return {
    requestDidStart(): GraphQLRequestListener<any> {
      let startTime: number;
      let logEntry: LogEntry;
      
      return {
        didResolveOperation({ request, operationName, contextValue }) {
          startTime = Date.now();
          
          logEntry = {
            timestamp: new Date().toISOString(),
            requestId: contextValue.req.get('x-request-id') || generateRequestId(),
            userId: contextValue.user?.id,
            operation: operationName || 'anonymous',
            operationType: request.operationName,
            variables: request.variables,
            ip: contextValue.ip,
            userAgent: contextValue.userAgent
          };
        },
        
        didEncounterErrors({ errors, contextValue }) {
          logEntry.errors = errors.map(error => ({
            message: error.message,
            code: error.extensions?.code,
            path: error.path,
            stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
          }));
          
          // Log GraphQL errors
          console.error('GraphQL Errors:', {
            ...logEntry,
            errors: logEntry.errors
          });
        },
        
        willSendResponse({ response, contextValue }) {
          logEntry.duration = Date.now() - startTime;
          
          // Extract complexity from response extensions if available
          if (response.http?.body && 'singleResult' in response.http.body) {
            const result = response.http.body.singleResult;
            if (result.extensions?.complexity) {
              logEntry.complexity = result.extensions.complexity.value;
            }
          }
          
          // Log the request
          if (logEntry.errors && logEntry.errors.length > 0) {
            console.error('GraphQL Request Failed:', logEntry);
          } else {
            // Only log slow queries or complex queries in production
            const isSlowQuery = logEntry.duration && logEntry.duration > 1000;
            const isComplexQuery = logEntry.complexity && logEntry.complexity > 500;
            
            if (process.env.NODE_ENV === 'development' || isSlowQuery || isComplexQuery) {
              console.log('GraphQL Request:', {
                ...logEntry,
                // Don't log variables in production for security
                variables: process.env.NODE_ENV === 'development' ? logEntry.variables : '[REDACTED]'
              });
            }
          }
          
          // Send metrics to monitoring system (e.g., DataDog, New Relic)
          if (process.env.MONITORING_ENABLED === 'true') {
            sendMetrics(logEntry);
          }
        }
      };
    }
  };
};

// Generate unique request ID
function generateRequestId(): string {
  return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// Send metrics to monitoring system
async function sendMetrics(logEntry: LogEntry): Promise<void> {
  try {
    // Example: Send to DataDog
    // const StatsD = require('hot-shots');
    // const dogstatsd = new StatsD();
    
    // dogstatsd.timing('graphql.query.duration', logEntry.duration);
    // dogstatsd.gauge('graphql.query.complexity', logEntry.complexity);
    // dogstatsd.increment('graphql.query.count', 1, {
    //   operation: logEntry.operation,
    //   user_role: logEntry.userRole
    // });
    
    // Example: Send to custom monitoring endpoint
    if (process.env.METRICS_ENDPOINT) {
      await fetch(process.env.METRICS_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${process.env.METRICS_API_KEY}`
        },
        body: JSON.stringify({
          service: 'activelog-graphql',
          metrics: {
            'query.duration': logEntry.duration,
            'query.complexity': logEntry.complexity,
            'query.count': 1
          },
          tags: {
            operation: logEntry.operation,
            user_id: logEntry.userId,
            has_errors: logEntry.errors ? logEntry.errors.length > 0 : false
          },
          timestamp: logEntry.timestamp
        })
      });
    }
  } catch (error) {
    console.error('Failed to send metrics:', error);
  }
}

// Structured logging utilities
export class GraphQLLogger {
  private context: any;
  
  constructor(context: any) {
    this.context = context;
  }
  
  log(level: 'info' | 'warn' | 'error', message: string, data?: any): void {
    const logData = {
      timestamp: new Date().toISOString(),
      level,
      message,
      userId: this.context.user?.id,
      requestId: this.context.req.get('x-request-id'),
      ip: this.context.ip,
      ...data
    };
    
    switch (level) {
      case 'info':
        console.log(JSON.stringify(logData));
        break;
      case 'warn':
        console.warn(JSON.stringify(logData));
        break;
      case 'error':
        console.error(JSON.stringify(logData));
        break;
    }
  }
  
  info(message: string, data?: any): void {
    this.log('info', message, data);
  }
  
  warn(message: string, data?: any): void {
    this.log('warn', message, data);
  }
  
  error(message: string, error?: Error | any, data?: any): void {
    this.log('error', message, {
      error: error instanceof Error ? {
        message: error.message,
        stack: error.stack,
        name: error.name
      } : error,
      ...data
    });
  }
}

// Performance monitoring
export class PerformanceMonitor {
  private startTimes: Map<string, number> = new Map();
  
  start(operationId: string): void {
    this.startTimes.set(operationId, Date.now());
  }
  
  end(operationId: string): number {
    const startTime = this.startTimes.get(operationId);
    if (!startTime) return 0;
    
    const duration = Date.now() - startTime;
    this.startTimes.delete(operationId);
    
    return duration;
  }
  
  measure<T>(operationId: string, operation: () => Promise<T>): Promise<T> {
    return new Promise(async (resolve, reject) => {
      this.start(operationId);
      
      try {
        const result = await operation();
        const duration = this.end(operationId);
        
        console.log(`Operation ${operationId} completed in ${duration}ms`);
        resolve(result);
      } catch (error) {
        const duration = this.end(operationId);
        console.error(`Operation ${operationId} failed after ${duration}ms:`, error);
        reject(error);
      }
    });
  }
}

// Audit logging for sensitive operations
export class AuditLogger {
  static async logUserAction(
    userId: string,
    action: string,
    resource: string,
    details?: any,
    context?: any
  ): Promise<void> {
    const auditEntry = {
      timestamp: new Date().toISOString(),
      userId,
      action,
      resource,
      details,
      ip: context?.ip,
      userAgent: context?.userAgent,
      requestId: context?.req?.get('x-request-id')
    };
    
    // Log to audit log
    console.log('AUDIT:', JSON.stringify(auditEntry));
    
    // Store in database for compliance
    if (process.env.AUDIT_DB_ENABLED === 'true') {
      // await auditDatabase.insertAuditLog(auditEntry);
    }
    
    // Send to security monitoring
    if (process.env.SECURITY_MONITORING_ENABLED === 'true') {
      // await securityMonitoring.send(auditEntry);
    }
  }
  
  static async logSecurityEvent(
    eventType: 'login' | 'logout' | 'failed_auth' | 'permission_denied' | 'suspicious_activity',
    details: any,
    context?: any
  ): Promise<void> {
    const securityEntry = {
      timestamp: new Date().toISOString(),
      eventType,
      details,
      ip: context?.ip,
      userAgent: context?.userAgent,
      userId: context?.user?.id
    };
    
    console.warn('SECURITY EVENT:', JSON.stringify(securityEntry));
    
    // Send to security monitoring immediately
    if (process.env.SECURITY_MONITORING_ENABLED === 'true') {
      // await securityMonitoring.sendImmediate(securityEntry);
    }
  }
}