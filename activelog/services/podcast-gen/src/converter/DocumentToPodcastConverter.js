import { EventEmitter } from 'events';
import fs from 'fs/promises';
import path from 'path';
import OpenAI from 'openai';
// import pdfParse from 'pdf-parse';
import mammoth from 'mammoth';
import { marked } from 'marked';
import * as cheerio from 'cheerio';
import compromise from 'compromise';
import natural from 'natural';
import Sentiment from 'sentiment';
import crypto from 'crypto';

class DocumentToPodcastConverter extends EventEmitter {
    constructor(config = {}) {
        super();
        this.conversions = new Map();
        this.templates = new Map();
        this.processingQueue = new Map();
        this.contentAnalyzer = new Map();
        this.scriptGenerator = new Map();

        this.openai = new OpenAI({
            apiKey: config.openai_api_key || process.env.OPENAI_API_KEY
        });

        this.initializeSystem();
    }

    initializeSystem() {
        this.initializeContentTemplates();
        this.initializeConversionRules();
        this.initializeAnalysisTools();
        
        this.emit('converter_initialized');
    }

    initializeContentTemplates() {
        const templates = [
            {
                id: 'technical_explainer',
                name: 'Technical Explainer',
                description: 'Convert technical documents into accessible explanations',
                style: 'educational',
                target_length: '15-25 minutes',
                voice_count: 2,
                roles: ['host', 'expert'],
                structure: {
                    intro: 'Brief overview and context setting',
                    main_content: 'Step-by-step explanation with examples',
                    recap: 'Summary and key takeaways',
                    outro: 'Call to action and next steps'
                },
                tone: 'informative_friendly',
                pacing: 'moderate'
            },
            {
                id: 'debate_format',
                name: 'Debate Format',
                description: 'Present multiple perspectives on a topic',
                style: 'debate',
                target_length: '20-30 minutes',
                voice_count: 3,
                roles: ['moderator', 'advocate', 'skeptic'],
                structure: {
                    intro: 'Topic introduction and participant introductions',
                    opening_statements: 'Initial positions from each side',
                    main_debate: 'Back-and-forth discussion with evidence',
                    closing_arguments: 'Final statements',
                    moderator_summary: 'Balanced conclusion'
                },
                tone: 'professional_engaging',
                pacing: 'dynamic'
            },
            {
                id: 'story_narrative',
                name: 'Story Narrative',
                description: 'Transform content into engaging storytelling format',
                style: 'narrative',
                target_length: '10-20 minutes',
                voice_count: 2,
                roles: ['narrator', 'character_voices'],
                structure: {
                    hook: 'Compelling opening that draws listeners in',
                    setup: 'Context and background information',
                    development: 'Main story with key points as plot points',
                    climax: 'Critical insights or revelations',
                    resolution: 'Conclusion and implications'
                },
                tone: 'engaging_dramatic',
                pacing: 'variable'
            },
            {
                id: 'interview_style',
                name: 'Interview Style',
                description: 'Present content as an expert interview',
                style: 'interview',
                target_length: '25-35 minutes',
                voice_count: 2,
                roles: ['interviewer', 'expert'],
                structure: {
                    intro: 'Guest introduction and topic overview',
                    background: 'Expert credentials and context',
                    deep_dive: 'Detailed Q&A on main topics',
                    practical_insights: 'Real-world applications',
                    wrap_up: 'Final thoughts and contact information'
                },
                tone: 'conversational_professional',
                pacing: 'natural'
            },
            {
                id: 'roast_comedy',
                name: 'Comedy Roast',
                description: 'Humorous take on serious topics',
                style: 'comedy',
                target_length: '15-25 minutes',
                voice_count: 3,
                roles: ['host', 'comedian_1', 'comedian_2'],
                structure: {
                    intro: 'Topic introduction with comedic setup',
                    roast_segments: 'Humorous commentary on key points',
                    fact_checking: 'Serious moments with actual information',
                    callback_jokes: 'References to earlier jokes',
                    outro: 'Wrap-up with final punchlines'
                },
                tone: 'humorous_irreverent',
                pacing: 'fast'
            },
            {
                id: 'news_report',
                name: 'News Report',
                description: 'Present information in news format',
                style: 'news',
                target_length: '8-15 minutes',
                voice_count: 2,
                roles: ['anchor', 'field_reporter'],
                structure: {
                    headline: 'Breaking news style opening',
                    overview: 'Key facts and timeline',
                    analysis: 'Expert commentary and implications',
                    related_stories: 'Connected topics and context',
                    outro: 'Summary and what to watch for next'
                },
                tone: 'authoritative_urgent',
                pacing: 'brisk'
            }
        ];

        templates.forEach(template => {
            this.templates.set(template.id, template);
        });
    }

    initializeConversionRules() {
        this.conversionRules = {
            document_types: {
                'pdf': { parser: 'pdf-parse', preprocessing: 'text_extraction' },
                'docx': { parser: 'mammoth', preprocessing: 'html_to_text' },
                'md': { parser: 'marked', preprocessing: 'markdown_to_html' },
                'txt': { parser: 'raw_text', preprocessing: 'direct' },
                'html': { parser: 'cheerio', preprocessing: 'html_parsing' },
                'json': { parser: 'json_parse', preprocessing: 'structured_data' }
            },
            content_analysis: {
                min_word_count: 500,
                max_word_count: 50000,
                complexity_scoring: true,
                topic_extraction: true,
                sentiment_analysis: true,
                readability_assessment: true
            },
            script_generation: {
                min_segment_length: 30,
                max_segment_length: 300,
                natural_breaks: true,
                voice_assignment: 'automatic',
                pacing_marks: true,
                emphasis_detection: true
            }
        };
    }

