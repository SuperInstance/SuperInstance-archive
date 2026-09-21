import { Decimal } from 'decimal.js';
import { v4 as uuidv4 } from 'uuid';
import { 
  ComputeCredit, 
  CCTransaction, 
  CCWallet, 
  CurrencyCode, 
  TransactionCategory,
  ExchangeRate 
} from '../types';
import { ExchangeRateService } from '../services/ExchangeRateService';
import { EventEmitter } from 'events';

export class CCreditSystem extends EventEmitter {
  private exchangeRateService: ExchangeRateService;
  private baseCurrency: CurrencyCode = 'USD';
  
  // Exchange rates for CC (1 CC = X USD equivalent)
  private readonly CC_BASE_RATE = new Decimal('0.01'); // 1 CC = $0.01 USD

  constructor(exchangeRateService: ExchangeRateService) {
    super();
    this.exchangeRateService = exchangeRateService;
  }

  /**
   * Create a new CC wallet for a user
   */
  async createWallet(userId: string, primaryCurrency: CurrencyCode = 'USD'): Promise<CCWallet> {
    const wallet: CCWallet = {
      id: uuidv4(),
      userId,
      primaryCurrency,
      balances: {
        USD: new Decimal(0),
        EUR: new Decimal(0),
        GBP: new Decimal(0),
        JPY: new Decimal(0),
        CAD: new Decimal(0),
        AUD: new Decimal(0),
        CHF: new Decimal(0),
        CNY: new Decimal(0),
        INR: new Decimal(0),
        BRL: new Decimal(0)
      },
      totalBalanceUSD: new Decimal(0),
      isActive: true,
      createdAt: new Date(),
      updatedAt: new Date()
    };

    this.emit('walletCreated', { wallet });
    return wallet;
  }

  /**
   * Award CC credits to a user
   */
  async awardCredits(
    userId: string,
    amount: Decimal,
    currency: CurrencyCode,
    sourceType: ComputeCredit['sourceType'],
    sourceId?: string,
    expiresAt?: Date,
    metadata?: Record<string, any>
  ): Promise<ComputeCredit> {
    const credit: ComputeCredit = {
      id: uuidv4(),
      userId,
      amount,
      currency,
      sourceType,
      sourceId,
      expiresAt,
      isActive: true,
      createdAt: new Date(),
      updatedAt: new Date(),
      metadata
    };

    // Create transaction record
    const transaction = await this.createTransaction(
      userId,
      'credit',
      amount,
      currency,
      `CC credits awarded: ${sourceType}`,
      this.mapSourceTypeToCategory(sourceType),
      sourceType,
      sourceId,
      metadata
    );

    this.emit('creditsAwarded', { credit, transaction });
    return credit;
  }

  /**
   * Debit CC credits from a user's account
   */
  async debitCredits(
    userId: string,
    amount: Decimal,
    currency: CurrencyCode,
    description: string,
    category: TransactionCategory,
    sourceType: string,
    sourceId?: string,
    metadata?: Record<string, any>
  ): Promise<CCTransaction> {
    // Check if user has sufficient balance
    const wallet = await this.getWallet(userId);
    const balanceInCurrency = wallet.balances[currency] || new Decimal(0);

    // Convert amount to primary currency for balance check if needed
    const amountInPrimaryCurrency = currency !== wallet.primaryCurrency 
      ? await this.convertCurrency(amount, currency, wallet.primaryCurrency)
      : amount;

    const primaryBalance = wallet.balances[wallet.primaryCurrency] || new Decimal(0);
    
    if (primaryBalance.lt(amountInPrimaryCurrency)) {
      throw new Error(`Insufficient CC balance. Required: ${amountInPrimaryCurrency.toString()} ${wallet.primaryCurrency}, Available: ${primaryBalance.toString()} ${wallet.primaryCurrency}`);
    }

    // Create debit transaction
    const transaction = await this.createTransaction(
      userId,
      'debit',
      amount,
      currency,
      description,
      category,
      sourceType,
      sourceId,
      metadata
    );

    this.emit('creditsDebited', { transaction });
    return transaction;
  }

