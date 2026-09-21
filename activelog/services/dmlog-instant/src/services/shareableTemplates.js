const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');

class ShareableTemplates extends EventEmitter {
    constructor(redisClient, io, logger) {
        super();
        this.redis = redisClient;
        this.io = io;
        this.logger = logger;
        
        // Template categories and metadata
        this.templateCategories = {
            'campaign': {
                name: 'Campaign Templates',
                description: 'Complete campaign structures with multiple sessions',
                fields: ['name', 'description', 'session_count', 'level_range', 'themes', 'story_structure'],
                validation_rules: {
                    min_sessions: 3,
                    max_sessions: 50,
                    required_fields: ['name', 'description', 'story_structure']
                }
            },
            
            'adventure': {
                name: 'Adventure Modules',
                description: 'Single or short-run adventures for one-shots or mini-campaigns',
                fields: ['name', 'description', 'duration', 'party_level', 'encounters', 'plot_hooks'],
                validation_rules: {
                    min_duration_hours: 1,
                    max_duration_hours: 12,
                    required_fields: ['name', 'description', 'encounters']
                }
            },
            
            'encounter': {
                name: 'Encounter Templates',
                description: 'Reusable combat, social, and exploration encounters',
                fields: ['name', 'type', 'difficulty', 'participants', 'environment', 'objectives'],
                validation_rules: {
                    valid_types: ['combat', 'social', 'exploration', 'puzzle'],
                    required_fields: ['name', 'type', 'difficulty']
                }
            },
            
            'character': {
                name: 'Character Templates',
                description: 'Pre-generated characters and NPCs',
                fields: ['name', 'race', 'class', 'level', 'background', 'personality', 'stats'],
                validation_rules: {
                    min_level: 1,
                    max_level: 20,
                    required_fields: ['name', 'race', 'class', 'level']
                }
            },
            
            'location': {
                name: 'Location Templates',
                description: 'Detailed locations including maps, NPCs, and plot hooks',
                fields: ['name', 'type', 'description', 'inhabitants', 'features', 'secrets'],
                validation_rules: {
                    valid_types: ['city', 'dungeon', 'wilderness', 'building', 'plane'],
                    required_fields: ['name', 'type', 'description']
                }
            },
            
            'magic_item': {
                name: 'Magic Item Templates',
                description: 'Custom magic items with descriptions and mechanics',
                fields: ['name', 'type', 'rarity', 'description', 'mechanics', 'lore'],
                validation_rules: {
                    valid_rarities: ['common', 'uncommon', 'rare', 'very_rare', 'legendary', 'artifact'],
                    required_fields: ['name', 'type', 'rarity', 'description']
                }
            },
            
            'rule_variant': {
                name: 'Rule Variants',
                description: 'House rules and mechanical variants',
                fields: ['name', 'description', 'mechanics', 'playtested', 'balance_notes'],
                validation_rules: {
                    required_fields: ['name', 'description', 'mechanics']
                }
            },
            
            'session_toolkit': {
                name: 'Session Toolkits',
                description: 'Collections of tools and resources for running specific types of sessions',
                fields: ['name', 'session_type', 'tools', 'handouts', 'dm_notes'],
                validation_rules: {
                    valid_session_types: ['social', 'combat', 'exploration', 'mystery', 'horror'],
                    required_fields: ['name', 'session_type', 'tools']
                }
            }
        };
        
        // Template sharing and discovery features
        this.sharingFeatures = {
            visibility_levels: {
                'private': {
                    name: 'Private',
                    description: 'Only you can see this template',
                    access_control: 'owner_only'
                },
                'friends': {
                    name: 'Friends Only',
                    description: 'Shared with your friends list',
                    access_control: 'friends_list'
                },
                'community': {
                    name: 'Community',
                    description: 'Public to all users with appropriate content',
                    access_control: 'community_moderated'
                },
                'featured': {
                    name: 'Featured',
                    description: 'Highlighted templates approved by moderators',
                    access_control: 'admin_curated'
                }
            },
            
            discovery_methods: {
                'search': 'Text-based search with filters',
                'category_browse': 'Browse by template category',
                'tag_exploration': 'Explore by tags and themes',
                'rating_sort': 'Sort by community ratings',
                'trending': 'Recently popular templates',
                'recommended': 'AI-powered recommendations'
            },
            
            community_features: {
                'ratings': 'Star ratings and reviews',
                'comments': 'Community discussion and feedback',
                'favorites': 'Save templates to personal collection',
                'forks': 'Create variations of existing templates',
                'collections': 'Curated template bundles',
                'following': 'Follow favorite creators'
            }
        };
        
        // Template quality standards
        this.qualityStandards = {
            content_guidelines: {
                'completeness': 'All required fields filled out thoroughly',
                'clarity': 'Clear, understandable descriptions and instructions',
                'balance': 'Mechanically balanced and playtested',
                'originality': 'Original content or proper attribution',
                'family_friendly': 'Appropriate for general audiences',
                'usability': 'Easy to understand and implement'
            },
            
            moderation_criteria: {
                'content_policy': 'Adheres to community content policies',
                'copyright': 'No copyright infringement',
                'quality_threshold': 'Meets minimum quality standards',
                'community_standards': 'Follows community guidelines',
                'technical_accuracy': 'Rules-accurate and functional'
            },
            
            rating_system: {
                '1_star': 'Poor - Significant issues, unusable',
                '2_star': 'Below Average - Major flaws, needs work',
                '3_star': 'Average - Usable but unremarkable',
                '4_star': 'Good - Well-crafted, recommended',
                '5_star': 'Excellent - Outstanding quality, highly recommended'
            }
        };
    }

