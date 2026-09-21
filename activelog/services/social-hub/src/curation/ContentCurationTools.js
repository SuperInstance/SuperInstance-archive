import { EventEmitter } from 'events';
import axios from 'axios';
import cheerio from 'cheerio';
import OpenAI from 'openai';
import { analyze } from 'sentiment';
import crypto from 'crypto';
import sharp from 'sharp';

class ContentCurationTools extends EventEmitter {
    constructor(config = {}) {
        super();
        this.sources = new Map();
        this.filters = new Map();
        this.collections = new Map();
        this.automationRules = new Map();
        this.contentDatabase = new Map();
        this.categories = new Map();
        this.keywords = new Map();
        this.trends = new Map();
        this.templates = new Map();

        this.openai = new OpenAI({
            apiKey: config.openai_api_key || process.env.OPENAI_API_KEY
        });

        this.initializeSystem();
    }

    initializeSystem() {
        this.initializeContentSources();
        this.initializeCurationFilters();
        this.initializeCategories();
        this.initializeTemplates();
        this.initializeAutomationRules();
        
        this.emit('curation_system_initialized');
    }

    initializeContentSources() {
        const sources = [
            {
                id: 'tech_blogs',
                name: 'Technology Blogs',
                type: 'rss',
                urls: [
                    'https://techcrunch.com/feed/',
                    'https://www.theverge.com/rss/index.xml',
                    'https://arstechnica.com/feed/',
                    'https://www.wired.com/feed'
                ],
                categories: ['technology', 'innovation', 'startups'],
                priority: 'high',
                check_frequency: 30, // minutes
                last_check: null
            },
            {
                id: 'iot_news',
                name: 'IoT and Hardware News',
                type: 'rss',
                urls: [
                    'https://iot-analytics.com/feed/',
                    'https://www.embedded.com/feed/',
                    'https://hackaday.com/feed/'
                ],
                categories: ['iot', 'hardware', 'sensors'],
                priority: 'high',
                check_frequency: 15,
                last_check: null
            },
            {
                id: 'social_trends',
                name: 'Social Media Trends',
                type: 'api',
                platforms: ['twitter', 'reddit', 'hacker_news'],
                categories: ['trending', 'viral', 'discussions'],
                priority: 'medium',
                check_frequency: 10,
                last_check: null
            },
            {
                id: 'industry_reports',
                name: 'Industry Research',
                type: 'manual',
                sources: ['research_firms', 'whitepapers', 'case_studies'],
                categories: ['research', 'analysis', 'insights'],
                priority: 'medium',
                check_frequency: 1440, // daily
                last_check: null
            },
            {
                id: 'visual_content',
                name: 'Visual Content Sources',
                type: 'api',
                platforms: ['unsplash', 'pexels', 'pixabay'],
                categories: ['images', 'videos', 'graphics'],
                priority: 'low',
                check_frequency: 60,
                last_check: null
            },
            {
                id: 'competitor_analysis',
                name: 'Competitor Content',
                type: 'social_monitoring',
                targets: ['competitor_accounts', 'industry_leaders'],
                categories: ['competitive_intelligence', 'benchmarking'],
                priority: 'high',
                check_frequency: 20,
                last_check: null
            }
        ];

        sources.forEach(source => {
            this.sources.set(source.id, source);
        });
    }

    initializeCurationFilters() {
        const filters = [
            {
                id: 'relevance_filter',
                name: 'Content Relevance',
                type: 'keyword_matching',
                criteria: {
                    required_keywords: ['iot', 'sensors', 'technology', 'innovation', 'hardware'],
                    excluded_keywords: ['politics', 'sports', 'celebrity', 'gossip'],
                    min_relevance_score: 0.6
                },
                enabled: true,
                priority: 1
            },
            {
                id: 'quality_filter',
                name: 'Content Quality',
                type: 'multi_factor',
                criteria: {
                    min_word_count: 100,
                    max_word_count: 5000,
                    requires_images: false,
                    source_authority_min: 0.5,
                    engagement_threshold: 10
                },
                enabled: true,
                priority: 2
            },
            {
                id: 'freshness_filter',
                name: 'Content Freshness',
                type: 'temporal',
                criteria: {
                    max_age_hours: 168, // 1 week
                    prefer_recent: true,
                    trending_boost: true
                },
                enabled: true,
                priority: 3
            },
            {
                id: 'sentiment_filter',
                name: 'Sentiment Analysis',
                type: 'sentiment',
                criteria: {
                    min_sentiment: -0.3,
                    prefer_positive: true,
                    neutral_acceptable: true
                },
                enabled: true,
                priority: 4
            },
            {
                id: 'duplicate_filter',
                name: 'Duplicate Detection',
                type: 'similarity',
                criteria: {
                    max_similarity: 0.8,
                    check_title: true,
                    check_content: true,
                    check_url: true
                },
                enabled: true,
                priority: 5
            }
        ];

        filters.forEach(filter => {
            this.filters.set(filter.id, filter);
        });
    }

