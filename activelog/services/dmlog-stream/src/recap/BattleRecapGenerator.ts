import { EventEmitter } from 'events';
import { createCanvas, CanvasRenderingContext2D } from 'canvas';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as ffmpeg from 'fluent-ffmpeg';
import { 
  SessionEvent, 
  Character, 
  ViewerDiceRoll,
  OverlayElement,
  StreamHighlight
} from '../types';

export interface BattleParticipant {
  name: string;
  type: 'player' | 'npc' | 'enemy' | 'ally';
  level?: number;
  hitPoints: {
    start: number;
    end: number;
    max: number;
  };
  armorClass?: number;
  actions: BattleAction[];
  status: 'alive' | 'unconscious' | 'dead' | 'fled';
  portrait?: string;
}

export interface BattleAction {
  id: string;
  timestamp: Date;
  actor: string;
  type: 'attack' | 'spell' | 'movement' | 'other';
  target?: string;
  description: string;
  diceRoll?: ViewerDiceRoll;
  damage?: number;
  healing?: number;
  success: boolean;
  critical?: boolean;
  fumble?: boolean;
}

export interface BattleStats {
  duration: number; // minutes
  totalRounds: number;
  totalActions: number;
  totalDamage: number;
  totalHealing: number;
  criticalHits: number;
  criticalMisses: number;
  knockedOut: string[];
  deaths: string[];
  mvp?: string; // Most valuable player
  topDamageDealer?: string;
  topHealer?: string;
}

export interface BattleRecap {
  id: string;
  title: string;
  description: string;
  startTime: Date;
  endTime: Date;
  participants: BattleParticipant[];
  actions: BattleAction[];
  stats: BattleStats;
  result: 'victory' | 'defeat' | 'retreat' | 'draw';
  significance: number; // 0-1 scale
  videoPath?: string;
  thumbnailPath?: string;
}

export class BattleRecapGenerator extends EventEmitter {
  private outputPath: string;
  private currentBattle: BattleRecap | null = null;
  private battleHistory: BattleRecap[] = [];
  private characters: Map<string, Character> = new Map();
  private actionQueue: BattleAction[] = [];

  constructor(outputPath: string) {
    super();
    this.outputPath = outputPath;
  }

  public async initialize(): Promise<void> {
    try {
      await fs.mkdir(this.outputPath, { recursive: true });
      console.log('⚔️  Battle recap generator initialized');
      this.emit('initialized');
    } catch (error) {
      console.error('Error initializing battle recap generator:', error);
      throw error;
    }
  }

  public setCharacters(characters: Character[]): void {
    this.characters.clear();
    characters.forEach(char => {
      this.characters.set(char.name, char);
    });
  }

  public startBattle(
    title: string,
    description: string,
    participants: Array<{name: string; type: BattleParticipant['type']; hp: number; ac?: number; level?: number}>
  ): BattleRecap {
    if (this.currentBattle) {
      this.endBattle('victory'); // Auto-end previous battle
    }

    this.currentBattle = {
      id: this.generateBattleId(),
      title,
      description,
      startTime: new Date(),
      endTime: new Date(), // Will be updated when battle ends
      participants: participants.map(p => ({
        name: p.name,
        type: p.type,
        level: p.level,
        hitPoints: {
          start: p.hp,
          end: p.hp,
          max: p.hp
        },
        armorClass: p.ac,
        actions: [],
        status: 'alive'
      })),
      actions: [],
      stats: this.initializeBattleStats(),
      result: 'victory',
      significance: 0.5
    };

    console.log(`⚔️  Battle started: ${title}`);
    this.emit('battle-started', this.currentBattle);
    
    return this.currentBattle;
  }

  private initializeBattleStats(): BattleStats {
    return {
      duration: 0,
      totalRounds: 0,
      totalActions: 0,
      totalDamage: 0,
      totalHealing: 0,
      criticalHits: 0,
      criticalMisses: 0,
      knockedOut: [],
      deaths: []
    };
  }

