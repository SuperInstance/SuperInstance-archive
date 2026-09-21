import Purchases, {
  PurchasesOffering,
  PurchasesPackage,
  CustomerInfo,
  PurchasesError,
  PURCHASE_TYPE,
  PACKAGE_TYPE,
  PurchasesStoreTransaction,
} from 'react-native-purchases';
import { Platform } from 'react-native';
import Constants from 'expo-constants';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface Product {
  identifier: string;
  description: string;
  title: string;
  price: number;
  priceString: string;
  currencyCode: string;
  introPrice?: {
    price: number;
    priceString: string;
    cycles: number;
    period: string;
    periodUnit: string;
  };
}

export interface Subscription extends Product {
  subscriptionPeriod: string;
  subscriptionGroupIdentifier?: string;
  isTrialEligible: boolean;
  trialPeriod?: string;
  discounts?: SubscriptionDiscount[];
}

export interface SubscriptionDiscount {
  identifier: string;
  price: number;
  priceString: string;
  cycles: number;
  period: string;
  periodUnit: string;
  type: 'introductory' | 'promotional';
}

export interface PurchaseResult {
  success: boolean;
  customerInfo?: CustomerInfo;
  userCancelled?: boolean;
  error?: string;
  errorCode?: string;
  transaction?: PurchasesStoreTransaction;
}

export interface RestoreResult {
  success: boolean;
  customerInfo?: CustomerInfo;
  error?: string;
  restoredPurchases: string[];
}

export interface EntitlementInfo {
  identifier: string;
  isActive: boolean;
  willRenew: boolean;
  periodType: string;
  latestPurchaseDate: Date;
  originalPurchaseDate: Date;
  expirationDate?: Date;
  store: string;
  productIdentifier: string;
  isSandbox: boolean;
  unsubscribeDetectedAt?: Date;
  billingIssueDetectedAt?: Date;
}

export interface SubscriptionStatus {
  isActive: boolean;
  isPremium: boolean;
  isBusiness: boolean;
  plan: 'free' | 'premium' | 'business' | 'trial';
  expirationDate?: Date;
  willRenew: boolean;
  isInTrial: boolean;
  trialEndDate?: Date;
  entitlements: EntitlementInfo[];
}

export interface PurchaseOption {
  packageType: PACKAGE_TYPE;
  product: Product | Subscription;
  offeringIdentifier: string;
}

class InAppPurchaseServiceClass {
  private isInitialized = false;
  private customerInfo: CustomerInfo | null = null;
  private offerings: PurchasesOffering[] = [];
  private appVariant: string = 'personal-log';
  private purchaseListeners: ((result: PurchaseResult) => void)[] = [];
  private customerInfoListeners: ((info: CustomerInfo) => void)[] = [];

  // Product identifiers for different app variants
  private readonly PRODUCT_IDS = {
    'personal-log': {
      premium_monthly: 'personal_premium_monthly',
      premium_yearly: 'personal_premium_yearly',
      premium_lifetime: 'personal_premium_lifetime',
    },
    'business-log': {
      business_monthly: 'business_monthly',
      business_yearly: 'business_yearly',
      enterprise_monthly: 'enterprise_monthly',
      enterprise_yearly: 'enterprise_yearly',
    },
    'family-log': {
      family_monthly: 'family_monthly',
      family_yearly: 'family_yearly',
      family_premium_monthly: 'family_premium_monthly',
      family_premium_yearly: 'family_premium_yearly',
    },
    'fitness-log': {
      fitness_premium_monthly: 'fitness_premium_monthly',
      fitness_premium_yearly: 'fitness_premium_yearly',
      fitness_coach_monthly: 'fitness_coach_monthly',
    },
    'travel-log': {
      traveler_monthly: 'traveler_monthly',
      traveler_yearly: 'traveler_yearly',
      explorer_lifetime: 'explorer_lifetime',
    },
    'education-log': {
      student_monthly: 'student_monthly',
      student_yearly: 'student_yearly',
      educator_monthly: 'educator_monthly',
      educator_yearly: 'educator_yearly',
    },
  };

  // Entitlement identifiers
  private readonly ENTITLEMENTS = {
    premium: 'premium_access',
    business: 'business_access',
    family: 'family_access',
    unlimited: 'unlimited_logs',
    sync: 'cloud_sync',
    export: 'export_features',
    analytics: 'advanced_analytics',
    support: 'priority_support',
  };

