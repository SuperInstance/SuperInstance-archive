import { Canvas, createCanvas, CanvasRenderingContext2D } from 'canvas';
import { OverlayElement, StreamSettings, Character, ViewerDiceRoll, ViewerPoll, Donation } from '../types';
import { EventEmitter } from 'events';
import * as fs from 'fs';
import * as path from 'path';

export class OverlayGenerator extends EventEmitter {
  private canvas: Canvas;
  private ctx: CanvasRenderingContext2D;
  private elements: Map<string, OverlayElement> = new Map();
  private animations: Map<string, NodeJS.Timeout> = new Map();
  private settings: StreamSettings;
  private assetsPath: string;
  private outputPath: string;

  constructor(width: number = 1920, height: number = 1080, settings: StreamSettings) {
    super();
    this.canvas = createCanvas(width, height);
    this.ctx = this.canvas.getContext('2d');
    this.settings = settings;
    this.assetsPath = path.join(__dirname, '../../assets');
    this.outputPath = path.join(__dirname, '../../public/overlays');
    
    this.setupCanvas();
    this.loadAssets();
  }

  private setupCanvas(): void {
    this.ctx.fillStyle = 'transparent';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    
    // Set default font
    this.ctx.font = '16px Arial';
    this.ctx.textAlign = 'left';
    this.ctx.textBaseline = 'top';
  }

  private async loadAssets(): Promise<void> {
    // Ensure assets and output directories exist
    if (!fs.existsSync(this.assetsPath)) {
      fs.mkdirSync(this.assetsPath, { recursive: true });
    }
    if (!fs.existsSync(this.outputPath)) {
      fs.mkdirSync(this.outputPath, { recursive: true });
    }
  }

  public addElement(element: OverlayElement): void {
    this.elements.set(element.id, element);
    this.render();
    
    // Handle animations
    if (element.animation) {
      this.startAnimation(element);
    }
  }

  public removeElement(elementId: string): void {
    this.elements.delete(elementId);
    this.stopAnimation(elementId);
    this.render();
  }

  public updateElement(elementId: string, updates: Partial<OverlayElement>): void {
    const element = this.elements.get(elementId);
    if (element) {
      this.elements.set(elementId, { ...element, ...updates });
      this.render();
    }
  }

  public createDiceRollOverlay(diceRoll: ViewerDiceRoll): OverlayElement {
    return {
      id: `dice-${diceRoll.id}`,
      type: 'dice',
      position: { x: 50, y: 100, anchor: 'top-left' },
      size: { width: 300, height: 150, scale: 1 },
      style: {
        background: 'rgba(0, 0, 0, 0.8)',
        borderRadius: 10,
        color: '#ffffff',
        fontSize: 18,
        fontFamily: 'Arial, sans-serif'
      },
      data: {
        username: diceRoll.username,
        notation: diceRoll.notation,
        result: diceRoll.result,
        timestamp: diceRoll.timestamp
      },
      visible: true,
      animation: {
        type: 'slide',
        duration: 500,
        easing: 'ease-out'
      }
    };
  }

  public createCharacterShowcase(character: Character): OverlayElement {
    return {
      id: `character-${character.id}`,
      type: 'character',
      position: { x: 1400, y: 50, anchor: 'top-left' },
      size: { width: 450, height: 600, scale: 1 },
      style: {
        background: 'linear-gradient(135deg, rgba(0,0,0,0.9), rgba(20,20,20,0.9))',
        border: '2px solid #d4af37',
        borderRadius: 15,
        color: '#ffffff',
        fontSize: 16,
        fontFamily: 'Arial, sans-serif'
      },
      data: {
        character: character,
        showStats: true,
        showEquipment: true,
        showSpells: false
      },
      visible: true
    };
  }

  public createPollOverlay(poll: ViewerPoll): OverlayElement {
    return {
      id: `poll-${poll.id}`,
      type: 'poll',
      position: { x: 50, y: 300, anchor: 'top-left' },
      size: { width: 400, height: 250, scale: 1 },
      style: {
        background: 'rgba(30, 30, 30, 0.95)',
        border: '2px solid #6441a5',
        borderRadius: 12,
        color: '#ffffff',
        fontSize: 14,
        fontFamily: 'Arial, sans-serif'
      },
      data: {
        poll: poll,
        showPercentages: true,
        showVoterCount: true
      },
      visible: true,
      animation: {
        type: 'fade',
        duration: 300,
        easing: 'ease-in'
      }
    };
  }

