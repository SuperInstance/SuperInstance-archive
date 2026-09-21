import * as Linking from 'expo-linking';
import * as WebBrowser from 'expo-web-browser';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
import { AnalyticsService } from './analytics';
import { CrashReportingService } from './crash-reporting';

export interface DeepLinkConfig {
  scheme: string;
  prefix: string;
  
  // Universal links (iOS) / App links (Android)
  universalLinks: {
    ios: string[];
    android: string[];
  };
  
  // Custom URL schemes
  customSchemes: string[];
  
  // Fallback URLs when app is not installed
  fallbackUrls: {
    ios: string;
    android: string;
    web: string;
  };
  
  // Link validation and security
  allowedDomains: string[];
  requireAuthentication: string[]; // Routes that require user to be logged in
  
  // Analytics and tracking
  trackClicks: boolean;
  trackConversions: boolean;
  utmTracking: boolean;
}

export interface ParsedDeepLink {
  url: string;
  scheme: string;
  hostname: string;
  path: string;
  queryParams: Record<string, string>;
  
  // Parsed route information
  route?: string;
  params?: Record<string, any>;
  
  // Tracking information
  utmSource?: string;
  utmMedium?: string;
  utmCampaign?: string;
  utmContent?: string;
  utmTerm?: string;
  
  // Metadata
  timestamp: Date;
  referrer?: string;
  userAgent?: string;
}

export interface DeepLinkRoute {
  pattern: string;
  screen: string;
  params?: Record<string, any>;
  requireAuth?: boolean;
  
  // Route-specific handling
  handler?: (link: ParsedDeepLink) => Promise<void>;
  validator?: (params: Record<string, any>) => boolean;
  transformer?: (params: Record<string, any>) => Record<string, any>;
}

export interface DeepLinkEvent {
  type: 'link_opened' | 'link_generated' | 'link_shared' | 'fallback_used' | 'route_matched' | 'route_failed';
  url: string;
  route?: string;
  success: boolean;
  timestamp: Date;
  metadata?: Record<string, any>;
}

export interface ShareableLink {
  url: string;
  title: string;
  description?: string;
  imageUrl?: string;
  
  // Campaign tracking
  campaign?: string;
  source?: string;
  medium?: string;
  
  // Expiration and limits
  expiresAt?: Date;
  maxUses?: number;
  currentUses?: number;
  
  // Personalization
  userId?: string;
  customData?: Record<string, any>;
}

class DeepLinkingServiceClass {
  private config: DeepLinkConfig;
  private isInitialized = false;
  private routes: Map<string, DeepLinkRoute> = new Map();
  private pendingLink: ParsedDeepLink | null = null;
  private navigationReadyCallback: ((link: ParsedDeepLink) => void) | null = null;
  private linkHistory: DeepLinkEvent[] = [];
  
  constructor() {
    this.config = {
      scheme: 'activelog',
      prefix: 'https://app.activelog.com',
      
      universalLinks: {
        ios: ['https://app.activelog.com', 'https://activelog.com'],
        android: ['https://app.activelog.com', 'https://activelog.com']
      },
      
      customSchemes: ['activelog://', 'personallog://', 'businesslog://', 'familylog://', 'fitnesslog://', 'travellog://', 'educationlog://'],
      
      fallbackUrls: {
        ios: 'https://apps.apple.com/app/activelog',
        android: 'https://play.google.com/store/apps/details?id=com.activelog',
        web: 'https://activelog.com/download'
      },
      
      allowedDomains: ['activelog.com', 'app.activelog.com', 'share.activelog.com'],
      requireAuthentication: ['/profile', '/settings', '/premium', '/shared-private'],
      
      trackClicks: true,
      trackConversions: true,
      utmTracking: true
    };
  }

  public async initialize(appVariant?: string): Promise<void> {
    try {
      // Customize config for app variant
      this.customizeConfigForVariant(appVariant);
      
      // Set up Expo Linking configuration
      const linkingConfig = {
        prefixes: [this.config.prefix, ...this.config.customSchemes],
        config: {
          screens: this.buildScreenConfig()
        }
      };
      
      // Register default routes
      this.registerDefaultRoutes(appVariant);
      
      // Set up link event listeners
      this.setupLinkListeners();
      
      // Load link history
      await this.loadLinkHistory();
      
      // Check for initial URL (app launched via deep link)
      const initialUrl = await Linking.getInitialURL();
      if (initialUrl) {
        const parsedLink = await this.parseDeepLink(initialUrl);
        if (parsedLink) {
          this.pendingLink = parsedLink;
          this.trackLinkEvent('link_opened', parsedLink.url, true, { source: 'app_launch' });
        }
      }
      
      this.isInitialized = true;
      
      console.log('🔗 Deep Linking Service initialized');
      
      AnalyticsService.track('deep_linking_initialized', {
        app_variant: appVariant,
        scheme: this.config.scheme,
        universal_links_count: this.config.universalLinks.ios.length + this.config.universalLinks.android.length
      });
      
    } catch (error) {
      console.error('Failed to initialize deep linking service:', error);
      CrashReportingService.recordError(error as Error, {
        service: 'deep_linking',
        action: 'initialize'
      });
    }
  }

