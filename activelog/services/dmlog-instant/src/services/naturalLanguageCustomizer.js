const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');

class NaturalLanguageCustomizer extends EventEmitter {
    constructor(redisClient, io, logger) {
        super();
        this.redis = redisClient;
        this.io = io;
        this.logger = logger;
        
        // Pattern recognition for different game aspects
        this.patterns = {
            campaign_themes: {
                'horror': ['horror', 'scary', 'frightening', 'dark', 'creepy', 'gothic', 'undead', 'supernatural'],
                'political': ['political', 'intrigue', 'court', 'nobles', 'diplomacy', 'scheming', 'power', 'kingdom'],
                'exploration': ['exploration', 'discovery', 'unknown', 'wilderness', 'uncharted', 'journey', 'travel'],
                'urban': ['city', 'urban', 'town', 'streets', 'civilized', 'metropolitan', 'districts'],
                'dungeon_crawl': ['dungeon', 'underground', 'caves', 'tomb', 'ruins', 'ancient', 'treasure'],
                'seafaring': ['ocean', 'sea', 'pirates', 'ships', 'islands', 'sailing', 'maritime', 'naval'],
                'planar': ['planes', 'dimensions', 'otherworldly', 'cosmic', 'multiverse', 'realms', 'portals'],
                'survival': ['survival', 'harsh', 'wilderness', 'post-apocalyptic', 'wasteland', 'resources']
            },
            
            tone_keywords: {
                'serious': ['serious', 'mature', 'realistic', 'gritty', 'dark', 'somber'],
                'light': ['light', 'fun', 'comedic', 'humorous', 'silly', 'whimsical', 'cheerful'],
                'epic': ['epic', 'heroic', 'grand', 'legendary', 'mythic', 'divine', 'world-saving'],
                'mysterious': ['mysterious', 'enigmatic', 'puzzling', 'cryptic', 'secretive', 'hidden'],
                'action': ['action', 'fast-paced', 'combat', 'fighting', 'battles', 'warfare', 'conflict']
            },
            
            difficulty_indicators: {
                'easy': ['easy', 'beginner', 'simple', 'casual', 'relaxed', 'gentle', 'forgiving'],
                'moderate': ['moderate', 'balanced', 'normal', 'standard', 'fair', 'reasonable'],
                'hard': ['hard', 'challenging', 'difficult', 'tough', 'demanding', 'intense'],
                'extreme': ['deadly', 'brutal', 'punishing', 'hardcore', 'nightmare', 'impossible']
            },
            
            character_focus: {
                'roleplay': ['roleplay', 'character', 'story', 'narrative', 'dialogue', 'personality', 'relationships'],
                'combat': ['combat', 'fighting', 'battles', 'tactical', 'strategy', 'warfare', 'encounters'],
                'exploration': ['exploration', 'discovery', 'investigation', 'puzzles', 'secrets', 'mysteries'],
                'social': ['social', 'interaction', 'diplomacy', 'negotiation', 'persuasion', 'politics']
            },
            
            setting_elements: {
                'fantasy_high': ['high fantasy', 'magic', 'wizards', 'dragons', 'elves', 'dwarves', 'magical'],
                'fantasy_low': ['low fantasy', 'realistic', 'grounded', 'minimal magic', 'human-centric'],
                'steampunk': ['steampunk', 'industrial', 'clockwork', 'steam', 'Victorian', 'mechanical'],
                'modern': ['modern', 'contemporary', 'current', 'technology', 'urban fantasy'],
                'futuristic': ['futuristic', 'sci-fi', 'space', 'technology', 'cyberpunk', 'dystopian'],
                'historical': ['historical', 'medieval', 'ancient', 'renaissance', 'period', 'authentic']
            },
            
            pacing_preferences: {
                'fast': ['fast', 'quick', 'rapid', 'speedy', 'immediate', 'instant', 'short sessions'],
                'medium': ['medium', 'moderate', 'balanced', 'normal', 'regular', 'standard'],
                'slow': ['slow', 'deliberate', 'methodical', 'detailed', 'thorough', 'deep', 'immersive']
            },
            
            player_agency: {
                'high': ['freedom', 'choice', 'sandbox', 'open', 'player-driven', 'agency', 'flexible'],
                'medium': ['guided', 'structured', 'balanced', 'some choice', 'directed'],
                'low': ['linear', 'railroad', 'story-driven', 'predetermined', 'scripted', 'fixed']
            },
            
            content_preferences: {
                'family_friendly': ['family', 'kid-friendly', 'clean', 'wholesome', 'appropriate', 'innocent'],
                'mature': ['mature', 'adult', 'serious themes', 'complex', 'realistic consequences'],
                'dark': ['dark', 'grim', 'disturbing', 'psychological', 'horror', 'tragic'],
                'romantic': ['romance', 'love', 'relationships', 'emotional', 'intimate', 'passion']
            }
        };
        
        // Common phrases and their interpretations
        this.phrasePatterns = {
            'I want': 'desire',
            'I like': 'preference',
            'I hate': 'dislike',
            'I love': 'strong_preference', 
            'no': 'exclude',
            'avoid': 'exclude',
            'include': 'include',
            'focus on': 'emphasize',
            'less': 'reduce',
            'more': 'increase',
            'similar to': 'reference'
        };
        
        // Game references for inspiration
        this.gameReferences = {
            'lord of the rings': { theme: 'epic fantasy', tone: 'heroic', setting: 'fantasy_high' },
            'game of thrones': { theme: 'political', tone: 'gritty', content: 'mature' },
            'harry potter': { theme: 'magical school', tone: 'light', setting: 'fantasy_high' },
            'lovecraft': { theme: 'horror', tone: 'mysterious', content: 'dark' },
            'pirates of the caribbean': { theme: 'seafaring', tone: 'light', setting: 'historical' },
            'skyrim': { theme: 'exploration', tone: 'epic', setting: 'fantasy_high' },
            'mass effect': { theme: 'space opera', tone: 'epic', setting: 'futuristic' },
            'witcher': { theme: 'monster hunting', tone: 'mature', content: 'dark' },
            'avatar last airbender': { theme: 'elemental', tone: 'light', content: 'family_friendly' }
        };
    }

