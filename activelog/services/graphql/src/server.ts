import { ApolloServer } from '@apollo/server';
import { expressMiddleware } from '@apollo/server/express4';
import { ApolloGateway, IntrospectAndCompose, RemoteGraphQLDataSource } from '@apollo/gateway';
import { buildSubgraphSchema } from '@apollo/subgraph';
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import rateLimit from 'express-rate-limit';
import { createServer } from 'http';
import { WebSocketServer } from 'ws';
import { useServer } from 'graphql-ws/lib/use/ws';
import { GraphQLFormattedError } from 'graphql';
import Redis from 'ioredis';
import { typeDefs } from '@/schema';
import { resolvers } from '@/resolvers';
import { createDataLoaders } from '@/dataloaders';
import { Context, DataSources } from '@/types/context';
import { authMiddleware } from './middleware/auth';
import { complexityPlugin } from './plugins/complexity';
import { rateLimitPlugin } from './plugins/rateLimit';
import { cachePlugin } from './plugins/cache';
import { loggingPlugin } from './plugins/logging';

const port = process.env.PORT || 8010;
const isProduction = process.env.NODE_ENV === 'production';
const enablePlayground = !isProduction || process.env.ENABLE_PLAYGROUND === 'true';
const enableIntrospection = !isProduction || process.env.ENABLE_INTROSPECTION === 'true';

// Redis client for caching
const redis = new Redis({
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379'),
  password: process.env.REDIS_PASSWORD,
  retryDelayOnFailover: 100,
  enableReadyCheck: false,
  maxRetriesPerRequest: null
});

// Data sources factory
const createDataSources = (): DataSources => ({
  userAPI: new (require('@/datasources/UserAPI').default)(),
  fileAPI: new (require('@/datasources/FileAPI').default)(),
  videoAPI: new (require('@/datasources/VideoAPI').default)(),
  pluginAPI: new (require('@/datasources/PluginAPI').default)(),
  organizationAPI: new (require('@/datasources/OrganizationAPI').default)(),
  analyticsAPI: new (require('@/datasources/AnalyticsAPI').default)(),
  notificationAPI: new (require('@/datasources/NotificationAPI').default)(),
  subscriptionAPI: new (require('@/datasources/SubscriptionAPI').default)(),
  activityAPI: new (require('@/datasources/ActivityAPI').default)(),
  permissionAPI: new (require('@/datasources/PermissionAPI').default)()
});

// Gateway configuration for schema stitching
const gateway = new ApolloGateway({
  supergraphSdl: new IntrospectAndCompose({
    subgraphs: [
      // Main GraphQL service (this service)
      {
        name: 'main',
        url: `http://localhost:${port}/graphql`
      },
      // Additional microservices can be added here
      ...(process.env.USER_SERVICE_URL ? [{
        name: 'users',
        url: process.env.USER_SERVICE_URL
      }] : []),
      ...(process.env.FILE_SERVICE_URL ? [{
        name: 'files', 
        url: process.env.FILE_SERVICE_URL
      }] : []),
      ...(process.env.VIDEO_SERVICE_URL ? [{
        name: 'videos',
        url: process.env.VIDEO_SERVICE_URL
      }] : []),
      ...(process.env.PLUGIN_SERVICE_URL ? [{
        name: 'plugins',
        url: process.env.PLUGIN_SERVICE_URL
      }] : []),
      ...(process.env.ANALYTICS_SERVICE_URL ? [{
        name: 'analytics',
        url: process.env.ANALYTICS_SERVICE_URL
      }] : [])
    ]
  }),
  buildService({ url }) {
    return new RemoteGraphQLDataSource({
      url,
      willSendRequest({ request, context }) {
        // Forward auth headers to subservices
        if (context.user) {
          request.http?.headers.set('x-user-id', context.user.id);
          request.http?.headers.set('x-user-role', context.user.role);
        }
        
        // Forward request metadata
        request.http?.headers.set('x-request-id', context.req.get('x-request-id') || '');
        request.http?.headers.set('x-forwarded-for', context.ip);
        request.http?.headers.set('user-agent', context.userAgent);
      }
    });
  }
});

// Main Apollo Server (for monolith mode or when gateway is disabled)
const mainServer = new ApolloServer({
  schema: buildSubgraphSchema({ typeDefs, resolvers }),
  plugins: [
    complexityPlugin(),
    rateLimitPlugin(),
    cachePlugin(redis),
    loggingPlugin()
  ],
  introspection: enableIntrospection,
  formatError: (formattedError: GraphQLFormattedError) => {
    // Log errors in production
    if (isProduction) {
      console.error('GraphQL Error:', formattedError);
    }
    
    // Don't expose internal errors in production
    if (isProduction && formattedError.message.startsWith('Database')) {
      return new Error('Internal server error');
    }
    
    return formattedError;
  }
});

// Gateway Apollo Server (for microservices mode)
const gatewayServer = new ApolloServer({
  gateway,
  plugins: [
    complexityPlugin(),
    rateLimitPlugin(),
    cachePlugin(redis),
    loggingPlugin()
  ],
  introspection: enableIntrospection,
  formatError: (formattedError: GraphQLFormattedError) => {
    if (isProduction) {
      console.error('GraphQL Gateway Error:', formattedError);
    }
    
    if (isProduction && formattedError.message.startsWith('Database')) {
      return new Error('Internal server error');
    }
    
    return formattedError;
  }
});

