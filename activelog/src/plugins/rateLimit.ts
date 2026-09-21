import { ApolloServerPlugin, GraphQLRequestListener } from '@apollo/server';
import { GraphQLError } from 'graphql';
import { Redis } from 'ioredis';
import { getDirective } from '@graphql-tools/utils';

interface RateLimitConfig {
  max: number;
  window: number; // in seconds
  keyGenerator?: (root: any, args: any, context: any, info: any) => string;
}

const DEFAULT_RATE_LIMITS = {
  max: 100,
  window: 60
};

// Redis client for rate limiting
const redis = new Redis({
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379'),
  password: process.env.REDIS_PASSWORD
});

export const rateLimitPlugin = (): ApolloServerPlugin => {
  const rateLimitMap = new Map<string, RateLimitConfig>();
  
  return {
    requestDidStart(): GraphQLRequestListener<any> {
      return {
        async willSendResponse(requestContext) {
          const { document, contextValue, operationName } = requestContext.request;
          const user = contextValue.user;
          
          if (!document || !user) return;
          
          // Extract rate limit directives from the query
          const rateLimits = extractRateLimits(document);
          
          for (const rateLimit of rateLimits) {
            const key = generateRateLimitKey(user.id, rateLimit.field, rateLimit.config);
            
            try {
              const isAllowed = await checkRateLimit(key, rateLimit.config);
              
              if (!isAllowed) {
                throw new GraphQLError(
                  `Rate limit exceeded for ${rateLimit.field}. Max ${rateLimit.config.max} requests per ${rateLimit.config.window} seconds`,
                  {
                    extensions: {
                      code: 'RATE_LIMIT_EXCEEDED',
                      field: rateLimit.field,
                      max: rateLimit.config.max,
                      window: rateLimit.config.window
                    }
                  }
                );
              }
            } catch (error) {
              if (error instanceof GraphQLError) {
                throw error;
              }
              
              console.error('Rate limit check failed:', error);
              // Allow request if rate limit check fails
            }
          }
        }
      };
    }
  };
};

// Extract rate limit directives from document
function extractRateLimits(document: any): Array<{ field: string; config: RateLimitConfig }> {
  const rateLimits: Array<{ field: string; config: RateLimitConfig }> = [];
  
  // This is a simplified implementation
  // In a real implementation, you'd traverse the document AST
  // and extract @rateLimit directives from each field
  
  // For now, return default rate limits for the operation
  rateLimits.push({
    field: 'default',
    config: DEFAULT_RATE_LIMITS
  });
  
  return rateLimits;
}

// Generate rate limit key
function generateRateLimitKey(
  userId: string,
  field: string,
  config: RateLimitConfig
): string {
  const window = Math.floor(Date.now() / 1000 / config.window);
  return `ratelimit:${userId}:${field}:${window}`;
}

// Check rate limit using Redis
async function checkRateLimit(
  key: string,
  config: RateLimitConfig
): Promise<boolean> {
  const current = await redis.incr(key);
  
  if (current === 1) {
    // Set expiration on first request
    await redis.expire(key, config.window);
  }
  
  return current <= config.max;
}

// Advanced rate limiting with sliding window
export async function checkSlidingWindowRateLimit(
  key: string,
  config: RateLimitConfig
): Promise<boolean> {
  const now = Date.now();
  const window = config.window * 1000; // Convert to milliseconds
  const pipeline = redis.pipeline();
  
  // Remove expired entries
  pipeline.zremrangebyscore(key, 0, now - window);
  
  // Count current entries
  pipeline.zcard(key);
  
  // Add current request
  pipeline.zadd(key, now, `${now}-${Math.random()}`);
  
  // Set expiration
  pipeline.expire(key, config.window);
  
  const results = await pipeline.exec();
  
  if (!results) return false;
  
  const count = results[1][1] as number;
  return count < config.max;
}

// Rate limiting by IP address
export async function checkIPRateLimit(
  ip: string,
  config: RateLimitConfig
): Promise<boolean> {
  const key = `ratelimit:ip:${ip}`;
  return checkRateLimit(key, config);
}

// Rate limiting by user role
export async function checkRoleBasedRateLimit(
  userId: string,
  role: string,
  field: string
): Promise<boolean> {
  const config = getRoleBasedConfig(role);
  const key = generateRateLimitKey(userId, field, config);
  return checkRateLimit(key, config);
}

// Get rate limit configuration based on user role
function getRoleBasedConfig(role: string): RateLimitConfig {
  switch (role) {
    case 'ADMIN':
    case 'SUPER_ADMIN':
      return { max: 500, window: 60 };
    case 'USER':
      return { max: 100, window: 60 };
    default:
      return DEFAULT_RATE_LIMITS;
  }
}

// Clean up expired rate limit keys
export async function cleanupRateLimits(): Promise<void> {
  const pattern = 'ratelimit:*';
  let cursor = '0';
  
  do {
    const result = await redis.scan(cursor, 'MATCH', pattern, 'COUNT', 100);
    cursor = result[0];
    const keys = result[1];
    
    if (keys.length > 0) {
      const pipeline = redis.pipeline();
      
      for (const key of keys) {
        const ttl = await redis.ttl(key);
        if (ttl === -1) {
          // Key exists but has no expiration - delete it
          pipeline.del(key);
        }
      }
      
      await pipeline.exec();
    }
  } while (cursor !== '0');
}

// Schedule cleanup every hour
setInterval(cleanupRateLimits, 60 * 60 * 1000);