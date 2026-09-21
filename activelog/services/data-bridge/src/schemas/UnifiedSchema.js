const { EventEmitter } = require('events');
const Joi = require('joi');

class UnifiedSchema extends EventEmitter {
    constructor() {
        super();
        this.schemas = new Map();
        this.entityTypes = new Map();
        this.relationships = new Map();
        this.versionHistory = new Map();
        this.validationCache = new Map();
        
        this.initializeCoreSchemas();
        this.setupEventHandlers();
    }

    initializeCoreSchemas() {
        // Core entity schemas
        const baseEntitySchema = {
            id: Joi.string().uuid().required(),
            type: Joi.string().required(),
            version: Joi.string().default('1.0.0'),
            createdAt: Joi.date().iso().default(() => new Date()),
            updatedAt: Joi.date().iso().default(() => new Date()),
            createdBy: Joi.string().uuid(),
            updatedBy: Joi.string().uuid(),
            tenantId: Joi.string().uuid(),
            source: Joi.string().required(),
            metadata: Joi.object().default({})
        };

        // User entity schema
        this.registerSchema('user', Joi.object({
            ...baseEntitySchema,
            email: Joi.string().email().required(),
            username: Joi.string().alphanum().min(3).max(30),
            firstName: Joi.string().max(50),
            lastName: Joi.string().max(50),
            avatar: Joi.string().uri(),
            preferences: Joi.object().default({}),
            roles: Joi.array().items(Joi.string()).default([]),
            status: Joi.string().valid('active', 'inactive', 'suspended').default('active'),
            lastLoginAt: Joi.date().iso(),
            loginCount: Joi.number().integer().min(0).default(0)
        }));

        // Document/Log entry schema
        this.registerSchema('document', Joi.object({
            ...baseEntitySchema,
            title: Joi.string().max(200).required(),
            content: Joi.string(),
            tags: Joi.array().items(Joi.string()).default([]),
            category: Joi.string(),
            priority: Joi.string().valid('low', 'medium', 'high', 'critical').default('medium'),
            status: Joi.string().valid('draft', 'published', 'archived').default('draft'),
            attachments: Joi.array().items(Joi.object({
                id: Joi.string().uuid(),
                filename: Joi.string(),
                mimeType: Joi.string(),
                size: Joi.number().integer(),
                url: Joi.string().uri()
            })).default([]),
            permissions: Joi.object({
                read: Joi.array().items(Joi.string()).default([]),
                write: Joi.array().items(Joi.string()).default([]),
                delete: Joi.array().items(Joi.string()).default([])
            }).default({})
        }));

        // Project/Business entity schema
        this.registerSchema('project', Joi.object({
            ...baseEntitySchema,
            name: Joi.string().max(100).required(),
            description: Joi.string(),
            startDate: Joi.date().iso(),
            endDate: Joi.date().iso(),
            status: Joi.string().valid('planning', 'active', 'on-hold', 'completed', 'cancelled').default('planning'),
            budget: Joi.object({
                amount: Joi.number().min(0),
                currency: Joi.string().length(3).default('USD')
            }),
            team: Joi.array().items(Joi.object({
                userId: Joi.string().uuid(),
                role: Joi.string(),
                permissions: Joi.array().items(Joi.string())
            })).default([]),
            milestones: Joi.array().items(Joi.object({
                id: Joi.string().uuid(),
                name: Joi.string(),
                dueDate: Joi.date().iso(),
                status: Joi.string().valid('pending', 'completed')
            })).default([])
        }));

        // Activity/Event schema
        this.registerSchema('activity', Joi.object({
            ...baseEntitySchema,
            action: Joi.string().required(),
            entityType: Joi.string().required(),
            entityId: Joi.string().uuid().required(),
            description: Joi.string(),
            data: Joi.object().default({}),
            ipAddress: Joi.string().ip(),
            userAgent: Joi.string(),
            timestamp: Joi.date().iso().default(() => new Date()),
            severity: Joi.string().valid('info', 'warning', 'error', 'critical').default('info')
        }));

        // Comment/Note schema
        this.registerSchema('comment', Joi.object({
            ...baseEntitySchema,
            content: Joi.string().required(),
            parentId: Joi.string().uuid(),
            entityType: Joi.string().required(),
            entityId: Joi.string().uuid().required(),
            mentions: Joi.array().items(Joi.string().uuid()).default([]),
            reactions: Joi.object().pattern(
                Joi.string(),
                Joi.array().items(Joi.string().uuid())
            ).default({})
        }));

        // File/Asset schema
        this.registerSchema('asset', Joi.object({
            ...baseEntitySchema,
            filename: Joi.string().required(),
            originalFilename: Joi.string(),
            mimeType: Joi.string().required(),
            size: Joi.number().integer().min(0).required(),
            hash: Joi.string().required(),
            url: Joi.string().uri(),
            thumbnails: Joi.object().pattern(
                Joi.string(),
                Joi.string().uri()
            ).default({}),
            exifData: Joi.object().default({}),
            virusScanResult: Joi.object({
                clean: Joi.boolean(),
                scanDate: Joi.date().iso(),
                scanner: Joi.string()
            })
        }));

        this.emit('schemas:initialized');
    }

