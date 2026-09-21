module.exports = {
  port: process.env.PORT || 8369,
  env: process.env.NODE_ENV || 'development',
  logging: {
    level: process.env.LOG_LEVEL || 'info'
  },
  frameCapture: {
    fps: 1,
    quality: 80,
    detectActions: true
  },
  aiDetection: {
    confidenceThreshold: 0.7
  },
  overlay: {
    defaultOpacity: 0.8,
    fadeTime: 300
  },
  radar: {
    enableDetection: true,
    targetTracking: true,
    collisionDetection: true
  }
};