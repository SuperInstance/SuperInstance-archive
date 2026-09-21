import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { EventEmitter } from 'events';
import WebSocket from 'ws';

export interface OctoPrintConfig {
  baseUrl: string;
  apiKey: string;
  timeout?: number;
  retryAttempts?: number;
  retryDelay?: number;
}

export interface OctoPrintConnection {
  current: {
    state: string;
    port: string | null;
    baudrate: number | null;
    printerProfile: string;
  };
  options: {
    ports: string[];
    baudrates: number[];
    printerProfiles: Array<{
      id: string;
      name: string;
    }>;
    portPreference: string | null;
    baudratePreference: number | null;
    printerProfilePreference: string | null;
    autoconnect: boolean;
  };
}

export interface OctoPrintJob {
  job: {
    file: {
      name: string | null;
      origin: string | null;
      size: number | null;
      date: number | null;
    };
    estimatedPrintTime: number | null;
    lastPrintTime: number | null;
    filament: {
      length: number | null;
      volume: number | null;
    } | null;
  };
  progress: {
    completion: number | null;
    filepos: number | null;
    printTime: number | null;
    printTimeLeft: number | null;
    printTimeOrigin: number | null;
  };
  state: string;
}

export interface OctoPrintPrinter {
  temperature: {
    bed?: {
      actual: number;
      target: number;
      offset: number;
    };
    tool0?: {
      actual: number;
      target: number;
      offset: number;
    };
    [key: string]: any;
  };
  sd: {
    ready: boolean;
  };
  state: {
    text: string;
    flags: {
      operational: boolean;
      paused: boolean;
      printing: boolean;
      cancelling: boolean;
      pausing: boolean;
      error: boolean;
      ready: boolean;
      closedOrError: boolean;
    };
  };
}

export interface OctoPrintFile {
  name: string;
  path: string;
  type: 'folder' | 'machinecode';
  typePath: string[];
  size?: number;
  date?: number;
  origin: 'local' | 'sdcard';
  refs?: {
    resource: string;
    download: string;
  };
  gcodeAnalysis?: {
    estimatedPrintTime: number;
    filament: {
      length: number;
      volume: number;
    };
    dimensions: {
      depth: number;
      height: number;
      width: number;
    };
  };
  prints?: {
    failure: number;
    success: number;
    last?: {
      date: number;
      printTime: number;
      success: boolean;
    };
  };
}

export interface OctoPrintSettings {
  api: {
    key: string;
    allowCrossOrigin: boolean;
  };
  appearance: {
    name: string;
    color: string;
    colorTransparent: boolean;
    colorIcon: boolean;
    defaultLanguage: string;
  };
  printer: {
    defaultExtrusionLength: number;
  };
  serial: {
    port: string;
    baudrate: number;
    autoconnect: boolean;
  };
  server: {
    host: string;
    port: number;
  };
  webcam: {
    streamUrl: string;
    snapshotUrl: string;
    ffmpegPath: string;
    bitrate: string;
    watermark: boolean;
    flipH: boolean;
    flipV: boolean;
    rotate90: boolean;
  };
  [key: string]: any;
}

export interface OctoPrintSystemInfo {
  version: string;
  branch: string;
  pip: {
    [packageName: string]: {
      version: string;
      requirement: string;
    };
  };
}

export interface OctoPrintTimelapse {
  config: {
    type: 'off' | 'zchange' | 'timed';
    postRoll: number;
    fps: number;
    bitrate: string;
    threads: number;
    videoCodec: 'mpeg2video' | 'libx264';
    interval?: number;
  };
  files: Array<{
    name: string;
    size: number;
    date: number;
    url: string;
  }>;
}

