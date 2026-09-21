import { EventEmitter } from 'events';
import OBSWebSocket from 'obs-websocket-js';
import * as path from 'path';
import * as fs from 'fs/promises';
import { Donation, DonationEffect, OverlayElement, ViewerDiceRoll } from '../types';
import { OverlayGenerator } from '../overlays/OverlayGenerator';
import { CameraSwitcher } from '../automation/CameraSwitcher';

export interface EffectContext {
  donation: Donation;
  obs: OBSWebSocket;
  overlayGenerator: OverlayGenerator;
  cameraSwitcher?: CameraSwitcher;
  soundPath?: string;
}

export class DonationEffects extends EventEmitter {
  private obs: OBSWebSocket;
  private overlayGenerator: OverlayGenerator;
  private cameraSwitcher?: CameraSwitcher;
  private effects: Map<string, DonationEffect> = new Map();
  private activeEffects: Map<string, NodeJS.Timeout> = new Map();
  private soundPath: string;
  private effectHistory: Array<{donation: Donation; effects: string[]; timestamp: Date}> = [];

  constructor(
    obs: OBSWebSocket,
    overlayGenerator: OverlayGenerator,
    soundPath: string,
    cameraSwitcher?: CameraSwitcher
  ) {
    super();
    this.obs = obs;
    this.overlayGenerator = overlayGenerator;
    this.soundPath = soundPath;
    this.cameraSwitcher = cameraSwitcher;
    this.setupDefaultEffects();
  }

  private setupDefaultEffects(): void {
    // Sound effects based on donation amount
    this.effects.set('sound_small', {
      type: 'sound',
      trigger: { minAmount: 5 },
      settings: {
        file: 'coin_drop.wav',
        volume: 0.7
      }
    });

    this.effects.set('sound_medium', {
      type: 'sound',
      trigger: { minAmount: 25 },
      settings: {
        file: 'magic_chime.wav',
        volume: 0.8
      }
    });

    this.effects.set('sound_large', {
      type: 'sound',
      trigger: { minAmount: 100 },
      settings: {
        file: 'dragon_roar.wav',
        volume: 1.0
      }
    });

    // Overlay effects
    this.effects.set('overlay_thankyou', {
      type: 'overlay',
      trigger: { minAmount: 10 },
      settings: {
        template: 'thank_you',
        duration: 5000,
        position: { x: 50, y: 20 },
        animation: 'fade_in'
      },
      duration: 5000
    });

    this.effects.set('overlay_celebration', {
      type: 'overlay',
      trigger: { minAmount: 50 },
      settings: {
        template: 'celebration',
        duration: 8000,
        position: { x: 50, y: 50 },
        animation: 'bounce',
        effects: ['confetti', 'sparkles']
      },
      duration: 8000
    });

    this.effects.set('overlay_epic', {
      type: 'overlay',
      trigger: { minAmount: 200 },
      settings: {
        template: 'epic_donation',
        duration: 15000,
        position: { x: 50, y: 30 },
        animation: 'dramatic_zoom',
        effects: ['fireworks', 'golden_glow', 'screen_shake']
      },
      duration: 15000
    });

    // Camera effects
    this.effects.set('camera_reaction', {
      type: 'scene_change',
      trigger: { minAmount: 25 },
      settings: {
        scene: 'donation_cam',
        duration: 8000,
        transition: 'zoom'
      },
      duration: 8000
    });

    this.effects.set('camera_epic_reaction', {
      type: 'scene_change',
      trigger: { minAmount: 100 },
      settings: {
        scene: 'donation_cam',
        duration: 12000,
        transition: 'dramatic_zoom',
        followUp: 'overview'
      },
      duration: 12000
    });

    // Character action effects
    this.effects.set('character_cheer', {
      type: 'character_action',
      trigger: { minAmount: 20 },
      settings: {
        action: 'cheer',
        duration: 6000,
        characters: 'all'
      },
      duration: 6000
    });

    this.effects.set('character_dance', {
      type: 'character_action',
      trigger: { minAmount: 75 },
      settings: {
        action: 'victory_dance',
        duration: 10000,
        characters: 'party'
      },
      duration: 10000
    });

    // Special dice roll effects
    this.effects.set('lucky_dice', {
      type: 'dice_roll',
      trigger: { minAmount: 50 },
      settings: {
        diceType: 'd20',
        count: 1,
        modifier: '+5',
        blessing: 'Donation Luck',
        duration: 30000
      },
      duration: 30000
    });

    // Light effects (if supported)
    this.effects.set('lights_flash', {
      type: 'light_effect',
      trigger: { minAmount: 15 },
      settings: {
        pattern: 'flash',
        color: '#FFD700',
        duration: 3000,
        intensity: 0.8
      },
      duration: 3000
    });

    this.effects.set('lights_rainbow', {
      type: 'light_effect',
      trigger: { minAmount: 100 },
      settings: {
        pattern: 'rainbow_wave',
        duration: 10000,
        intensity: 1.0,
        speed: 'fast'
      },
      duration: 10000
    });

    // Keyword-based effects
    this.effects.set('dice_keyword', {
      type: 'dice_roll',
      trigger: { keywords: ['roll', 'dice', 'check', 'save'] },
      settings: {
        diceType: 'd20',
        count: 1,
        message: 'Donation dice roll for the party!'
      }
    });

    this.effects.set('heal_keyword', {
      type: 'character_action',
      trigger: { keywords: ['heal', 'health', 'potion', 'restore'] },
      settings: {
        action: 'heal',
        amount: '2d8+4',
        target: 'all',
        message: 'Donation healing for everyone!'
      }
    });
  }

