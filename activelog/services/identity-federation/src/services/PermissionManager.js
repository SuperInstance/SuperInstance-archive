const EventEmitter = require('events');
const Permission = require('../models/Permission');
const Role = require('../models/Role');
const User = require('../models/User');
const Organization = require('../models/Organization');
const AuditLogger = require('./AuditLogger');

class PermissionManager extends EventEmitter {
  constructor(config = {}) {
    super();
    this.config = {
      permissionCacheTimeout: config.permissionCacheTimeout || 300000, // 5 minutes
      hierarchyDepthLimit: config.hierarchyDepthLimit || 10,
      ...config
    };
    
    this.auditLogger = new AuditLogger();
    this.permissionCache = new Map();
    this.roleCache = new Map();
    
    // Built-in system permissions
    this.systemPermissions = {
      // User management
      'users:read': 'Read user information',
      'users:write': 'Create and update users',
      'users:delete': 'Delete users',
      'users:impersonate': 'Impersonate other users',
      
      // Organization management
      'organizations:read': 'Read organization information',
      'organizations:write': 'Create and update organizations',
      'organizations:delete': 'Delete organizations',
      'organizations:admin': 'Full organization administration',
      
      // Permission management
      'permissions:read': 'Read permissions and roles',
      'permissions:write': 'Create and update permissions and roles',
      'permissions:assign': 'Assign permissions to users and roles',
      
      // System administration
      'system:admin': 'System-wide administrative access',
      'system:audit': 'Access audit logs and system monitoring',
      'system:config': 'Modify system configuration',
      
      // Data access
      'data:read': 'Read data',
      'data:write': 'Create and update data',
      'data:delete': 'Delete data',
      'data:export': 'Export data',
      
      // Identity federation
      'federation:admin': 'Manage identity federation',
      'federation:read': 'Read federation settings',
      'federation:write': 'Configure federation providers',
      
      // Privacy and compliance
      'privacy:admin': 'Manage privacy settings',
      'privacy:read': 'Read privacy data',
      'privacy:export': 'Export user data',
      'privacy:delete': 'Delete user data',
      
      // Emergency access
      'emergency:access': 'Emergency system access',
      'emergency:override': 'Override security controls'
    };
    
    this.initializeSystemRoles();
  }

  async initializeSystemRoles() {
    const systemRoles = [
      {
        name: 'super_admin',
        displayName: 'Super Administrator',
        description: 'Full system access',
        permissions: Object.keys(this.systemPermissions),
        isSystem: true,
        level: 100
      },
      {
        name: 'organization_admin',
        displayName: 'Organization Administrator',
        description: 'Organization-level administrative access',
        permissions: [
          'users:read', 'users:write', 'users:delete',
          'organizations:read', 'organizations:write',
          'permissions:read', 'permissions:assign',
          'data:read', 'data:write', 'data:delete', 'data:export'
        ],
        isSystem: true,
        level: 80
      },
      {
        name: 'user_manager',
        displayName: 'User Manager',
        description: 'User management within organization',
        permissions: [
          'users:read', 'users:write',
          'organizations:read',
          'permissions:read'
        ],
        isSystem: true,
        level: 60
      },
      {
        name: 'standard_user',
        displayName: 'Standard User',
        description: 'Standard user access',
        permissions: [
          'data:read', 'data:write'
        ],
        isSystem: true,
        level: 40
      },
      {
        name: 'read_only',
        displayName: 'Read Only User',
        description: 'Read-only access',
        permissions: [
          'data:read'
        ],
        isSystem: true,
        level: 20
      }
    ];

    for (const roleData of systemRoles) {
      try {
        await Role.findOneAndUpdate(
          { name: roleData.name, isSystem: true },
          roleData,
          { upsert: true, new: true }
        );
      } catch (error) {
        console.error(`Error creating system role ${roleData.name}:`, error);
      }
    }
  }

  async checkPermission(userId, permission, context = {}) {
    try {
      const cacheKey = `${userId}:${permission}:${JSON.stringify(context)}`;
      const cached = this.permissionCache.get(cacheKey);
      
      if (cached && cached.expires > Date.now()) {
        return cached.hasPermission;
      }

      const user = await User.findById(userId).populate('organizations');
      if (!user || !user.isActive) {
        return false;
      }

      let hasPermission = false;

      // Check direct user permissions
      if (user.permissions && user.permissions.includes(permission)) {
        hasPermission = true;
      }

      // Check user roles
      if (!hasPermission && user.roles) {
        for (const roleId of user.roles) {
          const role = await this.getRole(roleId);
          if (role && role.permissions.includes(permission)) {
            hasPermission = true;
            break;
          }
        }
      }

      // Check organization-specific permissions
      if (!hasPermission && context.organizationId) {
        const org = await Organization.findById(context.organizationId);
        if (org) {
          const member = org.members.find(m => m.user.toString() === userId);
          if (member) {
            // Check direct organization permissions
            if (member.permissions && member.permissions.includes(permission)) {
              hasPermission = true;
            }
            
            // Check organization roles
            if (!hasPermission && member.roles) {
              for (const roleId of member.roles) {
                const role = await this.getRole(roleId);
                if (role && role.permissions.includes(permission)) {
                  hasPermission = true;
                  break;
                }
              }
            }
          }
        }
      }

      // Check permission inheritance
      if (!hasPermission) {
        hasPermission = await this.checkPermissionInheritance(userId, permission, context);
      }

      // Cache result
      this.permissionCache.set(cacheKey, {
        hasPermission,
        expires: Date.now() + this.config.permissionCacheTimeout
      });

      // Log permission check for audit
      await this.auditLogger.log('permission_check', hasPermission ? 'granted' : 'denied', {
        userId,
        permission,
        context,
        result: hasPermission
      });

      return hasPermission;
    } catch (error) {
      console.error('Permission check error:', error);
      return false;
    }
  }