  public async initialize(appVariant: string): Promise<void> {
    try {
      this.appVariant = appVariant;
      
      // Get API key from config
      const apiKey = Constants.expoConfig?.extra?.revenueCatApiKey;
      if (!apiKey) {
        throw new Error('RevenueCat API key not found in configuration');
      }

      // Configure Purchases
      Purchases.setLogLevel('INFO');
      
      if (Platform.OS === 'ios') {
        await Purchases.configure({
          apiKey: apiKey,
          appUserID: undefined, // Will be set later when user logs in
          observerMode: false,
          userDefaultsSuiteName: undefined,
          useStoreKit2IfAvailable: true,
        });
      } else {
        await Purchases.configure({
          apiKey: apiKey,
          appUserID: undefined,
          observerMode: false,
          useAmazonStore: false,
        });
      }

      // Set up listeners
      this.setupPurchaseListeners();

      // Load initial data
      await this.loadCustomerInfo();
      await this.loadOfferings();

      this.isInitialized = true;
      console.log('💳 In-app purchase service initialized for:', appVariant);
    } catch (error) {
      console.error('Failed to initialize in-app purchases:', error);
      throw error;
    }
  }

  public async setUserID(userID: string): Promise<void> {
    if (!this.isInitialized) {
      throw new Error('In-app purchase service not initialized');
    }

    try {
      await Purchases.logIn(userID);
      await this.loadCustomerInfo();
      console.log('👤 RevenueCat user ID set:', userID);
    } catch (error) {
      console.error('Failed to set user ID:', error);
      throw error;
    }
  }

  public async logOut(): Promise<void> {
    if (!this.isInitialized) return;

    try {
      await Purchases.logOut();
      this.customerInfo = null;
      await AsyncStorage.removeItem('last_customer_info');
      console.log('👋 User logged out from RevenueCat');
    } catch (error) {
      console.error('Failed to log out user:', error);
    }
  }

  public async getOfferings(): Promise<PurchasesOffering[]> {
    if (!this.isInitialized) {
      throw new Error('In-app purchase service not initialized');
    }

    try {
      const offerings = await Purchases.getOfferings();
      this.offerings = Object.values(offerings.all);
      return this.offerings;
    } catch (error) {
      console.error('Failed to get offerings:', error);
      return this.offerings; // Return cached offerings
    }
  }

  public async getCurrentOffering(): Promise<PurchasesOffering | null> {
    try {
      const offerings = await Purchases.getOfferings();
      return offerings.current;
    } catch (error) {
      console.error('Failed to get current offering:', error);
      return null;
    }
  }

  public async purchasePackage(pkg: PurchasesPackage): Promise<PurchaseResult> {
    if (!this.isInitialized) {
      throw new Error('In-app purchase service not initialized');
    }

    try {
      console.log('🛒 Starting purchase:', pkg.identifier);
      
      const { customerInfo, userCancelled } = await Purchases.purchasePackage(pkg);
      
      if (userCancelled) {
        console.log('❌ Purchase cancelled by user');
        return {
          success: false,
          userCancelled: true,
          customerInfo,
        };
      }

      this.customerInfo = customerInfo;
      await this.saveCustomerInfo();

      console.log('✅ Purchase successful:', pkg.identifier);
      
      const result: PurchaseResult = {
        success: true,
        customerInfo,
        userCancelled: false,
      };

      // Notify listeners
      this.notifyPurchaseListeners(result);
      
      return result;
    } catch (error) {
      console.error('❌ Purchase failed:', error);
      
      const purchaseError = error as PurchasesError;
      const result: PurchaseResult = {
        success: false,
        error: purchaseError.message,
        errorCode: purchaseError.code.toString(),
        userCancelled: purchaseError.userCancelled,
      };

      this.notifyPurchaseListeners(result);
      return result;
    }
  }

  public async purchaseProduct(productId: string): Promise<PurchaseResult> {
    try {
      const offerings = await this.getOfferings();
      
      // Find the package with the matching product ID
      let targetPackage: PurchasesPackage | null = null;
      
      for (const offering of offerings) {
        for (const pkg of Object.values(offering.availablePackages)) {
          if (pkg.product.identifier === productId) {
            targetPackage = pkg;
            break;
          }
        }
        if (targetPackage) break;
      }

      if (!targetPackage) {
        throw new Error(`Product not found: ${productId}`);
      }

      return await this.purchasePackage(targetPackage);
    } catch (error) {
      console.error('Failed to purchase product:', error);
      return {
        success: false,
        error: (error as Error).message,
      };
    }
  }

  public async restorePurchases(): Promise<RestoreResult> {
    if (!this.isInitialized) {
      throw new Error('In-app purchase service not initialized');
    }

    try {
      console.log('🔄 Restoring purchases...');
      
      const customerInfo = await Purchases.restorePurchases();
      this.customerInfo = customerInfo;
      await this.saveCustomerInfo();

      const restoredPurchases = Object.keys(customerInfo.entitlements.active);
      
      console.log('✅ Purchases restored:', restoredPurchases);
      
      return {
        success: true,
        customerInfo,
        restoredPurchases,
      };
    } catch (error) {
      console.error('❌ Failed to restore purchases:', error);
      return {
        success: false,
        error: (error as Error).message,
        restoredPurchases: [],
      };
    }
  }

