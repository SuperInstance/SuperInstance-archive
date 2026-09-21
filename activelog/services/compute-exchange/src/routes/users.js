import express from 'express';
import Joi from 'joi';
import { getDb } from '../database/init.js';
import { authMiddleware, requireRole } from '../middleware/auth.js';
import { logger } from '../utils/logger.js';

const router = express.Router();

// Validation schemas
const updatePreferencesSchema = Joi.object({
  preferred_providers: Joi.string().optional(),
  max_cost_per_hour: Joi.number().min(0).precision(4).optional(),
  auto_failover: Joi.boolean().optional(),
  notification_email: Joi.boolean().optional(),
  notification_slack: Joi.boolean().optional(),
  notification_webhook: Joi.string().uri().allow('').optional(),
  preferred_quality_tier: Joi.string().valid('basic', 'standard', 'premium', 'enterprise').optional(),
  budget_alerts: Joi.boolean().optional(),
  budget_alert_threshold: Joi.number().min(0).max(1).optional(),
  weekend_jobs: Joi.boolean().optional(),
  off_hours_only: Joi.boolean().optional()
});

const updateProfileSchema = Joi.object({
  first_name: Joi.string().min(1).max(100).optional(),
  last_name: Joi.string().min(1).max(100).optional(),
  department: Joi.string().max(100).allow('').optional(),
  budget_limit: Joi.number().min(0).precision(4).optional()
});

// Get current user profile
router.get('/profile', authMiddleware, async (req, res) => {
  try {
    const user = await getUserWithPreferences(req.user.id);
    
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    // Don't return password hash
    delete user.password_hash;
    
    res.json(user);
  } catch (error) {
    logger.error('Failed to get user profile:', error);
    res.status(500).json({ error: 'Failed to get profile' });
  }
});

// Update user profile
router.put('/profile', authMiddleware, async (req, res) => {
  try {
    const { error, value } = updateProfileSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    await updateUserProfile(req.user.id, value);
    
    logger.info(`Profile updated for user ${req.user.id}`);
    
    res.json({ 
      message: 'Profile updated successfully',
      updated_fields: Object.keys(value)
    });
  } catch (error) {
    logger.error('Failed to update user profile:', error);
    res.status(500).json({ error: 'Failed to update profile' });
  }
});

// Get user preferences
router.get('/preferences', authMiddleware, async (req, res) => {
  try {
    const preferences = await getUserPreferences(req.user.id);
    
    if (!preferences) {
      // Create default preferences if none exist
      await createDefaultPreferences(req.user.id);
      const defaultPrefs = await getUserPreferences(req.user.id);
      return res.json(defaultPrefs);
    }
    
    res.json(preferences);
  } catch (error) {
    logger.error('Failed to get user preferences:', error);
    res.status(500).json({ error: 'Failed to get preferences' });
  }
});

// Update user preferences
router.put('/preferences', authMiddleware, async (req, res) => {
  try {
    const { error, value } = updatePreferencesSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    // Check if preferences exist
    const existingPrefs = await getUserPreferences(req.user.id);
    
    if (!existingPrefs) {
      // Create preferences with submitted values
      await createUserPreferences(req.user.id, value);
    } else {
      // Update existing preferences
      await updateUserPreferences(req.user.id, value);
    }
    
    logger.info(`Preferences updated for user ${req.user.id}:`, Object.keys(value));
    
    res.json({ 
      message: 'Preferences updated successfully',
      updated_fields: Object.keys(value)
    });
  } catch (error) {
    logger.error('Failed to update user preferences:', error);
    res.status(500).json({ error: 'Failed to update preferences' });
  }
});

// Get user spending summary
router.get('/spending', authMiddleware, async (req, res) => {
  try {
    const period = req.query.period || 'month'; // month, week, day
    const spending = await getUserSpending(req.user.id, period);
    
    res.json(spending);
  } catch (error) {
    logger.error('Failed to get user spending:', error);
    res.status(500).json({ error: 'Failed to get spending data' });
  }
});

