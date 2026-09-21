import { EventEmitter } from 'events';
import { ViewerDiceRoll, DiceResult, ViewerEngagement, InteractionSettings } from '../types';
import * as tmi from 'tmi.js';

export class ViewerDiceSystem extends EventEmitter {
  private twitchClient: tmi.Client | null = null;
  private settings: InteractionSettings;
  private rollCooldowns: Map<string, number> = new Map();
  private userRollCounts: Map<string, number> = new Map();
  private dailyResetTime: Date = new Date();
  private validDiceTypes = ['d4', 'd6', 'd8', 'd10', 'd12', 'd20', 'd100'];
  
  constructor(settings: InteractionSettings) {
    super();
    this.settings = settings;
    this.setupDailyReset();
  }

  public async initialize(twitchConfig: any): Promise<void> {
    this.twitchClient = new tmi.Client({
      options: { debug: false },
      connection: {
        reconnect: true,
        secure: true
      },
      identity: {
        username: twitchConfig.botUsername,
        password: twitchConfig.oauthToken
      },
      channels: [twitchConfig.channel]
    });

    this.twitchClient.on('message', this.handleChatMessage.bind(this));
    this.twitchClient.on('connected', this.onTwitchConnected.bind(this));
    
    await this.twitchClient.connect();
  }

  private onTwitchConnected(address: string, port: number): void {
    console.log(`✅ Connected to Twitch chat at ${address}:${port}`);
    this.emit('connected');
  }

  private async handleChatMessage(channel: string, tags: tmi.ChatUserstate, message: string, self: boolean): Promise<void> {
    if (self || !this.settings.viewerDice.enabled) return;

    const username = tags.username || 'anonymous';
    const userId = tags['user-id'] || username;

    // Check for dice roll commands
    const diceMatch = this.parseDiceCommand(message);
    if (diceMatch) {
      await this.processDiceRoll(userId, username, diceMatch, tags);
    }
  }

  private parseDiceCommand(message: string): { notation: string; context?: string } | null {
    // Support various dice roll formats
    const patterns = [
      /^!roll\s+([0-9]*d[0-9]+(?:[+\-][0-9]+)?)\s*(.*)?$/i,
      /^!r\s+([0-9]*d[0-9]+(?:[+\-][0-9]+)?)\s*(.*)?$/i,
      /^\$([0-9]*d[0-9]+(?:[+\-][0-9]+)?)\s*(.*)?$/i,
      /^\/roll\s+([0-9]*d[0-9]+(?:[+\-][0-9]+)?)\s*(.*)?$/i,
      /^roll\s+([0-9]*d[0-9]+(?:[+\-][0-9]+)?)\s*(.*)?$/i,
    ];

    for (const pattern of patterns) {
      const match = message.match(pattern);
      if (match) {
        return {
          notation: match[1],
          context: match[2]?.trim() || undefined
        };
      }
    }

    return null;
  }

  private async processDiceRoll(userId: string, username: string, diceMatch: { notation: string; context?: string }, tags: tmi.ChatUserstate): Promise<void> {
    // Check cooldown
    if (this.isOnCooldown(userId)) {
      const remaining = this.getRemainingCooldown(userId);
      await this.sendChatResponse(`@${username}, you must wait ${Math.ceil(remaining / 1000)} more seconds before rolling again.`);
      return;
    }

    // Check daily roll limit
    if (this.hasExceededDailyLimit(userId)) {
      await this.sendChatResponse(`@${username}, you've reached your daily roll limit of ${this.settings.viewerDice.maxRolls}.`);
      return;
    }

    // Validate dice notation
    if (!this.isValidDiceNotation(diceMatch.notation)) {
      await this.sendChatResponse(`@${username}, invalid dice notation. Try: !roll 1d20 or !roll 2d6+3`);
      return;
    }

    try {
      // Execute the roll
      const result = this.rollDice(diceMatch.notation);
      
      // Create dice roll object
      const diceRoll: ViewerDiceRoll = {
        id: this.generateRollId(),
        userId,
        username,
        notation: diceMatch.notation,
        result,
        timestamp: new Date(),
        context: diceMatch.context
      };

      // Update cooldown and roll count
      this.setCooldown(userId);
      this.incrementRollCount(userId);

      // Emit the roll event
      this.emit('dice-roll', diceRoll);

      // Send chat response
      await this.sendDiceRollResponse(diceRoll, tags);

      // Check for special results
      this.checkForSpecialResults(diceRoll, tags);

    } catch (error) {
      console.error('Error processing dice roll:', error);
      await this.sendChatResponse(`@${username}, error processing your roll. Please try again.`);
    }
  }

