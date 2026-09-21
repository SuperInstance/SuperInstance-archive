/**
 * Core Game Engine - Monopoly/Cashflow Hybrid Mechanics
 * Manages game flow, turn-based gameplay, and board mechanics
 */

import { EventEmitter } from 'events';
import { 
  Player, 
  GameSession, 
  BoardSpace, 
  CashflowStatement,
  GamePhase,
  SpaceType,
  GameMode,
  DifficultyLevel,
  WinCondition
} from '../types/game-types';
import { EconomyEngine } from '../economy/EconomyEngine';
import { PlayerManager } from '../players/PlayerManager';
import { BoardManager } from '../board/BoardManager';
import { DiceRoller } from './DiceRoller';

export class GameEngine extends EventEmitter {
  private session: GameSession;
  private economyEngine: EconomyEngine;
  private playerManager: PlayerManager;
  private boardManager: BoardManager;
  private diceRoller: DiceRoller;
  
  private turnTimer?: NodeJS.Timeout;
  private gameTimer?: NodeJS.Timeout;
  private autoSaveInterval?: NodeJS.Timeout;

  constructor(session: GameSession) {
    super();
    this.session = session;
    this.economyEngine = new EconomyEngine(session.difficulty);
    this.playerManager = new PlayerManager();
    this.boardManager = new BoardManager();
    this.diceRoller = new DiceRoller();
    
    this.setupEventListeners();
    this.initializeGame();
  }

  /**
   * Initialize game with starting conditions
   */
  private initializeGame(): void {
    console.log(`🎮 Initializing Empire Game: ${this.session.name}`);
    
    // Set up players with starting resources
    this.session.players.forEach((player, index) => {
      this.initializePlayer(player, index);
    });

    // Initialize economy state
    this.economyEngine.initialize();
    
    // Set up board
    this.boardManager.initializeBoard(this.session.board);
    
    // Start auto-save if multiplayer
    if (this.session.mode !== GameMode.SINGLE_PLAYER) {
      this.startAutoSave();
    }

    this.emit('game:initialized', { sessionId: this.session.id });
  }

  /**
   * Initialize individual player with starting resources
   */
  private initializePlayer(player: Player, turnOrder: number): void {
    const startingCash = this.getStartingCash(player.level);
    
    player.cash = startingCash;
    player.position = 0; // Start at GO
    player.turnOrder = turnOrder;
    player.netWorth = startingCash;
    player.creditScore = 650; // Average starting credit
    player.passiveIncome = 0;
    player.totalIncome = 0;
    player.totalExpenses = 0;

    // Initialize monthly cashflow
    this.generateMonthlyCashflow(player);

    console.log(`👤 Player ${player.name} initialized with $${startingCash.toLocaleString()}`);
  }

  /**
   * Start a new game turn
   */
  async startTurn(): Promise<void> {
    if (this.session.gamePhase !== GamePhase.PLAYING) return;

    const currentPlayer = this.getCurrentPlayer();
    if (!currentPlayer) return;

    console.log(`🎯 Starting turn for ${currentPlayer.name} (Round ${this.session.currentRound})`);

    this.emit('turn:started', { 
      playerId: currentPlayer.id, 
      round: this.session.currentRound,
      turn: this.session.currentTurn 
    });

    // Process monthly cashflow at start of turn
    this.processMonthlyCashflow(currentPlayer);

    // Check for random events
    await this.processRandomEvents(currentPlayer);

    // Start turn timer for multiplayer games
    if (this.session.mode !== GameMode.SINGLE_PLAYER) {
      this.startTurnTimer();
    }
  }

