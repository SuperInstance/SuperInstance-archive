const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');
const moment = require('moment');
const axios = require('axios');
const cheerio = require('cheerio');

class SEOOptimizer extends EventEmitter {
    constructor(redisClient, socketServer, logger) {
        super();
        this.redis = redisClient;
        this.io = socketServer;
        this.logger = logger;
        
        this.websites = new Map();
        this.keywords = new Map();
        this.rankings = new Map();
        this.audits = new Map();
        this.competitors = new Map();
        this.backlinks = new Map();
        
        this.setupEventHandlers();
        this.initializeSEOTools();
        this.startRankingMonitor();
        this.startAuditEngine();
    }

    setupEventHandlers() {
        this.on('website_added', this.handleWebsiteAdded.bind(this));
        this.on('audit_completed', this.handleAuditCompleted.bind(this));
        this.on('ranking_changed', this.handleRankingChanged.bind(this));
        this.on('optimization_suggestion', this.handleOptimizationSuggestion.bind(this));
        this.on('competitor_analyzed', this.handleCompetitorAnalyzed.bind(this));
    }

    initializeSEOTools() {
        this.seoTools = {
            googleSearchConsole: {
                name: 'Google Search Console',
                apiUrl: 'https://searchconsole.googleapis.com/v1',
                features: ['search_analytics', 'indexing', 'sitemaps', 'mobile_usability']
            },
            semrush: {
                name: 'SEMrush',
                apiUrl: 'https://api.semrush.com/',
                features: ['keyword_research', 'competitor_analysis', 'backlinks', 'rank_tracking']
            },
            ahrefs: {
                name: 'Ahrefs',
                apiUrl: 'https://apiv2.ahrefs.com/',
                features: ['backlinks', 'keyword_research', 'content_explorer', 'rank_tracker']
            },
            moz: {
                name: 'Moz',
                apiUrl: 'https://lsapi.seomoz.com/v2/',
                features: ['link_explorer', 'keyword_explorer', 'rank_tracker', 'site_crawl']
            },
            screaming_frog: {
                name: 'Screaming Frog',
                features: ['site_crawl', 'technical_seo', 'broken_links', 'redirects']
            }
        };
        
        this.searchEngines = {
            google: {
                name: 'Google',
                baseUrl: 'https://www.google.com/search',
                marketShare: 92.47
            },
            bing: {
                name: 'Bing',
                baseUrl: 'https://www.bing.com/search',
                marketShare: 3.39
            },
            yahoo: {
                name: 'Yahoo',
                baseUrl: 'https://search.yahoo.com/search',
                marketShare: 1.20
            }
        };
    }

    async addWebsite(websiteData) {
        try {
            const websiteId = uuidv4();
            const website = {
                id: websiteId,
                domain: websiteData.domain,
                url: websiteData.url,
                name: websiteData.name || websiteData.domain,
                description: websiteData.description || '',
                industry: websiteData.industry || '',
                targetCountries: websiteData.targetCountries || ['US'],
                targetLanguages: websiteData.targetLanguages || ['en'],
                competitors: websiteData.competitors || [],
                settings: {
                    crawlDelay: websiteData.settings?.crawlDelay || 1000,
                    maxPages: websiteData.settings?.maxPages || 1000,
                    followExternal: websiteData.settings?.followExternal || false,
                    checkImages: websiteData.settings?.checkImages !== false,
                    checkMobile: websiteData.settings?.checkMobile !== false
                },
                integrations: {
                    googleAnalytics: websiteData.integrations?.googleAnalytics || null,
                    searchConsole: websiteData.integrations?.searchConsole || null,
                    gtm: websiteData.integrations?.gtm || null
                },
                createdAt: new Date(),
                createdBy: websiteData.createdBy,
                lastAudit: null,
                lastCrawl: null,
                status: 'active',
                analytics: {
                    totalPages: 0,
                    indexedPages: 0,
                    organicTraffic: 0,
                    averagePosition: 0,
                    totalKeywords: 0,
                    topKeywords: [],
                    technicalScore: 0,
                    contentScore: 0,
                    backlinksCount: 0,
                    domainAuthority: 0
                }
            };

            this.websites.set(websiteId, website);
            await this.redis.hset('seo_websites', websiteId, JSON.stringify(website));
            
            // Perform initial analysis
            await this.performInitialAnalysis(websiteId);
            
            this.logger.info('Website added to SEO monitoring', { 
                websiteId, 
                domain: website.domain,
                name: website.name
            });
            
            this.io.emit('website_added', {
                websiteId,
                domain: website.domain,
                name: website.name,
                status: website.status
            });
            
            this.emit('website_added', website);
            
            return { success: true, websiteId, website: this.sanitizeWebsiteData(website) };
        } catch (error) {
            this.logger.error('Failed to add website', { error: error.message, websiteData });
            throw new Error(`Website addition failed: ${error.message}`);
        }
    }

