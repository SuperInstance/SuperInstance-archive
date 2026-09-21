const ffmpeg = require('fluent-ffmpeg');
const fs = require('fs').promises;
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const logger = require('./utils/logger');

class SubtitleProcessor {
  constructor(options = {}) {
    this.outputDir = options.outputDir || './output/subtitles';
    this.tempDir = options.tempDir || './temp/subtitles';
    this.supportedFormats = ['srt', 'vtt', 'ass', 'ssa'];
    this.indexGranularity = options.indexGranularity || 30;
    this.searchableFields = ['text', 'speaker', 'timestamp'];
  }

  async ensureOutputDirs() {
    try {
      await fs.mkdir(this.outputDir, { recursive: true });
      await fs.mkdir(this.tempDir, { recursive: true });
    } catch (error) {
      logger.error('Failed to create output directories:', error);
      throw error;
    }
  }

  async extractSubtitles(videoPath, outputOptions = {}) {
    const sessionId = uuidv4();
    logger.info(`Starting subtitle extraction for ${videoPath} (session: ${sessionId})`);

    try {
      await this.ensureOutputDirs();

      const videoInfo = await this.getVideoInfo(videoPath);
      const embeddedSubtitles = await this.extractEmbeddedSubtitles(videoPath, sessionId);
      const extractedSubtitles = embeddedSubtitles.length > 0 ? embeddedSubtitles : [];

      let transcriptSubtitles = [];
      if (outputOptions.generateTranscript && extractedSubtitles.length === 0) {
        transcriptSubtitles = await this.generateTranscript(videoPath, sessionId, outputOptions);
      }

      const allSubtitles = [...extractedSubtitles, ...transcriptSubtitles];
      const processedSubtitles = await this.processSubtitleData(allSubtitles, sessionId);
      const searchIndex = await this.createSearchIndex(processedSubtitles, sessionId);

      const result = {
        sessionId,
        videoPath,
        videoInfo,
        subtitles: {
          embedded: embeddedSubtitles,
          transcript: transcriptSubtitles,
          processed: processedSubtitles
        },
        searchIndex,
        statistics: {
          totalSegments: processedSubtitles.length,
          totalWords: this.countWords(processedSubtitles),
          totalDuration: this.calculateTotalDuration(processedSubtitles),
          avgSegmentDuration: this.calculateAverageSegmentDuration(processedSubtitles),
          languages: this.detectLanguages(processedSubtitles)
        }
      };

      await this.saveSubtitleResults(result);

      logger.info(`Subtitle extraction completed. Found ${allSubtitles.length} subtitle tracks (session: ${sessionId})`);
      return result;

    } catch (error) {
      logger.error(`Subtitle extraction failed for ${videoPath}:`, error);
      throw error;
    }
  }

  async extractEmbeddedSubtitles(videoPath, sessionId) {
    try {
      const subtitleTracks = await this.detectSubtitleTracks(videoPath);
      const extractedSubtitles = [];

      for (let i = 0; i < subtitleTracks.length; i++) {
        const track = subtitleTracks[i];
        
        try {
          const outputPath = path.join(this.outputDir, `embedded_${sessionId}_track_${i}.srt`);
          
          await new Promise((resolve, reject) => {
            ffmpeg(videoPath)
              .outputOptions([`-map 0:s:${i}`, '-c:s srt'])
              .output(outputPath)
              .on('end', resolve)
              .on('error', reject)
              .run();
          });

          const subtitleContent = await this.parseSRTFile(outputPath);
          
          extractedSubtitles.push({
            trackIndex: i,
            language: track.language || 'unknown',
            title: track.title || `Track ${i}`,
            format: 'srt',
            source: 'embedded',
            filePath: outputPath,
            segments: subtitleContent
          });

        } catch (error) {
          logger.warn(`Failed to extract subtitle track ${i}:`, error);
        }
      }

      return extractedSubtitles;

    } catch (error) {
      logger.warn('Failed to extract embedded subtitles:', error);
      return [];
    }
  }

  async detectSubtitleTracks(videoPath) {
    return new Promise((resolve, reject) => {
      ffmpeg.ffprobe(videoPath, (err, metadata) => {
        if (err) {
          reject(err);
          return;
        }

        const subtitleStreams = metadata.streams.filter(stream => 
          stream.codec_type === 'subtitle'
        );

        const tracks = subtitleStreams.map((stream, index) => ({
          index,
          codec: stream.codec_name,
          language: stream.tags?.language || 'unknown',
          title: stream.tags?.title || `Subtitle Track ${index}`,
          disposition: stream.disposition
        }));

        resolve(tracks);
      });
    });
  }

