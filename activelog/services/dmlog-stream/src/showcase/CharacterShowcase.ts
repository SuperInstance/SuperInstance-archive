import { EventEmitter } from 'events';
import { Character, OverlayElement, StreamSettings } from '../types';
import { OverlayGenerator } from '../overlays/OverlayGenerator';
import { Canvas, createCanvas, CanvasRenderingContext2D, Image, loadImage } from 'canvas';
import * as fs from 'fs';
import * as path from 'path';

export class CharacterShowcase extends EventEmitter {
  private overlayGenerator: OverlayGenerator;
  private currentCharacter: Character | null = null;
  private showcaseQueue: Character[] = [];
  private isShowcasing: boolean = false;
  private showcaseTimer: NodeJS.Timeout | null = null;
  private settings: StreamSettings;
  private assetsPath: string;

  constructor(overlayGenerator: OverlayGenerator, settings: StreamSettings) {
    super();
    this.overlayGenerator = overlayGenerator;
    this.settings = settings;
    this.assetsPath = path.join(__dirname, '../../assets/characters');
    this.ensureAssetsDirectory();
  }

  private ensureAssetsDirectory(): void {
    if (!fs.existsSync(this.assetsPath)) {
      fs.mkdirSync(this.assetsPath, { recursive: true });
    }
  }

  public async showcaseCharacter(character: Character, duration: number = 30000): Promise<void> {
    if (this.isShowcasing) {
      this.showcaseQueue.push(character);
      this.emit('character-queued', { character, queuePosition: this.showcaseQueue.length });
      return;
    }

    this.isShowcasing = true;
    this.currentCharacter = character;

    try {
      // Create detailed character showcase overlay
      const showcaseElement = await this.createDetailedCharacterOverlay(character);
      this.overlayGenerator.addElement(showcaseElement);

      // Create supporting elements
      const statsElement = this.createCharacterStatsOverlay(character);
      const equipmentElement = this.createCharacterEquipmentOverlay(character);
      const spellsElement = this.createCharacterSpellsOverlay(character);

      this.overlayGenerator.addElement(statsElement);
      this.overlayGenerator.addElement(equipmentElement);
      if (character.spells.length > 0) {
        this.overlayGenerator.addElement(spellsElement);
      }

      // Set up animated transitions
      await this.animateShowcaseEntry();

      this.emit('character-showcase-started', {
        character,
        duration,
        elements: [showcaseElement.id, statsElement.id, equipmentElement.id]
      });

      // Schedule showcase end
      this.showcaseTimer = setTimeout(async () => {
        await this.endShowcase();
      }, duration);

      // Start spotlight effects
      this.startSpotlightEffects(character);

    } catch (error) {
      console.error('Error showcasing character:', error);
      this.isShowcasing = false;
      this.emit('character-showcase-error', { character, error });
    }
  }

  private async createDetailedCharacterOverlay(character: Character): Promise<OverlayElement> {
    const portraitUrl = await this.getCharacterPortrait(character);
    
    return {
      id: `character-showcase-${character.id}`,
      type: 'character',
      position: { x: 1200, y: 50, anchor: 'top-left' },
      size: { width: 650, height: 900, scale: 1 },
      style: {
        background: this.getCharacterThemeGradient(character),
        border: `3px solid ${this.getClassColor(character.class)}`,
        borderRadius: 20,
        color: '#ffffff',
        fontSize: 16,
        fontFamily: 'Arial, sans-serif',
        shadow: '0 0 30px rgba(0,0,0,0.8)'
      },
      data: {
        character,
        portraitUrl,
        showDetailed: true,
        showBackground: true,
        showPersonality: true,
        zIndex: 100
      },
      visible: true,
      animation: {
        type: 'slide',
        duration: 1000,
        easing: 'ease-out'
      }
    };
  }

  private createCharacterStatsOverlay(character: Character): OverlayElement {
    return {
      id: `character-stats-${character.id}`,
      type: 'character',
      position: { x: 50, y: 200, anchor: 'top-left' },
      size: { width: 400, height: 500, scale: 1 },
      style: {
        background: 'rgba(0, 0, 0, 0.85)',
        border: `2px solid ${this.getClassColor(character.class)}`,
        borderRadius: 15,
        color: '#ffffff',
        fontSize: 14,
        fontFamily: 'Arial, sans-serif'
      },
      data: {
        character,
        showType: 'stats',
        showAbilities: true,
        showSkills: true,
        showSavingThrows: true,
        zIndex: 90
      },
      visible: true,
      animation: {
        type: 'fade',
        duration: 800,
        easing: 'ease-in'
      }
    };
  }

