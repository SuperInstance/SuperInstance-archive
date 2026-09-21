const { EventEmitter } = require('events');
const crypto = require('crypto');
const { diff } = require('diff');
const { applyPatch, createPatch } = require('fast-json-patch');

class ConflictResolver extends EventEmitter {
    constructor(options = {}) {
        super();
        this.strategies = new Map();
        this.conflicts = new Map();
        this.resolutions = new Map();
        this.rules = new Map();
        this.defaultStrategy = options.defaultStrategy || 'timestamp';
        this.autoResolveThreshold = options.autoResolveThreshold || 0.8;
        this.conflictHistory = [];
        
        this.initializeStrategies();
        this.setupEventHandlers();
    }

    initializeStrategies() {
        // Timestamp-based resolution
        this.registerStrategy('timestamp', async (conflict) => {
            const sourceTime = new Date(conflict.sourceEntity.updatedAt);
            const targetTime = new Date(conflict.targetEntity.updatedAt);
            
            if (sourceTime > targetTime) {
                return {
                    resolution: 'source-wins',
                    entity: conflict.sourceEntity,
                    confidence: 0.9,
                    reason: `Source entity is newer (${sourceTime} > ${targetTime})`
                };
            } else if (targetTime > sourceTime) {
                return {
                    resolution: 'target-wins',
                    entity: conflict.targetEntity,
                    confidence: 0.9,
                    reason: `Target entity is newer (${targetTime} > ${sourceTime})`
                };
            } else {
                return {
                    resolution: 'equal-timestamp',
                    entity: conflict.sourceEntity,
                    confidence: 0.5,
                    reason: 'Entities have equal timestamps, using source by default'
                };
            }
        });

        // Version-based resolution
        this.registerStrategy('version', async (conflict) => {
            const sourceVersion = this.parseVersion(conflict.sourceEntity.version);
            const targetVersion = this.parseVersion(conflict.targetEntity.version);
            
            const comparison = this.compareVersions(sourceVersion, targetVersion);
            if (comparison > 0) {
                return {
                    resolution: 'source-wins',
                    entity: conflict.sourceEntity,
                    confidence: 0.95,
                    reason: `Source version is higher (${conflict.sourceEntity.version} > ${conflict.targetEntity.version})`
                };
            } else if (comparison < 0) {
                return {
                    resolution: 'target-wins',
                    entity: conflict.targetEntity,
                    confidence: 0.95,
                    reason: `Target version is higher (${conflict.targetEntity.version} > ${conflict.sourceEntity.version})`
                };
            } else {
                // Fall back to timestamp if versions are equal
                return this.strategies.get('timestamp')(conflict);
            }
        });

        // Field-level merge strategy
        this.registerStrategy('merge', async (conflict) => {
            const merged = await this.performFieldMerge(conflict);
            return {
                resolution: 'merged',
                entity: merged.entity,
                confidence: merged.confidence,
                reason: merged.reason,
                mergeDetails: merged.details
            };
        });

        // Priority-based resolution
        this.registerStrategy('priority', async (conflict) => {
            const sourcePriority = this.getEntityPriority(conflict.sourceEntity, conflict.sourceService);
            const targetPriority = this.getEntityPriority(conflict.targetEntity, conflict.targetService);
            
            if (sourcePriority > targetPriority) {
                return {
                    resolution: 'source-wins',
                    entity: conflict.sourceEntity,
                    confidence: 0.8,
                    reason: `Source has higher priority (${sourcePriority} > ${targetPriority})`
                };
            } else if (targetPriority > sourcePriority) {
                return {
                    resolution: 'target-wins',
                    entity: conflict.targetEntity,
                    confidence: 0.8,
                    reason: `Target has higher priority (${targetPriority} > ${sourcePriority})`
                };
            } else {
                // Fall back to timestamp if priorities are equal
                return this.strategies.get('timestamp')(conflict);
            }
        });

        // Content-based resolution using diff analysis
        this.registerStrategy('content-diff', async (conflict) => {
            const changes = this.analyzeContentChanges(conflict.sourceEntity, conflict.targetEntity);
            
            if (changes.conflictLevel < 0.3) {
                // Low conflict - can auto-merge
                const merged = this.smartMerge(conflict.sourceEntity, conflict.targetEntity, changes);
                return {
                    resolution: 'auto-merged',
                    entity: merged,
                    confidence: 1 - changes.conflictLevel,
                    reason: 'Low conflict detected, auto-merged successfully',
                    changes
                };
            } else {
                // High conflict - prefer more comprehensive update
                const entity = changes.sourceChanges > changes.targetChanges 
                    ? conflict.sourceEntity 
                    : conflict.targetEntity;
                
                return {
                    resolution: changes.sourceChanges > changes.targetChanges ? 'source-wins' : 'target-wins',
                    entity,
                    confidence: 0.6,
                    reason: `Entity with more changes selected (conflict level: ${changes.conflictLevel})`,
                    changes
                };
            }
        });

        // User-defined rule-based resolution
        this.registerStrategy('rules', async (conflict) => {
            const applicableRules = this.findApplicableRules(conflict);
            
            for (const rule of applicableRules) {
                const result = await this.evaluateRule(rule, conflict);
                if (result.matches) {
                    return {
                        resolution: result.resolution,
                        entity: result.entity,
                        confidence: result.confidence,
                        reason: `Rule applied: ${rule.name}`,
                        rule: rule.id
                    };
                }
            }
            
            // No applicable rules found, fall back to default
            return this.strategies.get(this.defaultStrategy)(conflict);
        });
    }

