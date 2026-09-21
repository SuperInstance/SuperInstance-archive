const Joi = require('joi');
const logger = require('./logger');

// Custom validation schemas
const schemas = {
  // MongoDB ObjectId pattern
  objectId: Joi.string().pattern(/^[0-9a-fA-F]{24}$/),
  
  // UUID pattern
  uuid: Joi.string().uuid(),
  
  // World ID pattern (can be UUID or custom format)
  worldId: Joi.string().min(8).max(64),
  
  // User ID pattern
  userId: Joi.string().min(1).max(128),
  
  // World name
  worldName: Joi.string().min(1).max(200).trim(),
  
  // Description
  description: Joi.string().max(2000).allow('').trim(),
  
  // Theme
  theme: Joi.string().valid('fantasy', 'sci-fi', 'modern', 'historical', 'horror', 'steampunk', 'cyberpunk'),
  
  // Location types
  locationType: Joi.string().valid('settlement', 'dungeon', 'wilderness', 'landmark', 'region'),
  
  // NPC roles
  npcRole: Joi.string().valid('ally', 'enemy', 'neutral', 'vendor', 'quest_giver', 'ruler', 'guard'),
  
  // Quest types
  questType: Joi.string().valid('fetch', 'kill', 'escort', 'explore', 'social', 'puzzle', 'delivery'),
  
  // Difficulty levels
  difficulty: Joi.string().valid('easy', 'medium', 'hard', 'deadly'),
  
  // Coordinates
  coordinates: Joi.object({
    x: Joi.number().required(),
    y: Joi.number().required(),
    z: Joi.number().optional()
  }),
  
  // Stats object
  stats: Joi.object({
    str: Joi.number().min(1).max(30).default(10),
    dex: Joi.number().min(1).max(30).default(10),
    con: Joi.number().min(1).max(30).default(10),
    int: Joi.number().min(1).max(30).default(10),
    wis: Joi.number().min(1).max(30).default(10),
    cha: Joi.number().min(1).max(30).default(10)
  }),
  
  // Personality traits
  personality: Joi.object({
    traits: Joi.array().items(Joi.string().max(200)).max(10),
    ideals: Joi.array().items(Joi.string().max(200)).max(10),
    bonds: Joi.array().items(Joi.string().max(200)).max(10),
    flaws: Joi.array().items(Joi.string().max(200)).max(10),
    motivation: Joi.string().max(500).allow(''),
    voice: Joi.string().max(300).allow('')
  }),
  
  // AI generation context
  aiContext: Joi.object({
    partyLevel: Joi.number().min(1).max(20).default(1),
    partySize: Joi.number().min(1).max(8).default(4),
    theme: Joi.string().default('fantasy'),
    tone: Joi.string().valid('serious', 'humorous', 'dark', 'heroic', 'mystery').default('serious'),
    complexity: Joi.string().valid('simple', 'moderate', 'complex').default('moderate')
  })
};

// Request validation middleware factory
function validateRequest(schema) {
  return (req, res, next) => {
    const validation = validateData(req.body, schema);
    
    if (!validation.valid) {
      logger.warn('Request validation failed', {
        path: req.path,
        method: req.method,
        errors: validation.errors,
        userId: req.user?.id
      });
      
      return res.status(400).json({
        success: false,
        error: 'Validation failed',
        details: validation.errors
      });
    }
    
    // Replace request body with validated data
    req.body = validation.data;
    next();
  };
}

// Query parameters validation middleware
function validateQuery(schema) {
  return (req, res, next) => {
    const validation = validateData(req.query, schema);
    
    if (!validation.valid) {
      return res.status(400).json({
        success: false,
        error: 'Query validation failed',
        details: validation.errors
      });
    }
    
    req.query = validation.data;
    next();
  };
}

// Generic data validation function
function validateData(data, schema) {
  try {
    // Convert string schema to Joi schema
    const joiSchema = buildJoiSchema(schema);
    
    // Validate data
    const { error, value } = joiSchema.validate(data, {
      abortEarly: false,
      stripUnknown: true,
      convert: true
    });
    
    if (error) {
      return {
        valid: false,
        errors: error.details.map(detail => ({
          field: detail.path.join('.'),
          message: detail.message,
          value: detail.context?.value
        }))
      };
    }
    
    return {
      valid: true,
      data: value
    };
    
  } catch (err) {
    logger.error('Validation error:', err);
    return {
      valid: false,
      errors: [{ field: 'general', message: 'Validation schema error' }]
    };
  }
}