    async getTemplates(options = {}) {
        try {
            const searchParams = {
                category: options.category,
                tags: options.tags || [],
                rating_min: options.min_rating || 0,
                author: options.author,
                visibility: options.visibility || 'community',
                search_text: options.search,
                limit: Math.min(options.limit || 20, 100),
                offset: options.offset || 0
            };
            
            // Build search key pattern
            let searchPattern = 'template:*';
            if (searchParams.category) {
                searchPattern = `template:${searchParams.category}:*`;
            }
            
            // Get matching template keys
            const templateKeys = await this.redis.keys(searchPattern);
            const templates = [];
            
            // Retrieve and filter templates
            for (const key of templateKeys) {
                try {
                    const templateData = await this.redis.get(key);
                    if (templateData) {
                        const template = JSON.parse(templateData);
                        
                        // Apply filters
                        if (this._matchesFilters(template, searchParams)) {
                            templates.push(this._sanitizeTemplateForDisplay(template));
                        }
                    }
                } catch (error) {
                    this.logger.warn(`Error processing template ${key}:`, error);
                }
            }
            
            // Sort templates
            const sortedTemplates = this._sortTemplates(templates, options.sort_by || 'rating');
            
            // Apply pagination
            const paginatedTemplates = sortedTemplates.slice(
                searchParams.offset,
                searchParams.offset + searchParams.limit
            );
            
            return {
                templates: paginatedTemplates,
                total_count: sortedTemplates.length,
                filters_applied: searchParams,
                categories: this._getAvailableCategories(),
                popular_tags: await this._getPopularTags()
            };
            
        } catch (error) {
            this.logger.error('Error getting templates:', error);
            throw error;
        }
    }