    registerStrategy(name, resolver) {
        this.strategies.set(name, resolver);
        this.emit('strategy:registered', { name, resolver });
        return this;
    }

    async resolveConflict(conflict, strategyName = null) {
        const conflictId = crypto.randomUUID();
        const conflictInfo = {
            id: conflictId,
            ...conflict,
            detectedAt: new Date(),
            status: 'resolving'
        };

        this.conflicts.set(conflictId, conflictInfo);
        this.emit('conflict:started', conflictInfo);

        try {
            const strategy = strategyName || this.selectBestStrategy(conflict);
            const resolver = this.strategies.get(strategy);
            
            if (!resolver) {
                throw new Error(`Unknown conflict resolution strategy: ${strategy}`);
            }

            const resolution = await resolver(conflict);
            resolution.strategy = strategy;
            resolution.conflictId = conflictId;
            resolution.resolvedAt = new Date();

            // Validate resolution
            await this.validateResolution(resolution, conflict);

            conflictInfo.status = 'resolved';
            conflictInfo.resolution = resolution;

            this.resolutions.set(conflictId, resolution);
            this.conflictHistory.push(conflictInfo);

            this.emit('conflict:resolved', {
                conflict: conflictInfo,
                resolution
            });

            return resolution;

        } catch (error) {
            conflictInfo.status = 'failed';
            conflictInfo.error = error.message;

            this.emit('conflict:failed', {
                conflict: conflictInfo,
                error: error.message
            });

            throw error;
        } finally {
            this.conflicts.delete(conflictId);
        }
    }

    selectBestStrategy(conflict) {
        // Analyze conflict characteristics to choose best strategy
        const characteristics = this.analyzeConflict(conflict);
        
        if (characteristics.hasVersionInfo && characteristics.versionDifference > 0) {
            return 'version';
        }
        
        if (characteristics.hasRules) {
            return 'rules';
        }
        
        if (characteristics.contentSimilarity > 0.7) {
            return 'content-diff';
        }
        
        if (characteristics.hasPriorityInfo) {
            return 'priority';
        }
        
        return this.defaultStrategy;
    }

    analyzeConflict(conflict) {
        const source = conflict.sourceEntity;
        const target = conflict.targetEntity;
        
        return {
            hasVersionInfo: !!(source.version && target.version),
            versionDifference: this.getVersionDifference(source.version, target.version),
            hasPriorityInfo: !!(source.priority || target.priority),
            hasRules: this.findApplicableRules(conflict).length > 0,
            contentSimilarity: this.calculateContentSimilarity(source, target),
            timeDifference: Math.abs(new Date(source.updatedAt) - new Date(target.updatedAt)),
            fieldConflicts: this.identifyFieldConflicts(source, target)
        };
    }