  public async processDonation(donation: Donation): Promise<void> {
    console.log(`💰 Processing donation: ${donation.username} - $${donation.amount}`);
    
    const triggeredEffects = this.findTriggeredEffects(donation);
    const appliedEffects: string[] = [];

    for (const effect of triggeredEffects) {
      try {
        const effectId = await this.applyEffect(donation, effect);
        if (effectId) {
          appliedEffects.push(effectId);
        }
      } catch (error) {
        console.error(`Error applying effect ${effect.type}:`, error);
      }
    }

    // Record effect history
    this.effectHistory.push({
      donation,
      effects: appliedEffects,
      timestamp: new Date()
    });

    // Limit history size
    if (this.effectHistory.length > 100) {
      this.effectHistory = this.effectHistory.slice(-50);
    }

    this.emit('donation-processed', { donation, effects: appliedEffects });
  }

  private findTriggeredEffects(donation: Donation): DonationEffect[] {
    const triggered: DonationEffect[] = [];

    for (const effect of this.effects.values()) {
      if (this.shouldTriggerEffect(effect, donation)) {
        triggered.push(effect);
      }
    }

    // Sort by trigger requirements (higher amounts first)
    return triggered.sort((a, b) => {
      const aMin = a.trigger.minAmount || 0;
      const bMin = b.trigger.minAmount || 0;
      return bMin - aMin;
    });
  }

  private shouldTriggerEffect(effect: DonationEffect, donation: Donation): boolean {
    // Check minimum amount
    if (effect.trigger.minAmount && donation.amount < effect.trigger.minAmount) {
      return false;
    }

    // Check keywords
    if (effect.trigger.keywords && donation.message) {
      const message = donation.message.toLowerCase();
      const hasKeyword = effect.trigger.keywords.some(keyword => 
        message.includes(keyword.toLowerCase())
      );
      if (!hasKeyword) {
        return false;
      }
    }

    return true;
  }