  /**
   * Roll dice and move player
   */
  async rollDice(playerId: string): Promise<{ dice: number[], total: number, newPosition: number }> {
    const player = this.getPlayerById(playerId);
    if (!player || this.getCurrentPlayer()?.id !== playerId) {
      throw new Error('Not your turn or invalid player');
    }

    const roll = this.diceRoller.roll(2); // Roll 2 dice
    const total = roll.reduce((sum, die) => sum + die, 0);
    const oldPosition = player.position;
    const newPosition = (oldPosition + total) % this.session.board.size;

    player.position = newPosition;

    // Check if passed GO (Cashflow payday)
    if (newPosition < oldPosition) {
      this.processPassGo(player);
    }

    const landedSpace = this.boardManager.getSpace(newPosition);
    
    console.log(`🎲 ${player.name} rolled ${dice.join('+')}=${total}, moved to ${landedSpace.name}`);

    this.emit('dice:rolled', {
      playerId,
      dice: roll,
      total,
      oldPosition,
      newPosition,
      spaceName: landedSpace.name
    });

    // Process space action
    await this.processSpaceAction(player, landedSpace);

    return { dice: roll, total, newPosition };
  }

  /**
   * Process action for landed space
   */
  private async processSpaceAction(player: Player, space: BoardSpace): Promise<void> {
    switch (space.type) {
      case SpaceType.START:
        // Already handled in movement
        break;
        
      case SpaceType.PROPERTY:
        await this.processPropertySpace(player, space);
        break;
        
      case SpaceType.BUSINESS:
        await this.processBusinessSpace(player, space);
        break;
        
      case SpaceType.EVENT:
        await this.processEventSpace(player, space);
        break;
        
      case SpaceType.TAX:
        await this.processTaxSpace(player, space);
        break;
        
      case SpaceType.JAIL:
        await this.processJailSpace(player);
        break;
        
      case SpaceType.GO_TO_JAIL:
        await this.sendToJail(player);
        break;
        
      case SpaceType.FREE_PARKING:
        // Collect money from community fund
        const jackpot = this.session.economy?.communityFund || 0;
        if (jackpot > 0) {
          player.cash += jackpot;
          this.session.economy!.communityFund = 0;
          this.emit('jackpot:won', { playerId: player.id, amount: jackpot });
        }
        break;
    }
  }

  /**
   * Process property purchase/rent
   */
  private async processPropertySpace(player: Player, space: BoardSpace): Promise<void> {
    const property = this.boardManager.getPropertyAtSpace(space.id);
    if (!property) return;

    const owner = this.getPropertyOwner(property.id);
    
    if (!owner) {
      // Property available for purchase
      const canAfford = player.cash >= property.purchasePrice;
      
      this.emit('property:available', {
        playerId: player.id,
        property,
        canAfford,
        financingOptions: this.getFinancingOptions(player, property.purchasePrice)
      });
      
    } else if (owner.id !== player.id) {
      // Pay rent to owner
      const rent = this.calculateRent(property, owner);
      const payment = Math.min(player.cash, rent);
      
      player.cash -= payment;
      owner.cash += payment;
      
      this.emit('rent:paid', {
        payerId: player.id,
        ownerId: owner.id,
        propertyId: property.id,
        amount: payment
      });
      
      console.log(`💰 ${player.name} paid $${payment} rent to ${owner.name} for ${property.name}`);
    }
  }

  /**
   * Process business opportunity space
   */
  private async processBusinessSpace(player: Player, space: BoardSpace): Promise<void> {
    if (space.businessOpportunity) {
      const opportunity = space.businessOpportunity;
      
      this.emit('business:opportunity', {
        playerId: player.id,
        opportunity,
        playerCash: player.cash,
        creditAvailable: this.calculateCreditLimit(player)
      });
    }
  }

  /**
   * Process event card space
   */
  private async processEventSpace(player: Player, space: BoardSpace): Promise<void> {
    if (space.eventCard) {
      const card = space.eventCard;
      await this.processEventCard(player, card);
    }
  }

  /**
   * Process tax space
   */
  private async processTaxSpace(player: Player, space: BoardSpace): Promise<void> {
    const taxAmount = space.cost || 0;
    const actualTax = Math.min(player.cash, taxAmount);
    
    player.cash -= actualTax;
    
    // Add to community fund for Free Parking
    if (this.session.economy) {
      this.session.economy.communityFund = (this.session.economy.communityFund || 0) + actualTax;
    }
    
    this.emit('tax:paid', {
      playerId: player.id,
      amount: actualTax,
      spaceName: space.name
    });
  }

