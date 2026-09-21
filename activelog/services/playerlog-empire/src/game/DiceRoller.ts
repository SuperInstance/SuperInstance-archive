/**
 * Dice Rolling System with Animation and Effects
 * Supports various dice configurations and fair randomization
 */

export interface DiceRoll {
  dice: number[];
  total: number;
  timestamp: number;
  isDoubles: boolean;
  consecutiveDoubles: number;
}

export interface DiceAnimation {
  duration: number;
  frames: number[][];
  finalResult: number[];
}

export class DiceRoller {
  private rollHistory: DiceRoll[] = [];
  private consecutiveDoubles = 0;
  private lastRollTime = 0;

  /**
   * Roll specified number of dice
   */
  roll(numberOfDice: number = 2, sides: number = 6): number[] {
    const dice: number[] = [];
    
    for (let i = 0; i < numberOfDice; i++) {
      dice.push(this.rollSingleDie(sides));
    }

    const total = dice.reduce((sum, die) => sum + die, 0);
    const isDoubles = numberOfDice === 2 && dice[0] === dice[1];
    
    if (isDoubles) {
      this.consecutiveDoubles++;
    } else {
      this.consecutiveDoubles = 0;
    }

    const roll: DiceRoll = {
      dice,
      total,
      timestamp: Date.now(),
      isDoubles,
      consecutiveDoubles: this.consecutiveDoubles
    };

    this.rollHistory.push(roll);
    this.lastRollTime = Date.now();

    // Keep only last 100 rolls
    if (this.rollHistory.length > 100) {
      this.rollHistory = this.rollHistory.slice(-100);
    }

    return dice;
  }

  /**
   * Roll single die with cryptographically secure randomness
   */
  private rollSingleDie(sides: number): number {
    // Use crypto.randomBytes for better randomness if available
    if (typeof window !== 'undefined' && window.crypto && window.crypto.getRandomValues) {
      const array = new Uint32Array(1);
      window.crypto.getRandomValues(array);
      return (array[0] % sides) + 1;
    } else if (typeof require !== 'undefined') {
      const crypto = require('crypto');
      const randomBytes = crypto.randomBytes(4);
      const randomInt = randomBytes.readUInt32BE(0);
      return (randomInt % sides) + 1;
    } else {
      // Fallback to Math.random with improved distribution
      return Math.floor(Math.random() * sides) + 1;
    }
  }

  /**
   * Generate dice animation frames
   */
  generateAnimation(finalResult: number[], animationDuration: number = 1000): DiceAnimation {
    const frameRate = 60; // 60fps
    const totalFrames = Math.floor(animationDuration / (1000 / frameRate));
    const frames: number[][] = [];

    for (let frame = 0; frame < totalFrames; frame++) {
      const frameRoll: number[] = [];
      
      for (let i = 0; i < finalResult.length; i++) {
        // More random movement at beginning, settle to final result at end
        const progress = frame / totalFrames;
        const randomness = Math.max(0, 1 - progress * 2); // Reduce randomness over time
        
        if (progress >= 0.8) {
          // Final 20% of animation shows actual result
          frameRoll.push(finalResult[i]);
        } else if (Math.random() < randomness) {
          // Random face during animation
          frameRoll.push(Math.floor(Math.random() * 6) + 1);
        } else {
          // Increasingly show final result
          frameRoll.push(finalResult[i]);
        }
      }
      
      frames.push(frameRoll);
    }

    return {
      duration: animationDuration,
      frames,
      finalResult
    };
  }

