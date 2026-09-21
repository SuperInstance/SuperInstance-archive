const { EventEmitter } = require('events');

class PermissionInheritance extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = {
      maxInheritanceDepth: options.maxInheritanceDepth || 20,
      enableConditionalInheritance: options.enableConditionalInheritance !== false,
      enableDynamicInheritance: options.enableDynamicInheritance !== false,
      cacheTimeout: options.cacheTimeout || 300000, // 5 minutes
      enableInheritanceLogging: options.enableInheritanceLogging !== false,
      ...options
    };
    
    this.inheritanceRules = new Map();
    this.organizationHierarchy = new Map();
    this.roleInheritance = new Map();
    this.conditionalRules = new Map();
    this.dynamicInheritance = new Map();
    this.inheritanceCache = new Map();
    this.inheritanceLog = [];
    
    this.setupDefaultInheritanceRules();
  }

  // Organization Hierarchy Management
  createOrganization(orgData) {
    const organization = {
      id: orgData.id,
      name: orgData.name,
      type: orgData.type || 'department',
      parentId: orgData.parentId || null,
      
      // Inheritance settings
      inheritancePolicy: orgData.inheritancePolicy || 'inherit_all',
      inheritanceFilters: orgData.inheritanceFilters || [],
      
      // Organization attributes
      attributes: orgData.attributes || {},
      
      // Inheritance rules
      customInheritanceRules: orgData.customInheritanceRules || [],
      
      // Metadata
      createdAt: new Date(),
      updatedAt: new Date(),
      isActive: true
    };
    
    // Validate hierarchy
    if (organization.parentId) {
      this.validateOrganizationHierarchy(organization.id, organization.parentId);
    }
    
    this.organizationHierarchy.set(organization.id, organization);
    this.clearInheritanceCache();
    this.emit('organizationCreated', organization);
    return organization;
  }

  updateOrganization(orgId, updates) {
    const organization = this.organizationHierarchy.get(orgId);
    if (!organization) {
      throw new Error(`Organization ${orgId} not found`);
    }
    
    const updatedOrg = {
      ...organization,
      ...updates,
      updatedAt: new Date()
    };
    
    // Validate hierarchy if parent changed
    if (updates.parentId !== undefined) {
      this.validateOrganizationHierarchy(orgId, updates.parentId);
    }
    
    this.organizationHierarchy.set(orgId, updatedOrg);
    this.clearInheritanceCache();
    this.emit('organizationUpdated', updatedOrg);
    return updatedOrg;
  }

  deleteOrganization(orgId) {
    const organization = this.organizationHierarchy.get(orgId);
    if (!organization) {
      throw new Error(`Organization ${orgId} not found`);
    }
    
    // Check for children
    const children = this.getOrganizationChildren(orgId);
    if (children.length > 0) {
      throw new Error(`Cannot delete organization with children: ${children.map(c => c.id).join(', ')}`);
    }
    
    this.organizationHierarchy.delete(orgId);
    this.clearInheritanceCache();
    this.emit('organizationDeleted', organization);
    return true;
  }

  getOrganizationHierarchy(orgId) {
    const organization = this.organizationHierarchy.get(orgId);
    if (!organization) {
      return null;
    }
    
    const hierarchy = {
      ...organization,
      children: this.getOrganizationChildren(orgId),
      ancestors: this.getOrganizationAncestors(orgId),
      descendants: this.getOrganizationDescendants(orgId)
    };
    
    return hierarchy;
  }

  getOrganizationChildren(orgId) {
    return Array.from(this.organizationHierarchy.values())
      .filter(org => org.parentId === orgId);
  }

  getOrganizationAncestors(orgId, visited = new Set()) {
    if (visited.has(orgId)) {
      return []; // Prevent circular references
    }
    
    visited.add(orgId);
    const organization = this.organizationHierarchy.get(orgId);
    
    if (!organization || !organization.parentId) {
      return [];
    }
    
    const parent = this.organizationHierarchy.get(organization.parentId);
    if (!parent) {
      return [];
    }
    
    return [parent, ...this.getOrganizationAncestors(organization.parentId, visited)];
  }

  getOrganizationDescendants(orgId, visited = new Set()) {
    if (visited.has(orgId)) {
      return []; // Prevent circular references
    }
    
    visited.add(orgId);
    const children = this.getOrganizationChildren(orgId);
    const descendants = [...children];
    
    for (const child of children) {
      descendants.push(...this.getOrganizationDescendants(child.id, visited));
    }
    
    return descendants;
  }

  validateOrganizationHierarchy(orgId, parentId) {
    if (!parentId) {
      return; // Root organization
    }
    
    const parent = this.organizationHierarchy.get(parentId);
    if (!parent) {
      throw new Error(`Parent organization ${parentId} not found`);
    }
    
    // Check for circular references
    const ancestors = this.getOrganizationAncestors(parentId);
    if (ancestors.some(ancestor => ancestor.id === orgId)) {
      throw new Error('Circular organization hierarchy detected');
    }
    
    // Check depth
    if (ancestors.length >= this.options.maxInheritanceDepth) {
      throw new Error(`Organization hierarchy exceeds maximum depth of ${this.options.maxInheritanceDepth}`);
    }
  }

  // Inheritance Rule Management
  createInheritanceRule(ruleData) {
    const rule = {
      id: ruleData.id || this.generateRuleId(),
      name: ruleData.name,
      description: ruleData.description,
      
      // Rule scope
      scope: ruleData.scope || 'global', // 'global', 'organization', 'role'
      scopeId: ruleData.scopeId,
      
      // Inheritance behavior
      inheritanceType: ruleData.inheritanceType || 'additive', // 'additive', 'override', 'restrictive'
      direction: ruleData.direction || 'down', // 'up', 'down', 'both'
      
      // Permission filters
      permissionFilters: {
        include: ruleData.permissionFilters?.include || [],
        exclude: ruleData.permissionFilters?.exclude || [],
        patterns: ruleData.permissionFilters?.patterns || []
      },
      
      // Role filters
      roleFilters: {
        include: ruleData.roleFilters?.include || [],
        exclude: ruleData.roleFilters?.exclude || [],
        patterns: ruleData.roleFilters?.patterns || []
      },
      
      // Conditions
      conditions: ruleData.conditions || [],
      
      // Transformations
      transformations: ruleData.transformations || [],
      
      // Priority and metadata
      priority: ruleData.priority || 0,
      enabled: ruleData.enabled !== false,
      createdAt: new Date(),
      updatedAt: new Date()
    };
    
    this.inheritanceRules.set(rule.id, rule);
    this.clearInheritanceCache();
    this.emit('inheritanceRuleCreated', rule);
    return rule;
  }

  updateInheritanceRule(ruleId, updates) {
    const rule = this.inheritanceRules.get(ruleId);
    if (!rule) {
      throw new Error(`Inheritance rule ${ruleId} not found`);
    }
    
    const updatedRule = {
      ...rule,
      ...updates,
      updatedAt: new Date()
    };
    
    this.inheritanceRules.set(ruleId, updatedRule);
    this.clearInheritanceCache();
    this.emit('inheritanceRuleUpdated', updatedRule);
    return updatedRule;
  }

  deleteInheritanceRule(ruleId) {
    const rule = this.inheritanceRules.get(ruleId);
    if (!rule) {
      throw new Error(`Inheritance rule ${ruleId} not found`);
    }
    
    this.inheritanceRules.delete(ruleId);
    this.clearInheritanceCache();
    this.emit('inheritanceRuleDeleted', rule);
    return true;
  }

  // Permission Inheritance Calculation
  async calculateInheritedPermissions(userId, context = {}) {
    const cacheKey = `permissions:${userId}:${JSON.stringify(context)}`;
    
    // Check cache
    if (this.inheritanceCache.has(cacheKey)) {
      const cached = this.inheritanceCache.get(cacheKey);
      if (cached.expiresAt > Date.now()) {
        return cached.permissions;
      }
      this.inheritanceCache.delete(cacheKey);
    }
    
    const permissions = await this.computeInheritedPermissions(userId, context);
    
    // Cache result
    this.inheritanceCache.set(cacheKey, {
      permissions,
      expiresAt: Date.now() + this.options.cacheTimeout
    });
    
    return permissions;
  }

  async computeInheritedPermissions(userId, context = {}) {
    const userOrganization = context.organizationId;
    const userRoles = context.roles || [];
    
    const inheritedPermissions = new Map();
    const inheritancePath = [];
    
    // Start with direct permissions
    const directPermissions = await this.getDirectPermissions(userId, context);
    for (const permission of directPermissions) {
      inheritedPermissions.set(permission.id, {
        ...permission,
        source: 'direct',
        inheritancePath: ['direct']
      });
    }
    
    // Add organization-based inheritance
    if (userOrganization) {
      await this.addOrganizationInheritedPermissions(
        inheritedPermissions,
        userOrganization,
        userId,
        context,
        inheritancePath
      );
    }
    
    // Add role-based inheritance
    for (const role of userRoles) {
      await this.addRoleInheritedPermissions(
        inheritedPermissions,
        role,
        userId,
        context,
        inheritancePath
      );
    }
    
    // Apply conditional inheritance
    if (this.options.enableConditionalInheritance) {
      await this.applyConditionalInheritance(inheritedPermissions, userId, context);
    }
    
    // Apply dynamic inheritance
    if (this.options.enableDynamicInheritance) {
      await this.applyDynamicInheritance(inheritedPermissions, userId, context);
    }
    
    // Log inheritance if enabled
    if (this.options.enableInheritanceLogging) {
      this.logInheritanceCalculation(userId, inheritedPermissions, context);
    }
    
    return Array.from(inheritedPermissions.values());
  }

  async addOrganizationInheritedPermissions(inheritedPermissions, organizationId, userId, context, path) {
    const organization = this.organizationHierarchy.get(organizationId);
    if (!organization || !organization.isActive) {
      return;
    }
    
    // Prevent circular inheritance
    if (path.includes(organizationId)) {
      return;
    }
    
    const newPath = [...path, organizationId];
    
    // Get applicable inheritance rules for this organization
    const rules = this.getApplicableInheritanceRules('organization', organizationId);
    
    // Apply inheritance based on organization policy
    switch (organization.inheritancePolicy) {
      case 'inherit_all':
        await this.inheritAllFromParent(inheritedPermissions, organization, userId, context, newPath, rules);
        break;
        
      case 'inherit_filtered':
        await this.inheritFilteredFromParent(inheritedPermissions, organization, userId, context, newPath, rules);
        break;
        
      case 'no_inherit':
        // No inheritance from parent
        break;
        
      case 'custom':
        await this.applyCustomInheritanceRules(inheritedPermissions, organization, userId, context, newPath, rules);
        break;
    }
    
    // Continue up the hierarchy if applicable
    if (organization.parentId && newPath.length < this.options.maxInheritanceDepth) {
      await this.addOrganizationInheritedPermissions(
        inheritedPermissions,
        organization.parentId,
        userId,
        context,
        newPath
      );
    }
  }

  async inheritAllFromParent(inheritedPermissions, organization, userId, context, path, rules) {
    if (!organization.parentId) {
      return;
    }
    
    const parentPermissions = await this.getOrganizationPermissions(organization.parentId, context);
    
    for (const permission of parentPermissions) {
      if (this.shouldInheritPermission(permission, rules)) {
        const transformedPermission = await this.transformInheritedPermission(
          permission,
          'organization',
          organization.id,
          path,
          rules
        );
        
        this.addInheritedPermission(inheritedPermissions, transformedPermission);
      }
    }
  }

  async inheritFilteredFromParent(inheritedPermissions, organization, userId, context, path, rules) {
    if (!organization.parentId) {
      return;
    }
    
    const parentPermissions = await this.getOrganizationPermissions(organization.parentId, context);
    const filters = organization.inheritanceFilters;
    
    for (const permission of parentPermissions) {
      if (this.permissionMatchesFilters(permission, filters) && 
          this.shouldInheritPermission(permission, rules)) {
        
        const transformedPermission = await this.transformInheritedPermission(
          permission,
          'organization',
          organization.id,
          path,
          rules
        );
        
        this.addInheritedPermission(inheritedPermissions, transformedPermission);
      }
    }
  }

  async applyCustomInheritanceRules(inheritedPermissions, organization, userId, context, path, rules) {
    for (const customRule of organization.customInheritanceRules) {
      await this.applyInheritanceRule(inheritedPermissions, customRule, organization, userId, context, path);
    }
  }

  async addRoleInheritedPermissions(inheritedPermissions, roleId, userId, context, path) {
    // Prevent circular inheritance
    if (path.includes(`role:${roleId}`)) {
      return;
    }
    
    const newPath = [...path, `role:${roleId}`];
    const rules = this.getApplicableInheritanceRules('role', roleId);
    
    // Get role inheritance configuration
    const roleInheritanceConfig = this.roleInheritance.get(roleId);
    if (roleInheritanceConfig) {
      for (const inheritedRoleId of roleInheritanceConfig.inheritsFrom) {
        const inheritedRolePermissions = await this.getRolePermissions(inheritedRoleId, context);
        
        for (const permission of inheritedRolePermissions) {
          if (this.shouldInheritPermission(permission, rules)) {
            const transformedPermission = await this.transformInheritedPermission(
              permission,
              'role',
              roleId,
              newPath,
              rules
            );
            
            this.addInheritedPermission(inheritedPermissions, transformedPermission);
          }
        }
        
        // Recursively inherit from inherited roles
        if (newPath.length < this.options.maxInheritanceDepth) {
          await this.addRoleInheritedPermissions(
            inheritedPermissions,
            inheritedRoleId,
            userId,
            context,
            newPath
          );
        }
      }
    }
  }

  async applyConditionalInheritance(inheritedPermissions, userId, context) {
    const conditionalRules = Array.from(this.conditionalRules.values())
      .filter(rule => rule.enabled);
    
    for (const rule of conditionalRules) {
      const conditionsMet = await this.evaluateInheritanceConditions(rule.conditions, userId, context);
      
      if (conditionsMet) {
        await this.applyConditionalInheritanceRule(inheritedPermissions, rule, userId, context);
      }
    }
  }

  async applyDynamicInheritance(inheritedPermissions, userId, context) {
    const dynamicRules = Array.from(this.dynamicInheritance.values())
      .filter(rule => rule.enabled);
    
    for (const rule of dynamicRules) {
      const shouldApply = await this.evaluateDynamicInheritanceRule(rule, userId, context);
      
      if (shouldApply) {
        await this.applyDynamicInheritanceRule(inheritedPermissions, rule, userId, context);
      }
    }
  }

  // Permission Transformation
  async transformInheritedPermission(permission, sourceType, sourceId, inheritancePath, rules) {
    let transformedPermission = { ...permission };
    
    // Add inheritance metadata
    transformedPermission.source = sourceType;
    transformedPermission.sourceId = sourceId;
    transformedPermission.inheritancePath = inheritancePath;
    transformedPermission.inherited = true;
    
    // Apply transformations from rules
    for (const rule of rules) {
      if (rule.transformations && rule.transformations.length > 0) {
        for (const transformation of rule.transformations) {
          transformedPermission = await this.applyPermissionTransformation(
            transformedPermission,
            transformation
          );
        }
      }
    }
    
    return transformedPermission;
  }

  async applyPermissionTransformation(permission, transformation) {
    switch (transformation.type) {
      case 'scope_restriction':
        return this.applyScopeRestriction(permission, transformation);
        
      case 'attribute_modification':
        return this.applyAttributeModification(permission, transformation);
        
      case 'condition_addition':
        return this.addCondition(permission, transformation);
        
      case 'expiration':
        return this.addExpiration(permission, transformation);
        
      case 'custom':
        return await this.applyCustomTransformation(permission, transformation);
        
      default:
        return permission;
    }
  }

  applyScopeRestriction(permission, transformation) {
    return {
      ...permission,
      scope: transformation.newScope,
      scopeRestricted: true,
      originalScope: permission.scope
    };
  }

  applyAttributeModification(permission, transformation) {
    const modifiedAttributes = { ...permission.attributes };
    
    for (const [key, value] of Object.entries(transformation.attributeChanges)) {
      if (transformation.operation === 'set') {
        modifiedAttributes[key] = value;
      } else if (transformation.operation === 'append' && Array.isArray(modifiedAttributes[key])) {
        modifiedAttributes[key] = [...modifiedAttributes[key], value];
      } else if (transformation.operation === 'remove') {
        delete modifiedAttributes[key];
      }
    }
    
    return {
      ...permission,
      attributes: modifiedAttributes
    };
  }

  addCondition(permission, transformation) {
    return {
      ...permission,
      conditions: [...(permission.conditions || []), transformation.condition]
    };
  }

  addExpiration(permission, transformation) {
    const expiresAt = new Date(Date.now() + transformation.durationMs);
    
    return {
      ...permission,
      expiresAt,
      temporary: true
    };
  }

  // Helper Methods
  addInheritedPermission(inheritedPermissions, permission) {
    const existingPermission = inheritedPermissions.get(permission.id);
    
    if (!existingPermission) {
      inheritedPermissions.set(permission.id, permission);
      return;
    }
    
    // Handle permission conflicts based on inheritance type
    const resolvedPermission = this.resolvePermissionConflict(existingPermission, permission);
    inheritedPermissions.set(permission.id, resolvedPermission);
  }

  resolvePermissionConflict(existing, incoming) {
    // Priority-based resolution
    const existingPriority = this.getPermissionPriority(existing);
    const incomingPriority = this.getPermissionPriority(incoming);
    
    if (incomingPriority > existingPriority) {
      return incoming;
    }
    
    // For same priority, merge attributes and conditions
    return {
      ...existing,
      attributes: { ...existing.attributes, ...incoming.attributes },
      conditions: [...(existing.conditions || []), ...(incoming.conditions || [])],
      inheritancePath: [...existing.inheritancePath, ...incoming.inheritancePath]
    };
  }

  getPermissionPriority(permission) {
    if (permission.source === 'direct') return 100;
    if (permission.source === 'role') return 80;
    if (permission.source === 'organization') return 60;
    return 50;
  }

  shouldInheritPermission(permission, rules) {
    for (const rule of rules) {
      if (!this.permissionMatchesRuleFilters(permission, rule)) {
        continue;
      }
      
      // Rule applies to this permission
      return rule.inheritanceType !== 'deny';
    }
    
    return true; // Default to inherit if no applicable rules
  }

  permissionMatchesRuleFilters(permission, rule) {
    const { permissionFilters } = rule;
    
    // Check include filters
    if (permissionFilters.include.length > 0) {
      if (!permissionFilters.include.includes(permission.id)) {
        return false;
      }
    }
    
    // Check exclude filters
    if (permissionFilters.exclude.includes(permission.id)) {
      return false;
    }
    
    // Check pattern filters
    for (const pattern of permissionFilters.patterns) {
      if (pattern.type === 'include' && !this.matchesPattern(permission.id, pattern.pattern)) {
        return false;
      }
      if (pattern.type === 'exclude' && this.matchesPattern(permission.id, pattern.pattern)) {
        return false;
      }
    }
    
    return true;
  }

  permissionMatchesFilters(permission, filters) {
    // Check include filters
    if (filters.include && filters.include.length > 0) {
      return filters.include.some(filter => this.matchesPattern(permission.id, filter));
    }
    
    // Check exclude filters
    if (filters.exclude && filters.exclude.length > 0) {
      return !filters.exclude.some(filter => this.matchesPattern(permission.id, filter));
    }
    
    return true;
  }

  matchesPattern(value, pattern) {
    const regexPattern = pattern.replace(/\*/g, '.*');
    return new RegExp(`^${regexPattern}$`).test(value);
  }

  getApplicableInheritanceRules(scope, scopeId) {
    return Array.from(this.inheritanceRules.values())
      .filter(rule => rule.enabled)
      .filter(rule => rule.scope === 'global' || (rule.scope === scope && rule.scopeId === scopeId))
      .sort((a, b) => b.priority - a.priority);
  }

  async evaluateInheritanceConditions(conditions, userId, context) {
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
        return this.checkUserAttribute(userId, condition.attribute, condition.value, condition.operator, context);
        
      case 'time_based':
        return this.checkTimeCondition(condition);
        
      case 'organization_level':
        return this.checkOrganizationLevel(context.organizationId, condition.level, condition.operator);
        
      case 'custom':
        return await this.evaluateCustomCondition(condition, userId, context);
        
      default:
        return true;
    }
  }

  // Data Access Methods (these would typically integrate with other services)
  async getDirectPermissions(userId, context) {
    // This would integrate with the RBAC manager or user service
    return [];
  }

  async getOrganizationPermissions(organizationId, context) {
    // This would get permissions specific to an organization
    return [];
  }

  async getRolePermissions(roleId, context) {
    // This would get permissions for a specific role
    return [];
  }

  // Cache Management
  clearInheritanceCache() {
    this.inheritanceCache.clear();
    this.emit('inheritanceCacheCleared');
  }

  clearInheritanceCacheForUser(userId) {
    for (const [key] of this.inheritanceCache) {
      if (key.startsWith(`permissions:${userId}:`)) {
        this.inheritanceCache.delete(key);
      }
    }
  }

  // Logging and Audit
  logInheritanceCalculation(userId, inheritedPermissions, context) {
    const logEntry = {
      id: this.generateLogId(),
      userId,
      timestamp: new Date(),
      context,
      permissionCount: inheritedPermissions.size,
      inheritanceSources: this.analyzeInheritanceSources(inheritedPermissions),
      calculationTime: Date.now() // This would be measured properly
    };
    
    this.inheritanceLog.push(logEntry);
    
    // Keep only last 1000 log entries
    if (this.inheritanceLog.length > 1000) {
      this.inheritanceLog.shift();
    }
    
    this.emit('inheritanceCalculationLogged', logEntry);
  }

  analyzeInheritanceSources(inheritedPermissions) {
    const sources = {};
    
    for (const permission of inheritedPermissions.values()) {
      const source = permission.source || 'unknown';
      sources[source] = (sources[source] || 0) + 1;
    }
    
    return sources;
  }

  // Utility Methods
  generateRuleId() {
    return `rule_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  generateLogId() {
    return `log_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  setupDefaultInheritanceRules() {
    // Create default inheritance rule for admins
    this.createInheritanceRule({
      id: 'admin-full-inheritance',
      name: 'Admin Full Inheritance',
      description: 'Administrators inherit all permissions from parent organizations',
      scope: 'role',
      scopeId: 'admin',
      inheritanceType: 'additive',
      direction: 'down',
      conditions: [
        {
          type: 'user_attribute',
          attribute: 'roles',
          operator: 'contains',
          value: 'admin'
        }
      ]
    });
    
    // Create default rule for restricted permissions
    this.createInheritanceRule({
      id: 'security-restricted',
      name: 'Security Restricted Permissions',
      description: 'Security-sensitive permissions are not inherited by default',
      scope: 'global',
      inheritanceType: 'restrictive',
      permissionFilters: {
        exclude: ['admin:*', 'security:*', 'system:*']
      }
    });
  }

  // Statistics and Monitoring
  getInheritanceStats() {
    return {
      inheritanceRules: this.inheritanceRules.size,
      organizations: this.organizationHierarchy.size,
      conditionalRules: this.conditionalRules.size,
      dynamicRules: this.dynamicInheritance.size,
      cacheSize: this.inheritanceCache.size,
      logEntries: this.inheritanceLog.length
    };
  }

  getInheritanceRules() {
    return Array.from(this.inheritanceRules.values());
  }

  getOrganizations() {
    return Array.from(this.organizationHierarchy.values());
  }

  reset() {
    this.inheritanceRules.clear();
    this.organizationHierarchy.clear();
    this.roleInheritance.clear();
    this.conditionalRules.clear();
    this.dynamicInheritance.clear();
    this.inheritanceCache.clear();
    this.inheritanceLog = [];
    this.setupDefaultInheritanceRules();
  }
}

module.exports = PermissionInheritance;