    initializeCategories() {
        const categories = [
            {
                id: 'product_spotlight',
                name: 'Product Spotlight',
                description: 'Featuring ActiveLog products and related technologies',
                keywords: ['fish counter', 'solar camera', 'sensors', 'iot devices', 'activelog'],
                priority: 'high',
                posting_frequency: 'daily'
            },
            {
                id: 'industry_insights',
                name: 'Industry Insights',
                description: 'Latest trends and insights in IoT and hardware',
                keywords: ['iot trends', 'hardware innovation', 'technology insights', 'market analysis'],
                priority: 'high',
                posting_frequency: 'daily'
            },
            {
                id: 'educational_content',
                name: 'Educational Content',
                description: 'How-to guides, tutorials, and educational material',
                keywords: ['tutorial', 'how-to', 'guide', 'learn', 'education', 'tips'],
                priority: 'medium',
                posting_frequency: '3x_weekly'
            },
            {
                id: 'innovation_showcase',
                name: 'Innovation Showcase',
                description: 'Highlighting innovative projects and technologies',
                keywords: ['innovation', 'breakthrough', 'cutting-edge', 'revolutionary'],
                priority: 'medium',
                posting_frequency: '2x_weekly'
            },
            {
                id: 'community_highlights',
                name: 'Community Highlights',
                description: 'Featuring community projects and user-generated content',
                keywords: ['community', 'user project', 'showcase', 'feature'],
                priority: 'medium',
                posting_frequency: 'weekly'
            },
            {
                id: 'thought_leadership',
                name: 'Thought Leadership',
                description: 'Industry opinions, predictions, and leadership content',
                keywords: ['opinion', 'prediction', 'future', 'leadership', 'vision'],
                priority: 'low',
                posting_frequency: 'weekly'
            }
        ];

        categories.forEach(category => {
            this.categories.set(category.id, category);
        });
    }

    initializeTemplates() {
        const templates = [
            {
                id: 'article_share',
                name: 'Article Share Template',
                platform_variations: {
                    twitter: '📖 Interesting read: "{title}" - {summary} {url} #{hashtag1} #{hashtag2}',
                    linkedin: 'Just came across this insightful article: "{title}"\n\n{summary}\n\n{url}\n\n#{hashtag1} #{hashtag2} #{hashtag3}',
                    facebook: '📖 Worth reading: "{title}"\n\n{summary}\n\nRead more: {url}',
                    instagram: 'Swipe to learn more about {topic}! 📖\n\n{summary}\n\nLink in bio for full article 👆\n\n#{hashtag1} #{hashtag2} #{hashtag3}'
                },
                variables: ['title', 'summary', 'url', 'topic', 'hashtag1', 'hashtag2', 'hashtag3']
            },
            {
                id: 'trend_alert',
                name: 'Trend Alert Template',
                platform_variations: {
                    twitter: '🚨 Trending now in #{category}: {trend_topic} - {brief_description} Thoughts?',
                    linkedin: '📈 Industry Trend Alert: {trend_topic}\n\n{detailed_description}\n\nWhat\'s your take on this development?\n\n#{category} #trends',
                    facebook: '🚨 Trend Alert! We\'re seeing interesting developments in {trend_topic}\n\n{detailed_description}\n\nWhat do you think about this trend?',
                    instagram: 'Trend alert! 🚨✨\n\n{trend_topic} is gaining momentum\n\n{brief_description}\n\n#{category} #trends #innovation'
                },
                variables: ['category', 'trend_topic', 'brief_description', 'detailed_description']
            },
            {
                id: 'product_feature',
                name: 'Product Feature Template',
                platform_variations: {
                    twitter: '🔥 Feature spotlight: {product_name} - {key_benefit}. Perfect for {use_case}! Learn more: {url}',
                    linkedin: '🌟 Product Spotlight: {product_name}\n\n{detailed_description}\n\nKey benefits:\n• {benefit1}\n• {benefit2}\n• {benefit3}\n\nLearn more: {url}',
                    facebook: '✨ Introducing: {product_name}!\n\n{detailed_description}\n\nWhy customers love it:\n{customer_quote}\n\nDiscover more: {url}',
                    instagram: 'Meet {product_name}! ✨\n\n{brief_description}\n\nSwipe to see it in action! 👉\n\n#{product_category} #innovation #activelog'
                },
                variables: ['product_name', 'key_benefit', 'use_case', 'detailed_description', 'benefit1', 'benefit2', 'benefit3', 'customer_quote', 'brief_description', 'product_category', 'url']
            },
            {
                id: 'educational_tip',
                name: 'Educational Tip Template',
                platform_variations: {
                    twitter: '💡 Pro tip: {tip_title} - {short_explanation} Thread below 👇',
                    linkedin: '💡 {tip_category} Tip: {tip_title}\n\n{detailed_explanation}\n\n{additional_resources}\n\n#{tip_category} #learning',
                    facebook: '💡 Did you know? {tip_title}\n\n{detailed_explanation}\n\nTry this and let us know how it works for you!',
                    instagram: 'Pro tip Tuesday! 💡\n\n{tip_title}\n\n{brief_explanation}\n\nSave this post for later! 📌\n\n#tips #learning #{tip_category}'
                },
                variables: ['tip_title', 'tip_category', 'short_explanation', 'detailed_explanation', 'brief_explanation', 'additional_resources']
            }
        ];

        templates.forEach(template => {
            this.templates.set(template.id, template);
        });
    }

