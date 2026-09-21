import { EventEmitter } from 'events';
import crypto from 'crypto';

export interface PaymentMethod {
  id: string;
  userId: string;
  type: 'credit_card' | 'debit_card' | 'bank_account' | 'crypto_wallet' | 'digital_wallet';
  provider: 'stripe' | 'paypal' | 'crypto' | 'bank_transfer';
  details: PaymentMethodDetails;
  isDefault: boolean;
  isVerified: boolean;
  createdAt: Date;
  lastUsed?: Date;
}

export interface PaymentMethodDetails {
  // Credit/Debit Card
  last4?: string;
  brand?: string;
  expiryMonth?: number;
  expiryYear?: number;
  
  // Bank Account
  accountType?: 'checking' | 'savings';
  bankName?: string;
  routingNumber?: string;
  accountNumber?: string;
  
  // Crypto Wallet
  walletAddress?: string;
  currency?: string;
  network?: string;
  
  // Digital Wallet
  email?: string;
  phone?: string;
}

export interface Transaction {
  id: string;
  jobId?: string;
  payerId: string;
  payeeId: string;
  amount: number;
  currency: string;
  type: 'job_payment' | 'escrow_deposit' | 'escrow_release' | 'refund' | 'fee' | 'bonus';
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled' | 'disputed';
  paymentMethodId: string;
  description: string;
  metadata?: Record<string, any>;
  fees: TransactionFees;
  createdAt: Date;
  processedAt?: Date;
  failureReason?: string;
  externalTransactionId?: string;
}

export interface TransactionFees {
  platformFee: number;
  processingFee: number;
  networkFee?: number;
  total: number;
}

export interface EscrowAccount {
  id: string;
  jobId: string;
  payerId: string;
  payeeId: string;
  amount: number;
  currency: string;
  status: 'active' | 'released' | 'refunded' | 'disputed';
  conditions: EscrowConditions;
  createdAt: Date;
  releaseDate?: Date;
  autoReleaseDate: Date;
}

export interface EscrowConditions {
  autoReleaseHours: number;
  milestones?: EscrowMilestone[];
  disputeDeadlineHours: number;
  requiresApproval: boolean;
}

export interface EscrowMilestone {
  id: string;
  description: string;
  percentage: number;
  status: 'pending' | 'completed' | 'disputed';
  completedAt?: Date;
}

export interface PaymentIntent {
  id: string;
  amount: number;
  currency: string;
  paymentMethodId: string;
  recipientId: string;
  description: string;
  metadata?: Record<string, any>;
  status: 'requires_payment' | 'requires_action' | 'processing' | 'succeeded' | 'cancelled';
  clientSecret: string;
  createdAt: Date;
}

export interface PayoutAccount {
  id: string;
  userId: string;
  type: 'bank_account' | 'crypto_wallet' | 'digital_wallet';
  details: PayoutAccountDetails;
  isVerified: boolean;
  minimumPayout: number;
  currency: string;
  createdAt: Date;
}

export interface PayoutAccountDetails {
  // Bank Account
  accountHolderName?: string;
  bankName?: string;
  accountNumber?: string;
  routingNumber?: string;
  swiftCode?: string;
  iban?: string;
  
  // Crypto Wallet
  walletAddress?: string;
  network?: string;
  
  // Digital Wallet
  email?: string;
  walletId?: string;
}

export interface PayoutRequest {
  id: string;
  userId: string;
  amount: number;
  currency: string;
  payoutAccountId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  description: string;
  fees: number;
  netAmount: number;
  requestedAt: Date;
  processedAt?: Date;
  failureReason?: string;
  externalTransactionId?: string;
}

export class PaymentProcessor extends EventEmitter {
  private transactions: Map<string, Transaction> = new Map();
  private escrowAccounts: Map<string, EscrowAccount> = new Map();
  private paymentMethods: Map<string, PaymentMethod[]> = new Map();
  private payoutAccounts: Map<string, PayoutAccount[]> = new Map();
  private paymentIntents: Map<string, PaymentIntent> = new Map();
  private payoutRequests: Map<string, PayoutRequest[]> = new Map();
  private balances: Map<string, number> = new Map();
  private autoReleaseTimer: NodeJS.Timeout | null = null;

  constructor() {
    super();
    this.startAutoReleaseTimer();
  }

  public async addPaymentMethod(userId: string, method: Omit<PaymentMethod, 'id' | 'userId' | 'createdAt'>): Promise<string> {
    const methodId = this.generateId('pm');
    const paymentMethod: PaymentMethod = {
      ...method,
      id: methodId,
      userId,
      createdAt: new Date()
    };

    const userMethods = this.paymentMethods.get(userId) || [];
    
    // Set as default if it's the first method
    if (userMethods.length === 0) {
      paymentMethod.isDefault = true;
    }

    userMethods.push(paymentMethod);
    this.paymentMethods.set(userId, userMethods);

    this.emit('paymentMethodAdded', paymentMethod);
    return methodId;
  }