    async performFieldMerge(conflict) {
        const source = conflict.sourceEntity;
        const target = conflict.targetEntity;
        const merged = { ...target };
        
        let totalFields = 0;
        let conflictFields = 0;
        let mergedFields = 0;
        const details = {
            conflicts: [],
            merged: [],
            unchanged: []
        };

        // Compare each field
        for (const [field, sourceValue] of Object.entries(source)) {
            totalFields++;
            const targetValue = target[field];

            if (sourceValue === targetValue) {
                details.unchanged.push(field);
                continue;
            }

            if (targetValue === undefined) {
                // Field only exists in source
                merged[field] = sourceValue;
                details.merged.push({ field, action: 'added', value: sourceValue });
                mergedFields++;
                continue;
            }

            // Field exists in both with different values
            const resolution = await this.resolveFieldConflict(field, sourceValue, targetValue, conflict);
            
            if (resolution.canMerge) {
                merged[field] = resolution.value;
                details.merged.push({ 
                    field, 
                    action: 'merged', 
                    sourceValue, 
                    targetValue, 
                    resolvedValue: resolution.value 
                });
                mergedFields++;
            } else {
                conflictFields++;
                details.conflicts.push({
                    field,
                    sourceValue,
                    targetValue,
                    reason: resolution.reason
                });

                // Use field-specific resolution strategy
                if (resolution.prefer === 'source') {
                    merged[field] = sourceValue;
                } else if (resolution.prefer === 'target') {
                    merged[field] = targetValue;
                } else {
                    // Use timestamp-based resolution for this field
                    const sourceTime = new Date(source.updatedAt);
                    const targetTime = new Date(target.updatedAt);
                    merged[field] = sourceTime > targetTime ? sourceValue : targetValue;
                }
            }
        }

        // Check for fields that only exist in target
        for (const [field, targetValue] of Object.entries(target)) {
            if (source[field] === undefined) {
                totalFields++;
                details.unchanged.push(field);
            }
        }

        const confidence = conflictFields === 0 ? 0.95 : Math.max(0.3, 1 - (conflictFields / totalFields));
        
        return {
            entity: merged,
            confidence,
            reason: `Merged ${mergedFields} fields, ${conflictFields} conflicts resolved`,
            details
        };
    }

    async resolveFieldConflict(field, sourceValue, targetValue, conflict) {
        // Special handling for different field types
        switch (field) {
            case 'tags':
                // Merge arrays by union
                if (Array.isArray(sourceValue) && Array.isArray(targetValue)) {
                    return {
                        canMerge: true,
                        value: [...new Set([...sourceValue, ...targetValue])]
                    };
                }
                break;
                
            case 'metadata':
                // Deep merge objects
                if (typeof sourceValue === 'object' && typeof targetValue === 'object') {
                    return {
                        canMerge: true,
                        value: { ...targetValue, ...sourceValue }
                    };
                }
                break;
                
            case 'content':
                // Try to merge text content
                if (typeof sourceValue === 'string' && typeof targetValue === 'string') {
                    const merged = this.mergeTextContent(sourceValue, targetValue);
                    if (merged.success) {
                        return {
                            canMerge: true,
                            value: merged.content
                        };
                    }
                }
                break;
        }

        return {
            canMerge: false,
            reason: `Cannot automatically merge field '${field}'`,
            prefer: 'timestamp'
        };
    }