  private rollDice(notation: string): DiceResult {
    const parts = notation.toLowerCase().match(/^([0-9]*)d([0-9]+)([+\-][0-9]+)?$/);
    if (!parts) {
      throw new Error('Invalid dice notation');
    }

    const count = parseInt(parts[1]) || 1;
    const sides = parseInt(parts[2]);
    const modifier = parts[3] ? parseInt(parts[3]) : 0;

    if (count > 20) {
      throw new Error('Too many dice (max 20)');
    }
    if (sides > 1000) {
      throw new Error('Dice too large (max d1000)');
    }

    const rolls: number[] = [];
    let total = 0;

    // Roll each die
    for (let i = 0; i < count; i++) {
      const roll = Math.floor(Math.random() * sides) + 1;
      rolls.push(roll);
      total += roll;
    }

    total += modifier;

    // Check for critical results
    const critical = sides === 20 && rolls.some(roll => roll === 20);
    const fumble = sides === 20 && rolls.some(roll => roll === 1);

    // Create breakdown string
    let breakdown = `[${rolls.join(', ')}]`;
    if (modifier !== 0) {
      breakdown += ` ${modifier >= 0 ? '+' : ''}${modifier}`;
    }

    return {
      total,
      rolls,
      modifiers: modifier !== 0 ? [modifier] : [],
      breakdown,
      critical,
      fumble
    };
  }

  private async sendDiceRollResponse(diceRoll: ViewerDiceRoll, tags: tmi.ChatUserstate): Promise<void> {
    let response = `@${diceRoll.username} rolled ${diceRoll.notation}: ${diceRoll.result.total}`;
    
    // Add breakdown for multiple dice
    if (diceRoll.result.rolls.length > 1 || diceRoll.result.modifiers.length > 0) {
      response += ` (${diceRoll.result.breakdown})`;
    }

    // Add special result indicators
    if (diceRoll.result.critical) {
      response += ' 🎉 CRITICAL!';
    } else if (diceRoll.result.fumble) {
      response += ' 💀 FUMBLE!';
    }

    // Add context if provided
    if (diceRoll.context) {
      response += ` for ${diceRoll.context}`;
    }

    await this.sendChatResponse(response);
  }

  private async checkForSpecialResults(diceRoll: ViewerDiceRoll, tags: tmi.ChatUserstate): Promise<void> {
    // Critical hit celebration
    if (diceRoll.result.critical) {
      this.emit('critical-hit', {
        diceRoll,
        user: tags,
        celebration: 'critical-hit-animation'
      });

      // Special message for natural 20s
      if (diceRoll.notation.includes('d20') && diceRoll.result.rolls.includes(20)) {
        setTimeout(async () => {
          await this.sendChatResponse(`🎉 ${diceRoll.username} rolled a NATURAL 20! The dice gods smile upon you! 🎉`);
        }, 2000);
      }
    }

    // Fumble commiseration
    if (diceRoll.result.fumble) {
      this.emit('fumble', {
        diceRoll,
        user: tags,
        effect: 'fumble-animation'
      });

      // Special message for natural 1s
      if (diceRoll.notation.includes('d20') && diceRoll.result.rolls.includes(1)) {
        setTimeout(async () => {
          await this.sendChatResponse(`💀 ${diceRoll.username} rolled a NATURAL 1! The dice have betrayed you! 💀`);
        }, 2000);
      }
    }

    // Perfect rolls (all dice show maximum)
    const isPerfectRoll = diceRoll.result.rolls.every(roll => {
      const maxValue = this.getMaxValueFromNotation(diceRoll.notation);
      return roll === maxValue;
    });

    if (isPerfectRoll && diceRoll.result.rolls.length > 1) {
      this.emit('perfect-roll', {
        diceRoll,
        user: tags,
        effect: 'perfect-roll-animation'
      });

      setTimeout(async () => {
        await this.sendChatResponse(`✨ ${diceRoll.username} rolled MAXIMUM on all dice! Absolutely perfect! ✨`);
      }, 1500);
    }

    // Snake eyes (all 1s on multiple dice)
    const isSnakeEyes = diceRoll.result.rolls.every(roll => roll === 1) && diceRoll.result.rolls.length > 1;
    if (isSnakeEyes) {
      this.emit('snake-eyes', {
        diceRoll,
        user: tags,
        effect: 'snake-eyes-animation'
      });

      setTimeout(async () => {
        await this.sendChatResponse(`🐍 ${diceRoll.username} rolled SNAKE EYES! All ones! That's... unlucky. 🐍`);
      }, 1500);
    }
  }

