import { Request, Response, NextFunction } from 'express';
import { Logger } from '@/utils/logger';

const logger = new Logger('ProtocolMiddleware');

export const protocolMiddleware = () => {
  return (req: Request, res: Response, next: NextFunction) => {
    // Check if client wants Protocol Buffer response
    const acceptHeader = req.headers.accept || '';
    const wantsProtobuf = acceptHeader.includes('application/x-protobuf') || 
                         acceptHeader.includes('application/protobuf') ||
                         req.headers['x-accept-protobuf'] === 'true';
    
    // Check if client sent Protocol Buffer data
    const contentType = req.headers['content-type'] || '';
    const isProtobufRequest = contentType.includes('application/x-protobuf') || 
                             contentType.includes('application/protobuf');

    if (isProtobufRequest) {
      // Handle incoming Protocol Buffer data
      let bufferData = Buffer.alloc(0);
      
      req.on('data', (chunk: Buffer) => {
        bufferData = Buffer.concat([bufferData, chunk]);
      });
      
      req.on('end', () => {
        try {
          // Parse Protocol Buffer message
          // This would use the compiled protobuf definitions
          // For now, we'll just store the raw buffer
          (req as any).protobuf = {
            buffer: bufferData,
            parsed: null // Would contain parsed protobuf message
          };
          
          logger.info(`Received Protocol Buffer message: ${bufferData.length} bytes`);
          
        } catch (error) {
          logger.error('Failed to parse Protocol Buffer message', error);
          return res.status(400).json({ error: 'Invalid Protocol Buffer message' });
        }
      });
    }

    if (wantsProtobuf) {
      // Override res.json to return Protocol Buffer response
      const originalJson = res.json;
      
      res.json = function(obj: any) {
        try {
          // Convert JSON to Protocol Buffer
          // This would use the compiled protobuf definitions
          // For now, we'll just return JSON with protobuf content type
          
          const jsonData = JSON.stringify(obj);
          
          res.set({
            'Content-Type': 'application/x-protobuf',
            'Content-Length': jsonData.length.toString(),
            'X-Protocol': 'protobuf-json-fallback'
          });
          
          return res.send(jsonData);
          
        } catch (error) {
          logger.error('Failed to serialize to Protocol Buffer', error);
          // Fallback to JSON
          return originalJson.call(this, obj);
        }
      };
    }

    // Add Protocol Buffer utility methods to response
    (res as any).protobuf = {
      send: (message: any, messageType: string) => {
        try {
          // This would serialize the message using protobuf
          // For now, just send JSON with protobuf headers
          const data = JSON.stringify(message);
          
          res.set({
            'Content-Type': 'application/x-protobuf',
            'X-Message-Type': messageType,
            'Content-Length': data.length.toString()
          });
          
          return res.send(data);
          
        } catch (error) {
          logger.error('Failed to send Protocol Buffer message', error);
          return res.status(500).json({ error: 'Serialization failed' });
        }
      }
    };
    
    next();
  };
};