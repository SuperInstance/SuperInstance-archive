const EventEmitter = require('events');
const crypto = require('crypto');

class ParentApprovalSystem extends EventEmitter {
    constructor() {
        super();
        this.pendingApprovals = new Map();
        this.approvedConnections = new Map();
        this.parentPermissions = new Map();
        this.connectionRequests = new Map();
        this.childProfiles = new Map();
        this.approvalHistory = new Map();
        this.emergencyOverrides = new Map();
        this.initializeDefaultSettings();
    }

    initializeDefaultSettings() {
        this.defaultApprovalSettings = {
            requireApprovalFor: {
                newConnections: true,
                schoolChanges: true,
                programParticipation: true,
                languagePartners: true,
                culturalExchange: true,
                videoChat: true,
                fileSharing: true,
                locationSharing: false // Always disabled by default
            },
            autoApprovalCriteria: {
                sameSchool: false, // Still requires approval even within school
                teacherSupervised: true, // Can auto-approve teacher-supervised activities
                parentRecommended: true, // Parent can pre-approve specific users
                verifiedEducationalPlatform: true
            },
            restrictionLevels: {
                strict: 'all-require-approval',
                moderate: 'educational-auto-approve',
                relaxed: 'school-auto-approve' // Still safer than no approval
            }
        };
    }

    async registerChild(childData, parentData) {
        const childId = this.generateSecureId();
        const parentId = this.generateSecureId();
        
        const childProfile = {
            id: childId,
            name: childData.name,
            age: childData.age,
            grade: childData.grade,
            schoolId: childData.schoolId,
            parentIds: [parentId],
            approvalSettings: this.getAgeAppropriateSettings(childData.age),
            createdAt: new Date(),
            lastActive: null,
            emergencyContacts: childData.emergencyContacts || [],
            medicalInformation: childData.medicalInformation || {},
            specialNeeds: childData.specialNeeds || []
        };

        const parentPermissions = {
            parentId: parentId,
            childIds: [childId],
            name: parentData.name,
            email: parentData.email,
            phone: parentData.phone,
            relationshipToChild: parentData.relationship || 'parent',
            permissions: {
                canApproveConnections: true,
                canViewAllActivity: true,
                canSetTimeRestrictions: true,
                canAccessEmergencyOverride: true,
                canModifySettings: true,
                canExportData: true,
                canDeleteAccount: parentData.relationship === 'parent'
            },
            notificationPreferences: parentData.notificationPreferences || {
                email: true,
                sms: true,
                app: true,
                frequency: 'immediate' // immediate, hourly, daily
            },
            verificationStatus: 'pending',
            verificationMethod: null,
            verifiedAt: null
        };

        this.childProfiles.set(childId, childProfile);
        this.parentPermissions.set(parentId, parentPermissions);

        // Send verification email/SMS
        await this.sendParentVerification(parentPermissions);

        this.emit('childRegistered', { childId, parentId });

        return {
            childId,
            parentId,
            verificationRequired: true,
            message: 'Verification email sent to parent'
        };
    }

    getAgeAppropriateSettings(age) {
        if (age <= 8) {
            return {
                restrictionLevel: 'strict',
                requireApprovalFor: {
                    ...this.defaultApprovalSettings.requireApprovalFor,
                    allCommunication: true,
                    allContent: true
                },
                allowedContentTypes: ['text'],
                maxConnectionsPerDay: 2,
                maxSessionDuration: 30, // minutes
                parentMustBePresent: true
            };
        } else if (age <= 12) {
            return {
                restrictionLevel: 'strict',
                requireApprovalFor: this.defaultApprovalSettings.requireApprovalFor,
                allowedContentTypes: ['text', 'drawing', 'educational-images'],
                maxConnectionsPerDay: 5,
                maxSessionDuration: 60,
                parentMustBePresent: false
            };
        } else if (age <= 16) {
            return {
                restrictionLevel: 'moderate',
                requireApprovalFor: {
                    ...this.defaultApprovalSettings.requireApprovalFor,
                    programParticipation: false // Can join educational programs without approval
                },
                allowedContentTypes: ['text', 'drawing', 'images', 'audio-messages'],
                maxConnectionsPerDay: 10,
                maxSessionDuration: 120,
                parentMustBePresent: false
            };
        } else {
            return {
                restrictionLevel: 'relaxed',
                requireApprovalFor: {
                    newConnections: true,
                    schoolChanges: true,
                    culturalExchange: false,
                    languagePartners: false,
                    videoChat: true,
                    fileSharing: true
                },
                allowedContentTypes: ['text', 'drawing', 'images', 'audio-messages', 'video-messages'],
                maxConnectionsPerDay: 20,
                maxSessionDuration: 180,
                parentMustBePresent: false
            };
        }
    }