    async createTemplate(templateData) {
        try {
            const templateId = uuidv4();
            const category = templateData.category;
            
            // Validate template data
            const validation = this._validateTemplate(templateData);
            if (!validation.valid) {
                throw new Error(`Template validation failed: ${validation.errors.join(', ')}`);
            }
            
            // Create template object
            const template = {
                id: templateId,
                category: category,
                name: templateData.name,
                description: templateData.description,
                author: templateData.author || 'anonymous',
                
                // Template content
                content: this._processTemplateContent(templateData, category),
                
                // Metadata
                created_at: new Date(),
                updated_at: new Date(),
                version: '1.0.0',
                
                // Sharing settings
                visibility: templateData.visibility || 'private',
                tags: templateData.tags || [],
                
                // Community features
                statistics: {
                    downloads: 0,
                    ratings_count: 0,
                    average_rating: 0,
                    favorites: 0,
                    views: 0,
                    forks: 0
                },
                
                // Quality assurance
                moderation_status: 'pending_review',
                quality_score: this._calculateInitialQualityScore(templateData),
                
                // Usage tracking
                usage_history: [],
                feedback: []
            };
            
            // Store template
            const templateKey = `template:${category}:${templateId}`;
            await this.redis.setex(templateKey, 86400 * 90, JSON.stringify(template)); // 90 days
            
            // Update indexes
            await this._updateTemplateIndexes(template);
            
            // Queue for moderation if public
            if (template.visibility === 'community') {
                await this._queueForModeration(template);
            }
            
            this.logger.info(`Created template: ${template.name} (${templateId})`);
            this.io.emit('template_created', { 
                templateId, 
                category,
                name: template.name,
                author: template.author 
            });
            
            return template;
            
        } catch (error) {
            this.logger.error('Error creating template:', error);
            throw error;
        }
    }

    async getTemplate(templateId) {
        try {
            // Try to find template across all categories
            const categories = Object.keys(this.templateCategories);
            
            for (const category of categories) {
                const templateKey = `template:${category}:${templateId}`;
                const templateData = await this.redis.get(templateKey);
                
                if (templateData) {
                    const template = JSON.parse(templateData);
                    
                    // Increment view count
                    template.statistics.views++;
                    await this.redis.setex(templateKey, 86400 * 90, JSON.stringify(template));
                    
                    return template;
                }
            }
            
            throw new Error('Template not found');
            
        } catch (error) {
            if (error.message !== 'Template not found') {
                this.logger.error('Error retrieving template:', error);
            }
            throw error;
        }
    }

    async updateTemplate(templateId, updateData) {
        try {
            // Find and load existing template
            const existingTemplate = await this.getTemplate(templateId);
            
            // Check permissions (simplified - would check user auth)
            if (updateData.requester_id && updateData.requester_id !== existingTemplate.author) {
                throw new Error('Permission denied: Only template author can update');
            }
            
            // Validate updates
            const mergedData = { ...existingTemplate.content, ...updateData.content };
            const validation = this._validateTemplate({ 
                ...existingTemplate, 
                ...updateData,
                content: mergedData
            });
            
            if (!validation.valid) {
                throw new Error(`Update validation failed: ${validation.errors.join(', ')}`);
            }
            
            // Create updated template
            const updatedTemplate = {
                ...existingTemplate,
                ...updateData,
                content: mergedData,
                updated_at: new Date(),
                version: this._incrementVersion(existingTemplate.version)
            };
            
            // Re-queue for moderation if content changed significantly
            if (this._isSignificantUpdate(existingTemplate, updatedTemplate)) {
                updatedTemplate.moderation_status = 'pending_review';
                await this._queueForModeration(updatedTemplate);
            }
            
            // Store updated template
            const templateKey = `template:${existingTemplate.category}:${templateId}`;
            await this.redis.setex(templateKey, 86400 * 90, JSON.stringify(updatedTemplate));
            
            // Update indexes
            await this._updateTemplateIndexes(updatedTemplate);
            
            this.logger.info(`Updated template: ${updatedTemplate.name} (${templateId})`);
            this.io.emit('template_updated', { templateId, version: updatedTemplate.version });
            
            return updatedTemplate;
            
        } catch (error) {
            this.logger.error('Error updating template:', error);
            throw error;
        }
    }

