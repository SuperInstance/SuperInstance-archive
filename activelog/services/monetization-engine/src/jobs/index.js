const cron = require('node-cron');
const logger = require('../utils/logger');
const BillingService = require('../services/BillingService');
const CreditsService = require('../services/CreditsService');
const database = require('../config/database');

// Initialize services
const billingService = new BillingService();
const creditsService = new CreditsService();

// Job to process monthly billing
const processMonthlyBilling = cron.schedule('0 2 1 * *', async () => {
  logger.info('Starting monthly billing job');
  
  try {
    // Get all active subscriptions
    const activeSubscriptions = await database('subscriptions')
      .where('status', 'active')
      .select('*');
    
    for (const subscription of activeSubscriptions) {
      try {
        await billingService.processMonthlyBilling(subscription.user_id);
        logger.billing('Monthly billing processed', {
          userId: subscription.user_id,
          subscriptionId: subscription.id
        });
      } catch (error) {
        logger.error('Failed to process monthly billing', {
          userId: subscription.user_id,
          error: error.message
        });
      }
    }
    
    logger.info('Monthly billing job completed');
  } catch (error) {
    logger.error('Monthly billing job failed:', error);
  }
}, {
  scheduled: false
});

// Job to clean up expired credits
const cleanupExpiredCredits = cron.schedule('0 3 * * *', async () => {
  logger.info('Starting expired credits cleanup job');
  
  try {
    const expired = await database('compute_credit_transactions')
      .where('expires_at', '<', new Date())
      .where('status', 'active')
      .update({
        status: 'expired',
        updated_at: new Date()
      });
    
    logger.info('Expired credits cleanup completed', { expiredCount: expired });
  } catch (error) {
    logger.error('Expired credits cleanup failed:', error);
  }
});

// Job to process affiliate payouts
const processAffiliatePayout = cron.schedule('0 4 1 * *', async () => {
  logger.info('Starting affiliate payout job');
  
  try {
    // Get pending payouts above minimum threshold
    const pendingPayouts = await database('affiliate_payouts')
      .where('status', 'requested')
      .where('amount', '>=', 5000) // $50 minimum
      .select('*');
    
    for (const payout of pendingPayouts) {
      try {
        // Process payout via Stripe (simplified)
        await database('affiliate_payouts')
          .where('id', payout.id)
          .update({
            status: 'processing',
            processed_at: new Date(),
            updated_at: new Date()
          });
        
        logger.affiliate('Payout processed', {
          affiliateId: payout.affiliate_id,
          payoutId: payout.id,
          amount: payout.amount
        });
      } catch (error) {
        logger.error('Failed to process affiliate payout', {
          payoutId: payout.id,
          error: error.message
        });
      }
    }
    
    logger.info('Affiliate payout job completed');
  } catch (error) {
    logger.error('Affiliate payout job failed:', error);
  }
});

// Job to send billing alerts
const sendBillingAlerts = cron.schedule('0 8 * * *', async () => {
  logger.info('Starting billing alerts job');
  
  try {
    // Get users with active billing alerts
    const alerts = await database('billing_alerts')
      .where('enabled', true)
      .select('*');
    
    for (const alert of alerts) {
      try {
        const shouldTrigger = await billingService.checkAlertThreshold(alert);
        
        if (shouldTrigger) {
          // Send notification (implement notification service)
          logger.billing('Alert triggered', {
            userId: alert.user_id,
            alertType: alert.alert_type,
            threshold: alert.threshold
          });
          
          // Update last triggered
          await database('billing_alerts')
            .where('id', alert.id)
            .update({
              last_triggered: new Date(),
              updated_at: new Date()
            });
        }
      } catch (error) {
        logger.error('Failed to process billing alert', {
          alertId: alert.id,
          error: error.message
        });
      }
    }
    
    logger.info('Billing alerts job completed');
  } catch (error) {
    logger.error('Billing alerts job failed:', error);
  }
});

// Job to update affiliate tiers
const updateAffiliateTiers = cron.schedule('0 5 1 * *', async () => {
  logger.info('Starting affiliate tier update job');
  
  try {
    const affiliates = await database('affiliates')
      .where('status', 'active')
      .select('*');
    
    for (const affiliate of affiliates) {
      try {
        // Calculate performance metrics for the last 12 months
        const performance = await database('affiliate_conversions')
          .where('affiliate_id', affiliate.id)
          .where('created_at', '>=', new Date(Date.now() - 365 * 24 * 60 * 60 * 1000))
          .select(
            database.raw('COUNT(*) as conversions'),
            database.raw('SUM(commission_amount) as total_earnings')
          )
          .first();
        
        const conversions = parseInt(performance.conversions) || 0;
        const earnings = parseInt(performance.total_earnings) || 0;
        
        // Determine new tier
        let newTier = 'bronze';
        let newCommissionRate = 0.15;
        
        if (conversions >= 100 && earnings >= 10000) { // $100+, 100+ conversions
          newTier = 'platinum';
          newCommissionRate = 0.25;
        } else if (conversions >= 50 && earnings >= 5000) { // $50+, 50+ conversions
          newTier = 'gold';
          newCommissionRate = 0.20;
        } else if (conversions >= 20 && earnings >= 2000) { // $20+, 20+ conversions
          newTier = 'silver';
          newCommissionRate = 0.17;
        }
        
        // Update if different
        if (affiliate.tier_level !== newTier) {
          await database('affiliates')
            .where('id', affiliate.id)
            .update({
              tier_level: newTier,
              commission_rate: newCommissionRate,
              updated_at: new Date()
            });
          
          logger.affiliate('Tier updated', {
            affiliateId: affiliate.id,
            oldTier: affiliate.tier_level,
            newTier,
            conversions,
            earnings
          });
        }
      } catch (error) {
        logger.error('Failed to update affiliate tier', {
          affiliateId: affiliate.id,
          error: error.message
        });
      }
    }
    
    logger.info('Affiliate tier update job completed');
  } catch (error) {
    logger.error('Affiliate tier update job failed:', error);
  }
});

