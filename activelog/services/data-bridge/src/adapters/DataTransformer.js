const { EventEmitter } = require('events');
const crypto = require('crypto');
const jsonpath = require('jsonpath');
const dot = require('dot');

class DataTransformer extends EventEmitter {
    constructor(options = {}) {
        super();
        this.adapters = new Map();
        this.transformations = new Map();
        this.templates = new Map();
        this.cache = new Map();
        this.statistics = new Map();
        this.errorHandlers = new Map();
        this.validationRules = new Map();
        
        this.cacheSize = options.cacheSize || 1000;
        this.cacheTTL = options.cacheTTL || 300000; // 5 minutes
        
        this.initializeBuiltInAdapters();
        this.setupEventHandlers();
    }

    initializeBuiltInAdapters() {
        // JSON to JSON transformer
        this.registerAdapter('json-to-json', {
            name: 'JSON to JSON Transformer',
            sourceFormat: 'json',
            targetFormat: 'json',
            transformer: async (data, config) => {
                return this.applyJSONTransformation(data, config);
            }
        });

        // CSV to JSON transformer
        this.registerAdapter('csv-to-json', {
            name: 'CSV to JSON Transformer',
            sourceFormat: 'csv',
            targetFormat: 'json',
            transformer: async (data, config) => {
                return this.csvToJson(data, config);
            }
        });

        // JSON to CSV transformer
        this.registerAdapter('json-to-csv', {
            name: 'JSON to CSV Transformer',
            sourceFormat: 'json',
            targetFormat: 'csv',
            transformer: async (data, config) => {
                return this.jsonToCsv(data, config);
            }
        });

        // XML to JSON transformer
        this.registerAdapter('xml-to-json', {
            name: 'XML to JSON Transformer',
            sourceFormat: 'xml',
            targetFormat: 'json',
            transformer: async (data, config) => {
                return this.xmlToJson(data, config);
            }
        });

        // Personal Log to Business Log transformer
        this.registerAdapter('personal-to-business', {
            name: 'Personal Log to Business Log Transformer',
            sourceFormat: 'personal-log',
            targetFormat: 'business-log',
            transformer: async (data, config) => {
                return this.personalToBusinessTransform(data, config);
            }
        });

        // Business Log to Personal Log transformer
        this.registerAdapter('business-to-personal', {
            name: 'Business Log to Personal Log Transformer',
            sourceFormat: 'business-log',
            targetFormat: 'personal-log',
            transformer: async (data, config) => {
                return this.businessToPersonalTransform(data, config);
            }
        });

        // Normalization transformer
        this.registerAdapter('normalize', {
            name: 'Data Normalizer',
            sourceFormat: 'any',
            targetFormat: 'normalized',
            transformer: async (data, config) => {
                return this.normalizeData(data, config);
            }
        });

        // Denormalization transformer
        this.registerAdapter('denormalize', {
            name: 'Data Denormalizer',
            sourceFormat: 'normalized',
            targetFormat: 'any',
            transformer: async (data, config) => {
                return this.denormalizeData(data, config);
            }
        });
    }

    registerAdapter(adapterId, config) {
        const adapter = {
            id: adapterId,
            name: config.name || adapterId,
            sourceFormat: config.sourceFormat,
            targetFormat: config.targetFormat,
            transformer: config.transformer,
            validator: config.validator,
            errorHandler: config.errorHandler,
            metadata: config.metadata || {},
            registeredAt: new Date(),
            usageCount: 0,
            successCount: 0,
            errorCount: 0
        };

        this.adapters.set(adapterId, adapter);
        this.emit('adapter:registered', adapter);
        return adapter;
    }

