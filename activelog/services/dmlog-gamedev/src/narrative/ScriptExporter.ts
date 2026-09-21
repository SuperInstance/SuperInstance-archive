import { EventEmitter } from 'events';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as yaml from 'js-yaml';
import MarkdownIt from 'markdown-it';
import { 
  Campaign, 
  NarrativeStructure, 
  StoryAct, 
  DialogueEntry, 
  Character,
  NPC,
  Session,
  CutsceneScript
} from '../types';

export interface ScriptExportOptions {
  format: 'markdown' | 'fountain' | 'json' | 'yaml' | 'xml' | 'csv' | 'twine' | 'articy';
  includeStageDirections: boolean;
  includeCharacterNotes: boolean;
  includeMetadata: boolean;
  combineFiles: boolean;
  addTimestamps: boolean;
  localizeText: boolean;
  language: string;
}

export interface NarrativeScript {
  title: string;
  version: string;
  metadata: ScriptMetadata;
  acts: ScriptAct[];
  characters: ScriptCharacter[];
  locations: ScriptLocation[];
  themes: string[];
  notes: string[];
}

export interface ScriptMetadata {
  genre: string;
  target_audience: string;
  estimated_length: number; // in minutes
  complexity: 'simple' | 'moderate' | 'complex';
  tone: string[];
  pacing: 'slow' | 'moderate' | 'fast' | 'variable';
  interactive_elements: InteractiveElement[];
}

export interface ScriptAct {
  id: string;
  title: string;
  order: number;
  scenes: ScriptScene[];
  themes: string[];
  character_arcs: string[];
  plot_points: PlotPoint[];
  duration_estimate: number;
}

export interface ScriptScene {
  id: string;
  title: string;
  location: string;
  time_of_day?: string;
  weather?: string;
  atmosphere: string;
  participants: string[];
  dialogue: DialogueLine[];
  action_lines: ActionLine[];
  stage_directions: StageDirection[];
  narrative_purpose: string;
  emotional_beats: EmotionalBeat[];
}

export interface DialogueLine {
  speaker: string;
  text: string;
  subtext?: string;
  emotion: string;
  delivery_notes: string;
  interruptions: Interruption[];
  emphasis: TextEmphasis[];
  audio_cues: AudioCue[];
}

export interface ActionLine {
  description: string;
  characters_involved: string[];
  duration: number;
  complexity: 'simple' | 'moderate' | 'complex';
  visual_priority: 'low' | 'medium' | 'high';
}

export interface StageDirection {
  type: 'lighting' | 'sound' | 'movement' | 'props' | 'camera' | 'special_effect';
  description: string;
  timing: 'before' | 'during' | 'after';
  target?: string;
}

export interface EmotionalBeat {
  character: string;
  emotion: string;
  intensity: number; // 1-10
  trigger: string;
  expression: string;
}

export interface ScriptCharacter {
  id: string;
  name: string;
  role: 'protagonist' | 'antagonist' | 'supporting' | 'minor' | 'narrator';
  description: string;
  voice: VoiceProfile;
  arc_summary: string;
  relationships: CharacterRelationship[];
  iconic_lines: string[];
  character_function: string[];
}

export interface VoiceProfile {
  tone: string;
  pace: string;
  accent: string;
  vocabulary_level: string;
  speech_patterns: string[];
  catchphrases: string[];
}

export interface CharacterRelationship {
  with_character: string;
  relationship_type: string;
  dynamic: string;
  development: string;
}

export interface ScriptLocation {
  id: string;
  name: string;
  type: string;
  description: string;
  atmosphere: string;
  significance: string;
  recurring: boolean;
  visual_elements: string[];
  audio_elements: string[];
}

export interface InteractiveElement {
  type: 'choice' | 'skill_check' | 'puzzle' | 'combat' | 'exploration';
  description: string;
  frequency: 'rare' | 'occasional' | 'common' | 'frequent';
  impact: 'low' | 'medium' | 'high';
}

export interface PlotPoint {
  type: 'inciting_incident' | 'plot_twist' | 'climax' | 'resolution' | 'revelation';
  description: string;
  impact: string;
  foreshadowing: string[];
}

export interface Interruption {
  type: 'character' | 'event' | 'environment';
  source: string;
  description: string;
}

export interface TextEmphasis {
  start: number;
  end: number;
  type: 'bold' | 'italic' | 'caps' | 'whisper' | 'shout';
}

export interface AudioCue {
  type: 'sound_effect' | 'music' | 'ambient' | 'silence';
  description: string;
  timing: 'before' | 'with' | 'after';
}