    async parseCustomization(options = {}) {
        try {
            const customizationId = uuidv4();
            const input = options.description || options.input || '';
            
            if (!input.trim()) {
                throw new Error('No customization description provided');
            }
            
            const parsed = {
                id: customizationId,
                original_input: input,
                processed_at: new Date(),
                
                // Core game aspects
                themes: this._extractThemes(input),
                tone: this._extractTone(input),
                difficulty: this._extractDifficulty(input),
                focus_areas: this._extractFocusAreas(input),
                setting: this._extractSetting(input),
                pacing: this._extractPacing(input),
                player_agency: this._extractPlayerAgency(input),
                content_rating: this._extractContentRating(input),
                
                // Specific preferences
                preferences: this._extractPreferences(input),
                exclusions: this._extractExclusions(input),
                references: this._extractReferences(input),
                
                // Parsed details
                key_phrases: this._extractKeyPhrases(input),
                sentiment: this._analyzeSentiment(input),
                confidence_score: 0,
                
                // Generated recommendations
                recommendations: {},
                warnings: []
            };
            
            // Calculate confidence score
            parsed.confidence_score = this._calculateConfidenceScore(parsed);
            
            // Generate specific recommendations
            parsed.recommendations = await this._generateRecommendations(parsed);
            
            // Check for potential issues
            parsed.warnings = this._generateWarnings(parsed);
            
            await this.redis.setex(
                `customization:${customizationId}`,
                86400 * 7, // 7 days
                JSON.stringify(parsed)
            );
            
            this.logger.info(`Parsed customization: ${customizationId}`);
            this.io.emit('customization_parsed', { customizationId, themes: parsed.themes });
            
            return parsed;
            
        } catch (error) {
            this.logger.error('Error parsing customization:', error);
            throw error;
        }
    }

    async applyCustomization(options = {}) {
        try {
            const customizationId = options.customizationId;
            const gameElements = options.gameElements || {};
            
            const customization = await this.getCustomization(customizationId);
            if (!customization) {
                throw new Error('Customization not found');
            }
            
            const applied = {
                customization_id: customizationId,
                applied_at: new Date(),
                
                // Modified game elements
                modified_campaign: this._applyCampaignCustomizations(gameElements.campaign, customization),
                modified_characters: this._applyCharacterCustomizations(gameElements.characters, customization),
                modified_encounters: this._applyEncounterCustomizations(gameElements.encounters, customization),
                modified_environment: this._applyEnvironmentCustomizations(gameElements.environment, customization),
                
                // Rule modifications
                rule_modifications: this._generateRuleModifications(customization),
                
                // DM guidance
                dm_instructions: this._generateDMInstructions(customization),
                
                // Summary of changes
                changes_summary: this._generateChangesSummary(customization),
                
                success: true
            };
            
            this.logger.info(`Applied customization: ${customizationId}`);
            this.io.emit('customization_applied', { customizationId, success: true });
            
            return applied;
            
        } catch (error) {
            this.logger.error('Error applying customization:', error);
            throw error;
        }
    }

