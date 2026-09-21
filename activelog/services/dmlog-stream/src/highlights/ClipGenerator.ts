import { EventEmitter } from 'events';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as ffmpeg from 'fluent-ffmpeg';
import { StreamHighlight, SessionEvent, StreamAnalytics, StreamSession } from '../types';

export class ClipGenerator extends EventEmitter {
  private recordingPath: string;
  private outputPath: string;
  private session: StreamSession | null = null;
  private highlights: StreamHighlight[] = [];
  private isRecording: boolean = false;
  private recordingStartTime: Date | null = null;
  private pendingClips: Map<string, StreamHighlight> = new Map();
  private clipQueue: StreamHighlight[] = [];
  private processingClips: boolean = false;

  constructor(recordingPath: string, outputPath: string) {
    super();
    this.recordingPath = recordingPath;
    this.outputPath = outputPath;
  }

  public async initialize(): Promise<void> {
    try {
      await fs.mkdir(this.outputPath, { recursive: true });
      console.log('🎬 Highlight clip generator initialized');
    } catch (error) {
      console.error('Error initializing clip generator:', error);
      throw error;
    }
  }

  public startSession(session: StreamSession): void {
    this.session = session;
    this.isRecording = true;
    this.recordingStartTime = new Date();
    this.highlights = [];
    
    console.log(`🔴 Started recording session: ${session.title}`);
    this.emit('recording-started', session);
  }

  public stopSession(): void {
    this.isRecording = false;
    this.recordingStartTime = null;
    
    console.log('⏹️  Stopped recording session');
    this.emit('recording-stopped');
    
    // Process any pending clips
    this.processClipQueue();
  }

  // Auto-detect highlights based on events
  public async detectHighlight(event: SessionEvent): Promise<StreamHighlight | null> {
    if (!this.isRecording || !this.session) {
      return null;
    }

    const score = this.calculateHighlightScore(event);
    if (score < 0.6) { // Threshold for auto-detection
      return null;
    }

    const highlight = await this.createHighlight(event, score, 'auto');
    if (highlight) {
      this.highlights.push(highlight);
      this.clipQueue.push(highlight);
      this.emit('highlight-detected', highlight);
      
      // Start processing if not already running
      if (!this.processingClips) {
        this.processClipQueue();
      }
    }

    return highlight;
  }

  private calculateHighlightScore(event: SessionEvent): number {
    let score = 0;

    // Base score by event type
    const typeScores = {
      'combat': 0.7,
      'roleplay': 0.5,
      'discovery': 0.8,
      'puzzle': 0.6,
      'social': 0.4,
      'exploration': 0.3
    };
    score += typeScores[event.type] || 0.3;

    // Keyword analysis in description
    const highValueKeywords = [
      'critical', 'nat 20', 'natural 20', 'fumble', 'nat 1',
      'death save', 'unconscious', 'dies', 'revived',
      'boss', 'final', 'victory', 'defeat',
      'treasure', 'legendary', 'artifact',
      'surprise', 'ambush', 'trap',
      'revelation', 'plot twist', 'betrayal'
    ];

    const description = event.description.toLowerCase();
    highValueKeywords.forEach(keyword => {
      if (description.includes(keyword)) {
        score += 0.3;
      }
    });

    // Participant involvement (more players = potentially more interesting)
    if (event.participants.length >= 3) {
      score += 0.2;
    }

    // Outcome significance
    if (event.outcome && event.outcome.length > 50) {
      score += 0.2;
    }

    // Experience reward indicates significance
    if (event.experience && event.experience > 100) {
      score += 0.3;
    }

    // Cap at 1.0
    return Math.min(score, 1.0);
  }

  // Manual highlight creation
  public async createManualHighlight(
    startTime: number,
    endTime: number,
    title: string,
    description?: string,
    type: StreamHighlight['type'] = 'custom'
  ): Promise<StreamHighlight> {
    if (!this.session) {
      throw new Error('No active session');
    }

    const highlight: StreamHighlight = {
      id: this.generateHighlightId(),
      sessionId: this.session.id,
      startTime,
      endTime,
      title,
      description,
      type,
      participants: [],
      tags: [],
      score: 1.0,
      createdBy: 'manual',
      status: 'pending'
    };

    this.highlights.push(highlight);
    this.clipQueue.push(highlight);
    
    this.emit('highlight-created', highlight);
    
    if (!this.processingClips) {
      this.processClipQueue();
    }

    return highlight;
  }

