import { ApolloServerPlugin, GraphQLRequestListener } from '@apollo/server';
import { Redis } from 'ioredis';
import { GraphQLResolveInfo } from 'graphql';
import crypto from 'crypto';

interface CacheConfig {
  ttl: number; // Time to live in seconds
  keyGenerator?: (root: any, args: any, context: any, info: any) => string;
  skipCache?: (root: any, args: any, context: any, info: any) => boolean;
}

const DEFAULT_TTL = 300; // 5 minutes

export const cachePlugin = (redis: Redis): ApolloServerPlugin => {
  return {
    requestDidStart(): GraphQLRequestListener<any> {
      return {
        willSendResponse(requestContext) {
          // Cache implementation will be handled in field resolvers
          // This plugin can be used for response-level caching if needed
        }
      };
    }
  };
};

// Cache decorator for resolver functions
export function Cache(config: Partial<CacheConfig> = {}) {
  return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value;
    const cacheConfig: CacheConfig = {
      ttl: config.ttl || DEFAULT_TTL,
      keyGenerator: config.keyGenerator || defaultKeyGenerator,
      skipCache: config.skipCache || (() => false)
    };
    
    descriptor.value = async function (
      root: any,
      args: any,
      context: any,
      info: GraphQLResolveInfo
    ) {
      // Skip cache if configured to do so
      if (cacheConfig.skipCache!(root, args, context, info)) {
        return originalMethod.apply(this, [root, args, context, info]);
      }
      
      // Generate cache key
      const cacheKey = cacheConfig.keyGenerator!(root, args, context, info);
      
      // Try to get from cache
      try {
        const cached = await getCachedValue(context.redis || redis, cacheKey);
        if (cached !== null) {
          console.log(`Cache HIT: ${cacheKey}`);
          return cached;
        }
      } catch (error) {
        console.warn('Cache read error:', error);
      }
      
      // Execute original resolver
      const result = await originalMethod.apply(this, [root, args, context, info]);
      
      // Cache the result
      try {
        await setCachedValue(
          context.redis || redis,
          cacheKey,
          result,
          cacheConfig.ttl
        );
        console.log(`Cache SET: ${cacheKey} (TTL: ${cacheConfig.ttl}s)`);
      } catch (error) {
        console.warn('Cache write error:', error);
      }
      
      return result;
    };
    
    return descriptor;
  };
}

// Default cache key generator
function defaultKeyGenerator(
  root: any,
  args: any,
  context: any,
  info: GraphQLResolveInfo
): string {
  const fieldName = info.fieldName;
  const parentType = info.parentType.name;
  const userId = context.user?.id || 'anonymous';
  
  // Create a hash of the arguments
  const argsHash = createArgsHash(args);
  
  // Include parent object ID if available
  const parentId = root?.id || '';
  
  return `gql:${parentType}:${fieldName}:${userId}:${parentId}:${argsHash}`;
}

// Create hash from arguments
function createArgsHash(args: any): string {
  const sortedArgs = JSON.stringify(args, Object.keys(args).sort());
  return crypto.createHash('md5').update(sortedArgs).digest('hex');
}

// Get value from cache
async function getCachedValue(redis: Redis, key: string): Promise<any> {
  const cached = await redis.get(key);
  
  if (!cached) {
    return null;
  }
  
  try {
    return JSON.parse(cached);
  } catch {
    // If parsing fails, return the raw string
    return cached;
  }
}

// Set value in cache
async function setCachedValue(
  redis: Redis,
  key: string,
  value: any,
  ttl: number
): Promise<void> {
  const serialized = typeof value === 'string' ? value : JSON.stringify(value);
  await redis.setex(key, ttl, serialized);
}

// Invalidate cache by pattern
export async function invalidateCache(
  redis: Redis,
  pattern: string
): Promise<number> {
  let cursor = '0';
  let deletedCount = 0;
  
  do {
    const result = await redis.scan(cursor, 'MATCH', pattern, 'COUNT', 100);
    cursor = result[0];
    const keys = result[1];
    
    if (keys.length > 0) {
      deletedCount += await redis.del(...keys);
    }
  } while (cursor !== '0');
  
  return deletedCount;
}

// Cache invalidation helpers
export class CacheInvalidator {
  constructor(private redis: Redis) {}
  
  // Invalidate user-specific cache
  async invalidateUser(userId: string): Promise<void> {
    await invalidateCache(this.redis, `gql:*:*:${userId}:*`);
  }
  
  // Invalidate entity cache
  async invalidateEntity(entityType: string, entityId: string): Promise<void> {
    await Promise.all([
      invalidateCache(this.redis, `gql:${entityType}:*:*:${entityId}:*`),
      invalidateCache(this.redis, `gql:*:*:*:${entityId}:*`)
    ]);
  }
  
  // Invalidate field cache
  async invalidateField(
    entityType: string,
    fieldName: string,
    userId?: string
  ): Promise<void> {
    const userPattern = userId ? userId : '*';
    await invalidateCache(this.redis, `gql:${entityType}:${fieldName}:${userPattern}:*`);
  }
  
  // Invalidate organization cache
  async invalidateOrganization(orgId: string): Promise<void> {
    await invalidateCache(this.redis, `gql:*:*:*:*:*${orgId}*`);
  }
}

// Warming cache with batch operations
export class CacheWarmer {
  constructor(private redis: Redis) {}
  
  // Warm user cache
  async warmUserCache(
    userId: string,
    userData: any,
    ttl: number = DEFAULT_TTL
  ): Promise<void> {
    const key = `gql:User:user:${userId}::${createArgsHash({ id: userId })}`;
    await setCachedValue(this.redis, key, userData, ttl);
  }
  
  // Warm popular queries
  async warmPopularQueries(queries: Array<{
    key: string;
    resolver: () => Promise<any>;
    ttl?: number;
  }>): Promise<void> {
    const pipeline = this.redis.pipeline();
    
    for (const query of queries) {
      try {
        const result = await query.resolver();
        const serialized = JSON.stringify(result);
        pipeline.setex(query.key, query.ttl || DEFAULT_TTL, serialized);
      } catch (error) {
        console.error(`Failed to warm cache for ${query.key}:`, error);
      }
    }
    
    await pipeline.exec();
  }
}

// Cache statistics
export class CacheStats {
  constructor(private redis: Redis) {}
  
  async getStats(): Promise<{
    totalKeys: number;
    memoryUsage: number;
    hitRate: number;
    keysByPattern: Record<string, number>;
  }> {
    const info = await this.redis.info('memory');
    const memoryMatch = info.match(/used_memory:(\d+)/);
    const memoryUsage = memoryMatch ? parseInt(memoryMatch[1]) : 0;
    
    // Count keys by pattern
    const patterns = ['gql:User:*', 'gql:File:*', 'gql:Video:*', 'gql:Organization:*'];
    const keysByPattern: Record<string, number> = {};
    
    for (const pattern of patterns) {
      let count = 0;
      let cursor = '0';
      
      do {
        const result = await this.redis.scan(cursor, 'MATCH', pattern, 'COUNT', 100);
        cursor = result[0];
        count += result[1].length;
      } while (cursor !== '0');
      
      keysByPattern[pattern] = count;
    }
    
    const totalKeys = Object.values(keysByPattern).reduce((sum, count) => sum + count, 0);
    
    return {
      totalKeys,
      memoryUsage,
      hitRate: 0, // Would need to track hits/misses for this
      keysByPattern
    };
  }
}