  /**
   * Get user's CC wallet with current balances
   */
  async getWallet(userId: string): Promise<CCWallet> {
    // This would typically fetch from database
    // For now, return a mock wallet
    const wallet: CCWallet = {
      id: uuidv4(),
      userId,
      primaryCurrency: 'USD',
      balances: {
        USD: new Decimal(100.50),
        EUR: new Decimal(0),
        GBP: new Decimal(0),
        JPY: new Decimal(0),
        CAD: new Decimal(0),
        AUD: new Decimal(0),
        CHF: new Decimal(0),
        CNY: new Decimal(0),
        INR: new Decimal(0),
        BRL: new Decimal(0)
      },
      totalBalanceUSD: new Decimal(100.50),
      isActive: true,
      createdAt: new Date(),
      updatedAt: new Date()
    };

    return wallet;
  }

  /**
   * Convert CC credits between currencies
   */
  async convertCurrency(
    amount: Decimal,
    fromCurrency: CurrencyCode,
    toCurrency: CurrencyCode
  ): Promise<Decimal> {
    if (fromCurrency === toCurrency) {
      return amount;
    }

    const exchangeRate = await this.exchangeRateService.getExchangeRate(fromCurrency, toCurrency);
    return amount.mul(exchangeRate.rate);
  }

  /**
   * Get CC credit equivalent in USD
   */
  getCCValueInUSD(ccAmount: Decimal): Decimal {
    return ccAmount.mul(this.CC_BASE_RATE);
  }

  /**
   * Get CC credits equivalent for USD amount
   */
  getUSDValueInCC(usdAmount: Decimal): Decimal {
    return usdAmount.div(this.CC_BASE_RATE);
  }

  /**
   * Purchase CC credits with real money
   */
  async purchaseCredits(
    userId: string,
    usdAmount: Decimal,
    paymentMethodId: string,
    currency: CurrencyCode = 'USD'
  ): Promise<{ credit: ComputeCredit; ccAmount: Decimal }> {
    const ccAmount = this.getUSDValueInCC(usdAmount);
    
    const credit = await this.awardCredits(
      userId,
      ccAmount,
      currency,
      'purchase',
      paymentMethodId,
      undefined,
      { usdAmount: usdAmount.toString(), paymentMethodId }
    );

    return { credit, ccAmount };
  }

  /**
   * Get user's transaction history
   */
  async getTransactionHistory(
    userId: string,
    limit: number = 50,
    offset: number = 0,
    category?: TransactionCategory
  ): Promise<CCTransaction[]> {
    // This would fetch from database
    // Mock implementation
    const transactions: CCTransaction[] = [];
    
    // Sample transaction
    transactions.push({
      id: uuidv4(),
      userId,
      type: 'credit',
      amount: new Decimal(100),
      currency: 'USD',
      description: 'CC credits purchased',
      category: 'subscription',
      sourceType: 'purchase',
      balanceAfter: new Decimal(100),
      createdAt: new Date(),
      metadata: { paymentAmount: '$10.00' }
    });

    return transactions.filter(t => !category || t.category === category)
                     .slice(offset, offset + limit);
  }

  /**
   * Get user's total balance across all currencies in USD equivalent
   */
  async getTotalBalanceUSD(userId: string): Promise<Decimal> {
    const wallet = await this.getWallet(userId);
    let totalUSD = new Decimal(0);

    for (const [currency, balance] of Object.entries(wallet.balances)) {
      if (balance.gt(0)) {
        const usdValue = currency === 'USD' 
          ? balance 
          : await this.convertCurrency(balance, currency as CurrencyCode, 'USD');
        totalUSD = totalUSD.add(usdValue);
      }
    }

    return totalUSD;
  }

  /**
   * Transfer CC credits between users
   */
  async transferCredits(
    fromUserId: string,
    toUserId: string,
    amount: Decimal,
    currency: CurrencyCode,
    reason: string
  ): Promise<{ debitTransaction: CCTransaction; creditTransaction: CCTransaction }> {
    // Debit from sender
    const debitTransaction = await this.debitCredits(
      fromUserId,
      amount,
      currency,
      `Transfer to user ${toUserId}: ${reason}`,
      'subscription', // Could be a new category 'transfer'
      'transfer',
      toUserId,
      { transferTo: toUserId, reason }
    );

    // Credit to receiver
    const creditTransaction = await this.createTransaction(
      toUserId,
      'credit',
      amount,
      currency,
      `Transfer from user ${fromUserId}: ${reason}`,
      'subscription',
      'transfer',
      fromUserId,
      { transferFrom: fromUserId, reason }
    );

    this.emit('creditsTransferred', { 
      fromUserId, 
      toUserId, 
      amount, 
      currency, 
      debitTransaction, 
      creditTransaction 
    });

    return { debitTransaction, creditTransaction };
  }

