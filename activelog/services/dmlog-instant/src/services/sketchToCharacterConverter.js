const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');
const sharp = require('sharp');
const canvas = require('canvas');
const { createCanvas, loadImage } = canvas;

class SketchToCharacterConverter extends EventEmitter {
    constructor(redisClient, io, logger) {
        super();
        this.redis = redisClient;
        this.io = io;
        this.logger = logger;
        
        // Visual feature recognition patterns
        this.visualFeatures = {
            body_types: {
                'tall_thin': {
                    indicators: ['elongated proportions', 'narrow waist', 'long limbs'],
                    suggested_races: ['elf', 'half-elf'],
                    stat_modifiers: { dexterity: 1 }
                },
                'short_stocky': {
                    indicators: ['broad shoulders', 'short legs', 'muscular build'],
                    suggested_races: ['dwarf', 'halfling'],
                    stat_modifiers: { constitution: 1 }
                },
                'average_build': {
                    indicators: ['balanced proportions', 'medium height'],
                    suggested_races: ['human', 'half-elf'],
                    stat_modifiers: { versatility: 1 }
                },
                'large_muscular': {
                    indicators: ['broad frame', 'defined muscles', 'imposing size'],
                    suggested_races: ['half-orc', 'dragonborn'],
                    stat_modifiers: { strength: 1 }
                }
            },
            
            clothing_armor: {
                'robes': {
                    suggested_classes: ['wizard', 'sorcerer', 'warlock'],
                    equipment: ['spellbook', 'component pouch', 'quarterstaff']
                },
                'leather_armor': {
                    suggested_classes: ['rogue', 'ranger', 'bard'],
                    equipment: ['thieves tools', 'shortbow', 'daggers']
                },
                'plate_armor': {
                    suggested_classes: ['paladin', 'fighter', 'cleric'],
                    equipment: ['longsword', 'shield', 'holy symbol']
                },
                'studded_leather': {
                    suggested_classes: ['ranger', 'rogue', 'bard'],
                    equipment: ['longbow', 'shortsword', 'survival gear']
                },
                'chain_mail': {
                    suggested_classes: ['fighter', 'cleric', 'paladin'],
                    equipment: ['warhammer', 'shield', 'chain mail']
                }
            },
            
            weapons_tools: {
                'sword': {
                    suggested_classes: ['fighter', 'paladin', 'ranger'],
                    combat_style: 'melee_fighter'
                },
                'bow': {
                    suggested_classes: ['ranger', 'fighter', 'rogue'],
                    combat_style: 'ranged_attacker'
                },
                'staff_wand': {
                    suggested_classes: ['wizard', 'sorcerer', 'druid'],
                    combat_style: 'spellcaster'
                },
                'daggers': {
                    suggested_classes: ['rogue', 'bard', 'warlock'],
                    combat_style: 'stealth_attacker'
                },
                'shield': {
                    suggested_classes: ['paladin', 'fighter', 'cleric'],
                    combat_style: 'tank_defender'
                }
            },
            
            facial_features: {
                'pointed_ears': {
                    suggested_races: ['elf', 'half-elf'],
                    traits: ['keen senses', 'fey ancestry']
                },
                'beard': {
                    suggested_races: ['dwarf', 'human'],
                    personality_traits: ['traditional', 'wise', 'stubborn']
                },
                'scales': {
                    suggested_races: ['dragonborn'],
                    traits: ['draconic heritage', 'breath weapon']
                },
                'horns': {
                    suggested_races: ['tiefling'],
                    traits: ['fiendish heritage', 'charismatic']
                },
                'tusks': {
                    suggested_races: ['half-orc'],
                    traits: ['savage attacks', 'relentless endurance']
                }
            },
            
            accessories: {
                'holy_symbol': {
                    suggested_classes: ['cleric', 'paladin'],
                    background: 'acolyte'
                },
                'thieves_tools': {
                    suggested_classes: ['rogue'],
                    background: 'criminal'
                },
                'musical_instrument': {
                    suggested_classes: ['bard'],
                    background: 'entertainer'
                },
                'spell_components': {
                    suggested_classes: ['wizard', 'sorcerer'],
                    background: 'sage'
                },
                'noble_clothing': {
                    backgrounds: ['noble', 'guild artisan'],
                    personality_traits: ['refined', 'privileged']
                }
            }
        };
        
        // Character archetypes for personality generation
        this.characterArchetypes = {
            'warrior': {
                personality: ['brave', 'loyal', 'straightforward'],
                ideals: ['justice', 'honor', 'protection'],
                bonds: ['comrades in arms', 'homeland', 'code of honor'],
                flaws: ['quick to anger', 'suspicious of magic', 'inflexible']
            },
            'scholar': {
                personality: ['curious', 'methodical', 'verbose'],
                ideals: ['knowledge', 'discovery', 'understanding'],
                bonds: ['mentor', 'library', 'ancient mystery'],
                flaws: ['absent-minded', 'condescending', 'physically weak']
            },
            'trickster': {
                personality: ['witty', 'charming', 'unpredictable'],
                ideals: ['freedom', 'creativity', 'change'],
                bonds: ['thieves guild', 'old friend', 'gambling debt'],
                flaws: ['can\'t resist a challenge', 'untrustworthy', 'greedy']
            },
            'protector': {
                personality: ['caring', 'selfless', 'determined'],
                ideals: ['compassion', 'service', 'sacrifice'],
                bonds: ['those they protect', 'fallen comrade', 'sacred duty'],
                flaws: ['overly trusting', 'self-sacrificing', 'judgmental']
            },
            'loner': {
                personality: ['independent', 'observant', 'guarded'],
                ideals: ['self-reliance', 'survival', 'solitude'],
                bonds: ['animal companion', 'wilderness', 'lost love'],
                flaws: ['distrustful', 'antisocial', 'stubborn']
            }
        };
        
        // Color associations for personality and background
        this.colorAssociations = {
            red: ['passionate', 'aggressive', 'brave'],
            blue: ['calm', 'loyal', 'wise'],
            green: ['nature-loving', 'balanced', 'healing'],
            purple: ['mystical', 'noble', 'magical'],
            black: ['mysterious', 'dark', 'brooding'],
            white: ['pure', 'holy', 'peaceful'],
            gold: ['wealthy', 'divine', 'prestigious'],
            brown: ['earthy', 'practical', 'humble']
        };
    }

