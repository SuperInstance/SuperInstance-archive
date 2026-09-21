const { EventEmitter } = require('events');
const crypto = require('crypto');

class DataMigrator extends EventEmitter {
    constructor(options = {}) {
        super();
        this.migrations = new Map();
        this.migrationHistory = [];
        this.activeMigrations = new Map();
        this.dataSources = new Map();
        this.validators = new Map();
        this.transformers = new Map();
        
        this.batchSize = options.batchSize || 1000;
        this.maxConcurrentMigrations = options.maxConcurrentMigrations || 3;
        this.retryAttempts = options.retryAttempts || 3;
        this.retryDelay = options.retryDelay || 5000;
        this.enableRollback = options.enableRollback !== false;
        this.enableValidation = options.enableValidation !== false;
        
        this.setupEventHandlers();
    }

    registerDataSource(sourceId, config) {
        const dataSource = {
            id: sourceId,
            name: config.name || sourceId,
            type: config.type, // 'database', 'api', 'file', 'service'
            connectionConfig: config.connectionConfig || {},
            readConfig: config.readConfig || {},
            writeConfig: config.writeConfig || {},
            supportedOperations: config.supportedOperations || ['read', 'write'],
            metadata: config.metadata || {},
            registeredAt: new Date(),
            totalOperations: 0,
            lastOperation: null
        };

        this.dataSources.set(sourceId, dataSource);
        this.emit('datasource:registered', dataSource);
        return dataSource;
    }

    createMigration(migrationId, config) {
        const migration = {
            id: migrationId,
            name: config.name || migrationId,
            description: config.description,
            version: config.version || '1.0.0',
            sourceId: config.sourceId,
            targetId: config.targetId,
            entityType: config.entityType,
            migrationStrategy: config.strategy || 'full', // full, incremental, continuous
            transformationRules: config.transformationRules || {},
            validationRules: config.validationRules || {},
            filters: config.filters || {},
            mapping: config.mapping || {},
            batchSize: config.batchSize || this.batchSize,
            parallelism: config.parallelism || 1,
            priority: config.priority || 5,
            dependencies: config.dependencies || [],
            rollbackStrategy: config.rollbackStrategy || 'delete_target',
            scheduleConfig: config.scheduleConfig,
            metadata: config.metadata || {},
            createdAt: new Date(),
            createdBy: config.createdBy,
            status: 'created',
            totalRuns: 0,
            successfulRuns: 0,
            failedRuns: 0
        };

        this.migrations.set(migrationId, migration);
        this.emit('migration:created', migration);
        return migration;
    }

    async executeMigration(migrationId, options = {}) {
        const migration = this.migrations.get(migrationId);
        if (!migration) {
            throw new Error(`Migration not found: ${migrationId}`);
        }

        // Check if already running
        if (this.activeMigrations.has(migrationId)) {
            throw new Error(`Migration already running: ${migrationId}`);
        }

        // Check concurrency limit
        if (this.activeMigrations.size >= this.maxConcurrentMigrations) {
            throw new Error('Maximum concurrent migrations reached');
        }

        // Check dependencies
        await this.checkDependencies(migration);

        const executionId = crypto.randomUUID();
        const execution = {
            id: executionId,
            migrationId,
            startTime: new Date(),
            endTime: null,
            status: 'running',
            progress: {
                totalRecords: 0,
                processedRecords: 0,
                successfulRecords: 0,
                failedRecords: 0,
                skippedRecords: 0,
                currentBatch: 0,
                totalBatches: 0
            },
            statistics: {
                readTime: 0,
                transformTime: 0,
                writeTime: 0,
                validationTime: 0
            },
            errors: [],
            warnings: [],
            rollbackData: [],
            options: options,
            metadata: {}
        };

        this.activeMigrations.set(migrationId, execution);
        migration.totalRuns++;
        migration.status = 'running';

        this.emit('migration:started', {
            migrationId,
            executionId,
            migration,
            execution
        });

        try {
            await this.performMigration(migration, execution, options);
            
            execution.status = 'completed';
            execution.endTime = new Date();
            execution.duration = execution.endTime - execution.startTime;
            migration.successfulRuns++;
            migration.status = 'completed';

            this.migrationHistory.push(execution);
            this.emit('migration:completed', execution);
            
            return execution;

        } catch (error) {
            execution.status = 'failed';
            execution.endTime = new Date();
            execution.error = error.message;
            execution.errors.push({
                error: error.message,
                timestamp: new Date(),
                context: 'migration_execution'
            });
            
            migration.failedRuns++;
            migration.status = 'failed';

            // Attempt rollback if enabled
            if (this.enableRollback && options.enableRollback !== false) {
                try {
                    await this.rollbackMigration(execution);
                } catch (rollbackError) {
                    execution.rollbackError = rollbackError.message;
                }
            }

            this.migrationHistory.push(execution);
            this.emit('migration:failed', execution);
            throw error;

        } finally {
            this.activeMigrations.delete(migrationId);
        }
    }

