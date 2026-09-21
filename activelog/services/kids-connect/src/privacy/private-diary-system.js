const EventEmitter = require('events');
const crypto = require('crypto');

class PrivateDiarySystem extends EventEmitter {
    constructor() {
        super();
        this.diaryEntries = new Map();
        this.diarySettings = new Map();
        this.emergencyAccess = new Map();
        this.safetyFlags = new Map();
        this.encryptionKeys = new Map();
        this.accessLogs = new Map();
        this.therapeuticResources = new Map();
        this.parentalGuidance = new Map();
        this.initializeDefaultSettings();
    }

    initializeDefaultSettings() {
        this.privacyPolicies = {
            diaryPrivacy: {
                encryptionLevel: 'AES-256',
                parentAccess: false, // Parents cannot read diary entries
                teacherAccess: false, // Teachers cannot read diary entries
                platformAccess: 'emergency-only', // Only in extreme safety situations
                childControls: true, // Child has full control over their diary
                deletionRights: true, // Child can delete entries
                exportRights: true, // Child can export their diary
                dataRetention: 'until-deletion', // Keep until child/parent deletes account
                anonymousMode: true // Remove identifying information from safety analysis
            },
            safetyMonitoring: {
                automaticScanEnabled: true, // Scan for dangerous content only
                keywordDetection: 'safety-critical-only', // Only flag serious safety issues
                sentimentAnalysis: 'mental-health-indicators', // Watch for depression, self-harm
                professionalIntervention: 'when-necessary', // Contact professionals if needed
                parentNotification: 'safety-concerns-only', // Only notify for serious safety
                schoolNotification: 'imminent-danger-only', // Only for immediate threats
                emergencyServices: 'life-threatening-only' // Contact authorities only for extreme cases
            },
            therapeuticFeatures: {
                promptsAvailable: true, // Helpful writing prompts
                emotionTracking: true, // Help kids identify emotions
                copingStrategies: true, // Suggest healthy coping mechanisms
                positiveReinforcement: true, // Encourage healthy expression
                professionalResources: true, // Links to counseling resources
                peerSupport: false, // NO sharing with other users
                anonymousSupport: true // Anonymous crisis support if needed
            }
        };

        this.safetyKeywords = {
            critical: [
                'suicide', 'kill myself', 'end my life', 'want to die', 'better off dead',
                'self harm', 'cut myself', 'hurt myself', 'hate myself',
                'sexual abuse', 'touched inappropriately', 'forced me to', 
                'bullying me', 'threatening me', 'scared to go home',
                'nobody cares', 'everyone hates me', 'worthless', 'hopeless'
            ],
            concerning: [
                'depressed', 'sad all the time', 'crying every day', 'can\'t sleep',
                'not eating', 'angry all the time', 'worried', 'anxious',
                'lonely', 'isolated', 'nobody understands', 'stressed',
                'overwhelmed', 'scared', 'confused', 'lost'
            ],
            positive: [
                'happy', 'excited', 'proud', 'accomplished', 'grateful',
                'loved', 'supported', 'confident', 'hopeful', 'peaceful',
                'successful', 'creative', 'inspired', 'motivated', 'calm'
            ]
        };

        this.therapeuticPrompts = [
            "What made you smile today?",
            "Describe a person who makes you feel safe and loved.",
            "What is something you're proud of accomplishing?",
            "If you could tell your future self something, what would it be?",
            "What are three things you're grateful for today?",
            "Describe your perfect day. What would you do?",
            "What is a challenge you overcame recently?",
            "Who is someone you admire and why?",
            "What makes you feel most like yourself?",
            "If you could change one thing in the world, what would it be?"
        ];
    }

    async createDiary(childId, parentIds, settings = {}) {
        // Generate encryption key for this child's diary
        const encryptionKey = crypto.randomBytes(32);
        this.encryptionKeys.set(childId, encryptionKey);

        const diarySettings = {
            childId,
            parentIds,
            createdAt: new Date(),
            settings: {
                ...this.privacyPolicies,
                ...settings
            },
            totalEntries: 0,
            lastEntry: null,
            safetyAlerts: 0,
            emotionTracking: {
                enabled: true,
                history: []
            },
            therapeuticMode: settings.therapeuticMode || false,
            parentalGuidanceRequests: [],
            emergencyContactsNotified: [],
            professionalResourcesAccessed: []
        };

        this.diarySettings.set(childId, diarySettings);
        
        // Initialize empty diary entries
        this.diaryEntries.set(childId, []);
        
        // Initialize access logs
        this.accessLogs.set(childId, []);

        // Inform parents about diary privacy (but not give access)
        await this.informParentsAboutDiary(parentIds, childId);

        this.emit('diaryCreated', { childId, privacyGuaranteed: true });

        return {
            diaryId: childId,
            privacyLevel: 'maximum',
            parentAccess: false,
            safetyMonitoring: 'anonymous-and-minimal',
            message: 'Your diary is completely private. Only you can read your entries.'
        };
    }