  public async createPaymentIntent(
    payerId: string, 
    amount: number, 
    currency: string = 'USD',
    options: {
      recipientId: string;
      paymentMethodId?: string;
      description: string;
      metadata?: Record<string, any>;
    }
  ): Promise<PaymentIntent> {
    const intentId = this.generateId('pi');
    const clientSecret = this.generateClientSecret(intentId);

    let paymentMethodId = options.paymentMethodId;
    if (!paymentMethodId) {
      const defaultMethod = await this.getDefaultPaymentMethod(payerId);
      if (!defaultMethod) {
        throw new Error('No payment method available');
      }
      paymentMethodId = defaultMethod.id;
    }

    const intent: PaymentIntent = {
      id: intentId,
      amount,
      currency,
      paymentMethodId,
      recipientId: options.recipientId,
      description: options.description,
      metadata: options.metadata,
      status: 'requires_payment',
      clientSecret,
      createdAt: new Date()
    };

    this.paymentIntents.set(intentId, intent);
    this.emit('paymentIntentCreated', intent);

    return intent;
  }

  public async processPayment(intentId: string, jobId?: string): Promise<Transaction> {
    const intent = this.paymentIntents.get(intentId);
    if (!intent) {
      throw new Error('Payment intent not found');
    }

    if (intent.status !== 'requires_payment') {
      throw new Error(`Cannot process payment in status: ${intent.status}`);
    }

    intent.status = 'processing';
    this.paymentIntents.set(intentId, intent);

    try {
      const fees = this.calculateFees(intent.amount, intent.currency);
      const transactionId = this.generateId('txn');

      const transaction: Transaction = {
        id: transactionId,
        jobId,
        payerId: intent.recipientId, // Note: recipientId in intent is actually the payer
        payeeId: intent.recipientId,
        amount: intent.amount,
        currency: intent.currency,
        type: jobId ? 'job_payment' : 'escrow_deposit',
        status: 'processing',
        paymentMethodId: intent.paymentMethodId,
        description: intent.description,
        metadata: intent.metadata,
        fees,
        createdAt: new Date()
      };

      // Simulate payment processing
      await this.simulatePaymentProcessing(transaction);

      transaction.status = 'completed';
      transaction.processedAt = new Date();
      transaction.externalTransactionId = this.generateExternalTransactionId();

      this.transactions.set(transactionId, transaction);
      intent.status = 'succeeded';
      this.paymentIntents.set(intentId, intent);

      // Update balances
      await this.updateBalance(transaction.payeeId, transaction.amount - fees.total);

      this.emit('paymentCompleted', transaction);
      return transaction;

    } catch (error) {
      intent.status = 'cancelled';
      this.paymentIntents.set(intentId, intent);
      
      const failedTransaction: Transaction = {
        id: this.generateId('txn'),
        jobId,
        payerId: intent.recipientId,
        payeeId: intent.recipientId,
        amount: intent.amount,
        currency: intent.currency,
        type: jobId ? 'job_payment' : 'escrow_deposit',
        status: 'failed',
        paymentMethodId: intent.paymentMethodId,
        description: intent.description,
        metadata: intent.metadata,
        fees: this.calculateFees(intent.amount, intent.currency),
        createdAt: new Date(),
        failureReason: (error as Error).message
      };

      this.transactions.set(failedTransaction.id, failedTransaction);
      this.emit('paymentFailed', failedTransaction);
      throw error;
    }
  }

  public async createEscrowAccount(
    jobId: string,
    payerId: string,
    payeeId: string,
    amount: number,
    currency: string = 'USD',
    conditions?: Partial<EscrowConditions>
  ): Promise<string> {
    const escrowId = this.generateId('esc');
    const defaultConditions: EscrowConditions = {
      autoReleaseHours: 72, // 3 days
      disputeDeadlineHours: 24,
      requiresApproval: false,
      ...conditions
    };

    const escrowAccount: EscrowAccount = {
      id: escrowId,
      jobId,
      payerId,
      payeeId,
      amount,
      currency,
      status: 'active',
      conditions: defaultConditions,
      createdAt: new Date(),
      autoReleaseDate: new Date(Date.now() + defaultConditions.autoReleaseHours * 60 * 60 * 1000)
    };

    this.escrowAccounts.set(escrowId, escrowAccount);
    this.emit('escrowCreated', escrowAccount);

    return escrowId;
  }

