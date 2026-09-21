import { DiceRoll } from '@/types';

// Dice notation parser and roller
export class DiceEngine {
  private static parseNotation(notation: string): { count: number; sides: number; modifier: number } {
    // Parse notation like "1d20+5", "2d6-1", "1d12"
    const match = notation.match(/(\d+)?d(\d+)([+-]\d+)?/i);
    if (!match) {
      throw new Error(`Invalid dice notation: ${notation}`);
    }

    const count = parseInt(match[1] || '1');
    const sides = parseInt(match[2]);
    const modifier = parseInt(match[3] || '0');

    if (count < 1 || sides < 2) {
      throw new Error(`Invalid dice parameters: ${count}d${sides}`);
    }

    return { count, sides, modifier };
  }

  private static rollDie(sides: number): number {
    return Math.floor(Math.random() * sides) + 1;
  }

  public static roll(
    notation: string, 
    options: { advantage?: boolean; disadvantage?: boolean } = {}
  ): Omit<DiceRoll, 'id' | 'timestamp' | 'type'> {
    const { count, sides, modifier } = this.parseNotation(notation);
    let results: number[] = [];
    let modifiers: number[] = [];

    // Handle advantage/disadvantage for d20 rolls
    if (options.advantage && sides === 20 && count === 1) {
      const roll1 = this.rollDie(sides);
      const roll2 = this.rollDie(sides);
      results = [Math.max(roll1, roll2)];
      // Store both rolls for display
      results.push(roll1, roll2);
    } else if (options.disadvantage && sides === 20 && count === 1) {
      const roll1 = this.rollDie(sides);
      const roll2 = this.rollDie(sides);
      results = [Math.min(roll1, roll2)];
      // Store both rolls for display
      results.push(roll1, roll2);
    } else {
      // Normal rolling
      for (let i = 0; i < count; i++) {
        results.push(this.rollDie(sides));
      }
    }

    if (modifier !== 0) {
      modifiers.push(modifier);
    }

    const total = results.slice(0, count).reduce((sum, result) => sum + result, 0) + modifier;
    const critical = sides === 20 && count === 1 && results[0] === 20;

    return {
      notation,
      results,
      modifiers,
      total,
      advantage: options.advantage,
      disadvantage: options.disadvantage,
      critical
    };
  }

  public static rollMultiple(notations: string[]): Omit<DiceRoll, 'id' | 'timestamp' | 'type'> {
    let allResults: number[] = [];
    let allModifiers: number[] = [];
    let totalSum = 0;
    let combinedNotation = '';

    notations.forEach((notation, index) => {
      const result = this.roll(notation);
      allResults = allResults.concat(result.results);
      allModifiers = allModifiers.concat(result.modifiers);
      totalSum += result.total;
      combinedNotation += (index > 0 ? ' + ' : '') + notation;
    });

    return {
      notation: combinedNotation,
      results: allResults,
      modifiers: allModifiers,
      total: totalSum
    };
  }

  // Quick roll methods for common dice
  public static d4(count = 1, modifier = 0): Omit<DiceRoll, 'id' | 'timestamp' | 'type'> {
    return this.roll(`${count}d4${modifier >= 0 ? '+' : ''}${modifier}`);
  }

  public static d6(count = 1, modifier = 0): Omit<DiceRoll, 'id' | 'timestamp' | 'type'> {
    return this.roll(`${count}d6${modifier >= 0 ? '+' : ''}${modifier}`);
  }

  public static d8(count = 1, modifier = 0): Omit<DiceRoll, 'id' | 'timestamp' | 'type'> {
    return this.roll(`${count}d8${modifier >= 0 ? '+' : ''}${modifier}`);
  }

  public static d10(count = 1, modifier = 0): Omit<DiceRoll, 'id' | 'timestamp' | 'type'> {
    return this.roll(`${count}d10${modifier >= 0 ? '+' : ''}${modifier}`);
  }

  public static d12(count = 1, modifier = 0): Omit<DiceRoll, 'id' | 'timestamp' | 'type'> {
    return this.roll(`${count}d12${modifier >= 0 ? '+' : ''}${modifier}`);
  }