    async addDiaryEntry(childId, content, metadata = {}) {
        const settings = this.diarySettings.get(childId);
        if (!settings) {
            throw new Error('Diary not found for child');
        }

        // Encrypt the content
        const encryptedContent = await this.encryptContent(childId, content);

        const entry = {
            id: this.generateSecureId(),
            childId,
            timestamp: new Date(),
            encryptedContent,
            wordCount: content.split(' ').length,
            characterCount: content.length,
            metadata: {
                mood: metadata.mood || null,
                prompt: metadata.prompt || null,
                writingTime: metadata.writingTime || null,
                deviceType: metadata.deviceType || null
            },
            safetyAnalysis: null, // Will be populated after analysis
            flagged: false,
            parentNotified: false,
            professionalReferred: false
        };

        // Perform safety analysis on the original content (before encryption)
        const safetyAnalysis = await this.performSafetyAnalysis(content, childId, entry.id);
        entry.safetyAnalysis = safetyAnalysis;

        // Store the encrypted entry
        this.diaryEntries.get(childId).push(entry);
        
        // Update settings
        settings.totalEntries++;
        settings.lastEntry = new Date();

        // Track emotions if enabled
        if (settings.emotionTracking.enabled && metadata.mood) {
            settings.emotionTracking.history.push({
                date: new Date(),
                mood: metadata.mood,
                entryId: entry.id
            });
        }

        // Handle any safety flags
        if (safetyAnalysis.flagged) {
            await this.handleSafetyFlag(childId, entry, safetyAnalysis);
        }

        // Log access (child writing)
        await this.logAccess(childId, 'write', entry.id, childId);

        this.emit('diaryEntryAdded', { 
            childId, 
            entryId: entry.id, 
            safetyStatus: safetyAnalysis.level,
            flagged: safetyAnalysis.flagged 
        });

        return {
            entryId: entry.id,
            timestamp: entry.timestamp,
            wordCount: entry.wordCount,
            safetyCheck: safetyAnalysis.flagged ? 'reviewed-for-safety' : 'safe',
            nextPrompt: this.getNextTherapeuticPrompt()
        };
    }

    async encryptContent(childId, content) {
        const key = this.encryptionKeys.get(childId);
        if (!key) {
            throw new Error('Encryption key not found');
        }

        const iv = crypto.randomBytes(16);
        const cipher = crypto.createCipher('aes-256-cbc', key);
        
        let encrypted = cipher.update(content, 'utf8', 'hex');
        encrypted += cipher.final('hex');

        return {
            iv: iv.toString('hex'),
            content: encrypted
        };
    }

    async decryptContent(childId, encryptedData) {
        const key = this.encryptionKeys.get(childId);
        if (!key) {
            throw new Error('Encryption key not found');
        }

        const decipher = crypto.createDecipher('aes-256-cbc', key);
        
        let decrypted = decipher.update(encryptedData.content, 'hex', 'utf8');
        decrypted += decipher.final('utf8');

        return decrypted;
    }

