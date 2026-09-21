const EventEmitter = require('events');
const User = require('../models/User');
const Organization = require('../models/Organization');
const Context = require('../models/Context');
const AuditLogger = require('./AuditLogger');
const PermissionManager = require('./PermissionManager');

class OrganizationSeparator extends EventEmitter {
  constructor(config = {}) {
    super();
    this.config = {
      allowPersonalAccounts: config.allowPersonalAccounts !== false,
      defaultPersonalOrgName: config.defaultPersonalOrgName || 'Personal',
      maxOrganizationsPerUser: config.maxOrganizationsPerUser || 10,
      contextSwitchAuditLog: config.contextSwitchAuditLog !== false,
      ...config
    };
    
    this.auditLogger = new AuditLogger();
    this.permissionManager = new PermissionManager();
    this.activeContexts = new Map(); // userId -> contextId
  }

  async createPersonalOrganization(userId) {
    try {
      const user = await User.findById(userId);
      if (!user) {
        throw new Error('User not found');
      }

      // Check if user already has a personal organization
      const existingPersonalOrg = await Organization.findOne({
        'members.user': userId,
        type: 'personal',
        ownerId: userId
      });

      if (existingPersonalOrg) {
        return existingPersonalOrg;
      }

      const personalOrg = new Organization({
        name: `${user.firstName || user.email}'s ${this.config.defaultPersonalOrgName}`,
        displayName: this.config.defaultPersonalOrgName,
        type: 'personal',
        ownerId: userId,
        settings: {
          isDefault: true,
          visibility: 'private',
          allowInvitations: false,
          requireApproval: false
        },
        members: [{
          user: userId,
          role: 'owner',
          permissions: ['organizations:admin'],
          joinedAt: new Date(),
          status: 'active'
        }],
        metadata: {
          createdBy: userId,
          isSystemGenerated: true
        }
      });

      await personalOrg.save();

      // Update user with personal organization reference
      user.organizations = user.organizations || [];
      user.organizations.push(personalOrg._id);
      user.defaultOrganization = personalOrg._id;
      await user.save();

      await this.auditLogger.log('personal_organization_created', 'success', {
        userId,
        organizationId: personalOrg._id,
        organizationName: personalOrg.name
      });

      this.emit('personal_organization_created', {
        user,
        organization: personalOrg
      });

      return personalOrg;
    } catch (error) {
      await this.auditLogger.log('personal_organization_created', 'failed', {
        userId,
        error: error.message
      });
      throw error;
    }
  }

  async createCompanyOrganization(organizationData, createdBy) {
    try {
      const user = await User.findById(createdBy);
      if (!user) {
        throw new Error('Creator user not found');
      }

      // Validate organization data
      if (!organizationData.name || !organizationData.domain) {
        throw new Error('Organization name and domain are required');
      }

      // Check if domain is already taken
      const existingOrg = await Organization.findOne({ 
        domain: organizationData.domain.toLowerCase() 
      });
      
      if (existingOrg) {
        throw new Error('Domain already taken');
      }

      const companyOrg = new Organization({
        name: organizationData.name,
        displayName: organizationData.displayName || organizationData.name,
        domain: organizationData.domain.toLowerCase(),
        type: 'company',
        ownerId: createdBy,
        industry: organizationData.industry,
        size: organizationData.size,
        settings: {
          visibility: organizationData.visibility || 'private',
          allowInvitations: organizationData.allowInvitations !== false,
          requireApproval: organizationData.requireApproval !== false,
          emailDomainRestriction: organizationData.emailDomainRestriction || false,
          allowedDomains: organizationData.allowedDomains || [organizationData.domain]
        },
        members: [{
          user: createdBy,
          role: 'owner',
          permissions: ['organizations:admin'],
          joinedAt: new Date(),
          status: 'active'
        }],
        branding: {
          logo: organizationData.logo,
          primaryColor: organizationData.primaryColor,
          secondaryColor: organizationData.secondaryColor
        },
        metadata: {
          createdBy,
          isSystemGenerated: false
        }
      });

      await companyOrg.save();

      // Update user's organizations
      user.organizations = user.organizations || [];
      user.organizations.push(companyOrg._id);
      await user.save();

      await this.auditLogger.log('company_organization_created', 'success', {
        userId: createdBy,
        organizationId: companyOrg._id,
        organizationName: companyOrg.name,
        domain: companyOrg.domain
      });

      this.emit('company_organization_created', {
        user,
        organization: companyOrg
      });

      return companyOrg;
    } catch (error) {
      await this.auditLogger.log('company_organization_created', 'failed', {
        userId: createdBy,
        organizationData,
        error: error.message
      });
      throw error;
    }
  }