  public createDonationAlert(donation: Donation): OverlayElement {
    return {
      id: `donation-${donation.id}`,
      type: 'donation',
      position: { x: 960, y: 50, anchor: 'center' },
      size: { width: 500, height: 200, scale: 1 },
      style: {
        background: 'linear-gradient(45deg, #ff6b6b, #feca57)',
        border: '3px solid #ffffff',
        borderRadius: 20,
        color: '#ffffff',
        fontSize: 24,
        fontFamily: 'Arial Black, sans-serif',
        shadow: '0 0 20px rgba(255, 107, 107, 0.5)'
      },
      data: {
        donation: donation,
        showAmount: true,
        showMessage: true,
        duration: 8000
      },
      visible: true,
      animation: {
        type: 'bounce',
        duration: 1000,
        easing: 'ease-out'
      }
    };
  }

  public createCampaignProgress(campaign: any): OverlayElement {
    return {
      id: 'campaign-progress',
      type: 'progress',
      position: { x: 50, y: 950, anchor: 'top-left' },
      size: { width: 800, height: 80, scale: 1 },
      style: {
        background: 'rgba(0, 0, 0, 0.7)',
        borderRadius: 8,
        color: '#ffffff',
        fontSize: 14,
        fontFamily: 'Arial, sans-serif'
      },
      data: {
        campaign: campaign,
        showLevel: true,
        showXP: true,
        showObjectives: true
      },
      visible: true
    };
  }

  private render(): void {
    // Clear canvas
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    
    // Render elements in order
    const sortedElements = Array.from(this.elements.values())
      .filter(el => el.visible)
      .sort((a, b) => (a.data.zIndex || 0) - (b.data.zIndex || 0));

    for (const element of sortedElements) {
      this.renderElement(element);
    }

    // Save to file for OBS browser source
    this.saveToFile();
    this.emit('rendered');
  }

  private renderElement(element: OverlayElement): void {
    const { x, y } = this.getAbsolutePosition(element);
    
    this.ctx.save();
    this.ctx.translate(x, y);
    this.ctx.scale(element.size.scale, element.size.scale);

    switch (element.type) {
      case 'dice':
        this.renderDiceElement(element);
        break;
      case 'character':
        this.renderCharacterElement(element);
        break;
      case 'poll':
        this.renderPollElement(element);
        break;
      case 'donation':
        this.renderDonationElement(element);
        break;
      case 'progress':
        this.renderProgressElement(element);
        break;
      case 'timer':
        this.renderTimerElement(element);
        break;
      case 'text':
        this.renderTextElement(element);
        break;
      case 'image':
        this.renderImageElement(element);
        break;
    }

    this.ctx.restore();
  }

  private renderDiceElement(element: OverlayElement): void {
    const { username, notation, result, timestamp } = element.data;
    
    // Background
    this.drawRoundedRect(0, 0, element.size.width, element.size.height, 
                        element.style.borderRadius || 0, element.style.background);
    
    this.ctx.fillStyle = element.style.color || '#ffffff';
    this.ctx.font = `${element.style.fontSize}px ${element.style.fontFamily}`;
    
    // Username
    this.ctx.font = `bold ${element.style.fontSize + 2}px ${element.style.fontFamily}`;
    this.ctx.fillText(`${username} rolled:`, 15, 20);
    
    // Dice notation
    this.ctx.font = `${element.style.fontSize}px ${element.style.fontFamily}`;
    this.ctx.fillText(notation, 15, 50);
    
    // Result with color coding
    const resultText = `Result: ${result.total}`;
    this.ctx.font = `bold ${element.style.fontSize + 4}px ${element.style.fontFamily}`;
    
    if (result.critical) {
      this.ctx.fillStyle = '#00ff00'; // Green for critical success
    } else if (result.fumble) {
      this.ctx.fillStyle = '#ff0000'; // Red for critical failure
    } else {
      this.ctx.fillStyle = '#ffff00'; // Yellow for normal rolls
    }
    
    this.ctx.fillText(resultText, 15, 80);
    
    // Breakdown
    this.ctx.fillStyle = element.style.color || '#ffffff';
    this.ctx.font = `${element.style.fontSize - 2}px ${element.style.fontFamily}`;
    this.ctx.fillText(result.breakdown, 15, 110);
    
    // Timestamp
    const timeAgo = this.getTimeAgo(timestamp);
    this.ctx.fillText(timeAgo, element.size.width - 80, element.size.height - 20);
  }

