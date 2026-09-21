const axios = require('axios');
const fs = require('fs').promises;
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const logger = require('./utils/logger');

class AISummarizer {
  constructor(options = {}) {
    this.outputDir = options.outputDir || './output/summaries';
    this.aiProvider = options.aiProvider || 'openai';
    this.model = options.model || 'gpt-3.5-turbo';
    this.maxTokens = options.maxTokens || 1000;
    this.temperature = options.temperature || 0.7;
    this.apiKey = options.apiKey || process.env.OPENAI_API_KEY;
    this.aiOrchestratorUrl = options.aiOrchestratorUrl || 'http://localhost:8003';
    this.chunkSize = options.chunkSize || 10;
  }

  async ensureOutputDir() {
    try {
      await fs.mkdir(this.outputDir, { recursive: true });
    } catch (error) {
      logger.error('Failed to create output directory:', error);
      throw error;
    }
  }

  async generateVideoSummary(videoData, options = {}) {
    const sessionId = uuidv4();
    logger.info(`Generating AI summary for video (session: ${sessionId})`);

    try {
      await this.ensureOutputDir();

      const summaryData = {
        videoPath: videoData.videoPath,
        duration: videoData.duration || 0,
        scenes: videoData.scenes || [],
        keyframes: videoData.keyframes || [],
        ocrResults: videoData.ocrResults || [],
        subtitles: videoData.subtitles || []
      };

      const contextualSummary = await this.generateContextualSummary(summaryData, options);
      const technicalSummary = await this.generateTechnicalSummary(summaryData, options);
      const thematicAnalysis = await this.generateThematicAnalysis(summaryData, options);

      const comprehensiveSummary = await this.generateComprehensiveSummary({
        contextual: contextualSummary,
        technical: technicalSummary,
        thematic: thematicAnalysis,
        metadata: summaryData
      }, options);

      const result = {
        sessionId,
        videoPath: videoData.videoPath,
        timestamp: new Date().toISOString(),
        summaries: {
          comprehensive: comprehensiveSummary,
          contextual: contextualSummary,
          technical: technicalSummary,
          thematic: thematicAnalysis
        },
        metadata: {
          duration: summaryData.duration,
          sceneCount: summaryData.scenes.length,
          keyframeCount: summaryData.keyframes.length,
          hasOCR: summaryData.ocrResults.length > 0,
          hasSubtitles: summaryData.subtitles.length > 0
        }
      };

      await this.saveSummaryResults(result);

      logger.info(`AI summary generation completed (session: ${sessionId})`);
      return result;

    } catch (error) {
      logger.error(`AI summary generation failed:`, error);
      throw error;
    }
  }

  async generateContextualSummary(videoData, options = {}) {
    try {
      const prompt = this.buildContextualPrompt(videoData);
      
      const response = await this.callAIService({
        prompt,
        maxTokens: this.maxTokens,
        temperature: this.temperature,
        type: 'contextual_summary'
      });

      return {
        type: 'contextual',
        content: response.content,
        keyPoints: this.extractKeyPoints(response.content),
        timeline: this.generateSummaryTimeline(videoData.scenes, response.content),
        confidence: response.confidence || 0.8
      };

    } catch (error) {
      logger.warn('Failed to generate contextual summary:', error);
      return {
        type: 'contextual',
        content: 'Failed to generate contextual summary',
        keyPoints: [],
        timeline: [],
        confidence: 0,
        error: error.message
      };
    }
  }

  async generateTechnicalSummary(videoData, options = {}) {
    try {
      const prompt = this.buildTechnicalPrompt(videoData);
      
      const response = await this.callAIService({
        prompt,
        maxTokens: 500,
        temperature: 0.3,
        type: 'technical_summary'
      });

      return {
        type: 'technical',
        content: response.content,
        specifications: this.extractTechnicalSpecs(videoData),
        qualityMetrics: this.calculateQualityMetrics(videoData),
        processingInfo: this.generateProcessingInfo(videoData),
        confidence: response.confidence || 0.9
      };

    } catch (error) {
      logger.warn('Failed to generate technical summary:', error);
      return {
        type: 'technical',
        content: 'Failed to generate technical summary',
        specifications: {},
        qualityMetrics: {},
        processingInfo: {},
        confidence: 0,
        error: error.message
      };
    }
  }

