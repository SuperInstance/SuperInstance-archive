// D&D 5E Quick Reference Rules Data

export interface RuleSection {
  id: string;
  title: string;
  content: string;
  tags: string[];
  category: 'combat' | 'spells' | 'conditions' | 'movement' | 'general' | 'abilities';
}

export interface RuleCategory {
  id: string;
  title: string;
  emoji: string;
  description: string;
  color: string;
}

export const ruleCategories: RuleCategory[] = [
  {
    id: 'combat',
    title: 'Combat',
    emoji: '⚔️',
    description: 'Combat actions, attacks, and battle rules',
    color: '#e74c3c'
  },
  {
    id: 'spells',
    title: 'Spellcasting',
    emoji: '✨',
    description: 'Spell components, casting, and magic rules',
    color: '#9b59b6'
  },
  {
    id: 'conditions',
    title: 'Conditions',
    emoji: '🎭',
    description: 'Status effects and their game effects',
    color: '#f39c12'
  },
  {
    id: 'movement',
    title: 'Movement',
    emoji: '🏃',
    description: 'Movement speeds, terrain, and travel',
    color: '#3498db'
  },
  {
    id: 'abilities',
    title: 'Ability Checks',
    emoji: '🎲',
    description: 'Skills, saves, and ability check rules',
    color: '#2ecc71'
  },
  {
    id: 'general',
    title: 'General Rules',
    emoji: '📖',
    description: 'Core mechanics and general gameplay',
    color: '#34495e'
  }
];