  public async handleDeepLink(url: string): Promise<boolean> {
    if (!this.isInitialized) {
      console.warn('Deep linking service not initialized');
      return false;
    }

    try {
      const parsedLink = await this.parseDeepLink(url);
      if (!parsedLink) {
        console.warn('Failed to parse deep link:', url);
        return false;
      }
      
      // Validate link security
      if (!this.validateLinkSecurity(parsedLink)) {
        console.warn('Deep link failed security validation:', url);
        this.trackLinkEvent('route_failed', url, false, { reason: 'security_validation' });
        return false;
      }
      
      // Find matching route
      const route = this.findMatchingRoute(parsedLink);
      if (!route) {
        console.warn('No matching route found for deep link:', parsedLink.path);
        this.trackLinkEvent('route_failed', url, false, { reason: 'no_matching_route' });
        return false;
      }
      
      // Check authentication requirements
      if (route.requireAuth && !await this.isUserAuthenticated()) {
        console.log('Route requires authentication, storing pending link');
        this.pendingLink = parsedLink;
        this.trackLinkEvent('route_failed', url, false, { reason: 'authentication_required' });
        
        // Navigate to login screen
        if (this.navigationReadyCallback) {
          this.navigationReadyCallback({ 
            ...parsedLink, 
            route: '/login',
            params: { returnUrl: url }
          });
        }
        return true;
      }
      
      // Validate route parameters
      if (route.validator && !route.validator(parsedLink.params || {})) {
        console.warn('Route parameters failed validation:', parsedLink.params);
        this.trackLinkEvent('route_failed', url, false, { reason: 'parameter_validation' });
        return false;
      }
      
      // Transform parameters if needed
      let finalParams = parsedLink.params || {};
      if (route.transformer) {
        finalParams = route.transformer(finalParams);
      }
      
      // Execute custom handler if provided
      if (route.handler) {
        await route.handler({ ...parsedLink, params: finalParams });
      }
      
      // Navigate to the route
      const navigationLink: ParsedDeepLink = {
        ...parsedLink,
        route: route.screen,
        params: { ...finalParams, ...route.params }
      };
      
      if (this.navigationReadyCallback) {
        this.navigationReadyCallback(navigationLink);
      } else {
        // Store for later when navigation is ready
        this.pendingLink = navigationLink;
      }
      
      this.trackLinkEvent('route_matched', url, true, { 
        route: route.screen,
        params: finalParams
      });
      
      return true;
      
    } catch (error) {
      console.error('Error handling deep link:', error);
      CrashReportingService.recordError(error as Error, {
        service: 'deep_linking',
        action: 'handle_deep_link',
        url
      });
      
      this.trackLinkEvent('route_failed', url, false, { 
        reason: 'exception',
        error: error instanceof Error ? error.message : 'Unknown error'
      });
      
      return false;
    }
  }

  public onNavigationReady(callback: (link: ParsedDeepLink) => void): void {
    this.navigationReadyCallback = callback;
    
    // If there's a pending link, handle it now
    if (this.pendingLink) {
      callback(this.pendingLink);
      this.pendingLink = null;
    }
  }

