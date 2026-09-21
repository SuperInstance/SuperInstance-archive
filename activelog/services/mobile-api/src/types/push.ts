// Push Notification Types
export interface PushNotification {
  id: string;
  userId: string;
  deviceToken: string;
  platform: PushPlatform;
  payload: PushPayload;
  options?: PushOptions;
  status: PushStatus;
  createdAt: Date;
  sentAt: Date | null;
  deliveredAt: Date | null;
  errorMessage: string | null;
  retryCount: number;
}

export enum PushPlatform {
  ANDROID = 0,
  IOS = 1,
  WEB = 2
}

export interface PushPayload {
  title: string;
  body: string;
  icon?: string;
  image?: string;
  sound?: string;
  badge?: number;
  color?: string;
  tag?: string;
  clickAction?: string;
  data?: { [key: string]: string };
  android?: AndroidPayload;
  ios?: IOSPayload;
  web?: WebPayload;
}

export interface AndroidPayload {
  channelId?: string;
  priority?: AndroidPriority;
  ttl?: number;
  collapseKey?: boolean;
  restrictedPackageName?: string;
  notification?: AndroidNotification;
}

export enum AndroidPriority {
  NORMAL_ANDROID = 0,
  HIGH_ANDROID = 1
}

export interface AndroidNotification {
  title?: string;
  body?: string;
  icon?: string;
  color?: string;
  sound?: string;
  tag?: string;
  clickAction?: string;
  bodyLocKey?: string;
  bodyLocArgs?: string[];
  titleLocKey?: string;
  titleLocArgs?: string[];
  channelId?: string;
  visibility?: AndroidVisibility;
  notificationPriority?: number;
  defaultSound?: boolean;
  defaultVibrateTimings?: boolean;
  defaultLightSettings?: boolean;
  vibrateTimings?: number[];
  lightSettings?: LightSettings;
  notificationCount?: number;
}

export enum AndroidVisibility {
  PRIVATE = 0,
  PUBLIC = 1,
  SECRET = 2
}

export interface LightSettings {
  color: number;
  lightOnDuration: number;
  lightOffDuration: number;
}

export interface IOSPayload {
  alert?: IOSAlert;
  badge?: number;
  sound?: string;
  contentAvailable?: boolean;
  mutableContent?: boolean;
  category?: string;
  threadId?: string;
  priority?: IOSPriority;
  apnsPushType?: string;
  apnsExpiration?: string;
  apnsCollapseId?: string;
}

export enum IOSPriority {
  CONSERVE_POWER = 0,
  SEND_IMMEDIATELY = 1
}

export interface IOSAlert {
  title?: string;
  subtitle?: string;
  body?: string;
  launchImage?: string;
  titleLocKey?: string;
  titleLocArgs?: string[];
  subtitleLocKey?: string;
  subtitleLocArgs?: string[];
  locKey?: string;
  locArgs?: string[];
}

export interface WebPayload {
  icon?: string;
  image?: string;
  badge?: string;
  actions?: WebAction[];
  dir?: string;
  lang?: string;
  renotify?: boolean;
  requireInteraction?: boolean;
  silent?: boolean;
  tag?: string;
  timestamp?: number;
  vibrate?: number[];
}

export interface WebAction {
  action: string;
  title: string;
  icon?: string;
}

export interface PushOptions {
  priority?: PushPriority;
  ttlSeconds?: number;
  dryRun?: boolean;
  collapseKey?: string;
  contentAvailable?: boolean;
  topic?: string;
  tags?: string[];
  scheduling?: SchedulingOptions;
  targeting?: TargetingOptions;
}

export enum PushPriority {
  LOW_PUSH = 0,
  NORMAL_PUSH = 1,
  HIGH_PUSH = 2
}

export interface SchedulingOptions {
  sendAt?: Date;
  timezone?: string;
  allowedHours?: number[];
  allowedDays?: number[];
  respectUserTimezone?: boolean;
}

export interface TargetingOptions {
  deviceTokens?: string[];
  userIds?: string[];
  segments?: string[];
  userProperties?: { [key: string]: string };
  deviceTargeting?: DeviceTargeting;
  locationTargeting?: LocationTargeting;
}

export interface DeviceTargeting {
  platforms?: PushPlatform[];
  appVersions?: string[];
  osVersions?: string[];
  deviceTypes?: string[];
  languages?: string[];
}

export interface LocationTargeting {
  countries?: string[];
  regions?: string[];
  cities?: string[];
  geoFence?: GeoFence;
}

export interface GeoFence {
  latitude: number;
  longitude: number;
  radiusMeters: number;
}

export enum PushStatus {
  PENDING = 0,
  SENT = 1,
  DELIVERED = 2,
  FAILED = 3,
  CANCELLED = 4,
  EXPIRED = 5
}

export interface DeviceRegistration {
  userId: string;
  deviceToken: string;
  platform: PushPlatform;
  appVersion?: string;
  osVersion?: string;
  deviceModel?: string;
  deviceName?: string;
  notificationsEnabled: boolean;
  subscribedTopics?: string[];
  metadata?: { [key: string]: string };
  registeredAt: Date;
  lastActiveAt: Date;
}

export interface PushCampaign {
  id: string;
  name: string;
  description?: string;
  type: CampaignType;
  status: CampaignStatus;
  payload: PushPayload;
  targeting?: TargetingOptions;
  scheduling?: SchedulingOptions;
  options?: PushOptions;
  stats?: CampaignStats;
  createdAt: Date;
  updatedAt: Date;
  sentAt?: Date;
}

export enum CampaignType {
  IMMEDIATE = 0,
  SCHEDULED = 1,
  RECURRING = 2,
  TRIGGERED = 3
}

export enum CampaignStatus {
  DRAFT = 0,
  SCHEDULED_CAMPAIGN = 1,
  SENDING = 2,
  SENT_CAMPAIGN = 3,
  PAUSED = 4,
  CANCELLED_CAMPAIGN = 5,
  COMPLETED = 6
}

export interface CampaignStats {
  targetCount: number;
  sentCount: number;
  deliveredCount: number;
  openedCount: number;
  clickedCount: number;
  failedCount: number;
  deliveryRate: number;
  openRate: number;
  clickRate: number;
}