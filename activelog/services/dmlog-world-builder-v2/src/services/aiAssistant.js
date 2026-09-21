const OpenAI = require('openai');
const logger = require('../utils/logger');
const { generateUniqueId } = require('../utils/helpers');

class AIAssistant {
  constructor() {
    // Only initialize OpenAI if API key is provided
    if (process.env.OPENAI_API_KEY) {
      this.openai = new OpenAI({
        apiKey: process.env.OPENAI_API_KEY
      });
      this.isEnabled = true;
    } else {
      this.openai = null;
      this.isEnabled = false;
      console.warn('OpenAI API key not provided - AI features will be disabled');
    }
    
    // Model configurations for different tasks
    this.models = {
      creative: 'gpt-4-1106-preview', // For story generation
      analytical: 'gpt-4', // For balancing and analysis
      quick: 'gpt-3.5-turbo-1106' // For quick responses
    };
    
    // Base system prompts for different contexts
    this.systemPrompts = {
      worldBuilder: `You are an expert D&D world builder and dungeon master. You create immersive, balanced, and engaging content for tabletop RPG campaigns. Always consider game balance, narrative coherence, and player engagement. Respond with structured, actionable content.`,
      
      storyGenerator: `You are a master storyteller specializing in D&D adventures. Create compelling narratives with interesting plot hooks, memorable NPCs, and engaging conflicts. Balance challenge with player agency and ensure stories have clear objectives and meaningful choices.`,
      
      encounterDesigner: `You are an expert encounter designer for D&D 5e. Create balanced, interesting combat and social encounters that challenge players appropriately for their level. Consider action economy, terrain, objectives beyond "kill everything," and opportunities for creative problem-solving.`,
      
      npcCreator: `You are skilled at creating memorable NPCs for D&D campaigns. Design characters with clear motivations, distinctive personalities, and interesting backstories that can drive plot forward. Make them feel alive and reactive to player actions.`,
      
      worldAnalyst: `You are an analytical expert who evaluates D&D content for balance, consistency, and engagement. Provide constructive feedback and suggestions for improvement while maintaining the creative vision.`
    };
  }

  // Check if AI is available
  checkAvailability() {
    if (!this.isEnabled) {
      throw new Error('AI features are disabled - OpenAI API key not provided. Please set OPENAI_API_KEY environment variable.');
    }
  }

  // Generate complete adventure from description
  async generateAdventure(prompt, options = {}) {
    this.checkAvailability();
    
    try {
      const {
        partyLevel = 5,
        partySize = 4,
        theme = 'fantasy',
        length = 'medium', // short, medium, long
        includeNPCs = true,
        includeEncounters = true,
        includeLocations = true
      } = options;

      const systemPrompt = `${this.systemPrompts.storyGenerator}
      
Create a complete D&D adventure for a party of ${partySize} level ${partyLevel} characters. The adventure should be ${length} length and have a ${theme} theme. Include the following structure:

1. Adventure Title and Summary
2. Background and Hook
3. Key NPCs (if requested)
4. Locations (if requested) 
5. Encounters (if requested)
6. Treasure and Rewards
7. Potential Complications
8. Adventure Conclusion Options

Make it engaging, balanced, and provide clear guidance for the DM.`;

      const response = await this.openai.chat.completions.create({
        model: this.models.creative,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: prompt }
        ],
        temperature: 0.8,
        max_tokens: 2000
      });

      const content = response.choices[0].message.content;
      
      // Parse and structure the response
      const adventure = this.parseAdventureResponse(content, {
        partyLevel,
        partySize,
        theme,
        length
      });