export class ScriptExporter extends EventEmitter {
  private outputPath: string;
  private md: MarkdownIt;

  constructor(outputPath: string) {
    super();
    this.outputPath = outputPath;
    this.md = new MarkdownIt({ html: true, linkify: true });
  }

  public async initialize(): Promise<void> {
    try {
      await fs.mkdir(this.outputPath, { recursive: true });
      console.log('📝 Narrative script exporter initialized');
      this.emit('initialized');
    } catch (error) {
      console.error('Error initializing script exporter:', error);
      throw error;
    }
  }

  public async exportNarrativeScript(
    campaign: Campaign, 
    options: ScriptExportOptions
  ): Promise<string> {
    console.log(`📝 Exporting narrative script: ${campaign.name}`);
    
    // Analyze and structure the narrative
    const narrative = await this.analyzeCampaignNarrative(campaign);
    const script = await this.buildNarrativeScript(campaign, narrative);
    
    // Export in requested format
    let exportedContent: string;
    let fileExtension: string;
    
    switch (options.format) {
      case 'markdown':
        exportedContent = await this.exportAsMarkdown(script, options);
        fileExtension = 'md';
        break;
      case 'fountain':
        exportedContent = await this.exportAsFountain(script, options);
        fileExtension = 'fountain';
        break;
      case 'json':
        exportedContent = JSON.stringify(script, null, 2);
        fileExtension = 'json';
        break;
      case 'yaml':
        exportedContent = yaml.dump(script, { indent: 2 });
        fileExtension = 'yaml';
        break;
      case 'xml':
        exportedContent = await this.exportAsXML(script, options);
        fileExtension = 'xml';
        break;
      case 'csv':
        exportedContent = await this.exportAsCSV(script, options);
        fileExtension = 'csv';
        break;
      case 'twine':
        exportedContent = await this.exportAsTwine(script, options);
        fileExtension = 'html';
        break;
      case 'articy':
        exportedContent = await this.exportAsArticy(script, options);
        fileExtension = 'xml';
        break;
      default:
        throw new Error(`Unsupported export format: ${options.format}`);
    }

    // Write to file
    const fileName = `${this.sanitizeFileName(campaign.name)}_script.${fileExtension}`;
    const filePath = path.join(this.outputPath, fileName);
    await fs.writeFile(filePath, exportedContent, 'utf-8');
    
    console.log(`✅ Script exported: ${filePath}`);
    this.emit('script-exported', { campaign: campaign.name, format: options.format, path: filePath });
    
    return filePath;
  }

  private async analyzeCampaignNarrative(campaign: Campaign): Promise<NarrativeStructure> {
    // Extract narrative structure from campaign data
    const acts = await this.identifyStoryActs(campaign.sessions);
    const characterArcs = await this.analyzeCharacterArcs(campaign.characters, campaign.sessions);
    const dialogueTrees = await this.extractDialogueTrees(campaign.sessions, campaign.npcs);
    const worldLore = await this.compileWorldLore(campaign);
    const cutscenes = await this.identifyCutsceneOpportunities(campaign.sessions);
    
    return {
      mainStory: acts,
      sideQuests: campaign.quests.filter(q => q.type === 'side'),
      dialogueTrees,
      characterArcs,
      worldLore,
      cutscenes,
      narrativeChoices: await this.identifyNarrativeChoices(campaign.sessions)
    };
  }

  private async identifyStoryActs(sessions: Session[]): Promise<StoryAct[]> {
    const acts: StoryAct[] = [];
    
    // Group sessions into acts based on narrative significance
    let currentAct: StoryAct = {
      id: 'act_1',
      title: 'The Beginning',
      description: 'Introduction and initial conflict',
      scenes: [],
      climax: '',
      resolution: '',
      themes: []
    };
    
    let actNumber = 1;
    let significantEventsInAct = 0;
    
    for (let i = 0; i < sessions.length; i++) {
      const session = sessions[i];
      const scenes = await this.sessionToScenes(session);
      currentAct.scenes.push(...scenes);
      
      // Check for act boundaries (major plot points, significant events)
      const hasClimax = session.events.some(event => 
        event.description.toLowerCase().includes('climax') ||
        event.description.toLowerCase().includes('final') ||
        event.consequences.length > 2
      );
      
      if (hasClimax || significantEventsInAct > 3) {
        // Close current act
        currentAct.climax = this.identifyActClimax(currentAct.scenes);
        currentAct.resolution = this.identifyActResolution(currentAct.scenes);
        currentAct.themes = this.extractActThemes(currentAct.scenes);
        acts.push(currentAct);
        
        // Start new act if there are more sessions
        if (i < sessions.length - 1) {
          actNumber++;
          currentAct = {
            id: `act_${actNumber}`,
            title: actNumber === 2 ? 'Rising Action' : 
                   actNumber === 3 ? 'The Climax' : 
                   `Act ${actNumber}`,
            description: this.generateActDescription(actNumber),
            scenes: [],
            climax: '',
            resolution: '',
            themes: []
          };
          significantEventsInAct = 0;
        }
      } else {
        significantEventsInAct += session.events.filter(e => e.consequences.length > 0).length;
      }
    }
    
    // Add final act if it has content
    if (currentAct.scenes.length > 0) {
      currentAct.climax = this.identifyActClimax(currentAct.scenes);
      currentAct.resolution = this.identifyActResolution(currentAct.scenes);
      currentAct.themes = this.extractActThemes(currentAct.scenes);
      acts.push(currentAct);
    }
    
    return acts;
  }