// Build Joi schema from simple object definition
function buildJoiSchema(schema) {
  if (schema instanceof Object && schema.isJoi) {
    return schema;
  }
  
  const joiSchema = {};
  
  for (const [key, definition] of Object.entries(schema)) {
    joiSchema[key] = parseFieldDefinition(definition);
  }
  
  return Joi.object(joiSchema);
}

// Parse field definition string/object to Joi validator
function parseFieldDefinition(definition) {
  if (typeof definition === 'string') {
    return parseStringDefinition(definition);
  }
  
  if (definition && typeof definition === 'object' && definition.isJoi) {
    return definition;
  }
  
  if (typeof definition === 'object') {
    return Joi.object(definition);
  }
  
  return Joi.any();
}

// Parse string definition like "string?", "number", "array"
function parseStringDefinition(definition) {
  const optional = definition.endsWith('?');
  const type = optional ? definition.slice(0, -1) : definition;
  
  let validator;
  
  switch (type) {
    case 'string':
      validator = Joi.string();
      break;
    case 'number':
      validator = Joi.number();
      break;
    case 'integer':
      validator = Joi.number().integer();
      break;
    case 'boolean':
      validator = Joi.boolean();
      break;
    case 'array':
      validator = Joi.array();
      break;
    case 'object':
      validator = Joi.object();
      break;
    case 'date':
      validator = Joi.date();
      break;
    case 'email':
      validator = Joi.string().email();
      break;
    case 'uuid':
      validator = schemas.uuid;
      break;
    case 'objectId':
      validator = schemas.objectId;
      break;
    case 'worldId':
      validator = schemas.worldId;
      break;
    case 'userId':
      validator = schemas.userId;
      break;
    case 'worldName':
      validator = schemas.worldName;
      break;
    case 'description':
      validator = schemas.description;
      break;
    case 'theme':
      validator = schemas.theme;
      break;
    case 'locationType':
      validator = schemas.locationType;
      break;
    case 'npcRole':
      validator = schemas.npcRole;
      break;
    case 'questType':
      validator = schemas.questType;
      break;
    case 'difficulty':
      validator = schemas.difficulty;
      break;
    case 'coordinates':
      validator = schemas.coordinates;
      break;
    case 'stats':
      validator = schemas.stats;
      break;
    case 'personality':
      validator = schemas.personality;
      break;
    case 'aiContext':
      validator = schemas.aiContext;
      break;
    default:
      validator = Joi.any();
  }
  
  return optional ? validator.optional() : validator.required();
}

// Validate world data structure
function validateWorldData(worldData) {
  const schema = Joi.object({
    worldId: schemas.worldId.required(),
    name: schemas.worldName.required(),
    description: schemas.description.optional(),
    theme: schemas.theme.required(),
    creator: schemas.userId.required(),
    
    content: Joi.object({
      settings: Joi.object({
        geography: Joi.object({
          climate: Joi.string().optional(),
          terrain: Joi.array().items(Joi.string()).optional(),
          size: Joi.string().valid('local', 'regional', 'continental', 'global', 'planar').optional(),
          magicLevel: Joi.string().valid('none', 'low', 'medium', 'high', 'overwhelming').optional()
        }).optional(),
        
        culture: Joi.object({
          races: Joi.array().items(Joi.string()).optional(),
          languages: Joi.array().items(Joi.string()).optional(),
          religions: Joi.array().items(Joi.string()).optional(),
          governments: Joi.array().items(Joi.string()).optional()
        }).optional(),
        
        technology: Joi.object({
          level: Joi.string().valid('stone', 'bronze', 'iron', 'medieval', 'renaissance', 'industrial', 'modern', 'futuristic').optional(),
          magic: Joi.boolean().optional(),
          commonItems: Joi.array().items(Joi.string()).optional()
        }).optional()
      }).optional(),
      
      locations: Joi.array().items(Joi.object({
        locationId: Joi.string().required(),
        name: Joi.string().required(),
        type: schemas.locationType.required(),
        description: schemas.description.optional(),
        coordinates: schemas.coordinates.optional()
      })).optional(),
      
      npcs: Joi.array().items(Joi.object({
        npcId: Joi.string().required(),
        name: Joi.string().required(),
        race: Joi.string().optional(),
        class: Joi.string().optional(),
        level: Joi.number().min(1).max(30).default(1),
        stats: schemas.stats.optional(),
        personality: schemas.personality.optional()
      })).optional(),
      
      story: Joi.object({
        mainQuest: Joi.object({
          title: Joi.string().optional(),
          description: Joi.string().optional(),
          stages: Joi.array().optional()
        }).optional(),
        
        sideQuests: Joi.array().items(Joi.object({
          questId: Joi.string().required(),
          title: Joi.string().required(),
          description: Joi.string().optional(),
          type: schemas.questType.optional(),
          level: Joi.number().min(1).max(20).default(1)
        })).optional(),
        
        plotHooks: Joi.array().optional(),
        events: Joi.array().optional(),
        factions: Joi.array().optional()
      }).optional()
    }).required(),
    
    permissions: Joi.object({
      public: Joi.boolean().default(false),
      allowGuests: Joi.boolean().default(false),
      adminUsers: Joi.array().items(schemas.userId).default([]),
      editUsers: Joi.array().items(schemas.userId).default([]),
      viewUsers: Joi.array().items(schemas.userId).default([])
    }).optional()
  });
  
  return validateData(worldData, schema);
}

