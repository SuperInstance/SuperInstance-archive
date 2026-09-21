import { EventEmitter } from 'events';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as ffmpeg from 'fluent-ffmpeg';
import { 
  StreamSession, 
  StreamChapter, 
  SessionEvent, 
  StreamHighlight,
  StreamAnalytics 
} from '../types';

export interface ChapterMetadata {
  title: string;
  start: number; // seconds
  end?: number; // seconds
  description?: string;
  thumbnail?: string;
  type: StreamChapter['type'];
  significance: number; // 0-1 score
}

export interface VODMetadata {
  title: string;
  description: string;
  chapters: ChapterMetadata[];
  highlights: Array<{
    time: number;
    title: string;
    description: string;
  }>;
  tags: string[];
  duration: number;
}

export class VODChapterGenerator extends EventEmitter {
  private outputPath: string;
  private session: StreamSession | null = null;
  private chapters: StreamChapter[] = [];
  private events: SessionEvent[] = [];
  private highlights: StreamHighlight[] = [];
  private analytics: StreamAnalytics | null = null;
  private vodMetadata: VODMetadata | null = null;

  constructor(outputPath: string) {
    super();
    this.outputPath = outputPath;
  }

  public async initialize(): Promise<void> {
    try {
      await fs.mkdir(this.outputPath, { recursive: true });
      console.log('📹 VOD chapter generator initialized');
      this.emit('initialized');
    } catch (error) {
      console.error('Error initializing VOD chapter generator:', error);
      throw error;
    }
  }

  public startSession(session: StreamSession): void {
    this.session = session;
    this.chapters = [];
    this.events = [];
    this.highlights = [];
    this.analytics = null;
    this.vodMetadata = null;
    
    console.log(`📹 Started VOD processing for: ${session.title}`);
    this.emit('session-started', session);
  }

  public addEvent(event: SessionEvent): void {
    if (!this.session) return;
    
    this.events.push(event);
    this.emit('event-added', event);
  }

  public addHighlight(highlight: StreamHighlight): void {
    if (!this.session) return;
    
    this.highlights.push(highlight);
    this.emit('highlight-added', highlight);
  }

  public setAnalytics(analytics: StreamAnalytics): void {
    this.analytics = analytics;
  }

  public async generateChapters(): Promise<StreamChapter[]> {
    if (!this.session) {
      throw new Error('No active session');
    }

    console.log('📝 Generating VOD chapters...');
    
    // Clear existing chapters
    this.chapters = [];
    
    // Generate chapters based on different strategies
    await this.generateIntroChapter();
    await this.generateEventBasedChapters();
    await this.generateHighlightChapters();
    await this.generateOutroChapter();
    
    // Merge and optimize chapters
    this.optimizeChapters();
    
    // Generate thumbnails for chapters
    await this.generateChapterThumbnails();
    
    console.log(`✅ Generated ${this.chapters.length} chapters`);
    this.emit('chapters-generated', this.chapters);
    
    return this.chapters;
  }

  private async generateIntroChapter(): Promise<void> {
    if (!this.session) return;

    // Create intro chapter (first 2-5 minutes typically)
    const introDuration = Math.min(300, this.getSessionDuration() * 0.05); // Max 5 min or 5% of stream
    
    const introChapter: StreamChapter = {
      id: `${this.session.id}_intro`,
      sessionId: this.session.id,
      startTime: 0,
      endTime: introDuration,
      title: 'Stream Introduction',
      description: 'Welcome, introductions, and session setup',
      type: 'intro'
    };

    this.chapters.push(introChapter);
  }

  private async generateEventBasedChapters(): Promise<void> {
    if (!this.session || this.events.length === 0) return;

    // Group events by type and time proximity
    const eventGroups = this.groupEventsByProximity(this.events, 300); // 5-minute windows
    
    for (const group of eventGroups) {
      const chapter = await this.createChapterFromEventGroup(group);
      if (chapter) {
        this.chapters.push(chapter);
      }
    }
  }