  private async sessionToScenes(session: Session): Promise<any[]> {
    const scenes: any[] = [];
    
    // Group events by location and time to create scenes
    const locationGroups = new Map<string, any[]>();
    
    session.events.forEach(event => {
      const location = event.location || 'Unknown Location';
      if (!locationGroups.has(location)) {
        locationGroups.set(location, []);
      }
      locationGroups.get(location)!.push(event);
    });
    
    // Convert each location group to a scene
    for (const [location, events] of locationGroups) {
      const scene = {
        id: `scene_${session.id}_${location.toLowerCase().replace(/\s+/g, '_')}`,
        title: this.generateSceneTitle(events),
        location,
        time_of_day: this.inferTimeOfDay(events),
        atmosphere: this.inferAtmosphere(events),
        participants: [...new Set(events.flatMap(e => e.participants))],
        dialogue: this.extractDialogueFromEvents(events, session.dialogue),
        action_lines: this.eventsToActionLines(events),
        stage_directions: this.generateStageDirections(events, location),
        narrative_purpose: this.identifyNarrativePurpose(events),
        emotional_beats: this.identifyEmotionalBeats(events)
      };
      
      scenes.push(scene);
    }
    
    return scenes;
  }

  private async buildNarrativeScript(campaign: Campaign, narrative: NarrativeStructure): Promise<NarrativeScript> {
    return {
      title: campaign.name,
      version: '1.0.0',
      metadata: {
        genre: campaign.genre,
        target_audience: this.inferTargetAudience(campaign),
        estimated_length: this.calculateEstimatedLength(narrative),
        complexity: this.assessComplexity(narrative),
        tone: this.identifyTone(campaign),
        pacing: this.assessPacing(narrative),
        interactive_elements: this.identifyInteractiveElements(campaign)
      },
      acts: narrative.mainStory.map((act, index) => ({
        id: act.id,
        title: act.title,
        order: index + 1,
        scenes: act.scenes.map(scene => this.processScene(scene)),
        themes: act.themes,
        character_arcs: this.identifyCharacterArcsInAct(act, narrative.characterArcs),
        plot_points: this.identifyPlotPoints(act),
        duration_estimate: this.estimateActDuration(act)
      })),
      characters: campaign.characters.map(char => this.characterToScriptCharacter(char, campaign)),
      locations: campaign.locations.map(loc => this.locationToScriptLocation(loc)),
      themes: this.extractCampaignThemes(campaign),
      notes: this.generateProductionNotes(campaign, narrative)
    };
  }

