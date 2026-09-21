const cv = require('opencv4nodejs');
const tesseract = require('node-tesseract-ocr');
const fs = require('fs').promises;
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const logger = require('./utils/logger');

class OCRProcessor {
  constructor(options = {}) {
    this.outputDir = options.outputDir || './output/ocr';
    this.tempDir = options.tempDir || './temp/ocr';
    this.languages = options.languages || ['eng'];
    this.confidence = options.confidence || 30;
    this.frameInterval = options.frameInterval || 30;
    this.textRegions = options.textRegions || [];
    this.preprocessingOptions = {
      resize: options.resize || true,
      denoise: options.denoise || true,
      sharpen: options.sharpen || false,
      contrast: options.contrast || true,
      ...options.preprocessing
    };
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

  preprocessFrame(frame) {
    try {
      let processedFrame = frame.clone();

      if (this.preprocessingOptions.resize && (frame.cols > 1920 || frame.rows > 1080)) {
        const scale = Math.min(1920 / frame.cols, 1080 / frame.rows);
        const newSize = new cv.Size(
          Math.floor(frame.cols * scale),
          Math.floor(frame.rows * scale)
        );
        processedFrame = processedFrame.resize(newSize.height, newSize.width);
      }

      let grayFrame = processedFrame.cvtColor(cv.COLOR_BGR2GRAY);

      if (this.preprocessingOptions.denoise) {
        grayFrame = grayFrame.medianBlur(3);
      }

      if (this.preprocessingOptions.contrast) {
        grayFrame = grayFrame.adaptiveThreshold(255, cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY, 11, 2);
      }

      if (this.preprocessingOptions.sharpen) {
        const kernel = new cv.Mat([
          [-1, -1, -1],
          [-1,  9, -1],
          [-1, -1, -1]
        ], cv.CV_32F);
        grayFrame = grayFrame.filter2D(cv.CV_8U, kernel);
      }

      return grayFrame;
    } catch (error) {
      logger.warn('Failed to preprocess frame:', error);
      return frame.cvtColor(cv.COLOR_BGR2GRAY);
    }
  }

  async extractTextFromFrame(frame, frameNumber, timestamp) {
    const sessionId = uuidv4();
    
    try {
      const processedFrame = this.preprocessFrame(frame);
      const tempImagePath = path.join(this.tempDir, `frame_${sessionId}_${frameNumber}.png`);
      
      cv.imwrite(tempImagePath, processedFrame);

      const config = {
        lang: this.languages.join('+'),
        oem: 1,
        psm: 3,
      };

      const text = await tesseract.recognize(tempImagePath, config);
      
      await fs.unlink(tempImagePath);

      const words = this.parseOCROutput(text);
      const filteredWords = words.filter(word => word.confidence >= this.confidence);

      return {
        frameNumber,
        timestamp,
        rawText: text.trim(),
        words: filteredWords,
        wordCount: filteredWords.length,
        averageConfidence: filteredWords.length > 0 ? 
          filteredWords.reduce((sum, word) => sum + word.confidence, 0) / filteredWords.length : 0
      };

    } catch (error) {
      logger.warn(`OCR failed for frame ${frameNumber}:`, error);
      return {
        frameNumber,
        timestamp,
        rawText: '',
        words: [],
        wordCount: 0,
        averageConfidence: 0,
        error: error.message
      };
    }
  }

  parseOCROutput(text) {
    const words = [];
    const lines = text.split('\n');
    
    for (const line of lines) {
      const trimmedLine = line.trim();
      if (trimmedLine.length > 0) {
        const lineWords = trimmedLine.split(/\s+/);
        for (const word of lineWords) {
          if (word.length > 0) {
            words.push({
              text: word,
              confidence: 85
            });
          }
        }
      }
    }
    
    return words;
  }

  async extractTextFromVideo(videoPath, outputOptions = {}) {
    const sessionId = uuidv4();
    logger.info(`Starting OCR extraction for ${videoPath} (session: ${sessionId})`);

    try {
      await this.ensureOutputDirs();
      
      const cap = new cv.VideoCapture(videoPath);
      const totalFrames = cap.get(cv.CAP_PROP_FRAME_COUNT);
      const fps = cap.get(cv.CAP_PROP_FPS);
      
      if (totalFrames <= 0 || fps <= 0) {
        throw new Error('Invalid video file');
      }

      const frameInterval = outputOptions.frameInterval || this.frameInterval;
      const ocrResults = [];
      let frameNumber = 0;
      let processedFrames = 0;

      logger.info(`Processing every ${frameInterval} frames for OCR (total: ${totalFrames} frames)`);

      while (frameNumber < totalFrames) {
        cap.set(cv.CAP_PROP_POS_FRAMES, frameNumber);
        const frame = cap.read();
        
        if (frame.empty) break;

        const timestamp = frameNumber / fps;
        const result = await this.extractTextFromFrame(frame, frameNumber, timestamp);
        
        if (result.wordCount > 0) {
          ocrResults.push(result);
        }

        processedFrames++;
        frameNumber += frameInterval;

        if (outputOptions.onProgress && processedFrames % 10 === 0) {
          const progress = (frameNumber / totalFrames) * 100;
          outputOptions.onProgress(progress, processedFrames, Math.ceil(totalFrames / frameInterval));
        }
      }

      cap.release();

      const analysisResult = this.analyzeOCRResults(ocrResults);
      const timeline = this.generateTextTimeline(ocrResults);

      const result = {
        sessionId,
        videoPath,
        totalFrames,
        fps,
        frameInterval,
        processedFrames,
        ocrResults,
        analysis: analysisResult,
        timeline,
        statistics: {
          totalTextFrames: ocrResults.length,
          totalWords: ocrResults.reduce((sum, result) => sum + result.wordCount, 0),
          averageConfidence: ocrResults.length > 0 ?
            ocrResults.reduce((sum, result) => sum + result.averageConfidence, 0) / ocrResults.length : 0,
          textCoverage: (ocrResults.length / processedFrames) * 100
        }
      };

      await this.saveOCRResults(result);

      logger.info(`OCR extraction completed. Found text in ${ocrResults.length} frames (session: ${sessionId})`);
      return result;

    } catch (error) {
      logger.error(`OCR extraction failed for ${videoPath}:`, error);
      throw error;
    }
  }

  analyzeOCRResults(ocrResults) {
    const allWords = [];
    const wordFrequency = {};
    const textByMinute = {};

    for (const result of ocrResults) {
      const minute = Math.floor(result.timestamp / 60);
      
      if (!textByMinute[minute]) {
        textByMinute[minute] = [];
      }
      
      for (const word of result.words) {
        const cleanWord = word.text.toLowerCase().replace(/[^\w]/g, '');
        if (cleanWord.length > 2) {
          allWords.push(cleanWord);
          wordFrequency[cleanWord] = (wordFrequency[cleanWord] || 0) + 1;
          textByMinute[minute].push(cleanWord);
        }
      }
    }

    const sortedWords = Object.entries(wordFrequency)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 20);

    const textDensityByMinute = Object.entries(textByMinute)
      .map(([minute, words]) => ({
        minute: parseInt(minute),
        wordCount: words.length,
        uniqueWords: [...new Set(words)].length
      }))
      .sort((a, b) => a.minute - b.minute);

    return {
      totalUniqueWords: Object.keys(wordFrequency).length,
      mostFrequentWords: sortedWords,
      textDensityByMinute,
      languages: this.detectLanguages(allWords)
    };
  }