    initializeAnalysisTools() {
        this.stemmer = natural.PorterStemmer;
        this.tokenizer = new natural.WordTokenizer();
        this.sentiment = new Sentiment();
    }

    // Main conversion method
    async convertDocument(conversionRequest) {
        try {
            const conversionId = crypto.randomBytes(16).toString('hex');
            
            const conversion = {
                id: conversionId,
                status: 'initializing',
                document_path: conversionRequest.document_path,
                document_type: this.detectDocumentType(conversionRequest.document_path),
                template_id: conversionRequest.template_id || 'technical_explainer',
                target_length: conversionRequest.target_length || 'auto',
                voice_preferences: conversionRequest.voice_preferences || {},
                style_options: conversionRequest.style_options || {},
                created_at: new Date(),
                processing_steps: [],
                result: null
            };

            this.conversions.set(conversionId, conversion);
            this.emit('conversion_started', { conversion_id: conversionId });

            // Process the conversion
            const result = await this.processConversion(conversionId);
            
            return {
                success: true,
                conversion_id: conversionId,
                result: result
            };

        } catch (error) {
            this.emit('conversion_error', { conversionRequest, error });
            return { success: false, error: error.message };
        }
    }

    async processConversion(conversionId) {
        const conversion = this.conversions.get(conversionId);
        if (!conversion) {
            throw new Error('Conversion not found');
        }

        try {
            // Step 1: Extract content from document
            conversion.status = 'extracting_content';
            this.updateConversion(conversionId, conversion);
            
            const rawContent = await this.extractContent(conversion.document_path, conversion.document_type);
            conversion.processing_steps.push({ step: 'content_extraction', completed: true, data: { length: rawContent.length } });

            // Step 2: Analyze content
            conversion.status = 'analyzing_content';
            this.updateConversion(conversionId, conversion);
            
            const contentAnalysis = await this.analyzeContent(rawContent);
            conversion.processing_steps.push({ step: 'content_analysis', completed: true, data: contentAnalysis.summary });

            // Step 3: Generate script structure
            conversion.status = 'generating_structure';
            this.updateConversion(conversionId, conversion);
            
            const scriptStructure = await this.generateScriptStructure(rawContent, contentAnalysis, conversion.template_id);
            conversion.processing_steps.push({ step: 'structure_generation', completed: true, data: { segments: scriptStructure.segments.length } });

            // Step 4: Generate dialogue
            conversion.status = 'generating_dialogue';
            this.updateConversion(conversionId, conversion);
            
            const dialogue = await this.generateDialogue(scriptStructure, conversion.template_id, conversion.style_options);
            conversion.processing_steps.push({ step: 'dialogue_generation', completed: true, data: { total_words: dialogue.total_words } });

            // Step 5: Finalize script
            conversion.status = 'finalizing_script';
            this.updateConversion(conversionId, conversion);
            
            const finalScript = await this.finalizeScript(dialogue, conversion);
            conversion.processing_steps.push({ step: 'script_finalization', completed: true });

            // Complete conversion
            conversion.status = 'completed';
            conversion.completed_at = new Date();
            conversion.result = finalScript;
            
            this.updateConversion(conversionId, conversion);
            this.emit('conversion_completed', { conversion_id: conversionId, result: finalScript });

            return finalScript;

        } catch (error) {
            conversion.status = 'failed';
            conversion.error = error.message;
            this.updateConversion(conversionId, conversion);
            throw error;
        }
    }

    detectDocumentType(filePath) {
        const extension = path.extname(filePath).toLowerCase().substring(1);
        return extension || 'txt';
    }

    async extractContent(documentPath, documentType) {
        try {
            const fileBuffer = await fs.readFile(documentPath);
            
            switch (documentType) {
                case 'pdf':
                    return await this.extractFromPDF(fileBuffer);
                case 'docx':
                    return await this.extractFromDocx(fileBuffer);
                case 'md':
                    return await this.extractFromMarkdown(fileBuffer.toString());
                case 'html':
                    return await this.extractFromHTML(fileBuffer.toString());
                case 'txt':
                    return fileBuffer.toString('utf-8');
                case 'json':
                    return await this.extractFromJSON(fileBuffer.toString());
                default:
                    throw new Error(`Unsupported document type: ${documentType}`);
            }
        } catch (error) {
            throw new Error(`Content extraction failed: ${error.message}`);
        }
    }

    async extractFromPDF(buffer) {
        throw new Error('PDF parsing temporarily disabled - install working pdf parser');
        // try {
        //     const data = await pdfParse(buffer);
        //     return this.cleanText(data.text);
        // } catch (error) {
        //     throw new Error(`PDF parsing failed: ${error.message}`);
        // }
    }

