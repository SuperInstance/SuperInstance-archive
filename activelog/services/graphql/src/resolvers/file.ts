import { Context } from '@/types/context';

export const fileResolvers = {
  Query: {
    file: async (_: any, { id }: { id: string }, { loaders }: Context) => {
      return loaders.fileLoader.load(id);
    },
    
    files: async (_: any, { pagination, filter }: any, { dataSources }: Context) => {
      return dataSources.fileAPI.getFilesByUserId('');
    }
  },
  
  Mutation: {
    uploadFile: async (_: any, { input }: any, { user, dataSources }: Context) => {
      if (!user) throw new Error('Not authenticated');
      return dataSources.fileAPI.uploadFile({ ...input, userId: user.id });
    }
  },
  
  Subscription: {
    fileUploaded: {
      subscribe: () => {
        // Implementation in subscription resolver
      }
    }
  },
  
  File: {
    owner: async (file: any, _: any, { loaders }: Context) => {
      return loaders.userLoader.load(file.ownerId);
    }
  }
};