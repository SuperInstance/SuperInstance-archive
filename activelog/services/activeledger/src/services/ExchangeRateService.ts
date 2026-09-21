import { Decimal } from 'decimal.js';
import { v4 as uuidv4 } from 'uuid';
import { EventEmitter } from 'events';
import { CurrencyCode, ExchangeRate, CurrencyConversion } from '../types';

export class ExchangeRateService extends EventEmitter {
  private rates: Map<string, ExchangeRate> = new Map();
  private updateInterval: NodeJS.Timeout | null = null;
  private readonly API_SOURCES = ['exchangerate-api.com', 'fixer.io', 'currencylayer.com'];

  constructor() {
    super();
    this.initializeRates();
    this.startPeriodicUpdates();
  }

  /**
   * Get exchange rate between two currencies
   */
  async getExchangeRate(fromCurrency: CurrencyCode, toCurrency: CurrencyCode): Promise<ExchangeRate> {
    if (fromCurrency === toCurrency) {
      return {
        id: uuidv4(),
        fromCurrency,
        toCurrency,
        rate: new Decimal(1),
        source: 'internal',
        validFrom: new Date(),
        validTo: new Date(Date.now() + 24 * 60 * 60 * 1000), // 24 hours
        createdAt: new Date()
      };
    }

    const rateKey = `${fromCurrency}_${toCurrency}`;
    const rate = this.rates.get(rateKey);

    if (rate && rate.validTo > new Date()) {
      return rate;
    }

    // Fetch fresh rate if not available or expired
    return await this.fetchExchangeRate(fromCurrency, toCurrency);
  }

  /**
   * Convert amount between currencies
   */
  async convertCurrency(
    amount: Decimal,
    fromCurrency: CurrencyCode,
    toCurrency: CurrencyCode
  ): Promise<{ convertedAmount: Decimal; exchangeRate: ExchangeRate; fee: Decimal }> {
    const exchangeRate = await this.getExchangeRate(fromCurrency, toCurrency);
    const convertedAmount = amount.mul(exchangeRate.rate);
    
    // Calculate conversion fee (0.5% of converted amount)
    const fee = convertedAmount.mul(0.005);

    return {
      convertedAmount: convertedAmount.sub(fee),
      exchangeRate,
      fee
    };
  }

  /**
   * Get all current exchange rates
   */
  getCurrentRates(): ExchangeRate[] {
    return Array.from(this.rates.values())
      .filter(rate => rate.validTo > new Date());
  }

  /**
   * Get historical exchange rate
   */
  async getHistoricalRate(
    fromCurrency: CurrencyCode,
    toCurrency: CurrencyCode,
    date: Date
  ): Promise<ExchangeRate | null> {
    // Mock implementation - would query database for historical rates
    return await this.fetchExchangeRate(fromCurrency, toCurrency, date);
  }

  /**
   * Update exchange rates from external API
   */
  async updateExchangeRates(): Promise<void> {
    const baseCurrencies: CurrencyCode[] = ['USD', 'EUR', 'GBP'];
    const targetCurrencies: CurrencyCode[] = [
      'USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY', 'INR', 'BRL'
    ];

    for (const baseCurrency of baseCurrencies) {
      for (const targetCurrency of targetCurrencies) {
        if (baseCurrency !== targetCurrency) {
          try {
            const rate = await this.fetchExchangeRate(baseCurrency, targetCurrency);
            this.rates.set(`${baseCurrency}_${targetCurrency}`, rate);
          } catch (error) {
            console.error(`Failed to update rate ${baseCurrency}/${targetCurrency}:`, error);
          }
        }
      }
    }

    this.emit('ratesUpdated', { updatedAt: new Date(), rateCount: this.rates.size });
  }

