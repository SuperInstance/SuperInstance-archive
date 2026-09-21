import { createCanvas } from 'canvas';
import sharp from 'sharp';
import fs from 'fs/promises';
import path from 'path';

class VisualizationEngine {
  constructor() {
    this.renderer = null;
    this.scenes = new Map();
    this.cameras = new Map();
    this.materials = new Map();
    this.geometries = new Map();
    this.animations = new Map();
    
    this.initializeEngine();
  }

  async initializeEngine() {
    // For server-side rendering, we'll skip Three.js WebGL and use canvas-based rendering
    // This avoids WebGL context issues in headless environment
    console.log('Initializing visualization engine in headless mode');
    
    // Store basic configuration for later use
    this.renderWidth = 1920;
    this.renderHeight = 1080;
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
    this.geometries.set('d4', { type: 'triangle', size: 20 });
    this.geometries.set('d6', { type: 'rectangle', size: 20 });
    this.geometries.set('d8', { type: 'diamond', size: 20 });
    this.geometries.set('d10', { type: 'diamond', size: 22 });
    this.geometries.set('d12', { type: 'dodecagon', size: 24 });
    this.geometries.set('d20', { type: 'icosahedron', size: 26 });
  }

  async loadTexture(path) {
    // For headless mode, return a simple pattern identifier
    return { path, loaded: true };
  }

  createD4Geometry() {
    // Return simplified geometry for headless mode
    return { type: 'triangle', size: 20, faces: 4 };
  }

  createD8Geometry() {
    const vertices = [
      1, 0, 0, -1, 0, 0,  // x-axis
      0, 1, 0, 0, -1, 0,  // y-axis
      0, 0, 1, 0, 0, -1   // z-axis
    ];
    
    const indices = [
      0, 2, 4, 0, 4, 3, 0, 3, 5, 0, 5, 2,
      1, 4, 2, 1, 3, 4, 1, 5, 3, 1, 2, 5
    ];
    
    const geometry = new THREE.BufferGeometry();
    geometry.setIndex(indices);
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    geometry.computeVertexNormals();
    
    return geometry;
  }

  createD10Geometry() {
    return new THREE.ConeGeometry(1, 2, 10);
  }

  createD12Geometry() {
    return new THREE.DodecahedronGeometry(1, 0);
  }

  createD20Geometry() {
    return new THREE.IcosahedronGeometry(1, 0);
  }

  async createBattleMap(mapData) {
    const { width, height, grid, terrain, objects, lighting } = mapData;
    const sceneId = `battlemap-${Date.now()}`;
    
    // Create scene and camera
    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(0x000000, 10, 50);
    
    const camera = new THREE.PerspectiveCamera(75, 16/9, 0.1, 1000);
    camera.position.set(width/2, height/2 + 10, height/2);
    camera.lookAt(width/2, 0, height/2);
    
    // Create grid
    if (grid.enabled) {
      const gridHelper = new THREE.GridHelper(Math.max(width, height), grid.size, 0x808080, 0x404040);
      scene.add(gridHelper);
    }
    
    // Create terrain
    for (const tile of terrain) {
      const geometry = this.geometries.get('plane');
      const material = this.materials.get(tile.material || 'stone');
      
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(tile.x, tile.elevation || 0, tile.z);
      mesh.rotation.x = -Math.PI / 2;
      mesh.scale.set(grid.size, grid.size, 1);
      
      if (tile.elevation > 0) {
        mesh.castShadow = true;
        mesh.receiveShadow = true;
      }
      
      scene.add(mesh);
    }
    
    // Add objects (walls, doors, furniture, etc.)
    for (const obj of objects) {
      const geometry = this.geometries.get(obj.geometry || 'cube');
      const material = this.materials.get(obj.material || 'stone');
      
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(obj.x, obj.y || 0.5, obj.z);
      mesh.scale.set(obj.width || 1, obj.height || 1, obj.depth || 1);
      
      if (obj.rotation) {
        mesh.rotation.set(obj.rotation.x || 0, obj.rotation.y || 0, obj.rotation.z || 0);
      }
      
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      
      scene.add(mesh);
    }
    
    // Add lighting
    const ambientLight = new THREE.AmbientLight(0x404040, 0.3);
    scene.add(ambientLight);
    
    for (const light of lighting) {
      let lightSource;
      
      switch (light.type) {
        case 'point':
          lightSource = new THREE.PointLight(light.color || 0xffffff, light.intensity || 1, light.distance || 10);
          break;
        case 'spot':
          lightSource = new THREE.SpotLight(light.color || 0xffffff, light.intensity || 1, light.distance || 10, light.angle || Math.PI/4);
          break;
        case 'directional':
        default:
          lightSource = new THREE.DirectionalLight(light.color || 0xffffff, light.intensity || 0.5);
          break;
      }
      
      lightSource.position.set(light.x, light.y || 5, light.z);
      lightSource.castShadow = true;
      
      // Configure shadow properties
      lightSource.shadow.mapSize.width = 2048;
      lightSource.shadow.mapSize.height = 2048;
      lightSource.shadow.camera.near = 0.5;
      lightSource.shadow.camera.far = 50;
      
      scene.add(lightSource);
    }
    
    this.scenes.set(sceneId, scene);
    this.cameras.set(sceneId, camera);
    
    return sceneId;
  }