    async performMigration(migration, execution, options) {
        const sourceDataSource = this.dataSources.get(migration.sourceId);
        const targetDataSource = this.dataSources.get(migration.targetId);

        if (!sourceDataSource || !targetDataSource) {
            throw new Error('Source or target data source not found');
        }

        // Phase 1: Data Discovery
        const discoveryResult = await this.discoverSourceData(
            sourceDataSource,
            migration,
            execution
        );

        execution.progress.totalRecords = discoveryResult.totalCount;
        execution.progress.totalBatches = Math.ceil(discoveryResult.totalCount / migration.batchSize);

        this.emit('migration:progress', {
            executionId: execution.id,
            phase: 'discovery',
            progress: execution.progress
        });

        // Phase 2: Batch Processing
        await this.processBatches(
            sourceDataSource,
            targetDataSource,
            migration,
            execution,
            discoveryResult
        );

        // Phase 3: Final Validation
        if (this.enableValidation && options.skipValidation !== true) {
            await this.validateMigrationResults(migration, execution);
        }

        // Phase 4: Cleanup
        await this.cleanupMigration(migration, execution);
    }

    async discoverSourceData(sourceDataSource, migration, execution) {
        const startTime = Date.now();
        
        try {
            // Mock data discovery - in real implementation, this would query the actual source
            const discoveryResult = {
                totalCount: Math.floor(Math.random() * 10000) + 1000,
                schema: {
                    fields: ['id', 'name', 'email', 'createdAt', 'updatedAt'],
                    types: {
                        id: 'string',
                        name: 'string',
                        email: 'string',
                        createdAt: 'datetime',
                        updatedAt: 'datetime'
                    }
                },
                constraints: {
                    primaryKey: 'id',
                    required: ['id', 'name'],
                    unique: ['id', 'email']
                },
                statistics: {
                    nullValues: {},
                    duplicates: 0,
                    invalidRecords: 0
                },
                sampleData: []
            };

            // Generate sample data
            for (let i = 0; i < Math.min(10, discoveryResult.totalCount); i++) {
                discoveryResult.sampleData.push({
                    id: crypto.randomUUID(),
                    name: `Sample Record ${i + 1}`,
                    email: `sample${i + 1}@example.com`,
                    createdAt: new Date().toISOString(),
                    updatedAt: new Date().toISOString()
                });
            }

            execution.statistics.readTime += Date.now() - startTime;
            execution.metadata.discoveryResult = discoveryResult;

            return discoveryResult;

        } catch (error) {
            throw new Error(`Data discovery failed: ${error.message}`);
        }
    }

