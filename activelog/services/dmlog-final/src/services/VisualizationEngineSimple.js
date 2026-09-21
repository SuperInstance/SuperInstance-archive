import { createCanvas } from 'canvas';
import sharp from 'sharp';
import fs from 'fs/promises';
import path from 'path';

class VisualizationEngine {
  constructor() {
    this.renderWidth = 1920;
    this.renderHeight = 1080;
    this.initialized = false;
    this.materials = new Map();
    this.geometries = new Map();
    
    this.initializeEngine();
  }

  async initializeEngine() {
    console.log('Initializing visualization engine in headless mode');
    
    // Store basic configuration for later use
    this.initialized = true;
    
    // Load default materials and geometries
    await this.loadDefaultAssets();
  }

  async loadDefaultAssets() {
    // For headless mode, we'll use simplified 2D canvas-based rendering
    console.log('Loading simplified assets for headless rendering');
    
    // Store basic material properties for canvas rendering
    this.materials.set('stone', { color: '#808080', pattern: 'stone' });
    this.materials.set('wood', { color: '#8B4513', pattern: 'wood' });
    this.materials.set('metal', { color: '#C0C0C0', pattern: 'metal' });
    this.materials.set('grass', { color: '#228B22', pattern: 'grass' });
    
    // Store basic shape definitions
    this.geometries.set('cube', { type: 'rectangle', size: 30 });
    this.geometries.set('cylinder', { type: 'circle', size: 25 });
    this.geometries.set('sphere', { type: 'circle', size: 25 });
    this.geometries.set('character-base', { type: 'circle', size: 20 });
    
    // Dice shapes for canvas rendering
    this.geometries.set('d4', { type: 'triangle', size: 20, faces: 4 });
    this.geometries.set('d6', { type: 'rectangle', size: 20, faces: 6 });
    this.geometries.set('d8', { type: 'diamond', size: 20, faces: 8 });
    this.geometries.set('d10', { type: 'diamond', size: 22, faces: 10 });
    this.geometries.set('d12', { type: 'dodecagon', size: 24, faces: 12 });
    this.geometries.set('d20', { type: 'icosahedron', size: 26, faces: 20 });
  }

  async renderDice(diceData) {
    const { type, result, color = '#ffffff', size = 100 } = diceData;
    
    const canvas = createCanvas(size * 2, size * 2);
    const ctx = canvas.getContext('2d');
    
    // Clear canvas
    ctx.fillStyle = 'transparent';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    
    // Draw dice shape
    ctx.fillStyle = color;
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 2;
    
    const geometry = this.geometries.get(type);
    if (geometry) {
      this.drawShape(ctx, centerX, centerY, geometry, size);
    }
    
    // Draw result number
    ctx.fillStyle = '#000000';
    ctx.font = `bold ${size / 3}px Arial`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(result.toString(), centerX, centerY);
    
    // Convert to buffer
    return {
      type: 'dice_render',
      dice: type,
      result,
      image: canvas.toBuffer('image/png'),
      dimensions: { width: canvas.width, height: canvas.height }
    };
  }

