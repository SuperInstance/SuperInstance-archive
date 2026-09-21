import { EventEmitter } from 'events';
import { createCanvas, CanvasRenderingContext2D } from 'canvas';
import * as fs from 'fs/promises';
import * as path from 'path';
import { Campaign, Session, SessionEvent, Character, OverlayElement } from '../types';
import { OverlayGenerator } from './OverlayGenerator';

export interface ProgressMilestone {
  id: string;
  title: string;
  description: string;
  type: 'level' | 'story' | 'location' | 'achievement' | 'treasure' | 'relationship';
  achieved: boolean;
  achievedAt?: Date;
  value?: number;
  icon?: string;
  color?: string;
}

export interface CampaignStats {
  sessionsPlayed: number;
  totalPlaytime: number; // in hours
  averageLevel: number;
  totalExperience: number;
  enemiesDefeated: number;
  treasureFound: number;
  locationsVisited: string[];
  majorEvents: string[];
  characterDeaths: number;
  criticalHits: number;
  criticalMisses: number;
}

export class CampaignProgress extends EventEmitter {
  private overlayGenerator: OverlayGenerator;
  private campaign: Campaign | null = null;
  private currentSession: Session | null = null;
  private milestones: Map<string, ProgressMilestone> = new Map();
  private stats: CampaignStats;
  private progressData: any = {};
  private dataPath: string;
  private activeOverlays: Map<string, OverlayElement> = new Map();

  constructor(overlayGenerator: OverlayGenerator, dataPath: string) {
    super();
    this.overlayGenerator = overlayGenerator;
    this.dataPath = dataPath;
    this.stats = {
      sessionsPlayed: 0,
      totalPlaytime: 0,
      averageLevel: 1,
      totalExperience: 0,
      enemiesDefeated: 0,
      treasureFound: 0,
      locationsVisited: [],
      majorEvents: [],
      characterDeaths: 0,
      criticalHits: 0,
      criticalMisses: 0
    };
  }

  public async initialize(): Promise<void> {
    try {
      await fs.mkdir(this.dataPath, { recursive: true });
      await this.loadProgressData();
      
      console.log('🗺️  Campaign progress overlay initialized');
      this.emit('initialized');
    } catch (error) {
      console.error('Error initializing campaign progress:', error);
      throw error;
    }
  }

  private async loadProgressData(): Promise<void> {
    try {
      const dataFile = path.join(this.dataPath, 'campaign_progress.json');
      const data = await fs.readFile(dataFile, 'utf-8');
      const parsed = JSON.parse(data);
      
      this.progressData = parsed.progress || {};
      this.stats = { ...this.stats, ...parsed.stats };
      
      // Load milestones
      if (parsed.milestones) {
        for (const [id, milestone] of Object.entries(parsed.milestones)) {
          this.milestones.set(id, milestone as ProgressMilestone);
        }
      }
      
      console.log('📊 Loaded campaign progress data');
    } catch (error) {
      // File doesn't exist or is invalid, start fresh
      console.log('🆕 Starting with fresh campaign progress');
    }
  }

  private async saveProgressData(): Promise<void> {
    try {
      const data = {
        progress: this.progressData,
        stats: this.stats,
        milestones: Object.fromEntries(this.milestones),
        lastUpdated: new Date().toISOString()
      };
      
      const dataFile = path.join(this.dataPath, 'campaign_progress.json');
      await fs.writeFile(dataFile, JSON.stringify(data, null, 2));
    } catch (error) {
      console.error('Error saving progress data:', error);
    }
  }

  public startCampaign(campaign: Campaign): void {
    this.campaign = campaign;
    this.setupDefaultMilestones();
    this.updateStatsFromCampaign(campaign);
    
    console.log(`🏰 Started tracking progress for campaign: ${campaign.name}`);
    this.emit('campaign-started', campaign);
  }

  public startSession(session: Session): void {
    this.currentSession = session;
    this.stats.sessionsPlayed++;
    
    console.log(`📖 Session ${session.sessionNumber} started: ${session.title}`);
    this.emit('session-started', session);
  }

  public async endSession(session: Session): Promise<void> {
    if (this.currentSession?.id === session.id) {
      const duration = session.endTime && session.startTime ? 
        (session.endTime.getTime() - session.startTime.getTime()) / (1000 * 60 * 60) : 0;
      
      this.stats.totalPlaytime += duration;
      this.currentSession = null;
      
      await this.processSessionEvents(session);
      await this.saveProgressData();
      
      console.log(`📖 Session ended: ${session.title} (${duration.toFixed(1)}h)`);
      this.emit('session-ended', session);
    }
  }