    async extractFromDocx(buffer) {
        try {
            const result = await mammoth.extractRawText({ buffer });
            return this.cleanText(result.value);
        } catch (error) {
            throw new Error(`DOCX parsing failed: ${error.message}`);
        }
    }

    async extractFromMarkdown(text) {
        try {
            const html = marked(text);
            const $ = cheerio.load(html);
            const plainText = $.text();
            return this.cleanText(plainText);
        } catch (error) {
            throw new Error(`Markdown parsing failed: ${error.message}`);
        }
    }

    async extractFromHTML(html) {
        try {
            const $ = cheerio.load(html);
            
            // Remove script and style tags
            $('script, style').remove();
            
            // Extract main content (try common content selectors)
            const contentSelectors = ['main', 'article', '.content', '#content', 'body'];
            let content = '';
            
            for (const selector of contentSelectors) {
                const element = $(selector);
                if (element.length > 0 && element.text().trim().length > content.length) {
                    content = element.text();
                }
            }
            
            return this.cleanText(content || $('body').text());
        } catch (error) {
            throw new Error(`HTML parsing failed: ${error.message}`);
        }
    }

    async extractFromJSON(jsonString) {
        try {
            const data = JSON.parse(jsonString);
            
            // Try to extract meaningful text from various JSON structures
            let text = '';
            
            if (typeof data === 'string') {
                text = data;
            } else if (data.content) {
                text = data.content;
            } else if (data.text) {
                text = data.text;
            } else if (data.body) {
                text = data.body;
            } else if (Array.isArray(data)) {
                text = data.map(item => 
                    typeof item === 'string' ? item : 
                    item.content || item.text || item.body || JSON.stringify(item)
                ).join('\n\n');
            } else {
                // Flatten object to text
                text = this.flattenObjectToText(data);
            }
            
            return this.cleanText(text);
        } catch (error) {
            throw new Error(`JSON parsing failed: ${error.message}`);
        }
    }

    flattenObjectToText(obj, depth = 0) {
        if (depth > 3) return ''; // Prevent infinite recursion
        
        let text = '';
        for (const [key, value] of Object.entries(obj)) {
            if (typeof value === 'string') {
                text += `${key}: ${value}\n`;
            } else if (typeof value === 'object' && value !== null) {
                if (Array.isArray(value)) {
                    text += `${key}: ${value.join(', ')}\n`;
                } else {
                    text += `${key}:\n${this.flattenObjectToText(value, depth + 1)}`;
                }
            }
        }
        return text;
    }

    cleanText(text) {
        return text
            .replace(/\r\n/g, '\n')
            .replace(/\r/g, '\n')
            .replace(/\n{3,}/g, '\n\n')
            .replace(/\s{2,}/g, ' ')
            .trim();
    }

    async analyzeContent(content) {
        try {
            const words = this.tokenizer.tokenize(content);
            const sentences = content.split(/[.!?]+/).filter(s => s.trim().length > 0);
            
            // Basic metrics
            const analysis = {
                word_count: words.length,
                sentence_count: sentences.length,
                avg_sentence_length: words.length / sentences.length,
                estimated_reading_time: Math.ceil(words.length / 200), // minutes
                estimated_listening_time: Math.ceil(words.length / 150), // minutes (slower for listening)
            };

            // Complexity analysis
            analysis.complexity = this.analyzeComplexity(content, words, sentences);

            // Topic extraction
            analysis.topics = await this.extractTopics(content);

            // Sentiment analysis
            analysis.sentiment = this.analyzeSentiment(content);

            // Structure analysis
            analysis.structure = this.analyzeStructure(content);

            // Content type detection
            analysis.content_type = this.detectContentType(content);

            // Key points extraction
            analysis.key_points = await this.extractKeyPoints(content);

            return {
                success: true,
                analysis: analysis,
                summary: {
                    words: analysis.word_count,
                    complexity: analysis.complexity.level,
                    main_topics: analysis.topics.slice(0, 3),
                    content_type: analysis.content_type
                }
            };

        } catch (error) {
            throw new Error(`Content analysis failed: ${error.message}`);
        }
    }

    analyzeComplexity(content, words, sentences) {
        // Flesch Reading Ease Score
        const avgSentenceLength = words.length / sentences.length;
        const avgSyllables = this.estimateAverageSyllables(words);
        
        const fleschScore = 206.835 - (1.015 * avgSentenceLength) - (84.6 * avgSyllables);
        
        let level;
        if (fleschScore >= 90) level = 'very_easy';
        else if (fleschScore >= 80) level = 'easy';
        else if (fleschScore >= 70) level = 'fairly_easy';
        else if (fleschScore >= 60) level = 'standard';
        else if (fleschScore >= 50) level = 'fairly_difficult';
        else if (fleschScore >= 30) level = 'difficult';
        else level = 'very_difficult';

        return {
            flesch_score: Math.round(fleschScore),
            level: level,
            avg_sentence_length: Math.round(avgSentenceLength),
            avg_syllables: avgSyllables.toFixed(2)
        };
    }

    estimateAverageSyllables(words) {
        const syllableCounts = words.map(word => this.countSyllables(word));
        return syllableCounts.reduce((sum, count) => sum + count, 0) / words.length;
    }

