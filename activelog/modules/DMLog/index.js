class DMLog {
    constructor() {
        this.characterSheets = null;
        this.diceRoller = null;
        this.campaignManager = null;
        this.initialize();
    }

    initialize() {
        this.setupCharacterSheets();
        this.setupDiceRolling();
        this.setupCampaignManagement();
    }

    setupCharacterSheets() {
        this.characterSheets = {
            createCharacter: (characterData) => {
                return {
                    characterId: this.generateId(),
                    name: characterData.name,
                    class: characterData.class,
                    race: characterData.race,
                    level: characterData.level || 1,
                    stats: {
                        strength: 10,
                        dexterity: 10,
                        constitution: 10,
                        intelligence: 10,
                        wisdom: 10,
                        charisma: 10
                    },
                    hitPoints: {
                        current: 0,
                        maximum: 0,
                        temporary: 0
                    },
                    skills: [],
                    equipment: [],
                    spells: [],
                    created: new Date()
                };
            },
            updateCharacter: (characterId, updates) => {
                return {
                    characterId: characterId,
                    updated: updates,
                    timestamp: new Date()
                };
            },
            calculateModifier: (statValue) => {
                return Math.floor((statValue - 10) / 2);
            },
            rollStats: () => {
                return {
                    strength: this.rollStat(),
                    dexterity: this.rollStat(),
                    constitution: this.rollStat(),
                    intelligence: this.rollStat(),
                    wisdom: this.rollStat(),
                    charisma: this.rollStat()
                };
            },
            levelUp: (characterId) => {
                return {
                    characterId: characterId,
                    newLevel: 0,
                    hitPointIncrease: 0,
                    newAbilities: [],
                    leveledUp: new Date()
                };
            }
        };
    }

    setupDiceRolling() {
        this.diceRoller = {
            roll: (diceNotation) => {
                const result = this.parseDiceNotation(diceNotation);
                return {
                    notation: diceNotation,
                    rolls: result.rolls,
                    total: result.total,
                    modifier: result.modifier,
                    timestamp: new Date()
                };
            },
            rollMultiple: (diceArray) => {
                return diceArray.map(dice => this.diceRoller.roll(dice));
            },
            rollWithAdvantage: (diceNotation) => {
                const roll1 = this.diceRoller.roll(diceNotation);
                const roll2 = this.diceRoller.roll(diceNotation);
                return {
                    rolls: [roll1, roll2],
                    result: roll1.total > roll2.total ? roll1 : roll2,
                    type: 'advantage'
                };
            },
            rollWithDisadvantage: (diceNotation) => {
                const roll1 = this.diceRoller.roll(diceNotation);
                const roll2 = this.diceRoller.roll(diceNotation);
                return {
                    rolls: [roll1, roll2],
                    result: roll1.total < roll2.total ? roll1 : roll2,
                    type: 'disadvantage'
                };
            },
            createCustomDie: (sides, modifier) => {
                return {
                    sides: sides,
                    modifier: modifier || 0,
                    roll: () => Math.floor(Math.random() * sides) + 1 + (modifier || 0)
                };
            }
        };
    }

    setupCampaignManagement() {
        this.campaignManager = {
            createCampaign: (campaignData) => {
                return {
                    campaignId: this.generateId(),
                    name: campaignData.name,
                    description: campaignData.description,
                    dm: campaignData.dm,
                    players: [],
                    sessions: [],
                    npcs: [],
                    locations: [],
                    quests: [],
                    created: new Date()
                };
            },
            addPlayer: (campaignId, playerId, characterId) => {
                return {
                    campaignId: campaignId,
                    playerId: playerId,
                    characterId: characterId,
                    joined: new Date()
                };
            },
            createSession: (campaignId, sessionData) => {
                return {
                    sessionId: this.generateId(),
                    campaignId: campaignId,
                    title: sessionData.title,
                    summary: sessionData.summary,
                    date: sessionData.date || new Date(),
                    participants: sessionData.participants || [],
                    events: [],
                    notes: sessionData.notes || ''
                };
            },
            createNPC: (npcData) => {
                return {
                    npcId: this.generateId(),
                    name: npcData.name,
                    race: npcData.race,
                    class: npcData.class,
                    role: npcData.role,
                    location: npcData.location,
                    personality: npcData.personality,
                    backstory: npcData.backstory,
                    stats: npcData.stats || {}
                };
            },
            trackQuest: (questData) => {
                return {
                    questId: this.generateId(),
                    title: questData.title,
                    description: questData.description,
                    status: 'active',
                    objectives: questData.objectives || [],
                    rewards: questData.rewards || [],
                    created: new Date()
                };
            }
        };
    }

    rollStat() {
        const rolls = [];
        for (let i = 0; i < 4; i++) {
            rolls.push(Math.floor(Math.random() * 6) + 1);
        }
        rolls.sort((a, b) => b - a);
        return rolls.slice(0, 3).reduce((sum, roll) => sum + roll, 0);
    }

    parseDiceNotation(notation) {
        const match = notation.match(/(\d+)?d(\d+)([+-]\d+)?/i);
        if (!match) {
            return { rolls: [], total: 0, modifier: 0 };
        }

        const numDice = parseInt(match[1]) || 1;
        const sides = parseInt(match[2]);
        const modifier = parseInt(match[3]) || 0;

        const rolls = [];
        let total = 0;

        for (let i = 0; i < numDice; i++) {
            const roll = Math.floor(Math.random() * sides) + 1;
            rolls.push(roll);
            total += roll;
        }

        total += modifier;

        return { rolls, total, modifier };
    }

    logGameSession(sessionData) {
        const entry = {
            ...sessionData,
            timestamp: new Date(),
            id: this.generateId()
        };
        return entry;
    }

    generateEncounter(partyLevel, difficulty) {
        return {
            encounterId: this.generateId(),
            partyLevel: partyLevel,
            difficulty: difficulty,
            monsters: [],
            environment: '',
            treasure: [],
            xpReward: 0,
            generated: new Date()
        };
    }

    generateLoot(challengeRating) {
        return {
            coins: {
                copper: 0,
                silver: 0,
                gold: 0,
                platinum: 0
            },
            items: [],
            magicItems: [],
            challengeRating: challengeRating
        };
    }

    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }
}

module.exports = DMLog;