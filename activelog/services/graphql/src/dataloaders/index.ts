import DataLoader from 'dataloader';
import { DataSources } from '@/types/context';

// User DataLoaders
export const createUserLoader = (dataSources: DataSources) => 
  new DataLoader(async (userIds: readonly string[]) => {
    const users = await dataSources.userAPI.getUsersByIds([...userIds]);
    return userIds.map(id => users.find(user => user.id === id) || null);
  });

export const createUserByEmailLoader = (dataSources: DataSources) =>
  new DataLoader(async (emails: readonly string[]) => {
    const users = await dataSources.userAPI.getUsersByEmails([...emails]);
    return emails.map(email => users.find(user => user.email === email) || null);
  });

// File DataLoaders
export const createFileLoader = (dataSources: DataSources) =>
  new DataLoader(async (fileIds: readonly string[]) => {
    const files = await dataSources.fileAPI.getFilesByIds([...fileIds]);
    return fileIds.map(id => files.find(file => file.id === id) || null);
  });

export const createFilesByUserLoader = (dataSources: DataSources) =>
  new DataLoader(async (userIds: readonly string[]) => {
    const results = await Promise.all(
      userIds.map(userId => dataSources.fileAPI.getFilesByUserId(userId))
    );
    return results;
  });

export const createFilesByFolderLoader = (dataSources: DataSources) =>
  new DataLoader(async (folderIds: readonly string[]) => {
    const results = await Promise.all(
      folderIds.map(folderId => dataSources.fileAPI.getFilesByFolderId(folderId))
    );
    return results;
  });

// Folder DataLoaders
export const createFolderLoader = (dataSources: DataSources) =>
  new DataLoader(async (folderIds: readonly string[]) => {
    const folders = await dataSources.fileAPI.getFoldersByIds([...folderIds]);
    return folderIds.map(id => folders.find(folder => folder.id === id) || null);
  });

export const createFoldersByParentLoader = (dataSources: DataSources) =>
  new DataLoader(async (parentIds: readonly string[]) => {
    const results = await Promise.all(
      parentIds.map(parentId => dataSources.fileAPI.getFoldersByParentId(parentId))
    );
    return results;
  });

// Video DataLoaders
export const createVideoLoader = (dataSources: DataSources) =>
  new DataLoader(async (videoIds: readonly string[]) => {
    const videos = await dataSources.videoAPI.getVideosByIds([...videoIds]);
    return videoIds.map(id => videos.find(video => video.id === id) || null);
  });

export const createVideosByUserLoader = (dataSources: DataSources) =>
  new DataLoader(async (userIds: readonly string[]) => {
    const results = await Promise.all(
      userIds.map(userId => dataSources.videoAPI.getVideosByUserId(userId))
    );
    return results;
  });

export const createVideoProcessingJobsLoader = (dataSources: DataSources) =>
  new DataLoader(async (videoIds: readonly string[]) => {
    const results = await Promise.all(
      videoIds.map(videoId => dataSources.videoAPI.getProcessingJobsByVideoId(videoId))
    );
    return results;
  });

// Plugin DataLoaders
export const createPluginLoader = (dataSources: DataSources) =>
  new DataLoader(async (pluginIds: readonly string[]) => {
    const plugins = await dataSources.pluginAPI.getPluginsByIds([...pluginIds]);
    return pluginIds.map(id => plugins.find(plugin => plugin.id === id) || null);
  });

export const createInstalledPluginsLoader = (dataSources: DataSources) =>
  new DataLoader(async (userIds: readonly string[]) => {
    const results = await Promise.all(
      userIds.map(userId => dataSources.pluginAPI.getInstalledPlugins(userId))
    );
    return results;
  });

export const createPluginExecutionsLoader = (dataSources: DataSources) =>
  new DataLoader(async (pluginIds: readonly string[]) => {
    const results = await Promise.all(
      pluginIds.map(pluginId => dataSources.pluginAPI.getExecutionsByPluginId(pluginId))
    );
    return results;
  });