  drawShape(ctx, x, y, geometry, size) {
    const { type } = geometry;
    const radius = size / 2;
    
    switch (type) {
      case 'rectangle':
        ctx.fillRect(x - radius, y - radius, size, size);
        ctx.strokeRect(x - radius, y - radius, size, size);
        break;
        
      case 'circle':
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, 2 * Math.PI);
        ctx.fill();
        ctx.stroke();
        break;
        
      case 'triangle':
        ctx.beginPath();
        ctx.moveTo(x, y - radius);
        ctx.lineTo(x - radius, y + radius);
        ctx.lineTo(x + radius, y + radius);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
        break;
        
      case 'diamond':
        ctx.beginPath();
        ctx.moveTo(x, y - radius);
        ctx.lineTo(x + radius, y);
        ctx.lineTo(x, y + radius);
        ctx.lineTo(x - radius, y);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
        break;
        
      default:
        // Default to circle
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, 2 * Math.PI);
        ctx.fill();
        ctx.stroke();
    }
  }

  async createBattleMap(mapData) {
    const { 
      width = 20, 
      height = 20, 
      grid = true, 
      terrain = [], 
      objects = [], 
      lighting = 'normal',
      scale = 40
    } = mapData;
    
    const canvas = createCanvas(width * scale, height * scale);
    const ctx = canvas.getContext('2d');
    
    // Background
    ctx.fillStyle = '#f0f0f0';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Draw terrain
    terrain.forEach(tile => {
      const material = this.materials.get(tile.type) || { color: '#cccccc' };
      ctx.fillStyle = material.color;
      ctx.fillRect(tile.x * scale, tile.y * scale, scale, scale);
    });
    
    // Draw grid
    if (grid) {
      ctx.strokeStyle = '#cccccc';
      ctx.lineWidth = 1;
      
      for (let x = 0; x <= width; x++) {
        ctx.beginPath();
        ctx.moveTo(x * scale, 0);
        ctx.lineTo(x * scale, height * scale);
        ctx.stroke();
      }
      
      for (let y = 0; y <= height; y++) {
        ctx.beginPath();
        ctx.moveTo(0, y * scale);
        ctx.lineTo(width * scale, y * scale);
        ctx.stroke();
      }
    }
    
    // Draw objects
    objects.forEach(obj => {
      const geometry = this.geometries.get(obj.type) || { type: 'circle', size: 20 };
      const x = obj.x * scale + scale / 2;
      const y = obj.y * scale + scale / 2;
      
      ctx.fillStyle = obj.color || '#666666';
      this.drawShape(ctx, x, y, geometry, Math.min(scale * 0.8, geometry.size));
    });
    
    return {
      type: 'battle_map',
      dimensions: { width: canvas.width, height: canvas.height },
      image: canvas.toBuffer('image/png'),
      metadata: { width, height, scale, grid }
    };
  }

  async renderSpellEffect(spellData) {
    const { 
      spell, 
      area, 
      color = '#ff0000', 
      intensity = 1.0,
      duration = 1000
    } = spellData;
    
    const size = Math.max(area.width || 100, area.height || 100);
    const canvas = createCanvas(size, size);
    const ctx = canvas.getContext('2d');
    
    // Create spell effect visualization
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    
    // Create gradient for spell effect
    const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, size / 2);
    gradient.addColorStop(0, color + Math.floor(intensity * 255).toString(16).padStart(2, '0'));
    gradient.addColorStop(1, color + '00');
    
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Add spell-specific effects
    switch (spell) {
      case 'fireball':
        // Add flame-like patterns
        ctx.fillStyle = '#ff4500';
        for (let i = 0; i < 20; i++) {
          const angle = (i / 20) * 2 * Math.PI;
          const radius = (size / 4) + Math.random() * (size / 8);
          const x = centerX + Math.cos(angle) * radius;
          const y = centerY + Math.sin(angle) * radius;
          ctx.beginPath();
          ctx.arc(x, y, 5 + Math.random() * 10, 0, 2 * Math.PI);
          ctx.fill();
        }
        break;
        
      case 'lightning_bolt':
        // Draw zigzag lightning pattern
        ctx.strokeStyle = color;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(0, centerY);
        for (let x = 0; x < canvas.width; x += 20) {
          const y = centerY + (Math.random() - 0.5) * 40;
          ctx.lineTo(x, y);
        }
        ctx.stroke();
        break;
        
      case 'healing_word':
        // Gentle healing glow
        ctx.fillStyle = '#90EE90' + '80';
        ctx.beginPath();
        ctx.arc(centerX, centerY, size / 3, 0, 2 * Math.PI);
        ctx.fill();
        break;
    }
    
    return {
      type: 'spell_effect',
      spell,
      image: canvas.toBuffer('image/png'),
      dimensions: { width: canvas.width, height: canvas.height },
      duration
    };
  }

  // Helper methods for compatibility
  async generateBattleMap(mapData) {
    return await this.createBattleMap(mapData);
  }

  async generateDiceRender(diceData) {
    return await this.renderDice(diceData);
  }

  async generateSpellEffect(spellData) {
    return await this.renderSpellEffect(spellData);
  }
}

export default VisualizationEngine;