  private getMaxValueFromNotation(notation: string): number {
    const match = notation.match(/d([0-9]+)/);
    return match ? parseInt(match[1]) : 1;
  }

  private isValidDiceNotation(notation: string): boolean {
    const pattern = /^([0-9]*)d([0-9]+)([+\-][0-9]+)?$/;
    const match = notation.toLowerCase().match(pattern);
    
    if (!match) return false;

    const count = parseInt(match[1]) || 1;
    const sides = parseInt(match[2]);
    const modifier = match[3] ? Math.abs(parseInt(match[3])) : 0;

    // Validation rules
    if (count > 20) return false; // Max 20 dice
    if (sides < 2 || sides > 1000) return false; // Valid die sizes
    if (modifier > 100) return false; // Reasonable modifier limit

    // Check if die type is allowed (if restrictions are set)
    if (this.settings.viewerDice.allowedDice.length > 0) {
      const dieType = `d${sides}`;
      if (!this.settings.viewerDice.allowedDice.includes(dieType)) {
        return false;
      }
    }

    return true;
  }

  private isOnCooldown(userId: string): boolean {
    const lastRoll = this.rollCooldowns.get(userId);
    if (!lastRoll) return false;
    
    return (Date.now() - lastRoll) < (this.settings.viewerDice.cooldown * 1000);
  }

  private getRemainingCooldown(userId: string): number {
    const lastRoll = this.rollCooldowns.get(userId) || 0;
    return Math.max(0, (this.settings.viewerDice.cooldown * 1000) - (Date.now() - lastRoll));
  }

  private setCooldown(userId: string): void {
    this.rollCooldowns.set(userId, Date.now());
  }

  private hasExceededDailyLimit(userId: string): boolean {
    const rollCount = this.userRollCounts.get(userId) || 0;
    return rollCount >= this.settings.viewerDice.maxRolls;
  }

  private incrementRollCount(userId: string): void {
    const current = this.userRollCounts.get(userId) || 0;
    this.userRollCounts.set(userId, current + 1);
  }

  private setupDailyReset(): void {
    // Reset counters at midnight
    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(0, 0, 0, 0);
    
    const msUntilMidnight = tomorrow.getTime() - now.getTime();
    
    setTimeout(() => {
      this.resetDailyCounts();
      
      // Set up recurring daily reset
      setInterval(() => {
        this.resetDailyCounts();
      }, 24 * 60 * 60 * 1000);
    }, msUntilMidnight);
  }

  private resetDailyCounts(): void {
    this.userRollCounts.clear();
    this.dailyResetTime = new Date();
    console.log('📊 Daily dice roll counts reset');
    this.emit('daily-reset');
  }

