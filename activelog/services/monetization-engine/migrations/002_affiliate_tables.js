exports.up = function(knex) {
  return Promise.all([

    // Affiliates
    knex.schema.createTable('affiliates', table => {
      table.increments('id').primary();
      table.integer('user_id').references('id').inTable('users').onDelete('SET NULL');
      table.string('name').notNullable();
      table.string('email').unique().notNullable();
      table.string('affiliate_code').unique().notNullable();
      table.string('website');
      table.json('social_media'); // array of social media profiles
      table.text('audience'); // description of their audience
      table.string('promotion_method'); // how they plan to promote
      table.string('tax_id'); // for tax reporting
      table.string('payment_method').defaultTo('stripe'); // stripe, paypal, bank_transfer
      table.decimal('commission_rate', 5, 4).defaultTo(0.15); // 15% default
      table.string('tier_level').defaultTo('bronze'); // bronze, silver, gold, platinum
      table.string('status').defaultTo('pending'); // pending, active, suspended, rejected
      table.text('notes'); // internal notes about the affiliate
      table.timestamps(true, true);
      table.index(['affiliate_code']);
      table.index(['email']);
      table.index(['status']);
      table.index(['tier_level']);
    }),

    // Affiliate links
    knex.schema.createTable('affiliate_links', table => {
      table.increments('id').primary();
      table.integer('affiliate_id').references('id').inTable('affiliates').onDelete('CASCADE');
      table.string('short_code').unique().notNullable();
      table.text('target_url').notNullable();
      table.text('affiliate_url').notNullable();
      table.text('short_url').notNullable();
      table.string('campaign').defaultTo('default');
      table.string('medium').defaultTo('affiliate');
      table.string('content'); // additional content parameter
      table.integer('total_clicks').defaultTo(0);
      table.integer('total_conversions').defaultTo(0);
      table.integer('total_earnings').defaultTo(0); // in cents
      table.boolean('is_active').defaultTo(true);
      table.timestamps(true, true);
      table.index(['affiliate_id']);
      table.index(['short_code']);
      table.index(['campaign']);
      table.index(['is_active']);
    }),

    // Affiliate clicks tracking
    knex.schema.createTable('affiliate_clicks', table => {
      table.increments('id').primary();
      table.integer('affiliate_id').references('id').inTable('affiliates').onDelete('CASCADE');
      table.integer('affiliate_link_id').references('id').inTable('affiliate_links').onDelete('CASCADE');
      table.string('ip_address');
      table.text('user_agent');
      table.text('referer');
      table.string('accept_language');
      table.string('utm_source');
      table.string('utm_medium');
      table.string('utm_campaign');
      table.string('utm_content');
      table.string('utm_term');
      table.string('country_code', 2); // ISO country code
      table.string('device_type'); // mobile, desktop, tablet
      table.timestamp('created_at').defaultTo(knex.fn.now());
      table.index(['affiliate_id']);
      table.index(['affiliate_link_id']);
      table.index(['created_at']);
      table.index(['ip_address']);
    }),

    // Affiliate conversions
    knex.schema.createTable('affiliate_conversions', table => {
      table.increments('id').primary();
      table.integer('affiliate_id').references('id').inTable('affiliates').onDelete('CASCADE');
      table.integer('affiliate_click_id').references('id').inTable('affiliate_clicks').onDelete('SET NULL');
      table.integer('customer_id').references('id').inTable('users').onDelete('CASCADE');
      table.string('order_id').notNullable();
      table.integer('order_value').notNullable(); // in cents
      table.string('currency', 3).defaultTo('usd');
      table.string('product_type'); // subscription, one_time, credits
      table.decimal('commission_rate', 5, 4).notNullable();
      table.integer('commission_amount').notNullable(); // in cents
      table.string('status').defaultTo('confirmed'); // pending, confirmed, rejected, refunded
      table.text('notes');
      table.timestamps(true, true);
      table.index(['affiliate_id']);
      table.index(['customer_id']);
      table.index(['order_id']);
      table.index(['status']);
      table.index(['created_at']);
    }),

    // Affiliate payouts
    knex.schema.createTable('affiliate_payouts', table => {
      table.increments('id').primary();
      table.integer('affiliate_id').references('id').inTable('affiliates').onDelete('CASCADE');
      table.integer('amount').notNullable(); // in cents
      table.string('currency', 3).defaultTo('usd');
      table.string('payment_method').notNullable(); // stripe, paypal, bank_transfer
      table.string('status').defaultTo('requested'); // requested, processing, completed, failed
      table.string('payment_reference'); // external payment ID
      table.text('notes');
      table.timestamp('requested_at').defaultTo(knex.fn.now());
      table.timestamp('processed_at');
      table.json('payment_details'); // payment method specific details
      table.timestamps(true, true);
      table.index(['affiliate_id']);
      table.index(['status']);
      table.index(['requested_at']);
      table.index(['processed_at']);
    }),

    // Affiliate marketing materials
    knex.schema.createTable('affiliate_materials', table => {
      table.increments('id').primary();
      table.string('title').notNullable();
      table.string('type').notNullable(); // banner, text_ad, email_template, social_post
      table.string('category'); // general, product_specific, seasonal
      table.text('content'); // HTML content, text, or JSON data
      table.string('image_url');
      table.string('size'); // for banners: 728x90, 300x250, etc.
      table.json('tier_access'); // which tiers can access this material
      table.boolean('is_active').defaultTo(true);
      table.integer('usage_count').defaultTo(0);
      table.timestamps(true, true);
      table.index(['type']);
      table.index(['category']);
      table.index(['is_active']);
    }),

    // Affiliate material usage tracking
    knex.schema.createTable('affiliate_material_usage', table => {
      table.increments('id').primary();
      table.integer('affiliate_id').references('id').inTable('affiliates').onDelete('CASCADE');
      table.integer('material_id').references('id').inTable('affiliate_materials').onDelete('CASCADE');
      table.timestamp('used_at').defaultTo(knex.fn.now());
      table.string('usage_context'); // download, view, copy
      table.index(['affiliate_id']);
      table.index(['material_id']);
      table.index(['used_at']);
    })

  ]);
};

exports.down = function(knex) {
  return Promise.all([
    knex.schema.dropTableIfExists('affiliate_material_usage'),
    knex.schema.dropTableIfExists('affiliate_materials'),
    knex.schema.dropTableIfExists('affiliate_payouts'),
    knex.schema.dropTableIfExists('affiliate_conversions'),
    knex.schema.dropTableIfExists('affiliate_clicks'),
    knex.schema.dropTableIfExists('affiliate_links'),
    knex.schema.dropTableIfExists('affiliates')
  ]);
};