    countSyllables(word) {
        word = word.toLowerCase();
        if (word.length <= 3) return 1;
        
        let count = 0;
        const vowels = 'aeiouy';
        let previousWasVowel = false;
        
        for (let i = 0; i < word.length; i++) {
            const isVowel = vowels.includes(word[i]);
            if (isVowel && !previousWasVowel) {
                count++;
            }
            previousWasVowel = isVowel;
        }
        
        // Handle silent 'e'
        if (word.endsWith('e')) {
            count--;
        }
        
        return Math.max(1, count);
    }

    async extractTopics(content) {
        try {
            // Use NLP to extract key topics
            const doc = compromise(content);
            
            // Extract nouns and noun phrases
            const nouns = doc.nouns().out('array');
            const topics = doc.topics().out('array');
            const places = doc.places().out('array');
            const people = doc.people().out('array');
            
            // Combine and rank topics
            const allTopics = [...nouns, ...topics, ...places, ...people];
            const topicCounts = {};
            
            allTopics.forEach(topic => {
                const normalized = topic.toLowerCase();
                topicCounts[normalized] = (topicCounts[normalized] || 0) + 1;
            });
            
            return Object.entries(topicCounts)
                .filter(([topic, count]) => count > 1 && topic.length > 2)
                .sort(([,a], [,b]) => b - a)
                .slice(0, 10)
                .map(([topic]) => topic);

        } catch (error) {
            // Fallback to simple keyword extraction
            return this.simpleTopicExtraction(content);
        }
    }

