const { test, expect } = require('@playwright/test');
const axios = require('axios');

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8201';

test.describe('API End-to-End Tests', () => {
  let authToken;
  let testUser;

  test.beforeAll(async () => {
    // Create test user and get auth token
    testUser = {
      email: `api-test-${Date.now()}@example.com`,
      password: 'ApiTestPassword123!',
      firstName: 'API',
      lastName: 'Tester'
    };

    // Register user
    const registerResponse = await axios.post(`${API_BASE_URL}/api/auth/register`, testUser);
    expect(registerResponse.status).toBe(201);

    // Login to get token
    const loginResponse = await axios.post(`${API_BASE_URL}/api/auth/login`, {
      email: testUser.email,
      password: testUser.password
    });
    expect(loginResponse.status).toBe(200);
    authToken = loginResponse.data.token;
  });

  test('SSO Authentication Flow', async () => {
    // Test token validation
    const validateResponse = await axios.get(`${API_BASE_URL}/api/auth/validate`, {
      headers: { Authorization: `Bearer ${authToken}` }
    });
    expect(validateResponse.status).toBe(200);
    expect(validateResponse.data.valid).toBe(true);

    // Test user profile retrieval
    const profileResponse = await axios.get(`${API_BASE_URL}/api/users/profile`, {
      headers: { Authorization: `Bearer ${authToken}` }
    });
    expect(profileResponse.status).toBe(200);
    expect(profileResponse.data.email).toBe(testUser.email);
  });

  test('Data Bridge Schema Operations', async () => {
    const DATA_BRIDGE_URL = 'http://localhost:8202';

    // Test schema retrieval
    const schemasResponse = await axios.get(`${DATA_BRIDGE_URL}/api/schema`);
    expect(schemasResponse.status).toBe(200);
    expect(schemasResponse.data).toHaveProperty('user');
    expect(schemasResponse.data).toHaveProperty('document');

    // Test entity validation
    const validationResponse = await axios.post(`${DATA_BRIDGE_URL}/api/schema/validate`, {
      entityType: 'user',
      data: {
        id: '123e4567-e89b-12d3-a456-426614174000',
        email: 'test@example.com',
        firstName: 'Test',
        lastName: 'User'
      }
    });
    expect(validationResponse.status).toBe(200);
    expect(validationResponse.data.valid).toBe(true);

    // Test invalid entity validation
    const invalidValidationResponse = await axios.post(`${DATA_BRIDGE_URL}/api/schema/validate`, {
      entityType: 'user',
      data: {
        id: 'invalid-id',
        email: 'not-an-email'
      }
    });
    expect(invalidValidationResponse.status).toBe(200);
    expect(invalidValidationResponse.data.valid).toBe(false);
    expect(invalidValidationResponse.data.errors.length).toBeGreaterThan(0);
  });

  test('Personal Log CRUD Operations', async () => {
    // Create log entry
    const createEntryData = {
      title: 'API Test Entry',
      content: 'This is a test entry created via API',
      category: 'personal',
      tags: ['api', 'test', 'automation'],
      priority: 'medium'
    };

    const createResponse = await axios.post(`${API_BASE_URL}/api/personal-log/entries`, createEntryData, {
      headers: { Authorization: `Bearer ${authToken}` }
    });
    expect(createResponse.status).toBe(201);
    expect(createResponse.data).toHaveProperty('id');
    const entryId = createResponse.data.id;

    // Retrieve entry
    const getResponse = await axios.get(`${API_BASE_URL}/api/personal-log/entries/${entryId}`, {
      headers: { Authorization: `Bearer ${authToken}` }
    });
    expect(getResponse.status).toBe(200);
    expect(getResponse.data.title).toBe(createEntryData.title);
    expect(getResponse.data.content).toBe(createEntryData.content);

    // Update entry
    const updateData = {
      title: 'Updated API Test Entry',
      content: 'This content has been updated via API'
    };

    const updateResponse = await axios.put(`${API_BASE_URL}/api/personal-log/entries/${entryId}`, updateData, {
      headers: { Authorization: `Bearer ${authToken}` }
    });
    expect(updateResponse.status).toBe(200);
    expect(updateResponse.data.title).toBe(updateData.title);

    // List entries
    const listResponse = await axios.get(`${API_BASE_URL}/api/personal-log/entries`, {
      headers: { Authorization: `Bearer ${authToken}` }
    });
    expect(listResponse.status).toBe(200);
    expect(Array.isArray(listResponse.data.entries)).toBe(true);
    expect(listResponse.data.entries.some(entry => entry.id === entryId)).toBe(true);

    // Delete entry
    const deleteResponse = await axios.delete(`${API_BASE_URL}/api/personal-log/entries/${entryId}`, {
      headers: { Authorization: `Bearer ${authToken}` }
    });
    expect(deleteResponse.status).toBe(204);

    // Verify deletion
    try {
      await axios.get(`${API_BASE_URL}/api/personal-log/entries/${entryId}`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      throw new Error('Expected 404 error');
    } catch (error) {
      expect(error.response.status).toBe(404);
    }
  });

  test('Business Log Operations', async () => {
    // Create project
    const projectData = {
      name: 'API Test Project',
      description: 'Project created via API testing',
      status: 'active',
      startDate: new Date().toISOString(),
      team: [
        {
          userId: testUser.id,
          role: 'owner',
          permissions: ['read', 'write', 'delete']
        }
      ]
    };

    const createProjectResponse = await axios.post(`${API_BASE_URL}/api/business-log/projects`, projectData, {
      headers: { Authorization: `Bearer ${authToken}` }
    });
    expect(createProjectResponse.status).toBe(201);
    const projectId = createProjectResponse.data.id;

    // Create business log entry
    const businessEntryData = {
      title: 'API Business Entry',
      content: 'Business entry created via API',
      projectId: projectId,
      category: 'project',
      priority: 'high',
      assignedTo: testUser.id
    };

    const createBusinessEntryResponse = await axios.post(`${API_BASE_URL}/api/business-log/entries`, businessEntryData, {
      headers: { Authorization: `Bearer ${authToken}` }
    });
    expect(createBusinessEntryResponse.status).toBe(201);

    // Verify project association
    const projectResponse = await axios.get(`${API_BASE_URL}/api/business-log/projects/${projectId}`, {
      headers: { Authorization: `Bearer ${authToken}` }
    });
    expect(projectResponse.status).toBe(200);
    expect(projectResponse.data.name).toBe(projectData.name);
  });

  test('Search Functionality', async () => {
    const DATA_BRIDGE_URL = 'http://localhost:8202';

    // Create test index
    const indexName = `test-index-${Date.now()}`;
    const createIndexResponse = await axios.post(`${DATA_BRIDGE_URL}/api/search/indices`, {
      indexName: indexName,
      mapping: {
        properties: {
          title: { type: 'text' },
          content: { type: 'text' },
          tags: { type: 'keyword' }
        }
      }
    });
    expect(createIndexResponse.status).toBe(200);

    // Index test documents
    const testDocuments = [
      {
        id: '1',
        title: 'First Test Document',
        content: 'This is the content of the first test document',
        tags: ['test', 'first']
      },
      {
        id: '2',
        title: 'Second Test Document',
        content: 'This is the content of the second test document',
        tags: ['test', 'second']
      }
    ];

    for (const doc of testDocuments) {
      const indexResponse = await axios.post(`${DATA_BRIDGE_URL}/api/search/indices/${indexName}/documents`, {
        document: doc
      });
      expect(indexResponse.status).toBe(200);
    }

    // Wait for indexing
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Search documents
    const searchResponse = await axios.post(`${DATA_BRIDGE_URL}/api/search/search`, {
      query: 'test document',
      options: {
        index: indexName
      }
    });
    expect(searchResponse.status).toBe(200);
    expect(searchResponse.data.hits.length).toBeGreaterThan(0);
  });

  test('Data Sync Operations', async () => {
    const DATA_BRIDGE_URL = 'http://localhost:8202';

    // Register services
    const personalLogService = {
      serviceName: 'personal-log',
      config: {
        endpoint: `${API_BASE_URL}/api/personal-log`,
        syncEnabled: true,
        syncStrategy: 'bidirectional',
        entityTypes: ['document']
      }
    };

    const registerResponse = await axios.post(`${DATA_BRIDGE_URL}/api/sync/services`, personalLogService);
    expect(registerResponse.status).toBe(200);

    // Create sync rule
    const syncRule = {
      ruleId: 'test-sync-rule',
      config: {
        sourceService: 'personal-log',
        targetServices: ['business-log'],
        entityType: 'document',
        syncMode: 'realtime'
      }
    };

    const createRuleResponse = await axios.post(`${DATA_BRIDGE_URL}/api/sync/rules`, syncRule);
    expect(createRuleResponse.status).toBe(200);

    // Test entity sync
    const syncResponse = await axios.post(`${DATA_BRIDGE_URL}/api/sync/sync`, {
      entityType: 'document',
      entityId: 'test-entity-id',
      sourceService: 'personal-log'
    });
    expect(syncResponse.status).toBe(200);
  });

  test('Privacy and Data Protection', async () => {
    const DATA_BRIDGE_URL = 'http://localhost:8202';

    // Create privacy policy
    const privacyPolicy = {
      policyId: 'test-policy',
      config: {
        name: 'Test Privacy Policy',
        dataTypes: ['personal-data'],
        classification: 'personal',
        allowedPurposes: ['testing', 'analytics'],
        consentRequired: true
      }
    };

    const policyResponse = await axios.post(`${DATA_BRIDGE_URL}/api/privacy/policies`, privacyPolicy);
    expect(policyResponse.status).toBe(200);

    // Record consent
    const consent = {
      userId: testUser.id,
      dataType: 'personal-data',
      purposes: ['testing'],
      options: {
        expiresAt: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString()
      }
    };

    const consentResponse = await axios.post(`${DATA_BRIDGE_URL}/api/privacy/consent`, consent);
    expect(consentResponse.status).toBe(200);

    // Test data sharing
    const sharingRequest = {
      data: {
        id: testUser.id,
        email: testUser.email,
        firstName: testUser.firstName
      },
      sourceApp: 'personal-log',
      targetApp: 'business-log',
      options: {
        userId: testUser.id,
        purpose: 'testing'
      }
    };

    const sharingResponse = await axios.post(`${DATA_BRIDGE_URL}/api/privacy/share`, sharingRequest);
    expect(sharingResponse.status).toBe(200);
    expect(sharingResponse.data).toHaveProperty('data');
    expect(sharingResponse.data).toHaveProperty('metadata');
  });

  test('Event Sourcing Operations', async () => {
    const DATA_BRIDGE_URL = 'http://localhost:8202';
    const streamId = `test-stream-${Date.now()}`;

    // Append events
    const events = [
      {
        eventType: 'EntityCreated',
        data: {
          entityId: streamId,
          name: 'Test Entity',
          type: 'test'
        }
      },
      {
        eventType: 'EntityUpdated',
        data: {
          entityId: streamId,
          name: 'Updated Test Entity'
        }
      }
    ];

    const appendResponse = await axios.post(`${DATA_BRIDGE_URL}/api/events/streams/${streamId}/events`, {
      events: events
    });
    expect(appendResponse.status).toBe(200);
    expect(appendResponse.data.eventIds.length).toBe(2);

    // Retrieve events
    const getEventsResponse = await axios.get(`${DATA_BRIDGE_URL}/api/events/streams/${streamId}/events`);
    expect(getEventsResponse.status).toBe(200);
    expect(getEventsResponse.data.events.length).toBe(2);

    // Test command handling
    const command = {
      type: 'UpdateEntity',
      aggregateId: streamId,
      data: {
        name: 'Command Updated Entity'
      }
    };

    const commandResponse = await axios.post(`${DATA_BRIDGE_URL}/api/events/commands`, command);
    expect(commandResponse.status).toBe(200);
  });

  test('Error Handling and Edge Cases', async () => {
    // Test 404 errors
    try {
      await axios.get(`${API_BASE_URL}/api/personal-log/entries/non-existent-id`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      throw new Error('Expected 404 error');
    } catch (error) {
      expect(error.response.status).toBe(404);
    }

    // Test invalid authentication
    try {
      await axios.get(`${API_BASE_URL}/api/personal-log/entries`, {
        headers: { Authorization: 'Bearer invalid-token' }
      });
      throw new Error('Expected 401 error');
    } catch (error) {
      expect(error.response.status).toBe(401);
    }

    // Test invalid data
    try {
      await axios.post(`${API_BASE_URL}/api/personal-log/entries`, {
        title: '', // Invalid empty title
        content: 'Test content'
      }, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      throw new Error('Expected 400 error');
    } catch (error) {
      expect(error.response.status).toBe(400);
    }

    // Test rate limiting
    const requests = Array(150).fill().map(() => 
      axios.get(`${API_BASE_URL}/health`).catch(err => err.response)
    );
    
    const responses = await Promise.all(requests);
    const rateLimitedResponses = responses.filter(response => 
      response && response.status === 429
    );
    
    expect(rateLimitedResponses.length).toBeGreaterThan(0);
  });

  test('WebSocket Connections', async ({ page }) => {
    // Test WebSocket connection to data bridge
    await page.goto('/dashboard');
    
    const wsConnected = await page.evaluate(() => {
      return new Promise((resolve) => {
        const ws = new WebSocket('ws://localhost:8202');
        ws.onopen = () => resolve(true);
        ws.onerror = () => resolve(false);
        setTimeout(() => resolve(false), 5000);
      });
    });
    
    expect(wsConnected).toBe(true);

    // Test real-time updates
    const messageReceived = await page.evaluate(() => {
      return new Promise((resolve) => {
        const ws = new WebSocket('ws://localhost:8202');
        ws.onopen = () => {
          ws.send(JSON.stringify({
            type: 'subscribe',
            topics: ['sync', 'events']
          }));
        };
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.type === 'subscribed') {
            resolve(true);
          }
        };
        setTimeout(() => resolve(false), 5000);
      });
    });
    
    expect(messageReceived).toBe(true);
  });
});

// Utility functions for API testing
async function createTestData(authToken) {
  const entries = [];
  for (let i = 0; i < 5; i++) {
    const entryData = {
      title: `Test Entry ${i + 1}`,
      content: `Content for test entry ${i + 1}`,
      category: i % 2 === 0 ? 'personal' : 'work',
      tags: [`tag${i}`, 'test']
    };

    const response = await axios.post(`${API_BASE_URL}/api/personal-log/entries`, entryData, {
      headers: { Authorization: `Bearer ${authToken}` }
    });
    entries.push(response.data);
  }
  return entries;
}

async function cleanupTestData(authToken, entryIds) {
  for (const entryId of entryIds) {
    try {
      await axios.delete(`${API_BASE_URL}/api/personal-log/entries/${entryId}`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
    } catch (error) {
      // Ignore cleanup errors
    }
  }
}

module.exports = {
  createTestData,
  cleanupTestData
};