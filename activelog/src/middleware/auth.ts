import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { User } from '@/types/context';

const JWT_SECRET = process.env.JWT_SECRET || 'development-secret-key';
const JWT_ALGORITHM = 'HS256';

export interface AuthRequest extends Request {
  user?: User;
}

export const authMiddleware = async (
  req: AuthRequest,
  res: Response,
  next: NextFunction
) => {
  try {
    const token = extractToken(req);
    
    if (!token) {
      // Allow unauthenticated requests - will be handled by @auth directive
      return next();
    }
    
    const decoded = jwt.verify(token, JWT_SECRET, { algorithms: [JWT_ALGORITHM] }) as any;
    
    // Fetch user details from database or cache
    const user: User = {
      id: decoded.userId,
      email: decoded.email,
      role: decoded.role || 'USER',
      organizationId: decoded.organizationId,
      permissions: decoded.permissions || [],
      friends: [], // Would be loaded from database
      teamMembers: [] // Would be loaded from database
    };
    
    req.user = user;
    next();
  } catch (error) {
    if (error instanceof jwt.JsonWebTokenError) {
      // Invalid token - allow request but don't set user
      return next();
    }
    
    console.error('Auth middleware error:', error);
    return res.status(500).json({ error: 'Internal authentication error' });
  }
};

function extractToken(req: Request): string | null {
  const authHeader = req.headers.authorization;
  
  if (authHeader && authHeader.startsWith('Bearer ')) {
    return authHeader.substring(7);
  }
  
  // Check query parameter (for subscriptions)
  if (req.query.token && typeof req.query.token === 'string') {
    return req.query.token;
  }
  
  // Check cookies
  if (req.cookies && req.cookies.token) {
    return req.cookies.token;
  }
  
  return null;
}

// Helper function to verify tokens for subscriptions
authMiddleware.verifyToken = async (token: string): Promise<User | null> => {
  try {
    const decoded = jwt.verify(token, JWT_SECRET, { algorithms: [JWT_ALGORITHM] }) as any;
    
    return {
      id: decoded.userId,
      email: decoded.email,
      role: decoded.role || 'USER',
      organizationId: decoded.organizationId,
      permissions: decoded.permissions || [],
      friends: [],
      teamMembers: []
    };
  } catch (error) {
    console.error('Token verification error:', error);
    return null;
  }
};

// Generate JWT token helper
export const generateToken = (user: Partial<User>, expiresIn = '24h'): string => {
  return jwt.sign(
    {
      userId: user.id,
      email: user.email,
      role: user.role,
      organizationId: user.organizationId,
      permissions: user.permissions
    },
    JWT_SECRET,
    {
      algorithm: JWT_ALGORITHM,
      expiresIn,
      issuer: 'activelog-graphql',
      audience: 'activelog-client'
    }
  );
};

// Refresh token helper
export const refreshToken = (token: string): string | null => {
  try {
    const decoded = jwt.verify(token, JWT_SECRET, { 
      algorithms: [JWT_ALGORITHM],
      ignoreExpiration: true 
    }) as any;
    
    // Check if token is not too old (e.g., not older than 7 days)
    const tokenAge = Date.now() / 1000 - decoded.iat;
    const maxAge = 7 * 24 * 60 * 60; // 7 days
    
    if (tokenAge > maxAge) {
      return null;
    }
    
    // Generate new token
    return generateToken({
      id: decoded.userId,
      email: decoded.email,
      role: decoded.role,
      organizationId: decoded.organizationId,
      permissions: decoded.permissions
    });
  } catch (error) {
    return null;
  }
};