  /**
   * Get currency conversion with detailed tracking
   */
  async trackCurrencyConversion(
    userId: string,
    fromAmount: Decimal,
    fromCurrency: CurrencyCode,
    toCurrency: CurrencyCode
  ): Promise<CurrencyConversion> {
    const { convertedAmount, exchangeRate, fee } = await this.convertCurrency(
      fromAmount,
      fromCurrency,
      toCurrency
    );

    const conversion: CurrencyConversion = {
      id: uuidv4(),
      userId,
      fromAmount,
      fromCurrency,
      toAmount: convertedAmount,
      toCurrency,
      exchangeRate: exchangeRate.rate,
      fee,
      status: 'completed',
      createdAt: new Date(),
      completedAt: new Date()
    };

    this.emit('currencyConverted', { conversion });
    return conversion;
  }

  /**
   * Get supported currencies with their details
   */
  getSupportedCurrencies(): Array<{
    code: CurrencyCode;
    name: string;
    symbol: string;
    decimalPlaces: number;
    isActive: boolean;
  }> {
    return [
      { code: 'USD', name: 'US Dollar', symbol: '$', decimalPlaces: 2, isActive: true },
      { code: 'EUR', name: 'Euro', symbol: '€', decimalPlaces: 2, isActive: true },
      { code: 'GBP', name: 'British Pound', symbol: '£', decimalPlaces: 2, isActive: true },
      { code: 'JPY', name: 'Japanese Yen', symbol: '¥', decimalPlaces: 0, isActive: true },
      { code: 'CAD', name: 'Canadian Dollar', symbol: 'C$', decimalPlaces: 2, isActive: true },
      { code: 'AUD', name: 'Australian Dollar', symbol: 'A$', decimalPlaces: 2, isActive: true },
      { code: 'CHF', name: 'Swiss Franc', symbol: 'CHF', decimalPlaces: 2, isActive: true },
      { code: 'CNY', name: 'Chinese Yuan', symbol: '¥', decimalPlaces: 2, isActive: true },
      { code: 'INR', name: 'Indian Rupee', symbol: '₹', decimalPlaces: 2, isActive: true },
      { code: 'BRL', name: 'Brazilian Real', symbol: 'R$', decimalPlaces: 2, isActive: true }
    ];
  }

  /**
   * Calculate cross-currency rates (e.g., EUR to JPY via USD)
   */
  async calculateCrossRate(
    fromCurrency: CurrencyCode,
    toCurrency: CurrencyCode,
    baseCurrency: CurrencyCode = 'USD'
  ): Promise<Decimal> {
    if (fromCurrency === toCurrency) {
      return new Decimal(1);
    }

    // Direct rate check first
    const directRateKey = `${fromCurrency}_${toCurrency}`;
    const directRate = this.rates.get(directRateKey);
    
    if (directRate && directRate.validTo > new Date()) {
      return directRate.rate;
    }

    // Cross-rate calculation via base currency
    const fromToBaseRate = await this.getExchangeRate(fromCurrency, baseCurrency);
    const baseToTargetRate = await this.getExchangeRate(baseCurrency, toCurrency);
    
    return fromToBaseRate.rate.mul(baseToTargetRate.rate);
  }

  /**
   * Get rate change information
   */
  async getRateChange(
    fromCurrency: CurrencyCode,
    toCurrency: CurrencyCode,
    period: '1d' | '7d' | '30d' = '1d'
  ): Promise<{
    currentRate: Decimal;
    previousRate: Decimal;
    change: Decimal;
    changePercent: Decimal;
    trend: 'up' | 'down' | 'stable';
  }> {
    const currentRate = await this.getExchangeRate(fromCurrency, toCurrency);
    
    // Mock previous rate (would fetch from database)
    const changePercent = new Decimal(Math.random() * 4 - 2); // -2% to +2%
    const previousRate = {
      ...currentRate,
      rate: currentRate.rate.div(new Decimal(1).add(changePercent.div(100)))
    };

    const change = currentRate.rate.sub(previousRate.rate);
    
    let trend: 'up' | 'down' | 'stable' = 'stable';
    if (change.gt(0.001)) trend = 'up';
    else if (change.lt(-0.001)) trend = 'down';

    return {
      currentRate: currentRate.rate,
      previousRate: previousRate.rate,
      change,
      changePercent,
      trend
    };
  }