    async forkTemplate(templateId, forkData) {
        try {
            // Get original template
            const originalTemplate = await this.getTemplate(templateId);
            
            // Create fork
            const forkId = uuidv4();
            const forkedTemplate = {
                ...originalTemplate,
                id: forkId,
                name: forkData.name || `${originalTemplate.name} (Fork)`,
                description: forkData.description || `Forked from ${originalTemplate.name}`,
                author: forkData.author,
                
                // Fork metadata
                forked_from: {
                    original_id: templateId,
                    original_author: originalTemplate.author,
                    fork_timestamp: new Date(),
                    original_version: originalTemplate.version
                },
                
                // Reset statistics
                statistics: {
                    downloads: 0,
                    ratings_count: 0,
                    average_rating: 0,
                    favorites: 0,
                    views: 0,
                    forks: 0
                },
                
                // Reset moderation
                moderation_status: forkData.visibility === 'community' ? 'pending_review' : 'approved',
                
                // Update timestamps
                created_at: new Date(),
                updated_at: new Date(),
                version: '1.0.0',
                
                // Apply any immediate changes
                content: forkData.content_changes ? 
                    { ...originalTemplate.content, ...forkData.content_changes } : 
                    originalTemplate.content,
                
                visibility: forkData.visibility || 'private',
                tags: forkData.tags || originalTemplate.tags
            };
            
            // Store forked template
            const forkKey = `template:${originalTemplate.category}:${forkId}`;
            await this.redis.setex(forkKey, 86400 * 90, JSON.stringify(forkedTemplate));
            
            // Update original template's fork count
            originalTemplate.statistics.forks++;
            const originalKey = `template:${originalTemplate.category}:${templateId}`;
            await this.redis.setex(originalKey, 86400 * 90, JSON.stringify(originalTemplate));
            
            // Update indexes
            await this._updateTemplateIndexes(forkedTemplate);
            
            this.logger.info(`Forked template: ${originalTemplate.name} -> ${forkedTemplate.name}`);
            this.io.emit('template_forked', { 
                originalId: templateId,
                forkId: forkId,
                author: forkData.author 
            });
            
            return forkedTemplate;
            
        } catch (error) {
            this.logger.error('Error forking template:', error);
            throw error;
        }
    }

    async rateTemplate(templateId, rating, review = null) {
        try {
            if (rating < 1 || rating > 5) {
                throw new Error('Rating must be between 1 and 5');
            }
            
            // Get template
            const template = await this.getTemplate(templateId);
            
            // Add rating
            const ratingEntry = {
                id: uuidv4(),
                rating: rating,
                review: review,
                timestamp: new Date(),
                helpful_votes: 0
            };
            
            template.feedback.push(ratingEntry);
            
            // Update statistics
            template.statistics.ratings_count++;
            const totalRating = template.feedback.reduce((sum, r) => sum + r.rating, 0);
            template.statistics.average_rating = totalRating / template.statistics.ratings_count;
            
            // Store updated template
            const templateKey = `template:${template.category}:${templateId}`;
            await this.redis.setex(templateKey, 86400 * 90, JSON.stringify(template));
            
            this.logger.info(`Rated template: ${templateId} (${rating}/5)`);
            this.io.emit('template_rated', { 
                templateId, 
                newRating: template.statistics.average_rating,
                totalRatings: template.statistics.ratings_count 
            });
            
            return {
                rating_id: ratingEntry.id,
                new_average: template.statistics.average_rating,
                total_ratings: template.statistics.ratings_count
            };
            
        } catch (error) {
            this.logger.error('Error rating template:', error);
            throw error;
        }
    }

    async searchTemplates(query, options = {}) {
        try {
            const searchResults = [];
            const searchTerms = query.toLowerCase().split(' ');
            
            // Get all templates for searching
            const allCategories = Object.keys(this.templateCategories);
            
            for (const category of allCategories) {
                const categoryKeys = await this.redis.keys(`template:${category}:*`);
                
                for (const key of categoryKeys) {
                    try {
                        const templateData = await this.redis.get(key);
                        if (templateData) {
                            const template = JSON.parse(templateData);
                            
                            // Calculate relevance score
                            const relevanceScore = this._calculateRelevanceScore(template, searchTerms);
                            
                            if (relevanceScore > 0) {
                                searchResults.push({
                                    template: this._sanitizeTemplateForDisplay(template),
                                    relevance_score: relevanceScore
                                });
                            }
                        }
                    } catch (error) {
                        this.logger.warn(`Error processing search result ${key}:`, error);
                    }
                }
            }
            
            // Sort by relevance score
            searchResults.sort((a, b) => b.relevance_score - a.relevance_score);
            
            // Apply filters and pagination
            const filteredResults = searchResults.filter(result => 
                this._matchesFilters(result.template, options)
            );
            
            const limit = Math.min(options.limit || 20, 100);
            const offset = options.offset || 0;
            const paginatedResults = filteredResults.slice(offset, offset + limit);
            
            return {
                results: paginatedResults.map(r => r.template),
                total_matches: filteredResults.length,
                search_query: query,
                suggested_filters: this._generateSearchSuggestions(searchResults, query)
            };
            
        } catch (error) {
            this.logger.error('Error searching templates:', error);
            throw error;
        }
    }