  private groupEventsByProximity(events: SessionEvent[], windowSeconds: number): SessionEvent[][] {
    if (events.length === 0) return [];
    
    const groups: SessionEvent[][] = [];
    let currentGroup: SessionEvent[] = [events[0]];
    
    for (let i = 1; i < events.length; i++) {
      const timeDiff = events[i].timestamp.getTime() - events[i-1].timestamp.getTime();
      
      if (timeDiff <= windowSeconds * 1000) {
        currentGroup.push(events[i]);
      } else {
        if (currentGroup.length > 0) {
          groups.push(currentGroup);
        }
        currentGroup = [events[i]];
      }
    }
    
    if (currentGroup.length > 0) {
      groups.push(currentGroup);
    }
    
    return groups;
  }

  private async createChapterFromEventGroup(events: SessionEvent[]): Promise<StreamChapter | null> {
    if (!this.session || events.length === 0) return null;

    const firstEvent = events[0];
    const lastEvent = events[events.length - 1];
    
    // Determine chapter type based on dominant event type
    const eventTypes = events.map(e => e.type);
    const dominantType = this.getMostFrequentEventType(eventTypes);
    
    const startTime = this.getEventTimestamp(firstEvent);
    const endTime = this.getEventTimestamp(lastEvent) + this.estimateEventDuration(lastEvent);
    
    // Skip very short chapters (less than 2 minutes)
    if (endTime - startTime < 120) {
      return null;
    }
    
    const title = this.generateChapterTitle(events, dominantType);
    const description = this.generateChapterDescription(events);
    
    return {
      id: `${this.session.id}_${dominantType}_${startTime}`,
      sessionId: this.session.id,
      startTime,
      endTime,
      title,
      description,
      type: this.mapEventTypeToChapterType(dominantType)
    };
  }

