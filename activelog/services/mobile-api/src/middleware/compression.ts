import { Request, Response, NextFunction } from 'express';
import * as zlib from 'zlib';
import { Logger } from '@/utils/logger';

const logger = new Logger('CompressionMiddleware');

export const compressionMiddleware = () => {
  return (req: Request, res: Response, next: NextFunction) => {
    // Check if client supports compression
    const acceptEncoding = req.headers['accept-encoding'] || '';
    const supportsGzip = acceptEncoding.includes('gzip');
    const supportsBrotli = acceptEncoding.includes('br');
    
    // Skip compression for small responses or specific content types
    const skipCompression = 
      req.path.includes('/images/') ||
      req.headers['content-type']?.startsWith('image/') ||
      req.headers['content-type']?.startsWith('video/') ||
      req.headers['content-type']?.startsWith('audio/');
    
    if (skipCompression) {
      return next();
    }

    // Override res.json to add compression
    const originalJson = res.json;
    const originalSend = res.send;
    
    res.json = function(obj: any) {
      const data = JSON.stringify(obj);
      
      // Only compress if response is large enough
      if (data.length > 1024 && (supportsGzip || supportsBrotli)) {
        try {
          if (supportsBrotli) {
            const compressed = zlib.brotliCompressSync(data, {
              params: {
                [zlib.constants.BROTLI_PARAM_QUALITY]: 6,
                [zlib.constants.BROTLI_PARAM_SIZE_HINT]: data.length
              }
            });
            
            res.set({
              'Content-Encoding': 'br',
              'Content-Length': compressed.length.toString(),
              'X-Original-Size': data.length.toString(),
              'X-Compression-Ratio': Math.round((1 - compressed.length / data.length) * 100).toString()
            });
            
            return res.send(compressed);
            
          } else if (supportsGzip) {
            const compressed = zlib.gzipSync(data, { level: 6 });
            
            res.set({
              'Content-Encoding': 'gzip',
              'Content-Length': compressed.length.toString(),
              'X-Original-Size': data.length.toString(),
              'X-Compression-Ratio': Math.round((1 - compressed.length / data.length) * 100).toString()
            });
            
            return res.send(compressed);
          }
        } catch (error) {
          logger.warn('Compression failed, sending uncompressed response', error);
        }
      }
      
      // Send uncompressed response
      return originalJson.call(this, obj);
    };

    res.send = function(data: any) {
      // Handle binary data compression for Protocol Buffers
      if (Buffer.isBuffer(data) && data.length > 1024 && (supportsGzip || supportsBrotli)) {
        try {
          if (supportsBrotli) {
            const compressed = zlib.brotliCompressSync(data);
            res.set({
              'Content-Encoding': 'br',
              'Content-Length': compressed.length.toString()
            });
            return originalSend.call(this, compressed);
          } else if (supportsGzip) {
            const compressed = zlib.gzipSync(data);
            res.set({
              'Content-Encoding': 'gzip',
              'Content-Length': compressed.length.toString()
            });
            return originalSend.call(this, compressed);
          }
        } catch (error) {
          logger.warn('Binary compression failed', error);
        }
      }
      
      return originalSend.call(this, data);
    };
    
    next();
  };
};