// Job to generate daily revenue reports
const generateDailyReports = cron.schedule('0 6 * * *', async () => {
  logger.info('Starting daily reports job');
  
  try {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    yesterday.setHours(0, 0, 0, 0);
    
    const endOfYesterday = new Date(yesterday);
    endOfYesterday.setHours(23, 59, 59, 999);
    
    // Generate revenue summary
    const [subscriptionRevenue, creditRevenue, affiliateCommissions] = await Promise.all([
      // Subscription revenue
      database('billing_history')
        .whereBetween('created_at', [yesterday, endOfYesterday])
        .where('transaction_type', 'subscription')
        .where('status', 'completed')
        .sum('amount_cents as total')
        .first(),
      
      // Credit purchases
      database('compute_credit_transactions')
        .whereBetween('created_at', [yesterday, endOfYesterday])
        .where('transaction_type', 'purchase')
        .where('status', 'completed')
        .sum('amount_cents as total')
        .first(),
      
      // Affiliate commissions paid
      database('affiliate_conversions')
        .whereBetween('created_at', [yesterday, endOfYesterday])
        .where('status', 'confirmed')
        .sum('commission_amount as total')
        .first()
    ]);
    
    const report = {
      date: yesterday.toISOString().split('T')[0],
      subscriptionRevenue: parseInt(subscriptionRevenue.total) || 0,
      creditRevenue: parseInt(creditRevenue.total) || 0,
      affiliateCommissions: parseInt(affiliateCommissions.total) || 0,
      totalRevenue: (parseInt(subscriptionRevenue.total) || 0) + (parseInt(creditRevenue.total) || 0),
      generatedAt: new Date()
    };
    
    // Store report
    await database('daily_revenue_reports').insert(report);
    
    logger.info('Daily report generated', report);
  } catch (error) {
    logger.error('Daily reports job failed:', error);
  }
});

// Job to sync with external payment processors
const syncPaymentProcessors = cron.schedule('*/15 * * * *', async () => {
  logger.info('Starting payment processor sync job');
  
  try {
    // Sync pending payment intents with Stripe
    const pendingPayments = await database('payment_intents')
      .where('status', 'pending')
      .where('created_at', '>', new Date(Date.now() - 24 * 60 * 60 * 1000)) // Last 24 hours
      .select('*');
    
    for (const payment of pendingPayments) {
      try {
        // Check status with Stripe (simplified)
        // In real implementation, you would call Stripe API
        logger.payment('Checking payment status', {
          paymentIntentId: payment.stripe_payment_intent_id
        });
      } catch (error) {
        logger.error('Failed to sync payment', {
          paymentIntentId: payment.stripe_payment_intent_id,
          error: error.message
        });
      }
    }
    
    logger.info('Payment processor sync completed');
  } catch (error) {
    logger.error('Payment processor sync job failed:', error);
  }
});

// Start all jobs
const startJobs = () => {
  try {
    processMonthlyBilling.start();
    cleanupExpiredCredits.start();
    processAffiliatePayout.start();
    sendBillingAlerts.start();
    updateAffiliateTiers.start();
    generateDailyReports.start();
    syncPaymentProcessors.start();
    
    logger.info('All cron jobs started successfully');
  } catch (error) {
    logger.error('Failed to start cron jobs:', error);
  }
};

// Stop all jobs
const stopJobs = () => {
  try {
    processMonthlyBilling.stop();
    cleanupExpiredCredits.stop();
    processAffiliatePayout.stop();
    sendBillingAlerts.stop();
    updateAffiliateTiers.stop();
    generateDailyReports.stop();
    syncPaymentProcessors.stop();
    
    logger.info('All cron jobs stopped');
  } catch (error) {
    logger.error('Failed to stop cron jobs:', error);
  }
};

// Only start jobs in production or when explicitly enabled
if (process.env.NODE_ENV === 'production' || process.env.ENABLE_CRON_JOBS === 'true') {
  startJobs();
}

// Export for manual control
module.exports = {
  startJobs,
  stopJobs,
  jobs: {
    processMonthlyBilling,
    cleanupExpiredCredits,
    processAffiliatePayout,
    sendBillingAlerts,
    updateAffiliateTiers,
    generateDailyReports,
    syncPaymentProcessors
  }
};