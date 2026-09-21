import sqlite3 from 'sqlite3';
import path from 'path';
import fs from 'fs';
import { logger } from '../utils/logger.js';

const DB_PATH = process.env.DATABASE_PATH || './data/compute-exchange.db';

export async function initializeDatabase() {
  try {
    // Create data directory if it doesn't exist
    const dbDir = path.dirname(DB_PATH);
    if (!fs.existsSync(dbDir)) {
      fs.mkdirSync(dbDir, { recursive: true });
    }

    const db = new sqlite3.Database(DB_PATH);
    
    // Enable foreign keys
    await runQuery(db, 'PRAGMA foreign_keys = ON');
    
    // Create tables
    await createTables(db);
    
    logger.info('Database initialized successfully');
    db.close();
  } catch (error) {
    logger.error('Database initialization failed:', error);
    throw error;
  }
}

function runQuery(db, query, params = []) {
  return new Promise((resolve, reject) => {
    db.run(query, params, function(err) {
      if (err) reject(err);
      else resolve(this);
    });
  });
}

async function createTables(db) {
  // Universities table
  await runQuery(db, `
    CREATE TABLE IF NOT EXISTS universities (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE,
      code TEXT NOT NULL UNIQUE,
      admin_email TEXT NOT NULL,
      contact_name TEXT,
      contact_phone TEXT,
      timezone TEXT DEFAULT 'America/New_York',
      status TEXT DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'inactive')),
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `);

  // Providers table (server farms)
  await runQuery(db, `
    CREATE TABLE IF NOT EXISTS providers (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      university_id INTEGER NOT NULL,
      name TEXT NOT NULL,
      type TEXT NOT NULL CHECK (type IN ('slurm', 'kubernetes', 'docker', 'bare_metal')),
      endpoint TEXT NOT NULL,
      ssh_host TEXT,
      ssh_port INTEGER DEFAULT 22,
      ssh_username TEXT,
      ssh_key_path TEXT,
      config_data TEXT,
      total_cpu_cores INTEGER DEFAULT 0,
      total_memory_gb INTEGER DEFAULT 0,
      total_storage_gb INTEGER DEFAULT 0,
      available_cpu_cores INTEGER DEFAULT 0,
      available_memory_gb INTEGER DEFAULT 0,
      available_storage_gb INTEGER DEFAULT 0,
      utilization_percent REAL DEFAULT 0.0,
      status TEXT DEFAULT 'active' CHECK (status IN ('active', 'maintenance', 'offline', 'error')),
      last_heartbeat DATETIME,
      reputation_score REAL DEFAULT 5.0,
      uptime_percent REAL DEFAULT 100.0,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (university_id) REFERENCES universities(id)
    )
  `);

  // Users table
  await runQuery(db, `
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      university_id INTEGER,
      username TEXT NOT NULL UNIQUE,
      email TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      first_name TEXT NOT NULL,
      last_name TEXT NOT NULL,
      role TEXT DEFAULT 'user' CHECK (role IN ('admin', 'university_admin', 'user')),
      department TEXT,
      budget_limit DECIMAL(10,4) DEFAULT 1000.0000,
      current_balance DECIMAL(10,4) DEFAULT 0.0000,
      status TEXT DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'inactive')),
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (university_id) REFERENCES universities(id)
    )
  `);

  // User preferences table
  await runQuery(db, `
    CREATE TABLE IF NOT EXISTS user_preferences (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL UNIQUE,
      preferred_providers TEXT,
      max_cost_per_hour DECIMAL(10,4) DEFAULT 10.0000,
      auto_failover BOOLEAN DEFAULT 1,
      notification_email BOOLEAN DEFAULT 1,
      notification_slack BOOLEAN DEFAULT 0,
      notification_webhook TEXT,
      preferred_quality_tier TEXT DEFAULT 'standard' CHECK (preferred_quality_tier IN ('basic', 'standard', 'premium', 'enterprise')),
      budget_alerts BOOLEAN DEFAULT 1,
      budget_alert_threshold REAL DEFAULT 0.8,
      weekend_jobs BOOLEAN DEFAULT 1,
      off_hours_only BOOLEAN DEFAULT 0,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id)
    )
  `);

  // Jobs table
  await runQuery(db, `
    CREATE TABLE IF NOT EXISTS jobs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      provider_id INTEGER,
      job_name TEXT NOT NULL,
      job_type TEXT DEFAULT 'compute' CHECK (job_type IN ('compute', 'gpu', 'memory', 'storage', 'network')),
      priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
      cpu_cores INTEGER NOT NULL,
      memory_gb INTEGER NOT NULL,
      storage_gb INTEGER DEFAULT 0,
      gpu_count INTEGER DEFAULT 0,
      estimated_duration_minutes INTEGER,
      max_cost DECIMAL(10,4),
      quality_tier TEXT DEFAULT 'standard' CHECK (quality_tier IN ('basic', 'standard', 'premium', 'enterprise')),
      command TEXT,
      environment_vars TEXT,
      docker_image TEXT,
      status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'queued', 'running', 'completed', 'failed', 'cancelled', 'timeout')),
      external_job_id TEXT,
      started_at DATETIME,
      completed_at DATETIME,
      actual_duration_minutes INTEGER,
      exit_code INTEGER,
      error_message TEXT,
      output_path TEXT,
      scheduled_start DATETIME,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id),
      FOREIGN KEY (provider_id) REFERENCES providers(id)
    )
  `);

  // Job queue table
  await runQuery(db, `
    CREATE TABLE IF NOT EXISTS job_queue (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      job_id INTEGER NOT NULL,
      queue_position INTEGER,
      priority_score REAL,
      estimated_wait_minutes INTEGER,
      resource_requirements TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (job_id) REFERENCES jobs(id)
    )
  `);

  // Pricing table
  await runQuery(db, `
    CREATE TABLE IF NOT EXISTS pricing (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      provider_id INTEGER NOT NULL,
      job_type TEXT NOT NULL,
      quality_tier TEXT NOT NULL,
      base_rate DECIMAL(10,6) NOT NULL,
      current_rate DECIMAL(10,6) NOT NULL,
      peak_multiplier REAL DEFAULT 2.0,
      off_peak_multiplier REAL DEFAULT 0.5,
      weekend_multiplier REAL DEFAULT 0.7,
      summer_multiplier REAL DEFAULT 0.6,
      bulk_discount_threshold INTEGER DEFAULT 1000,
      bulk_discount_rate REAL DEFAULT 0.2,
      demand_multiplier REAL DEFAULT 1.0,
      effective_from DATETIME DEFAULT CURRENT_TIMESTAMP,
      effective_until DATETIME,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (provider_id) REFERENCES providers(id)
    )
  `);

  // Billing table
  await runQuery(db, `
    CREATE TABLE IF NOT EXISTS billing (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      job_id INTEGER NOT NULL,
      user_id INTEGER NOT NULL,
      provider_id INTEGER NOT NULL,
      university_id INTEGER NOT NULL,
      billing_period_start DATETIME NOT NULL,
      billing_period_end DATETIME NOT NULL,
      cpu_hours DECIMAL(10,4) DEFAULT 0.0000,
      memory_gb_hours DECIMAL(10,4) DEFAULT 0.0000,
      storage_gb_hours DECIMAL(10,4) DEFAULT 0.0000,
      gpu_hours DECIMAL(10,4) DEFAULT 0.0000,
      base_cost DECIMAL(10,4) NOT NULL,
      multiplier_applied REAL DEFAULT 1.0,
      discount_applied DECIMAL(10,4) DEFAULT 0.0000,
      final_cost DECIMAL(10,4) NOT NULL,
      billing_status TEXT DEFAULT 'pending' CHECK (billing_status IN ('pending', 'approved', 'paid', 'disputed')),
      invoice_number TEXT,
      paid_at DATETIME,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (job_id) REFERENCES jobs(id),
      FOREIGN KEY (user_id) REFERENCES users(id),
      FOREIGN KEY (provider_id) REFERENCES providers(id),
      FOREIGN KEY (university_id) REFERENCES universities(id)
    )
  `);

  // SLA agreements table
  await runQuery(db, `
    CREATE TABLE IF NOT EXISTS sla_agreements (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      provider_id INTEGER NOT NULL,
      quality_tier TEXT NOT NULL,
      uptime_guarantee REAL NOT NULL,
      max_response_time_ms INTEGER NOT NULL,
      max_queue_time_minutes INTEGER NOT NULL,
      penalty_rate REAL DEFAULT 0.1,
      compensation_method TEXT DEFAULT 'credit' CHECK (compensation_method IN ('credit', 'refund', 'discount')),
      effective_from DATETIME DEFAULT CURRENT_TIMESTAMP,
      effective_until DATETIME,
      status TEXT DEFAULT 'active' CHECK (status IN ('active', 'expired', 'suspended')),
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (provider_id) REFERENCES providers(id)
    )
  `);

  // SLA violations table
  await runQuery(db, `
    CREATE TABLE IF NOT EXISTS sla_violations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      job_id INTEGER NOT NULL,
      provider_id INTEGER NOT NULL,
      sla_agreement_id INTEGER NOT NULL,
      violation_type TEXT NOT NULL CHECK (violation_type IN ('uptime', 'response_time', 'queue_time', 'availability')),
      expected_value REAL NOT NULL,
      actual_value REAL NOT NULL,
      impact_severity TEXT DEFAULT 'medium' CHECK (impact_severity IN ('low', 'medium', 'high', 'critical')),
      compensation_amount DECIMAL(10,4) DEFAULT 0.0000,
      status TEXT DEFAULT 'detected' CHECK (status IN ('detected', 'investigating', 'resolved', 'disputed')),
      resolution_notes TEXT,
      detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      resolved_at DATETIME,
      FOREIGN KEY (job_id) REFERENCES jobs(id),
      FOREIGN KEY (provider_id) REFERENCES providers(id),
      FOREIGN KEY (sla_agreement_id) REFERENCES sla_agreements(id)
    )
  `);

  // Provider reputation history table
  await runQuery(db, `
    CREATE TABLE IF NOT EXISTS provider_reputation (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      provider_id INTEGER NOT NULL,
      job_id INTEGER,
      rating REAL NOT NULL CHECK (rating >= 1.0 AND rating <= 5.0),
      factor_type TEXT NOT NULL CHECK (factor_type IN ('uptime', 'performance', 'reliability', 'support', 'pricing', 'sla_compliance')),
      impact_weight REAL DEFAULT 1.0,
      notes TEXT,
      recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (provider_id) REFERENCES providers(id),
      FOREIGN KEY (job_id) REFERENCES jobs(id)
    )
  `);

  // Failover events table
  await runQuery(db, `
    CREATE TABLE IF NOT EXISTS failover_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      job_id INTEGER NOT NULL,
      original_provider_id INTEGER NOT NULL,
      failover_provider_id INTEGER NOT NULL,
      trigger_reason TEXT NOT NULL,
      trigger_threshold TEXT,
      response_time_ms INTEGER,
      success BOOLEAN DEFAULT 0,
      error_message TEXT,
      cost_impact DECIMAL(10,4) DEFAULT 0.0000,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (job_id) REFERENCES jobs(id),
      FOREIGN KEY (original_provider_id) REFERENCES providers(id),
      FOREIGN KEY (failover_provider_id) REFERENCES providers(id)
    )
  `);

  // Capacity monitoring table
  await runQuery(db, `
    CREATE TABLE IF NOT EXISTS capacity_monitoring (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      provider_id INTEGER NOT NULL,
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
      cpu_utilization REAL DEFAULT 0.0,
      memory_utilization REAL DEFAULT 0.0,
      storage_utilization REAL DEFAULT 0.0,
      network_utilization REAL DEFAULT 0.0,
      active_jobs INTEGER DEFAULT 0,
      queued_jobs INTEGER DEFAULT 0,
      avg_response_time_ms INTEGER DEFAULT 0,
      spare_capacity_percent REAL DEFAULT 100.0,
      predicted_capacity_1h REAL,
      predicted_capacity_24h REAL,
      FOREIGN KEY (provider_id) REFERENCES providers(id)
    )
  `);

  // Organization bulk rates table
  await runQuery(db, `
    CREATE TABLE IF NOT EXISTS bulk_rates (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      university_id INTEGER NOT NULL,
      provider_id INTEGER,
      tier_name TEXT NOT NULL,
      minimum_monthly_spend DECIMAL(10,4) NOT NULL,
      discount_percentage REAL NOT NULL,
      cpu_hour_commitment INTEGER DEFAULT 0,
      gpu_hour_commitment INTEGER DEFAULT 0,
      contract_start DATETIME NOT NULL,
      contract_end DATETIME NOT NULL,
      auto_renew BOOLEAN DEFAULT 0,
      status TEXT DEFAULT 'active' CHECK (status IN ('active', 'expired', 'suspended', 'pending')),
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (university_id) REFERENCES universities(id),
      FOREIGN KEY (provider_id) REFERENCES providers(id)
    )
  `);

  logger.info('All database tables created successfully');
}

export function getDb() {
  return new sqlite3.Database(DB_PATH);
}