    initializeAutomationRules() {
        const rules = [
            {
                id: 'high_engagement_auto_curate',
                name: 'Auto-curate High Engagement Content',
                enabled: true,
                conditions: {
                    min_engagement_score: 100,
                    min_relevance_score: 0.8,
                    max_age_hours: 24
                },
                actions: ['auto_approve', 'schedule_posting', 'notify_team'],
                priority: 'high'
            },
            {
                id: 'trending_topic_alert',
                name: 'Trending Topic Auto-Detection',
                enabled: true,
                conditions: {
                    trend_velocity: 'fast',
                    relevance_score: 0.7,
                    mention_threshold: 50
                },
                actions: ['create_trend_post', 'notify_team', 'update_content_calendar'],
                priority: 'urgent'
            },
            {
                id: 'competitor_content_analysis',
                name: 'Competitor Content Analysis',
                enabled: true,
                conditions: {
                    content_type: 'competitor_post',
                    engagement_threshold: 500,
                    relevance_score: 0.6
                },
                actions: ['analyze_approach', 'suggest_counter_content', 'flag_for_review'],
                priority: 'medium'
            }
        ];

        rules.forEach(rule => {
            this.automationRules.set(rule.id, rule);
        });
    }

    // Main curation workflow
    async runCurationCycle() {
        try {
            this.emit('curation_cycle_started');

            // Step 1: Collect content from all sources
            const rawContent = await this.collectContentFromSources();
            
            // Step 2: Apply filters to raw content
            const filteredContent = await this.applyFilters(rawContent);
            
            // Step 3: Categorize and score content
            const categorizedContent = await this.categorizeContent(filteredContent);
            
            // Step 4: Apply automation rules
            const processedContent = await this.applyAutomationRules(categorizedContent);
            
            // Step 5: Generate curated collections
            const collections = await this.generateCollections(processedContent);

            this.emit('curation_cycle_completed', {
                raw_content_count: rawContent.length,
                filtered_content_count: filteredContent.length,
                categorized_content_count: categorizedContent.length,
                collections_created: collections.length
            });

            return {
                success: true,
                collections,
                stats: {
                    raw_content: rawContent.length,
                    filtered_content: filteredContent.length,
                    approved_content: processedContent.filter(c => c.approval_status === 'approved').length
                }
            };

        } catch (error) {
            this.emit('curation_cycle_error', error);
            return { success: false, error: error.message };
        }
    }