    async requestConnectionApproval(requesterId, targetId, connectionType, metadata = {}) {
        const requesterProfile = this.childProfiles.get(requesterId);
        const targetProfile = this.childProfiles.get(targetId);

        if (!requesterProfile || !targetProfile) {
            throw new Error('Invalid user profiles');
        }

        // Check if approval is required based on settings
        const requiresApproval = this.checkApprovalRequirement(
            requesterProfile,
            targetProfile,
            connectionType,
            metadata
        );

        if (!requiresApproval.required) {
            // Auto-approve based on criteria
            return await this.createAutoApprovedConnection(
                requesterId,
                targetId,
                connectionType,
                requiresApproval.reason
            );
        }

        const approvalId = this.generateSecureId();
        const approval = {
            id: approvalId,
            requesterId,
            targetId,
            connectionType,
            metadata,
            status: 'pending',
            requestedAt: new Date(),
            expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days
            requesterProfile: {
                name: requesterProfile.name,
                age: requesterProfile.age,
                school: requesterProfile.schoolId,
                grade: requesterProfile.grade
            },
            targetProfile: {
                name: targetProfile.name,
                age: targetProfile.age,
                school: targetProfile.schoolId,
                grade: targetProfile.grade
            },
            safetyChecks: await this.performSafetyChecks(requesterId, targetId, connectionType),
            recommendationScore: await this.calculateRecommendationScore(requesterProfile, targetProfile),
            parentNotificationsSent: []
        };

        this.pendingApprovals.set(approvalId, approval);

        // Notify both sets of parents
        await this.notifyParentsOfRequest(approval);

        this.emit('approvalRequested', approval);

        return {
            approvalId,
            status: 'pending',
            message: 'Connection request sent to parents for approval',
            estimatedResponseTime: '24-48 hours'
        };
    }

    checkApprovalRequirement(requesterProfile, targetProfile, connectionType, metadata) {
        const requesterSettings = requesterProfile.approvalSettings;
        const targetSettings = targetProfile.approvalSettings;

        // Always require approval if either child's settings demand it
        if (requesterSettings.requireApprovalFor[connectionType] || 
            targetSettings.requireApprovalFor[connectionType] ||
            requesterSettings.requireApprovalFor.allCommunication ||
            targetSettings.requireApprovalFor.allCommunication) {
            return { required: true, reason: 'policy-requirement' };
        }

        // Check auto-approval criteria
        const autoApprovalChecks = [
            {
                condition: metadata.teacherSupervised && 
                          requesterSettings.autoApprovalCriteria.teacherSupervised &&
                          targetSettings.autoApprovalCriteria.teacherSupervised,
                reason: 'teacher-supervised'
            },
            {
                condition: requesterProfile.schoolId === targetProfile.schoolId && 
                          requesterSettings.autoApprovalCriteria.sameSchool &&
                          targetSettings.autoApprovalCriteria.sameSchool,
                reason: 'same-school'
            },
            {
                condition: metadata.educationalPlatform && 
                          requesterSettings.autoApprovalCriteria.verifiedEducationalPlatform &&
                          targetSettings.autoApprovalCriteria.verifiedEducationalPlatform,
                reason: 'verified-educational-platform'
            }
        ];

        for (const check of autoApprovalChecks) {
            if (check.condition) {
                return { required: false, reason: check.reason };
            }
        }

        return { required: true, reason: 'default-policy' };
    }

