import { createCanvas, loadImage } from 'canvas';
import sharp from 'sharp';
import WebSocket from 'ws';
const { WebSocketServer } = WebSocket;
import fs from 'fs/promises';
import path from 'path';

class StreamingOverlay {
  constructor() {
    this.overlays = new Map();
    this.templates = new Map();
    this.activeStreams = new Map();
    this.websocketServer = null;
    
    this.initializeTemplates();
    this.setupWebSocketServer();
  }

  async initializeTemplates() {
    // Pre-built overlay templates
    this.templates.set('initiative', {
      name: 'Initiative Tracker',
      dimensions: { width: 300, height: 600 },
      position: { x: 'right', y: 'top' },
      background: 'rgba(0, 0, 0, 0.7)',
      elements: ['current_turn', 'turn_order', 'round_counter']
    });

    this.templates.set('dice', {
      name: 'Dice Results',
      dimensions: { width: 400, height: 200 },
      position: { x: 'center', y: 'bottom' },
      background: 'rgba(25, 25, 112, 0.8)',
      elements: ['last_roll', 'roll_history', 'roll_animation']
    });

    this.templates.set('healthbars', {
      name: 'Health Bars',
      dimensions: { width: 500, height: 150 },
      position: { x: 'left', y: 'top' },
      background: 'transparent',
      elements: ['party_health', 'enemy_health', 'boss_health']
    });

    this.templates.set('battlemap', {
      name: 'Battle Map Overlay',
      dimensions: { width: 800, height: 600 },
      position: { x: 'center', y: 'center' },
      background: 'transparent',
      elements: ['grid', 'tokens', 'effects', 'measurements']
    });

    this.templates.set('spellcasts', {
      name: 'Spell Effects',
      dimensions: { width: 300, height: 400 },
      position: { x: 'right', y: 'center' },
      background: 'rgba(75, 0, 130, 0.6)',
      elements: ['active_spells', 'spell_descriptions', 'duration_timers']
    });
  }

  setupWebSocketServer() {
    this.websocketServer = new WebSocketServer({ port: 8510 });
    
    this.websocketServer.on('connection', (ws) => {
      ws.on('message', (message) => {
        try {
          const data = JSON.parse(message);
          this.handleStreamingCommand(ws, data);
        } catch (error) {
          console.error('WebSocket message error:', error);
        }
      });
    });
  }

  async handleStreamingCommand(ws, data) {
    const { command, streamId, payload } = data;

    switch (command) {
      case 'create_overlay':
        await this.createOverlay(streamId, payload);
        break;
      case 'update_overlay':
        await this.updateOverlay(streamId, payload);
        break;
      case 'animate_dice':
        await this.animateDiceRoll(streamId, payload);
        break;
      case 'show_spell_effect':
        await this.showSpellEffect(streamId, payload);
        break;
      case 'update_initiative':
        await this.updateInitiativeTracker(streamId, payload);
        break;
    }

    // Broadcast update to all connected clients
    this.broadcastOverlayUpdate(streamId);
  }

  async createOverlay(streamId, config) {
    const { template, customization } = config;
    const templateData = this.templates.get(template);
    
    if (!templateData) {
      throw new Error(`Unknown template: ${template}`);
    }

    const overlay = {
      id: `${streamId}_${template}`,
      streamId,
      template,
      ...templateData,
      ...customization,
      elements: {},
      lastUpdate: Date.now()
    };

    this.overlays.set(overlay.id, overlay);
    
    // Generate initial overlay image
    await this.renderOverlay(overlay.id);
    
    return overlay;
  }

  async updateOverlay(streamId, update) {
    const overlayId = `${streamId}_${update.template}`;
    const overlay = this.overlays.get(overlayId);
    
    if (!overlay) {
      throw new Error(`Overlay not found: ${overlayId}`);
    }

    // Update overlay data
    Object.assign(overlay.elements, update.data);
    overlay.lastUpdate = Date.now();

    // Re-render overlay
    await this.renderOverlay(overlayId);
    
    return overlay;
  }

