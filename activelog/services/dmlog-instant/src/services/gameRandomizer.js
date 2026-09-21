const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');
const _ = require('lodash');

class GameRandomizer extends EventEmitter {
    constructor(redisClient, socketServer, logger) {
        super();
        this.redis = redisClient;
        this.io = socketServer;
        this.logger = logger;
        
        this.gameElements = new Map();
        this.generatedGames = new Map();
        this.randomTables = new Map();
        
        this.setupEventHandlers();
        this.initializeGameElements();
        this.loadRandomTables();
    }

    setupEventHandlers() {
        this.on('game_generated', this.handleGameGenerated.bind(this));
        this.on('elements_updated', this.handleElementsUpdated.bind(this));
    }

    initializeGameElements() {
        // Core D&D elements
        this.gameElements.set('races', [
            { name: 'Human', traits: ['Versatile', 'Ambitious'], modifiers: { charisma: 1, wisdom: 1 } },
            { name: 'Elf', traits: ['Graceful', 'Long-lived'], modifiers: { dexterity: 2 } },
            { name: 'Dwarf', traits: ['Hardy', 'Proud'], modifiers: { constitution: 2 } },
            { name: 'Halfling', traits: ['Lucky', 'Brave'], modifiers: { dexterity: 2 } },
            { name: 'Dragonborn', traits: ['Proud', 'Breath Weapon'], modifiers: { strength: 2, charisma: 1 } },
            { name: 'Gnome', traits: ['Curious', 'Magical'], modifiers: { intelligence: 2 } },
            { name: 'Half-Elf', traits: ['Charismatic', 'Adaptable'], modifiers: { charisma: 2 } },
            { name: 'Half-Orc', traits: ['Strong', 'Fierce'], modifiers: { strength: 2, constitution: 1 } },
            { name: 'Tiefling', traits: ['Infernal', 'Charismatic'], modifiers: { charisma: 2, intelligence: 1 } }
        ]);

        this.gameElements.set('classes', [
            { name: 'Fighter', hitDie: 10, primaryAbility: 'Strength', savingThrows: ['Strength', 'Constitution'] },
            { name: 'Wizard', hitDie: 6, primaryAbility: 'Intelligence', savingThrows: ['Intelligence', 'Wisdom'] },
            { name: 'Rogue', hitDie: 8, primaryAbility: 'Dexterity', savingThrows: ['Dexterity', 'Intelligence'] },
            { name: 'Cleric', hitDie: 8, primaryAbility: 'Wisdom', savingThrows: ['Wisdom', 'Charisma'] },
            { name: 'Ranger', hitDie: 10, primaryAbility: 'Dexterity', savingThrows: ['Strength', 'Dexterity'] },
            { name: 'Paladin', hitDie: 10, primaryAbility: 'Strength', savingThrows: ['Wisdom', 'Charisma'] },
            { name: 'Barbarian', hitDie: 12, primaryAbility: 'Strength', savingThrows: ['Strength', 'Constitution'] },
            { name: 'Bard', hitDie: 8, primaryAbility: 'Charisma', savingThrows: ['Dexterity', 'Charisma'] },
            { name: 'Druid', hitDie: 8, primaryAbility: 'Wisdom', savingThrows: ['Intelligence', 'Wisdom'] },
            { name: 'Monk', hitDie: 8, primaryAbility: 'Dexterity', savingThrows: ['Strength', 'Dexterity'] },
            { name: 'Sorcerer', hitDie: 6, primaryAbility: 'Charisma', savingThrows: ['Constitution', 'Charisma'] },
            { name: 'Warlock', hitDie: 8, primaryAbility: 'Charisma', savingThrows: ['Wisdom', 'Charisma'] }
        ]);

        this.gameElements.set('backgrounds', [
            { name: 'Acolyte', skills: ['Insight', 'Religion'], languages: 2, equipment: ['Holy Symbol', 'Prayer Book'] },
            { name: 'Criminal', skills: ['Deception', 'Stealth'], toolProficiencies: ['Thieves Tools'], languages: 0 },
            { name: 'Folk Hero', skills: ['Animal Handling', 'Survival'], toolProficiencies: ['Artisan Tools'], languages: 0 },
            { name: 'Noble', skills: ['History', 'Persuasion'], toolProficiencies: ['Gaming Set'], languages: 1 },
            { name: 'Sage', skills: ['Arcana', 'History'], languages: 2, equipment: ['Ink', 'Quill', 'Small Knife'] },
            { name: 'Soldier', skills: ['Athletics', 'Intimidation'], toolProficiencies: ['Vehicles (Land)'], languages: 0 }
        ]);

        this.gameElements.set('environments', [
            { name: 'Forest', encounters: ['Owlbear', 'Dryad', 'Giant Spider'], hazards: ['Thick Undergrowth', 'Quicksand'] },
            { name: 'Dungeon', encounters: ['Goblin', 'Skeleton', 'Gelatinous Cube'], hazards: ['Pit Trap', 'Poison Gas'] },
            { name: 'City', encounters: ['Thieves Guild', 'Noble', 'City Watch'], hazards: ['Pickpockets', 'Politics'] },
            { name: 'Mountain', encounters: ['Dragon', 'Giant Eagle', 'Stone Giant'], hazards: ['Avalanche', 'Thin Air'] },
            { name: 'Desert', encounters: ['Sphinx', 'Mummy', 'Giant Scorpion'], hazards: ['Sandstorm', 'Dehydration'] },
            { name: 'Ocean', encounters: ['Kraken', 'Merfolk', 'Sahuagin'], hazards: ['Storm', 'Sea Monsters'] }
        ]);

        this.gameElements.set('questTypes', [
            { name: 'Rescue Mission', objectives: ['Save someone', 'Escape safely'], difficulty: 'Medium' },
            { name: 'Treasure Hunt', objectives: ['Find treasure', 'Overcome guardians'], difficulty: 'Hard' },
            { name: 'Investigation', objectives: ['Gather clues', 'Solve mystery'], difficulty: 'Easy' },
            { name: 'Escort Mission', objectives: ['Protect NPC', 'Reach destination'], difficulty: 'Medium' },
            { name: 'Conquest', objectives: ['Defeat enemy', 'Claim territory'], difficulty: 'Hard' },
            { name: 'Diplomacy', objectives: ['Negotiate peace', 'Avoid conflict'], difficulty: 'Medium' }
        ]);

        this.gameElements.set('villains', [
            { name: 'Lich', type: 'Undead', motivations: ['Immortality', 'Knowledge', 'Power'], cr: 21 },
            { name: 'Adult Red Dragon', type: 'Dragon', motivations: ['Treasure', 'Territory', 'Pride'], cr: 17 },
            { name: 'Vampire Lord', type: 'Undead', motivations: ['Blood', 'Control', 'Revenge'], cr: 13 },
            { name: 'Mind Flayer', type: 'Aberration', motivations: ['Brains', 'Domination', 'Knowledge'], cr: 7 },
            { name: 'Cult Leader', type: 'Humanoid', motivations: ['Religious Zealotry', 'Power', 'Chaos'], cr: 9 },
            { name: 'Corrupt Noble', type: 'Humanoid', motivations: ['Wealth', 'Status', 'Control'], cr: 5 }
        ]);

        this.gameElements.set('treasures', [
            { name: 'Legendary Sword', type: 'Weapon', rarity: 'Legendary', properties: ['+3 Enhancement', 'Flame Tongue'] },
            { name: 'Ring of Wishes', type: 'Ring', rarity: 'Legendary', properties: ['3 Wishes', 'One Use'] },
            { name: 'Bag of Holding', type: 'Wondrous Item', rarity: 'Uncommon', properties: ['Extra-dimensional Storage'] },
            { name: 'Cloak of Elvenkind', type: 'Wondrous Item', rarity: 'Uncommon', properties: ['Stealth Advantage'] },
            { name: 'Potion of Healing', type: 'Potion', rarity: 'Common', properties: ['Restores 2d4+2 HP'] },
            { name: 'Ancient Tome', type: 'Book', rarity: 'Rare', properties: ['Contains Forgotten Spells'] }
        ]);

        this.gameElements.set('plotTwists', [
            { name: 'Betrayal', description: 'A trusted ally reveals their true allegiance', impact: 'Major' },
            { name: 'False Identity', description: 'Someone is not who they appear to be', impact: 'Medium' },
            { name: 'Hidden Curse', description: 'A blessing turns out to be a curse', impact: 'Major' },
            { name: 'Time Loop', description: 'Events repeat until a condition is met', impact: 'Extreme' },
            { name: 'Moral Dilemma', description: 'The right choice has terrible consequences', impact: 'Medium' },
            { name: 'Divine Intervention', description: 'A deity directly interferes', impact: 'Major' }
        ]);
    }