  public addBattleAction(
    actor: string,
    type: BattleAction['type'],
    description: string,
    target?: string,
    diceRoll?: ViewerDiceRoll,
    damage?: number,
    healing?: number
  ): BattleAction | null {
    if (!this.currentBattle) {
      console.warn('No active battle to add action to');
      return null;
    }

    const action: BattleAction = {
      id: this.generateActionId(),
      timestamp: new Date(),
      actor,
      type,
      target,
      description,
      diceRoll,
      damage,
      healing,
      success: this.determineActionSuccess(diceRoll, type),
      critical: diceRoll?.result.critical,
      fumble: diceRoll?.result.fumble
    };

    this.currentBattle.actions.push(action);
    
    // Update participant actions
    const participant = this.currentBattle.participants.find(p => p.name === actor);
    if (participant) {
      participant.actions.push(action);
    }

    // Update battle stats
    this.updateBattleStats(action);
    
    // Apply action effects
    this.applyActionEffects(action);

    console.log(`⚔️  Action: ${actor} ${type} - ${description}`);
    this.emit('battle-action', action);
    
    return action;
  }

  private determineActionSuccess(diceRoll?: ViewerDiceRoll, type?: string): boolean {
    if (!diceRoll) return true; // Non-dice actions are assumed successful
    
    if (diceRoll.result.critical) return true;
    if (diceRoll.result.fumble) return false;
    
    // Simple success determination based on total
    const threshold = type === 'attack' ? 10 : 8;
    return diceRoll.result.total >= threshold;
  }

  private updateBattleStats(action: BattleAction): void {
    if (!this.currentBattle) return;

    const stats = this.currentBattle.stats;
    
    stats.totalActions++;
    
    if (action.damage) {
      stats.totalDamage += action.damage;
    }
    
    if (action.healing) {
      stats.totalHealing += action.healing;
    }
    
    if (action.critical) {
      stats.criticalHits++;
    }
    
    if (action.fumble) {
      stats.criticalMisses++;
    }
  }

  private applyActionEffects(action: BattleAction): void {
    if (!this.currentBattle || !action.target) return;

    const target = this.currentBattle.participants.find(p => p.name === action.target);
    if (!target) return;

    // Apply damage
    if (action.damage && action.success) {
      target.hitPoints.end = Math.max(0, target.hitPoints.end - action.damage);
      
      if (target.hitPoints.end === 0) {
        target.status = 'unconscious';
        if (!this.currentBattle.stats.knockedOut.includes(target.name)) {
          this.currentBattle.stats.knockedOut.push(target.name);
        }
      }
    }

    // Apply healing
    if (action.healing) {
      target.hitPoints.end = Math.min(target.hitPoints.max, target.hitPoints.end + action.healing);
      
      if (target.status === 'unconscious' && target.hitPoints.end > 0) {
        target.status = 'alive';
      }
    }
  }

  public updateParticipantStatus(name: string, status: BattleParticipant['status']): void {
    if (!this.currentBattle) return;

    const participant = this.currentBattle.participants.find(p => p.name === name);
    if (participant) {
      participant.status = status;
      
      if (status === 'dead' && !this.currentBattle.stats.deaths.includes(name)) {
        this.currentBattle.stats.deaths.push(name);
      }
    }
  }

  public endBattle(result: BattleRecap['result']): BattleRecap | null {
    if (!this.currentBattle) return null;

    this.currentBattle.endTime = new Date();
    this.currentBattle.result = result;
    
    // Calculate final stats
    this.finalizeBattleStats();
    
    // Calculate significance
    this.currentBattle.significance = this.calculateBattleSignificance();
    
    // Save to history
    this.battleHistory.push(this.currentBattle);
    
    const completedBattle = this.currentBattle;
    this.currentBattle = null;
    
    console.log(`⚔️  Battle ended: ${completedBattle.title} (${result})`);
    this.emit('battle-ended', completedBattle);
    
    return completedBattle;
  }

  private finalizeBattleStats(): void {
    if (!this.currentBattle) return;

    const stats = this.currentBattle.stats;
    
    // Calculate duration
    stats.duration = (this.currentBattle.endTime.getTime() - this.currentBattle.startTime.getTime()) / 60000; // minutes
    
    // Estimate rounds (roughly 1 round per 6 actions)
    stats.totalRounds = Math.ceil(stats.totalActions / 6);
    
    // Determine MVP
    stats.mvp = this.determineMVP();
    stats.topDamageDealer = this.getTopDamageDealer();
    stats.topHealer = this.getTopHealer();
  }