// Express app setup
const app = express();

// Security middleware
app.use(helmet({
  contentSecurityPolicy: enablePlayground ? false : undefined,
  crossOriginEmbedderPolicy: false
}));

app.use(compression());

// CORS configuration
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
  credentials: true,
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'x-request-id']
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: process.env.RATE_LIMIT_MAX ? parseInt(process.env.RATE_LIMIT_MAX) : 1000,
  message: 'Too many requests from this IP',
  standardHeaders: true,
  legacyHeaders: false,
  skip: (req) => {
    // Skip rate limiting for health checks
    return req.path === '/health' || req.path === '/ready';
  }
});

app.use(limiter);

// Body parsing
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Health check endpoints
app.get('/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    timestamp: new Date().toISOString(),
    version: process.env.npm_package_version || '1.0.0'
  });
});

app.get('/ready', async (req, res) => {
  try {
    // Check Redis connection
    await redis.ping();
    
    res.json({ 
      status: 'Ready',
      services: {
        redis: 'OK',
        graphql: 'OK'
      }
    });
  } catch (error) {
    res.status(503).json({ 
      status: 'Not Ready',
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Context creation function
const createContext = async ({ req, res }: { req: express.Request; res: express.Response }): Promise<Context> => {
  // Extract user from auth middleware
  const user = (req as any).user;
  
  // Create data sources
  const dataSources = createDataSources();
  
  // Create DataLoaders
  const loaders = createDataLoaders(dataSources);
  
  return {
    req,
    res,
    user,
    dataSources,
    loaders,
    ip: req.ip || req.connection.remoteAddress || '',
    userAgent: req.get('User-Agent') || ''
  };
};

async function startServer() {
  // Determine which server to use
  const useGateway = process.env.USE_GATEWAY === 'true' && process.env.NODE_ENV === 'production';
  const server = useGateway ? gatewayServer : mainServer;
  
  console.log(`Starting ${useGateway ? 'Gateway' : 'Main'} Apollo Server...`);
  
  await server.start();
  
  // Apply GraphQL middleware
  app.use('/graphql', 
    authMiddleware, // Authentication middleware
    expressMiddleware(server, {
      context: createContext
    })
  );
  
  // Serve GraphQL Playground in development
  if (enablePlayground && !useGateway) {
    const { ApolloServerPluginLandingPageGraphQLPlayground } = require('@apollo/server-plugin-landing-page-graphql-playground');
    
    // Add playground plugin
    server.addPlugin(
      ApolloServerPluginLandingPageGraphQLPlayground({
        settings: {
          'request.credentials': 'include'
        }
      })
    );
  }
  
  // Create HTTP server for subscriptions
  const httpServer = createServer(app);
  
  // Set up WebSocket server for subscriptions
  const wsServer = new WebSocketServer({
    server: httpServer,
    path: '/graphql'
  });
  
  const serverCleanup = useServer(
    {
      schema: buildSubgraphSchema({ typeDefs, resolvers }),
      context: async (ctx) => {
        // Extract token from connection params or headers
        const token = ctx.connectionParams?.authorization || ctx.extra.request.headers.authorization;
        
        // Authenticate user for subscriptions
        let user;
        if (token) {
          try {
            // Verify JWT token here
            user = await authMiddleware.verifyToken(token.replace('Bearer ', ''));
          } catch (error) {
            console.error('Subscription auth error:', error);
          }
        }
        
        return {
          user,
          dataSources: createDataSources(),
          loaders: createDataLoaders(createDataSources())
        };
      }
    },
    wsServer
  );
  
  // Graceful shutdown
  process.on('SIGTERM', async () => {
    console.log('SIGTERM received. Shutting down gracefully...');
    
    serverCleanup.dispose();
    await server.stop();
    await redis.quit();
    
    httpServer.close(() => {
      console.log('Server shut down successfully');
      process.exit(0);
    });
  });
  
  // Start the server
  httpServer.listen(port, () => {
    console.log(`🚀 ActiveLog GraphQL Service ready at http://localhost:${port}/graphql`);
    
    if (enablePlayground && !useGateway) {
      console.log(`🎮 GraphQL Playground available at http://localhost:${port}/graphql`);
    }
    
    console.log(`📡 Subscriptions ready at ws://localhost:${port}/graphql`);
    
    if (useGateway) {
      console.log(`🌐 Gateway mode enabled with schema stitching`);
    }
    
    console.log(`⚡ Redis connection: ${redis.status}`);
    console.log(`🔒 Authentication: ${process.env.JWT_SECRET ? 'Enabled' : 'Disabled'}`);
    console.log(`📊 Rate limiting: ${process.env.RATE_LIMIT_MAX || 1000} requests per 15 minutes`);
  });
}

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

// Start the server
startServer().catch(error => {
  console.error('Failed to start server:', error);
  process.exit(1);
});