    registerSchema(entityType, schema, options = {}) {
        const schemaInfo = {
            schema,
            version: options.version || '1.0.0',
            description: options.description || '',
            createdAt: new Date(),
            ...options
        };

        this.schemas.set(entityType, schemaInfo);
        this.entityTypes.set(entityType, {
            ...schemaInfo,
            relationships: new Set()
        });

        // Store version history
        const versionKey = `${entityType}:${schemaInfo.version}`;
        this.versionHistory.set(versionKey, schemaInfo);

        this.emit('schema:registered', { entityType, schema: schemaInfo });
        return this;
    }

    getSchema(entityType, version = null) {
        if (version) {
            const versionKey = `${entityType}:${version}`;
            return this.versionHistory.get(versionKey);
        }
        return this.schemas.get(entityType);
    }

    getAllSchemas() {
        const schemas = {};
        for (const [entityType, schemaInfo] of this.schemas) {
            schemas[entityType] = schemaInfo;
        }
        return schemas;
    }

    validateEntity(entityType, data, options = {}) {
        const cacheKey = `${entityType}:${JSON.stringify(data)}`;
        
        if (!options.skipCache && this.validationCache.has(cacheKey)) {
            const cached = this.validationCache.get(cacheKey);
            if (Date.now() - cached.timestamp < 300000) { // 5 minutes
                return cached.result;
            }
        }

        const schemaInfo = this.getSchema(entityType);
        if (!schemaInfo) {
            return {
                valid: false,
                errors: [`Unknown entity type: ${entityType}`]
            };
        }

        const { error, value } = schemaInfo.schema.validate(data, {
            abortEarly: false,
            stripUnknown: options.stripUnknown !== false,
            ...options
        });

        const result = {
            valid: !error,
            errors: error ? error.details.map(d => d.message) : [],
            data: value,
            entityType,
            timestamp: new Date()
        };

        // Cache validation result
        this.validationCache.set(cacheKey, {
            result,
            timestamp: Date.now()
        });

        this.emit('validation:completed', result);
        return result;
    }

    defineRelationship(fromType, toType, relationshipType, options = {}) {
        const relationship = {
            from: fromType,
            to: toType,
            type: relationshipType,
            cardinality: options.cardinality || 'many-to-many',
            cascadeDelete: options.cascadeDelete || false,
            required: options.required || false,
            metadata: options.metadata || {},
            createdAt: new Date()
        };

        const relationshipKey = `${fromType}:${toType}:${relationshipType}`;
        this.relationships.set(relationshipKey, relationship);

        // Update entity type relationships
        if (this.entityTypes.has(fromType)) {
            this.entityTypes.get(fromType).relationships.add(relationshipKey);
        }
        if (this.entityTypes.has(toType)) {
            this.entityTypes.get(toType).relationships.add(relationshipKey);
        }

        this.emit('relationship:defined', relationship);
        return relationship;
    }

    getRelationships(entityType) {
        const relationships = [];
        for (const [key, relationship] of this.relationships) {
            if (relationship.from === entityType || relationship.to === entityType) {
                relationships.push(relationship);
            }
        }
        return relationships;
    }

    transformEntity(data, fromType, toType, options = {}) {
        const fromSchema = this.getSchema(fromType);
        const toSchema = this.getSchema(toType);

        if (!fromSchema || !toSchema) {
            throw new Error(`Schema not found for transformation: ${fromType} -> ${toType}`);
        }

        // First validate source data
        const validation = this.validateEntity(fromType, data);
        if (!validation.valid) {
            throw new Error(`Invalid source data: ${validation.errors.join(', ')}`);
        }

        // Apply transformation rules
        const transformedData = this.applyTransformationRules(
            validation.data,
            fromType,
            toType,
            options.rules || {}
        );

        // Validate transformed data
        const targetValidation = this.validateEntity(toType, transformedData);
        if (!targetValidation.valid && !options.allowPartial) {
            throw new Error(`Transformation failed validation: ${targetValidation.errors.join(', ')}`);
        }

        this.emit('entity:transformed', {
            from: { type: fromType, data },
            to: { type: toType, data: targetValidation.data },
            timestamp: new Date()
        });

        return targetValidation.data;
    }