    async getCustomization(customizationId) {
        try {
            const cached = await this.redis.get(`customization:${customizationId}`);
            if (cached) {
                return JSON.parse(cached);
            }
            
            return null;
            
        } catch (error) {
            this.logger.error('Error retrieving customization:', error);
            throw error;
        }
    }

    _extractThemes(input) {
        const foundThemes = [];
        const lowerInput = input.toLowerCase();
        
        for (const [theme, keywords] of Object.entries(this.patterns.campaign_themes)) {
            const matches = keywords.filter(keyword => lowerInput.includes(keyword));
            if (matches.length > 0) {
                foundThemes.push({
                    theme: theme,
                    confidence: matches.length / keywords.length,
                    matched_keywords: matches
                });
            }
        }
        
        // Sort by confidence
        return foundThemes.sort((a, b) => b.confidence - a.confidence);
    }

    _extractTone(input) {
        const lowerInput = input.toLowerCase();
        let bestMatch = null;
        let maxScore = 0;
        
        for (const [tone, keywords] of Object.entries(this.patterns.tone_keywords)) {
            const score = keywords.reduce((acc, keyword) => {
                return acc + (lowerInput.includes(keyword) ? 1 : 0);
            }, 0);
            
            if (score > maxScore) {
                maxScore = score;
                bestMatch = tone;
            }
        }
        
        return {
            primary_tone: bestMatch || 'balanced',
            confidence: maxScore > 0 ? maxScore / 3 : 0.5,
            detected_keywords: bestMatch ? this.patterns.tone_keywords[bestMatch].filter(kw => lowerInput.includes(kw)) : []
        };
    }

    _extractDifficulty(input) {
        const lowerInput = input.toLowerCase();
        
        for (const [difficulty, keywords] of Object.entries(this.patterns.difficulty_indicators)) {
            const matches = keywords.filter(keyword => lowerInput.includes(keyword));
            if (matches.length > 0) {
                return {
                    level: difficulty,
                    confidence: matches.length / keywords.length,
                    matched_keywords: matches
                };
            }
        }
        
        return {
            level: 'moderate',
            confidence: 0.3,
            matched_keywords: []
        };
    }

    _extractFocusAreas(input) {
        const focuses = [];
        const lowerInput = input.toLowerCase();
        
        for (const [focus, keywords] of Object.entries(this.patterns.character_focus)) {
            const matches = keywords.filter(keyword => lowerInput.includes(keyword));
            if (matches.length > 0) {
                focuses.push({
                    area: focus,
                    strength: matches.length / keywords.length,
                    keywords: matches
                });
            }
        }
        
        // If no specific focus found, assume balanced
        if (focuses.length === 0) {
            focuses.push({
                area: 'balanced',
                strength: 0.5,
                keywords: []
            });
        }
        
        return focuses.sort((a, b) => b.strength - a.strength);
    }

    _extractSetting(input) {
        const lowerInput = input.toLowerCase();
        
        for (const [setting, keywords] of Object.entries(this.patterns.setting_elements)) {
            const matches = keywords.filter(keyword => lowerInput.includes(keyword));
            if (matches.length > 0) {
                return {
                    type: setting,
                    confidence: matches.length / keywords.length,
                    matched_keywords: matches
                };
            }
        }
        
        return {
            type: 'fantasy_high',
            confidence: 0.3,
            matched_keywords: []
        };
    }

    _extractPacing(input) {
        const lowerInput = input.toLowerCase();
        
        for (const [pace, keywords] of Object.entries(this.patterns.pacing_preferences)) {
            const matches = keywords.filter(keyword => lowerInput.includes(keyword));
            if (matches.length > 0) {
                return {
                    speed: pace,
                    confidence: matches.length / keywords.length,
                    indicators: matches
                };
            }
        }
        
        return {
            speed: 'medium',
            confidence: 0.4,
            indicators: []
        };
    }