  /**
   * Check if roll appears to be fair (statistical analysis)
   */
  analyzeRollFairness(): {
    totalRolls: number;
    distribution: Record<number, number>;
    expectedFrequency: number;
    chiSquare: number;
    isFair: boolean;
    doublesFrequency: number;
    expectedDoublesFrequency: number;
  } {
    if (this.rollHistory.length === 0) {
      return {
        totalRolls: 0,
        distribution: {},
        expectedFrequency: 0,
        chiSquare: 0,
        isFair: true,
        doublesFrequency: 0,
        expectedDoublesFrequency: 0
      };
    }

    const distribution: Record<number, number> = {};
    let doublesCount = 0;

    // Analyze individual die faces (assuming 6-sided dice)
    this.rollHistory.forEach(roll => {
      roll.dice.forEach(die => {
        distribution[die] = (distribution[die] || 0) + 1;
      });
      
      if (roll.isDoubles) {
        doublesCount++;
      }
    });

    const totalDice = this.rollHistory.reduce((sum, roll) => sum + roll.dice.length, 0);
    const expectedFrequency = totalDice / 6;
    
    // Calculate chi-square statistic
    let chiSquare = 0;
    for (let i = 1; i <= 6; i++) {
      const observed = distribution[i] || 0;
      const expected = expectedFrequency;
      chiSquare += Math.pow(observed - expected, 2) / expected;
    }

    // Chi-square critical value for 5 degrees of freedom at 95% confidence is ~11.07
    const isFair = chiSquare < 11.07;

    const doublesFrequency = doublesCount / this.rollHistory.length;
    const expectedDoublesFrequency = 1 / 6; // 1/6 chance for doubles

    return {
      totalRolls: this.rollHistory.length,
      distribution,
      expectedFrequency,
      chiSquare,
      isFair,
      doublesFrequency,
      expectedDoublesFrequency
    };
  }

  /**
   * Get roll statistics
   */
  getStatistics(): {
    totalRolls: number;
    averageRoll: number;
    highestRoll: number;
    lowestRoll: number;
    mostCommonTotal: number;
    doublesPercentage: number;
    maxConsecutiveDoubles: number;
    recentRolls: DiceRoll[];
  } {
    if (this.rollHistory.length === 0) {
      return {
        totalRolls: 0,
        averageRoll: 0,
        highestRoll: 0,
        lowestRoll: 0,
        mostCommonTotal: 0,
        doublesPercentage: 0,
        maxConsecutiveDoubles: 0,
        recentRolls: []
      };
    }

    const totals = this.rollHistory.map(roll => roll.total);
    const doublesCount = this.rollHistory.filter(roll => roll.isDoubles).length;
    const maxConsecutiveDoubles = Math.max(...this.rollHistory.map(roll => roll.consecutiveDoubles));

    // Find most common total
    const totalCounts: Record<number, number> = {};
    totals.forEach(total => {
      totalCounts[total] = (totalCounts[total] || 0) + 1;
    });
    
    const mostCommonTotal = Object.entries(totalCounts)
      .reduce((max, [total, count]) => 
        count > totalCounts[max] ? parseInt(total) : max, 
        parseInt(Object.keys(totalCounts)[0])
      );

    return {
      totalRolls: this.rollHistory.length,
      averageRoll: totals.reduce((sum, total) => sum + total, 0) / totals.length,
      highestRoll: Math.max(...totals),
      lowestRoll: Math.min(...totals),
      mostCommonTotal,
      doublesPercentage: (doublesCount / this.rollHistory.length) * 100,
      maxConsecutiveDoubles,
      recentRolls: this.rollHistory.slice(-10)
    };
  }

  /**
   * Weighted dice roll (for special events)
   */
  rollWeighted(weights: number[], numberOfDice: number = 1): number[] {
    if (weights.length !== 6) {
      throw new Error('Weights must be provided for all 6 faces');
    }

    const totalWeight = weights.reduce((sum, weight) => sum + weight, 0);
    const dice: number[] = [];

    for (let d = 0; d < numberOfDice; d++) {
      const random = Math.random() * totalWeight;
      let cumulativeWeight = 0;
      
      for (let i = 0; i < weights.length; i++) {
        cumulativeWeight += weights[i];
        if (random <= cumulativeWeight) {
          dice.push(i + 1);
          break;
        }
      }
    }

    return dice;
  }

