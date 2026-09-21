const EventEmitter = require('events');
const logger = require('../core/logger');

class OverlaySystem extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.options = {
      defaultOpacity: options.defaultOpacity || 0.8,
      fadeTime: options.fadeTime || 300,
      maxOverlays: options.maxOverlays || 50,
      ...options
    };

    this.overlays = new Map();
    this.overlayCount = 0;
    this.active = false;
  }

  async initialize() {
    logger.info('Initializing Overlay System...');
    this.active = true;
    logger.info('Overlay System initialized successfully');
  }

  async createOverlay(type, data, position = {}) {
    const overlayId = `overlay_${Date.now()}_${++this.overlayCount}`;
    
    const overlay = {
      id: overlayId,
      type,
      data,
      position: {
        x: position.x || 0,
        y: position.y || 0,
        width: position.width || 200,
        height: position.height || 100
      },
      opacity: this.options.defaultOpacity,
      visible: true,
      created: Date.now()
    };

    this.overlays.set(overlayId, overlay);
    
    this.emit('overlay-created', overlay);
    logger.debug(`Created overlay: ${overlayId} of type: ${type}`);
    
    return overlayId;
  }

  async removeOverlay(overlayId) {
    if (this.overlays.has(overlayId)) {
      const overlay = this.overlays.get(overlayId);
      this.overlays.delete(overlayId);
      this.emit('overlay-removed', overlay);
      logger.debug(`Removed overlay: ${overlayId}`);
    }
  }

  isActive() {
    return this.active;
  }
  
  getStatus() {
    return {
      active: this.active,
      overlayCount: this.overlays.size
    };
  }

  async cleanup() {
    this.overlays.clear();
    this.removeAllListeners();
    logger.info('Overlay System cleaned up');
  }
}

module.exports = OverlaySystem;