  private renderCharacterElement(element: OverlayElement): void {
    const { character, showStats, showEquipment, showSpells } = element.data;
    
    // Background with gradient effect
    this.drawRoundedRect(0, 0, element.size.width, element.size.height, 
                        element.style.borderRadius || 0, element.style.background);
    
    // Border
    if (element.style.border) {
      this.ctx.strokeStyle = element.style.border;
      this.ctx.lineWidth = 2;
      this.ctx.strokeRect(0, 0, element.size.width, element.size.height);
    }
    
    this.ctx.fillStyle = element.style.color || '#ffffff';
    let yOffset = 20;
    
    // Character name and basic info
    this.ctx.font = `bold ${element.style.fontSize + 6}px ${element.style.fontFamily}`;
    this.ctx.fillText(character.name, 20, yOffset);
    yOffset += 30;
    
    this.ctx.font = `${element.style.fontSize}px ${element.style.fontFamily}`;
    this.ctx.fillText(`Level ${character.level} ${character.race} ${character.class}`, 20, yOffset);
    yOffset += 25;
    
    // Portrait placeholder
    this.ctx.strokeStyle = '#666666';
    this.ctx.strokeRect(20, yOffset, 100, 120);
    this.ctx.fillStyle = '#333333';
    this.ctx.fillRect(20, yOffset, 100, 120);
    yOffset += 130;
    
    if (showStats) {
      // Health
      this.ctx.fillStyle = element.style.color || '#ffffff';
      this.ctx.font = `${element.style.fontSize}px ${element.style.fontFamily}`;
      this.ctx.fillText(`HP: ${character.stats.hitPoints.current}/${character.stats.hitPoints.maximum}`, 140, yOffset - 100);
      this.ctx.fillText(`AC: ${character.stats.armorClass}`, 140, yOffset - 80);
      this.ctx.fillText(`Speed: ${character.stats.speed} ft`, 140, yOffset - 60);
      
      // Ability scores
      const abilities = character.stats.abilities;
      let xOffset = 20;
      yOffset += 20;
      
      Object.entries(abilities).forEach(([ability, score]) => {
        this.ctx.fillText(`${ability.substring(0, 3).toUpperCase()}: ${score}`, xOffset, yOffset);
        xOffset += 60;
        if (xOffset > element.size.width - 60) {
          xOffset = 20;
          yOffset += 25;
        }
      });
    }
    
    if (showEquipment && character.equipment.length > 0) {
      yOffset += 30;
      this.ctx.font = `bold ${element.style.fontSize}px ${element.style.fontFamily}`;
      this.ctx.fillText('Equipment:', 20, yOffset);
      yOffset += 25;
      
      this.ctx.font = `${element.style.fontSize - 2}px ${element.style.fontFamily}`;
      character.equipment.slice(0, 5).forEach(item => {
        if (item.equipped) {
          this.ctx.fillStyle = '#ffff00'; // Highlight equipped items
          this.ctx.fillText(`• ${item.name} (equipped)`, 20, yOffset);
        } else {
          this.ctx.fillStyle = element.style.color || '#ffffff';
          this.ctx.fillText(`• ${item.name}`, 20, yOffset);
        }
        yOffset += 20;
      });
    }
  }