export class OctoPrintClient extends EventEmitter {
  private client: AxiosInstance;
  private config: Required<OctoPrintConfig>;
  private websocket?: WebSocket;
  private heartbeatInterval?: NodeJS.Timeout;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  constructor(config: OctoPrintConfig) {
    super();
    
    this.config = {
      timeout: 10000,
      retryAttempts: 3,
      retryDelay: 1000,
      ...config
    };

    this.client = axios.create({
      baseURL: this.config.baseUrl,
      timeout: this.config.timeout,
      headers: {
        'X-Api-Key': this.config.apiKey,
        'Content-Type': 'application/json'
      }
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        this.emit('requestSent', { url: config.url, method: config.method });
        return config;
      },
      (error) => {
        this.emit('requestError', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        this.emit('responseReceived', { 
          url: response.config.url, 
          status: response.status, 
          data: response.data 
        });
        return response;
      },
      async (error) => {
        const { config } = error;
        
        if (!config || !config.retry) {
          config.retry = 0;
        }

        if (config.retry < this.config.retryAttempts) {
          config.retry += 1;
          
          this.emit('retryAttempt', { 
            attempt: config.retry, 
            maxAttempts: this.config.retryAttempts, 
            url: config.url 
          });

          await new Promise(resolve => setTimeout(resolve, this.config.retryDelay));
          return this.client(config);
        }

        this.emit('responseError', error);
        return Promise.reject(error);
      }
    );
  }

  async connect(): Promise<void> {
    try {
      await this.getVersion();
      this.connectWebSocket();
      this.emit('connected');
    } catch (error) {
      this.emit('connectionError', error);
      throw error;
    }
  }

  async disconnect(): Promise<void> {
    if (this.websocket) {
      this.websocket.close();
      this.websocket = undefined;
    }

    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = undefined;
    }

    this.emit('disconnected');
  }

  private connectWebSocket(): void {
    const wsUrl = this.config.baseUrl.replace(/^http/, 'ws') + '/sockjs/websocket';
    
    this.websocket = new WebSocket(wsUrl);

    this.websocket.on('open', () => {
      this.emit('websocketConnected');
      this.reconnectAttempts = 0;
      
      // Send authentication
      this.websocket?.send(JSON.stringify({
        auth: this.config.apiKey
      }));

      // Start heartbeat
      this.startHeartbeat();
    });

    this.websocket.on('message', (data: string) => {
      try {
        const message = JSON.parse(data);
        this.handleWebSocketMessage(message);
      } catch (error) {
        this.emit('websocketError', { type: 'parse', error, data });
      }
    });

    this.websocket.on('close', () => {
      this.emit('websocketDisconnected');
      
      if (this.heartbeatInterval) {
        clearInterval(this.heartbeatInterval);
        this.heartbeatInterval = undefined;
      }

      // Attempt to reconnect
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        setTimeout(() => {
          this.connectWebSocket();
        }, 5000 * this.reconnectAttempts);
      }
    });