  private async createHighlight(
    event: SessionEvent,
    score: number,
    createdBy: 'auto' | 'manual'
  ): Promise<StreamHighlight | null> {
    if (!this.session || !this.recordingStartTime) {
      return null;
    }

    const now = new Date();
    const sessionDuration = now.getTime() - this.recordingStartTime.getTime();
    const eventTime = sessionDuration / 1000; // Convert to seconds

    // Create highlight with buffer before and after
    const bufferSeconds = 10;
    const highlightDuration = this.estimateHighlightDuration(event);
    
    const highlight: StreamHighlight = {
      id: this.generateHighlightId(),
      sessionId: this.session.id,
      startTime: Math.max(0, eventTime - bufferSeconds),
      endTime: eventTime + highlightDuration + bufferSeconds,
      title: event.title || 'Stream Highlight',
      description: event.description,
      type: this.mapEventTypeToHighlightType(event.type),
      participants: event.participants,
      tags: this.generateTags(event),
      score,
      createdBy,
      status: 'pending'
    };

    return highlight;
  }

  private estimateHighlightDuration(event: SessionEvent): number {
    // Estimate duration based on event type and description length
    const baseDurations = {
      'combat': 30,
      'roleplay': 20,
      'discovery': 15,
      'puzzle': 25,
      'social': 15,
      'exploration': 10
    };

    let duration = baseDurations[event.type] || 15;
    
    // Adjust based on description length
    if (event.description.length > 200) {
      duration += 10;
    }
    
    return duration;
  }

  private mapEventTypeToHighlightType(eventType: SessionEvent['type']): StreamHighlight['type'] {
    const mapping = {
      'combat': 'combat' as const,
      'roleplay': 'roleplay' as const,
      'exploration': 'roleplay' as const,
      'puzzle': 'custom' as const,
      'social': 'roleplay' as const,
      'discovery': 'custom' as const
    };

    return mapping[eventType] || 'custom';
  }

  private generateTags(event: SessionEvent): string[] {
    const tags: string[] = [event.type];
    
    const description = event.description.toLowerCase();
    
    // Add specific tags based on content
    if (description.includes('critical') || description.includes('nat 20')) {
      tags.push('critical-hit');
    }
    if (description.includes('fumble') || description.includes('nat 1')) {
      tags.push('fumble');
    }
    if (description.includes('death') || description.includes('unconscious')) {
      tags.push('dramatic');
    }
    if (description.includes('treasure') || description.includes('loot')) {
      tags.push('treasure');
    }
    if (description.includes('boss') || description.includes('final')) {
      tags.push('boss-fight');
    }

    // Add participant tags
    event.participants.forEach(participant => {
      tags.push(`character-${participant.toLowerCase().replace(/\s+/g, '-')}`);
    });

    return tags;
  }

  // Process clip generation queue
  private async processClipQueue(): Promise<void> {
    if (this.processingClips || this.clipQueue.length === 0) {
      return;
    }

    this.processingClips = true;
    console.log(`🎬 Processing ${this.clipQueue.length} clips...`);

    while (this.clipQueue.length > 0) {
      const highlight = this.clipQueue.shift()!;
      try {
        await this.generateClip(highlight);
      } catch (error) {
        console.error(`Error processing clip ${highlight.id}:`, error);
        highlight.status = 'failed';
        this.emit('clip-failed', { highlight, error });
      }
    }

    this.processingClips = false;
    console.log('✅ Finished processing clip queue');
  }