  private createCharacterEquipmentOverlay(character: Character): OverlayElement {
    return {
      id: `character-equipment-${character.id}`,
      type: 'character',
      position: { x: 500, y: 200, anchor: 'top-left' },
      size: { width: 400, height: 500, scale: 1 },
      style: {
        background: 'rgba(20, 20, 20, 0.9)',
        border: '2px solid #d4af37',
        borderRadius: 15,
        color: '#ffffff',
        fontSize: 14,
        fontFamily: 'Arial, sans-serif'
      },
      data: {
        character,
        showType: 'equipment',
        showWeapons: true,
        showArmor: true,
        showMagicalItems: true,
        maxItems: 8,
        zIndex: 90
      },
      visible: true,
      animation: {
        type: 'slide',
        duration: 1200,
        easing: 'ease-out'
      }
    };
  }

  private createCharacterSpellsOverlay(character: Character): OverlayElement {
    return {
      id: `character-spells-${character.id}`,
      type: 'character',
      position: { x: 50, y: 750, anchor: 'top-left' },
      size: { width: 850, height: 250, scale: 1 },
      style: {
        background: 'rgba(30, 10, 50, 0.9)',
        border: '2px solid #9932cc',
        borderRadius: 15,
        color: '#ffffff',
        fontSize: 12,
        fontFamily: 'Arial, sans-serif'
      },
      data: {
        character,
        showType: 'spells',
        showPreparedOnly: true,
        showByLevel: true,
        maxSpells: 12,
        zIndex: 90
      },
      visible: true,
      animation: {
        type: 'bounce',
        duration: 1500,
        easing: 'ease-out'
      }
    };
  }

  private async animateShowcaseEntry(): Promise<void> {
    return new Promise((resolve) => {
      let step = 0;
      const animationSteps = 60; // 1 second at 60fps
      
      const animate = () => {
        step++;
        
        // Create spotlight effect
        const spotlight = this.createSpotlightOverlay(step / animationSteps);
        this.overlayGenerator.addElement(spotlight);
        
        if (step >= animationSteps) {
          resolve();
        } else {
          setTimeout(animate, 16); // 60fps
        }
      };
      
      animate();
    });
  }

  private createSpotlightOverlay(progress: number): OverlayElement {
    return {
      id: 'character-spotlight',
      type: 'image',
      position: { x: 0, y: 0, anchor: 'top-left' },
      size: { width: 1920, height: 1080, scale: 1 },
      style: {
        opacity: 0.3 * progress,
        background: `radial-gradient(circle at 1525px 500px, transparent 300px, rgba(0,0,0,0.8) 600px)`
      },
      data: {
        type: 'spotlight',
        progress,
        zIndex: 50
      },
      visible: true
    };
  }

  private startSpotlightEffects(character: Character): void {
    // Pulse effect for character border
    let pulseDirection = 1;
    let pulseIntensity = 0.5;
    
    const pulseInterval = setInterval(() => {
      pulseIntensity += pulseDirection * 0.1;
      if (pulseIntensity >= 1 || pulseIntensity <= 0.3) {
        pulseDirection *= -1;
      }
      
      const element = this.overlayGenerator['elements'].get(`character-showcase-${character.id}`);
      if (element && this.isShowcasing) {
        element.style.shadow = `0 0 ${30 * pulseIntensity}px ${this.getClassColor(character.class)}`;
        this.overlayGenerator.render();
      } else {
        clearInterval(pulseInterval);
      }
    }, 100);

    // Floating elements animation
    this.startFloatingAnimation(character);
  }

  private startFloatingAnimation(character: Character): void {
    const floatingElements = [
      { emoji: '⚔️', speed: 2, radius: 100 },
      { emoji: '🛡️', speed: 1.5, radius: 120 },
      { emoji: '✨', speed: 3, radius: 80 },
      { emoji: '🎲', speed: 2.5, radius: 90 }
    ];

    floatingElements.forEach((elem, index) => {
      let angle = (index * Math.PI * 2) / floatingElements.length;
      
      const floatInterval = setInterval(() => {
        if (!this.isShowcasing) {
          clearInterval(floatInterval);
          return;
        }

        angle += elem.speed * 0.02;
        const x = 1525 + Math.cos(angle) * elem.radius;
        const y = 500 + Math.sin(angle) * elem.radius;

        const floatingElement: OverlayElement = {
          id: `floating-${index}`,
          type: 'text',
          position: { x, y, anchor: 'center' },
          size: { width: 40, height: 40, scale: 1 },
          style: {
            fontSize: 24,
            color: '#ffffff',
            opacity: 0.7
          },
          data: {
            text: elem.emoji,
            zIndex: 110
          },
          visible: true
        };

        this.overlayGenerator.addElement(floatingElement);
        
        setTimeout(() => {
          this.overlayGenerator.removeElement(`floating-${index}`);
        }, 50);
      }, 50);
    });
  }

