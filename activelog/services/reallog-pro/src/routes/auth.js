import express from 'express';
import logger from '../lib/logger.js';

export default function createAuthRoutes() {
  const router = express.Router();

  // Login endpoint
  router.post('/login', async (req, res) => {
    try {
      const { email, password } = req.body;
      
      // Mock authentication logic
      const user = {
        id: 'user_123',
        email,
        name: 'Demo User',
        role: 'user'
      };

      logger.info('User login attempt', { email });
      
      res.json({
        success: true,
        user,
        token: 'mock_jwt_token_' + Date.now()
      });
    } catch (error) {
      logger.error('Login error:', error);
      res.status(500).json({
        error: 'Login failed',
        message: error.message
      });
    }
  });

  // Register endpoint
  router.post('/register', async (req, res) => {
    try {
      const { email, password, name } = req.body;
      
      // Mock registration logic
      const user = {
        id: 'user_' + Date.now(),
        email,
        name,
        role: 'user',
        createdAt: new Date()
      };

      logger.info('User registration', { email, name });
      
      res.status(201).json({
        success: true,
        user,
        token: 'mock_jwt_token_' + Date.now()
      });
    } catch (error) {
      logger.error('Registration error:', error);
      res.status(500).json({
        error: 'Registration failed',
        message: error.message
      });
    }
  });

  // Logout endpoint
  router.post('/logout', async (req, res) => {
    try {
      logger.info('User logout');
      
      res.json({
        success: true,
        message: 'Logged out successfully'
      });
    } catch (error) {
      logger.error('Logout error:', error);
      res.status(500).json({
        error: 'Logout failed',
        message: error.message
      });
    }
  });

  // Get current user
  router.get('/me', async (req, res) => {
    try {
      // Mock current user data
      const user = {
        id: 'user_123',
        email: 'demo@example.com',
        name: 'Demo User',
        role: 'user'
      };

      res.json({
        success: true,
        user
      });
    } catch (error) {
      logger.error('Get current user error:', error);
      res.status(500).json({
        error: 'Failed to get user data',
        message: error.message
      });
    }
  });

  return router;
}