  private determineMVP(): string | undefined {
    if (!this.currentBattle) return undefined;

    const playerParticipants = this.currentBattle.participants
      .filter(p => p.type === 'player');
    
    if (playerParticipants.length === 0) return undefined;

    // Score participants based on actions, damage dealt, healing, etc.
    const scores = playerParticipants.map(participant => {
      let score = 0;
      
      participant.actions.forEach(action => {
        score += 1; // Base action score
        if (action.success) score += 1;
        if (action.critical) score += 3;
        if (action.damage) score += action.damage * 0.1;
        if (action.healing) score += action.healing * 0.15; // Healing is more valuable
      });
      
      return { name: participant.name, score };
    });

    return scores.sort((a, b) => b.score - a.score)[0]?.name;
  }

  private getTopDamageDealer(): string | undefined {
    if (!this.currentBattle) return undefined;

    const damageMap = new Map<string, number>();
    
    this.currentBattle.actions.forEach(action => {
      if (action.damage && action.success) {
        const current = damageMap.get(action.actor) || 0;
        damageMap.set(action.actor, current + action.damage);
      }
    });

    if (damageMap.size === 0) return undefined;

    return Array.from(damageMap.entries())
      .sort((a, b) => b[1] - a[1])[0][0];
  }

  private getTopHealer(): string | undefined {
    if (!this.currentBattle) return undefined;

    const healingMap = new Map<string, number>();
    
    this.currentBattle.actions.forEach(action => {
      if (action.healing) {
        const current = healingMap.get(action.actor) || 0;
        healingMap.set(action.actor, current + action.healing);
      }
    });

    if (healingMap.size === 0) return undefined;

    return Array.from(healingMap.entries())
      .sort((a, b) => b[1] - a[1])[0][0];
  }

  private calculateBattleSignificance(): number {
    if (!this.currentBattle) return 0;

    let significance = 0.5; // Base significance
    
    const stats = this.currentBattle.stats;
    
    // Duration factor
    if (stats.duration > 30) significance += 0.2; // Long battles are significant
    else if (stats.duration > 15) significance += 0.1;
    
    // Death factor
    significance += stats.deaths.length * 0.3;
    
    // Critical hits factor
    significance += Math.min(0.2, stats.criticalHits * 0.05);
    
    // Damage factor (normalized)
    if (stats.totalDamage > 100) significance += 0.1;
    if (stats.totalDamage > 200) significance += 0.1;
    
    // Result factor
    if (this.currentBattle.result === 'victory') significance += 0.1;
    else if (this.currentBattle.result === 'defeat') significance += 0.2; // Defeats are memorable
    
    return Math.min(1.0, significance);
  }

  // Video generation
  public async generateBattleRecapVideo(battle: BattleRecap): Promise<string> {
    if (!battle) throw new Error('No battle provided');

    console.log(`🎬 Generating battle recap video: ${battle.title}`);
    
    // Create frames for the battle recap
    const frames = await this.generateRecapFrames(battle);
    
    // Combine frames into video
    const videoPath = await this.createVideoFromFrames(battle, frames);
    
    battle.videoPath = videoPath;
    
    console.log(`✅ Battle recap video generated: ${videoPath}`);
    this.emit('recap-video-generated', battle);
    
    return videoPath;
  }

  private async generateRecapFrames(battle: BattleRecap): Promise<string[]> {
    const frames: string[] = [];
    
    // Title frame
    frames.push(await this.createTitleFrame(battle));
    
    // Participants frame
    frames.push(await this.createParticipantsFrame(battle));
    
    // Key moments frames
    const keyMoments = this.extractKeyMoments(battle);
    for (const moment of keyMoments) {
      frames.push(await this.createMomentFrame(moment, battle));
    }
    
    // Stats frame
    frames.push(await this.createStatsFrame(battle));
    
    // Result frame
    frames.push(await this.createResultFrame(battle));
    
    return frames;
  }

