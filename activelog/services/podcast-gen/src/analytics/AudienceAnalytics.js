import { EventEmitter } from 'events';
import fs from 'fs/promises';
import path from 'path';
import { v4 as uuidv4 } from 'uuid';

class AudienceAnalytics extends EventEmitter {
    constructor(config = {}) {
        super();
        this.config = {
            analytics_directory: config.analytics_directory || './data/analytics',
            reports_directory: config.reports_directory || './output/analytics_reports',
            retention_period: config.retention_period || 365, // days
            sampling_rate: config.sampling_rate || 1.0, // 100% by default
            ...config
        };

        this.listeners = new Map();
        this.episodes = new Map();
        this.sessions = new Map();
        this.events = new Map();
        this.cohorts = new Map();
        this.funnels = new Map();

        this.ensureDirectories();
        this.initializeMetricDefinitions();
    }

    async ensureDirectories() {
        try {
            await fs.mkdir(this.config.analytics_directory, { recursive: true });
            await fs.mkdir(this.config.reports_directory, { recursive: true });
            await fs.mkdir(path.join(this.config.analytics_directory, 'events'), { recursive: true });
            await fs.mkdir(path.join(this.config.analytics_directory, 'sessions'), { recursive: true });
            await fs.mkdir(path.join(this.config.analytics_directory, 'listeners'), { recursive: true });
        } catch (error) {
            this.emit('error', { type: 'directory-creation', error });
        }
    }

    initializeMetricDefinitions() {
        this.metricDefinitions = {
            // Engagement Metrics
            completion_rate: {
                name: 'Completion Rate',
                description: 'Percentage of episode completed by listeners',
                calculation: 'completed_duration / total_duration',
                unit: 'percentage',
                benchmark: { good: 70, excellent: 85 }
            },
            
            retention_rate: {
                name: 'Retention Rate',
                description: 'Percentage of listeners who return for subsequent episodes',
                calculation: 'returning_listeners / total_listeners',
                unit: 'percentage',
                benchmark: { good: 30, excellent: 50 }
            },
            
            average_listen_duration: {
                name: 'Average Listen Duration',
                description: 'Average time spent listening per session',
                calculation: 'total_listen_time / total_sessions',
                unit: 'minutes',
                benchmark: { good: 15, excellent: 25 }
            },

            // Acquisition Metrics
            new_listener_rate: {
                name: 'New Listener Rate',
                description: 'Percentage of listeners who are new to the podcast',
                calculation: 'new_listeners / total_listeners',
                unit: 'percentage',
                benchmark: { good: 15, excellent: 25 }
            },

            // Behavioral Metrics
            skip_rate: {
                name: 'Skip Rate',
                description: 'Percentage of content that gets skipped',
                calculation: 'skipped_duration / total_duration',
                unit: 'percentage',
                benchmark: { good: 10, excellent: 5 }
            },

            replay_rate: {
                name: 'Replay Rate',
                description: 'Percentage of content that gets replayed',
                calculation: 'replayed_segments / total_segments',
                unit: 'percentage',
                benchmark: { good: 5, excellent: 10 }
            }
        };
    }

    async trackListenerEvent(eventData) {
        const eventId = uuidv4();
        
        try {
            // Check sampling rate
            if (Math.random() > this.config.sampling_rate) {
                return null; // Skip this event based on sampling
            }

            const event = {
                id: eventId,
                listener_id: eventData.listener_id || this.generateAnonymousId(),
                session_id: eventData.session_id,
                episode_id: eventData.episode_id,
                event_type: eventData.event_type,
                timestamp: eventData.timestamp || new Date().toISOString(),
                properties: eventData.properties || {},
                context: {
                    user_agent: eventData.user_agent,
                    platform: eventData.platform,
                    location: eventData.location,
                    referrer: eventData.referrer
                }
            };

            // Store event
            this.events.set(eventId, event);
            
            // Update listener profile
            await this.updateListenerProfile(event);
            
            // Update session data
            await this.updateSession(event);
            
            // Process real-time metrics
            await this.processRealTimeMetrics(event);

            this.emit('event-tracked', { eventId, eventType: event.event_type });

            return event;

        } catch (error) {
            this.emit('event-tracking-failed', { eventId, error });
            throw error;
        }
    }