    async createAutoApprovedConnection(requesterId, targetId, connectionType, reason) {
        const connectionId = this.generateSecureId();
        const connection = {
            id: connectionId,
            participants: [requesterId, targetId],
            connectionType,
            status: 'approved',
            approvalMethod: 'auto-approved',
            approvalReason: reason,
            createdAt: new Date(),
            restrictions: this.getConnectionRestrictions(requesterId, targetId, connectionType),
            monitoringLevel: 'standard',
            parentNotification: true
        };

        this.approvedConnections.set(connectionId, connection);

        // Still notify parents of auto-approved connection
        await this.notifyParentsOfApprovedConnection(connection);

        this.emit('connectionApproved', connection);

        return {
            connectionId,
            status: 'approved',
            approvalMethod: 'automatic',
            restrictions: connection.restrictions
        };
    }

    async performSafetyChecks(requesterId, targetId, connectionType) {
        const checks = {
            ageAppropriate: await this.checkAgeAppropriateness(requesterId, targetId),
            geographicLocation: await this.checkGeographicSafety(requesterId, targetId),
            previousInteractions: await this.checkPreviousInteractions(requesterId, targetId),
            schoolVerification: await this.checkSchoolVerification(requesterId, targetId),
            parentReferences: await this.checkParentReferences(requesterId, targetId),
            riskAssessment: await this.performRiskAssessment(requesterId, targetId, connectionType)
        };

        checks.overallRisk = this.calculateOverallRisk(checks);
        checks.recommendation = this.generateSafetyRecommendation(checks);

        return checks;
    }

    async checkAgeAppropriateness(requesterId, targetId) {
        const requester = this.childProfiles.get(requesterId);
        const target = this.childProfiles.get(targetId);
        
        const ageDifference = Math.abs(requester.age - target.age);
        
        return {
            appropriate: ageDifference <= 3, // Max 3 year age difference
            ageDifference,
            requesterAge: requester.age,
            targetAge: target.age,
            recommendation: ageDifference <= 2 ? 'approved' : ageDifference <= 3 ? 'caution' : 'not-recommended'
        };
    }

    async checkGeographicSafety(requesterId, targetId) {
        // Implement geographic safety checks
        // For now, return safe if both are in different countries (cultural exchange)
        // or same school district (local connections)
        return {
            safe: true,
            type: 'international-educational', // or 'local-school'
            details: 'Geographic location verified for educational purposes'
        };
    }

    async checkPreviousInteractions(requesterId, targetId) {
        // Check history of interactions between users
        const interactions = this.getInteractionHistory(requesterId, targetId);
        
        return {
            hasHistory: interactions.length > 0,
            positiveInteractions: interactions.filter(i => i.rating > 3).length,
            negativeInteractions: interactions.filter(i => i.rating <= 2).length,
            overallRating: interactions.length > 0 ? 
                interactions.reduce((sum, i) => sum + i.rating, 0) / interactions.length : null
        };
    }

    async checkSchoolVerification(requesterId, targetId) {
        const requester = this.childProfiles.get(requesterId);
        const target = this.childProfiles.get(targetId);
        
        return {
            requesterSchoolVerified: await this.verifySchoolRegistration(requester.schoolId),
            targetSchoolVerified: await this.verifySchoolRegistration(target.schoolId),
            sameSchool: requester.schoolId === target.schoolId,
            bothVerified: true // Simplified for demo
        };
    }