    async convertSketch(options = {}) {
        try {
            const conversionId = uuidv4();
            const imageData = options.image_data || options.sketch;
            
            if (!imageData) {
                throw new Error('No image data provided');
            }
            
            // Process the sketch
            const analysis = await this._analyzeSketch(imageData);
            const character = await this._generateCharacterFromAnalysis(analysis, options.preferences);
            
            const result = {
                id: conversionId,
                original_image: imageData,
                analysis: analysis,
                character: character,
                confidence_score: this._calculateConfidenceScore(analysis),
                alternative_interpretations: await this._generateAlternatives(analysis),
                created_at: new Date()
            };
            
            // Cache the result
            await this.redis.setex(
                `sketch_conversion:${conversionId}`,
                86400 * 7, // 7 days
                JSON.stringify(result)
            );
            
            this.logger.info(`Converted sketch to character: ${conversionId}`);
            this.io.emit('sketch_converted', { 
                conversionId, 
                characterName: character.name,
                race: character.race,
                class: character.class
            });
            
            return result;
            
        } catch (error) {
            this.logger.error('Error converting sketch:', error);
            throw error;
        }
    }

    async analyzeSketch(options = {}) {
        try {
            const analysisId = uuidv4();
            const imageData = options.image_data || options.sketch;
            
            if (!imageData) {
                throw new Error('No image data provided');
            }
            
            const analysis = await this._analyzeSketch(imageData);
            
            const result = {
                id: analysisId,
                analysis: analysis,
                feature_confidence: this._calculateFeatureConfidence(analysis),
                suggestions: this._generateSuggestions(analysis),
                analyzed_at: new Date()
            };
            
            // Cache the analysis
            await this.redis.setex(
                `sketch_analysis:${analysisId}`,
                86400 * 3, // 3 days
                JSON.stringify(result)
            );
            
            this.logger.info(`Analyzed sketch: ${analysisId}`);
            this.io.emit('sketch_analyzed', { analysisId, features: analysis.detected_features });
            
            return result;
            
        } catch (error) {
            this.logger.error('Error analyzing sketch:', error);
            throw error;
        }
    }