    loadRandomTables() {
        // Weather table
        this.randomTables.set('weather', [
            { result: 'Clear skies', effect: 'None', probability: 40 },
            { result: 'Light rain', effect: 'Disadvantage on Perception (sight)', probability: 20 },
            { result: 'Heavy rain', effect: 'Heavily obscured beyond 100 feet', probability: 15 },
            { result: 'Fog', effect: 'Lightly obscured beyond 60 feet', probability: 10 },
            { result: 'Strong wind', effect: 'Disadvantage on ranged attacks', probability: 10 },
            { result: 'Storm', effect: 'Lightning and thunder, frightening effects', probability: 5 }
        ]);

        // Random encounters
        this.randomTables.set('forestEncounters', [
            { result: '1d4 Wolves', cr: 2, type: 'Combat' },
            { result: 'Friendly Druid', cr: 0, type: 'Social' },
            { result: 'Hidden Grove', cr: 0, type: 'Exploration' },
            { result: '1 Owlbear', cr: 3, type: 'Combat' },
            { result: 'Lost Traveler', cr: 0, type: 'Social' },
            { result: 'Ancient Ruins', cr: 0, type: 'Exploration' }
        ]);

        // Tavern names
        this.randomTables.set('tavernNames', [
            'The Prancing Pony', 'The Drunken Dragon', 'The Silver Tankard',
            'The Weary Traveler', 'The Golden Griffin', 'The Rusty Anchor',
            'The Dancing Bear', 'The Crooked Crown', 'The Laughing Maiden'
        ]);

        // NPC motivations
        this.randomTables.set('npcMotivations', [
            { motivation: 'Revenge', description: 'Seeks to right a past wrong' },
            { motivation: 'Love', description: 'Driven by romantic feelings' },
            { motivation: 'Greed', description: 'Wants wealth and material goods' },
            { motivation: 'Power', description: 'Seeks control and influence' },
            { motivation: 'Knowledge', description: 'Pursues learning and discovery' },
            { motivation: 'Redemption', description: 'Trying to atone for past mistakes' },
            { motivation: 'Survival', description: 'Fighting to stay alive' },
            { motivation: 'Family', description: 'Protecting loved ones' }
        ]);
    }