  async renderOverlay(overlayId) {
    const overlay = this.overlays.get(overlayId);
    if (!overlay) return;

    const { dimensions, background } = overlay;
    const canvas = createCanvas(dimensions.width, dimensions.height);
    const ctx = canvas.getContext('2d');

    // Set background
    if (background !== 'transparent') {
      ctx.fillStyle = background;
      ctx.fillRect(0, 0, dimensions.width, dimensions.height);
    }

    // Render based on template
    switch (overlay.template) {
      case 'initiative':
        await this.renderInitiativeTracker(ctx, overlay);
        break;
      case 'dice':
        await this.renderDiceResults(ctx, overlay);
        break;
      case 'healthbars':
        await this.renderHealthBars(ctx, overlay);
        break;
      case 'battlemap':
        await this.renderBattleMapOverlay(ctx, overlay);
        break;
      case 'spellcasts':
        await this.renderSpellEffects(ctx, overlay);
        break;
    }

    // Save overlay image
    const buffer = canvas.toBuffer('image/png');
    const overlayPath = path.join(process.cwd(), 'overlays', `${overlayId}.png`);
    
    // Ensure directory exists
    await fs.mkdir(path.dirname(overlayPath), { recursive: true });
    await fs.writeFile(overlayPath, buffer);

    // Also create webp version for better compression
    await sharp(buffer)
      .webp({ quality: 90 })
      .toFile(overlayPath.replace('.png', '.webp'));

    return overlayPath;
  }

  async renderInitiativeTracker(ctx, overlay) {
    const { elements } = overlay;
    const { turn_order = [], current_turn = 0, round_counter = 1 } = elements;

    ctx.font = 'bold 24px Arial';
    ctx.fillStyle = '#ffffff';
    ctx.fillText(`Round ${round_counter}`, 20, 40);

    ctx.font = '18px Arial';
    let y = 80;

    turn_order.forEach((character, index) => {
      const isActive = index === current_turn;
      
      // Highlight active character
      if (isActive) {
        ctx.fillStyle = 'rgba(255, 255, 0, 0.3)';
        ctx.fillRect(10, y - 25, 280, 35);
      }

      // Character name and initiative
      ctx.fillStyle = isActive ? '#ffff00' : '#ffffff';
      ctx.fillText(`${character.initiative}`, 20, y);
      ctx.fillText(character.name, 60, y);

      // Health bar if available
      if (character.health) {
        const healthWidth = 100;
        const healthPercent = character.health.current / character.health.max;
        
        ctx.fillStyle = '#333333';
        ctx.fillRect(180, y - 15, healthWidth, 12);
        
        ctx.fillStyle = healthPercent > 0.5 ? '#4CAF50' : 
                       healthPercent > 0.25 ? '#FF9800' : '#F44336';
        ctx.fillRect(180, y - 15, healthWidth * healthPercent, 12);
      }

      y += 40;
    });
  }

  async renderDiceResults(ctx, overlay) {
    const { elements } = overlay;
    const { last_roll, roll_history = [], roll_animation } = elements;

    if (last_roll) {
      // Main dice result
      ctx.font = 'bold 48px Arial';
      ctx.fillStyle = '#ffffff';
      ctx.textAlign = 'center';
      ctx.fillText(last_roll.result.toString(), 200, 100);
      
      ctx.font = '16px Arial';
      ctx.fillText(`d${last_roll.sides}`, 200, 125);

      // Animation effect
      if (roll_animation && roll_animation.active) {
        const alpha = Math.sin(Date.now() / 200) * 0.5 + 0.5;
        ctx.save();
        ctx.globalAlpha = alpha;
        ctx.strokeStyle = '#ffff00';
        ctx.lineWidth = 3;
        ctx.strokeRect(150, 50, 100, 100);
        ctx.restore();
      }
    }

    // Roll history
    if (roll_history.length > 0) {
      ctx.font = '12px Arial';
      ctx.fillStyle = '#cccccc';
      ctx.textAlign = 'left';
      
      let y = 170;
      roll_history.slice(-5).forEach((roll) => {
        ctx.fillText(`d${roll.sides}: ${roll.result}`, 20, y);
        y += 15;
      });
    }
  }

