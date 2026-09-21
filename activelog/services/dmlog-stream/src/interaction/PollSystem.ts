import { EventEmitter } from 'events';
import { ViewerPoll, PollOption, ViewerEngagement, InteractionSettings } from '../types';
import * as tmi from 'tmi.js';

export class PollSystem extends EventEmitter {
  private twitchClient: tmi.Client | null = null;
  private activePoll: ViewerPoll | null = null;
  private pollHistory: ViewerPoll[] = [];
  private settings: InteractionSettings;
  private pollTimer: NodeJS.Timeout | null = null;
  private viewerEngagement: Map<string, ViewerEngagement> = new Map();

  constructor(settings: InteractionSettings) {
    super();
    this.settings = settings;
  }

  public async initialize(twitchClient: tmi.Client): Promise<void> {
    this.twitchClient = twitchClient;
    this.twitchClient.on('message', this.handleChatMessage.bind(this));
    console.log('📊 Poll system initialized');
  }

  private async handleChatMessage(channel: string, tags: tmi.ChatUserstate, message: string, self: boolean): Promise<void> {
    if (self || !this.settings.polls.enabled) return;

    const username = tags.username || 'anonymous';
    const userId = tags['user-id'] || username;

    // Handle poll votes
    if (this.activePoll && this.activePoll.status === 'active') {
      const vote = this.parseVoteCommand(message);
      if (vote !== null) {
        await this.processVote(userId, username, vote, tags);
        return;
      }
    }

    // Handle poll creation commands (for mods/streamers)
    if (this.canCreatePoll(tags)) {
      const pollCommand = this.parsePollCommand(message);
      if (pollCommand) {
        await this.createPoll(pollCommand, username);
      }
    }
  }

  private parseVoteCommand(message: string): number | null {
    const trimmed = message.trim();
    
    // Support various vote formats
    const patterns = [
      /^!vote\s+([1-9])$/i,
      /^!(\d)$/,
      /^(\d)$/,
      /^vote\s+([1-9])$/i,
      /^([1-9])\s*$/,
    ];

    for (const pattern of patterns) {
      const match = trimmed.match(pattern);
      if (match) {
        const optionIndex = parseInt(match[1]) - 1; // Convert to 0-based index
        if (this.activePoll && optionIndex >= 0 && optionIndex < this.activePoll.options.length) {
          return optionIndex;
        }
      }
    }

    return null;
  }

