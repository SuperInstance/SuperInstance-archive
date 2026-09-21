import { EventEmitter } from 'events';
import crypto from 'crypto';

class PatentProtectionSystem extends EventEmitter {
    constructor() {
        super();
        this.applications = new Map();
        this.priorArt = new Map();
        this.patentDatabase = new Map();
        this.searches = new Map();
        this.attorneys = new Map();
        this.filings = new Map();
        this.monitoring = new Map();
        this.disputes = new Map();
        this.licensing = new Map();
        
        this.initializeData();
    }

    initializeData() {
        // Initialize sample patent attorneys and services
        const sampleAttorneys = [
            {
                id: 'attorney_001',
                name: 'Sarah Johnson',
                firm: 'Innovation IP Partners',
                specializations: ['Electronics', 'IoT Devices', 'Hardware Systems'],
                experience_years: 12,
                success_rate: 94.2,
                average_cost: {
                    provisional: '$1,200',
                    utility: '$3,500',
                    international: '$8,900'
                },
                contact: {
                    phone: '+1-555-0123',
                    email: 'sarah.johnson@innovationip.com'
                },
                ratings: {
                    average: 4.8,
                    reviews: 67
                },
                languages: ['English', 'Spanish'],
                bar_admissions: ['USPTO', 'California State Bar'],
                certifications: ['Patent Bar Certified', 'Trademark Specialist']
            },
            {
                id: 'attorney_002',
                name: 'Dr. Michael Chen',
                firm: 'TechPatent Legal Group',
                specializations: ['AI/ML Systems', 'Sensor Technology', 'Marine Electronics'],
                experience_years: 15,
                success_rate: 91.7,
                average_cost: {
                    provisional: '$1,500',
                    utility: '$4,200',
                    international: '$10,500'
                },
                contact: {
                    phone: '+1-555-0124',
                    email: 'michael.chen@techpatent.com'
                },
                ratings: {
                    average: 4.9,
                    reviews: 83
                },
                languages: ['English', 'Mandarin', 'Japanese'],
                bar_admissions: ['USPTO', 'New York State Bar'],
                certifications: ['Patent Bar Certified', 'PhD Electrical Engineering']
            },
            {
                id: 'attorney_003',
                name: 'Lisa Rodriguez',
                firm: 'Marine Tech IP Solutions',
                specializations: ['Marine Technology', 'Environmental Sensors', 'Solar Systems'],
                experience_years: 9,
                success_rate: 89.5,
                average_cost: {
                    provisional: '$1,000',
                    utility: '$3,200',
                    international: '$7,800'
                },
                contact: {
                    phone: '+1-555-0125',
                    email: 'lisa.rodriguez@marinetechip.com'
                },
                ratings: {
                    average: 4.7,
                    reviews: 45
                },
                languages: ['English', 'Spanish', 'Portuguese'],
                bar_admissions: ['USPTO', 'Florida State Bar'],
                certifications: ['Patent Bar Certified', 'Marine Engineering Background']
            }
        ];

        sampleAttorneys.forEach(attorney => {
            this.attorneys.set(attorney.id, attorney);
        });

        // Initialize sample patent database entries
        const samplePatents = [
            {
                id: 'patent_001',
                patent_number: 'US11,234,567',
                title: 'Underwater Fish Counting System with AI Recognition',
                inventors: ['John Smith', 'Emily Davis'],
                assignee: 'AquaTech Solutions Inc.',
                filing_date: new Date('2022-03-15'),
                granted_date: new Date('2023-08-22'),
                expiry_date: new Date('2042-03-15'),
                status: 'granted',
                classification: {
                    primary: 'G06K 9/62',
                    secondary: ['A01K 61/00', 'G06T 7/20']
                },
                abstract: 'A system for automatically counting fish underwater using computer vision and machine learning algorithms...',
                claims: 20,
                related_applications: ['US16,789,234', 'PCT/US2022/123456'],
                geography: ['US', 'EP', 'JP', 'CA']
            },
            {
                id: 'patent_002',
                patent_number: 'US11,345,678',
                title: 'Solar-Powered Wireless Camera Network with Mesh Communication',
                inventors: ['Maria Garcia', 'David Wilson'],
                assignee: 'SolarVision Technologies LLC',
                filing_date: new Date('2021-11-08'),
                granted_date: new Date('2023-06-14'),
                expiry_date: new Date('2041-11-08'),
                status: 'granted',
                classification: {
                    primary: 'H04N 7/18',
                    secondary: ['H02S 40/30', 'H04W 84/18']
                },
                abstract: 'A solar-powered camera system with wireless mesh networking capabilities for remote monitoring...',
                claims: 18,
                related_applications: ['US16,890,345', 'PCT/US2021/234567'],
                geography: ['US', 'EP', 'CN', 'AU']
            },
            {
                id: 'patent_003',
                patent_number: 'US11,456,789',
                title: 'Multi-Sensor Environmental Monitoring Hub with Edge Computing',
                inventors: ['Alex Thompson', 'Rachel Kim'],
                assignee: 'EcoSense Innovations Inc.',
                filing_date: new Date('2022-07-20'),
                granted_date: new Date('2024-01-10'),
                expiry_date: new Date('2042-07-20'),
                status: 'granted',
                classification: {
                    primary: 'G01D 21/02',
                    secondary: ['G06F 15/16', 'H04L 12/28']
                },
                abstract: 'An environmental monitoring system with multiple sensors and edge computing capabilities...',
                claims: 25,
                related_applications: ['US17,123,456', 'PCT/US2022/345678'],
                geography: ['US', 'EP', 'JP', 'KR', 'CA']
            }
        ];

        samplePatents.forEach(patent => {
            this.patentDatabase.set(patent.id, patent);
        });

        // Initialize sample applications
        const sampleApplications = [
            {
                id: 'app_001',
                title: 'Advanced Fish Species Recognition Algorithm',
                inventor_id: 'user_003',
                status: 'draft',
                type: 'utility',
                priority_date: new Date('2024-08-01'),
                description: 'Machine learning algorithm for identifying and counting multiple fish species',
                category: 'AI/ML Systems',
                assigned_attorney: 'attorney_002',
                estimated_cost: '$4,200',
                timeline: {
                    filing: new Date('2024-09-15'),
                    examination: new Date('2024-12-15'),
                    estimated_grant: new Date('2025-08-15')
                },
                documentation_status: {
                    invention_disclosure: 'complete',
                    prior_art_search: 'in_progress',
                    claims_draft: 'pending',
                    drawings: 'complete'
                }
            },
            {
                id: 'app_002',
                title: 'Ultra-Low Power Sensor Network Architecture',
                inventor_id: 'user_001',
                status: 'filed',
                type: 'utility',
                priority_date: new Date('2024-07-10'),
                application_number: 'US18/123,456',
                description: 'Novel architecture for ultra-low power sensor networks with mesh topology',
                category: 'Hardware Systems',
                assigned_attorney: 'attorney_001',
                estimated_cost: '$3,500',
                timeline: {
                    filing: new Date('2024-07-10'),
                    examination: new Date('2024-10-10'),
                    estimated_grant: new Date('2025-05-10')
                },
                documentation_status: {
                    invention_disclosure: 'complete',
                    prior_art_search: 'complete',
                    claims_draft: 'complete',
                    drawings: 'complete'
                }
            }
        ];

        sampleApplications.forEach(app => {
            this.applications.set(app.id, app);
        });

        // Initialize sample monitoring alerts
        const sampleMonitoring = [
            {
                id: 'monitor_001',
                user_id: 'user_001',
                keywords: ['sensor network', 'low power', 'mesh topology'],
                alert_frequency: 'weekly',
                last_alert: new Date('2024-08-17'),
                active: true,
                matches_found: 12
            },
            {
                id: 'monitor_002',
                user_id: 'user_003',
                keywords: ['fish counting', 'underwater detection', 'marine AI'],
                alert_frequency: 'monthly',
                last_alert: new Date('2024-08-01'),
                active: true,
                matches_found: 8
            }
        ];

        sampleMonitoring.forEach(monitor => {
            this.monitoring.set(monitor.id, monitor);
        });
    }