    async performSafetyAnalysis(content, childId, entryId) {
        const analysis = {
            entryId,
            analyzedAt: new Date(),
            level: 'safe', // safe, concerning, critical
            flags: [],
            keywordsDetected: {
                critical: [],
                concerning: [],
                positive: []
            },
            sentimentScore: null,
            recommendedAction: 'none',
            flagged: false,
            anonymous: true // Always anonymous to protect privacy
        };

        // Check for critical safety keywords
        const criticalFlags = this.safetyKeywords.critical.filter(keyword => 
            content.toLowerCase().includes(keyword.toLowerCase())
        );
        
        const concerningFlags = this.safetyKeywords.concerning.filter(keyword => 
            content.toLowerCase().includes(keyword.toLowerCase())
        );

        const positiveFlags = this.safetyKeywords.positive.filter(keyword => 
            content.toLowerCase().includes(keyword.toLowerCase())
        );

        analysis.keywordsDetected.critical = criticalFlags;
        analysis.keywordsDetected.concerning = concerningFlags;
        analysis.keywordsDetected.positive = positiveFlags;

        // Determine safety level
        if (criticalFlags.length > 0) {
            analysis.level = 'critical';
            analysis.flagged = true;
            analysis.recommendedAction = 'immediate-intervention';
            analysis.flags.push('critical-safety-concern');
        } else if (concerningFlags.length >= 3) {
            analysis.level = 'concerning';
            analysis.flagged = true;
            analysis.recommendedAction = 'parental-awareness-and-support';
            analysis.flags.push('mental-health-concern');
        } else if (concerningFlags.length > 0) {
            analysis.level = 'monitor';
            analysis.recommendedAction = 'provide-resources';
            analysis.flags.push('mild-concern');
        }

        // Simple sentiment analysis
        const positiveWords = positiveFlags.length;
        const negativeWords = criticalFlags.length + concerningFlags.length;
        analysis.sentimentScore = positiveWords - negativeWords;

        // Store safety analysis separately (without content)
        this.safetyFlags.set(entryId, analysis);

        return analysis;
    }

    async handleSafetyFlag(childId, entry, safetyAnalysis) {
        const settings = this.diarySettings.get(childId);
        
        if (safetyAnalysis.level === 'critical') {
            // Critical safety concern - immediate intervention needed
            await this.handleCriticalSafetyConcern(childId, entry, safetyAnalysis);
        } else if (safetyAnalysis.level === 'concerning') {
            // Mental health concern - provide support and consider parental awareness
            await this.handleMentalHealthConcern(childId, entry, safetyAnalysis);
        } else if (safetyAnalysis.level === 'monitor') {
            // Mild concern - provide resources and monitor
            await this.provideSupportResources(childId, entry, safetyAnalysis);
        }

        settings.safetyAlerts++;
    }

    async handleCriticalSafetyConcern(childId, entry, safetyAnalysis) {
        // This is for life-threatening situations
        const settings = this.diarySettings.get(childId);
        
        // Create anonymous alert for parents and professionals
        const alertData = {
            childId,
            level: 'critical',
            timestamp: new Date(),
            concernType: safetyAnalysis.flags,
            anonymousSummary: 'Your child has expressed serious safety concerns in their private diary. Professional intervention may be needed.',
            resourcesProvided: [],
            professionalContactRecommended: true,
            emergencyServicesContacted: false
        };

        // Notify parents (without diary content)
        if (settings.settings.safetyMonitoring.parentNotification === 'safety-concerns-only') {
            await this.notifyParentsOfSafetyConcern(settings.parentIds, alertData);
        }

        // Contact professional resources
        await this.contactProfessionalResources(childId, alertData);

        // Provide immediate support to child
        await this.provideImmediateSupport(childId);

        // Log the intervention
        settings.emergencyContactsNotified.push({
            timestamp: new Date(),
            level: 'critical',
            action: 'professional-intervention-initiated'
        });

        this.emit('criticalSafetyConcern', alertData);
    }

    async handleMentalHealthConcern(childId, entry, safetyAnalysis) {
        const settings = this.diarySettings.get(childId);
        
        const alertData = {
            childId,
            level: 'concerning',
            timestamp: new Date(),
            concernType: safetyAnalysis.flags,
            anonymousSummary: 'Your child may be experiencing emotional difficulties. Consider having a caring conversation.',
            resourcesProvided: [],
            suggestedActions: [
                'Have a gentle, non-judgmental conversation',
                'Consider professional counseling resources',
                'Maintain open communication',
                'Monitor for changes in behavior'
            ]
        };

        // Provide gentle resources to the child
        await this.provideGentleSupport(childId, safetyAnalysis);

        // Notify parents with guidance (no diary content shared)
        await this.notifyParentsWithGuidance(settings.parentIds, alertData);

        this.emit('mentalHealthConcern', alertData);
    }

