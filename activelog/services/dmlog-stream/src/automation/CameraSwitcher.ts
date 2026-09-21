import { EventEmitter } from 'events';
import OBSWebSocket from 'obs-websocket-js';
import { CameraScene, SceneTrigger, AutomationSettings, SessionEvent } from '../types';

export class CameraSwitcher extends EventEmitter {
  private obs: OBSWebSocket;
  private scenes: Map<string, CameraScene> = new Map();
  private currentScene: string | null = null;
  private isAutoMode: boolean = true;
  private settings: AutomationSettings;
  private eventQueue: SessionEvent[] = [];
  private sceneTimer: NodeJS.Timeout | null = null;
  private fadeDuration: number = 1000;

  constructor(obs: OBSWebSocket, settings: AutomationSettings) {
    super();
    this.obs = obs;
    this.settings = settings;
    this.setupDefaultScenes();
  }

  private setupDefaultScenes(): void {
    const defaultScenes: CameraScene[] = [
      {
        id: 'overview',
        name: 'Overview Shot',
        description: 'Wide shot showing all players',
        obsSceneName: 'Overview',
        triggers: [
          { type: 'roleplay', priority: 1 },
          { type: 'exploration', priority: 1 }
        ],
        duration: 30000
      },
      {
        id: 'dm_close',
        name: 'DM Close-up',
        description: 'Close shot of the DM for narration',
        obsSceneName: 'DM_Closeup',
        triggers: [
          { type: 'roleplay', priority: 2, condition: 'narrator' },
          { type: 'exploration', priority: 2, condition: 'description' }
        ],
        duration: 15000
      },
      {
        id: 'combat',
        name: 'Combat Overview',
        description: 'Battle map and initiative tracker focus',
        obsSceneName: 'Combat_Map',
        triggers: [
          { type: 'combat', priority: 5 }
        ],
        duration: 60000
      },
      {
        id: 'dice_focus',
        name: 'Dice Rolling Focus',
        description: 'Close-up on dice rolling area',
        obsSceneName: 'Dice_Focus',
        triggers: [
          { type: 'dice_roll', priority: 3 }
        ],
        duration: 5000
      },
      {
        id: 'player_focus',
        name: 'Player Spotlight',
        description: 'Individual player focus for character moments',
        obsSceneName: 'Player_Spotlight',
        triggers: [
          { type: 'roleplay', priority: 4, condition: 'character_moment' },
          { type: 'dice_roll', priority: 2, condition: 'important_roll' }
        ],
        duration: 10000
      },
      {
        id: 'donation_cam',
        name: 'Donation Reaction',
        description: 'DM reaction cam for donations',
        obsSceneName: 'DM_Reaction',
        triggers: [
          { type: 'donation', priority: 10 }
        ],
        duration: 8000
      }
    ];

    defaultScenes.forEach(scene => {
      this.scenes.set(scene.id, scene);
    });
  }

  public async initialize(): Promise<void> {
    try {
      // Verify OBS scenes exist
      const { scenes } = await this.obs.call('GetSceneList');
      const obsSceneNames = scenes.map((s: any) => s.sceneName);
      
      for (const [id, scene] of this.scenes) {
        if (!obsSceneNames.includes(scene.obsSceneName)) {
          console.warn(`⚠️  OBS Scene '${scene.obsSceneName}' not found for camera scene '${id}'`);
          // Create basic scene if it doesn't exist
          await this.createBasicScene(scene.obsSceneName);
        }
      }

      console.log('🎥 Camera switching system initialized');
      this.emit('initialized');
    } catch (error) {
      console.error('Error initializing camera switcher:', error);
      throw error;
    }
  }

  private async createBasicScene(sceneName: string): Promise<void> {
    try {
      await this.obs.call('CreateScene', { sceneName });
      console.log(`✅ Created basic OBS scene: ${sceneName}`);
    } catch (error) {
      console.error(`Failed to create scene ${sceneName}:`, error);
    }
  }

  public async handleEvent(event: SessionEvent): Promise<void> {
    if (!this.settings.cameraSwitching.enabled || !this.isAutoMode) {
      return;
    }

    this.eventQueue.push(event);
    await this.evaluateSceneChange(event);
  }