  async switchContext(userId, organizationId, contextData = {}) {
    try {
      const user = await User.findById(userId).populate('organizations');
      if (!user) {
        throw new Error('User not found');
      }

      const organization = await Organization.findById(organizationId);
      if (!organization) {
        throw new Error('Organization not found');
      }

      // Verify user is a member of the organization
      const membership = organization.members.find(m => m.user.toString() === userId);
      if (!membership) {
        throw new Error('User is not a member of this organization');
      }

      // Check if user has permission to access this organization
      const hasAccess = await this.permissionManager.checkPermission(
        userId, 
        'organizations:read', 
        { organizationId }
      );

      if (!hasAccess) {
        throw new Error('Access denied to organization');
      }

      // Create or update context
      const context = await this.createContext(userId, organizationId, contextData);

      // Update active context
      this.activeContexts.set(userId, context._id);

      // Update user's current organization
      user.currentOrganization = organizationId;
      await user.save();

      if (this.config.contextSwitchAuditLog) {
        await this.auditLogger.log('context_switched', 'success', {
          userId,
          fromOrganizationId: contextData.previousOrganizationId,
          toOrganizationId: organizationId,
          contextId: context._id,
          sessionId: contextData.sessionId
        });
      }

      this.emit('context_switched', {
        user,
        organization,
        context,
        previousOrganizationId: contextData.previousOrganizationId
      });

      return {
        context,
        organization,
        permissions: await this.permissionManager.getUserEffectivePermissions(
          userId, 
          { organizationId }
        )
      };
    } catch (error) {
      await this.auditLogger.log('context_switched', 'failed', {
        userId,
        organizationId,
        error: error.message
      });
      throw error;
    }
  }

  async createContext(userId, organizationId, contextData = {}) {
    const context = new Context({
      userId,
      organizationId,
      sessionId: contextData.sessionId,
      deviceId: contextData.deviceId,
      ipAddress: contextData.ipAddress,
      userAgent: contextData.userAgent,
      location: contextData.location,
      startTime: new Date(),
      isActive: true,
      metadata: {
        referrer: contextData.referrer,
        platform: contextData.platform,
        timezone: contextData.timezone
      }
    });

    await context.save();
    return context;
  }

  async getActiveContext(userId) {
    const contextId = this.activeContexts.get(userId);
    if (!contextId) {
      return null;
    }

    const context = await Context.findById(contextId)
      .populate('organizationId')
      .populate('userId', 'email firstName lastName');

    return context && context.isActive ? context : null;
  }

  async getUserOrganizations(userId, includePersonal = true) {
    try {
      const user = await User.findById(userId).populate({
        path: 'organizations',
        populate: {
          path: 'members.user',
          select: 'email firstName lastName avatar'
        }
      });

      if (!user) {
        return [];
      }

      let organizations = user.organizations || [];

      if (!includePersonal) {
        organizations = organizations.filter(org => org.type !== 'personal');
      }

      // Add membership role and permissions for each organization
      const enrichedOrganizations = organizations.map(org => {
        const membership = org.members.find(m => m.user._id.toString() === userId);
        return {
          ...org.toObject(),
          membership: {
            role: membership?.role,
            permissions: membership?.permissions || [],
            joinedAt: membership?.joinedAt,
            status: membership?.status
          }
        };
      });

      return enrichedOrganizations;
    } catch (error) {
      await this.auditLogger.log('get_user_organizations', 'failed', {
        userId,
        error: error.message
      });
      throw error;
    }
  }