  public async generateShareableLink(
    route: string,
    params: Record<string, any> = {},
    options: Partial<ShareableLink> = {}
  ): Promise<string> {
    try {
      const baseUrl = this.config.prefix;
      const queryParams = new URLSearchParams();
      
      // Add route parameters
      Object.entries(params).forEach(([key, value]) => {
        queryParams.append(key, String(value));
      });
      
      // Add UTM tracking parameters
      if (this.config.utmTracking) {
        if (options.campaign) queryParams.append('utm_campaign', options.campaign);
        if (options.source) queryParams.append('utm_source', options.source);
        if (options.medium) queryParams.append('utm_medium', options.medium);
        
        // Add default tracking if not provided
        if (!options.source) queryParams.append('utm_source', 'app_share');
        if (!options.medium) queryParams.append('utm_medium', 'deep_link');
      }
      
      // Add custom tracking
      if (options.userId) queryParams.append('shared_by', options.userId);
      if (options.customData) {
        Object.entries(options.customData).forEach(([key, value]) => {
          queryParams.append(`custom_${key}`, String(value));
        });
      }
      
      // Build final URL
      const finalUrl = `${baseUrl}${route}?${queryParams.toString()}`;
      
      // Store shareable link metadata
      await this.storeShareableLinkMetadata(finalUrl, options);
      
      this.trackLinkEvent('link_generated', finalUrl, true, {
        route,
        params,
        campaign: options.campaign,
        source: options.source
      });
      
      AnalyticsService.track('deep_link_generated', {
        route,
        params,
        campaign: options.campaign,
        source: options.source,
        user_id: options.userId
      });
      
      return finalUrl;
      
    } catch (error) {
      console.error('Error generating shareable link:', error);
      CrashReportingService.recordError(error as Error, {
        service: 'deep_linking',
        action: 'generate_shareable_link',
        route,
        params
      });
      
      // Return fallback URL
      return `${this.config.prefix}${route}`;
    }
  }

  public async shareLink(
    route: string,
    params: Record<string, any> = {},
    shareOptions: {
      title: string;
      message?: string;
      url?: string;
      campaign?: string;
    } = { title: 'Check this out!' }
  ): Promise<boolean> {
    try {
      const shareUrl = shareOptions.url || await this.generateShareableLink(route, params, {
        campaign: shareOptions.campaign,
        source: 'native_share',
        medium: 'social'
      });
      
      // Use native sharing where available
      if (Platform.OS === 'ios' || Platform.OS === 'android') {
        const { Share } = require('react-native');
        const result = await Share.share({
          title: shareOptions.title,
          message: shareOptions.message || shareOptions.title,
          url: shareUrl
        });
        
        const success = result.action === Share.sharedAction;
        
        this.trackLinkEvent('link_shared', shareUrl, success, {
          platform: Platform.OS,
          route,
          campaign: shareOptions.campaign
        });
        
        return success;
      } else {
        // Web fallback
        if (navigator.share) {
          await navigator.share({
            title: shareOptions.title,
            text: shareOptions.message,
            url: shareUrl
          });
          
          this.trackLinkEvent('link_shared', shareUrl, true, {
            platform: 'web',
            method: 'native',
            route
          });
          
          return true;
        } else {
          // Fallback to clipboard
          await navigator.clipboard.writeText(shareUrl);
          console.log('Link copied to clipboard');
          
          this.trackLinkEvent('link_shared', shareUrl, true, {
            platform: 'web',
            method: 'clipboard',
            route
          });
          
          return true;
        }
      }
    } catch (error) {
      console.error('Error sharing link:', error);
      CrashReportingService.recordError(error as Error, {
        service: 'deep_linking',
        action: 'share_link',
        route
      });
      
      this.trackLinkEvent('link_shared', '', false, {
        route,
        error: error instanceof Error ? error.message : 'Unknown error'
      });
      
      return false;
    }
  }

  public async openExternalLink(url: string, inApp: boolean = false): Promise<boolean> {
    try {
      if (inApp && (Platform.OS === 'ios' || Platform.OS === 'android')) {
        // Open in in-app browser
        const result = await WebBrowser.openBrowserAsync(url, {
          presentationStyle: WebBrowser.WebBrowserPresentationStyle.FULL_SCREEN,
          controlsColor: '#007AFF',
          showTitle: true,
          enableBarCollapsing: true
        });
        
        AnalyticsService.track('external_link_opened', {
          url,
          method: 'in_app_browser',
          result: result.type
        });
        
        return result.type === WebBrowser.WebBrowserResultType.DISMISS;
      } else {
        // Open in system browser
        const supported = await Linking.canOpenURL(url);
        if (supported) {
          await Linking.openURL(url);
          
          AnalyticsService.track('external_link_opened', {
            url,
            method: 'system_browser',
            supported
          });
          
          return true;
        } else {
          console.warn('Cannot open URL:', url);
          return false;
        }
      }
    } catch (error) {
      console.error('Error opening external link:', error);
      CrashReportingService.recordError(error as Error, {
        service: 'deep_linking',
        action: 'open_external_link',
        url
      });
      return false;
    }
  }

  public registerRoute(pattern: string, route: Omit<DeepLinkRoute, 'pattern'>): void {
    this.routes.set(pattern, { pattern, ...route });
  }