  private async exportAsMarkdown(script: NarrativeScript, options: ScriptExportOptions): Promise<string> {
    let markdown = `# ${script.title}\n\n`;
    
    if (options.includeMetadata) {
      markdown += `## Metadata\n\n`;
      markdown += `- **Genre:** ${script.metadata.genre}\n`;
      markdown += `- **Target Audience:** ${script.metadata.target_audience}\n`;
      markdown += `- **Estimated Length:** ${script.metadata.estimated_length} minutes\n`;
      markdown += `- **Complexity:** ${script.metadata.complexity}\n`;
      markdown += `- **Tone:** ${script.metadata.tone.join(', ')}\n`;
      markdown += `- **Pacing:** ${script.metadata.pacing}\n\n`;
    }

    // Table of Contents
    markdown += `## Table of Contents\n\n`;
    script.acts.forEach(act => {
      markdown += `- [${act.title}](#${act.title.toLowerCase().replace(/\s+/g, '-')})\n`;
    });
    markdown += `\n`;

    // Characters
    if (options.includeCharacterNotes) {
      markdown += `## Characters\n\n`;
      script.characters.forEach(character => {
        markdown += `### ${character.name}\n\n`;
        markdown += `**Role:** ${character.role}\n\n`;
        markdown += `${character.description}\n\n`;
        markdown += `**Voice:** ${character.voice.tone}, ${character.voice.pace}\n\n`;
        if (character.iconic_lines.length > 0) {
          markdown += `**Iconic Lines:**\n`;
          character.iconic_lines.forEach(line => {
            markdown += `- "${line}"\n`;
          });
          markdown += `\n`;
        }
      });
    }

    // Acts and Scenes
    script.acts.forEach(act => {
      markdown += `## ${act.title}\n\n`;
      markdown += `${act.themes.join(', ')}\n\n`;
      
      act.scenes.forEach(scene => {
        markdown += `### Scene: ${scene.title}\n\n`;
        markdown += `**Location:** ${scene.location}\n`;
        markdown += `**Atmosphere:** ${scene.atmosphere}\n`;
        markdown += `**Participants:** ${scene.participants.join(', ')}\n\n`;
        
        if (options.includeStageDirections && scene.stage_directions.length > 0) {
          markdown += `**Stage Directions:**\n`;
          scene.stage_directions.forEach(direction => {
            markdown += `- *${direction.description}*\n`;
          });
          markdown += `\n`;
        }
        
        // Dialogue
        scene.dialogue.forEach(line => {
          if (line.speaker === 'NARRATOR') {
            markdown += `*${line.text}*\n\n`;
          } else {
            markdown += `**${line.speaker.toUpperCase()}**`;
            if (line.emotion) {
              markdown += ` *(${line.emotion})*`;
            }
            markdown += `\n${line.text}\n\n`;
          }
        });
        
        // Action lines
        scene.action_lines.forEach(action => {
          markdown += `*${action.description}*\n\n`;
        });
      });
    });

    return markdown;
  }

  private async exportAsFountain(script: NarrativeScript, options: ScriptExportOptions): Promise<string> {
    let fountain = `Title: ${script.title}\n`;
    fountain += `Author: Generated from D&D Campaign\n`;
    fountain += `Genre: ${script.metadata.genre}\n\n`;

    script.acts.forEach((act, actIndex) => {
      fountain += `# ${act.title}\n\n`;
      
      act.scenes.forEach((scene, sceneIndex) => {
        // Scene header
        fountain += `## ${scene.location.toUpperCase()}\n\n`;
        
        if (scene.atmosphere) {
          fountain += `${scene.atmosphere}\n\n`;
        }
        
        // Dialogue and action
        scene.dialogue.forEach(line => {
          if (line.speaker === 'NARRATOR') {
            fountain += `${line.text}\n\n`;
          } else {
            fountain += `${line.speaker.toUpperCase()}\n`;
            if (line.delivery_notes) {
              fountain += `(${line.delivery_notes})\n`;
            }
            fountain += `${line.text}\n\n`;
          }
        });
        
        scene.action_lines.forEach(action => {
          fountain += `${action.description}\n\n`;
        });
      });
    });

    return fountain;
  }

  private async exportAsXML(script: NarrativeScript, options: ScriptExportOptions): Promise<string> {
    let xml = `<?xml version="1.0" encoding="UTF-8"?>\n`;
    xml += `<narrative_script>\n`;
    xml += `  <metadata>\n`;
    xml += `    <title>${this.escapeXML(script.title)}</title>\n`;
    xml += `    <genre>${script.metadata.genre}</genre>\n`;
    xml += `    <estimated_length>${script.metadata.estimated_length}</estimated_length>\n`;
    xml += `  </metadata>\n`;
    
    xml += `  <characters>\n`;
    script.characters.forEach(character => {
      xml += `    <character id="${character.id}">\n`;
      xml += `      <name>${this.escapeXML(character.name)}</name>\n`;
      xml += `      <role>${character.role}</role>\n`;
      xml += `      <description>${this.escapeXML(character.description)}</description>\n`;
      xml += `    </character>\n`;
    });
    xml += `  </characters>\n`;
    
    xml += `  <acts>\n`;
    script.acts.forEach(act => {
      xml += `    <act id="${act.id}" order="${act.order}">\n`;
      xml += `      <title>${this.escapeXML(act.title)}</title>\n`;
      xml += `      <scenes>\n`;
      
      act.scenes.forEach(scene => {
        xml += `        <scene id="${scene.id}">\n`;
        xml += `          <title>${this.escapeXML(scene.title)}</title>\n`;
        xml += `          <location>${this.escapeXML(scene.location)}</location>\n`;
        xml += `          <dialogue>\n`;
        
        scene.dialogue.forEach(line => {
          xml += `            <line speaker="${this.escapeXML(line.speaker)}" emotion="${line.emotion || ''}">\n`;
          xml += `              ${this.escapeXML(line.text)}\n`;
          xml += `            </line>\n`;
        });
        
        xml += `          </dialogue>\n`;
        xml += `        </scene>\n`;
      });
      
      xml += `      </scenes>\n`;
      xml += `    </act>\n`;
    });
    xml += `  </acts>\n`;
    xml += `</narrative_script>`;
    
    return xml;
  }