  async renderHealthBars(ctx, overlay) {
    const { elements } = overlay;
    const { party_health = [], enemy_health = [], boss_health } = elements;

    let y = 20;

    // Party health bars
    if (party_health.length > 0) {
      ctx.font = 'bold 14px Arial';
      ctx.fillStyle = '#ffffff';
      ctx.fillText('Party', 20, y);
      y += 25;

      party_health.forEach((character) => {
        this.drawHealthBar(ctx, 20, y, 200, 15, character);
        y += 25;
      });
    }

    // Enemy health bars
    if (enemy_health.length > 0) {
      y += 10;
      ctx.font = 'bold 14px Arial';
      ctx.fillStyle = '#ffffff';
      ctx.fillText('Enemies', 250, y);
      y += 25;

      enemy_health.forEach((enemy) => {
        this.drawHealthBar(ctx, 250, y, 200, 15, enemy);
        y += 25;
      });
    }

    // Boss health bar
    if (boss_health) {
      y += 20;
      ctx.font = 'bold 16px Arial';
      ctx.fillStyle = '#ff4444';
      ctx.fillText(boss_health.name, 20, y);
      y += 25;
      this.drawHealthBar(ctx, 20, y, 460, 25, boss_health, true);
    }
  }

  drawHealthBar(ctx, x, y, width, height, character, isBoss = false) {
    const healthPercent = character.health.current / character.health.max;
    
    // Background
    ctx.fillStyle = '#333333';
    ctx.fillRect(x, y, width, height);
    
    // Health fill
    if (isBoss) {
      ctx.fillStyle = '#8B0000';
    } else {
      ctx.fillStyle = healthPercent > 0.5 ? '#4CAF50' : 
                     healthPercent > 0.25 ? '#FF9800' : '#F44336';
    }
    ctx.fillRect(x, y, width * healthPercent, height);
    
    // Text overlay
    ctx.fillStyle = '#ffffff';
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(character.name, x + width/2, y + height - 3);
  }

  async animateDiceRoll(streamId, rollData) {
    const overlayId = `${streamId}_dice`;
    const overlay = this.overlays.get(overlayId);
    
    if (!overlay) return;

    // Start animation
    overlay.elements.roll_animation = { active: true, startTime: Date.now() };
    
    // Update multiple times during animation
    const animationSteps = 10;
    const animationDuration = 1000; // 1 second
    
    for (let i = 0; i < animationSteps; i++) {
      setTimeout(async () => {
        if (i === animationSteps - 1) {
          // Final result
          overlay.elements.last_roll = rollData;
          overlay.elements.roll_animation = { active: false };
          
          // Add to history
          if (!overlay.elements.roll_history) {
            overlay.elements.roll_history = [];
          }
          overlay.elements.roll_history.push(rollData);
          
          // Keep only last 10 rolls
          if (overlay.elements.roll_history.length > 10) {
            overlay.elements.roll_history = overlay.elements.roll_history.slice(-10);
          }
        }
        
        await this.renderOverlay(overlayId);
        this.broadcastOverlayUpdate(streamId);
      }, (animationDuration / animationSteps) * i);
    }
  }

  async showSpellEffect(streamId, spellData) {
    const overlayId = `${streamId}_spellcasts`;
    const overlay = this.overlays.get(overlayId);
    
    if (!overlay) return;

    if (!overlay.elements.active_spells) {
      overlay.elements.active_spells = [];
    }

    // Add spell to active list
    const spell = {
      ...spellData,
      startTime: Date.now(),
      id: `spell_${Date.now()}`
    };

    overlay.elements.active_spells.push(spell);

    // Auto-remove after duration
    if (spellData.duration) {
      setTimeout(() => {
        overlay.elements.active_spells = overlay.elements.active_spells.filter(
          s => s.id !== spell.id
        );
        this.renderOverlay(overlayId);
        this.broadcastOverlayUpdate(streamId);
      }, spellData.duration * 1000);
    }

    await this.renderOverlay(overlayId);
    this.broadcastOverlayUpdate(streamId);
  }