  private getMostFrequentEventType(types: string[]): string {
    const counts = types.reduce((acc, type) => {
      acc[type] = (acc[type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    
    return Object.entries(counts).reduce((a, b) => 
      counts[a[0]] > counts[b[0]] ? a : b
    )[0];
  }

  private generateChapterTitle(events: SessionEvent[], dominantType: string): string {
    const titles = {
      'combat': 'Battle Sequence',
      'roleplay': 'Roleplay Scene',
      'exploration': 'Exploration',
      'puzzle': 'Puzzle & Problem Solving',
      'social': 'Social Interaction',
      'discovery': 'Discovery & Investigation'
    };

    let baseTitle = titles[dominantType as keyof typeof titles] || 'Adventure Segment';
    
    // Add specific details if available
    const significantEvents = events.filter(e => 
      e.title && (e.experience || 0) > 50
    );
    
    if (significantEvents.length > 0) {
      const mainEvent = significantEvents.sort((a, b) => 
        (b.experience || 0) - (a.experience || 0)
      )[0];
      
      baseTitle = mainEvent.title || baseTitle;
    }

    return baseTitle;
  }

  private generateChapterDescription(events: SessionEvent[]): string {
    const eventSummaries = events
      .filter(e => e.description && e.description.length > 20)
      .slice(0, 3) // Top 3 events
      .map(e => e.description);
    
    if (eventSummaries.length === 0) {
      return 'Adventure continues with exciting developments.';
    }
    
    return eventSummaries.join(' ');
  }

  private mapEventTypeToChapterType(eventType: string): StreamChapter['type'] {
    const mapping = {
      'combat': 'combat' as const,
      'roleplay': 'roleplay' as const,
      'exploration': 'exploration' as const,
      'puzzle': 'roleplay' as const,
      'social': 'roleplay' as const,
      'discovery': 'exploration' as const
    };

    return mapping[eventType as keyof typeof mapping] || 'roleplay';
  }

  private getEventTimestamp(event: SessionEvent): number {
    if (!this.session) return 0;
    
    const sessionStart = this.session.startTime.getTime();
    const eventTime = event.timestamp.getTime();
    
    return Math.max(0, (eventTime - sessionStart) / 1000); // Convert to seconds
  }

  private estimateEventDuration(event: SessionEvent): number {
    const baseDurations = {
      'combat': 600, // 10 minutes
      'roleplay': 300, // 5 minutes
      'exploration': 180, // 3 minutes
      'puzzle': 420, // 7 minutes
      'social': 240, // 4 minutes
      'discovery': 120 // 2 minutes
    };

    return baseDurations[event.type as keyof typeof baseDurations] || 300;
  }

  private async generateHighlightChapters(): Promise<void> {
    if (!this.session || this.highlights.length === 0) return;

    // Create chapters for significant highlights
    const significantHighlights = this.highlights
      .filter(h => h.score >= 0.8) // High-quality highlights only
      .sort((a, b) => b.score - a.score)
      .slice(0, 5); // Top 5 highlights

    for (const highlight of significantHighlights) {
      const chapter: StreamChapter = {
        id: `${this.session.id}_highlight_${highlight.id}`,
        sessionId: this.session.id,
        startTime: Math.max(0, highlight.startTime - 30), // 30s buffer before
        endTime: highlight.endTime + 30, // 30s buffer after
        title: `🌟 ${highlight.title}`,
        description: highlight.description || 'Epic moment from the stream',
        type: 'roleplay' // Most highlights are roleplay moments
      };

      this.chapters.push(chapter);
    }
  }

  private async generateOutroChapter(): Promise<void> {
    if (!this.session) return;

    const sessionDuration = this.getSessionDuration();
    const outroDuration = Math.min(180, sessionDuration * 0.05); // Max 3 min or 5% of stream
    
    if (sessionDuration > outroDuration) {
      const outroChapter: StreamChapter = {
        id: `${this.session.id}_outro`,
        sessionId: this.session.id,
        startTime: sessionDuration - outroDuration,
        endTime: sessionDuration,
        title: 'Session Wrap-up',
        description: 'Session summary, goodbyes, and next time preview',
        type: 'outro'
      };

      this.chapters.push(outroChapter);
    }
  }

  private getSessionDuration(): number {
    if (!this.session) return 0;
    
    const endTime = this.session.endTime || new Date();
    return (endTime.getTime() - this.session.startTime.getTime()) / 1000;
  }

  private optimizeChapters(): void {
    if (this.chapters.length === 0) return;

    // Sort chapters by start time
    this.chapters.sort((a, b) => a.startTime - b.startTime);
    
    // Merge overlapping chapters
    const optimized: StreamChapter[] = [];
    let current = this.chapters[0];
    
    for (let i = 1; i < this.chapters.length; i++) {
      const next = this.chapters[i];
      
      // If chapters overlap significantly, merge them
      if (next.startTime < current.endTime! - 60) { // 1-minute buffer
        current = this.mergeChapters(current, next);
      } else {
        optimized.push(current);
        current = next;
      }
    }
    
    optimized.push(current);
    
    // Remove very short chapters (less than 2 minutes)
    this.chapters = optimized.filter(chapter => 
      (chapter.endTime || 0) - chapter.startTime >= 120
    );
    
    // Ensure no gaps between chapters
    this.fillChapterGaps();
  }

  private mergeChapters(chapter1: StreamChapter, chapter2: StreamChapter): StreamChapter {
    const combinedTitle = chapter1.type === chapter2.type ? 
      chapter1.title : 
      `${chapter1.title} & ${chapter2.title}`;
    
    return {
      ...chapter1,
      endTime: Math.max(chapter1.endTime || 0, chapter2.endTime || 0),
      title: combinedTitle,
      description: `${chapter1.description} ${chapter2.description}`.trim()
    };
  }

  private fillChapterGaps(): void {
    if (this.chapters.length <= 1) return;

    const filled: StreamChapter[] = [];
    
    for (let i = 0; i < this.chapters.length; i++) {
      filled.push(this.chapters[i]);
      
      // Check for gap between this chapter and the next
      if (i < this.chapters.length - 1) {
        const current = this.chapters[i];
        const next = this.chapters[i + 1];
        const gap = next.startTime - (current.endTime || 0);
        
        // If there's a significant gap (more than 5 minutes), create a filler chapter
        if (gap > 300) {
          const fillerChapter: StreamChapter = {
            id: `${this.session!.id}_filler_${i}`,
            sessionId: this.session!.id,
            startTime: current.endTime || 0,
            endTime: next.startTime,
            title: 'General Gameplay',
            description: 'Continued adventure and character interactions',
            type: 'roleplay'
          };
          
          filled.push(fillerChapter);
        }
      }
    }
    
    this.chapters = filled;
  }

  private async generateChapterThumbnails(): Promise<void> {
    if (!this.session) return;

    const videoPath = path.join(this.outputPath, `${this.session.id}.mp4`);
    
    try {
      await fs.access(videoPath);
    } catch {
      console.warn('Video file not found for thumbnail generation');
      return;
    }

    console.log('📸 Generating chapter thumbnails...');
    
    for (const chapter of this.chapters) {
      try {
        const thumbnailPath = path.join(
          this.outputPath, 
          `${chapter.id}_thumb.jpg`
        );
        
        await this.generateThumbnail(videoPath, chapter, thumbnailPath);
        chapter.thumbnail = thumbnailPath;
        
      } catch (error) {
        console.error(`Error generating thumbnail for chapter ${chapter.id}:`, error);
      }
    }
  }

  private generateThumbnail(
    videoPath: string, 
    chapter: StreamChapter, 
    outputPath: string
  ): Promise<void> {
    const thumbnailTime = chapter.startTime + ((chapter.endTime || chapter.startTime) - chapter.startTime) / 2;
    
    return new Promise((resolve, reject) => {
      ffmpeg(videoPath)
        .seekInput(thumbnailTime)
        .frames(1)
        .size('320x180')
        .format('image2')
        .on('end', () => {
          console.log(`📸 Generated thumbnail: ${chapter.title}`);
          resolve();
        })
        .on('error', reject)
        .save(outputPath);
    });
  }

  public async generateVODMetadata(): Promise<VODMetadata> {
    if (!this.session) {
      throw new Error('No active session');
    }

    if (this.chapters.length === 0) {
      await this.generateChapters();
    }

    const chapterMetadata: ChapterMetadata[] = this.chapters.map(chapter => ({
      title: chapter.title,
      start: chapter.startTime,
      end: chapter.endTime,
      description: chapter.description,
      thumbnail: chapter.thumbnail,
      type: chapter.type,
      significance: this.calculateChapterSignificance(chapter)
    }));

    const highlightMetadata = this.highlights
      .filter(h => h.score >= 0.7)
      .sort((a, b) => b.score - a.score)
      .slice(0, 10)
      .map(h => ({
        time: h.startTime,
        title: h.title,
        description: h.description || 'Epic moment'
      }));

    this.vodMetadata = {
      title: this.session.title,
      description: this.generateVODDescription(),
      chapters: chapterMetadata,
      highlights: highlightMetadata,
      tags: this.generateVODTags(),
      duration: this.getSessionDuration()
    };

    console.log('📋 Generated VOD metadata');
    this.emit('metadata-generated', this.vodMetadata);
    
    return this.vodMetadata;
  }

  private calculateChapterSignificance(chapter: StreamChapter): number {
    let significance = 0.5; // Base significance
    
    // Chapter type significance
    const typeSignificance = {
      'intro': 0.3,
      'outro': 0.3,
      'combat': 0.9,
      'roleplay': 0.7,
      'exploration': 0.6
    };
    
    significance *= typeSignificance[chapter.type] || 0.5;
    
    // Duration significance (longer chapters are often more significant)
    const duration = (chapter.endTime || 0) - chapter.startTime;
    if (duration > 1200) significance += 0.2; // 20+ minutes
    else if (duration > 600) significance += 0.1; // 10+ minutes
    
    // Highlight overlap (chapters containing highlights are more significant)
    const chapterHighlights = this.highlights.filter(h => 
      h.startTime >= chapter.startTime && 
      h.endTime <= (chapter.endTime || Infinity)
    );
    
    significance += chapterHighlights.length * 0.1;
    
    return Math.min(1.0, significance);
  }

  private generateVODDescription(): string {
    if (!this.session) return 'D&D Adventure Stream';

    let description = `${this.session.title}\n\n`;
    
    if (this.session.description) {
      description += `${this.session.description}\n\n`;
    }
    
    // Add chapter overview
    if (this.chapters.length > 0) {
      description += 'Chapters:\n';
      this.chapters.forEach((chapter, index) => {
        const timestamp = this.formatTimestamp(chapter.startTime);
        description += `${timestamp} - ${chapter.title}\n`;
      });
      description += '\n';
    }
    
    // Add highlights
    if (this.highlights.length > 0) {
      description += 'Highlights:\n';
      this.highlights
        .filter(h => h.score >= 0.8)
        .slice(0, 5)
        .forEach(highlight => {
          const timestamp = this.formatTimestamp(highlight.startTime);
          description += `${timestamp} - ${highlight.title}\n`;
        });
    }
    
    return description;
  }

  private generateVODTags(): string[] {
    const tags = ['DnD', 'TTRPG', 'Tabletop', 'RPG', 'Adventure'];
    
    // Add tags based on chapter content
    const chapterTypes = [...new Set(this.chapters.map(c => c.type))];
    chapterTypes.forEach(type => {
      if (type === 'combat') tags.push('Combat', 'Battle');
      if (type === 'roleplay') tags.push('Roleplay', 'Story');
      if (type === 'exploration') tags.push('Exploration', 'Discovery');
    });
    
    // Add tags based on events
    if (this.events.some(e => e.type === 'combat')) {
      tags.push('Epic Battles');
    }
    if (this.events.some(e => e.description.toLowerCase().includes('critical'))) {
      tags.push('Critical Hits');
    }
    if (this.events.some(e => e.description.toLowerCase().includes('death'))) {
      tags.push('Character Death', 'Drama');
    }
    
    return [...new Set(tags)]; // Remove duplicates
  }

  private formatTimestamp(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
      return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }
  }

  public async exportChapterFile(): Promise<string> {
    if (!this.session || this.chapters.length === 0) {
      throw new Error('No chapters to export');
    }

    const chapterData = {
      sessionId: this.session.id,
      sessionTitle: this.session.title,
      duration: this.getSessionDuration(),
      chapters: this.chapters.map(chapter => ({
        id: chapter.id,
        title: chapter.title,
        start: this.formatTimestamp(chapter.startTime),
        end: chapter.endTime ? this.formatTimestamp(chapter.endTime) : undefined,
        description: chapter.description,
        type: chapter.type,
        thumbnail: chapter.thumbnail
      })),
      metadata: this.vodMetadata,
      generatedAt: new Date().toISOString()
    };

    const exportPath = path.join(this.outputPath, `${this.session.id}_chapters.json`);
    await fs.writeFile(exportPath, JSON.stringify(chapterData, null, 2));
    
    console.log(`📄 Exported chapters to: ${exportPath}`);
    return exportPath;
  }

  public async exportYouTubeChapters(): Promise<string> {
    if (!this.session || this.chapters.length === 0) {
      throw new Error('No chapters to export');
    }

    // YouTube chapter format: timestamp - title
    const youtubeChapters = this.chapters
      .map(chapter => `${this.formatTimestamp(chapter.startTime)} ${chapter.title}`)
      .join('\n');

    const exportPath = path.join(this.outputPath, `${this.session.id}_youtube_chapters.txt`);
    await fs.writeFile(exportPath, youtubeChapters);
    
    console.log(`📺 Exported YouTube chapters to: ${exportPath}`);
    return exportPath;
  }

  // Analytics and reporting
  public getChapterStatistics(): any {
    if (this.chapters.length === 0) return null;

    const typeBreakdown = this.chapters.reduce((acc, chapter) => {
      acc[chapter.type] = (acc[chapter.type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const averageDuration = this.chapters.reduce((sum, chapter) => 
      sum + ((chapter.endTime || 0) - chapter.startTime), 0
    ) / this.chapters.length;

    return {
      totalChapters: this.chapters.length,
      typeBreakdown,
      averageDuration: Math.round(averageDuration),
      longestChapter: this.chapters.reduce((longest, chapter) => {
        const duration = (chapter.endTime || 0) - chapter.startTime;
        const longestDuration = (longest.endTime || 0) - longest.startTime;
        return duration > longestDuration ? chapter : longest;
      }),
      coverage: this.calculateChapterCoverage()
    };
  }

  private calculateChapterCoverage(): number {
    if (this.chapters.length === 0) return 0;
    
    const sessionDuration = this.getSessionDuration();
    const chaptersTime = this.chapters.reduce((sum, chapter) => 
      sum + ((chapter.endTime || 0) - chapter.startTime), 0
    );
    
    return sessionDuration > 0 ? (chaptersTime / sessionDuration) * 100 : 0;
  }

  // Getters
  public getChapters(): StreamChapter[] {
    return [...this.chapters];
  }

  public getVODMetadata(): VODMetadata | null {
    return this.vodMetadata;
  }

  public getSession(): StreamSession | null {
    return this.session;
  }
}