  private async exportAsCSV(script: NarrativeScript, options: ScriptExportOptions): Promise<string> {
    let csv = 'Act,Scene,Location,Speaker,Dialogue,Emotion,Notes\n';
    
    script.acts.forEach(act => {
      act.scenes.forEach(scene => {
        scene.dialogue.forEach(line => {
          const row = [
            act.title,
            scene.title,
            scene.location,
            line.speaker,
            `"${line.text.replace(/"/g, '""')}"`,
            line.emotion || '',
            line.delivery_notes || ''
          ].join(',');
          csv += row + '\n';
        });
      });
    });
    
    return csv;
  }

  private async exportAsTwine(script: NarrativeScript, options: ScriptExportOptions): Promise<string> {
    let twine = `<tw-storydata name="${script.title}" startnode="1" creator="DMLog Converter">\n`;
    
    let nodeId = 1;
    script.acts.forEach((act, actIndex) => {
      twine += `<tw-passagedata pid="${nodeId}" name="${act.title}" tags="">\n`;
      twine += `<h2>${act.title}</h2>\n`;
      
      act.scenes.forEach((scene, sceneIndex) => {
        twine += `<p><strong>${scene.location}</strong></p>\n`;
        twine += `<p>${scene.atmosphere}</p>\n`;
        
        scene.dialogue.forEach(line => {
          if (line.speaker === 'NARRATOR') {
            twine += `<p><em>${line.text}</em></p>\n`;
          } else {
            twine += `<p><strong>${line.speaker}:</strong> ${line.text}</p>\n`;
          }
        });
        
        if (sceneIndex < act.scenes.length - 1) {
          twine += `<p>[[Continue to next scene|Scene${nodeId + 1}]]</p>\n`;
        }
      });
      
      if (actIndex < script.acts.length - 1) {
        twine += `<p>[[Continue to ${script.acts[actIndex + 1].title}|${script.acts[actIndex + 1].title}]]</p>\n`;
      }
      
      twine += `</tw-passagedata>\n`;
      nodeId++;
    });
    
    twine += `</tw-storydata>`;
    return twine;
  }

  private async exportAsArticy(script: NarrativeScript, options: ScriptExportOptions): Promise<string> {
    // Articy XML format for professional game writing tools
    let articy = `<?xml version="1.0" encoding="UTF-8"?>\n`;
    articy += `<articy:project xmlns:articy="http://www.articy.com/schemas/articydraft/1.0">\n`;
    articy += `  <content>\n`;
    
    // Characters
    articy += `    <entities>\n`;
    script.characters.forEach(character => {
      articy += `      <entity category="Character" id="${character.id}">\n`;
      articy += `        <properties>\n`;
      articy += `          <property name="DisplayName" value="${this.escapeXML(character.name)}"/>\n`;
      articy += `          <property name="Description" value="${this.escapeXML(character.description)}"/>\n`;
      articy += `          <property name="Role" value="${character.role}"/>\n`;
      articy += `        </properties>\n`;
      articy += `      </entity>\n`;
    });
    articy += `    </entities>\n`;
    
    // Flow (dialogue trees would go here)
    articy += `    <flow>\n`;
    script.acts.forEach((act, actIndex) => {
      articy += `      <node type="Hub" id="act_${actIndex}">\n`;
      articy += `        <properties>\n`;
      articy += `          <property name="DisplayName" value="${this.escapeXML(act.title)}"/>\n`;
      articy += `        </properties>\n`;
      articy += `      </node>\n`;
    });
    articy += `    </flow>\n`;
    
    articy += `  </content>\n`;
    articy += `</articy:project>`;
    
    return articy;
  }