    async analyzePage(pageData) {
        try {
            const analysisId = uuidv4();
            const url = pageData.url;
            
            // Fetch page content
            const pageContent = await this.fetchPageContent(url);
            
            // Parse HTML
            const $ = cheerio.load(pageContent.html);
            
            // Perform comprehensive analysis
            const analysis = {
                id: analysisId,
                url,
                websiteId: pageData.websiteId || null,
                timestamp: new Date(),
                technical: await this.analyzeTechnicalSEO($, pageContent),
                onPage: await this.analyzeOnPageSEO($, pageContent),
                content: await this.analyzeContent($, pageContent),
                mobile: await this.analyzeMobileOptimization($, pageContent),
                performance: pageContent.performance || {},
                accessibility: await this.analyzeAccessibility($, pageContent),
                structured: await this.analyzeStructuredData($),
                social: await this.analyzeSocialSignals($),
                recommendations: []
            };
            
            // Generate recommendations
            analysis.recommendations = await this.generateSEORecommendations(analysis);
            
            // Calculate overall score
            analysis.overallScore = this.calculateSEOScore(analysis);
            
            // Store analysis
            await this.redis.hset('seo_analyses', analysisId, JSON.stringify(analysis));
            
            this.logger.info('Page SEO analysis completed', { 
                analysisId,
                url,
                score: analysis.overallScore,
                recommendations: analysis.recommendations.length
            });
            
            return { success: true, analysisId, analysis };
        } catch (error) {
            this.logger.error('Failed to analyze page', { error: error.message, pageData });
            throw new Error(`Page analysis failed: ${error.message}`);
        }
    }

    async researchKeywords(researchData) {
        try {
            const researchId = uuidv4();
            const seedKeywords = researchData.keywords || [];
            const targetCountry = researchData.country || 'US';
            const language = researchData.language || 'en';
            
            const keywordResearch = {
                id: researchId,
                seedKeywords,
                targetCountry,
                language,
                websiteId: researchData.websiteId || null,
                createdAt: new Date(),
                keywords: [],
                clusters: [],
                opportunities: [],
                analytics: {
                    totalKeywords: 0,
                    totalSearchVolume: 0,
                    averageDifficulty: 0,
                    avgCostPerClick: 0
                }
            };
            
            // Research keywords using multiple sources
            const keywordData = await this.gatherKeywordData(seedKeywords, targetCountry, language);
            
            // Process and analyze keywords
            for (const keyword of keywordData) {
                const processedKeyword = {
                    id: uuidv4(),
                    term: keyword.term,
                    searchVolume: keyword.searchVolume || 0,
                    difficulty: keyword.difficulty || 0,
                    cpc: keyword.cpc || 0,
                    competition: keyword.competition || 'low',
                    trend: keyword.trend || [],
                    intent: this.classifySearchIntent(keyword.term),
                    variations: keyword.variations || [],
                    relatedKeywords: keyword.relatedKeywords || [],
                    questions: keyword.questions || [],
                    currentRanking: null,
                    opportunity: this.calculateKeywordOpportunity(keyword)
                };
                
                keywordResearch.keywords.push(processedKeyword);
            }
            
            // Create keyword clusters
            keywordResearch.clusters = await this.createKeywordClusters(keywordResearch.keywords);
            
            // Identify opportunities
            keywordResearch.opportunities = this.identifyKeywordOpportunities(keywordResearch.keywords);
            
            // Calculate analytics
            keywordResearch.analytics = this.calculateKeywordAnalytics(keywordResearch.keywords);
            
            // Store research
            await this.redis.hset('keyword_research', researchId, JSON.stringify(keywordResearch));
            
            this.logger.info('Keyword research completed', { 
                researchId,
                totalKeywords: keywordResearch.keywords.length,
                clusters: keywordResearch.clusters.length,
                opportunities: keywordResearch.opportunities.length
            });
            
            return { 
                success: true, 
                researchId, 
                research: this.sanitizeKeywordResearch(keywordResearch) 
            };
        } catch (error) {
            this.logger.error('Failed to research keywords', { error: error.message, researchData });
            throw new Error(`Keyword research failed: ${error.message}`);
        }
    }