    _extractPlayerAgency(input) {
        const lowerInput = input.toLowerCase();
        
        for (const [agency, keywords] of Object.entries(this.patterns.player_agency)) {
            const matches = keywords.filter(keyword => lowerInput.includes(keyword));
            if (matches.length > 0) {
                return {
                    level: agency,
                    confidence: matches.length / keywords.length,
                    indicators: matches
                };
            }
        }
        
        return {
            level: 'medium',
            confidence: 0.3,
            indicators: []
        };
    }

    _extractContentRating(input) {
        const lowerInput = input.toLowerCase();
        
        for (const [rating, keywords] of Object.entries(this.patterns.content_preferences)) {
            const matches = keywords.filter(keyword => lowerInput.includes(keyword));
            if (matches.length > 0) {
                return {
                    rating: rating,
                    confidence: matches.length / keywords.length,
                    indicators: matches
                };
            }
        }
        
        return {
            rating: 'moderate',
            confidence: 0.3,
            indicators: []
        };
    }

    _extractPreferences(input) {
        const preferences = [];
        const lowerInput = input.toLowerCase();
        
        // Look for positive indicators
        const positivePatterns = ['I want', 'I like', 'I love', 'include', 'focus on', 'more'];
        
        for (const pattern of positivePatterns) {
            const index = lowerInput.indexOf(pattern.toLowerCase());
            if (index !== -1) {
                const afterPattern = lowerInput.substring(index + pattern.length).trim();
                const nextSentence = afterPattern.split(/[.!?]/)[0];
                
                if (nextSentence.length > 0 && nextSentence.length < 100) {
                    preferences.push({
                        type: 'preference',
                        pattern: pattern,
                        content: nextSentence.trim(),
                        strength: this._getPatternStrength(pattern)
                    });
                }
            }
        }
        
        return preferences;
    }

    _extractExclusions(input) {
        const exclusions = [];
        const lowerInput = input.toLowerCase();
        
        // Look for negative indicators
        const negativePatterns = ['I hate', 'I dislike', 'no', 'avoid', 'don\'t want', 'not', 'less'];
        
        for (const pattern of negativePatterns) {
            const index = lowerInput.indexOf(pattern.toLowerCase());
            if (index !== -1) {
                const afterPattern = lowerInput.substring(index + pattern.length).trim();
                const nextSentence = afterPattern.split(/[.!?]/)[0];
                
                if (nextSentence.length > 0 && nextSentence.length < 100) {
                    exclusions.push({
                        type: 'exclusion',
                        pattern: pattern,
                        content: nextSentence.trim(),
                        strength: this._getPatternStrength(pattern)
                    });
                }
            }
        }
        
        return exclusions;
    }

    _extractReferences(input) {
        const references = [];
        const lowerInput = input.toLowerCase();
        
        for (const [reference, properties] of Object.entries(this.gameReferences)) {
            if (lowerInput.includes(reference)) {
                references.push({
                    reference: reference,
                    properties: properties,
                    confidence: 0.8
                });
            }
        }
        
        // Look for "like X" or "similar to X" patterns
        const referencePatterns = ['like', 'similar to', 'inspired by', 'based on'];
        for (const pattern of referencePatterns) {
            const regex = new RegExp(`${pattern} ([a-zA-Z ]+)`, 'gi');
            const matches = lowerInput.match(regex);
            if (matches) {
                for (const match of matches) {
                    const referenceName = match.replace(new RegExp(pattern, 'i'), '').trim();
                    references.push({
                        reference: referenceName,
                        properties: this.gameReferences[referenceName] || {},
                        confidence: 0.6
                    });
                }
            }
        }
        
        return references;
    }

    _extractKeyPhrases(input) {
        const phrases = [];
        const sentences = input.split(/[.!?]+/);
        
        for (const sentence of sentences) {
            const trimmed = sentence.trim();
            if (trimmed.length > 10 && trimmed.length < 200) {
                phrases.push({
                    phrase: trimmed,
                    importance: this._calculatePhraseImportance(trimmed)
                });
            }
        }
        
        return phrases.sort((a, b) => b.importance - a.importance).slice(0, 5);
    }