    async generateRandomGame(gameData = {}) {
        try {
            const gameId = uuidv4();
            const preferences = gameData.preferences || {};
            
            // Generate core game elements
            const game = {
                id: gameId,
                title: this.generateGameTitle(),
                setting: await this.generateSetting(preferences),
                characters: await this.generateCharacters(preferences),
                campaign: await this.generateCampaign(preferences),
                encounters: await this.generateEncounters(preferences),
                treasure: await this.generateTreasure(preferences),
                plotHooks: await this.generatePlotHooks(preferences),
                npcs: await this.generateNPCs(preferences),
                locations: await this.generateLocations(preferences),
                timeline: await this.generateTimeline(preferences),
                rules: await this.generateRuleVariants(preferences),
                createdAt: new Date(),
                complexity: preferences.complexity || 'medium'
            };

            // Apply any specific preferences
            if (preferences.theme) {
                game.theme = preferences.theme;
                await this.applyTheme(game, preferences.theme);
            }

            if (preferences.playerCount) {
                game.playerCount = preferences.playerCount;
                await this.adjustForPlayerCount(game, preferences.playerCount);
            }

            // Store generated game
            this.generatedGames.set(gameId, game);
            await this.redis.hset('generated_games', gameId, JSON.stringify(game));

            this.logger.info('Random game generated', {
                gameId,
                title: game.title,
                complexity: game.complexity,
                playerCount: game.playerCount
            });

            this.emit('game_generated', game);

            return { success: true, gameId, game };
        } catch (error) {
            this.logger.error('Failed to generate random game', { error: error.message });
            throw new Error(`Game generation failed: ${error.message}`);
        }
    }

    async generateSetting(preferences = {}) {
        const environment = preferences.environment || 
            this.getRandomElement('environments');
        
        const setting = {
            primaryEnvironment: environment,
            climate: this.rollOnTable('weather'),
            culture: this.generateCulture(),
            technology: preferences.technology || this.randomChoice(['Medieval', 'Renaissance', 'Industrial', 'Modern', 'Futuristic']),
            magicLevel: preferences.magicLevel || this.randomChoice(['Low', 'Medium', 'High', 'Extreme']),
            pantheon: this.generatePantheon(),
            conflicts: this.generateConflicts(),
            landmarks: this.generateLandmarks(environment)
        };

        return setting;
    }

