import React, { useState, useEffect } from 'react';
import { io, Socket } from 'socket.io-client';
import { useAuthStore } from '@/store/authStore';

export interface WebSocketMessage {
  type: string;
  source: string;
  data: any;
  timestamp: number;
  userId?: string;
}

export interface ServiceStatus {
  serviceId: string;
  hubId: string;
  status: 'online' | 'offline' | 'maintenance' | 'error';
  lastHeartbeat: string;
  responseTime?: number;
}

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  source: string;
  timestamp: string;
  read: boolean;
  actions?: Array<{
    label: string;
    action: string;
    variant?: 'primary' | 'secondary' | 'destructive';
  }>;
  data?: any;
}

export class WebSocketService {
  private socket: Socket | null = null;
  private connected = false;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private messageHandlers: Map<string, Array<(message: WebSocketMessage) => void>> = new Map();
  private statusUpdateCallbacks: Array<(status: ServiceStatus) => void> = [];
  private notificationCallbacks: Array<(notification: Notification) => void> = [];
  private connectionCallbacks: Array<(connected: boolean) => void> = [];

  // Initialize WebSocket connection
  initialize() {
    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8001';
    
    this.socket = io(wsUrl, {
      autoConnect: false,
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 10000,
      forceNew: true
    });

    this.setupEventHandlers();
  }