    this.websocket.on('error', (error) => {
      this.emit('websocketError', { type: 'connection', error });
    });
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
        this.websocket.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);
  }

  private handleWebSocketMessage(message: any): void {
    switch (message.current?.state) {
      case 'Printing':
        this.emit('printingStarted', message);
        break;
      case 'Operational':
        this.emit('printerReady', message);
        break;
      case 'Offline':
        this.emit('printerOffline', message);
        break;
    }

    if (message.current?.job) {
      this.emit('jobUpdate', message.current.job);
    }

    if (message.current?.progress) {
      this.emit('progressUpdate', message.current.progress);
    }

    if (message.temps) {
      this.emit('temperatureUpdate', message.temps);
    }

    if (message.logs) {
      this.emit('logMessage', message.logs);
    }

    this.emit('message', message);
  }

  // Connection API
  async getConnectionStatus(): Promise<OctoPrintConnection> {
    const response = await this.client.get<OctoPrintConnection>('/api/connection');
    return response.data;
  }

  async connectPrinter(options?: { port?: string; baudrate?: number; printerProfile?: string; save?: boolean; autoconnect?: boolean }): Promise<void> {
    await this.client.post('/api/connection', {
      command: 'connect',
      ...options
    });
  }

  async disconnectPrinter(): Promise<void> {
    await this.client.post('/api/connection', {
      command: 'disconnect'
    });
  }

  // Job API
  async getJobStatus(): Promise<OctoPrintJob> {
    const response = await this.client.get<OctoPrintJob>('/api/job');
    return response.data;
  }

  async startJob(): Promise<void> {
    await this.client.post('/api/job', {
      command: 'start'
    });
  }

  async pauseJob(): Promise<void> {
    await this.client.post('/api/job', {
      command: 'pause',
      action: 'pause'
    });
  }

  async resumeJob(): Promise<void> {
    await this.client.post('/api/job', {
      command: 'pause',
      action: 'resume'
    });
  }

  async cancelJob(): Promise<void> {
    await this.client.post('/api/job', {
      command: 'cancel'
    });
  }

  async restartJob(): Promise<void> {
    await this.client.post('/api/job', {
      command: 'restart'
    });
  }

  // Printer API
  async getPrinterStatus(): Promise<OctoPrintPrinter> {
    const response = await this.client.get<OctoPrintPrinter>('/api/printer');
    return response.data;
  }

  async setToolTemperature(tool: number, temperature: number): Promise<void> {
    await this.client.post('/api/printer/tool', {
      command: 'target',
      targets: {
        [`tool${tool}`]: temperature
      }
    });
  }

  async setBedTemperature(temperature: number): Promise<void> {
    await this.client.post('/api/printer/bed', {
      command: 'target',
      target: temperature
    });
  }

  async homeAxes(axes?: ('x' | 'y' | 'z')[]): Promise<void> {
    await this.client.post('/api/printer/printhead', {
      command: 'home',
      axes: axes || ['x', 'y', 'z']
    });
  }

  async moveHead(axes: { x?: number; y?: number; z?: number }, absolute = false, speed?: number): Promise<void> {
    await this.client.post('/api/printer/printhead', {
      command: 'jog',
      ...axes,
      absolute,
      speed
    });
  }

  async extrudeFilament(amount: number, speed?: number): Promise<void> {
    await this.client.post('/api/printer/tool', {
      command: 'extrude',
      amount,
      speed
    });
  }

  async retractFilament(amount: number, speed?: number): Promise<void> {
    await this.client.post('/api/printer/tool', {
      command: 'extrude',
      amount: -amount,
      speed
    });
  }

  async sendGCode(commands: string | string[]): Promise<void> {
    const commandArray = Array.isArray(commands) ? commands : [commands];
    
    await this.client.post('/api/printer/command', {
      commands: commandArray
    });
  }

  // Files API
  async getFiles(location: 'local' | 'sdcard' = 'local', recursive = false): Promise<{ files: OctoPrintFile[] }> {
    const response = await this.client.get<{ files: OctoPrintFile[] }>('/api/files', {
      params: { recursive }
    });
    return response.data;
  }

  async getFile(location: 'local' | 'sdcard', path: string): Promise<OctoPrintFile> {
    const response = await this.client.get<OctoPrintFile>(`/api/files/${location}/${path}`);
    return response.data;
  }

  async uploadFile(file: Buffer | Blob, filename: string, path = '', select = false, print = false): Promise<{ files: { local: OctoPrintFile } }> {
    const formData = new FormData();
    formData.append('file', file, filename);
    formData.append('path', path);
    if (select) formData.append('select', 'true');
    if (print) formData.append('print', 'true');

    const response = await this.client.post<{ files: { local: OctoPrintFile } }>('/api/files/local', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });

    return response.data;
  }

  async selectFile(location: 'local' | 'sdcard', path: string, print = false): Promise<void> {
    await this.client.post(`/api/files/${location}/${path}`, {
      command: 'select',
      print
    });
  }

  async deleteFile(location: 'local' | 'sdcard', path: string): Promise<void> {
    await this.client.delete(`/api/files/${location}/${path}`);
  }

  // Settings API
  async getSettings(): Promise<OctoPrintSettings> {
    const response = await this.client.get<OctoPrintSettings>('/api/settings');
    return response.data;
  }

  async updateSettings(settings: Partial<OctoPrintSettings>): Promise<void> {
    await this.client.post('/api/settings', settings);
  }

  // System API
  async getSystemInfo(): Promise<OctoPrintSystemInfo> {
    const response = await this.client.get<OctoPrintSystemInfo>('/api/system');
    return response.data;
  }

  async getVersion(): Promise<{ api: string; server: string; text: string }> {
    const response = await this.client.get('/api/version');
    return response.data;
  }

  async restartOctoPrint(): Promise<void> {
    await this.client.post('/api/system/commands/core/restart');
  }

  async shutdownOctoPrint(): Promise<void> {
    await this.client.post('/api/system/commands/core/shutdown');
  }

  // Timelapse API
  async getTimelapseConfig(): Promise<OctoPrintTimelapse> {
    const response = await this.client.get<OctoPrintTimelapse>('/api/timelapse');
    return response.data;
  }

  async updateTimelapseConfig(config: Partial<OctoPrintTimelapse['config']>): Promise<void> {
    await this.client.post('/api/timelapse', config);
  }

  async getTimelapseFiles(): Promise<OctoPrintTimelapse['files']> {
    const response = await this.client.get<OctoPrintTimelapse>('/api/timelapse');
    return response.data.files;
  }

  async deleteTimelapse(filename: string): Promise<void> {
    await this.client.delete(`/api/timelapse/${filename}`);
  }

  // Plugin API
  async getPlugins(): Promise<any> {
    const response = await this.client.get('/api/plugin/pluginmanager');
    return response.data;
  }

  async enablePlugin(pluginKey: string): Promise<void> {
    await this.client.post(`/api/plugin/pluginmanager`, {
      command: 'enable',
      plugin: pluginKey
    });
  }

  async disablePlugin(pluginKey: string): Promise<void> {
    await this.client.post(`/api/plugin/pluginmanager`, {
      command: 'disable',
      plugin: pluginKey
    });
  }

  // Utility methods
  async isOnline(): Promise<boolean> {
    try {
      await this.getVersion();
      return true;
    } catch {
      return false;
    }
  }

  async waitForJobCompletion(checkInterval = 5000): Promise<void> {
    return new Promise((resolve, reject) => {
      const checkJob = async () => {
        try {
          const job = await this.getJobStatus();
          
          if (job.state === 'Operational' || job.state === 'Finished') {
            resolve();
          } else if (job.state === 'Error' || job.state === 'Cancelled') {
            reject(new Error(`Job failed with state: ${job.state}`));
          } else {
            setTimeout(checkJob, checkInterval);
          }
        } catch (error) {
          reject(error);
        }
      };

      checkJob();
    });
  }

  async getSnapshot(): Promise<Buffer> {
    const settings = await this.getSettings();
    const snapshotUrl = settings.webcam.snapshotUrl;
    
    if (!snapshotUrl) {
      throw new Error('Webcam snapshot URL not configured');
    }

    const response = await axios.get(snapshotUrl, {
      responseType: 'arraybuffer',
      timeout: 10000
    });

    return Buffer.from(response.data);
  }

  getStreamUrl(): string | null {
    // This would need to be called after getting settings
    return null;
  }

  // Batch operations
  async executeBatch(operations: Array<() => Promise<any>>): Promise<any[]> {
    const results: any[] = [];
    
    for (const operation of operations) {
      try {
        const result = await operation();
        results.push({ success: true, result });
      } catch (error) {
        results.push({ success: false, error });
      }
    }

    return results;
  }
}