    async generateCharacters(preferences = {}) {
        const count = preferences.playerCount || 4;
        const characters = [];

        for (let i = 0; i < count; i++) {
            const race = this.getRandomElement('races');
            const characterClass = this.getRandomElement('classes');
            const background = this.getRandomElement('backgrounds');

            const character = {
                id: uuidv4(),
                name: this.generateCharacterName(race.name),
                race: race,
                class: characterClass,
                background: background,
                level: preferences.startingLevel || 1,
                stats: this.generateStats(),
                personality: this.generatePersonality(),
                backstory: this.generateBackstory(race, characterClass, background),
                goals: this.generateCharacterGoals(),
                equipment: this.generateStartingEquipment(characterClass, background),
                spells: characterClass.name.includes('Wizard') || characterClass.name.includes('Cleric') ? 
                    this.generateSpells(characterClass, 1) : []
            };

            characters.push(character);
        }

        return characters;
    }

    async generateCampaign(preferences = {}) {
        const questType = this.getRandomElement('questTypes');
        const villain = this.getRandomElement('villains');
        
        const campaign = {
            title: this.generateCampaignTitle(questType, villain),
            questType: questType,
            mainVillain: villain,
            theme: preferences.theme || this.randomChoice(['Heroic Fantasy', 'Dark Fantasy', 'Political Intrigue', 'Exploration', 'Horror', 'Comedy']),
            duration: preferences.duration || this.randomChoice(['One-shot', 'Short (2-5 sessions)', 'Medium (6-12 sessions)', 'Long (13+ sessions)']),
            acts: this.generateCampaignActs(questType, villain),
            majorNPCs: this.generateMajorNPCs(),
            factions: this.generateFactions(),
            overarcPlot: this.generateOverarcPlot(questType, villain),
            playerHooks: this.generatePlayerHooks()
        };

        return campaign;
    }

    async generateEncounters(preferences = {}) {
        const encounters = [];
        const encounterCount = preferences.encounterCount || 8;

        for (let i = 0; i < encounterCount; i++) {
            const encounterType = this.randomChoice(['Combat', 'Social', 'Exploration', 'Puzzle']);
            
            const encounter = {
                id: uuidv4(),
                type: encounterType,
                name: this.generateEncounterName(encounterType),
                description: this.generateEncounterDescription(encounterType),
                difficulty: this.randomChoice(['Easy', 'Medium', 'Hard', 'Deadly']),
                environment: this.getRandomElement('environments').name,
                participants: this.generateEncounterParticipants(encounterType),
                objectives: this.generateEncounterObjectives(encounterType),
                rewards: this.generateEncounterRewards(),
                complications: this.generateEncounterComplications()
            };

            encounters.push(encounter);
        }

        return encounters;
    }

    generateGameTitle() {
        const prefixes = ['The', 'Chronicles of', 'Tales of', 'Legends of', 'The Adventures of', 'Saga of'];
        const subjects = ['Dragon', 'Crystal', 'Shadow', 'Light', 'Crown', 'Sword', 'Temple', 'Tower', 'Kingdom', 'Empire'];
        const suffixes = ['Destiny', 'Mystery', 'Power', 'Glory', 'Doom', 'Hope', 'Vengeance', 'Honor', 'Chaos', 'Order'];

        const prefix = this.randomChoice(prefixes);
        const subject = this.randomChoice(subjects);
        const suffix = this.randomChoice(suffixes);

        return `${prefix} ${subject} ${this.randomChoice(['of', 'and', '&'])} ${suffix}`;
    }

    generateCharacterName(race) {
        const nameMap = {
            'Human': {
                male: ['Aerdrie', 'Beiro', 'Carric', 'Drannor', 'Enna', 'Galinndan', 'Hadarai'],
                female: ['Adrie', 'Birel', 'Caelynn', 'Dara', 'Enna', 'Galina', 'Halimath']
            },
            'Elf': {
                male: ['Aelar', 'Berris', 'Carric', 'Dayereth', 'Enna', 'Galinndan', 'Hadarai'],
                female: ['Adrie', 'Birel', 'Caelynn', 'Dara', 'Enna', 'Galina', 'Halimath']
            },
            'Dwarf': {
                male: ['Adrik', 'Baern', 'Darrak', 'Eberk', 'Fargrim', 'Gardain', 'Harbek'],
                female: ['Amber', 'Bardryn', 'Diesa', 'Eldeth', 'Gunnloda', 'Helja', 'Hlin']
            },
            'Halfling': {
                male: ['Alton', 'Beau', 'Cade', 'Eldon', 'Garret', 'Lyle', 'Milo'],
                female: ['Andry', 'Bree', 'Callie', 'Cora', 'Euphemia', 'Jillian', 'Kithri']
            }
        };

        const names = nameMap[race] || nameMap['Human'];
        const gender = this.randomChoice(['male', 'female']);
        return this.randomChoice(names[gender]);
    }