  private renderPollElement(element: OverlayElement): void {
    const { poll, showPercentages, showVoterCount } = element.data;
    
    // Background
    this.drawRoundedRect(0, 0, element.size.width, element.size.height, 
                        element.style.borderRadius || 0, element.style.background);
    
    this.ctx.fillStyle = element.style.color || '#ffffff';
    this.ctx.font = `bold ${element.style.fontSize + 2}px ${element.style.fontFamily}`;
    
    // Poll question
    this.ctx.fillText('Poll:', 15, 20);
    this.ctx.font = `${element.style.fontSize}px ${element.style.fontFamily}`;
    this.wrapText(poll.question, 15, 45, element.size.width - 30, 20);
    
    let yOffset = 90;
    
    // Poll options
    poll.options.forEach((option, index) => {
      const percentage = poll.totalVotes > 0 ? (option.votes / poll.totalVotes) * 100 : 0;
      
      // Option background bar
      const barWidth = (element.size.width - 30) * (percentage / 100);
      this.ctx.fillStyle = `hsl(${index * 60}, 70%, 50%)`;
      this.ctx.fillRect(15, yOffset - 15, barWidth, 25);
      
      // Option text
      this.ctx.fillStyle = element.style.color || '#ffffff';
      this.ctx.font = `${element.style.fontSize}px ${element.style.fontFamily}`;
      
      let optionText = `${index + 1}. ${option.text}`;
      if (showPercentages) {
        optionText += ` (${percentage.toFixed(1)}%)`;
      }
      if (showVoterCount) {
        optionText += ` - ${option.votes} votes`;
      }
      
      this.ctx.fillText(optionText, 20, yOffset);
      yOffset += 35;
    });
    
    // Poll status
    const timeLeft = poll.endTime ? Math.max(0, poll.endTime.getTime() - Date.now()) / 1000 : 0;
    this.ctx.font = `${element.style.fontSize - 2}px ${element.style.fontFamily}`;
    this.ctx.fillStyle = '#cccccc';
    this.ctx.fillText(`Time left: ${Math.ceil(timeLeft)}s | Total votes: ${poll.totalVotes}`, 
                     15, element.size.height - 15);
  }

  private renderDonationElement(element: OverlayElement): void {
    const { donation, showAmount, showMessage } = element.data;
    
    // Background with gradient
    this.drawRoundedRect(0, 0, element.size.width, element.size.height, 
                        element.style.borderRadius || 0, element.style.background);
    
    // Border with glow effect
    if (element.style.border) {
      this.ctx.strokeStyle = element.style.border;
      this.ctx.lineWidth = 3;
      this.ctx.shadowColor = '#ff6b6b';
      this.ctx.shadowBlur = 10;
      this.ctx.strokeRect(0, 0, element.size.width, element.size.height);
      this.ctx.shadowBlur = 0;
    }
    
    this.ctx.fillStyle = element.style.color || '#ffffff';
    this.ctx.textAlign = 'center';
    
    // Thank you message
    this.ctx.font = `bold ${element.style.fontSize}px ${element.style.fontFamily}`;
    this.ctx.fillText('Thank you!', element.size.width / 2, 30);
    
    // Donor name
    this.ctx.font = `bold ${element.style.fontSize + 2}px ${element.style.fontFamily}`;
    this.ctx.fillText(donation.username, element.size.width / 2, 65);
    
    if (showAmount) {
      // Donation amount
      this.ctx.font = `bold ${element.style.fontSize + 8}px ${element.style.fontFamily}`;
      this.ctx.fillStyle = '#ffff00';
      this.ctx.fillText(`$${donation.amount}`, element.size.width / 2, 105);
    }
    
    if (showMessage && donation.message) {
      // Donation message
      this.ctx.fillStyle = element.style.color || '#ffffff';
      this.ctx.font = `${element.style.fontSize - 2}px ${element.style.fontFamily}`;
      this.wrapText(donation.message, element.size.width / 2, 140, element.size.width - 40, 18);
    }
    
    this.ctx.textAlign = 'left';
  }

  private renderProgressElement(element: OverlayElement): void {
    const { campaign, showLevel, showXP, showObjectives } = element.data;
    
    // Background
    this.drawRoundedRect(0, 0, element.size.width, element.size.height, 
                        element.style.borderRadius || 0, element.style.background);
    
    this.ctx.fillStyle = element.style.color || '#ffffff';
    this.ctx.font = `${element.style.fontSize}px ${element.style.fontFamily}`;
    
    let xOffset = 15;
    
    // Campaign name
    this.ctx.font = `bold ${element.style.fontSize}px ${element.style.fontFamily}`;
    this.ctx.fillText(campaign.name, xOffset, 25);
    xOffset += this.ctx.measureText(campaign.name).width + 30;
    
    if (showLevel) {
      // Party level (average)
      this.ctx.font = `${element.style.fontSize}px ${element.style.fontFamily}`;
      const avgLevel = campaign.characters?.reduce((sum: number, char: any) => sum + char.level, 0) / campaign.characters?.length || 1;
      this.ctx.fillText(`Level ${Math.round(avgLevel)}`, xOffset, 25);
      xOffset += 80;
    }
    
    if (showXP) {
      // Experience progress bar
      const totalXP = campaign.characters?.reduce((sum: number, char: any) => sum + (char.experience || 0), 0) || 0;
      const nextLevelXP = this.getNextLevelXP(Math.round(totalXP / (campaign.characters?.length || 1)));
      
      this.ctx.fillText('XP:', xOffset, 25);
      xOffset += 30;
      
      // XP Progress bar
      const barWidth = 200;
      const progress = (totalXP % nextLevelXP) / nextLevelXP;
      
      this.ctx.fillStyle = '#333333';
      this.ctx.fillRect(xOffset, 10, barWidth, 20);
      this.ctx.fillStyle = '#00ff00';
      this.ctx.fillRect(xOffset, 10, barWidth * progress, 20);
      
      this.ctx.fillStyle = element.style.color || '#ffffff';
      this.ctx.font = `${element.style.fontSize - 2}px ${element.style.fontFamily}`;
      this.ctx.fillText(`${Math.round(totalXP % nextLevelXP)}/${nextLevelXP}`, xOffset + 5, 23);
    }
    
    if (showObjectives && campaign.currentObjectives) {
      // Current objectives
      this.ctx.font = `${element.style.fontSize - 2}px ${element.style.fontFamily}`;
      this.ctx.fillText(`Objective: ${campaign.currentObjectives[0] || 'Explore the world!'}`, 
                       15, element.size.height - 15);
    }
  }