  async addCharacterToMap(sceneId, character) {
    const scene = this.scenes.get(sceneId);
    if (!scene) throw new Error('Scene not found');
    
    // Character base
    const baseGeometry = this.geometries.get('character-base');
    const baseMaterial = new THREE.MeshPhongMaterial({ 
      color: character.color || 0x0066ff,
      transparent: true,
      opacity: 0.8
    });
    
    const base = new THREE.Mesh(baseGeometry, baseMaterial);
    base.position.set(character.x, 0.05, character.z);
    base.castShadow = true;
    base.receiveShadow = true;
    
    // Character figure (simplified)
    const figureGeometry = new THREE.CapsuleGeometry(0.2, 1.5, 4, 8);
    const figureMaterial = new THREE.MeshPhongMaterial({ 
      color: character.skinColor || 0xffdbac 
    });
    
    const figure = new THREE.Mesh(figureGeometry, figureMaterial);
    figure.position.set(character.x, 0.85, character.z);
    figure.castShadow = true;
    
    // Equipment (basic sword/shield visualization)
    if (character.equipment) {
      if (character.equipment.weapon) {
        const weaponGeometry = new THREE.CylinderGeometry(0.02, 0.02, 1, 8);
        const weaponMaterial = this.materials.get('metal');
        const weapon = new THREE.Mesh(weaponGeometry, weaponMaterial);
        weapon.position.set(character.x + 0.3, 1, character.z);
        weapon.rotation.z = Math.PI / 4;
        scene.add(weapon);
      }
      
      if (character.equipment.shield) {
        const shieldGeometry = new THREE.CylinderGeometry(0.4, 0.4, 0.05, 8);
        const shieldMaterial = this.materials.get('metal');
        const shield = new THREE.Mesh(shieldGeometry, shieldMaterial);
        shield.position.set(character.x - 0.3, 1, character.z);
        shield.rotation.z = Math.PI / 2;
        scene.add(shield);
      }
    }
    
    // Health bar above character
    if (character.hp) {
      const healthBarGeometry = new THREE.PlaneGeometry(0.8, 0.1);
      const healthPercentage = character.hp.current / character.hp.max;
      const healthColor = healthPercentage > 0.5 ? 0x00ff00 : healthPercentage > 0.25 ? 0xffff00 : 0xff0000;
      
      const healthBarMaterial = new THREE.MeshBasicMaterial({ 
        color: healthColor,
        transparent: true,
        opacity: 0.8
      });
      
      const healthBar = new THREE.Mesh(healthBarGeometry, healthBarMaterial);
      healthBar.position.set(character.x, 2.2, character.z);
      healthBar.scale.x = healthPercentage;
      healthBar.lookAt(this.cameras.get(sceneId).position);
      
      scene.add(healthBar);
    }
    
    scene.add(base);
    scene.add(figure);
    
    return { base, figure };
  }