  private async generateClip(highlight: StreamHighlight): Promise<void> {
    if (!this.session) {
      throw new Error('No active session');
    }

    highlight.status = 'processing';
    this.emit('clip-processing', highlight);

    const inputFile = path.join(this.recordingPath, `${this.session.id}.mp4`);
    const outputFile = path.join(this.outputPath, `${highlight.id}.mp4`);
    const thumbnailFile = path.join(this.outputPath, `${highlight.id}_thumb.jpg`);

    // Check if input file exists
    try {
      await fs.access(inputFile);
    } catch {
      throw new Error(`Recording file not found: ${inputFile}`);
    }

    return new Promise((resolve, reject) => {
      // Generate clip with FFmpeg
      ffmpeg(inputFile)
        .seekInput(highlight.startTime)
        .duration(highlight.endTime - highlight.startTime)
        .videoCodec('libx264')
        .audioCodec('aac')
        .size('1920x1080')
        .fps(30)
        .videoBitrate('2500k')
        .audioBitrate('128k')
        // Add title overlay
        .videoFilters([
          {
            filter: 'drawtext',
            options: {
              text: highlight.title,
              fontfile: 'arial.ttf',
              fontsize: 24,
              fontcolor: 'white',
              x: '(w-tw)/2',
              y: 50,
              shadowcolor: 'black',
              shadowx: 2,
              shadowy: 2
            }
          }
        ])
        .on('start', (commandLine) => {
          console.log(`🎬 Generating clip: ${highlight.title}`);
          console.log(`Command: ${commandLine}`);
        })
        .on('progress', (progress) => {
          this.emit('clip-progress', { highlight, progress: progress.percent });
        })
        .on('end', async () => {
          try {
            // Generate thumbnail
            await this.generateThumbnail(inputFile, highlight, thumbnailFile);
            
            highlight.clipUrl = outputFile;
            highlight.thumbnail = thumbnailFile;
            highlight.status = 'ready';
            
            console.log(`✅ Generated clip: ${highlight.title}`);
            this.emit('clip-ready', highlight);
            resolve();
          } catch (error) {
            reject(error);
          }
        })
        .on('error', (error) => {
          console.error(`❌ Error generating clip: ${error.message}`);
          reject(error);
        })
        .save(outputFile);
    });
  }

  private async generateThumbnail(
    inputFile: string,
    highlight: StreamHighlight,
    thumbnailFile: string
  ): Promise<void> {
    const thumbnailTime = highlight.startTime + (highlight.endTime - highlight.startTime) / 2;
    
    return new Promise((resolve, reject) => {
      ffmpeg(inputFile)
        .seekInput(thumbnailTime)
        .frames(1)
        .size('320x180')
        .format('image2')
        .on('end', () => {
          console.log(`📸 Generated thumbnail for: ${highlight.title}`);
          resolve();
        })
        .on('error', reject)
        .save(thumbnailFile);
    });
  }

  // Batch operations for session end
  public async generateSessionHighlights(): Promise<StreamHighlight[]> {
    if (!this.session) {
      throw new Error('No active session');
    }

    console.log('🎬 Generating session highlight reel...');

    // Get top highlights by score
    const topHighlights = this.highlights
      .filter(h => h.score >= 0.8)
      .sort((a, b) => b.score - a.score)
      .slice(0, 5);

    if (topHighlights.length === 0) {
      console.log('No high-quality highlights found for session reel');
      return [];
    }

    // Create compilation highlight
    const compilation: StreamHighlight = {
      id: `${this.session.id}_compilation`,
      sessionId: this.session.id,
      startTime: 0,
      endTime: 0,
      title: `${this.session.title} - Best Moments`,
      description: 'Compilation of the best moments from this session',
      type: 'custom',
      participants: [...new Set(topHighlights.flatMap(h => h.participants))],
      tags: ['compilation', 'best-of'],
      score: 1.0,
      createdBy: 'auto',
      status: 'pending'
    };

    await this.generateCompilation(compilation, topHighlights);
    return [compilation, ...topHighlights];
  }

  private async generateCompilation(
    compilation: StreamHighlight,
    highlights: StreamHighlight[]
  ): Promise<void> {
    if (!this.session) {
      throw new Error('No active session');
    }

    const inputFile = path.join(this.recordingPath, `${this.session.id}.mp4`);
    const outputFile = path.join(this.outputPath, `${compilation.id}.mp4`);
    
    return new Promise((resolve, reject) => {
      let command = ffmpeg();

      // Add each highlight as input
      highlights.forEach(highlight => {
        command = command.input(inputFile)
          .seekInput(highlight.startTime)
          .duration(highlight.endTime - highlight.startTime);
      });

      // Concatenate clips with transitions
      const filterComplex = highlights.map((_, index) => 
        `[${index}:v][${index}:a]`
      ).join('') + `concat=n=${highlights.length}:v=1:a=1[outv][outa]`;

      command
        .complexFilter(filterComplex)
        .map('[outv]').map('[outa]')
        .videoCodec('libx264')
        .audioCodec('aac')
        .on('end', () => {
          compilation.clipUrl = outputFile;
          compilation.status = 'ready';
          console.log('✅ Generated session compilation');
          resolve();
        })
        .on('error', reject)
        .save(outputFile);
    });
  }