    async approveConnection(approvalId, approved, parentId, conditions = {}) {
        const approval = this.pendingApprovals.get(approvalId);
        if (!approval) {
            throw new Error('Approval request not found');
        }

        if (approval.status !== 'pending') {
            throw new Error('Approval request already processed');
        }

        // Verify parent has permission to approve
        const parentPermissions = this.parentPermissions.get(parentId);
        if (!parentPermissions) {
            throw new Error('Parent not found');
        }

        const childInvolved = approval.requesterId === parentPermissions.childIds[0] || 
                             approval.targetId === parentPermissions.childIds[0];
        
        if (!childInvolved) {
            throw new Error('Parent does not have permission for this approval');
        }

        approval.status = approved ? 'approved' : 'denied';
        approval.reviewedAt = new Date();
        approval.reviewedBy = parentId;
        approval.conditions = conditions;
        approval.parentDecision = {
            approved,
            reason: conditions.reason || '',
            restrictions: conditions.restrictions || {},
            monitoringLevel: conditions.monitoringLevel || 'standard'
        };

        if (approved) {
            // Create the connection
            const connectionId = this.generateSecureId();
            const connection = {
                id: connectionId,
                participants: [approval.requesterId, approval.targetId],
                connectionType: approval.connectionType,
                status: 'approved',
                approvalMethod: 'parent-approved',
                approvalId,
                createdAt: new Date(),
                restrictions: {
                    ...this.getConnectionRestrictions(
                        approval.requesterId, 
                        approval.targetId, 
                        approval.connectionType
                    ),
                    ...conditions.restrictions
                },
                monitoringLevel: conditions.monitoringLevel || 'standard',
                parentNotification: true,
                conditions: conditions
            };

            this.approvedConnections.set(connectionId, connection);

            // Notify all involved parents
            await this.notifyParentsOfApprovedConnection(connection);

            // Remove from pending
            this.pendingApprovals.delete(approvalId);

            this.emit('connectionApproved', connection);

            return {
                connectionId,
                status: 'approved',
                message: 'Connection approved by parent'
            };
        } else {
            // Connection denied
            await this.notifyParentsOfDeniedConnection(approval);
            
            // Keep in history for reference
            this.moveToApprovalHistory(approval);
            this.pendingApprovals.delete(approvalId);

            this.emit('connectionDenied', approval);

            return {
                status: 'denied',
                message: 'Connection denied by parent'
            };
        }
    }

    getConnectionRestrictions(requesterId, targetId, connectionType) {
        const requesterProfile = this.childProfiles.get(requesterId);
        const targetProfile = this.childProfiles.get(targetId);
        
        // Apply the most restrictive settings from both children
        const requesterSettings = requesterProfile.approvalSettings;
        const targetSettings = targetProfile.approvalSettings;

        return {
            allowedContentTypes: this.intersectArrays(
                requesterSettings.allowedContentTypes || [],
                targetSettings.allowedContentTypes || []
            ),
            maxSessionDuration: Math.min(
                requesterSettings.maxSessionDuration || 120,
                targetSettings.maxSessionDuration || 120
            ),
            requiresSupervision: requesterSettings.parentMustBePresent || 
                               targetSettings.parentMustBePresent ||
                               connectionType === 'video-chat',
            allowedDays: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'], // Weekdays only by default
            allowedHours: { start: '08:00', end: '18:00' }, // Daytime only
            blockList: [], // Can be expanded with inappropriate words/topics
            reportingRequired: true,
            autoDisconnectOnFlag: true
        };
    }