    async transform(data, sourceFormat, targetFormat, options = {}) {
        const transformId = crypto.randomUUID();
        const startTime = Date.now();
        
        const transformInfo = {
            id: transformId,
            sourceFormat,
            targetFormat,
            dataSize: this.calculateDataSize(data),
            startTime: new Date(),
            options
        };

        this.emit('transform:started', transformInfo);

        try {
            // Check cache first
            const cacheKey = this.generateCacheKey(data, sourceFormat, targetFormat, options);
            if (!options.skipCache && this.cache.has(cacheKey)) {
                const cached = this.cache.get(cacheKey);
                if (Date.now() - cached.timestamp < this.cacheTTL) {
                    this.emit('transform:cache-hit', { transformId, cacheKey });
                    return cached.result;
                }
            }

            // Find appropriate adapter
            const adapter = this.findAdapter(sourceFormat, targetFormat, options);
            if (!adapter) {
                throw new Error(`No adapter found for transformation: ${sourceFormat} -> ${targetFormat}`);
            }

            // Validate input data if validator exists
            if (adapter.validator) {
                await this.validateInput(data, adapter.validator, sourceFormat);
            }

            // Apply transformation
            const transformed = await this.executeTransformation(
                adapter,
                data,
                options,
                transformInfo
            );

            // Validate output data
            if (options.validateOutput !== false) {
                await this.validateOutput(transformed, targetFormat, options);
            }

            // Cache result
            this.cache.set(cacheKey, {
                result: transformed,
                timestamp: Date.now()
            });

            // Update statistics
            this.updateAdapterStats(adapter.id, true, Date.now() - startTime);
            
            transformInfo.endTime = new Date();
            transformInfo.duration = Date.now() - startTime;
            transformInfo.success = true;

            this.emit('transform:completed', {
                ...transformInfo,
                resultSize: this.calculateDataSize(transformed)
            });

            return transformed;

        } catch (error) {
            this.updateAdapterStats(adapter?.id, false, Date.now() - startTime);
            
            transformInfo.endTime = new Date();
            transformInfo.error = error.message;
            transformInfo.success = false;

            this.emit('transform:failed', transformInfo);
            throw error;
        }
    }

    findAdapter(sourceFormat, targetFormat, options = {}) {
        // Direct match
        for (const [id, adapter] of this.adapters) {
            if (adapter.sourceFormat === sourceFormat && adapter.targetFormat === targetFormat) {
                return adapter;
            }
        }

        // Wildcard match
        for (const [id, adapter] of this.adapters) {
            if ((adapter.sourceFormat === 'any' || adapter.sourceFormat === sourceFormat) &&
                (adapter.targetFormat === 'any' || adapter.targetFormat === targetFormat)) {
                return adapter;
            }
        }

        // Custom adapter specified in options
        if (options.adapterId && this.adapters.has(options.adapterId)) {
            return this.adapters.get(options.adapterId);
        }

        return null;
    }

    async executeTransformation(adapter, data, options, transformInfo) {
        adapter.usageCount++;
        
        const config = {
            ...options,
            transformId: transformInfo.id,
            sourceFormat: transformInfo.sourceFormat,
            targetFormat: transformInfo.targetFormat
        };

        try {
            const result = await adapter.transformer(data, config);
            adapter.successCount++;
            return result;
        } catch (error) {
            adapter.errorCount++;
            
            // Try error handler if available
            if (adapter.errorHandler) {
                return await adapter.errorHandler(error, data, config);
            }
            
            throw error;
        }
    }

    async applyJSONTransformation(data, config) {
        let transformed = { ...data };

        // Apply field mappings
        if (config.fieldMappings) {
            transformed = this.applyFieldMappings(transformed, config.fieldMappings);
        }

        // Apply value transformations
        if (config.valueTransformations) {
            transformed = await this.applyValueTransformations(transformed, config.valueTransformations);
        }

        // Apply JSONPath extractions
        if (config.extractions) {
            transformed = this.applyExtractions(transformed, config.extractions);
        }

        // Apply templates
        if (config.template) {
            transformed = this.applyTemplate(transformed, config.template);
        }

        // Apply filters
        if (config.filters) {
            transformed = this.applyFilters(transformed, config.filters);
        }

        return transformed;
    }