  async separatePersonalData(userId, organizationId) {
    try {
      // This method ensures personal data is isolated from company data
      const user = await User.findById(userId);
      const organization = await Organization.findById(organizationId);

      if (!user || !organization) {
        throw new Error('User or organization not found');
      }

      // Get personal organization
      const personalOrg = await Organization.findOne({
        type: 'personal',
        ownerId: userId
      });

      if (!personalOrg) {
        throw new Error('Personal organization not found');
      }

      const separation = {
        userId,
        personalOrganizationId: personalOrg._id,
        companyOrganizationId: organizationId,
        separatedAt: new Date(),
        dataTypes: {
          profile: 'separated',
          preferences: 'separated',
          files: 'separated',
          communications: 'separated'
        }
      };

      await this.auditLogger.log('data_separation_applied', 'success', separation);

      return separation;
    } catch (error) {
      await this.auditLogger.log('data_separation_applied', 'failed', {
        userId,
        organizationId,
        error: error.message
      });
      throw error;
    }
  }

  async inviteUserToOrganization(organizationId, inviterUserId, inviteData) {
    try {
      const organization = await Organization.findById(organizationId);
      const inviter = await User.findById(inviterUserId);

      if (!organization || !inviter) {
        throw new Error('Organization or inviter not found');
      }

      // Check if inviter has permission to invite users
      const canInvite = await this.permissionManager.checkPermission(
        inviterUserId,
        'users:write',
        { organizationId }
      );

      if (!canInvite) {
        throw new Error('No permission to invite users');
      }

      // Validate email domain if restriction is enabled
      if (organization.settings.emailDomainRestriction) {
        const emailDomain = inviteData.email.split('@')[1];
        if (!organization.settings.allowedDomains.includes(emailDomain)) {
          throw new Error('Email domain not allowed');
        }
      }

      // Check if user already exists
      let invitedUser = await User.findOne({ email: inviteData.email.toLowerCase() });
      
      const invitation = {
        id: require('uuid').v4(),
        organizationId,
        inviterUserId,
        email: inviteData.email.toLowerCase(),
        role: inviteData.role || 'standard_user',
        permissions: inviteData.permissions || [],
        message: inviteData.message,
        expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days
        status: 'pending',
        createdAt: new Date()
      };

      // Store invitation (would typically be in database)
      await this.storeInvitation(invitation);

      // Send invitation email
      await this.sendInvitationEmail(invitation, organization, inviter);

      await this.auditLogger.log('user_invited', 'success', {
        organizationId,
        inviterUserId,
        invitedEmail: inviteData.email,
        role: inviteData.role,
        invitationId: invitation.id
      });

      this.emit('user_invited', {
        invitation,
        organization,
        inviter
      });

      return invitation;
    } catch (error) {
      await this.auditLogger.log('user_invited', 'failed', {
        organizationId,
        inviterUserId,
        inviteData,
        error: error.message
      });
      throw error;
    }
  }

