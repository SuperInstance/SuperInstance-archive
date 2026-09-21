const EventEmitter = require('events');
const logger = require('../core/logger');
const crypto = require('crypto');
const { v4: uuidv4 } = require('uuid');

class FindMyDevice extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.options = {
      // Discovery settings
      discoveryInterval: options.discoveryInterval || 30000, // 30 seconds
      deviceTimeout: options.deviceTimeout || 300000, // 5 minutes
      maxDevicesPerUser: options.maxDevicesPerUser || 20,
      
      // Location tracking
      enableLocationTracking: options.enableLocationTracking !== false,
      locationAccuracy: options.locationAccuracy || 'high', // high, medium, low
      locationTimeout: options.locationTimeout || 10000,
      
      // Network discovery
      enableNetworkScanning: options.enableNetworkScanning !== false,
      scanNetworkPorts: options.scanNetworkPorts || [22, 80, 443, 3389, 5900],
      localNetworkOnly: options.localNetworkOnly !== false,
      
      // Bluetooth discovery
      enableBluetoothScanning: options.enableBluetoothScanning !== false,
      bluetoothTimeout: options.bluetoothTimeout || 30000,
      
      // Security features
      requireAuthentication: options.requireAuthentication !== false,
      encryptDeviceData: options.encryptDeviceData !== false,
      allowRemoteActions: options.allowRemoteActions !== false,
      
      // Remote actions
      enableRemoteLock: options.enableRemoteLock !== false,
      enableRemoteWipe: options.enableRemoteWipe !== false,
      enableRemoteAlarm: options.enableRemoteAlarm !== false,
      enableRemoteMessage: options.enableRemoteMessage !== false,
      
      // Privacy settings
      shareLocationWithFamily: options.shareLocationWithFamily || false,
      anonymizeDeviceInfo: options.anonymizeDeviceInfo || false,
      