    applyFieldMappings(data, mappings) {
        const result = {};
        
        for (const [sourcePath, targetPath] of Object.entries(mappings)) {
            const value = jsonpath.value(data, sourcePath);
            if (value !== undefined) {
                this.setNestedValue(result, targetPath, value);
            }
        }

        // Include unmapped fields if specified
        if (mappings._includeUnmapped !== false) {
            const mappedPaths = Object.keys(mappings);
            this.includeUnmappedFields(data, result, mappedPaths);
        }

        return result;
    }

    async applyValueTransformations(data, transformations) {
        const result = { ...data };

        for (const [path, transformation] of Object.entries(transformations)) {
            const value = jsonpath.value(result, path);
            if (value !== undefined) {
                const transformedValue = await this.applyValueTransformation(value, transformation);
                jsonpath.value(result, path, transformedValue);
            }
        }

        return result;
    }

    async applyValueTransformation(value, transformation) {
        if (typeof transformation === 'function') {
            return await transformation(value);
        }

        if (typeof transformation === 'object') {
            const { type, ...params } = transformation;

            switch (type) {
                case 'format':
                    return this.formatValue(value, params);
                case 'convert':
                    return this.convertValue(value, params);
                case 'replace':
                    return this.replaceValue(value, params);
                case 'calculate':
                    return this.calculateValue(value, params);
                case 'lookup':
                    return this.lookupValue(value, params);
                default:
                    throw new Error(`Unknown transformation type: ${type}`);
            }
        }

        return value;
    }

    formatValue(value, params) {
        switch (params.format) {
            case 'date':
                return new Date(value).toISOString();
            case 'currency':
                return new Intl.NumberFormat('en-US', {
                    style: 'currency',
                    currency: params.currency || 'USD'
                }).format(value);
            case 'percentage':
                return `${(value * 100).toFixed(params.decimals || 2)}%`;
            case 'uppercase':
                return String(value).toUpperCase();
            case 'lowercase':
                return String(value).toLowerCase();
            case 'trim':
                return String(value).trim();
            default:
                return value;
        }
    }

    convertValue(value, params) {
        switch (params.to) {
            case 'string':
                return String(value);
            case 'number':
                return Number(value);
            case 'boolean':
                return Boolean(value);
            case 'date':
                return new Date(value);
            case 'array':
                return Array.isArray(value) ? value : [value];
            default:
                return value;
        }
    }

    replaceValue(value, params) {
        const str = String(value);
        if (params.regex) {
            const regex = new RegExp(params.pattern, params.flags || 'g');
            return str.replace(regex, params.replacement || '');
        } else {
            return str.replace(params.pattern, params.replacement || '');
        }
    }

    calculateValue(value, params) {
        switch (params.operation) {
            case 'add':
                return Number(value) + (params.operand || 0);
            case 'subtract':
                return Number(value) - (params.operand || 0);
            case 'multiply':
                return Number(value) * (params.operand || 1);
            case 'divide':
                return Number(value) / (params.operand || 1);
            case 'modulo':
                return Number(value) % (params.operand || 1);
            case 'power':
                return Math.pow(Number(value), params.operand || 2);
            default:
                return value;
        }
    }

    lookupValue(value, params) {
        if (params.table && typeof params.table === 'object') {
            return params.table[value] || params.default || value;
        }
        return value;
    }

    applyExtractions(data, extractions) {
        const result = {};

        for (const [key, path] of Object.entries(extractions)) {
            const extracted = jsonpath.query(data, path);
            result[key] = extracted.length === 1 ? extracted[0] : extracted;
        }

        return result;
    }

    applyTemplate(data, templateConfig) {
        if (typeof templateConfig === 'string') {
            // Simple template string
            const template = dot.template(templateConfig);
            return template(data);
        }

        if (typeof templateConfig === 'object') {
            const result = {};
            for (const [key, templateStr] of Object.entries(templateConfig)) {
                const template = dot.template(templateStr);
                result[key] = template(data);
            }
            return result;
        }

        return data;
    }

