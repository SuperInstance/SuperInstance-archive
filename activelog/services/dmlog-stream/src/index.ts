import express from 'express';
import { createServer } from 'http';
import { Server as SocketIOServer } from 'socket.io';
import OBSWebSocket from 'obs-websocket-js';
import * as path from 'path';

// Import all our streaming components
import { OverlayGenerator } from './overlays/OverlayGenerator';
import { ViewerDiceSystem } from './interaction/ViewerDiceSystem';
import { PollSystem } from './interaction/PollSystem';
import { CharacterShowcase } from './showcase/CharacterShowcase';
import { CameraSwitcher } from './automation/CameraSwitcher';
import { ClipGenerator } from './highlights/ClipGenerator';
import { EngagementTracker } from './analytics/EngagementTracker';
import { DonationEffects } from './effects/DonationEffects';
import { CampaignProgress } from './overlays/CampaignProgress';
import { AutoPoster } from './social/AutoPoster';
import { VODChapterGenerator } from './processing/VODChapterGenerator';
import { BattleRecapGenerator } from './recap/BattleRecapGenerator';

import { 
  StreamSession, 
  StreamSettings, 
  InteractionSettings,
  AutomationSettings,
  StreamConfig 
} from './types';

export class DMLogStreamService {
  private app: express.Application;
  private server: any;
  private io: SocketIOServer;
  private obs: OBSWebSocket;
  
  // Core components
  private overlayGenerator: OverlayGenerator;
  private diceSystem: ViewerDiceSystem;
  private pollSystem: PollSystem;
  private characterShowcase: CharacterShowcase;
  private cameraSwitcher: CameraSwitcher;
  private clipGenerator: ClipGenerator;
  private engagementTracker: EngagementTracker;
  private donationEffects: DonationEffects;
  private campaignProgress: CampaignProgress;
  private autoSocial: AutoPoster;
  private vodChapters: VODChapterGenerator;
  private battleRecap: BattleRecapGenerator;
  
  // State
  private currentSession: StreamSession | null = null;
  private isStreaming: boolean = false;
  private config: StreamConfig;
  
  constructor(config: StreamConfig) {
    this.config = config;
    this.app = express();
    this.server = createServer(this.app);
    this.io = new SocketIOServer(this.server, {
      cors: {
        origin: config.server.cors.origins,
        methods: ['GET', 'POST']
      }
    });
    
    this.obs = new OBSWebSocket();
    this.initializeComponents();
    this.setupRoutes();
    this.setupSocketHandlers();
  }

  private initializeComponents(): void {
    // Initialize all streaming components
    const dataPath = path.join(__dirname, '../data');
    const overlaysPath = path.join(__dirname, '../overlays');
    const recordingsPath = path.join(__dirname, '../recordings');
    const clipsPath = path.join(__dirname, '../clips');
    const soundsPath = path.join(__dirname, '../sounds');
    
    // Default settings
    const defaultInteractionSettings: InteractionSettings = {
      viewerDice: {
        enabled: true,
        cooldown: 30,
        maxRolls: 50,
        allowedDice: ['d20', 'd12', 'd10', 'd8', 'd6', 'd4']
      },
      polls: {
        enabled: true,
        duration: 60,
        showResults: true,
        requireSubscription: false
      },
      donations: {
        enabled: true,
        effects: [],
        minimumAmount: 1,
        showDonorName: true
      }
    };

    const defaultAutomationSettings: AutomationSettings = {
      cameraSwitching: {
        enabled: true,
        mode: 'scene-based',
        scenes: []
      },
      socialPosting: {
        enabled: false,
        platforms: [],
        templates: []
      },
      vodProcessing: {
        enabled: true,
        autoChapters: true,
        highlightDetection: true,
        uploadToYoutube: false
      }
    };

    // Core overlay system
    this.overlayGenerator = new OverlayGenerator(overlaysPath);
    
    // Interaction systems
    this.diceSystem = new ViewerDiceSystem(defaultInteractionSettings);
    this.pollSystem = new PollSystem(defaultInteractionSettings);
    
    // Showcase and automation
    this.characterShowcase = new CharacterShowcase(this.overlayGenerator);
    this.cameraSwitcher = new CameraSwitcher(this.obs, defaultAutomationSettings);
    
    // Content generation
    this.clipGenerator = new ClipGenerator(recordingsPath, clipsPath);
    this.engagementTracker = new EngagementTracker(dataPath);
    
    // Effects and overlays
    this.donationEffects = new DonationEffects(this.obs, this.overlayGenerator, soundsPath, this.cameraSwitcher);
    this.campaignProgress = new CampaignProgress(this.overlayGenerator, dataPath);
    
    // Social and processing
    this.autoSocial = new AutoPoster(defaultAutomationSettings, dataPath);
    this.vodChapters = new VODChapterGenerator(clipsPath);
    this.battleRecap = new BattleRecapGenerator(clipsPath);
  }