  private renderTimerElement(element: OverlayElement): void {
    const { startTime, duration, label } = element.data;
    
    this.drawRoundedRect(0, 0, element.size.width, element.size.height, 
                        element.style.borderRadius || 0, element.style.background);
    
    this.ctx.fillStyle = element.style.color || '#ffffff';
    this.ctx.font = `bold ${element.style.fontSize + 4}px ${element.style.fontFamily}`;
    this.ctx.textAlign = 'center';
    
    const elapsed = (Date.now() - startTime) / 1000;
    const remaining = Math.max(0, duration - elapsed);
    
    const minutes = Math.floor(remaining / 60);
    const seconds = Math.floor(remaining % 60);
    const timeString = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    
    if (label) {
      this.ctx.font = `${element.style.fontSize}px ${element.style.fontFamily}`;
      this.ctx.fillText(label, element.size.width / 2, 20);
    }
    
    this.ctx.font = `bold ${element.style.fontSize + 8}px ${element.style.fontFamily}`;
    this.ctx.fillText(timeString, element.size.width / 2, element.size.height / 2 + 10);
    
    this.ctx.textAlign = 'left';
  }

  private renderTextElement(element: OverlayElement): void {
    const { text, alignment } = element.data;
    
    if (element.style.background) {
      this.drawRoundedRect(0, 0, element.size.width, element.size.height, 
                          element.style.borderRadius || 0, element.style.background);
    }
    
    this.ctx.fillStyle = element.style.color || '#ffffff';
    this.ctx.font = `${element.style.fontSize}px ${element.style.fontFamily}`;
    this.ctx.textAlign = alignment || 'left';
    
    const x = alignment === 'center' ? element.size.width / 2 : 
              alignment === 'right' ? element.size.width : 0;
    
    this.wrapText(text, x, 20, element.size.width, element.style.fontSize + 5);
    this.ctx.textAlign = 'left';
  }

  private renderImageElement(element: OverlayElement): void {
    // Image rendering would require loading actual image files
    // For now, render a placeholder
    this.ctx.fillStyle = '#666666';
    this.ctx.fillRect(0, 0, element.size.width, element.size.height);
    
    this.ctx.fillStyle = '#ffffff';
    this.ctx.font = `${element.style.fontSize}px ${element.style.fontFamily}`;
    this.ctx.textAlign = 'center';
    this.ctx.fillText('Image Placeholder', element.size.width / 2, element.size.height / 2);
    this.ctx.textAlign = 'left';
  }

  private getAbsolutePosition(element: OverlayElement): { x: number; y: number } {
    const { x, y, anchor } = element.position;
    let absoluteX = x;
    let absoluteY = y;

    switch (anchor) {
      case 'top-right':
        absoluteX = this.canvas.width - x - element.size.width;
        break;
      case 'bottom-left':
        absoluteY = this.canvas.height - y - element.size.height;
        break;
      case 'bottom-right':
        absoluteX = this.canvas.width - x - element.size.width;
        absoluteY = this.canvas.height - y - element.size.height;
        break;
      case 'center':
        absoluteX = (this.canvas.width - element.size.width) / 2 + x;
        absoluteY = (this.canvas.height - element.size.height) / 2 + y;
        break;
    }

    return { x: absoluteX, y: absoluteY };
  }