  public async endShowcase(): Promise<void> {
    if (!this.isShowcasing || !this.currentCharacter) return;

    const character = this.currentCharacter;

    // Clear timer
    if (this.showcaseTimer) {
      clearTimeout(this.showcaseTimer);
      this.showcaseTimer = null;
    }

    // Animate exit
    await this.animateShowcaseExit();

    // Remove all showcase elements
    this.overlayGenerator.removeElement(`character-showcase-${character.id}`);
    this.overlayGenerator.removeElement(`character-stats-${character.id}`);
    this.overlayGenerator.removeElement(`character-equipment-${character.id}`);
    this.overlayGenerator.removeElement(`character-spells-${character.id}`);
    this.overlayGenerator.removeElement('character-spotlight');

    this.emit('character-showcase-ended', {
      character,
      duration: Date.now() - (this.showcaseTimer ? 0 : 30000)
    });

    this.isShowcasing = false;
    this.currentCharacter = null;

    // Process queue
    if (this.showcaseQueue.length > 0) {
      const nextCharacter = this.showcaseQueue.shift()!;
      setTimeout(() => {
        this.showcaseCharacter(nextCharacter);
      }, 1000);
    }
  }

  private async animateShowcaseExit(): Promise<void> {
    return new Promise((resolve) => {
      let step = 60;
      
      const animate = () => {
        step--;
        
        if (step <= 0) {
          resolve();
        } else {
          setTimeout(animate, 16);
        }
      };
      
      animate();
    });
  }

  // Character display utilities
  private getCharacterThemeGradient(character: Character): string {
    const classColors = this.getClassColorPair(character.class);
    return `linear-gradient(135deg, ${classColors.primary}AA, ${classColors.secondary}AA, rgba(0,0,0,0.9))`;
  }

  private getClassColor(characterClass: string): string {
    const colors: { [key: string]: string } = {
      'Artificer': '#DAA520',
      'Barbarian': '#DC143C',
      'Bard': '#FF69B4',
      'Cleric': '#FFD700',
      'Druid': '#228B22',
      'Fighter': '#B22222',
      'Monk': '#DDA0DD',
      'Paladin': '#1E90FF',
      'Ranger': '#006400',
      'Rogue': '#2F4F4F',
      'Sorcerer': '#FF4500',
      'Warlock': '#8B008B',
      'Wizard': '#4169E1',
      'Blood Hunter': '#8B0000'
    };
    return colors[characterClass] || '#666666';
  }

  private getClassColorPair(characterClass: string): { primary: string; secondary: string } {
    const pairs: { [key: string]: { primary: string; secondary: string } } = {
      'Artificer': { primary: '#DAA520', secondary: '#4682B4' },
      'Barbarian': { primary: '#DC143C', secondary: '#8B4513' },
      'Bard': { primary: '#FF69B4', secondary: '#9370DB' },
      'Cleric': { primary: '#FFD700', secondary: '#FFF8DC' },
      'Druid': { primary: '#228B22', secondary: '#8FBC8F' },
      'Fighter': { primary: '#B22222', secondary: '#C0C0C0' },
      'Monk': { primary: '#DDA0DD', secondary: '#F0E68C' },
      'Paladin': { primary: '#1E90FF', secondary: '#FFD700' },
      'Ranger': { primary: '#006400', secondary: '#8FBC8F' },
      'Rogue': { primary: '#2F4F4F', secondary: '#696969' },
      'Sorcerer': { primary: '#FF4500', secondary: '#FF6347' },
      'Warlock': { primary: '#8B008B', secondary: '#4B0082' },
      'Wizard': { primary: '#4169E1', secondary: '#E6E6FA' }
    };
    return pairs[characterClass] || { primary: '#666666', secondary: '#999999' };
  }

  private async getCharacterPortrait(character: Character): Promise<string> {
    const portraitPath = path.join(this.assetsPath, `${character.id}.png`);
    
    if (fs.existsSync(portraitPath)) {
      return portraitPath;
    }
    
    // Generate placeholder portrait
    return this.generatePlaceholderPortrait(character);
  }