  public static d20(count = 1, modifier = 0, options?: { advantage?: boolean; disadvantage?: boolean }): Omit<DiceRoll, 'id' | 'timestamp' | 'type'> {
    return this.roll(`${count}d20${modifier >= 0 ? '+' : ''}${modifier}`, options);
  }

  public static d100(count = 1, modifier = 0): Omit<DiceRoll, 'id' | 'timestamp' | 'type'> {
    return this.roll(`${count}d100${modifier >= 0 ? '+' : ''}${modifier}`);
  }
}

// Common D&D roll types
export const rollAbilityCheck = (ability: number, proficiency?: number, advantage?: boolean): Omit<DiceRoll, 'id' | 'timestamp'> => {
  const modifier = Math.floor((ability - 10) / 2) + (proficiency || 0);
  const result = DiceEngine.d20(1, modifier, { advantage });
  return {
    ...result,
    type: 'ability'
  };
};

export const rollSavingThrow = (ability: number, proficient: boolean, proficiencyBonus: number, advantage?: boolean): Omit<DiceRoll, 'id' | 'timestamp'> => {
  const modifier = Math.floor((ability - 10) / 2) + (proficient ? proficiencyBonus : 0);
  const result = DiceEngine.d20(1, modifier, { advantage });
  return {
    ...result,
    type: 'saving-throw'
  };
};

export const rollAttack = (ability: number, proficiencyBonus: number, weaponBonus = 0, advantage?: boolean): Omit<DiceRoll, 'id' | 'timestamp'> => {
  const modifier = Math.floor((ability - 10) / 2) + proficiencyBonus + weaponBonus;
  const result = DiceEngine.d20(1, modifier, { advantage });
  return {
    ...result,
    type: 'attack'
  };
};

export const rollDamage = (damageDice: string, ability?: number, weaponBonus = 0): Omit<DiceRoll, 'id' | 'timestamp'> => {
  const abilityMod = ability ? Math.floor((ability - 10) / 2) : 0;
  const modifier = abilityMod + weaponBonus;
  const notation = modifier !== 0 ? `${damageDice}${modifier >= 0 ? '+' : ''}${modifier}` : damageDice;
  
  const result = DiceEngine.roll(notation);
  return {
    ...result,
    type: 'damage'
  };
};

export const rollSkillCheck = (ability: number, proficient: boolean, expertise: boolean, proficiencyBonus: number, advantage?: boolean): Omit<DiceRoll, 'id' | 'timestamp'> => {
  const abilityMod = Math.floor((ability - 10) / 2);
  let skillBonus = abilityMod;
  
  if (proficient) {
    skillBonus += proficiencyBonus;
  }
  if (expertise) {
    skillBonus += proficiencyBonus;
  }
  
  const result = DiceEngine.d20(1, skillBonus, { advantage });
  return {
    ...result,
    type: 'skill'
  };
};

export const rollInitiative = (dexterity: number, bonus = 0): Omit<DiceRoll, 'id' | 'timestamp'> => {
  const modifier = Math.floor((dexterity - 10) / 2) + bonus;
  const result = DiceEngine.d20(1, modifier);
  return {
    ...result,
    type: 'ability'
  };
};

// Utility functions
export const getAbilityModifier = (score: number): number => {
  return Math.floor((score - 10) / 2);
};

export const formatModifier = (modifier: number): string => {
  return modifier >= 0 ? `+${modifier}` : `${modifier}`;
};

export const formatDiceResult = (roll: DiceRoll): string => {
  let result = `${roll.notation} = ${roll.total}`;
  
  if (roll.results.length > 1 || roll.modifiers.length > 0) {
    const parts: string[] = [];
    
    if (roll.results.length > 0) {
      parts.push(`[${roll.results.join(', ')}]`);
    }
    
    if (roll.modifiers.length > 0) {
      roll.modifiers.forEach(mod => {
        parts.push(mod >= 0 ? `+${mod}` : `${mod}`);
      });
    }
    
    result = `${roll.notation} = ${parts.join(' ')} = ${roll.total}`;
  }
  
  if (roll.advantage) {
    result += ' (Advantage)';
  } else if (roll.disadvantage) {
    result += ' (Disadvantage)';
  }
  
  if (roll.critical) {
    result += ' (Critical!)';
  }
  
  return result;
};