  public async releaseEscrow(escrowId: string, releasedBy: string, reason: string = 'Job completed'): Promise<void> {
    const escrow = this.escrowAccounts.get(escrowId);
    if (!escrow) {
      throw new Error('Escrow account not found');
    }

    if (escrow.status !== 'active') {
      throw new Error(`Cannot release escrow in status: ${escrow.status}`);
    }

    escrow.status = 'released';
    escrow.releaseDate = new Date();
    this.escrowAccounts.set(escrowId, escrow);

    // Create release transaction
    const transaction: Transaction = {
      id: this.generateId('txn'),
      jobId: escrow.jobId,
      payerId: escrow.payerId,
      payeeId: escrow.payeeId,
      amount: escrow.amount,
      currency: escrow.currency,
      type: 'escrow_release',
      status: 'completed',
      paymentMethodId: 'escrow',
      description: reason,
      fees: this.calculateFees(escrow.amount, escrow.currency, 'escrow_release'),
      createdAt: new Date(),
      processedAt: new Date()
    };

    this.transactions.set(transaction.id, transaction);

    // Update payee balance
    await this.updateBalance(escrow.payeeId, escrow.amount - transaction.fees.total);

    this.emit('escrowReleased', escrow, transaction);
  }

  public async refundEscrow(escrowId: string, refundedBy: string, reason: string): Promise<void> {
    const escrow = this.escrowAccounts.get(escrowId);
    if (!escrow) {
      throw new Error('Escrow account not found');
    }

    if (escrow.status !== 'active') {
      throw new Error(`Cannot refund escrow in status: ${escrow.status}`);
    }

    escrow.status = 'refunded';
    this.escrowAccounts.set(escrowId, escrow);

    // Create refund transaction
    const transaction: Transaction = {
      id: this.generateId('txn'),
      jobId: escrow.jobId,
      payerId: escrow.payeeId, // Reversed for refund
      payeeId: escrow.payerId, // Reversed for refund
      amount: escrow.amount,
      currency: escrow.currency,
      type: 'refund',
      status: 'completed',
      paymentMethodId: 'escrow',
      description: reason,
      fees: { platformFee: 0, processingFee: 0, total: 0 }, // No fees for refunds
      createdAt: new Date(),
      processedAt: new Date()
    };

    this.transactions.set(transaction.id, transaction);

    // Refund to original payer
    await this.updateBalance(escrow.payerId, escrow.amount);

    this.emit('escrowRefunded', escrow, transaction);
  }

  public async addPayoutAccount(userId: string, account: Omit<PayoutAccount, 'id' | 'userId' | 'createdAt'>): Promise<string> {
    const accountId = this.generateId('pa');
    const payoutAccount: PayoutAccount = {
      ...account,
      id: accountId,
      userId,
      createdAt: new Date()
    };

    const userAccounts = this.payoutAccounts.get(userId) || [];
    userAccounts.push(payoutAccount);
    this.payoutAccounts.set(userId, userAccounts);

    this.emit('payoutAccountAdded', payoutAccount);
    return accountId;
  }

  public async requestPayout(
    userId: string,
    amount: number,
    payoutAccountId: string,
    currency: string = 'USD'
  ): Promise<string> {
    const balance = this.getBalance(userId);
    if (balance < amount) {
      throw new Error('Insufficient balance');
    }

    const payoutAccount = await this.getPayoutAccount(userId, payoutAccountId);
    if (!payoutAccount || !payoutAccount.isVerified) {
      throw new Error('Invalid or unverified payout account');
    }

    if (amount < payoutAccount.minimumPayout) {
      throw new Error(`Minimum payout amount is ${payoutAccount.minimumPayout} ${currency}`);
    }

    const requestId = this.generateId('po');
    const fees = this.calculatePayoutFees(amount, currency);
    const netAmount = amount - fees;

    const payoutRequest: PayoutRequest = {
      id: requestId,
      userId,
      amount,
      currency,
      payoutAccountId,
      status: 'pending',
      description: `Payout to ${payoutAccount.type}`,
      fees,
      netAmount,
      requestedAt: new Date()
    };

    const userPayouts = this.payoutRequests.get(userId) || [];
    userPayouts.push(payoutRequest);
    this.payoutRequests.set(userId, userPayouts);

    // Deduct from balance immediately
    await this.updateBalance(userId, -amount);

    this.emit('payoutRequested', payoutRequest);

    // Process payout asynchronously
    this.processPayout(payoutRequest);

    return requestId;
  }

  private async processPayout(payout: PayoutRequest): Promise<void> {
    try {
      payout.status = 'processing';
      this.updatePayoutRequest(payout);

      // Simulate payout processing
      await this.simulatePayoutProcessing(payout);

      payout.status = 'completed';
      payout.processedAt = new Date();
      payout.externalTransactionId = this.generateExternalTransactionId();

      this.updatePayoutRequest(payout);
      this.emit('payoutCompleted', payout);

    } catch (error) {
      payout.status = 'failed';
      payout.failureReason = (error as Error).message;
      this.updatePayoutRequest(payout);

      // Refund to balance on failure
      await this.updateBalance(payout.userId, payout.amount);

      this.emit('payoutFailed', payout);
    }
  }