    _analyzeSentiment(input) {
        const positiveWords = ['love', 'like', 'want', 'enjoy', 'fun', 'great', 'amazing', 'awesome', 'exciting'];
        const negativeWords = ['hate', 'dislike', 'boring', 'bad', 'awful', 'terrible', 'avoid', 'not'];
        
        const words = input.toLowerCase().split(/\s+/);
        
        let positiveScore = 0;
        let negativeScore = 0;
        
        for (const word of words) {
            if (positiveWords.includes(word)) positiveScore++;
            if (negativeWords.includes(word)) negativeScore++;
        }
        
        const totalScore = positiveScore + negativeScore;
        if (totalScore === 0) {
            return { overall: 'neutral', positive: 0.5, negative: 0.5 };
        }
        
        return {
            overall: positiveScore > negativeScore ? 'positive' : 'negative',
            positive: positiveScore / totalScore,
            negative: negativeScore / totalScore
        };
    }

    _calculateConfidenceScore(parsed) {
        let totalConfidence = 0;
        let factors = 0;
        
        // Theme confidence
        if (parsed.themes.length > 0) {
            totalConfidence += parsed.themes[0].confidence;
            factors++;
        }
        
        // Tone confidence
        totalConfidence += parsed.tone.confidence;
        factors++;
        
        // Difficulty confidence
        totalConfidence += parsed.difficulty.confidence;
        factors++;
        
        // Reference confidence
        if (parsed.references.length > 0) {
            totalConfidence += parsed.references[0].confidence;
            factors++;
        }
        
        // Input length factor (longer inputs generally provide more confidence)
        const lengthFactor = Math.min(1.0, parsed.original_input.length / 200);
        totalConfidence += lengthFactor;
        factors++;
        
        return factors > 0 ? totalConfidence / factors : 0.3;
    }

    async _generateRecommendations(parsed) {
        const recommendations = {
            campaign_adjustments: [],
            character_suggestions: [],
            encounter_modifications: [],
            rule_changes: [],
            dm_tips: []
        };
        
        // Theme-based recommendations
        if (parsed.themes.length > 0) {
            const primaryTheme = parsed.themes[0];
            recommendations.campaign_adjustments.push(...this._getThemeRecommendations(primaryTheme.theme));
        }
        
        // Difficulty-based recommendations
        recommendations.encounter_modifications.push(...this._getDifficultyRecommendations(parsed.difficulty.level));
        
        // Focus area recommendations
        if (parsed.focus_areas.length > 0) {
            const primaryFocus = parsed.focus_areas[0];
            recommendations.rule_changes.push(...this._getFocusRecommendations(primaryFocus.area));
        }
        
        // Tone-based DM tips
        recommendations.dm_tips.push(...this._getToneRecommendations(parsed.tone.primary_tone));
        
        return recommendations;
    }

    _getThemeRecommendations(theme) {
        const themeRecommendations = {
            'horror': ['Reduce lighting descriptions', 'Increase psychological tension', 'Use fear-based mechanics'],
            'political': ['Add court intrigue plots', 'Introduce faction relationships', 'Emphasize social consequences'],
            'exploration': ['Generate more wilderness encounters', 'Add discovery rewards', 'Create detailed maps'],
            'dungeon_crawl': ['Focus on trap mechanics', 'Include puzzle rooms', 'Add treasure hunting elements'],
            'seafaring': ['Include naval combat', 'Add weather mechanics', 'Create island-hopping adventures']
        };
        
        return themeRecommendations[theme] || ['Maintain thematic consistency throughout the campaign'];
    }

    _getDifficultyRecommendations(difficulty) {
        const difficultyMods = {
            'easy': ['Reduce enemy AC by 1-2', 'Provide more healing resources', 'Give advantage on death saves'],
            'moderate': ['Use standard encounter guidelines', 'Balance challenging and easy encounters'],
            'hard': ['Increase enemy damage by 25%', 'Add environmental hazards', 'Limit rest opportunities'],
            'extreme': ['Use maximum HP for enemies', 'Add multiple objectives per encounter', 'Implement resource scarcity']
        };
        
        return difficultyMods[difficulty] || difficultyMods['moderate'];
    }

    _getFocusRecommendations(focus) {
        const focusRecommendations = {
            'roleplay': ['Encourage character development scenes', 'Add personal subplot hooks', 'Reward creative roleplay'],
            'combat': ['Increase combat encounter frequency', 'Add tactical battlefield elements', 'Include combat variety'],
            'exploration': ['Create detailed environments', 'Add hidden secrets and passages', 'Reward thorough investigation'],
            'social': ['Include more NPC interactions', 'Add political and social conflicts', 'Emphasize reputation mechanics']
        };
        
        return focusRecommendations[focus] || ['Balance different aspects of gameplay'];
    }