    async getRecommendations(userId, options = {}) {
        try {
            // Get user's template history and preferences
            const userHistory = await this._getUserTemplateHistory(userId);
            const userPreferences = await this._analyzeUserPreferences(userHistory);
            
            // Generate recommendations based on different algorithms
            const recommendations = {
                similar_to_liked: await this._getSimilarRecommendations(userPreferences),
                trending_in_categories: await this._getTrendingRecommendations(userPreferences),
                collaborative_filtering: await this._getCollaborativeRecommendations(userId, userHistory),
                editorial_picks: await this._getEditorialRecommendations()
            };
            
            // Combine and rank recommendations
            const combinedRecommendations = this._combineRecommendations(recommendations);
            
            // Apply diversity to avoid too many similar recommendations
            const diverseRecommendations = this._diversifyRecommendations(combinedRecommendations);
            
            return {
                recommendations: diverseRecommendations.slice(0, options.limit || 10),
                recommendation_reasons: this._generateRecommendationReasons(diverseRecommendations),
                user_preferences: userPreferences
            };
            
        } catch (error) {
            this.logger.error('Error getting recommendations:', error);
            throw error;
        }
    }

    // Template validation and processing methods
    _validateTemplate(templateData) {
        const category = templateData.category;
        const categoryConfig = this.templateCategories[category];
        
        if (!categoryConfig) {
            return { valid: false, errors: ['Invalid template category'] };
        }
        
        const errors = [];
        const rules = categoryConfig.validation_rules;
        
        // Check required fields
        for (const field of rules.required_fields) {
            if (!templateData[field] && !templateData.content?.[field]) {
                errors.push(`Missing required field: ${field}`);
            }
        }
        
        // Category-specific validation
        switch (category) {
            case 'campaign':
                if (templateData.content?.session_count && (
                    templateData.content.session_count < rules.min_sessions ||
                    templateData.content.session_count > rules.max_sessions
                )) {
                    errors.push(`Session count must be between ${rules.min_sessions} and ${rules.max_sessions}`);
                }
                break;
                
            case 'character':
                if (templateData.content?.level && (
                    templateData.content.level < rules.min_level ||
                    templateData.content.level > rules.max_level
                )) {
                    errors.push(`Character level must be between ${rules.min_level} and ${rules.max_level}`);
                }
                break;
                
            case 'encounter':
                if (templateData.content?.type && !rules.valid_types.includes(templateData.content.type)) {
                    errors.push(`Invalid encounter type. Must be one of: ${rules.valid_types.join(', ')}`);
                }
                break;
        }
        
        return {
            valid: errors.length === 0,
            errors: errors,
            warnings: this._generateValidationWarnings(templateData, categoryConfig)
        };
    }

    _processTemplateContent(templateData, category) {
        const categoryConfig = this.templateCategories[category];
        const content = {};
        
        // Extract content fields based on category
        for (const field of categoryConfig.fields) {
            if (templateData[field] !== undefined) {
                content[field] = templateData[field];
            }
        }
        
        // Add category-specific processing
        switch (category) {
            case 'campaign':
                content.estimated_playtime = this._calculateCampaignPlaytime(content);
                content.complexity_level = this._assessComplexityLevel(content);
                break;
                
            case 'encounter':
                content.estimated_duration = this._estimateEncounterDuration(content);
                content.required_prep_time = this._estimatePrepTime(content);
                break;
                
            case 'character':
                content.character_sheet_data = this._generateCharacterSheetData(content);
                content.roleplay_hooks = this._generateRoleplayHooks(content);
                break;
        }
        
        return content;
    }