  public async getSubscriptionStatus(): Promise<SubscriptionStatus> {
    if (!this.customerInfo) {
      await this.loadCustomerInfo();
    }

    if (!this.customerInfo) {
      return {
        isActive: false,
        isPremium: false,
        isBusiness: false,
        plan: 'free',
        willRenew: false,
        isInTrial: false,
        entitlements: [],
      };
    }

    const entitlements = Object.values(this.customerInfo.entitlements.active);
    const allEntitlements = Object.values(this.customerInfo.entitlements.all);
    
    const isPremium = this.hasEntitlement(this.ENTITLEMENTS.premium);
    const isBusiness = this.hasEntitlement(this.ENTITLEMENTS.business);
    const isActive = entitlements.length > 0;

    // Determine plan
    let plan: 'free' | 'premium' | 'business' | 'trial' = 'free';
    if (isBusiness) {
      plan = 'business';
    } else if (isPremium) {
      plan = 'premium';
    }

    // Check for trial
    const isInTrial = entitlements.some(e => 
      e.periodType === 'trial' || 
      (e.periodType === 'intro' && new Date() < new Date(e.expirationDate || 0))
    );

    if (isInTrial) {
      plan = 'trial';
    }

    // Get expiration date
    const expirationDate = entitlements.length > 0 
      ? new Date(Math.max(...entitlements.map(e => new Date(e.expirationDate || 0).getTime())))
      : undefined;

    // Check if will renew
    const willRenew = entitlements.some(e => e.willRenew);

    return {
      isActive,
      isPremium,
      isBusiness,
      plan,
      expirationDate,
      willRenew,
      isInTrial,
      trialEndDate: isInTrial ? expirationDate : undefined,
      entitlements: allEntitlements.map(this.mapEntitlementInfo),
    };
  }

  public hasEntitlement(entitlementId: string): boolean {
    if (!this.customerInfo) return false;
    
    const entitlement = this.customerInfo.entitlements.active[entitlementId];
    return entitlement?.isActive ?? false;
  }

  public async getCustomerInfo(): Promise<CustomerInfo | null> {
    if (!this.isInitialized) return null;

    try {
      this.customerInfo = await Purchases.getCustomerInfo();
      await this.saveCustomerInfo();
      return this.customerInfo;
    } catch (error) {
      console.error('Failed to get customer info:', error);
      return this.customerInfo; // Return cached info
    }
  }

  public async refreshCustomerInfo(): Promise<void> {
    await this.getCustomerInfo();
    if (this.customerInfo) {
      this.notifyCustomerInfoListeners(this.customerInfo);
    }
  }

  public getProductIdsForCurrentVariant(): Record<string, string> {
    return this.PRODUCT_IDS[this.appVariant as keyof typeof this.PRODUCT_IDS] || {};
  }

  public async checkTrialEligibility(productId: string): Promise<boolean> {
    try {
      const eligibility = await Purchases.checkTrialOrIntroductoryPriceEligibility([productId]);
      return eligibility[productId]?.status === 'eligible';
    } catch (error) {
      console.error('Failed to check trial eligibility:', error);
      return false;
    }
  }

  public async presentCodeRedemptionSheet(): Promise<void> {
    if (Platform.OS === 'ios') {
      try {
        await Purchases.presentCodeRedemptionSheet();
      } catch (error) {
        console.error('Failed to present code redemption sheet:', error);
      }
    }
  }

  public addPurchaseListener(listener: (result: PurchaseResult) => void): void {
    this.purchaseListeners.push(listener);
  }

  public removePurchaseListener(listener: (result: PurchaseResult) => void): void {
    const index = this.purchaseListeners.indexOf(listener);
    if (index > -1) {
      this.purchaseListeners.splice(index, 1);
    }
  }

  public addCustomerInfoListener(listener: (info: CustomerInfo) => void): void {
    this.customerInfoListeners.push(listener);
  }

  public removeCustomerInfoListener(listener: (info: CustomerInfo) => void): void {
    const index = this.customerInfoListeners.indexOf(listener);
    if (index > -1) {
      this.customerInfoListeners.splice(index, 1);
    }
  }