    simpleTopicExtraction(content) {
        const words = this.tokenizer.tokenize(content.toLowerCase());
        const stopWords = new Set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']);
        
        const wordCounts = {};
        words.forEach(word => {
            if (!stopWords.has(word) && word.length > 3) {
                wordCounts[word] = (wordCounts[word] || 0) + 1;
            }
        });
        
        return Object.entries(wordCounts)
            .filter(([word, count]) => count > 2)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 10)
            .map(([word]) => word);
    }

    analyzeSentiment(content) {
        // Simple sentiment analysis
        const positiveWords = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'awesome', 'brilliant', 'outstanding'];
        const negativeWords = ['bad', 'terrible', 'awful', 'horrible', 'disgusting', 'hate', 'worst', 'pathetic', 'useless'];
        
        const words = this.tokenizer.tokenize(content.toLowerCase());
        
        let positive = 0;
        let negative = 0;
        
        words.forEach(word => {
            if (positiveWords.includes(word)) positive++;
            if (negativeWords.includes(word)) negative++;
        });
        
        const total = positive + negative;
        if (total === 0) return { score: 0, label: 'neutral' };
        
        const score = (positive - negative) / total;
        let label;
        if (score > 0.1) label = 'positive';
        else if (score < -0.1) label = 'negative';
        else label = 'neutral';
        
        return { score: score.toFixed(2), label, positive, negative };
    }

    analyzeStructure(content) {
        const lines = content.split('\n').filter(line => line.trim().length > 0);
        const headings = lines.filter(line => {
            const trimmed = line.trim();
            return trimmed.length < 100 && 
                   (trimmed.match(/^#{1,6}\s/) || // Markdown headers
                    trimmed.match(/^\d+\./) || // Numbered sections
                    trimmed.match(/^[A-Z][A-Z\s]{2,}$/) || // All caps headers
                    trimmed.endsWith(':') && trimmed.length < 50); // Section headers
        });

        const paragraphs = content.split(/\n\s*\n/).filter(p => p.trim().length > 50);
        
        return {
            total_lines: lines.length,
            headings_detected: headings.length,
            paragraphs: paragraphs.length,
            avg_paragraph_length: paragraphs.length > 0 ? 
                paragraphs.reduce((sum, p) => sum + p.length, 0) / paragraphs.length : 0,
            has_clear_structure: headings.length > 2
        };
    }

    detectContentType(content) {
        const indicators = {
            academic: ['abstract', 'methodology', 'conclusion', 'references', 'hypothesis', 'research'],
            technical: ['function', 'algorithm', 'implementation', 'code', 'system', 'technical'],
            business: ['strategy', 'market', 'revenue', 'customers', 'business', 'growth'],
            tutorial: ['step', 'how to', 'guide', 'instructions', 'tutorial', 'learn'],
            news: ['reported', 'sources', 'breaking', 'update', 'news', 'journalist'],
            opinion: ['opinion', 'believe', 'think', 'perspective', 'view', 'argue']
        };

        const contentLower = content.toLowerCase();
        const scores = {};

        Object.entries(indicators).forEach(([type, words]) => {
            scores[type] = words.reduce((score, word) => {
                const matches = (contentLower.match(new RegExp(word, 'g')) || []).length;
                return score + matches;
            }, 0);
        });

        const maxScore = Math.max(...Object.values(scores));
        const detectedType = Object.entries(scores).find(([, score]) => score === maxScore)?.[0];

        return detectedType || 'general';
    }

    async extractKeyPoints(content) {
        try {
            const sentences = content.split(/[.!?]+/).filter(s => s.trim().length > 20);
            
            // Score sentences based on various factors
            const scoredSentences = sentences.map(sentence => {
                let score = 0;
                const words = this.tokenizer.tokenize(sentence.toLowerCase());
                
                // Length factor (moderate length preferred)
                const wordCount = words.length;
                if (wordCount >= 10 && wordCount <= 25) score += 2;
                else if (wordCount >= 6 && wordCount <= 30) score += 1;
                
                // Position factor (beginning and end more important)
                const position = sentences.indexOf(sentence);
                if (position < 3 || position > sentences.length - 4) score += 1;
                
                // Keyword density
                const importantWords = ['important', 'key', 'main', 'primary', 'essential', 'critical', 'significant'];
                importantWords.forEach(word => {
                    if (sentence.toLowerCase().includes(word)) score += 2;
                });
                
                // Numbers and data
                if (sentence.match(/\d+/)) score += 1;
                
                return { sentence: sentence.trim(), score };
            });

            return scoredSentences
                .filter(item => item.score > 0)
                .sort((a, b) => b.score - a.score)
                .slice(0, 8)
                .map(item => item.sentence);

        } catch (error) {
            return [];
        }
    }

    async generateScriptStructure(content, analysis, templateId) {
        try {
            const template = this.templates.get(templateId);
            if (!template) {
                throw new Error(`Template not found: ${templateId}`);
            }

            // Calculate target segments based on content length and template
            const targetMinutes = this.parseTargetLength(template.target_length);
            const wordsPerMinute = 150; // Average speaking pace
            const targetWords = targetMinutes * wordsPerMinute;
            
            // Adjust based on content complexity
            const complexityMultiplier = this.getComplexityMultiplier(analysis.analysis.complexity.level);
            const adjustedTargetWords = Math.round(targetWords * complexityMultiplier);

            // Create structure based on template
            const structure = {
                template_id: templateId,
                template_name: template.name,
                target_length_minutes: targetMinutes,
                target_words: adjustedTargetWords,
                voice_count: template.voice_count,
                roles: template.roles,
                tone: template.tone,
                pacing: template.pacing,
                segments: []
            };

            // Generate segments based on template structure
            const segmentSpecs = Object.entries(template.structure);
            const contentChunks = this.chunkContent(content, analysis, segmentSpecs.length);

            for (let i = 0; i < segmentSpecs.length; i++) {
                const [segmentName, segmentDescription] = segmentSpecs[i];
                const chunk = contentChunks[i] || '';
                
                const segment = {
                    id: crypto.randomBytes(8).toString('hex'),
                    name: segmentName,
                    description: segmentDescription,
                    content_source: chunk,
                    estimated_duration: Math.round((adjustedTargetWords / segmentSpecs.length) / wordsPerMinute),
                    voice_assignments: this.assignVoicesToSegment(template.roles, segmentName, template.style),
                    key_points: this.extractSegmentKeyPoints(chunk, analysis.analysis.key_points),
                    tone_markers: this.generateToneMarkers(segmentName, template.tone),
                    pacing_notes: this.generatePacingNotes(template.pacing, segmentName)
                };

                structure.segments.push(segment);
            }

            return structure;

        } catch (error) {
            throw new Error(`Script structure generation failed: ${error.message}`);
        }
    }

    parseTargetLength(lengthString) {
        if (typeof lengthString === 'number') return lengthString;
        
        // Parse strings like "15-25 minutes" or "20 minutes"
        const match = lengthString.match(/(\d+)(?:-(\d+))?\s*minutes?/);
        if (match) {
            const min = parseInt(match[1]);
            const max = match[2] ? parseInt(match[2]) : min;
            return Math.round((min + max) / 2);
        }
        
        return 20; // Default fallback
    }

    getComplexityMultiplier(complexityLevel) {
        const multipliers = {
            'very_easy': 0.8,
            'easy': 0.9,
            'fairly_easy': 0.95,
            'standard': 1.0,
            'fairly_difficult': 1.1,
            'difficult': 1.25,
            'very_difficult': 1.4
        };
        
        return multipliers[complexityLevel] || 1.0;
    }

    chunkContent(content, analysis, numChunks) {
        const sentences = content.split(/[.!?]+/).filter(s => s.trim().length > 10);
        const sentencesPerChunk = Math.ceil(sentences.length / numChunks);
        
        const chunks = [];
        for (let i = 0; i < numChunks; i++) {
            const start = i * sentencesPerChunk;
            const end = Math.min(start + sentencesPerChunk, sentences.length);
            const chunk = sentences.slice(start, end).join('. ').trim();
            if (chunk) {
                chunks.push(chunk + (chunk.endsWith('.') ? '' : '.'));
            }
        }
        
        // Fill any missing chunks with key points
        while (chunks.length < numChunks) {
            const keyPointIndex = chunks.length - 1;
            const keyPoint = analysis.analysis.key_points[keyPointIndex] || 'Additional discussion points.';
            chunks.push(keyPoint);
        }
        
        return chunks;
    }

    assignVoicesToSegment(roles, segmentName, style) {
        const assignments = {};
        
        switch (style) {
            case 'debate':
                if (segmentName.includes('intro') || segmentName.includes('summary')) {
                    assignments.primary = 'moderator';
                } else if (segmentName.includes('opening') || segmentName.includes('closing')) {
                    assignments.primary = 'advocate';
                    assignments.secondary = 'skeptic';
                } else {
                    assignments.primary = 'advocate';
                    assignments.secondary = 'skeptic';
                    assignments.moderator = 'moderator';
                }
                break;
                
            case 'interview':
                assignments.primary = 'interviewer';
                assignments.secondary = 'expert';
                break;
                
            case 'comedy':
                if (segmentName.includes('intro') || segmentName.includes('outro')) {
                    assignments.primary = 'host';
                } else {
                    assignments.primary = 'comedian_1';
                    assignments.secondary = 'comedian_2';
                    assignments.moderator = 'host';
                }
                break;
                
            default:
                assignments.primary = roles[0];
                if (roles.length > 1) assignments.secondary = roles[1];
        }
        
        return assignments;
    }

    extractSegmentKeyPoints(chunk, globalKeyPoints) {
        if (!chunk || chunk.length < 50) return [];
        
        // Find key points that appear in this chunk
        const chunkLower = chunk.toLowerCase();
        const relevantPoints = globalKeyPoints.filter(point => {
            const pointWords = this.tokenizer.tokenize(point.toLowerCase());
            return pointWords.some(word => chunkLower.includes(word));
        });
        
        // If no relevant points found, extract from chunk directly
        if (relevantPoints.length === 0) {
            const sentences = chunk.split(/[.!?]+/).filter(s => s.trim().length > 20);
            return sentences.slice(0, 2);
        }
        
        return relevantPoints.slice(0, 3);
    }

    generateToneMarkers(segmentName, templateTone) {
        const markers = [];
        
        // Base tone from template
        markers.push(templateTone);
        
        // Segment-specific adjustments
        if (segmentName.includes('intro')) {
            markers.push('welcoming', 'engaging');
        } else if (segmentName.includes('outro') || segmentName.includes('conclusion')) {
            markers.push('summarizing', 'conclusive');
        } else if (segmentName.includes('debate') || segmentName.includes('argument')) {
            markers.push('assertive', 'analytical');
        } else if (segmentName.includes('explanation') || segmentName.includes('technical')) {
            markers.push('educational', 'clear');
        } else if (segmentName.includes('story') || segmentName.includes('narrative')) {
            markers.push('storytelling', 'engaging');
        }
        
        return [...new Set(markers)]; // Remove duplicates
    }

    generatePacingNotes(templatePacing, segmentName) {
        const notes = [];
        
        // Base pacing
        notes.push(`Overall pacing: ${templatePacing}`);
        
        // Segment-specific pacing
        if (segmentName.includes('intro')) {
            notes.push('Start energetic to hook listeners');
        } else if (segmentName.includes('technical') || segmentName.includes('complex')) {
            notes.push('Slow down for complex information');
        } else if (segmentName.includes('debate') || segmentName.includes('argument')) {
            notes.push('Dynamic pacing with natural back-and-forth');
        } else if (segmentName.includes('conclusion') || segmentName.includes('summary')) {
            notes.push('Moderate pace for clarity and emphasis');
        } else if (segmentName.includes('comedy') || segmentName.includes('roast')) {
            notes.push('Quick pacing for comedic effect');
        }
        
        return notes;
    }

    async generateDialogue(scriptStructure, templateId, styleOptions = {}) {
        try {
            const template = this.templates.get(templateId);
            const dialogue = {
                script_id: crypto.randomBytes(16).toString('hex'),
                template_id: templateId,
                template_name: template.name,
                generated_at: new Date(),
                total_estimated_duration: 0,
                total_words: 0,
                segments: []
            };

            for (const segment of scriptStructure.segments) {
                const segmentDialogue = await this.generateSegmentDialogue(segment, template, styleOptions);
                dialogue.segments.push(segmentDialogue);
                dialogue.total_estimated_duration += segmentDialogue.estimated_duration;
                dialogue.total_words += segmentDialogue.word_count;
            }

            return dialogue;

        } catch (error) {
            throw new Error(`Dialogue generation failed: ${error.message}`);
        }
    }

    async generateSegmentDialogue(segment, template, styleOptions) {
        try {
            const prompt = this.buildDialoguePrompt(segment, template, styleOptions);
            
            const completion = await this.openai.chat.completions.create({
                model: "gpt-4",
                messages: [{ role: "user", content: prompt }],
                temperature: 0.7,
                max_tokens: 2000
            });

            const rawDialogue = completion.choices[0].message.content;
            const processedDialogue = this.processRawDialogue(rawDialogue, segment.voice_assignments);

            return {
                segment_id: segment.id,
                segment_name: segment.name,
                dialogue: processedDialogue,
                word_count: this.countWords(rawDialogue),
                estimated_duration: Math.ceil(this.countWords(rawDialogue) / 150), // minutes
                voice_count: Object.keys(processedDialogue).length,
                tone_achieved: segment.tone_markers,
                pacing_notes: segment.pacing_notes
            };

        } catch (error) {
            throw new Error(`Segment dialogue generation failed: ${error.message}`);
        }
    }

    buildDialoguePrompt(segment, template, styleOptions) {
        const voiceRoles = Object.values(segment.voice_assignments);
        const uniqueRoles = [...new Set(voiceRoles)];

        return `Create engaging podcast dialogue for the "${segment.name}" segment.

Template: ${template.name} (${template.style})
Segment Description: ${segment.description}

Content to Cover:
${segment.content_source}

Key Points to Include:
${segment.key_points.join('\n')}

Characters/Voices:
${uniqueRoles.map(role => `- ${role}: ${this.getRoleDescription(role, template.style)}`).join('\n')}

Tone: ${segment.tone_markers.join(', ')}
Pacing: ${segment.pacing_notes.join('; ')}

Style Guidelines:
- Make it sound natural and conversational
- ${template.style === 'debate' ? 'Include disagreement and counterpoints' : ''}
- ${template.style === 'comedy' ? 'Include humor and comedic timing' : ''}
- ${template.style === 'interview' ? 'Include thoughtful questions and responses' : ''}
- ${template.style === 'educational' ? 'Explain complex concepts clearly' : ''}
- Use appropriate transitions and natural speech patterns
- Include [pause], [emphasis], [excited], [thoughtful] markers for voice direction
- Target approximately ${segment.estimated_duration} minutes of content

Format as:
[VOICE_NAME]: Dialogue text with [direction] markers
[OTHER_VOICE]: Response text

Generate natural, engaging dialogue that covers the content effectively.`;
    }

    getRoleDescription(role, style) {
        const descriptions = {
            host: 'Main presenter who guides the conversation',
            expert: 'Knowledgeable specialist providing insights',
            interviewer: 'Asks thoughtful questions to draw out information',
            moderator: 'Facilitates discussion and keeps things balanced',
            advocate: 'Argues in favor of ideas or positions',
            skeptic: 'Questions and challenges presented information',
            narrator: 'Tells the story and provides context',
            comedian_1: 'Primary comedic voice with quick wit',
            comedian_2: 'Secondary comedic voice, plays off the first',
            anchor: 'Professional news presenter style',
            field_reporter: 'On-location reporting style',
            character_voices: 'Various character voices for storytelling'
        };

        return descriptions[role] || 'Conversational participant';
    }

    processRawDialogue(rawDialogue, voiceAssignments) {
        const lines = rawDialogue.split('\n').filter(line => line.trim());
        const processedDialogue = {};
        
        let currentSpeaker = null;
        
        lines.forEach(line => {
            const speakerMatch = line.match(/^\[([^\]]+)\]:\s*(.+)$/);
            
            if (speakerMatch) {
                const [, speaker, dialogue] = speakerMatch;
                currentSpeaker = speaker.trim();
                
                if (!processedDialogue[currentSpeaker]) {
                    processedDialogue[currentSpeaker] = [];
                }
                
                processedDialogue[currentSpeaker].push({
                    text: dialogue.trim(),
                    markers: this.extractVoiceMarkers(dialogue),
                    timestamp: null // Will be set during audio generation
                });
            } else if (currentSpeaker && line.trim()) {
                // Continuation of previous speaker
                const lastEntry = processedDialogue[currentSpeaker].slice(-1)[0];
                if (lastEntry) {
                    lastEntry.text += ' ' + line.trim();
                }
            }
        });

        return processedDialogue;
    }

    extractVoiceMarkers(dialogue) {
        const markerRegex = /\[([^\]]+)\]/g;
        const markers = [];
        let match;
        
        while ((match = markerRegex.exec(dialogue)) !== null) {
            markers.push(match[1].toLowerCase());
        }
        
        return markers;
    }

    countWords(text) {
        return this.tokenizer.tokenize(text).length;
    }

    async finalizeScript(dialogue, conversion) {
        try {
            const finalScript = {
                conversion_id: conversion.id,
                script_id: dialogue.script_id,
                metadata: {
                    title: this.generateTitle(conversion),
                    description: this.generateDescription(dialogue, conversion),
                    estimated_duration: dialogue.total_estimated_duration,
                    word_count: dialogue.total_words,
                    voice_count: this.countUniqueVoices(dialogue),
                    template_used: dialogue.template_name,
                    created_at: dialogue.generated_at,
                    language: 'en', // TODO: Detect language
                    tags: this.generateTags(conversion)
                },
                structure: {
                    segments: dialogue.segments.map(segment => ({
                        id: segment.segment_id,
                        name: segment.segment_name,
                        duration: segment.estimated_duration,
                        word_count: segment.word_count,
                        voice_count: segment.voice_count
                    }))
                },
                dialogue: dialogue.segments,
                production_notes: {
                    voice_assignments: this.compileFinalVoiceAssignments(dialogue),
                    pacing_guidelines: this.compilePacingGuidelines(dialogue),
                    tone_directions: this.compileToneDirections(dialogue),
                    technical_notes: this.generateTechnicalNotes(dialogue)
                },
                next_steps: [
                    'Review and edit dialogue if needed',
                    'Generate audio with voice synthesis',
                    'Add background music and effects',
                    'Create final podcast episode'
                ]
            };

            return finalScript;

        } catch (error) {
            throw new Error(`Script finalization failed: ${error.message}`);
        }
    }

    generateTitle(conversion) {
        const template = this.templates.get(conversion.template_id);
        const docName = path.basename(conversion.document_path, path.extname(conversion.document_path));
        
        const titleTemplates = {
            'technical_explainer': `Understanding ${docName}: A Technical Deep Dive`,
            'debate_format': `The Great ${docName} Debate`,
            'story_narrative': `The Story of ${docName}`,
            'interview_style': `Expert Interview: ${docName}`,
            'roast_comedy': `Roasting ${docName}: A Comedy Podcast`,
            'news_report': `Breaking: ${docName} Report`
        };

        return titleTemplates[conversion.template_id] || `Podcast: ${docName}`;
    }

    generateDescription(dialogue, conversion) {
        const template = this.templates.get(conversion.template_id);
        const duration = Math.round(dialogue.total_estimated_duration);
        
        return `A ${duration}-minute ${template.style} podcast exploring the key topics and insights from the source document. ` +
               `Generated using ActiveLog's AI podcast engine in ${template.name} format.`;
    }

    countUniqueVoices(dialogue) {
        const allVoices = new Set();
        dialogue.segments.forEach(segment => {
            Object.keys(segment.dialogue).forEach(voice => allVoices.add(voice));
        });
        return allVoices.size;
    }

    generateTags(conversion) {
        const template = this.templates.get(conversion.template_id);
        const baseTags = ['ai-generated', 'podcast', template.style];
        
        const docType = conversion.document_type;
        baseTags.push(`from-${docType}`);
        
        return baseTags;
    }

    compileFinalVoiceAssignments(dialogue) {
        const assignments = {};
        
        dialogue.segments.forEach(segment => {
            Object.keys(segment.dialogue).forEach(voice => {
                if (!assignments[voice]) {
                    assignments[voice] = {
                        role: voice,
                        characteristics: this.getVoiceCharacteristics(voice),
                        total_lines: 0
                    };
                }
                assignments[voice].total_lines += segment.dialogue[voice].length;
            });
        });

        return assignments;
    }

    getVoiceCharacteristics(voice) {
        const characteristics = {
            host: { tone: 'warm and professional', pace: 'moderate', style: 'engaging' },
            expert: { tone: 'authoritative and knowledgeable', pace: 'measured', style: 'educational' },
            interviewer: { tone: 'curious and respectful', pace: 'conversational', style: 'inquisitive' },
            moderator: { tone: 'neutral and balanced', pace: 'steady', style: 'facilitative' },
            advocate: { tone: 'passionate and convincing', pace: 'dynamic', style: 'persuasive' },
            skeptic: { tone: 'questioning and analytical', pace: 'thoughtful', style: 'challenging' },
            narrator: { tone: 'storytelling and descriptive', pace: 'rhythmic', style: 'narrative' },
            comedian_1: { tone: 'humorous and quick', pace: 'fast and punchy', style: 'comedic' },
            comedian_2: { tone: 'witty and supportive', pace: 'responsive', style: 'comedic' }
        };

        return characteristics[voice.toLowerCase()] || { tone: 'conversational', pace: 'moderate', style: 'natural' };
    }

    compilePacingGuidelines(dialogue) {
        const guidelines = [];
        
        dialogue.segments.forEach(segment => {
            guidelines.push(`${segment.segment_name}: ${segment.pacing_notes.join('; ')}`);
        });

        return guidelines;
    }

    compileToneDirections(dialogue) {
        const directions = [];
        
        dialogue.segments.forEach(segment => {
            directions.push(`${segment.segment_name}: ${segment.tone_achieved.join(', ')}`);
        });

        return directions;
    }

    generateTechnicalNotes(dialogue) {
        return [
            'Use natural speech synthesis with appropriate pauses',
            'Apply EQ and compression for broadcast quality',
            'Add subtle background music during appropriate segments',
            'Include brief pauses between speakers for clarity',
            'Apply noise gate to remove background artifacts',
            'Master to -16 LUFS for podcast distribution standards'
        ];
    }

    updateConversion(conversionId, conversion) {
        this.conversions.set(conversionId, conversion);
        this.emit('conversion_progress', {
            conversion_id: conversionId,
            status: conversion.status,
            progress: this.calculateProgress(conversion)
        });
    }

    calculateProgress(conversion) {
        const totalSteps = 5; // extraction, analysis, structure, dialogue, finalization
        return Math.round((conversion.processing_steps.filter(step => step.completed).length / totalSteps) * 100);
    }

    // Utility methods
    getConversionStatus(conversionId) {
        const conversion = this.conversions.get(conversionId);
        if (!conversion) {
            return { success: false, error: 'Conversion not found' };
        }

        return {
            success: true,
            conversion: {
                id: conversion.id,
                status: conversion.status,
                progress: this.calculateProgress(conversion),
                created_at: conversion.created_at,
                completed_at: conversion.completed_at,
                estimated_duration: conversion.result?.metadata?.estimated_duration,
                error: conversion.error
            }
        };
    }

    getAvailableTemplates() {
        return Array.from(this.templates.values()).map(template => ({
            id: template.id,
            name: template.name,
            description: template.description,
            style: template.style,
            target_length: template.target_length,
            voice_count: template.voice_count,
            tone: template.tone
        }));
    }

    getConversionHistory() {
        return Array.from(this.conversions.values()).map(conversion => ({
            id: conversion.id,
            status: conversion.status,
            template_name: this.templates.get(conversion.template_id)?.name,
            created_at: conversion.created_at,
            completed_at: conversion.completed_at,
            duration_estimate: conversion.result?.metadata?.estimated_duration
        }));
    }
}

export default DocumentToPodcastConverter;