    _getToneRecommendations(tone) {
        const toneRecommendations = {
            'serious': ['Emphasize realistic consequences', 'Maintain consistent world logic', 'Avoid breaking immersion'],
            'light': ['Include humor and levity', 'Allow comedic character moments', 'Don\'t punish creative solutions harshly'],
            'epic': ['Scale up the stakes regularly', 'Include world-changing events', 'Emphasize heroic moments'],
            'mysterious': ['Leave some questions unanswered', 'Use foreshadowing liberally', 'Create atmosphere through description']
        };
        
        return toneRecommendations[tone] || ['Maintain tonal consistency throughout the campaign'];
    }

    _generateWarnings(parsed) {
        const warnings = [];
        
        // Check for conflicting preferences
        if (parsed.preferences.length > 0 && parsed.exclusions.length > 0) {
            warnings.push('Some preferences may conflict with exclusions - manual review recommended');
        }
        
        // Check for low confidence
        if (parsed.confidence_score < 0.5) {
            warnings.push('Low confidence in interpretation - consider providing more specific details');
        }
        
        // Check for extreme difficulty with inexperienced player indicators
        if (parsed.difficulty.level === 'extreme' && parsed.original_input.includes('beginner')) {
            warnings.push('Extreme difficulty requested but beginner indicators detected');
        }
        
        // Check for family-friendly with mature themes
        if (parsed.content_rating.rating === 'family_friendly' && 
            parsed.themes.some(t => ['horror', 'political'].includes(t.theme))) {
            warnings.push('Family-friendly content requested but mature themes detected');
        }
        
        return warnings;
    }

    _applyCampaignCustomizations(campaign, customization) {
        if (!campaign) return null;
        
        const modified = { ...campaign };
        
        // Apply theme modifications
        if (customization.themes.length > 0) {
            modified.primary_theme = customization.themes[0].theme;
            modified.theme_elements = customization.themes[0].matched_keywords;
        }
        
        // Apply tone modifications
        modified.tone = customization.tone.primary_tone;
        
        // Apply difficulty
        modified.difficulty = customization.difficulty.level;
        
        // Apply setting
        modified.setting_type = customization.setting.type;
        
        return modified;
    }

    _applyCharacterCustomizations(characters, customization) {
        if (!characters || !Array.isArray(characters)) return [];
        
        return characters.map(character => {
            const modified = { ...character };
            
            // Adjust character based on tone
            if (customization.tone.primary_tone === 'light') {
                modified.personality_quirks = modified.personality_quirks || [];
                modified.personality_quirks.push('Has a good sense of humor');
            }
            
            // Adjust based on content rating
            if (customization.content_rating.rating === 'family_friendly') {
                modified.background = modified.background?.replace(/dark|grim|violent/gi, 'adventurous');
            }
            
            return modified;
        });
    }

    _applyEncounterCustomizations(encounters, customization) {
        if (!encounters || !Array.isArray(encounters)) return [];
        
        return encounters.map(encounter => {
            const modified = { ...encounter };
            
            // Apply difficulty scaling
            if (customization.difficulty.level === 'easy') {
                modified.challenge_rating = Math.max(1, modified.challenge_rating - 1);
            } else if (customization.difficulty.level === 'hard') {
                modified.challenge_rating += 1;
            } else if (customization.difficulty.level === 'extreme') {
                modified.challenge_rating += 2;
            }
            
            // Apply theme modifications
            if (customization.themes.length > 0) {
                const theme = customization.themes[0].theme;
                if (theme === 'horror' && !modified.description.includes('eerie')) {
                    modified.description = `An eerie ${modified.description.toLowerCase()}`;
                }
            }
            
            return modified;
        });
    }

    _applyEnvironmentCustomizations(environment, customization) {
        if (!environment) return null;
        
        const modified = { ...environment };
        
        // Apply setting customizations
        if (customization.setting.type === 'urban') {
            modified.locations = modified.locations?.map(loc => ({
                ...loc,
                urban_features: true
            }));
        }
        
        // Apply tone to descriptions
        if (customization.tone.primary_tone === 'mysterious') {
            modified.atmosphere = 'mysterious and foreboding';
        } else if (customization.tone.primary_tone === 'light') {
            modified.atmosphere = 'bright and welcoming';
        }
        
        return modified;
    }

