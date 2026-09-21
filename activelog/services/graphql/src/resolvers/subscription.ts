import { PubSub, withFilter } from 'graphql-subscriptions';
import { RedisPubSub } from 'graphql-redis-subscriptions';
import Redis from 'ioredis';
import { Context } from '@/types/context';

// Create Redis clients for pub/sub
const redisOptions = {
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379'),
  password: process.env.REDIS_PASSWORD,
  retryDelayOnFailover: 100,
  enableReadyCheck: false,
  maxRetriesPerRequest: null
};

const pubsub = new RedisPubSub({
  publisher: new Redis(redisOptions),
  subscriber: new Redis(redisOptions)
});

// Subscription event names
export const SUBSCRIPTION_EVENTS = {
  // User events
  USER_UPDATED: 'USER_UPDATED',
  USER_ONLINE_STATUS: 'USER_ONLINE_STATUS',
  
  // File events
  FILE_UPLOADED: 'FILE_UPLOADED',
  FILE_PROCESSED: 'FILE_PROCESSED',
  FILE_SHARED: 'FILE_SHARED',
  FOLDER_UPDATED: 'FOLDER_UPDATED',
  
  // Video events
  VIDEO_PROCESSING_UPDATE: 'VIDEO_PROCESSING_UPDATE',
  VIDEO_TRANSCODING_COMPLETE: 'VIDEO_TRANSCODING_COMPLETE',
  
  // Plugin events
  PLUGIN_INSTALLED: 'PLUGIN_INSTALLED',
  PLUGIN_EXECUTION_UPDATE: 'PLUGIN_EXECUTION_UPDATE',
  
  // Organization events
  ORGANIZATION_UPDATED: 'ORGANIZATION_UPDATED',
  TEAM_MEMBER_ADDED: 'TEAM_MEMBER_ADDED',
  
  // Analytics events
  ANALYTICS_UPDATED: 'ANALYTICS_UPDATED',
  REAL_TIME_METRICS: 'REAL_TIME_METRICS',
  
  // Notification events
  NOTIFICATION_RECEIVED: 'NOTIFICATION_RECEIVED',
  NOTIFICATION_READ: 'NOTIFICATION_READ',
  UNREAD_COUNT_CHANGED: 'UNREAD_COUNT_CHANGED',
  
  // Subscription events
  SUBSCRIPTION_UPDATED: 'SUBSCRIPTION_UPDATED',
  USAGE_THRESHOLD_REACHED: 'USAGE_THRESHOLD_REACHED',
  PAYMENT_FAILED: 'PAYMENT_FAILED',
  INVOICE_GENERATED: 'INVOICE_GENERATED'
};