    async processBatches(sourceDataSource, targetDataSource, migration, execution, discoveryResult) {
        const totalBatches = execution.progress.totalBatches;
        
        for (let batchIndex = 0; batchIndex < totalBatches; batchIndex++) {
            const batchStart = batchIndex * migration.batchSize;
            const batchEnd = Math.min(batchStart + migration.batchSize, discoveryResult.totalCount);
            
            execution.progress.currentBatch = batchIndex + 1;

            try {
                await this.processBatch(
                    sourceDataSource,
                    targetDataSource,
                    migration,
                    execution,
                    batchIndex,
                    batchStart,
                    batchEnd
                );

                this.emit('migration:progress', {
                    executionId: execution.id,
                    phase: 'processing',
                    progress: execution.progress,
                    batch: batchIndex + 1
                });

            } catch (error) {
                execution.errors.push({
                    error: error.message,
                    timestamp: new Date(),
                    context: `batch_${batchIndex}`,
                    batchStart,
                    batchEnd
                });

                // Decide whether to continue or fail
                if (options.continueOnError) {
                    execution.warnings.push({
                        warning: `Batch ${batchIndex} failed: ${error.message}`,
                        timestamp: new Date()
                    });
                    continue;
                } else {
                    throw new Error(`Batch processing failed at batch ${batchIndex}: ${error.message}`);
                }
            }
        }
    }

    async processBatch(sourceDataSource, targetDataSource, migration, execution, batchIndex, start, end) {
        // Read data from source
        const readStartTime = Date.now();
        const sourceData = await this.readSourceBatch(
            sourceDataSource,
            migration,
            start,
            end - start
        );
        execution.statistics.readTime += Date.now() - readStartTime;

        // Transform data
        const transformStartTime = Date.now();
        const transformedData = await this.transformBatch(
            sourceData,
            migration,
            execution
        );
        execution.statistics.transformTime += Date.now() - transformStartTime;

        // Validate data
        const validationStartTime = Date.now();
        const validationResults = await this.validateBatch(
            transformedData,
            migration,
            execution
        );
        execution.statistics.validationTime += Date.now() - validationStartTime;

        // Filter out invalid records if configured
        const validRecords = validationResults.filter(result => result.isValid)
            .map(result => result.record);

        if (validRecords.length !== transformedData.length) {
            execution.progress.failedRecords += transformedData.length - validRecords.length;
            execution.warnings.push({
                warning: `Batch ${batchIndex}: ${transformedData.length - validRecords.length} records failed validation`,
                timestamp: new Date()
            });
        }

        // Write data to target
        const writeStartTime = Date.now();
        const writeResult = await this.writeTargetBatch(
            targetDataSource,
            validRecords,
            migration,
            execution
        );
        execution.statistics.writeTime += Date.now() - writeStartTime;

        // Update progress
        execution.progress.processedRecords += sourceData.length;
        execution.progress.successfulRecords += writeResult.successCount;
        execution.progress.failedRecords += writeResult.failureCount;

        // Store rollback data if enabled
        if (this.enableRollback) {
            execution.rollbackData.push({
                batchIndex,
                writtenRecords: writeResult.writtenRecords,
                operation: 'batch_write',
                timestamp: new Date()
            });
        }
    }

    async readSourceBatch(sourceDataSource, migration, offset, limit) {
        // Mock source data reading
        const batch = [];
        for (let i = 0; i < limit; i++) {
            batch.push({
                id: crypto.randomUUID(),
                name: `Record ${offset + i + 1}`,
                email: `record${offset + i + 1}@example.com`,
                category: ['personal', 'business', 'other'][Math.floor(Math.random() * 3)],
                priority: Math.floor(Math.random() * 5) + 1,
                createdAt: new Date(Date.now() - Math.random() * 86400000 * 30).toISOString(),
                updatedAt: new Date().toISOString(),
                metadata: {
                    source: sourceDataSource.id,
                    batchOffset: offset
                }
            });
        }

        sourceDataSource.totalOperations++;
        sourceDataSource.lastOperation = new Date();

        return batch;
    }