    mergeTextContent(source, target) {
        try {
            const diffs = diff.diffLines(target, source);
            let merged = '';
            let hasConflicts = false;

            for (const change of diffs) {
                if (change.added || change.removed) {
                    hasConflicts = true;
                }
                
                if (!change.removed) {
                    merged += change.value;
                }
            }

            return {
                success: !hasConflicts,
                content: merged,
                hasConflicts
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    defineRule(ruleId, config) {
        const rule = {
            id: ruleId,
            name: config.name || ruleId,
            entityTypes: config.entityTypes || [],
            services: config.services || [],
            conditions: config.conditions || {},
            resolution: config.resolution || 'source-wins',
            priority: config.priority || 5,
            enabled: config.enabled !== false,
            createdAt: new Date()
        };

        this.rules.set(ruleId, rule);
        this.emit('rule:defined', rule);
        return rule;
    }

    findApplicableRules(conflict) {
        const applicable = [];
        
        for (const [ruleId, rule] of this.rules) {
            if (!rule.enabled) continue;
            
            // Check entity type match
            if (rule.entityTypes.length > 0 && 
                !rule.entityTypes.includes(conflict.sourceEntity.type)) {
                continue;
            }
            
            // Check service match
            if (rule.services.length > 0 && 
                !rule.services.includes(conflict.sourceService) &&
                !rule.services.includes(conflict.targetService)) {
                continue;
            }
            
            applicable.push(rule);
        }
        
        return applicable.sort((a, b) => b.priority - a.priority);
    }

    async evaluateRule(rule, conflict) {
        // Evaluate rule conditions
        for (const [condition, expected] of Object.entries(rule.conditions)) {
            const actual = this.evaluateCondition(condition, conflict);
            if (actual !== expected) {
                return { matches: false };
            }
        }

        // Rule matches, apply resolution
        let entity, resolution;
        switch (rule.resolution) {
            case 'source-wins':
                entity = conflict.sourceEntity;
                resolution = 'source-wins';
                break;
            case 'target-wins':
                entity = conflict.targetEntity;
                resolution = 'target-wins';
                break;
            case 'merge':
                const merged = await this.performFieldMerge(conflict);
                entity = merged.entity;
                resolution = 'merged';
                break;
            default:
                throw new Error(`Unknown rule resolution: ${rule.resolution}`);
        }

        return {
            matches: true,
            entity,
            resolution,
            confidence: 0.9
        };
    }

    evaluateCondition(condition, conflict) {
        const [entity, path] = condition.split('.');
        const targetEntity = entity === 'source' ? conflict.sourceEntity : conflict.targetEntity;
        
        return this.getNestedValue(targetEntity, path);
    }

    getNestedValue(obj, path) {
        return path.split('.').reduce((current, key) => current?.[key], obj);
    }

    analyzeContentChanges(source, target) {
        const sourceStr = JSON.stringify(source, null, 0);
        const targetStr = JSON.stringify(target, null, 0);
        
        const diffs = diff.diffChars(targetStr, sourceStr);
        
        let additions = 0;
        let deletions = 0;
        let total = 0;

        for (const change of diffs) {
            total += change.value.length;
            if (change.added) additions += change.value.length;
            if (change.removed) deletions += change.value.length;
        }

        const conflictLevel = (additions + deletions) / (total || 1);
        
        return {
            conflictLevel,
            sourceChanges: additions,
            targetChanges: deletions,
            totalChanges: additions + deletions,
            similarity: 1 - conflictLevel
        };
    }

    smartMerge(source, target, changes) {
        // Perform intelligent merge based on change analysis
        const merged = { ...target };
        
        // Apply non-conflicting changes from source
        const sourcePatches = createPatch(target, source);
        const safePatches = sourcePatches.filter(patch => 
            !this.wouldCauseConflict(patch, changes)
        );
        
        try {
            return applyPatch(merged, safePatches).newDocument;
        } catch (error) {
            // Fall back to simple merge
            return { ...target, ...source };
        }
    }

    wouldCauseConflict(patch, changes) {
        // Simplified conflict detection for patches
        return changes.conflictLevel > 0.5 && patch.op === 'replace';
    }

    parseVersion(version) {
        if (!version) return [0, 0, 0];
        return version.split('.').map(Number);
    }

    compareVersions(v1, v2) {
        for (let i = 0; i < Math.max(v1.length, v2.length); i++) {
            const a = v1[i] || 0;
            const b = v2[i] || 0;
            if (a > b) return 1;
            if (a < b) return -1;
        }
        return 0;
    }

    getVersionDifference(v1, v2) {
        const version1 = this.parseVersion(v1);
        const version2 = this.parseVersion(v2);
        return this.compareVersions(version1, version2);
    }

    getEntityPriority(entity, service) {
        return entity.priority || service?.priority || 5;
    }

    calculateContentSimilarity(source, target) {
        const sourceStr = JSON.stringify(source, Object.keys(source).sort());
        const targetStr = JSON.stringify(target, Object.keys(target).sort());
        
        if (sourceStr === targetStr) return 1.0;
        
        const maxLength = Math.max(sourceStr.length, targetStr.length);
        const distance = this.levenshteinDistance(sourceStr, targetStr);
        
        return 1 - (distance / maxLength);
    }

    levenshteinDistance(str1, str2) {
        const matrix = [];
        
        for (let i = 0; i <= str2.length; i++) {
            matrix[i] = [i];
        }
        
        for (let j = 0; j <= str1.length; j++) {
            matrix[0][j] = j;
        }
        
        for (let i = 1; i <= str2.length; i++) {
            for (let j = 1; j <= str1.length; j++) {
                if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
                    matrix[i][j] = matrix[i - 1][j - 1];
                } else {
                    matrix[i][j] = Math.min(
                        matrix[i - 1][j - 1] + 1,
                        matrix[i][j - 1] + 1,
                        matrix[i - 1][j] + 1
                    );
                }
            }
        }
        
        return matrix[str2.length][str1.length];
    }

    identifyFieldConflicts(source, target) {
        const conflicts = [];
        const allFields = new Set([...Object.keys(source), ...Object.keys(target)]);
        
        for (const field of allFields) {
            const sourceValue = source[field];
            const targetValue = target[field];
            
            if (sourceValue !== undefined && targetValue !== undefined && sourceValue !== targetValue) {
                conflicts.push({
                    field,
                    sourceValue,
                    targetValue,
                    type: this.getConflictType(sourceValue, targetValue)
                });
            }
        }
        
        return conflicts;
    }

    getConflictType(sourceValue, targetValue) {
        if (typeof sourceValue !== typeof targetValue) {
            return 'type-mismatch';
        }
        
        if (Array.isArray(sourceValue) && Array.isArray(targetValue)) {
            return 'array-conflict';
        }
        
        if (typeof sourceValue === 'object' && sourceValue !== null) {
            return 'object-conflict';
        }
        
        return 'value-conflict';
    }

    async validateResolution(resolution, conflict) {
        // Validate that the resolution is valid
        if (!resolution.entity || !resolution.resolution) {
            throw new Error('Invalid resolution: missing entity or resolution type');
        }

        // Ensure resolved entity has required fields
        const requiredFields = ['id', 'type', 'updatedAt'];
        for (const field of requiredFields) {
            if (!resolution.entity[field]) {
                throw new Error(`Invalid resolution: missing required field '${field}'`);
            }
        }

        // Validate confidence score
        if (resolution.confidence < 0 || resolution.confidence > 1) {
            throw new Error('Invalid resolution: confidence must be between 0 and 1');
        }

        this.emit('resolution:validated', resolution);
        return true;
    }

    setupEventHandlers() {
        this.on('conflict:resolved', ({ conflict, resolution }) => {
            console.log(`Conflict resolved: ${conflict.id} using ${resolution.strategy}`);
        });

        this.on('conflict:failed', ({ conflict, error }) => {
            console.error(`Conflict resolution failed: ${conflict.id} - ${error}`);
        });
    }

    getStats() {
        return {
            strategies: this.strategies.size,
            activeConflicts: this.conflicts.size,
            resolvedConflicts: this.resolutions.size,
            rules: this.rules.size,
            historySize: this.conflictHistory.length,
            successRate: this.calculateSuccessRate()
        };
    }

    calculateSuccessRate() {
        if (this.conflictHistory.length === 0) return 0;
        
        const resolved = this.conflictHistory.filter(c => c.status === 'resolved').length;
        return resolved / this.conflictHistory.length;
    }

    getConflictHistory(limit = 100) {
        return this.conflictHistory
            .sort((a, b) => b.detectedAt - a.detectedAt)
            .slice(0, limit);
    }

    reset() {
        this.conflicts.clear();
        this.resolutions.clear();
        this.rules.clear();
        this.conflictHistory.length = 0;
        this.emit('reset');
    }
}

module.exports = ConflictResolver;