  private setupRoutes(): void {
    this.app.use(express.json());
    this.app.use(express.static(path.join(__dirname, '../public')));
    
    // Health check
    this.app.get('/health', (req, res) => {
      res.json({ 
        status: 'healthy',
        isStreaming: this.isStreaming,
        session: this.currentSession?.title || 'No active session'
      });
    });

    // Session management
    this.app.post('/session/start', async (req, res) => {
      try {
        const session: StreamSession = req.body;
        await this.startSession(session);
        res.json({ success: true, session: this.currentSession });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/session/end', async (req, res) => {
      try {
        await this.endSession();
        res.json({ success: true });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    // Dice rolls
    this.app.post('/dice/roll', async (req, res) => {
      try {
        const { userId, username, notation, context } = req.body;
        const result = await this.diceSystem.rollDice(userId, username, notation, context);
        res.json({ success: true, result });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    // Polls
    this.app.post('/poll/create', async (req, res) => {
      try {
        const { question, options, duration, createdBy } = req.body;
        const poll = await this.pollSystem.createPoll({ question, options, duration }, createdBy);
        res.json({ success: true, poll });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.get('/poll/active', (req, res) => {
      const activePoll = this.pollSystem.getActivePoll();
      res.json({ success: true, poll: activePoll });
    });

    // Character showcase
    this.app.post('/character/showcase', async (req, res) => {
      try {
        const { character, duration } = req.body;
        await this.characterShowcase.showcaseCharacter(character, duration);
        res.json({ success: true });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    // Camera switching
    this.app.post('/camera/scene/:sceneId', async (req, res) => {
      try {
        const { sceneId } = req.params;
        await this.cameraSwitcher.manualSwitchToScene(sceneId);
        res.json({ success: true });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.get('/camera/scenes', (req, res) => {
      const scenes = this.cameraSwitcher.getAvailableScenes();
      res.json({ success: true, scenes });
    });

    // Analytics
    this.app.get('/analytics/engagement', (req, res) => {
      const stats = this.engagementTracker.generateStats();
      res.json({ success: true, stats });
    });

    this.app.get('/analytics/poll', (req, res) => {
      const stats = this.pollSystem.getPollStatistics();
      res.json({ success: true, stats });
    });

    // Campaign progress
    this.app.post('/campaign/progress/show', async (req, res) => {
      try {
        const { duration } = req.body;
        await this.campaignProgress.showProgressOverlay(duration);
        res.json({ success: true });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.get('/campaign/progress/summary', (req, res) => {
      const summary = this.campaignProgress.getProgressSummary();
      res.json({ success: true, summary });
    });

    // Battle system
    this.app.post('/battle/start', async (req, res) => {
      try {
        const { title, description, participants } = req.body;
        const battle = this.battleRecap.startBattle(title, description, participants);
        res.json({ success: true, battle });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/battle/action', (req, res) => {
      try {
        const { actor, type, description, target, damage, healing } = req.body;
        const action = this.battleRecap.addBattleAction(actor, type, description, target, undefined, damage, healing);
        res.json({ success: true, action });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/battle/end', async (req, res) => {
      try {
        const { result } = req.body;
        const battle = this.battleRecap.endBattle(result);
        if (battle) {
          // Generate battle recap video
          const videoPath = await this.battleRecap.generateBattleRecapVideo(battle);
          res.json({ success: true, battle, videoPath });
        } else {
          res.json({ success: false, error: 'No active battle' });
        }
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });
  }

  private setupSocketHandlers(): void {
    this.io.on('connection', (socket) => {
      console.log('🔗 Client connected:', socket.id);
      
      // Send current state
      socket.emit('session-state', {
        isStreaming: this.isStreaming,
        session: this.currentSession
      });

      // Dice roll events
      socket.on('dice-roll', async (data) => {
        try {
          const result = await this.diceSystem.rollDice(data.userId, data.username, data.notation, data.context);
          this.io.emit('dice-rolled', result);
        } catch (error) {
          socket.emit('error', { message: (error as Error).message });
        }
      });

      // Poll vote events
      socket.on('poll-vote', (data) => {
        // This would be handled by the poll system
        this.io.emit('poll-updated', this.pollSystem.getActivePoll());
      });

      // Chat events (for engagement tracking)
      socket.on('chat-message', (data) => {
        this.engagementTracker.trackChatMessage(data.userId, data.username, data.message, data.metadata);
      });

      socket.on('disconnect', () => {
        console.log('🔌 Client disconnected:', socket.id);
      });
    });
  }

  public async initialize(): Promise<void> {
    console.log('🚀 Initializing DMLog Stream Service...');
    
    try {
      // Initialize OBS connection
      await this.connectToOBS();
      
      // Initialize all components
      await Promise.all([
        this.overlayGenerator.initialize(),
        this.diceSystem.initialize(null), // Would need Twitch client
        this.pollSystem.initialize(null), // Would need Twitch client
        this.characterShowcase.initialize(),
        this.cameraSwitcher.initialize(),
        this.clipGenerator.initialize(),
        this.engagementTracker.initialize(),
        this.campaignProgress.initialize(),
        this.autoSocial.initialize(),
        this.vodChapters.initialize(),
        this.battleRecap.initialize()
      ]);

      // Setup component event listeners
      this.setupEventListeners();
      
      console.log('✅ DMLog Stream Service initialized successfully');
      
    } catch (error) {
      console.error('❌ Failed to initialize DMLog Stream Service:', error);
      throw error;
    }
  }

  private async connectToOBS(): Promise<void> {
    try {
      await this.obs.connect(
        `ws://${this.config.obs.host}:${this.config.obs.port}`,
        this.config.obs.password
      );
      console.log('🎥 Connected to OBS Studio');
    } catch (error) {
      console.warn('⚠️  Could not connect to OBS Studio:', error);
      // Continue without OBS - some features will be limited
    }
  }

  private setupEventListeners(): void {
    // Dice system events
    this.diceSystem.on('dice-rolled', (roll) => {
      this.io.emit('dice-rolled', roll);
      this.engagementTracker.trackDiceRoll(roll);
      
      // Generate highlight for critical hits/fumbles
      if (roll.result.critical || roll.result.fumble) {
        this.clipGenerator.createDiceRollHighlight(roll);
      }
    });

    // Poll system events
    this.pollSystem.on('poll-created', (poll) => {
      this.io.emit('poll-created', poll);
    });

    this.pollSystem.on('vote-cast', (data) => {
      this.io.emit('poll-updated', data.poll);
      this.engagementTracker.trackPollVote(data.voter.userId, data.voter.username, data.poll.id, data.option);
    });

    this.pollSystem.on('poll-ended', (poll) => {
      this.io.emit('poll-ended', poll);
    });

    // Character showcase events
    this.characterShowcase.on('showcase-started', (data) => {
      this.io.emit('character-showcase', data);
    });

    // Camera switching events
    this.cameraSwitcher.on('scene-changed', (data) => {
      this.io.emit('scene-changed', data);
    });

    // Engagement tracking events
    this.engagementTracker.on('milestone-achieved', (milestone) => {
      this.io.emit('engagement-milestone', milestone);
    });

    // Campaign progress events
    this.campaignProgress.on('milestone-achieved', (milestone) => {
      this.io.emit('campaign-milestone', milestone);
      // Auto-post significant milestones to social media
      if (milestone.type === 'level' || milestone.type === 'story') {
        this.autoSocial.onMilestoneAchieved(milestone, 'Current Campaign');
      }
    });

    // Battle recap events
    this.battleRecap.on('battle-started', (battle) => {
      this.io.emit('battle-started', battle);
      this.cameraSwitcher.triggerCombatMode();
    });

    this.battleRecap.on('battle-action', (action) => {
      this.io.emit('battle-action', action);
    });

    this.battleRecap.on('battle-ended', (battle) => {
      this.io.emit('battle-ended', battle);
      this.campaignProgress.updateCharacterLevels([]); // Would need actual character data
    });

    // Clip generation events
    this.clipGenerator.on('clip-ready', (highlight) => {
      this.io.emit('clip-ready', highlight);
    });
  }

  public async startSession(session: StreamSession): Promise<void> {
    if (this.isStreaming) {
      throw new Error('A session is already active');
    }

    this.currentSession = session;
    this.isStreaming = true;

    // Start all session-dependent services
    this.engagementTracker.startSession(session);
    this.clipGenerator.startSession(session);
    this.vodChapters.startSession(session);

    // Post to social media
    if (session.settings.automation.socialPosting.enabled) {
      await this.autoSocial.onSessionStart(session);
    }

    console.log(`🎬 Session started: ${session.title}`);
    this.io.emit('session-started', session);
  }

  public async endSession(): Promise<void> {
    if (!this.isStreaming || !this.currentSession) {
      throw new Error('No active session to end');
    }

    // Generate final analytics
    const finalStats = await this.engagementTracker.endSession();
    
    // Generate chapters for VOD
    const chapters = await this.vodChapters.generateChapters();
    const vodMetadata = await this.vodChapters.generateVODMetadata();
    
    // Stop clip generation
    this.clipGenerator.stopSession();
    
    // Generate session highlights
    const highlights = await this.clipGenerator.generateSessionHighlights();
    
    // Post session end to social media
    if (this.currentSession.settings.automation.socialPosting.enabled) {
      await this.autoSocial.onSessionEnd(this.currentSession, {
        duration: finalStats.averageSessionTime * finalStats.totalViewers / 60, // Approximate
        highlightCount: highlights.length,
        peakViewers: finalStats.totalViewers,
        sessionSummary: 'An epic session with amazing moments!',
        highlights
      });
    }

    const endedSession = this.currentSession;
    this.currentSession = null;
    this.isStreaming = false;

    console.log(`🎬 Session ended: ${endedSession.title}`);
    this.io.emit('session-ended', {
      session: endedSession,
      stats: finalStats,
      chapters,
      highlights,
      vodMetadata
    });
  }

  public async start(): Promise<void> {
    await this.initialize();
    
    this.server.listen(this.config.server.port, this.config.server.host, () => {
      console.log(`🌟 DMLog Stream Service running on http://${this.config.server.host}:${this.config.server.port}`);
      console.log('📺 Ready for streaming!');
    });
  }

  public async shutdown(): Promise<void> {
    console.log('🛑 Shutting down DMLog Stream Service...');
    
    if (this.isStreaming) {
      await this.endSession();
    }

    // Shutdown all components
    await Promise.all([
      this.engagementTracker.shutdown(),
      this.campaignProgress.shutdown(),
      this.autoSocial.shutdown(),
      this.donationEffects.shutdown(),
      this.battleRecap.shutdown()
    ]);

    // Disconnect from OBS
    if (this.obs.identified) {
      await this.obs.disconnect();
    }

    this.server.close();
    console.log('✅ DMLog Stream Service shut down');
  }

  // Getters for component access
  public getOverlayGenerator(): OverlayGenerator { return this.overlayGenerator; }
  public getDiceSystem(): ViewerDiceSystem { return this.diceSystem; }
  public getPollSystem(): PollSystem { return this.pollSystem; }
  public getCharacterShowcase(): CharacterShowcase { return this.characterShowcase; }
  public getCameraSwitcher(): CameraSwitcher { return this.cameraSwitcher; }
  public getClipGenerator(): ClipGenerator { return this.clipGenerator; }
  public getEngagementTracker(): EngagementTracker { return this.engagementTracker; }
  public getDonationEffects(): DonationEffects { return this.donationEffects; }
  public getCampaignProgress(): CampaignProgress { return this.campaignProgress; }
  public getAutoSocial(): AutoPoster { return this.autoSocial; }
  public getVODChapters(): VODChapterGenerator { return this.vodChapters; }
  public getBattleRecap(): BattleRecapGenerator { return this.battleRecap; }
  public getCurrentSession(): StreamSession | null { return this.currentSession; }
  public isStreamingActive(): boolean { return this.isStreaming; }
}

// Export main service class and types
export * from './types';
export { DMLogStreamService };

// Default configuration
const defaultConfig: StreamConfig = {
  server: {
    port: 3000,
    host: '0.0.0.0',
    cors: {
      origins: ['http://localhost:3000', 'http://localhost:8080']
    }
  },
  obs: {
    host: 'localhost',
    port: 4455,
    password: '',
    reconnectDelay: 5000
  },
  twitch: {
    clientId: process.env.TWITCH_CLIENT_ID || '',
    clientSecret: process.env.TWITCH_CLIENT_SECRET || '',
    redirectUri: 'http://localhost:3000/auth/twitch/callback',
    scopes: ['chat:read', 'chat:edit', 'channel:read:subscriptions']
  },
  youtube: {
    apiKey: process.env.YOUTUBE_API_KEY || '',
    clientId: process.env.YOUTUBE_CLIENT_ID || '',
    clientSecret: process.env.YOUTUBE_CLIENT_SECRET || ''
  },
  database: {
    type: 'sqlite',
    database: './data/dmlog.db'
  },
  storage: {
    type: 'local',
    path: './data/storage'
  },
  ffmpeg: {
    path: 'ffmpeg',
    outputPath: './output',
    quality: 'high'
  }
};

// Start service if run directly
if (require.main === module) {
  const service = new DMLogStreamService(defaultConfig);
  
  process.on('SIGINT', async () => {
    console.log('\n🛑 Received SIGINT, shutting down gracefully...');
    await service.shutdown();
    process.exit(0);
  });

  process.on('SIGTERM', async () => {
    console.log('\n🛑 Received SIGTERM, shutting down gracefully...');
    await service.shutdown();
    process.exit(0);
  });

  service.start().catch(error => {
    console.error('❌ Failed to start service:', error);
    process.exit(1);
  });
}