  async renderDiceRoll(diceType, result) {
    const sceneId = `dice-${Date.now()}`;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a1a);
    
    const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
    camera.position.set(2, 2, 2);
    camera.lookAt(0, 0, 0);
    
    // Add lighting
    const ambientLight = new THREE.AmbientLight(0x404040, 0.4);
    scene.add(ambientLight);
    
    const pointLight = new THREE.PointLight(0xffffff, 1, 100);
    pointLight.position.set(5, 5, 5);
    pointLight.castShadow = true;
    scene.add(pointLight);
    
    // Create dice
    const diceGeometry = this.geometries.get(diceType);
    const diceMaterial = new THREE.MeshPhongMaterial({ 
      color: this.getDiceColor(diceType),
      shininess: 100
    });
    
    const dice = new THREE.Mesh(diceGeometry, diceMaterial);
    dice.castShadow = true;
    
    // Add result text
    const canvas = new Canvas(256, 256);
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 128px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(result.toString(), 128, 150);
    
    const texture = new THREE.CanvasTexture(canvas);
    const textMaterial = new THREE.MeshBasicMaterial({ map: texture });
    const textGeometry = new THREE.PlaneGeometry(1, 1);
    const textMesh = new THREE.Mesh(textGeometry, textMaterial);
    textMesh.position.set(0, 0, 1.1);
    
    scene.add(dice);
    scene.add(textMesh);
    
    // Add ground plane
    const groundGeometry = new THREE.PlaneGeometry(10, 10);
    const groundMaterial = new THREE.MeshPhongMaterial({ color: 0x333333 });
    const ground = new THREE.Mesh(groundGeometry, groundMaterial);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -1;
    ground.receiveShadow = true;
    scene.add(ground);
    
    this.scenes.set(sceneId, scene);
    this.cameras.set(sceneId, camera);
    