    async provideSupportResources(childId, entry, safetyAnalysis) {
        // Provide helpful resources without alerting parents for mild concerns
        const resources = {
            copingStrategies: [
                'Take deep breaths when feeling overwhelmed',
                'Talk to a trusted adult about your feelings',
                'Try physical exercise or creative activities',
                'Practice mindfulness or meditation',
                'Write more about your feelings - it can help'
            ],
            encouragement: [
                'Your feelings are valid and important',
                'It\'s normal to have difficult days',
                'You are stronger than you think',
                'There are people who care about you',
                'Things can and do get better'
            ],
            resources: [
                'Kids Help Phone: 1-800-668-6868',
                'Crisis Text Line: Text HOME to 741741',
                'Local counseling services available',
                'School counselor can provide support'
            ]
        };

        // Store resources provided
        this.therapeuticResources.set(entry.id, {
            timestamp: new Date(),
            resources: resources,
            childResponseRequested: false
        });

        // Send supportive message to child (shown when they next log in)
        await this.sendSupportMessage(childId, resources);
    }

    async getDiaryEntries(childId, requesterId, limit = 10) {
        // Only the child can read their own diary entries
        if (requesterId !== childId) {
            // Check if this is an emergency access request
            const emergencyAccess = this.emergencyAccess.get(childId);
            if (!emergencyAccess || emergencyAccess.requesterId !== requesterId) {
                throw new Error('Access denied. Diary entries are private.');
            }
        }

        const entries = this.diaryEntries.get(childId) || [];
        const recentEntries = entries.slice(-limit).reverse(); // Most recent first

        // Decrypt entries for the child
        const decryptedEntries = [];
        for (const entry of recentEntries) {
            const decryptedContent = await this.decryptContent(childId, entry.encryptedContent);
            
            decryptedEntries.push({
                id: entry.id,
                timestamp: entry.timestamp,
                content: decryptedContent,
                wordCount: entry.wordCount,
                mood: entry.metadata.mood,
                prompt: entry.metadata.prompt
            });
        }

        // Log access
        await this.logAccess(childId, 'read', null, requesterId);

        return decryptedEntries;
    }

    async requestEmergencyAccess(parentId, childId, reason, professionalInvolvement = false) {
        // Emergency access is only granted in extreme circumstances
        const settings = this.diarySettings.get(childId);
        if (!settings || !settings.parentIds.includes(parentId)) {
            throw new Error('Invalid parent or child ID');
        }

        const emergencyRequest = {
            id: this.generateSecureId(),
            parentId,
            childId,
            reason,
            professionalInvolvement,
            requestedAt: new Date(),
            status: 'pending',
            approvedBy: null,
            approvedAt: null,
            accessLevel: 'summary-only', // Never full content without extreme justification
            justification: '',
            timeLimit: 24 * 60 * 60 * 1000, // 24 hours
            childInformed: false
        };

        // Store emergency request
        this.emergencyAccess.set(childId, emergencyRequest);

        // This would typically require manual approval by platform administrators
        // and possibly child protective services or mental health professionals
        
        this.emit('emergencyAccessRequested', emergencyRequest);

        return {
            requestId: emergencyRequest.id,
            status: 'pending',
            message: 'Emergency access request submitted for review. This requires professional evaluation.',
            reviewTime: 'Manual review required - typically 2-4 hours for genuine emergencies'
        };
    }

    async getChildDiaryDashboard(childId) {
        const settings = this.diarySettings.get(childId);
        if (!settings) {
            throw new Error('Diary not found');
        }

        const entries = this.diaryEntries.get(childId) || [];
        
        const dashboard = {
            totalEntries: entries.length,
            firstEntry: entries.length > 0 ? entries[0].timestamp : null,
            lastEntry: entries.length > 0 ? entries[entries.length - 1].timestamp : null,
            writingStreak: await this.calculateWritingStreak(childId),
            wordCount: entries.reduce((sum, entry) => sum + entry.wordCount, 0),
            averageWordsPerEntry: entries.length > 0 ? 
                Math.round(entries.reduce((sum, entry) => sum + entry.wordCount, 0) / entries.length) : 0,
            moodTracking: settings.emotionTracking.enabled ? {
                enabled: true,
                recentMoods: settings.emotionTracking.history.slice(-7) // Last 7 entries
            } : { enabled: false },
            suggestedPrompts: this.getPersonalizedPrompts(childId),
            achievements: await this.getDiaryAchievements(childId),
            supportResources: await this.getAvailableResources(childId),
            privacyReminder: 'Your diary is completely private. Only you can read your entries.'
        };

        return dashboard;
    }

