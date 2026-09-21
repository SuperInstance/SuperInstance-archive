const express = require('express');
const router = express.Router();
const World = require('../models/World');
const logger = require('../utils/logger');
const { validateRequest } = require('../utils/validation');
const { requireAuth } = require('../utils/auth');
const { generateUniqueId } = require('../utils/helpers');

// Middleware
router.use(requireAuth);

// Get story elements for a world
router.get('/:worldId', async (req, res) => {
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

    // Check view permission
    if (!hasPermission(world, userId, 'view')) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    res.json({
      success: true,
      data: {
        mainQuest: world.content.story.mainQuest,
        sideQuests: world.content.story.sideQuests,
        plotHooks: world.content.story.plotHooks,
        events: world.content.story.events,
        factions: world.content.story.factions
      }
    });

  } catch (error) {
    logger.error('Get story error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Update main quest
router.put('/:worldId/main-quest', validateRequest({
  title: 'string?',
  description: 'string?',
  stages: 'array?'
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

    // Update main quest
    Object.assign(world.content.story.mainQuest, updates);
    world.lastModifiedBy = userId;
    
    await world.save();

    logger.info(`Main quest updated for world ${worldId}`, { userId });

    res.json({
      success: true,
      data: world.content.story.mainQuest
    });

  } catch (error) {
    logger.error('Update main quest error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Create side quest
router.post('/:worldId/side-quests', validateRequest({
  title: 'string',
  description: 'string',
  giver: 'string?',
  location: 'string?',
  level: 'number?',
  type: 'questType?'
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

    const sideQuest = {
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
      status: 'available',
      created: new Date(),
      createdBy: userId
    };

    world.content.story.sideQuests.push(sideQuest);
    world.lastModifiedBy = userId;
    
    await world.save();

    logger.info(`Side quest created for world ${worldId}: ${sideQuest.title}`, { userId });

    res.status(201).json({
      success: true,
      data: sideQuest
    });

  } catch (error) {
    logger.error('Create side quest error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Update side quest
router.put('/:worldId/side-quests/:questId', validateRequest({
  title: 'string?',
  description: 'string?',
  objectives: 'array?',
  rewards: 'object?',
  status: 'string?'
}), async (req, res) => {
  try {
    const { worldId, questId } = req.params;
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

    const quest = world.content.story.sideQuests.find(q => q.questId === questId);
    if (!quest) {
      return res.status(404).json({
        success: false,
        error: 'Quest not found'
      });
    }

    Object.assign(quest, updates);
    quest.lastModified = new Date();
    quest.lastModifiedBy = userId;
    
    world.lastModifiedBy = userId;
    await world.save();

    logger.info(`Side quest updated: ${questId}`, { worldId, userId });

    res.json({
      success: true,
      data: quest
    });

  } catch (error) {
    logger.error('Update side quest error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Delete side quest
router.delete('/:worldId/side-quests/:questId', async (req, res) => {
  try {
    const { worldId, questId } = req.params;
    const userId = req.user.id;

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

    const questIndex = world.content.story.sideQuests.findIndex(q => q.questId === questId);
    if (questIndex === -1) {
      return res.status(404).json({
        success: false,
        error: 'Quest not found'
      });
    }

    const deletedQuest = world.content.story.sideQuests.splice(questIndex, 1)[0];
    world.lastModifiedBy = userId;
    
    await world.save();

    logger.info(`Side quest deleted: ${questId}`, { worldId, userId });

    res.json({
      success: true,
      message: 'Quest deleted successfully',
      data: { questId: deletedQuest.questId }
    });

  } catch (error) {
    logger.error('Delete side quest error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Create plot hook
router.post('/:worldId/plot-hooks', validateRequest({
  title: 'string',
  description: 'string',
  characters: 'array?',
  locations: 'array?',
  urgency: 'string?'
}), async (req, res) => {
  try {
    const { worldId } = req.params;
    const userId = req.user.id;
    const hookData = req.body;

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

    const plotHook = {
      hookId: generateUniqueId(),
      ...hookData,
      urgency: hookData.urgency || 'medium',
      used: false,
      created: new Date(),
      createdBy: userId
    };

    world.content.story.plotHooks.push(plotHook);
    world.lastModifiedBy = userId;
    
    await world.save();

    logger.info(`Plot hook created for world ${worldId}: ${plotHook.title}`, { userId });

    res.status(201).json({
      success: true,
      data: plotHook
    });

  } catch (error) {
    logger.error('Create plot hook error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Mark plot hook as used
router.put('/:worldId/plot-hooks/:hookId/use', async (req, res) => {
  try {
    const { worldId, hookId } = req.params;
    const userId = req.user.id;

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

    const hook = world.content.story.plotHooks.find(h => h.hookId === hookId);
    if (!hook) {
      return res.status(404).json({
        success: false,
        error: 'Plot hook not found'
      });
    }

    hook.used = true;
    hook.usedDate = new Date();
    hook.usedBy = userId;
    
    world.lastModifiedBy = userId;
    await world.save();

    logger.info(`Plot hook marked as used: ${hookId}`, { worldId, userId });

    res.json({
      success: true,
      data: hook
    });

  } catch (error) {
    logger.error('Mark plot hook as used error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Create story event
router.post('/:worldId/events', validateRequest({
  title: 'string',
  description: 'string',
  date: 'date?',
  location: 'string?',
  participants: 'array?',
  consequences: 'array?'
}), async (req, res) => {
  try {
    const { worldId } = req.params;
    const userId = req.user.id;
    const eventData = req.body;

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

    const storyEvent = {
      eventId: generateUniqueId(),
      ...eventData,
      date: eventData.date || new Date(),
      created: new Date(),
      createdBy: userId
    };

    world.content.story.events.push(storyEvent);
    world.lastModifiedBy = userId;
    
    await world.save();

    logger.info(`Story event created for world ${worldId}: ${storyEvent.title}`, { userId });

    res.status(201).json({
      success: true,
      data: storyEvent
    });

  } catch (error) {
    logger.error('Create story event error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Create faction
router.post('/:worldId/factions', validateRequest({
  name: 'string',
  description: 'string',
  goals: 'array?',
  resources: 'object?'
}), async (req, res) => {
  try {
    const { worldId } = req.params;
    const userId = req.user.id;
    const factionData = req.body;

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

    const faction = {
      factionId: generateUniqueId(),
      ...factionData,
      resources: {
        military: 0,
        economic: 0,
        political: 0,
        magical: 0,
        ...factionData.resources
      },
      relationships: [],
      members: [],
      controlled_locations: [],
      created: new Date(),
      createdBy: userId
    };

    world.content.story.factions.push(faction);
    world.lastModifiedBy = userId;
    
    await world.save();

    logger.info(`Faction created for world ${worldId}: ${faction.name}`, { userId });

    res.status(201).json({
      success: true,
      data: faction
    });

  } catch (error) {
    logger.error('Create faction error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Update faction
router.put('/:worldId/factions/:factionId', validateRequest({
  name: 'string?',
  description: 'string?',
  goals: 'array?',
  resources: 'object?',
  relationships: 'array?'
}), async (req, res) => {
  try {
    const { worldId, factionId } = req.params;
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

    const faction = world.content.story.factions.find(f => f.factionId === factionId);
    if (!faction) {
      return res.status(404).json({
        success: false,
        error: 'Faction not found'
      });
    }

    Object.assign(faction, updates);
    faction.lastModified = new Date();
    faction.lastModifiedBy = userId;
    
    world.lastModifiedBy = userId;
    await world.save();

    logger.info(`Faction updated: ${factionId}`, { worldId, userId });

    res.json({
      success: true,
      data: faction
    });

  } catch (error) {
    logger.error('Update faction error:', error);
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