// Get user usage statistics
router.get('/usage', authMiddleware, async (req, res) => {
  try {
    const days = Math.min(parseInt(req.query.days) || 30, 365);
    const usage = await getUserUsageStats(req.user.id, days);
    
    res.json(usage);
  } catch (error) {
    logger.error('Failed to get user usage:', error);
    res.status(500).json({ error: 'Failed to get usage statistics' });
  }
});

// Reset user preferences to defaults
router.post('/preferences/reset', authMiddleware, async (req, res) => {
  try {
    await deleteUserPreferences(req.user.id);
    await createDefaultPreferences(req.user.id);
    
    const newPreferences = await getUserPreferences(req.user.id);
    
    logger.info(`Preferences reset to defaults for user ${req.user.id}`);
    
    res.json({
      message: 'Preferences reset to defaults',
      preferences: newPreferences
    });
  } catch (error) {
    logger.error('Failed to reset preferences:', error);
    res.status(500).json({ error: 'Failed to reset preferences' });
  }
});

// Get preferred providers for user
router.get('/preferred-providers', authMiddleware, async (req, res) => {
  try {
    const preferences = await getUserPreferences(req.user.id);
    
    if (!preferences || !preferences.preferred_providers) {
      return res.json({ preferred_providers: [] });
    }
    
    const providerIds = preferences.preferred_providers.split(',').map(id => parseInt(id.trim()));
    const providers = await getProvidersByIds(providerIds);
    
    res.json({ 
      preferred_providers: providers,
      preference_order: providerIds
    });
  } catch (error) {
    logger.error('Failed to get preferred providers:', error);
    res.status(500).json({ error: 'Failed to get preferred providers' });
  }
});

// Update preferred providers
router.put('/preferred-providers', authMiddleware, async (req, res) => {
  try {
    const { provider_ids } = req.body;
    
    if (!Array.isArray(provider_ids)) {
      return res.status(400).json({ error: 'provider_ids must be an array' });
    }
    
    // Validate provider IDs exist and are active
    const validProviders = await getProvidersByIds(provider_ids);
    const validIds = validProviders.map(p => p.id);
    
    if (validIds.length !== provider_ids.length) {
      return res.status(400).json({ 
        error: 'Some provider IDs are invalid',
        valid_ids: validIds,
        requested_ids: provider_ids
      });
    }
    
    const preferredProvidersString = provider_ids.join(',');
    await updateUserPreferences(req.user.id, { 
      preferred_providers: preferredProvidersString 
    });
    
    logger.info(`Preferred providers updated for user ${req.user.id}:`, provider_ids);
    
    res.json({
      message: 'Preferred providers updated',
      preferred_providers: validProviders
    });
  } catch (error) {
    logger.error('Failed to update preferred providers:', error);
    res.status(500).json({ error: 'Failed to update preferred providers' });
  }
});

// Get notification settings
router.get('/notifications', authMiddleware, async (req, res) => {
  try {
    const preferences = await getUserPreferences(req.user.id);
    
    const notifications = {
      email: preferences?.notification_email || false,
      slack: preferences?.notification_slack || false,
      webhook: preferences?.notification_webhook || '',
      budget_alerts: preferences?.budget_alerts || false,
      budget_alert_threshold: preferences?.budget_alert_threshold || 0.8
    };
    
    res.json(notifications);
  } catch (error) {
    logger.error('Failed to get notification settings:', error);
    res.status(500).json({ error: 'Failed to get notification settings' });
  }
});