export class OctoPrintFleetManager extends EventEmitter {
  private clients: Map<string, OctoPrintClient> = new Map();

  addPrinter(printerId: string, config: OctoPrintConfig): OctoPrintClient {
    const client = new OctoPrintClient(config);
    
    // Forward events with printer ID
    client.on('connected', () => this.emit('printerConnected', printerId));
    client.on('disconnected', () => this.emit('printerDisconnected', printerId));
    client.on('printingStarted', (data) => this.emit('printingStarted', printerId, data));
    client.on('printerReady', (data) => this.emit('printerReady', printerId, data));
    client.on('progressUpdate', (data) => this.emit('progressUpdate', printerId, data));
    client.on('temperatureUpdate', (data) => this.emit('temperatureUpdate', printerId, data));
    client.on('connectionError', (error) => this.emit('connectionError', printerId, error));

    this.clients.set(printerId, client);
    return client;
  }

  removePrinter(printerId: string): boolean {
    const client = this.clients.get(printerId);
    if (client) {
      client.disconnect();
      this.clients.delete(printerId);
      return true;
    }
    return false;
  }

  getClient(printerId: string): OctoPrintClient | undefined {
    return this.clients.get(printerId);
  }

  getAllClients(): Map<string, OctoPrintClient> {
    return this.clients;
  }

  async connectAll(): Promise<void> {
    const promises = Array.from(this.clients.values()).map(client => 
      client.connect().catch(error => ({ error }))
    );
    
    await Promise.all(promises);
  }

  async disconnectAll(): Promise<void> {
    const promises = Array.from(this.clients.values()).map(client => client.disconnect());
    await Promise.all(promises);
  }

  async getFleetStatus(): Promise<Map<string, any>> {
    const statuses = new Map();
    
    for (const [printerId, client] of this.clients) {
      try {
        const [job, printer, connection] = await Promise.all([
          client.getJobStatus(),
          client.getPrinterStatus(),
          client.getConnectionStatus()
        ]);
        
        statuses.set(printerId, {
          online: true,
          job,
          printer,
          connection
        });
      } catch (error) {
        statuses.set(printerId, {
          online: false,
          error: error.message
        });
      }
    }

    return statuses;
  }
}

export const octoprintFleet = new OctoPrintFleetManager();