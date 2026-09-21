import express from 'express';
import mongoose from 'mongoose';
import { v4 as uuidv4 } from 'uuid';

const router = express.Router();

// Character schema
const CharacterSchema = new mongoose.Schema({
  name: { type: String, required: true },
  playerId: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  campaignId: { type: mongoose.Schema.Types.ObjectId, ref: 'Campaign' },
  
  // Basic character info
  race: String,
  class: String,
  subclass: String,
  level: { type: Number, default: 1 },
  background: String,
  alignment: String,
  experiencePoints: { type: Number, default: 0 },
  
  // Ability scores
  abilityScores: {
    strength: { type: Number, default: 10 },
    dexterity: { type: Number, default: 10 },
    constitution: { type: Number, default: 10 },
    intelligence: { type: Number, default: 10 },
    wisdom: { type: Number, default: 10 },
    charisma: { type: Number, default: 10 }
  },
  
  // Derived stats
  hitPoints: {
    current: Number,
    maximum: Number,
    temporary: { type: Number, default: 0 }
  },
  armorClass: { type: Number, default: 10 },
  speed: { type: Number, default: 30 },
  proficiencyBonus: { type: Number, default: 2 },
  
  // Skills and proficiencies
  skills: [{
    name: String,
    proficient: { type: Boolean, default: false },
    expertise: { type: Boolean, default: false }
  }],
  savingThrows: [{
    ability: String,
    proficient: { type: Boolean, default: false }
  }],
  languages: [String],
  proficiencies: [String],
  
  // Combat stats
  initiative: Number,
  attacks: [{
    name: String,
    attackBonus: Number,
    damage: String,
    damageType: String,
    range: String,
    properties: [String]
  }],
  
  // Spellcasting
  spellcasting: {
    class: String,
    ability: String,
    spellAttackBonus: Number,
    spellSaveDC: Number,
    spellSlots: [{
      level: Number,
      total: Number,
      used: { type: Number, default: 0 }
    }],
    spells: [{
      name: String,
      level: Number,
      school: String,
      castingTime: String,
      range: String,
      components: String,
      duration: String,
      description: String,
      prepared: { type: Boolean, default: false }
    }]
  },
  
  // Equipment and inventory
  equipment: [{
    name: String,
    type: String,
    quantity: { type: Number, default: 1 },
    weight: Number,
    value: {
      amount: Number,
      currency: { type: String, default: 'gp' }
    },
    properties: [String],
    description: String,
    equipped: { type: Boolean, default: false }
  }],
  currency: {
    cp: { type: Number, default: 0 },
    sp: { type: Number, default: 0 },
    gp: { type: Number, default: 0 },
    pp: { type: Number, default: 0 }
  },
  
  // Character features and traits
  features: [{
    name: String,
    source: String, // class, race, feat, etc.
    description: String,
    uses: {
      type: String, // 'per_rest', 'per_day', 'unlimited'
      maximum: Number,
      current: Number
    }
  }],
  traits: [{
    name: String,
    description: String
  }],
  
  // Character backstory
  backstory: {
    personality: String,
    ideals: String,
    bonds: String,
    flaws: String,
    backstory: String
  },
  
  // Visual customization
  appearance: {
    age: String,
    height: String,
    weight: String,
    eyes: String,
    skin: String,
    hair: String,
    portrait: String, // URL or path to image
    description: String
  },
  
  // Character sheet preferences
  preferences: {
    theme: { type: String, default: 'classic' },
    layout: { type: String, default: 'standard' },
    diceStyle: { type: String, default: 'standard' },
    visibility: { type: String, enum: ['private', 'campaign', 'public'], default: 'campaign' }
  },
  
  // Import/export data
  source: {
    platform: String, // 'dnd_beyond', 'roll20', 'foundry', etc.
    importId: String,
    lastSync: Date
  },
  
  // Stats and history
  stats: {
    sessionsPlayed: { type: Number, default: 0 },
    totalDamageDealt: { type: Number, default: 0 },
    totalDamageTaken: { type: Number, default: 0 },
    totalHealingDone: { type: Number, default: 0 },
    spellsCast: { type: Number, default: 0 },
    criticalHits: { type: Number, default: 0 },
    criticalFails: { type: Number, default: 0 }
  },
  
  // Condition tracking
  conditions: [{
    name: String,
    description: String,
    duration: String,
    appliedAt: { type: Date, default: Date.now }
  }],
  
  // Notes and journal
  notes: [{
    title: String,
    content: String,
    category: String,
    createdAt: { type: Date, default: Date.now },
    updatedAt: { type: Date, default: Date.now }
  }]
}, {
  timestamps: true
});