    async _analyzeSketch(imageData) {
        try {
            // Process image data
            const processedImage = await this._preprocessImage(imageData);
            
            // Analyze visual features
            const analysis = {
                image_properties: await this._analyzeImageProperties(processedImage),
                detected_features: await this._detectVisualFeatures(processedImage),
                color_analysis: await this._analyzeColors(processedImage),
                composition: await this._analyzeComposition(processedImage),
                style_indicators: await this._analyzeStyle(processedImage)
            };
            
            return analysis;
            
        } catch (error) {
            this.logger.error('Error in sketch analysis:', error);
            throw error;
        }
    }

    async _preprocessImage(imageData) {
        try {
            let buffer;
            
            // Handle different image data formats
            if (typeof imageData === 'string' && imageData.startsWith('data:')) {
                // Base64 data URL
                const base64Data = imageData.split(',')[1];
                buffer = Buffer.from(base64Data, 'base64');
            } else if (Buffer.isBuffer(imageData)) {
                buffer = imageData;
            } else {
                throw new Error('Unsupported image data format');
            }
            
            // Use Sharp to process the image
            const processed = await sharp(buffer)
                .resize(512, 512, { fit: 'inside' })
                .greyscale()
                .normalize()
                .toBuffer();
            
            return processed;
            
        } catch (error) {
            this.logger.error('Error preprocessing image:', error);
            throw error;
        }
    }

    async _analyzeImageProperties(imageBuffer) {
        try {
            const metadata = await sharp(imageBuffer).metadata();
            
            return {
                width: metadata.width,
                height: metadata.height,
                aspect_ratio: metadata.width / metadata.height,
                format: metadata.format,
                channels: metadata.channels,
                density: metadata.density
            };
            
        } catch (error) {
            this.logger.error('Error analyzing image properties:', error);
            return {};
        }
    }

    async _detectVisualFeatures(imageBuffer) {
        try {
            // Simulate feature detection with rule-based analysis
            // In a real implementation, this would use computer vision/AI
            const features = {
                body_type: this._detectBodyType(),
                clothing_armor: this._detectClothingArmor(),
                weapons_tools: this._detectWeaponsTools(),
                facial_features: this._detectFacialFeatures(),
                accessories: this._detectAccessories(),
                pose: this._detectPose(),
                details: this._detectDetails()
            };
            
            return features;
            
        } catch (error) {
            this.logger.error('Error detecting visual features:', error);
            return {};
        }
    }

    async _analyzeColors(imageBuffer) {
        try {
            // Extract dominant colors from the image
            const { dominant } = await sharp(imageBuffer).stats();
            
            const colors = {
                primary_colors: this._identifyPrimaryColors(dominant),
                color_harmony: this._analyzeColorHarmony(dominant),
                brightness: this._calculateBrightness(dominant),
                contrast: this._calculateContrast(dominant)
            };
            
            return colors;
            
        } catch (error) {
            this.logger.error('Error analyzing colors:', error);
            return {};
        }
    }

    async _analyzeComposition(imageBuffer) {
        return {
            figure_position: 'center', // Simplified
            viewing_angle: 'front',
            detail_level: 'medium',
            line_style: 'sketch'
        };
    }

    async _analyzeStyle(imageBuffer) {
        return {
            art_style: 'sketch',
            detail_level: 'medium',
            realism_level: 'stylized',
            technique: 'line_art'
        };
    }

    // Feature detection methods (simplified for demonstration)
    _detectBodyType() {
        const bodyTypes = Object.keys(this.visualFeatures.body_types);
        return this._randomChoice(bodyTypes);
    }

    _detectClothingArmor() {
        const clothingTypes = Object.keys(this.visualFeatures.clothing_armor);
        return this._randomChoice(clothingTypes);
    }

    _detectWeaponsTools() {
        const weapons = Object.keys(this.visualFeatures.weapons_tools);
        return Math.random() > 0.3 ? this._randomChoice(weapons) : null;
    }

    _detectFacialFeatures() {
        const features = Object.keys(this.visualFeatures.facial_features);
        const detectedFeatures = [];
        
        // Randomly detect 0-2 facial features
        const numFeatures = Math.floor(Math.random() * 3);
        for (let i = 0; i < numFeatures; i++) {
            const feature = this._randomChoice(features);
            if (!detectedFeatures.includes(feature)) {
                detectedFeatures.push(feature);
            }
        }
        
        return detectedFeatures;
    }

    _detectAccessories() {
        const accessories = Object.keys(this.visualFeatures.accessories);
        return Math.random() > 0.5 ? this._randomChoice(accessories) : null;
    }

