import { Request, Response } from 'express';
import { Logger } from '@/utils/logger';
import { ImageOptimizationService } from '@/services/ImageOptimizationService';
import * as fs from 'fs';
import * as path from 'path';

const logger = new Logger('ImageController');

interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    role: string;
  };
  file?: Express.Multer.File;
}

export const imageController = {
  async optimizeImage(req: AuthenticatedRequest, res: Response) {
    let tempFilePath: string | null = null;
    
    try {
      const imageService = req.app.locals.services.imageService as ImageOptimizationService;
      
      const userId = req.user?.id;
      if (!userId) {
        return res.status(401).json({ error: 'Unauthorized' });
      }

      if (!req.file) {
        return res.status(400).json({ error: 'Image file required' });
      }

      // Save uploaded file temporarily
      tempFilePath = path.join('/tmp', `${Date.now()}-${req.file.originalname}`);
      await fs.promises.writeFile(tempFilePath, req.file.buffer);

      const { variants, generateProgressive = true } = req.body;
      let customVariants;
      
      if (variants) {
        try {
          customVariants = JSON.parse(variants);
        } catch (error) {
          return res.status(400).json({ error: 'Invalid variants JSON' });
        }
      }

      const result = await imageService.optimizeImage(tempFilePath, {
        variants: customVariants,
        userId,
        generateProgressive,
        enableCache: true
      });

      // Clean up temp file
      if (tempFilePath) {
        await fs.promises.unlink(tempFilePath).catch(() => {});
      }

      res.json({
        success: true,
        optimization: result
      });

    } catch (error) {
      // Clean up temp file on error
      if (tempFilePath) {
        await fs.promises.unlink(tempFilePath).catch(() => {});
      }

      logger.error('Image optimization failed', error);
      res.status(500).json({ error: 'Image optimization failed' });
    }
  },

  async generateResponsiveSet(req: AuthenticatedRequest, res: Response) {
    let tempFilePath: string | null = null;
    
    try {
      const imageService = req.app.locals.services.imageService as ImageOptimizationService;
      
      const userId = req.user?.id;
      if (!userId) {
        return res.status(401).json({ error: 'Unauthorized' });
      }

      if (!req.file) {
        return res.status(400).json({ error: 'Image file required' });
      }

      // Save uploaded file temporarily
      tempFilePath = path.join('/tmp', `${Date.now()}-${req.file.originalname}`);
      await fs.promises.writeFile(tempFilePath, req.file.buffer);

      const { breakpoints, format = 'jpeg', quality = 85 } = req.body;
      
      let customBreakpoints;
      if (breakpoints) {
        try {
          customBreakpoints = JSON.parse(breakpoints);
        } catch (error) {
          return res.status(400).json({ error: 'Invalid breakpoints JSON' });
        }
      }

      const result = await imageService.generateResponsiveImageSet(tempFilePath, customBreakpoints, {
        format,
        quality: parseInt(quality),
        userId
      });

      // Clean up temp file
      if (tempFilePath) {
        await fs.promises.unlink(tempFilePath).catch(() => {});
      }

      res.json({
        success: true,
        responsive: result
      });

    } catch (error) {
      // Clean up temp file on error
      if (tempFilePath) {
        await fs.promises.unlink(tempFilePath).catch(() => {});
      }

      logger.error('Responsive image generation failed', error);
      res.status(500).json({ error: 'Responsive image generation failed' });
    }
  },

  async optimizeForMobile(req: AuthenticatedRequest, res: Response) {
    let tempFilePath: string | null = null;
    
    try {
      const imageService = req.app.locals.services.imageService as ImageOptimizationService;
      
      const userId = req.user?.id;
      if (!userId) {
        return res.status(401).json({ error: 'Unauthorized' });
      }

      if (!req.file) {
        return res.status(400).json({ error: 'Image file required' });
      }

      // Save uploaded file temporarily
      tempFilePath = path.join('/tmp', `${Date.now()}-${req.file.originalname}`);
      await fs.promises.writeFile(tempFilePath, req.file.buffer);

      const { 
        deviceType = 'phone', 
        networkType = 'slow', 
        generateWebP = true 
      } = req.body;

      const result = await imageService.optimizeForMobile(
        tempFilePath, 
        deviceType as 'phone' | 'tablet' | 'desktop',
        networkType as 'slow' | 'fast',
        {
          userId,
          generateWebP: generateWebP === 'true' || generateWebP === true
        }
      );

      // Clean up temp file
      if (tempFilePath) {
        await fs.promises.unlink(tempFilePath).catch(() => {});
      }

      res.json({
        success: true,
        mobile: result
      });

    } catch (error) {
      // Clean up temp file on error
      if (tempFilePath) {
        await fs.promises.unlink(tempFilePath).catch(() => {});
      }

      logger.error('Mobile image optimization failed', error);
      res.status(500).json({ error: 'Mobile image optimization failed' });
    }
  },

  async generatePlaceholder(req: AuthenticatedRequest, res: Response) {
    let tempFilePath: string | null = null;
    
    try {
      const imageService = req.app.locals.services.imageService as ImageOptimizationService;
      
      const userId = req.user?.id;
      if (!userId) {
        return res.status(401).json({ error: 'Unauthorized' });
      }

      if (!req.file) {
        return res.status(400).json({ error: 'Image file required' });
      }

      // Save uploaded file temporarily
      tempFilePath = path.join('/tmp', `${Date.now()}-${req.file.originalname}`);
      await fs.promises.writeFile(tempFilePath, req.file.buffer);

      const placeholderUrl = await imageService.generateBlurredPlaceholder(tempFilePath);

      // Clean up temp file
      if (tempFilePath) {
        await fs.promises.unlink(tempFilePath).catch(() => {});
      }

      res.json({
        success: true,
        placeholderUrl
      });

    } catch (error) {
      // Clean up temp file on error
      if (tempFilePath) {
        await fs.promises.unlink(tempFilePath).catch(() => {});
      }

      logger.error('Placeholder generation failed', error);
      res.status(500).json({ error: 'Placeholder generation failed' });
    }
  },

  async getOptimizationStats(req: AuthenticatedRequest, res: Response) {
    try {
      const imageService = req.app.locals.services.imageService as ImageOptimizationService;
      
      // Check if user has permission to view stats
      if (req.user?.role !== 'admin' && req.user?.role !== 'super_admin') {
        return res.status(403).json({ error: 'Insufficient permissions' });
      }

      const stats = await imageService.getOptimizationStats();

      res.json(stats);

    } catch (error) {
      logger.error('Failed to get optimization stats', error);
      res.status(500).json({ error: 'Failed to get optimization stats' });
    }
  }
};