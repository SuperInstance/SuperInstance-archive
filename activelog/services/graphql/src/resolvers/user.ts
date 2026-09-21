import { Context } from '@/types/context';

export const userResolvers = {
  Query: {
    me: async (_: any, __: any, { user }: Context) => {
      if (!user) throw new Error('Not authenticated');
      return user;
    },
    
    user: async (_: any, { id }: { id: string }, { dataSources, loaders }: Context) => {
      return loaders.userLoader.load(id);
    },
    
    users: async (_: any, { pagination, filter }: any, { dataSources }: Context) => {
      return dataSources.userAPI.getUsersByIds([]);
    }
  },
  
  Mutation: {
    updateProfile: async (_: any, { input }: any, { user, dataSources }: Context) => {
      if (!user) throw new Error('Not authenticated');
      return dataSources.userAPI.updateUser(user.id, input);
    }
  },
  
  Subscription: {
    userUpdated: {
      subscribe: () => {
        // Subscription implementation handled in subscription resolver
      }
    }
  },
  
  User: {
    organizations: async (user: any, _: any, { loaders }: Context) => {
      return loaders.userOrganizationsLoader.load(user.id);
    }
  }
};