  detectLanguages(words) {
    const commonEnglishWords = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use'];
    
    const englishMatches = words.filter(word => commonEnglishWords.includes(word.toLowerCase())).length;
    const confidence = words.length > 0 ? (englishMatches / words.length) * 100 : 0;
    
    return [
      {
        language: 'english',
        confidence: confidence.toFixed(2)
      }
    ];
  }

  generateTextTimeline(ocrResults) {
    const timeline = [];
    let currentSegment = null;

    for (const result of ocrResults) {
      if (result.rawText.trim().length > 0) {
        if (!currentSegment) {
          currentSegment = {
            startTime: result.timestamp,
            endTime: result.timestamp,
            text: result.rawText,
            frameCount: 1
          };
        } else if (result.timestamp - currentSegment.endTime < 5) {
          currentSegment.endTime = result.timestamp;
          currentSegment.text += ' ' + result.rawText;
          currentSegment.frameCount++;
        } else {
          timeline.push(currentSegment);
          currentSegment = {
            startTime: result.timestamp,
            endTime: result.timestamp,
            text: result.rawText,
            frameCount: 1
          };
        }
      } else if (currentSegment) {
        timeline.push(currentSegment);
        currentSegment = null;
      }
    }

    if (currentSegment) {
      timeline.push(currentSegment);
    }

    return timeline.map((segment, index) => ({
      id: index,
      startTime: parseFloat(segment.startTime.toFixed(2)),
      endTime: parseFloat(segment.endTime.toFixed(2)),
      duration: parseFloat((segment.endTime - segment.startTime).toFixed(2)),
      text: segment.text.trim(),
      frameCount: segment.frameCount
    }));
  }