// Add indexes for better query performance
CharacterSchema.index({ playerId: 1, campaignId: 1 });
CharacterSchema.index({ name: 'text' });

const Character = mongoose.models.Character || mongoose.model('Character', CharacterSchema);

// GET /api/characters - List characters
router.get('/', async (req, res) => {
  try {
    const { 
      page = 1, 
      limit = 10, 
      search, 
      campaignId,
      class: charClass,
      level,
      sort = 'updatedAt'
    } = req.query;

    const userId = req.user.id;
    const query = {};

    // Filter by user's characters or campaign characters they can see
    if (campaignId) {
      // Check if user has access to this campaign
      const Campaign = mongoose.model('Campaign');
      const campaign = await Campaign.findById(campaignId);
      
      if (!campaign) {
        return res.status(404).json({ error: 'Campaign not found' });
      }

      const hasAccess = campaign.dmId.toString() === userId ||
                       campaign.players.includes(userId);

      if (!hasAccess) {
        return res.status(403).json({ error: 'Access denied to campaign' });
      }

      query.campaignId = campaignId;
    } else {
      // Show user's own characters or public characters
      query.$or = [
        { playerId: userId },
        { 'preferences.visibility': 'public' }
      ];
    }

    // Search filter
    if (search) {
      query.name = { $regex: search, $options: 'i' };
    }

    // Class filter
    if (charClass) {
      query.class = { $regex: charClass, $options: 'i' };
    }

    // Level filter
    if (level) {
      query.level = parseInt(level);
    }

    const options = {
      page: parseInt(page),
      limit: parseInt(limit),
      sort: { [sort]: -1 },
      populate: [
        { path: 'playerId', select: 'username avatar' },
        { path: 'campaignId', select: 'name dmId' }
      ]
    };

    const characters = await Character.paginate(query, options);
    res.json(characters);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// GET /api/characters/:id - Get specific character
router.get('/:id', async (req, res) => {
  try {
    const character = await Character.findById(req.params.id)
      .populate('playerId', 'username avatar')
      .populate('campaignId', 'name dmId players');

    if (!character) {
      return res.status(404).json({ error: 'Character not found' });
    }

    // Check permissions
    const userId = req.user.id;
    const isOwner = character.playerId._id.toString() === userId;
    const isDM = character.campaignId && character.campaignId.dmId.toString() === userId;
    const isPlayer = character.campaignId && character.campaignId.players.includes(userId);
    const isPublic = character.preferences.visibility === 'public';
    const isCampaignVisible = character.preferences.visibility === 'campaign' && (isDM || isPlayer);

    if (!isOwner && !isDM && !isPublic && !isCampaignVisible) {
      return res.status(403).json({ error: 'Access denied' });
    }

    res.json(character);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// POST /api/characters - Create new character
router.post('/', async (req, res) => {
  try {
    const characterData = {
      ...req.body,
      playerId: req.user.id
    };

    // Validate campaign access if specified
    if (characterData.campaignId) {
      const Campaign = mongoose.model('Campaign');
      const campaign = await Campaign.findById(characterData.campaignId);
      
      if (!campaign) {
        return res.status(404).json({ error: 'Campaign not found' });
      }

      const hasAccess = campaign.dmId.toString() === req.user.id ||
                       campaign.players.includes(req.user.id);

      if (!hasAccess) {
        return res.status(403).json({ error: 'Access denied to campaign' });
      }
    }

    const character = new Character(characterData);
    await character.save();

    await character.populate([
      { path: 'playerId', select: 'username avatar' },
      { path: 'campaignId', select: 'name dmId' }
    ]);

    res.status(201).json(character);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// PUT /api/characters/:id - Update character
router.put('/:id', async (req, res) => {
  try {
    const character = await Character.findById(req.params.id);
    
    if (!character) {
      return res.status(404).json({ error: 'Character not found' });
    }

    // Check if user owns the character or is the DM
    const userId = req.user.id;
    const isOwner = character.playerId.toString() === userId;
    
    let isDM = false;
    if (character.campaignId) {
      const Campaign = mongoose.model('Campaign');
      const campaign = await Campaign.findById(character.campaignId);
      isDM = campaign && campaign.dmId.toString() === userId;
    }

    if (!isOwner && !isDM) {
      return res.status(403).json({ error: 'Access denied' });
    }

    const updatedCharacter = await Character.findByIdAndUpdate(
      req.params.id,
      req.body,
      { new: true, runValidators: true }
    ).populate([
      { path: 'playerId', select: 'username avatar' },
      { path: 'campaignId', select: 'name dmId' }
    ]);

    res.json(updatedCharacter);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// DELETE /api/characters/:id - Delete character
router.delete('/:id', async (req, res) => {
  try {
    const character = await Character.findById(req.params.id);
    
    if (!character) {
      return res.status(404).json({ error: 'Character not found' });
    }

    // Only character owner can delete
    if (character.playerId.toString() !== req.user.id) {
      return res.status(403).json({ error: 'Only the character owner can delete this character' });
    }

    await Character.findByIdAndDelete(req.params.id);
    res.json({ message: 'Character deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// POST /api/characters/:id/level-up - Level up character
router.post('/:id/level-up', async (req, res) => {
  try {
    const character = await Character.findById(req.params.id);
    
    if (!character) {
      return res.status(404).json({ error: 'Character not found' });
    }

    const userId = req.user.id;
    const isOwner = character.playerId.toString() === userId;
    
    let isDM = false;
    if (character.campaignId) {
      const Campaign = mongoose.model('Campaign');
      const campaign = await Campaign.findById(character.campaignId);
      isDM = campaign && campaign.dmId.toString() === userId;
    }

    if (!isOwner && !isDM) {
      return res.status(403).json({ error: 'Access denied' });
    }

    const { hitPointIncrease, newFeatures, newSpells } = req.body;

    character.level += 1;
    character.hitPoints.maximum += hitPointIncrease || 0;
    character.hitPoints.current += hitPointIncrease || 0;
    
    // Update proficiency bonus
    character.proficiencyBonus = Math.ceil(character.level / 4) + 1;

    // Add new features if provided
    if (newFeatures && newFeatures.length > 0) {
      character.features.push(...newFeatures);
    }

    // Add new spells if provided
    if (newSpells && newSpells.length > 0) {
      character.spellcasting.spells.push(...newSpells);
    }

    await character.save();

    const { logger } = req.app.locals.services;
    logger.info(`Character ${character.name} leveled up to ${character.level}`);

    res.json(character);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// POST /api/characters/:id/damage - Apply damage to character
router.post('/:id/damage', async (req, res) => {
  try {
    const character = await Character.findById(req.params.id);
    
    if (!character) {
      return res.status(404).json({ error: 'Character not found' });
    }

    // DM or character owner can apply damage
    const userId = req.user.id;
    const isOwner = character.playerId.toString() === userId;
    
    let isDM = false;
    if (character.campaignId) {
      const Campaign = mongoose.model('Campaign');
      const campaign = await Campaign.findById(character.campaignId);
      isDM = campaign && campaign.dmId.toString() === userId;
    }

    if (!isOwner && !isDM) {
      return res.status(403).json({ error: 'Access denied' });
    }

    const { damage, type = 'damage' } = req.body;

    if (type === 'damage') {
      // Apply damage (reduce temp HP first, then regular HP)
      let remainingDamage = damage;
      
      if (character.hitPoints.temporary > 0) {
        const tempReduction = Math.min(character.hitPoints.temporary, remainingDamage);
        character.hitPoints.temporary -= tempReduction;
        remainingDamage -= tempReduction;
      }
      
      if (remainingDamage > 0) {
        character.hitPoints.current = Math.max(0, character.hitPoints.current - remainingDamage);
      }
      
      character.stats.totalDamageTaken += damage;
    } else if (type === 'healing') {
      // Apply healing
      character.hitPoints.current = Math.min(
        character.hitPoints.maximum,
        character.hitPoints.current + damage
      );
      character.stats.totalHealingDone += damage;
    } else if (type === 'temp_hp') {
      // Set temporary hit points (don't stack)
      character.hitPoints.temporary = Math.max(character.hitPoints.temporary, damage);
    }

    await character.save();
    res.json({ 
      hitPoints: character.hitPoints,
      message: `Applied ${damage} ${type} to ${character.name}`
    });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// POST /api/characters/:id/rest - Take rest (short or long)
router.post('/:id/rest', async (req, res) => {
  try {
    const character = await Character.findById(req.params.id);
    
    if (!character) {
      return res.status(404).json({ error: 'Character not found' });
    }

    const userId = req.user.id;
    const isOwner = character.playerId.toString() === userId;
    
    let isDM = false;
    if (character.campaignId) {
      const Campaign = mongoose.model('Campaign');
      const campaign = await Campaign.findById(character.campaignId);
      isDM = campaign && campaign.dmId.toString() === userId;
    }

    if (!isOwner && !isDM) {
      return res.status(403).json({ error: 'Access denied' });
    }

    const { type = 'short', hitDiceUsed = 0 } = req.body;

    if (type === 'short') {
      // Short rest: recover some HP using hit dice, reset some features
      if (hitDiceUsed > 0) {
        const constitution = character.abilityScores.constitution;
        const constitutionModifier = Math.floor((constitution - 10) / 2);
        const hpRecovered = hitDiceUsed * (6 + constitutionModifier); // Assuming d6 hit dice
        
        character.hitPoints.current = Math.min(
          character.hitPoints.maximum,
          character.hitPoints.current + hpRecovered
        );
      }
      
      // Reset short rest features
      character.features.forEach(feature => {
        if (feature.uses && feature.uses.type === 'per_rest') {
          feature.uses.current = feature.uses.maximum;
        }
      });
    } else if (type === 'long') {
      // Long rest: full HP recovery, reset all features and spell slots
      character.hitPoints.current = character.hitPoints.maximum;
      character.hitPoints.temporary = 0;
      
      // Reset all features
      character.features.forEach(feature => {
        if (feature.uses) {
          feature.uses.current = feature.uses.maximum;
        }
      });
      
      // Reset spell slots
      character.spellcasting.spellSlots.forEach(slot => {
        slot.used = 0;
      });
      
      // Remove conditions that end on long rest
      character.conditions = character.conditions.filter(
        condition => !['exhaustion', 'poisoned'].includes(condition.name)
      );
    }

    await character.save();
    res.json({ 
      message: `${character.name} took a ${type} rest`,
      hitPoints: character.hitPoints
    });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// POST /api/characters/:id/import - Import character from external source
router.post('/:id/import', async (req, res) => {
  try {
    const { platform, data } = req.body;
    
    let characterData;
    
    switch (platform) {
      case 'dnd_beyond':
        characterData = await importFromDnDBeyond(data);
        break;
      case 'roll20':
        characterData = await importFromRoll20(data);
        break;
      case 'foundry':
        characterData = await importFromFoundry(data);
        break;
      default:
        return res.status(400).json({ error: 'Unsupported import platform' });
    }

    characterData.playerId = req.user.id;
    characterData.source = {
      platform,
      importId: data.id || data._id,
      lastSync: new Date()
    };

    const character = new Character(characterData);
    await character.save();

    await character.populate([
      { path: 'playerId', select: 'username avatar' },
      { path: 'campaignId', select: 'name dmId' }
    ]);

    res.status(201).json(character);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// GET /api/characters/:id/export - Export character
router.get('/:id/export', async (req, res) => {
  try {
    const character = await Character.findById(req.params.id)
      .populate('playerId', 'username avatar')
      .populate('campaignId', 'name');
    
    if (!character) {
      return res.status(404).json({ error: 'Character not found' });
    }

    // Check permissions
    const userId = req.user.id;
    const isOwner = character.playerId._id.toString() === userId;
    
    if (!isOwner) {
      return res.status(403).json({ error: 'Access denied' });
    }

    const { format = 'json' } = req.query;

    if (format === 'pdf') {
      // Use backup service to generate PDF
      const { backup } = req.app.locals.services;
      const pdf = await backup.exportCharacterToPDF(character);
      
      res.setHeader('Content-Type', 'application/pdf');
      res.setHeader('Content-Disposition', `attachment; filename="${character.name}.pdf"`);
      res.send(pdf.buffer);
    } else {
      // JSON export
      const exportData = {
        character: character.toObject(),
        exported_at: new Date().toISOString(),
        format: 'dmlog_character_v2',
        version: '2.0.0'
      };

      res.setHeader('Content-Type', 'application/json');
      res.setHeader('Content-Disposition', `attachment; filename="${character.name}.json"`);
      res.json(exportData);
    }
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Helper functions for imports (simplified implementations)
async function importFromDnDBeyond(data) {
  // Transform D&D Beyond data to our schema
  return {
    name: data.name,
    race: data.race?.fullName,
    class: data.classes?.[0]?.definition?.name,
    level: data.classes?.[0]?.level || 1,
    background: data.background?.definition?.name,
    abilityScores: {
      strength: data.stats?.find(s => s.id === 1)?.value || 10,
      dexterity: data.stats?.find(s => s.id === 2)?.value || 10,
      constitution: data.stats?.find(s => s.id === 3)?.value || 10,
      intelligence: data.stats?.find(s => s.id === 4)?.value || 10,
      wisdom: data.stats?.find(s => s.id === 5)?.value || 10,
      charisma: data.stats?.find(s => s.id === 6)?.value || 10,
    },
    hitPoints: {
      current: data.baseHitPoints || 8,
      maximum: data.baseHitPoints || 8
    }
  };
}

async function importFromRoll20(data) {
  // Transform Roll20 data to our schema
  return {
    name: data.name,
    race: data.race,
    class: data.class,
    level: parseInt(data.level) || 1,
    abilityScores: {
      strength: parseInt(data.strength) || 10,
      dexterity: parseInt(data.dexterity) || 10,
      constitution: parseInt(data.constitution) || 10,
      intelligence: parseInt(data.intelligence) || 10,
      wisdom: parseInt(data.wisdom) || 10,
      charisma: parseInt(data.charisma) || 10,
    }
  };
}

async function importFromFoundry(data) {
  // Transform Foundry VTT data to our schema
  return {
    name: data.name,
    race: data.data?.details?.race,
    class: data.data?.details?.class,
    level: data.data?.details?.level || 1,
    abilityScores: {
      strength: data.data?.abilities?.str?.value || 10,
      dexterity: data.data?.abilities?.dex?.value || 10,
      constitution: data.data?.abilities?.con?.value || 10,
      intelligence: data.data?.abilities?.int?.value || 10,
      wisdom: data.data?.abilities?.wis?.value || 10,
      charisma: data.data?.abilities?.cha?.value || 10,
    },
    hitPoints: {
      current: data.data?.attributes?.hp?.value || 8,
      maximum: data.data?.attributes?.hp?.max || 8
    }
  };
}

export default router;