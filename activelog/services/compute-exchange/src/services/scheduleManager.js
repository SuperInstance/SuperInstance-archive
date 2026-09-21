import { getDb } from '../database/init.js';
import { logger } from '../utils/logger.js';
import moment from 'moment-timezone';
import cron from 'node-cron';

export class ScheduleManager {
  constructor() {
    this.scheduledTasks = new Map();
    this.academicCalendar = new Map();
  }

  async initialize() {
    try {
      await this.loadAcademicCalendars();
      this.startScheduledTaskProcessor();
      this.startAcademicPeriodUpdater();
      logger.info('Schedule manager initialized');
    } catch (error) {
      logger.error('Failed to initialize schedule manager:', error);
      throw error;
    }
  }

  async loadAcademicCalendars() {
    // This would typically load from a configuration file or database
    // For now, we'll use common US academic calendar patterns
    const currentYear = new Date().getFullYear();
    
    // Common academic periods (can be university-specific)
    this.academicCalendar.set('summer_break', {
      start: new Date(currentYear, 5, 1), // June 1st
      end: new Date(currentYear, 7, 31), // August 31st
      discount_multiplier: parseFloat(process.env.SUMMER_DISCOUNT) || 0.6
    });

    this.academicCalendar.set('winter_break', {
      start: new Date(currentYear, 11, 15), // December 15th
      end: new Date(currentYear + 1, 0, 15), // January 15th
      discount_multiplier: parseFloat(process.env.ACADEMIC_BREAK_DISCOUNT) || 0.5
    });

    this.academicCalendar.set('spring_break', {
      start: new Date(currentYear, 2, 15), // March 15th
      end: new Date(currentYear, 2, 25), // March 25th
      discount_multiplier: parseFloat(process.env.ACADEMIC_BREAK_DISCOUNT) || 0.5
    });

    logger.info(`Loaded ${this.academicCalendar.size} academic calendar periods`);
  }

  isAcademicBreakPeriod(date = new Date()) {
    const checkDate = moment(date);
    
    for (const [period, config] of this.academicCalendar) {
      const start = moment(config.start);
      const end = moment(config.end);
      
      if (checkDate.isBetween(start, end, null, '[]')) {
        return {
          is_break: true,
          period_name: period,
          discount_multiplier: config.discount_multiplier,
          period_start: config.start,
          period_end: config.end
        };
      }
    }
    
    return { is_break: false };
  }

  isWeekendOrOffHours(date = new Date(), timezone = 'America/New_York') {
    const localTime = moment(date).tz(timezone);
    const hour = localTime.hour();
    const dayOfWeek = localTime.day(); // 0 = Sunday, 6 = Saturday
    
    const peakStart = parseInt(process.env.PEAK_HOURS_START) || 8;
    const peakEnd = parseInt(process.env.PEAK_HOURS_END) || 18;
    
    const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
    const isOffHours = hour < peakStart || hour >= peakEnd;
    
    return {
      is_weekend: isWeekend,
      is_off_hours: isOffHours,
      is_weekend_or_off_hours: isWeekend || isOffHours,
      current_hour: hour,
      day_of_week: dayOfWeek,
      timezone: timezone
    };
  }