    generateStats() {
        const stats = {};
        const abilities = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma'];
        
        abilities.forEach(ability => {
            // Roll 4d6, drop lowest
            const rolls = Array.from({ length: 4 }, () => Math.floor(Math.random() * 6) + 1)
                .sort((a, b) => b - a)
                .slice(0, 3);
            stats[ability] = rolls.reduce((sum, roll) => sum + roll, 0);
        });

        return stats;
    }

    generatePersonality() {
        const traits = [
            'Brave', 'Cowardly', 'Curious', 'Lazy', 'Honest', 'Deceptive',
            'Kind', 'Cruel', 'Patient', 'Impulsive', 'Loyal', 'Treacherous',
            'Optimistic', 'Pessimistic', 'Confident', 'Insecure'
        ];

        const ideals = [
            'Justice', 'Freedom', 'Tradition', 'Knowledge', 'Power', 'Beauty',
            'Balance', 'Redemption', 'Honesty', 'Independence', 'Fairness', 'Glory'
        ];

        const bonds = [
            'Family member', 'Mentor', 'Childhood friend', 'Rival', 'Sacred place',
            'Heirloom weapon', 'Lost love', 'Home town', 'Religious institution', 'Guild'
        ];

        const flaws = [
            'Hot tempered', 'Greedy', 'Arrogant', 'Secretive', 'Vengeful',
            'Addictive personality', 'Overly trusting', 'Coward in face of danger'
        ];

        return {
            traits: this.randomChoice(traits, 2),
            ideals: this.randomChoice(ideals),
            bonds: this.randomChoice(bonds),
            flaws: this.randomChoice(flaws)
        };
    }

    generateBackstory(race, characterClass, background) {
        const backstoryElements = [
            `Born into a ${background.name.toLowerCase()} family`,
            `Discovered their calling as a ${characterClass.name.toLowerCase()} at an early age`,
            `Trained in the ancient traditions of their ${race.name.toLowerCase()} heritage`,
            `Faced a life-changing event that shaped their destiny`,
            `Seeks to prove themselves worthy of their ancestors' legacy`
        ];

        return backstoryElements.join('. ') + '.';
    }

    generateCampaignActs(questType, villain) {
        const acts = [
            {
                number: 1,
                title: 'The Call to Adventure',
                description: `The heroes are drawn into the quest to ${questType.objectives[0].toLowerCase()}`,
                keyEvents: ['Initial hook', 'Meet important NPCs', 'Discover the threat'],
                climax: 'First confrontation with villain\'s agents'
            },
            {
                number: 2,
                title: 'Rising Action',
                description: 'Complications arise as the true scope of the challenge becomes clear',
                keyEvents: ['Gather allies', 'Overcome obstacles', 'Uncover villain\'s plan'],
                climax: 'Major setback or revelation'
            },
            {
                number: 3,
                title: 'Final Confrontation',
                description: `The ultimate showdown with ${villain.name}`,
                keyEvents: ['Prepare for final battle', 'Confront the villain', 'Resolve the quest'],
                climax: 'Defeat the main antagonist'
            }
        ];

        return acts;
    }

    rollOnTable(tableName) {
        const table = this.randomTables.get(tableName);
        if (!table) return null;

        const totalProbability = table.reduce((sum, entry) => sum + (entry.probability || 1), 0);
        let roll = Math.random() * totalProbability;

        for (const entry of table) {
            roll -= (entry.probability || 1);
            if (roll <= 0) {
                return entry;
            }
        }

        return table[table.length - 1]; // Fallback
    }

    getRandomElement(category) {
        const elements = this.gameElements.get(category);
        if (!elements || elements.length === 0) return null;
        return elements[Math.floor(Math.random() * elements.length)];
    }

    randomChoice(array, count = 1) {
        if (!Array.isArray(array)) return array;
        if (count === 1) {
            return array[Math.floor(Math.random() * array.length)];
        }
        return _.sampleSize(array, Math.min(count, array.length));
    }

