import { GraphQLResolverMap } from 'apollo-graphql';
import { userResolvers } from './user';
import { fileResolvers } from './file';
import { videoResolvers } from './video';
import { pluginResolvers } from './plugin';
import { organizationResolvers } from './organization';
import { analyticsResolvers } from './analytics';
import { notificationResolvers } from './notification';
import { subscriptionResolvers } from './subscription';
import { scalarResolvers } from './scalars';

export const resolvers: GraphQLResolverMap = {
  // Scalars
  ...scalarResolvers,
  
  // Base resolvers
  Query: {
    // Health check
    health: () => ({
      status: 'OK',
      timestamp: new Date(),
      services: [
        { name: 'graphql', status: 'OK', responseTime: 0.1 },
        { name: 'database', status: 'OK', responseTime: 2.5 },
        { name: 'redis', status: 'OK', responseTime: 0.8 }
      ]
    }),
    
    version: () => process.env.npm_package_version || '1.0.0',
    
    _service: () => ({
      sdl: '' // Will be populated by federation
    }),
    
    // Extend with module resolvers
    ...userResolvers.Query,
    ...fileResolvers.Query,
    ...videoResolvers.Query,
    ...pluginResolvers.Query,
    ...organizationResolvers.Query,
    ...analyticsResolvers.Query,
    ...notificationResolvers.Query,
    ...subscriptionResolvers.Query
  },
  
  Mutation: {
    _placeholder: () => false,
    
    // Extend with module resolvers
    ...userResolvers.Mutation,
    ...fileResolvers.Mutation,
    ...videoResolvers.Mutation,
    ...pluginResolvers.Mutation,
    ...organizationResolvers.Mutation,
    ...analyticsResolvers.Mutation,
    ...notificationResolvers.Mutation,
    ...subscriptionResolvers.Mutation
  },
  
  Subscription: {
    _placeholder: () => false,
    
    // Extend with module resolvers
    ...userResolvers.Subscription,
    ...fileResolvers.Subscription,
    ...videoResolvers.Subscription,
    ...pluginResolvers.Subscription,
    ...organizationResolvers.Subscription,
    ...analyticsResolvers.Subscription,
    ...notificationResolvers.Subscription,
    ...subscriptionResolvers.Subscription
  },
  
  // Entity resolvers
  ...userResolvers,
  ...fileResolvers,
  ...videoResolvers,
  ...pluginResolvers,
  ...organizationResolvers,
  ...analyticsResolvers,
  ...notificationResolvers,
  ...subscriptionResolvers
};