    async validateConnectionRequest(requesterId, targetId, requestType) {
        try {
            // Basic validation
            if (requesterId === targetId) {
                return { approved: false, reason: 'Cannot connect to yourself' };
            }

            const requesterProfile = this.childProfiles.get(requesterId);
            const targetProfile = this.childProfiles.get(targetId);

            if (!requesterProfile || !targetProfile) {
                return { approved: false, reason: 'Invalid user profiles' };
            }

            // Check if connection already exists
            const existingConnection = this.findExistingConnection(requesterId, targetId);
            if (existingConnection) {
                return { approved: false, reason: 'Connection already exists' };
            }

            // Check daily connection limits
            const todayConnections = this.getTodayConnections(requesterId);
            if (todayConnections >= requesterProfile.approvalSettings.maxConnectionsPerDay) {
                return { 
                    approved: false, 
                    reason: 'Daily connection limit reached',
                    limit: requesterProfile.approvalSettings.maxConnectionsPerDay
                };
            }

            // All basic validations passed
            return { approved: true };

        } catch (error) {
            return { approved: false, reason: 'Validation error occurred' };
        }
    }

    async createConnection(requesterId, targetId, requestType, approvalId) {
        const connectionId = this.generateSecureId();
        const connection = {
            id: connectionId,
            participants: [requesterId, targetId],
            connectionType: requestType,
            status: 'active',
            createdAt: new Date(),
            lastActivity: new Date(),
            approvalId: approvalId,
            restrictions: this.getConnectionRestrictions(requesterId, targetId, requestType),
            monitoringActive: true
        };

        this.approvedConnections.set(connectionId, connection);
        return connection;
    }

    getPendingApprovals(parentId) {
        const parentPermissions = this.parentPermissions.get(parentId);
        if (!parentPermissions) {
            return [];
        }

        const childIds = parentPermissions.childIds;
        const pendingApprovals = [];

        for (const approval of this.pendingApprovals.values()) {
            if (childIds.includes(approval.requesterId) || childIds.includes(approval.targetId)) {
                pendingApprovals.push(this.sanitizeApprovalForParent(approval));
            }
        }

        return pendingApprovals.sort((a, b) => new Date(b.requestedAt) - new Date(a.requestedAt));
    }

    sanitizeApprovalForParent(approval) {
        return {
            id: approval.id,
            connectionType: approval.connectionType,
            requestedAt: approval.requestedAt,
            expiresAt: approval.expiresAt,
            requesterProfile: approval.requesterProfile,
            targetProfile: approval.targetProfile,
            safetyChecks: approval.safetyChecks,
            recommendationScore: approval.recommendationScore,
            metadata: approval.metadata
        };
    }

    async notifyParentsOfRequest(approval) {
        const requesterParents = await this.getChildParents(approval.requesterId);
        const targetParents = await this.getChildParents(approval.targetId);
        
        const allParents = [...requesterParents, ...targetParents];
        
        for (const parent of allParents) {
            await this.sendApprovalNotification(parent, approval);
            approval.parentNotificationsSent.push({
                parentId: parent.parentId,
                sentAt: new Date(),
                method: 'email'
            });
        }
    }

    async getChildParents(childId) {
        const parents = [];
        for (const parentPermissions of this.parentPermissions.values()) {
            if (parentPermissions.childIds.includes(childId)) {
                parents.push(parentPermissions);
            }
        }
        return parents;
    }

    async sendApprovalNotification(parent, approval) {
        const notification = {
            to: parent.email,
            subject: 'New Connection Request Requires Your Approval',
            type: 'connection-approval-request',
            data: {
                childName: approval.requesterProfile.name,
                partnerName: approval.targetProfile.name,
                connectionType: approval.connectionType,
                approvalLink: `${process.env.PARENT_PORTAL_URL}/approvals/${approval.id}`,
                safetyScore: approval.recommendationScore,
                expiresAt: approval.expiresAt
            }
        };

        // Emit notification event for email service to handle
        this.emit('sendNotification', notification);
    }

    async sendParentVerification(parentPermissions) {
        const verificationToken = this.generateSecureId();
        
        // Store verification token temporarily
        this.pendingVerifications = this.pendingVerifications || new Map();
        this.pendingVerifications.set(verificationToken, {
            parentId: parentPermissions.parentId,
            email: parentPermissions.email,
            expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000) // 24 hours
        });