    async trackRankings(trackingData) {
        try {
            const trackingId = uuidv4();
            const websiteId = trackingData.websiteId;
            const keywords = trackingData.keywords || [];
            const searchEngines = trackingData.searchEngines || ['google'];
            const locations = trackingData.locations || ['US'];
            
            const tracking = {
                id: trackingId,
                websiteId,
                keywords: keywords.map(keyword => ({
                    id: uuidv4(),
                    term: keyword,
                    currentPosition: null,
                    previousPosition: null,
                    bestPosition: null,
                    url: null,
                    lastChecked: null,
                    history: []
                })),
                searchEngines,
                locations,
                frequency: trackingData.frequency || 'daily',
                status: 'active',
                createdAt: new Date(),
                lastUpdate: null,
                analytics: {
                    averagePosition: 0,
                    topRankings: 0,
                    improved: 0,
                    declined: 0,
                    visibility: 0
                }
            };
            
            // Perform initial ranking check
            await this.checkRankings(tracking);
            
            // Store tracking configuration
            await this.redis.hset('ranking_tracking', trackingId, JSON.stringify(tracking));
            
            this.logger.info('Ranking tracking started', { 
                trackingId,
                websiteId,
                keywords: keywords.length,
                searchEngines: searchEngines.length
            });
            
            return { success: true, trackingId, tracking };
        } catch (error) {
            this.logger.error('Failed to start ranking tracking', { error: error.message, trackingData });
            throw error;
        }
    }

    async performInitialAnalysis(websiteId) {
        try {
            const website = this.websites.get(websiteId);
            if (!website) return;
            
            // Crawl website
            const crawlResults = await this.crawlWebsite(website);
            
            // Analyze homepage
            const homepageAnalysis = await this.analyzePage({ 
                url: website.url, 
                websiteId 
            });
            
            // Check technical SEO basics
            const technicalCheck = await this.performTechnicalCheck(website);
            
            // Update website analytics
            website.analytics = {
                ...website.analytics,
                totalPages: crawlResults.totalPages,
                technicalScore: technicalCheck.score,
                contentScore: homepageAnalysis.analysis?.content?.score || 0,
                lastAudit: new Date()
            };
            
            website.lastCrawl = new Date();
            
            await this.redis.hset('seo_websites', websiteId, JSON.stringify(website));
            
            this.logger.info('Initial website analysis completed', { 
                websiteId,
                totalPages: crawlResults.totalPages,
                technicalScore: technicalCheck.score
            });
            
        } catch (error) {
            this.logger.error('Initial analysis failed', { error: error.message, websiteId });
        }
    }

    async fetchPageContent(url) {
        try {
            const startTime = Date.now();
            
            const response = await axios.get(url, {
                headers: {
                    'User-Agent': 'SEO-Optimizer-Bot/1.0 (compatible; SEO analysis tool)',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate',
                    'Cache-Control': 'no-cache'
                },
                timeout: 30000,
                maxRedirects: 5
            });
            
            const loadTime = Date.now() - startTime;
            
            return {
                html: response.data,
                status: response.status,
                headers: response.headers,
                performance: {
                    loadTime,
                    size: Buffer.byteLength(response.data, 'utf8'),
                    redirects: response.request._redirects?.length || 0
                },
                url: response.request.res.responseUrl || url
            };
        } catch (error) {
            this.logger.error('Failed to fetch page content', { error: error.message, url });
            throw new Error(`Could not fetch page: ${error.message}`);
        }
    }