    _detectPose() {
        const poses = ['standing', 'sitting', 'action', 'portrait', 'profile'];
        return this._randomChoice(poses);
    }

    _detectDetails() {
        return {
            sketch_quality: Math.random() > 0.5 ? 'detailed' : 'simple',
            line_weight: Math.random() > 0.5 ? 'bold' : 'light',
            shading: Math.random() > 0.3 ? 'present' : 'minimal'
        };
    }

    async _generateCharacterFromAnalysis(analysis, preferences = {}) {
        try {
            // Determine race based on facial features and body type
            const race = this._determineRace(analysis, preferences);
            
            // Determine class based on clothing, weapons, and accessories
            const characterClass = this._determineClass(analysis, preferences);
            
            // Generate stats based on race and class
            const stats = this._generateStats(race, characterClass);
            
            // Generate personality based on analysis and archetype
            const personality = this._generatePersonality(analysis, characterClass);
            
            // Generate backstory based on visual elements
            const backstory = this._generateBackstory(analysis, race, characterClass);
            
            const character = {
                // Basic info
                name: preferences.name || this._generateCharacterName(race),
                race: race,
                class: characterClass,
                level: preferences.level || 1,
                
                // Stats
                stats: stats,
                
                // Personality
                personality_traits: personality.traits,
                ideals: personality.ideals,
                bonds: personality.bonds,
                flaws: personality.flaws,
                
                // Background
                background: this._determineBackground(analysis),
                backstory: backstory,
                
                // Equipment
                equipment: this._determineEquipment(analysis, characterClass),
                
                // Physical appearance
                physical_description: this._generatePhysicalDescription(analysis, race),
                
                // Skills and abilities
                skills: this._determineSkills(characterClass, analysis),
                spells: characterClass.includes('spell') ? this._generateSpells(characterClass) : [],
                
                // Source information
                created_from: 'sketch_analysis',
                source_features: analysis.detected_features
            };
            
            return character;
            
        } catch (error) {
            this.logger.error('Error generating character from analysis:', error);
            throw error;
        }
    }

    _determineRace(analysis, preferences = {}) {
        if (preferences.race) return preferences.race;
        
        const features = analysis.detected_features;
        let raceScores = {};
        
        // Score races based on facial features
        if (features.facial_features) {
            for (const feature of features.facial_features) {
                if (this.visualFeatures.facial_features[feature]) {
                    const suggestedRaces = this.visualFeatures.facial_features[feature].suggested_races;
                    for (const race of suggestedRaces) {
                        raceScores[race] = (raceScores[race] || 0) + 2;
                    }
                }
            }
        }
        
        // Score races based on body type
        if (features.body_type && this.visualFeatures.body_types[features.body_type]) {
            const suggestedRaces = this.visualFeatures.body_types[features.body_type].suggested_races;
            for (const race of suggestedRaces) {
                raceScores[race] = (raceScores[race] || 0) + 1;
            }
        }
        
        // Default to human if no clear indicators
        if (Object.keys(raceScores).length === 0) {
            return 'human';
        }
        
        // Return highest scoring race
        const sortedRaces = Object.entries(raceScores).sort((a, b) => b[1] - a[1]);
        return sortedRaces[0][0];
    }

    _determineClass(analysis, preferences = {}) {
        if (preferences.class) return preferences.class;
        
        const features = analysis.detected_features;
        let classScores = {};
        
        // Score classes based on clothing/armor
        if (features.clothing_armor && this.visualFeatures.clothing_armor[features.clothing_armor]) {
            const suggestedClasses = this.visualFeatures.clothing_armor[features.clothing_armor].suggested_classes;
            for (const charClass of suggestedClasses) {
                classScores[charClass] = (classScores[charClass] || 0) + 2;
            }
        }
        
        // Score classes based on weapons/tools
        if (features.weapons_tools && this.visualFeatures.weapons_tools[features.weapons_tools]) {
            const suggestedClasses = this.visualFeatures.weapons_tools[features.weapons_tools].suggested_classes;
            for (const charClass of suggestedClasses) {
                classScores[charClass] = (classScores[charClass] || 0) + 2;
            }
        }
        
        // Score classes based on accessories
        if (features.accessories && this.visualFeatures.accessories[features.accessories]) {
            const suggestedClasses = this.visualFeatures.accessories[features.accessories].suggested_classes || [];
            for (const charClass of suggestedClasses) {
                classScores[charClass] = (classScores[charClass] || 0) + 1;
            }
        }
        
        // Default to fighter if no clear indicators
        if (Object.keys(classScores).length === 0) {
            return 'fighter';
        }
        
        // Return highest scoring class
        const sortedClasses = Object.entries(classScores).sort((a, b) => b[1] - a[1]);
        return sortedClasses[0][0];
    }