  /**
   * Expire old CC credits
   */
  async expireCredits(): Promise<void> {
    const now = new Date();
    
    // This would update database to mark credits as inactive where expiresAt < now
    // and create corresponding debit transactions
    
    this.emit('creditsExpired', { expiredAt: now });
  }

  /**
   * Get pricing for CC credits in different currencies
   */
  async getCCPricing(currency: CurrencyCode): Promise<{
    currency: CurrencyCode;
    pricePerCC: Decimal;
    packages: Array<{
      ccAmount: Decimal;
      price: Decimal;
      bonus: Decimal;
      totalCC: Decimal;
    }>;
  }> {
    const basePriceUSD = this.CC_BASE_RATE;
    const priceInCurrency = currency === 'USD' 
      ? basePriceUSD 
      : await this.convertCurrency(basePriceUSD, 'USD', currency);

    // Define CC packages with bonuses
    const packages = [
      { ccAmount: new Decimal(1000), bonus: new Decimal(0) },      // $10
      { ccAmount: new Decimal(5000), bonus: new Decimal(250) },    // $50 + 2.5% bonus
      { ccAmount: new Decimal(10000), bonus: new Decimal(750) },   // $100 + 7.5% bonus
      { ccAmount: new Decimal(25000), bonus: new Decimal(2500) },  // $250 + 10% bonus
      { ccAmount: new Decimal(50000), bonus: new Decimal(7500) },  // $500 + 15% bonus
    ];

    const packagePricing = packages.map(pkg => ({
      ccAmount: pkg.ccAmount,
      price: pkg.ccAmount.mul(priceInCurrency),
      bonus: pkg.bonus,
      totalCC: pkg.ccAmount.add(pkg.bonus)
    }));

    return {
      currency,
      pricePerCC: priceInCurrency,
      packages: packagePricing
    };
  }

  /**
   * Create a transaction record
   */
  private async createTransaction(
    userId: string,
    type: 'debit' | 'credit',
    amount: Decimal,
    currency: CurrencyCode,
    description: string,
    category: TransactionCategory,
    sourceType: string,
    sourceId?: string,
    metadata?: Record<string, any>
  ): Promise<CCTransaction> {
    const wallet = await this.getWallet(userId);
    const currentBalance = wallet.balances[currency] || new Decimal(0);
    const balanceAfter = type === 'credit' 
      ? currentBalance.add(amount)
      : currentBalance.sub(amount);

    const transaction: CCTransaction = {
      id: uuidv4(),
      userId,
      type,
      amount,
      currency,
      description,
      category,
      sourceType,
      sourceId,
      balanceAfter,
      createdAt: new Date(),
      metadata
    };

    return transaction;
  }

  /**
   * Map source type to transaction category
   */
  private mapSourceTypeToCategory(sourceType: ComputeCredit['sourceType']): TransactionCategory {
    switch (sourceType) {
      case 'ad_revenue':
        return 'ad_revenue';
      case 'affiliate':
        return 'affiliate';
      case 'purchase':
        return 'subscription';
      case 'refund':
      case 'compute_refund':
        return 'refund';
      default:
        return 'subscription';
    }
  }

  /**
   * Validate CC amount and currency
   */
  validateCCAmount(amount: Decimal, currency: CurrencyCode): void {
    if (amount.lte(0)) {
      throw new Error('CC amount must be positive');
    }

    if (amount.dp() > 2) {
      throw new Error('CC amount cannot have more than 2 decimal places');
    }

    const supportedCurrencies: CurrencyCode[] = [
      'USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY', 'INR', 'BRL'
    ];

    if (!supportedCurrencies.includes(currency)) {
      throw new Error(`Unsupported currency: ${currency}`);
    }
  }

  /**
   * Get CC system statistics
   */
  async getSystemStats(): Promise<{
    totalCreditsIssued: Decimal;
    totalCreditsSpent: Decimal;
    totalCreditsExpired: Decimal;
    activeUsers: number;
    totalTransactions: number;
  }> {
    // This would aggregate data from database
    return {
      totalCreditsIssued: new Decimal(1000000),
      totalCreditsSpent: new Decimal(750000),
      totalCreditsExpired: new Decimal(25000),
      activeUsers: 5000,
      totalTransactions: 25000
    };
  }
}