    async transformBatch(sourceData, migration, execution) {
        const transformer = this.transformers.get(migration.entityType) || 
                           this.transformers.get('default') ||
                           this.defaultTransformer;

        const transformed = [];
        for (const record of sourceData) {
            try {
                const transformedRecord = await transformer(record, migration);
                transformed.push(transformedRecord);
            } catch (error) {
                execution.errors.push({
                    error: `Transformation failed for record ${record.id}: ${error.message}`,
                    timestamp: new Date(),
                    context: 'transformation',
                    recordId: record.id
                });

                // Include original record if transformation fails
                if (migration.options?.includeFailedTransformations) {
                    transformed.push(record);
                }
            }
        }

        return transformed;
    }

    defaultTransformer(record, migration) {
        let transformed = { ...record };

        // Apply field mappings
        if (migration.mapping.fieldMappings) {
            for (const [sourceField, targetField] of Object.entries(migration.mapping.fieldMappings)) {
                if (transformed[sourceField] !== undefined) {
                    transformed[targetField] = transformed[sourceField];
                    if (sourceField !== targetField) {
                        delete transformed[sourceField];
                    }
                }
            }
        }

        // Apply transformations
        if (migration.transformationRules.dateFormat) {
            for (const field of migration.transformationRules.dateFormat) {
                if (transformed[field]) {
                    transformed[field] = new Date(transformed[field]).toISOString();
                }
            }
        }

        if (migration.transformationRules.lowercase) {
            for (const field of migration.transformationRules.lowercase) {
                if (transformed[field] && typeof transformed[field] === 'string') {
                    transformed[field] = transformed[field].toLowerCase();
                }
            }
        }

        // Add migration metadata
        transformed._migrationMetadata = {
            migrationId: migration.id,
            migratedAt: new Date().toISOString(),
            sourceId: migration.sourceId,
            originalId: record.id
        };

        return transformed;
    }

    registerTransformer(entityType, transformer) {
        this.transformers.set(entityType, transformer);
        this.emit('transformer:registered', { entityType, transformer });
    }

    async validateBatch(transformedData, migration, execution) {
        const validator = this.validators.get(migration.entityType) || 
                          this.validators.get('default') ||
                          this.defaultValidator;

        const validationResults = [];
        for (const record of transformedData) {
            try {
                const isValid = await validator(record, migration);
                validationResults.push({
                    record,
                    isValid,
                    errors: isValid ? [] : ['Validation failed']
                });
            } catch (error) {
                validationResults.push({
                    record,
                    isValid: false,
                    errors: [error.message]
                });
            }
        }

        return validationResults;
    }

    defaultValidator(record, migration) {
        // Basic validation
        const rules = migration.validationRules;
        
        if (rules.required) {
            for (const field of rules.required) {
                if (!record[field]) {
                    return false;
                }
            }
        }

        if (rules.unique) {
            // In a real implementation, this would check against existing data
            // For now, we'll assume uniqueness based on the presence of the field
            for (const field of rules.unique) {
                if (!record[field]) {
                    return false;
                }
            }
        }

        if (rules.patterns) {
            for (const [field, pattern] of Object.entries(rules.patterns)) {
                if (record[field] && !new RegExp(pattern).test(record[field])) {
                    return false;
                }
            }
        }

        return true;
    }

    registerValidator(entityType, validator) {
        this.validators.set(entityType, validator);
        this.emit('validator:registered', { entityType, validator });
    }

    async writeTargetBatch(targetDataSource, records, migration, execution) {
        const writeResult = {
            successCount: 0,
            failureCount: 0,
            writtenRecords: [],
            errors: []
        };

        // Mock target data writing
        for (const record of records) {
            try {
                // Simulate write operation
                const writtenRecord = {
                    ...record,
                    _targetId: crypto.randomUUID(),
                    _writtenAt: new Date().toISOString()
                };

                writeResult.writtenRecords.push(writtenRecord);
                writeResult.successCount++;

            } catch (error) {
                writeResult.failureCount++;
                writeResult.errors.push({
                    recordId: record.id,
                    error: error.message
                });
            }
        }

        targetDataSource.totalOperations++;
        targetDataSource.lastOperation = new Date();

        return writeResult;
    }