  private async createTitleFrame(battle: BattleRecap): Promise<string> {
    const canvas = createCanvas(1920, 1080);
    const ctx = canvas.getContext('2d');
    
    // Background
    const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
    gradient.addColorStop(0, '#2C1810');
    gradient.addColorStop(1, '#1A0E08');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Title
    ctx.fillStyle = '#FFD700';
    ctx.font = 'bold 72px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(battle.title, canvas.width / 2, 300);
    
    // Subtitle
    ctx.fillStyle = '#FFFFFF';
    ctx.font = '36px Arial';
    ctx.fillText('Battle Recap', canvas.width / 2, 360);
    
    // Description
    ctx.fillStyle = '#CCCCCC';
    ctx.font = '28px Arial';
    this.wrapText(ctx, battle.description, canvas.width / 2, 450, 1400, 40);
    
    // Duration
    ctx.fillStyle = '#FFD700';
    ctx.font = '24px Arial';
    ctx.fillText(`Duration: ${battle.stats.duration.toFixed(1)} minutes`, canvas.width / 2, 800);
    
    const framePath = path.join(this.outputPath, `${battle.id}_frame_title.png`);
    const buffer = canvas.toBuffer('image/png');
    await fs.writeFile(framePath, buffer);
    
    return framePath;
  }

  private async createParticipantsFrame(battle: BattleRecap): Promise<string> {
    const canvas = createCanvas(1920, 1080);
    const ctx = canvas.getContext('2d');
    
    // Background
    const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
    gradient.addColorStop(0, '#1A0E08');
    gradient.addColorStop(1, '#2C1810');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Title
    ctx.fillStyle = '#FFD700';
    ctx.font = 'bold 48px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Battle Participants', canvas.width / 2, 100);
    
    // Separate participants by type
    const players = battle.participants.filter(p => p.type === 'player');
    const enemies = battle.participants.filter(p => p.type === 'enemy');
    
    let yPos = 200;
    
    // Players
    if (players.length > 0) {
      ctx.fillStyle = '#4CAF50';
      ctx.font = 'bold 36px Arial';
      ctx.textAlign = 'left';
      ctx.fillText('Heroes:', 200, yPos);
      yPos += 60;
      
      players.forEach(participant => {
        ctx.fillStyle = '#FFFFFF';
        ctx.font = '24px Arial';
        const statusColor = participant.status === 'alive' ? '#4CAF50' : 
                           participant.status === 'unconscious' ? '#FF9800' : '#F44336';
        
        ctx.fillText(`${participant.name}`, 240, yPos);
        ctx.fillStyle = statusColor;
        ctx.fillText(`${participant.status.toUpperCase()}`, 600, yPos);
        
        // HP bar
        this.drawHPBar(ctx, 800, yPos - 15, 200, 20, participant.hitPoints);
        
        yPos += 40;
      });
    }
    
    yPos += 40;
    
    // Enemies
    if (enemies.length > 0) {
      ctx.fillStyle = '#F44336';
      ctx.font = 'bold 36px Arial';
      ctx.textAlign = 'left';
      ctx.fillText('Enemies:', 200, yPos);
      yPos += 60;
      
      enemies.forEach(participant => {
        ctx.fillStyle = '#FFFFFF';
        ctx.font = '24px Arial';
        const statusColor = participant.status === 'alive' ? '#4CAF50' : 
                           participant.status === 'unconscious' ? '#FF9800' : '#F44336';
        
        ctx.fillText(`${participant.name}`, 240, yPos);
        ctx.fillStyle = statusColor;
        ctx.fillText(`${participant.status.toUpperCase()}`, 600, yPos);
        
        // HP bar
        this.drawHPBar(ctx, 800, yPos - 15, 200, 20, participant.hitPoints);
        
        yPos += 40;
      });
    }
    
    const framePath = path.join(this.outputPath, `${battle.id}_frame_participants.png`);
    const buffer = canvas.toBuffer('image/png');
    await fs.writeFile(framePath, buffer);
    