    return sceneId;
  }

  getDiceColor(diceType) {
    const colors = {
      'd4': 0xff6b6b,    // Red
      'd6': 0x4ecdc4,    // Teal
      'd8': 0x45b7d1,    // Blue
      'd10': 0x96ceb4,   // Green
      'd12': 0xfeca57,   // Yellow
      'd20': 0x9c88ff    // Purple
    };
    
    return colors[diceType] || 0xffffff;
  }

  async renderScene(sceneId, options = {}) {
    const scene = this.scenes.get(sceneId);
    const camera = this.cameras.get(sceneId);
    
    if (!scene || !camera) {
      throw new Error('Scene or camera not found');
    }
    
    // Configure render options
    this.renderer.setSize(options.width || 1920, options.height || 1080);
    
    if (options.background) {
      scene.background = new THREE.Color(options.background);
    }
    
    // Render the scene
    this.renderer.render(scene, camera);
    
    // Get image data
    const canvas = this.renderer.domElement;
    const buffer = canvas.toBuffer('image/png');
    
    // Process with sharp for optimization
    const processedBuffer = await sharp(buffer)
      .resize(options.width || 1920, options.height || 1080)
      .jpeg({ quality: options.quality || 90 })
      .toBuffer();
    
    return processedBuffer;
  }

  async createSpellEffect(spellData) {
    const { type, level, element, area } = spellData;
    const sceneId = `spell-${Date.now()}`;
    
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, 16/9, 0.1, 1000);
    camera.position.set(5, 5, 5);
    camera.lookAt(0, 0, 0);
    
    // Base effect
    let effectGeometry, effectMaterial;
    
    switch (type) {
      case 'fireball':
        effectGeometry = new THREE.SphereGeometry(area.radius, 16, 16);
        effectMaterial = new THREE.MeshBasicMaterial({ 
          color: 0xff4500,
          transparent: true,
          opacity: 0.7
        });
        break;
        
      case 'lightning':
        effectGeometry = new THREE.CylinderGeometry(0.1, 0.1, 10, 8);
        effectMaterial = new THREE.MeshBasicMaterial({ 
          color: 0x00ffff,
          emissive: 0x004466
        });
        break;
        
      case 'shield':
        effectGeometry = new THREE.SphereGeometry(2, 16, 16);
        effectMaterial = new THREE.MeshBasicMaterial({ 
          color: 0x4444ff,
          transparent: true,
          opacity: 0.3,
          wireframe: true
        });
        break;
        
      default:
        effectGeometry = new THREE.SphereGeometry(1, 16, 16);
        effectMaterial = new THREE.MeshBasicMaterial({ 
          color: 0xffffff,
          transparent: true,
          opacity: 0.5
        });
    }
    
    const effectMesh = new THREE.Mesh(effectGeometry, effectMaterial);
    scene.add(effectMesh);
    
    // Add particle system for enhanced effects
    const particleCount = level * 100;
    const particles = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    
    for (let i = 0; i < particleCount * 3; i++) {
      positions[i] = (Math.random() - 0.5) * area.radius * 2;
    }
    
    particles.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    
    const particleMaterial = new THREE.PointsMaterial({
      color: effectMaterial.color,
      size: 0.1,
      transparent: true,
      opacity: 0.6
    });
    
    const particleSystem = new THREE.Points(particles, particleMaterial);
    scene.add(particleSystem);
    
    // Lighting
    const ambientLight = new THREE.AmbientLight(0x404040, 0.4);
    scene.add(ambientLight);
    
    const effectLight = new THREE.PointLight(effectMaterial.color, 1, 20);
    effectLight.position.set(0, 0, 0);
    scene.add(effectLight);
    
    this.scenes.set(sceneId, scene);
    this.cameras.set(sceneId, camera);
    
    return sceneId;
  }

  async create3DModel(modelData) {
    const { type, dimensions, details, materials } = modelData;
    const sceneId = `model-${Date.now()}`;
    
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
    
    let model;
    
    switch (type) {
      case 'miniature':
        model = await this.createMiniatureModel(dimensions, details);
        break;
      case 'terrain':
        model = await this.createTerrainModel(dimensions, details);
        break;
      case 'prop':
        model = await this.createPropModel(dimensions, details);
        break;
      default:
        model = await this.createGenericModel(dimensions, details);
    }
    
    // Apply materials
    if (materials && materials.length > 0) {
      model.traverse((child) => {
        if (child.isMesh) {
          child.material = this.materials.get(materials[0]) || child.material;
        }
      });
    }
    
    scene.add(model);
    
    // Position camera based on model size
    const box = new THREE.Box3().setFromObject(model);
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    
    camera.position.set(maxDim * 1.5, maxDim * 1.2, maxDim * 1.5);
    camera.lookAt(0, 0, 0);
    
    // Add lighting
    const ambientLight = new THREE.AmbientLight(0x404040, 0.4);
    scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(10, 10, 5);
    directionalLight.castShadow = true;
    scene.add(directionalLight);
    
    this.scenes.set(sceneId, scene);
    this.cameras.set(sceneId, camera);
    
    return { sceneId, model };
  }

  async createMiniatureModel(dimensions, details) {
    const group = new THREE.Group();
    
    // Base
    const baseGeometry = new THREE.CylinderGeometry(
      dimensions.baseRadius || 0.5,
      dimensions.baseRadius || 0.5,
      dimensions.baseHeight || 0.1,
      16
    );
    const baseMaterial = new THREE.MeshPhongMaterial({ color: 0x333333 });
    const base = new THREE.Mesh(baseGeometry, baseMaterial);
    group.add(base);
    
    // Body
    const bodyGeometry = new THREE.CapsuleGeometry(
      dimensions.bodyRadius || 0.2,
      dimensions.height || 1.8,
      4, 8
    );
    const bodyMaterial = new THREE.MeshPhongMaterial({ 
      color: details.skinColor || 0xffdbac 
    });
    const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
    body.position.y = (dimensions.height || 1.8) / 2 + (dimensions.baseHeight || 0.1);
    group.add(body);
    
    // Head
    const headGeometry = new THREE.SphereGeometry(dimensions.headRadius || 0.15, 16, 16);
    const head = new THREE.Mesh(headGeometry, bodyMaterial);
    head.position.y = dimensions.height || 1.8 + (dimensions.baseHeight || 0.1) + (dimensions.headRadius || 0.15);
    group.add(head);
    
    // Equipment details would be added here based on character class/equipment
    
    return group;
  }

  async createTerrainModel(dimensions, details) {
    const group = new THREE.Group();
    
    // Generate terrain using noise functions
    const geometry = new THREE.PlaneGeometry(
      dimensions.width || 10,
      dimensions.depth || 10,
      dimensions.segments || 32,
      dimensions.segments || 32
    );
    
    const positions = geometry.attributes.position.array;
    
    // Apply height map
    for (let i = 0; i < positions.length; i += 3) {
      const x = positions[i];
      const z = positions[i + 2];
      positions[i + 1] = this.noise(x * 0.1, z * 0.1) * (dimensions.maxHeight || 2);
    }
    
    geometry.computeVertexNormals();
    
    const material = this.materials.get(details.material || 'grass');
    const terrain = new THREE.Mesh(geometry, material);
    terrain.rotation.x = -Math.PI / 2;
    
    group.add(terrain);
    
    return group;
  }

  async createPropModel(dimensions, details) {
    const group = new THREE.Group();
    
    switch (details.propType) {
      case 'chest':
        const chestGeometry = new THREE.BoxGeometry(
          dimensions.width || 1,
          dimensions.height || 0.6,
          dimensions.depth || 0.6
        );
        const chestMaterial = this.materials.get('wood');
        const chest = new THREE.Mesh(chestGeometry, chestMaterial);
        group.add(chest);
        break;
        
      case 'door':
        const doorGeometry = new THREE.BoxGeometry(
          dimensions.width || 0.1,
          dimensions.height || 2,
          dimensions.depth || 1
        );
        const doorMaterial = this.materials.get('wood');
        const door = new THREE.Mesh(doorGeometry, doorMaterial);
        group.add(door);
        break;
        
      default:
        const defaultGeometry = new THREE.BoxGeometry(
          dimensions.width || 1,
          dimensions.height || 1,
          dimensions.depth || 1
        );
        const defaultMaterial = this.materials.get('stone');
        const defaultProp = new THREE.Mesh(defaultGeometry, defaultMaterial);
        group.add(defaultProp);
    }
    
    return group;
  }

  async createGenericModel(dimensions, details) {
    const geometry = new THREE.BoxGeometry(
      dimensions.width || 1,
      dimensions.height || 1,
      dimensions.depth || 1
    );
    const material = new THREE.MeshPhongMaterial({ color: 0x666666 });
    return new THREE.Mesh(geometry, material);
  }

  // Simple noise function for terrain generation
  noise(x, y) {
    return Math.sin(x) * Math.cos(y) * 0.5 + 
           Math.sin(x * 2.1) * Math.cos(y * 1.9) * 0.25 +
           Math.sin(x * 4.3) * Math.cos(y * 3.7) * 0.125;
  }

  async exportModel(sceneId, format = 'stl') {
    const scene = this.scenes.get(sceneId);
    if (!scene) throw new Error('Scene not found');
    
    // Export logic would depend on the format
    // For STL export, we'd need a library like three-to-stl
    // For now, return a placeholder
    return {
      format,
      data: 'model-export-data',
      filename: `model-${sceneId}.${format}`
    };
  }

  cleanup(sceneId) {
    const scene = this.scenes.get(sceneId);
    if (scene) {
      scene.traverse((object) => {
        if (object.geometry) object.geometry.dispose();
        if (object.material) {
          if (Array.isArray(object.material)) {
            object.material.forEach(material => material.dispose());
          } else {
            object.material.dispose();
          }
        }
      });
      
      this.scenes.delete(sceneId);
      this.cameras.delete(sceneId);
    }
  }
}

export default VisualizationEngine;