  private async applyEffect(donation: Donation, effect: DonationEffect): Promise<string | null> {
    const effectId = `${effect.type}_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
    
    const context: EffectContext = {
      donation,
      obs: this.obs,
      overlayGenerator: this.overlayGenerator,
      cameraSwitcher: this.cameraSwitcher,
      soundPath: this.soundPath
    };

    try {
      switch (effect.type) {
        case 'sound':
          await this.applySoundEffect(effectId, effect, context);
          break;
        
        case 'overlay':
          await this.applyOverlayEffect(effectId, effect, context);
          break;
        
        case 'scene_change':
          await this.applySceneEffect(effectId, effect, context);
          break;
        
        case 'character_action':
          await this.applyCharacterEffect(effectId, effect, context);
          break;
        
        case 'dice_roll':
          await this.applyDiceEffect(effectId, effect, context);
          break;
        
        case 'light_effect':
          await this.applyLightEffect(effectId, effect, context);
          break;
        
        default:
          console.warn(`Unknown effect type: ${effect.type}`);
          return null;
      }

      // Set cleanup timer if duration is specified
      if (effect.duration) {
        const timer = setTimeout(() => {
          this.cleanupEffect(effectId, effect.type);
        }, effect.duration);
        
        this.activeEffects.set(effectId, timer);
      }

      console.log(`✨ Applied effect: ${effect.type} for $${donation.amount} donation`);
      return effectId;

    } catch (error) {
      console.error(`Failed to apply ${effect.type} effect:`, error);
      return null;
    }
  }

  private async applySoundEffect(effectId: string, effect: DonationEffect, context: EffectContext): Promise<void> {
    const soundFile = path.join(context.soundPath || '', effect.settings.file);
    
    try {
      // Check if file exists
      await fs.access(soundFile);
      
      // Play sound via OBS media source
      const sourceName = `donation_sound_${effectId}`;
      
      // Create temporary media source
      await context.obs.call('CreateInput', {
        sceneName: 'Donation_Overlay', // Assume this scene exists
        inputName: sourceName,
        inputKind: 'ffmpeg_source',
        inputSettings: {
          local_file: soundFile,
          is_local_file: true,
          restart_on_activate: true,
          close_when_inactive: true
        }
      });

      // Set volume
      if (effect.settings.volume) {
        await context.obs.call('SetInputVolume', {
          inputName: sourceName,
          inputVolumeMul: effect.settings.volume
        });
      }

      // Auto-cleanup after playback
      setTimeout(async () => {
        try {
          await context.obs.call('RemoveInput', { inputName: sourceName });
        } catch (error) {
          console.error('Error cleaning up sound source:', error);
        }
      }, 10000); // 10 second cleanup

    } catch (error) {
      console.warn(`Sound file not found: ${soundFile}, using text overlay instead`);
      
      // Fallback to text overlay
      await this.createSoundFallbackOverlay(context, effect.settings.file);
    }
  }

  private async createSoundFallbackOverlay(context: EffectContext, soundName: string): Promise<void> {
    const soundEmojis = {
      'coin_drop.wav': '🪙💫',
      'magic_chime.wav': '✨🔔',
      'dragon_roar.wav': '🐲🔥'
    };
    
    const emoji = soundEmojis[soundName as keyof typeof soundEmojis] || '🎵';
    
    const overlay = context.overlayGenerator.createTextOverlay(
      `${emoji} Thank you ${context.donation.username}! ${emoji}`,
      {
        position: { x: 50, y: 80, anchor: 'center' },
        style: {
          fontSize: 24,
          color: '#FFD700',
          background: 'rgba(0,0,0,0.8)',
          borderRadius: 10
        },
        animation: {
          type: 'pulse',
          duration: 2000,
          easing: 'ease-in-out',
          loop: true
        }
      }
    );

    await context.overlayGenerator.showOverlay(overlay, 3000);
  }

  private async applyOverlayEffect(effectId: string, effect: DonationEffect, context: EffectContext): Promise<void> {
    const overlay = this.createDonationOverlay(context.donation, effect.settings);
    await context.overlayGenerator.showOverlay(overlay, effect.settings.duration || 5000);
  }

  private createDonationOverlay(donation: Donation, settings: any): OverlayElement {
    const templates = {
      'thank_you': this.createThankYouOverlay(donation, settings),
      'celebration': this.createCelebrationOverlay(donation, settings),
      'epic_donation': this.createEpicDonationOverlay(donation, settings)
    };

    return templates[settings.template as keyof typeof templates] || templates['thank_you'];
  }

  private createThankYouOverlay(donation: Donation, settings: any): OverlayElement {
    return {
      id: `donation_thanks_${donation.id}`,
      type: 'text',
      position: settings.position || { x: 50, y: 20, anchor: 'center' },
      size: { width: 400, height: 100, scale: 1 },
      style: {
        background: 'linear-gradient(45deg, #FFD700, #FFA500)',
        border: '2px solid #FFD700',
        borderRadius: 15,
        color: '#FFFFFF',
        fontSize: 18,
        fontFamily: 'Arial Black'
      },
      data: {
        text: `💝 Thank you ${donation.username}!\n$${donation.amount} donation`,
        alignment: 'center'
      },
      visible: true,
      animation: {
        type: 'fade',
        duration: 1000,
        easing: 'ease-in-out'
      }
    };
  }

  private createCelebrationOverlay(donation: Donation, settings: any): OverlayElement {
    return {
      id: `donation_celebration_${donation.id}`,
      type: 'text',
      position: settings.position || { x: 50, y: 50, anchor: 'center' },
      size: { width: 500, height: 150, scale: 1.2 },
      style: {
        background: 'radial-gradient(circle, #FF6B6B, #4ECDC4)',
        border: '3px solid #FFFFFF',
        borderRadius: 20,
        color: '#FFFFFF',
        fontSize: 24,
        fontFamily: 'Arial Black',
        shadow: '0 0 20px rgba(255,107,107,0.8)'
      },
      data: {
        text: `🎉 AMAZING DONATION! 🎉\n${donation.username}: $${donation.amount}`,
        alignment: 'center',
        effects: settings.effects || []
      },
      visible: true,
      animation: {
        type: 'bounce',
        duration: 2000,
        easing: 'ease-out'
      }
    };
  }

  private createEpicDonationOverlay(donation: Donation, settings: any): OverlayElement {
    return {
      id: `donation_epic_${donation.id}`,
      type: 'text',
      position: settings.position || { x: 50, y: 30, anchor: 'center' },
      size: { width: 800, height: 200, scale: 1.5 },
      style: {
        background: 'linear-gradient(45deg, #9D4EDD, #C77DFF, #E0AAFF)',
        border: '5px solid #FFD60A',
        borderRadius: 25,
        color: '#FFFFFF',
        fontSize: 36,
        fontFamily: 'Impact',
        shadow: '0 0 40px rgba(157,78,221,1)'
      },
      data: {
        text: `⭐ LEGENDARY DONATION! ⭐\n${donation.username}\n$${donation.amount}`,
        alignment: 'center',
        effects: ['fireworks', 'golden_glow', 'screen_shake']
      },
      visible: true,
      animation: {
        type: 'dramatic_zoom',
        duration: 3000,
        easing: 'ease-out'
      }
    };
  }

  private async applySceneEffect(effectId: string, effect: DonationEffect, context: EffectContext): Promise<void> {
    if (!context.cameraSwitcher) {
      console.warn('Camera switcher not available for scene effect');
      return;
    }

    // Trigger donation reaction scene
    await context.cameraSwitcher.triggerDonationReaction();
    
    // Set up follow-up scene if specified
    if (effect.settings.followUp && effect.duration) {
      setTimeout(async () => {
        try {
          await context.cameraSwitcher!.manualSwitchToScene(effect.settings.followUp);
        } catch (error) {
          console.error('Error switching to follow-up scene:', error);
        }
      }, effect.duration);
    }
  }

  private async applyCharacterEffect(effectId: string, effect: DonationEffect, context: EffectContext): Promise<void> {
    // Create character action overlay
    const actionText = this.getCharacterActionText(effect.settings.action, context.donation);
    
    const overlay: OverlayElement = {
      id: `character_action_${effectId}`,
      type: 'text',
      position: { x: 50, y: 70, anchor: 'center' },
      size: { width: 600, height: 120, scale: 1 },
      style: {
        background: 'rgba(76, 175, 80, 0.9)',
        border: '2px solid #4CAF50',
        borderRadius: 10,
        color: '#FFFFFF',
        fontSize: 20,
        fontFamily: 'Arial'
      },
      data: {
        text: actionText,
        alignment: 'center'
      },
      visible: true,
      animation: {
        type: 'slide',
        duration: 1500,
        easing: 'ease-out'
      }
    };

    await context.overlayGenerator.showOverlay(overlay, effect.settings.duration || 6000);

    // If it's a heal action, show healing numbers
    if (effect.settings.action === 'heal') {
      await this.showHealingEffect(context, effect.settings);
    }
  }

  private getCharacterActionText(action: string, donation: Donation): string {
    const actions = {
      'cheer': `🎉 The party cheers for ${donation.username}'s generosity! 🎉`,
      'victory_dance': `💃 Epic victory dance inspired by ${donation.username}! 🕺`,
      'heal': `✨ ${donation.username}'s donation brings healing magic! ✨`,
      'inspire': `🌟 ${donation.username} inspires the party to greatness! 🌟`
    };