  public getPendingLink(): ParsedDeepLink | null {
    return this.pendingLink;
  }

  public clearPendingLink(): void {
    this.pendingLink = null;
  }

  public getConfig(): DeepLinkConfig {
    return { ...this.config };
  }

  public updateConfig(updates: Partial<DeepLinkConfig>): void {
    this.config = { ...this.config, ...updates };
  }

  public getLinkHistory(): DeepLinkEvent[] {
    return [...this.linkHistory];
  }

  private async parseDeepLink(url: string): Promise<ParsedDeepLink | null> {
    try {
      const parsed = Linking.parse(url);
      const urlObj = new URL(url);
      
      const queryParams: Record<string, string> = {};
      urlObj.searchParams.forEach((value, key) => {
        queryParams[key] = value;
      });
      
      const result: ParsedDeepLink = {
        url,
        scheme: parsed.scheme || '',
        hostname: parsed.hostname || '',
        path: parsed.path || '/',
        queryParams,
        timestamp: new Date()
      };
      
      // Extract UTM parameters
      if (this.config.utmTracking) {
        result.utmSource = queryParams.utm_source;
        result.utmMedium = queryParams.utm_medium;
        result.utmCampaign = queryParams.utm_campaign;
        result.utmContent = queryParams.utm_content;
        result.utmTerm = queryParams.utm_term;
      }
      
      // Convert query params to route params
      result.params = { ...queryParams };
      
      // Remove UTM params from route params
      ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'].forEach(param => {
        delete result.params![param];
      });
      