    async analyzeTechnicalSEO($, pageContent) {
        const technical = {
            score: 0,
            issues: [],
            checks: {}
        };
        
        // Page speed
        technical.checks.pageSpeed = {
            loadTime: pageContent.performance.loadTime,
            size: pageContent.performance.size,
            score: this.calculateSpeedScore(pageContent.performance.loadTime),
            recommendation: pageContent.performance.loadTime > 3000 ? 
                'Optimize page load time (currently > 3 seconds)' : 'Page load time is good'
        };
        
        // HTTPS
        technical.checks.https = {
            enabled: pageContent.url.startsWith('https://'),
            score: pageContent.url.startsWith('https://') ? 10 : 0,
            recommendation: pageContent.url.startsWith('https://') ? 
                'HTTPS is properly implemented' : 'Implement HTTPS for security and SEO benefits'
        };
        
        // Meta robots
        const robotsMeta = $('meta[name="robots"]').attr('content') || '';
        technical.checks.robots = {
            content: robotsMeta,
            noindex: robotsMeta.includes('noindex'),
            nofollow: robotsMeta.includes('nofollow'),
            score: robotsMeta.includes('noindex') ? 0 : 10,
            recommendation: robotsMeta.includes('noindex') ? 
                'Page is set to noindex - remove if you want it indexed' : 'Robots meta tag is properly configured'
        };
        
        // Canonical URL
        const canonical = $('link[rel="canonical"]').attr('href');
        technical.checks.canonical = {
            url: canonical,
            present: !!canonical,
            score: canonical ? 10 : 5,
            recommendation: canonical ? 
                'Canonical URL is properly set' : 'Consider adding canonical URL for duplicate content prevention'
        };
        
        // XML Sitemap (check if referenced)
        const sitemapLinks = $('link[type="application/xml"]').length;
        technical.checks.sitemap = {
            referenced: sitemapLinks > 0,
            score: sitemapLinks > 0 ? 10 : 5,
            recommendation: sitemapLinks > 0 ? 
                'XML sitemap is referenced' : 'Consider referencing XML sitemap in HTML head'
        };
        
        // Mobile viewport
        const viewport = $('meta[name="viewport"]').attr('content');
        technical.checks.viewport = {
            content: viewport,
            present: !!viewport,
            responsive: viewport?.includes('width=device-width'),
            score: viewport?.includes('width=device-width') ? 10 : 0,
            recommendation: viewport?.includes('width=device-width') ? 
                'Mobile viewport is properly configured' : 'Add responsive viewport meta tag'
        };
        
        // Calculate overall technical score
        const scores = Object.values(technical.checks).map(check => check.score);
        technical.score = scores.reduce((sum, score) => sum + score, 0) / scores.length;
        
        // Identify issues
        technical.issues = Object.entries(technical.checks)
            .filter(([key, check]) => check.score < 8)
            .map(([key, check]) => ({
                type: key,
                severity: check.score === 0 ? 'high' : 'medium',
                message: check.recommendation
            }));
        
        return technical;
    }

    async analyzeOnPageSEO($, pageContent) {
        const onPage = {
            score: 0,
            elements: {}
        };
        
        // Title tag
        const title = $('title').text() || '';
        onPage.elements.title = {
            text: title,
            length: title.length,
            present: title.length > 0,
            optimal: title.length >= 30 && title.length <= 60,
            score: this.calculateTitleScore(title),
            recommendation: this.getTitleRecommendation(title)
        };
        
        // Meta description
        const description = $('meta[name="description"]').attr('content') || '';
        onPage.elements.metaDescription = {
            text: description,
            length: description.length,
            present: description.length > 0,
            optimal: description.length >= 120 && description.length <= 160,
            score: this.calculateDescriptionScore(description),
            recommendation: this.getDescriptionRecommendation(description)
        };
        
        // Headings
        const headings = {
            h1: $('h1').length,
            h2: $('h2').length,
            h3: $('h3').length,
            h4: $('h4').length,
            h5: $('h5').length,
            h6: $('h6').length
        };
        
        const h1Text = $('h1').first().text() || '';
        onPage.elements.headings = {
            structure: headings,
            h1Text,
            h1Count: headings.h1,
            properStructure: headings.h1 === 1 && headings.h2 > 0,
            score: this.calculateHeadingScore(headings, h1Text),
            recommendation: this.getHeadingRecommendation(headings, h1Text)
        };
        
        // Images
        const images = $('img');
        const imagesWithAlt = $('img[alt]');
        const imagesWithoutAlt = images.length - imagesWithAlt.length;
        
        onPage.elements.images = {
            total: images.length,
            withAlt: imagesWithAlt.length,
            withoutAlt: imagesWithoutAlt,
            altPercentage: images.length > 0 ? (imagesWithAlt.length / images.length) * 100 : 100,
            score: images.length > 0 ? Math.min((imagesWithAlt.length / images.length) * 10, 10) : 10,
            recommendation: imagesWithoutAlt > 0 ? 
                `Add alt text to ${imagesWithoutAlt} images` : 'All images have alt text'
        };
        
        // Internal and external links
        const allLinks = $('a[href]');
        const internalLinks = allLinks.filter((i, el) => {
            const href = $(el).attr('href');
            return href && (href.startsWith('/') || href.includes(new URL(pageContent.url).hostname));
        });
        const externalLinks = allLinks.length - internalLinks.length;
        
        onPage.elements.links = {
            total: allLinks.length,
            internal: internalLinks.length,
            external: externalLinks,
            score: allLinks.length > 0 ? Math.min(allLinks.length / 5, 10) : 5,
            recommendation: allLinks.length < 3 ? 
                'Consider adding more internal links' : 'Good link structure'
        };
        
        // Calculate overall on-page score
        const scores = Object.values(onPage.elements).map(element => element.score);
        onPage.score = scores.reduce((sum, score) => sum + score, 0) / scores.length;
        
        return onPage;
    }