      ...options
    };

    // Device registry
    this.registeredDevices = new Map(); // deviceId -> device
    this.userDevices = new Map(); // userId -> deviceIds[]
    this.deviceLocations = new Map(); // deviceId -> location history
    this.nearbyDevices = new Map(); // discovered devices
    
    // Network and discovery state
    this.networkScanners = new Map();
    this.bluetoothScanners = new Map();
    this.activeScans = new Set();
    
    // Security
    this.deviceKeys = new Map(); // deviceId -> encryption key
    this.pendingActions = new Map(); // actionId -> action
    
    // Family/group sharing
    this.familyGroups = new Map(); // groupId -> members
    this.sharedDevices = new Map(); // deviceId -> shared with
    
    // Metrics
    this.metrics = {
      devicesRegistered: 0,
      devicesFound: 0,
      locationsTracked: 0,
      remoteActionsExecuted: 0,
      networkScansPerformed: 0,
      bluetoothScansPerformed: 0
    };
  }

  async initialize() {
    logger.info('Initializing Find My Device system...');
    
    try {
      // Start device discovery
      this.startDeviceDiscovery();
      
      // Start location tracking
      if (this.options.enableLocationTracking) {
        this.startLocationTracking();
      }
      
      // Start network scanning
      if (this.options.enableNetworkScanning) {
        this.startNetworkScanning();
      }
      
      // Start Bluetooth scanning
      if (this.options.enableBluetoothScanning) {
        this.startBluetoothScanning();
      }
      
      // Setup cleanup intervals
      this.startCleanupRoutines();
      
      logger.info('Find My Device system initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize Find My Device system:', error);
      throw error;
    }
  }

  async registerDevice(userId, deviceInfo) {
    try {
      const deviceId = deviceInfo.id || uuidv4();
      const now = Date.now();
      
      // Validate device limit
      const userDeviceIds = this.userDevices.get(userId) || [];
      if (userDeviceIds.length >= this.options.maxDevicesPerUser) {
        throw new Error(`Maximum devices (${this.options.maxDevicesPerUser}) reached for user`);
      }

      const device = {
        id: deviceId,
        userId,
        name: deviceInfo.name,
        type: deviceInfo.type, // desktop, laptop, mobile, tablet, smart_device
        platform: deviceInfo.platform, // windows, macos, linux, ios, android
        version: deviceInfo.version,
        
        // Hardware info
        manufacturer: deviceInfo.manufacturer,
        model: deviceInfo.model,
        serialNumber: this.options.anonymizeDeviceInfo 
          ? this.hashSensitiveData(deviceInfo.serialNumber) 
          : deviceInfo.serialNumber,
        
        // Network info
        macAddress: this.hashSensitiveData(deviceInfo.macAddress),
        ipAddress: deviceInfo.ipAddress,
        hostname: deviceInfo.hostname,
        
        // Status
        status: 'online',
        lastSeen: now,
        registeredAt: now,
        
        // Location
        location: null,
        locationHistory: [],
        locationEnabled: deviceInfo.locationEnabled !== false,
        
        // Capabilities
        capabilities: {
          canLock: deviceInfo.capabilities?.canLock !== false,
          canWipe: deviceInfo.capabilities?.canWipe !== false,
          canAlarm: deviceInfo.capabilities?.canAlarm !== false,
          canMessage: deviceInfo.capabilities?.canMessage !== false,
          hasCamera: deviceInfo.capabilities?.hasCamera || false,
          hasMicrophone: deviceInfo.capabilities?.hasMicrophone || false
        },
        
        // Security
        encrypted: this.options.encryptDeviceData,
        lastAuthCheck: now,
        
        // Metadata
        tags: deviceInfo.tags || [],
        notes: deviceInfo.notes || ''
      };

      // Generate encryption key if needed
      if (this.options.encryptDeviceData) {
        this.deviceKeys.set(deviceId, crypto.randomBytes(32));
      }

      // Register device
      this.registeredDevices.set(deviceId, device);
      
      // Update user device list
      userDeviceIds.push(deviceId);
      this.userDevices.set(userId, userDeviceIds);
      
      // Initialize location tracking
      if (device.locationEnabled) {
        this.deviceLocations.set(deviceId, []);
      }

      this.metrics.devicesRegistered++;

      logger.info(`Device registered: ${device.name}`, {
        deviceId,
        userId,
        type: device.type,
        platform: device.platform
      });

      this.emit('device-registered', { device, userId });

      return device;
    } catch (error) {
      logger.error('Device registration error:', error);
      throw error;
    }
  }

  async unregisterDevice(userId, deviceId) {
    const device = this.registeredDevices.get(deviceId);
    if (!device || device.userId !== userId) {
      throw new Error('Device not found or unauthorized');
    }

    // Remove from all maps
    this.registeredDevices.delete(deviceId);
    this.deviceLocations.delete(deviceId);
    this.deviceKeys.delete(deviceId);
    this.nearbyDevices.delete(deviceId);

    // Update user device list
    const userDeviceIds = this.userDevices.get(userId) || [];
    const filteredIds = userDeviceIds.filter(id => id !== deviceId);
    this.userDevices.set(userId, filteredIds);

    // Remove from family sharing
    this.sharedDevices.delete(deviceId);

    logger.info(`Device unregistered: ${device.name}`, { deviceId, userId });
    this.emit('device-unregistered', { deviceId, userId });

    return true;
  }

  async updateDeviceLocation(deviceId, locationData) {
    const device = this.registeredDevices.get(deviceId);
    if (!device || !device.locationEnabled) return false;

    const location = {
      timestamp: Date.now(),
      latitude: locationData.latitude,
      longitude: locationData.longitude,
      accuracy: locationData.accuracy || 0,
      altitude: locationData.altitude,
      heading: locationData.heading,
      speed: locationData.speed,
      source: locationData.source || 'gps', // gps, wifi, cellular, bluetooth
      batteryLevel: locationData.batteryLevel
    };

    // Update device location
    device.location = location;
    device.lastSeen = location.timestamp;
    device.status = 'online';

    // Add to location history
    const history = this.deviceLocations.get(deviceId) || [];
    history.push(location);
    
    // Keep last 100 locations
    if (history.length > 100) {
      history.splice(0, history.length - 100);
    }
    
    this.deviceLocations.set(deviceId, history);
    this.metrics.locationsTracked++;

    // Check for geofence alerts
    await this.checkGeofences(device, location);

    this.emit('location-updated', { deviceId, location, device });

    logger.debug(`Location updated for device ${device.name}`, {
      deviceId,
      latitude: location.latitude,
      longitude: location.longitude,
      accuracy: location.accuracy
    });

    return true;
  }

  startDeviceDiscovery() {
    this.discoveryInterval = setInterval(async () => {
      try {
        await this.discoverDevices();
        await this.updateDeviceStatuses();
      } catch (error) {
        logger.error('Device discovery error:', error);
      }
    }, this.options.discoveryInterval);
  }

  async discoverDevices() {
    // Simulate device discovery across different methods
    const discovered = [];

    // Network discovery
    if (this.options.enableNetworkScanning) {
      const networkDevices = await this.scanNetwork();
      discovered.push(...networkDevices);
    }

    // Bluetooth discovery
    if (this.options.enableBluetoothScanning) {
      const bluetoothDevices = await this.scanBluetooth();
      discovered.push(...bluetoothDevices);
    }

    // Update nearby devices
    for (const device of discovered) {
      this.nearbyDevices.set(device.id, {
        ...device,
        discoveredAt: Date.now(),
        discoveryMethod: device.method
      });
    }

    this.metrics.devicesFound += discovered.length;

    if (discovered.length > 0) {
      this.emit('devices-discovered', discovered);
    }
  }

  async scanNetwork() {
    this.metrics.networkScansPerformed++;
    
    // Simulate network scanning
    const devices = [
      {
        id: 'network_device_1',
        name: 'Unknown Device',
        ipAddress: '192.168.1.105',
        macAddress: this.hashSensitiveData('AA:BB:CC:DD:EE:FF'),
        type: 'unknown',
        method: 'network',
        ports: [80, 443],
        hostname: 'unknown-device.local'
      },
      {
        id: 'network_device_2',
        name: 'Smart TV',
        ipAddress: '192.168.1.110',
        macAddress: this.hashSensitiveData('11:22:33:44:55:66'),
        type: 'smart_device',
        method: 'network',
        ports: [80],
        hostname: 'smart-tv.local'
      }
    ];

    return devices;
  }

  async scanBluetooth() {
    this.metrics.bluetoothScansPerformed++;
    
    // Simulate Bluetooth scanning
    const devices = [
      {
        id: 'bt_device_1',
        name: 'iPhone 12',
        address: this.hashSensitiveData('00:11:22:33:44:55'),
        type: 'mobile',
        method: 'bluetooth',
        rssi: -45,
        services: ['audio', 'hid']
      },
      {
        id: 'bt_device_2',
        name: 'AirPods Pro',
        address: this.hashSensitiveData('66:77:88:99:AA:BB'),
        type: 'audio',
        method: 'bluetooth',
        rssi: -35,
        services: ['audio']
      }
    ];

    return devices;
  }

  startLocationTracking() {
    setInterval(async () => {
      // Request location updates from all registered devices
      for (const [deviceId, device] of this.registeredDevices) {
        if (device.locationEnabled && device.status === 'online') {
          await this.requestLocationUpdate(deviceId);
        }
      }
    }, 60000); // Every minute
  }

  async requestLocationUpdate(deviceId) {
    const device = this.registeredDevices.get(deviceId);
    if (!device) return;

    // In a real implementation, this would send a request to the device
    // Simulate location update
    const simulatedLocation = {
      latitude: 40.7128 + (Math.random() - 0.5) * 0.01,
      longitude: -74.0060 + (Math.random() - 0.5) * 0.01,
      accuracy: Math.random() * 100,
      source: 'simulated',
      batteryLevel: Math.floor(Math.random() * 100)
    };

    await this.updateDeviceLocation(deviceId, simulatedLocation);
  }

  async updateDeviceStatuses() {
    const now = Date.now();
    
    for (const [deviceId, device] of this.registeredDevices) {
      const timeSinceLastSeen = now - device.lastSeen;
      
      if (timeSinceLastSeen > this.options.deviceTimeout) {
        if (device.status !== 'offline') {
          device.status = 'offline';
          this.emit('device-offline', { deviceId, device });
          
          logger.info(`Device went offline: ${device.name}`, {
            deviceId,
            lastSeen: new Date(device.lastSeen).toISOString()
          });
        }
      } else if (device.status === 'offline') {
        device.status = 'online';
        this.emit('device-online', { deviceId, device });
        
        logger.info(`Device came online: ${device.name}`, { deviceId });
      }
    }
  }

  async findDevice(userId, deviceId, options = {}) {
    const device = this.registeredDevices.get(deviceId);
    
    if (!device) {
      throw new Error('Device not found');
    }

    // Check ownership or sharing permissions
    if (device.userId !== userId && !this.canAccessDevice(userId, deviceId)) {
      throw new Error('Unauthorized access to device');
    }

    const result = {
      device: this.sanitizeDeviceForUser(device, userId),
      location: device.location,
      lastSeen: device.lastSeen,
      status: device.status,
      nearbyDevices: [],
      locationHistory: []
    };

    // Include location history if requested
    if (options.includeHistory) {
      result.locationHistory = this.deviceLocations.get(deviceId) || [];
    }

    // Find nearby devices
    if (options.includeNearby && device.location) {
      result.nearbyDevices = await this.findNearbyDevices(deviceId, device.location);
    }

    this.emit('device-found', { userId, deviceId, result });

    return result;
  }

  async executeRemoteAction(userId, deviceId, action, options = {}) {
    if (!this.options.allowRemoteActions) {
      throw new Error('Remote actions are disabled');
    }

    const device = this.registeredDevices.get(deviceId);
    if (!device) {
      throw new Error('Device not found');
    }

    // Check ownership or permissions
    if (device.userId !== userId && !this.canAccessDevice(userId, deviceId)) {
      throw new Error('Unauthorized access to device');
    }

    // Check device capabilities
    if (!this.deviceSupportsAction(device, action)) {
      throw new Error(`Device does not support action: ${action}`);
    }

    const actionId = uuidv4();
    const remoteAction = {
      id: actionId,
      deviceId,
      userId,
      action,
      options,
      timestamp: Date.now(),
      status: 'pending',
      result: null
    };

    this.pendingActions.set(actionId, remoteAction);

    try {
      // Execute the action
      const result = await this.performRemoteAction(device, action, options);
      
      remoteAction.status = 'completed';
      remoteAction.result = result;
      remoteAction.completedAt = Date.now();

      this.metrics.remoteActionsExecuted++;

      logger.info(`Remote action executed: ${action}`, {
        deviceId,
        userId,
        actionId,
        success: result.success
      });

      this.emit('remote-action-completed', remoteAction);

      return result;
    } catch (error) {
      remoteAction.status = 'failed';
      remoteAction.error = error.message;
      
      logger.error(`Remote action failed: ${action}`, {
        deviceId,
        userId,
        actionId,
        error: error.message
      });

      this.emit('remote-action-failed', { ...remoteAction, error });
      throw error;
    }
  }

  async performRemoteAction(device, action, options) {
    // Simulate remote actions
    switch (action) {
      case 'lock':
        if (!this.options.enableRemoteLock) throw new Error('Remote lock disabled');
        return { success: true, message: 'Device locked successfully' };

      case 'alarm':
        if (!this.options.enableRemoteAlarm) throw new Error('Remote alarm disabled');
        return { success: true, message: 'Alarm activated on device', duration: options.duration || 60 };

      case 'message':
        if (!this.options.enableRemoteMessage) throw new Error('Remote message disabled');
        return { success: true, message: 'Message sent to device', content: options.message };

      case 'locate':
        return { success: true, message: 'Location request sent', location: device.location };

      case 'wipe':
        if (!this.options.enableRemoteWipe) throw new Error('Remote wipe disabled');
        // This would be a destructive action requiring additional confirmation
        if (!options.confirmed) throw new Error('Wipe action requires confirmation');
        return { success: true, message: 'Device wipe initiated' };

      default:
        throw new Error(`Unknown action: ${action}`);
    }
  }

  deviceSupportsAction(device, action) {
    switch (action) {
      case 'lock':
        return device.capabilities.canLock;
      case 'alarm':
        return device.capabilities.canAlarm;
      case 'message':
        return device.capabilities.canMessage;
      case 'wipe':
        return device.capabilities.canWipe;
      case 'locate':
        return device.locationEnabled;
      default:
        return false;
    }
  }

  async findNearbyDevices(deviceId, location, radius = 1000) {
    const nearby = [];
    
    // Check registered devices
    for (const [id, device] of this.registeredDevices) {
      if (id === deviceId || !device.location) continue;
      
      const distance = this.calculateDistance(location, device.location);
      if (distance <= radius) {
        nearby.push({
          deviceId: id,
          name: device.name,
          type: device.type,
          distance: Math.round(distance),
          lastSeen: device.lastSeen
        });
      }
    }

    // Check discovered devices
    for (const [id, device] of this.nearbyDevices) {
      if (device.location) {
        const distance = this.calculateDistance(location, device.location);
        if (distance <= radius) {
          nearby.push({
            deviceId: id,
            name: device.name || 'Unknown Device',
            type: device.type,
            distance: Math.round(distance),
            discoveryMethod: device.discoveryMethod
          });
        }
      }
    }

    return nearby.sort((a, b) => a.distance - b.distance);
  }

  calculateDistance(loc1, loc2) {
    // Haversine formula for calculating distance between two coordinates
    const R = 6371000; // Earth's radius in meters
    const φ1 = loc1.latitude * Math.PI / 180;
    const φ2 = loc2.latitude * Math.PI / 180;
    const Δφ = (loc2.latitude - loc1.latitude) * Math.PI / 180;
    const Δλ = (loc2.longitude - loc1.longitude) * Math.PI / 180;

    const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
              Math.cos(φ1) * Math.cos(φ2) *
              Math.sin(Δλ/2) * Math.sin(Δλ/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));

    return R * c; // Distance in meters
  }

  async createFamilyGroup(ownerId, groupName, members = []) {
    const groupId = uuidv4();
    const group = {
      id: groupId,
      name: groupName,
      owner: ownerId,
      members: [ownerId, ...members],
      devices: [],
      createdAt: Date.now(),
      settings: {
        shareLocations: true,
        allowRemoteActions: false,
        notifyOnDeviceEvents: true
      }
    };

    this.familyGroups.set(groupId, group);

    logger.info(`Family group created: ${groupName}`, {
      groupId,
      owner: ownerId,
      memberCount: group.members.length
    });

    this.emit('family-group-created', group);
    return group;
  }

  async shareDeviceWithGroup(userId, deviceId, groupId, permissions = {}) {
    const device = this.registeredDevices.get(deviceId);
    const group = this.familyGroups.get(groupId);

    if (!device || device.userId !== userId) {
      throw new Error('Device not found or unauthorized');
    }

    if (!group || !group.members.includes(userId)) {
      throw new Error('Group not found or unauthorized');
    }

    const shareConfig = {
      groupId,
      sharedBy: userId,
      sharedAt: Date.now(),
      permissions: {
        canView: permissions.canView !== false,
        canLocate: permissions.canLocate !== false,
        canSendMessage: permissions.canSendMessage || false,
        canLock: permissions.canLock || false,
        canAlarm: permissions.canAlarm || false
      }
    };

    this.sharedDevices.set(deviceId, shareConfig);
    
    if (!group.devices.includes(deviceId)) {
      group.devices.push(deviceId);
    }

    logger.info(`Device shared with group: ${device.name}`, {
      deviceId,
      groupId,
      groupName: group.name
    });

    this.emit('device-shared', { deviceId, groupId, shareConfig });
    return shareConfig;
  }

  canAccessDevice(userId, deviceId) {
    // Check direct ownership
    const device = this.registeredDevices.get(deviceId);
    if (device && device.userId === userId) return true;

    // Check family sharing
    const shareConfig = this.sharedDevices.get(deviceId);
    if (!shareConfig) return false;

    const group = this.familyGroups.get(shareConfig.groupId);
    return group && group.members.includes(userId);
  }

  sanitizeDeviceForUser(device, userId) {
    const isOwner = device.userId === userId;
    
    return {
      id: device.id,
      name: device.name,
      type: device.type,
      platform: device.platform,
      status: device.status,
      lastSeen: device.lastSeen,
      location: device.location,
      capabilities: isOwner ? device.capabilities : {
        canLock: false,
        canWipe: false,
        canAlarm: device.capabilities.canAlarm,
        canMessage: device.capabilities.canMessage
      },
      isOwned: isOwner
    };
  }

  async checkGeofences(device, location) {
    // Implement geofence checking logic
    // This would check if the device has entered or left defined areas
    const geofences = [
      { name: 'Home', lat: 40.7128, lng: -74.0060, radius: 100 },
      { name: 'Work', lat: 40.7589, lng: -73.9851, radius: 200 }
    ];

    for (const geofence of geofences) {
      const distance = this.calculateDistance(location, {
        latitude: geofence.lat,
        longitude: geofence.lng
      });

      if (distance <= geofence.radius) {
        this.emit('geofence-entered', {
          deviceId: device.id,
          device,
          geofence,
          location
        });
      }
    }
  }

  hashSensitiveData(data) {
    if (!data) return null;
    return crypto.createHash('sha256').update(data).digest('hex').substr(0, 8);
  }

  startNetworkScanning() {
    setInterval(async () => {
      if (this.activeScans.has('network')) return;
      
      this.activeScans.add('network');
      try {
        await this.scanNetwork();
      } finally {
        this.activeScans.delete('network');
      }
    }, 120000); // Every 2 minutes
  }

  startBluetoothScanning() {
    setInterval(async () => {
      if (this.activeScans.has('bluetooth')) return;
      
      this.activeScans.add('bluetooth');
      try {
        await this.scanBluetooth();
      } finally {
        this.activeScans.delete('bluetooth');
      }
    }, 180000); // Every 3 minutes
  }

  startCleanupRoutines() {
    // Clean up old nearby devices
    setInterval(() => {
      const cutoffTime = Date.now() - (this.options.deviceTimeout * 2);
      
      for (const [deviceId, device] of this.nearbyDevices) {
        if (device.discoveredAt < cutoffTime) {
          this.nearbyDevices.delete(deviceId);
        }
      }
    }, 300000); // Every 5 minutes

    // Clean up completed actions
    setInterval(() => {
      const cutoffTime = Date.now() - 3600000; // 1 hour
      
      for (const [actionId, action] of this.pendingActions) {
        if (action.completedAt && action.completedAt < cutoffTime) {
          this.pendingActions.delete(actionId);
        }
      }
    }, 3600000); // Every hour
  }

  // Public API methods
  getUserDevices(userId) {
    const deviceIds = this.userDevices.get(userId) || [];
    return deviceIds.map(deviceId => {
      const device = this.registeredDevices.get(deviceId);
      return device ? this.sanitizeDeviceForUser(device, userId) : null;
    }).filter(Boolean);
  }

  getFamilyDevices(userId) {
    const devices = [];
    
    for (const [groupId, group] of this.familyGroups) {
      if (!group.members.includes(userId)) continue;
      
      for (const deviceId of group.devices) {
        const device = this.registeredDevices.get(deviceId);
        if (device) {
          devices.push({
            ...this.sanitizeDeviceForUser(device, userId),
            groupId,
            groupName: group.name
          });
        }
      }
    }

    return devices;
  }

  getDiscoveredDevices() {
    return Array.from(this.nearbyDevices.values());
  }

  getMetrics() {
    return {
      ...this.metrics,
      registeredDevicesCount: this.registeredDevices.size,
      nearbyDevicesCount: this.nearbyDevices.size,
      familyGroupsCount: this.familyGroups.size,
      pendingActionsCount: this.pendingActions.size
    };
  }

  async cleanup() {
    // Clear intervals
    if (this.discoveryInterval) clearInterval(this.discoveryInterval);
    
    // Clear all data
    this.registeredDevices.clear();
    this.userDevices.clear();
    this.deviceLocations.clear();
    this.nearbyDevices.clear();
    this.deviceKeys.clear();
    this.pendingActions.clear();
    this.familyGroups.clear();
    this.sharedDevices.clear();

    this.removeAllListeners();
    logger.info('Find My Device system cleaned up');
  }
}

module.exports = FindMyDevice;