  private async evaluateSceneChange(event: SessionEvent): Promise<void> {
    const matchingScenes = this.findMatchingScenes(event);
    
    if (matchingScenes.length === 0) {
      return;
    }

    // Sort by priority (higher number = higher priority)
    matchingScenes.sort((a, b) => b.priority - a.priority);
    const bestMatch = matchingScenes[0];
    
    const targetScene = this.scenes.get(bestMatch.sceneId);
    if (!targetScene) {
      return;
    }

    // Check if we should switch scenes
    if (this.shouldSwitchScene(targetScene, event)) {
      await this.switchToScene(targetScene, event);
    }
  }

  private findMatchingScenes(event: SessionEvent): Array<{sceneId: string, priority: number}> {
    const matches: Array<{sceneId: string, priority: number}> = [];
    
    for (const [sceneId, scene] of this.scenes) {
      for (const trigger of scene.triggers) {
        if (this.triggerMatches(trigger, event)) {
          matches.push({ sceneId, priority: trigger.priority });
        }
      }
    }

    return matches;
  }

  private triggerMatches(trigger: SceneTrigger, event: SessionEvent): boolean {
    // Type must match
    if (trigger.type !== event.type) {
      return false;
    }

    // Check condition if specified
    if (trigger.condition) {
      return this.evaluateCondition(trigger.condition, event);
    }

    return true;
  }

  private evaluateCondition(condition: string, event: SessionEvent): boolean {
    switch (condition) {
      case 'narrator':
        return event.description.toLowerCase().includes('narrator') ||
               event.description.toLowerCase().includes('describes') ||
               event.title.toLowerCase().includes('narration');
      
      case 'description':
        return event.description.length > 100; // Long descriptions get DM focus
      
      case 'character_moment':
        return event.participants.length === 1 && // Single participant
               (event.description.toLowerCase().includes('speaks') ||
                event.description.toLowerCase().includes('says') ||
                event.description.toLowerCase().includes('reacts'));
      
      case 'important_roll':
        return event.description.toLowerCase().includes('critical') ||
               event.description.toLowerCase().includes('saving throw') ||
               event.description.toLowerCase().includes('death save');
      
      default:
        return false;
    }
  }

  private shouldSwitchScene(targetScene: CameraScene, event: SessionEvent): boolean {
    // Always switch for high-priority events
    const highPriorityTypes = ['donation', 'combat'];
    if (highPriorityTypes.includes(event.type)) {
      return true;
    }

    // Don't switch too frequently
    if (this.sceneTimer) {
      const remainingTime = this.getRemainingSceneTime();
      if (remainingTime > 3000) { // At least 3 seconds left
        return false;
      }
    }

    // Don't switch to the same scene
    if (this.currentScene === targetScene.obsSceneName) {
      return false;
    }

    return true;
  }

  private getRemainingSceneTime(): number {
    // This would need to track when the current scene started
    // For now, return 0 to allow switches
    return 0;
  }

  public async switchToScene(scene: CameraScene, event?: SessionEvent): Promise<void> {
    try {
      // Clear existing timer
      if (this.sceneTimer) {
        clearTimeout(this.sceneTimer);
        this.sceneTimer = null;
      }

      // Perform the scene transition
      await this.performSceneTransition(scene.obsSceneName);
      
      this.currentScene = scene.obsSceneName;
      
      // Set timer for scene duration if specified
      if (scene.duration && scene.duration > 0) {
        this.sceneTimer = setTimeout(() => {
          this.returnToDefaultScene();
        }, scene.duration);
      }

      console.log(`🎥 Switched to scene: ${scene.name} (${scene.obsSceneName})`);
      
      this.emit('scene-changed', {
        scene,
        previousScene: this.currentScene,
        event,
        timestamp: new Date()
      });

    } catch (error) {
      console.error('Error switching scene:', error);
    }
  }

  private async performSceneTransition(sceneName: string): Promise<void> {
    try {
      // Get current scene for transition
      const { currentProgramSceneName } = await this.obs.call('GetCurrentProgramScene');
      
      if (currentProgramSceneName === sceneName) {
        return; // Already on target scene
      }

      // Apply transition if fade is enabled
      if (this.fadeDuration > 0) {
        await this.obs.call('SetCurrentSceneTransition', {
          transitionName: 'Fade'
        });
        
        await this.obs.call('SetCurrentSceneTransitionDuration', {
          transitionDuration: this.fadeDuration
        });
      }

      // Switch scene
      await this.obs.call('SetCurrentProgramScene', {
        sceneName
      });

    } catch (error) {
      console.error('Error performing scene transition:', error);
      throw error;
    }
  }