  private setupDefaultMilestones(): void {
    if (!this.campaign) return;

    // Level milestones
    for (let level = 2; level <= 20; level++) {
      this.milestones.set(`level_${level}`, {
        id: `level_${level}`,
        title: `Level ${level} Achieved`,
        description: `The party has reached level ${level}!`,
        type: 'level',
        achieved: false,
        value: level,
        icon: '⭐',
        color: '#FFD700'
      });
    }

    // Story milestones (these would be campaign-specific)
    const storyMilestones = [
      { id: 'first_boss', title: 'First Boss Defeated', description: 'Defeated your first major enemy!' },
      { id: 'first_city', title: 'Major City Visited', description: 'Explored your first major settlement!' },
      { id: 'first_dungeon', title: 'Dungeon Cleared', description: 'Successfully cleared your first dungeon!' },
      { id: 'party_formed', title: 'Party Assembled', description: 'The adventuring party has been formed!' },
      { id: 'first_treasure', title: 'Treasure Discovered', description: 'Found your first significant treasure!' }
    ];

    storyMilestones.forEach(milestone => {
      this.milestones.set(milestone.id, {
        ...milestone,
        type: 'story',
        achieved: false,
        icon: '🏆',
        color: '#4CAF50'
      });
    });

    // Achievement milestones
    const achievements = [
      { id: 'crit_master', title: 'Critical Master', description: 'Rolled 10 natural 20s!', value: 10 },
      { id: 'survivor', title: 'Survivor', description: 'Survived 5 sessions without a character death!', value: 5 },
      { id: 'explorer', title: 'Explorer', description: 'Visited 10 different locations!', value: 10 },
      { id: 'wealthy', title: 'Wealthy Adventurers', description: 'Accumulated 1000 gold pieces!', value: 1000 }
    ];

    achievements.forEach(achievement => {
      this.milestones.set(achievement.id, {
        ...achievement,
        type: 'achievement',
        achieved: false,
        icon: '🎖️',
        color: '#9C27B0'
      });
    });
  }

  private updateStatsFromCampaign(campaign: Campaign): void {
    if (campaign.characters.length > 0) {
      const totalLevels = campaign.characters.reduce((sum, char) => sum + char.level, 0);
      this.stats.averageLevel = totalLevels / campaign.characters.length;
    }

    this.stats.sessionsPlayed = campaign.sessions.length;
    
    // Calculate total playtime from sessions
    this.stats.totalPlaytime = campaign.sessions.reduce((total, session) => {
      if (session.endTime && session.startTime) {
        return total + (session.endTime.getTime() - session.startTime.getTime()) / (1000 * 60 * 60);
      }
      return total;
    }, 0);
  }

  private async processSessionEvents(session: Session): Promise<void> {
    for (const event of session.events) {
      await this.processEvent(event);
    }

    // Check for milestone achievements
    await this.checkMilestoneAchievements();
  }

  private async processEvent(event: SessionEvent): Promise<void> {
    switch (event.type) {
      case 'combat':
        if (event.outcome?.toLowerCase().includes('victory')) {
          this.stats.enemiesDefeated++;
          
          // Check for boss defeats
          if (event.description.toLowerCase().includes('boss') || 
              event.description.toLowerCase().includes('final')) {
            await this.achieveMilestone('first_boss');
          }
        }
        break;

      case 'discovery':
        if (event.treasure && event.treasure.length > 0) {
          this.stats.treasureFound += event.treasure.length;
          await this.achieveMilestone('first_treasure');
        }
        break;

      case 'exploration':
        const location = this.extractLocationFromEvent(event);
        if (location && !this.stats.locationsVisited.includes(location)) {
          this.stats.locationsVisited.push(location);
          
          if (location.toLowerCase().includes('city') || 
              location.toLowerCase().includes('town')) {
            await this.achieveMilestone('first_city');
          }
        }
        break;

      case 'social':
        if (event.description.toLowerCase().includes('death')) {
          this.stats.characterDeaths++;
        }
        break;
    }

    // Track major events
    if (event.experience && event.experience > 100) {
      this.stats.majorEvents.push(event.title);
    }

    if (event.experience) {
      this.stats.totalExperience += event.experience;
    }
  }

  private extractLocationFromEvent(event: SessionEvent): string | null {
    // Simple location extraction - in a real implementation, 
    // this would be more sophisticated
    const locationKeywords = ['enters', 'arrives', 'discovers', 'reaches'];
    const description = event.description.toLowerCase();
    
    for (const keyword of locationKeywords) {
      const index = description.indexOf(keyword);
      if (index !== -1) {
        // Extract the next few words as potential location
        const words = description.substring(index).split(' ');
        if (words.length > 2) {
          return words.slice(1, 4).join(' ');
        }
      }
    }
    
    return null;
  }

