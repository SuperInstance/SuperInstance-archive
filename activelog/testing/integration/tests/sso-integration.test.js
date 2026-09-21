const jwt = require('jsonwebtoken');

describe('SSO System Integration Tests', () => {
  const SSO_BASE_URL = process.env.SSO_SYSTEM_URL || 'http://localhost:18201';
  let testUser;
  let authToken;

  beforeAll(async () => {
    // Create test user
    testUser = global.testUtils.generateUser({
      email: 'sso-integration-test@example.com',
      password: 'TestPassword123!'
    });
  });

  describe('Authentication Flow', () => {
    test('should register a new user', async () => {
      const response = await global.testUtils.http.post(`${SSO_BASE_URL}/api/auth/register`, {
        email: testUser.email,
        password: testUser.password,
        firstName: testUser.firstName,
        lastName: testUser.lastName
      });

      expect(response.status).toBe(201);
      expect(response.data).toHaveProperty('user');
      expect(response.data).toHaveProperty('token');
      expect(response.data.user.email).toBe(testUser.email);
      
      authToken = response.data.token;
    });

    test('should not register user with duplicate email', async () => {
      const response = await global.testUtils.http.post(`${SSO_BASE_URL}/api/auth/register`, {
        email: testUser.email,
        password: 'AnotherPassword123!',
        firstName: 'Another',
        lastName: 'User'
      });

      expect(response.status).toBe(409);
      expect(response.data.error).toContain('already exists');
    });

    test('should login with valid credentials', async () => {
      const response = await global.testUtils.http.post(`${SSO_BASE_URL}/api/auth/login`, {
        email: testUser.email,
        password: testUser.password
      });

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('token');
      expect(response.data).toHaveProperty('user');
      expect(response.data.user.email).toBe(testUser.email);

      // Verify JWT token structure
      const decoded = jwt.decode(response.data.token);
      expect(decoded).toHaveProperty('userId');
      expect(decoded).toHaveProperty('email');
      expect(decoded).toHaveProperty('exp');
    });

    test('should reject login with invalid credentials', async () => {
      const response = await global.testUtils.http.post(`${SSO_BASE_URL}/api/auth/login`, {
        email: testUser.email,
        password: 'WrongPassword'
      });

      expect(response.status).toBe(401);
      expect(response.data.error).toContain('Invalid credentials');
    });

    test('should validate JWT token', async () => {
      const response = await global.testUtils.http.get(`${SSO_BASE_URL}/api/auth/validate`, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });

      expect(response.status).toBe(200);
      expect(response.data.valid).toBe(true);
      expect(response.data.user.email).toBe(testUser.email);
    });

    test('should reject invalid JWT token', async () => {
      const response = await global.testUtils.http.get(`${SSO_BASE_URL}/api/auth/validate`, {
        headers: {
          Authorization: 'Bearer invalid-token'
        }
      });

      expect(response.status).toBe(401);
      expect(response.data.valid).toBe(false);
    });
  });

  describe('Multi-Factor Authentication', () => {
    test('should enable MFA for user', async () => {
      const response = await global.testUtils.http.post(`${SSO_BASE_URL}/api/auth/mfa/enable`, {}, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('secret');
      expect(response.data).toHaveProperty('qrCode');
      expect(response.data).toHaveProperty('backupCodes');
    });

    test('should verify MFA token', async () => {
      // First enable MFA
      const enableResponse = await global.testUtils.http.post(`${SSO_BASE_URL}/api/auth/mfa/enable`, {}, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });

      // Mock TOTP verification (in real test, you'd generate actual TOTP)
      const mockTotpCode = '123456';
      const verifyResponse = await global.testUtils.http.post(`${SSO_BASE_URL}/api/auth/mfa/verify`, {
        token: mockTotpCode
      }, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });

      expect(verifyResponse.status).toBe(200);
      expect(verifyResponse.data.verified).toBe(true);
    });
  });

  describe('Role-Based Access Control', () => {
    test('should create role', async () => {
      const roleData = {
        name: 'test-role',
        description: 'Test role for integration testing',
        permissions: ['read:personal-log', 'write:personal-log']
      };

      const response = await global.testUtils.http.post(`${SSO_BASE_URL}/api/rbac/roles`, roleData, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });

      expect(response.status).toBe(201);
      expect(response.data.name).toBe(roleData.name);
      expect(response.data.permissions).toEqual(roleData.permissions);
    });

    test('should assign role to user', async () => {
      const response = await global.testUtils.http.post(`${SSO_BASE_URL}/api/rbac/users/${testUser.id}/roles`, {
        roles: ['test-role']
      }, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });

      expect(response.status).toBe(200);
      expect(response.data.roles).toContain('test-role');
    });

    test('should check user permissions', async () => {
      const response = await global.testUtils.http.get(`${SSO_BASE_URL}/api/rbac/users/${testUser.id}/permissions`, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });

      expect(response.status).toBe(200);
      expect(response.data.permissions).toContain('read:personal-log');
      expect(response.data.permissions).toContain('write:personal-log');
    });
  });

  describe('Session Management', () => {
    test('should create session', async () => {
      const sessionData = {
        userId: testUser.id,
        deviceInfo: {
          userAgent: 'Jest Integration Test',
          ipAddress: '127.0.0.1'
        }
      };

      const response = await global.testUtils.http.post(`${SSO_BASE_URL}/api/sessions`, sessionData, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });

      expect(response.status).toBe(201);
      expect(response.data).toHaveProperty('sessionId');
      expect(response.data.userId).toBe(testUser.id);
    });

    test('should get active sessions', async () => {
      const response = await global.testUtils.http.get(`${SSO_BASE_URL}/api/sessions`, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });

      expect(response.status).toBe(200);
      expect(Array.isArray(response.data)).toBe(true);
      expect(response.data.length).toBeGreaterThan(0);
    });

    test('should revoke session', async () => {
      // Create a session first
      const createResponse = await global.testUtils.http.post(`${SSO_BASE_URL}/api/sessions`, {
        userId: testUser.id,
        deviceInfo: { userAgent: 'Test Session' }
      }, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });

      const sessionId = createResponse.data.sessionId;

      // Revoke the session
      const revokeResponse = await global.testUtils.http.delete(`${SSO_BASE_URL}/api/sessions/${sessionId}`, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });

      expect(revokeResponse.status).toBe(204);
    });
  });

  describe('API Key Management', () => {
    let apiKeyId;

    test('should create API key', async () => {
      const keyData = {
        name: 'Test API Key',
        scopes: ['read:personal-log'],
        expiresAt: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString()
      };

      const response = await global.testUtils.http.post(`${SSO_BASE_URL}/api/api-keys`, keyData, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });

      expect(response.status).toBe(201);
      expect(response.data).toHaveProperty('id');
      expect(response.data).toHaveProperty('key');
      expect(response.data.name).toBe(keyData.name);
      
      apiKeyId = response.data.id;
    });

    test('should validate API key', async () => {
      // Get the API key first
      const getResponse = await global.testUtils.http.get(`${SSO_BASE_URL}/api/api-keys/${apiKeyId}`, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });

      const apiKey = getResponse.data.key;

      // Validate the API key
      const validateResponse = await global.testUtils.http.get(`${SSO_BASE_URL}/api/auth/api-key/validate`, {
        headers: {
          'X-API-Key': apiKey
        }
      });

      expect(validateResponse.status).toBe(200);
      expect(validateResponse.data.valid).toBe(true);
    });

    test('should revoke API key', async () => {
      const response = await global.testUtils.http.delete(`${SSO_BASE_URL}/api/api-keys/${apiKeyId}`, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });

      expect(response.status).toBe(204);
    });
  });

  describe('Social Login Integration', () => {
    test('should initiate OAuth flow', async () => {
      const response = await global.testUtils.http.get(`${SSO_BASE_URL}/api/auth/oauth/google`);

      expect(response.status).toBe(302);
      expect(response.headers.location).toContain('accounts.google.com');
    });

    test('should handle OAuth callback', async () => {
      // Mock OAuth callback data
      const mockCallbackData = {
        code: 'mock-auth-code',
        state: 'mock-state'
      };

      const response = await global.testUtils.http.get(
        `${SSO_BASE_URL}/api/auth/oauth/google/callback?code=${mockCallbackData.code}&state=${mockCallbackData.state}`
      );

      // In a real test, this would redirect or return user data
      expect([200, 302]).toContain(response.status);
    });
  });

  describe('Audit Logging', () => {
    test('should log authentication events', async () => {
      // Perform login to generate audit log
      await global.testUtils.http.post(`${SSO_BASE_URL}/api/auth/login`, {
        email: testUser.email,
        password: testUser.password
      });

      // Check audit logs
      const response = await global.testUtils.http.get(`${SSO_BASE_URL}/api/audit/logs`, {
        headers: {
          Authorization: `Bearer ${authToken}`
        },
        params: {
          userId: testUser.id,
          event: 'user_login'
        }
      });

      expect(response.status).toBe(200);
      expect(Array.isArray(response.data)).toBe(true);
      expect(response.data.length).toBeGreaterThan(0);
      
      const loginLog = response.data.find(log => log.event === 'user_login');
      expect(loginLog).toBeDefined();
      expect(loginLog.userId).toBe(testUser.id);
    });

    test('should export audit logs', async () => {
      const response = await global.testUtils.http.get(`${SSO_BASE_URL}/api/audit/logs/export`, {
        headers: {
          Authorization: `Bearer ${authToken}`
        },
        params: {
          format: 'json',
          startDate: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
          endDate: new Date().toISOString()
        }
      });

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('logs');
      expect(Array.isArray(response.data.logs)).toBe(true);
    });
  });

  describe('Device Fingerprinting', () => {
    test('should create device fingerprint', async () => {
      const fingerprintData = {
        userAgent: 'Mozilla/5.0 (Test Browser)',
        screenResolution: '1920x1080',
        timezone: 'America/New_York',
        language: 'en-US',
        plugins: ['PDF Viewer', 'Chrome PDF Plugin']
      };

      const response = await global.testUtils.http.post(`${SSO_BASE_URL}/api/device/fingerprint`, fingerprintData, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('deviceId');
      expect(response.data).toHaveProperty('riskScore');
      expect(response.data.riskScore).toBeGreaterThanOrEqual(0);
      expect(response.data.riskScore).toBeLessThanOrEqual(1);
    });

    test('should detect suspicious device', async () => {
      const suspiciousFingerprintData = {
        userAgent: 'SuspiciousBot/1.0',
        screenResolution: '1x1',
        timezone: 'Unknown',
        language: 'unknown',
        plugins: []
      };

      const response = await global.testUtils.http.post(`${SSO_BASE_URL}/api/device/fingerprint`, suspiciousFingerprintData, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });

      expect(response.status).toBe(200);
      expect(response.data.riskScore).toBeGreaterThan(0.5);
      expect(response.data.flags).toContain('suspicious_user_agent');
    });
  });

  describe('Error Handling', () => {
    test('should handle missing authentication', async () => {
      const response = await global.testUtils.http.get(`${SSO_BASE_URL}/api/auth/validate`);

      expect(response.status).toBe(401);
      expect(response.data.error).toContain('authentication');
    });

    test('should handle invalid JSON', async () => {
      const response = await global.testUtils.http.post(`${SSO_BASE_URL}/api/auth/login`, 'invalid-json', {
        headers: {
          'Content-Type': 'application/json'
        }
      });

      expect(response.status).toBe(400);
      expect(response.data.error).toContain('Invalid JSON');
    });

    test('should handle rate limiting', async () => {
      // Send many requests quickly to trigger rate limiting
      const requests = Array(200).fill().map(() =>
        global.testUtils.http.post(`${SSO_BASE_URL}/api/auth/login`, {
          email: 'nonexistent@example.com',
          password: 'wrongpassword'
        })
      );

      const responses = await Promise.all(requests);
      const rateLimitedResponses = responses.filter(res => res.status === 429);

      expect(rateLimitedResponses.length).toBeGreaterThan(0);
    });
  });

  describe('Health and Monitoring', () => {
    test('should return health status', async () => {
      const response = await global.testUtils.http.get(`${SSO_BASE_URL}/health`);

      expect(response.status).toBe(200);
      expect(response.data.status).toBe('healthy');
      expect(response.data).toHaveProperty('timestamp');
      expect(response.data).toHaveProperty('version');
    });

    test('should return service metrics', async () => {
      const response = await global.testUtils.http.get(`${SSO_BASE_URL}/api/metrics`, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('authentication');
      expect(response.data).toHaveProperty('sessions');
      expect(response.data).toHaveProperty('apiKeys');
    });
  });
});