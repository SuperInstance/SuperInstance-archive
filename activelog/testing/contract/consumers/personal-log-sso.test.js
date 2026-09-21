const { Matchers } = require('@pact-foundation/pact');
const { createPersonalLogSSOPact } = require('../pact.config');
const axios = require('axios');

const { like, eachLike, term, iso8601DateTime } = Matchers;

describe('PersonalLog -> SSO System Contract Tests', () => {
  const provider = createPersonalLogSSOPact();

  beforeAll(() => provider.setup());
  afterEach(() => provider.verify());
  afterAll(() => provider.finalize());

  describe('Authentication', () => {
    test('should authenticate user with valid credentials', async () => {
      // Define the expected interaction
      await provider.addInteraction({
        state: 'user exists with valid credentials',
        uponReceiving: 'a login request with valid credentials',
        withRequest: {
          method: 'POST',
          path: '/api/auth/login',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: {
            email: 'user@example.com',
            password: 'validPassword123!'
          }
        },
        willRespondWith: {
          status: 200,
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            token: term({
              matcher: '^[A-Za-z0-9-_=]+\\.[A-Za-z0-9-_=]+\\.[A-Za-z0-9-_.+/=]*$',
              generate: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIxMjMiLCJlbWFpbCI6InVzZXJAZXhhbXBsZS5jb20iLCJpYXQiOjE2MzQ1Njc4OTAsImV4cCI6MTYzNDU3MTQ5MH0.signature'
            }),
            user: {
              id: like('123'),
              email: like('user@example.com'),
              firstName: like('John'),
              lastName: like('Doe'),
              roles: eachLike('user'),
              createdAt: iso8601DateTime('2024-01-01T00:00:00Z'),
              lastLoginAt: iso8601DateTime('2024-01-01T12:00:00Z')
            },
            expiresAt: iso8601DateTime('2024-01-01T13:00:00Z'),
            refreshToken: like('refresh_token_here')
          }
        }
      });

      // Make the actual request
      const response = await axios.post(`${provider.mockService.baseUrl}/api/auth/login`, {
        email: 'user@example.com',
        password: 'validPassword123!'
      }, {
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      });

      expect(response.status).toBe(200);
      expect(response.data.token).toMatch(/^[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.[A-Za-z0-9-_.+/=]*$/);
      expect(response.data.user.email).toBe('user@example.com');
    });

    test('should reject authentication with invalid credentials', async () => {
      await provider.addInteraction({
        state: 'user exists but credentials are invalid',
        uponReceiving: 'a login request with invalid credentials',
        withRequest: {
          method: 'POST',
          path: '/api/auth/login',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: {
            email: 'user@example.com',
            password: 'invalidPassword'
          }
        },
        willRespondWith: {
          status: 401,
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            error: like('Invalid credentials'),
            code: like('AUTH_FAILED'),
            timestamp: iso8601DateTime('2024-01-01T12:00:00Z')
          }
        }
      });

      try {
        await axios.post(`${provider.mockService.baseUrl}/api/auth/login`, {
          email: 'user@example.com',
          password: 'invalidPassword'
        });
        throw new Error('Expected request to fail');
      } catch (error) {
        expect(error.response.status).toBe(401);
        expect(error.response.data.error).toBe('Invalid credentials');
      }
    });

    test('should validate JWT token', async () => {
      await provider.addInteraction({
        state: 'valid JWT token exists',
        uponReceiving: 'a token validation request',
        withRequest: {
          method: 'GET',
          path: '/api/auth/validate',
          headers: {
            'Authorization': term({
              matcher: '^Bearer [A-Za-z0-9-_=]+\\.[A-Za-z0-9-_=]+\\.[A-Za-z0-9-_.+/=]*$',
              generate: 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIxMjMiLCJlbWFpbCI6InVzZXJAZXhhbXBsZS5jb20iLCJpYXQiOjE2MzQ1Njc4OTAsImV4cCI6MTYzNDU3MTQ5MH0.signature'
            }),
            'Accept': 'application/json'
          }
        },
        willRespondWith: {
          status: 200,
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            valid: like(true),
            user: {
              id: like('123'),
              email: like('user@example.com'),
              firstName: like('John'),
              lastName: like('Doe'),
              roles: eachLike('user')
            },
            permissions: eachLike('read:personal-log'),
            expiresAt: iso8601DateTime('2024-01-01T13:00:00Z')
          }
        }
      });

      const response = await axios.get(`${provider.mockService.baseUrl}/api/auth/validate`, {
        headers: {
          'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIxMjMiLCJlbWFpbCI6InVzZXJAZXhhbXBsZS5jb20iLCJpYXQiOjE2MzQ1Njc4OTAsImV4cCI6MTYzNDU3MTQ5MH0.signature',
          'Accept': 'application/json'
        }
      });

      expect(response.status).toBe(200);
      expect(response.data.valid).toBe(true);
      expect(response.data.user.email).toBe('user@example.com');
    });
  });

  describe('User Registration', () => {
    test('should register new user successfully', async () => {
      await provider.addInteraction({
        state: 'no existing user with email',
        uponReceiving: 'a user registration request',
        withRequest: {
          method: 'POST',
          path: '/api/auth/register',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: {
            email: 'newuser@example.com',
            password: 'SecurePassword123!',
            firstName: 'New',
            lastName: 'User'
          }
        },
        willRespondWith: {
          status: 201,
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            user: {
              id: like('456'),
              email: like('newuser@example.com'),
              firstName: like('New'),
              lastName: like('User'),
              roles: eachLike('user'),
              createdAt: iso8601DateTime('2024-01-01T12:00:00Z'),
              emailVerified: like(false)
            },
            token: term({
              matcher: '^[A-Za-z0-9-_=]+\\.[A-Za-z0-9-_=]+\\.[A-Za-z0-9-_.+/=]*$',
              generate: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI0NTYiLCJlbWFpbCI6Im5ld3VzZXJAZXhhbXBsZS5jb20iLCJpYXQiOjE2MzQ1Njc4OTAsImV4cCI6MTYzNDU3MTQ5MH0.signature'
            }),
            message: like('Registration successful')
          }
        }
      });

      const response = await axios.post(`${provider.mockService.baseUrl}/api/auth/register`, {
        email: 'newuser@example.com',
        password: 'SecurePassword123!',
        firstName: 'New',
        lastName: 'User'
      });

      expect(response.status).toBe(201);
      expect(response.data.user.email).toBe('newuser@example.com');
      expect(response.data.token).toMatch(/^[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.[A-Za-z0-9-_.+/=]*$/);
    });

    test('should reject registration with existing email', async () => {
      await provider.addInteraction({
        state: 'user with email already exists',
        uponReceiving: 'a registration request with existing email',
        withRequest: {
          method: 'POST',
          path: '/api/auth/register',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: {
            email: 'existing@example.com',
            password: 'Password123!',
            firstName: 'Existing',
            lastName: 'User'
          }
        },
        willRespondWith: {
          status: 409,
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            error: like('User with this email already exists'),
            code: like('USER_EXISTS'),
            timestamp: iso8601DateTime('2024-01-01T12:00:00Z')
          }
        }
      });

      try {
        await axios.post(`${provider.mockService.baseUrl}/api/auth/register`, {
          email: 'existing@example.com',
          password: 'Password123!',
          firstName: 'Existing',
          lastName: 'User'
        });
        throw new Error('Expected request to fail');
      } catch (error) {
        expect(error.response.status).toBe(409);
        expect(error.response.data.error).toBe('User with this email already exists');
      }
    });
  });

  describe('User Profile Management', () => {
    test('should retrieve user profile', async () => {
      await provider.addInteraction({
        state: 'authenticated user exists',
        uponReceiving: 'a request for user profile',
        withRequest: {
          method: 'GET',
          path: '/api/users/profile',
          headers: {
            'Authorization': term({
              matcher: '^Bearer [A-Za-z0-9-_=]+\\.[A-Za-z0-9-_=]+\\.[A-Za-z0-9-_.+/=]*$',
              generate: 'Bearer valid_jwt_token'
            }),
            'Accept': 'application/json'
          }
        },
        willRespondWith: {
          status: 200,
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            id: like('123'),
            email: like('user@example.com'),
            firstName: like('John'),
            lastName: like('Doe'),
            avatar: like('https://example.com/avatar.jpg'),
            preferences: {
              theme: like('light'),
              notifications: {
                email: like(true),
                push: like(false)
              },
              timezone: like('America/New_York')
            },
            roles: eachLike('user'),
            permissions: eachLike('read:personal-log'),
            createdAt: iso8601DateTime('2024-01-01T00:00:00Z'),
            updatedAt: iso8601DateTime('2024-01-01T12:00:00Z'),
            lastLoginAt: iso8601DateTime('2024-01-01T11:30:00Z')
          }
        }
      });

      const response = await axios.get(`${provider.mockService.baseUrl}/api/users/profile`, {
        headers: {
          'Authorization': 'Bearer valid_jwt_token',
          'Accept': 'application/json'
        }
      });

      expect(response.status).toBe(200);
      expect(response.data.email).toBe('user@example.com');
      expect(response.data.preferences).toBeDefined();
      expect(response.data.roles).toContain('user');
    });

    test('should update user profile', async () => {
      await provider.addInteraction({
        state: 'authenticated user exists',
        uponReceiving: 'a profile update request',
        withRequest: {
          method: 'PUT',
          path: '/api/users/profile',
          headers: {
            'Authorization': term({
              matcher: '^Bearer [A-Za-z0-9-_=]+\\.[A-Za-z0-9-_=]+\\.[A-Za-z0-9-_.+/=]*$',
              generate: 'Bearer valid_jwt_token'
            }),
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: {
            firstName: 'Updated',
            lastName: 'Name',
            preferences: {
              theme: 'dark',
              notifications: {
                email: false
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
            id: like('123'),
            email: like('user@example.com'),
            firstName: like('Updated'),
            lastName: like('Name'),
            preferences: {
              theme: like('dark'),
              notifications: {
                email: like(false),
                push: like(false)
              },
              timezone: like('America/New_York')
            },
            updatedAt: iso8601DateTime('2024-01-01T12:30:00Z')
          }
        }
      });

      const response = await axios.put(`${provider.mockService.baseUrl}/api/users/profile`, {
        firstName: 'Updated',
        lastName: 'Name',
        preferences: {
          theme: 'dark',
          notifications: {
            email: false
          }
        }
      }, {
        headers: {
          'Authorization': 'Bearer valid_jwt_token',
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      });

      expect(response.status).toBe(200);
      expect(response.data.firstName).toBe('Updated');
      expect(response.data.preferences.theme).toBe('dark');
    });
  });

  describe('Multi-Factor Authentication', () => {
    test('should enable MFA for user', async () => {
      await provider.addInteraction({
        state: 'authenticated user without MFA enabled',
        uponReceiving: 'a request to enable MFA',
        withRequest: {
          method: 'POST',
          path: '/api/auth/mfa/enable',
          headers: {
            'Authorization': term({
              matcher: '^Bearer [A-Za-z0-9-_=]+\\.[A-Za-z0-9-_=]+\\.[A-Za-z0-9-_.+/=]*$',
              generate: 'Bearer valid_jwt_token'
            }),
            'Accept': 'application/json'
          }
        },
        willRespondWith: {
          status: 200,
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            secret: term({
              matcher: '^[A-Z2-7]{32}$',
              generate: 'JBSWY3DPEHPK3PXP4MQUC5KRAUGC25TK'
            }),
            qrCode: like('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...'),
            backupCodes: eachLike('12345678'),
            message: like('MFA enabled successfully')
          }
        }
      });

      const response = await axios.post(`${provider.mockService.baseUrl}/api/auth/mfa/enable`, {}, {
        headers: {
          'Authorization': 'Bearer valid_jwt_token',
          'Accept': 'application/json'
        }
      });

      expect(response.status).toBe(200);
      expect(response.data.secret).toMatch(/^[A-Z2-7]{32}$/);
      expect(response.data.qrCode).toContain('data:image/png;base64,');
      expect(Array.isArray(response.data.backupCodes)).toBe(true);
    });

    test('should verify MFA token', async () => {
      await provider.addInteraction({
        state: 'user has MFA enabled',
        uponReceiving: 'a MFA token verification request',
        withRequest: {
          method: 'POST',
          path: '/api/auth/mfa/verify',
          headers: {
            'Authorization': term({
              matcher: '^Bearer [A-Za-z0-9-_=]+\\.[A-Za-z0-9-_=]+\\.[A-Za-z0-9-_.+/=]*$',
              generate: 'Bearer valid_jwt_token'
            }),
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: {
            token: term({
              matcher: '^[0-9]{6}$',
              generate: '123456'
            })
          }
        },
        willRespondWith: {
          status: 200,
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            verified: like(true),
            message: like('MFA token verified successfully')
          }
        }
      });

      const response = await axios.post(`${provider.mockService.baseUrl}/api/auth/mfa/verify`, {
        token: '123456'
      }, {
        headers: {
          'Authorization': 'Bearer valid_jwt_token',
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      });

      expect(response.status).toBe(200);
      expect(response.data.verified).toBe(true);
    });
  });

  describe('Permission Management', () => {
    test('should check user permissions', async () => {
      await provider.addInteraction({
        state: 'authenticated user with specific permissions',
        uponReceiving: 'a permission check request',
        withRequest: {
          method: 'GET',
          path: term({
            matcher: '^/api/users/[0-9a-zA-Z-]+/permissions$',
            generate: '/api/users/123/permissions'
          }),
          headers: {
            'Authorization': term({
              matcher: '^Bearer [A-Za-z0-9-_=]+\\.[A-Za-z0-9-_=]+\\.[A-Za-z0-9-_.+/=]*$',
              generate: 'Bearer valid_jwt_token'
            }),
            'Accept': 'application/json'
          }
        },
        willRespondWith: {
          status: 200,
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            userId: like('123'),
            permissions: eachLike('read:personal-log'),
            roles: eachLike('user'),
            effectivePermissions: {
              'personal-log': eachLike('read'),
              'business-log': eachLike('read')
            }
          }
        }
      });

      const response = await axios.get(`${provider.mockService.baseUrl}/api/users/123/permissions`, {
        headers: {
          'Authorization': 'Bearer valid_jwt_token',
          'Accept': 'application/json'
        }
      });

      expect(response.status).toBe(200);
      expect(response.data.userId).toBe('123');
      expect(Array.isArray(response.data.permissions)).toBe(true);
      expect(response.data.effectivePermissions).toBeDefined();
    });
  });
});