    return framePath;
  }

  private drawHPBar(
    ctx: CanvasRenderingContext2D, 
    x: number, 
    y: number, 
    width: number, 
    height: number, 
    hp: {start: number; end: number; max: number}
  ): void {
    // Background
    ctx.fillStyle = '#333333';
    ctx.fillRect(x, y, width, height);
    
    // Damage (start HP)
    const startPercent = hp.start / hp.max;
    ctx.fillStyle = '#666666';
    ctx.fillRect(x, y, width * startPercent, height);
    
    // Current HP
    const endPercent = hp.end / hp.max;
    const color = endPercent > 0.6 ? '#4CAF50' : endPercent > 0.3 ? '#FF9800' : '#F44336';
    ctx.fillStyle = color;
    ctx.fillRect(x, y, width * endPercent, height);
    
    // Border
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineWidth = 1;
    ctx.strokeRect(x, y, width, height);
    
    // HP Text
    ctx.fillStyle = '#FFFFFF';
    ctx.font = '14px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(`${hp.end}/${hp.max}`, x + width / 2, y + height / 2 + 5);
  }

  private extractKeyMoments(battle: BattleRecap): BattleAction[] {
    // Select the most significant actions
    return battle.actions
      .filter(action => 
        action.critical || 
        action.fumble || 
        (action.damage && action.damage > 15) ||
        (action.healing && action.healing > 10)
      )
      .sort((a, b) => {
        let scoreA = 0;
        let scoreB = 0;
        
        if (a.critical) scoreA += 10;
        if (a.fumble) scoreA += 8;
        if (a.damage) scoreA += a.damage * 0.5;
        if (a.healing) scoreA += a.healing * 0.6;
        
        if (b.critical) scoreB += 10;
        if (b.fumble) scoreB += 8;
        if (b.damage) scoreB += b.damage * 0.5;
        if (b.healing) scoreB += b.healing * 0.6;
        
        return scoreB - scoreA;
      })
      .slice(0, 5); // Top 5 moments
  }

  private async createMomentFrame(action: BattleAction, battle: BattleRecap): Promise<string> {
    const canvas = createCanvas(1920, 1080);
    const ctx = canvas.getContext('2d');
    
    // Background
    let bgColor1 = '#1A0E08';
    let bgColor2 = '#2C1810';
    
    if (action.critical) {
      bgColor1 = '#2A1810';
      bgColor2 = '#4A3020';
    } else if (action.fumble) {
      bgColor1 = '#1A0F10';
      bgColor2 = '#301820';
    }
    
    const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
    gradient.addColorStop(0, bgColor1);
    gradient.addColorStop(1, bgColor2);
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Title
    let title = 'Key Moment';
    if (action.critical) title = '🎯 CRITICAL HIT!';
    else if (action.fumble) title = '💀 CRITICAL FUMBLE!';
    else if (action.damage && action.damage > 20) title = '💥 MASSIVE DAMAGE!';
    else if (action.healing && action.healing > 15) title = '✨ POWERFUL HEALING!';
    
    ctx.fillStyle = action.critical ? '#FFD700' : action.fumble ? '#FF4444' : '#FFFFFF';
    ctx.font = 'bold 56px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(title, canvas.width / 2, 200);
    
    // Actor
    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 36px Arial';
    ctx.fillText(action.actor, canvas.width / 2, 300);
    
    // Action description
    ctx.fillStyle = '#CCCCCC';
    ctx.font = '28px Arial';
    this.wrapText(ctx, action.description, canvas.width / 2, 400, 1400, 40);
    
    // Dice roll if available
    if (action.diceRoll) {
      ctx.fillStyle = '#FFD700';
      ctx.font = 'bold 48px Arial';
      ctx.fillText(`Rolled: ${action.diceRoll.result.total}`, canvas.width / 2, 650);
      
      ctx.fillStyle = '#FFFFFF';
      ctx.font = '24px Arial';
      ctx.fillText(action.diceRoll.result.breakdown, canvas.width / 2, 690);
    }
    
    // Damage/Healing
    if (action.damage) {
      ctx.fillStyle = '#FF4444';
      ctx.font = 'bold 36px Arial';
      ctx.fillText(`${action.damage} Damage`, canvas.width / 2, 800);
    } else if (action.healing) {
      ctx.fillStyle = '#44FF44';
      ctx.font = 'bold 36px Arial';
      ctx.fillText(`${action.healing} Healing`, canvas.width / 2, 800);
    }
    
    const framePath = path.join(this.outputPath, `${battle.id}_frame_moment_${action.id}.png`);
    const buffer = canvas.toBuffer('image/png');
    await fs.writeFile(framePath, buffer);
    
    return framePath;
  }

  private async createStatsFrame(battle: BattleRecap): Promise<string> {
    const canvas = createCanvas(1920, 1080);
    const ctx = canvas.getContext('2d');
    
    // Background
    const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
    gradient.addColorStop(0, '#1A0E08');
    gradient.addColorStop(1, '#2C1810');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Title
    ctx.fillStyle = '#FFD700';
    ctx.font = 'bold 48px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Battle Statistics', canvas.width / 2, 100);
    
    // Stats in two columns
    const stats = [
      `Duration: ${battle.stats.duration.toFixed(1)} minutes`,
      `Total Rounds: ${battle.stats.totalRounds}`,
      `Total Actions: ${battle.stats.totalActions}`,
      `Total Damage: ${battle.stats.totalDamage}`,
      `Total Healing: ${battle.stats.totalHealing}`,
      `Critical Hits: ${battle.stats.criticalHits}`,
      `Critical Misses: ${battle.stats.criticalMisses}`,
      `Knocked Out: ${battle.stats.knockedOut.join(', ') || 'None'}`,
      `Deaths: ${battle.stats.deaths.join(', ') || 'None'}`
    ];
    
    ctx.fillStyle = '#FFFFFF';
    ctx.font = '32px Arial';
    ctx.textAlign = 'left';
    
    const leftColumn = stats.slice(0, Math.ceil(stats.length / 2));
    const rightColumn = stats.slice(Math.ceil(stats.length / 2));
    
    leftColumn.forEach((stat, index) => {
      ctx.fillText(stat, 200, 250 + (index * 60));
    });
    
    rightColumn.forEach((stat, index) => {
      ctx.fillText(stat, 1000, 250 + (index * 60));
    });
    
    // MVP and special mentions
    let yPos = 700;
    
    if (battle.stats.mvp) {
      ctx.fillStyle = '#FFD700';
      ctx.font = 'bold 36px Arial';
      ctx.textAlign = 'center';
      ctx.fillText(`🏆 MVP: ${battle.stats.mvp}`, canvas.width / 2, yPos);
      yPos += 60;
    }
    
    if (battle.stats.topDamageDealer) {
      ctx.fillStyle = '#FF4444';
      ctx.font = '28px Arial';
      ctx.fillText(`⚔️ Top Damage: ${battle.stats.topDamageDealer}`, canvas.width / 2, yPos);
      yPos += 50;
    }
    
    if (battle.stats.topHealer) {
      ctx.fillStyle = '#44FF44';
      ctx.font = '28px Arial';
      ctx.fillText(`🩹 Top Healer: ${battle.stats.topHealer}`, canvas.width / 2, yPos);
    }
    
    const framePath = path.join(this.outputPath, `${battle.id}_frame_stats.png`);
    const buffer = canvas.toBuffer('image/png');
    await fs.writeFile(framePath, buffer);
    
    return framePath;
  }

  private async createResultFrame(battle: BattleRecap): Promise<string> {
    const canvas = createCanvas(1920, 1080);
    const ctx = canvas.getContext('2d');
    
    // Background based on result
    let bgColor1 = '#1A0E08';
    let bgColor2 = '#2C1810';
    let resultColor = '#FFD700';
    let resultEmoji = '⚔️';
    
    switch (battle.result) {
      case 'victory':
        bgColor1 = '#0A2A0A';
        bgColor2 = '#1A4A1A';
        resultColor = '#44FF44';
        resultEmoji = '🏆';
        break;
      case 'defeat':
        bgColor1 = '#2A0A0A';
        bgColor2 = '#4A1A1A';
        resultColor = '#FF4444';
        resultEmoji = '💀';
        break;
      case 'retreat':
        bgColor1 = '#2A1A0A';
        bgColor2 = '#4A3A1A';
        resultColor = '#FFAA44';
        resultEmoji = '🏃';
        break;
    }
    
    const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
    gradient.addColorStop(0, bgColor1);
    gradient.addColorStop(1, bgColor2);
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Result
    ctx.fillStyle = resultColor;
    ctx.font = 'bold 96px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(`${resultEmoji} ${battle.result.toUpperCase()}! ${resultEmoji}`, canvas.width / 2, 400);
    
    // Battle title
    ctx.fillStyle = '#FFFFFF';
    ctx.font = '48px Arial';
    ctx.fillText(battle.title, canvas.width / 2, 500);
    
    // Significance
    const significanceText = battle.significance > 0.8 ? 'LEGENDARY BATTLE' :
                           battle.significance > 0.6 ? 'EPIC ENCOUNTER' :
                           'MEMORABLE FIGHT';
    
    ctx.fillStyle = '#FFD700';
    ctx.font = 'bold 36px Arial';
    ctx.fillText(significanceText, canvas.width / 2, 600);
    
    const framePath = path.join(this.outputPath, `${battle.id}_frame_result.png`);
    const buffer = canvas.toBuffer('image/png');
    await fs.writeFile(framePath, buffer);
    
    return framePath;
  }

  private async createVideoFromFrames(battle: BattleRecap, frames: string[]): Promise<string> {
    const outputPath = path.join(this.outputPath, `${battle.id}_recap.mp4`);
    
    return new Promise((resolve, reject) => {
      let command = ffmpeg();
      
      // Add each frame as input with 4-second duration
      frames.forEach((frame, index) => {
        command = command
          .input(frame)
          .inputOptions(['-t 4', '-f image2']); // 4 seconds per frame
      });
      
      // Create filter complex to concatenate frames
      const filterInputs = frames.map((_, index) => `[${index}:v]`).join('');
      const filterComplex = `${filterInputs}concat=n=${frames.length}:v=1:a=0[outv]`;
      
      command
        .complexFilter(filterComplex)
        .map('[outv]')
        .videoCodec('libx264')
        .size('1920x1080')
        .fps(30)
        .videoBitrate('2500k')
        .format('mp4')
        .on('start', (commandLine) => {
          console.log(`🎬 Creating battle recap video: ${commandLine}`);
        })
        .on('end', () => {
          console.log(`✅ Battle recap video created: ${outputPath}`);
          resolve(outputPath);
        })
        .on('error', (error) => {
          console.error(`❌ Error creating battle recap video: ${error.message}`);
          reject(error);
        })
        .save(outputPath);
    });
  }

  private wrapText(
    ctx: CanvasRenderingContext2D, 
    text: string, 
    x: number, 
    y: number, 
    maxWidth: number, 
    lineHeight: number
  ): void {
    const words = text.split(' ');
    let line = '';
    let currentY = y;
    
    for (const word of words) {
      const testLine = line + word + ' ';
      const metrics = ctx.measureText(testLine);
      const testWidth = metrics.width;
      
      if (testWidth > maxWidth && line !== '') {
        ctx.fillText(line.trim(), x, currentY);
        line = word + ' ';
        currentY += lineHeight;
      } else {
        line = testLine;
      }
    }
    
    ctx.fillText(line.trim(), x, currentY);
  }

  // Utility methods
  private generateBattleId(): string {
    return `battle_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateActionId(): string {
    return `action_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // Analytics and reporting
  public getBattleHistory(): BattleRecap[] {
    return [...this.battleHistory];
  }

  public getBattleStatistics(): any {
    if (this.battleHistory.length === 0) return null;

    const totalBattles = this.battleHistory.length;
    const victories = this.battleHistory.filter(b => b.result === 'victory').length;
    const defeats = this.battleHistory.filter(b => b.result === 'defeat').length;
    
    const avgDuration = this.battleHistory.reduce((sum, b) => sum + b.stats.duration, 0) / totalBattles;
    const totalDamage = this.battleHistory.reduce((sum, b) => sum + b.stats.totalDamage, 0);
    const totalCrits = this.battleHistory.reduce((sum, b) => sum + b.stats.criticalHits, 0);

    return {
      totalBattles,
      winRate: (victories / totalBattles) * 100,
      avgDuration: Math.round(avgDuration * 100) / 100,
      totalDamage,
      totalCrits,
      mostSignificant: this.battleHistory
        .sort((a, b) => b.significance - a.significance)[0],
      longestBattle: this.battleHistory
        .sort((a, b) => b.stats.duration - a.stats.duration)[0]
    };
  }

  public getCurrentBattle(): BattleRecap | null {
    return this.currentBattle;
  }

  public async shutdown(): Promise<void> {
    if (this.currentBattle) {
      this.endBattle('draw'); // Auto-end with draw result
    }
    console.log('⚔️  Battle recap generator shut down');
  }
}