  /**
   * Generate monthly cashflow statement
   */
  private generateMonthlyCashflow(player: Player): CashflowStatement {
    const now = new Date();
    const statement: CashflowStatement = {
      playerId: player.id,
      month: now.getMonth() + 1,
      year: now.getFullYear(),
      
      // Income calculations
      salary: this.calculateSalary(player),
      businessIncome: this.calculateBusinessIncome(player),
      passiveIncome: this.calculatePassiveIncome(player),
      capitalGains: 0, // Will be calculated when assets are sold
      otherIncome: 0,
      totalIncome: 0,
      
      // Expense calculations
      taxes: 0,
      livingExpenses: this.calculateLivingExpenses(player),
      businessExpenses: this.calculateBusinessExpenses(player),
      debtService: this.calculateDebtService(player),
      otherExpenses: 0,
      totalExpenses: 0,
      
      // Cash flow
      netCashFlow: 0,
      cumulativeCashFlow: player.cash,
      
      // Ratios
      savingsRate: 0,
      debtToIncomeRatio: 0,
      expenseRatio: 0
    };

    // Calculate totals
    statement.totalIncome = statement.salary + statement.businessIncome + 
                          statement.passiveIncome + statement.capitalGains + statement.otherIncome;
    
    statement.taxes = statement.totalIncome * this.getTaxRate(player, statement.totalIncome);
    statement.totalExpenses = statement.taxes + statement.livingExpenses + 
                             statement.businessExpenses + statement.debtService + statement.otherExpenses;
    
    statement.netCashFlow = statement.totalIncome - statement.totalExpenses;
    
    // Calculate ratios
    if (statement.totalIncome > 0) {
      statement.savingsRate = Math.max(0, statement.netCashFlow / statement.totalIncome);
      statement.expenseRatio = statement.totalExpenses / statement.totalIncome;
    }
    
    if (statement.totalIncome > 0 && statement.debtService > 0) {
      statement.debtToIncomeRatio = statement.debtService / statement.totalIncome;
    }

    return statement;
  }

  /**
   * Process monthly cashflow for player
   */
  private processMonthlyCashflow(player: Player): void {
    const statement = this.generateMonthlyCashflow(player);
    
    // Apply cashflow to player
    player.cash += statement.netCashFlow;
    player.totalIncome += statement.totalIncome;
    player.totalExpenses += statement.totalExpenses;
    player.passiveIncome = statement.passiveIncome;
    
    // Update net worth
    this.updatePlayerNetWorth(player);
    
    this.emit('cashflow:processed', {
      playerId: player.id,
      statement,
      newCash: player.cash,
      netWorth: player.netWorth
    });
    
    console.log(`💳 ${player.name} - Monthly Cashflow: ${statement.netCashFlow >= 0 ? '+' : ''}$${statement.netCashFlow.toLocaleString()}`);
  }

  /**
   * End current turn and move to next player
   */
  endTurn(): void {
    this.clearTurnTimer();
    
    const currentPlayer = this.getCurrentPlayer();
    if (currentPlayer) {
      this.emit('turn:ended', { playerId: currentPlayer.id });
    }

    // Move to next player
    this.session.currentPlayerIndex = (this.session.currentPlayerIndex + 1) % this.session.players.length;
    this.session.currentTurn++;
    
    // Check if round completed
    if (this.session.currentPlayerIndex === 0) {
      this.session.currentRound++;
      this.emit('round:completed', { round: this.session.currentRound - 1 });
      
      // Process end of round events
      this.processEndOfRound();
    }

    // Check win conditions
    if (this.checkWinConditions()) {
      return;
    }

    // Start next turn
    setTimeout(() => this.startTurn(), 1000);
  }

  /**
   * Check if any player has won
   */
  private checkWinConditions(): boolean {
    for (const condition of this.session.rules.winConditions) {
      const winner = this.evaluateWinCondition(condition);
      if (winner) {
        this.endGame(winner);
        return true;
      }
    }

    // Check for bankruptcy elimination
    const activePlayers = this.session.players.filter(p => p.cash > this.session.rules.bankruptcyThreshold);
    if (activePlayers.length === 1) {
      this.endGame(activePlayers[0]);
      return true;
    }

    return false;
  }