export const subscriptionResolvers = {
  Query: {
    // Subscription billing queries
    activeSubscriptions: async (_: any, __: any, { user, dataSources }: Context) => {
      return dataSources.subscriptionAPI.getActiveSubscriptions(user.id);
    },
    
    subscriptionPlans: async (_: any, __: any, { dataSources }: Context) => {
      return dataSources.subscriptionAPI.getPlans();
    },
    
    currentSubscription: async (_: any, __: any, { user, dataSources }: Context) => {
      return dataSources.subscriptionAPI.getCurrentSubscription(user.id);
    },
    
    usageMetrics: async (_: any, { period, organizationId }: any, { user, dataSources }: Context) => {
      return dataSources.subscriptionAPI.getUsageMetrics(user.id, { period, organizationId });
    },
    
    billingHistory: async (_: any, { pagination, filter }: any, { user, dataSources }: Context) => {
      return dataSources.subscriptionAPI.getBillingHistory(user.id, { pagination, filter });
    },
    
    paymentMethods: async (_: any, __: any, { user, dataSources }: Context) => {
      return dataSources.subscriptionAPI.getPaymentMethods(user.id);
    },
    
    invoice: async (_: any, { id }: any, { user, dataSources }: Context) => {
      return dataSources.subscriptionAPI.getInvoice(id, user.id);
    },
    
    upcomingInvoice: async (_: any, __: any, { user, dataSources }: Context) => {
      return dataSources.subscriptionAPI.getUpcomingInvoice(user.id);
    }
  },
  
  Mutation: {
    // Subscription management
    createSubscription: async (_: any, { input }: any, { user, dataSources }: Context) => {
      const result = await dataSources.subscriptionAPI.createSubscription(user.id, input);
      
      if (result.success) {
        pubsub.publish(SUBSCRIPTION_EVENTS.SUBSCRIPTION_UPDATED, {
          subscriptionUpdated: {
            subscription: result.subscription,
            changeType: 'CREATED',
            previousState: null
          },
          userId: user.id
        });
      }
      
      return result;
    },
    
    updateSubscription: async (_: any, { input }: any, { user, dataSources }: Context) => {
      const result = await dataSources.subscriptionAPI.updateSubscription(user.id, input);
      
      if (result.success) {
        pubsub.publish(SUBSCRIPTION_EVENTS.SUBSCRIPTION_UPDATED, {
          subscriptionUpdated: {
            subscription: result.subscription,
            changeType: 'UPDATED',
            previousState: input.previousState
          },
          userId: user.id
        });
      }
      
      return result;
    },
    
    cancelSubscription: async (_: any, { input }: any, { user, dataSources }: Context) => {
      const result = await dataSources.subscriptionAPI.cancelSubscription(user.id, input);
      
      if (result.success) {
        pubsub.publish(SUBSCRIPTION_EVENTS.SUBSCRIPTION_UPDATED, {
          subscriptionUpdated: {
            subscription: result.subscription,
            changeType: 'CANCELLATION',
            previousState: null
          },
          userId: user.id
        });
      }
      
      return result;
    },
    
    changePlan: async (_: any, { input }: any, { user, dataSources }: Context) => {
      const result = await dataSources.subscriptionAPI.changePlan(user.id, input);
      
      if (result.success) {
        pubsub.publish(SUBSCRIPTION_EVENTS.SUBSCRIPTION_UPDATED, {
          subscriptionUpdated: {
            subscription: result.subscription,
            changeType: 'PLAN_CHANGE',
            previousState: { planId: input.previousPlanId }
          },
          userId: user.id
        });
      }
      
      return result;
    },
    
    // Payment methods
    addPaymentMethod: async (_: any, { input }: any, { user, dataSources }: Context) => {
      return dataSources.subscriptionAPI.addPaymentMethod(user.id, input);
    },
    
    retryPayment: async (_: any, { invoiceId }: any, { user, dataSources }: Context) => {
      const result = await dataSources.subscriptionAPI.retryPayment(invoiceId, user.id);
      
      if (!result.success) {
        pubsub.publish(SUBSCRIPTION_EVENTS.PAYMENT_FAILED, {
          paymentFailed: {
            invoiceId,
            amount: result.amount,
            reason: result.error,
            nextRetryAt: result.nextRetryAt,
            attemptsRemaining: result.attemptsRemaining
          },
          userId: user.id
        });
      }
      
      return result;
    },
    
    // Usage tracking
    recordUsage: async (_: any, { input }: any, { dataSources }: Context) => {
      const result = await dataSources.subscriptionAPI.recordUsage(input);
      
      // Check if usage threshold is reached
      const usage = await dataSources.subscriptionAPI.getUsageMetrics(input.organizationId);
      const threshold = 0.8; // 80% threshold
      
      const metricUsage = usage[input.metric.toLowerCase()];
      if (metricUsage && metricUsage.percentage >= threshold) {
        pubsub.publish(SUBSCRIPTION_EVENTS.USAGE_THRESHOLD_REACHED, {
          usageThresholdReached: {
            organizationId: input.organizationId,
            metric: input.metric,
            threshold,
            currentUsage: metricUsage.current,
            limit: metricUsage.limit,
            severity: metricUsage.percentage >= 0.95 ? 'CRITICAL' : 'WARNING'
          },
          organizationId: input.organizationId
        });
      }
      
      return result;
    }
  },
  
  Subscription: {
    // User subscriptions
    userUpdated: {
      subscribe: withFilter(
        () => pubsub.asyncIterator([SUBSCRIPTION_EVENTS.USER_UPDATED]),
        (payload, variables) => payload.userId === variables.userId
      )
    },
    
    userOnlineStatus: {
      subscribe: withFilter(
        () => pubsub.asyncIterator([SUBSCRIPTION_EVENTS.USER_ONLINE_STATUS]),
        (payload, variables, context) => {
          // Only send to friends or team members
          return payload.userId === variables.userId || 
                 context.user.friends.includes(payload.userId) ||
                 context.user.teamMembers.includes(payload.userId);
        }
      )
    },
    
    // File subscriptions
    fileUploaded: {
      subscribe: withFilter(
        () => pubsub.asyncIterator([SUBSCRIPTION_EVENTS.FILE_UPLOADED]),
        (payload, variables) => payload.userId === variables.userId
      )
    },
    
    fileProcessed: {
      subscribe: withFilter(
        () => pubsub.asyncIterator([SUBSCRIPTION_EVENTS.FILE_PROCESSED]),
        (payload, variables) => payload.fileId === variables.fileId
      )
    },
    
    fileShared: {
      subscribe: withFilter(
        () => pubsub.asyncIterator([SUBSCRIPTION_EVENTS.FILE_SHARED]),
        (payload, variables) => payload.userId === variables.userId
      )
    },
    
    folderUpdated: {
      subscribe: withFilter(
        () => pubsub.asyncIterator([SUBSCRIPTION_EVENTS.FOLDER_UPDATED]),
        (payload, variables) => payload.folderId === variables.folderId
      )
    },
    
    // Video subscriptions
    videoProcessingUpdate: {
      subscribe: withFilter(
        () => pubsub.asyncIterator([SUBSCRIPTION_EVENTS.VIDEO_PROCESSING_UPDATE]),
        (payload, variables) => payload.videoId === variables.videoId
      )
    },
    
    videoTranscodingComplete: {
      subscribe: withFilter(
        () => pubsub.asyncIterator([SUBSCRIPTION_EVENTS.VIDEO_TRANSCODING_COMPLETE]),
        (payload, variables) => payload.userId === variables.userId
      )
    },
    
    // Plugin subscriptions
    pluginInstalled: {
      subscribe: withFilter(
        () => pubsub.asyncIterator([SUBSCRIPTION_EVENTS.PLUGIN_INSTALLED]),
        (payload, variables) => payload.userId === variables.userId
      )
    },
    
    pluginExecutionUpdate: {
      subscribe: withFilter(
        () => pubsub.asyncIterator([SUBSCRIPTION_EVENTS.PLUGIN_EXECUTION_UPDATE]),
        (payload, variables) => payload.executionId === variables.executionId
      )
    },
    
    // Organization subscriptions
    organizationUpdated: {
      subscribe: withFilter(
        () => pubsub.asyncIterator([SUBSCRIPTION_EVENTS.ORGANIZATION_UPDATED]),
        (payload, variables) => payload.organizationId === variables.organizationId
      )
    },
    
    teamMemberAdded: {
      subscribe: withFilter(
        () => pubsub.asyncIterator([SUBSCRIPTION_EVENTS.TEAM_MEMBER_ADDED]),
        (payload, variables) => payload.organizationId === variables.organizationId
      )
    },
    
    // Analytics subscriptions
    analyticsUpdated: {
      subscribe: withFilter(
        () => pubsub.asyncIterator([SUBSCRIPTION_EVENTS.ANALYTICS_UPDATED]),
        (payload, variables) => payload.dashboardId === variables.dashboardId
      )
    },
    
    realTimeMetrics: {
      subscribe: withFilter(
        () => pubsub.asyncIterator([SUBSCRIPTION_EVENTS.REAL_TIME_METRICS]),
        (payload, variables) => payload.organizationId === variables.organizationId
      )
    },
    
    // Notification subscriptions
    notificationReceived: {
      subscribe: withFilter(
        () => pubsub.asyncIterator([SUBSCRIPTION_EVENTS.NOTIFICATION_RECEIVED]),
        (payload, variables) => payload.userId === variables.userId
      )
    },
    
    notificationRead: {
      subscribe: withFilter(
        () => pubsub.asyncIterator([SUBSCRIPTION_EVENTS.NOTIFICATION_READ]),
        (payload, variables) => payload.userId === variables.userId
      )
    },
    
    unreadCountChanged: {
      subscribe: withFilter(
        () => pubsub.asyncIterator([SUBSCRIPTION_EVENTS.UNREAD_COUNT_CHANGED]),
        (payload, variables) => payload.userId === variables.userId
      )
    },
    
    // Subscription billing subscriptions
    subscriptionUpdated: {
      subscribe: withFilter(
        () => pubsub.asyncIterator([SUBSCRIPTION_EVENTS.SUBSCRIPTION_UPDATED]),
        (payload, variables) => payload.userId === variables.userId
      )
    },
    
    usageThresholdReached: {
      subscribe: withFilter(
        () => pubsub.asyncIterator([SUBSCRIPTION_EVENTS.USAGE_THRESHOLD_REACHED]),
        (payload, variables) => payload.organizationId === variables.organizationId
      )
    },
    
    paymentFailed: {
      subscribe: withFilter(
        () => pubsub.asyncIterator([SUBSCRIPTION_EVENTS.PAYMENT_FAILED]),
        (payload, variables) => payload.userId === variables.userId
      )
    },
    
    invoiceGenerated: {
      subscribe: withFilter(
        () => pubsub.asyncIterator([SUBSCRIPTION_EVENTS.INVOICE_GENERATED]),
        (payload, variables) => payload.userId === variables.userId
      )
    }
  }
};

// Export pubsub for use in other resolvers
export { pubsub };