    async collectContentFromSources() {
        const allContent = [];
        
        for (const [sourceId, source] of this.sources) {
            try {
                let sourceContent = [];
                
                switch (source.type) {
                    case 'rss':
                        sourceContent = await this.collectFromRSSFeeds(source);
                        break;
                    case 'api':
                        sourceContent = await this.collectFromAPIs(source);
                        break;
                    case 'social_monitoring':
                        sourceContent = await this.collectFromSocialMonitoring(source);
                        break;
                    case 'manual':
                        sourceContent = await this.collectManualContent(source);
                        break;
                }

                sourceContent.forEach(content => {
                    content.source_id = sourceId;
                    content.collected_at = new Date();
                });

                allContent.push(...sourceContent);
                
                // Update last check time
                source.last_check = new Date();
                this.sources.set(sourceId, source);

            } catch (error) {
                this.emit('source_collection_error', { sourceId, error });
            }
        }

        return allContent;
    }

    async collectFromRSSFeeds(source) {
        const content = [];
        
        for (const url of source.urls) {
            try {
                const response = await axios.get(url, { timeout: 10000 });
                const $ = cheerio.load(response.data, { xmlMode: true });
                
                $('item').each((i, item) => {
                    const $item = $(item);
                    content.push({
                        id: crypto.randomBytes(16).toString('hex'),
                        type: 'rss_article',
                        title: $item.find('title').text().trim(),
                        description: $item.find('description').text().trim().replace(/<[^>]*>/g, ''),
                        url: $item.find('link').text().trim(),
                        published_date: new Date($item.find('pubDate').text()),
                        author: $item.find('author').text() || $item.find('dc\\:creator').text() || '',
                        categories: source.categories,
                        source_url: url,
                        raw_data: $item.html()
                    });
                });

            } catch (error) {
                this.emit('rss_feed_error', { url, error });
            }
        }

        return content;
    }

    async collectFromAPIs(source) {
        const content = [];
        
        for (const platform of source.platforms) {
            try {
                let platformContent = [];
                
                switch (platform) {
                    case 'twitter':
                        platformContent = await this.collectTwitterTrends();
                        break;
                    case 'reddit':
                        platformContent = await this.collectRedditContent();
                        break;
                    case 'hacker_news':
                        platformContent = await this.collectHackerNewsContent();
                        break;
                    case 'unsplash':
                        platformContent = await this.collectUnsplashImages();
                        break;
                }

                content.push(...platformContent);

            } catch (error) {
                this.emit('api_collection_error', { platform, error });
            }
        }

        return content;
    }

    async collectTwitterTrends() {
        // This would integrate with Twitter API v2
        // For now, returning mock data
        return [
            {
                id: crypto.randomBytes(16).toString('hex'),
                type: 'twitter_trend',
                title: 'IoT Innovation',
                description: 'Trending topic about IoT innovations',
                url: 'https://twitter.com/search?q=%23IoTInnovation',
                published_date: new Date(),
                engagement_metrics: { tweets: 1250, likes: 8900, retweets: 2340 },
                categories: ['technology', 'trending']
            }
        ];
    }

    async collectRedditContent() {
        try {
            const response = await axios.get('https://www.reddit.com/r/technology/hot.json?limit=25');
            const posts = response.data.data.children;
            
            return posts.map(post => {
                const data = post.data;
                return {
                    id: crypto.randomBytes(16).toString('hex'),
                    type: 'reddit_post',
                    title: data.title,
                    description: data.selftext || '',
                    url: data.url,
                    published_date: new Date(data.created_utc * 1000),
                    author: data.author,
                    engagement_metrics: {
                        upvotes: data.ups,
                        downvotes: data.downs,
                        comments: data.num_comments,
                        score: data.score
                    },
                    subreddit: data.subreddit,
                    categories: ['reddit', 'technology']
                };
            });

        } catch (error) {
            this.emit('reddit_collection_error', error);
            return [];
        }
    }

    async collectHackerNewsContent() {
        try {
            // Get top stories
            const topStoriesResponse = await axios.get('https://hacker-news.firebaseio.com/v0/topstories.json');
            const topStoryIds = topStoriesResponse.data.slice(0, 20);
            
            const stories = [];
            for (const id of topStoryIds) {
                try {
                    const storyResponse = await axios.get(`https://hacker-news.firebaseio.com/v0/item/${id}.json`);
                    const story = storyResponse.data;
                    
                    stories.push({
                        id: crypto.randomBytes(16).toString('hex'),
                        type: 'hackernews_story',
                        title: story.title,
                        description: story.text || '',
                        url: story.url || `https://news.ycombinator.com/item?id=${story.id}`,
                        published_date: new Date(story.time * 1000),
                        author: story.by,
                        engagement_metrics: {
                            score: story.score || 0,
                            comments: story.descendants || 0
                        },
                        categories: ['hackernews', 'technology']
                    });
                } catch (error) {
                    // Skip individual story errors
                }
            }
            
            return stories;

        } catch (error) {
            this.emit('hackernews_collection_error', error);
            return [];
        }
    }