    generateId(prefix) {
        return `${prefix}_${crypto.randomBytes(8).toString('hex')}`;
    }

    // Patent Search and Analysis
    async searchPatents(searchParams) {
        try {
            let results = Array.from(this.patentDatabase.values());

            // Apply search filters
            if (searchParams.keywords) {
                const keywords = searchParams.keywords.toLowerCase().split(/\s+/);
                results = results.filter(patent => {
                    const searchText = `${patent.title} ${patent.abstract}`.toLowerCase();
                    return keywords.some(keyword => searchText.includes(keyword));
                });
            }

            if (searchParams.classification) {
                results = results.filter(patent => 
                    patent.classification.primary === searchParams.classification ||
                    patent.classification.secondary.includes(searchParams.classification)
                );
            }

            if (searchParams.assignee) {
                results = results.filter(patent => 
                    patent.assignee.toLowerCase().includes(searchParams.assignee.toLowerCase())
                );
            }

            if (searchParams.inventor) {
                results = results.filter(patent => 
                    patent.inventors.some(inv => 
                        inv.toLowerCase().includes(searchParams.inventor.toLowerCase())
                    )
                );
            }

            if (searchParams.date_range) {
                const { start, end } = searchParams.date_range;
                results = results.filter(patent => {
                    const filingDate = new Date(patent.filing_date);
                    return filingDate >= new Date(start) && filingDate <= new Date(end);
                });
            }

            // Calculate relevance scores
            results = results.map(patent => {
                let relevance = 0;
                if (searchParams.keywords) {
                    const keywords = searchParams.keywords.toLowerCase().split(/\s+/);
                    const searchText = `${patent.title} ${patent.abstract}`.toLowerCase();
                    relevance = keywords.reduce((score, keyword) => {
                        const matches = (searchText.match(new RegExp(keyword, 'g')) || []).length;
                        return score + matches;
                    }, 0);
                }
                return { ...patent, relevance_score: relevance };
            });

            // Sort by relevance
            results.sort((a, b) => b.relevance_score - a.relevance_score);

            const searchRecord = {
                id: this.generateId('search'),
                query: searchParams,
                results_count: results.length,
                timestamp: new Date(),
                results: results.slice(0, searchParams.limit || 50)
            };

            this.searches.set(searchRecord.id, searchRecord);

            return {
                success: true,
                search_id: searchRecord.id,
                results: searchRecord.results,
                total_found: results.length,
                search_params: searchParams
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async conductPriorArtSearch(inventionDescription) {
        try {
            const priorArtId = this.generateId('prior_art');
            
            // Extract key concepts from invention description
            const keywordExtraction = this.extractTechnicalKeywords(inventionDescription);
            
            // Search existing patents
            const searchResults = await this.searchPatents({
                keywords: keywordExtraction.join(' '),
                limit: 100
            });

            // Analyze relevance and potential conflicts
            const analysis = this.analyzePriorArtRelevance(inventionDescription, searchResults.results);

            const priorArtReport = {
                id: priorArtId,
                invention_description: inventionDescription,
                search_keywords: keywordExtraction,
                relevant_patents: analysis.relevant_patents,
                potential_conflicts: analysis.conflicts,
                patentability_assessment: analysis.patentability,
                recommendations: analysis.recommendations,
                generated_date: new Date(),
                confidence_score: analysis.confidence
            };

            this.priorArt.set(priorArtId, priorArtReport);

            return {
                success: true,
                prior_art_id: priorArtId,
                report: priorArtReport
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    extractTechnicalKeywords(description) {
        // Simplified keyword extraction - in production, this would use NLP
        const technicalTerms = [
            'sensor', 'wireless', 'AI', 'machine learning', 'IoT', 'solar',
            'battery', 'mesh', 'network', 'detection', 'recognition',
            'algorithm', 'hardware', 'software', 'system', 'device',
            'monitoring', 'tracking', 'analysis', 'processing', 'communication'
        ];

        const words = description.toLowerCase().split(/\s+/);
        return words.filter(word => 
            technicalTerms.includes(word) || word.length > 6
        ).slice(0, 10);
    }

    analyzePriorArtRelevance(inventionDescription, patents) {
        // Simplified analysis - production version would use advanced NLP
        const relevant = patents.filter(p => p.relevance_score > 0);
        
        return {
            relevant_patents: relevant.slice(0, 20),
            conflicts: relevant.filter(p => p.relevance_score > 5).slice(0, 5),
            patentability: relevant.length < 10 ? 'High' : relevant.length < 20 ? 'Medium' : 'Low',
            recommendations: this.generatePatentabilityRecommendations(relevant.length),
            confidence: Math.max(0.3, 1 - (relevant.length / 100))
        };
    }

    generatePatentabilityRecommendations(priorArtCount) {
        if (priorArtCount < 5) {
            return [
                'Strong patentability prospects',
                'Proceed with utility patent application',
                'Consider broader claim scope',
                'File provisional application for early priority date'
            ];
        } else if (priorArtCount < 15) {
            return [
                'Moderate patentability with careful claim crafting',
                'Focus on novel technical aspects',
                'Consider continuation-in-part strategy',
                'Consult patent attorney for claim optimization'
            ];
        } else {
            return [
                'Challenging patentability landscape',
                'Identify unique differentiating features',
                'Consider trade secret protection instead',
                'Explore design patent possibilities'
            ];
        }
    }

    // Application Management
    async createPatentApplication(applicationData) {
        try {
            const application = {
                id: this.generateId('app'),
                title: applicationData.title,
                inventor_id: applicationData.inventor_id,
                inventors: applicationData.inventors || [],
                assignee: applicationData.assignee || '',
                status: 'draft',
                type: applicationData.type || 'utility',
                priority_date: new Date(),
                description: applicationData.description,
                category: applicationData.category,
                claims: applicationData.claims || [],
                drawings: applicationData.drawings || [],
                assigned_attorney: applicationData.attorney_id || null,
                estimated_cost: '$0',
                timeline: {
                    creation: new Date(),
                    target_filing: applicationData.target_filing || new Date(Date.now() + 60*24*60*60*1000),
                    estimated_examination: null,
                    estimated_grant: null
                },
                documentation_status: {
                    invention_disclosure: 'pending',
                    prior_art_search: 'pending',
                    claims_draft: 'pending',
                    drawings: applicationData.drawings ? 'complete' : 'pending',
                    specification: 'pending'
                },
                costs: {
                    attorney_fees: 0,
                    filing_fees: 0,
                    search_fees: 0,
                    examination_fees: 0,
                    total_estimated: 0
                }
            };

            this.applications.set(application.id, application);
            this.emit('application_created', application);

            return {
                success: true,
                application_id: application.id,
                message: 'Patent application created successfully'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async updateApplicationStatus(applicationId, status, notes = '') {
        try {
            const application = this.applications.get(applicationId);
            if (!application) {
                throw new Error('Application not found');
            }

            const oldStatus = application.status;
            application.status = status;
            application.last_updated = new Date();

            if (notes) {
                if (!application.status_history) {
                    application.status_history = [];
                }
                application.status_history.push({
                    from: oldStatus,
                    to: status,
                    date: new Date(),
                    notes: notes
                });
            }

            // Update timeline based on status
            if (status === 'filed' && !application.timeline.filing) {
                application.timeline.filing = new Date();
                application.timeline.estimated_examination = new Date(Date.now() + 90*24*60*60*1000);
                application.timeline.estimated_grant = new Date(Date.now() + 365*24*60*60*1000);
            }

            this.applications.set(applicationId, application);
            this.emit('application_status_updated', { application_id: applicationId, old_status: oldStatus, new_status: status });

            return {
                success: true,
                message: `Application status updated to ${status}`
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    // Attorney Management
    async searchAttorneys(criteria = {}) {
        try {
            let attorneys = Array.from(this.attorneys.values());

            if (criteria.specialization) {
                attorneys = attorneys.filter(a => 
                    a.specializations.some(s => 
                        s.toLowerCase().includes(criteria.specialization.toLowerCase())
                    )
                );
            }

            if (criteria.max_cost) {
                attorneys = attorneys.filter(a => 
                    parseInt(a.average_cost.utility.replace(/[$,]/g, '')) <= criteria.max_cost
                );
            }

            if (criteria.min_success_rate) {
                attorneys = attorneys.filter(a => a.success_rate >= criteria.min_success_rate);
            }

            if (criteria.min_rating) {
                attorneys = attorneys.filter(a => a.ratings.average >= criteria.min_rating);
            }

            // Sort by rating and success rate
            attorneys.sort((a, b) => {
                const scoreA = (a.ratings.average * 0.6) + (a.success_rate * 0.004);
                const scoreB = (b.ratings.average * 0.6) + (b.success_rate * 0.004);
                return scoreB - scoreA;
            });

            return {
                success: true,
                attorneys: attorneys,
                search_criteria: criteria
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async requestAttorneyConsultation(attorneyId, applicationId, consultationType = 'initial') {
        try {
            const attorney = this.attorneys.get(attorneyId);
            const application = this.applications.get(applicationId);

            if (!attorney) throw new Error('Attorney not found');
            if (!application) throw new Error('Application not found');

            const consultation = {
                id: this.generateId('consultation'),
                attorney_id: attorneyId,
                application_id: applicationId,
                type: consultationType,
                status: 'requested',
                requested_date: new Date(),
                estimated_cost: this.getConsultationCost(consultationType),
                meeting_preferences: {
                    format: 'video_call',
                    duration: '60 minutes',
                    availability: 'weekdays'
                }
            };

            this.emit('consultation_requested', consultation);

            return {
                success: true,
                consultation_id: consultation.id,
                attorney: attorney,
                estimated_cost: consultation.estimated_cost,
                message: 'Consultation requested successfully'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    getConsultationCost(type) {
        const costs = {
            'initial': '$200',
            'patentability': '$350',
            'filing_strategy': '$450',
            'prosecution': '$300',
            'licensing': '$400'
        };
        return costs[type] || '$250';
    }

    // Patent Monitoring
    async setupPatentMonitoring(userId, keywords, alertFrequency = 'weekly') {
        try {
            const monitoring = {
                id: this.generateId('monitor'),
                user_id: userId,
                keywords: Array.isArray(keywords) ? keywords : [keywords],
                alert_frequency: alertFrequency,
                created_date: new Date(),
                last_alert: null,
                active: true,
                matches_found: 0,
                notification_preferences: {
                    email: true,
                    in_app: true,
                    webhook: false
                }
            };

            this.monitoring.set(monitoring.id, monitoring);
            this.emit('monitoring_setup', monitoring);

            return {
                success: true,
                monitoring_id: monitoring.id,
                message: 'Patent monitoring setup successfully'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async runMonitoringCheck(monitoringId) {
        try {
            const monitor = this.monitoring.get(monitoringId);
            if (!monitor) {
                throw new Error('Monitoring configuration not found');
            }

            // Search for new patents matching keywords
            const searchResults = await this.searchPatents({
                keywords: monitor.keywords.join(' '),
                date_range: {
                    start: monitor.last_alert || new Date(Date.now() - 7*24*60*60*1000),
                    end: new Date()
                }
            });

            if (searchResults.results.length > 0) {
                monitor.matches_found += searchResults.results.length;
                monitor.last_alert = new Date();
                this.monitoring.set(monitoringId, monitor);

                this.emit('monitoring_alert', {
                    monitoring_id: monitoringId,
                    new_matches: searchResults.results.length,
                    results: searchResults.results.slice(0, 10)
                });
            }

            return {
                success: true,
                new_matches: searchResults.results.length,
                latest_patents: searchResults.results.slice(0, 5)
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    // Licensing and IP Management
    async createLicensingOpportunity(patentId, terms) {
        try {
            const patent = this.patentDatabase.get(patentId);
            if (!patent) {
                throw new Error('Patent not found');
            }

            const licensing = {
                id: this.generateId('license'),
                patent_id: patentId,
                licensor_id: terms.licensor_id,
                status: 'available',
                license_type: terms.type || 'non-exclusive',
                territory: terms.territory || 'worldwide',
                field_of_use: terms.field_of_use || 'all fields',
                royalty_rate: terms.royalty_rate || '5%',
                upfront_fee: terms.upfront_fee || '$0',
                minimum_royalty: terms.minimum_royalty || '$0',
                term_years: terms.term_years || 'life_of_patent',
                created_date: new Date(),
                expressions_of_interest: 0
            };

            this.licensing.set(licensing.id, licensing);
            this.emit('licensing_opportunity_created', licensing);

            return {
                success: true,
                licensing_id: licensing.id,
                message: 'Licensing opportunity created successfully'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    // Portfolio Analytics
    async getPatentPortfolioAnalysis(userId) {
        try {
            const userApplications = Array.from(this.applications.values())
                .filter(app => app.inventor_id === userId);

            const statusBreakdown = {};
            const categoryBreakdown = {};
            let totalCosts = 0;

            userApplications.forEach(app => {
                // Status breakdown
                statusBreakdown[app.status] = (statusBreakdown[app.status] || 0) + 1;

                // Category breakdown
                categoryBreakdown[app.category] = (categoryBreakdown[app.category] || 0) + 1;

                // Cost calculation
                totalCosts += app.costs ? app.costs.total_estimated || 0 : 0;
            });

            const analysis = {
                total_applications: userApplications.length,
                status_breakdown: statusBreakdown,
                category_breakdown: categoryBreakdown,
                total_estimated_costs: totalCosts,
                average_cost_per_application: userApplications.length > 0 ? totalCosts / userApplications.length : 0,
                timeline_analysis: this.analyzeTimelines(userApplications),
                recommendations: this.generatePortfolioRecommendations(userApplications)
            };

            return {
                success: true,
                portfolio_analysis: analysis,
                applications: userApplications
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    analyzeTimelines(applications) {
        const activeApps = applications.filter(app => 
            ['draft', 'filed', 'under_examination'].includes(app.status)
        );

        if (activeApps.length === 0) {
            return { average_timeline: null, pending_deadlines: [] };
        }

        const now = new Date();
        const pendingDeadlines = activeApps
            .filter(app => app.timeline && app.timeline.target_filing)
            .map(app => ({
                application_id: app.id,
                title: app.title,
                deadline: app.timeline.target_filing,
                days_remaining: Math.ceil((new Date(app.timeline.target_filing) - now) / (1000 * 60 * 60 * 24))
            }))
            .filter(item => item.days_remaining > -30)
            .sort((a, b) => a.days_remaining - b.days_remaining);

        return {
            active_applications: activeApps.length,
            pending_deadlines: pendingDeadlines,
            urgent_deadlines: pendingDeadlines.filter(d => d.days_remaining <= 30).length
        };
    }

    generatePortfolioRecommendations(applications) {
        const recommendations = [];

        const draftApps = applications.filter(app => app.status === 'draft').length;
        if (draftApps > 3) {
            recommendations.push('Consider prioritizing draft applications for filing to secure priority dates');
        }

        const categories = new Set(applications.map(app => app.category));
        if (categories.size === 1) {
            recommendations.push('Consider diversifying patent portfolio across multiple technology areas');
        }

        if (applications.length > 5) {
            recommendations.push('Consider patent portfolio management tools for better tracking and analytics');
        }

        if (applications.some(app => !app.assigned_attorney)) {
            recommendations.push('Assign patent attorneys to applications for professional prosecution');
        }

        return recommendations;
    }
}

export default PatentProtectionSystem;