export const rulesData: RuleSection[] = [
  // Combat Rules
  {
    id: 'actions-in-combat',
    title: 'Actions in Combat',
    category: 'combat',
    tags: ['action', 'combat', 'turn'],
    content: `**On Your Turn, you can:**

**Action:** Attack, Cast a Spell, Dash, Disengage, Dodge, Help, Hide, Ready, Search, Use an Object

**Move:** Up to your speed

**Bonus Action:** Only if a spell or feature grants it

**Free Actions:** Draw/sheathe weapon, open door, brief communication

**Reaction:** One per round, triggered by specific conditions`
  },
  {
    id: 'attack-rolls',
    title: 'Attack Rolls',
    category: 'combat',
    tags: ['attack', 'combat', 'dice'],
    content: `**Making an Attack Roll:**

1. Roll 1d20
2. Add ability modifier (Str for melee, Dex for ranged)
3. Add proficiency bonus (if proficient)
4. Add other modifiers

**Hit if:** Attack roll ≥ target's Armor Class

**Critical Hit:** Natural 20 - roll damage dice twice

**Critical Miss:** Natural 1 - automatic miss`
  },
  {
    id: 'damage-resistance',
    title: 'Damage & Resistance',
    category: 'combat',
    tags: ['damage', 'resistance', 'vulnerability'],
    content: `**Damage Types:**
Bludgeoning, Piercing, Slashing, Acid, Cold, Fire, Force, Lightning, Necrotic, Poison, Psychic, Radiant, Thunder

**Resistance:** Take half damage (round down)

**Vulnerability:** Take double damage

**Immunity:** Take no damage

**Temporary Hit Points:** Don't stack, use highest value`
  },
  {
    id: 'opportunity-attacks',
    title: 'Opportunity Attacks',
    category: 'combat',
    tags: ['opportunity', 'attack', 'movement', 'reaction'],
    content: `**Triggers:** When a hostile creature moves out of your reach

**Requirements:**
- Must be able to see the creature
- Must have a melee weapon
- Uses your reaction

**Avoiding:** Disengage action, teleportation, being forced to move, becoming incapacitated`
  },

  // Spellcasting Rules
  {
    id: 'spell-components',
    title: 'Spell Components',
    category: 'spells',
    tags: ['spells', 'components', 'casting'],
    content: `**Verbal (V):** Spoken incantation - can't cast if silenced

**Somatic (S):** Hand gestures - need one free hand (or hand holding focus)

**Material (M):** Physical components
- Spellcasting focus can replace most materials
- Costly materials (specified cost) must be provided
- Consumed materials are used up when cast`
  },
  {
    id: 'concentration',
    title: 'Concentration',
    category: 'spells',
    tags: ['concentration', 'spells', 'duration'],
    content: `**Concentration Rules:**

- Only one concentration spell at a time
- Lasts until duration ends, you lose concentration, or you die
- Broken by: casting another concentration spell, taking damage (make Con save), being incapacitated, dying

**Constitution Save DC:** 10 or half damage taken (whichever is higher)

**Minimum DC:** 10`
  },
  {
    id: 'spell-attack-saves',
    title: 'Spell Attacks & Saves',
    category: 'spells',
    tags: ['spells', 'attack', 'saving throw'],
    content: `**Spell Attack Bonus:**
1d20 + ability modifier + proficiency bonus

**Spell Save DC:**
8 + ability modifier + proficiency bonus

**Saving Throws:**
- Success: Usually half damage or no effect
- Failure: Full effect
- Some spells have partial effects on success`
  },

  // Conditions
  {
    id: 'blinded',
    title: 'Blinded',
    category: 'conditions',
    tags: ['condition', 'blinded', 'vision'],
    content: `**Effects:**
- Can't see, automatically fails sight-based Perception checks
- Attack rolls against you have advantage
- Your attack rolls have disadvantage`
  },
  {
    id: 'charmed',
    title: 'Charmed',
    category: 'conditions',
    tags: ['condition', 'charmed', 'social'],
    content: `**Effects:**
- Can't attack the charmer or target them with harmful abilities/spells
- Charmer has advantage on social interaction checks with you`
  },
  {
    id: 'frightened',
    title: 'Frightened',
    category: 'conditions',
    tags: ['condition', 'frightened', 'fear'],
    content: `**Effects:**
- Disadvantage on ability checks and attack rolls while source of fear is in line of sight
- Can't willingly move closer to the source of fear`
  },
  {
    id: 'grappled',
    title: 'Grappled',
    category: 'conditions',
    tags: ['condition', 'grappled', 'movement'],
    content: `**Effects:**
- Speed becomes 0
- Can't benefit from bonuses to speed
- Ends if grappler is incapacitated or moved away`
  },
  {
    id: 'paralyzed',
    title: 'Paralyzed',
    category: 'conditions',
    tags: ['condition', 'paralyzed', 'incapacitated'],
    content: `**Effects:**
- Incapacitated and can't move or speak
- Fails Strength and Dexterity saves
- Attack rolls against you have advantage
- Hits within 5 feet are automatic critical hits`
  },
  {
    id: 'poisoned',
    title: 'Poisoned',
    category: 'conditions',
    tags: ['condition', 'poisoned', 'disadvantage'],
    content: `**Effects:**
- Disadvantage on attack rolls and ability checks`
  },
  {
    id: 'prone',
    title: 'Prone',
    category: 'conditions',
    tags: ['condition', 'prone', 'movement'],
    content: `**Effects:**
- Can only crawl (costs extra movement) or stand up
- Disadvantage on attack rolls
- Attacks within 5 feet have advantage, beyond 5 feet have disadvantage`
  },
  {
    id: 'restrained',
    title: 'Restrained',
    category: 'conditions',
    tags: ['condition', 'restrained', 'movement'],
    content: `**Effects:**
- Speed becomes 0
- Disadvantage on attack rolls and Dexterity saves
- Attack rolls against you have advantage`
  },
  {
    id: 'stunned',
    title: 'Stunned',
    category: 'conditions',
    tags: ['condition', 'stunned', 'incapacitated'],
    content: `**Effects:**
- Incapacitated and can't move
- Can speak falteringly
- Fails Strength and Dexterity saves
- Attack rolls against you have advantage`
  },
  {
    id: 'unconscious',
    title: 'Unconscious',
    category: 'conditions',
    tags: ['condition', 'unconscious', 'incapacitated'],
    content: `**Effects:**
- Incapacitated, can't move or speak, unaware of surroundings
- Drops what it's holding and falls prone
- Fails Strength and Dexterity saves
- Attack rolls against you have advantage
- Hits within 5 feet are automatic critical hits`
  },

  // Movement Rules
  {
    id: 'movement-speeds',
    title: 'Movement Speeds',
    category: 'movement',
    tags: ['movement', 'speed', 'travel'],
    content: `**Base Speeds by Race:**
- Most races: 30 feet
- Dwarf, Halfling: 25 feet
- Wood Elf: 35 feet

**Movement Types:**
- **Walk:** Normal speed
- **Climb/Swim:** Half speed (unless you have climbing/swimming speed)
- **Crawl:** Half speed
- **High Jump:** 3 + Str modifier feet
- **Long Jump:** Str score feet (with 10-foot running start)`
  },
  {
    id: 'difficult-terrain',
    title: 'Difficult Terrain',
    category: 'movement',
    tags: ['terrain', 'movement', 'speed'],
    content: `**Cost:** 2 feet of movement for every 1 foot moved

**Examples:**
- Thick undergrowth
- Deep mud or snow
- Steep stairs
- Rubble
- Ice

**Note:** Multiple sources don't stack - still costs 2 feet per foot`
  },

  // Ability Checks
  {
    id: 'advantage-disadvantage',
    title: 'Advantage & Disadvantage',
    category: 'abilities',
    tags: ['advantage', 'disadvantage', 'dice'],
    content: `**Advantage:** Roll two d20s, use the higher result

**Disadvantage:** Roll two d20s, use the lower result

**Multiple Sources:** Don't stack - you either have it or you don't

**Canceling:** If you have both advantage and disadvantage, roll normally (even if you have multiple sources of each)`
  },
  {
    id: 'skill-checks',
    title: 'Skill Checks',
    category: 'abilities',
    tags: ['skills', 'ability check', 'proficiency'],
    content: `**Skill Check = 1d20 + ability modifier + proficiency bonus (if proficient)**

**Proficiency:** Add proficiency bonus to skills you're trained in

**Expertise:** Double proficiency bonus (some classes/backgrounds)

**Difficulty Classes:**
- Very Easy: DC 5
- Easy: DC 10  
- Medium: DC 15
- Hard: DC 20
- Very Hard: DC 25
- Nearly Impossible: DC 30`
  },
  {
    id: 'saving-throws',
    title: 'Saving Throws',
    category: 'abilities',
    tags: ['saving throws', 'saves', 'abilities'],
    content: `**Saving Throw = 1d20 + ability modifier + proficiency bonus (if proficient)**

**Save Types:**
- **Strength:** Resist being moved or restrained
- **Dexterity:** Avoid area effects, act quickly
- **Constitution:** Resist poison, disease, death
- **Intelligence:** Resist mental attacks, illusions
- **Wisdom:** Resist being charmed, frightened
- **Charisma:** Resist banishment, possession`
  },

  // General Rules
  {
    id: 'resting',
    title: 'Resting',
    category: 'general',
    tags: ['rest', 'healing', 'recovery'],
    content: `**Short Rest:** 1+ hours of light activity
- Spend Hit Dice to heal
- Regain some class features
- Once per 24 hours: gain benefits

**Long Rest:** 8 hours (6 hours sleep + 2 hours light activity)
- Regain all HP and half your total Hit Dice
- Regain all spell slots and most features
- Remove one level of exhaustion
- Once per 24 hours: gain benefits`
  },
  {
    id: 'death-saving-throws',
    title: 'Death Saving Throws',
    category: 'general',
    tags: ['death', 'dying', 'saving throws'],
    content: `**When at 0 HP and not killed outright:**

Roll 1d20 at start of each turn:
- **10+:** Success
- **9 or less:** Failure
- **Natural 20:** Regain 1 HP
- **Natural 1:** Counts as 2 failures

**3 Successes:** Stabilized (unconscious but alive)
**3 Failures:** Dead

**Taking damage:** 1 failure (2 failures if critical hit)
**Healing:** Immediately conscious with healed HP amount`
  },
  {
    id: 'inspiration',
    title: 'Inspiration',
    category: 'general',
    tags: ['inspiration', 'advantage', 'roleplay'],
    content: `**Gaining Inspiration:**
- DM awards for exceptional roleplay
- Playing to character traits, ideals, bonds, flaws
- Can only have one inspiration at a time

**Using Inspiration:**
- Spend to gain advantage on one attack roll, saving throw, or ability check
- Can be used after rolling but before knowing the result`
  },
  {
    id: 'cover',
    title: 'Cover',
    category: 'general',
    tags: ['cover', 'AC', 'protection'],
    content: `**Half Cover:** +2 AC and Dex saves
- Target has cover but attacker can still see them
- Low wall, furniture, creatures

**Three-Quarters Cover:** +5 AC and Dex saves  
- Partially concealed by cover
- Arrow slit, thick tree trunk

**Total Cover:** Can't be targeted
- Completely concealed by cover`
  }
];

export const searchRules = (query: string, category?: string): RuleSection[] => {
  const lowerQuery = query.toLowerCase();
  
  return rulesData.filter(rule => {
    const matchesCategory = !category || rule.category === category;
    const matchesQuery = !query || 
      rule.title.toLowerCase().includes(lowerQuery) ||
      rule.content.toLowerCase().includes(lowerQuery) ||
      rule.tags.some(tag => tag.toLowerCase().includes(lowerQuery));
    
    return matchesCategory && matchesQuery;
  });
};

export const getRulesByCategory = (category: string): RuleSection[] => {
  return rulesData.filter(rule => rule.category === category);
};