  private async generatePlaceholderPortrait(character: Character): Promise<string> {
    const canvas = createCanvas(300, 300);
    const ctx = canvas.getContext('2d');
    
    // Background with class color
    const gradient = ctx.createRadialGradient(150, 150, 0, 150, 150, 150);
    gradient.addColorStop(0, this.getClassColor(character.class) + '80');
    gradient.addColorStop(1, '#00000080');
    
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 300, 300);
    
    // Character initial
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 120px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(character.name.charAt(0).toUpperCase(), 150, 150);
    
    // Class indicator
    ctx.font = 'bold 24px Arial';
    ctx.fillText(character.class, 150, 220);
    
    // Level
    ctx.font = '18px Arial';
    ctx.fillText(`Level ${character.level}`, 150, 250);
    
    // Save placeholder
    const buffer = canvas.toBuffer('image/png');
    const placeholderPath = path.join(this.assetsPath, `${character.id}_placeholder.png`);
    fs.writeFileSync(placeholderPath, buffer);
    
    return placeholderPath;
  }

  // Quick showcase methods
  public async quickShowcase(character: Character): Promise<void> {
    await this.showcaseCharacter(character, 15000); // 15 seconds
  }

  public async levelUpShowcase(character: Character): Promise<void> {
    // Special showcase for level up moments
    const levelUpElement: OverlayElement = {
      id: `levelup-${character.id}`,
      type: 'text',
      position: { x: 960, y: 100, anchor: 'center' },
      size: { width: 600, height: 100, scale: 1 },
      style: {
        background: 'linear-gradient(45deg, #FFD700, #FFA500)',
        border: '3px solid #ffffff',
        borderRadius: 20,
        color: '#000000',
        fontSize: 32,
        fontFamily: 'Arial Black, sans-serif',
        shadow: '0 0 20px rgba(255, 215, 0, 0.8)'
      },
      data: {
        text: `${character.name} reached Level ${character.level}!`,
        zIndex: 200
      },
      visible: true,
      animation: {
        type: 'bounce',
        duration: 2000,
        easing: 'ease-out'
      }
    };

    this.overlayGenerator.addElement(levelUpElement);
    
    setTimeout(() => {
      this.overlayGenerator.removeElement(`levelup-${character.id}`);
    }, 5000);

    await this.showcaseCharacter(character, 20000);
  }

  public async deathShowcase(character: Character): Promise<void> {
    // Memorial showcase for character death
    const memorialElement: OverlayElement = {
      id: `memorial-${character.id}`,
      type: 'text',
      position: { x: 960, y: 540, anchor: 'center' },
      size: { width: 800, height: 200, scale: 1 },
      style: {
        background: 'linear-gradient(45deg, #000000, #333333)',
        border: '3px solid #ffffff',
        borderRadius: 20,
        color: '#ffffff',
        fontSize: 28,
        fontFamily: 'Arial, sans-serif'
      },
      data: {
        text: `In memory of ${character.name}\n${character.race} ${character.class}\nLevel 1 - ${character.level}`,
        alignment: 'center',
        zIndex: 200
      },
      visible: true,
      animation: {
        type: 'fade',
        duration: 3000,
        easing: 'ease-in'
      }
    };

    this.overlayGenerator.addElement(memorialElement);
    
    setTimeout(() => {
      this.overlayGenerator.removeElement(`memorial-${character.id}`);
    }, 10000);

    await this.showcaseCharacter(character, 25000);
  }

  // Queue management
  public getShowcaseQueue(): Character[] {
    return [...this.showcaseQueue];
  }

  public clearShowcaseQueue(): void {
    this.showcaseQueue = [];
    this.emit('queue-cleared');
  }

  public removeFromQueue(characterId: string): boolean {
    const index = this.showcaseQueue.findIndex(char => char.id === characterId);
    if (index !== -1) {
      this.showcaseQueue.splice(index, 1);
      this.emit('character-removed-from-queue', { characterId, newQueueLength: this.showcaseQueue.length });
      return true;
    }
    return false;
  }

  // Status methods
  public isCurrentlyShowcasing(): boolean {
    return this.isShowcasing;
  }

  public getCurrentCharacter(): Character | null {
    return this.currentCharacter;
  }

  public getQueueLength(): number {
    return this.showcaseQueue.length;
  }

  public updateSettings(newSettings: StreamSettings): void {
    this.settings = newSettings;
    this.emit('settings-updated', newSettings);
  }
}