  private drawRoundedRect(x: number, y: number, width: number, height: number, 
                         radius: number, fillStyle: string): void {
    this.ctx.beginPath();
    this.ctx.moveTo(x + radius, y);
    this.ctx.lineTo(x + width - radius, y);
    this.ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
    this.ctx.lineTo(x + width, y + height - radius);
    this.ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
    this.ctx.lineTo(x + radius, y + height);
    this.ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
    this.ctx.lineTo(x, y + radius);
    this.ctx.quadraticCurveTo(x, y, x + radius, y);
    this.ctx.closePath();
    
    this.ctx.fillStyle = fillStyle;
    this.ctx.fill();
  }

  private wrapText(text: string, x: number, y: number, maxWidth: number, lineHeight: number): void {
    const words = text.split(' ');
    let line = '';
    let currentY = y;

    for (const word of words) {
      const testLine = line + word + ' ';
      const metrics = this.ctx.measureText(testLine);
      const testWidth = metrics.width;

      if (testWidth > maxWidth && line.length > 0) {
        this.ctx.fillText(line.trim(), x, currentY);
        line = word + ' ';
        currentY += lineHeight;
      } else {
        line = testLine;
      }
    }
    this.ctx.fillText(line.trim(), x, currentY);
  }

  private getTimeAgo(timestamp: Date): string {
    const seconds = Math.floor((Date.now() - timestamp.getTime()) / 1000);
    
    if (seconds < 60) return 'now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
    return `${Math.floor(seconds / 86400)}d`;
  }

  private getNextLevelXP(level: number): number {
    // D&D 5e XP thresholds
    const xpThresholds = [0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000, 85000, 100000];
    return xpThresholds[Math.min(level + 1, xpThresholds.length - 1)] || 100000;
  }

  private startAnimation(element: OverlayElement): void {
    if (!element.animation) return;

    const animationId = setInterval(() => {
      // Simple animation implementation
      this.render();
    }, 16); // 60fps

    this.animations.set(element.id, animationId);

    // Auto-remove temporary elements
    if (element.data.duration) {
      setTimeout(() => {
        this.removeElement(element.id);
      }, element.data.duration);
    }
  }

  private stopAnimation(elementId: string): void {
    const animation = this.animations.get(elementId);
    if (animation) {
      clearInterval(animation);
      this.animations.delete(elementId);
    }
  }

  private saveToFile(): void {
    const buffer = this.canvas.toBuffer('image/png');
    const filename = path.join(this.outputPath, 'current-overlay.png');
    fs.writeFileSync(filename, buffer);
    
    // Also save as HTML for browser source
    this.generateHTMLOverlay();
  }

  private generateHTMLOverlay(): void {
    const htmlContent = `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>DMLog Overlay</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            background: transparent;
            overflow: hidden;
            font-family: Arial, sans-serif;
        }
        .overlay-container {
            width: 1920px;
            height: 1080px;
            position: relative;
            background: transparent;
        }
        .overlay-element {
            position: absolute;
            pointer-events: none;
        }
    </style>
    <script src="/socket.io/socket.io.js"></script>
</head>
<body>
    <div class="overlay-container" id="overlay">
        <img src="current-overlay.png" style="width: 100%; height: 100%;" />
    </div>
    
    <script>
        const socket = io();
        
        socket.on('overlay-update', (data) => {
            const img = document.querySelector('img');
            img.src = 'current-overlay.png?' + Date.now();
        });
        
        // Auto-refresh every 100ms for smooth updates
        setInterval(() => {
            const img = document.querySelector('img');
            img.src = 'current-overlay.png?' + Date.now();
        }, 100);
    </script>
</body>
</html>`;

    const htmlPath = path.join(this.outputPath, 'overlay.html');
    fs.writeFileSync(htmlPath, htmlContent);
  }

  public getOverlayURL(): string {
    return `http://localhost:3000/overlays/overlay.html`;
  }

  public exportSettings(): any {
    return {
      elements: Array.from(this.elements.entries()),
      settings: this.settings,
      canvasSize: { width: this.canvas.width, height: this.canvas.height }
    };
  }

  public importSettings(data: any): void {
    this.elements.clear();
    this.settings = data.settings;
    
    if (data.elements) {
      data.elements.forEach(([id, element]: [string, OverlayElement]) => {
        this.elements.set(id, element);
      });
    }
    
    this.render();
  }
}