// Validate AI generation request
function validateAIRequest(requestData) {
  const schema = Joi.object({
    prompt: Joi.string().min(10).max(2000).required(),
    context: schemas.aiContext.optional(),
    options: Joi.object({
      includeNPCs: Joi.boolean().default(true),
      includeLocations: Joi.boolean().default(true),
      includeEncounters: Joi.boolean().default(true),
      includeLore: Joi.boolean().default(false),
      complexity: Joi.string().valid('simple', 'moderate', 'complex').default('moderate')
    }).optional()
  });
  
  return validateData(requestData, schema);
}

// Validate collaboration session data
function validateCollaborationSession(sessionData) {
  const schema = Joi.object({
    worldId: schemas.worldId.required(),
    userId: schemas.userId.required(),
    userName: Joi.string().min(1).max(100).required(),
    permissions: Joi.object({
      edit: Joi.boolean().default(true),
      create: Joi.boolean().default(true),
      delete: Joi.boolean().default(false),
      ai: Joi.boolean().default(true)
    }).optional(),
    currentContext: Joi.object({
      type: Joi.string().valid('character', 'map', 'story', 'world').default('world'),
      documentId: Joi.string().optional(),
      cursor: Joi.object({
        x: Joi.number().optional(),
        y: Joi.number().optional()
      }).optional()
    }).optional()
  });
  
  return validateData(sessionData, schema);
}

// Sanitize HTML content
function sanitizeHtml(content) {
  if (!content || typeof content !== 'string') return '';
  
  // Basic HTML sanitization - remove dangerous tags and attributes
  return content
    .replace(/<script[^>]*>.*?<\/script>/gi, '')
    .replace(/<iframe[^>]*>.*?<\/iframe>/gi, '')
    .replace(/<object[^>]*>.*?<\/object>/gi, '')
    .replace(/<embed[^>]*>/gi, '')
    .replace(/javascript:/gi, '')
    .replace(/on\w+\s*=/gi, '')
    .trim();
}

// Validate file upload
function validateFileUpload(file, options = {}) {
  const {
    maxSize = 10 * 1024 * 1024, // 10MB default
    allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
    allowedExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
  } = options;
  
  const errors = [];
  
  if (!file) {
    errors.push('No file provided');
    return { valid: false, errors };
  }
  
  // Check file size
  if (file.size > maxSize) {
    errors.push(`File size exceeds maximum allowed size of ${Math.round(maxSize / (1024 * 1024))}MB`);
  }
  
  // Check MIME type
  if (allowedTypes.length > 0 && !allowedTypes.includes(file.mimetype)) {
    errors.push(`File type ${file.mimetype} is not allowed`);
  }
  
  // Check file extension
  if (allowedExtensions.length > 0) {
    const ext = file.originalname.toLowerCase().substring(file.originalname.lastIndexOf('.'));
    if (!allowedExtensions.includes(ext)) {
      errors.push(`File extension ${ext} is not allowed`);
    }
  }
  
  return {
    valid: errors.length === 0,
    errors
  };
}

module.exports = {
  validateRequest,
  validateQuery,
  validateData,
  validateWorldData,
  validateAIRequest,
  validateCollaborationSession,
  sanitizeHtml,
  validateFileUpload,
  schemas
};