  // Setup socket event handlers
  private setupEventHandlers() {
    if (!this.socket) return;

    // Connection events
    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.connected = true;
      this.reconnectAttempts = 0;
      this.notifyConnectionChange(true);
      this.authenticateConnection();
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      this.connected = false;
      this.notifyConnectionChange(false);
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.reconnectAttempts++;
      
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        console.error('Max reconnection attempts reached');
      }
    });

    // Service status updates
    this.socket.on('service_status_update', (data: ServiceStatus) => {
      console.log('Service status update:', data);
      this.statusUpdateCallbacks.forEach(callback => callback(data));
    });

    // Hub health updates
    this.socket.on('hub_health_update', (data: any) => {
      console.log('Hub health update:', data);
      // Forward to service status handlers
      if (data.services) {
        data.services.forEach((service: ServiceStatus) => {
          this.statusUpdateCallbacks.forEach(callback => callback(service));
        });
      }
    });

    // Real-time notifications
    this.socket.on('notification', (data: Notification) => {
      console.log('New notification:', data);
      this.notificationCallbacks.forEach(callback => callback(data));
    });

    // Integration status updates
    this.socket.on('integration_update', (data: any) => {
      console.log('Integration update:', data);
      this.handleMessage({
        type: 'integration_update',
        source: 'unified-hub',
        data,
        timestamp: Date.now()
      });
    });

    // Cross-service messages
    this.socket.on('cross_service_message', (data: WebSocketMessage) => {
      console.log('Cross-service message:', data);
      this.handleMessage(data);
    });

    // User activity broadcasts
    this.socket.on('user_activity', (data: any) => {
      this.handleMessage({
        type: 'user_activity',
        source: data.source || 'unknown',
        data,
        timestamp: Date.now()
      });
    });

    // Error events
    this.socket.on('error', (error: any) => {
      console.error('WebSocket error:', error);
      this.handleMessage({
        type: 'error',
        source: 'websocket',
        data: { error: error.message || 'Unknown error' },
        timestamp: Date.now()
      });
    });
  }

  // Authenticate the connection
  private authenticateConnection() {
    const { user, tokens } = useAuthStore.getState();
    
    if (user && tokens.accessToken && this.socket) {
      this.socket.emit('authenticate', {
        token: tokens.accessToken,
        userId: user.id,
        userRole: user.role
      });
    }
  }

  // Connect to WebSocket
  connect() {
    if (this.socket && !this.connected) {
      this.socket.connect();
    } else if (!this.socket) {
      this.initialize();
      this.socket?.connect();
    }
  }

  // Disconnect from WebSocket
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.connected = false;
      this.notifyConnectionChange(false);
    }
  }

  // Send message
  sendMessage(type: string, data: any, target?: string) {
    if (!this.socket || !this.connected) {
      console.warn('WebSocket not connected, queuing message');
      return;
    }

    const message: WebSocketMessage = {
      type,
      source: 'unified-hub',
      data,
      timestamp: Date.now(),
      userId: useAuthStore.getState().user?.id
    };

    if (target) {
      this.socket.emit('targeted_message', { ...message, target });
    } else {
      this.socket.emit('broadcast_message', message);
    }
  }

  // Subscribe to service status updates
  subscribeToServiceUpdates() {
    if (this.socket && this.connected) {
      this.socket.emit('subscribe_service_updates');
    }
  }

  // Subscribe to specific service
  subscribeToService(serviceId: string) {
    if (this.socket && this.connected) {
      this.socket.emit('subscribe_service', { serviceId });
    }
  }

  // Unsubscribe from service
  unsubscribeFromService(serviceId: string) {
    if (this.socket && this.connected) {
      this.socket.emit('unsubscribe_service', { serviceId });
    }
  }

  // Subscribe to hub updates
  subscribeToHub(hubId: string) {
    if (this.socket && this.connected) {
      this.socket.emit('subscribe_hub', { hubId });
    }
  }

  // Request health check for all services
  requestHealthCheck() {
    if (this.socket && this.connected) {
      this.socket.emit('request_health_check');
    }
  }

  // Request integration status
  requestIntegrationStatus() {
    if (this.socket && this.connected) {
      this.socket.emit('request_integration_status');
    }
  }

  // Handle incoming messages
  private handleMessage(message: WebSocketMessage) {
    const handlers = this.messageHandlers.get(message.type);
    if (handlers) {
      handlers.forEach(handler => handler(message));
    }

    // Also handle with generic handlers
    const genericHandlers = this.messageHandlers.get('*');
    if (genericHandlers) {
      genericHandlers.forEach(handler => handler(message));
    }
  }

  // Register message handler
  onMessage(type: string, handler: (message: WebSocketMessage) => void) {
    const handlers = this.messageHandlers.get(type) || [];
    handlers.push(handler);
    this.messageHandlers.set(type, handlers);

    // Return unsubscribe function
    return () => {
      const currentHandlers = this.messageHandlers.get(type) || [];
      const index = currentHandlers.indexOf(handler);
      if (index > -1) {
        currentHandlers.splice(index, 1);
        this.messageHandlers.set(type, currentHandlers);
      }
    };
  }

  // Register status update callback
  onStatusUpdate(callback: (status: ServiceStatus) => void) {
    this.statusUpdateCallbacks.push(callback);

    // Return unsubscribe function
    return () => {
      const index = this.statusUpdateCallbacks.indexOf(callback);
      if (index > -1) {
        this.statusUpdateCallbacks.splice(index, 1);
      }
    };
  }

  // Register notification callback
  onNotification(callback: (notification: Notification) => void) {
    this.notificationCallbacks.push(callback);

    // Return unsubscribe function
    return () => {
      const index = this.notificationCallbacks.indexOf(callback);
      if (index > -1) {
        this.notificationCallbacks.splice(index, 1);
      }
    };
  }

  // Register connection callback
  onConnectionChange(callback: (connected: boolean) => void) {
    this.connectionCallbacks.push(callback);

    // Return unsubscribe function
    return () => {
      const index = this.connectionCallbacks.indexOf(callback);
      if (index > -1) {
        this.connectionCallbacks.splice(index, 1);
      }
    };
  }

  // Notify connection change
  private notifyConnectionChange(connected: boolean) {
    this.connectionCallbacks.forEach(callback => callback(connected));
  }

  // Send user activity
  sendUserActivity(activity: string, data?: any) {
    this.sendMessage('user_activity', {
      activity,
      timestamp: Date.now(),
      ...data
    });
  }

  // Send notification acknowledgment
  acknowledgeNotification(notificationId: string) {
    if (this.socket && this.connected) {
      this.socket.emit('acknowledge_notification', { notificationId });
    }
  }

  // Send typing indicator (for future chat features)
  sendTypingIndicator(target: string, typing: boolean) {
    this.sendMessage('typing_indicator', { typing }, target);
  }

  // Get connection status
  isConnected(): boolean {
    return this.connected;
  }

  // Get socket instance (for advanced usage)
  getSocket(): Socket | null {
    return this.socket;
  }
}

// Global WebSocket service instance
export const webSocketService = new WebSocketService();

// Auto-initialize when auth state changes
useAuthStore.subscribe((state) => {
  if (state.isAuthenticated && !webSocketService.isConnected()) {
    webSocketService.connect();
  } else if (!state.isAuthenticated && webSocketService.isConnected()) {
    webSocketService.disconnect();
  }
});

// React hook for using WebSocket
export function useWebSocket() {
  const [connected, setConnected] = useState(webSocketService.isConnected());

  useEffect(() => {
    const unsubscribe = webSocketService.onConnectionChange(setConnected);
    return unsubscribe;
  }, []);

  return {
    connected,
    service: webSocketService,
    sendMessage: webSocketService.sendMessage.bind(webSocketService),
    onMessage: webSocketService.onMessage.bind(webSocketService),
    onStatusUpdate: webSocketService.onStatusUpdate.bind(webSocketService),
    onNotification: webSocketService.onNotification.bind(webSocketService)
  };
}