    _generateRuleModifications(customization) {
        const modifications = [];
        
        // Difficulty-based rule changes
        if (customization.difficulty.level === 'easy') {
            modifications.push('Players start with one additional hit die');
            modifications.push('Short rests restore all spell slots of 1st level');
        } else if (customization.difficulty.level === 'extreme') {
            modifications.push('Healing potions take a full action to use');
            modifications.push('Failed death saves carry over between encounters');
        }
        
        // Focus-based modifications
        if (customization.focus_areas.length > 0) {
            const primaryFocus = customization.focus_areas[0];
            if (primaryFocus.area === 'roleplay') {
                modifications.push('Inspiration is awarded for excellent roleplay each session');
            } else if (primaryFocus.area === 'combat') {
                modifications.push('Tactical movement and positioning provide situational bonuses');
            }
        }
        
        return modifications;
    }

    _generateDMInstructions(customization) {
        const instructions = [];
        
        // Theme-specific instructions
        if (customization.themes.length > 0) {
            const theme = customization.themes[0].theme;
            instructions.push(`Maintain ${theme} theme throughout the campaign`);
            instructions.push(`Use ${theme}-appropriate atmosphere and descriptions`);
        }
        
        // Tone instructions
        instructions.push(`Keep the overall tone ${customization.tone.primary_tone}`);
        
        // Player agency instructions
        instructions.push(`Provide ${customization.player_agency.level} levels of player choice and freedom`);
        
        // Pacing instructions
        instructions.push(`Maintain ${customization.pacing.speed} pacing throughout sessions`);
        
        return instructions;
    }

    _generateChangesSummary(customization) {
        const changes = [];
        
        if (customization.themes.length > 0) {
            changes.push(`Campaign theme set to ${customization.themes[0].theme}`);
        }
        
        changes.push(`Tone adjusted to ${customization.tone.primary_tone}`);
        changes.push(`Difficulty set to ${customization.difficulty.level}`);
        changes.push(`Pacing set to ${customization.pacing.speed}`);
        
        if (customization.focus_areas.length > 0) {
            changes.push(`Primary focus on ${customization.focus_areas[0].area}`);
        }
        
        return changes;
    }

    _getPatternStrength(pattern) {
        const strengthMap = {
            'I love': 1.0,
            'I want': 0.8,
            'I like': 0.6,
            'I hate': -1.0,
            'avoid': -0.8,
            'no': -0.6
        };
        
        return strengthMap[pattern] || 0.5;
    }

    _calculatePhraseImportance(phrase) {
        let importance = 0.1;
        
        // Longer phrases tend to be more specific
        importance += Math.min(phrase.length / 100, 0.3);
        
        // Phrases with action words are more important
        const actionWords = ['want', 'need', 'like', 'hate', 'focus', 'include', 'avoid'];
        for (const word of actionWords) {
            if (phrase.toLowerCase().includes(word)) {
                importance += 0.2;
                break;
            }
        }
        
        // Phrases with game terms are more important
        const gameTerms = ['combat', 'roleplay', 'story', 'character', 'difficulty', 'challenge'];
        for (const term of gameTerms) {
            if (phrase.toLowerCase().includes(term)) {
                importance += 0.1;
            }
        }
        
        return Math.min(importance, 1.0);
    }

    async getStats() {
        try {
            const keys = await this.redis.keys('customization:*');
            const totalCustomizations = keys.length;
            
            let totalConfidence = 0;
            let themeDistribution = {};
            
            for (const key of keys.slice(0, 100)) { // Sample first 100
                const data = await this.redis.get(key);
                if (data) {
                    const customization = JSON.parse(data);
                    totalConfidence += customization.confidence_score || 0;
                    
                    if (customization.themes.length > 0) {
                        const theme = customization.themes[0].theme;
                        themeDistribution[theme] = (themeDistribution[theme] || 0) + 1;
                    }
                }
            }
            
            return {
                total_customizations: totalCustomizations,
                average_confidence: totalCustomizations > 0 ? totalConfidence / totalCustomizations : 0,
                popular_themes: themeDistribution,
                processed_today: 0 // Could implement daily tracking
            };
            
        } catch (error) {
            this.logger.error('Error getting customization stats:', error);
            return {
                total_customizations: 0,
                average_confidence: 0,
                popular_themes: {},
                processed_today: 0
            };
        }
    }
}

module.exports = NaturalLanguageCustomizer;