    async collectUnsplashImages() {
        // This would require Unsplash API key
        // Returning mock data for now
        return [
            {
                id: crypto.randomBytes(16).toString('hex'),
                type: 'unsplash_image',
                title: 'Technology Innovation',
                description: 'High-quality image for technology posts',
                url: 'https://images.unsplash.com/photo-technology',
                published_date: new Date(),
                author: 'Photographer Name',
                image_data: {
                    width: 1920,
                    height: 1080,
                    format: 'jpg'
                },
                categories: ['visual', 'technology']
            }
        ];
    }

    async applyFilters(rawContent) {
        let filteredContent = [...rawContent];

        // Apply filters in priority order
        const orderedFilters = Array.from(this.filters.values())
            .filter(filter => filter.enabled)
            .sort((a, b) => a.priority - b.priority);

        for (const filter of orderedFilters) {
            filteredContent = await this.applyFilter(filter, filteredContent);
        }

        return filteredContent;
    }

    async applyFilter(filter, content) {
        switch (filter.type) {
            case 'keyword_matching':
                return this.applyKeywordFilter(filter, content);
            case 'multi_factor':
                return this.applyQualityFilter(filter, content);
            case 'temporal':
                return this.applyFreshnessFilter(filter, content);
            case 'sentiment':
                return await this.applySentimentFilter(filter, content);
            case 'similarity':
                return this.applyDuplicateFilter(filter, content);
            default:
                return content;
        }
    }

    applyKeywordFilter(filter, content) {
        const { required_keywords, excluded_keywords } = filter.criteria;
        
        return content.filter(item => {
            const text = `${item.title} ${item.description}`.toLowerCase();
            
            // Check required keywords
            const hasRequired = required_keywords.some(keyword => 
                text.includes(keyword.toLowerCase())
            );
            
            // Check excluded keywords
            const hasExcluded = excluded_keywords.some(keyword => 
                text.includes(keyword.toLowerCase())
            );
            
            return hasRequired && !hasExcluded;
        });
    }

    applyQualityFilter(filter, content) {
        const { min_word_count, max_word_count, requires_images, source_authority_min } = filter.criteria;
        
        return content.filter(item => {
            const wordCount = item.description.split(' ').length;
            
            if (wordCount < min_word_count || wordCount > max_word_count) {
                return false;
            }
            
            if (requires_images && !item.image_data && item.type !== 'unsplash_image') {
                return false;
            }
            
            // Simple authority score based on source
            const authorityScore = this.calculateSourceAuthority(item.source_id);
            if (authorityScore < source_authority_min) {
                return false;
            }
            
            return true;
        });
    }

    applyFreshnessFilter(filter, content) {
        const { max_age_hours, prefer_recent } = filter.criteria;
        const now = new Date();
        const maxAge = max_age_hours * 60 * 60 * 1000; // Convert to milliseconds
        
        let filtered = content.filter(item => {
            const age = now - new Date(item.published_date);
            return age <= maxAge;
        });
        
        if (prefer_recent) {
            filtered.sort((a, b) => new Date(b.published_date) - new Date(a.published_date));
        }
        
        return filtered;
    }

    async applySentimentFilter(filter, content) {
        const { min_sentiment, prefer_positive } = filter.criteria;
        
        const analyzedContent = content.map(item => {
            const sentiment = analyze(`${item.title} ${item.description}`);
            item.sentiment_score = sentiment.score;
            item.sentiment_label = sentiment.score > 0.1 ? 'positive' : 
                                  sentiment.score < -0.1 ? 'negative' : 'neutral';
            return item;
        });
        
        let filtered = analyzedContent.filter(item => 
            item.sentiment_score >= min_sentiment
        );
        
        if (prefer_positive) {
            filtered.sort((a, b) => b.sentiment_score - a.sentiment_score);
        }
        
        return filtered;
    }