    async analyzeContent($, pageContent) {
        const content = {
            score: 0,
            analysis: {}
        };
        
        // Extract text content
        const textContent = $('body').text().replace(/\s+/g, ' ').trim();
        const wordCount = textContent.split(' ').filter(word => word.length > 0).length;
        
        content.analysis.wordCount = {
            count: wordCount,
            adequate: wordCount >= 300,
            score: this.calculateWordCountScore(wordCount),
            recommendation: this.getWordCountRecommendation(wordCount)
        };
        
        // Reading level analysis
        content.analysis.readability = {
            score: this.calculateFleschReadingEase(textContent),
            level: this.getReadingLevel(textContent),
            recommendation: 'Aim for 60-70 Flesch Reading Ease score for general audiences'
        };
        
        // Keyword density (basic analysis)
        const words = textContent.toLowerCase().match(/\b\w+\b/g) || [];
        const wordFreq = {};
        words.forEach(word => {
            if (word.length > 3) {
                wordFreq[word] = (wordFreq[word] || 0) + 1;
            }
        });
        
        const topWords = Object.entries(wordFreq)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 10)
            .map(([word, count]) => ({
                word,
                count,
                density: ((count / words.length) * 100).toFixed(2)
            }));
        
        content.analysis.keywords = {
            topWords,
            uniqueWords: Object.keys(wordFreq).length,
            score: topWords.length > 0 ? 8 : 5,
            recommendation: 'Monitor keyword density to ensure natural content flow'
        };
        
        // Calculate overall content score
        const scores = Object.values(content.analysis).map(analysis => analysis.score);
        content.score = scores.reduce((sum, score) => sum + score, 0) / scores.length;
        
