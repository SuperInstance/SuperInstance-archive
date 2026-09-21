const { spawn, exec } = require('child_process');
const fs = require('fs').promises;
const path = require('path');
const winston = require('winston');
const WebSocket = require('ws');
const net = require('net');

class UnityConnectorService {
  constructor(config = {}) {
    this.logger = winston.createLogger({
      level: 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
      ),
      transports: [
        new winston.transports.Console(),
        new winston.transports.File({ filename: 'logs/unity-connector.log' })
      ]
    });

    this.unityPath = config.unityPath || process.env.UNITY_PATH || '/Applications/Unity/Hub/Editor/2023.3.0f1/Unity.app/Contents/MacOS/Unity';
    this.projectPath = config.projectPath || './unity-projects/dmlog-realtime';
    this.tcpPort = config.tcpPort || 7777;
    this.wsPort = config.wsPort || 7778;
    this.isInitialized = false;
    this.unityProcess = null;
    this.tcpServer = null;
    this.wsServer = null;
    this.activeConnections = new Map();
    this.sceneInstances = new Map();
    this.realtimeData = new Map();
  }

  async initialize() {
    try {
      this.logger.info('Initializing Unity Connector Service');
      
      await this.checkUnityInstallation();
      await this.setupProject();
      await this.startCommunicationServers();
      await this.launchUnityEditor();
      
      this.isInitialized = true;
      this.logger.info('Unity Connector Service initialized successfully');
      return true;
    } catch (error) {
      this.logger.error('Failed to initialize Unity Connector Service:', error);
      return false;
    }
  }

  async checkUnityInstallation() {
    try {
      const unityExists = await fs.access(this.unityPath).then(() => true).catch(() => false);
      if (!unityExists) {
        this.logger.warn('Unity Editor not found at specified path, using mock mode');
        this.mockMode = true;
        return;
      }
      
      this.logger.info('Unity Editor installation verified');
    } catch (error) {
      this.logger.error('Unity installation check failed:', error);
      throw error;
    }
  }

  async setupProject() {
    try {
      const projectExists = await fs.access(this.projectPath).then(() => true).catch(() => false);
      if (!projectExists) {
        await this.createUnityProject();
      }
      
      await this.setupRealTimeAssets();
      await this.configureNetworking();
      await this.setupSceneTemplates();
      await this.installRequiredPackages();
      
      this.logger.info('Unity project setup completed');
    } catch (error) {
      this.logger.error('Unity project setup failed:', error);
      throw error;
    }
  }

  async createUnityProject() {
    if (this.mockMode) {
      await fs.mkdir(this.projectPath, { recursive: true });
      await this.createMockProjectStructure();
      return;
    }

    return new Promise((resolve, reject) => {
      const createCmd = `"${this.unityPath}" -createProject "${this.projectPath}" -cloneFromTemplate "${path.join(__dirname, '../templates/unity-3d-template')}"`;
      
      exec(createCmd, (error, stdout, stderr) => {
        if (error) {
          this.logger.error('Failed to create Unity project:', error);
          reject(error);
          return;
        }
        
        this.logger.info('Unity project created successfully');
        resolve();
      });
    });
  }

  async createMockProjectStructure() {
    const directories = [
      'Assets',
      'Assets/Scripts',
      'Assets/Scripts/DMLog',
      'Assets/Prefabs',
      'Assets/Prefabs/Characters',
      'Assets/Prefabs/Environments',
      'Assets/Materials',
      'Assets/Textures',
      'Assets/Audio',
      'Assets/Animations',
      'ProjectSettings',
      'Packages'
    ];

    for (const dir of directories) {
      await fs.mkdir(path.join(this.projectPath, dir), { recursive: true });
    }

    await fs.writeFile(
      path.join(this.projectPath, 'Assets/Scripts/DMLog/RealtimeConnector.cs'),
      this.generateRealtimeConnectorScript()
    );

    this.logger.info('Mock Unity project structure created');
  }

  generateRealtimeConnectorScript() {
    return `using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using Newtonsoft.Json;

namespace DMLog.Realtime
{
    public class RealtimeConnector : MonoBehaviour
    {
        [Header("Connection Settings")]
        public string serverHost = "localhost";
        public int serverPort = 7777;
        
        private TcpClient tcpClient;
        private NetworkStream stream;
        private Thread tcpListenerThread;
        private bool isConnected = false;
        
        [Header("Scene Management")]
        public Transform characterContainer;
        public Transform environmentContainer;
        public Transform effectsContainer;
        
        private Dictionary<string, GameObject> activeCharacters = new Dictionary<string, GameObject>();
        private Dictionary<string, GameObject> activeEffects = new Dictionary<string, GameObject>();
        
        void Start()
        {
            ConnectToServer();
        }
        
        void ConnectToServer()
        {
            try
            {
                tcpListenerThread = new Thread(new ThreadStart(ListenForData));
                tcpListenerThread.IsBackground = true;
                tcpListenerThread.Start();
            }
            catch (System.Exception e)
            {
                Debug.LogError("Unity Connector: " + e.Message);
            }
        }
        
        void ListenForData()
        {
            try
            {
                tcpClient = new TcpClient(serverHost, serverPort);
                stream = tcpClient.GetStream();
                isConnected = true;
                
                Byte[] bytes = new Byte[4096];
                while (true)
                {
                    int length = stream.Read(bytes, 0, bytes.Length);
                    if (length != 0)
                    {
                        string incomingData = Encoding.UTF8.GetString(bytes, 0, length);
                        ProcessIncomingData(incomingData);
                    }
                }
            }
            catch (System.Exception e)
            {
                Debug.LogError("Unity TCP Listener: " + e.Message);
            }
        }
        
        void ProcessIncomingData(string data)
        {
            try
            {
                var message = JsonConvert.DeserializeObject<RealtimeMessage>(data);
                
                switch (message.type)
                {
                    case "scene_update":
                        UpdateScene(message.data);
                        break;
                    case "character_action":
                        ProcessCharacterAction(message.data);
                        break;
                    case "environment_change":
                        UpdateEnvironment(message.data);
                        break;
                    case "effect_spawn":
                        SpawnEffect(message.data);
                        break;
                }
            }
            catch (System.Exception e)
            {
                Debug.LogError("Unity Data Processing: " + e.Message);
            }
        }
        
        void UpdateScene(object sceneData)
        {
            // Scene update logic
            Debug.Log("Updating Unity scene with real-time data");
        }
        
        void ProcessCharacterAction(object actionData)
        {
            // Character action processing
            Debug.Log("Processing character action in Unity");
        }
        
        void UpdateEnvironment(object envData)
        {
            // Environment update logic
            Debug.Log("Updating Unity environment");
        }
        
        void SpawnEffect(object effectData)
        {
            // Effect spawning logic
            Debug.Log("Spawning effect in Unity");
        }
        
        void OnDestroy()
        {
            if (tcpListenerThread != null)
            {
                tcpListenerThread.Abort();
            }
            
            if (tcpClient != null)
            {
                tcpClient.Close();
            }
        }
    }
    
    [System.Serializable]
    public class RealtimeMessage
    {
        public string type;
        public object data;
        public long timestamp;
    }
}`;
  }

  async setupRealTimeAssets() {
    const assetsPath = path.join(this.projectPath, 'Assets/DMLog');
    
    this.assetCategories = {
      characters: {
        path: path.join(assetsPath, 'Characters'),
        prefabs: ['Warrior', 'Mage', 'Rogue', 'Cleric', 'Ranger', 'Barbarian']
      },
      environments: {
        path: path.join(assetsPath, 'Environments'),
        scenes: ['Tavern', 'Dungeon', 'Forest', 'Castle', 'Cave', 'Village']
      },
      effects: {
        path: path.join(assetsPath, 'Effects'),
        types: ['Magic', 'Combat', 'Environment', 'UI', 'Particles']
      },
      audio: {
        path: path.join(assetsPath, 'Audio'),
        categories: ['Music', 'SFX', 'Voice', 'Ambient']
      }
    };

    for (const [category, config] of Object.entries(this.assetCategories)) {
      await fs.mkdir(config.path, { recursive: true });
    }
    
    this.logger.info('Real-time assets structure created');
  }

  async configureNetworking() {
    this.networkConfig = {
      maxConnections: 100,
      updateRate: 30,
      compressionEnabled: true,
      encryptionEnabled: false,
      heartbeatInterval: 5000,
      reconnectAttempts: 5
    };
    
    this.logger.info('Networking configuration set');
  }

  async setupSceneTemplates() {
    this.sceneTemplates = {
      tavern: {
        lighting: 'Warm_Indoor',
        atmosphere: 'Cozy',
        props: ['Tables', 'Chairs', 'Bar', 'Fireplace'],
        audio: 'Tavern_Ambient',
        cameraPositions: [
          { name: 'Wide', position: { x: 0, y: 5, z: -10 } },
          { name: 'Close', position: { x: 2, y: 2, z: -5 } }
        ]
      },
      dungeon: {
        lighting: 'Dark_Underground',
        atmosphere: 'Ominous',
        props: ['Torches', 'Chains', 'Bones', 'Treasure'],
        audio: 'Dungeon_Ambient',
        cameraPositions: [
          { name: 'Overhead', position: { x: 0, y: 8, z: 0 } },
          { name: 'FirstPerson', position: { x: 0, y: 1.8, z: 0 } }
        ]
      },
      forest: {
        lighting: 'Natural_Outdoor',
        atmosphere: 'Mystical',
        props: ['Trees', 'Rocks', 'Streams', 'Wildlife'],
        audio: 'Forest_Ambient',
        cameraPositions: [
          { name: 'Canopy', position: { x: 0, y: 12, z: -8 } },
          { name: 'Ground', position: { x: 0, y: 2, z: -6 } }
        ]
      }
    };
    
    this.logger.info('Scene templates configured');
  }

  async installRequiredPackages() {
    const requiredPackages = [
      'com.unity.netcode.gameobjects',
      'com.unity.timeline',
      'com.unity.cinemachine',
      'com.unity.postprocessing',
      'com.unity.addressables',
      'com.unity.animation.rigging'
    ];
    
    if (this.mockMode) {
      this.logger.info('Mock mode: Skipped Unity package installation');
      return;
    }
    
    for (const packageName of requiredPackages) {
      await this.installUnityPackage(packageName);
    }
    
    this.logger.info('Unity packages installed');
  }

  async installUnityPackage(packageName) {
    return new Promise((resolve, reject) => {
      const installCmd = `"${this.unityPath}" -batchmode -quit -projectPath "${this.projectPath}" -importPackage "${packageName}"`;
      
      exec(installCmd, (error, stdout, stderr) => {
        if (error) {
          this.logger.warn(`Failed to install package ${packageName}:`, error.message);
        } else {
          this.logger.info(`Installed Unity package: ${packageName}`);
        }
        resolve();
      });
    });
  }

  async startCommunicationServers() {
    await this.startTCPServer();
    await this.startWebSocketServer();
    
    this.logger.info('Communication servers started');
  }

  async startTCPServer() {
    return new Promise((resolve) => {
      this.tcpServer = net.createServer((socket) => {
        const connectionId = `tcp_${Date.now()}_${Math.random()}`;
        this.activeConnections.set(connectionId, {
          type: 'tcp',
          socket,
          lastHeartbeat: Date.now()
        });
        
        this.logger.info(`Unity TCP connection established: ${connectionId}`);
        
        socket.on('data', (data) => {
          this.handleTCPMessage(connectionId, data);
        });
        
        socket.on('close', () => {
          this.activeConnections.delete(connectionId);
          this.logger.info(`Unity TCP connection closed: ${connectionId}`);
        });
        
        socket.on('error', (error) => {
          this.logger.error(`Unity TCP connection error: ${connectionId}`, error);
          this.activeConnections.delete(connectionId);
        });
      });
      
      this.tcpServer.listen(this.tcpPort, () => {
        this.logger.info(`Unity TCP server listening on port ${this.tcpPort}`);
        resolve();
      });
    });
  }

  async startWebSocketServer() {
    this.wsServer = new WebSocket.Server({ port: this.wsPort });
    
    this.wsServer.on('connection', (ws) => {
      const connectionId = `ws_${Date.now()}_${Math.random()}`;
      this.activeConnections.set(connectionId, {
        type: 'websocket',
        socket: ws,
        lastHeartbeat: Date.now()
      });
      
      this.logger.info(`Unity WebSocket connection established: ${connectionId}`);
      
      ws.on('message', (data) => {
        this.handleWebSocketMessage(connectionId, data);
      });
      
      ws.on('close', () => {
        this.activeConnections.delete(connectionId);
        this.logger.info(`Unity WebSocket connection closed: ${connectionId}`);
      });
      
      ws.on('error', (error) => {
        this.logger.error(`Unity WebSocket connection error: ${connectionId}`, error);
        this.activeConnections.delete(connectionId);
      });
    });
    
    this.logger.info(`Unity WebSocket server listening on port ${this.wsPort}`);
  }

  handleTCPMessage(connectionId, data) {
    try {
      const message = JSON.parse(data.toString());
      this.processUnityMessage(connectionId, message);
    } catch (error) {
      this.logger.error('Invalid TCP message from Unity:', error);
    }
  }

  handleWebSocketMessage(connectionId, data) {
    try {
      const message = JSON.parse(data.toString());
      this.processUnityMessage(connectionId, message);
    } catch (error) {
      this.logger.error('Invalid WebSocket message from Unity:', error);
    }
  }

  processUnityMessage(connectionId, message) {
    switch (message.type) {
      case 'heartbeat':
        this.handleHeartbeat(connectionId);
        break;
      case 'scene_ready':
        this.handleSceneReady(connectionId, message.data);
        break;
      case 'character_update':
        this.handleCharacterUpdate(connectionId, message.data);
        break;
      case 'render_complete':
        this.handleRenderComplete(connectionId, message.data);
        break;
      case 'error':
        this.handleUnityError(connectionId, message.data);
        break;
      default:
        this.logger.warn(`Unknown message type from Unity: ${message.type}`);
    }
  }

  handleHeartbeat(connectionId) {
    const connection = this.activeConnections.get(connectionId);
    if (connection) {
      connection.lastHeartbeat = Date.now();
    }
  }

  handleSceneReady(connectionId, data) {
    this.logger.info(`Unity scene ready: ${data.sceneId}`);
    this.sceneInstances.set(data.sceneId, {
      connectionId,
      status: 'ready',
      timestamp: Date.now()
    });
  }

  handleCharacterUpdate(connectionId, data) {
    this.realtimeData.set(`character_${data.characterId}`, {
      position: data.position,
      rotation: data.rotation,
      animation: data.animation,
      timestamp: Date.now()
    });
  }

  handleRenderComplete(connectionId, data) {
    this.logger.info(`Unity render complete: ${data.sceneId}`);
    this.emit('renderComplete', {
      sceneId: data.sceneId,
      outputPath: data.outputPath,
      connectionId
    });
  }

  handleUnityError(connectionId, error) {
    this.logger.error(`Unity error from ${connectionId}:`, error);
  }

  async launchUnityEditor() {
    if (this.mockMode) {
      this.logger.info('Mock mode: Unity Editor launch simulated');
      return;
    }
    
    return new Promise((resolve, reject) => {
      const launchCmd = `"${this.unityPath}" -projectPath "${this.projectPath}"`;
      
      this.unityProcess = spawn(this.unityPath, ['-projectPath', this.projectPath], {
        detached: true,
        stdio: 'ignore'
      });
      
      this.unityProcess.on('error', (error) => {
        this.logger.error('Failed to launch Unity Editor:', error);
        reject(error);
      });
      
      this.unityProcess.unref();
      
      setTimeout(() => {
        this.logger.info('Unity Editor launched');
        resolve();
      }, 3000);
    });
  }

  async renderRealtimeScene(sceneData) {
    try {
      const sceneId = `unity_${Date.now()}`;
      this.logger.info(`Starting real-time Unity scene render: ${sceneId}`);
      
      if (this.mockMode) {
        return await this.mockRenderRealtimeScene(sceneData, sceneId);
      }
      
      const message = {
        type: 'render_scene',
        sceneId,
        data: {
          template: sceneData.template,
          characters: sceneData.characters,
          environment: sceneData.environment,
          lighting: sceneData.lighting,
          effects: sceneData.effects,
          cameraSettings: sceneData.cameraSettings
        },
        timestamp: Date.now()
      };
      
      await this.broadcastToUnity(message);
      
      return {
        sceneId,
        status: 'rendering',
        estimatedDuration: 5000
      };
    } catch (error) {
      this.logger.error('Real-time scene render failed:', error);
      throw error;
    }
  }

  async mockRenderRealtimeScene(sceneData, sceneId) {
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    return {
      sceneId,
      status: 'rendered',
      outputPath: `/tmp/unity-renders/${sceneId}.mp4`,
      metadata: {
        characters: sceneData.characters?.length || 0,
        template: sceneData.template || 'default',
        renderTime: 1000
      }
    };
  }

  async broadcastToUnity(message) {
    const messageString = JSON.stringify(message);
    let sentCount = 0;
    
    for (const [connectionId, connection] of this.activeConnections.entries()) {
      try {
        if (connection.type === 'tcp') {
          connection.socket.write(messageString + '\n');
        } else if (connection.type === 'websocket') {
          connection.socket.send(messageString);
        }
        sentCount++;
      } catch (error) {
        this.logger.error(`Failed to send message to Unity connection ${connectionId}:`, error);
        this.activeConnections.delete(connectionId);
      }
    }
    
    this.logger.info(`Message broadcast to ${sentCount} Unity connections`);
  }

  async updateRealtimeScene(sceneId, updateData) {
    try {
      const message = {
        type: 'scene_update',
        sceneId,
        data: updateData,
        timestamp: Date.now()
      };
      
      await this.broadcastToUnity(message);
      
      this.logger.info(`Real-time scene update sent: ${sceneId}`);
      
      return {
        sceneId,
        status: 'updated',
        timestamp: Date.now()
      };
    } catch (error) {
      this.logger.error('Real-time scene update failed:', error);
      throw error;
    }
  }

  async getRealtimeData() {
    const data = {};
    
    for (const [key, value] of this.realtimeData.entries()) {
      if (Date.now() - value.timestamp < 30000) {
        data[key] = value;
      }
    }
    
    return data;
  }

  async exportUnityScene(sceneId, format = 'mp4') {
    try {
      const message = {
        type: 'export_scene',
        sceneId,
        data: {
          format,
          quality: 'high',
          resolution: { width: 1920, height: 1080 }
        },
        timestamp: Date.now()
      };
      
      await this.broadcastToUnity(message);
      
      this.logger.info(`Unity scene export requested: ${sceneId}`);
      
      return {
        sceneId,
        status: 'exporting',
        format
      };
    } catch (error) {
      this.logger.error('Unity scene export failed:', error);
      throw error;
    }
  }

  async cleanup() {
    try {
      this.logger.info('Cleaning up Unity Connector Service');
      
      if (this.tcpServer) {
        this.tcpServer.close();
      }
      
      if (this.wsServer) {
        this.wsServer.close();
      }
      
      if (this.unityProcess && !this.unityProcess.killed) {
        this.unityProcess.kill();
      }
      
      this.activeConnections.clear();
      this.sceneInstances.clear();
      this.realtimeData.clear();
      
      this.logger.info('Unity Connector Service cleanup completed');
    } catch (error) {
      this.logger.error('Unity Connector Service cleanup failed:', error);
    }
  }
}

module.exports = UnityConnectorService;