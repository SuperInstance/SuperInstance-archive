const { EventEmitter } = require('events');

class RBACManager extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = {
      enableInheritance: options.enableInheritance !== false,
      enableDynamicRoles: options.enableDynamicRoles !== false,
      maxRoleDepth: options.maxRoleDepth || 10,
      cacheTimeout: options.cacheTimeout || 300000, // 5 minutes
      ...options
    };
    
    this.roles = new Map();
    this.permissions = new Map();
    this.userRoles = new Map();
    this.roleHierarchy = new Map();
    this.resourcePermissions = new Map();
    this.contextualRules = new Map();
    this.permissionCache = new Map();
    
    this.initializeDefaultRoles();
    this.setupCacheCleanup();
  }

  // Permission Management
  createPermission(permissionData) {
    const permission = {
      id: permissionData.id,
      name: permissionData.name,
      description: permissionData.description,
      resource: permissionData.resource,
      action: permissionData.action,
      
      // Permission attributes
      attributes: permissionData.attributes || {},
      conditions: permissionData.conditions || [],
      
      // Scope and context
      scope: permissionData.scope || 'global',
      context: permissionData.context || {},
      
      // Metadata
      createdAt: new Date(),
      updatedAt: new Date(),
      isActive: true
    };
    
    this.permissions.set(permission.id, permission);
    this.clearPermissionCache();
    this.emit('permissionCreated', permission);
    return permission;
  }

  updatePermission(permissionId, updates) {
    const permission = this.permissions.get(permissionId);
    if (!permission) {
      throw new Error(`Permission ${permissionId} not found`);
    }
    
    const updatedPermission = {
      ...permission,
      ...updates,
      updatedAt: new Date()
    };
    
    this.permissions.set(permissionId, updatedPermission);
    this.clearPermissionCache();
    this.emit('permissionUpdated', updatedPermission);
    return updatedPermission;
  }

  deletePermission(permissionId) {
    const permission = this.permissions.get(permissionId);
    if (!permission) {
      throw new Error(`Permission ${permissionId} not found`);
    }
    
    // Remove permission from all roles
    for (const role of this.roles.values()) {
      if (role.permissions.includes(permissionId)) {
        role.permissions = role.permissions.filter(p => p !== permissionId);
        this.roles.set(role.id, role);
      }
    }
    
    this.permissions.delete(permissionId);
    this.clearPermissionCache();
    this.emit('permissionDeleted', permission);
    return true;
  }

  getPermission(permissionId) {
    return this.permissions.get(permissionId);
  }

  getPermissions(filters = {}) {
    let permissions = Array.from(this.permissions.values());
    
    if (filters.resource) {
      permissions = permissions.filter(p => p.resource === filters.resource);
    }
    
    if (filters.action) {
      permissions = permissions.filter(p => p.action === filters.action);
    }
    
    if (filters.scope) {
      permissions = permissions.filter(p => p.scope === filters.scope);
    }
    
    return permissions;
  }

  // Role Management
  createRole(roleData) {
    const role = {
      id: roleData.id,
      name: roleData.name,
      description: roleData.description,
      
      // Role permissions
      permissions: roleData.permissions || [],
      
      // Role inheritance
      inherits: roleData.inherits || [],
      
      // Role attributes
      attributes: roleData.attributes || {},
      
      // Scope and context
      scope: roleData.scope || 'global',
      context: roleData.context || {},
      
      // Role constraints
      constraints: {
        maxUsers: roleData.constraints?.maxUsers,
        expiresAt: roleData.constraints?.expiresAt,
        conditions: roleData.constraints?.conditions || []
      },
      
      // Dynamic role settings
      isDynamic: roleData.isDynamic || false,
      dynamicRules: roleData.dynamicRules || [],
      
      // Metadata
      createdAt: new Date(),
      updatedAt: new Date(),
      isActive: true
    };
    
    // Validate role hierarchy
    if (role.inherits.length > 0) {
      this.validateRoleHierarchy(role.id, role.inherits);
    }
    
    this.roles.set(role.id, role);
    this.updateRoleHierarchy(role.id, role.inherits);
    this.clearPermissionCache();
    this.emit('roleCreated', role);
    return role;
  }

  updateRole(roleId, updates) {
    const role = this.roles.get(roleId);
    if (!role) {
      throw new Error(`Role ${roleId} not found`);
    }
    
    const updatedRole = {
      ...role,
      ...updates,
      updatedAt: new Date()
    };
    
    // Validate hierarchy if inheritance changed
    if (updates.inherits) {
      this.validateRoleHierarchy(roleId, updates.inherits);
      this.updateRoleHierarchy(roleId, updates.inherits);
    }
    
    this.roles.set(roleId, updatedRole);
    this.clearPermissionCache();
    this.emit('roleUpdated', updatedRole);
    return updatedRole;
  }

  deleteRole(roleId) {
    const role = this.roles.get(roleId);
    if (!role) {
      throw new Error(`Role ${roleId} not found`);
    }
    
    // Remove role from users
    for (const [userId, userRoles] of this.userRoles) {
      if (userRoles.includes(roleId)) {
        this.userRoles.set(userId, userRoles.filter(r => r !== roleId));
      }
    }
    
    // Remove role from hierarchy
    this.roleHierarchy.delete(roleId);
    for (const [parentRole, children] of this.roleHierarchy) {
      this.roleHierarchy.set(parentRole, children.filter(r => r !== roleId));
    }
    
    this.roles.delete(roleId);
    this.clearPermissionCache();
    this.emit('roleDeleted', role);
    return true;
  }

  getRole(roleId) {
    return this.roles.get(roleId);
  }

  getRoles(filters = {}) {
    let roles = Array.from(this.roles.values());
    
    if (filters.scope) {
      roles = roles.filter(r => r.scope === filters.scope);
    }
    
    if (filters.isDynamic !== undefined) {
      roles = roles.filter(r => r.isDynamic === filters.isDynamic);
    }
    
    if (filters.isActive !== undefined) {
      roles = roles.filter(r => r.isActive === filters.isActive);
    }
    
    return roles;
  }

  // User Role Assignment
  assignUserRole(userId, roleId, context = {}) {
    const role = this.roles.get(roleId);
    if (!role) {
      throw new Error(`Role ${roleId} not found`);
    }
    
    if (!role.isActive) {
      throw new Error(`Role ${roleId} is not active`);
    }
    
    // Check role constraints
    const constraintResult = this.checkRoleConstraints(role, userId, context);
    if (!constraintResult.allowed) {
      throw new Error(`Role assignment denied: ${constraintResult.reason}`);
    }
    
    if (!this.userRoles.has(userId)) {
      this.userRoles.set(userId, []);
    }
    
    const userRoles = this.userRoles.get(userId);
    if (!userRoles.includes(roleId)) {
      userRoles.push(roleId);
      this.clearPermissionCacheForUser(userId);
      this.emit('roleAssigned', { userId, roleId, context });
    }
    
    return true;
  }

  removeUserRole(userId, roleId) {
    if (!this.userRoles.has(userId)) {
      return false;
    }
    
    const userRoles = this.userRoles.get(userId);
    const updatedRoles = userRoles.filter(r => r !== roleId);
    
    if (updatedRoles.length !== userRoles.length) {
      this.userRoles.set(userId, updatedRoles);
      this.clearPermissionCacheForUser(userId);
      this.emit('roleRemoved', { userId, roleId });
      return true;
    }
    
    return false;
  }

  getUserRoles(userId, includeInherited = true) {
    const directRoles = this.userRoles.get(userId) || [];
    
    if (!includeInherited || !this.options.enableInheritance) {
      return directRoles;
    }
    
    const allRoles = new Set(directRoles);
    
    // Add inherited roles
    for (const roleId of directRoles) {
      const inheritedRoles = this.getInheritedRoles(roleId);
      inheritedRoles.forEach(r => allRoles.add(r));
    }
    
    return Array.from(allRoles);
  }

  setUserRoles(userId, roleIds, context = {}) {
    // Remove all current roles
    this.userRoles.delete(userId);
    
    // Assign new roles
    for (const roleId of roleIds) {
      this.assignUserRole(userId, roleId, context);
    }
    
    this.emit('userRolesSet', { userId, roleIds, context });
  }

  // Permission Checking
  async hasPermission(userId, permissionId, context = {}) {
    const cacheKey = `${userId}:${permissionId}:${JSON.stringify(context)}`;
    
    // Check cache
    if (this.permissionCache.has(cacheKey)) {
      const cached = this.permissionCache.get(cacheKey);
      if (cached.expiresAt > Date.now()) {
        return cached.hasPermission;
      }
      this.permissionCache.delete(cacheKey);
    }
    
    const hasPermission = await this.checkPermission(userId, permissionId, context);
    
    // Cache result
    this.permissionCache.set(cacheKey, {
      hasPermission,
      expiresAt: Date.now() + this.options.cacheTimeout
    });
    
    return hasPermission;
  }

  async checkPermission(userId, permissionId, context = {}) {
    const permission = this.permissions.get(permissionId);
    if (!permission || !permission.isActive) {
      return false;
    }
    
    const userRoles = this.getUserRoles(userId, true);
    
    // Check if any role has this permission
    for (const roleId of userRoles) {
      const role = this.roles.get(roleId);
      if (!role || !role.isActive) {
        continue;
      }
      
      if (role.permissions.includes(permissionId)) {
        // Check permission conditions
        if (await this.evaluatePermissionConditions(permission, userId, context)) {
          return true;
        }
      }
    }
    
    // Check dynamic roles if enabled
    if (this.options.enableDynamicRoles) {
      const dynamicPermission = await this.checkDynamicPermission(userId, permissionId, context);
      if (dynamicPermission) {
        return true;
      }
    }
    
    return false;
  }

  async hasResourcePermission(userId, resource, action, context = {}) {
    const userRoles = this.getUserRoles(userId, true);
    
    // Check direct permissions
    for (const permissionId of this.permissions.keys()) {
      const permission = this.permissions.get(permissionId);
      
      if (permission.resource === resource && permission.action === action) {
        if (await this.hasPermission(userId, permissionId, context)) {
          return true;
        }
      }
    }
    
    // Check wildcard permissions
    return await this.checkWildcardPermissions(userId, resource, action, context);
  }

  async getUserPermissions(userId, context = {}) {
    const userRoles = this.getUserRoles(userId, true);
    const permissions = new Set();
    
    for (const roleId of userRoles) {
      const role = this.roles.get(roleId);
      if (!role || !role.isActive) {
        continue;
      }
      
      for (const permissionId of role.permissions) {
        const permission = this.permissions.get(permissionId);
        if (permission && permission.isActive) {
          if (await this.evaluatePermissionConditions(permission, userId, context)) {
            permissions.add(permissionId);
          }
        }
      }
    }
    
    return Array.from(permissions);
  }

  // Role Hierarchy Management
  validateRoleHierarchy(roleId, inheritsFrom) {
    const visited = new Set();
    const checkCircular = (currentRole, path = []) => {
      if (path.includes(currentRole)) {
        throw new Error(`Circular role inheritance detected: ${path.join(' -> ')} -> ${currentRole}`);
      }
      
      if (visited.has(currentRole)) {
        return;
      }
      
      visited.add(currentRole);
      const role = this.roles.get(currentRole);
      
      if (role && role.inherits) {
        for (const inheritedRole of role.inherits) {
          checkCircular(inheritedRole, [...path, currentRole]);
        }
      }
    };
    
    // Check for circular dependency
    for (const inheritedRole of inheritsFrom) {
      checkCircular(inheritedRole, [roleId]);
    }
    
    // Check depth
    const checkDepth = (currentRole, depth = 0) => {
      if (depth > this.options.maxRoleDepth) {
        throw new Error(`Role hierarchy exceeds maximum depth of ${this.options.maxRoleDepth}`);
      }
      
      const role = this.roles.get(currentRole);
      if (role && role.inherits) {
        for (const inheritedRole of role.inherits) {
          checkDepth(inheritedRole, depth + 1);
        }
      }
    };
    
    checkDepth(roleId);
  }

  updateRoleHierarchy(roleId, inheritsFrom) {
    this.roleHierarchy.set(roleId, inheritsFrom);
  }

  getInheritedRoles(roleId, visited = new Set()) {
    if (visited.has(roleId)) {
      return [];
    }
    
    visited.add(roleId);
    const role = this.roles.get(roleId);
    
    if (!role || !role.inherits || role.inherits.length === 0) {
      return [];
    }
    
    const inherited = [...role.inherits];
    
    // Recursively get inherited roles
    for (const inheritedRole of role.inherits) {
      const subInherited = this.getInheritedRoles(inheritedRole, visited);
      inherited.push(...subInherited);
    }
    
    return [...new Set(inherited)];
  }

  // Dynamic Roles
  async evaluateDynamicRoles(userId, context = {}) {
    const dynamicRoles = [];
    
    for (const role of this.roles.values()) {
      if (!role.isDynamic || !role.isActive) {
        continue;
      }
      
      const qualifies = await this.evaluateDynamicRoleRules(role, userId, context);
      if (qualifies) {
        dynamicRoles.push(role.id);
      }
    }
    
    return dynamicRoles;
  }

  async evaluateDynamicRoleRules(role, userId, context) {
    for (const rule of role.dynamicRules) {
      const result = await this.evaluateRule(rule, userId, context);
      if (!result) {
        return false;
      }
    }
    
    return true;
  }

  async checkDynamicPermission(userId, permissionId, context) {
    const dynamicRoles = await this.evaluateDynamicRoles(userId, context);
    
    for (const roleId of dynamicRoles) {
      const role = this.roles.get(roleId);
      if (role && role.permissions.includes(permissionId)) {
        return true;
      }
    }
    
    return false;
  }

  // Contextual Rules
  addContextualRule(rule) {
    const ruleData = {
      id: rule.id || this.generateRuleId(),
      name: rule.name,
      description: rule.description,
      
      // Rule conditions
      conditions: rule.conditions,
      
      // Rule effects
      effect: rule.effect, // 'allow' or 'deny'
      permissions: rule.permissions || [],
      roles: rule.roles || [],
      
      // Priority and metadata
      priority: rule.priority || 0,
      enabled: rule.enabled !== false,
      createdAt: new Date()
    };
    
    this.contextualRules.set(ruleData.id, ruleData);
    this.emit('contextualRuleAdded', ruleData);
    return ruleData;
  }

  async evaluateContextualRules(userId, permissionId, context) {
    const applicableRules = Array.from(this.contextualRules.values())
      .filter(rule => rule.enabled)
      .filter(rule => rule.permissions.includes(permissionId) || rule.permissions.length === 0)
      .sort((a, b) => b.priority - a.priority);
    
    for (const rule of applicableRules) {
      const ruleApplies = await this.evaluateRuleConditions(rule.conditions, userId, context);
      
      if (ruleApplies) {
        return rule.effect === 'allow';
      }
    }
    
    return null; // No applicable rule
  }

  // Condition Evaluation
  async evaluatePermissionConditions(permission, userId, context) {
    if (!permission.conditions || permission.conditions.length === 0) {
      return true;
    }
    
    for (const condition of permission.conditions) {
      const result = await this.evaluateCondition(condition, userId, context);
      if (!result) {
        return false;
      }
    }
    
    return true;
  }

  async evaluateRuleConditions(conditions, userId, context) {
    if (!conditions || conditions.length === 0) {
      return true;
    }
    
    for (const condition of conditions) {
      const result = await this.evaluateCondition(condition, userId, context);
      if (!result) {
        return false;
      }
    }
    
    return true;
  }

  async evaluateCondition(condition, userId, context) {
    switch (condition.type) {
      case 'user_attribute':
        return this.evaluateUserAttributeCondition(condition, userId, context);
        
      case 'resource_attribute':
        return this.evaluateResourceAttributeCondition(condition, context);
        
      case 'time_range':
        return this.evaluateTimeRangeCondition(condition);
        
      case 'ip_range':
        return this.evaluateIPRangeCondition(condition, context);
        
      case 'custom':
        return this.evaluateCustomCondition(condition, userId, context);
        
      default:
        return true;
    }
  }

  evaluateUserAttributeCondition(condition, userId, context) {
    const userAttributes = context.user || {};
    const attributeValue = userAttributes[condition.attribute];
    
    return this.compareValues(attributeValue, condition.value, condition.operator);
  }

  evaluateResourceAttributeCondition(condition, context) {
    const resourceAttributes = context.resource || {};
    const attributeValue = resourceAttributes[condition.attribute];
    
    return this.compareValues(attributeValue, condition.value, condition.operator);
  }

  evaluateTimeRangeCondition(condition) {
    const now = new Date();
    const currentHour = now.getHours();
    const currentDay = now.getDay();
    
    if (condition.hours) {
      const [startHour, endHour] = condition.hours;
      if (currentHour < startHour || currentHour > endHour) {
        return false;
      }
    }
    
    if (condition.days) {
      if (!condition.days.includes(currentDay)) {
        return false;
      }
    }
    
    return true;
  }

  evaluateIPRangeCondition(condition, context) {
    const clientIP = context.ip;
    if (!clientIP) {
      return false;
    }
    
    return condition.ranges.some(range => clientIP.startsWith(range));
  }

  async evaluateCustomCondition(condition, userId, context) {
    // Custom condition evaluation would be implemented based on business logic
    try {
      if (condition.handler && typeof condition.handler === 'function') {
        return await condition.handler(userId, context);
      }
      return true;
    } catch (error) {
      console.error('Error evaluating custom condition:', error);
      return false;
    }
  }

  compareValues(actual, expected, operator = 'equals') {
    switch (operator) {
      case 'equals':
        return actual === expected;
      case 'not_equals':
        return actual !== expected;
      case 'contains':
        return Array.isArray(actual) ? actual.includes(expected) : false;
      case 'not_contains':
        return Array.isArray(actual) ? !actual.includes(expected) : true;
      case 'greater_than':
        return actual > expected;
      case 'less_than':
        return actual < expected;
      case 'matches':
        return new RegExp(expected).test(actual);
      default:
        return true;
    }
  }

  // Role Constraints
  checkRoleConstraints(role, userId, context) {
    const constraints = role.constraints;
    
    // Check max users constraint
    if (constraints.maxUsers) {
      const currentUsers = this.countUsersWithRole(role.id);
      if (currentUsers >= constraints.maxUsers) {
        return { allowed: false, reason: 'Maximum users limit reached for role' };
      }
    }
    
    // Check expiration constraint
    if (constraints.expiresAt && constraints.expiresAt < new Date()) {
      return { allowed: false, reason: 'Role has expired' };
    }
    
    // Check custom conditions
    for (const condition of constraints.conditions) {
      if (!this.evaluateCondition(condition, userId, context)) {
        return { allowed: false, reason: 'Role constraint not met' };
      }
    }
    
    return { allowed: true };
  }

  countUsersWithRole(roleId) {
    let count = 0;
    for (const userRoles of this.userRoles.values()) {
      if (userRoles.includes(roleId)) {
        count++;
      }
    }
    return count;
  }

  // Wildcard Permissions
  async checkWildcardPermissions(userId, resource, action, context) {
    const wildcardPatterns = [
      `${resource}:*`,
      `*:${action}`,
      '*:*'
    ];
    
    for (const pattern of wildcardPatterns) {
      const hasWildcardPermission = await this.hasWildcardPermission(userId, pattern, context);
      if (hasWildcardPermission) {
        return true;
      }
    }
    
    return false;
  }

  async hasWildcardPermission(userId, pattern, context) {
    for (const permission of this.permissions.values()) {
      const permissionPattern = `${permission.resource}:${permission.action}`;
      
      if (this.matchesPattern(permissionPattern, pattern)) {
        if (await this.hasPermission(userId, permission.id, context)) {
          return true;
        }
      }
    }
    
    return false;
  }

  matchesPattern(value, pattern) {
    const regexPattern = pattern.replace(/\*/g, '.*');
    return new RegExp(`^${regexPattern}$`).test(value);
  }

  // Cache Management
  clearPermissionCache() {
    this.permissionCache.clear();
    this.emit('cacheCleared', 'all');
  }

  clearPermissionCacheForUser(userId) {
    for (const [key] of this.permissionCache) {
      if (key.startsWith(`${userId}:`)) {
        this.permissionCache.delete(key);
      }
    }
    this.emit('cacheCleared', userId);
  }

  setupCacheCleanup() {
    setInterval(() => {
      const now = Date.now();
      for (const [key, cached] of this.permissionCache) {
        if (cached.expiresAt <= now) {
          this.permissionCache.delete(key);
        }
      }
    }, 60000); // Clean up every minute
  }

  // Utility Methods
  generateRuleId() {
    return `rule_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // Default Roles Setup
  initializeDefaultRoles() {
    // Create default permissions
    this.createPermission({
      id: 'user:read',
      name: 'Read User',
      description: 'Read user information',
      resource: 'user',
      action: 'read'
    });
    
    this.createPermission({
      id: 'user:write',
      name: 'Write User',
      description: 'Create and update user information',
      resource: 'user',
      action: 'write'
    });
    
    this.createPermission({
      id: 'admin:all',
      name: 'Admin All',
      description: 'Full administrative access',
      resource: '*',
      action: '*'
    });
    
    // Create default roles
    this.createRole({
      id: 'user',
      name: 'User',
      description: 'Basic user role',
      permissions: ['user:read']
    });
    
    this.createRole({
      id: 'admin',
      name: 'Administrator',
      description: 'System administrator',
      permissions: ['admin:all'],
      inherits: ['user']
    });
    
    this.createRole({
      id: 'super_admin',
      name: 'Super Administrator',
      description: 'Super administrator with all permissions',
      permissions: ['admin:all'],
      inherits: ['admin']
    });
  }

  // Statistics and Monitoring
  getStats() {
    return {
      roles: this.roles.size,
      permissions: this.permissions.size,
      userRoleAssignments: this.userRoles.size,
      contextualRules: this.contextualRules.size,
      cacheSize: this.permissionCache.size
    };
  }

  reset() {
    this.roles.clear();
    this.permissions.clear();
    this.userRoles.clear();
    this.roleHierarchy.clear();
    this.resourcePermissions.clear();
    this.contextualRules.clear();
    this.permissionCache.clear();
    this.initializeDefaultRoles();
  }
}

module.exports = RBACManager;