    async getParentGuidance(parentId, childId) {
        // Parents get guidance on supporting their child, but NO access to diary content
        const settings = this.diarySettings.get(childId);
        if (!settings || !settings.parentIds.includes(parentId)) {
            throw new Error('Invalid parent or child ID');
        }

        const guidance = {
            childId,
            diaryActive: settings.totalEntries > 0,
            lastActivity: settings.lastEntry,
            writingFrequency: await this.calculateWritingFrequency(childId),
            generalWellbeingIndicators: await this.getAnonymousWellbeingIndicators(childId),
            supportingSuggestions: [
                'Encourage regular writing as a healthy emotional outlet',
                'Respect your child\'s privacy - their diary is their safe space',
                'Be available for conversations when they want to talk',
                'Look for changes in mood or behavior in daily life',
                'Consider family activities that promote emotional expression'
            ],
            resourcesForParents: [
                'How to support children\'s emotional development',
                'Recognizing signs of emotional distress',
                'When to seek professional help',
                'Building trust and open communication'
            ],
            warningSignsToWatch: [
                'Significant changes in sleep or eating patterns',
                'Withdrawal from family and friends',
                'Decline in school performance',
                'Loss of interest in usual activities',
                'Expressions of hopelessness or self-harm'
            ],
            professionalResourcesAvailable: true,
            emergencyContactInfo: {
                crisisLine: '1-800-273-8255',
                textCrisis: 'Text HOME to 741741',
                localEmergency: '911'
            }
        };

        return guidance;
    }

    async logAccess(childId, action, entryId, accessorId) {
        const log = {
            childId,
            action, // read, write, emergency-access
            entryId,
            accessorId,
            timestamp: new Date(),
            ipAddress: null, // Would be captured from request
            userAgent: null // Would be captured from request
        };

        if (!this.accessLogs.has(childId)) {
            this.accessLogs.set(childId, []);
        }
        this.accessLogs.get(childId).push(log);
    }

    async informParentsAboutDiary(parentIds, childId) {
        const notification = {
            type: 'diary-created',
            childId,
            message: 'Your child has started using a private diary feature. This is a safe space for them to express their feelings privately. You will be notified only if there are serious safety concerns.',
            privacyPolicy: 'complete-privacy',
            safetyMonitoring: 'anonymous-safety-monitoring-only',
            yourRole: 'supportive-and-available',
            resources: 'parental-guidance-available'
        };

        for (const parentId of parentIds) {
            this.emit('parentNotification', {
                parentId,
                notification
            });
        }
    }

    getNextTherapeuticPrompt() {
        const randomIndex = Math.floor(Math.random() * this.therapeuticPrompts.length);
        return this.therapeuticPrompts[randomIndex];
    }

    getPersonalizedPrompts(childId) {
        // Could be enhanced to provide personalized prompts based on previous entries
        return this.therapeuticPrompts.slice(0, 3);
    }

    generateSecureId() {
        return crypto.randomBytes(16).toString('hex');
    }

    // Additional helper methods...
    async calculateWritingStreak(childId) {
        // Implementation for calculating consecutive days of writing
        return 0;
    }

    async getDiaryAchievements(childId) {
        // Implementation for diary-related achievements
        return [];
    }

    async getAvailableResources(childId) {
        // Implementation for getting available support resources
        return [];
    }

    async calculateWritingFrequency(childId) {
        // Implementation for calculating writing frequency
        return 'occasional';
    }

    async getAnonymousWellbeingIndicators(childId) {
        // Implementation for anonymous wellbeing indicators
        return {
            overallTrend: 'stable',
            expressionFrequency: 'regular',
            emotionalRange: 'varied'
        };
    }

    async notifyParentsOfSafetyConcern(parentIds, alertData) {
        // Implementation for notifying parents of safety concerns
        for (const parentId of parentIds) {
            this.emit('safetyAlert', { parentId, alertData });
        }
    }

    async contactProfessionalResources(childId, alertData) {
        // Implementation for contacting professional resources
        this.emit('professionalResourceContact', { childId, alertData });
    }

    async provideImmediateSupport(childId) {
        // Implementation for providing immediate support resources
        this.emit('immediateSupportProvided', { childId });
    }

    async provideGentleSupport(childId, safetyAnalysis) {
        // Implementation for providing gentle support
        this.emit('gentleSupportProvided', { childId, safetyAnalysis });
    }

    async notifyParentsWithGuidance(parentIds, alertData) {
        // Implementation for notifying parents with guidance
        for (const parentId of parentIds) {
            this.emit('parentGuidance', { parentId, alertData });
        }
    }

    async sendSupportMessage(childId, resources) {
        // Implementation for sending support message to child
        this.emit('supportMessageSent', { childId, resources });
    }
}

module.exports = PrivateDiarySystem;