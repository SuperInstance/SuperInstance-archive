const fs = require('fs').promises;
const path = require('path');
const winston = require('winston');
const Canvas = require('canvas');
const { createCanvas, loadImage } = Canvas;

class RetroEngineService {
  constructor(config = {}) {
    this.logger = winston.createLogger({
      level: 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
      ),
      transports: [
        new winston.transports.Console(),
        new winston.transports.File({ filename: 'logs/retro-engine.log' })
      ]
    });

    this.outputPath = config.outputPath || './retro-renders';
    this.spriteLibrary = new Map();
    this.tilesets = new Map();
    this.animations = new Map();
    this.isInitialized = false;
    
    this.pixelArtConfig = {
      snesResolution: { width: 256, height: 224 },
      chronoTriggerPalette: {
        colors: 32,
        paletteSize: 256,
        colorDepth: 16
      },
      pixelScale: 3,
      frameRate: 60,
      animationSpeed: 8
    };
  }

  async initialize() {
    try {
      this.logger.info('Initializing Retro Engine Service');
      
      await this.setupOutputDirectory();
      await this.loadSpriteLibrary();
      await this.loadTilesets();
      await this.loadAnimationTemplates();
      await this.setupPixelArtStyles();
      
      this.isInitialized = true;
      this.logger.info('Retro Engine Service initialized successfully');
      return true;
    } catch (error) {
      this.logger.error('Failed to initialize Retro Engine Service:', error);
      return false;
    }
  }

  async setupOutputDirectory() {
    await fs.mkdir(this.outputPath, { recursive: true });
    await fs.mkdir(path.join(this.outputPath, 'sprites'), { recursive: true });
    await fs.mkdir(path.join(this.outputPath, 'backgrounds'), { recursive: true });
    await fs.mkdir(path.join(this.outputPath, 'animations'), { recursive: true });
    
    this.logger.info('Retro render output directories created');
  }

  async loadSpriteLibrary() {
    try {
      this.spriteTemplates = {
        characters: {
          warrior: {
            idle: { frames: 2, width: 16, height: 24 },
            walk: { frames: 4, width: 16, height: 24 },
            attack: { frames: 3, width: 24, height: 24 },
            cast: { frames: 4, width: 20, height: 24 }
          },
          mage: {
            idle: { frames: 2, width: 16, height: 24 },
            walk: { frames: 4, width: 16, height: 24 },
            attack: { frames: 2, width: 20, height: 24 },
            cast: { frames: 6, width: 24, height: 24 }
          },
          rogue: {
            idle: { frames: 2, width: 16, height: 24 },
            walk: { frames: 4, width: 16, height: 24 },
            attack: { frames: 4, width: 20, height: 24 },
            stealth: { frames: 3, width: 16, height: 24 }
          }
        },
        effects: {
          fireball: { frames: 8, width: 32, height: 32 },
          heal: { frames: 12, width: 24, height: 32 },
          lightning: { frames: 6, width: 16, height: 48 },
          explosion: { frames: 10, width: 48, height: 48 }
        },
        ui: {
          healthBar: { frames: 1, width: 32, height: 4 },
          manaBar: { frames: 1, width: 32, height: 4 },
          dialogBox: { frames: 1, width: 240, height: 64 }
        }
      };
      
      await this.generateSpriteAssets();
      this.logger.info('Sprite library loaded');
    } catch (error) {
      this.logger.error('Failed to load sprite library:', error);
      throw error;
    }
  }

  async generateSpriteAssets() {
    for (const [category, sprites] of Object.entries(this.spriteTemplates)) {
      for (const [spriteName, animations] of Object.entries(sprites)) {
        for (const [animName, config] of Object.entries(animations)) {
          const spriteKey = `${category}_${spriteName}_${animName}`;
          this.spriteLibrary.set(spriteKey, await this.createPixelArtSprite(config, spriteKey));
        }
      }
    }
  }

  async createPixelArtSprite(config, spriteKey) {
    const canvas = createCanvas(config.width * config.frames, config.height);
    const ctx = canvas.getContext('2d');
    
    ctx.imageSmoothingEnabled = false;
    
    const palette = this.generateChronoTriggerPalette();
    
    for (let frame = 0; frame < config.frames; frame++) {
      const x = frame * config.width;
      await this.drawPixelArtFrame(ctx, x, 0, config.width, config.height, palette, spriteKey, frame);
    }
    
    const spriteData = {
      canvas,
      width: config.width,
      height: config.height,
      frames: config.frames,
      palette
    };
    
    const outputFile = path.join(this.outputPath, 'sprites', `${spriteKey}.png`);
    const buffer = canvas.toBuffer('image/png');
    await fs.writeFile(outputFile, buffer);
    
    return spriteData;
  }

  async drawPixelArtFrame(ctx, x, y, width, height, palette, spriteKey, frame) {
    const pixelData = this.generatePixelPattern(width, height, spriteKey, frame);
    
    for (let py = 0; py < height; py++) {
      for (let px = 0; px < width; px++) {
        const colorIndex = pixelData[py * width + px];
        if (colorIndex > 0) {
          ctx.fillStyle = palette[colorIndex % palette.length];
          ctx.fillRect(x + px, y + py, 1, 1);
        }
      }
    }
  }

  generatePixelPattern(width, height, spriteKey, frame) {
    const pattern = new Array(width * height).fill(0);
    
    if (spriteKey.includes('warrior')) {
      return this.generateWarriorPattern(width, height, frame);
    } else if (spriteKey.includes('mage')) {
      return this.generateMagePattern(width, height, frame);
    } else if (spriteKey.includes('fireball')) {
      return this.generateFireballPattern(width, height, frame);
    }
    
    return this.generateGenericPattern(width, height, frame);
  }

  generateWarriorPattern(width, height, frame) {
    const pattern = new Array(width * height).fill(0);
    const centerX = Math.floor(width / 2);
    
    for (let y = 2; y < height - 2; y++) {
      for (let x = Math.max(0, centerX - 3); x < Math.min(width, centerX + 4); x++) {
        if (y < 6) {
          pattern[y * width + x] = 8;
        } else if (y < 12) {
          pattern[y * width + x] = 12;
        } else if (y < 18) {
          pattern[y * width + x] = 15;
        } else {
          pattern[y * width + x] = 6;
        }
      }
    }
    
    if (frame % 2 === 1) {
      for (let i = 0; i < pattern.length; i++) {
        if (pattern[i] > 0 && Math.random() > 0.9) {
          pattern[i] = Math.max(1, pattern[i] - 1);
        }
      }
    }
    
    return pattern;
  }

  generateMagePattern(width, height, frame) {
    const pattern = new Array(width * height).fill(0);
    const centerX = Math.floor(width / 2);
    
    for (let y = 2; y < height - 2; y++) {
      for (let x = Math.max(0, centerX - 2); x < Math.min(width, centerX + 3); x++) {
        if (y < 6) {
          pattern[y * width + x] = 11;
        } else if (y < 16) {
          pattern[y * width + x] = 9;
        } else {
          pattern[y * width + x] = 13;
        }
      }
    }
    
    if (frame > 0) {
      for (let y = 0; y < 8; y++) {
        for (let x = centerX - 6; x < centerX + 7; x++) {
          if (x >= 0 && x < width && Math.random() > 0.7) {
            pattern[y * width + x] = 3 + (frame % 4);
          }
        }
      }
    }
    
    return pattern;
  }

  generateFireballPattern(width, height, frame) {
    const pattern = new Array(width * height).fill(0);
    const centerX = Math.floor(width / 2);
    const centerY = Math.floor(height / 2);
    const radius = 6 + Math.sin(frame * 0.5) * 2;
    
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const dist = Math.sqrt((x - centerX) ** 2 + (y - centerY) ** 2);
        if (dist < radius) {
          if (dist < radius * 0.4) {
            pattern[y * width + x] = 2;
          } else if (dist < radius * 0.7) {
            pattern[y * width + x] = 4;
          } else {
            pattern[y * width + x] = 1;
          }
        }
      }
    }
    
    return pattern;
  }

  generateGenericPattern(width, height, frame) {
    const pattern = new Array(width * height).fill(0);
    
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        if (Math.random() > 0.7) {
          pattern[y * width + x] = Math.floor(Math.random() * 8) + 1;
        }
      }
    }
    
    return pattern;
  }

  generateChronoTriggerPalette() {
    return [
      '#000000',
      '#FF6B47',
      '#FFD23F',
      '#47B5FF',
      '#FF47FF',
      '#47FF47',
      '#8B4513',
      '#A0522D',
      '#DEB887',
      '#4169E1',
      '#32CD32',
      '#FF69B4',
      '#FFA500',
      '#9400D3',
      '#00CED1',
      '#FFFFFF'
    ];
  }

  async loadTilesets() {
    this.tilesetTemplates = {
      medieval: {
        stone: { id: 1, color: '#8C7853' },
        grass: { id: 2, color: '#228B22' },
        water: { id: 3, color: '#4682B4', animated: true },
        wood: { id: 4, color: '#8B4513' },
        metal: { id: 5, color: '#708090' }
      },
      cave: {
        rock: { id: 1, color: '#696969' },
        crystal: { id: 2, color: '#9370DB', animated: true },
        lava: { id: 3, color: '#FF4500', animated: true },
        stalactite: { id: 4, color: '#A9A9A9' }
      },
      forest: {
        tree: { id: 1, color: '#228B22' },
        flower: { id: 2, color: '#FF69B4', animated: true },
        mushroom: { id: 3, color: '#DDA0DD' },
        path: { id: 4, color: '#DEB887' }
      }
    };
    
    for (const [tilesetName, tiles] of Object.entries(this.tilesetTemplates)) {
      this.tilesets.set(tilesetName, await this.createTileset(tiles, tilesetName));
    }
    
    this.logger.info('Tilesets loaded');
  }

  async createTileset(tiles, tilesetName) {
    const tileSize = 16;
    const tilesPerRow = 8;
    const totalTiles = Object.keys(tiles).length;
    const rows = Math.ceil(totalTiles / tilesPerRow);
    
    const canvas = createCanvas(tilesPerRow * tileSize, rows * tileSize);
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    
    let tileIndex = 0;
    for (const [tileName, tileData] of Object.entries(tiles)) {
      const x = (tileIndex % tilesPerRow) * tileSize;
      const y = Math.floor(tileIndex / tilesPerRow) * tileSize;
      
      await this.drawTile(ctx, x, y, tileSize, tileData, tileName);
      tileIndex++;
    }
    
    const outputFile = path.join(this.outputPath, 'sprites', `tileset_${tilesetName}.png`);
    const buffer = canvas.toBuffer('image/png');
    await fs.writeFile(outputFile, buffer);
    
    return {
      canvas,
      tiles,
      tileSize,
      tilesPerRow
    };
  }

  async drawTile(ctx, x, y, size, tileData, tileName) {
    ctx.fillStyle = tileData.color;
    ctx.fillRect(x, y, size, size);
    
    if (tileData.animated) {
      ctx.fillStyle = this.lightenColor(tileData.color, 20);
      ctx.fillRect(x + 2, y + 2, size - 4, size - 4);
    }
    
    if (tileName === 'water') {
      for (let i = 0; i < 3; i++) {
        ctx.fillStyle = this.lightenColor(tileData.color, 40);
        const waveX = x + (i * 4) + 2;
        const waveY = y + 6 + Math.sin(i) * 2;
        ctx.fillRect(waveX, waveY, 2, 1);
      }
    }
  }

  lightenColor(color, percent) {
    const num = parseInt(color.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent);
    const R = (num >> 16) + amt;
    const G = (num >> 8 & 0x00FF) + amt;
    const B = (num & 0x0000FF) + amt;
    return '#' + (0x1000000 + (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 +
      (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 +
      (B < 255 ? B < 1 ? 0 : B : 255)).toString(16).slice(1);
  }

  async loadAnimationTemplates() {
    this.animationTemplates = {
      character_walk: {
        duration: 800,
        frames: [0, 1, 2, 1],
        loop: true
      },
      character_attack: {
        duration: 600,
        frames: [0, 1, 2],
        loop: false
      },
      spell_cast: {
        duration: 1200,
        frames: [0, 1, 2, 3, 4, 5],
        loop: false
      },
      effect_explosion: {
        duration: 1000,
        frames: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        loop: false
      }
    };
    
    this.logger.info('Animation templates loaded');
  }

  async setupPixelArtStyles() {
    this.pixelArtStyles = {
      snes: {
        resolution: { width: 256, height: 224 },
        colorDepth: 16,
        paletteSize: 256,
        maxSprites: 128,
        maxColors: 32
      },
      chronoTrigger: {
        resolution: { width: 256, height: 224 },
        colorDepth: 16,
        artStyle: 'detailed',
        animationStyle: 'smooth',
        effectStyle: 'magical'
      },
      finalFantasy: {
        resolution: { width: 256, height: 224 },
        colorDepth: 16,
        artStyle: 'iconic',
        animationStyle: 'dramatic',
        effectStyle: 'elemental'
      }
    };
    
    this.logger.info('Pixel art styles configured');
  }

  async renderRetroScene(sceneData) {
    try {
      const sceneId = `retro_${Date.now()}`;
      this.logger.info(`Starting retro scene render: ${sceneId}`);
      
      const style = this.pixelArtStyles[sceneData.style] || this.pixelArtStyles.snes;
      const canvas = createCanvas(style.resolution.width * this.pixelArtConfig.pixelScale, 
                                  style.resolution.height * this.pixelArtConfig.pixelScale);
      const ctx = canvas.getContext('2d');
      ctx.imageSmoothingEnabled = false;
      
      await this.renderBackground(ctx, sceneData.background, style);
      await this.renderCharacters(ctx, sceneData.characters, style);
      await this.renderEffects(ctx, sceneData.effects, style);
      await this.renderUI(ctx, sceneData.ui, style);
      
      const outputPath = await this.saveRetroRender(canvas, sceneId);
      
      return {
        sceneId,
        status: 'rendered',
        outputPath,
        style: sceneData.style,
        resolution: style.resolution,
        metadata: {
          characters: sceneData.characters?.length || 0,
          effects: sceneData.effects?.length || 0,
          renderTime: 500
        }
      };
    } catch (error) {
      this.logger.error('Retro scene render failed:', error);
      throw error;
    }
  }

  async renderBackground(ctx, backgroundData, style) {
    const tileset = this.tilesets.get(backgroundData.tileset) || this.tilesets.get('medieval');
    if (!tileset) return;
    
    const tileSize = tileset.tileSize * this.pixelArtConfig.pixelScale;
    const mapWidth = Math.ceil(style.resolution.width / tileset.tileSize);
    const mapHeight = Math.ceil(style.resolution.height / tileset.tileSize);
    
    for (let y = 0; y < mapHeight; y++) {
      for (let x = 0; x < mapWidth; x++) {
        const tileType = this.getTileForPosition(x, y, backgroundData.pattern);
        await this.drawScaledTile(ctx, x * tileSize, y * tileSize, tileSize, tileset, tileType);
      }
    }
  }

  getTileForPosition(x, y, pattern) {
    if (!pattern) return 'grass';
    
    const index = (y * 16 + x) % pattern.length;
    return pattern[index] || 'grass';
  }

  async drawScaledTile(ctx, x, y, size, tileset, tileType) {
    const tileData = tileset.tiles[tileType];
    if (!tileData) return;
    
    ctx.fillStyle = tileData.color;
    ctx.fillRect(x, y, size, size);
    
    if (tileData.animated) {
      const animOffset = Math.sin(Date.now() * 0.005) * 10;
      ctx.fillStyle = this.lightenColor(tileData.color, 30);
      ctx.fillRect(x + 2, y + 2 + animOffset, size - 4, size - 4);
    }
  }

  async renderCharacters(ctx, characters, style) {
    for (const character of characters || []) {
      const spriteKey = `characters_${character.class}_${character.animation}`;
      const sprite = this.spriteLibrary.get(spriteKey);
      
      if (sprite) {
        const frame = Math.floor(Date.now() / this.pixelArtConfig.animationSpeed) % sprite.frames;
        await this.drawScaledSprite(ctx, character.position, sprite, frame, this.pixelArtConfig.pixelScale);
      }
    }
  }

  async drawScaledSprite(ctx, position, sprite, frame, scale) {
    const sourceX = frame * sprite.width;
    const destX = position.x * scale;
    const destY = position.y * scale;
    const destWidth = sprite.width * scale;
    const destHeight = sprite.height * scale;
    
    ctx.drawImage(sprite.canvas, 
                  sourceX, 0, sprite.width, sprite.height,
                  destX, destY, destWidth, destHeight);
  }

  async renderEffects(ctx, effects, style) {
    for (const effect of effects || []) {
      const spriteKey = `effects_${effect.type}`;
      const sprite = this.spriteLibrary.get(spriteKey);
      
      if (sprite) {
        const frame = Math.floor((Date.now() - effect.startTime) / 100) % sprite.frames;
        await this.drawScaledSprite(ctx, effect.position, sprite, frame, this.pixelArtConfig.pixelScale);
      }
    }
  }

  async renderUI(ctx, uiData, style) {
    if (!uiData) return;
    
    const scale = this.pixelArtConfig.pixelScale;
    
    if (uiData.healthBars) {
      for (const healthBar of uiData.healthBars) {
        await this.drawHealthBar(ctx, healthBar, scale);
      }
    }
    
    if (uiData.dialogBox) {
      await this.drawDialogBox(ctx, uiData.dialogBox, style, scale);
    }
  }

  async drawHealthBar(ctx, healthBar, scale) {
    const x = healthBar.position.x * scale;
    const y = healthBar.position.y * scale;
    const width = 32 * scale;
    const height = 4 * scale;
    
    ctx.fillStyle = '#800000';
    ctx.fillRect(x, y, width, height);
    
    const healthWidth = (width - 2 * scale) * (healthBar.current / healthBar.max);
    ctx.fillStyle = '#00FF00';
    ctx.fillRect(x + scale, y + scale, healthWidth, height - 2 * scale);
  }

  async drawDialogBox(ctx, dialogBox, style, scale) {
    const x = 8 * scale;
    const y = (style.resolution.height - 72) * scale;
    const width = 240 * scale;
    const height = 64 * scale;
    
    ctx.fillStyle = '#000080';
    ctx.fillRect(x, y, width, height);
    
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(x + scale, y + scale, width - 2 * scale, height - 2 * scale);
    
    if (dialogBox.text) {
      ctx.fillStyle = '#000000';
      ctx.font = `${8 * scale}px monospace`;
      ctx.fillText(dialogBox.text, x + 4 * scale, y + 12 * scale);
    }
  }

  async saveRetroRender(canvas, sceneId) {
    const outputFile = path.join(this.outputPath, `${sceneId}.png`);
    const buffer = canvas.toBuffer('image/png');
    await fs.writeFile(outputFile, buffer);
    
    this.logger.info(`Retro render saved: ${outputFile}`);
    return outputFile;
  }

  async createRetroAnimation(animationData) {
    try {
      const animId = `retro_anim_${Date.now()}`;
      this.logger.info(`Creating retro animation: ${animId}`);
      
      const frames = [];
      const style = this.pixelArtStyles[animationData.style] || this.pixelArtStyles.snes;
      
      for (let frame = 0; frame < animationData.frameCount; frame++) {
        const canvas = createCanvas(style.resolution.width * this.pixelArtConfig.pixelScale,
                                    style.resolution.height * this.pixelArtConfig.pixelScale);
        const ctx = canvas.getContext('2d');
        ctx.imageSmoothingEnabled = false;
        
        const frameData = {
          ...animationData,
          currentFrame: frame,
          time: frame * (1000 / this.pixelArtConfig.frameRate)
        };
        
        await this.renderAnimationFrame(ctx, frameData, style);
        frames.push(canvas.toBuffer('image/png'));
      }
      
      const outputPath = await this.saveRetroAnimation(frames, animId);
      
      return {
        animId,
        outputPath,
        frameCount: frames.length,
        duration: frames.length * (1000 / this.pixelArtConfig.frameRate)
      };
    } catch (error) {
      this.logger.error('Retro animation creation failed:', error);
      throw error;
    }
  }

  async renderAnimationFrame(ctx, frameData, style) {
    await this.renderBackground(ctx, frameData.background, style);
    
    for (const character of frameData.characters || []) {
      const animatedCharacter = {
        ...character,
        position: this.interpolatePosition(character, frameData.currentFrame, frameData.frameCount),
        animation: this.getFrameAnimation(character, frameData.currentFrame)
      };
      
      await this.renderCharacters(ctx, [animatedCharacter], style);
    }
    
    await this.renderEffects(ctx, frameData.effects, style);
    await this.renderUI(ctx, frameData.ui, style);
  }

  interpolatePosition(character, currentFrame, totalFrames) {
    if (!character.path || character.path.length < 2) {
      return character.position;
    }
    
    const progress = currentFrame / totalFrames;
    const segmentLength = 1 / (character.path.length - 1);
    const segmentIndex = Math.floor(progress / segmentLength);
    const segmentProgress = (progress % segmentLength) / segmentLength;
    
    if (segmentIndex >= character.path.length - 1) {
      return character.path[character.path.length - 1];
    }
    
    const startPos = character.path[segmentIndex];
    const endPos = character.path[segmentIndex + 1];
    
    return {
      x: startPos.x + (endPos.x - startPos.x) * segmentProgress,
      y: startPos.y + (endPos.y - startPos.y) * segmentProgress
    };
  }

  getFrameAnimation(character, currentFrame) {
    if (character.actions) {
      for (const action of character.actions) {
        if (currentFrame >= action.startFrame && currentFrame <= action.endFrame) {
          return action.animation;
        }
      }
    }
    
    return character.animation || 'idle';
  }

  async saveRetroAnimation(frames, animId) {
    const animDir = path.join(this.outputPath, 'animations', animId);
    await fs.mkdir(animDir, { recursive: true });
    
    for (let i = 0; i < frames.length; i++) {
      const frameFile = path.join(animDir, `frame_${i.toString().padStart(4, '0')}.png`);
      await fs.writeFile(frameFile, frames[i]);
    }
    
    const outputFile = path.join(this.outputPath, `${animId}.gif`);
    
    this.logger.info(`Retro animation saved: ${animDir}`);
    return animDir;
  }

  async cleanup() {
    try {
      this.logger.info('Cleaning up Retro Engine Service');
      
      this.spriteLibrary.clear();
      this.tilesets.clear();
      this.animations.clear();
      
      this.logger.info('Retro Engine Service cleanup completed');
    } catch (error) {
      this.logger.error('Retro Engine Service cleanup failed:', error);
    }
  }
}

module.exports = RetroEngineService;