    applyDuplicateFilter(filter, content) {
        const { max_similarity, check_title, check_content } = filter.criteria;
        const uniqueContent = [];
        
        for (const item of content) {
            let isDuplicate = false;
            
            for (const existing of uniqueContent) {
                let similarity = 0;
                
                if (check_title) {
                    similarity += this.calculateStringSimilarity(item.title, existing.title) * 0.6;
                }
                
                if (check_content) {
                    similarity += this.calculateStringSimilarity(item.description, existing.description) * 0.4;
                }
                
                if (similarity >= max_similarity) {
                    isDuplicate = true;
                    break;
                }
            }
            
            if (!isDuplicate) {
                uniqueContent.push(item);
            }
        }
        
        return uniqueContent;
    }

    calculateStringSimilarity(str1, str2) {
        // Simple Jaccard similarity
        const set1 = new Set(str1.toLowerCase().split(' '));
        const set2 = new Set(str2.toLowerCase().split(' '));
        
        const intersection = new Set([...set1].filter(x => set2.has(x)));
        const union = new Set([...set1, ...set2]);
        
        return intersection.size / union.size;
    }

    calculateSourceAuthority(sourceId) {
        const authorityScores = {
            'tech_blogs': 0.9,
            'iot_news': 0.8,
            'social_trends': 0.6,
            'industry_reports': 0.95,
            'visual_content': 0.5,
            'competitor_analysis': 0.7
        };
        
        return authorityScores[sourceId] || 0.5;
    }

    async categorizeContent(content) {
        const categorizedContent = [];
        
        for (const item of content) {
            const category = await this.determineContentCategory(item);
            const relevanceScore = await this.calculateRelevanceScore(item, category);
            const engagementPotential = this.predictEngagementPotential(item);
            
            categorizedContent.push({
                ...item,
                category: category.id,
                category_confidence: category.confidence,
                relevance_score: relevanceScore,
                engagement_potential: engagementPotential,
                curation_score: (relevanceScore * 0.4) + (engagementPotential * 0.3) + (category.confidence * 0.3)
            });
        }
        
        // Sort by curation score
        return categorizedContent.sort((a, b) => b.curation_score - a.curation_score);
    }

    async determineContentCategory(item) {
        const text = `${item.title} ${item.description}`.toLowerCase();
        let bestMatch = null;
        let bestScore = 0;
        
        for (const [categoryId, category] of this.categories) {
            let score = 0;
            
            // Keyword matching
            const keywordMatches = category.keywords.filter(keyword => 
                text.includes(keyword.toLowerCase())
            ).length;
            score += keywordMatches * 10;
            
            // Category-specific logic
            switch (categoryId) {
                case 'product_spotlight':
                    if (text.includes('activelog') || text.includes('fish counter') || text.includes('solar camera')) {
                        score += 50;
                    }
                    break;
                case 'educational_content':
                    if (text.includes('how to') || text.includes('tutorial') || text.includes('guide')) {
                        score += 30;
                    }
                    break;
                case 'innovation_showcase':
                    if (text.includes('new') || text.includes('innovative') || text.includes('breakthrough')) {
                        score += 25;
                    }
                    break;
            }
            
            if (score > bestScore) {
                bestScore = score;
                bestMatch = { id: categoryId, confidence: Math.min(score / 100, 1) };
            }
        }
        
        return bestMatch || { id: 'uncategorized', confidence: 0 };
    }

    async calculateRelevanceScore(item, category) {
        try {
            // Use AI for more sophisticated relevance scoring
            const prompt = `Rate the relevance of this content for social media posting about IoT, sensors, and hardware technology (0-100):

Title: ${item.title}
Description: ${item.description.substring(0, 500)}
Category: ${category.id}

Consider:
- Relevance to IoT/hardware/technology
- Quality of content
- Engagement potential
- Brand alignment

Score (0-100):`;

            const completion = await this.openai.chat.completions.create({
                model: "gpt-3.5-turbo",
                messages: [{ role: "user", content: prompt }],
                temperature: 0.3,
                max_tokens: 10
            });

            const score = parseInt(completion.choices[0].message.content.trim()) || 0;
            return Math.min(Math.max(score / 100, 0), 1);

        } catch (error) {
            // Fallback to simple keyword-based scoring
            return this.calculateSimpleRelevanceScore(item);
        }
    }

    calculateSimpleRelevanceScore(item) {
        const relevantKeywords = ['iot', 'sensor', 'technology', 'innovation', 'hardware', 'smart', 'connected'];
        const text = `${item.title} ${item.description}`.toLowerCase();
        
        const matches = relevantKeywords.filter(keyword => 
            text.includes(keyword)
        ).length;
        
        return Math.min(matches / relevantKeywords.length, 1);
    }