  private generateRollId(): string {
    return `roll_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private async sendChatResponse(message: string): Promise<void> {
    if (this.twitchClient) {
      try {
        const channels = this.twitchClient.getChannels();
        if (channels.length > 0) {
          await this.twitchClient.say(channels[0], message);
        }
      } catch (error) {
        console.error('Error sending chat message:', error);
      }
    }
  }

  // Public API methods
  public getRollStatistics(): any {
    const totalRolls = Array.from(this.userRollCounts.values()).reduce((sum, count) => sum + count, 0);
    const uniqueUsers = this.userRollCounts.size;
    const averageRollsPerUser = uniqueUsers > 0 ? totalRolls / uniqueUsers : 0;

    return {
      totalRolls,
      uniqueUsers,
      averageRollsPerUser,
      dailyResetTime: this.dailyResetTime,
      cooldownActive: this.rollCooldowns.size,
      settings: this.settings.viewerDice
    };
  }

  public getTopRollers(limit: number = 10): Array<{ userId: string; rollCount: number }> {
    return Array.from(this.userRollCounts.entries())
      .map(([userId, rollCount]) => ({ userId, rollCount }))
      .sort((a, b) => b.rollCount - a.rollCount)
      .slice(0, limit);
  }

  public updateSettings(newSettings: InteractionSettings): void {
    this.settings = newSettings;
    this.emit('settings-updated', newSettings);
  }

  public async simulateRoll(notation: string, username: string = 'TestUser'): Promise<ViewerDiceRoll> {
    const result = this.rollDice(notation);
    const diceRoll: ViewerDiceRoll = {
      id: this.generateRollId(),
      userId: 'simulate',
      username,
      notation,
      result,
      timestamp: new Date()
    };

    this.emit('dice-roll', diceRoll);
    return diceRoll;
  }

  public isConnected(): boolean {
    return this.twitchClient !== null && this.twitchClient.readyState() === 'OPEN';
  }

  public async disconnect(): Promise<void> {
    if (this.twitchClient) {
      await this.twitchClient.disconnect();
      this.twitchClient = null;
    }
  }

  // Command handlers for special dice features
  public registerCustomCommands(): void {
    // These would be handled in the chat message parser
    const customCommands = {
      '!stats': this.handleStatsCommand.bind(this),
      '!toprollers': this.handleTopRollersCommand.bind(this),
      '!dicehelp': this.handleHelpCommand.bind(this),
      '!rollbattle': this.handleRollBattleCommand.bind(this),
    };
  }

  private async handleStatsCommand(username: string): Promise<void> {
    const stats = this.getRollStatistics();
    const userRolls = this.userRollCounts.get(username) || 0;
    
    await this.sendChatResponse(
      `@${username} Your rolls today: ${userRolls}/${this.settings.viewerDice.maxRolls} | ` +
      `Total community rolls: ${stats.totalRolls} by ${stats.uniqueUsers} users`
    );
  }

  private async handleTopRollersCommand(): Promise<void> {
    const topRollers = this.getTopRollers(5);
    if (topRollers.length === 0) {
      await this.sendChatResponse('No rolls yet today! Be the first with !roll 1d20');
      return;
    }

    const leaderboard = topRollers
      .map((roller, index) => `${index + 1}. ${roller.userId} (${roller.rollCount})`)
      .join(' | ');
    
    await this.sendChatResponse(`🎲 Top Rollers Today: ${leaderboard}`);
  }

  private async handleHelpCommand(): Promise<void> {
    await this.sendChatResponse(
      '🎲 Dice Commands: !roll 1d20, !r 2d6+3, $1d4 | ' +
      `Cooldown: ${this.settings.viewerDice.cooldown}s | ` +
      `Daily limit: ${this.settings.viewerDice.maxRolls} rolls`
    );
  }

  private async handleRollBattleCommand(username: string, opponents: string[]): Promise<void> {
    // Roll-off feature for dramatic moments
    const participants = [username, ...opponents].slice(0, 4); // Max 4 participants
    const results: Array<{ name: string; roll: number }> = [];

    for (const participant of participants) {
      const result = this.rollDice('1d20');
      results.push({ name: participant, roll: result.total });
    }

    results.sort((a, b) => b.roll - a.roll);
    
    const battleResults = results
      .map((result, index) => `${index + 1}. ${result.name}: ${result.roll}`)
      .join(' | ');
    
    await this.sendChatResponse(`⚔️ Roll Battle Results: ${battleResults} | ${results[0].name} wins!`);
    
    this.emit('roll-battle', {
      participants,
      results,
      winner: results[0]
    });
  }
}