// Update notification settings
router.put('/notifications', authMiddleware, async (req, res) => {
  try {
    const notificationUpdates = {};
    const allowedFields = ['notification_email', 'notification_slack', 'notification_webhook', 'budget_alerts', 'budget_alert_threshold'];
    
    for (const field of allowedFields) {
      if (req.body.hasOwnProperty(field)) {
        notificationUpdates[field] = req.body[field];
      }
    }
    
    if (Object.keys(notificationUpdates).length === 0) {
      return res.status(400).json({ error: 'No notification settings provided' });
    }
    
    const { error } = updatePreferencesSchema.validate(notificationUpdates);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }
    
    await updateUserPreferences(req.user.id, notificationUpdates);
    
    logger.info(`Notification settings updated for user ${req.user.id}:`, Object.keys(notificationUpdates));
    
    res.json({
      message: 'Notification settings updated',
      updated_settings: notificationUpdates
    });
  } catch (error) {
    logger.error('Failed to update notification settings:', error);
    res.status(500).json({ error: 'Failed to update notification settings' });
  }
});

// Helper functions
async function getUserWithPreferences(userId) {
  const db = getDb();
  try {
    return await new Promise((resolve, reject) => {
      db.get(`
        SELECT u.*, up.preferred_providers, up.max_cost_per_hour, up.auto_failover,
               up.notification_email, up.notification_slack, up.notification_webhook,
               up.preferred_quality_tier, up.budget_alerts, up.budget_alert_threshold,
               up.weekend_jobs, up.off_hours_only
        FROM users u
        LEFT JOIN user_preferences up ON u.id = up.user_id
        WHERE u.id = ?
      `, [userId], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
  } finally {
    db.close();
  }
}

async function updateUserProfile(userId, updates) {
  const db = getDb();
  try {
    const fields = Object.keys(updates).map(key => `${key} = ?`).join(', ');
    const values = [...Object.values(updates), userId];
    
    await new Promise((resolve, reject) => {
      db.run(
        `UPDATE users SET ${fields}, updated_at = CURRENT_TIMESTAMP WHERE id = ?`,
        values,
        (err) => {
          if (err) reject(err);
          else resolve();
        }
      );
    });
  } finally {
    db.close();
  }
}

async function getUserPreferences(userId) {
  const db = getDb();
  try {
    return await new Promise((resolve, reject) => {
      db.get('SELECT * FROM user_preferences WHERE user_id = ?', [userId], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
  } finally {
    db.close();
  }
}

async function createDefaultPreferences(userId) {
  const db = getDb();
  try {
    await new Promise((resolve, reject) => {
      db.run(`
        INSERT INTO user_preferences (
          user_id, preferred_providers, max_cost_per_hour, auto_failover,
          notification_email, notification_slack, notification_webhook,
          preferred_quality_tier, budget_alerts, budget_alert_threshold,
          weekend_jobs, off_hours_only, created_at, updated_at
        ) VALUES (?, '', 10.0000, 1, 1, 0, '', 'standard', 1, 0.8, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
      `, [userId], (err) => {
        if (err) reject(err);
        else resolve();
      });
    });
  } finally {
    db.close();
  }
}

async function createUserPreferences(userId, preferences) {
  const db = getDb();
  try {
    const defaultPrefs = {
      preferred_providers: '',
      max_cost_per_hour: 10.0000,
      auto_failover: true,
      notification_email: true,
      notification_slack: false,
      notification_webhook: '',
      preferred_quality_tier: 'standard',
      budget_alerts: true,
      budget_alert_threshold: 0.8,
      weekend_jobs: true,
      off_hours_only: false,
      ...preferences
    };

    const fields = Object.keys(defaultPrefs).join(', ');
    const placeholders = Object.keys(defaultPrefs).map(() => '?').join(', ');
    const values = [userId, ...Object.values(defaultPrefs)];

    await new Promise((resolve, reject) => {
      db.run(`
        INSERT INTO user_preferences (
          user_id, ${fields}, created_at, updated_at
        ) VALUES (?, ${placeholders}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
      `, values, (err) => {
        if (err) reject(err);
        else resolve();
      });
    });
  } finally {
    db.close();
  }
}

async function updateUserPreferences(userId, updates) {
  const db = getDb();
  try {
    const fields = Object.keys(updates).map(key => `${key} = ?`).join(', ');
    const values = [...Object.values(updates), userId];
    
    await new Promise((resolve, reject) => {
      db.run(
        `UPDATE user_preferences SET ${fields}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?`,
        values,
        (err) => {
          if (err) reject(err);
          else resolve();
        }
      );
    });
  } finally {
    db.close();
  }
}

async function deleteUserPreferences(userId) {
  const db = getDb();
  try {
    await new Promise((resolve, reject) => {
      db.run('DELETE FROM user_preferences WHERE user_id = ?', [userId], (err) => {
        if (err) reject(err);
        else resolve();
      });
    });
  } finally {
    db.close();
  }
}

async function getUserSpending(userId, period) {
  const db = getDb();
  try {
    let dateFilter;
    switch (period) {
      case 'day':
        dateFilter = "date('now')";
        break;
      case 'week':
        dateFilter = "date('now', '-7 days')";
        break;
      case 'month':
      default:
        dateFilter = "date('now', 'start of month')";
        break;
    }

    return await new Promise((resolve, reject) => {
      db.get(`
        SELECT 
          COUNT(*) as job_count,
          COALESCE(SUM(final_cost), 0) as total_spent,
          COALESCE(AVG(final_cost), 0) as avg_cost_per_job,
          COALESCE(MAX(final_cost), 0) as highest_cost,
          COALESCE(SUM(cpu_hours), 0) as total_cpu_hours,
          COALESCE(SUM(gpu_hours), 0) as total_gpu_hours
        FROM billing 
        WHERE user_id = ? 
          AND billing_period_start >= ${dateFilter}
          AND billing_status IN ('approved', 'paid')
      `, [userId], (err, row) => {
        if (err) reject(err);
        else resolve({
          period,
          ...row,
          total_spent: parseFloat(row.total_spent).toFixed(4),
          avg_cost_per_job: parseFloat(row.avg_cost_per_job).toFixed(4),
          highest_cost: parseFloat(row.highest_cost).toFixed(4)
        });
      });
    });
  } finally {
    db.close();
  }
}

async function getUserUsageStats(userId, days) {
  const db = getDb();
  try {
    return await new Promise((resolve, reject) => {
      db.get(`
        SELECT 
          COUNT(*) as total_jobs,
          SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_jobs,
          SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_jobs,
          AVG(CASE WHEN actual_duration_minutes > 0 THEN actual_duration_minutes END) as avg_duration,
          SUM(CASE WHEN actual_duration_minutes > 0 THEN actual_duration_minutes ELSE 0 END) as total_compute_minutes,
          COUNT(DISTINCT DATE(created_at)) as active_days
        FROM jobs 
        WHERE user_id = ? 
          AND created_at >= date('now', '-${days} days')
      `, [userId], (err, row) => {
        if (err) reject(err);
        else resolve({
          period_days: days,
          ...row,
          success_rate: row.total_jobs > 0 ? (row.completed_jobs / row.total_jobs * 100).toFixed(1) : 0,
          avg_duration_minutes: Math.round(row.avg_duration || 0),
          total_compute_hours: Math.round((row.total_compute_minutes || 0) / 60)
        });
      });
    });
  } finally {
    db.close();
  }
}

async function getProvidersByIds(providerIds) {
  if (!providerIds.length) return [];
  
  const db = getDb();
  try {
    const placeholders = providerIds.map(() => '?').join(',');
    
    return await new Promise((resolve, reject) => {
      db.all(`
        SELECT id, name, type, university_id, status, reputation_score
        FROM providers 
        WHERE id IN (${placeholders}) AND status = 'active'
        ORDER BY reputation_score DESC
      `, providerIds, (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
  } finally {
    db.close();
  }
}

export default router;