  // Helper methods for script processing
  private generateSceneTitle(events: any[]): string {
    if (events.length === 0) return 'Untitled Scene';
    
    const firstEvent = events[0];
    if (firstEvent.type === 'combat') return 'Battle Scene';
    if (firstEvent.type === 'social') return 'Social Encounter';
    if (firstEvent.type === 'exploration') return 'Exploration';
    
    return firstEvent.description.split('.')[0] || 'Scene';
  }

  private inferTimeOfDay(events: any[]): string {
    // Simple inference based on event descriptions
    const descriptions = events.map(e => e.description.toLowerCase()).join(' ');
    
    if (descriptions.includes('morning') || descriptions.includes('dawn')) return 'morning';
    if (descriptions.includes('evening') || descriptions.includes('dusk')) return 'evening';
    if (descriptions.includes('night') || descriptions.includes('dark')) return 'night';
    
    return 'day';
  }

  private inferAtmosphere(events: any[]): string {
    const descriptions = events.map(e => e.description.toLowerCase()).join(' ');
    
    if (descriptions.includes('tense') || descriptions.includes('danger')) return 'tense';
    if (descriptions.includes('peaceful') || descriptions.includes('calm')) return 'peaceful';
    if (descriptions.includes('mysterious') || descriptions.includes('strange')) return 'mysterious';
    if (descriptions.includes('combat') || descriptions.includes('battle')) return 'intense';
    
    return 'neutral';
  }

  private extractDialogueFromEvents(events: any[], sessionDialogue: DialogueEntry[]): DialogueLine[] {
    const dialogueLines: DialogueLine[] = [];
    
    // Match dialogue entries to events by timestamp proximity
    events.forEach(event => {
      const eventTime = event.timestamp.getTime();
      const relatedDialogue = sessionDialogue.filter(d => 
        Math.abs(d.timestamp.getTime() - eventTime) < 300000 // 5 minutes
      );
      
      relatedDialogue.forEach(dialogue => {
        dialogueLines.push({
          speaker: dialogue.speaker,
          text: dialogue.text,
          emotion: dialogue.emotion || 'neutral',
          delivery_notes: dialogue.context || '',
          interruptions: [],
          emphasis: this.analyzeTextEmphasis(dialogue.text),
          audio_cues: []
        });
      });
    });
    
    return dialogueLines;
  }

  private analyzeTextEmphasis(text: string): TextEmphasis[] {
    const emphasis: TextEmphasis[] = [];
    
    // Look for emphasized text patterns
    let match;
    
    // Bold text (surrounded by asterisks)
    const boldRegex = /\*([^*]+)\*/g;
    while ((match = boldRegex.exec(text)) !== null) {
      emphasis.push({
        start: match.index,
        end: match.index + match[0].length,
        type: 'bold'
      });
    }
    
    // All caps (shouting)
    const capsRegex = /\b[A-Z]{3,}\b/g;
    while ((match = capsRegex.exec(text)) !== null) {
      emphasis.push({
        start: match.index,
        end: match.index + match[0].length,
        type: 'shout'
      });
    }
    
    return emphasis;
  }

  private eventsToActionLines(events: any[]): ActionLine[] {
    return events.map(event => ({
      description: event.description,
      characters_involved: event.participants || [],
      duration: this.estimateEventDuration(event),
      complexity: this.assessEventComplexity(event),
      visual_priority: this.assessVisualPriority(event)
    }));
  }

  private generateStageDirections(events: any[], location: string): StageDirection[] {
    const directions: StageDirection[] = [];
    
    // Add lighting based on location and events
    if (location.toLowerCase().includes('dungeon') || location.toLowerCase().includes('cave')) {
      directions.push({
        type: 'lighting',
        description: 'Dim, flickering torchlight',
        timing: 'before'
      });
    }
    
    // Add sound based on events
    events.forEach(event => {
      if (event.type === 'combat') {
        directions.push({
          type: 'sound',
          description: 'Combat music intensifies',
          timing: 'with'
        });
      }
    });
    
    return directions;
  }

  private identifyNarrativePurpose(events: any[]): string {
    const eventTypes = events.map(e => e.type);
    
    if (eventTypes.includes('combat')) return 'Action sequence';
    if (eventTypes.includes('social')) return 'Character development';
    if (eventTypes.includes('discovery')) return 'Plot advancement';
    if (eventTypes.includes('exploration')) return 'World building';
    
    return 'Narrative progression';
  }

  private identifyEmotionalBeats(events: any[]): EmotionalBeat[] {
    const beats: EmotionalBeat[] = [];
    
    events.forEach(event => {
      if (event.consequences && event.consequences.length > 0) {
        beats.push({
          character: event.participants[0] || 'Unknown',
          emotion: this.inferEmotionFromEvent(event),
          intensity: event.consequences.length * 3,
          trigger: event.description,
          expression: this.generateEmotionalExpression(event)
        });
      }
    });
    
    return beats;
  }