  async generateThematicAnalysis(videoData, options = {}) {
    try {
      const prompt = this.buildThematicPrompt(videoData);
      
      const response = await this.callAIService({
        prompt,
        maxTokens: 800,
        temperature: 0.8,
        type: 'thematic_analysis'
      });

      return {
        type: 'thematic',
        content: response.content,
        themes: this.extractThemes(response.content),
        sentiment: this.analyzeSentiment(videoData),
        topics: this.extractTopics(videoData.ocrResults, videoData.subtitles),
        confidence: response.confidence || 0.7
      };

    } catch (error) {
      logger.warn('Failed to generate thematic analysis:', error);
      return {
        type: 'thematic',
        content: 'Failed to generate thematic analysis',
        themes: [],
        sentiment: 'neutral',
        topics: [],
        confidence: 0,
        error: error.message
      };
    }
  }

  async generateComprehensiveSummary(summaryData, options = {}) {
    try {
      const prompt = this.buildComprehensivePrompt(summaryData);
      
      const response = await this.callAIService({
        prompt,
        maxTokens: 1500,
        temperature: 0.6,
        type: 'comprehensive_summary'
      });

      return {
        type: 'comprehensive',
        content: response.content,
        executiveSummary: this.extractExecutiveSummary(response.content),
        recommendations: this.extractRecommendations(response.content),
        insights: this.generateInsights(summaryData),
        confidence: response.confidence || 0.8
      };

    } catch (error) {
      logger.warn('Failed to generate comprehensive summary:', error);
      return {
        type: 'comprehensive',
        content: 'Failed to generate comprehensive summary',
        executiveSummary: '',
        recommendations: [],
        insights: [],
        confidence: 0,
        error: error.message
      };
    }
  }

  buildContextualPrompt(videoData) {
    let prompt = `Analyze this video content and provide a contextual summary:\n\n`;
    
    prompt += `Video Duration: ${videoData.duration} seconds\n`;
    prompt += `Number of Scenes: ${videoData.scenes.length}\n\n`;

    if (videoData.scenes.length > 0) {
      prompt += `Scene Information:\n`;
      videoData.scenes.slice(0, 10).forEach((scene, index) => {
        prompt += `Scene ${index + 1}: ${scene.startTime}s - ${scene.endTime}s (${scene.duration}s)\n`;
      });
      prompt += `\n`;
    }

    if (videoData.ocrResults.length > 0) {
      prompt += `Text Content Found:\n`;
      const textSegments = videoData.ocrResults.slice(0, 5).map(ocr => 
        `${ocr.timestamp}s: ${ocr.rawText}`
      );
      prompt += textSegments.join('\n') + '\n\n';
    }

    if (videoData.subtitles.length > 0) {
      prompt += `Subtitle Content:\n`;
      const subtitleSegments = videoData.subtitles.slice(0, 5).map(sub => 
        `${sub.startTime}s: ${sub.text}`
      );
      prompt += subtitleSegments.join('\n') + '\n\n';
    }

    prompt += `Please provide:\n`;
    prompt += `1. A concise summary of the video content\n`;
    prompt += `2. Key events or moments\n`;
    prompt += `3. Main topics or themes\n`;
    prompt += `4. Overall narrative flow\n`;

    return prompt;
  }

  buildTechnicalPrompt(videoData) {
    let prompt = `Provide a technical analysis of this video:\n\n`;
    
    prompt += `Duration: ${videoData.duration} seconds\n`;
    prompt += `Scenes Detected: ${videoData.scenes.length}\n`;
    prompt += `Keyframes Extracted: ${videoData.keyframes.length}\n`;
    prompt += `OCR Results: ${videoData.ocrResults.length} frames with text\n\n`;

    if (videoData.scenes.length > 0) {
      const avgSceneDuration = videoData.scenes.reduce((sum, scene) => sum + scene.duration, 0) / videoData.scenes.length;
      prompt += `Average Scene Duration: ${avgSceneDuration.toFixed(2)} seconds\n`;
    }

    prompt += `Please analyze:\n`;
    prompt += `1. Video structure and pacing\n`;
    prompt += `2. Content density and complexity\n`;
    prompt += `3. Technical quality indicators\n`;
    prompt += `4. Processing efficiency metrics\n`;

    return prompt;
  }