// Organization DataLoaders
export const createOrganizationLoader = (dataSources: DataSources) =>
  new DataLoader(async (orgIds: readonly string[]) => {
    const orgs = await dataSources.organizationAPI.getOrganizationsByIds([...orgIds]);
    return orgIds.map(id => orgs.find(org => org.id === id) || null);
  });

export const createOrganizationMembersLoader = (dataSources: DataSources) =>
  new DataLoader(async (orgIds: readonly string[]) => {
    const results = await Promise.all(
      orgIds.map(orgId => dataSources.organizationAPI.getMembersByOrgId(orgId))
    );
    return results;
  });

export const createUserOrganizationsLoader = (dataSources: DataSources) =>
  new DataLoader(async (userIds: readonly string[]) => {
    const results = await Promise.all(
      userIds.map(userId => dataSources.organizationAPI.getOrganizationsByUserId(userId))
    );
    return results;
  });

// Team DataLoaders
export const createTeamLoader = (dataSources: DataSources) =>
  new DataLoader(async (teamIds: readonly string[]) => {
    const teams = await dataSources.organizationAPI.getTeamsByIds([...teamIds]);
    return teamIds.map(id => teams.find(team => team.id === id) || null);
  });

export const createTeamMembersLoader = (dataSources: DataSources) =>
  new DataLoader(async (teamIds: readonly string[]) => {
    const results = await Promise.all(
      teamIds.map(teamId => dataSources.organizationAPI.getTeamMembersByTeamId(teamId))
    );
    return results;
  });

// Analytics DataLoaders
export const createDashboardLoader = (dataSources: DataSources) =>
  new DataLoader(async (dashboardIds: readonly string[]) => {
    const dashboards = await dataSources.analyticsAPI.getDashboardsByIds([...dashboardIds]);
    return dashboardIds.map(id => dashboards.find(dashboard => dashboard.id === id) || null);
  });

export const createDashboardsByUserLoader = (dataSources: DataSources) =>
  new DataLoader(async (userIds: readonly string[]) => {
    const results = await Promise.all(
      userIds.map(userId => dataSources.analyticsAPI.getDashboardsByUserId(userId))
    );
    return results;
  });

export const createMetricsLoader = (dataSources: DataSources) =>
  new DataLoader(async (metricIds: readonly string[]) => {
    const metrics = await dataSources.analyticsAPI.getMetricsByIds([...metricIds]);
    return metricIds.map(id => metrics.find(metric => metric.id === id) || null);
  });

// Notification DataLoaders
export const createNotificationLoader = (dataSources: DataSources) =>
  new DataLoader(async (notificationIds: readonly string[]) => {
    const notifications = await dataSources.notificationAPI.getNotificationsByIds([...notificationIds]);
    return notificationIds.map(id => notifications.find(notification => notification.id === id) || null);
  });

export const createNotificationsByUserLoader = (dataSources: DataSources) =>
  new DataLoader(async (userIds: readonly string[]) => {
    const results = await Promise.all(
      userIds.map(userId => dataSources.notificationAPI.getNotificationsByUserId(userId))
    );
    return results;
  });

export const createUnreadCountsLoader = (dataSources: DataSources) =>
  new DataLoader(async (userIds: readonly string[]) => {
    const results = await Promise.all(
      userIds.map(userId => dataSources.notificationAPI.getUnreadCount(userId))
    );
    return results;
  });

// Subscription DataLoaders
export const createSubscriptionLoader = (dataSources: DataSources) =>
  new DataLoader(async (subscriptionIds: readonly string[]) => {
    const subscriptions = await dataSources.subscriptionAPI.getSubscriptionsByIds([...subscriptionIds]);
    return subscriptionIds.map(id => subscriptions.find(sub => sub.id === id) || null);
  });

export const createSubscriptionsByUserLoader = (dataSources: DataSources) =>
  new DataLoader(async (userIds: readonly string[]) => {
    const results = await Promise.all(
      userIds.map(userId => dataSources.subscriptionAPI.getSubscriptionsByUserId(userId))
    );
    return results;
  });

export const createUsageMetricsLoader = (dataSources: DataSources) =>
  new DataLoader(async (orgIds: readonly string[]) => {
    const results = await Promise.all(
      orgIds.map(orgId => dataSources.subscriptionAPI.getUsageMetrics(orgId))
    );
    return results;
  });