    applyFilters(data, filters) {
        let result = data;

        for (const filter of filters) {
            switch (filter.type) {
                case 'include':
                    result = this.includeFields(result, filter.fields);
                    break;
                case 'exclude':
                    result = this.excludeFields(result, filter.fields);
                    break;
                case 'condition':
                    result = this.applyConditionFilter(result, filter);
                    break;
            }
        }

        return result;
    }

    includeFields(data, fields) {
        const result = {};
        for (const field of fields) {
            if (data.hasOwnProperty(field)) {
                result[field] = data[field];
            }
        }
        return result;
    }

    excludeFields(data, fields) {
        const result = { ...data };
        for (const field of fields) {
            delete result[field];
        }
        return result;
    }

    applyConditionFilter(data, filter) {
        // Simple condition evaluation
        const { field, operator, value } = filter.condition;
        const fieldValue = jsonpath.value(data, field);

        let passes = false;
        switch (operator) {
            case 'equals':
                passes = fieldValue === value;
                break;
            case 'not_equals':
                passes = fieldValue !== value;
                break;
            case 'greater_than':
                passes = fieldValue > value;
                break;
            case 'less_than':
                passes = fieldValue < value;
                break;
            case 'contains':
                passes = String(fieldValue).includes(value);
                break;
        }

        return passes ? data : null;
    }

    async personalToBusinessTransform(data, config) {
        const businessData = {
            id: data.id,
            type: 'business-log',
            title: data.title || 'Untitled Entry',
            content: data.content || data.description,
            category: this.mapPersonalToBusinessCategory(data.category),
            priority: data.priority || 'medium',
            status: 'active',
            tags: data.tags || [],
            projectId: config.defaultProjectId,
            assignedTo: data.createdBy,
            departmentId: config.defaultDepartmentId,
            businessContext: {
                originalType: 'personal-log',
                transformedAt: new Date().toISOString(),
                confidentialityLevel: this.assessConfidentiality(data)
            },
            createdAt: data.createdAt,
            updatedAt: new Date().toISOString(),
            createdBy: data.createdBy,
            updatedBy: data.createdBy
        };

        // Apply business-specific transformations
        if (config.addBusinessMetadata) {
            businessData.metadata = {
                ...data.metadata,
                businessUnit: config.businessUnit,
                costCenter: config.costCenter,
                complianceFlags: this.identifyComplianceFlags(data)
            };
        }

        return businessData;
    }

    async businessToPersonalTransform(data, config) {
        const personalData = {
            id: data.id,
            type: 'personal-log',
            title: data.title,
            content: data.content,
            category: this.mapBusinessToPersonalCategory(data.category),
            priority: data.priority,
            tags: [...(data.tags || []), 'from-business'],
            mood: this.inferMoodFromBusiness(data),
            location: data.metadata?.location,
            weather: data.metadata?.weather,
            personalContext: {
                originalType: 'business-log',
                transformedAt: new Date().toISOString(),
                sanitized: true
            },
            createdAt: data.createdAt,
            updatedAt: new Date().toISOString(),
            createdBy: data.createdBy || data.assignedTo,
            updatedBy: data.assignedTo
        };

        // Remove sensitive business information
        if (config.sanitize !== false) {
            personalData.content = this.sanitizeBusinessContent(personalData.content);
        }

        return personalData;
    }

    mapPersonalToBusinessCategory(personalCategory) {
        const mapping = {
            'personal': 'general',
            'work': 'project',
            'health': 'hr',
            'finance': 'finance',
            'travel': 'travel',
            'learning': 'training'
        };
        return mapping[personalCategory] || 'general';
    }

    mapBusinessToPersonalCategory(businessCategory) {
        const mapping = {
            'project': 'work',
            'hr': 'work',
            'finance': 'finance',
            'travel': 'travel',
            'training': 'learning',
            'meeting': 'work'
        };
        return mapping[businessCategory] || 'personal';
    }