  async saveOCRResults(results) {
    try {
      const filename = `ocr_results_${results.sessionId}.json`;
      const outputPath = path.join(this.outputDir, filename);
      
      await fs.writeFile(outputPath, JSON.stringify(results, null, 2));
      logger.info(`OCR results saved to ${outputPath}`);
      
      const textFilename = `extracted_text_${results.sessionId}.txt`;
      const textPath = path.join(this.outputDir, textFilename);
      const allText = results.timeline.map(segment => 
        `[${segment.startTime}s - ${segment.endTime}s] ${segment.text}`
      ).join('\n\n');
      
      await fs.writeFile(textPath, allText);
      logger.info(`Extracted text saved to ${textPath}`);
      
    } catch (error) {
      logger.warn('Failed to save OCR results:', error);
    }
  }

  async extractTextFromRegions(videoPath, regions, outputOptions = {}) {
    const sessionId = uuidv4();
    logger.info(`Extracting text from ${regions.length} regions in ${videoPath} (session: ${sessionId})`);

    try {
      const cap = new cv.VideoCapture(videoPath);
      const totalFrames = cap.get(cv.CAP_PROP_FRAME_COUNT);
      const fps = cap.get(cv.CAP_PROP_FPS);

      const regionResults = [];

      for (let regionIndex = 0; regionIndex < regions.length; regionIndex++) {
        const region = regions[regionIndex];
        const regionOCR = [];

        let frameNumber = 0;
        const frameInterval = outputOptions.frameInterval || this.frameInterval;

        while (frameNumber < totalFrames) {
          cap.set(cv.CAP_PROP_POS_FRAMES, frameNumber);
          const frame = cap.read();
          
          if (frame.empty) break;

          try {
            const roi = frame.getRegion(new cv.Rect(region.x, region.y, region.width, region.height));
            const timestamp = frameNumber / fps;
            
            const result = await this.extractTextFromFrame(roi, frameNumber, timestamp);
            if (result.wordCount > 0) {
              regionOCR.push(result);
            }
          } catch (error) {
            logger.warn(`Failed to extract ROI for region ${regionIndex} at frame ${frameNumber}:`, error);
          }

          frameNumber += frameInterval;
        }

        regionResults.push({
          regionIndex,
          region,
          ocrResults: regionOCR,
          timeline: this.generateTextTimeline(regionOCR)
        });

        if (outputOptions.onProgress) {
          const progress = ((regionIndex + 1) / regions.length) * 100;
          outputOptions.onProgress(progress, regionIndex + 1, regions.length);
        }
      }

      cap.release();

      const result = {
        sessionId,
        videoPath,
        regions,
        regionResults,
        totalFrames,
        fps
      };

      logger.info(`Region-based OCR extraction completed for ${regions.length} regions (session: ${sessionId})`);
      return result;

    } catch (error) {
      logger.error(`Region-based OCR extraction failed for ${videoPath}:`, error);
      throw error;
    }
  }
}

module.exports = OCRProcessor;