  public async achieveMilestone(milestoneId: string): Promise<void> {
    const milestone = this.milestones.get(milestoneId);
    if (!milestone || milestone.achieved) {
      return;
    }

    milestone.achieved = true;
    milestone.achievedAt = new Date();
    
    console.log(`🏆 Milestone achieved: ${milestone.title}`);
    
    // Show achievement overlay
    await this.showMilestoneAchievement(milestone);
    
    this.emit('milestone-achieved', milestone);
    await this.saveProgressData();
  }

  private async showMilestoneAchievement(milestone: ProgressMilestone): Promise<void> {
    const overlay: OverlayElement = {
      id: `milestone_${milestone.id}`,
      type: 'text',
      position: { x: 50, y: 25, anchor: 'center' },
      size: { width: 600, height: 150, scale: 1 },
      style: {
        background: `linear-gradient(45deg, ${milestone.color || '#FFD700'}, #FFA500)`,
        border: '3px solid #FFFFFF',
        borderRadius: 20,
        color: '#FFFFFF',
        fontSize: 24,
        fontFamily: 'Arial Black',
        shadow: '0 0 30px rgba(255,215,0,0.8)'
      },
      data: {
        text: `${milestone.icon || '🏆'} MILESTONE ACHIEVED! ${milestone.icon || '🏆'}\n${milestone.title}\n${milestone.description}`,
        alignment: 'center'
      },
      visible: true,
      animation: {
        type: 'bounce',
        duration: 2000,
        easing: 'ease-out'
      }
    };

    await this.overlayGenerator.showOverlay(overlay, 8000);
  }

  private async checkMilestoneAchievements(): Promise<void> {
    // Check level milestones
    if (this.campaign && this.campaign.characters.length > 0) {
      const maxLevel = Math.max(...this.campaign.characters.map(c => c.level));
      for (let level = 2; level <= maxLevel; level++) {
        await this.achieveMilestone(`level_${level}`);
      }
    }

    // Check achievement milestones
    if (this.stats.criticalHits >= 10) {
      await this.achieveMilestone('crit_master');
    }

    if (this.stats.sessionsPlayed >= 5 && this.stats.characterDeaths === 0) {
      await this.achieveMilestone('survivor');
    }

    if (this.stats.locationsVisited.length >= 10) {
      await this.achieveMilestone('explorer');
    }

    if (this.stats.treasureFound >= 1000) { // Assuming gold value
      await this.achieveMilestone('wealthy');
    }
  }

  // Overlay creation methods
  public async showProgressOverlay(duration: number = 30000): Promise<void> {
    if (!this.campaign) {
      throw new Error('No active campaign');
    }

    const overlay = await this.createProgressOverlay();
    await this.overlayGenerator.showOverlay(overlay, duration);
    this.activeOverlays.set(overlay.id, overlay);
  }

  private async createProgressOverlay(): Promise<OverlayElement> {
    const canvas = createCanvas(800, 600);
    const ctx = canvas.getContext('2d');
    
    await this.drawProgressBackground(ctx, canvas.width, canvas.height);
    await this.drawCampaignInfo(ctx);
    await this.drawStats(ctx);
    await this.drawRecentMilestones(ctx);
    
    // Convert to data URL
    const dataUrl = canvas.toDataURL();
    
    return {
      id: `campaign_progress_${Date.now()}`,
      type: 'image',
      position: { x: 10, y: 10, anchor: 'top-left' },
      size: { width: 800, height: 600, scale: 0.8 },
      style: {
        borderRadius: 15,
        shadow: '0 0 20px rgba(0,0,0,0.5)'
      },
      data: {
        src: dataUrl
      },
      visible: true,
      animation: {
        type: 'fade',
        duration: 1500,
        easing: 'ease-in-out'
      }
    };
  }