    _generateStats(race, characterClass) {
        // Base stats
        const stats = {
            strength: this._rollStat(),
            dexterity: this._rollStat(),
            constitution: this._rollStat(),
            intelligence: this._rollStat(),
            wisdom: this._rollStat(),
            charisma: this._rollStat()
        };
        
        // Apply racial modifiers
        this._applyRacialModifiers(stats, race);
        
        // Boost primary stats for class
        this._applyClassStatBoosts(stats, characterClass);
        
        return stats;
    }

    _rollStat() {
        // 4d6 drop lowest
        const rolls = [];
        for (let i = 0; i < 4; i++) {
            rolls.push(Math.floor(Math.random() * 6) + 1);
        }
        rolls.sort((a, b) => b - a);
        return rolls.slice(0, 3).reduce((sum, val) => sum + val, 0);
    }

    _applyRacialModifiers(stats, race) {
        const modifiers = {
            'human': { strength: 1, dexterity: 1, constitution: 1, intelligence: 1, wisdom: 1, charisma: 1 },
            'elf': { dexterity: 2 },
            'dwarf': { constitution: 2 },
            'halfling': { dexterity: 2 },
            'half-orc': { strength: 2, constitution: 1 },
            'dragonborn': { strength: 2, charisma: 1 },
            'tiefling': { intelligence: 1, charisma: 2 },
            'half-elf': { charisma: 2 }
        };
        
        const raceMods = modifiers[race] || {};
        for (const [stat, modifier] of Object.entries(raceMods)) {
            if (modifier === 1 && race === 'human') {
                stats[stat] = Math.min(20, stats[stat] + 1);
            } else {
                stats[stat] = Math.min(20, stats[stat] + modifier);
            }
        }
    }

    _applyClassStatBoosts(stats, characterClass) {
        const primaryStats = {
            'fighter': ['strength', 'constitution'],
            'wizard': ['intelligence'],
            'rogue': ['dexterity'],
            'cleric': ['wisdom'],
            'ranger': ['dexterity', 'wisdom'],
            'paladin': ['strength', 'charisma'],
            'bard': ['charisma'],
            'sorcerer': ['charisma'],
            'warlock': ['charisma'],
            'barbarian': ['strength', 'constitution'],
            'druid': ['wisdom']
        };
        
        const primary = primaryStats[characterClass] || ['strength'];
        for (const stat of primary) {
            if (stats[stat] < 14) {
                stats[stat] = Math.min(20, stats[stat] + 2);
            }
        }
    }

    _generatePersonality(analysis, characterClass) {
        // Determine archetype based on class and visual features
        let archetype = 'warrior'; // default
        
        if (['wizard', 'sorcerer', 'warlock'].includes(characterClass)) {
            archetype = 'scholar';
        } else if (['rogue', 'bard'].includes(characterClass)) {
            archetype = 'trickster';
        } else if (['cleric', 'paladin'].includes(characterClass)) {
            archetype = 'protector';
        } else if (['ranger', 'druid'].includes(characterClass)) {
            archetype = 'loner';
        }
        
        const archetypeData = this.characterArchetypes[archetype];
        
        return {
            traits: this._selectRandomElements(archetypeData.personality, 2),
            ideals: this._selectRandomElements(archetypeData.ideals, 1),
            bonds: this._selectRandomElements(archetypeData.bonds, 1),
            flaws: this._selectRandomElements(archetypeData.flaws, 1)
        };
    }

    _generateBackstory(analysis, race, characterClass) {
        const backstoryTemplates = [
            `A ${race} ${characterClass} who left their homeland seeking adventure and purpose.`,
            `Born into a family of ${characterClass}s, this ${race} carries on ancient traditions.`,
            `Once a simple ${race}, they discovered their calling as a ${characterClass} after a life-changing event.`,
            `Raised in isolation, this ${race} ${characterClass} has much to learn about the world.`,
            `A veteran ${characterClass} who has seen too much and seeks redemption.`
        ];
        
        return this._randomChoice(backstoryTemplates);
    }

