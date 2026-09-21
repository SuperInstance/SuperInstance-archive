/**
 * WebSocket Manager for real-time updates
 */

import { EventEmitter } from './events.js';
import { AuthManager } from './auth.js';

class WebSocketManagerClass extends EventEmitter {
    constructor() {
        super();
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.isConnecting = false;
        this.isConnected = false;
        this.messageQueue = [];
        this.subscriptions = new Set();
    }

    init() {
        this.connect();
        
        // Listen for auth changes
        AuthManager.on('login', () => {
            if (!this.isConnected) {
                this.connect();
            }
        });
        
        AuthManager.on('logout', () => {
            this.disconnect();
        });
    }

    connect() {
        if (this.isConnecting || this.isConnected) {
            return;
        }

        this.isConnecting = true;
        
        const wsUrl = this.getWebSocketUrl();
        console.log('Connecting to WebSocket:', wsUrl);

        try {
            this.ws = new WebSocket(wsUrl);
            this.setupEventListeners();
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.handleConnectionError();
        }
    }

    getWebSocketUrl() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const token = AuthManager.getToken();
        
        let url = `${protocol}//${host}/ws`;
        
        if (token) {
            url += `?token=${encodeURIComponent(token)}`;
        }
        
        return url;
    }

    setupEventListeners() {
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.isConnecting = false;
            this.isConnected = true;
            this.reconnectAttempts = 0;
            
            // Send queued messages
            this.flushMessageQueue();
            
            // Re-subscribe to channels
            this.resubscribe();
            
            this.emit('connected');
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };

        this.ws.onclose = (event) => {
            console.log('WebSocket disconnected:', event.code, event.reason);
            this.isConnecting = false;
            this.isConnected = false;
            
            this.emit('disconnected', event.code, event.reason);
            
            // Attempt to reconnect if not intentionally closed
            if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
                this.scheduleReconnect();
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.emit('error', error);
        };
    }

    handleMessage(data) {
        const { type, payload, channel } = data;
        
        // Emit specific event based on message type
        this.emit(type, payload, channel);
        
        // Emit general message event
        this.emit('message', data);
        
        // Handle specific message types
        switch (type) {
            case 'file_change':
                this.emit('fileChange', payload);
                break;
            case 'sync_status':
                this.emit('syncStatus', payload);
                break;
            case 'upload_progress':
                this.emit('uploadProgress', payload);
                break;
            case 'system_notification':
                this.emit('systemNotification', payload);
                break;
        }
    }

    send(message) {
        if (this.isConnected && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
            return true;
        } else {
            // Queue message for later
            this.messageQueue.push(message);
            return false;
        }
    }

    subscribe(channel) {
        this.subscriptions.add(channel);
        
        const message = {
            type: 'subscribe',
            channel: channel
        };
        
        return this.send(message);
    }

    unsubscribe(channel) {
        this.subscriptions.delete(channel);
        
        const message = {
            type: 'unsubscribe',
            channel: channel
        };
        
        return this.send(message);
    }

    resubscribe() {
        this.subscriptions.forEach(channel => {
            const message = {
                type: 'subscribe',
                channel: channel
            };
            this.send(message);
        });
    }

    flushMessageQueue() {
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            this.send(message);
        }
    }

    scheduleReconnect() {
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        
        console.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
        
        setTimeout(() => {
            if (!this.isConnected) {
                this.connect();
            }
        }, delay);
    }

    handleConnectionError() {
        this.isConnecting = false;
        
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
        } else {
            console.error('Max reconnection attempts reached');
            this.emit('connectionFailed');
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close(1000, 'User logout');
            this.ws = null;
        }
        
        this.isConnected = false;
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.messageQueue = [];
        this.subscriptions.clear();
    }

    getConnectionStatus() {
        return {
            isConnected: this.isConnected,
            isConnecting: this.isConnecting,
            reconnectAttempts: this.reconnectAttempts
        };
    }

    // Utility methods for common operations
    subscribeToFileEvents() {
        return this.subscribe('file_events');
    }

    subscribeToSyncStatus() {
        return this.subscribe('sync_status');
    }

    subscribeToUploadProgress() {
        return this.subscribe('upload_progress');
    }

    subscribeToNotifications() {
        return this.subscribe('notifications');
    }
}

export const WebSocketManager = new WebSocketManagerClass();