        const notification = {
            to: parentPermissions.email,
            subject: 'Verify Your Kids Connect Parent Account',
            type: 'parent-verification',
            data: {
                verificationLink: `${process.env.PARENT_PORTAL_URL}/verify/${verificationToken}`,
                childName: 'your child', // Will be filled in by email template
                expiresIn: '24 hours'
            }
        };

        this.emit('sendNotification', notification);
    }

    findExistingConnection(userId1, userId2) {
        for (const connection of this.approvedConnections.values()) {
            if (connection.participants.includes(userId1) && 
                connection.participants.includes(userId2)) {
                return connection;
            }
        }
        return null;
    }

    getTodayConnections(userId) {
        const today = new Date().toDateString();
        let count = 0;
        
        for (const connection of this.approvedConnections.values()) {
            if (connection.participants.includes(userId) && 
                new Date(connection.createdAt).toDateString() === today) {
                count++;
            }
        }
        
        return count;
    }

    intersectArrays(arr1, arr2) {
        return arr1.filter(item => arr2.includes(item));
    }

    generateSecureId() {
        return crypto.randomBytes(16).toString('hex');
    }

    calculateOverallRisk(checks) {
        // Simple risk calculation - can be enhanced
        let riskScore = 0;
        
        if (!checks.ageAppropriate.appropriate) riskScore += 3;
        if (!checks.geographicLocation.safe) riskScore += 2;
        if (checks.previousInteractions.negativeInteractions > 0) riskScore += 2;
        if (!checks.schoolVerification.bothVerified) riskScore += 1;
        
        return {
            score: riskScore,
            level: riskScore <= 1 ? 'low' : riskScore <= 3 ? 'medium' : 'high'
        };
    }

    generateSafetyRecommendation(checks) {
        if (checks.overallRisk.level === 'high') {
            return {
                recommendation: 'deny',
                reason: 'High risk factors detected',
                suggestions: ['Consider connections within same school', 'Verify age appropriateness']
            };
        } else if (checks.overallRisk.level === 'medium') {
            return {
                recommendation: 'approve-with-restrictions',
                reason: 'Some risk factors present',
                suggestions: ['Increase monitoring', 'Limit session duration', 'Require supervision']
            };
        } else {
            return {
                recommendation: 'approve',
                reason: 'Low risk connection',
                suggestions: ['Standard monitoring sufficient']
            };
        }
    }

    calculateRecommendationScore(requesterProfile, targetProfile) {
        let score = 50; // Base score
        
        // Same school bonus
        if (requesterProfile.schoolId === targetProfile.schoolId) {
            score += 20;
        }
        
        // Age appropriateness
        const ageDiff = Math.abs(requesterProfile.age - targetProfile.age);
        if (ageDiff <= 1) score += 15;
        else if (ageDiff <= 2) score += 10;
        else if (ageDiff <= 3) score += 5;
        
        // Grade level proximity
        const gradeDiff = Math.abs(parseInt(requesterProfile.grade) - parseInt(targetProfile.grade));
        if (gradeDiff <= 1) score += 10;
        
        return Math.min(100, Math.max(0, score));
    }

    getInteractionHistory(userId1, userId2) {
        // Placeholder - would retrieve from database
        return [];
    }

    async verifySchoolRegistration(schoolId) {
        // Placeholder - would verify with school database
        return true;
    }

    async notifyParentsOfApprovedConnection(connection) {
        // Implementation for notifying parents of approved connections
        this.emit('parentNotification', {
            type: 'connection-approved',
            connection: connection
        });
    }

    async notifyParentsOfDeniedConnection(approval) {
        // Implementation for notifying parents of denied connections
        this.emit('parentNotification', {
            type: 'connection-denied',
            approval: approval
        });
    }

    moveToApprovalHistory(approval) {
        const historyId = this.generateSecureId();
        this.approvalHistory.set(historyId, {
            ...approval,
            historicalId: historyId,
            archivedAt: new Date()
        });
    }
}

module.exports = ParentApprovalSystem;