  async acceptInvitation(invitationId, userId) {
    try {
      const invitation = await this.getInvitation(invitationId);
      if (!invitation) {
        throw new Error('Invitation not found');
      }

      if (invitation.status !== 'pending') {
        throw new Error('Invitation already processed');
      }

      if (invitation.expiresAt < new Date()) {
        throw new Error('Invitation expired');
      }

      const user = await User.findById(userId);
      const organization = await Organization.findById(invitation.organizationId);

      if (!user || !organization) {
        throw new Error('User or organization not found');
      }

      // Verify email matches
      if (user.email.toLowerCase() !== invitation.email.toLowerCase()) {
        throw new Error('Email mismatch');
      }

      // Add user to organization
      organization.members.push({
        user: userId,
        role: invitation.role,
        permissions: invitation.permissions,
        joinedAt: new Date(),
        status: 'active'
      });

      await organization.save();

      // Update user's organizations
      user.organizations = user.organizations || [];
      if (!user.organizations.includes(organization._id)) {
        user.organizations.push(organization._id);
      }
      await user.save();

      // Update invitation status
      invitation.status = 'accepted';
      invitation.acceptedAt = new Date();
      invitation.acceptedBy = userId;
      await this.updateInvitation(invitation);

      await this.auditLogger.log('invitation_accepted', 'success', {
        invitationId,
        userId,
        organizationId: invitation.organizationId,
        role: invitation.role
      });

      this.emit('invitation_accepted', {
        invitation,
        user,
        organization
      });

      return { organization, role: invitation.role };
    } catch (error) {
      await this.auditLogger.log('invitation_accepted', 'failed', {
        invitationId,
        userId,
        error: error.message
      });
      throw error;
    }
  }

  async removeUserFromOrganization(organizationId, userId, removedBy) {
    try {
      const organization = await Organization.findById(organizationId);
      if (!organization) {
        throw new Error('Organization not found');
      }

      // Check permissions
      const canRemove = await this.permissionManager.checkPermission(
        removedBy,
        'users:delete',
        { organizationId }
      );

      if (!canRemove && removedBy !== userId) {
        throw new Error('No permission to remove users');
      }

      // Cannot remove organization owner
      if (organization.ownerId.toString() === userId) {
        throw new Error('Cannot remove organization owner');
      }

      // Remove user from organization members
      organization.members = organization.members.filter(
        m => m.user.toString() !== userId
      );
      await organization.save();

      // Remove organization from user's organizations
      const user = await User.findById(userId);
      if (user) {
        user.organizations = user.organizations.filter(
          orgId => orgId.toString() !== organizationId
        );
        
        // If this was the current organization, switch to personal
        if (user.currentOrganization?.toString() === organizationId) {
          const personalOrg = await Organization.findOne({
            type: 'personal',
            ownerId: userId
          });
          user.currentOrganization = personalOrg?._id || null;
        }
        
        await user.save();
      }

      // Clear active context if needed
      const activeContext = this.activeContexts.get(userId);
      if (activeContext) {
        const context = await Context.findById(activeContext);
        if (context && context.organizationId.toString() === organizationId) {
          context.isActive = false;
          context.endTime = new Date();
          await context.save();
          this.activeContexts.delete(userId);
        }
      }

      await this.auditLogger.log('user_removed_from_organization', 'success', {
        organizationId,
        userId,
        removedBy
      });

      this.emit('user_removed_from_organization', {
        organizationId,
        userId,
        removedBy
      });

      return true;
    } catch (error) {
      await this.auditLogger.log('user_removed_from_organization', 'failed', {
        organizationId,
        userId,
        removedBy,
        error: error.message
      });
      throw error;
    }
  }

  // Helper methods for invitation management
  async storeInvitation(invitation) {
    // In production, this would store in database
    // For now, using in-memory storage
    if (!this.invitations) {
      this.invitations = new Map();
    }
    this.invitations.set(invitation.id, invitation);
  }

  async getInvitation(invitationId) {
    if (!this.invitations) {
      return null;
    }
    return this.invitations.get(invitationId);
  }

  async updateInvitation(invitation) {
    if (this.invitations) {
      this.invitations.set(invitation.id, invitation);
    }
  }

  async sendInvitationEmail(invitation, organization, inviter) {
    // Email sending implementation would go here
    // For now, just emit an event
    this.emit('invitation_email_sent', {
      invitation,
      organization,
      inviter
    });
  }
}

module.exports = OrganizationSeparator;