  buildThematicPrompt(videoData) {
    let prompt = `Analyze the themes and content of this video:\n\n`;

    if (videoData.ocrResults.length > 0) {
      prompt += `Text Content:\n`;
      const allText = videoData.ocrResults.map(ocr => ocr.rawText).join(' ');
      prompt += allText.substring(0, 1000) + '\n\n';
    }

    if (videoData.subtitles.length > 0) {
      prompt += `Spoken Content:\n`;
      const allSubtitles = videoData.subtitles.map(sub => sub.text).join(' ');
      prompt += allSubtitles.substring(0, 1000) + '\n\n';
    }

    prompt += `Please identify:\n`;
    prompt += `1. Main themes and topics\n`;
    prompt += `2. Emotional tone and sentiment\n`;
    prompt += `3. Key concepts and ideas\n`;
    prompt += `4. Target audience and purpose\n`;

    return prompt;
  }

  buildComprehensivePrompt(summaryData) {
    let prompt = `Create a comprehensive summary based on these analyses:\n\n`;
    
    prompt += `Contextual Summary: ${summaryData.contextual.content}\n\n`;
    prompt += `Technical Summary: ${summaryData.technical.content}\n\n`;
    prompt += `Thematic Analysis: ${summaryData.thematic.content}\n\n`;

    prompt += `Please provide:\n`;
    prompt += `1. Executive summary (2-3 sentences)\n`;
    prompt += `2. Key insights and findings\n`;
    prompt += `3. Recommendations for use or improvement\n`;
    prompt += `4. Overall assessment and value\n`;

    return prompt;
  }

  async callAIService(params) {
    try {
      if (this.aiOrchestratorUrl) {
        const response = await axios.post(`${this.aiOrchestratorUrl}/process`, {
          provider: this.aiProvider,
          model: this.model,
          messages: [
            { role: 'user', content: params.prompt }
          ],
          max_tokens: params.maxTokens,
          temperature: params.temperature
        });

        return {
          content: response.data.choices[0].message.content,
          confidence: 0.8
        };
      } else {
        return {
          content: `Mock AI response for ${params.type}. This would contain actual AI-generated content in a production environment.`,
          confidence: 0.5
        };
      }

    } catch (error) {
      logger.warn(`AI service call failed: ${error.message}`);
      return {
        content: `Failed to generate ${params.type}`,
        confidence: 0,
        error: error.message
      };
    }
  }

  extractKeyPoints(content) {
    const sentences = content.split(/[.!?]+/).filter(s => s.trim().length > 0);
    return sentences.slice(0, 5).map(sentence => sentence.trim());
  }

  extractThemes(content) {
    const themeKeywords = ['theme:', 'topic:', 'subject:', 'main idea:', 'concept:'];
    const lines = content.split('\n');
    const themes = [];

    for (const line of lines) {
      const lowerLine = line.toLowerCase();
      for (const keyword of themeKeywords) {
        if (lowerLine.includes(keyword)) {
          const theme = line.substring(line.toLowerCase().indexOf(keyword) + keyword.length).trim();
          if (theme.length > 0) {
            themes.push(theme);
          }
        }
      }
    }

    return themes.slice(0, 5);
  }

  extractExecutiveSummary(content) {
    const lines = content.split('\n');
    for (const line of lines) {
      if (line.toLowerCase().includes('executive') || line.toLowerCase().includes('summary')) {
        const nextLineIndex = lines.indexOf(line) + 1;
        if (nextLineIndex < lines.length) {
          return lines.slice(nextLineIndex, nextLineIndex + 3).join(' ').trim();
        }
      }
    }
    
    return content.split('\n')[0] || '';
  }

