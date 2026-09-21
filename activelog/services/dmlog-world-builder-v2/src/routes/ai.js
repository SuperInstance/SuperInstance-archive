const express = require('express');
const router = express.Router();
const aiAssistant = require('../services/aiAssistant');
const logger = require('../utils/logger');
const { validateRequest } = require('../utils/validation');
const { requireAuth } = require('../utils/auth');

// Middleware
router.use(requireAuth);

// Generate complete adventure from description
router.post('/generate-adventure', validateRequest({
  prompt: 'string',
  partyLevel: 'number?',
  partySize: 'number?',
  theme: 'string?',
  length: 'string?'
}), async (req, res) => {
  try {
    const { prompt, ...options } = req.body;
    
    logger.info(`Generating adventure for user ${req.user.id}: ${prompt}`);
    
    const result = await aiAssistant.generateAdventure(prompt, options);
    
    res.json({
      success: true,
      data: result.adventure,
      usage: result.usage
    });

  } catch (error) {
    logger.error('Adventure generation error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Generate NPCs from character backstories
router.post('/generate-npcs', validateRequest({
  characterBackstories: 'array',
  worldContext: 'object?'
}), async (req, res) => {
  try {
    const { characterBackstories, worldContext } = req.body;
    
    logger.info(`Generating NPCs for user ${req.user.id} from ${characterBackstories.length} backstories`);
    
    const result = await aiAssistant.generateNPCsFromBackstories(characterBackstories, worldContext);
    
    res.json({
      success: true,
      data: result.npcs,
      usage: result.usage
    });

  } catch (error) {
    logger.error('NPC generation error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Balance encounter automatically
router.post('/balance-encounter', validateRequest({
  encounter: 'object',
  partyLevel: 'number',
  partySize: 'number'
}), async (req, res) => {
  try {
    const { encounter, partyLevel, partySize } = req.body;
    
    logger.info(`Balancing encounter for user ${req.user.id}: Level ${partyLevel}, Party size ${partySize}`);
    
    const result = await aiAssistant.balanceEncounter(encounter, partyLevel, partySize);
    
    res.json({
      success: true,
      data: result.encounter,
      usage: result.usage
    });

  } catch (error) {
    logger.error('Encounter balancing error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Generate appropriate loot
router.post('/generate-loot', validateRequest({
  context: 'object'
}), async (req, res) => {
  try {
    const { context } = req.body;
    
    logger.info(`Generating loot for user ${req.user.id}: ${JSON.stringify(context)}`);
    
    const result = await aiAssistant.generateLoot(context);
    
    res.json({
      success: true,
      data: result.loot,
      usage: result.usage
    });

  } catch (error) {
    logger.error('Loot generation error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Generate narrative beats and pacing
router.post('/generate-pacing', validateRequest({
  adventure: 'object',
  sessionLength: 'number?'
}), async (req, res) => {
  try {
    const { adventure, sessionLength = 4 } = req.body;
    
    logger.info(`Generating pacing for user ${req.user.id}: ${sessionLength}h session`);
    
    const result = await aiAssistant.generateNarrativePacing(adventure, sessionLength);
    
    res.json({
      success: true,
      data: result.pacing,
      usage: result.usage
    });

  } catch (error) {
    logger.error('Pacing generation error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Suggest plot twists and complications
router.post('/generate-plot-twists', validateRequest({
  currentStory: 'object',
  characterActions: 'array?'
}), async (req, res) => {
  try {
    const { currentStory, characterActions = [] } = req.body;
    
    logger.info(`Generating plot twists for user ${req.user.id}`);
    
    const result = await aiAssistant.generatePlotTwists(currentStory, characterActions);
    
    res.json({
      success: true,
      data: result.twists,
      usage: result.usage
    });

  } catch (error) {
    logger.error('Plot twist generation error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// One-click complete world generation
router.post('/generate-complete-world', validateRequest({
  concept: 'string',
  playerCount: 'number?',
  experienceLevel: 'string?'
}), async (req, res) => {
  try {
    const { concept, playerCount = 4, experienceLevel = 'beginner' } = req.body;
    
    logger.info(`Generating complete world for user ${req.user.id}: ${concept}`);
    
    const result = await aiAssistant.generateCompleteWorld(concept, playerCount, experienceLevel);
    
    res.json({
      success: true,
      data: result.world,
      usage: result.usage
    });

  } catch (error) {
    logger.error('Complete world generation error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Generate location from description
router.post('/generate-location', validateRequest({
  description: 'string',
  locationType: 'string?',
  theme: 'string?',
  dangerLevel: 'string?'
}), async (req, res) => {
  try {
    const { description, locationType = 'settlement', theme = 'fantasy', dangerLevel = 'medium' } = req.body;
    
    const prompt = `Create a detailed D&D location based on this description: ${description}
    
Location Type: ${locationType}
Theme: ${theme}
Danger Level: ${dangerLevel}

Include:
1. Physical description and layout
2. Key NPCs who live/work there
3. Notable features and points of interest
4. Potential encounters or conflicts
5. Shops, services, or resources available
6. Secrets or hidden elements
7. Connection opportunities to other locations`;

    const result = await aiAssistant.generateAdventure(prompt, {
      theme,
      length: 'short',
      includeNPCs: true,
      includeLocations: true,
      includeEncounters: true
    });

    res.json({
      success: true,
      data: {
        location: {
          name: result.adventure.title,
          description: result.adventure.summary,
          type: locationType,
          npcs: result.adventure.npcs || [],
          encounters: result.adventure.encounters || [],
          features: result.adventure.locations || [],
          theme,
          dangerLevel
        }
      },
      usage: result.usage
    });

  } catch (error) {
    logger.error('Location generation error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Generate NPC with personality
router.post('/generate-npc', validateRequest({
  description: 'string',
  role: 'string?',
  relationship: 'string?',
  location: 'string?'
}), async (req, res) => {
  try {
    const { description, role = 'neutral', relationship = 'stranger', location = 'unknown' } = req.body;
    
    const prompt = `Create a detailed D&D NPC based on this description: ${description}
    
Role: ${role}
Relationship to party: ${relationship}
Location: ${location}

Include:
1. Name, race, and basic appearance
2. Personality traits, ideals, bonds, flaws
3. Backstory and current situation
4. Goals and motivations
5. Speaking mannerisms and voice
6. Secrets they might know
7. Plot hooks they could provide
8. Basic stats if combat likely
9. How they react to different approaches`;

    const result = await aiAssistant.generateNPCsFromBackstories([prompt], { location, role });

    res.json({
      success: true,
      data: result.npcs[0] || {
        name: 'Generated NPC',
        description,
        role,
        location
      },
      usage: result.usage
    });

  } catch (error) {
    logger.error('NPC generation error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Generate encounter
router.post('/generate-encounter', validateRequest({
  type: 'string',
  difficulty: 'string',
  environment: 'string?',
  partyLevel: 'number',
  partySize: 'number',
  objective: 'string?'
}), async (req, res) => {
  try {
    const { type, difficulty, environment = 'generic', partyLevel, partySize, objective = 'defeat enemies' } = req.body;
    
    const prompt = `Create a ${difficulty} ${type} encounter for a party of ${partySize} level ${partyLevel} characters.
    
Environment: ${environment}
Objective: ${objective}

For combat encounters, include:
1. Creatures with appropriate CR
2. Tactical setup and terrain
3. Victory conditions beyond killing
4. Environmental hazards or features
5. Treasure rewards

For social encounters, include:
1. NPCs with clear goals
2. Negotiation stakes
3. Skill challenge elements
4. Multiple resolution paths

For exploration encounters, include:
1. Discovery objectives
2. Environmental challenges
3. Hidden elements
4. Progress mechanics`;

    const result = await aiAssistant.balanceEncounter({
      type,
      difficulty,
      environment,
      objective,
      description: prompt
    }, partyLevel, partySize);

    res.json({
      success: true,
      data: result.encounter,
      usage: result.usage
    });

  } catch (error) {
    logger.error('Encounter generation error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Generate quest from concept
router.post('/generate-quest', validateRequest({
  concept: 'string',
  questGiver: 'string?',
  location: 'string?',
  level: 'number?',
  type: 'string?'
}), async (req, res) => {
  try {
    const { concept, questGiver = 'unknown', location = 'starting town', level = 1, type = 'adventure' } = req.body;
    
    const prompt = `Create a D&D quest based on this concept: ${concept}
    
Quest Giver: ${questGiver}
Location: ${location}
Target Level: ${level}
Quest Type: ${type}

Include:
1. Clear quest title and description
2. Motivation for the quest giver
3. Step-by-step objectives
4. Potential obstacles and challenges
5. Multiple solution approaches
6. Appropriate rewards (XP, gold, items, reputation)
7. Possible complications or twists
8. Connections to larger story elements`;

    const result = await aiAssistant.generateAdventure(prompt, {
      partyLevel: level,
      length: 'short',
      theme: 'fantasy',
      includeNPCs: true,
      includeEncounters: true,
      includeLocations: false
    });

    const quest = {
      title: result.adventure.title,
      description: result.adventure.summary,
      giver: questGiver,
      location,
      level,
      type,
      objectives: result.adventure.background ? [result.adventure.background] : [],
      rewards: result.adventure.treasure || [],
      npcs: result.adventure.npcs || [],
      encounters: result.adventure.encounters || []
    };

    res.json({
      success: true,
      data: quest,
      usage: result.usage
    });

  } catch (error) {
    logger.error('Quest generation error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// AI DM mode - generate responses to player actions
router.post('/ai-dm-response', validateRequest({
  situation: 'string',
  playerActions: 'array',
  worldContext: 'object?',
  npcs: 'array?'
}), async (req, res) => {
  try {
    const { situation, playerActions, worldContext = {}, npcs = [] } = req.body;
    
    const prompt = `You are an AI Dungeon Master. Respond to the player actions in the current situation.

Current Situation: ${situation}

Player Actions:
${playerActions.map((action, i) => `Player ${i + 1}: ${action}`).join('\n')}

World Context: ${JSON.stringify(worldContext)}

Available NPCs: ${npcs.map(npc => `${npc.name} (${npc.role || 'NPC'})`).join(', ')}

Provide a response that:
1. Acknowledges each player action
2. Describes immediate consequences
3. Updates the situation
4. Presents new choices or challenges
5. Maintains story momentum
6. Stays consistent with the world
7. Encourages player engagement

Format as a narrative response suitable for reading aloud.`;

    const result = await aiAssistant.generatePlotTwists({
      situation,
      playerActions,
      worldContext,
      npcs
    }, playerActions);

    res.json({
      success: true,
      data: {
        response: result.twists[0]?.description || 'The situation develops...',
        consequences: result.twists[0]?.implementation || [],
        newSituation: result.twists[0]?.implications || situation,
        suggestedActions: [
          'Continue with current plan',
          'Try a different approach',
          'Gather more information',
          'Consult with NPCs'
        ]
      },
      usage: result.usage
    });

  } catch (error) {
    logger.error('AI DM response error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

module.exports = router;