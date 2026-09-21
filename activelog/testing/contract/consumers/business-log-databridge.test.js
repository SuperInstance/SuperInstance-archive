const { Matchers } = require('@pact-foundation/pact');
const { createBusinessLogDataBridgePact } = require('../pact.config');
const axios = require('axios');

const { like, eachLike, term, iso8601DateTime } = Matchers;

describe('BusinessLog -> DataBridge Contract Tests', () => {
  const provider = createBusinessLogDataBridgePact();

  beforeAll(() => provider.setup());
  afterEach(() => provider.verify());
  afterAll(() => provider.finalize());

  describe('Schema Validation', () => {
    test('should validate business log entry against schema', async () => {
      await provider.addInteraction({
        state: 'unified schema exists for document type',
        uponReceiving: 'a schema validation request for business log entry',
        withRequest: {
          method: 'POST',
          path: '/api/schema/validate',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: {
            entityType: 'document',
            data: {
              id: '550e8400-e29b-41d4-a716-446655440000',
              type: 'business-log',
              title: 'Business Meeting Notes',
              content: 'Discussion about Q1 objectives and team goals.',
              category: 'meeting',
              priority: 'high',
              projectId: '123e4567-e89b-12d3-a456-426614174000',
              assignedTo: '789e1234-e89b-12d3-a456-426614174000',
              tags: ['meeting', 'q1', 'objectives'],
              createdAt: '2024-01-01T10:00:00Z',
              updatedAt: '2024-01-01T10:30:00Z',
              createdBy: '789e1234-e89b-12d3-a456-426614174000'
            }
          }
        },
        willRespondWith: {
          status: 200,
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            valid: like(true),
            errors: eachLike(''),
            data: {
              id: like('550e8400-e29b-41d4-a716-446655440000'),
              type: like('business-log'),
              title: like('Business Meeting Notes'),
              content: like('Discussion about Q1 objectives and team goals.'),
              category: like('meeting'),
              priority: like('high'),
              projectId: like('123e4567-e89b-12d3-a456-426614174000'),
              assignedTo: like('789e1234-e89b-12d3-a456-426614174000'),
              tags: eachLike('meeting'),
              createdAt: iso8601DateTime('2024-01-01T10:00:00Z'),
              updatedAt: iso8601DateTime('2024-01-01T10:30:00Z'),
              createdBy: like('789e1234-e89b-12d3-a456-426614174000')
            },
            entityType: like('document'),
            timestamp: iso8601DateTime('2024-01-01T10:30:00Z')
          }
        }
      });

      const response = await axios.post(`${provider.mockService.baseUrl}/api/schema/validate`, {
        entityType: 'document',
        data: {
          id: '550e8400-e29b-41d4-a716-446655440000',
          type: 'business-log',
          title: 'Business Meeting Notes',
          content: 'Discussion about Q1 objectives and team goals.',
          category: 'meeting',
          priority: 'high',
          projectId: '123e4567-e89b-12d3-a456-426614174000',
          assignedTo: '789e1234-e89b-12d3-a456-426614174000',
          tags: ['meeting', 'q1', 'objectives'],
          createdAt: '2024-01-01T10:00:00Z',
          updatedAt: '2024-01-01T10:30:00Z',
          createdBy: '789e1234-e89b-12d3-a456-426614174000'
        }
      });

      expect(response.status).toBe(200);
      expect(response.data.valid).toBe(true);
      expect(response.data.data.type).toBe('business-log');
    });

    test('should transform personal log to business log format', async () => {
      await provider.addInteraction({
        state: 'transformation rules exist for personal to business log',
        uponReceiving: 'a transformation request from personal to business log',
        withRequest: {
          method: 'POST',
          path: '/api/schema/transform',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: {
            data: {
              id: '550e8400-e29b-41d4-a716-446655440000',
              title: 'Personal Task Notes',
              content: 'Need to complete the project documentation.',
              category: 'work',
              tags: ['task', 'documentation'],
              createdBy: '789e1234-e89b-12d3-a456-426614174000'
            },
            fromType: 'personal-log',
            toType: 'business-log',
            options: {
              defaultProjectId: '123e4567-e89b-12d3-a456-426614174000',
              businessUnit: 'Engineering'
            }
          }
        },
        willRespondWith: {
          status: 200,
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            success: like(true),
            data: {
              id: like('550e8400-e29b-41d4-a716-446655440000'),
              type: like('business-log'),
              title: like('Personal Task Notes'),
              content: like('Need to complete the project documentation.'),
              category: like('project'),
              priority: like('medium'),
              status: like('active'),
              tags: eachLike('task'),
              projectId: like('123e4567-e89b-12d3-a456-426614174000'),
              assignedTo: like('789e1234-e89b-12d3-a456-426614174000'),
              businessContext: {
                originalType: like('personal-log'),
                transformedAt: iso8601DateTime('2024-01-01T11:00:00Z'),
                confidentialityLevel: like('low')
              }
            }
          }
        }
      });

      const response = await axios.post(`${provider.mockService.baseUrl}/api/schema/transform`, {
        data: {
          id: '550e8400-e29b-41d4-a716-446655440000',
          title: 'Personal Task Notes',
          content: 'Need to complete the project documentation.',
          category: 'work',
          tags: ['task', 'documentation'],
          createdBy: '789e1234-e89b-12d3-a456-426614174000'
        },
        fromType: 'personal-log',
        toType: 'business-log',
        options: {
          defaultProjectId: '123e4567-e89b-12d3-a456-426614174000',
          businessUnit: 'Engineering'
        }
      });

      expect(response.status).toBe(200);
      expect(response.data.success).toBe(true);
      expect(response.data.data.type).toBe('business-log');
      expect(response.data.data.projectId).toBe('123e4567-e89b-12d3-a456-426614174000');
    });
  });

  describe('Data Synchronization', () => {
    test('should register business log service for sync', async () => {
      await provider.addInteraction({
        state: 'data bridge is ready to register services',
        uponReceiving: 'a service registration request for business log',
        withRequest: {
          method: 'POST',
          path: '/api/sync/services',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: {
            serviceName: 'business-log',
            config: {
              endpoint: 'http://localhost:3002/api',
              syncEnabled: true,
              syncStrategy: 'bidirectional',
              entityTypes: ['document', 'project'],
              rateLimits: {
                requests: 1000,
                window: 3600000
              },
              priority: 7,
              metadata: {
                version: '1.0.0',
                environment: 'development'
              }
            }
          }
        },
        willRespondWith: {
          status: 200,
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            name: like('business-log'),
            endpoint: like('http://localhost:3002/api'),
            syncEnabled: like(true),
            syncStrategy: like('bidirectional'),
            entityTypes: eachLike('document'),
            priority: like(7),
            registeredAt: iso8601DateTime('2024-01-01T11:00:00Z'),
            totalOperations: like(0),
            lastOperation: like(null)
          }
        }
      });

      const response = await axios.post(`${provider.mockService.baseUrl}/api/sync/services`, {
        serviceName: 'business-log',
        config: {
          endpoint: 'http://localhost:3002/api',
          syncEnabled: true,
          syncStrategy: 'bidirectional',
          entityTypes: ['document', 'project'],
          rateLimits: {
            requests: 1000,
            window: 3600000
          },
          priority: 7,
          metadata: {
            version: '1.0.0',
            environment: 'development'
          }
        }
      });

      expect(response.status).toBe(200);
      expect(response.data.name).toBe('business-log');
      expect(response.data.syncEnabled).toBe(true);
      expect(response.data.entityTypes).toContain('document');
    });

    test('should create sync rule for business documents', async () => {
      await provider.addInteraction({
        state: 'business log service is registered',
        uponReceiving: 'a sync rule creation request',
        withRequest: {
          method: 'POST',
          path: '/api/sync/rules',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: {
            ruleId: 'business-document-sync',
            config: {
              sourceService: 'business-log',
              targetServices: ['personal-log', 'data-warehouse'],
              entityType: 'document',
              syncMode: 'realtime',
              filters: {
                category: ['project', 'meeting', 'report'],
                priority: ['high', 'critical']
              },
              transformations: {
                fieldMapping: {
                  'assignedTo': 'ownerId',
                  'projectId': 'context.projectId'
                }
              }
            }
          }
        },
        willRespondWith: {
          status: 200,
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            id: like('business-document-sync'),
            sourceService: like('business-log'),
            targetServices: eachLike('personal-log'),
            entityType: like('document'),
            syncMode: like('realtime'),
            enabled: like(true),
            createdAt: iso8601DateTime('2024-01-01T11:00:00Z'),
            lastExecuted: like(null),
            successCount: like(0),
            errorCount: like(0)
          }
        }
      });

      const response = await axios.post(`${provider.mockService.baseUrl}/api/sync/rules`, {
        ruleId: 'business-document-sync',
        config: {
          sourceService: 'business-log',
          targetServices: ['personal-log', 'data-warehouse'],
          entityType: 'document',
          syncMode: 'realtime',
          filters: {
            category: ['project', 'meeting', 'report'],
            priority: ['high', 'critical']
          },
          transformations: {
            fieldMapping: {
              'assignedTo': 'ownerId',
              'projectId': 'context.projectId'
            }
          }
        }
      });

      expect(response.status).toBe(200);
      expect(response.data.id).toBe('business-document-sync');
      expect(response.data.syncMode).toBe('realtime');
      expect(response.data.targetServices).toContain('personal-log');
    });

    test('should sync business document to other services', async () => {
      await provider.addInteraction({
        state: 'sync rule exists and target services are available',
        uponReceiving: 'a document sync request',
        withRequest: {
          method: 'POST',
          path: '/api/sync/sync',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: {
            entityType: 'document',
            entityId: '550e8400-e29b-41d4-a716-446655440000',
            sourceService: 'business-log',
            options: {
              targetServices: ['personal-log'],
              priority: 'high'
            }
          }
        },
        willRespondWith: {
          status: 200,
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            id: term({
              matcher: '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
              generate: '123e4567-e89b-12d3-a456-426614174000'
            }),
            entityType: like('document'),
            entityId: like('550e8400-e29b-41d4-a716-446655440000'),
            sourceService: like('business-log'),
            targetServices: eachLike('personal-log'),
            status: term({
              matcher: '^(completed|partial|failed)$',
              generate: 'completed'
            }),
            results: {
              'personal-log': {
                success: like(true),
                action: like('updated'),
                result: {
                  id: like('550e8400-e29b-41d4-a716-446655440000'),
                  status: like('synced')
                }
              }
            },
            startTime: iso8601DateTime('2024-01-01T11:00:00Z'),
            endTime: iso8601DateTime('2024-01-01T11:00:05Z')
          }
        }
      });

      const response = await axios.post(`${provider.mockService.baseUrl}/api/sync/sync`, {
        entityType: 'document',
        entityId: '550e8400-e29b-41d4-a716-446655440000',
        sourceService: 'business-log',
        options: {
          targetServices: ['personal-log'],
          priority: 'high'
        }
      });

      expect(response.status).toBe(200);
      expect(response.data.status).toMatch(/^(completed|partial|failed)$/);
      expect(response.data.results['personal-log'].success).toBe(true);
    });
  });

  describe('Search and Indexing', () => {
    test('should index business document for search', async () => {
      await provider.addInteraction({
        state: 'search index exists for business documents',
        uponReceiving: 'a document indexing request',
        withRequest: {
          method: 'POST',
          path: '/api/search/indices/business-documents/documents',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: {
            document: {
              id: '550e8400-e29b-41d4-a716-446655440000',
              title: 'Q1 Business Review',
              content: 'Comprehensive review of Q1 performance metrics and objectives.',
              category: 'report',
              priority: 'high',
              tags: ['q1', 'review', 'metrics'],
              projectId: '123e4567-e89b-12d3-a456-426614174000',
              departmentId: 'dept-engineering',
              createdAt: '2024-01-01T11:00:00Z',
              createdBy: '789e1234-e89b-12d3-a456-426614174000'
            },
            options: {
              source: 'business-log',
              filters: ['privacy']
            }
          }
        },
        willRespondWith: {
          status: 200,
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            id: like('550e8400-e29b-41d4-a716-446655440000'),
            index: like('business-documents'),
            result: term({
              matcher: '^(created|updated)$',
              generate: 'created'
            }),
            version: like(1)
          }
        }
      });

      const response = await axios.post(`${provider.mockService.baseUrl}/api/search/indices/business-documents/documents`, {
        document: {
          id: '550e8400-e29b-41d4-a716-446655440000',
          title: 'Q1 Business Review',
          content: 'Comprehensive review of Q1 performance metrics and objectives.',
          category: 'report',
          priority: 'high',
          tags: ['q1', 'review', 'metrics'],
          projectId: '123e4567-e89b-12d3-a456-426614174000',
          departmentId: 'dept-engineering',
          createdAt: '2024-01-01T11:00:00Z',
          createdBy: '789e1234-e89b-12d3-a456-426614174000'
        },
        options: {
          source: 'business-log',
          filters: ['privacy']
        }
      });

      expect(response.status).toBe(200);
      expect(response.data.result).toMatch(/^(created|updated)$/);
      expect(response.data.index).toBe('business-documents');
    });

    test('should search business documents', async () => {
      await provider.addInteraction({
        state: 'business documents are indexed',
        uponReceiving: 'a search request for business documents',
        withRequest: {
          method: 'POST',
          path: '/api/search/search',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: {
            query: 'Q1 review metrics',
            options: {
              index: 'business-documents',
              filters: {
                category: ['report'],
                priority: ['high']
              },
              size: 20,
              sort: [
                { priority: { order: 'desc' } },
                { createdAt: { order: 'desc' } }
              ]
            }
          }
        },
        willRespondWith: {
          status: 200,
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            query: like('Q1 review metrics'),
            took: like(45),
            total: like(3),
            hits: eachLike({
              id: '550e8400-e29b-41d4-a716-446655440000',
              index: 'business-documents',
              score: 1.2345,
              source: {
                id: like('550e8400-e29b-41d4-a716-446655440000'),
                title: like('Q1 Business Review'),
                content: like('Comprehensive review of Q1 performance metrics and objectives.'),
                category: like('report'),
                priority: like('high'),
                tags: eachLike('q1'),
                createdAt: iso8601DateTime('2024-01-01T11:00:00Z')
              },
              highlight: {
                title: eachLike('<mark>Q1</mark> Business <mark>Review</mark>'),
                content: eachLike('Comprehensive <mark>review</mark> of <mark>Q1</mark> performance <mark>metrics</mark>')
              }
            }),
            searchId: term({
              matcher: '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
              generate: '123e4567-e89b-12d3-a456-426614174000'
            })
          }
        }
      });

      const response = await axios.post(`${provider.mockService.baseUrl}/api/search/search`, {
        query: 'Q1 review metrics',
        options: {
          index: 'business-documents',
          filters: {
            category: ['report'],
            priority: ['high']
          },
          size: 20,
          sort: [
            { priority: { order: 'desc' } },
            { createdAt: { order: 'desc' } }
          ]
        }
      });

      expect(response.status).toBe(200);
      expect(response.data.total).toBe(3);
      expect(response.data.hits.length).toBeGreaterThan(0);
      expect(response.data.hits[0].source.category).toBe('report');
    });
  });

  describe('Privacy and Data Protection', () => {
    test('should process data sharing with privacy controls', async () => {
      await provider.addInteraction({
        state: 'privacy policies exist for business data',
        uponReceiving: 'a data sharing request with privacy controls',
        withRequest: {
          method: 'POST',
          path: '/api/privacy/share',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: {
            data: {
              id: '550e8400-e29b-41d4-a716-446655440000',
              title: 'Confidential Business Plan',
              content: 'Strategic business plan containing sensitive financial data.',
              assignedTo: '789e1234-e89b-12d3-a456-426614174000',
              departmentId: 'dept-finance',
              confidentialityLevel: 'high'
            },
            sourceApp: 'business-log',
            targetApp: 'analytics-service',
            options: {
              userId: '789e1234-e89b-12d3-a456-426614174000',
              purpose: 'analytics',
              forceAnonymize: true,
              classification: 'confidential'
            }
          }
        },
        willRespondWith: {
          status: 200,
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            data: {
              id: like('550e8400-e29b-41d4-a716-446655440000'),
              title: like('[REDACTED]'),
              content: like('[REDACTED]'),
              assignedTo: term({
                matcher: '^[a-f0-9]{8}$',
                generate: 'a1b2c3d4'
              }),
              departmentId: like('dept-finance'),
              confidentialityLevel: like('high')
            },
            metadata: {
              sharingId: term({
                matcher: '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
                generate: '123e4567-e89b-12d3-a456-426614174000'
              }),
              classification: like('confidential'),
              anonymized: like(true),
              encrypted: like(false),
              processedAt: iso8601DateTime('2024-01-01T11:30:00Z')
            }
          }
        }
      });

      const response = await axios.post(`${provider.mockService.baseUrl}/api/privacy/share`, {
        data: {
          id: '550e8400-e29b-41d4-a716-446655440000',
          title: 'Confidential Business Plan',
          content: 'Strategic business plan containing sensitive financial data.',
          assignedTo: '789e1234-e89b-12d3-a456-426614174000',
          departmentId: 'dept-finance',
          confidentialityLevel: 'high'
        },
        sourceApp: 'business-log',
        targetApp: 'analytics-service',
        options: {
          userId: '789e1234-e89b-12d3-a456-426614174000',
          purpose: 'analytics',
          forceAnonymize: true,
          classification: 'confidential'
        }
      });

      expect(response.status).toBe(200);
      expect(response.data.metadata.anonymized).toBe(true);
      expect(response.data.data.title).toBe('[REDACTED]');
    });
  });

  describe('Event Sourcing', () => {
    test('should append business events to event stream', async () => {
      await provider.addInteraction({
        state: 'event sourcing system is available',
        uponReceiving: 'a request to append business events',
        withRequest: {
          method: 'POST',
          path: '/api/events/streams/business-log-123/events',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: {
            events: [
              {
                eventType: 'DocumentCreated',
                data: {
                  id: '550e8400-e29b-41d4-a716-446655440000',
                  title: 'New Business Document',
                  category: 'report',
                  projectId: '123e4567-e89b-12d3-a456-426614174000'
                },
                metadata: {
                  causationId: 'cmd-create-document',
                  correlationId: 'business-flow-001',
                  userId: '789e1234-e89b-12d3-a456-426614174000'
                }
              },
              {
                eventType: 'DocumentCategorized',
                data: {
                  id: '550e8400-e29b-41d4-a716-446655440000',
                  category: 'report',
                  subcategory: 'quarterly'
                },
                metadata: {
                  causationId: 'cmd-categorize-document',
                  correlationId: 'business-flow-001',
                  userId: '789e1234-e89b-12d3-a456-426614174000'
                }
              }
            ],
            expectedVersion: -1
          }
        },
        willRespondWith: {
          status: 200,
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            streamId: like('business-log-123'),
            eventIds: eachLike('evt-123e4567-e89b-12d3-a456-426614174000'),
            version: like(1),
            eventCount: like(2)
          }
        }
      });

      const response = await axios.post(`${provider.mockService.baseUrl}/api/events/streams/business-log-123/events`, {
        events: [
          {
            eventType: 'DocumentCreated',
            data: {
              id: '550e8400-e29b-41d4-a716-446655440000',
              title: 'New Business Document',
              category: 'report',
              projectId: '123e4567-e89b-12d3-a456-426614174000'
            },
            metadata: {
              causationId: 'cmd-create-document',
              correlationId: 'business-flow-001',
              userId: '789e1234-e89b-12d3-a456-426614174000'
            }
          },
          {
            eventType: 'DocumentCategorized',
            data: {
              id: '550e8400-e29b-41d4-a716-446655440000',
              category: 'report',
              subcategory: 'quarterly'
            },
            metadata: {
              causationId: 'cmd-categorize-document',
              correlationId: 'business-flow-001',
              userId: '789e1234-e89b-12d3-a456-426614174000'
            }
          }
        ],
        expectedVersion: -1
      });

      expect(response.status).toBe(200);
      expect(response.data.streamId).toBe('business-log-123');
      expect(response.data.eventCount).toBe(2);
      expect(Array.isArray(response.data.eventIds)).toBe(true);
    });

    test('should handle business commands', async () => {
      await provider.addInteraction({
        state: 'command handlers are registered for business operations',
        uponReceiving: 'a business command',
        withRequest: {
          method: 'POST',
          path: '/api/events/commands',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: {
            type: 'AssignDocumentToProject',
            aggregateId: '550e8400-e29b-41d4-a716-446655440000',
            data: {
              projectId: '123e4567-e89b-12d3-a456-426614174000',
              assignedTo: '789e1234-e89b-12d3-a456-426614174000',
              priority: 'high',
              dueDate: '2024-01-15T23:59:59Z'
            },
            userId: '789e1234-e89b-12d3-a456-426614174000',
            correlationId: 'business-assign-001'
          }
        },
        willRespondWith: {
          status: 200,
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            eventIds: eachLike('evt-456e7890-e89b-12d3-a456-426614174000'),
            version: like(3),
            commandId: term({
              matcher: '^cmd-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
              generate: 'cmd-456e7890-e89b-12d3-a456-426614174000'
            })
          }
        }
      });

      const response = await axios.post(`${provider.mockService.baseUrl}/api/events/commands`, {
        type: 'AssignDocumentToProject',
        aggregateId: '550e8400-e29b-41d4-a716-446655440000',
        data: {
          projectId: '123e4567-e89b-12d3-a456-426614174000',
          assignedTo: '789e1234-e89b-12d3-a456-426614174000',
          priority: 'high',
          dueDate: '2024-01-15T23:59:59Z'
        },
        userId: '789e1234-e89b-12d3-a456-426614174000',
        correlationId: 'business-assign-001'
      });

      expect(response.status).toBe(200);
      expect(Array.isArray(response.data.eventIds)).toBe(true);
      expect(response.data.commandId).toMatch(/^cmd-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/);
    });
  });
});