    predictEngagementPotential(item) {
        let score = 0;
        
        // Factor in source engagement metrics
        if (item.engagement_metrics) {
            const metrics = item.engagement_metrics;
            if (metrics.likes || metrics.upvotes || metrics.score) {
                score += 0.3;
            }
            if (metrics.comments || metrics.replies) {
                score += 0.3;
            }
            if (metrics.shares || metrics.retweets) {
                score += 0.4;
            }
        }
        
        // Factor in content characteristics
        if (item.title.includes('?')) score += 0.1; // Questions generate engagement
        if (item.title.includes('!')) score += 0.1; // Exclamations show excitement
        if (item.description.length > 200) score += 0.1; // Detailed content
        
        // Factor in timeliness
        const age = new Date() - new Date(item.published_date);
        const ageHours = age / (1000 * 60 * 60);
        if (ageHours < 24) score += 0.2;
        else if (ageHours < 48) score += 0.1;
        
        return Math.min(score, 1);
    }

    async applyAutomationRules(content) {
        const processedContent = [];
        
        for (const item of content) {
            let processedItem = { ...item };
            
            // Check each automation rule
            for (const [ruleId, rule] of this.automationRules) {
                if (!rule.enabled) continue;
                
                if (this.evaluateRuleConditions(rule.conditions, processedItem)) {
                    processedItem = await this.executeRuleActions(rule.actions, processedItem);
                    processedItem.triggered_rules = processedItem.triggered_rules || [];
                    processedItem.triggered_rules.push(ruleId);
                }
            }
            
            processedContent.push(processedItem);
        }
        
        return processedContent;
    }

    evaluateRuleConditions(conditions, item) {
        if (conditions.min_engagement_score && (item.engagement_potential || 0) < conditions.min_engagement_score / 100) {
            return false;
        }
        
        if (conditions.min_relevance_score && (item.relevance_score || 0) < conditions.min_relevance_score) {
            return false;
        }
        
        if (conditions.max_age_hours) {
            const age = new Date() - new Date(item.published_date);
            const ageHours = age / (1000 * 60 * 60);
            if (ageHours > conditions.max_age_hours) {
                return false;
            }
        }
        
        return true;
    }

    async executeRuleActions(actions, item) {
        let processedItem = { ...item };
        
        for (const action of actions) {
            switch (action) {
                case 'auto_approve':
                    processedItem.approval_status = 'approved';
                    break;
                case 'schedule_posting':
                    processedItem.scheduled_for_posting = true;
                    break;
                case 'notify_team':
                    this.emit('content_notification', { item: processedItem, reason: 'automation_rule' });
                    break;
                case 'create_trend_post':
                    processedItem.suggested_posts = await this.generateTrendPost(processedItem);
                    break;
                case 'flag_for_review':
                    processedItem.review_required = true;
                    break;
            }
        }
        
        return processedItem;
    }

    async generateTrendPost(item) {
        try {
            const template = this.templates.get('trend_alert');
            const posts = {};
            
            for (const [platform, templateText] of Object.entries(template.platform_variations)) {
                posts[platform] = await this.fillTemplate(templateText, {
                    category: item.category,
                    trend_topic: item.title,
                    brief_description: item.description.substring(0, 100),
                    detailed_description: item.description.substring(0, 300)
                });
            }
            
            return posts;
            
        } catch (error) {
            this.emit('template_generation_error', { item, error });
            return {};
        }
    }

    async generateCollections(content) {
        const collections = [];
        
        // Group by category
        const categoryGroups = {};
        content.forEach(item => {
            const category = item.category || 'uncategorized';
            if (!categoryGroups[category]) {
                categoryGroups[category] = [];
            }
            categoryGroups[category].push(item);
        });
        
        // Create collections for each category
        for (const [category, items] of Object.entries(categoryGroups)) {
            if (items.length > 0) {
                const collection = {
                    id: crypto.randomBytes(16).toString('hex'),
                    category: category,
                    title: this.categories.get(category)?.name || category,
                    items: items.slice(0, 10), // Top 10 items
                    created_at: new Date(),
                    total_items: items.length,
                    average_score: items.reduce((sum, item) => sum + item.curation_score, 0) / items.length,
                    suggested_posts: await this.generateCollectionPosts(items.slice(0, 5))
                };
                
                this.collections.set(collection.id, collection);
                collections.push(collection);
            }
        }
        
        return collections;
    }