  async renderSpellEffects(ctx, overlay) {
    const { elements } = overlay;
    const { active_spells = [] } = elements;

    ctx.font = 'bold 16px Arial';
    ctx.fillStyle = '#ffffff';
    ctx.fillText('Active Spells', 20, 30);

    let y = 60;
    active_spells.forEach((spell) => {
      const timeLeft = spell.duration - (Date.now() - spell.startTime) / 1000;
      
      if (timeLeft > 0) {
        ctx.font = 'bold 14px Arial';
        ctx.fillStyle = '#bb86fc';
        ctx.fillText(spell.name, 20, y);
        
        ctx.font = '12px Arial';
        ctx.fillStyle = '#ffffff';
        ctx.fillText(`${Math.ceil(timeLeft)}s`, 200, y);
        
        // Duration bar
        const barWidth = 200;
        const timePercent = timeLeft / spell.duration;
        
        ctx.fillStyle = '#333333';
        ctx.fillRect(20, y + 5, barWidth, 8);
        
        ctx.fillStyle = '#bb86fc';
        ctx.fillRect(20, y + 5, barWidth * timePercent, 8);
        
        y += 40;
      }
    });
  }

  broadcastOverlayUpdate(streamId) {
    const message = JSON.stringify({
      type: 'overlay_updated',
      streamId,
      timestamp: Date.now()
    });

    this.websocketServer.clients.forEach((client) => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(message);
      }
    });
  }

  // OBS Studio integration helpers
  async generateOBSSceneCollection(streamId, overlayConfigs) {
    const sceneCollection = {
      name: `DMLog_${streamId}`,
      scenes: []
    };

    for (const config of overlayConfigs) {
      const overlay = await this.createOverlay(streamId, config);
      const overlayPath = await this.renderOverlay(overlay.id);
      
      sceneCollection.scenes.push({
        name: overlay.template,
        sources: [{
          name: `DMLog_${overlay.template}`,
          type: 'image_source',
          settings: {
            file: overlayPath,
            linear_alpha: true
          },
          transform: {
            pos: this.calculateOBSPosition(overlay.position, overlay.dimensions),
            scale: { x: 1.0, y: 1.0 },
            rot: 0.0
          }
        }]
      });
    }

    return sceneCollection;
  }

  calculateOBSPosition(position, dimensions) {
    const streamWidth = 1920; // Assuming 1080p stream
    const streamHeight = 1080;
    
    let x = 0, y = 0;
    
    switch (position.x) {
      case 'left': x = 50; break;
      case 'center': x = (streamWidth - dimensions.width) / 2; break;
      case 'right': x = streamWidth - dimensions.width - 50; break;
      default: x = position.x; break;
    }
    
    switch (position.y) {
      case 'top': y = 50; break;
      case 'center': y = (streamHeight - dimensions.height) / 2; break;
      case 'bottom': y = streamHeight - dimensions.height - 50; break;
      default: y = position.y; break;
    }
    
    return { x, y };
  }

  // Export overlay as video clip
  async generateClip(streamId, duration = 30) {
    // This would integrate with FFmpeg to create video clips
    // Implementation would depend on specific requirements
    return {
      status: 'generated',
      path: `/clips/${streamId}_${Date.now()}.mp4`,
      duration
    };
  }

  // Get overlay status for a stream
  getStreamOverlays(streamId) {
    const streamOverlays = [];
    
    for (const [id, overlay] of this.overlays.entries()) {
      if (overlay.streamId === streamId) {
        streamOverlays.push({
          id: overlay.id,
          template: overlay.template,
          lastUpdate: overlay.lastUpdate,
          active: Date.now() - overlay.lastUpdate < 300000 // 5 minutes
        });
      }
    }
    
    return streamOverlays;
  }
}

export default StreamingOverlay;