      return result;
    } catch (error) {
      console.error('Error parsing deep link:', error);
      return null;
    }
  }

  private validateLinkSecurity(link: ParsedDeepLink): boolean {
    // Check allowed domains
    if (this.config.allowedDomains.length > 0) {
      if (!this.config.allowedDomains.includes(link.hostname)) {
        return false;
      }
    }
    
    // Add more security validations as needed
    // - Check for malicious parameters
    // - Validate URL structure
    // - Check for suspicious patterns
    
    return true;
  }

  private findMatchingRoute(link: ParsedDeepLink): DeepLinkRoute | null {
    for (const route of this.routes.values()) {
      if (this.matchPattern(route.pattern, link.path)) {
        return route;
      }
    }
    return null;
  }

  private matchPattern(pattern: string, path: string): boolean {
    // Simple pattern matching - can be enhanced with more sophisticated regex
    const patternRegex = pattern
      .replace(/:[^/]+/g, '([^/]+)') // Replace :param with capture group
      .replace(/\*/g, '.*'); // Replace * with wildcard
    
    const regex = new RegExp(`^${patternRegex}$`);
    return regex.test(path);
  }

  private async isUserAuthenticated(): Promise<boolean> {
    try {
      const userId = await AsyncStorage.getItem('user_id');
      return userId !== null;
    } catch {
      return false;
    }
  }

  private customizeConfigForVariant(appVariant?: string): void {
    if (!appVariant) return;
    
    // Customize schemes and prefixes for app variant
    const variantScheme = `${appVariant.replace('-', '')}://`;
    this.config.customSchemes.unshift(variantScheme);
    
    // Update fallback URLs
    this.config.fallbackUrls.ios = `https://apps.apple.com/app/${appVariant}`;
    this.config.fallbackUrls.android = `https://play.google.com/store/apps/details?id=com.activelog.${appVariant.replace('-', '')}`;
  }

  private registerDefaultRoutes(appVariant?: string): void {
    // Register common routes
    this.registerRoute('/', { screen: 'Home' });
    this.registerRoute('/home', { screen: 'Home' });
    this.registerRoute('/profile', { screen: 'Profile', requireAuth: true });
    this.registerRoute('/settings', { screen: 'Settings', requireAuth: true });
    this.registerRoute('/premium', { screen: 'Premium' });
    
    // App variant specific routes
    switch (appVariant) {
      case 'personal-log':
        this.registerRoute('/entry/:id', { screen: 'JournalEntry' });
        this.registerRoute('/insights', { screen: 'Insights', requireAuth: true });
        this.registerRoute('/mood', { screen: 'MoodTracker', requireAuth: true });
        break;
        
      case 'business-log':
        this.registerRoute('/project/:id', { screen: 'ProjectView' });
        this.registerRoute('/team', { screen: 'TeamDashboard', requireAuth: true });
        this.registerRoute('/reports', { screen: 'Reports', requireAuth: true });
        break;
        
      case 'fitness-log':
        this.registerRoute('/workout/:id', { screen: 'WorkoutView' });
        this.registerRoute('/progress', { screen: 'ProgressCharts', requireAuth: true });
        this.registerRoute('/goals', { screen: 'Goals', requireAuth: true });
        break;
        
      case 'family-log':
        this.registerRoute('/memory/:id', { screen: 'MemoryView' });
        this.registerRoute('/calendar', { screen: 'FamilyCalendar', requireAuth: true });
        this.registerRoute('/albums', { screen: 'PhotoAlbums', requireAuth: true });
        break;
        
      case 'travel-log':
        this.registerRoute('/trip/:id', { screen: 'TripView' });
        this.registerRoute('/map', { screen: 'TravelMap', requireAuth: true });
        this.registerRoute('/expenses', { screen: 'ExpenseTracker', requireAuth: true });
        break;
        
      case 'education-log':
        this.registerRoute('/course/:id', { screen: 'CourseView' });
        this.registerRoute('/schedule', { screen: 'StudySchedule', requireAuth: true });
        this.registerRoute('/grades', { screen: 'GradeTracker', requireAuth: true });
        break;
    }
    
    // Shared content routes
    this.registerRoute('/shared/:type/:id', { 
      screen: 'SharedContent',
      handler: async (link) => {
        // Track shared content access
        AnalyticsService.track('shared_content_accessed', {
          content_type: link.params?.type,
          content_id: link.params?.id,
          utm_source: link.utmSource,
          utm_campaign: link.utmCampaign
        });
      }
    });
  }

  private setupLinkListeners(): void {
    // Listen for incoming links when app is running
    const subscription = Linking.addEventListener('url', (event) => {
      this.handleDeepLink(event.url);
    });
    
    // Store subscription for cleanup if needed
    // In a real app, you'd want to clean this up appropriately
  }

  private buildScreenConfig(): Record<string, any> {
    const screens: Record<string, any> = {};
    
    for (const route of this.routes.values()) {
      screens[route.screen] = route.pattern;
    }
    
    return screens;
  }

  private trackLinkEvent(type: DeepLinkEvent['type'], url: string, success: boolean, metadata?: Record<string, any>): void {
    const event: DeepLinkEvent = {
      type,
      url,
      success,
      timestamp: new Date(),
      metadata
    };
    
    this.linkHistory.unshift(event);
    
    // Keep only recent history
    if (this.linkHistory.length > 100) {
      this.linkHistory = this.linkHistory.slice(0, 100);
    }
    
    // Save to storage
    this.saveLinkHistory();
    
    // Track in analytics
    if (this.config.trackClicks) {
      AnalyticsService.track('deep_link_event', {
        event_type: type,
        url,
        success,
        ...metadata
      });
    }
  }

  private async storeShareableLinkMetadata(url: string, options: Partial<ShareableLink>): Promise<void> {
    try {
      const key = `shareable_link_${this.hashUrl(url)}`;
      const metadata = {
        url,
        createdAt: new Date().toISOString(),
        ...options
      };
      
      await AsyncStorage.setItem(key, JSON.stringify(metadata));
    } catch (error) {
      console.error('Error storing shareable link metadata:', error);
    }
  }

  private async loadLinkHistory(): Promise<void> {
    try {
      const stored = await AsyncStorage.getItem('deep_link_history');
      if (stored) {
        const history: DeepLinkEvent[] = JSON.parse(stored);
        this.linkHistory = history.map(event => ({
          ...event,
          timestamp: new Date(event.timestamp)
        }));
      }
    } catch (error) {
      console.error('Error loading link history:', error);
    }
  }

  private async saveLinkHistory(): Promise<void> {
    try {
      await AsyncStorage.setItem('deep_link_history', JSON.stringify(this.linkHistory));
    } catch (error) {
      console.error('Error saving link history:', error);
    }
  }

  private hashUrl(url: string): string {
    let hash = 0;
    for (let i = 0; i < url.length; i++) {
      const char = url.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return Math.abs(hash).toString(36);
  }

  public async clearHistory(): Promise<void> {
    this.linkHistory = [];
    await AsyncStorage.removeItem('deep_link_history');
  }

  public getDebugInfo(): any {
    return {
      isInitialized: this.isInitialized,
      config: this.config,
      registeredRoutesCount: this.routes.size,
      pendingLink: this.pendingLink,
      linkHistoryCount: this.linkHistory.length,
      registeredRoutes: Array.from(this.routes.entries()).map(([pattern, route]) => ({
        pattern,
        screen: route.screen,
        requireAuth: route.requireAuth
      }))
    };
  }
}

export const DeepLinkingService = new DeepLinkingServiceClass();