      return {
        success: true,
        adventure,
        usage: response.usage
      };

    } catch (error) {
      logger.error('Adventure generation error:', error);
      throw new Error(`Failed to generate adventure: ${error.message}`);
    }
  }

  // Generate NPCs from character backstories
  async generateNPCsFromBackstories(characterBackstories, worldContext = {}) {
    this.checkAvailability();
    
    try {
      const systemPrompt = `${this.systemPrompts.npcCreator}
      
Based on the provided character backstories, create relevant NPCs that can drive plot and create meaningful connections. For each NPC, provide:

1. Name and basic description
2. Relationship to character(s)
3. Current situation/conflict
4. Goals and motivations
5. Personality traits
6. Plot hooks they can provide
7. Stats (if combat is likely)

Make these NPCs feel connected to the world and the characters' stories.`;

      const prompt = `Character Backstories:
${characterBackstories.map((story, i) => `Character ${i + 1}: ${story}`).join('\n\n')}

World Context: ${JSON.stringify(worldContext, null, 2)}

Create 3-5 NPCs that would naturally fit into this campaign based on the character backstories.`;

      const response = await this.openai.chat.completions.create({
        model: this.models.creative,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: prompt }
        ],
        temperature: 0.7,
        max_tokens: 1500
      });

      const npcs = this.parseNPCResponse(response.choices[0].message.content);
      
      return {
        success: true,
        npcs,
        usage: response.usage
      };

    } catch (error) {
      logger.error('NPC generation error:', error);
      throw new Error(`Failed to generate NPCs: ${error.message}`);
    }
  }

  // Balance encounters automatically
  async balanceEncounter(encounter, partyLevel, partySize) {
    this.checkAvailability();
    
    try {
      const systemPrompt = `${this.systemPrompts.encounterDesigner}
      
Analyze and balance the provided encounter for a party of ${partySize} level ${partyLevel} characters. Provide:

1. Encounter difficulty rating (Easy/Medium/Hard/Deadly)
2. Adjustments needed for proper balance
3. Suggested modifications to creatures or terrain
4. Alternative victory conditions
5. Scaling options for different party compositions

Use D&D 5e encounter building guidelines.`;

      const prompt = `Encounter to Balance:
${JSON.stringify(encounter, null, 2)}

Party: ${partySize} characters at level ${partyLevel}`;

      const response = await this.openai.chat.completions.create({
        model: this.models.analytical,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: prompt }
        ],
        temperature: 0.3,
        max_tokens: 1000
      });

      const balancedEncounter = this.parseEncounterResponse(
        response.choices[0].message.content,
        encounter
      );

      return {
        success: true,
        encounter: balancedEncounter,
        usage: response.usage
      };

    } catch (error) {
      logger.error('Encounter balancing error:', error);
      throw new Error(`Failed to balance encounter: ${error.message}`);
    }
  }

  // Generate appropriate loot
  async generateLoot(context) {
    this.checkAvailability();
    
    try {
      const {
        partyLevel = 5,
        encounterType = 'combat',
        location = 'dungeon',
        theme = 'fantasy',
        boss = false
      } = context;

      const systemPrompt = `${this.systemPrompts.worldBuilder}
      
Generate appropriate loot for a D&D 5e encounter. Consider:
- Party level and expected wealth
- Encounter type and difficulty
- Location and theme appropriateness
- Game balance and utility

Provide a mix of:
1. Currency (appropriate amounts)
2. Common/consumable items
3. Equipment upgrades
4. Unique/special items (if appropriate)
5. Information or clues

Format as a structured list with item descriptions and any special properties.`;

      const prompt = `Generate loot for:
- Party Level: ${partyLevel}
- Encounter Type: ${encounterType}
- Location: ${location}
- Theme: ${theme}
- Boss Encounter: ${boss ? 'Yes' : 'No'}`;

      const response = await this.openai.chat.completions.create({
        model: this.models.analytical,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: prompt }
        ],
        temperature: 0.6,
        max_tokens: 800
      });

      const loot = this.parseLootResponse(response.choices[0].message.content);

      return {
        success: true,
        loot,
        usage: response.usage
      };

    } catch (error) {
      logger.error('Loot generation error:', error);
      throw new Error(`Failed to generate loot: ${error.message}`);
    }
  }

  // Generate narrative beats and pacing
  async generateNarrativePacing(adventure, sessionLength = 4) {
    try {
      const systemPrompt = `${this.systemPrompts.storyGenerator}
      
Create narrative pacing for a D&D adventure session. Break down the adventure into appropriate beats for a ${sessionLength}-hour session. Provide:

1. Opening hook (15-30 minutes)
2. Investigation/exploration beats
3. Social interaction opportunities  
4. Combat encounters
5. Puzzle/challenge moments
6. Climax preparation
7. Resolution and cliffhanger

Include estimated timing and transition suggestions.`;

      const prompt = `Adventure to Pace:
${JSON.stringify(adventure, null, 2)}

Target Session Length: ${sessionLength} hours`;

      const response = await this.openai.chat.completions.create({
        model: this.models.creative,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: prompt }
        ],
        temperature: 0.7,
        max_tokens: 1200
      });

      const pacing = this.parsePacingResponse(response.choices[0].message.content);

      return {
        success: true,
        pacing,
        usage: response.usage
      };

    } catch (error) {
      logger.error('Pacing generation error:', error);
      throw new Error(`Failed to generate pacing: ${error.message}`);
    }
  }

  // Suggest plot twists and complications
  async generatePlotTwists(currentStory, characterActions = []) {
    try {
      const systemPrompt = `${this.systemPrompts.storyGenerator}
      
Generate interesting plot twists and complications for an ongoing D&D story. Base suggestions on:
- Current story state
- Character actions and decisions
- Narrative tension opportunities
- Unexpected but logical developments

Provide 3-5 options with:
1. Brief description of the twist
2. How it connects to existing elements
3. Potential player reactions
4. How to implement smoothly
5. Long-term story implications`;

      const prompt = `Current Story:
${JSON.stringify(currentStory, null, 2)}

Recent Character Actions:
${characterActions.join('\n')}

Generate plot twists that feel natural and enhance the story.`;

      const response = await this.openai.chat.completions.create({
        model: this.models.creative,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: prompt }
        ],
        temperature: 0.8,
        max_tokens: 1000
      });

      const twists = this.parseTwistsResponse(response.choices[0].message.content);

      return {
        success: true,
        twists,
        usage: response.usage
      };

    } catch (error) {
      logger.error('Plot twist generation error:', error);
      throw new Error(`Failed to generate plot twists: ${error.message}`);
    }
  }

  // One-click game start - generate everything from concept
  async generateCompleteWorld(concept, playerCount = 4, experienceLevel = 'beginner') {
    try {
      const systemPrompt = `${this.systemPrompts.worldBuilder}
      
Create a complete, ready-to-play D&D world from the given concept. This should include everything needed for immediate play:

1. World overview and theme
2. Starting location with key NPCs
3. Initial adventure hook
4. 3-4 locations for exploration
5. 5-6 memorable NPCs with motivations
6. Balanced encounters for the party
7. Treasure and progression rewards
8. Session 1 outline
9. Future adventure seeds

Tailor complexity for ${experienceLevel} players. Make it immediately playable with minimal prep.`;

      const prompt = `World Concept: ${concept}
Player Count: ${playerCount}
Experience Level: ${experienceLevel}

Create a complete world ready for immediate play.`;

      const response = await this.openai.chat.completions.create({
        model: this.models.creative,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: prompt }
        ],
        temperature: 0.7,
        max_tokens: 3000
      });

      const world = this.parseCompleteWorldResponse(
        response.choices[0].message.content,
        { concept, playerCount, experienceLevel }
      );

      return {
        success: true,
        world,
        usage: response.usage
      };

    } catch (error) {
      logger.error('Complete world generation error:', error);
      throw new Error(`Failed to generate complete world: ${error.message}`);
    }
  }

  // Parse response helper methods
  parseAdventureResponse(content, options) {
    // This would parse the AI response into structured adventure data
    // For now, returning a basic structure
    return {
      id: generateUniqueId(),
      title: this.extractTitle(content),
      summary: this.extractSection(content, 'Summary'),
      background: this.extractSection(content, 'Background'),
      hook: this.extractSection(content, 'Hook'),
      npcs: this.extractNPCs(content),
      locations: this.extractLocations(content),
      encounters: this.extractEncounters(content),
      treasure: this.extractTreasure(content),
      complications: this.extractSection(content, 'Complications'),
      conclusion: this.extractSection(content, 'Conclusion'),
      metadata: options,
      generated: new Date()
    };
  }

  parseNPCResponse(content) {
    // Parse NPCs from AI response
    const npcs = [];
    const npcSections = content.split(/\d+\.\s+/).slice(1);
    
    npcSections.forEach(section => {
      const npc = {
        id: generateUniqueId(),
        name: this.extractName(section),
        description: this.extractDescription(section),
        relationship: this.extractRelationship(section),
        goals: this.extractGoals(section),
        personality: this.extractPersonality(section),
        plotHooks: this.extractPlotHooks(section),
        generated: new Date()
      };
      npcs.push(npc);
    });
    
    return npcs;
  }

  parseEncounterResponse(content, originalEncounter) {
    return {
      ...originalEncounter,
      balanced: true,
      difficulty: this.extractDifficulty(content),
      adjustments: this.extractAdjustments(content),
      alternatives: this.extractAlternatives(content),
      scaling: this.extractScaling(content),
      balancedAt: new Date()
    };
  }

  parseLootResponse(content) {
    return {
      currency: this.extractCurrency(content),
      items: this.extractItems(content),
      equipment: this.extractEquipment(content),
      special: this.extractSpecialItems(content),
      information: this.extractInformation(content),
      generated: new Date()
    };
  }

  parsePacingResponse(content) {
    return {
      totalTime: this.extractTotalTime(content),
      beats: this.extractBeats(content),
      transitions: this.extractTransitions(content),
      generated: new Date()
    };
  }

  parseTwistsResponse(content) {
    const twists = [];
    const twistSections = content.split(/\d+\.\s+/).slice(1);
    
    twistSections.forEach(section => {
      twists.push({
        id: generateUniqueId(),
        description: this.extractDescription(section),
        connection: this.extractConnection(section),
        implementation: this.extractImplementation(section),
        implications: this.extractImplications(section)
      });
    });
    
    return twists;
  }

  parseCompleteWorldResponse(content, options) {
    return {
      id: generateUniqueId(),
      concept: options.concept,
      overview: this.extractSection(content, 'Overview'),
      theme: this.extractTheme(content),
      startingLocation: this.extractStartingLocation(content),
      locations: this.extractLocations(content),
      npcs: this.extractNPCs(content),
      adventures: this.extractAdventures(content),
      encounters: this.extractEncounters(content),
      sessionOutline: this.extractSessionOutline(content),
      futureSeeds: this.extractFutureSeeds(content),
      metadata: options,
      generated: new Date()
    };
  }

  // Helper extraction methods (simplified implementations)
  extractTitle(content) {
    const titleMatch = content.match(/^#?\s*(.+)/m);
    return titleMatch ? titleMatch[1].trim() : 'Generated Adventure';
  }

  extractSection(content, sectionName) {
    const regex = new RegExp(`${sectionName}:?\\s*([\\s\\S]*?)(?=\\n\\w+:|$)`, 'i');
    const match = content.match(regex);
    return match ? match[1].trim() : '';
  }

  extractName(section) {
    const nameMatch = section.match(/^([^:\n]+)/);
    return nameMatch ? nameMatch[1].trim() : 'Unnamed';
  }

  extractDescription(section) {
    // Extract the main descriptive text
    return section.split('\n')[0] || section.substring(0, 200);
  }

  // Add more extraction methods as needed...
  extractRelationship(section) { return ''; }
  extractGoals(section) { return []; }
  extractPersonality(section) { return {}; }
  extractPlotHooks(section) { return []; }
  extractDifficulty(content) { return 'Medium'; }
  extractAdjustments(content) { return []; }
  extractAlternatives(content) { return []; }
  extractScaling(content) { return {}; }
  extractCurrency(content) { return {}; }
  extractItems(content) { return []; }
  extractEquipment(content) { return []; }
  extractSpecialItems(content) { return []; }
  extractInformation(content) { return []; }
  extractTotalTime(content) { return 4; }
  extractBeats(content) { return []; }
  extractTransitions(content) { return []; }
  extractConnection(section) { return ''; }
  extractImplementation(section) { return ''; }
  extractImplications(section) { return ''; }
  extractTheme(content) { return 'fantasy'; }
  extractStartingLocation(content) { return {}; }
  extractLocations(content) { return []; }
  extractNPCs(content) { return []; }
  extractAdventures(content) { return []; }
  extractEncounters(content) { return []; }
  extractSessionOutline(content) { return {}; }
  extractFutureSeeds(content) { return []; }
  extractTreasure(content) { return []; }
}

module.exports = new AIAssistant();