        return content;
    }

    async analyzeMobileOptimization($, pageContent) {
        const mobile = {
            score: 0,
            checks: {}
        };
        
        // Viewport meta tag
        const viewport = $('meta[name="viewport"]').attr('content');
        mobile.checks.viewport = {
            present: !!viewport,
            responsive: viewport?.includes('width=device-width'),
            score: viewport?.includes('width=device-width') ? 10 : 0
        };
        
        // Touch-friendly elements
        const buttons = $('button, input[type="button"], input[type="submit"], .button').length;
        const links = $('a').length;
        mobile.checks.touchElements = {
            buttons,
            links,
            score: (buttons + links) > 0 ? 8 : 5
        };
        
        // Font sizes
        const fontSizes = [];
        $('*').each((i, el) => {
            const fontSize = $(el).css('font-size');
            if (fontSize) {
                const size = parseInt(fontSize);
                if (!isNaN(size)) fontSizes.push(size);
            }
        });
        
        const minFontSize = Math.min(...fontSizes.filter(size => size > 0));
        mobile.checks.fonts = {
            minSize: minFontSize,
            readable: minFontSize >= 16,
            score: minFontSize >= 16 ? 10 : 5
        };
        
        // Calculate mobile score
        const scores = Object.values(mobile.checks).map(check => check.score);
        mobile.score = scores.reduce((sum, score) => sum + score, 0) / scores.length;
        
        return mobile;
    }

    async analyzeStructuredData($) {
        const structured = {
            score: 0,
            schemas: []
        };
        
        // JSON-LD structured data
        const jsonLdScripts = $('script[type="application/ld+json"]');
        jsonLdScripts.each((i, el) => {
            try {
                const data = JSON.parse($(el).html());
                structured.schemas.push({
                    type: 'json-ld',
                    schema: data['@type'] || 'Unknown',
                    valid: true
                });
            } catch (e) {
                structured.schemas.push({
                    type: 'json-ld',
                    schema: 'Invalid',
                    valid: false,
                    error: e.message
                });
            }
        });
        
        // Microdata
        const microdataItems = $('[itemscope]');
        microdataItems.each((i, el) => {
            const itemType = $(el).attr('itemtype') || 'Unknown';
            structured.schemas.push({
                type: 'microdata',
                schema: itemType.split('/').pop(),
                valid: true
            });
        });
        
        structured.score = structured.schemas.length > 0 ? Math.min(structured.schemas.length * 2, 10) : 0;
        
        return structured;
    }

    // Helper methods for scoring
    calculateSEOScore(analysis) {
        const weights = {
            technical: 0.25,
            onPage: 0.30,
            content: 0.25,
            mobile: 0.10,
            structured: 0.10
        };
        
        let weightedScore = 0;
        weightedScore += (analysis.technical?.score || 0) * weights.technical;
        weightedScore += (analysis.onPage?.score || 0) * weights.onPage;
        weightedScore += (analysis.content?.score || 0) * weights.content;
        weightedScore += (analysis.mobile?.score || 0) * weights.mobile;
        weightedScore += (analysis.structured?.score || 0) * weights.structured;
        
        return Math.round(weightedScore * 10) / 10;
    }

    calculateSpeedScore(loadTime) {
        if (loadTime < 1000) return 10;
        if (loadTime < 2000) return 8;
        if (loadTime < 3000) return 6;
        if (loadTime < 5000) return 4;
        return 2;
    }

    calculateTitleScore(title) {
        if (!title) return 0;
        if (title.length < 30) return 5;
        if (title.length > 60) return 6;
        return 10;
    }

    calculateDescriptionScore(description) {
        if (!description) return 0;
        if (description.length < 120) return 5;
        if (description.length > 160) return 6;
        return 10;
    }

    calculateWordCountScore(wordCount) {
        if (wordCount < 100) return 2;
        if (wordCount < 300) return 5;
        if (wordCount < 1000) return 8;
        return 10;
    }

    calculateFleschReadingEase(text) {
        // Simplified Flesch Reading Ease calculation
        const sentences = text.split(/[.!?]+/).length;
        const words = text.split(/\s+/).length;
        const syllables = this.countSyllables(text);
        
        if (sentences === 0 || words === 0) return 0;
        
        const score = 206.835 - (1.015 * (words / sentences)) - (84.6 * (syllables / words));
        return Math.max(0, Math.min(100, score));
    }

    countSyllables(text) {
        // Simplified syllable counting
        const words = text.toLowerCase().match(/\b\w+\b/g) || [];
        let syllableCount = 0;
        
        words.forEach(word => {
            const vowels = word.match(/[aeiouy]+/g) || [];
            let count = vowels.length;
            if (word.endsWith('e')) count--;
            if (count === 0) count = 1;
            syllableCount += count;
        });
        
        return syllableCount;
    }

    classifySearchIntent(keyword) {
        const intentPatterns = {
            informational: ['how', 'what', 'why', 'when', 'where', 'guide', 'tutorial', 'tips'],
            navigational: ['login', 'contact', 'about', 'home', 'company'],
            transactional: ['buy', 'purchase', 'order', 'shop', 'price', 'cost', 'cheap', 'deal'],
            commercial: ['best', 'review', 'compare', 'vs', 'top', 'recommended']
        };
        
        const lowerKeyword = keyword.toLowerCase();
        
        for (const [intent, patterns] of Object.entries(intentPatterns)) {
            if (patterns.some(pattern => lowerKeyword.includes(pattern))) {
                return intent;
            }
        }
        
        return 'informational'; // Default
    }

    async generateSEORecommendations(analysis) {
        const recommendations = [];
        
        // Technical recommendations
        if (analysis.technical?.score < 8) {
            analysis.technical.issues.forEach(issue => {
                recommendations.push({
                    category: 'technical',
                    priority: issue.severity === 'high' ? 'high' : 'medium',
                    title: `Fix ${issue.type} issue`,
                    description: issue.message,
                    impact: 'Technical SEO improvement'
                });
            });
        }
        
        // On-page recommendations
        if (analysis.onPage?.elements?.title?.score < 8) {
            recommendations.push({
                category: 'on-page',
                priority: 'high',
                title: 'Optimize title tag',
                description: analysis.onPage.elements.title.recommendation,
                impact: 'Improved click-through rates and rankings'
            });
        }
        
        if (analysis.onPage?.elements?.metaDescription?.score < 8) {
            recommendations.push({
                category: 'on-page',
                priority: 'medium',
                title: 'Optimize meta description',
                description: analysis.onPage.elements.metaDescription.recommendation,
                impact: 'Better SERP presentation and CTR'
            });
        }
        
        // Content recommendations
        if (analysis.content?.analysis?.wordCount?.score < 8) {
            recommendations.push({
                category: 'content',
                priority: 'medium',
                title: 'Improve content length',
                description: analysis.content.analysis.wordCount.recommendation,
                impact: 'Better content depth and keyword coverage'
            });
        }
        
        // Mobile recommendations
        if (analysis.mobile?.score < 8) {
            recommendations.push({
                category: 'mobile',
                priority: 'high',
                title: 'Improve mobile optimization',
                description: 'Optimize for mobile devices with responsive design',
                impact: 'Better mobile user experience and rankings'
            });
        }
        
        return recommendations.slice(0, 10); // Limit to top 10 recommendations
    }

    startRankingMonitor() {
        // Check rankings daily
        setInterval(async () => {
            try {
                await this.updateAllRankings();
            } catch (error) {
                this.logger.error('Ranking monitor error', { error: error.message });
            }
        }, 24 * 60 * 60 * 1000);
    }

    startAuditEngine() {
        // Run audits weekly
        setInterval(async () => {
            try {
                await this.runScheduledAudits();
            } catch (error) {
                this.logger.error('Audit engine error', { error: error.message });
            }
        }, 7 * 24 * 60 * 60 * 1000);
    }

    async getOverallStats() {
        const totalWebsites = this.websites.size;
        const totalKeywords = this.keywords.size;
        const totalAudits = this.audits.size;
        
        let averageTechnicalScore = 0;
        let averageContentScore = 0;
        let totalPages = 0;
        
        for (const website of this.websites.values()) {
            averageTechnicalScore += website.analytics.technicalScore;
            averageContentScore += website.analytics.contentScore;
            totalPages += website.analytics.totalPages;
        }
        
        return {
            totalWebsites,
            totalKeywords,
            totalAudits,
            totalPages,
            averageTechnicalScore: totalWebsites > 0 ? averageTechnicalScore / totalWebsites : 0,
            averageContentScore: totalWebsites > 0 ? averageContentScore / totalWebsites : 0
        };
    }

    // Event handlers
    handleWebsiteAdded(website) {
        this.logger.info('Website added to SEO monitoring', {
            websiteId: website.id,
            domain: website.domain
        });
    }

    handleAuditCompleted(audit) {
        this.logger.info('SEO audit completed', {
            auditId: audit.id,
            websiteId: audit.websiteId,
            score: audit.overallScore
        });
    }

    handleRankingChanged(data) {
        this.logger.info('Ranking position changed', {
            keyword: data.keyword,
            oldPosition: data.oldPosition,
            newPosition: data.newPosition
        });
    }

    handleOptimizationSuggestion(suggestion) {
        this.logger.info('SEO optimization suggestion generated', {
            type: suggestion.category,
            priority: suggestion.priority
        });
    }

    handleCompetitorAnalyzed(competitor) {
        this.logger.info('Competitor analysis completed', {
            competitorId: competitor.id,
            domain: competitor.domain
        });
    }

    // Data sanitization
    sanitizeWebsiteData(website) {
        return {
            ...website,
            // Remove sensitive data if needed
        };
    }

    sanitizeKeywordResearch(research) {
        return research;
    }
}

module.exports = SEOOptimizer;