const fs = require('fs').promises;
const path = require('path');
const winston = require('winston');
const Canvas = require('canvas');
const { createCanvas, loadImage } = Canvas;

class FFTacticsRendererService {
  constructor(config = {}) {
    this.logger = winston.createLogger({
      level: 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
      ),
      transports: [
        new winston.transports.Console(),
        new winston.transports.File({ filename: 'logs/ff-tactics-renderer.log' })
      ]
    });

    this.outputPath = config.outputPath || './ff-tactics-renders';
    this.isInitialized = false;
    this.battleGrids = new Map();
    this.characterModels = new Map();
    this.terrainAssets = new Map();
    this.tacticalCameras = new Map();
    
    this.tacticsConfig = {
      gridSize: 32,
      maxGridSize: { width: 16, height: 16 },
      isometricAngle: 30,
      heightScale: 0.8,
      animationFrames: 8,
      colorPalette: this.getFFTacticsPalette()
    };
  }

  async initialize() {
    try {
      this.logger.info('Initializing FF Tactics Renderer Service');
      
      await this.setupOutputDirectory();
      await this.loadTerrainAssets();
      await this.loadCharacterModels();
      await this.setupIsometricProjection();
      await this.loadTacticalTemplates();
      
      this.isInitialized = true;
      this.logger.info('FF Tactics Renderer Service initialized successfully');
      return true;
    } catch (error) {
      this.logger.error('Failed to initialize FF Tactics Renderer Service:', error);
      return false;
    }
  }

  getFFTacticsPalette() {
    return {
      terrain: {
        grass: '#4A7C2A',
        stone: '#8C7853',
        water: '#1E90FF',
        dirt: '#D2B48C',
        rock: '#696969',
        sand: '#F4A460',
        lava: '#FF4500',
        ice: '#B0E0E6'
      },
      character: {
        skin: ['#FDBCB4', '#F4A574', '#E68B3C', '#D4763A', '#BC6234'],
        hair: ['#4B3728', '#8B4513', '#DAA520', '#FF6347', '#000000'],
        clothing: ['#800080', '#4169E1', '#228B22', '#DC143C', '#FF8C00']
      },
      ui: {
        grid: '#FFFFFF',
        selection: '#FFD700',
        movement: '#00FF00',
        attack: '#FF0000',
        heal: '#00FFFF'
      }
    };
  }

  async setupOutputDirectory() {
    await fs.mkdir(this.outputPath, { recursive: true });
    await fs.mkdir(path.join(this.outputPath, 'battles'), { recursive: true });
    await fs.mkdir(path.join(this.outputPath, 'characters'), { recursive: true });
    await fs.mkdir(path.join(this.outputPath, 'terrain'), { recursive: true });
    await fs.mkdir(path.join(this.outputPath, 'animations'), { recursive: true });
    
    this.logger.info('FF Tactics render output directories created');
  }

  async loadTerrainAssets() {
    this.terrainTypes = {
      plains: {
        baseHeight: 0,
        variation: 2,
        textures: ['grass', 'dirt'],
        obstacles: ['tree', 'rock'],
        density: 0.1
      },
      mountain: {
        baseHeight: 3,
        variation: 5,
        textures: ['stone', 'rock'],
        obstacles: ['boulder', 'cliff'],
        density: 0.2
      },
      desert: {
        baseHeight: 0,
        variation: 1,
        textures: ['sand', 'stone'],
        obstacles: ['oasis', 'dune'],
        density: 0.05
      },
      swamp: {
        baseHeight: -1,
        variation: 2,
        textures: ['water', 'dirt'],
        obstacles: ['tree', 'bog'],
        density: 0.15
      },
      castle: {
        baseHeight: 1,
        variation: 3,
        textures: ['stone', 'stone'],
        obstacles: ['wall', 'pillar'],
        density: 0.3
      },
      cave: {
        baseHeight: -2,
        variation: 3,
        textures: ['rock', 'stone'],
        obstacles: ['stalactite', 'crystal'],
        density: 0.2
      }
    };
    
    for (const [terrainName, config] of Object.entries(this.terrainTypes)) {
      this.terrainAssets.set(terrainName, await this.generateTerrainTiles(config, terrainName));
    }
    
    this.logger.info('Terrain assets loaded');
  }

  async generateTerrainTiles(config, terrainName) {
    const tileSize = this.tacticsConfig.gridSize;
    const canvas = createCanvas(tileSize * 4, tileSize * 4);
    const ctx = canvas.getContext('2d');
    
    for (let row = 0; row < 4; row++) {
      for (let col = 0; col < 4; col++) {
        const x = col * tileSize;
        const y = row * tileSize;
        const height = config.baseHeight + Math.random() * config.variation;
        
        await this.drawIsometricTile(ctx, x, y, tileSize, config, height);
      }
    }
    
    const outputFile = path.join(this.outputPath, 'terrain', `${terrainName}_tiles.png`);
    const buffer = canvas.toBuffer('image/png');
    await fs.writeFile(outputFile, buffer);
    
    return {
      canvas,
      config,
      tileSize
    };
  }

  async drawIsometricTile(ctx, x, y, size, config, height) {
    const centerX = x + size / 2;
    const centerY = y + size / 2;
    const iso = this.toIsometric(0, 0, height);
    
    const baseColor = this.tacticsConfig.colorPalette.terrain[config.textures[0]];
    const topColor = this.lightenColor(baseColor, 20);
    const sideColor = this.darkenColor(baseColor, 30);
    
    ctx.beginPath();
    ctx.moveTo(centerX, centerY - iso.y);
    ctx.lineTo(centerX + size/2, centerY - iso.y + size/4);
    ctx.lineTo(centerX, centerY - iso.y + size/2);
    ctx.lineTo(centerX - size/2, centerY - iso.y + size/4);
    ctx.closePath();
    
    ctx.fillStyle = topColor;
    ctx.fill();
    
    if (height > 0) {
      ctx.fillStyle = sideColor;
      ctx.fillRect(centerX - size/2, centerY - iso.y + size/4, size/2, height * this.tacticsConfig.heightScale);
      ctx.fillRect(centerX, centerY - iso.y + size/4, size/2, height * this.tacticsConfig.heightScale);
    }
    
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  toIsometric(x, y, z) {
    const angle = this.tacticsConfig.isometricAngle * Math.PI / 180;
    return {
      x: (x - y) * Math.cos(angle),
      y: (x + y) * Math.sin(angle) - z * this.tacticsConfig.heightScale
    };
  }

  lightenColor(color, percent) {
    const num = parseInt(color.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent);
    const R = Math.min(255, (num >> 16) + amt);
    const G = Math.min(255, (num >> 8 & 0x00FF) + amt);
    const B = Math.min(255, (num & 0x0000FF) + amt);
    return '#' + ((R << 16) | (G << 8) | B).toString(16).padStart(6, '0');
  }

  darkenColor(color, percent) {
    const num = parseInt(color.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent);
    const R = Math.max(0, (num >> 16) - amt);
    const G = Math.max(0, (num >> 8 & 0x00FF) - amt);
    const B = Math.max(0, (num & 0x0000FF) - amt);
    return '#' + ((R << 16) | (G << 8) | B).toString(16).padStart(6, '0');
  }

  async loadCharacterModels() {
    this.characterClasses = {
      knight: {
        sprite: { width: 24, height: 32 },
        colors: { primary: '#4169E1', secondary: '#C0C0C0' },
        animations: ['idle', 'walk', 'attack', 'defend', 'cast'],
        weaponType: 'sword',
        range: 1,
        movement: 3
      },
      archer: {
        sprite: { width: 24, height: 32 },
        colors: { primary: '#228B22', secondary: '#8B4513' },
        animations: ['idle', 'walk', 'shoot', 'aim'],
        weaponType: 'bow',
        range: 4,
        movement: 3
      },
      wizard: {
        sprite: { width: 24, height: 32 },
        colors: { primary: '#800080', secondary: '#FFD700' },
        animations: ['idle', 'walk', 'cast', 'channel'],
        weaponType: 'staff',
        range: 3,
        movement: 2
      },
      thief: {
        sprite: { width: 24, height: 32 },
        colors: { primary: '#696969', secondary: '#2F4F4F' },
        animations: ['idle', 'walk', 'attack', 'stealth'],
        weaponType: 'dagger',
        range: 1,
        movement: 4
      },
      priest: {
        sprite: { width: 24, height: 32 },
        colors: { primary: '#FFFFFF', secondary: '#FFD700' },
        animations: ['idle', 'walk', 'heal', 'pray'],
        weaponType: 'mace',
        range: 2,
        movement: 2
      }
    };
    
    for (const [className, classData] of Object.entries(this.characterClasses)) {
      this.characterModels.set(className, await this.generateCharacterModel(classData, className));
    }
    
    this.logger.info('Character models loaded');
  }

  async generateCharacterModel(classData, className) {
    const spriteSheet = await this.createCharacterSpriteSheet(classData, className);
    
    return {
      spriteSheet,
      classData,
      animations: await this.generateCharacterAnimations(classData)
    };
  }

  async createCharacterSpriteSheet(classData, className) {
    const spriteSize = classData.sprite;
    const animationCount = classData.animations.length;
    const framesPerAnimation = this.tacticsConfig.animationFrames;
    
    const canvas = createCanvas(
      spriteSize.width * framesPerAnimation,
      spriteSize.height * animationCount
    );
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    
    for (let animIndex = 0; animIndex < animationCount; animIndex++) {
      const animName = classData.animations[animIndex];
      
      for (let frame = 0; frame < framesPerAnimation; frame++) {
        const x = frame * spriteSize.width;
        const y = animIndex * spriteSize.height;
        
        await this.drawCharacterFrame(ctx, x, y, spriteSize, classData, animName, frame);
      }
    }
    
    const outputFile = path.join(this.outputPath, 'characters', `${className}_spritesheet.png`);
    const buffer = canvas.toBuffer('image/png');
    await fs.writeFile(outputFile, buffer);
    
    return canvas;
  }

  async drawCharacterFrame(ctx, x, y, size, classData, animName, frame) {
    const centerX = x + size.width / 2;
    const centerY = y + size.height;
    
    const bodyColor = classData.colors.primary;
    const accentColor = classData.colors.secondary;
    
    const animationOffset = this.getAnimationOffset(animName, frame);
    
    ctx.fillStyle = bodyColor;
    ctx.fillRect(centerX - 4, centerY - 24 + animationOffset.y, 8, 16);
    
    ctx.fillStyle = this.tacticsConfig.colorPalette.character.skin[0];
    ctx.fillRect(centerX - 3, centerY - 28 + animationOffset.y, 6, 6);
    
    ctx.fillStyle = accentColor;
    ctx.fillRect(centerX - 2 + animationOffset.x, centerY - 18 + animationOffset.y, 4, 8);
    
    ctx.fillStyle = this.darkenColor(bodyColor, 20);
    ctx.fillRect(centerX - 3, centerY - 8, 2, 8);
    ctx.fillRect(centerX + 1, centerY - 8, 2, 8);
    
    if (animName === 'attack' && frame > 2 && frame < 6) {
      this.drawWeapon(ctx, centerX + 6, centerY - 20, classData.weaponType);
    }
  }

  getAnimationOffset(animName, frame) {
    const cycle = frame / this.tacticsConfig.animationFrames;
    
    switch (animName) {
      case 'walk':
        return {
          x: Math.sin(cycle * Math.PI * 2) * 2,
          y: Math.abs(Math.sin(cycle * Math.PI * 4)) * 1
        };
      case 'attack':
        const attackProgress = (frame % 4) / 4;
        return {
          x: Math.sin(attackProgress * Math.PI) * 4,
          y: -Math.sin(attackProgress * Math.PI) * 2
        };
      case 'cast':
        return {
          x: Math.sin(cycle * Math.PI * 4) * 1,
          y: -Math.sin(cycle * Math.PI * 2) * 2
        };
      default:
        return { x: 0, y: 0 };
    }
  }

  drawWeapon(ctx, x, y, weaponType) {
    ctx.strokeStyle = '#C0C0C0';
    ctx.lineWidth = 2;
    
    switch (weaponType) {
      case 'sword':
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(x, y - 12);
        ctx.stroke();
        break;
      case 'bow':
        ctx.beginPath();
        ctx.arc(x, y - 6, 4, 0, Math.PI * 2);
        ctx.stroke();
        break;
      case 'staff':
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(x, y - 16);
        ctx.stroke();
        break;
    }
  }

  async generateCharacterAnimations(classData) {
    const animations = {};
    
    for (const animName of classData.animations) {
      animations[animName] = {
        frames: this.tacticsConfig.animationFrames,
        duration: this.getAnimationDuration(animName),
        loop: animName === 'idle' || animName === 'walk'
      };
    }
    
    return animations;
  }

  getAnimationDuration(animName) {
    const durations = {
      idle: 2000,
      walk: 800,
      attack: 600,
      defend: 500,
      cast: 1200,
      shoot: 700,
      aim: 1000,
      channel: 2000,
      stealth: 1500,
      heal: 1800,
      pray: 2500
    };
    
    return durations[animName] || 1000;
  }

  async setupIsometricProjection() {
    this.projectionMatrix = {
      angle: this.tacticsConfig.isometricAngle,
      scale: 1.0,
      offsetX: 0,
      offsetY: 0
    };
    
    this.logger.info('Isometric projection configured');
  }

  async loadTacticalTemplates() {
    this.battleTemplates = {
      encounter: {
        gridSize: { width: 8, height: 8 },
        terrain: 'plains',
        elevation: 'flat',
        objectives: ['eliminate_enemies']
      },
      siege: {
        gridSize: { width: 12, height: 12 },
        terrain: 'castle',
        elevation: 'varied',
        objectives: ['capture_flag', 'protect_objective']
      },
      ambush: {
        gridSize: { width: 10, height: 6 },
        terrain: 'forest',
        elevation: 'irregular',
        objectives: ['escape', 'survive_turns']
      },
      dungeon: {
        gridSize: { width: 8, height: 10 },
        terrain: 'cave',
        elevation: 'multi_level',
        objectives: ['reach_exit', 'collect_treasure']
      }
    };
    
    this.logger.info('Tactical battle templates loaded');
  }

  async renderTacticalBattle(battleData) {
    try {
      const battleId = `tactics_${Date.now()}`;
      this.logger.info(`Starting FF Tactics battle render: ${battleId}`);
      
      const battleGrid = await this.createBattleGrid(battleData);
      const canvas = await this.renderBattleScene(battleGrid, battleData);
      const outputPath = await this.saveBattleRender(canvas, battleId);
      
      return {
        battleId,
        status: 'rendered',
        outputPath,
        gridSize: battleGrid.size,
        characterCount: battleData.characters?.length || 0,
        metadata: {
          terrain: battleData.terrain,
          template: battleData.template,
          renderTime: 1500
        }
      };
    } catch (error) {
      this.logger.error('Tactical battle render failed:', error);
      throw error;
    }
  }

  async createBattleGrid(battleData) {
    const template = this.battleTemplates[battleData.template] || this.battleTemplates.encounter;
    const terrain = this.terrainAssets.get(battleData.terrain) || this.terrainAssets.get('plains');
    
    const grid = {
      size: template.gridSize,
      terrain: terrain,
      cells: [],
      obstacles: [],
      objectives: template.objectives
    };
    
    for (let row = 0; row < grid.size.height; row++) {
      for (let col = 0; col < grid.size.width; col++) {
        const cell = {
          x: col,
          y: row,
          height: this.generateCellHeight(col, row, template.elevation),
          passable: true,
          terrainType: this.selectTerrainType(col, row, terrain.config),
          effects: []
        };
        
        grid.cells.push(cell);
      }
    }
    
    await this.addObstacles(grid, template);
    
    this.battleGrids.set(battleData.battleId, grid);
    return grid;
  }

  generateCellHeight(x, y, elevation) {
    switch (elevation) {
      case 'flat':
        return 0;
      case 'varied':
        return Math.floor(Math.random() * 3);
      case 'irregular':
        return Math.floor(Math.sin(x * 0.5) * Math.cos(y * 0.5) * 2);
      case 'multi_level':
        return Math.floor((x + y) / 4) % 3;
      default:
        return 0;
    }
  }

  selectTerrainType(x, y, terrainConfig) {
    const random = Math.random();
    if (random < 0.7) {
      return terrainConfig.textures[0];
    } else {
      return terrainConfig.textures[1];
    }
  }

  async addObstacles(grid, template) {
    const obstacleCount = Math.floor(grid.size.width * grid.size.height * 0.1);
    
    for (let i = 0; i < obstacleCount; i++) {
      const x = Math.floor(Math.random() * grid.size.width);
      const y = Math.floor(Math.random() * grid.size.height);
      const cellIndex = y * grid.size.width + x;
      
      if (cellIndex < grid.cells.length) {
        grid.cells[cellIndex].passable = false;
        grid.obstacles.push({
          x,
          y,
          type: 'rock',
          height: 1
        });
      }
    }
  }

  async renderBattleScene(battleGrid, battleData) {
    const gridSize = this.tacticsConfig.gridSize;
    const canvasWidth = battleGrid.size.width * gridSize * 2;
    const canvasHeight = battleGrid.size.height * gridSize * 2;
    
    const canvas = createCanvas(canvasWidth, canvasHeight);
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    
    const offsetX = canvasWidth / 2;
    const offsetY = canvasHeight / 4;
    
    await this.renderTerrain(ctx, battleGrid, offsetX, offsetY);
    await this.renderGrid(ctx, battleGrid, offsetX, offsetY);
    await this.renderCharacters(ctx, battleData.characters || [], battleGrid, offsetX, offsetY);
    await this.renderEffects(ctx, battleData.effects || [], battleGrid, offsetX, offsetY);
    await this.renderUI(ctx, battleData.ui || {}, battleGrid);
    
    return canvas;
  }

  async renderTerrain(ctx, battleGrid, offsetX, offsetY) {
    const gridSize = this.tacticsConfig.gridSize;
    
    for (const cell of battleGrid.cells) {
      const isoPos = this.toIsometric(cell.x, cell.y, cell.height);
      const screenX = offsetX + isoPos.x * gridSize;
      const screenY = offsetY + isoPos.y * gridSize;
      
      await this.drawIsometricTile(
        ctx,
        screenX - gridSize / 2,
        screenY - gridSize / 2,
        gridSize,
        battleGrid.terrain.config,
        cell.height
      );
    }
    
    for (const obstacle of battleGrid.obstacles) {
      const isoPos = this.toIsometric(obstacle.x, obstacle.y, obstacle.height);
      const screenX = offsetX + isoPos.x * gridSize;
      const screenY = offsetY + isoPos.y * gridSize;
      
      await this.drawObstacle(ctx, screenX, screenY, obstacle);
    }
  }

  async drawObstacle(ctx, x, y, obstacle) {
    ctx.fillStyle = this.tacticsConfig.colorPalette.terrain.rock;
    ctx.fillRect(x - 8, y - 16, 16, 16);
    
    ctx.fillStyle = this.lightenColor(this.tacticsConfig.colorPalette.terrain.rock, 30);
    ctx.fillRect(x - 8, y - 16, 16, 4);
  }

  async renderGrid(ctx, battleGrid, offsetX, offsetY) {
    ctx.strokeStyle = this.tacticsConfig.colorPalette.ui.grid;
    ctx.lineWidth = 0.5;
    ctx.globalAlpha = 0.3;
    
    const gridSize = this.tacticsConfig.gridSize;
    
    for (const cell of battleGrid.cells) {
      const isoPos = this.toIsometric(cell.x, cell.y, cell.height);
      const screenX = offsetX + isoPos.x * gridSize;
      const screenY = offsetY + isoPos.y * gridSize;
      
      ctx.beginPath();
      ctx.moveTo(screenX, screenY - gridSize / 2);
      ctx.lineTo(screenX + gridSize / 2, screenY);
      ctx.lineTo(screenX, screenY + gridSize / 2);
      ctx.lineTo(screenX - gridSize / 2, screenY);
      ctx.closePath();
      ctx.stroke();
    }
    
    ctx.globalAlpha = 1.0;
  }

  async renderCharacters(ctx, characters, battleGrid, offsetX, offsetY) {
    const gridSize = this.tacticsConfig.gridSize;
    
    for (const character of characters) {
      const characterModel = this.characterModels.get(character.class);
      if (!characterModel) continue;
      
      const cell = battleGrid.cells.find(c => c.x === character.position.x && c.y === character.position.y);
      if (!cell) continue;
      
      const isoPos = this.toIsometric(character.position.x, character.position.y, cell.height);
      const screenX = offsetX + isoPos.x * gridSize;
      const screenY = offsetY + isoPos.y * gridSize - 32;
      
      await this.drawTacticalCharacter(ctx, screenX, screenY, character, characterModel);
      
      if (character.showMovementRange) {
        await this.drawMovementRange(ctx, character, battleGrid, offsetX, offsetY);
      }
      
      if (character.showAttackRange) {
        await this.drawAttackRange(ctx, character, battleGrid, offsetX, offsetY);
      }
    }
  }

  async drawTacticalCharacter(ctx, x, y, character, characterModel) {
    const spriteSize = characterModel.classData.sprite;
    const animIndex = characterModel.classData.animations.indexOf(character.animation || 'idle');
    const frameIndex = Math.floor(Date.now() / 200) % this.tacticsConfig.animationFrames;
    
    const sourceX = frameIndex * spriteSize.width;
    const sourceY = Math.max(0, animIndex) * spriteSize.height;
    
    ctx.drawImage(
      characterModel.spriteSheet,
      sourceX, sourceY, spriteSize.width, spriteSize.height,
      x - spriteSize.width / 2, y - spriteSize.height, spriteSize.width, spriteSize.height
    );
    
    if (character.hp) {
      await this.drawHealthBar(ctx, x, y - spriteSize.height - 8, character.hp);
    }
    
    if (character.team) {
      await this.drawTeamIndicator(ctx, x, y - spriteSize.height - 16, character.team);
    }
  }

  async drawHealthBar(ctx, x, y, hp) {
    const barWidth = 24;
    const barHeight = 4;
    
    ctx.fillStyle = '#800000';
    ctx.fillRect(x - barWidth / 2, y, barWidth, barHeight);
    
    const healthWidth = barWidth * (hp.current / hp.max);
    const healthColor = hp.current / hp.max > 0.5 ? '#00FF00' : hp.current / hp.max > 0.25 ? '#FFFF00' : '#FF0000';
    
    ctx.fillStyle = healthColor;
    ctx.fillRect(x - barWidth / 2, y, healthWidth, barHeight);
    
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 1;
    ctx.strokeRect(x - barWidth / 2, y, barWidth, barHeight);
  }

  async drawTeamIndicator(ctx, x, y, team) {
    const teamColors = {
      player: '#0000FF',
      enemy: '#FF0000',
      neutral: '#FFFF00'
    };
    
    ctx.fillStyle = teamColors[team] || teamColors.neutral;
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fill();
    
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  async drawMovementRange(ctx, character, battleGrid, offsetX, offsetY) {
    const movement = character.movement || 3;
    const gridSize = this.tacticsConfig.gridSize;
    
    ctx.fillStyle = this.tacticsConfig.colorPalette.ui.movement;
    ctx.globalAlpha = 0.3;
    
    for (const cell of battleGrid.cells) {
      const distance = Math.abs(cell.x - character.position.x) + Math.abs(cell.y - character.position.y);
      if (distance <= movement && cell.passable) {
        const isoPos = this.toIsometric(cell.x, cell.y, cell.height);
        const screenX = offsetX + isoPos.x * gridSize;
        const screenY = offsetY + isoPos.y * gridSize;
        
        ctx.beginPath();
        ctx.moveTo(screenX, screenY - gridSize / 2);
        ctx.lineTo(screenX + gridSize / 2, screenY);
        ctx.lineTo(screenX, screenY + gridSize / 2);
        ctx.lineTo(screenX - gridSize / 2, screenY);
        ctx.closePath();
        ctx.fill();
      }
    }
    
    ctx.globalAlpha = 1.0;
  }

  async drawAttackRange(ctx, character, battleGrid, offsetX, offsetY) {
    const range = character.range || 1;
    const gridSize = this.tacticsConfig.gridSize;
    
    ctx.fillStyle = this.tacticsConfig.colorPalette.ui.attack;
    ctx.globalAlpha = 0.3;
    
    for (const cell of battleGrid.cells) {
      const distance = Math.abs(cell.x - character.position.x) + Math.abs(cell.y - character.position.y);
      if (distance <= range) {
        const isoPos = this.toIsometric(cell.x, cell.y, cell.height);
        const screenX = offsetX + isoPos.x * gridSize;
        const screenY = offsetY + isoPos.y * gridSize;
        
        ctx.beginPath();
        ctx.moveTo(screenX, screenY - gridSize / 2);
        ctx.lineTo(screenX + gridSize / 2, screenY);
        ctx.lineTo(screenX, screenY + gridSize / 2);
        ctx.lineTo(screenX - gridSize / 2, screenY);
        ctx.closePath();
        ctx.fill();
      }
    }
    
    ctx.globalAlpha = 1.0;
  }

  async renderEffects(ctx, effects, battleGrid, offsetX, offsetY) {
    const gridSize = this.tacticsConfig.gridSize;
    
    for (const effect of effects) {
      const cell = battleGrid.cells.find(c => c.x === effect.position.x && c.y === effect.position.y);
      if (!cell) continue;
      
      const isoPos = this.toIsometric(effect.position.x, effect.position.y, cell.height);
      const screenX = offsetX + isoPos.x * gridSize;
      const screenY = offsetY + isoPos.y * gridSize;
      
      await this.drawBattleEffect(ctx, screenX, screenY, effect);
    }
  }

  async drawBattleEffect(ctx, x, y, effect) {
    const time = Date.now();
    const progress = ((time - effect.startTime) / effect.duration) % 1;
    
    ctx.globalAlpha = 0.8;
    
    switch (effect.type) {
      case 'explosion':
        await this.drawExplosionEffect(ctx, x, y, progress);
        break;
      case 'heal':
        await this.drawHealEffect(ctx, x, y, progress);
        break;
      case 'magic':
        await this.drawMagicEffect(ctx, x, y, progress);
        break;
    }
    
    ctx.globalAlpha = 1.0;
  }

  async drawExplosionEffect(ctx, x, y, progress) {
    const radius = progress * 32;
    const alpha = 1 - progress;
    
    ctx.globalAlpha *= alpha;
    ctx.fillStyle = '#FF4500';
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
    
    ctx.fillStyle = '#FFD700';
    ctx.beginPath();
    ctx.arc(x, y, radius * 0.6, 0, Math.PI * 2);
    ctx.fill();
  }

  async drawHealEffect(ctx, x, y, progress) {
    const height = progress * 48;
    
    ctx.strokeStyle = '#00FF00';
    ctx.lineWidth = 2;
    
    for (let i = 0; i < 6; i++) {
      const angle = (i / 6) * Math.PI * 2;
      const particleX = x + Math.cos(angle) * 16;
      const particleY = y + Math.sin(angle) * 8 - height;
      
      ctx.beginPath();
      ctx.arc(particleX, particleY, 2, 0, Math.PI * 2);
      ctx.stroke();
    }
  }

  async drawMagicEffect(ctx, x, y, progress) {
    const rotation = progress * Math.PI * 4;
    
    ctx.strokeStyle = '#800080';
    ctx.lineWidth = 2;
    
    for (let i = 0; i < 8; i++) {
      const angle = (i / 8) * Math.PI * 2 + rotation;
      const radius = 20 + Math.sin(progress * Math.PI * 2) * 8;
      const particleX = x + Math.cos(angle) * radius;
      const particleY = y + Math.sin(angle) * radius * 0.5;
      
      ctx.beginPath();
      ctx.arc(particleX, particleY, 3, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  async renderUI(ctx, uiData, battleGrid) {
    if (uiData.turnOrder) {
      await this.drawTurnOrder(ctx, uiData.turnOrder);
    }
    
    if (uiData.actionMenu) {
      await this.drawActionMenu(ctx, uiData.actionMenu);
    }
    
    if (uiData.battleInfo) {
      await this.drawBattleInfo(ctx, uiData.battleInfo);
    }
  }

  async drawTurnOrder(ctx, turnOrder) {
    const x = 10;
    const y = 10;
    const characterSize = 32;
    
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    ctx.fillRect(x, y, turnOrder.length * characterSize + 20, characterSize + 20);
    
    for (let i = 0; i < turnOrder.length; i++) {
      const character = turnOrder[i];
      const charX = x + 10 + i * characterSize;
      const charY = y + 10;
      
      ctx.fillStyle = character.team === 'player' ? '#0000FF' : '#FF0000';
      ctx.fillRect(charX, charY, characterSize - 2, characterSize - 2);
      
      ctx.fillStyle = '#FFFFFF';
      ctx.font = '10px monospace';
      ctx.fillText(character.name.substring(0, 3), charX + 2, charY + 12);
    }
  }

  async drawActionMenu(ctx, actionMenu) {
    const x = actionMenu.position.x;
    const y = actionMenu.position.y;
    const menuWidth = 120;
    const menuHeight = actionMenu.actions.length * 24 + 16;
    
    ctx.fillStyle = 'rgba(0, 0, 50, 0.9)';
    ctx.fillRect(x, y, menuWidth, menuHeight);
    
    ctx.strokeStyle = '#FFD700';
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, menuWidth, menuHeight);
    
    for (let i = 0; i < actionMenu.actions.length; i++) {
      const action = actionMenu.actions[i];
      const itemY = y + 16 + i * 24;
      
      if (i === actionMenu.selectedIndex) {
        ctx.fillStyle = 'rgba(255, 215, 0, 0.3)';
        ctx.fillRect(x + 2, itemY - 12, menuWidth - 4, 20);
      }
      
      ctx.fillStyle = '#FFFFFF';
      ctx.font = '14px monospace';
      ctx.fillText(action.name, x + 8, itemY);
    }
  }

  async drawBattleInfo(ctx, battleInfo) {
    const x = ctx.canvas.width - 200;
    const y = 10;
    
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    ctx.fillRect(x, y, 190, 100);
    
    ctx.fillStyle = '#FFFFFF';
    ctx.font = '12px monospace';
    ctx.fillText(`Turn: ${battleInfo.turn}`, x + 8, y + 20);
    ctx.fillText(`Phase: ${battleInfo.phase}`, x + 8, y + 40);
    ctx.fillText(`Objective: ${battleInfo.objective}`, x + 8, y + 60);
    
    if (battleInfo.timer) {
      ctx.fillText(`Time: ${Math.ceil(battleInfo.timer / 1000)}s`, x + 8, y + 80);
    }
  }

  async saveBattleRender(canvas, battleId) {
    const outputFile = path.join(this.outputPath, 'battles', `${battleId}.png`);
    const buffer = canvas.toBuffer('image/png');
    await fs.writeFile(outputFile, buffer);
    
    this.logger.info(`FF Tactics battle render saved: ${outputFile}`);
    return outputFile;
  }

  async cleanup() {
    try {
      this.logger.info('Cleaning up FF Tactics Renderer Service');
      
      this.battleGrids.clear();
      this.characterModels.clear();
      this.terrainAssets.clear();
      this.tacticalCameras.clear();
      
      this.logger.info('FF Tactics Renderer Service cleanup completed');
    } catch (error) {
      this.logger.error('FF Tactics Renderer Service cleanup failed:', error);
    }
  }
}

module.exports = FFTacticsRendererService;