  async checkPermissionInheritance(userId, permission, context, depth = 0) {
    if (depth >= this.config.hierarchyDepthLimit) {
      return false;
    }

    // Check if permission implies other permissions
    const permissionHierarchy = {
      'system:admin': Object.keys(this.systemPermissions),
      'organizations:admin': [
        'users:read', 'users:write', 'users:delete',
        'organizations:read', 'organizations:write',
        'data:read', 'data:write', 'data:delete'
      ],
      'users:write': ['users:read'],
      'data:write': ['data:read'],
      'permissions:write': ['permissions:read']
    };

    for (const [parentPermission, childPermissions] of Object.entries(permissionHierarchy)) {
      if (childPermissions.includes(permission)) {
        const hasParentPermission = await this.checkPermission(userId, parentPermission, context);
        if (hasParentPermission) {
          return true;
        }
      }
    }

    return false;
  }

  async grantPermission(userId, permission, context = {}, grantedBy) {
    try {
      const user = await User.findById(userId);
      if (!user) {
        throw new Error('User not found');
      }

      if (context.organizationId) {
        // Grant organization-specific permission
        const org = await Organization.findById(context.organizationId);
        if (!org) {
          throw new Error('Organization not found');
        }

        const memberIndex = org.members.findIndex(m => m.user.toString() === userId);
        if (memberIndex === -1) {
          throw new Error('User is not a member of this organization');
        }

        if (!org.members[memberIndex].permissions) {
          org.members[memberIndex].permissions = [];
        }

        if (!org.members[memberIndex].permissions.includes(permission)) {
          org.members[memberIndex].permissions.push(permission);
          await org.save();
        }
      } else {
        // Grant global permission
        if (!user.permissions) {
          user.permissions = [];
        }

        if (!user.permissions.includes(permission)) {
          user.permissions.push(permission);
          await user.save();
        }
      }

      // Clear cache for this user
      this.clearUserPermissionCache(userId);

      await this.auditLogger.log('permission_granted', 'success', {
        userId,
        permission,
        context,
        grantedBy
      });

      this.emit('permission_granted', { userId, permission, context, grantedBy });
      
      return true;
    } catch (error) {
      await this.auditLogger.log('permission_granted', 'failed', {
        userId,
        permission,
        context,
        grantedBy,
        error: error.message
      });
      throw error;
    }
  }

  async revokePermission(userId, permission, context = {}, revokedBy) {
    try {
      if (context.organizationId) {
        const org = await Organization.findById(context.organizationId);
        if (org) {
          const memberIndex = org.members.findIndex(m => m.user.toString() === userId);
          if (memberIndex !== -1 && org.members[memberIndex].permissions) {
            const permIndex = org.members[memberIndex].permissions.indexOf(permission);
            if (permIndex !== -1) {
              org.members[memberIndex].permissions.splice(permIndex, 1);
              await org.save();
            }
          }
        }
      } else {
        const user = await User.findById(userId);
        if (user && user.permissions) {
          const permIndex = user.permissions.indexOf(permission);
          if (permIndex !== -1) {
            user.permissions.splice(permIndex, 1);
            await user.save();
          }
        }
      }

      this.clearUserPermissionCache(userId);

      await this.auditLogger.log('permission_revoked', 'success', {
        userId,
        permission,
        context,
        revokedBy
      });

      this.emit('permission_revoked', { userId, permission, context, revokedBy });
      
      return true;
    } catch (error) {
      await this.auditLogger.log('permission_revoked', 'failed', {
        userId,
        permission,
        context,
        revokedBy,
        error: error.message
      });
      throw error;
    }
  }