    async validateMigrationResults(migration, execution) {
        // Perform post-migration validation
        const validationResults = {
            recordCountMatch: false,
            dataIntegrityCheck: false,
            foreignKeyConsistency: false,
            customValidations: []
        };

        // Record count validation
        const sourceCount = execution.progress.totalRecords;
        const targetCount = execution.progress.successfulRecords;
        validationResults.recordCountMatch = sourceCount === targetCount;

        if (!validationResults.recordCountMatch) {
            execution.warnings.push({
                warning: `Record count mismatch: source ${sourceCount}, target ${targetCount}`,
                timestamp: new Date()
            });
        }

        // Data integrity validation (mock)
        validationResults.dataIntegrityCheck = execution.progress.failedRecords < execution.progress.totalRecords * 0.01; // Less than 1% failure

        execution.metadata.validationResults = validationResults;
        
        this.emit('migration:validated', {
            migrationId: migration.id,
            executionId: execution.id,
            results: validationResults
        });

        return validationResults;
    }

    async cleanupMigration(migration, execution) {
        // Cleanup temporary resources, close connections, etc.
        this.emit('migration:cleanup', {
            migrationId: migration.id,
            executionId: execution.id
        });
    }

    async rollbackMigration(execution) {
        const rollbackId = crypto.randomUUID();
        const rollbackInfo = {
            id: rollbackId,
            migrationExecutionId: execution.id,
            startTime: new Date(),
            status: 'running',
            operationsRolledBack: 0,
            errors: []
        };

        this.emit('rollback:started', rollbackInfo);

        try {
            // Reverse the operations in rollback data
            for (const rollbackOperation of execution.rollbackData.reverse()) {
                await this.performRollbackOperation(rollbackOperation, rollbackInfo);
            }

            rollbackInfo.status = 'completed';
            rollbackInfo.endTime = new Date();
            
            this.emit('rollback:completed', rollbackInfo);

        } catch (error) {
            rollbackInfo.status = 'failed';
            rollbackInfo.error = error.message;
            rollbackInfo.endTime = new Date();
            
            this.emit('rollback:failed', rollbackInfo);
            throw error;
        }

        return rollbackInfo;
    }

    async performRollbackOperation(rollbackOperation, rollbackInfo) {
        try {
            switch (rollbackOperation.operation) {
                case 'batch_write':
                    // Delete the written records
                    for (const record of rollbackOperation.writtenRecords) {
                        // Mock delete operation
                        console.log(`Rolling back record: ${record._targetId}`);
                    }
                    rollbackInfo.operationsRolledBack++;
                    break;
                    
                default:
                    console.warn(`Unknown rollback operation: ${rollbackOperation.operation}`);
            }
        } catch (error) {
            rollbackInfo.errors.push({
                operation: rollbackOperation.operation,
                error: error.message,
                timestamp: new Date()
            });
        }
    }

    async checkDependencies(migration) {
        for (const dependencyId of migration.dependencies) {
            const dependency = this.migrations.get(dependencyId);
            if (!dependency) {
                throw new Error(`Dependency migration not found: ${dependencyId}`);
            }
            
            if (dependency.status !== 'completed') {
                throw new Error(`Dependency migration not completed: ${dependencyId} (status: ${dependency.status})`);
            }
        }
    }

    getMigrationStatus(migrationId) {
        const migration = this.migrations.get(migrationId);
        if (!migration) {
            return null;
        }

        const activeExecution = this.activeMigrations.get(migrationId);
        const lastExecution = this.migrationHistory
            .filter(h => h.migrationId === migrationId)
            .sort((a, b) => b.startTime - a.startTime)[0];

        return {
            migration,
            isRunning: !!activeExecution,
            activeExecution,
            lastExecution,
            history: this.migrationHistory
                .filter(h => h.migrationId === migrationId)
                .sort((a, b) => b.startTime - a.startTime)
        };
    }