  /**
   * Get currency volatility metrics
   */
  async getCurrencyVolatility(
    currency: CurrencyCode,
    baseCurrency: CurrencyCode = 'USD',
    days: number = 30
  ): Promise<{
    volatility: Decimal; // Standard deviation
    averageRate: Decimal;
    minRate: Decimal;
    maxRate: Decimal;
    riskLevel: 'low' | 'medium' | 'high';
  }> {
    // Mock volatility data
    const volatilityMap: Record<CurrencyCode, number> = {
      USD: 0.5,
      EUR: 0.8,
      GBP: 1.2,
      JPY: 0.9,
      CAD: 1.0,
      AUD: 1.5,
      CHF: 0.6,
      CNY: 0.4,
      INR: 2.0,
      BRL: 3.0
    };

    const currentRate = await this.getExchangeRate(currency, baseCurrency);
    const volatility = new Decimal(volatilityMap[currency] || 1.0);
    
    return {
      volatility,
      averageRate: currentRate.rate,
      minRate: currentRate.rate.mul(0.95),
      maxRate: currentRate.rate.mul(1.05),
      riskLevel: volatility.lte(1) ? 'low' : volatility.lte(2) ? 'medium' : 'high'
    };
  }

  // Private methods

  private async fetchExchangeRate(
    fromCurrency: CurrencyCode,
    toCurrency: CurrencyCode,
    date?: Date
  ): Promise<ExchangeRate> {
    // Mock exchange rates for development
    const mockRates: Record<string, number> = {
      'USD_EUR': 0.85,
      'USD_GBP': 0.73,
      'USD_JPY': 110.0,
      'USD_CAD': 1.25,
      'USD_AUD': 1.35,
      'USD_CHF': 0.92,
      'USD_CNY': 6.45,
      'USD_INR': 74.5,
      'USD_BRL': 5.2,
      
      'EUR_USD': 1.18,
      'EUR_GBP': 0.86,
      'EUR_JPY': 129.4,
      
      'GBP_USD': 1.37,
      'GBP_EUR': 1.16,
      'GBP_JPY': 150.7
    };

    const rateKey = `${fromCurrency}_${toCurrency}`;
    const rate = mockRates[rateKey] || 1;

    // Add some random variation
    const variation = 1 + (Math.random() - 0.5) * 0.02; // ±1% variation
    const finalRate = new Decimal(rate * variation);

    const exchangeRate: ExchangeRate = {
      id: uuidv4(),
      fromCurrency,
      toCurrency,
      rate: finalRate,
      source: 'mock-api',
      validFrom: date || new Date(),
      validTo: new Date(Date.now() + 60 * 60 * 1000), // 1 hour validity
      createdAt: new Date()
    };

    return exchangeRate;
  }

  private initializeRates(): void {
    // Initialize with some basic rates
    const initialRates = [
      { from: 'USD', to: 'EUR', rate: 0.85 },
      { from: 'USD', to: 'GBP', rate: 0.73 },
      { from: 'USD', to: 'JPY', rate: 110.0 },
      { from: 'EUR', to: 'USD', rate: 1.18 },
      { from: 'GBP', to: 'USD', rate: 1.37 }
    ];

    for (const { from, to, rate } of initialRates) {
      const exchangeRate: ExchangeRate = {
        id: uuidv4(),
        fromCurrency: from as CurrencyCode,
        toCurrency: to as CurrencyCode,
        rate: new Decimal(rate),
        source: 'initial',
        validFrom: new Date(),
        validTo: new Date(Date.now() + 24 * 60 * 60 * 1000),
        createdAt: new Date()
      };
      
      this.rates.set(`${from}_${to}`, exchangeRate);
    }
  }

  private startPeriodicUpdates(): void {
    // Update rates every hour
    this.updateInterval = setInterval(() => {
      this.updateExchangeRates().catch(error => {
        console.error('Failed to update exchange rates:', error);
      });
    }, 60 * 60 * 1000); // 1 hour
  }

  /**
   * Stop the service and cleanup
   */
  destroy(): void {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = null;
    }
    this.removeAllListeners();
  }
}