  async scheduleJob(jobId, scheduledStart, userPreferences = {}) {
    const db = getDb();
    
    try {
      // Get job details
      const job = await new Promise((resolve, reject) => {
        db.get('SELECT * FROM jobs WHERE id = ?', [jobId], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });

      if (!job) {
        throw new Error(`Job ${jobId} not found`);
      }

      const scheduledTime = moment(scheduledStart);
      const now = moment();

      // Validate scheduling constraints
      await this.validateSchedulingConstraints(job, scheduledTime, userPreferences);

      // Check if scheduling optimization is needed
      const optimizedTime = await this.optimizeScheduleTime(scheduledTime, job, userPreferences);

      // Update job with scheduled start time
      await new Promise((resolve, reject) => {
        db.run(
          'UPDATE jobs SET scheduled_start = ?, status = "scheduled" WHERE id = ?',
          [optimizedTime.toISOString(), jobId],
          (err) => {
            if (err) reject(err);
            else resolve();
          }
        );
      });

      // Add to scheduled tasks tracking
      this.scheduledTasks.set(jobId, {
        scheduled_time: optimizedTime.toDate(),
        original_time: scheduledTime.toDate(),
        job_id: jobId,
        user_preferences: userPreferences
      });

      logger.info(`Job ${jobId} scheduled for ${optimizedTime.format()}`);

      return {
        job_id: jobId,
        original_time: scheduledStart,
        optimized_time: optimizedTime.toISOString(),
        was_optimized: !optimizedTime.isSame(scheduledTime),
        scheduling_info: this.getSchedulingInfo(optimizedTime, userPreferences)
      };
    } catch (error) {
      logger.error(`Failed to schedule job ${jobId}:`, error);
      throw error;
    } finally {
      db.close();
    }
  }

  async validateSchedulingConstraints(job, scheduledTime, userPreferences) {
    const now = moment();
    
    // Can't schedule in the past
    if (scheduledTime.isBefore(now)) {
      throw new Error('Cannot schedule job in the past');
    }

    // Check if user allows weekend jobs
    if (!userPreferences.weekend_jobs) {
      const timeInfo = this.isWeekendOrOffHours(scheduledTime.toDate());
      if (timeInfo.is_weekend) {
        throw new Error('User preferences do not allow weekend job execution');
      }
    }

    // Check if user requires off-hours only
    if (userPreferences.off_hours_only) {
      const timeInfo = this.isWeekendOrOffHours(scheduledTime.toDate());
      if (!timeInfo.is_off_hours && !timeInfo.is_weekend) {
        throw new Error('User preferences require off-hours execution only');
      }
    }

    // Check maximum advance scheduling (e.g., 30 days)
    const maxAdvanceDays = 30;
    const maxScheduleTime = now.clone().add(maxAdvanceDays, 'days');
    if (scheduledTime.isAfter(maxScheduleTime)) {
      throw new Error(`Cannot schedule more than ${maxAdvanceDays} days in advance`);
    }
  }

  async optimizeScheduleTime(requestedTime, job, userPreferences) {
    const timezone = 'America/New_York'; // Should be configurable per university
    let optimizedTime = requestedTime.clone();

    // If user prefers cost optimization, suggest off-peak times
    if (userPreferences.cost_optimization) {
      optimizedTime = this.findNearestOffPeakTime(requestedTime, timezone);
    }

    // If during academic break, no further optimization needed (already discounted)
    const breakInfo = this.isAcademicBreakPeriod(optimizedTime.toDate());
    if (breakInfo.is_break) {
      return optimizedTime;
    }

    // Check for weekend discounts
    if (userPreferences.prefer_weekends) {
      const weekendTime = this.findNearestWeekend(requestedTime);
      if (weekendTime && weekendTime.diff(requestedTime, 'hours') <= 48) {
        optimizedTime = weekendTime;
      }
    }

    return optimizedTime;
  }

  findNearestOffPeakTime(requestedTime, timezone = 'America/New_York') {
    const localTime = requestedTime.tz(timezone);
    const hour = localTime.hour();
    
    const peakStart = parseInt(process.env.PEAK_HOURS_START) || 8;
    const peakEnd = parseInt(process.env.PEAK_HOURS_END) || 18;
    
    // If already off-peak, return as-is
    if (hour < peakStart || hour >= peakEnd) {
      return requestedTime;
    }
    
    // Find nearest off-peak time
    const endOfDay = localTime.clone().hour(peakEnd).minute(0).second(0);
    const startOfNextDay = localTime.clone().add(1, 'day').hour(0).minute(0).second(0);
    const nextMorning = localTime.clone().add(1, 'day').hour(peakStart - 1).minute(0).second(0);
    
    // Choose the nearest off-peak time
    const optionTimes = [endOfDay, startOfNextDay, nextMorning];
    const nearestTime = optionTimes.reduce((nearest, current) => {
      return Math.abs(current.diff(requestedTime)) < Math.abs(nearest.diff(requestedTime)) 
        ? current : nearest;
    });
    
    return nearestTime;
  }

  findNearestWeekend(requestedTime) {
    const current = requestedTime.clone();
    
    // Find next Saturday
    const daysUntilSaturday = (6 - current.day() + 7) % 7;
    const nextSaturday = current.clone().add(daysUntilSaturday, 'days').hour(8).minute(0).second(0);
    
    // Find next Sunday if closer
    const daysUntilSunday = (7 - current.day()) % 7;
    const nextSunday = current.clone().add(daysUntilSunday, 'days').hour(8).minute(0).second(0);
    
    // Return the closer weekend day, but only if within reasonable time
    const saturday = daysUntilSaturday === 0 ? null : nextSaturday;
    const sunday = daysUntilSunday === 0 ? null : nextSunday;
    
    if (!saturday && !sunday) return null;
    if (!saturday) return sunday;
    if (!sunday) return saturday;
    
    return saturday.isBefore(sunday) ? saturday : sunday;
  }

  getSchedulingInfo(scheduledTime, userPreferences) {
    const timeInfo = this.isWeekendOrOffHours(scheduledTime.toDate());
    const breakInfo = this.isAcademicBreakPeriod(scheduledTime.toDate());
    
    return {
      ...timeInfo,
      ...breakInfo,
      scheduling_benefits: this.getSchedulingBenefits(timeInfo, breakInfo),
      estimated_cost_multiplier: this.calculateTimeBasedMultiplier(timeInfo, breakInfo)
    };
  }

  getSchedulingBenefits(timeInfo, breakInfo) {
    const benefits = [];
    
    if (timeInfo.is_weekend) {
      benefits.push(`Weekend discount: ${((1 - parseFloat(process.env.WEEKEND_DISCOUNT || 0.7)) * 100).toFixed(0)}% off`);
    }
    
    if (timeInfo.is_off_hours && !timeInfo.is_weekend) {
      benefits.push(`Off-peak discount: ${((1 - parseFloat(process.env.OFF_PEAK_MULTIPLIER || 0.5)) * 100).toFixed(0)}% off`);
    }
    
    if (breakInfo.is_break) {
      benefits.push(`${breakInfo.period_name.replace('_', ' ')} discount: ${((1 - breakInfo.discount_multiplier) * 100).toFixed(0)}% off`);
    }
    
    return benefits;
  }

  calculateTimeBasedMultiplier(timeInfo, breakInfo) {
    let multiplier = 1.0;
    
    if (breakInfo.is_break) {
      multiplier *= breakInfo.discount_multiplier;
    } else if (timeInfo.is_weekend) {
      multiplier *= parseFloat(process.env.WEEKEND_DISCOUNT) || 0.7;
    } else if (timeInfo.is_off_hours) {
      multiplier *= parseFloat(process.env.OFF_PEAK_MULTIPLIER) || 0.5;
    } else {
      multiplier *= parseFloat(process.env.PEAK_MULTIPLIER) || 2.0;
    }
    
    return multiplier;
  }

  async getOptimalSchedulingWindows(durationMinutes = 60, maxDaysOut = 7) {
    const now = moment();
    const windows = [];
    
    for (let day = 0; day < maxDaysOut; day++) {
      const checkDate = now.clone().add(day, 'days');
      const timeInfo = this.isWeekendOrOffHours(checkDate.toDate());
      const breakInfo = this.isAcademicBreakPeriod(checkDate.toDate());
      
      // Calculate cost multiplier for this day
      const costMultiplier = this.calculateTimeBasedMultiplier(timeInfo, breakInfo);
      
      // Add time windows for this day
      if (timeInfo.is_weekend) {
        // Weekend: all day is discounted
        windows.push({
          start: checkDate.clone().hour(0).minute(0),
          end: checkDate.clone().hour(23).minute(59),
          cost_multiplier: costMultiplier,
          type: 'weekend',
          savings_percent: Math.round((1 - costMultiplier) * 100)
        });
      } else {
        // Weekday: off-peak hours are discounted
        const peakStart = parseInt(process.env.PEAK_HOURS_START) || 8;
        const peakEnd = parseInt(process.env.PEAK_HOURS_END) || 18;
        
        // Early morning window
        if (peakStart > 0) {
          windows.push({
            start: checkDate.clone().hour(0).minute(0),
            end: checkDate.clone().hour(peakStart - 1).minute(59),
            cost_multiplier: parseFloat(process.env.OFF_PEAK_MULTIPLIER) || 0.5,
            type: 'off_peak_morning',
            savings_percent: Math.round((1 - (parseFloat(process.env.OFF_PEAK_MULTIPLIER) || 0.5)) * 100)
          });
        }
        
        // Evening window
        windows.push({
          start: checkDate.clone().hour(peakEnd).minute(0),
          end: checkDate.clone().hour(23).minute(59),
          cost_multiplier: parseFloat(process.env.OFF_PEAK_MULTIPLIER) || 0.5,
          type: 'off_peak_evening',
          savings_percent: Math.round((1 - (parseFloat(process.env.OFF_PEAK_MULTIPLIER) || 0.5)) * 100)
        });
      }
    }
    
    // Sort by cost multiplier (best savings first)
    windows.sort((a, b) => a.cost_multiplier - b.cost_multiplier);
    
    return windows.map(window => ({
      ...window,
      start: window.start.toISOString(),
      end: window.end.toISOString(),
      duration_hours: moment(window.end).diff(window.start, 'hours')
    }));
  }

  startScheduledTaskProcessor() {
    // Check for scheduled jobs every minute
    cron.schedule('* * * * *', async () => {
      try {
        await this.processScheduledTasks();
      } catch (error) {
        logger.error('Scheduled task processing error:', error);
      }
    });
    
    logger.info('Scheduled task processor started');
  }

  startAcademicPeriodUpdater() {
    // Update academic calendar daily at midnight
    cron.schedule('0 0 * * *', async () => {
      try {
        await this.loadAcademicCalendars();
        logger.info('Academic calendar updated');
      } catch (error) {
        logger.error('Academic calendar update error:', error);
      }
    });
    
    logger.info('Academic period updater started');
  }

  async processScheduledTasks() {
    const now = new Date();
    const tasksToExecute = [];
    
    for (const [jobId, taskInfo] of this.scheduledTasks) {
      if (taskInfo.scheduled_time <= now) {
        tasksToExecute.push(jobId);
      }
    }
    
    for (const jobId of tasksToExecute) {
      try {
        await this.executeScheduledJob(jobId);
        this.scheduledTasks.delete(jobId);
      } catch (error) {
        logger.error(`Failed to execute scheduled job ${jobId}:`, error);
      }
    }
    
    if (tasksToExecute.length > 0) {
      logger.info(`Executed ${tasksToExecute.length} scheduled jobs`);
    }
  }

  async executeScheduledJob(jobId) {
    const db = getDb();
    
    try {
      // Update job status from scheduled to pending (ready for queue)
      await new Promise((resolve, reject) => {
        db.run(
          'UPDATE jobs SET status = "pending", updated_at = CURRENT_TIMESTAMP WHERE id = ? AND status = "scheduled"',
          [jobId],
          (err) => {
            if (err) reject(err);
            else resolve();
          }
        );
      });
      
      logger.info(`Scheduled job ${jobId} moved to pending queue`);
      
      // The job will now be picked up by the regular job queue processor
    } catch (error) {
      logger.error(`Failed to execute scheduled job ${jobId}:`, error);
      throw error;
    } finally {
      db.close();
    }
  }

  async rescheduleJob(jobId, newScheduledTime, userPreferences = {}) {
    // Remove from current scheduled tasks
    this.scheduledTasks.delete(jobId);
    
    // Schedule with new time
    return await this.scheduleJob(jobId, newScheduledTime, userPreferences);
  }

  async getJobSchedule(userId = null) {
    const db = getDb();
    
    try {
      const query = userId 
        ? 'SELECT * FROM jobs WHERE user_id = ? AND status = "scheduled" ORDER BY scheduled_start'
        : 'SELECT * FROM jobs WHERE status = "scheduled" ORDER BY scheduled_start';
      
      const params = userId ? [userId] : [];
      
      const scheduledJobs = await new Promise((resolve, reject) => {
        db.all(query, params, (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });
      
      return scheduledJobs.map(job => ({
        ...job,
        scheduling_info: this.getSchedulingInfo(moment(job.scheduled_start), {})
      }));
    } catch (error) {
      logger.error('Failed to get job schedule:', error);
      throw error;
    } finally {
      db.close();
    }
  }
}