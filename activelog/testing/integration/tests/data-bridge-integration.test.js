describe('Data Bridge Integration Tests', () => {
  const DATA_BRIDGE_URL = process.env.DATA_BRIDGE_URL || 'http://localhost:18202';
  let testData = {};

  beforeAll(async () => {
    // Initialize test data
    testData.user = global.testUtils.generateUser();
    testData.logEntry = global.testUtils.generateLogEntry();
    testData.project = global.testUtils.generateProject();
  });

  describe('Unified Schema Management', () => {
    test('should retrieve all schemas', async () => {
      const response = await global.testUtils.http.get(`${DATA_BRIDGE_URL}/api/schema`);

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('user');
      expect(response.data).toHaveProperty('document');
      expect(response.data).toHaveProperty('project');
      expect(response.data.user).toHaveProperty('schema');
    });

    test('should validate entity against schema', async () => {
      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/schema/validate`, {
        entityType: 'user',
        data: testData.user
      });

      expect(response.status).toBe(200);
      expect(response.data.valid).toBe(true);
      expect(response.data.errors).toHaveLength(0);
    });

    test('should reject invalid entity', async () => {
      const invalidUser = {
        id: 'invalid-id-format',
        email: 'not-an-email',
        // missing required fields
      };

      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/schema/validate`, {
        entityType: 'user',
        data: invalidUser
      });

      expect(response.status).toBe(200);
      expect(response.data.valid).toBe(false);
      expect(response.data.errors.length).toBeGreaterThan(0);
    });

    test('should transform entity between types', async () => {
      const personalLogData = {
        id: testData.logEntry.id,
        title: testData.logEntry.title,
        content: testData.logEntry.content,
        category: 'personal',
        createdBy: testData.user.id
      };

      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/schema/transform`, {
        data: personalLogData,
        fromType: 'personal-log',
        toType: 'business-log',
        options: {
          defaultProjectId: testData.project.id,
          defaultDepartmentId: 'dept-123'
        }
      });

      expect(response.status).toBe(200);
      expect(response.data.success).toBe(true);
      expect(response.data.data.type).toBe('business-log');
      expect(response.data.data.projectId).toBe(testData.project.id);
    });
  });

  describe('Data Synchronization', () => {
    test('should register data source', async () => {
      const serviceConfig = {
        serviceName: 'test-personal-log',
        config: {
          endpoint: 'http://localhost:3001/api',
          syncEnabled: true,
          syncStrategy: 'bidirectional',
          entityTypes: ['document'],
          rateLimits: { requests: 100, window: 60000 }
        }
      };

      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/sync/services`, serviceConfig);

      expect(response.status).toBe(200);
      expect(response.data.name).toBe(serviceConfig.serviceName);
      expect(response.data.syncEnabled).toBe(true);
    });

    test('should create sync rule', async () => {
      const syncRule = {
        ruleId: 'test-sync-rule',
        config: {
          sourceService: 'test-personal-log',
          targetServices: ['test-business-log'],
          entityType: 'document',
          syncMode: 'realtime',
          filters: {
            category: ['work', 'project']
          }
        }
      };

      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/sync/rules`, syncRule);

      expect(response.status).toBe(200);
      expect(response.data.id).toBe(syncRule.ruleId);
      expect(response.data.syncMode).toBe('realtime');
    });

    test('should sync entity between services', async () => {
      const syncRequest = {
        entityType: 'document',
        entityId: testData.logEntry.id,
        sourceService: 'test-personal-log',
        options: {
          targetServices: ['test-business-log']
        }
      };

      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/sync/sync`, syncRequest);

      expect(response.status).toBe(200);
      expect(response.data.id).toBeDefined();
      expect(response.data.status).toMatch(/completed|partial/);
    });

    test('should handle sync conflicts', async () => {
      // Create a sync conflict scenario
      const conflictingData = {
        id: testData.logEntry.id,
        title: 'Conflicting Title Update',
        content: 'This content conflicts with another update',
        updatedAt: new Date().toISOString()
      };

      // This would typically trigger conflict resolution
      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/sync/sync`, {
        entityType: 'document',
        entityId: testData.logEntry.id,
        sourceService: 'test-personal-log',
        data: conflictingData
      });

      expect([200, 409]).toContain(response.status);
      if (response.status === 409) {
        expect(response.data.error).toContain('conflict');
      }
    });
  });

  describe('Conflict Resolution', () => {
    test('should resolve conflict using timestamp strategy', async () => {
      const conflict = {
        sourceEntity: {
          id: testData.logEntry.id,
          title: 'Source Title',
          updatedAt: new Date().toISOString()
        },
        targetEntity: {
          id: testData.logEntry.id,
          title: 'Target Title',
          updatedAt: new Date(Date.now() - 60000).toISOString() // 1 minute older
        },
        sourceService: 'personal-log',
        targetService: 'business-log'
      };

      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/conflicts/resolve`, {
        conflict,
        strategyName: 'timestamp'
      });

      expect(response.status).toBe(200);
      expect(response.data.resolution).toBe('source-wins');
      expect(response.data.entity.title).toBe('Source Title');
    });

    test('should define custom resolution rule', async () => {
      const rule = {
        ruleId: 'priority-rule',
        config: {
          name: 'Priority-based Resolution',
          entityTypes: ['document'],
          conditions: {
            'source.priority': 'high'
          },
          resolution: 'source-wins'
        }
      };

      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/conflicts/rules`, rule);

      expect(response.status).toBe(200);
      expect(response.data.id).toBe(rule.ruleId);
      expect(response.data.name).toBe(rule.config.name);
    });
  });

  describe('Data Transformation', () => {
    test('should transform JSON data', async () => {
      const transformRequest = {
        data: {
          user_name: 'John Doe',
          user_email: 'john@example.com',
          creation_date: '2024-01-01'
        },
        sourceFormat: 'json',
        targetFormat: 'json',
        options: {
          fieldMappings: {
            'user_name': 'name',
            'user_email': 'email',
            'creation_date': 'createdAt'
          },
          valueTransformations: {
            'createdAt': {
              type: 'format',
              format: 'date'
            }
          }
        }
      };

      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/transform/transform`, transformRequest);

      expect(response.status).toBe(200);
      expect(response.data.success).toBe(true);
      expect(response.data.data).toHaveProperty('name', 'John Doe');
      expect(response.data.data).toHaveProperty('email', 'john@example.com');
    });

    test('should list available adapters', async () => {
      const response = await global.testUtils.http.get(`${DATA_BRIDGE_URL}/api/transform/adapters`);

      expect(response.status).toBe(200);
      expect(Array.isArray(response.data)).toBe(true);
      expect(response.data.some(adapter => adapter.id === 'json-to-json')).toBe(true);
      expect(response.data.some(adapter => adapter.id === 'csv-to-json')).toBe(true);
    });
  });

  describe('Privacy Management', () => {
    test('should create privacy policy', async () => {
      const policy = {
        policyId: 'test-privacy-policy',
        config: {
          name: 'Test Privacy Policy',
          dataTypes: ['personal-data'],
          classification: 'personal',
          allowedPurposes: ['testing', 'development'],
          allowedRecipients: ['test-service'],
          consentRequired: true
        }
      };

      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/privacy/policies`, policy);

      expect(response.status).toBe(200);
      expect(response.data.id).toBe(policy.policyId);
      expect(response.data.consentRequired).toBe(true);
    });

    test('should record user consent', async () => {
      const consent = {
        userId: testData.user.id,
        dataType: 'personal-data',
        purposes: ['testing'],
        options: {
          expiresAt: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString()
        }
      };

      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/privacy/consent`, consent);

      expect(response.status).toBe(200);
      expect(response.data.userId).toBe(testData.user.id);
      expect(response.data.status).toBe('granted');
    });

    test('should process data sharing with privacy controls', async () => {
      const sharingRequest = {
        data: {
          id: testData.user.id,
          email: testData.user.email,
          firstName: testData.user.firstName,
          sensitiveField: 'sensitive-data'
        },
        sourceApp: 'personal-log',
        targetApp: 'business-log',
        options: {
          userId: testData.user.id,
          purpose: 'testing',
          forceAnonymize: true
        }
      };

      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/privacy/share`, sharingRequest);

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('data');
      expect(response.data).toHaveProperty('metadata');
      expect(response.data.metadata.anonymized).toBe(true);
    });
  });

  describe('Search Index Management', () => {
    let testIndexName;

    beforeAll(() => {
      testIndexName = `test-index-${Date.now()}`;
    });

    test('should create search index', async () => {
      const indexConfig = {
        indexName: testIndexName,
        mapping: {
          properties: {
            title: { type: 'text', analyzer: 'standard' },
            content: { type: 'text', analyzer: 'content' },
            category: { type: 'keyword' },
            tags: { type: 'keyword' },
            createdAt: { type: 'date' }
          }
        },
        settings: {
          number_of_shards: 1,
          number_of_replicas: 0
        }
      };

      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/search/indices`, indexConfig);

      expect(response.status).toBe(200);
      expect(response.data.name).toBe(testIndexName);
    });

    test('should index document', async () => {
      const document = {
        document: testData.logEntry,
        options: {
          source: 'integration-test'
        }
      };

      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/search/indices/${testIndexName}/documents`, document);

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('id');
      expect(response.data.result).toBe('created');
    });

    test('should search documents', async () => {
      // Wait for document to be indexed
      await global.testUtils.sleep(2000);

      const searchRequest = {
        query: testData.logEntry.title,
        options: {
          index: testIndexName,
          size: 10
        }
      };

      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/search/search`, searchRequest);

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('hits');
      expect(Array.isArray(response.data.hits)).toBe(true);
    });

    test('should get search analytics', async () => {
      const response = await global.testUtils.http.get(`${DATA_BRIDGE_URL}/api/search/analytics`);

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('totalSearches');
      expect(response.data).toHaveProperty('averageResponseTime');
      expect(response.data).toHaveProperty('topQueries');
    });
  });

  describe('Data Lineage Tracking', () => {
    test('should track entity creation', async () => {
      const entityInfo = {
        entityId: testData.logEntry.id,
        entityInfo: {
          type: 'document',
          source: 'personal-log',
          createdBy: testData.user.id,
          metadata: {
            category: testData.logEntry.category,
            tags: testData.logEntry.tags
          }
        }
      };

      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/lineage/entities`, entityInfo);

      expect(response.status).toBe(200);
      expect(response.data.entityId).toBe(testData.logEntry.id);
      expect(response.data.type).toBe('document');
    });

    test('should track data transformation', async () => {
      const targetEntityId = `transformed-${testData.logEntry.id}`;
      const transformation = {
        sourceEntityId: testData.logEntry.id,
        targetEntityId: targetEntityId,
        transformationInfo: {
          type: 'format_conversion',
          name: 'Personal to Business Log Transform',
          description: 'Convert personal log entry to business format',
          appliedBy: testData.user.id,
          tool: 'data-bridge-transformer',
          parameters: {
            targetFormat: 'business-log',
            addProjectContext: true
          }
        }
      };

      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/lineage/transformations`, transformation);

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('transformationId');
    });

    test('should get entity lineage', async () => {
      const response = await global.testUtils.http.get(`${DATA_BRIDGE_URL}/api/lineage/entities/${testData.logEntry.id}`, {
        params: {
          direction: 'both',
          maxDepth: 5,
          includeTransformations: true
        }
      });

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('entity');
      expect(response.data).toHaveProperty('upstream');
      expect(response.data).toHaveProperty('downstream');
      expect(response.data).toHaveProperty('transformations');
    });

    test('should perform impact analysis', async () => {
      const impactRequest = {
        entityId: testData.logEntry.id,
        changeType: 'data_change'
      };

      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/lineage/impact-analysis`, impactRequest);

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('id');
      expect(response.data).toHaveProperty('directImpacts');
      expect(response.data).toHaveProperty('indirectImpacts');
      expect(response.data).toHaveProperty('recommendations');
    });
  });

  describe('Change Data Capture', () => {
    test('should create data watcher', async () => {
      const watcherConfig = {
        watcherId: 'test-watcher',
        config: {
          name: 'Test Data Watcher',
          dataSource: 'test-database',
          tableName: 'log_entries',
          primaryKey: 'id',
          changeTypes: ['INSERT', 'UPDATE', 'DELETE'],
          batchingEnabled: true,
          realTimeEnabled: true
        }
      };

      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/cdc/watchers`, watcherConfig);

      expect(response.status).toBe(200);
      expect(response.data.id).toBe(watcherConfig.watcherId);
      expect(response.data.isActive).toBe(false);
    });

    test('should start and stop watcher', async () => {
      // Start watcher
      const startResponse = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/cdc/watchers/test-watcher/start`);
      expect(startResponse.status).toBe(200);
      expect(startResponse.data.isActive).toBe(true);

      // Stop watcher
      const stopResponse = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/cdc/watchers/test-watcher/stop`);
      expect(stopResponse.status).toBe(200);
      expect(stopResponse.data.isActive).toBe(false);
    });

    test('should subscribe to change events', async () => {
      const subscription = {
        subscriberId: 'test-subscriber',
        config: {
          name: 'Test Change Subscriber',
          watcherIds: ['test-watcher'],
          changeTypes: ['INSERT', 'UPDATE'],
          realTimeEnabled: true,
          endpoint: 'http://localhost:3001/webhook/changes'
        }
      };

      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/cdc/subscriptions`, subscription);

      expect(response.status).toBe(200);
      expect(response.data.id).toBe(subscription.subscriberId);
      expect(response.data.realTimeEnabled).toBe(true);
    });
  });

  describe('Event Sourcing', () => {
    const streamId = `test-stream-${Date.now()}`;

    test('should append events to stream', async () => {
      const events = [
        {
          eventType: 'EntityCreated',
          data: {
            id: testData.logEntry.id,
            title: testData.logEntry.title,
            category: testData.logEntry.category
          },
          metadata: {
            causationId: 'test-command-1',
            correlationId: 'test-correlation-1'
          }
        },
        {
          eventType: 'EntityUpdated',
          data: {
            id: testData.logEntry.id,
            title: 'Updated Title'
          },
          metadata: {
            causationId: 'test-command-2',
            correlationId: 'test-correlation-1'
          }
        }
      ];

      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/events/streams/${streamId}/events`, {
        events,
        expectedVersion: -1
      });

      expect(response.status).toBe(200);
      expect(response.data.eventIds).toHaveLength(2);
      expect(response.data.version).toBe(1);
    });

    test('should retrieve events from stream', async () => {
      const response = await global.testUtils.http.get(`${DATA_BRIDGE_URL}/api/events/streams/${streamId}/events`, {
        params: {
          from: 0,
          limit: 10
        }
      });

      expect(response.status).toBe(200);
      expect(response.data.events).toHaveLength(2);
      expect(response.data.events[0].eventType).toBe('EntityCreated');
      expect(response.data.events[1].eventType).toBe('EntityUpdated');
    });

    test('should handle commands', async () => {
      const command = {
        type: 'UpdateEntity',
        aggregateId: streamId,
        data: {
          title: 'Command Updated Title',
          content: 'Updated via command'
        },
        userId: testData.user.id
      };

      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/events/commands`, command);

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('eventIds');
      expect(Array.isArray(response.data.eventIds)).toBe(true);
    });

    test('should create and query projections', async () => {
      const projection = {
        projectionId: 'test-projection',
        config: {
          name: 'Entity Summary Projection',
          eventTypes: ['EntityCreated', 'EntityUpdated'],
          initialState: { entities: {}, count: 0 },
          reducer: `
            function(state, event) {
              const newState = { ...state };
              if (event.eventType === 'EntityCreated') {
                newState.entities[event.data.id] = event.data;
                newState.count++;
              } else if (event.eventType === 'EntityUpdated') {
                newState.entities[event.data.id] = { ...newState.entities[event.data.id], ...event.data };
              }
              return newState;
            }
          `
        }
      };

      const createResponse = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/events/projections`, projection);
      expect(createResponse.status).toBe(200);

      // Query projection state
      const queryResponse = await global.testUtils.http.get(`${DATA_BRIDGE_URL}/api/events/projections/test-projection`);
      expect(queryResponse.status).toBe(200);
      expect(queryResponse.data).toHaveProperty('state');
    });
  });

  describe('Data Migration', () => {
    test('should register data sources for migration', async () => {
      const sourceConfig = {
        sourceId: 'test-source-db',
        config: {
          name: 'Test Source Database',
          type: 'database',
          connectionConfig: {
            host: 'localhost',
            port: 5432,
            database: 'test_source'
          },
          supportedOperations: ['read']
        }
      };

      const targetConfig = {
        sourceId: 'test-target-db',
        config: {
          name: 'Test Target Database',
          type: 'database',
          connectionConfig: {
            host: 'localhost',
            port: 5433,
            database: 'test_target'
          },
          supportedOperations: ['write']
        }
      };

      const sourceResponse = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/migrate/sources`, sourceConfig);
      expect(sourceResponse.status).toBe(200);

      const targetResponse = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/migrate/sources`, targetConfig);
      expect(targetResponse.status).toBe(200);
    });

    test('should create migration plan', async () => {
      const migration = {
        migrationId: 'test-migration',
        config: {
          name: 'Test Data Migration',
          description: 'Migrate log entries from source to target',
          sourceId: 'test-source-db',
          targetId: 'test-target-db',
          entityType: 'log-entry',
          strategy: 'full',
          batchSize: 100,
          transformationRules: {
            fieldMappings: {
              'old_title': 'title',
              'old_content': 'content'
            }
          },
          validationRules: {
            required: ['title', 'content'],
            patterns: {
              'title': '^.{1,200}$'
            }
          }
        }
      };

      const response = await global.testUtils.http.post(`${DATA_BRIDGE_URL}/api/migrate/migrations`, migration);

      expect(response.status).toBe(200);
      expect(response.data.id).toBe(migration.migrationId);
      expect(response.data.status).toBe('created');
    });

    test('should execute migration', async () => {
      const executeResponse = await global.testUtils.http.post(
        `${DATA_BRIDGE_URL}/api/migrate/migrations/test-migration/execute`,
        {
          dryRun: true, // Execute in dry-run mode for testing
          continueOnError: false
        }
      );

      expect(executeResponse.status).toBe(200);
      expect(executeResponse.data).toHaveProperty('id');
      expect(executeResponse.data).toHaveProperty('status');
    });

    test('should check migration status and progress', async () => {
      const statusResponse = await global.testUtils.http.get(`${DATA_BRIDGE_URL}/api/migrate/migrations/test-migration/status`);
      expect(statusResponse.status).toBe(200);
      expect(statusResponse.data).toHaveProperty('migration');
      expect(statusResponse.data).toHaveProperty('isRunning');

      const progressResponse = await global.testUtils.http.get(`${DATA_BRIDGE_URL}/api/migrate/migrations/test-migration/progress`);
      // Progress might not be available if migration is not running
      expect([200, 404]).toContain(progressResponse.status);
    });
  });

  describe('WebSocket Real-time Updates', () => {
    test('should connect to WebSocket and receive updates', async () => {
      const WebSocket = require('ws');
      
      return new Promise((resolve, reject) => {
        const ws = new WebSocket(`ws://localhost:18202`);
        let messageCount = 0;

        ws.on('open', () => {
          // Subscribe to updates
          ws.send(JSON.stringify({
            type: 'subscribe',
            topics: ['sync', 'events', 'search']
          }));
        });

        ws.on('message', (data) => {
          const message = JSON.parse(data.toString());
          messageCount++;

          if (message.type === 'welcome') {
            expect(message.message).toContain('Connected to Data Bridge');
          } else if (message.type === 'subscribed') {
            expect(message.topics).toContain('sync');
            expect(message.topics).toContain('events');
            expect(message.topics).toContain('search');
          }

          // Close after receiving a few messages
          if (messageCount >= 2) {
            ws.close();
            resolve();
          }
        });

        ws.on('error', reject);
        
        // Timeout after 10 seconds
        setTimeout(() => {
          ws.close();
          reject(new Error('WebSocket test timed out'));
        }, 10000);
      });
    });
  });

  describe('Health and Monitoring', () => {
    test('should return health status', async () => {
      const response = await global.testUtils.http.get(`${DATA_BRIDGE_URL}/health`);

      expect(response.status).toBe(200);
      expect(response.data.status).toBe('healthy');
      expect(response.data).toHaveProperty('timestamp');
      expect(response.data).toHaveProperty('services');
      
      // Check individual service health
      expect(response.data.services).toHaveProperty('unifiedSchema');
      expect(response.data.services).toHaveProperty('dataSync');
      expect(response.data.services).toHaveProperty('searchIndex');
    });
  });
});