  private updatePayoutRequest(payout: PayoutRequest): void {
    const userPayouts = this.payoutRequests.get(payout.userId) || [];
    const index = userPayouts.findIndex(p => p.id === payout.id);
    if (index !== -1) {
      userPayouts[index] = payout;
      this.payoutRequests.set(payout.userId, userPayouts);
    }
  }

  public getBalance(userId: string): number {
    return this.balances.get(userId) || 0;
  }

  private async updateBalance(userId: string, amount: number): Promise<void> {
    const currentBalance = this.getBalance(userId);
    const newBalance = currentBalance + amount;
    this.balances.set(userId, Math.max(0, newBalance));
    this.emit('balanceUpdated', userId, newBalance, amount);
  }

  private calculateFees(amount: number, currency: string, type: string = 'standard'): TransactionFees {
    const platformFeeRate = 0.05; // 5%
    const processingFeeRate = type === 'escrow_release' ? 0.01 : 0.029; // Stripe-like fees
    const fixedFee = currency === 'USD' ? 0.30 : 0;

    const platformFee = amount * platformFeeRate;
    const processingFee = (amount * processingFeeRate) + fixedFee;
    const networkFee = type.includes('crypto') ? 0.001 * amount : 0;

    return {
      platformFee,
      processingFee,
      networkFee,
      total: platformFee + processingFee + (networkFee || 0)
    };
  }

  private calculatePayoutFees(amount: number, currency: string): number {
    // Simplified payout fees
    return Math.max(1.00, amount * 0.01); // 1% or minimum $1
  }

  private async getDefaultPaymentMethod(userId: string): Promise<PaymentMethod | undefined> {
    const methods = this.paymentMethods.get(userId) || [];
    return methods.find(m => m.isDefault);
  }

  private async getPayoutAccount(userId: string, accountId: string): Promise<PayoutAccount | undefined> {
    const accounts = this.payoutAccounts.get(userId) || [];
    return accounts.find(a => a.id === accountId);
  }

  private async simulatePaymentProcessing(transaction: Transaction): Promise<void> {
    // Simulate processing time
    await new Promise(resolve => setTimeout(resolve, Math.random() * 2000 + 1000));
    
    // Simulate occasional failures
    if (Math.random() < 0.05) { // 5% failure rate
      throw new Error('Payment declined by issuer');
    }
  }

  private async simulatePayoutProcessing(payout: PayoutRequest): Promise<void> {
    // Simulate processing time
    await new Promise(resolve => setTimeout(resolve, Math.random() * 5000 + 2000));
    
    // Simulate occasional failures
    if (Math.random() < 0.02) { // 2% failure rate
      throw new Error('Payout failed: Invalid account details');
    }
  }

  private startAutoReleaseTimer(): void {
    this.autoReleaseTimer = setInterval(async () => {
      await this.processAutoReleases();
    }, 60 * 60 * 1000); // Check every hour
  }

  private async processAutoReleases(): Promise<void> {
    const now = new Date();
    
    for (const [escrowId, escrow] of this.escrowAccounts) {
      if (escrow.status === 'active' && escrow.autoReleaseDate <= now) {
        try {
          await this.releaseEscrow(escrowId, 'system', 'Auto-release triggered');
        } catch (error) {
          console.error(`Failed to auto-release escrow ${escrowId}:`, error);
        }
      }
    }
  }

  private generateId(prefix: string): string {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substr(2, 9);
    return `${prefix}_${timestamp}_${random}`;
  }

  private generateClientSecret(intentId: string): string {
    return crypto
      .createHmac('sha256', 'payment-secret-key')
      .update(intentId)
      .digest('hex');
  }

  private generateExternalTransactionId(): string {
    return crypto.randomBytes(16).toString('hex');
  }

  public getUserTransactions(userId: string, limit: number = 50): Transaction[] {
    const allTransactions = Array.from(this.transactions.values());
    return allTransactions
      .filter(t => t.payerId === userId || t.payeeId === userId)
      .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
      .slice(0, limit);
  }

  public getTransaction(transactionId: string): Transaction | undefined {
    return this.transactions.get(transactionId);
  }

  public getEscrowAccount(escrowId: string): EscrowAccount | undefined {
    return this.escrowAccounts.get(escrowId);
  }

  public stop(): void {
    if (this.autoReleaseTimer) {
      clearInterval(this.autoReleaseTimer);
      this.autoReleaseTimer = null;
    }
  }
}

export default PaymentProcessor;