    getMigrationProgress(migrationId) {
        const activeExecution = this.activeMigrations.get(migrationId);
        if (!activeExecution) {
            return null;
        }

        const progress = activeExecution.progress;
        return {
            ...progress,
            percentComplete: progress.totalRecords > 0 ? 
                (progress.processedRecords / progress.totalRecords) * 100 : 0,
            estimatedTimeRemaining: this.estimateTimeRemaining(activeExecution),
            currentPhase: this.determineCurrentPhase(activeExecution)
        };
    }

    estimateTimeRemaining(execution) {
        const elapsed = Date.now() - execution.startTime;
        const progress = execution.progress;
        
        if (progress.processedRecords === 0) {
            return null;
        }

        const averageTimePerRecord = elapsed / progress.processedRecords;
        const remainingRecords = progress.totalRecords - progress.processedRecords;
        
        return remainingRecords * averageTimePerRecord;
    }

    determineCurrentPhase(execution) {
        const progress = execution.progress;
        
        if (progress.totalRecords === 0) {
            return 'discovery';
        } else if (progress.processedRecords < progress.totalRecords) {
            return 'processing';
        } else {
            return 'validation';
        }
    }

    pauseMigration(migrationId) {
        const execution = this.activeMigrations.get(migrationId);
        if (execution) {
            execution.status = 'paused';
            execution.pausedAt = new Date();
            this.emit('migration:paused', { migrationId, executionId: execution.id });
        }
    }

    resumeMigration(migrationId) {
        const execution = this.activeMigrations.get(migrationId);
        if (execution && execution.status === 'paused') {
            execution.status = 'running';
            execution.resumedAt = new Date();
            this.emit('migration:resumed', { migrationId, executionId: execution.id });
        }
    }

    cancelMigration(migrationId) {
        const execution = this.activeMigrations.get(migrationId);
        if (execution) {
            execution.status = 'cancelled';
            execution.endTime = new Date();
            execution.cancelledAt = new Date();
            
            this.activeMigrations.delete(migrationId);
            this.migrationHistory.push(execution);
            
            this.emit('migration:cancelled', { migrationId, executionId: execution.id });
        }
    }

    setupEventHandlers() {
        this.on('migration:completed', (execution) => {
            console.log(`Migration completed: ${execution.migrationId} in ${execution.duration}ms`);
        });

        this.on('migration:failed', (execution) => {
            console.error(`Migration failed: ${execution.migrationId} - ${execution.error}`);
        });

        this.on('rollback:completed', (rollback) => {
            console.log(`Rollback completed: ${rollback.operationsRolledBack} operations rolled back`);
        });
    }

    getStats() {
        return {
            migrations: this.migrations.size,
            activeMigrations: this.activeMigrations.size,
            migrationHistory: this.migrationHistory.length,
            dataSources: this.dataSources.size,
            validators: this.validators.size,
            transformers: this.transformers.size,
            totalExecutions: this.migrationHistory.length + this.activeMigrations.size
        };
    }

    getMigrations() {
        return Array.from(this.migrations.values());
    }

    getDataSources() {
        return Array.from(this.dataSources.values());
    }

    getActiveMigrations() {
        return Array.from(this.activeMigrations.values());
    }

    getMigrationHistory(limit = 100) {
        return this.migrationHistory
            .sort((a, b) => b.startTime - a.startTime)
            .slice(0, limit);
    }

    reset() {
        // Cancel all active migrations
        for (const [migrationId, execution] of this.activeMigrations) {
            this.cancelMigration(migrationId);
        }

        this.migrations.clear();
        this.migrationHistory.length = 0;
        this.activeMigrations.clear();
        this.dataSources.clear();
        this.validators.clear();
        this.transformers.clear();
        
        this.emit('reset');
    }
}

module.exports = DataMigrator;