  private inferEmotionFromEvent(event: any): string {
    const description = event.description.toLowerCase();
    
    if (description.includes('success') || description.includes('victory')) return 'triumph';
    if (description.includes('failure') || description.includes('defeat')) return 'disappointment';
    if (description.includes('death') || description.includes('loss')) return 'grief';
    if (description.includes('discovery') || description.includes('reveal')) return 'excitement';
    if (description.includes('danger') || description.includes('threat')) return 'fear';
    
    return 'neutral';
  }

  // Additional helper methods would continue here...
  
  private sanitizeFileName(name: string): string {
    return name.replace(/[^a-z0-9]/gi, '_').toLowerCase();
  }

  private escapeXML(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  private estimateEventDuration(event: any): number {
    // Estimate duration based on event type and complexity
    switch (event.type) {
      case 'combat': return 5;
      case 'social': return 2;
      case 'exploration': return 3;
      default: return 1;
    }
  }

  private assessEventComplexity(event: any): 'simple' | 'moderate' | 'complex' {
    const participants = event.participants?.length || 0;
    const consequences = event.consequences?.length || 0;
    
    if (participants > 3 || consequences > 2) return 'complex';
    if (participants > 1 || consequences > 0) return 'moderate';
    return 'simple';
  }

  private assessVisualPriority(event: any): 'low' | 'medium' | 'high' {
    if (event.type === 'combat') return 'high';
    if (event.type === 'discovery') return 'medium';
    return 'low';
  }

  private async analyzeCharacterArcs(characters: Character[], sessions: Session[]): Promise<any[]> {
    // This would analyze character development across sessions
    return characters.map(char => char.characterArc || { phases: [], growth: [], conflicts: [], resolution: '' });
  }

  private async extractDialogueTrees(sessions: Session[], npcs: NPC[]): Promise<any[]> {
    // This would extract dialogue patterns and create trees
    return [];
  }

  private async compileWorldLore(campaign: Campaign): Promise<any> {
    return {
      entries: [],
      categories: [],
      connections: []
    };
  }

  private async identifyCutsceneOpportunities(sessions: Session[]): Promise<CutsceneScript[]> {
    return [];
  }

  private async identifyNarrativeChoices(sessions: Session[]): Promise<any[]> {
    return [];
  }

  // Additional helper method implementations would continue...
  // For brevity, I'm showing the structure and key methods

  private identifyActClimax(scenes: any[]): string {
    return 'Act climax identified from scene analysis';
  }

  private identifyActResolution(scenes: any[]): string {
    return 'Act resolution identified from scene analysis';
  }

  private extractActThemes(scenes: any[]): string[] {
    return ['heroism', 'sacrifice', 'friendship'];
  }

  private generateActDescription(actNumber: number): string {
    const descriptions = [
      'Introduction of characters and initial conflict',
      'Rising tension and complications',
      'Climactic confrontation and resolution',
      'Aftermath and new beginnings'
    ];
    return descriptions[Math.min(actNumber - 1, descriptions.length - 1)];
  }

  private inferTargetAudience(campaign: Campaign): string {
    return 'Young Adult and Adult fantasy enthusiasts';
  }

  private calculateEstimatedLength(narrative: NarrativeStructure): number {
    return narrative.mainStory.length * 30; // Rough estimate: 30 minutes per act
  }

  private assessComplexity(narrative: NarrativeStructure): 'simple' | 'moderate' | 'complex' {
    const characterCount = narrative.characterArcs.length;
    const questCount = narrative.sideQuests.length;
    
    if (characterCount > 6 || questCount > 10) return 'complex';
    if (characterCount > 3 || questCount > 5) return 'moderate';
    return 'simple';
  }

  private identifyTone(campaign: Campaign): string[] {
    return [campaign.theme, 'adventure', 'heroic'];
  }

  private assessPacing(narrative: NarrativeStructure): 'slow' | 'moderate' | 'fast' | 'variable' {
    return 'variable'; // Most D&D campaigns have variable pacing
  }

  private identifyInteractiveElements(campaign: Campaign): InteractiveElement[] {
    return [
      { type: 'choice', description: 'Player decisions affect story', frequency: 'common', impact: 'high' },
      { type: 'combat', description: 'Turn-based tactical combat', frequency: 'frequent', impact: 'medium' }
    ];
  }

  private processScene(scene: any): any {
    return scene; // Process scene for final output
  }

  private identifyCharacterArcsInAct(act: any, characterArcs: any[]): string[] {
    return characterArcs.map(arc => arc.character || 'Unknown');
  }

  private identifyPlotPoints(act: any): PlotPoint[] {
    return [
      { type: 'revelation', description: 'Key information revealed', impact: 'Major story development', foreshadowing: [] }
    ];
  }

  private estimateActDuration(act: any): number {
    return act.scenes?.length * 10 || 30; // 10 minutes per scene average
  }

  private characterToScriptCharacter(character: Character, campaign: Campaign): ScriptCharacter {
    return {
      id: character.id,
      name: character.name,
      role: this.determineCharacterRole(character, campaign),
      description: character.backstory || `${character.race} ${character.class}`,
      voice: {
        tone: character.personality?.temperament || 'neutral',
        pace: 'moderate',
        accent: 'none',
        vocabulary_level: 'moderate',
        speech_patterns: character.personality?.traits || [],
        catchphrases: character.voiceLines || []
      },
      arc_summary: this.summarizeCharacterArc(character),
      relationships: character.relationships?.map(rel => ({
        with_character: rel.targetId,
        relationship_type: rel.type,
        dynamic: rel.history || '',
        development: 'ongoing'
      })) || [],
      iconic_lines: character.voiceLines || [],
      character_function: this.identifyCharacterFunction(character)
    };
  }

  private determineCharacterRole(character: Character, campaign: Campaign): 'protagonist' | 'antagonist' | 'supporting' | 'minor' | 'narrator' {
    // Logic to determine character role based on their involvement in the story
    return 'protagonist'; // Simplified
  }

  private summarizeCharacterArc(character: Character): string {
    return character.characterArc?.phases?.map(p => p.name).join(' -> ') || 'Character growth through adventure';
  }

  private identifyCharacterFunction(character: Character): string[] {
    const functions = ['hero'];
    if (character.class.toLowerCase().includes('cleric') || character.class.toLowerCase().includes('paladin')) {
      functions.push('healer', 'moral_compass');
    }
    if (character.class.toLowerCase().includes('rogue') || character.class.toLowerCase().includes('ranger')) {
      functions.push('scout', 'skill_specialist');
    }
    return functions;
  }

  private locationToScriptLocation(location: any): ScriptLocation {
    return {
      id: location.id,
      name: location.name,
      type: location.type,
      description: location.description,
      atmosphere: location.atmosphere || 'neutral',
      significance: this.assessLocationSignificance(location),
      recurring: this.isLocationRecurring(location),
      visual_elements: location.features?.map((f: any) => f.name) || [],
      audio_elements: location.ambience?.sounds || []
    };
  }

  private assessLocationSignificance(location: any): string {
    if (location.type === 'city') return 'Major hub location';
    if (location.type === 'dungeon') return 'Adventure location';
    return 'Supporting location';
  }

  private isLocationRecurring(location: any): boolean {
    // Logic to determine if location appears multiple times
    return location.connections?.length > 2;
  }

  private extractCampaignThemes(campaign: Campaign): string[] {
    const themes = [campaign.theme];
    
    // Extract themes from quest types and character backgrounds
    if (campaign.quests.some(q => q.type === 'personal')) {
      themes.push('personal_growth');
    }
    if (campaign.characters.some(c => c.background.toLowerCase().includes('noble'))) {
      themes.push('duty_and_honor');
    }
    
    return [...new Set(themes)];
  }

  private generateProductionNotes(campaign: Campaign, narrative: NarrativeStructure): string[] {
    return [
      `Adapted from D&D campaign: ${campaign.name}`,
      `Original campaign had ${campaign.sessions.length} sessions`,
      `Features ${campaign.characters.length} main characters`,
      'Consider interactive elements for player choice implementation',
      'Combat sequences may require action choreography',
      'Character voices should reflect their fantasy archetypes'
    ];
  }

  private generateEmotionalExpression(event: any): string {
    const emotion = this.inferEmotionFromEvent(event);
    
    const expressions = {
      'triumph': 'Raised fists, broad smile, confident posture',
      'disappointment': 'Slumped shoulders, downcast eyes, heavy sigh',
      'grief': 'Tears, trembling, difficulty speaking',
      'excitement': 'Wide eyes, animated gestures, quick speech',
      'fear': 'Tense body, darting eyes, protective stance'
    };
    
    return expressions[emotion as keyof typeof expressions] || 'Neutral expression';
  }
}