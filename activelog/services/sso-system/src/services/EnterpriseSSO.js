const saml = require('passport-saml');
const ldap = require('ldapjs');
const passport = require('passport');
const SamlStrategy = require('passport-saml').Strategy;
const crypto = require('crypto');
const { EventEmitter } = require('events');

class EnterpriseSSO extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = {
      samlCertPath: options.samlCertPath || './certs/saml.crt',
      samlKeyPath: options.samlKeyPath || './certs/saml.key',
      entityId: options.entityId || 'activelog-sso',
      callbackUrl: options.callbackUrl || 'http://localhost:8201',
      sessionTimeout: options.sessionTimeout || 28800000, // 8 hours
      enableJustInTimeProvisioning: options.enableJustInTimeProvisioning !== false,
      enableAttributeMapping: options.enableAttributeMapping !== false,
      enableGroupSync: options.enableGroupSync !== false,
      ...options
    };
    
    this.samlProviders = new Map();
    this.ldapConnections = new Map();
    this.enterpriseUsers = new Map();
    this.attributeMappings = new Map();
    this.groupMappings = new Map();
    this.provisioningRules = new Map();
    
    this.setupDefaultMappings();
  }

  // SAML Provider Management
  async createSAMLProvider(providerData) {
    const provider = {
      id: providerData.id,
      name: providerData.name,
      domain: providerData.domain,
      
      // SAML Configuration
      entryPoint: providerData.entryPoint, // IdP SSO URL
      issuer: providerData.issuer, // IdP Entity ID
      cert: providerData.cert, // IdP Certificate
      
      // SP Configuration
      callbackUrl: `${this.options.callbackUrl}/auth/saml/${providerData.id}/callback`,
      logoutUrl: providerData.logoutUrl,
      logoutCallbackUrl: `${this.options.callbackUrl}/auth/saml/${providerData.id}/logout/callback`,
      
      // Security Settings
      wantAssertionsSigned: providerData.wantAssertionsSigned !== false,
      wantAuthnResponseSigned: providerData.wantAuthnResponseSigned !== false,
      signatureAlgorithm: providerData.signatureAlgorithm || 'sha256',
      digestAlgorithm: providerData.digestAlgorithm || 'sha256',
      
      // Attribute Configuration
      attributeConsumingServiceIndex: providerData.attributeConsumingServiceIndex,
      authnContext: providerData.authnContext || ['urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport'],
      forceAuthn: providerData.forceAuthn || false,
      skipRequestCompression: providerData.skipRequestCompression || false,
      
      // Provisioning
      enableJIT: providerData.enableJIT !== false,
      defaultRole: providerData.defaultRole || 'user',
      
      // Metadata
      createdAt: new Date(),
      updatedAt: new Date(),
      isActive: true
    };
    
    this.samlProviders.set(provider.id, provider);
    this.setupSAMLStrategy(provider);
    
    this.emit('samlProviderCreated', provider);
    return provider;
  }

  updateSAMLProvider(providerId, updates) {
    const provider = this.samlProviders.get(providerId);
    if (!provider) {
      throw new Error(`SAML provider ${providerId} not found`);
    }
    
    const updatedProvider = {
      ...provider,
      ...updates,
      updatedAt: new Date()
    };
    
    this.samlProviders.set(providerId, updatedProvider);
    
    // Update Passport strategy
    passport.unuse(`saml-${providerId}`);
    this.setupSAMLStrategy(updatedProvider);
    
    this.emit('samlProviderUpdated', updatedProvider);
    return updatedProvider;
  }

  deleteSAMLProvider(providerId) {
    const provider = this.samlProviders.get(providerId);
    if (!provider) {
      throw new Error(`SAML provider ${providerId} not found`);
    }
    
    // Remove Passport strategy
    passport.unuse(`saml-${providerId}`);
    
    this.samlProviders.delete(providerId);
    
    this.emit('samlProviderDeleted', provider);
    return true;
  }

  setupSAMLStrategy(provider) {
    const strategy = new SamlStrategy({
      entryPoint: provider.entryPoint,
      issuer: provider.issuer,
      callbackUrl: provider.callbackUrl,
      cert: provider.cert,
      
      // Service Provider settings
      privateCert: this.loadPrivateKey(),
      cert: this.loadPublicCert(),
      
      // Security settings
      wantAssertionsSigned: provider.wantAssertionsSigned,
      wantAuthnResponseSigned: provider.wantAuthnResponseSigned,
      signatureAlgorithm: provider.signatureAlgorithm,
      digestAlgorithm: provider.digestAlgorithm,
      
      // Other settings
      attributeConsumingServiceIndex: provider.attributeConsumingServiceIndex,
      authnContext: provider.authnContext,
      forceAuthn: provider.forceAuthn,
      skipRequestCompression: provider.skipRequestCompression
    }, async (profile, done) => {
      try {
        const result = await this.handleSAMLLogin(provider.id, profile);
        done(null, result);
      } catch (error) {
        done(error, null);
      }
    });
    
    passport.use(`saml-${provider.id}`, strategy);
  }

  // LDAP Provider Management
  async createLDAPProvider(providerData) {
    const provider = {
      id: providerData.id,
      name: providerData.name,
      domain: providerData.domain,
      
      // Connection Settings
      url: providerData.url, // ldap://domain.com:389 or ldaps://domain.com:636
      bindDN: providerData.bindDN, // Service account DN
      bindCredentials: providerData.bindCredentials, // Service account password
      
      // Search Settings
      searchBase: providerData.searchBase, // Base DN for user searches
      searchFilter: providerData.searchFilter || '(sAMAccountName={{username}})',
      searchAttributes: providerData.searchAttributes || ['displayName', 'mail', 'memberOf'],
      
      // Group Settings
      groupSearchBase: providerData.groupSearchBase,
      groupSearchFilter: providerData.groupSearchFilter || '(member={{dn}})',
      groupSearchAttributes: providerData.groupSearchAttributes || ['cn', 'description'],
      
      // Security Settings
      tlsOptions: providerData.tlsOptions || {},
      timeout: providerData.timeout || 10000,
      connectTimeout: providerData.connectTimeout || 10000,
      idleTimeout: providerData.idleTimeout || 30000,
      
      // Provisioning
      enableJIT: providerData.enableJIT !== false,
      enableGroupSync: providerData.enableGroupSync !== false,
      defaultRole: providerData.defaultRole || 'user',
      
      // Metadata
      createdAt: new Date(),
      updatedAt: new Date(),
      isActive: true
    };
    
    this.ldapConnections.set(provider.id, provider);
    
    // Test connection
    await this.testLDAPConnection(provider.id);
    
    this.emit('ldapProviderCreated', provider);
    return provider;
  }

  updateLDAPProvider(providerId, updates) {
    const provider = this.ldapConnections.get(providerId);
    if (!provider) {
      throw new Error(`LDAP provider ${providerId} not found`);
    }
    
    const updatedProvider = {
      ...provider,
      ...updates,
      updatedAt: new Date()
    };
    
    this.ldapConnections.set(providerId, updatedProvider);
    
    this.emit('ldapProviderUpdated', updatedProvider);
    return updatedProvider;
  }

  deleteLDAPProvider(providerId) {
    const provider = this.ldapConnections.get(providerId);
    if (!provider) {
      throw new Error(`LDAP provider ${providerId} not found`);
    }
    
    this.ldapConnections.delete(providerId);
    
    this.emit('ldapProviderDeleted', provider);
    return true;
  }

  // SAML Authentication
  async handleSAMLLogin(providerId, profile) {
    const provider = this.samlProviders.get(providerId);
    if (!provider) {
      throw new Error(`SAML provider ${providerId} not found`);
    }
    
    // Normalize SAML attributes
    const normalizedProfile = this.normalizeSAMLProfile(profile, provider);
    
    // Check for existing user
    let enterpriseUser = this.findEnterpriseUserByEmail(normalizedProfile.email);
    
    if (enterpriseUser) {
      // Update existing user
      await this.updateEnterpriseUser(enterpriseUser.id, {
        lastLoginAt: new Date(),
        samlProfile: normalizedProfile,
        attributes: normalizedProfile.attributes
      });
      
      this.emit('samlLoginExisting', {
        providerId,
        userId: enterpriseUser.userId,
        email: normalizedProfile.email
      });
    } else {
      // Just-in-Time Provisioning
      if (provider.enableJIT && this.options.enableJustInTimeProvisioning) {
        enterpriseUser = await this.provisionUserFromSAML(provider, normalizedProfile);
        
        this.emit('samlUserProvisioned', {
          providerId,
          userId: enterpriseUser.userId,
          email: normalizedProfile.email
        });
      } else {
        throw new Error('User not found and Just-in-Time provisioning is disabled');
      }
    }
    
    // Apply attribute mappings and group sync
    if (this.options.enableAttributeMapping) {
      await this.applyAttributeMappings(enterpriseUser.id, normalizedProfile.attributes, providerId);
    }
    
    if (this.options.enableGroupSync) {
      await this.syncUserGroups(enterpriseUser.id, normalizedProfile.groups, providerId);
    }
    
    return {
      success: true,
      userId: enterpriseUser.userId,
      enterpriseUserId: enterpriseUser.id,
      provider: 'saml',
      providerId,
      profile: normalizedProfile
    };
  }

  normalizeSAMLProfile(profile, provider) {
    const attributeMap = this.attributeMappings.get(provider.id) || this.getDefaultSAMLAttributeMap();
    
    const normalized = {
      nameID: profile.nameID,
      nameIDFormat: profile.nameIDFormat,
      sessionIndex: profile.sessionIndex,
      
      // Map standard attributes
      email: this.getSAMLAttribute(profile, attributeMap.email),
      firstName: this.getSAMLAttribute(profile, attributeMap.firstName),
      lastName: this.getSAMLAttribute(profile, attributeMap.lastName),
      displayName: this.getSAMLAttribute(profile, attributeMap.displayName),
      department: this.getSAMLAttribute(profile, attributeMap.department),
      title: this.getSAMLAttribute(profile, attributeMap.title),
      phone: this.getSAMLAttribute(profile, attributeMap.phone),
      manager: this.getSAMLAttribute(profile, attributeMap.manager),
      
      // Extract groups/roles
      groups: this.extractSAMLGroups(profile, attributeMap.groups),
      
      // Store all attributes for custom mapping
      attributes: profile,
      
      // Metadata
      loginTime: new Date(),
      provider: provider.id
    };
    
    return normalized;
  }

  getSAMLAttribute(profile, attributeName) {
    if (!attributeName || !profile[attributeName]) {
      return null;
    }
    
    const value = profile[attributeName];
    return Array.isArray(value) ? value[0] : value;
  }

  extractSAMLGroups(profile, groupAttributeName) {
    if (!groupAttributeName || !profile[groupAttributeName]) {
      return [];
    }
    
    const groups = profile[groupAttributeName];
    return Array.isArray(groups) ? groups : [groups];
  }

  // LDAP Authentication
  async authenticateLDAP(providerId, username, password) {
    const provider = this.ldapConnections.get(providerId);
    if (!provider) {
      throw new Error(`LDAP provider ${providerId} not found`);
    }
    
    const client = ldap.createClient({
      url: provider.url,
      timeout: provider.timeout,
      connectTimeout: provider.connectTimeout,
      idleTimeout: provider.idleTimeout,
      tlsOptions: provider.tlsOptions
    });
    
    try {
      // First, bind with service account
      await this.bindLDAPClient(client, provider.bindDN, provider.bindCredentials);
      
      // Search for user
      const userProfile = await this.searchLDAPUser(client, provider, username);
      if (!userProfile) {
        throw new Error('User not found');
      }
      
      // Authenticate user
      await this.bindLDAPClient(client, userProfile.dn, password);
      
      // Get user groups if enabled
      let groups = [];
      if (provider.enableGroupSync) {
        groups = await this.getLDAPUserGroups(client, provider, userProfile);
      }
      
      // Normalize profile
      const normalizedProfile = this.normalizeLDAPProfile(userProfile, groups, provider);
      
      // Handle user provisioning
      let enterpriseUser = this.findEnterpriseUserByEmail(normalizedProfile.email);
      
      if (enterpriseUser) {
        await this.updateEnterpriseUser(enterpriseUser.id, {
          lastLoginAt: new Date(),
          ldapProfile: normalizedProfile,
          attributes: normalizedProfile.attributes
        });
      } else if (provider.enableJIT) {
        enterpriseUser = await this.provisionUserFromLDAP(provider, normalizedProfile);
      } else {
        throw new Error('User not found and Just-in-Time provisioning is disabled');
      }
      
      // Apply mappings
      if (this.options.enableAttributeMapping) {
        await this.applyAttributeMappings(enterpriseUser.id, normalizedProfile.attributes, providerId);
      }
      
      if (this.options.enableGroupSync) {
        await this.syncUserGroups(enterpriseUser.id, normalizedProfile.groups, providerId);
      }
      
      this.emit('ldapLoginSuccess', {
        providerId,
        userId: enterpriseUser.userId,
        username,
        email: normalizedProfile.email
      });
      
      return {
        success: true,
        userId: enterpriseUser.userId,
        enterpriseUserId: enterpriseUser.id,
        provider: 'ldap',
        providerId,
        profile: normalizedProfile
      };
      
    } finally {
      client.unbind();
    }
  }

  async bindLDAPClient(client, dn, password) {
    return new Promise((resolve, reject) => {
      client.bind(dn, password, (error) => {
        if (error) {
          reject(new Error(`LDAP bind failed: ${error.message}`));
        } else {
          resolve();
        }
      });
    });
  }

  async searchLDAPUser(client, provider, username) {
    const searchFilter = provider.searchFilter.replace('{{username}}', username);
    
    return new Promise((resolve, reject) => {
      client.search(provider.searchBase, {
        filter: searchFilter,
        attributes: ['dn', ...provider.searchAttributes],
        scope: 'sub'
      }, (error, searchRes) => {
        if (error) {
          reject(new Error(`LDAP search failed: ${error.message}`));
          return;
        }
        
        let userFound = false;
        let userProfile = null;
        
        searchRes.on('searchEntry', (entry) => {
          userFound = true;
          userProfile = {
            dn: entry.dn.toString(),
            attributes: entry.object
          };
        });
        
        searchRes.on('end', (result) => {
          if (!userFound) {
            resolve(null);
          } else {
            resolve(userProfile);
          }
        });
        
        searchRes.on('error', (error) => {
          reject(new Error(`LDAP search error: ${error.message}`));
        });
      });
    });
  }

  async getLDAPUserGroups(client, provider, userProfile) {
    if (!provider.groupSearchBase) {
      return [];
    }
    
    const searchFilter = provider.groupSearchFilter.replace('{{dn}}', userProfile.dn);
    
    return new Promise((resolve, reject) => {
      const groups = [];
      
      client.search(provider.groupSearchBase, {
        filter: searchFilter,
        attributes: provider.groupSearchAttributes,
        scope: 'sub'
      }, (error, searchRes) => {
        if (error) {
          resolve([]); // Don't fail auth if group search fails
          return;
        }
        
        searchRes.on('searchEntry', (entry) => {
          groups.push({
            dn: entry.dn.toString(),
            attributes: entry.object
          });
        });
        
        searchRes.on('end', () => {
          resolve(groups);
        });
        
        searchRes.on('error', () => {
          resolve([]); // Don't fail auth if group search fails
        });
      });
    });
  }

  normalizeLDAPProfile(userProfile, groups, provider) {
    const attributeMap = this.attributeMappings.get(provider.id) || this.getDefaultLDAPAttributeMap();
    
    const attrs = userProfile.attributes;
    
    const normalized = {
      dn: userProfile.dn,
      
      // Map standard attributes
      email: attrs[attributeMap.email] || attrs.mail || attrs.userPrincipalName,
      username: attrs[attributeMap.username] || attrs.sAMAccountName || attrs.uid,
      firstName: attrs[attributeMap.firstName] || attrs.givenName,
      lastName: attrs[attributeMap.lastName] || attrs.sn,
      displayName: attrs[attributeMap.displayName] || attrs.displayName || attrs.cn,
      department: attrs[attributeMap.department] || attrs.department,
      title: attrs[attributeMap.title] || attrs.title,
      phone: attrs[attributeMap.phone] || attrs.telephoneNumber,
      manager: attrs[attributeMap.manager] || attrs.manager,
      
      // Extract group names
      groups: groups.map(group => group.attributes.cn || group.attributes.name).filter(Boolean),
      
      // Store all attributes
      attributes: attrs,
      
      // Metadata
      loginTime: new Date(),
      provider: provider.id
    };
    
    return normalized;
  }

  // User Provisioning
  async provisionUserFromSAML(provider, profile) {
    const provisioningRules = this.provisioningRules.get(provider.id) || this.getDefaultProvisioningRules();
    
    // Apply provisioning rules
    const shouldProvision = await this.evaluateProvisioningRules(provisioningRules, profile);
    if (!shouldProvision.allowed) {
      throw new Error(`User provisioning denied: ${shouldProvision.reason}`);
    }
    
    // Create user account
    const userId = await this.createUser({
      email: profile.email,
      firstName: profile.firstName,
      lastName: profile.lastName,
      displayName: profile.displayName,
      department: profile.department,
      title: profile.title,
      phone: profile.phone,
      
      // Enterprise-specific fields
      enterpriseProvider: 'saml',
      enterpriseProviderId: provider.id,
      provisionedAt: new Date(),
      
      // Set default role
      roles: [provider.defaultRole],
      
      // Email is verified for SAML users
      emailVerified: true
    });
    
    // Create enterprise user record
    const enterpriseUserId = this.generateEnterpriseUserId();
    const enterpriseUser = {
      id: enterpriseUserId,
      userId,
      provider: 'saml',
      providerId: provider.id,
      providerUserId: profile.nameID,
      
      profile,
      
      createdAt: new Date(),
      updatedAt: new Date(),
      lastLoginAt: new Date(),
      
      isActive: true,
      isProvisioned: true
    };
    
    this.enterpriseUsers.set(enterpriseUserId, enterpriseUser);
    
    this.emit('userProvisioned', {
      enterpriseUserId,
      userId,
      provider: 'saml',
      providerId: provider.id,
      email: profile.email
    });
    
    return enterpriseUser;
  }

  async provisionUserFromLDAP(provider, profile) {
    const provisioningRules = this.provisioningRules.get(provider.id) || this.getDefaultProvisioningRules();
    
    const shouldProvision = await this.evaluateProvisioningRules(provisioningRules, profile);
    if (!shouldProvision.allowed) {
      throw new Error(`User provisioning denied: ${shouldProvision.reason}`);
    }
    
    const userId = await this.createUser({
      email: profile.email,
      username: profile.username,
      firstName: profile.firstName,
      lastName: profile.lastName,
      displayName: profile.displayName,
      department: profile.department,
      title: profile.title,
      phone: profile.phone,
      
      enterpriseProvider: 'ldap',
      enterpriseProviderId: provider.id,
      provisionedAt: new Date(),
      
      roles: [provider.defaultRole],
      emailVerified: true
    });
    
    const enterpriseUserId = this.generateEnterpriseUserId();
    const enterpriseUser = {
      id: enterpriseUserId,
      userId,
      provider: 'ldap',
      providerId: provider.id,
      providerUserId: profile.dn,
      
      profile,
      
      createdAt: new Date(),
      updatedAt: new Date(),
      lastLoginAt: new Date(),
      
      isActive: true,
      isProvisioned: true
    };
    
    this.enterpriseUsers.set(enterpriseUserId, enterpriseUser);
    
    this.emit('userProvisioned', {
      enterpriseUserId,
      userId,
      provider: 'ldap',
      providerId: provider.id,
      email: profile.email
    });
    
    return enterpriseUser;
  }

  // Attribute and Group Mapping
  createAttributeMapping(providerId, mappingData) {
    const mapping = {
      providerId,
      
      // Standard attribute mappings
      email: mappingData.email || 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress',
      firstName: mappingData.firstName || 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname',
      lastName: mappingData.lastName || 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname',
      displayName: mappingData.displayName || 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name',
      department: mappingData.department || 'http://schemas.microsoft.com/ws/2008/06/identity/claims/department',
      title: mappingData.title || 'http://schemas.microsoft.com/ws/2008/06/identity/claims/title',
      phone: mappingData.phone || 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/homephone',
      manager: mappingData.manager || 'http://schemas.microsoft.com/ws/2008/06/identity/claims/manager',
      groups: mappingData.groups || 'http://schemas.microsoft.com/ws/2008/06/identity/claims/groups',
      
      // Custom attribute mappings
      customMappings: mappingData.customMappings || {},
      
      createdAt: new Date(),
      updatedAt: new Date()
    };
    
    this.attributeMappings.set(providerId, mapping);
    
    this.emit('attributeMappingCreated', { providerId, mapping });
    return mapping;
  }

  createGroupMapping(providerId, mappingData) {
    const mapping = {
      providerId,
      mappings: mappingData.mappings || {}, // { 'LDAP Group': 'Application Role' }
      defaultRole: mappingData.defaultRole || 'user',
      
      // Group mapping rules
      rules: mappingData.rules || [],
      
      createdAt: new Date(),
      updatedAt: new Date()
    };
    
    this.groupMappings.set(providerId, mapping);
    
    this.emit('groupMappingCreated', { providerId, mapping });
    return mapping;
  }

  async applyAttributeMappings(enterpriseUserId, attributes, providerId) {
    const enterpriseUser = this.enterpriseUsers.get(enterpriseUserId);
    if (!enterpriseUser) {
      return;
    }
    
    const mapping = this.attributeMappings.get(providerId);
    if (!mapping) {
      return;
    }
    
    const updates = {};
    
    // Apply custom mappings
    for (const [localAttribute, providerAttribute] of Object.entries(mapping.customMappings)) {
      if (attributes[providerAttribute]) {
        updates[localAttribute] = attributes[providerAttribute];
      }
    }
    
    if (Object.keys(updates).length > 0) {
      await this.updateUser(enterpriseUser.userId, updates);
      
      this.emit('attributesApplied', {
        enterpriseUserId,
        userId: enterpriseUser.userId,
        providerId,
        updates
      });
    }
  }

  async syncUserGroups(enterpriseUserId, providerGroups, providerId) {
    const enterpriseUser = this.enterpriseUsers.get(enterpriseUserId);
    if (!enterpriseUser) {
      return;
    }
    
    const groupMapping = this.groupMappings.get(providerId);
    if (!groupMapping) {
      return;
    }
    
    const mappedRoles = [];
    
    // Map groups to roles
    for (const group of providerGroups) {
      if (groupMapping.mappings[group]) {
        mappedRoles.push(groupMapping.mappings[group]);
      }
    }
    
    // Add default role if no roles mapped
    if (mappedRoles.length === 0) {
      mappedRoles.push(groupMapping.defaultRole);
    }
    
    // Update user roles
    await this.updateUserRoles(enterpriseUser.userId, mappedRoles);
    
    this.emit('groupsSynced', {
      enterpriseUserId,
      userId: enterpriseUser.userId,
      providerId,
      providerGroups,
      mappedRoles
    });
  }

  // Provisioning Rules
  createProvisioningRule(providerId, ruleData) {
    const rules = this.provisioningRules.get(providerId) || { rules: [] };
    
    const rule = {
      id: ruleData.id || this.generateRuleId(),
      name: ruleData.name,
      description: ruleData.description,
      
      // Rule conditions
      conditions: ruleData.conditions || [],
      
      // Rule action
      action: ruleData.action || 'allow', // 'allow', 'deny'
      
      // Priority
      priority: ruleData.priority || 0,
      
      enabled: ruleData.enabled !== false,
      createdAt: new Date()
    };
    
    rules.rules.push(rule);
    rules.rules.sort((a, b) => b.priority - a.priority);
    
    this.provisioningRules.set(providerId, rules);
    
    this.emit('provisioningRuleCreated', { providerId, rule });
    return rule;
  }

  async evaluateProvisioningRules(rules, profile) {
    for (const rule of rules.rules || []) {
      if (!rule.enabled) {
        continue;
      }
      
      const ruleMatches = await this.evaluateRuleConditions(rule.conditions, profile);
      
      if (ruleMatches) {
        return {
          allowed: rule.action === 'allow',
          reason: rule.action === 'deny' ? rule.name : null,
          rule: rule.id
        };
      }
    }
    
    // Default to allow if no rules match
    return { allowed: true };
  }

  async evaluateRuleConditions(conditions, profile) {
    for (const condition of conditions) {
      const result = await this.evaluateCondition(condition, profile);
      if (!result) {
        return false;
      }
    }
    
    return true;
  }

  async evaluateCondition(condition, profile) {
    switch (condition.type) {
      case 'attribute_equals':
        return profile.attributes[condition.attribute] === condition.value;
        
      case 'attribute_contains':
        const attrValue = profile.attributes[condition.attribute];
        return attrValue && attrValue.includes && attrValue.includes(condition.value);
        
      case 'email_domain':
        return profile.email && profile.email.endsWith(`@${condition.domain}`);
        
      case 'group_member':
        return profile.groups && profile.groups.includes(condition.group);
        
      default:
        return true;
    }
  }

  // SAML Metadata Generation
  generateSAMLMetadata(providerId) {
    const provider = this.samlProviders.get(providerId);
    if (!provider) {
      throw new Error(`SAML provider ${providerId} not found`);
    }
    
    const entityId = `${this.options.entityId}-${providerId}`;
    const cert = this.loadPublicCert();
    
    return `<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" entityID="${entityId}">
  <md:SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol" 
                     WantAssertionsSigned="${provider.wantAssertionsSigned}" 
                     AuthnRequestsSigned="true">
    <md:KeyDescriptor use="signing">
      <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
        <ds:X509Data>
          <ds:X509Certificate>${cert}</ds:X509Certificate>
        </ds:X509Data>
      </ds:KeyInfo>
    </md:KeyDescriptor>
    <md:KeyDescriptor use="encryption">
      <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
        <ds:X509Data>
          <ds:X509Certificate>${cert}</ds:X509Certificate>
        </ds:X509Data>
      </ds:KeyInfo>
    </md:KeyDescriptor>
    <md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</md:NameIDFormat>
    <md:NameIDFormat>urn:oasis:names:tc:SAML:2.0:nameid-format:transient</md:NameIDFormat>
    <md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" 
                                Location="${provider.callbackUrl}" 
                                index="1" isDefault="true"/>
  </md:SPSSODescriptor>
</md:EntityDescriptor>`;
  }

  // Testing and Validation
  async testSAMLProvider(providerId) {
    const provider = this.samlProviders.get(providerId);
    if (!provider) {
      throw new Error(`SAML provider ${providerId} not found`);
    }
    
    try {
      // Test certificate validity
      if (!this.validateCertificate(provider.cert)) {
        throw new Error('Invalid IdP certificate');
      }
      
      // Test connectivity to IdP (this would be implemented based on provider)
      // For now, just check if required fields are present
      if (!provider.entryPoint || !provider.issuer) {
        throw new Error('Missing required SAML configuration');
      }
      
      this.emit('samlProviderTested', { providerId, status: 'success' });
      return { success: true, message: 'SAML provider configuration is valid' };
      
    } catch (error) {
      this.emit('samlProviderTested', { providerId, status: 'failed', error: error.message });
      throw error;
    }
  }

  async testLDAPConnection(providerId) {
    const provider = this.ldapConnections.get(providerId);
    if (!provider) {
      throw new Error(`LDAP provider ${providerId} not found`);
    }
    
    const client = ldap.createClient({
      url: provider.url,
      timeout: provider.timeout,
      connectTimeout: provider.connectTimeout,
      tlsOptions: provider.tlsOptions
    });
    
    try {
      await this.bindLDAPClient(client, provider.bindDN, provider.bindCredentials);
      
      this.emit('ldapProviderTested', { providerId, status: 'success' });
      return { success: true, message: 'LDAP connection successful' };
      
    } catch (error) {
      this.emit('ldapProviderTested', { providerId, status: 'failed', error: error.message });
      throw error;
    } finally {
      client.unbind();
    }
  }

  // Utility Methods
  findEnterpriseUserByEmail(email) {
    return Array.from(this.enterpriseUsers.values())
      .find(user => user.profile.email === email && user.isActive);
  }

  async updateEnterpriseUser(enterpriseUserId, updates) {
    const user = this.enterpriseUsers.get(enterpriseUserId);
    if (!user) {
      throw new Error(`Enterprise user ${enterpriseUserId} not found`);
    }
    
    const updatedUser = {
      ...user,
      ...updates,
      updatedAt: new Date()
    };
    
    this.enterpriseUsers.set(enterpriseUserId, updatedUser);
    return updatedUser;
  }

  generateEnterpriseUserId() {
    return `ent_${Date.now()}_${crypto.randomBytes(8).toString('hex')}`;
  }

  generateRuleId() {
    return `rule_${Date.now()}_${crypto.randomBytes(4).toString('hex')}`;
  }

  validateCertificate(cert) {
    // Basic certificate validation
    return cert && cert.includes('-----BEGIN CERTIFICATE-----');
  }

  loadPrivateKey() {
    // Load private key for SAML signing
    return process.env.SAML_PRIVATE_KEY || '';
  }

  loadPublicCert() {
    // Load public certificate for SAML
    return process.env.SAML_PUBLIC_CERT || '';
  }

  // Default Configurations
  setupDefaultMappings() {
    // Default SAML attribute mappings
    this.defaultSAMLAttributeMap = {
      email: 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress',
      firstName: 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname',
      lastName: 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname',
      displayName: 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name',
      department: 'http://schemas.microsoft.com/ws/2008/06/identity/claims/department',
      title: 'http://schemas.microsoft.com/ws/2008/06/identity/claims/title',
      phone: 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/homephone',
      manager: 'http://schemas.microsoft.com/ws/2008/06/identity/claims/manager',
      groups: 'http://schemas.microsoft.com/ws/2008/06/identity/claims/groups'
    };
    
    // Default LDAP attribute mappings
    this.defaultLDAPAttributeMap = {
      email: 'mail',
      username: 'sAMAccountName',
      firstName: 'givenName',
      lastName: 'sn',
      displayName: 'displayName',
      department: 'department',
      title: 'title',
      phone: 'telephoneNumber',
      manager: 'manager'
    };
  }

  getDefaultSAMLAttributeMap() {
    return this.defaultSAMLAttributeMap;
  }

  getDefaultLDAPAttributeMap() {
    return this.defaultLDAPAttributeMap;
  }

  getDefaultProvisioningRules() {
    return {
      rules: [
        {
          id: 'default-allow',
          name: 'Default Allow',
          description: 'Allow all users by default',
          conditions: [],
          action: 'allow',
          priority: 0,
          enabled: true
        }
      ]
    };
  }

  // Integration Methods (to be implemented)
  async createUser(userData) {
    // Integration with user management system
    return `user_${Date.now()}_${crypto.randomBytes(8).toString('hex')}`;
  }

  async updateUser(userId, updates) {
    // Integration with user management system
    return true;
  }

  async updateUserRoles(userId, roles) {
    // Integration with RBAC system
    return true;
  }

  // Statistics and Monitoring
  getStats() {
    return {
      samlProviders: this.samlProviders.size,
      ldapProviders: this.ldapConnections.size,
      enterpriseUsers: this.enterpriseUsers.size,
      attributeMappings: this.attributeMappings.size,
      groupMappings: this.groupMappings.size,
      provisioningRules: Array.from(this.provisioningRules.values()).reduce((total, rules) => total + rules.rules.length, 0)
    };
  }

  getSAMLProviders() {
    return Array.from(this.samlProviders.values());
  }

  getLDAPProviders() {
    return Array.from(this.ldapConnections.values());
  }

  reset() {
    this.samlProviders.clear();
    this.ldapConnections.clear();
    this.enterpriseUsers.clear();
    this.attributeMappings.clear();
    this.groupMappings.clear();
    this.provisioningRules.clear();
  }
}

module.exports = EnterpriseSSO;