  private async returnToDefaultScene(): Promise<void> {
    const defaultScene = this.scenes.get('overview');
    if (defaultScene && this.currentScene !== defaultScene.obsSceneName) {
      await this.switchToScene(defaultScene);
    }
  }

  // Manual control methods
  public async manualSwitchToScene(sceneId: string): Promise<void> {
    const scene = this.scenes.get(sceneId);
    if (!scene) {
      throw new Error(`Scene not found: ${sceneId}`);
    }

    const wasAutoMode = this.isAutoMode;
    this.isAutoMode = false; // Temporarily disable auto mode
    
    await this.switchToScene(scene);
    
    // Re-enable auto mode after a delay
    setTimeout(() => {
      this.isAutoMode = wasAutoMode;
    }, 10000);
  }

  public setAutoMode(enabled: boolean): void {
    this.isAutoMode = enabled;
    console.log(`🎥 Auto camera switching: ${enabled ? 'enabled' : 'disabled'}`);
    this.emit('auto-mode-changed', enabled);
  }

  public addCustomScene(scene: CameraScene): void {
    this.scenes.set(scene.id, scene);
    console.log(`➕ Added custom camera scene: ${scene.name}`);
  }

  public removeScene(sceneId: string): void {
    if (this.scenes.has(sceneId)) {
      this.scenes.delete(sceneId);
      console.log(`➖ Removed camera scene: ${sceneId}`);
    }
  }

  public async createScenePreset(name: string, description: string): Promise<string> {
    const { currentProgramSceneName } = await this.obs.call('GetCurrentProgramScene');
    
    const presetId = `preset_${Date.now()}`;
    const preset: CameraScene = {
      id: presetId,
      name,
      description,
      obsSceneName: currentProgramSceneName,
      triggers: [{ type: 'manual', priority: 1 }],
      duration: 30000
    };

    this.scenes.set(presetId, preset);
    return presetId;
  }

  // AI-assisted mode (future enhancement)
  public async enableAIMode(): Promise<void> {
    if (this.settings.cameraSwitching.mode === 'ai-assisted') {
      console.log('🤖 AI-assisted camera switching enabled (placeholder)');
      // This would integrate with an AI service to analyze stream content
      // and make intelligent camera decisions
    }
  }

  // Analytics and insights
  public getSceneStatistics(): any {
    const sceneUsage = new Map<string, number>();
    const totalEvents = this.eventQueue.length;

    // Count scene triggers from event queue
    this.eventQueue.forEach(event => {
      const matches = this.findMatchingScenes(event);
      matches.forEach(match => {
        const count = sceneUsage.get(match.sceneId) || 0;
        sceneUsage.set(match.sceneId, count + 1);
      });
    });

    return {
      totalEvents,
      sceneUsage: Object.fromEntries(sceneUsage),
      currentScene: this.currentScene,
      autoModeEnabled: this.isAutoMode,
      availableScenes: Array.from(this.scenes.values()).map(s => ({
        id: s.id,
        name: s.name,
        obsSceneName: s.obsSceneName
      }))
    };
  }

  public getCurrentScene(): string | null {
    return this.currentScene;
  }

  public getAvailableScenes(): CameraScene[] {
    return Array.from(this.scenes.values());
  }

  public updateSettings(newSettings: AutomationSettings): void {
    this.settings = newSettings;
    this.emit('settings-updated', newSettings);
  }

  // Scene-based triggers for integration with other systems
  public async triggerCombatMode(): Promise<void> {
    const combatScene = this.scenes.get('combat');
    if (combatScene) {
      await this.switchToScene(combatScene);
    }
  }

  public async triggerDiceRollFocus(): Promise<void> {
    const diceScene = this.scenes.get('dice_focus');
    if (diceScene) {
      await this.switchToScene(diceScene);
      // Auto-return after dice roll duration
      setTimeout(() => {
        this.returnToDefaultScene();
      }, 8000);
    }
  }

  public async triggerDonationReaction(): Promise<void> {
    const donationScene = this.scenes.get('donation_cam');
    if (donationScene) {
      await this.switchToScene(donationScene);
    }
  }

  public async triggerPlayerSpotlight(playerName: string): Promise<void> {
    const spotlightScene = this.scenes.get('player_focus');
    if (spotlightScene) {
      await this.switchToScene(spotlightScene);
      console.log(`🎭 Player spotlight: ${playerName}`);
    }
  }
}