    generateAnonymousId() {
        return `anon_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    async updateListenerProfile(event) {
        const listenerId = event.listener_id;
        let listener = this.listeners.get(listenerId);

        if (!listener) {
            // Create new listener profile
            listener = {
                id: listenerId,
                first_seen: event.timestamp,
                last_seen: event.timestamp,
                total_sessions: 0,
                total_listen_time: 0,
                episodes_consumed: new Set(),
                platforms_used: new Set(),
                behavioral_patterns: {
                    preferred_listen_times: [],
                    average_session_duration: 0,
                    completion_rates: [],
                    skip_patterns: [],
                    replay_patterns: []
                },
                demographics: {
                    location: event.context?.location,
                    platform_preference: event.context?.platform
                },
                engagement_score: 0,
                lifecycle_stage: 'new'
            };
        }

        // Update listener data based on event
        listener.last_seen = event.timestamp;
        
        if (event.context?.platform) {
            listener.platforms_used.add(event.context.platform);
        }

        if (event.episode_id) {
            listener.episodes_consumed.add(event.episode_id);
        }

        // Update behavioral patterns
        await this.updateBehavioralPatterns(listener, event);

        // Calculate engagement score
        listener.engagement_score = this.calculateEngagementScore(listener);

        // Determine lifecycle stage
        listener.lifecycle_stage = this.determineLifecycleStage(listener);

        this.listeners.set(listenerId, listener);

        // Persist listener profile
        await this.persistListenerProfile(listener);
    }

    async updateBehavioralPatterns(listener, event) {
        const eventTime = new Date(event.timestamp);
        const hourOfDay = eventTime.getHours();
        
        // Track preferred listen times
        listener.behavioral_patterns.preferred_listen_times.push(hourOfDay);
        
        // Keep only recent patterns (last 100 events)
        if (listener.behavioral_patterns.preferred_listen_times.length > 100) {
            listener.behavioral_patterns.preferred_listen_times = 
                listener.behavioral_patterns.preferred_listen_times.slice(-100);
        }

        // Update patterns based on event type
        switch (event.event_type) {
            case 'play':
                // Track play behavior
                break;
            case 'pause':
                // Track pause patterns
                break;
            case 'skip':
                listener.behavioral_patterns.skip_patterns.push({
                    episode_id: event.episode_id,
                    timestamp: event.properties?.timestamp,
                    reason: event.properties?.reason
                });
                break;
            case 'replay':
                listener.behavioral_patterns.replay_patterns.push({
                    episode_id: event.episode_id,
                    segment: event.properties?.segment,
                    timestamp: event.properties?.timestamp
                });
                break;
            case 'complete':
                const completionRate = event.properties?.completion_percentage || 100;
                listener.behavioral_patterns.completion_rates.push(completionRate);
                break;
        }
    }

    calculateEngagementScore(listener) {
        let score = 0;
        
        // Episode consumption factor (0-40 points)
        const episodeCount = listener.episodes_consumed.size;
        score += Math.min(40, episodeCount * 2);
        
        // Average completion rate (0-30 points)
        const completionRates = listener.behavioral_patterns.completion_rates;
        if (completionRates.length > 0) {
            const avgCompletion = completionRates.reduce((sum, rate) => sum + rate, 0) / completionRates.length;
            score += (avgCompletion / 100) * 30;
        }
        
        // Recency factor (0-20 points)
        const daysSinceLastSeen = (Date.now() - new Date(listener.last_seen)) / (1000 * 60 * 60 * 24);
        if (daysSinceLastSeen < 1) score += 20;
        else if (daysSinceLastSeen < 7) score += 15;
        else if (daysSinceLastSeen < 30) score += 10;
        else if (daysSinceLastSeen < 90) score += 5;
        
        // Replay behavior bonus (0-10 points)
        const replayCount = listener.behavioral_patterns.replay_patterns.length;
        score += Math.min(10, replayCount);
        
        return Math.min(100, Math.round(score));
    }

    determineLifecycleStage(listener) {
        const episodeCount = listener.episodes_consumed.size;
        const daysSinceFirstSeen = (Date.now() - new Date(listener.first_seen)) / (1000 * 60 * 60 * 24);
        const daysSinceLastSeen = (Date.now() - new Date(listener.last_seen)) / (1000 * 60 * 60 * 24);
        
        if (episodeCount === 1 && daysSinceFirstSeen < 7) {
            return 'new';
        } else if (episodeCount >= 2 && episodeCount < 5) {
            return 'exploring';
        } else if (episodeCount >= 5 && daysSinceLastSeen < 30) {
            return 'engaged';
        } else if (episodeCount >= 10 && daysSinceLastSeen < 7) {
            return 'loyal';
        } else if (daysSinceLastSeen > 90) {
            return 'churned';
        } else if (daysSinceLastSeen > 30) {
            return 'at_risk';
        } else {
            return 'active';
        }
    }

    async updateSession(event) {
        const sessionId = event.session_id;
        let session = this.sessions.get(sessionId);

        if (!session) {
            session = {
                id: sessionId,
                listener_id: event.listener_id,
                start_time: event.timestamp,
                end_time: event.timestamp,
                episode_id: event.episode_id,
                platform: event.context?.platform,
                events: [],
                duration: 0,
                engagement_metrics: {
                    play_count: 0,
                    pause_count: 0,
                    skip_count: 0,
                    replay_count: 0,
                    completion_percentage: 0
                }
            };
        }

        // Update session
        session.end_time = event.timestamp;
        session.events.push(event.id);
        session.duration = (new Date(session.end_time) - new Date(session.start_time)) / 1000; // seconds

        // Update engagement metrics
        switch (event.event_type) {
            case 'play':
                session.engagement_metrics.play_count++;
                break;
            case 'pause':
                session.engagement_metrics.pause_count++;
                break;
            case 'skip':
                session.engagement_metrics.skip_count++;
                break;
            case 'replay':
                session.engagement_metrics.replay_count++;
                break;
            case 'complete':
                session.engagement_metrics.completion_percentage = event.properties?.completion_percentage || 100;
                break;
        }

        this.sessions.set(sessionId, session);
    }

    async processRealTimeMetrics(event) {
        // Update real-time counters and aggregations
        const episodeId = event.episode_id;
        
        if (episodeId) {
            let episode = this.episodes.get(episodeId);
            
            if (!episode) {
                episode = {
                    id: episodeId,
                    total_plays: 0,
                    unique_listeners: new Set(),
                    total_duration_listened: 0,
                    skip_events: 0,
                    completion_events: 0,
                    replay_events: 0,
                    first_listen: event.timestamp,
                    last_listen: event.timestamp
                };
            }

            episode.last_listen = event.timestamp;
            episode.unique_listeners.add(event.listener_id);

            switch (event.event_type) {
                case 'play':
                    episode.total_plays++;
                    break;
                case 'skip':
                    episode.skip_events++;
                    break;
                case 'complete':
                    episode.completion_events++;
                    break;
                case 'replay':
                    episode.replay_events++;
                    break;
            }

            this.episodes.set(episodeId, episode);
        }
    }

    async generateAudienceReport(reportRequest) {
        const reportId = uuidv4();
        
        try {
            this.emit('report-generation-started', { reportId });

            const {
                time_period,
                metrics_requested,
                segments,
                comparison_period
            } = reportRequest;

            const report = {
                id: reportId,
                generated_at: new Date().toISOString(),
                time_period: time_period,
                summary: await this.generateReportSummary(time_period),
                audience_overview: await this.generateAudienceOverview(time_period),
                engagement_metrics: await this.generateEngagementMetrics(time_period, metrics_requested),
                listener_segments: await this.generateListenerSegments(segments),
                behavioral_insights: await this.generateBehavioralInsights(time_period),
                platform_analysis: await this.generatePlatformAnalysis(time_period),
                content_performance: await this.generateContentPerformance(time_period),
                retention_analysis: await this.generateRetentionAnalysis(time_period),
                recommendations: await this.generateRecommendations(time_period)
            };

            // Add comparison data if requested
            if (comparison_period) {
                report.comparison = await this.generateComparison(time_period, comparison_period);
            }

            // Save report
            const reportPath = path.join(
                this.config.reports_directory,
                `audience_report_${reportId}_${Date.now()}.json`
            );
            await fs.writeFile(reportPath, JSON.stringify(report, null, 2), 'utf8');

            this.emit('report-generated', {
                reportId,
                reportPath,
                totalListeners: report.summary.total_unique_listeners
            });

            return {
                report_id: reportId,
                report: report,
                report_path: reportPath
            };

        } catch (error) {
            this.emit('report-generation-failed', { reportId, error });
            throw error;
        }
    }

    async generateReportSummary(timePeriod) {
        const listeners = Array.from(this.listeners.values());
        const sessions = Array.from(this.sessions.values());
        const episodes = Array.from(this.episodes.values());

        return {
            total_unique_listeners: listeners.length,
            total_sessions: sessions.length,
            total_episodes_tracked: episodes.length,
            total_listen_time: sessions.reduce((sum, s) => sum + s.duration, 0),
            average_session_duration: sessions.length > 0 ? 
                sessions.reduce((sum, s) => sum + s.duration, 0) / sessions.length : 0,
            new_listeners_count: listeners.filter(l => l.lifecycle_stage === 'new').length,
            returning_listeners_count: listeners.filter(l => l.lifecycle_stage !== 'new').length
        };
    }

    async generateAudienceOverview(timePeriod) {
        const listeners = Array.from(this.listeners.values());
        
        // Lifecycle distribution
        const lifecycleDistribution = {};
        listeners.forEach(listener => {
            const stage = listener.lifecycle_stage;
            lifecycleDistribution[stage] = (lifecycleDistribution[stage] || 0) + 1;
        });

        // Engagement score distribution
        const engagementBuckets = { low: 0, medium: 0, high: 0 };
        listeners.forEach(listener => {
            if (listener.engagement_score < 30) engagementBuckets.low++;
            else if (listener.engagement_score < 70) engagementBuckets.medium++;
            else engagementBuckets.high++;
        });

        // Platform distribution
        const platformDistribution = {};
        listeners.forEach(listener => {
            listener.platforms_used.forEach(platform => {
                platformDistribution[platform] = (platformDistribution[platform] || 0) + 1;
            });
        });

        return {
            lifecycle_distribution: lifecycleDistribution,
            engagement_distribution: engagementBuckets,
            platform_distribution: platformDistribution,
            average_engagement_score: listeners.length > 0 ? 
                listeners.reduce((sum, l) => sum + l.engagement_score, 0) / listeners.length : 0
        };
    }

    async generateEngagementMetrics(timePeriod, metricsRequested) {
        const sessions = Array.from(this.sessions.values());
        const listeners = Array.from(this.listeners.values());
        
        const metrics = {};

        if (!metricsRequested || metricsRequested.includes('completion_rate')) {
            const completionRates = listeners
                .flatMap(l => l.behavioral_patterns.completion_rates)
                .filter(rate => rate > 0);
            
            metrics.completion_rate = {
                average: completionRates.length > 0 ? 
                    completionRates.reduce((sum, rate) => sum + rate, 0) / completionRates.length : 0,
                median: this.calculateMedian(completionRates),
                distribution: this.createDistribution(completionRates, [0, 25, 50, 75, 100])
            };
        }

        if (!metricsRequested || metricsRequested.includes('retention_rate')) {
            const returningListeners = listeners.filter(l => 
                l.lifecycle_stage !== 'new' && l.episodes_consumed.size > 1
            ).length;
            
            metrics.retention_rate = {
                value: listeners.length > 0 ? (returningListeners / listeners.length) * 100 : 0,
                cohort_analysis: await this.calculateCohortRetention()
            };
        }

        if (!metricsRequested || metricsRequested.includes('average_listen_duration')) {
            metrics.average_listen_duration = {
                overall: sessions.length > 0 ? 
                    sessions.reduce((sum, s) => sum + s.duration, 0) / sessions.length : 0,
                by_episode: this.calculateAverageByEpisode(sessions),
                trend: await this.calculateListenDurationTrend()
            };
        }

        return metrics;
    }

    async generateListenerSegments(segmentConfigs) {
        const listeners = Array.from(this.listeners.values());
        const segments = {};

        // Default segments
        segments.by_engagement = {
            high_engagement: listeners.filter(l => l.engagement_score >= 70),
            medium_engagement: listeners.filter(l => l.engagement_score >= 30 && l.engagement_score < 70),
            low_engagement: listeners.filter(l => l.engagement_score < 30)
        };

        segments.by_lifecycle = {};
        listeners.forEach(listener => {
            const stage = listener.lifecycle_stage;
            if (!segments.by_lifecycle[stage]) {
                segments.by_lifecycle[stage] = [];
            }
            segments.by_lifecycle[stage].push(listener);
        });

        segments.by_consumption = {
            power_listeners: listeners.filter(l => l.episodes_consumed.size >= 10),
            regular_listeners: listeners.filter(l => l.episodes_consumed.size >= 3 && l.episodes_consumed.size < 10),
            casual_listeners: listeners.filter(l => l.episodes_consumed.size < 3)
        };

        return segments;
    }

    async generateBehavioralInsights(timePeriod) {
        const listeners = Array.from(this.listeners.values());
        const sessions = Array.from(this.sessions.values());

        // Listening time patterns
        const listeningTimes = listeners
            .flatMap(l => l.behavioral_patterns.preferred_listen_times)
            .reduce((acc, hour) => {
                acc[hour] = (acc[hour] || 0) + 1;
                return acc;
            }, {});

        // Skip patterns analysis
        const skipPatterns = listeners
            .flatMap(l => l.behavioral_patterns.skip_patterns)
            .reduce((acc, skip) => {
                if (skip.reason) {
                    acc[skip.reason] = (acc[skip.reason] || 0) + 1;
                }
                return acc;
            }, {});

        // Replay patterns analysis
        const replayPatterns = listeners
            .flatMap(l => l.behavioral_patterns.replay_patterns)
            .reduce((acc, replay) => {
                if (replay.segment) {
                    acc[replay.segment] = (acc[replay.segment] || 0) + 1;
                }
                return acc;
            }, {});

        return {
            peak_listening_hours: Object.entries(listeningTimes)
                .sort(([,a], [,b]) => b - a)
                .slice(0, 5)
                .map(([hour, count]) => ({ hour: parseInt(hour), listeners: count })),
            common_skip_reasons: Object.entries(skipPatterns)
                .sort(([,a], [,b]) => b - a)
                .slice(0, 5),
            most_replayed_segments: Object.entries(replayPatterns)
                .sort(([,a], [,b]) => b - a)
                .slice(0, 5),
            session_patterns: {
                average_session_duration: sessions.reduce((sum, s) => sum + s.duration, 0) / sessions.length,
                sessions_with_skips: sessions.filter(s => s.engagement_metrics.skip_count > 0).length,
                sessions_with_replays: sessions.filter(s => s.engagement_metrics.replay_count > 0).length
            }
        };
    }

    async generatePlatformAnalysis(timePeriod) {
        const listeners = Array.from(this.listeners.values());
        const sessions = Array.from(this.sessions.values());

        const platformData = {};
        
        // Analyze each platform
        const allPlatforms = new Set();
        listeners.forEach(l => l.platforms_used.forEach(p => allPlatforms.add(p)));

        allPlatforms.forEach(platform => {
            const platformListeners = listeners.filter(l => l.platforms_used.has(platform));
            const platformSessions = sessions.filter(s => s.platform === platform);

            platformData[platform] = {
                unique_listeners: platformListeners.length,
                total_sessions: platformSessions.length,
                average_session_duration: platformSessions.length > 0 ?
                    platformSessions.reduce((sum, s) => sum + s.duration, 0) / platformSessions.length : 0,
                average_engagement_score: platformListeners.length > 0 ?
                    platformListeners.reduce((sum, l) => sum + l.engagement_score, 0) / platformListeners.length : 0,
                completion_rate: this.calculatePlatformCompletionRate(platformListeners)
            };
        });

        return {
            platform_breakdown: platformData,
            top_platforms: Object.entries(platformData)
                .sort(([,a], [,b]) => b.unique_listeners - a.unique_listeners)
                .slice(0, 5)
        };
    }

    async generateContentPerformance(timePeriod) {
        const episodes = Array.from(this.episodes.values());
        
        return episodes.map(episode => ({
            episode_id: episode.id,
            unique_listeners: episode.unique_listeners.size,
            total_plays: episode.total_plays,
            completion_rate: episode.completion_events / Math.max(1, episode.total_plays) * 100,
            skip_rate: episode.skip_events / Math.max(1, episode.total_plays) * 100,
            replay_rate: episode.replay_events / Math.max(1, episode.total_plays) * 100,
            engagement_score: this.calculateEpisodeEngagementScore(episode)
        })).sort((a, b) => b.engagement_score - a.engagement_score);
    }

    async generateRetentionAnalysis(timePeriod) {
        const listeners = Array.from(this.listeners.values());
        
        // Calculate retention by time periods
        const retentionData = {
            day_1: 0,
            day_7: 0,
            day_30: 0,
            day_90: 0
        };

        const now = new Date();
        listeners.forEach(listener => {
            const daysSinceFirst = (now - new Date(listener.first_seen)) / (1000 * 60 * 60 * 24);
            const daysSinceLast = (now - new Date(listener.last_seen)) / (1000 * 60 * 60 * 24);
            
            if (daysSinceFirst >= 1 && daysSinceLast <= 1) retentionData.day_1++;
            if (daysSinceFirst >= 7 && daysSinceLast <= 7) retentionData.day_7++;
            if (daysSinceFirst >= 30 && daysSinceLast <= 30) retentionData.day_30++;
            if (daysSinceFirst >= 90 && daysSinceLast <= 90) retentionData.day_90++;
        });

        return {
            retention_rates: retentionData,
            churn_analysis: {
                churned_listeners: listeners.filter(l => l.lifecycle_stage === 'churned').length,
                at_risk_listeners: listeners.filter(l => l.lifecycle_stage === 'at_risk').length
            },
            cohort_retention: await this.calculateCohortRetention()
        };
    }

    async calculateCohortRetention() {
        // Simplified cohort analysis
        const listeners = Array.from(this.listeners.values());
        const cohorts = {};
        
        listeners.forEach(listener => {
            const cohortMonth = new Date(listener.first_seen).toISOString().substring(0, 7);
            if (!cohorts[cohortMonth]) {
                cohorts[cohortMonth] = {
                    total: 0,
                    retained_week_1: 0,
                    retained_week_4: 0,
                    retained_week_12: 0
                };
            }
            
            cohorts[cohortMonth].total++;
            
            const weeksSinceFirst = (Date.now() - new Date(listener.first_seen)) / (1000 * 60 * 60 * 24 * 7);
            const weeksSinceLast = (Date.now() - new Date(listener.last_seen)) / (1000 * 60 * 60 * 24 * 7);
            
            if (weeksSinceFirst >= 1 && weeksSinceLast <= 1) cohorts[cohortMonth].retained_week_1++;
            if (weeksSinceFirst >= 4 && weeksSinceLast <= 4) cohorts[cohortMonth].retained_week_4++;
            if (weeksSinceFirst >= 12 && weeksSinceLast <= 12) cohorts[cohortMonth].retained_week_12++;
        });

        return cohorts;
    }

    async generateRecommendations(timePeriod) {
        const recommendations = [];
        const listeners = Array.from(this.listeners.values());
        const episodes = Array.from(this.episodes.values());
        
        // Engagement recommendations
        const avgEngagement = listeners.reduce((sum, l) => sum + l.engagement_score, 0) / listeners.length;
        if (avgEngagement < 50) {
            recommendations.push({
                category: 'engagement',
                priority: 'high',
                title: 'Improve Overall Engagement',
                description: 'Average engagement score is below 50. Consider improving content quality and listener interaction.',
                suggested_actions: [
                    'Analyze high-performing episodes for successful elements',
                    'Increase audience interaction through Q&A segments',
                    'Optimize episode length based on completion rates'
                ]
            });
        }

        // Retention recommendations
        const churnedListeners = listeners.filter(l => l.lifecycle_stage === 'churned').length;
        if (churnedListeners / listeners.length > 0.3) {
            recommendations.push({
                category: 'retention',
                priority: 'high',
                title: 'Address High Churn Rate',
                description: 'More than 30% of listeners have churned. Focus on retention strategies.',
                suggested_actions: [
                    'Create re-engagement campaigns for inactive listeners',
                    'Improve onboarding experience for new listeners',
                    'Develop series or recurring segments to build habit'
                ]
            });
        }

        // Content recommendations
        const lowPerformingEpisodes = episodes.filter(e => 
            e.completion_events / Math.max(1, e.total_plays) < 0.3
        );
        if (lowPerformingEpisodes.length > episodes.length * 0.2) {
            recommendations.push({
                category: 'content',
                priority: 'medium',
                title: 'Improve Content Performance',
                description: 'Several episodes have low completion rates. Review content strategy.',
                suggested_actions: [
                    'Analyze successful episodes for format and topic patterns',
                    'Consider shorter episode formats for better completion',
                    'Improve episode introductions to hook listeners'
                ]
            });
        }

        return recommendations;
    }

    calculateMedian(values) {
        if (values.length === 0) return 0;
        const sorted = [...values].sort((a, b) => a - b);
        const middle = Math.floor(sorted.length / 2);
        return sorted.length % 2 === 0 ? 
            (sorted[middle - 1] + sorted[middle]) / 2 : 
            sorted[middle];
    }

    createDistribution(values, buckets) {
        const distribution = {};
        buckets.forEach((bucket, i) => {
            const nextBucket = buckets[i + 1] || Infinity;
            const count = values.filter(v => v >= bucket && v < nextBucket).length;
            distribution[`${bucket}-${nextBucket === Infinity ? '100+' : nextBucket}`] = count;
        });
        return distribution;
    }

    calculateAverageByEpisode(sessions) {
        const episodeDurations = {};
        sessions.forEach(session => {
            if (!episodeDurations[session.episode_id]) {
                episodeDurations[session.episode_id] = [];
            }
            episodeDurations[session.episode_id].push(session.duration);
        });

        const averages = {};
        Object.entries(episodeDurations).forEach(([episodeId, durations]) => {
            averages[episodeId] = durations.reduce((sum, d) => sum + d, 0) / durations.length;
        });

        return averages;
    }

    async calculateListenDurationTrend() {
        // Calculate trend over time - simplified implementation
        const sessions = Array.from(this.sessions.values())
            .sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
        
        const weeklyAverages = {};
        sessions.forEach(session => {
            const week = new Date(session.start_time).toISOString().substring(0, 10);
            if (!weeklyAverages[week]) {
                weeklyAverages[week] = { total: 0, count: 0 };
            }
            weeklyAverages[week].total += session.duration;
            weeklyAverages[week].count++;
        });

        return Object.entries(weeklyAverages).map(([week, data]) => ({
            week,
            average_duration: data.total / data.count
        }));
    }

    calculatePlatformCompletionRate(platformListeners) {
        const completionRates = platformListeners
            .flatMap(l => l.behavioral_patterns.completion_rates)
            .filter(rate => rate > 0);
        
        return completionRates.length > 0 ? 
            completionRates.reduce((sum, rate) => sum + rate, 0) / completionRates.length : 0;
    }

    calculateEpisodeEngagementScore(episode) {
        const completionRate = episode.completion_events / Math.max(1, episode.total_plays);
        const skipRate = episode.skip_events / Math.max(1, episode.total_plays);
        const replayRate = episode.replay_events / Math.max(1, episode.total_plays);
        
        // Weighted engagement score
        return Math.round(
            (completionRate * 50) + 
            ((1 - skipRate) * 30) + 
            (replayRate * 20)
        );
    }

    async persistListenerProfile(listener) {
        try {
            const profilePath = path.join(
                this.config.analytics_directory,
                'listeners',
                `${listener.id}.json`
            );
            
            // Convert Set to Array for JSON serialization
            const serializableListener = {
                ...listener,
                episodes_consumed: Array.from(listener.episodes_consumed),
                platforms_used: Array.from(listener.platforms_used)
            };
            
            await fs.writeFile(profilePath, JSON.stringify(serializableListener, null, 2), 'utf8');
        } catch (error) {
            this.emit('profile-persistence-failed', { listenerId: listener.id, error });
        }
    }

    async loadListenerProfiles() {
        try {
            const profilesDir = path.join(this.config.analytics_directory, 'listeners');
            const files = await fs.readdir(profilesDir);
            
            for (const file of files) {
                if (file.endsWith('.json')) {
                    const profilePath = path.join(profilesDir, file);
                    const profileData = JSON.parse(await fs.readFile(profilePath, 'utf8'));
                    
                    // Convert Arrays back to Sets
                    profileData.episodes_consumed = new Set(profileData.episodes_consumed);
                    profileData.platforms_used = new Set(profileData.platforms_used);
                    
                    this.listeners.set(profileData.id, profileData);
                }
            }
            
            this.emit('listener-profiles-loaded', { count: this.listeners.size });
        } catch (error) {
            this.emit('profile-loading-failed', { error });
        }
    }

    getMetricDefinitions() {
        return this.metricDefinitions;
    }

    getListenerProfile(listenerId) {
        return this.listeners.get(listenerId);
    }

    getEpisodeMetrics(episodeId) {
        return this.episodes.get(episodeId);
    }

    async exportAnalyticsData(format = 'json', timeRange = null) {
        const exportId = uuidv4();
        
        try {
            const data = {
                export_id: exportId,
                exported_at: new Date().toISOString(),
                time_range: timeRange,
                listeners: Array.from(this.listeners.values()).map(l => ({
                    ...l,
                    episodes_consumed: Array.from(l.episodes_consumed),
                    platforms_used: Array.from(l.platforms_used)
                })),
                episodes: Array.from(this.episodes.values()).map(e => ({
                    ...e,
                    unique_listeners: Array.from(e.unique_listeners)
                })),
                sessions: Array.from(this.sessions.values())
            };

            const exportPath = path.join(
                this.config.reports_directory,
                `analytics_export_${exportId}.${format}`
            );

            if (format === 'json') {
                await fs.writeFile(exportPath, JSON.stringify(data, null, 2), 'utf8');
            } else if (format === 'csv') {
                // Convert to CSV format - simplified implementation
                const csv = this.convertToCSV(data);
                await fs.writeFile(exportPath, csv, 'utf8');
            }

            return {
                export_id: exportId,
                file_path: exportPath,
                format: format,
                record_count: data.listeners.length + data.episodes.length + data.sessions.length
            };

        } catch (error) {
            this.emit('export-failed', { exportId, error });
            throw error;
        }
    }

    convertToCSV(data) {
        // Simplified CSV conversion for listeners
        const headers = ['id', 'first_seen', 'last_seen', 'total_sessions', 'episodes_count', 'engagement_score', 'lifecycle_stage'];
        const rows = [headers.join(',')];
        
        data.listeners.forEach(listener => {
            const row = [
                listener.id,
                listener.first_seen,
                listener.last_seen,
                listener.total_sessions,
                listener.episodes_consumed.length,
                listener.engagement_score,
                listener.lifecycle_stage
            ];
            rows.push(row.join(','));
        });
        
        return rows.join('\n');
    }
}

export default AudienceAnalytics;