    return actions[action as keyof typeof actions] || `The party thanks ${donation.username}!`;
  }

  private async showHealingEffect(context: EffectContext, settings: any): Promise<void> {
    const healAmount = settings.amount || '1d8+2';
    const healingOverlay: OverlayElement = {
      id: `healing_${Date.now()}`,
      type: 'text',
      position: { x: 25, y: 40, anchor: 'center' },
      size: { width: 200, height: 80, scale: 1 },
      style: {
        background: 'rgba(76, 175, 80, 0.8)',
        color: '#FFFFFF',
        fontSize: 24,
        fontFamily: 'Arial Black'
      },
      data: {
        text: `+${healAmount} HP`,
        alignment: 'center'
      },
      visible: true,
      animation: {
        type: 'fade',
        duration: 2000,
        easing: 'ease-out'
      }
    };

    await context.overlayGenerator.showOverlay(healingOverlay, 3000);
  }

  private async applyDiceEffect(effectId: string, effect: DonationEffect, context: EffectContext): Promise<void> {
    // Create a special donation dice roll
    const diceRoll: ViewerDiceRoll = {
      id: `donation_${effectId}`,
      userId: context.donation.userId,
      username: context.donation.username,
      notation: `${effect.settings.count}${effect.settings.diceType}${effect.settings.modifier || ''}`,
      result: this.rollDice(effect.settings),
      timestamp: new Date(),
      context: effect.settings.blessing || 'Donation Luck'
    };

    // Show dice roll overlay
    const diceOverlay = context.overlayGenerator.createDiceRollOverlay(diceRoll);
    await context.overlayGenerator.showOverlay(diceOverlay, 8000);

    this.emit('donation-dice-roll', diceRoll);
  }

  private rollDice(settings: any): any {
    // Simple dice rolling implementation
    const sides = parseInt(settings.diceType.replace('d', ''));
    const count = settings.count || 1;
    const modifier = settings.modifier ? parseInt(settings.modifier.replace('+', '')) : 0;

    const rolls = Array.from({ length: count }, () => 
      Math.floor(Math.random() * sides) + 1
    );

    const total = rolls.reduce((sum, roll) => sum + roll, 0) + modifier;
    const critical = sides === 20 && rolls.some(roll => roll === 20);
    const fumble = sides === 20 && rolls.some(roll => roll === 1);

    return {
      total,
      rolls,
      modifiers: modifier ? [modifier] : [],
      breakdown: `${rolls.join(', ')}${modifier ? ` + ${modifier}` : ''} = ${total}`,
      critical,
      fumble
    };
  }

  private async applyLightEffect(effectId: string, effect: DonationEffect, context: EffectContext): Promise<void> {
    // This would integrate with smart lights or LED strips
    // For now, create a visual representation
    const lightOverlay: OverlayElement = {
      id: `light_effect_${effectId}`,
      type: 'image',
      position: { x: 0, y: 0, anchor: 'top-left' },
      size: { width: 1920, height: 1080, scale: 1 },
      style: {
        background: effect.settings.color || '#FFD700',
        opacity: effect.settings.intensity || 0.3
      },
      data: {
        pattern: effect.settings.pattern,
        speed: effect.settings.speed
      },
      visible: true,
      animation: {
        type: effect.settings.pattern === 'flash' ? 'pulse' : 'fade',
        duration: effect.settings.duration || 3000,
        easing: 'ease-in-out',
        loop: effect.settings.pattern === 'rainbow_wave'
      }
    };

    await context.overlayGenerator.showOverlay(lightOverlay, effect.settings.duration);
    console.log(`💡 Light effect: ${effect.settings.pattern} in ${effect.settings.color}`);
  }

  private cleanupEffect(effectId: string, effectType: string): void {
    const timer = this.activeEffects.get(effectId);
    if (timer) {
      clearTimeout(timer);
      this.activeEffects.delete(effectId);
    }

    console.log(`🧹 Cleaned up effect: ${effectType} (${effectId})`);
    this.emit('effect-cleanup', { effectId, effectType });
  }

  // Configuration methods
  public addCustomEffect(name: string, effect: DonationEffect): void {
    this.effects.set(name, effect);
    console.log(`➕ Added custom donation effect: ${name}`);
  }

  public removeEffect(name: string): void {
    this.effects.delete(name);
    console.log(`➖ Removed donation effect: ${name}`);
  }

  public updateEffect(name: string, effect: DonationEffect): void {
    this.effects.set(name, effect);
    console.log(`🔄 Updated donation effect: ${name}`);
  }

  public getEffects(): Map<string, DonationEffect> {
    return new Map(this.effects);
  }

  public getEffectHistory(): Array<{donation: Donation; effects: string[]; timestamp: Date}> {
    return [...this.effectHistory];
  }

  // Analytics
  public getEffectStatistics(): any {
    const stats = {
      totalDonations: this.effectHistory.length,
      totalAmount: this.effectHistory.reduce((sum, item) => sum + item.donation.amount, 0),
      averageAmount: 0,
      effectCounts: {} as Record<string, number>,
      topDonors: [] as Array<{username: string; amount: number; count: number}>
    };

    if (stats.totalDonations > 0) {
      stats.averageAmount = stats.totalAmount / stats.totalDonations;
    }

    // Count effects
    this.effectHistory.forEach(item => {
      item.effects.forEach(effectName => {
        stats.effectCounts[effectName] = (stats.effectCounts[effectName] || 0) + 1;
      });
    });

    // Calculate top donors
    const donorMap = new Map<string, {amount: number; count: number}>();
    this.effectHistory.forEach(item => {
      const existing = donorMap.get(item.donation.username) || {amount: 0, count: 0};
      existing.amount += item.donation.amount;
      existing.count += 1;
      donorMap.set(item.donation.username, existing);
    });

    stats.topDonors = Array.from(donorMap.entries())
      .map(([username, data]) => ({username, ...data}))
      .sort((a, b) => b.amount - a.amount)
      .slice(0, 10);

    return stats;
  }

  public async shutdown(): Promise<void> {
    // Clean up all active effects
    for (const [effectId, timer] of this.activeEffects) {
      clearTimeout(timer);
    }
    this.activeEffects.clear();
    
    console.log('🎭 Donation effects system shut down');
  }
}