  /**
   * Speed rolling for fast games
   */
  speedRoll(numberOfRolls: number, numberOfDice: number = 2): DiceRoll[] {
    const rolls: DiceRoll[] = [];
    
    for (let i = 0; i < numberOfRolls; i++) {
      const dice = this.roll(numberOfDice);
      rolls.push(this.rollHistory[this.rollHistory.length - 1]);
    }

    return rolls;
  }

  /**
   * Simulate probability of outcomes
   */
  simulateOutcomes(numberOfDice: number, trials: number = 10000): Record<number, number> {
    const outcomes: Record<number, number> = {};
    
    for (let trial = 0; trial < trials; trial++) {
      const total = this.roll(numberOfDice).reduce((sum, die) => sum + die, 0);
      outcomes[total] = (outcomes[total] || 0) + 1;
    }

    // Convert to percentages
    Object.keys(outcomes).forEach(total => {
      outcomes[parseInt(total)] = (outcomes[parseInt(total)] / trials) * 100;
    });

    return outcomes;
  }

  /**
   * Check for loaded dice (statistical test)
   */
  checkForLoadedDice(): {
    suspicious: boolean;
    reason: string;
    confidence: number;
    recommendations: string[];
  } {
    if (this.rollHistory.length < 100) {
      return {
        suspicious: false,
        reason: 'Insufficient data for analysis',
        confidence: 0,
        recommendations: ['Need at least 100 rolls for statistical analysis']
      };
    }

    const analysis = this.analyzeRollFairness();
    const stats = this.getStatistics();
    const issues: string[] = [];
    let suspicionLevel = 0;

    // Check chi-square test
    if (!analysis.isFair) {
      issues.push(`Chi-square test failed (${analysis.chiSquare.toFixed(2)} > 11.07)`);
      suspicionLevel += 30;
    }

    // Check doubles frequency
    const doublesDeviation = Math.abs(analysis.doublesFrequency - analysis.expectedDoublesFrequency);
    if (doublesDeviation > 0.1) { // More than 10% deviation
      issues.push(`Unusual doubles frequency: ${(analysis.doublesFrequency * 100).toFixed(1)}% (expected ~16.7%)`);
      suspicionLevel += 25;
    }

    // Check for excessive consecutive doubles
    if (stats.maxConsecutiveDoubles > 5) {
      issues.push(`Excessive consecutive doubles: ${stats.maxConsecutiveDoubles}`);
      suspicionLevel += 20;
    }

    // Check distribution uniformity
    const expectedCount = analysis.totalRolls / 6;
    const maxDeviation = Math.max(...Object.values(analysis.distribution).map(count => 
      Math.abs(count - expectedCount) / expectedCount
    ));

    if (maxDeviation > 0.2) { // More than 20% deviation
      issues.push(`Non-uniform distribution detected (max deviation: ${(maxDeviation * 100).toFixed(1)}%)`);
      suspicionLevel += 25;
    }

    const recommendations: string[] = [];
    if (suspicionLevel > 50) {
      recommendations.push('Consider resetting the random number generator');
      recommendations.push('Check for patterns in recent rolls');
      recommendations.push('Increase sample size for more reliable analysis');
    }

    return {
      suspicious: suspicionLevel > 50,
      reason: issues.join('; '),
      confidence: Math.min(suspicionLevel, 100),
      recommendations
    };
  }

  /**
   * Reset roll history
   */
  reset(): void {
    this.rollHistory = [];
    this.consecutiveDoubles = 0;
    this.lastRollTime = 0;
  }

  /**
   * Get recent roll history
   */
  getRollHistory(limit: number = 10): DiceRoll[] {
    return this.rollHistory.slice(-limit);
  }

  /**
   * Export roll data for analysis
   */
  exportData(): {
    history: DiceRoll[];
    statistics: ReturnType<DiceRoller['getStatistics']>;
    fairnessAnalysis: ReturnType<DiceRoller['analyzeRollFairness']>;
    exportedAt: number;
  } {
    return {
      history: this.rollHistory,
      statistics: this.getStatistics(),
      fairnessAnalysis: this.analyzeRollFairness(),
      exportedAt: Date.now()
    };
  }
}