    async generateCollectionPosts(items) {
        const posts = {};
        
        try {
            for (const item of items) {
                const template = this.selectBestTemplate(item);
                if (template) {
                    for (const [platform, templateText] of Object.entries(template.platform_variations)) {
                        if (!posts[platform]) {
                            posts[platform] = [];
                        }
                        
                        const post = await this.fillTemplate(templateText, {
                            title: item.title,
                            summary: item.description.substring(0, 150),
                            url: item.url,
                            topic: item.category,
                            hashtag1: this.extractHashtags(item)[0] || 'technology',
                            hashtag2: this.extractHashtags(item)[1] || 'innovation',
                            hashtag3: this.extractHashtags(item)[2] || 'activelog'
                        });
                        
                        posts[platform].push({
                            content: post,
                            item_id: item.id,
                            engagement_potential: item.engagement_potential
                        });
                    }
                }
            }
        } catch (error) {
            this.emit('post_generation_error', error);
        }
        
        return posts;
    }

    selectBestTemplate(item) {
        if (item.category === 'product_spotlight') {
            return this.templates.get('product_feature');
        } else if (item.category === 'educational_content') {
            return this.templates.get('educational_tip');
        } else {
            return this.templates.get('article_share');
        }
    }

    extractHashtags(item) {
        const text = `${item.title} ${item.description}`.toLowerCase();
        const potentialHashtags = ['iot', 'technology', 'innovation', 'sensors', 'hardware', 'smart', 'connected', 'activelog'];
        
        return potentialHashtags.filter(tag => 
            text.includes(tag)
        ).slice(0, 5);
    }

    async fillTemplate(templateText, variables) {
        let filled = templateText;
        
        Object.entries(variables).forEach(([key, value]) => {
            const regex = new RegExp(`{${key}}`, 'g');
            filled = filled.replace(regex, value || '');
        });
        
        return filled.trim();
    }

    // Manual curation methods
    async approveContent(contentId) {
        // Find content in collections
        for (const [collectionId, collection] of this.collections) {
            const item = collection.items.find(i => i.id === contentId);
            if (item) {
                item.approval_status = 'approved';
                item.approved_at = new Date();
                this.emit('content_approved', { contentId, collectionId });
                return { success: true, message: 'Content approved' };
            }
        }
        
        return { success: false, error: 'Content not found' };
    }

    async rejectContent(contentId, reason = '') {
        for (const [collectionId, collection] of this.collections) {
            const item = collection.items.find(i => i.id === contentId);
            if (item) {
                item.approval_status = 'rejected';
                item.rejection_reason = reason;
                item.rejected_at = new Date();
                this.emit('content_rejected', { contentId, collectionId, reason });
                return { success: true, message: 'Content rejected' };
            }
        }
        
        return { success: false, error: 'Content not found' };
    }

    // Analytics and reporting
    getCurationStats(timeframe = '24h') {
        const now = new Date();
        const cutoff = timeframe === '24h' ? 
            new Date(now.getTime() - 24 * 60 * 60 * 1000) :
            new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        
        const recentCollections = Array.from(this.collections.values())
            .filter(c => c.created_at >= cutoff);
        
        const stats = {
            collections_created: recentCollections.length,
            total_content_items: recentCollections.reduce((sum, c) => sum + c.items.length, 0),
            average_curation_score: 0,
            category_breakdown: {},
            approval_rate: 0,
            source_breakdown: {}
        };
        
        if (recentCollections.length > 0) {
            stats.average_curation_score = recentCollections.reduce((sum, c) => sum + c.average_score, 0) / recentCollections.length;
        }
        
        // Calculate category breakdown
        recentCollections.forEach(collection => {
            stats.category_breakdown[collection.category] = (stats.category_breakdown[collection.category] || 0) + 1;
        });
        
        return stats;
    }

    getSourcePerformance() {
        const performance = {};
        
        for (const [sourceId, source] of this.sources) {
            performance[sourceId] = {
                name: source.name,
                type: source.type,
                last_check: source.last_check,
                priority: source.priority,
                content_contributed: 0,
                average_quality_score: 0,
                success_rate: 1.0 // Would calculate based on actual data
            };
        }
        
        return performance;
    }
}

export default ContentCurationTools;