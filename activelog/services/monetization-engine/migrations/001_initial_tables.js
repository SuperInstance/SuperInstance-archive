exports.up = function(knex) {
  return Promise.all([
    
    // Users table (if not exists in main system)
    knex.schema.hasTable('users').then(exists => {
      if (!exists) {
        return knex.schema.createTable('users', table => {
          table.increments('id').primary();
          table.string('email').unique().notNullable();
          table.string('name').notNullable();
          table.string('password_hash');
          table.string('role').defaultTo('user');
          table.boolean('email_verified').defaultTo(false);
          table.timestamps(true, true);
          table.index(['email']);
        });
      }
    }),

    // Stripe customers
    knex.schema.createTable('stripe_customers', table => {
      table.increments('id').primary();
      table.integer('user_id').references('id').inTable('users').onDelete('CASCADE');
      table.string('stripe_customer_id').unique().notNullable();
      table.string('email');
      table.string('name');
      table.string('phone');
      table.json('address');
      table.json('metadata');
      table.timestamps(true, true);
      table.index(['stripe_customer_id']);
      table.index(['user_id']);
    }),

    // Subscriptions
    knex.schema.createTable('subscriptions', table => {
      table.increments('id').primary();
      table.integer('user_id').references('id').inTable('users').onDelete('CASCADE');
      table.string('stripe_subscription_id').unique();
      table.string('stripe_customer_id').references('stripe_customer_id').inTable('stripe_customers');
      table.string('plan').notNullable(); // free, pro, enterprise
      table.string('status').notNullable(); // active, canceled, past_due, etc.
      table.timestamp('current_period_start');
      table.timestamp('current_period_end');
      table.timestamp('trial_start');
      table.timestamp('trial_end');
      table.timestamp('cancel_at');
      table.timestamp('canceled_at');
      table.json('metadata');
      table.timestamps(true, true);
      table.index(['user_id']);
      table.index(['status']);
      table.index(['plan']);
    }),

    // Payment intents
    knex.schema.createTable('payment_intents', table => {
      table.increments('id').primary();
      table.string('stripe_payment_intent_id').unique().notNullable();
      table.integer('amount').notNullable();
      table.string('currency', 3).defaultTo('usd');
      table.string('status').notNullable();
      table.string('customer_id');
      table.json('metadata');
      table.timestamp('created_at');
      table.timestamp('updated_at').defaultTo(knex.fn.now());
      table.index(['stripe_payment_intent_id']);
      table.index(['status']);
    }),

    // Usage metrics
    knex.schema.createTable('usage_metrics', table => {
      table.increments('id').primary();
      table.integer('user_id').references('id').inTable('users').onDelete('CASCADE');
      table.date('period_start').notNullable();
      table.date('period_end').notNullable();
      table.decimal('storage_gb', 10, 2).defaultTo(0);
      table.integer('api_calls_current_month').defaultTo(0);
      table.integer('active_users').defaultTo(1);
      table.integer('compute_credits_used').defaultTo(0);
      table.integer('compute_credits_available').defaultTo(0);
      table.decimal('bandwidth_gb', 10, 2).defaultTo(0);
      table.timestamps(true, true);
      table.index(['user_id']);
      table.index(['period_start']);
      table.unique(['user_id', 'period_start']);
    }),

    // Compute credit transactions
    knex.schema.createTable('compute_credit_transactions', table => {
      table.increments('id').primary();
      table.integer('user_id').references('id').inTable('users').onDelete('CASCADE');
      table.string('transaction_type').notNullable(); // purchase, usage, refund
      table.integer('credits').notNullable();
      table.integer('amount_cents'); // For purchases
      table.integer('discount_amount').defaultTo(0);
      table.string('stripe_payment_intent_id');
      table.string('status').defaultTo('completed'); // pending, completed, failed
      table.text('description');
      table.timestamps(true, true);
      table.index(['user_id']);
      table.index(['transaction_type']);
      table.index(['created_at']);
    }),

    // Billing history
    knex.schema.createTable('billing_history', table => {
      table.increments('id').primary();
      table.integer('user_id').references('id').inTable('users').onDelete('CASCADE');
      table.string('transaction_type').notNullable(); // subscription, overage, credits, refund
      table.string('description').notNullable();
      table.integer('amount_cents').notNullable();
      table.string('currency', 3).defaultTo('usd');
      table.string('status').notNullable(); // pending, completed, failed, refunded
      table.string('stripe_payment_intent_id');
      table.string('stripe_invoice_id');
      table.json('metadata');
      table.timestamps(true, true);
      table.index(['user_id']);
      table.index(['transaction_type']);
      table.index(['status']);
      table.index(['created_at']);
    }),

    // Billing alerts
    knex.schema.createTable('billing_alerts', table => {
      table.increments('id').primary();
      table.integer('user_id').references('id').inTable('users').onDelete('CASCADE');
      table.string('alert_type').notNullable(); // usage_threshold, cost_threshold, credit_low
      table.decimal('threshold', 10, 2).notNullable();
      table.boolean('enabled').defaultTo(true);
      table.timestamp('last_triggered');
      table.timestamps(true, true);
      table.index(['user_id']);
      table.index(['alert_type']);
      table.index(['enabled']);
    }),

    // Spending limits
    knex.schema.createTable('spending_limits', table => {
      table.increments('id').primary();
      table.integer('user_id').references('id').inTable('users').onDelete('CASCADE').unique();
      table.integer('monthly_limit').notNullable(); // in cents
      table.json('alert_thresholds'); // array of percentage thresholds
      table.boolean('hard_limit').defaultTo(false); // whether to block usage when limit reached
      table.timestamps(true, true);
      table.index(['user_id']);
    }),

    // Promo codes
    knex.schema.createTable('promo_codes', table => {
      table.increments('id').primary();
      table.string('code').unique().notNullable();
      table.string('description');
      table.string('discount_type').notNullable(); // percentage, fixed_amount
      table.decimal('discount_percentage', 5, 2); // 0-100
      table.integer('discount_amount'); // in cents
      table.integer('max_uses');
      table.integer('current_uses').defaultTo(0);
      table.boolean('active').defaultTo(true);
      table.timestamp('expires_at');
      table.json('applicable_plans'); // which plans this code applies to
      table.timestamps(true, true);
      table.index(['code']);
      table.index(['active']);
      table.index(['expires_at']);
    }),

    // Promo code usage
    knex.schema.createTable('promo_code_usage', table => {
      table.increments('id').primary();
      table.integer('user_id').references('id').inTable('users').onDelete('CASCADE');
      table.integer('promo_code_id').references('id').inTable('promo_codes').onDelete('CASCADE');
      table.integer('discount_amount'); // actual discount applied in cents
      table.decimal('discount_percentage', 5, 2);
      table.timestamp('applied_at').defaultTo(knex.fn.now());
      table.unique(['user_id', 'promo_code_id']);
      table.index(['user_id']);
      table.index(['promo_code_id']);
    })

  ]);
};

exports.down = function(knex) {
  return Promise.all([
    knex.schema.dropTableIfExists('promo_code_usage'),
    knex.schema.dropTableIfExists('promo_codes'),
    knex.schema.dropTableIfExists('spending_limits'),
    knex.schema.dropTableIfExists('billing_alerts'),
    knex.schema.dropTableIfExists('billing_history'),
    knex.schema.dropTableIfExists('compute_credit_transactions'),
    knex.schema.dropTableIfExists('usage_metrics'),
    knex.schema.dropTableIfExists('payment_intents'),
    knex.schema.dropTableIfExists('subscriptions'),
    knex.schema.dropTableIfExists('stripe_customers')
    // Don't drop users table as it might be used by other services
  ]);
};