    _calculateInitialQualityScore(templateData) {
        let score = 0.5; // Base score
        
        // Content completeness
        if (templateData.description && templateData.description.length > 100) {
            score += 0.1;
        }
        
        // Has tags
        if (templateData.tags && templateData.tags.length > 0) {
            score += 0.1;
        }
        
        // Detailed content
        const contentLength = JSON.stringify(templateData.content || {}).length;
        if (contentLength > 500) {
            score += 0.2;
        }
        
        return Math.min(score, 1.0);
    }

    _matchesFilters(template, filters) {
        // Category filter
        if (filters.category && template.category !== filters.category) {
            return false;
        }
        
        // Rating filter
        if (filters.rating_min && template.statistics.average_rating < filters.rating_min) {
            return false;
        }
        
        // Author filter
        if (filters.author && template.author !== filters.author) {
            return false;
        }
        
        // Visibility filter
        if (filters.visibility && template.visibility !== filters.visibility) {
            return false;
        }
        
        // Tag filter
        if (filters.tags && filters.tags.length > 0) {
            const hasMatchingTag = filters.tags.some(tag => 
                template.tags.includes(tag)
            );
            if (!hasMatchingTag) {
                return false;
            }
        }
        
        // Text search filter
        if (filters.search_text) {
            const searchText = filters.search_text.toLowerCase();
            const searchableText = (
                template.name + ' ' + 
                template.description + ' ' + 
                template.tags.join(' ')
            ).toLowerCase();
            
            if (!searchableText.includes(searchText)) {
                return false;
            }
        }
        
        return true;
    }

    _sortTemplates(templates, sortBy) {
        switch (sortBy) {
            case 'rating':
                return templates.sort((a, b) => b.statistics.average_rating - a.statistics.average_rating);
            case 'downloads':
                return templates.sort((a, b) => b.statistics.downloads - a.statistics.downloads);
            case 'newest':
                return templates.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
            case 'updated':
                return templates.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
            case 'name':
                return templates.sort((a, b) => a.name.localeCompare(b.name));
            default:
                return templates.sort((a, b) => b.statistics.average_rating - a.statistics.average_rating);
        }
    }

    _sanitizeTemplateForDisplay(template) {
        // Remove sensitive or internal data before sending to client
        const sanitized = { ...template };
        
        // Keep only recent feedback summaries (not full reviews)
        if (sanitized.feedback) {
            sanitized.feedback = sanitized.feedback.slice(-5).map(f => ({
                rating: f.rating,
                timestamp: f.timestamp,
                review_excerpt: f.review ? f.review.substring(0, 100) + '...' : null
            }));
        }
        
        // Remove internal moderation data
        delete sanitized.usage_history;
        
        return sanitized;
    }

    async _updateTemplateIndexes(template) {
        // Update category index
        const categoryIndex = `index:category:${template.category}`;
        await this.redis.sadd(categoryIndex, template.id);
        
        // Update tag indexes
        for (const tag of template.tags) {
            const tagIndex = `index:tag:${tag}`;
            await this.redis.sadd(tagIndex, template.id);
        }
        
        // Update author index
        const authorIndex = `index:author:${template.author}`;
        await this.redis.sadd(authorIndex, template.id);
    }

    async _queueForModeration(template) {
        const moderationQueue = 'moderation_queue';
        const moderationItem = {
            template_id: template.id,
            category: template.category,
            submitted_at: new Date(),
            priority: this._calculateModerationPriority(template)
        };
        
        await this.redis.lpush(moderationQueue, JSON.stringify(moderationItem));
    }