    _determineBackground(analysis) {
        const backgrounds = ['acolyte', 'criminal', 'folk hero', 'noble', 'sage', 'soldier', 'charlatan', 'entertainer', 'guild artisan', 'hermit', 'outlander', 'sailor'];
        
        // Try to match background to detected accessories or features
        if (analysis.detected_features.accessories) {
            const accessory = analysis.detected_features.accessories;
            if (this.visualFeatures.accessories[accessory] && this.visualFeatures.accessories[accessory].background) {
                return this.visualFeatures.accessories[accessory].background;
            }
        }
        
        return this._randomChoice(backgrounds);
    }

    _determineEquipment(analysis, characterClass) {
        const equipment = [];
        
        // Add class-based starting equipment
        const classEquipment = {
            'fighter': ['longsword', 'shield', 'chain mail'],
            'wizard': ['quarterstaff', 'spellbook', 'component pouch'],
            'rogue': ['shortsword', 'thieves\' tools', 'leather armor'],
            'cleric': ['mace', 'shield', 'holy symbol'],
            'ranger': ['longbow', 'shortsword', 'leather armor']
        };
        
        equipment.push(...(classEquipment[characterClass] || ['club', 'leather armor']));
        
        // Add equipment based on detected features
        if (analysis.detected_features.weapons_tools && this.visualFeatures.weapons_tools[analysis.detected_features.weapons_tools]) {
            const weaponEquipment = this.visualFeatures.weapons_tools[analysis.detected_features.weapons_tools].suggested_classes[0];
            if (classEquipment[weaponEquipment]) {
                equipment.push(...classEquipment[weaponEquipment]);
            }
        }
        
        // Remove duplicates
        return [...new Set(equipment)];
    }

    _generatePhysicalDescription(analysis, race) {
        const features = analysis.detected_features;
        let description = `This ${race} has`;
        
        // Add body type description
        if (features.body_type) {
            const bodyTypeData = this.visualFeatures.body_types[features.body_type];
            description += ` a ${features.body_type.replace('_', ' ')} build`;
        }
        
        // Add facial features
        if (features.facial_features && features.facial_features.length > 0) {
            description += ` and notable ${features.facial_features.join(' and ')}`;
        }
        
        // Add clothing description
        if (features.clothing_armor) {
            description += `. They wear ${features.clothing_armor.replace('_', ' ')}`;
        }
        
        description += '.';
        return description;
    }

    _determineSkills(characterClass, analysis) {
        const classSkills = {
            'fighter': ['Athletics', 'Intimidation'],
            'wizard': ['Arcana', 'History'],
            'rogue': ['Stealth', 'Sleight of Hand'],
            'cleric': ['Medicine', 'Religion'],
            'ranger': ['Survival', 'Animal Handling'],
            'bard': ['Performance', 'Persuasion']
        };
        
        return classSkills[characterClass] || ['Athletics', 'Perception'];
    }

    _generateSpells(characterClass) {
        const spells = {
            'wizard': ['Magic Missile', 'Shield', 'Detect Magic'],
            'cleric': ['Cure Wounds', 'Sacred Flame', 'Guidance'],
            'sorcerer': ['Fire Bolt', 'Mage Armor', 'Prestidigitation'],
            'warlock': ['Eldritch Blast', 'Hex', 'Arms of Hadar']
        };
        
        return spells[characterClass] || [];
    }

    _generateCharacterName(race) {
        const names = {
            'human': ['Aerdrie', 'Berris', 'Cithreth', 'Enna', 'Galinndan', 'Hadarai', 'Lamlis', 'Laucian'],
            'elf': ['Adran', 'Aramil', 'Aranea', 'Berrian', 'Dayereth', 'Enna', 'Galinndan', 'Hadarai'],
            'dwarf': ['Adrik', 'Alberich', 'Baern', 'Barendd', 'Brottor', 'Bruenor', 'Dain', 'Darrak'],
            'halfling': ['Alton', 'Ander', 'Cade', 'Corrin', 'Eldon', 'Errich', 'Finnan', 'Garret'],
            'half-orc': ['Dench', 'Feng', 'Gell', 'Henk', 'Holg', 'Imsh', 'Keth', 'Krusk'],
            'dragonborn': ['Arjhan', 'Balasar', 'Bharash', 'Donaar', 'Ghesh', 'Heskan', 'Kriv', 'Medrash'],
            'tiefling': ['Akmenos', 'Amnon', 'Barakas', 'Damakos', 'Ekemon', 'Iados', 'Kairon', 'Leucis'],
            'half-elf': ['Aerdrie', 'Ahvak', 'Aramil', 'Aranea', 'Berrian', 'Cillirath', 'Dayereth', 'Enna']
        };
        
        const raceNames = names[race] || names['human'];
        return this._randomChoice(raceNames);
    }

