import { v4 as uuidv4 } from 'uuid';
import moment from 'moment';
import cron from 'node-cron';

export class ComplianceReportingService {
    constructor(redis, logger) {
        this.redis = redis;
        this.logger = logger;
        this.broadcast = null;
        
        this.complianceFrameworks = {
            'sox': { name: 'Sarbanes-Oxley Act', required: ['financial_controls', 'audit_logs'] },
            'gdpr': { name: 'GDPR', required: ['data_protection', 'privacy_controls'] },
            'hipaa': { name: 'HIPAA', required: ['healthcare_privacy', 'security_controls'] },
            'pci_dss': { name: 'PCI DSS', required: ['payment_security', 'data_encryption'] },
            'iso27001': { name: 'ISO 27001', required: ['security_management', 'risk_assessment'] }
        };
    }

    async generateComplianceReport(orgId, framework, period) {
        try {
            const reportId = uuidv4();
            const report = {
                id: reportId,
                orgId,
                framework,
                period,
                compliance_status: await this.assessCompliance(orgId, framework),
                generated_at: Date.now(),
                status: 'completed'
            };
            
            await this.redis.hset(`compliance_report:${reportId}`, report);
            return report;
        } catch (error) {
            this.logger.error('Error generating compliance report:', error);
            throw error;
        }
    }

    async assessCompliance(orgId, framework) {
        // Mock compliance assessment
        return {
            overall_score: Math.floor(Math.random() * 20) + 80, // 80-100
            requirements_met: Math.floor(Math.random() * 5) + 15, // 15-20
            total_requirements: 20,
            last_assessment: Date.now()
        };
    }

    async scheduleAutomaticReports(orgId, frameworks, frequency) {
        const scheduleId = uuidv4();
        const schedule = {
            id: scheduleId,
            orgId,
            frameworks: JSON.stringify(frameworks),
            frequency, // 'monthly', 'quarterly', 'annual'
            next_run: this.calculateNextRun(frequency),
            active: true,
            created_at: Date.now()
        };
        
        await this.redis.hset(`compliance_schedule:${scheduleId}`, schedule);
        return schedule;
    }

    calculateNextRun(frequency) {
        const now = moment();
        switch (frequency) {
            case 'monthly': return now.add(1, 'month').valueOf();
            case 'quarterly': return now.add(3, 'months').valueOf();
            case 'annual': return now.add(1, 'year').valueOf();
            default: return now.add(1, 'month').valueOf();
        }
    }

    async getStats() {
        const reportKeys = await this.redis.keys('compliance_report:*');
        const scheduleKeys = await this.redis.keys('compliance_schedule:*');
        
        return {
            totalReports: reportKeys.length,
            activeSchedules: scheduleKeys.length,
            frameworkSupport: Object.keys(this.complianceFrameworks)
        };
    }

    startScheduler() {
        cron.schedule('0 2 * * *', async () => {
            await this.processScheduledReports();
        });
    }

    async processScheduledReports() {
        const schedules = await this.redis.keys('compliance_schedule:*');
        const now = Date.now();
        
        for (const key of schedules) {
            const schedule = await this.redis.hgetall(key);
            if (schedule.active === 'true' && parseInt(schedule.next_run) <= now) {
                const frameworks = JSON.parse(schedule.frameworks);
                for (const framework of frameworks) {
                    await this.generateComplianceReport(schedule.orgId, framework, moment().format('YYYY-MM'));
                }
            }
        }
    }

    stopScheduler() {
        this.logger.info('Compliance reporting scheduler stopped');
    }
}