    applyTransformationRules(data, fromType, toType, rules) {
        const transformed = { ...data };
        
        // Apply field mapping rules
        if (rules.fieldMappings) {
            for (const [sourceField, targetField] of Object.entries(rules.fieldMappings)) {
                if (data[sourceField] !== undefined) {
                    transformed[targetField] = data[sourceField];
                    if (sourceField !== targetField) {
                        delete transformed[sourceField];
                    }
                }
            }
        }

        // Apply value transformation rules
        if (rules.valueTransformations) {
            for (const [field, transformer] of Object.entries(rules.valueTransformations)) {
                if (transformed[field] !== undefined) {
                    if (typeof transformer === 'function') {
                        transformed[field] = transformer(transformed[field]);
                    } else if (typeof transformer === 'object') {
                        transformed[field] = transformer[transformed[field]] || transformed[field];
                    }
                }
            }
        }

        // Apply default values for target type
        const toSchema = this.getSchema(toType);
        if (toSchema) {
            const { error, value } = toSchema.schema.validate(transformed, {
                stripUnknown: false
            });
            if (!error) {
                Object.assign(transformed, value);
            }
        }

        return transformed;
    }

    generateOpenAPISchema(entityType) {
        const schemaInfo = this.getSchema(entityType);
        if (!schemaInfo) {
            return null;
        }

        return this.joiToOpenAPI(schemaInfo.schema);
    }

    joiToOpenAPI(joiSchema) {
        // Simplified Joi to OpenAPI conversion
        const convert = (schema) => {
            const describe = schema.describe();
            const openApiSchema = {};

            switch (describe.type) {
                case 'string':
                    openApiSchema.type = 'string';
                    if (describe.rules) {
                        describe.rules.forEach(rule => {
                            if (rule.name === 'email') openApiSchema.format = 'email';
                            if (rule.name === 'uri') openApiSchema.format = 'uri';
                            if (rule.name === 'uuid') openApiSchema.format = 'uuid';
                            if (rule.name === 'min') openApiSchema.minLength = rule.args.limit;
                            if (rule.name === 'max') openApiSchema.maxLength = rule.args.limit;
                        });
                    }
                    if (describe.allow) {
                        openApiSchema.enum = describe.allow;
                    }
                    break;
                case 'number':
                    openApiSchema.type = 'number';
                    if (describe.rules) {
                        describe.rules.forEach(rule => {
                            if (rule.name === 'integer') openApiSchema.type = 'integer';
                            if (rule.name === 'min') openApiSchema.minimum = rule.args.limit;
                            if (rule.name === 'max') openApiSchema.maximum = rule.args.limit;
                        });
                    }
                    break;
                case 'boolean':
                    openApiSchema.type = 'boolean';
                    break;
                case 'date':
                    openApiSchema.type = 'string';
                    openApiSchema.format = 'date-time';
                    break;
                case 'array':
                    openApiSchema.type = 'array';
                    if (describe.items && describe.items.length > 0) {
                        openApiSchema.items = convert(describe.items[0]);
                    }
                    break;
                case 'object':
                    openApiSchema.type = 'object';
                    if (describe.keys) {
                        openApiSchema.properties = {};
                        const required = [];
                        for (const [key, keySchema] of Object.entries(describe.keys)) {
                            openApiSchema.properties[key] = convert(keySchema);
                            if (keySchema.flags && keySchema.flags.presence === 'required') {
                                required.push(key);
                            }
                        }
                        if (required.length > 0) {
                            openApiSchema.required = required;
                        }
                    }
                    break;
            }

            if (describe.flags && describe.flags.default !== undefined) {
                openApiSchema.default = describe.flags.default;
            }

            return openApiSchema;
        };

        return convert(joiSchema);
    }

    setupEventHandlers() {
        this.on('validation:completed', (result) => {
            if (!result.valid) {
                console.warn(`Validation failed for ${result.entityType}:`, result.errors);
            }
        });

        this.on('schema:registered', ({ entityType, schema }) => {
            console.log(`Schema registered for entity type: ${entityType}`);
        });

        // Clean validation cache periodically
        setInterval(() => {
            const now = Date.now();
            for (const [key, cached] of this.validationCache) {
                if (now - cached.timestamp > 1800000) { // 30 minutes
                    this.validationCache.delete(key);
                }
            }
        }, 600000); // Clean every 10 minutes
    }

    getStats() {
        return {
            schemas: this.schemas.size,
            entityTypes: this.entityTypes.size,
            relationships: this.relationships.size,
            versionHistory: this.versionHistory.size,
            validationCacheSize: this.validationCache.size,
            supportedTypes: Array.from(this.schemas.keys())
        };
    }

    reset() {
        this.schemas.clear();
        this.entityTypes.clear();
        this.relationships.clear();
        this.versionHistory.clear();
        this.validationCache.clear();
        this.initializeCoreSchemas();
        this.emit('reset');
    }
}

module.exports = UnifiedSchema;