    assessConfidentiality(data) {
        const content = (data.content || '').toLowerCase();
        const sensitiveKeywords = ['password', 'confidential', 'secret', 'private', 'ssn', 'credit card'];
        
        for (const keyword of sensitiveKeywords) {
            if (content.includes(keyword)) {
                return 'high';
            }
        }
        
        return 'low';
    }

    identifyComplianceFlags(data) {
        const flags = [];
        const content = (data.content || '').toLowerCase();
        
        if (content.includes('gdpr') || content.includes('personal data')) {
            flags.push('gdpr');
        }
        if (content.includes('hipaa') || content.includes('health')) {
            flags.push('hipaa');
        }
        if (content.includes('financial') || content.includes('payment')) {
            flags.push('pci');
        }
        
        return flags;
    }

    inferMoodFromBusiness(data) {
        const content = (data.content || '').toLowerCase();
        
        if (content.includes('success') || content.includes('completed') || content.includes('achieved')) {
            return 'positive';
        }
        if (content.includes('problem') || content.includes('issue') || content.includes('failed')) {
            return 'negative';
        }
        
        return 'neutral';
    }

    sanitizeBusinessContent(content) {
        // Remove sensitive business information
        return content
            .replace(/\b\d{3}-\d{2}-\d{4}\b/g, '[SSN]')
            .replace(/\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/g, '[CREDIT CARD]')
            .replace(/\$[\d,]+/g, '[AMOUNT]')
            .replace(/salary|wage|compensation/gi, '[COMPENSATION]');
    }

    csvToJson(csvData, config) {
        const lines = csvData.trim().split('\n');
        const headers = lines[0].split(',').map(h => h.trim());
        const result = [];

        for (let i = 1; i < lines.length; i++) {
            const values = lines[i].split(',').map(v => v.trim());
            const obj = {};
            
            headers.forEach((header, index) => {
                obj[header] = values[index] || '';
            });
            
            result.push(obj);
        }

        return result;
    }

    jsonToCsv(jsonData, config) {
        if (!Array.isArray(jsonData) || jsonData.length === 0) {
            return '';
        }

        const headers = Object.keys(jsonData[0]);
        const csvLines = [headers.join(',')];

        for (const item of jsonData) {
            const values = headers.map(header => {
                const value = item[header];
                return typeof value === 'string' && value.includes(',') 
                    ? `"${value}"` 
                    : value;
            });
            csvLines.push(values.join(','));
        }

        return csvLines.join('\n');
    }

    xmlToJson(xmlData, config) {
        // Simplified XML to JSON conversion
        // In a real implementation, use a proper XML parser like xml2js
        const result = {};
        
        const tagRegex = /<(\w+)>(.*?)<\/\1>/gs;
        let match;
        
        while ((match = tagRegex.exec(xmlData)) !== null) {
            const [, tagName, content] = match;
            result[tagName] = content.trim();
        }
        
        return result;
    }

    normalizeData(data, config) {
        const normalized = {
            id: data.id || crypto.randomUUID(),
            type: data.type || 'unknown',
            version: '1.0.0',
            createdAt: data.createdAt || new Date().toISOString(),
            updatedAt: data.updatedAt || new Date().toISOString(),
            metadata: data.metadata || {},
            data: this.extractDataFields(data, config.excludeFields || [])
        };

        return normalized;
    }

    denormalizeData(normalizedData, config) {
        const denormalized = {
            ...normalizedData.data,
            id: normalizedData.id,
            type: normalizedData.type,
            version: normalizedData.version,
            createdAt: normalizedData.createdAt,
            updatedAt: normalizedData.updatedAt
        };

        if (config.includeMetadata !== false) {
            denormalized.metadata = normalizedData.metadata;
        }

        return denormalized;
    }

