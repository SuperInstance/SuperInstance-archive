const express = require('express');
const router = express.Router();
const World = require('../models/World');
const logger = require('../utils/logger');
const { validateRequest } = require('../utils/validation');
const { requireAuth } = require('../utils/auth');
const { generateUniqueId } = require('../utils/helpers');
const { getActiveCollaborators } = require('../services/collaboration');

// Middleware
router.use(requireAuth);

// Get all worlds for user
router.get('/', async (req, res) => {
  try {
    const userId = req.user.id;
    const { limit = 20, offset = 0, search = '' } = req.query;

    const query = {
      $or: [
        { creator: userId },
        { 'permissions.editUsers': userId },
        { 'permissions.viewUsers': userId },
        { 'permissions.adminUsers': userId },
        { 'permissions.public': true }
      ]
    };

    if (search) {
      query.$and = [{
        $or: [
          { name: { $regex: search, $options: 'i' } },
          { description: { $regex: search, $options: 'i' } }
        ]
      }];
    }

    const worlds = await World.find(query)
      .select('worldId name description theme creator created lastModified permissions')
      .sort({ lastModified: -1 })
      .limit(parseInt(limit))
      .skip(parseInt(offset));

    const total = await World.countDocuments(query);

    res.json({
      success: true,
      data: worlds,
      pagination: {
        total,
        limit: parseInt(limit),
        offset: parseInt(offset),
        hasMore: offset + limit < total
      }
    });

  } catch (error) {
    logger.error('Get worlds error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Create new world
router.post('/', validateRequest({
  name: 'string',
  description: 'string?',
  theme: 'string?',
  template: 'string?'
}), async (req, res) => {
  try {
    const { name, description, theme = 'fantasy', template } = req.body;
    const userId = req.user.id;
    const userName = req.user.name || 'Unknown User';

    const worldId = generateUniqueId();
    const initialVersion = generateUniqueId();

    const world = new World({
      worldId,
      name,
      description,
      theme,
      creator: userId,
      currentVersion: initialVersion,
      versions: [{
        versionId: initialVersion,
        parentVersion: null,
        branch: 'main',
        author: userId,
        message: 'Initial world creation',
        timestamp: new Date(),
        changes: [{
          type: 'create',
          collection: 'world',
          documentId: worldId,
          newValue: { name, description, theme }
        }]
      }],
      branches: [{
        name: 'main',
        currentVersion: initialVersion,
        description: 'Main development branch',
        creator: userId,
        created: new Date()
      }],
      content: {
        settings: {
          geography: {
            climate: 'temperate',
            terrain: ['forest', 'plains', 'mountains'],
            size: 'regional',
            magicLevel: 'medium'
          },
          culture: {
            races: ['human', 'elf', 'dwarf', 'halfling'],
            languages: ['common'],
            religions: [],
            governments: ['monarchy']
          },
          technology: {
            level: 'medieval',
            magic: true,
            commonItems: []
          }
        },
        locations: [],
        npcs: [],
        story: {
          mainQuest: {
            title: '',
            description: '',
            stages: []
          },
          sideQuests: [],
          plotHooks: [],
          events: [],
          factions: []
        }
      }
    });

    // Apply template if specified
    if (template) {
      await this.applyTemplate(world, template);
    }

    await world.save();

    logger.info(`World created: ${worldId} by user ${userId}`);

    res.status(201).json({
      success: true,
      data: {
        worldId: world.worldId,
        name: world.name,
        description: world.description,
        theme: world.theme,
        created: world.created,
        currentVersion: world.currentVersion
      }
    });

  } catch (error) {
    logger.error('Create world error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Get specific world
router.get('/:worldId', async (req, res) => {
  try {
    const { worldId } = req.params;
    const userId = req.user.id;
    const { version, branch } = req.query;

    const world = await World.findOne({ worldId });
    if (!world) {
      return res.status(404).json({
        success: false,
        error: 'World not found'
      });
    }

    // Check permissions
    if (!hasPermission(world, userId, 'view')) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    // Get active collaborators
    const collaborators = getActiveCollaborators(worldId);

    // Return specific version if requested
    let worldData = world;
    if (version) {
      const versionData = world.versions.find(v => v.versionId === version);
      if (versionData && versionData.snapshot) {
        worldData = {
          ...world.toObject(),
          content: versionData.snapshot.content,
          _isHistoricalVersion: true,
          _requestedVersion: version
        };
      }
    }

    res.json({
      success: true,
      data: worldData,
      collaborators: collaborators.map(c => ({
        userId: c.userId,
        userName: c.userName,
        currentContext: c.currentContext,
        lastActivity: c.lastActivity
      }))
    });

  } catch (error) {
    logger.error('Get world error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Update world
router.put('/:worldId', validateRequest({
  name: 'string?',
  description: 'string?',
  theme: 'string?',
  content: 'object?'
}), async (req, res) => {
  try {
    const { worldId } = req.params;
    const userId = req.user.id;
    const updates = req.body;

    const world = await World.findOne({ worldId });
    if (!world) {
      return res.status(404).json({
        success: false,
        error: 'World not found'
      });
    }

    if (!hasPermission(world, userId, 'edit')) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    // Track changes for version control
    const changes = [];
    
    Object.keys(updates).forEach(field => {
      if (field !== 'content') {
        changes.push({
          type: 'update',
          collection: 'world',
          documentId: worldId,
          field,
          oldValue: world[field],
          newValue: updates[field]
        });
        world[field] = updates[field];
      }
    });

    if (updates.content) {
      changes.push({
        type: 'update',
        collection: 'world',
        documentId: worldId,
        field: 'content',
        oldValue: world.content,
        newValue: updates.content
      });
      world.content = updates.content;
    }

    world.lastModifiedBy = userId;
    await world.save();

    logger.info(`World updated: ${worldId} by user ${userId}`);

    res.json({
      success: true,
      data: world
    });

  } catch (error) {
    logger.error('Update world error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Delete world
router.delete('/:worldId', async (req, res) => {
  try {
    const { worldId } = req.params;
    const userId = req.user.id;

    const world = await World.findOne({ worldId });
    if (!world) {
      return res.status(404).json({
        success: false,
        error: 'World not found'
      });
    }

    // Only creator or admin can delete
    if (world.creator !== userId && !world.permissions.adminUsers.includes(userId)) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    await World.deleteOne({ worldId });

    logger.info(`World deleted: ${worldId} by user ${userId}`);

    res.json({
      success: true,
      message: 'World deleted successfully'
    });

  } catch (error) {
    logger.error('Delete world error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Get world locations
router.get('/:worldId/locations', async (req, res) => {
  try {
    const { worldId } = req.params;
    const userId = req.user.id;

    const world = await World.findOne({ worldId });
    if (!world) {
      return res.status(404).json({
        success: false,
        error: 'World not found'
      });
    }

    if (!hasPermission(world, userId, 'view')) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    res.json({
      success: true,
      data: world.content.locations || []
    });

  } catch (error) {
    logger.error('Get locations error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Add location
router.post('/:worldId/locations', validateRequest({
  name: 'string',
  type: 'string',
  description: 'string?',
  coordinates: 'object?'
}), async (req, res) => {
  try {
    const { worldId } = req.params;
    const userId = req.user.id;
    const locationData = req.body;

    const world = await World.findOne({ worldId });
    if (!world) {
      return res.status(404).json({
        success: false,
        error: 'World not found'
      });
    }

    if (!hasPermission(world, userId, 'edit')) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    const location = {
      locationId: generateUniqueId(),
      ...locationData,
      shops: [],
      npcs: [],
      encounters: [],
      quests: []
    };

    world.content.locations.push(location);
    await world.save();

    logger.info(`Location added to world ${worldId}: ${location.name}`);

    res.status(201).json({
      success: true,
      data: location
    });

  } catch (error) {
    logger.error('Add location error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Get world NPCs
router.get('/:worldId/npcs', async (req, res) => {
  try {
    const { worldId } = req.params;
    const userId = req.user.id;

    const world = await World.findOne({ worldId });
    if (!world) {
      return res.status(404).json({
        success: false,
        error: 'World not found'
      });
    }

    if (!hasPermission(world, userId, 'view')) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    res.json({
      success: true,
      data: world.content.npcs || []
    });

  } catch (error) {
    logger.error('Get NPCs error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Add NPC
router.post('/:worldId/npcs', validateRequest({
  name: 'string',
  race: 'string?',
  class: 'string?',
  description: 'string?'
}), async (req, res) => {
  try {
    const { worldId } = req.params;
    const userId = req.user.id;
    const npcData = req.body;

    const world = await World.findOne({ worldId });
    if (!world) {
      return res.status(404).json({
        success: false,
        error: 'World not found'
      });
    }

    if (!hasPermission(world, userId, 'edit')) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    const npc = {
      npcId: generateUniqueId(),
      ...npcData,
      level: npcData.level || 1,
      stats: {
        str: 10, dex: 10, con: 10, int: 10, wis: 10, cha: 10,
        ...npcData.stats
      },
      personality: {
        traits: [],
        ideals: [],
        bonds: [],
        flaws: [],
        ...npcData.personality
      },
      relationships: [],
      status: 'alive',
      armorClass: npcData.armorClass || 10,
      hitPoints: {
        current: npcData.hitPoints || 1,
        max: npcData.hitPoints || 1
      },
      inventory: [],
      equipment: {}
    };

    world.content.npcs.push(npc);
    await world.save();

    logger.info(`NPC added to world ${worldId}: ${npc.name}`);

    res.status(201).json({
      success: true,
      data: npc
    });

  } catch (error) {
    logger.error('Add NPC error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Get world quests
router.get('/:worldId/quests', async (req, res) => {
  try {
    const { worldId } = req.params;
    const userId = req.user.id;

    const world = await World.findOne({ worldId });
    if (!world) {
      return res.status(404).json({
        success: false,
        error: 'World not found'
      });
    }

    if (!hasPermission(world, userId, 'view')) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    const quests = [
      ...(world.content.story.mainQuest.title ? [world.content.story.mainQuest] : []),
      ...(world.content.story.sideQuests || [])
    ];

    res.json({
      success: true,
      data: quests
    });

  } catch (error) {
    logger.error('Get quests error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Add quest
router.post('/:worldId/quests', validateRequest({
  title: 'string',
  description: 'string',
  type: 'string?',
  level: 'number?'
}), async (req, res) => {
  try {
    const { worldId } = req.params;
    const userId = req.user.id;
    const questData = req.body;

    const world = await World.findOne({ worldId });
    if (!world) {
      return res.status(404).json({
        success: false,
        error: 'World not found'
      });
    }

    if (!hasPermission(world, userId, 'edit')) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    const quest = {
      questId: generateUniqueId(),
      ...questData,
      level: questData.level || 1,
      type: questData.type || 'adventure',
      objectives: [],
      rewards: {
        experience: 0,
        gold: 0,
        items: [],
        reputation: []
      },
      status: 'available'
    };

    world.content.story.sideQuests.push(quest);
    await world.save();

    logger.info(`Quest added to world ${worldId}: ${quest.title}`);

    res.status(201).json({
      success: true,
      data: quest
    });

  } catch (error) {
    logger.error('Add quest error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Update world permissions
router.put('/:worldId/permissions', validateRequest({
  permissions: 'object'
}), async (req, res) => {
  try {
    const { worldId } = req.params;
    const userId = req.user.id;
    const { permissions } = req.body;

    const world = await World.findOne({ worldId });
    if (!world) {
      return res.status(404).json({
        success: false,
        error: 'World not found'
      });
    }

    // Only creator or admin can change permissions
    if (world.creator !== userId && !world.permissions.adminUsers.includes(userId)) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    world.permissions = { ...world.permissions, ...permissions };
    await world.save();

    logger.info(`Permissions updated for world ${worldId} by user ${userId}`);

    res.json({
      success: true,
      data: world.permissions
    });

  } catch (error) {
    logger.error('Update permissions error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Helper function to check permissions
function hasPermission(world, userId, permission) {
  if (world.creator === userId) return true;
  if (world.permissions.adminUsers.includes(userId)) return true;

  switch (permission) {
    case 'view':
      return world.permissions.public || 
             world.permissions.viewUsers.includes(userId) ||
             world.permissions.editUsers.includes(userId);
    case 'edit':
      return world.permissions.editUsers.includes(userId);
    case 'admin':
      return world.permissions.adminUsers.includes(userId);
    default:
      return false;
  }
}

module.exports = router;