    _calculateRelevanceScore(template, searchTerms) {
        let score = 0;
        const searchableFields = [
            { field: template.name, weight: 3 },
            { field: template.description, weight: 2 },
            { field: template.tags.join(' '), weight: 1 },
            { field: JSON.stringify(template.content), weight: 0.5 }
        ];
        
        for (const term of searchTerms) {
            for (const { field, weight } of searchableFields) {
                const fieldText = (field || '').toLowerCase();
                if (fieldText.includes(term)) {
                    score += weight;
                    // Bonus for exact matches
                    if (fieldText === term) {
                        score += weight;
                    }
                }
            }
        }
        
        return score;
    }

    async getStats() {
        try {
            const categories = Object.keys(this.templateCategories);
            let totalTemplates = 0;
            let categoryDistribution = {};
            let totalDownloads = 0;
            let avgRating = 0;
            let ratedTemplates = 0;
            
            for (const category of categories) {
                const categoryKeys = await this.redis.keys(`template:${category}:*`);
                categoryDistribution[category] = categoryKeys.length;
                totalTemplates += categoryKeys.length;
                
                // Sample some templates for statistics
                for (const key of categoryKeys.slice(0, 10)) {
                    try {
                        const data = await this.redis.get(key);
                        if (data) {
                            const template = JSON.parse(data);
                            totalDownloads += template.statistics.downloads || 0;
                            if (template.statistics.ratings_count > 0) {
                                avgRating += template.statistics.average_rating;
                                ratedTemplates++;
                            }
                        }
                    } catch (error) {
                        // Skip invalid templates
                    }
                }
            }
            
            return {
                total_templates: totalTemplates,
                category_distribution: categoryDistribution,
                total_downloads: totalDownloads,
                average_rating: ratedTemplates > 0 ? avgRating / ratedTemplates : 0,
                templates_with_ratings: ratedTemplates,
                active_today: 0 // Could implement active usage tracking
            };
            
        } catch (error) {
            this.logger.error('Error getting template stats:', error);
            return {
                total_templates: 0,
                category_distribution: {},
                total_downloads: 0,
                average_rating: 0,
                templates_with_ratings: 0,
                active_today: 0
            };
        }
    }

    // Additional helper methods (simplified implementations)
    _getAvailableCategories() {
        return Object.keys(this.templateCategories).map(key => ({
            id: key,
            ...this.templateCategories[key]
        }));
    }

    async _getPopularTags() {
        // Implementation would aggregate tags from all templates
        return ['fantasy', 'horror', 'mystery', 'urban', 'comedy', 'serious', 'one-shot', 'campaign'];
    }

    _incrementVersion(currentVersion) {
        const parts = currentVersion.split('.');
        parts[2] = (parseInt(parts[2]) + 1).toString();
        return parts.join('.');
    }

    _isSignificantUpdate(oldTemplate, newTemplate) {
        // Check if core content has changed significantly
        return JSON.stringify(oldTemplate.content) !== JSON.stringify(newTemplate.content);
    }

    _calculateModerationPriority(template) {
        // Higher priority for featured templates, lower for private
        if (template.visibility === 'featured') return 'high';
        if (template.visibility === 'community') return 'medium';
        return 'low';
    }

    // Placeholder implementations for recommendation system
    async _getUserTemplateHistory(userId) { return []; }
    async _analyzeUserPreferences(history) { return {}; }
    async _getSimilarRecommendations(preferences) { return []; }
    async _getTrendingRecommendations(preferences) { return []; }
    async _getCollaborativeRecommendations(userId, history) { return []; }
    async _getEditorialRecommendations() { return []; }
    _combineRecommendations(recommendations) { return []; }
    _diversifyRecommendations(recommendations) { return recommendations; }
    _generateRecommendationReasons(recommendations) { return []; }
    _generateValidationWarnings(templateData, categoryConfig) { return []; }
    _calculateCampaignPlaytime(content) { return '8-12 hours'; }
    _assessComplexityLevel(content) { return 'intermediate'; }
    _estimateEncounterDuration(content) { return '30-60 minutes'; }
    _estimatePrepTime(content) { return '15 minutes'; }
    _generateCharacterSheetData(content) { return {}; }
    _generateRoleplayHooks(content) { return []; }
    _generateSearchSuggestions(searchResults, query) { return []; }
}

module.exports = ShareableTemplates;