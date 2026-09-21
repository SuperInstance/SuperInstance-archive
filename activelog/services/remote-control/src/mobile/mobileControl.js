const EventEmitter = require('events');
const logger = require('../core/logger');

class MobileControl extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.options = {
      // Touch and gesture settings
      touchSensitivity: options.touchSensitivity || 1.0,
      gestureThreshold: options.gestureThreshold || 10,
      multiTouchEnabled: options.multiTouchEnabled !== false,
      
      // Input simulation
      cursorSpeed: options.cursorSpeed || 1.0,
      scrollSensitivity: options.scrollSensitivity || 1.0,
      keyboardEnabled: options.keyboardEnabled !== false,
      
      // Security settings
      requirePermissions: options.requirePermissions !== false,
      allowedActions: options.allowedActions || ['mouse', 'keyboard', 'scroll', 'gesture'],
      restrictedKeys: options.restrictedKeys || ['ctrl+alt+del', 'cmd+space'],
      
      // Performance settings
      inputThrottling: options.inputThrottling || 50, // ms
      batchInputs: options.batchInputs !== false,
      
      ...options
    };

    // Connected mobile devices
    this.mobileDevices = new Map();
    this.inputQueue = [];
    this.lastInputTime = 0;
    
    // Input state tracking
    this.cursorPosition = { x: 0, y: 0 };
    this.activeGestures = new Map();
    this.keyboardState = new Map();
    
    // Metrics
    this.metrics = {
      totalInputs: 0,
      gesturesProcessed: 0,
      keystrokes: 0,
      mouseEvents: 0,
      connectedDevices: 0,
      averageLatency: 0
    };
  }

  async initialize() {
    logger.info('Initializing Mobile Control system...');
    
    // Start input processing loop
    this.startInputProcessing();
    
    // Setup performance monitoring
    this.setupPerformanceMonitoring();
    
    logger.info('Mobile Control system initialized successfully');
  }

  async connectMobileDevice(deviceId, deviceInfo, permissions) {
    try {
      // Validate permissions
      if (this.options.requirePermissions && !this.validatePermissions(permissions)) {
        throw new Error('Insufficient permissions for mobile control');
      }
      
      const device = {
        id: deviceId,
        info: deviceInfo,
        permissions: permissions,
        connected: Date.now(),
        lastActivity: Date.now(),
        inputCount: 0,
        capabilities: {
          touch: true,
          keyboard: deviceInfo.hasKeyboard || false,
          accelerometer: deviceInfo.hasAccelerometer || false,
          gyroscope: deviceInfo.hasGyroscope || false
        },
        settings: {
          touchSensitivity: this.options.touchSensitivity,
          cursorSpeed: this.options.cursorSpeed,
          scrollSensitivity: this.options.scrollSensitivity
        }
      };
      
      this.mobileDevices.set(deviceId, device);
      this.metrics.connectedDevices++;
      
      logger.info(`Mobile device connected: ${deviceId}`, {
        deviceType: deviceInfo.type,
        os: deviceInfo.os,
        permissions: Object.keys(permissions)
      });
      
      this.emit('device-connected', { deviceId, device });
      
      return device;
    } catch (error) {
      logger.error(`Failed to connect mobile device ${deviceId}:`, error);
      throw error;
    }
  }

  async disconnectMobileDevice(deviceId) {
    const device = this.mobileDevices.get(deviceId);
    if (!device) return false;
    
    // Cancel any active gestures
    for (const [gestureId, gesture] of this.activeGestures) {
      if (gesture.deviceId === deviceId) {
        this.activeGestures.delete(gestureId);
      }
    }
    
    this.mobileDevices.delete(deviceId);
    this.metrics.connectedDevices--;
    
    logger.info(`Mobile device disconnected: ${deviceId}`);
    this.emit('device-disconnected', { deviceId, device });
    
    return true;
  }

  validatePermissions(permissions) {
    const required = ['mouse_control', 'screen_view'];
    return required.every(perm => permissions[perm] === true);
  }

  async processInput(deviceId, inputData) {
    const startTime = Date.now();
    const device = this.mobileDevices.get(deviceId);
    
    if (!device) {
      logger.warn(`Input from unknown device: ${deviceId}`);
      return { success: false, error: 'Device not connected' };
    }
    
    // Check if input type is allowed
    if (!this.options.allowedActions.includes(inputData.type)) {
      logger.warn(`Blocked input type '${inputData.type}' from device ${deviceId}`);
      return { success: false, error: 'Input type not allowed' };
    }
    
    // Throttle inputs if needed
    if (this.options.inputThrottling > 0) {
      const timeSinceLastInput = Date.now() - this.lastInputTime;
      if (timeSinceLastInput < this.options.inputThrottling) {
        // Queue input for later processing
        this.inputQueue.push({ deviceId, inputData, timestamp: startTime });
        return { success: true, queued: true };
      }
    }
    
    try {
      const result = await this.executeInput(deviceId, inputData);
      
      // Update device activity
      device.lastActivity = Date.now();
      device.inputCount++;
      
      // Update metrics
      this.metrics.totalInputs++;
      this.updateInputMetrics(inputData.type);
      
      // Calculate latency
      const latency = Date.now() - startTime;
      this.metrics.averageLatency = (this.metrics.averageLatency + latency) / 2;
      
      this.lastInputTime = Date.now();
      
      this.emit('input-processed', {
        deviceId,
        inputType: inputData.type,
        latency,
        success: result.success
      });
      
      return result;
    } catch (error) {
      logger.error(`Input processing error for device ${deviceId}:`, error);
      return { success: false, error: error.message };
    }
  }

  async executeInput(deviceId, inputData) {
    const device = this.mobileDevices.get(deviceId);
    
    switch (inputData.type) {
      case 'touch':
        return await this.processTouchInput(deviceId, inputData, device);
      
      case 'mouse':
        return await this.processMouseInput(deviceId, inputData, device);
      
      case 'scroll':
        return await this.processScrollInput(deviceId, inputData, device);
      
      case 'gesture':
        return await this.processGestureInput(deviceId, inputData, device);
      
      case 'keyboard':
        return await this.processKeyboardInput(deviceId, inputData, device);
      
      default:
        return { success: false, error: `Unknown input type: ${inputData.type}` };
    }
  }

  async processTouchInput(deviceId, inputData, device) {
    try {
      const { x, y, action, pressure = 1.0 } = inputData;
      
      // Convert touch coordinates to screen coordinates
      const screenCoords = this.convertTouchCoordinates(x, y, inputData.screenSize);
      
      switch (action) {
        case 'down':
          // Simulate mouse down
          await this.simulateMouseEvent('mousedown', screenCoords, { button: 'left' });
          break;
          
        case 'up':
          // Simulate mouse up
          await this.simulateMouseEvent('mouseup', screenCoords, { button: 'left' });
          break;
          
        case 'move':
          // Simulate mouse move
          await this.simulateMouseEvent('mousemove', screenCoords);
          this.cursorPosition = screenCoords;
          break;
      }
      
      return { 
        success: true, 
        action, 
        coordinates: screenCoords,
        pressure 
      };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async processMouseInput(deviceId, inputData, device) {
    try {
      const { action, button = 'left', deltaX = 0, deltaY = 0 } = inputData;
      
      switch (action) {
        case 'move':
          const newX = Math.max(0, this.cursorPosition.x + (deltaX * device.settings.cursorSpeed));
          const newY = Math.max(0, this.cursorPosition.y + (deltaY * device.settings.cursorSpeed));
          
          await this.simulateMouseEvent('mousemove', { x: newX, y: newY });
          this.cursorPosition = { x: newX, y: newY };
          break;
          
        case 'click':
          await this.simulateMouseEvent('click', this.cursorPosition, { button });
          break;
          
        case 'doubleclick':
          await this.simulateMouseEvent('dblclick', this.cursorPosition, { button });
          break;
          
        case 'rightclick':
          await this.simulateMouseEvent('contextmenu', this.cursorPosition);
          break;
      }
      
      return { 
        success: true, 
        action, 
        position: this.cursorPosition,
        button 
      };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async processScrollInput(deviceId, inputData, device) {
    try {
      const { deltaX = 0, deltaY = 0, horizontal = false } = inputData;
      
      const scrollData = {
        x: this.cursorPosition.x,
        y: this.cursorPosition.y,
        deltaX: deltaX * device.settings.scrollSensitivity,
        deltaY: deltaY * device.settings.scrollSensitivity,
        deltaMode: 'pixel'
      };
      
      await this.simulateScrollEvent(scrollData);
      
      return { 
        success: true, 
        scrolled: { deltaX: scrollData.deltaX, deltaY: scrollData.deltaY } 
      };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async processGestureInput(deviceId, inputData, device) {
    try {
      const { gestureType, data, gestureId } = inputData;
      
      switch (gestureType) {
        case 'pinch':
          return await this.processPinchGesture(gestureId, data, device);
          
        case 'swipe':
          return await this.processSwipeGesture(gestureId, data, device);
          
        case 'rotate':
          return await this.processRotateGesture(gestureId, data, device);
          
        case 'tap':
          return await this.processTapGesture(gestureId, data, device);
          
        default:
          return { success: false, error: `Unknown gesture type: ${gestureType}` };
      }
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async processKeyboardInput(deviceId, inputData, device) {
    try {
      if (!this.options.keyboardEnabled || !device.permissions.keyboard_control) {
        return { success: false, error: 'Keyboard input not allowed' };
      }
      
      const { key, action, modifiers = [] } = inputData;
      
      // Check for restricted key combinations
      const keyCombo = modifiers.length > 0 ? `${modifiers.join('+')}+${key}` : key;
      if (this.options.restrictedKeys.includes(keyCombo)) {
        logger.warn(`Blocked restricted key combination: ${keyCombo}`);
        return { success: false, error: 'Key combination restricted' };
      }
      
      switch (action) {
        case 'keydown':
          await this.simulateKeyEvent('keydown', key, modifiers);
          break;
          
        case 'keyup':
          await this.simulateKeyEvent('keyup', key, modifiers);
          break;
          
        case 'keypress':
          await this.simulateKeyEvent('keypress', key, modifiers);
          break;
      }
      
      this.metrics.keystrokes++;
      
      return { 
        success: true, 
        key, 
        action, 
        modifiers 
      };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  convertTouchCoordinates(x, y, screenSize) {
    // Convert normalized touch coordinates (0-1) to screen coordinates
    // This would need to be adjusted based on actual screen resolution
    const screenWidth = 1920; // Would be obtained from display info
    const screenHeight = 1080;
    
    return {
      x: Math.round(x * screenWidth),
      y: Math.round(y * screenHeight)
    };
  }

  async simulateMouseEvent(type, coordinates, options = {}) {
    // In a real implementation, this would use native APIs or libraries
    // like robotjs to actually control the mouse
    logger.debug(`Simulating mouse event: ${type}`, { coordinates, options });
    
    this.emit('mouse-simulated', {
      type,
      coordinates,
      options,
      timestamp: Date.now()
    });
  }

  async simulateKeyEvent(type, key, modifiers) {
    // In a real implementation, this would use native APIs
    logger.debug(`Simulating key event: ${type}`, { key, modifiers });
    
    this.emit('key-simulated', {
      type,
      key,
      modifiers,
      timestamp: Date.now()
    });
  }

  async simulateScrollEvent(scrollData) {
    // In a real implementation, this would simulate actual scrolling
    logger.debug('Simulating scroll event', scrollData);
    
    this.emit('scroll-simulated', {
      ...scrollData,
      timestamp: Date.now()
    });
  }

  async processPinchGesture(gestureId, data, device) {
    const { scale, centerX, centerY } = data;
    
    // Convert pinch to zoom action
    if (scale > 1.1) {
      // Zoom in
      await this.simulateKeyEvent('keydown', '=', ['ctrl']);
      await this.simulateKeyEvent('keyup', '=', ['ctrl']);
    } else if (scale < 0.9) {
      // Zoom out
      await this.simulateKeyEvent('keydown', '-', ['ctrl']);
      await this.simulateKeyEvent('keyup', '-', ['ctrl']);
    }
    
    return { success: true, gestureType: 'pinch', scale };
  }

  async processSwipeGesture(gestureId, data, device) {
    const { direction, velocity, distance } = data;
    
    // Convert swipe to scroll or navigation
    switch (direction) {
      case 'up':
        await this.simulateScrollEvent({ x: 0, y: 0, deltaY: -distance });
        break;
      case 'down':
        await this.simulateScrollEvent({ x: 0, y: 0, deltaY: distance });
        break;
      case 'left':
        await this.simulateScrollEvent({ x: 0, y: 0, deltaX: -distance });
        break;
      case 'right':
        await this.simulateScrollEvent({ x: 0, y: 0, deltaX: distance });
        break;
    }
    
    return { success: true, gestureType: 'swipe', direction, distance };
  }

  startInputProcessing() {
    // Process queued inputs
    setInterval(() => {
      if (this.inputQueue.length > 0) {
        const input = this.inputQueue.shift();
        this.processInput(input.deviceId, input.inputData);
      }
    }, this.options.inputThrottling);
  }

  setupPerformanceMonitoring() {
    setInterval(() => {
      this.emit('performance-update', this.metrics);
    }, 5000);
  }

  updateInputMetrics(inputType) {
    switch (inputType) {
      case 'gesture':
        this.metrics.gesturesProcessed++;
        break;
      case 'keyboard':
        this.metrics.keystrokes++;
        break;
      case 'mouse':
      case 'touch':
        this.metrics.mouseEvents++;
        break;
    }
  }

  // Public API methods
  getConnectedDevices() {
    return Array.from(this.mobileDevices.values()).map(device => ({
      id: device.id,
      info: device.info,
      connected: device.connected,
      lastActivity: device.lastActivity,
      inputCount: device.inputCount,
      capabilities: device.capabilities
    }));
  }

  getDeviceSettings(deviceId) {
    const device = this.mobileDevices.get(deviceId);
    return device ? device.settings : null;
  }

  updateDeviceSettings(deviceId, settings) {
    const device = this.mobileDevices.get(deviceId);
    if (device) {
      Object.assign(device.settings, settings);
      logger.info(`Updated settings for device ${deviceId}`, settings);
      return true;
    }
    return false;
  }

  getCursorPosition() {
    return { ...this.cursorPosition };
  }

  getMetrics() {
    return {
      ...this.metrics,
      connectedDevices: this.mobileDevices.size,
      queuedInputs: this.inputQueue.length,
      activeGestures: this.activeGestures.size
    };
  }

  async cleanup() {
    this.mobileDevices.clear();
    this.activeGestures.clear();
    this.inputQueue = [];
    
    this.removeAllListeners();
    logger.info('Mobile Control system cleaned up');
  }
}

module.exports = MobileControl;