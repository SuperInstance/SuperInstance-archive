import { Request, Response } from 'express';
import { DataLoaders } from '@/dataloaders';

// User type
export interface User {
  id: string;
  email: string;
  role: 'USER' | 'ADMIN' | 'SUPER_ADMIN' | 'SERVICE';
  organizationId?: string;
  permissions: string[];
  friends: string[];
  teamMembers: string[];
}

// Data Sources interfaces
export interface UserAPI {
  getUserById(id: string): Promise<User | null>;
  getUsersByIds(ids: string[]): Promise<User[]>;
  getUsersByEmails(emails: string[]): Promise<User[]>;
  createUser(input: any): Promise<User>;
  updateUser(id: string, input: any): Promise<User>;
  deleteUser(id: string): Promise<boolean>;
  getUserPreferences(id: string): Promise<any>;
}

export interface FileAPI {
  getFileById(id: string): Promise<any>;
  getFilesByIds(ids: string[]): Promise<any[]>;
  getFilesByUserId(userId: string): Promise<any[]>;
  getFilesByFolderId(folderId: string): Promise<any[]>;
  getFoldersByIds(ids: string[]): Promise<any[]>;
  getFoldersByParentId(parentId: string): Promise<any[]>;
  uploadFile(input: any): Promise<any>;
  updateFile(id: string, input: any): Promise<any>;
  deleteFile(id: string): Promise<boolean>;
}

export interface VideoAPI {
  getVideoById(id: string): Promise<any>;
  getVideosByIds(ids: string[]): Promise<any[]>;
  getVideosByUserId(userId: string): Promise<any[]>;
  getProcessingJobsByVideoId(videoId: string): Promise<any[]>;
  createVideo(input: any): Promise<any>;
  updateVideo(id: string, input: any): Promise<any>;
  processVideo(id: string, input: any): Promise<any>;
}

export interface PluginAPI {
  getPluginById(id: string): Promise<any>;
  getPluginsByIds(ids: string[]): Promise<any[]>;
  getInstalledPlugins(userId: string): Promise<any[]>;
  getExecutionsByPluginId(pluginId: string): Promise<any[]>;
  installPlugin(userId: string, pluginId: string): Promise<any>;
  executePlugin(input: any): Promise<any>;
}

export interface OrganizationAPI {
  getOrganizationById(id: string): Promise<any>;
  getOrganizationsByIds(ids: string[]): Promise<any[]>;
  getMembersByOrgId(orgId: string): Promise<any[]>;
  getOrganizationsByUserId(userId: string): Promise<any[]>;
  getTeamsByIds(ids: string[]): Promise<any[]>;
  getTeamMembersByTeamId(teamId: string): Promise<any[]>;
  createOrganization(input: any): Promise<any>;
  updateOrganization(id: string, input: any): Promise<any>;
}

export interface AnalyticsAPI {
  getDashboardById(id: string): Promise<any>;
  getDashboardsByIds(ids: string[]): Promise<any[]>;
  getDashboardsByUserId(userId: string): Promise<any[]>;
  getMetricsByIds(ids: string[]): Promise<any[]>;
  getAnalytics(input: any): Promise<any>;
  createDashboard(input: any): Promise<any>;
  updateDashboard(id: string, input: any): Promise<any>;
}

export interface NotificationAPI {
  getNotificationById(id: string): Promise<any>;
  getNotificationsByIds(ids: string[]): Promise<any[]>;
  getNotificationsByUserId(userId: string): Promise<any[]>;
  getUnreadCount(userId: string): Promise<number>;
  createNotification(input: any): Promise<any>;
  markAsRead(id: string): Promise<boolean>;
  updateSettings(userId: string, input: any): Promise<any>;
}

export interface SubscriptionAPI {
  getSubscriptionById(id: string): Promise<any>;
  getSubscriptionsByIds(ids: string[]): Promise<any[]>;
  getSubscriptionsByUserId(userId: string): Promise<any[]>;
  getCurrentSubscription(userId: string): Promise<any>;
  getActiveSubscriptions(userId: string): Promise<any[]>;
  getPlans(): Promise<any[]>;
  getUsageMetrics(orgId: string, options?: any): Promise<any>;
  getBillingHistory(userId: string, options?: any): Promise<any>;
  getPaymentMethods(userId: string): Promise<any[]>;
  getInvoice(id: string, userId: string): Promise<any>;
  getUpcomingInvoice(userId: string): Promise<any>;
  createSubscription(userId: string, input: any): Promise<any>;
  updateSubscription(userId: string, input: any): Promise<any>;
  cancelSubscription(userId: string, input: any): Promise<any>;
  changePlan(userId: string, input: any): Promise<any>;
  addPaymentMethod(userId: string, input: any): Promise<any>;
  retryPayment(invoiceId: string, userId: string): Promise<any>;
  recordUsage(input: any): Promise<any>;
}

export interface ActivityAPI {
  getActivityById(id: string): Promise<any>;
  getActivitiesByIds(ids: string[]): Promise<any[]>;
  getActivitiesByEntity(entityType: string, entityId: string): Promise<any[]>;
  logActivity(input: any): Promise<any>;
}

export interface PermissionAPI {
  getPermissions(userId: string, resourceType: string, resourceId: string): Promise<any>;
  checkPermission(userId: string, permission: string, resourceId?: string): Promise<boolean>;
  grantPermission(userId: string, permission: string, resourceId?: string): Promise<boolean>;
  revokePermission(userId: string, permission: string, resourceId?: string): Promise<boolean>;
}

export interface DataSources {
  userAPI: UserAPI;
  fileAPI: FileAPI;
  videoAPI: VideoAPI;
  pluginAPI: PluginAPI;
  organizationAPI: OrganizationAPI;
  analyticsAPI: AnalyticsAPI;
  notificationAPI: NotificationAPI;
  subscriptionAPI: SubscriptionAPI;
  activityAPI: ActivityAPI;
  permissionAPI: PermissionAPI;
}

// GraphQL Context
export interface Context {
  req: Request;
  res: Response;
  user?: User;
  dataSources: DataSources;
  loaders: DataLoaders;
  ip: string;
  userAgent: string;
}

// Auth Context
export interface AuthContext extends Context {
  user: User; // Required user for authenticated routes
}