  /**
   * End game and declare winner
   */
  private endGame(winner: Player): void {
    this.session.gamePhase = GamePhase.COMPLETED;
    this.clearAllTimers();

    this.emit('game:ended', {
      winner: winner.id,
      winnerName: winner.name,
      finalScores: this.calculateFinalScores(),
      gameDuration: Date.now() - (this.session.startedAt?.getTime() || 0)
    });

    console.log(`🏆 Game Over! Winner: ${winner.name} with net worth of $${winner.netWorth.toLocaleString()}`);
  }

  /**
   * Calculate starting cash based on difficulty
   */
  private getStartingCash(difficulty: DifficultyLevel): number {
    const baseCash = {
      [DifficultyLevel.KID]: 10000,
      [DifficultyLevel.TEEN]: 5000,
      [DifficultyLevel.ADULT]: 3000,
      [DifficultyLevel.BUSINESS]: 2000,
      [DifficultyLevel.MBA]: 1500
    };

    return baseCash[difficulty] || 3000;
  }

  /**
   * Helper methods
   */
  private getCurrentPlayer(): Player | undefined {
    return this.session.players[this.session.currentPlayerIndex];
  }

  private getPlayerById(id: string): Player | undefined {
    return this.session.players.find(p => p.id === id);
  }

  private setupEventListeners(): void {
    this.economyEngine.on('economy:updated', (state) => {
      this.session.economy = state;
      this.emit('economy:changed', state);
    });
  }

  private startTurnTimer(): void {
    const timeLimit = 120000; // 2 minutes per turn
    this.turnTimer = setTimeout(() => {
      console.log('⏰ Turn timeout - auto-ending turn');
      this.endTurn();
    }, timeLimit);
  }

  private clearTurnTimer(): void {
    if (this.turnTimer) {
      clearTimeout(this.turnTimer);
      this.turnTimer = undefined;
    }
  }

  private startAutoSave(): void {
    this.autoSaveInterval = setInterval(() => {
      this.saveGameState();
    }, 60000); // Save every minute
  }

  private clearAllTimers(): void {
    this.clearTurnTimer();
    
    if (this.gameTimer) {
      clearTimeout(this.gameTimer);
    }
    
    if (this.autoSaveInterval) {
      clearInterval(this.autoSaveInterval);
    }
  }

  private saveGameState(): void {
    this.emit('game:save', { session: this.session });
  }

  // Placeholder methods - will be implemented in detail
  private calculateSalary(player: Player): number { return 3000; }
  private calculateBusinessIncome(player: Player): number { return 0; }
  private calculatePassiveIncome(player: Player): number { return 0; }
  private calculateLivingExpenses(player: Player): number { return 2000; }
  private calculateBusinessExpenses(player: Player): number { return 0; }
  private calculateDebtService(player: Player): number { return 0; }
  private getTaxRate(player: Player, income: number): number { return 0.25; }
  private updatePlayerNetWorth(player: Player): void {
    player.netWorth = player.cash + player.assets - player.liabilities;
  }
  private processPassGo(player: Player): void {
    const salary = 2000; // Base salary
    player.cash += salary;
    console.log(`💰 ${player.name} passed GO and collected $${salary}`);
  }
  private processRandomEvents(player: Player): Promise<void> { return Promise.resolve(); }
  private processJailSpace(player: Player): Promise<void> { return Promise.resolve(); }
  private sendToJail(player: Player): Promise<void> { return Promise.resolve(); }
  private getPropertyOwner(propertyId: string): Player | undefined { return undefined; }
  private calculateRent(property: any, owner: Player): number { return 500; }
  private getFinancingOptions(player: Player, amount: number): any[] { return []; }
  private calculateCreditLimit(player: Player): number { return player.creditScore * 100; }
  private processEventCard(player: Player, card: any): Promise<void> { return Promise.resolve(); }
  private processEndOfRound(): void {}
  private evaluateWinCondition(condition: WinCondition): Player | null { return null; }
  private calculateFinalScores(): Record<string, number> { return {}; }

  // Public methods
  public getSession(): GameSession { return this.session; }
  public pauseGame(): void { this.session.isPaused = true; }
  public resumeGame(): void { this.session.isPaused = false; }
  public getEconomyState() { return this.economyEngine.getState(); }
}