  // Analytics and management
  public getHighlights(): StreamHighlight[] {
    return this.highlights;
  }

  public getHighlightsByTag(tag: string): StreamHighlight[] {
    return this.highlights.filter(h => h.tags.includes(tag));
  }

  public getHighlightsByType(type: StreamHighlight['type']): StreamHighlight[] {
    return this.highlights.filter(h => h.type === type);
  }

  public async deleteHighlight(highlightId: string): Promise<void> {
    const highlight = this.highlights.find(h => h.id === highlightId);
    if (!highlight) {
      throw new Error('Highlight not found');
    }

    // Delete files if they exist
    if (highlight.clipUrl) {
      try {
        await fs.unlink(highlight.clipUrl);
      } catch {} // Ignore errors
    }
    
    if (highlight.thumbnail) {
      try {
        await fs.unlink(highlight.thumbnail);
      } catch {} // Ignore errors
    }

    // Remove from array
    this.highlights = this.highlights.filter(h => h.id !== highlightId);
    
    console.log(`🗑️  Deleted highlight: ${highlight.title}`);
    this.emit('highlight-deleted', highlightId);
  }

  public async exportHighlightMetadata(): Promise<string> {
    if (!this.session) {
      throw new Error('No active session');
    }

    const metadata = {
      sessionId: this.session.id,
      sessionTitle: this.session.title,
      generatedAt: new Date().toISOString(),
      highlights: this.highlights.map(h => ({
        id: h.id,
        title: h.title,
        description: h.description,
        type: h.type,
        startTime: h.startTime,
        endTime: h.endTime,
        duration: h.endTime - h.startTime,
        participants: h.participants,
        tags: h.tags,
        score: h.score,
        createdBy: h.createdBy,
        status: h.status,
        clipUrl: h.clipUrl,
        thumbnail: h.thumbnail
      }))
    };

    const metadataFile = path.join(this.outputPath, `${this.session.id}_highlights.json`);
    await fs.writeFile(metadataFile, JSON.stringify(metadata, null, 2));
    
    console.log(`📄 Exported highlight metadata to: ${metadataFile}`);
    return metadataFile;
  }

  // Utility methods
  private generateHighlightId(): string {
    return `highlight_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  public getQueueStatus(): { processing: boolean; queueLength: number; totalHighlights: number } {
    return {
      processing: this.processingClips,
      queueLength: this.clipQueue.length,
      totalHighlights: this.highlights.length
    };
  }

  // Integration methods for other systems
  public async createDiceRollHighlight(roll: any): Promise<StreamHighlight | null> {
    if (roll.result.critical || roll.result.fumble) {
      const event: SessionEvent = {
        id: `dice_${roll.id}`,
        timestamp: new Date(),
        type: 'roleplay',
        title: roll.result.critical ? 'Critical Hit!' : 'Critical Fumble!',
        description: `${roll.username} rolled ${roll.notation}: ${roll.result.breakdown}`,
        participants: [roll.username],
        outcome: roll.result.critical ? 'Success' : 'Failure'
      };

      return await this.detectHighlight(event);
    }
    return null;
  }

  public async createDonationHighlight(donation: any): Promise<StreamHighlight | null> {
    if (donation.amount >= 50) { // Significant donations
      const event: SessionEvent = {
        id: `donation_${donation.id}`,
        timestamp: new Date(),
        type: 'social',
        title: `${donation.amount} Donation!`,
        description: `${donation.username} donated $${donation.amount}: ${donation.message || 'Thank you!'}`,
        participants: [donation.username],
        outcome: 'Donation received'
      };

      return await this.detectHighlight(event);
    }
    return null;
  }
}