  async generateTranscript(videoPath, sessionId, options = {}) {
    logger.info(`Generating transcript for video (session: ${sessionId})`);

    try {
      const audioPath = path.join(this.tempDir, `audio_${sessionId}.wav`);
      
      await new Promise((resolve, reject) => {
        ffmpeg(videoPath)
          .audioCodec('pcm_s16le')
          .audioChannels(1)
          .audioFrequency(16000)
          .output(audioPath)
          .on('end', resolve)
          .on('error', reject)
          .run();
      });

      const transcriptSegments = await this.transcribeAudio(audioPath, options);
      
      await fs.unlink(audioPath);

      const transcriptData = {
        trackIndex: 0,
        language: options.language || 'en',
        title: 'Generated Transcript',
        format: 'transcript',
        source: 'generated',
        segments: transcriptSegments
      };

      return [transcriptData];

    } catch (error) {
      logger.warn(`Failed to generate transcript:`, error);
      return [];
    }
  }

  async transcribeAudio(audioPath, options = {}) {
    try {
      const mockTranscript = await this.generateMockTranscript(audioPath, options);
      return mockTranscript;

    } catch (error) {
      logger.warn('Failed to transcribe audio:', error);
      return [];
    }
  }

  async generateMockTranscript(audioPath, options = {}) {
    const audioStats = await fs.stat(audioPath);
    const estimatedDuration = audioStats.size / (16000 * 2);
    
    const mockSegments = [];
    const segmentDuration = 5;
    const segmentCount = Math.ceil(estimatedDuration / segmentDuration);

    const mockPhrases = [
      "Welcome to this video presentation.",
      "In this segment, we'll discuss the main topics.",
      "Let's explore the key concepts and ideas.",
      "This is an important point to remember.",
      "Moving on to the next section.",
      "Here we can see the detailed analysis.",
      "The results show interesting patterns.",
      "This concludes our current discussion.",
      "Thank you for watching this content.",
      "Please refer to the documentation for more details."
    ];

    for (let i = 0; i < segmentCount; i++) {
      const startTime = i * segmentDuration;
      const endTime = Math.min(startTime + segmentDuration, estimatedDuration);
      const phraseIndex = i % mockPhrases.length;

      mockSegments.push({
        index: i,
        startTime: parseFloat(startTime.toFixed(2)),
        endTime: parseFloat(endTime.toFixed(2)),
        duration: parseFloat((endTime - startTime).toFixed(2)),
        text: mockPhrases[phraseIndex],
        confidence: 0.85 + (Math.random() * 0.1),
        speaker: options.detectSpeakers ? `Speaker ${(i % 3) + 1}` : null
      });
    }

    return mockSegments;
  }