  private async drawProgressBackground(ctx: CanvasRenderingContext2D, width: number, height: number): Promise<void> {
    // Gradient background
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, '#1a1a2e');
    gradient.addColorStop(1, '#16213e');
    
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);
    
    // Border
    ctx.strokeStyle = '#FFD700';
    ctx.lineWidth = 3;
    ctx.strokeRect(5, 5, width - 10, height - 10);
    
    // Title
    ctx.fillStyle = '#FFD700';
    ctx.font = 'bold 32px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Campaign Progress', width / 2, 45);
  }

  private async drawCampaignInfo(ctx: CanvasRenderingContext2D): Promise<void> {
    if (!this.campaign) return;

    ctx.fillStyle = '#FFFFFF';
    ctx.font = '24px Arial';
    ctx.textAlign = 'left';
    
    ctx.fillText(`Campaign: ${this.campaign.name}`, 30, 90);
    ctx.font = '18px Arial';
    ctx.fillStyle = '#CCCCCC';
    ctx.fillText(`Sessions Played: ${this.stats.sessionsPlayed}`, 30, 120);
    ctx.fillText(`Total Playtime: ${this.stats.totalPlaytime.toFixed(1)} hours`, 30, 145);
    ctx.fillText(`Average Level: ${this.stats.averageLevel.toFixed(1)}`, 30, 170);
  }

  private async drawStats(ctx: CanvasRenderingContext2D): Promise<void> {
    ctx.fillStyle = '#FFD700';
    ctx.font = 'bold 20px Arial';
    ctx.fillText('Campaign Statistics', 30, 210);
    
    ctx.fillStyle = '#FFFFFF';
    ctx.font = '16px Arial';
    
    const stats = [
      `Enemies Defeated: ${this.stats.enemiesDefeated}`,
      `Treasure Found: ${this.stats.treasureFound} items`,
      `Locations Visited: ${this.stats.locationsVisited.length}`,
      `Character Deaths: ${this.stats.characterDeaths}`,
      `Critical Hits: ${this.stats.criticalHits}`,
      `Total Experience: ${this.stats.totalExperience.toLocaleString()} XP`
    ];
    
    stats.forEach((stat, index) => {
      ctx.fillText(stat, 30, 240 + (index * 25));
    });
  }

  private async drawRecentMilestones(ctx: CanvasRenderingContext2D): Promise<void> {
    const achievedMilestones = Array.from(this.milestones.values())
      .filter(m => m.achieved)
      .sort((a, b) => (b.achievedAt?.getTime() || 0) - (a.achievedAt?.getTime() || 0))
      .slice(0, 5);

    if (achievedMilestones.length === 0) return;

    ctx.fillStyle = '#FFD700';
    ctx.font = 'bold 20px Arial';
    ctx.fillText('Recent Achievements', 30, 410);

    achievedMilestones.forEach((milestone, index) => {
      ctx.fillStyle = milestone.color || '#4CAF50';
      ctx.font = '14px Arial';
      
      const y = 440 + (index * 25);
      ctx.fillText(`${milestone.icon || '🏆'} ${milestone.title}`, 30, y);
      
      if (milestone.achievedAt) {
        ctx.fillStyle = '#CCCCCC';
        ctx.font = '12px Arial';
        ctx.fillText(milestone.achievedAt.toLocaleDateString(), 450, y);
      }
    });
  }

  // Statistics and analytics
  public getProgressSummary(): any {
    const totalMilestones = this.milestones.size;
    const achievedMilestones = Array.from(this.milestones.values()).filter(m => m.achieved).length;
    const progressPercentage = totalMilestones > 0 ? (achievedMilestones / totalMilestones) * 100 : 0;

    return {
      campaign: this.campaign?.name || 'Unknown',
      stats: this.stats,
      milestones: {
        total: totalMilestones,
        achieved: achievedMilestones,
        percentage: Math.round(progressPercentage)
      },
      recentAchievements: Array.from(this.milestones.values())
        .filter(m => m.achieved && m.achievedAt)
        .sort((a, b) => (b.achievedAt?.getTime() || 0) - (a.achievedAt?.getTime() || 0))
        .slice(0, 5)
        .map(m => ({
          title: m.title,
          achievedAt: m.achievedAt,
          type: m.type
        }))
    };
  }

  public getMilestonesByType(type: ProgressMilestone['type']): ProgressMilestone[] {
    return Array.from(this.milestones.values()).filter(m => m.type === type);
  }

  public getUpcomingMilestones(): ProgressMilestone[] {
    return Array.from(this.milestones.values())
      .filter(m => !m.achieved)
      .sort((a, b) => (a.value || 0) - (b.value || 0))
      .slice(0, 5);
  }

  // Data tracking methods for integration
  public trackCriticalHit(): void {
    this.stats.criticalHits++;
    this.checkMilestoneAchievements();
  }

  public trackCriticalMiss(): void {
    this.stats.criticalMisses++;
  }

  public trackCharacterDeath(): void {
    this.stats.characterDeaths++;
  }

  public updateCharacterLevels(characters: Character[]): void {
    if (characters.length > 0) {
      const totalLevels = characters.reduce((sum, char) => sum + char.level, 0);
      this.stats.averageLevel = totalLevels / characters.length;
      this.checkMilestoneAchievements();
    }
  }

  // Cleanup
  public async shutdown(): Promise<void> {
    await this.saveProgressData();
    this.activeOverlays.clear();
    console.log('🗺️  Campaign progress system shut down');
  }

  // Getters
  public getCampaign(): Campaign | null {
    return this.campaign;
  }

  public getStats(): CampaignStats {
    return { ...this.stats };
  }

  public getMilestones(): Map<string, ProgressMilestone> {
    return new Map(this.milestones);
  }
}