  private parsePollCommand(message: string): { question: string; options: string[]; duration?: number } | null {
    // Parse poll creation command: !poll duration "question" "option1" "option2" ...
    const pollMatch = message.match(/^!poll\s+(?:(\d+)\s+)?"([^"]+)"\s*((?:"[^"]+"\s*)+)/i);
    if (!pollMatch) return null;

    const duration = pollMatch[1] ? parseInt(pollMatch[1]) : this.settings.polls.duration;
    const question = pollMatch[2];
    const optionsString = pollMatch[3];
    
    // Extract options from quoted strings
    const optionMatches = optionsString.match(/"([^"]+)"/g);
    if (!optionMatches || optionMatches.length < 2) return null;
    
    const options = optionMatches.map(opt => opt.slice(1, -1)); // Remove quotes
    
    if (options.length > 10) return null; // Max 10 options
    if (duration > 300) return null; // Max 5 minutes

    return { question, options, duration };
  }

  private canCreatePoll(tags: tmi.ChatUserstate): boolean {
    // Allow broadcaster, mods, and VIPs to create polls
    return !!(tags.badges?.broadcaster || tags.badges?.moderator || tags.badges?.vip);
  }

  public async createPoll(pollData: { question: string; options: string[]; duration?: number }, createdBy: string): Promise<ViewerPoll> {
    if (this.activePoll && this.activePoll.status === 'active') {
      throw new Error('A poll is already active');
    }

    const duration = pollData.duration || this.settings.polls.duration;
    const startTime = new Date();
    const endTime = new Date(startTime.getTime() + duration * 1000);

    const poll: ViewerPoll = {
      id: this.generatePollId(),
      question: pollData.question,
      options: pollData.options.map((text, index) => ({
        id: `option_${index}`,
        text,
        votes: 0,
        voters: []
      })),
      duration,
      startTime,
      endTime,
      status: 'active',
      totalVotes: 0,
      allowMultiple: false,
      requireSubscription: this.settings.polls.requireSubscription,
      createdBy
    };

    this.activePoll = poll;
    this.startPollTimer(poll);
    
    // Announce poll
    await this.announcePoll(poll);
    
    this.emit('poll-created', poll);
    return poll;
  }

  private async announcePoll(poll: ViewerPoll): Promise<void> {
    let announcement = `📊 NEW POLL: ${poll.question}\n`;
    
    poll.options.forEach((option, index) => {
      announcement += `${index + 1}. ${option.text}\n`;
    });
    
    announcement += `Vote with !${1}-!${poll.options.length} or just type the number! Duration: ${poll.duration}s`;
    
    if (poll.requireSubscription) {
      announcement += ' (Subscribers only)';
    }

    await this.sendChatMessage(announcement);
  }

  private async processVote(userId: string, username: string, optionIndex: number, tags: tmi.ChatUserstate): Promise<void> {
    if (!this.activePoll || this.activePoll.status !== 'active') {
      return;
    }

    // Check subscription requirement
    if (this.activePoll.requireSubscription && !this.isSubscriberOrHigher(tags)) {
      await this.sendChatMessage(`@${username}, this poll requires a subscription to vote.`);
      return;
    }

    const option = this.activePoll.options[optionIndex];
    if (!option) return;

    // Check if user already voted
    const hasAlreadyVoted = this.activePoll.options.some(opt => opt.voters.includes(userId));
    if (hasAlreadyVoted && !this.activePoll.allowMultiple) {
      await this.sendChatMessage(`@${username}, you have already voted in this poll!`);
      return;
    }

    // Remove previous vote if changing vote and multiple not allowed
    if (!this.activePoll.allowMultiple) {
      this.activePoll.options.forEach(opt => {
        const voterIndex = opt.voters.indexOf(userId);
        if (voterIndex !== -1) {
          opt.voters.splice(voterIndex, 1);
          opt.votes--;
          this.activePoll!.totalVotes--;
        }
      });
    }

    // Add new vote
    option.voters.push(userId);
    option.votes++;
    this.activePoll.totalVotes++;

    // Update viewer engagement
    this.updateViewerEngagement(userId, username, 'poll_vote');

    // Emit vote event
    this.emit('vote-cast', {
      poll: this.activePoll,
      voter: { userId, username },
      option: optionIndex,
      tags
    });

    // Optional vote confirmation
    if (Math.random() < 0.1) { // 10% chance to confirm vote
      await this.sendChatMessage(`Thanks ${username}! Vote for "${option.text}" recorded.`);
    }
  }

  private isSubscriberOrHigher(tags: tmi.ChatUserstate): boolean {
    return !!(tags.badges?.subscriber || tags.badges?.moderator || 
              tags.badges?.broadcaster || tags.badges?.vip);
  }

  private startPollTimer(poll: ViewerPoll): void {
    this.pollTimer = setTimeout(async () => {
      await this.endPoll();
    }, poll.duration * 1000);

    // Countdown warnings
    const warnings = [60, 30, 10, 5]; // Seconds before end
    warnings.forEach(seconds => {
      if (seconds < poll.duration) {
        setTimeout(async () => {
          if (this.activePoll?.id === poll.id && this.activePoll.status === 'active') {
            await this.sendChatMessage(`⏰ Poll ends in ${seconds} seconds!`);
          }
        }, (poll.duration - seconds) * 1000);
      }
    });
  }

  public async endPoll(): Promise<ViewerPoll | null> {
    if (!this.activePoll || this.activePoll.status !== 'active') {
      return null;
    }

    // Clear timer
    if (this.pollTimer) {
      clearTimeout(this.pollTimer);
      this.pollTimer = null;
    }

    // Update poll status
    this.activePoll.status = 'ended';
    this.activePoll.endTime = new Date();

    const endedPoll = { ...this.activePoll };
    
    // Announce results
    await this.announceResults(endedPoll);
    
    // Add to history
    this.pollHistory.push(endedPoll);
    if (this.pollHistory.length > 50) {
      this.pollHistory.shift(); // Keep last 50 polls
    }

    this.emit('poll-ended', endedPoll);
    
    // Clear active poll
    this.activePoll = null;
    
    return endedPoll;
  }

  private async announceResults(poll: ViewerPoll): Promise<void> {
    const sortedOptions = [...poll.options].sort((a, b) => b.votes - a.votes);
    
    let results = `📊 POLL RESULTS: "${poll.question}"\n`;
    
    sortedOptions.forEach((option, index) => {
      const percentage = poll.totalVotes > 0 ? 
        ((option.votes / poll.totalVotes) * 100).toFixed(1) : '0.0';
      
      const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : '▫️';
      results += `${medal} ${option.text}: ${option.votes} votes (${percentage}%)\n`;
    });
    
    results += `Total votes: ${poll.totalVotes}`;
    
    // Add winner celebration for close polls
    if (sortedOptions.length >= 2 && sortedOptions[0].votes > 0) {
      const margin = sortedOptions[0].votes - sortedOptions[1].votes;
      if (margin <= 1) {
        results += ' - What a close race! 🏁';
      } else if (margin / poll.totalVotes < 0.1) {
        results += ' - Nail-biter finish! 😱';
      } else if (sortedOptions[0].votes / poll.totalVotes > 0.8) {
        results += ' - Landslide victory! 🌊';
      }
    }

    await this.sendChatMessage(results);
  }

  // Quick poll creation methods for common scenarios
  public async createYesNoVote(question: string, duration: number = 60): Promise<ViewerPoll> {
    return this.createPoll({
      question,
      options: ['Yes', 'No'],
      duration
    }, 'system');
  }

  public async createCharacterChoice(characters: string[]): Promise<ViewerPoll> {
    return this.createPoll({
      question: 'Which character should take the spotlight?',
      options: characters,
      duration: 90
    }, 'system');
  }

  public async createActionVote(actions: string[]): Promise<ViewerPoll> {
    return this.createPoll({
      question: 'What should the party do next?',
      options: actions,
      duration: 120
    }, 'system');
  }

  public async createDifficultyVote(): Promise<ViewerPoll> {
    return this.createPoll({
      question: 'How challenging should this encounter be?',
      options: ['Easy Mode', 'Normal', 'Hard Mode', 'NIGHTMARE'],
      duration: 45
    }, 'system');
  }

  // Engagement tracking
  private updateViewerEngagement(userId: string, username: string, action: string): void {
    let engagement = this.viewerEngagement.get(userId);
    
    if (!engagement) {
      engagement = {
        userId,
        username,
        joinTime: new Date(),
        totalTime: 0,
        messageCount: 0,
        diceRolls: 0,
        pollVotes: 0,
        donations: 0,
        subscribed: false,
        follower: false,
        moderator: false,
        badges: []
      };
    }

    if (action === 'poll_vote') {
      engagement.pollVotes++;
    }

    this.viewerEngagement.set(userId, engagement);
  }

  // Analytics and statistics
  public getPollStatistics(): any {
    const activePollStats = this.activePoll ? {
      question: this.activePoll.question,
      totalVotes: this.activePoll.totalVotes,
      timeRemaining: this.activePoll.endTime ? 
        Math.max(0, this.activePoll.endTime.getTime() - Date.now()) / 1000 : 0,
      options: this.activePoll.options.map(opt => ({
        text: opt.text,
        votes: opt.votes,
        percentage: this.activePoll!.totalVotes > 0 ? 
          (opt.votes / this.activePoll!.totalVotes) * 100 : 0
      }))
    } : null;

    return {
      activePoll: activePollStats,
      totalPolls: this.pollHistory.length,
      totalVotes: this.pollHistory.reduce((sum, poll) => sum + poll.totalVotes, 0),
      averageVotesPerPoll: this.pollHistory.length > 0 ? 
        this.pollHistory.reduce((sum, poll) => sum + poll.totalVotes, 0) / this.pollHistory.length : 0,
      mostPopularPoll: this.getMostPopularPoll(),
      settings: this.settings.polls
    };
  }

  private getMostPopularPoll(): any {
    if (this.pollHistory.length === 0) return null;
    
    const mostPopular = this.pollHistory.reduce((prev, current) => 
      current.totalVotes > prev.totalVotes ? current : prev
    );

    return {
      question: mostPopular.question,
      votes: mostPopular.totalVotes,
      date: mostPopular.startTime
    };
  }

  public getRecentPolls(limit: number = 10): ViewerPoll[] {
    return this.pollHistory
      .sort((a, b) => b.startTime.getTime() - a.startTime.getTime())
      .slice(0, limit);
  }

  // Utility methods
  private generatePollId(): string {
    return `poll_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private async sendChatMessage(message: string): Promise<void> {
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

  // Public API
  public getActivePoll(): ViewerPoll | null {
    return this.activePoll;
  }

  public async cancelActivePoll(): Promise<void> {
    if (this.activePoll && this.activePoll.status === 'active') {
      if (this.pollTimer) {
        clearTimeout(this.pollTimer);
        this.pollTimer = null;
      }
      
      this.activePoll.status = 'ended';
      this.activePoll.endTime = new Date();
      
      await this.sendChatMessage('📊 Poll has been cancelled by the streamer.');
      this.emit('poll-cancelled', this.activePoll);
      
      this.activePoll = null;
    }
  }

  public updateSettings(newSettings: InteractionSettings): void {
    this.settings = newSettings;
    this.emit('settings-updated', newSettings);
  }

  // Special poll types for D&D scenarios
  public async createNPCReactionPoll(npcName: string, situation: string): Promise<ViewerPoll> {
    const reactions = [
      'Friendly and helpful',
      'Suspicious and cautious',
      'Hostile and aggressive',
      'Confused and scared',
      'Indifferent and bored'
    ];

    return this.createPoll({
      question: `How should ${npcName} react to ${situation}?`,
      options: reactions,
      duration: 60
    }, 'system');
  }

  public async createLootDistributionPoll(items: string[]): Promise<ViewerPoll> {
    return this.createPoll({
      question: 'Who should get the magical item?',
      options: items,
      duration: 90
    }, 'system');
  }

  public async createStoryDirectionPoll(directions: string[]): Promise<ViewerPoll> {
    return this.createPoll({
      question: 'Which plot thread should we explore next?',
      options: directions,
      duration: 120
    }, 'system');
  }

  public async createMerchantPoll(): Promise<ViewerPoll> {
    const options = [
      'Haggle for a better price',
      'Accept the deal as-is',
      'Ask to see more items',
      'Walk away and look elsewhere',
      'Try to befriend the merchant'
    ];

    return this.createPoll({
      question: 'How should we deal with this merchant?',
      options,
      duration: 75
    }, 'system');
  }

  public isConnected(): boolean {
    return this.twitchClient !== null;
  }
}