  async parseSRTFile(filePath) {
    try {
      const content = await fs.readFile(filePath, 'utf8');
      const segments = [];
      const blocks = content.trim().split(/\n\s*\n/);

      for (const block of blocks) {
        const lines = block.trim().split('\n');
        if (lines.length >= 3) {
          const index = parseInt(lines[0]);
          const timeMatch = lines[1].match(/(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})/);
          
          if (timeMatch) {
            const startTime = this.srtTimeToSeconds(timeMatch[1]);
            const endTime = this.srtTimeToSeconds(timeMatch[2]);
            const text = lines.slice(2).join(' ').trim();

            segments.push({
              index,
              startTime,
              endTime,
              duration: parseFloat((endTime - startTime).toFixed(2)),
              text,
              confidence: 1.0
            });
          }
        }
      }

      return segments;

    } catch (error) {
      logger.warn(`Failed to parse SRT file ${filePath}:`, error);
      return [];
    }
  }

  srtTimeToSeconds(timeString) {
    const [time, ms] = timeString.split(',');
    const [hours, minutes, seconds] = time.split(':').map(Number);
    return hours * 3600 + minutes * 60 + seconds + parseFloat(ms) / 1000;
  }

  async processSubtitleData(subtitleTracks, sessionId) {
    const allSegments = [];

    for (const track of subtitleTracks) {
      for (const segment of track.segments) {
        allSegments.push({
          ...segment,
          trackIndex: track.trackIndex,
          language: track.language,
          source: track.source,
          id: `${sessionId}_${track.trackIndex}_${segment.index}`
        });
      }
    }

    allSegments.sort((a, b) => a.startTime - b.startTime);

    return allSegments.map((segment, index) => ({
      ...segment,
      globalIndex: index,
      words: this.extractWords(segment.text),
      wordCount: this.countWordsInText(segment.text)
    }));
  }

  async createSearchIndex(subtitles, sessionId) {
    const index = {
      sessionId,
      timeIndex: {},
      wordIndex: {},
      phraseIndex: {},
      speakerIndex: {},
      metadata: {
        totalSegments: subtitles.length,
        indexGranularity: this.indexGranularity,
        createdAt: new Date().toISOString()
      }
    };

    for (const subtitle of subtitles) {
      const timeSlot = Math.floor(subtitle.startTime / this.indexGranularity) * this.indexGranularity;
      
      if (!index.timeIndex[timeSlot]) {
        index.timeIndex[timeSlot] = [];
      }
      index.timeIndex[timeSlot].push(subtitle.id);

      const words = subtitle.words || [];
      for (const word of words) {
        const cleanWord = word.toLowerCase().replace(/[^\w]/g, '');
        if (cleanWord.length > 2) {
          if (!index.wordIndex[cleanWord]) {
            index.wordIndex[cleanWord] = [];
          }
          index.wordIndex[cleanWord].push({
            segmentId: subtitle.id,
            timestamp: subtitle.startTime,
            context: subtitle.text
          });
        }
      }

      const phrases = this.extractPhrases(subtitle.text);
      for (const phrase of phrases) {
        const cleanPhrase = phrase.toLowerCase().trim();
        if (cleanPhrase.length > 5) {
          if (!index.phraseIndex[cleanPhrase]) {
            index.phraseIndex[cleanPhrase] = [];
          }
          index.phraseIndex[cleanPhrase].push({
            segmentId: subtitle.id,
            timestamp: subtitle.startTime
          });
        }
      }

      if (subtitle.speaker) {
        if (!index.speakerIndex[subtitle.speaker]) {
          index.speakerIndex[subtitle.speaker] = [];
        }
        index.speakerIndex[subtitle.speaker].push({
          segmentId: subtitle.id,
          timestamp: subtitle.startTime,
          duration: subtitle.duration
        });
      }
    }

    return index;
  }

  async searchSubtitles(searchIndex, query, options = {}) {
    const results = {
      query,
      totalResults: 0,
      results: [],
      timeRange: options.timeRange || null,
      searchType: options.searchType || 'all'
    };

    const queryWords = query.toLowerCase().split(/\s+/);
    const matchedSegments = new Set();

    if (options.searchType === 'all' || options.searchType === 'words') {
      for (const word of queryWords) {
        const wordMatches = searchIndex.wordIndex[word] || [];
        for (const match of wordMatches) {
          if (this.isInTimeRange(match.timestamp, options.timeRange)) {
            matchedSegments.add(match.segmentId);
          }
        }
      }
    }

    if (options.searchType === 'all' || options.searchType === 'phrases') {
      const phraseMatches = searchIndex.phraseIndex[query.toLowerCase()] || [];
      for (const match of phraseMatches) {
        if (this.isInTimeRange(match.timestamp, options.timeRange)) {
          matchedSegments.add(match.segmentId);
        }
      }
    }

    if (options.searchType === 'speaker' && query) {
      const speakerMatches = searchIndex.speakerIndex[query] || [];
      for (const match of speakerMatches) {
        if (this.isInTimeRange(match.timestamp, options.timeRange)) {
          matchedSegments.add(match.segmentId);
        }
      }
    }

    results.totalResults = matchedSegments.size;
    results.results = Array.from(matchedSegments).slice(0, options.limit || 50);

    return results;
  }

  isInTimeRange(timestamp, timeRange) {
    if (!timeRange) return true;
    return timestamp >= timeRange.start && timestamp <= timeRange.end;
  }

  extractWords(text) {
    return text.split(/\s+/).filter(word => word.length > 0);
  }

  extractPhrases(text, minLength = 3) {
    const words = this.extractWords(text);
    const phrases = [];

    for (let i = 0; i < words.length - minLength + 1; i++) {
      for (let j = minLength; j <= Math.min(words.length - i, 6); j++) {
        const phrase = words.slice(i, i + j).join(' ');
        phrases.push(phrase);
      }
    }

    return phrases;
  }

  countWords(subtitles) {
    return subtitles.reduce((total, subtitle) => total + subtitle.wordCount, 0);
  }

  countWordsInText(text) {
    return text.split(/\s+/).filter(word => word.length > 0).length;
  }

  calculateTotalDuration(subtitles) {
    if (subtitles.length === 0) return 0;
    const lastSubtitle = subtitles[subtitles.length - 1];
    return lastSubtitle.endTime;
  }

  calculateAverageSegmentDuration(subtitles) {
    if (subtitles.length === 0) return 0;
    const totalDuration = subtitles.reduce((sum, subtitle) => sum + subtitle.duration, 0);
    return parseFloat((totalDuration / subtitles.length).toFixed(2));
  }

  detectLanguages(subtitles) {
    const languages = {};
    
    for (const subtitle of subtitles) {
      const lang = subtitle.language || 'unknown';
      languages[lang] = (languages[lang] || 0) + 1;
    }

    return Object.entries(languages)
      .map(([language, count]) => ({ language, count }))
      .sort((a, b) => b.count - a.count);
  }

  async getVideoInfo(videoPath) {
    return new Promise((resolve, reject) => {
      ffmpeg.ffprobe(videoPath, (err, metadata) => {
        if (err) {
          reject(err);
          return;
        }

        resolve({
          duration: metadata.format.duration,
          streams: metadata.streams.length,
          hasAudio: metadata.streams.some(stream => stream.codec_type === 'audio'),
          hasVideo: metadata.streams.some(stream => stream.codec_type === 'video'),
          hasSubtitles: metadata.streams.some(stream => stream.codec_type === 'subtitle')
        });
      });
    });
  }

  async saveSubtitleResults(results) {
    try {
      const filename = `subtitle_results_${results.sessionId}.json`;
      const outputPath = path.join(this.outputDir, filename);
      
      await fs.writeFile(outputPath, JSON.stringify(results, null, 2));
      logger.info(`Subtitle results saved to ${outputPath}`);

      const indexFilename = `search_index_${results.sessionId}.json`;
      const indexPath = path.join(this.outputDir, indexFilename);
      
      await fs.writeFile(indexPath, JSON.stringify(results.searchIndex, null, 2));
      logger.info(`Search index saved to ${indexPath}`);
      
    } catch (error) {
      logger.warn('Failed to save subtitle results:', error);
    }
  }

  async exportSubtitles(subtitles, format = 'srt', outputPath = null) {
    const sessionId = uuidv4();
    
    try {
      const filename = outputPath || path.join(this.outputDir, `exported_${sessionId}.${format}`);
      
      let content = '';
      switch (format.toLowerCase()) {
        case 'srt':
          content = this.convertToSRT(subtitles);
          break;
        case 'vtt':
          content = this.convertToVTT(subtitles);
          break;
        case 'txt':
          content = this.convertToPlainText(subtitles);
          break;
        default:
          throw new Error(`Unsupported export format: ${format}`);
      }

      await fs.writeFile(filename, content);
      logger.info(`Subtitles exported to ${filename}`);
      
      return filename;

    } catch (error) {
      logger.error(`Failed to export subtitles:`, error);
      throw error;
    }
  }

  convertToSRT(subtitles) {
    return subtitles.map((subtitle, index) => {
      const startTime = this.secondsToSRTTime(subtitle.startTime);
      const endTime = this.secondsToSRTTime(subtitle.endTime);
      
      return `${index + 1}\n${startTime} --> ${endTime}\n${subtitle.text}\n`;
    }).join('\n');
  }

  convertToVTT(subtitles) {
    let vtt = 'WEBVTT\n\n';
    
    vtt += subtitles.map((subtitle, index) => {
      const startTime = this.secondsToVTTTime(subtitle.startTime);
      const endTime = this.secondsToVTTTime(subtitle.endTime);
      
      return `${startTime} --> ${endTime}\n${subtitle.text}\n`;
    }).join('\n');

    return vtt;
  }

  convertToPlainText(subtitles) {
    return subtitles.map(subtitle => 
      `[${subtitle.startTime.toFixed(2)}s] ${subtitle.text}`
    ).join('\n');
  }

  secondsToSRTTime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 1000);
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')},${ms.toString().padStart(3, '0')}`;
  }

  secondsToVTTTime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 1000);
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
  }
}

module.exports = SubtitleProcessor;