import jwt from 'jsonwebtoken';
import mongoose from 'mongoose';

const authMiddleware = async (req, res, next) => {
  try {
    const token = req.header('Authorization')?.replace('Bearer ', '');
    
    if (!token) {
      return res.status(401).json({ error: 'No token provided' });
    }

    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    
    // In a real implementation, you'd fetch user from database
    // For now, we'll simulate a user object
    req.user = {
      id: decoded.userId || '64f8a1b2c3d4e5f6a7b8c9d0',
      username: decoded.username || 'testuser',
      email: decoded.email || 'test@example.com',
      role: decoded.role || 'user',
      subscription: decoded.subscription || {
        planId: 'free',
        isPremium: false
      }
    };

    next();
  } catch (error) {
    if (error.name === 'JsonWebTokenError') {
      return res.status(401).json({ error: 'Invalid token' });
    }
    if (error.name === 'TokenExpiredError') {
      return res.status(401).json({ error: 'Token expired' });
    }
    return res.status(500).json({ error: 'Authentication error' });
  }
};

export default authMiddleware;