    async getRandomElements(category, options = {}) {
        try {
            const elements = this.gameElements.get(category);
            if (!elements) {
                throw new Error(`Category ${category} not found`);
            }

            const count = parseInt(options.count) || 1;
            const filter = options.filter;

            let filteredElements = elements;
            if (filter) {
                filteredElements = elements.filter(element => 
                    JSON.stringify(element).toLowerCase().includes(filter.toLowerCase())
                );
            }

            const selectedElements = this.randomChoice(filteredElements, count);
            
            return {
                success: true,
                category,
                elements: Array.isArray(selectedElements) ? selectedElements : [selectedElements],
                total: filteredElements.length
            };
        } catch (error) {
            this.logger.error('Failed to get random elements', { error: error.message, category });
            throw error;
        }
    }

    // Additional generation methods
    generateCulture() {
        const cultures = [
            'Medieval European', 'Ancient Egyptian', 'Viking Norse', 'Feudal Japanese',
            'Arabian Nights', 'Celtic Druidic', 'Roman Empire', 'Ancient Greek',
            'Aztec Empire', 'Oriental Mysticism', 'Wild West', 'Steampunk Victorian'
        ];
        return this.randomChoice(cultures);
    }

    generatePantheon() {
        const pantheon = [];
        const domains = ['War', 'Nature', 'Knowledge', 'Trickery', 'Death', 'Life', 'Light', 'Tempest'];
        
        for (let i = 0; i < 5; i++) {
            pantheon.push({
                name: this.generateDeityName(),
                domain: this.randomChoice(domains),
                alignment: this.randomChoice(['Good', 'Neutral', 'Evil']),
                portfolio: this.generateDeityPortfolio()
            });
        }
        
        return pantheon;
    }

    generateConflicts() {
        const conflicts = [
            'Ancient war between races', 'Religious schism', 'Resource scarcity',
            'Territorial disputes', 'Succession crisis', 'Magical catastrophe aftermath',
            'Trade route disruption', 'Plague or curse', 'Dragon attacks', 'Undead uprising'
        ];
        return this.randomChoice(conflicts, 3);
    }

    generateLandmarks(environment) {
        const landmarkTypes = {
            'Forest': ['Ancient Tree', 'Druid Circle', 'Hidden Grove', 'Abandoned Tower'],
            'Mountain': ['Dragon\'s Peak', 'Dwarven Mines', 'Sky Temple', 'Frozen Lake'],
            'Desert': ['Pyramid', 'Oasis', 'Sand Dunes', 'Ancient City Ruins'],
            'Ocean': ['Mysterious Island', 'Underwater City', 'Whirlpool', 'Lighthouse'],
            'City': ['Grand Cathedral', 'Royal Palace', 'Market Square', 'Thieves\' Quarter'],
            'Dungeon': ['Treasure Chamber', 'Trap Corridor', 'Monster Lair', 'Ancient Prison']
        };

        const landmarks = landmarkTypes[environment.name] || landmarkTypes['Forest'];
        return this.randomChoice(landmarks, 3).map(name => ({
            name,
            description: this.generateLandmarkDescription(name),
            significance: this.randomChoice(['Historical', 'Religious', 'Magical', 'Strategic'])
        }));
    }

    generateLandmarkDescription(name) {
        const descriptions = {
            'Ancient Tree': 'A massive tree that has stood for millennia, its roots deep and branches touching the sky',
            'Druid Circle': 'A ring of standing stones where druids gather to perform their sacred rituals',
            'Hidden Grove': 'A secret clearing known only to a few, where magical creatures feel safe',
            'Abandoned Tower': 'A crumbling spire that once belonged to a powerful wizard, now empty and mysterious'
        };
        return descriptions[name] || 'A place of mystery and wonder that draws adventurers from far and wide';
    }

    async getStats() {
        return {
            totalGames: this.generatedGames.size,
            gameElements: this.gameElements.size,
            randomTables: this.randomTables.size,
            popularCategories: Array.from(this.gameElements.keys()).slice(0, 5)
        };
    }

    // Event handlers
    handleGameGenerated(game) {
        this.logger.info('Game generated successfully', {
            gameId: game.id,
            title: game.title,
            complexity: game.complexity
        });

        this.io.emit('game_generated', {
            gameId: game.id,
            title: game.title,
            playerCount: game.playerCount,
            complexity: game.complexity
        });
    }

    handleElementsUpdated(data) {
        this.logger.info('Game elements updated', data);
    }
}

module.exports = GameRandomizer;