  extractRecommendations(content) {
    const lines = content.split('\n');
    const recommendations = [];
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].toLowerCase();
      if (line.includes('recommend') || line.includes('suggest') || line.includes('should')) {
        recommendations.push(lines[i].trim());
      }
    }
    
    return recommendations.slice(0, 3);
  }

  generateSummaryTimeline(scenes, summary) {
    if (!scenes || scenes.length === 0) return [];
    
    const timelineSegments = Math.min(scenes.length, 5);
    const segmentSize = Math.ceil(scenes.length / timelineSegments);
    const timeline = [];
    
    for (let i = 0; i < timelineSegments; i++) {
      const startIndex = i * segmentSize;
      const endIndex = Math.min(startIndex + segmentSize, scenes.length);
      const segmentScenes = scenes.slice(startIndex, endIndex);
      
      if (segmentScenes.length > 0) {
        timeline.push({
          startTime: segmentScenes[0].startTime,
          endTime: segmentScenes[segmentScenes.length - 1].endTime,
          description: `Segment ${i + 1}: Duration ${(segmentScenes[segmentScenes.length - 1].endTime - segmentScenes[0].startTime).toFixed(1)}s`
        });
      }
    }
    
    return timeline;
  }

  extractTechnicalSpecs(videoData) {
    return {
      processingMetrics: {
        scenesDetected: videoData.scenes.length,
        keyframesExtracted: videoData.keyframes.length,
        ocrFramesProcessed: videoData.ocrResults.length,
        subtitleSegments: videoData.subtitles.length
      },
      qualityIndicators: {
        sceneVariability: videoData.scenes.length > 0 ? 
          (videoData.scenes.reduce((sum, scene) => sum + scene.duration, 0) / videoData.scenes.length).toFixed(2) : 0,
        textContent: videoData.ocrResults.length > 0 ? 'detected' : 'none',
        audioContent: videoData.subtitles.length > 0 ? 'detected' : 'none'
      }
    };
  }

  calculateQualityMetrics(videoData) {
    const metrics = {
      contentRichness: 0,
      structuralComplexity: 0,
      informationDensity: 0
    };

    if (videoData.scenes.length > 0) {
      metrics.structuralComplexity = Math.min(videoData.scenes.length / 10, 1);
    }

    if (videoData.ocrResults.length > 0 || videoData.subtitles.length > 0) {
      metrics.informationDensity = Math.min(
        (videoData.ocrResults.length + videoData.subtitles.length) / 100, 1
      );
    }

    metrics.contentRichness = (metrics.structuralComplexity + metrics.informationDensity) / 2;

    return metrics;
  }

  generateProcessingInfo(videoData) {
    return {
      analysisTypes: [
        videoData.scenes.length > 0 ? 'scene_detection' : null,
        videoData.keyframes.length > 0 ? 'keyframe_extraction' : null,
        videoData.ocrResults.length > 0 ? 'ocr_processing' : null,
        videoData.subtitles.length > 0 ? 'subtitle_extraction' : null
      ].filter(Boolean),
      dataPoints: {
        scenes: videoData.scenes.length,
        keyframes: videoData.keyframes.length,
        ocrFrames: videoData.ocrResults.length,
        subtitleSegments: videoData.subtitles.length
      }
    };
  }

  analyzeSentiment(videoData) {
    let positiveWords = 0;
    let negativeWords = 0;
    let totalWords = 0;

    const positiveKeywords = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'perfect', 'love', 'best', 'awesome'];
    const negativeKeywords = ['bad', 'terrible', 'awful', 'horrible', 'worst', 'hate', 'problem', 'issue', 'error', 'fail'];

    const allText = [
      ...videoData.ocrResults.map(ocr => ocr.rawText),
      ...videoData.subtitles.map(sub => sub.text)
    ].join(' ').toLowerCase();

    const words = allText.split(/\s+/);
    totalWords = words.length;

    for (const word of words) {
      if (positiveKeywords.includes(word)) positiveWords++;
      if (negativeKeywords.includes(word)) negativeWords++;
    }

    if (positiveWords > negativeWords) return 'positive';
    if (negativeWords > positiveWords) return 'negative';
    return 'neutral';
  }

  extractTopics(ocrResults, subtitles) {
    const allText = [
      ...ocrResults.map(ocr => ocr.rawText),
      ...subtitles.map(sub => sub.text)
    ].join(' ').toLowerCase();

    const words = allText.split(/\s+/).filter(word => word.length > 3);
    const wordFreq = {};

    for (const word of words) {
      wordFreq[word] = (wordFreq[word] || 0) + 1;
    }

    return Object.entries(wordFreq)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 10)
      .map(([word, count]) => ({ word, frequency: count }));
  }

  generateInsights(summaryData) {
    const insights = [];

    if (summaryData.technical.specifications.processingMetrics.scenesDetected > 20) {
      insights.push("High scene variability suggests dynamic content");
    }

    if (summaryData.thematic.sentiment === 'positive') {
      insights.push("Overall positive sentiment detected in content");
    }

    if (summaryData.technical.qualityMetrics.informationDensity > 0.7) {
      insights.push("Information-dense content with significant text/audio");
    }

    return insights;
  }

  async saveSummaryResults(results) {
    try {
      const filename = `summary_${results.sessionId}.json`;
      const outputPath = path.join(this.outputDir, filename);
      
      await fs.writeFile(outputPath, JSON.stringify(results, null, 2));
      logger.info(`Summary results saved to ${outputPath}`);
      
    } catch (error) {
      logger.warn('Failed to save summary results:', error);
    }
  }
}

module.exports = AISummarizer;