export const createPaymentMethodsLoader = (dataSources: DataSources) =>
  new DataLoader(async (userIds: readonly string[]) => {
    const results = await Promise.all(
      userIds.map(userId => dataSources.subscriptionAPI.getPaymentMethods(userId))
    );
    return results;
  });

// Activity and Audit DataLoaders
export const createActivityLoader = (dataSources: DataSources) =>
  new DataLoader(async (activityIds: readonly string[]) => {
    const activities = await dataSources.activityAPI.getActivitiesByIds([...activityIds]);
    return activityIds.map(id => activities.find(activity => activity.id === id) || null);
  });

export const createActivitiesByEntityLoader = (dataSources: DataSources) =>
  new DataLoader(async (entityKeys: readonly string[]) => {
    // entityKey format: "entityType:entityId"
    const results = await Promise.all(
      entityKeys.map(key => {
        const [entityType, entityId] = key.split(':');
        return dataSources.activityAPI.getActivitiesByEntity(entityType, entityId);
      })
    );
    return results;
  });

// Permission DataLoaders
export const createPermissionsLoader = (dataSources: DataSources) =>
  new DataLoader(async (permissionKeys: readonly string[]) => {
    // permissionKey format: "userId:resourceType:resourceId"
    const results = await Promise.all(
      permissionKeys.map(key => {
        const [userId, resourceType, resourceId] = key.split(':');
        return dataSources.permissionAPI.getPermissions(userId, resourceType, resourceId);
      })
    );
    return results;
  });

// Create all DataLoaders
export const createDataLoaders = (dataSources: DataSources) => ({
  // User loaders
  userLoader: createUserLoader(dataSources),
  userByEmailLoader: createUserByEmailLoader(dataSources),
  
  // File loaders
  fileLoader: createFileLoader(dataSources),
  filesByUserLoader: createFilesByUserLoader(dataSources),
  filesByFolderLoader: createFilesByFolderLoader(dataSources),
  folderLoader: createFolderLoader(dataSources),
  foldersByParentLoader: createFoldersByParentLoader(dataSources),
  
  // Video loaders
  videoLoader: createVideoLoader(dataSources),
  videosByUserLoader: createVideosByUserLoader(dataSources),
  videoProcessingJobsLoader: createVideoProcessingJobsLoader(dataSources),
  
  // Plugin loaders
  pluginLoader: createPluginLoader(dataSources),
  installedPluginsLoader: createInstalledPluginsLoader(dataSources),
  pluginExecutionsLoader: createPluginExecutionsLoader(dataSources),
  
  // Organization loaders
  organizationLoader: createOrganizationLoader(dataSources),
  organizationMembersLoader: createOrganizationMembersLoader(dataSources),
  userOrganizationsLoader: createUserOrganizationsLoader(dataSources),
  teamLoader: createTeamLoader(dataSources),
  teamMembersLoader: createTeamMembersLoader(dataSources),
  
  // Analytics loaders
  dashboardLoader: createDashboardLoader(dataSources),
  dashboardsByUserLoader: createDashboardsByUserLoader(dataSources),
  metricsLoader: createMetricsLoader(dataSources),
  
  // Notification loaders
  notificationLoader: createNotificationLoader(dataSources),
  notificationsByUserLoader: createNotificationsByUserLoader(dataSources),
  unreadCountsLoader: createUnreadCountsLoader(dataSources),
  
  // Subscription loaders
  subscriptionLoader: createSubscriptionLoader(dataSources),
  subscriptionsByUserLoader: createSubscriptionsByUserLoader(dataSources),
  usageMetricsLoader: createUsageMetricsLoader(dataSources),
  paymentMethodsLoader: createPaymentMethodsLoader(dataSources),
  
  // Activity loaders
  activityLoader: createActivityLoader(dataSources),
  activitiesByEntityLoader: createActivitiesByEntityLoader(dataSources),
  
  // Permission loaders
  permissionsLoader: createPermissionsLoader(dataSources)
});

export type DataLoaders = ReturnType<typeof createDataLoaders>;