    extractDataFields(data, excludeFields) {
        const systemFields = ['id', 'type', 'version', 'createdAt', 'updatedAt', 'metadata'];
        const allExcludeFields = [...systemFields, ...excludeFields];
        
        const dataFields = {};
        for (const [key, value] of Object.entries(data)) {
            if (!allExcludeFields.includes(key)) {
                dataFields[key] = value;
            }
        }
        
        return dataFields;
    }

    setNestedValue(obj, path, value) {
        const keys = path.split('.');
        let current = obj;
        
        for (let i = 0; i < keys.length - 1; i++) {
            const key = keys[i];
            if (!current[key] || typeof current[key] !== 'object') {
                current[key] = {};
            }
            current = current[key];
        }
        
        current[keys[keys.length - 1]] = value;
    }

    includeUnmappedFields(source, target, mappedPaths) {
        for (const [key, value] of Object.entries(source)) {
            if (!mappedPaths.includes(`$.${key}`) && !target.hasOwnProperty(key)) {
                target[key] = value;
            }
        }
    }

    generateCacheKey(data, sourceFormat, targetFormat, options) {
        const keyData = {
            dataHash: crypto.createHash('md5').update(JSON.stringify(data)).digest('hex'),
            sourceFormat,
            targetFormat,
            options: JSON.stringify(options, Object.keys(options).sort())
        };
        
        return crypto.createHash('md5').update(JSON.stringify(keyData)).digest('hex');
    }

    calculateDataSize(data) {
        return Buffer.byteLength(JSON.stringify(data), 'utf8');
    }

    async validateInput(data, validator, format) {
        if (typeof validator === 'function') {
            const result = await validator(data, format);
            if (!result.valid) {
                throw new Error(`Input validation failed: ${result.errors.join(', ')}`);
            }
        }
    }

    async validateOutput(data, format, options) {
        // Basic output validation
        if (data === null || data === undefined) {
            throw new Error('Transformation resulted in null or undefined output');
        }

        if (options.requireNonEmpty && 
            (Array.isArray(data) && data.length === 0) ||
            (typeof data === 'object' && Object.keys(data).length === 0)) {
            throw new Error('Transformation resulted in empty output');
        }
    }

    updateAdapterStats(adapterId, success, duration) {
        if (!this.statistics.has(adapterId)) {
            this.statistics.set(adapterId, {
                totalTransforms: 0,
                successfulTransforms: 0,
                failedTransforms: 0,
                totalDuration: 0,
                averageDuration: 0
            });
        }

        const stats = this.statistics.get(adapterId);
        stats.totalTransforms++;
        stats.totalDuration += duration;
        
        if (success) {
            stats.successfulTransforms++;
        } else {
            stats.failedTransforms++;
        }
        
        stats.averageDuration = stats.totalDuration / stats.totalTransforms;
    }

    setupEventHandlers() {
        this.on('transform:completed', (info) => {
            console.log(`Transform completed: ${info.sourceFormat} -> ${info.targetFormat} in ${info.duration}ms`);
        });

        this.on('transform:failed', (info) => {
            console.error(`Transform failed: ${info.sourceFormat} -> ${info.targetFormat} - ${info.error}`);
        });

        // Cache cleanup
        setInterval(() => {
            const now = Date.now();
            for (const [key, cached] of this.cache) {
                if (now - cached.timestamp > this.cacheTTL) {
                    this.cache.delete(key);
                }
            }
        }, 300000); // Clean every 5 minutes
    }

    getStats() {
        return {
            adapters: this.adapters.size,
            transformations: this.transformations.size,
            cacheSize: this.cache.size,
            statistics: Object.fromEntries(this.statistics)
        };
    }

    getAdapterInfo(adapterId) {
        return this.adapters.get(adapterId);
    }

    listAdapters() {
        return Array.from(this.adapters.values());
    }

    reset() {
        this.cache.clear();
        this.statistics.clear();
        this.transformations.clear();
        this.emit('reset');
    }
}

module.exports = DataTransformer;