  // Utility methods for common purchase flows
  public async showPaywall(): Promise<boolean> {
    try {
      const offerings = await this.getOfferings();
      if (offerings.length === 0) {
        console.warn('No offerings available for paywall');
        return false;
      }

      // Here you would typically show your paywall UI
      console.log('📱 Would show paywall with offerings:', offerings.length);
      return true;
    } catch (error) {
      console.error('Failed to show paywall:', error);
      return false;
    }
  }

  public async purchasePremiumMonthly(): Promise<PurchaseResult> {
    const productIds = this.getProductIdsForCurrentVariant();
    const monthlyId = Object.values(productIds).find(id => id.includes('monthly'));
    
    if (!monthlyId) {
      return {
        success: false,
        error: 'Monthly premium product not available for this app variant',
      };
    }

    return await this.purchaseProduct(monthlyId);
  }

  public async purchasePremiumYearly(): Promise<PurchaseResult> {
    const productIds = this.getProductIdsForCurrentVariant();
    const yearlyId = Object.values(productIds).find(id => id.includes('yearly'));
    
    if (!yearlyId) {
      return {
        success: false,
        error: 'Yearly premium product not available for this app variant',
      };
    }

    return await this.purchaseProduct(yearlyId);
  }

  public getFeatureAvailability(): Record<string, boolean> {
    return {
      unlimited_logs: this.hasEntitlement(this.ENTITLEMENTS.unlimited),
      cloud_sync: this.hasEntitlement(this.ENTITLEMENTS.sync),
      export_features: this.hasEntitlement(this.ENTITLEMENTS.export),
      advanced_analytics: this.hasEntitlement(this.ENTITLEMENTS.analytics),
      priority_support: this.hasEntitlement(this.ENTITLEMENTS.support),
    };
  }

  private async loadCustomerInfo(): Promise<void> {
    try {
      // Try to get from cache first
      const cachedInfo = await AsyncStorage.getItem('last_customer_info');
      if (cachedInfo) {
        this.customerInfo = JSON.parse(cachedInfo);
      }

      // Then get fresh data
      this.customerInfo = await Purchases.getCustomerInfo();
      await this.saveCustomerInfo();
    } catch (error) {
      console.error('Failed to load customer info:', error);
    }
  }

  private async loadOfferings(): Promise<void> {
    try {
      const offerings = await Purchases.getOfferings();
      this.offerings = Object.values(offerings.all);
    } catch (error) {
      console.error('Failed to load offerings:', error);
    }
  }

  private async saveCustomerInfo(): Promise<void> {
    if (this.customerInfo) {
      try {
        await AsyncStorage.setItem('last_customer_info', JSON.stringify(this.customerInfo));
      } catch (error) {
        console.error('Failed to save customer info:', error);
      }
    }
  }

  private setupPurchaseListeners(): void {
    // Set up customer info update listener
    Purchases.addCustomerInfoUpdateListener((customerInfo) => {
      console.log('👤 Customer info updated');
      this.customerInfo = customerInfo;
      this.saveCustomerInfo();
      this.notifyCustomerInfoListeners(customerInfo);
    });
  }

  private notifyPurchaseListeners(result: PurchaseResult): void {
    this.purchaseListeners.forEach(listener => {
      try {
        listener(result);
      } catch (error) {
        console.error('Error in purchase listener:', error);
      }
    });
  }

  private notifyCustomerInfoListeners(info: CustomerInfo): void {
    this.customerInfoListeners.forEach(listener => {
      try {
        listener(info);
      } catch (error) {
        console.error('Error in customer info listener:', error);
      }
    });
  }

  private mapEntitlementInfo(entitlement: any): EntitlementInfo {
    return {
      identifier: entitlement.identifier,
      isActive: entitlement.isActive,
      willRenew: entitlement.willRenew,
      periodType: entitlement.periodType,
      latestPurchaseDate: new Date(entitlement.latestPurchaseDate),
      originalPurchaseDate: new Date(entitlement.originalPurchaseDate),
      expirationDate: entitlement.expirationDate ? new Date(entitlement.expirationDate) : undefined,
      store: entitlement.store,
      productIdentifier: entitlement.productIdentifier,
      isSandbox: entitlement.isSandbox,
      unsubscribeDetectedAt: entitlement.unsubscribeDetectedAt ? new Date(entitlement.unsubscribeDetectedAt) : undefined,
      billingIssueDetectedAt: entitlement.billingIssueDetectedAt ? new Date(entitlement.billingIssueDetectedAt) : undefined,
    };
  }

  public isInitialized(): boolean {
    return this.isInitialized;
  }

  public getCurrentCustomerInfo(): CustomerInfo | null {
    return this.customerInfo;
  }

  public getAppVariant(): string {
    return this.appVariant;
  }
}

export const InAppPurchaseService = new InAppPurchaseServiceClass();