    async _generateAlternatives(analysis) {
        const alternatives = [];
        
        // Generate 2-3 alternative interpretations
        for (let i = 0; i < 3; i++) {
            const altCharacter = await this._generateCharacterFromAnalysis(analysis, {});
            alternatives.push({
                interpretation: `Alternative ${i + 1}`,
                character: altCharacter,
                reasoning: `Based on different emphasis of detected features`
            });
        }
        
        return alternatives;
    }

    _calculateConfidenceScore(analysis) {
        let confidence = 0.5; // Base confidence
        
        // Increase confidence based on detected features
        const features = analysis.detected_features;
        
        if (features.facial_features && features.facial_features.length > 0) {
            confidence += 0.1 * features.facial_features.length;
        }
        
        if (features.weapons_tools) confidence += 0.15;
        if (features.accessories) confidence += 0.1;
        if (features.clothing_armor) confidence += 0.1;
        
        // Image quality factors
        if (analysis.style_indicators && analysis.style_indicators.detail_level === 'high') {
            confidence += 0.1;
        }
        
        return Math.min(confidence, 0.95); // Cap at 95%
    }

    _calculateFeatureConfidence(analysis) {
        const features = analysis.detected_features;
        const confidence = {};
        
        for (const [category, value] of Object.entries(features)) {
            if (value && value !== null) {
                confidence[category] = Math.random() * 0.3 + 0.6; // 60-90% confidence
            }
        }
        
        return confidence;
    }

    _generateSuggestions(analysis) {
        const suggestions = [];
        
        // Suggest improvements based on detected features
        if (!analysis.detected_features.weapons_tools) {
            suggestions.push('Add weapons or tools to better determine character class');
        }
        
        if (!analysis.detected_features.accessories) {
            suggestions.push('Include accessories or symbols to help determine background');
        }
        
        if (analysis.detected_features.facial_features.length === 0) {
            suggestions.push('Add distinctive facial features to help determine race');
        }
        
        return suggestions;
    }

    // Helper methods
    _identifyPrimaryColors(dominant) {
        // Simplified color identification
        return ['sketch_grey', 'line_black'];
    }

    _analyzeColorHarmony(dominant) {
        return 'monochromatic';
    }

    _calculateBrightness(dominant) {
        return 0.5;
    }

    _calculateContrast(dominant) {
        return 0.7;
    }

    _selectRandomElements(array, count) {
        const shuffled = [...array].sort(() => 0.5 - Math.random());
        return shuffled.slice(0, count);
    }

    _randomChoice(array) {
        return array[Math.floor(Math.random() * array.length)];
    }

    async getStats() {
        try {
            const keys = await this.redis.keys('sketch_conversion:*');
            const totalConversions = keys.length;
            
            let totalConfidence = 0;
            let classDistribution = {};
            let raceDistribution = {};
            
            for (const key of keys.slice(0, 100)) {
                const data = await this.redis.get(key);
                if (data) {
                    const conversion = JSON.parse(data);
                    totalConfidence += conversion.confidence_score || 0;
                    
                    if (conversion.character) {
                        const charClass = conversion.character.class;
                        const race = conversion.character.race;
                        
                        classDistribution[charClass] = (classDistribution[charClass] || 0) + 1;
                        raceDistribution[race] = (raceDistribution[race] || 0) + 1;
                    }
                }
            }
            
            return {
                total_conversions: totalConversions,
                average_confidence: totalConversions > 0 ? totalConfidence / totalConversions : 0,
                popular_classes: classDistribution,
                popular_races: raceDistribution,
                processed_today: 0 // Could implement daily tracking
            };
            
        } catch (error) {
            this.logger.error('Error getting conversion stats:', error);
            return {
                total_conversions: 0,
                average_confidence: 0,
                popular_classes: {},
                popular_races: {},
                processed_today: 0
            };
        }
    }
}

module.exports = SketchToCharacterConverter;