  async createRole(roleData, createdBy) {
    try {
      const role = new Role({
        ...roleData,
        createdBy,
        createdAt: new Date()
      });

      await role.save();

      await this.auditLogger.log('role_created', 'success', {
        roleId: role._id,
        roleName: role.name,
        permissions: role.permissions,
        createdBy
      });

      this.emit('role_created', { role, createdBy });
      
      return role;
    } catch (error) {
      await this.auditLogger.log('role_created', 'failed', {
        roleData,
        createdBy,
        error: error.message
      });
      throw error;
    }
  }

  async assignRole(userId, roleId, context = {}, assignedBy) {
    try {
      const user = await User.findById(userId);
      const role = await Role.findById(roleId);

      if (!user || !role) {
        throw new Error('User or role not found');
      }

      if (context.organizationId) {
        const org = await Organization.findById(context.organizationId);
        if (!org) {
          throw new Error('Organization not found');
        }

        const memberIndex = org.members.findIndex(m => m.user.toString() === userId);
        if (memberIndex === -1) {
          throw new Error('User is not a member of this organization');
        }

        if (!org.members[memberIndex].roles) {
          org.members[memberIndex].roles = [];
        }

        if (!org.members[memberIndex].roles.includes(roleId)) {
          org.members[memberIndex].roles.push(roleId);
          await org.save();
        }
      } else {
        if (!user.roles) {
          user.roles = [];
        }

        if (!user.roles.includes(roleId)) {
          user.roles.push(roleId);
          await user.save();
        }
      }

      this.clearUserPermissionCache(userId);

      await this.auditLogger.log('role_assigned', 'success', {
        userId,
        roleId,
        roleName: role.name,
        context,
        assignedBy
      });

      this.emit('role_assigned', { userId, roleId, role, context, assignedBy });
      
      return true;
    } catch (error) {
      await this.auditLogger.log('role_assigned', 'failed', {
        userId,
        roleId,
        context,
        assignedBy,
        error: error.message
      });
      throw error;
    }
  }

  async getRole(roleId) {
    const cached = this.roleCache.get(roleId);
    if (cached && cached.expires > Date.now()) {
      return cached.role;
    }

    const role = await Role.findById(roleId);
    if (role) {
      this.roleCache.set(roleId, {
        role,
        expires: Date.now() + this.config.permissionCacheTimeout
      });
    }

    return role;
  }

  async getUserEffectivePermissions(userId, context = {}) {
    const user = await User.findById(userId).populate('organizations');
    if (!user) {
      return [];
    }

    const permissions = new Set();

    // Add direct user permissions
    if (user.permissions) {
      user.permissions.forEach(perm => permissions.add(perm));
    }

    // Add role-based permissions
    if (user.roles) {
      for (const roleId of user.roles) {
        const role = await this.getRole(roleId);
        if (role && role.permissions) {
          role.permissions.forEach(perm => permissions.add(perm));
        }
      }
    }

    // Add organization-specific permissions
    if (context.organizationId) {
      const org = await Organization.findById(context.organizationId);
      if (org) {
        const member = org.members.find(m => m.user.toString() === userId);
        if (member) {
          if (member.permissions) {
            member.permissions.forEach(perm => permissions.add(perm));
          }
          
          if (member.roles) {
            for (const roleId of member.roles) {
              const role = await this.getRole(roleId);
              if (role && role.permissions) {
                role.permissions.forEach(perm => permissions.add(perm));
              }
            }
          }
        }
      }
    }

    return Array.from(permissions);
  }

  async createPermissionBoundary(userId, permissions, context = {}) {
    try {
      const boundary = {
        userId,
        permissions,
        context,
        createdAt: new Date(),
        isActive: true
      };

      // Store boundary (could be in database or cache)
      const boundaryId = require('uuid').v4();
      await this.storeBoundary(boundaryId, boundary);

      await this.auditLogger.log('permission_boundary_created', 'success', {
        boundaryId,
        userId,
        permissions,
        context
      });

      return boundaryId;
    } catch (error) {
      await this.auditLogger.log('permission_boundary_created', 'failed', {
        userId,
        permissions,
        context,
        error: error.message
      });
      throw error;
    }
  }

  async storeBoundary(boundaryId, boundary) {
    // Implementation would store in database or distributed cache
    // For now, storing in memory (would need persistence in production)
    if (!this.boundaries) {
      this.boundaries = new Map();
    }
    this.boundaries.set(boundaryId, boundary);
  }

  clearUserPermissionCache(userId) {
    for (const [key] of this.permissionCache.entries()) {
      if (key.startsWith(`${userId}:`)) {
        this.permissionCache.delete(key);
      }
    }
  }

  clearAllCaches() {
    this.permissionCache.clear();
    this.roleCache.clear();
  }

  async validatePermissionStructure(permissions) {
    const validPermissions = Object.keys(this.systemPermissions);
    const invalidPermissions = permissions.filter(perm => !validPermissions.includes(perm));
    
    if (invalidPermissions.length > 0) {
      throw new Error(`Invalid permissions: ${invalidPermissions.join(', ')}`);
    }
    
    return true;
  }
}

module.exports = PermissionManager;