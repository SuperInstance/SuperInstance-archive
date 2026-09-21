import { EventEmitter } from 'events';
import fs from 'fs/promises';
import path from 'path';
import { v4 as uuidv4 } from 'uuid';

class TranscriptGenerator extends EventEmitter {
    constructor(config = {}) {
        super();
        this.config = {
            output_directory: config.output_directory || './output/transcripts',
            formats: config.formats || ['txt', 'srt', 'vtt', 'json'],
            include_timestamps: config.include_timestamps !== false,
            include_speaker_labels: config.include_speaker_labels !== false,
            include_confidence_scores: config.include_confidence_scores || false,
            word_level_timestamps: config.word_level_timestamps || false,
            ...config
        };

        this.transcriptionTasks = new Map();
        this.transcriptTemplates = new Map();
        this.generatedTranscripts = new Map();

        this.initializeTranscriptTemplates();
        this.ensureDirectories();
    }

    async ensureDirectories() {
        try {
            await fs.mkdir(this.config.output_directory, { recursive: true });
            await fs.mkdir(path.join(this.config.output_directory, 'txt'), { recursive: true });
            await fs.mkdir(path.join(this.config.output_directory, 'srt'), { recursive: true });
            await fs.mkdir(path.join(this.config.output_directory, 'vtt'), { recursive: true });
            await fs.mkdir(path.join(this.config.output_directory, 'json'), { recursive: true });
        } catch (error) {
            this.emit('error', { type: 'directory-creation', error });
        }
    }

    initializeTranscriptTemplates() {
        // Plain Text Template
        this.transcriptTemplates.set('txt', {
            id: 'txt',
            name: 'Plain Text',
            extension: '.txt',
            mime_type: 'text/plain',
            supports_timestamps: true,
            supports_speakers: true,
            generator: this.generatePlainTextTranscript.bind(this)
        });

        // SRT Subtitles Template
        this.transcriptTemplates.set('srt', {
            id: 'srt',
            name: 'SRT Subtitles',
            extension: '.srt',
            mime_type: 'application/x-subrip',
            supports_timestamps: true,
            supports_speakers: true,
            generator: this.generateSRTTranscript.bind(this)
        });

        // WebVTT Template
        this.transcriptTemplates.set('vtt', {
            id: 'vtt',
            name: 'WebVTT',
            extension: '.vtt',
            mime_type: 'text/vtt',
            supports_timestamps: true,
            supports_speakers: true,
            generator: this.generateVTTTranscript.bind(this)
        });

        // JSON Template
        this.transcriptTemplates.set('json', {
            id: 'json',
            name: 'JSON',
            extension: '.json',
            mime_type: 'application/json',
            supports_timestamps: true,
            supports_speakers: true,
            supports_metadata: true,
            generator: this.generateJSONTranscript.bind(this)
        });

        // Word Document Template
        this.transcriptTemplates.set('docx', {
            id: 'docx',
            name: 'Word Document',
            extension: '.docx',
            mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            supports_timestamps: true,
            supports_speakers: true,
            supports_formatting: true,
            generator: this.generateWordTranscript.bind(this)
        });

        // PDF Template
        this.transcriptTemplates.set('pdf', {
            id: 'pdf',
            name: 'PDF Document',
            extension: '.pdf',
            mime_type: 'application/pdf',
            supports_timestamps: true,
            supports_speakers: true,
            supports_formatting: true,
            generator: this.generatePDFTranscript.bind(this)
        });
    }

    async generateTranscript(podcastScript, audioFilePath, transcriptionOptions = {}) {
        const taskId = uuidv4();
        
        try {
            this.emit('transcription-started', { taskId });

            const task = {
                id: taskId,
                podcast_script: podcastScript,
                audio_file_path: audioFilePath,
                options: transcriptionOptions,
                status: 'processing',
                started_at: new Date().toISOString(),
                formats_requested: transcriptionOptions.formats || this.config.formats,
                generated_files: []
            };

            this.transcriptionTasks.set(taskId, task);

            // Generate timing information from script segments
            const timedSegments = await this.generateTimingFromScript(podcastScript, audioFilePath);
            
            // Create transcript data structure
            const transcriptData = await this.createTranscriptData(
                podcastScript,
                timedSegments,
                transcriptionOptions
            );

            // Generate requested formats
            const generatedFiles = [];
            for (const format of task.formats_requested) {
                try {
                    const filePath = await this.generateTranscriptFormat(
                        transcriptData,
                        format,
                        taskId,
                        transcriptionOptions
                    );
                    
                    generatedFiles.push({
                        format: format,
                        file_path: filePath,
                        generated_at: new Date().toISOString()
                    });

                    this.emit('transcript-format-generated', {
                        taskId,
                        format,
                        filePath
                    });

                } catch (formatError) {
                    this.emit('transcript-format-failed', {
                        taskId,
                        format,
                        error: formatError
                    });
                }
            }

            task.generated_files = generatedFiles;
            task.transcript_data = transcriptData;
            task.status = 'completed';
            task.completed_at = new Date().toISOString();

            this.generatedTranscripts.set(taskId, {
                task: task,
                transcript_data: transcriptData,
                files: generatedFiles
            });

            this.emit('transcription-completed', {
                taskId,
                filesGenerated: generatedFiles.length,
                formats: generatedFiles.map(f => f.format)
            });

            return {
                task_id: taskId,
                transcript_data: transcriptData,
                generated_files: generatedFiles
            };

        } catch (error) {
            const task = this.transcriptionTasks.get(taskId);
            if (task) {
                task.status = 'failed';
                task.error = error.message;
            }
            
            this.emit('transcription-failed', { taskId, error });
            throw error;
        }
    }

    async generateTimingFromScript(podcastScript, audioFilePath) {
        // Generate estimated timing based on script content
        const segments = podcastScript.segments || [];
        const totalDuration = await this.getAudioDuration(audioFilePath);
        
        let currentTime = 0;
        const wordsPerMinute = 150; // Average speaking rate
        
        const timedSegments = segments.map((segment, index) => {
            const words = segment.text.split(/\s+/).length;
            const estimatedDuration = (words / wordsPerMinute) * 60; // Convert to seconds
            
            // Add some variation based on segment type
            let adjustedDuration = estimatedDuration;
            if (segment.segment_type === 'transition') {
                adjustedDuration *= 1.2; // Transitions tend to be slower
            } else if (segment.segment_type === 'excitement') {
                adjustedDuration *= 0.9; // Excited speech tends to be faster
            }

            const startTime = currentTime;
            const endTime = currentTime + adjustedDuration;
            
            currentTime = endTime;

            return {
                index: index,
                speaker: segment.speaker,
                text: segment.text,
                start_time: startTime,
                end_time: endTime,
                duration: adjustedDuration,
                word_count: words,
                segment_type: segment.segment_type || 'dialogue'
            };
        });

        // Adjust timing to fit actual audio duration
        const estimatedTotalTime = currentTime;
        const timeScale = totalDuration / estimatedTotalTime;
        
        timedSegments.forEach(segment => {
            segment.start_time *= timeScale;
            segment.end_time *= timeScale;
            segment.duration *= timeScale;
        });

        return timedSegments;
    }

    async getAudioDuration(audioFilePath) {
        try {
            // This would typically use ffprobe, but for now we'll estimate
            // In a real implementation, you'd use ffmpeg.ffprobe
            return 1800; // 30 minutes default
        } catch (error) {
            return 1800; // Fallback duration
        }
    }

    async createTranscriptData(podcastScript, timedSegments, options) {
        const metadata = podcastScript.metadata || {};
        
        return {
            metadata: {
                title: metadata.title || 'Podcast Transcript',
                description: metadata.description || '',
                host: metadata.host || '',
                guests: metadata.guests || [],
                recording_date: metadata.recording_date || new Date().toISOString().split('T')[0],
                duration: timedSegments.length > 0 ? timedSegments[timedSegments.length - 1].end_time : 0,
                total_words: timedSegments.reduce((sum, seg) => sum + seg.word_count, 0),
                speakers: [...new Set(timedSegments.map(seg => seg.speaker))],
                generated_at: new Date().toISOString()
            },
            segments: timedSegments.map(segment => ({
                index: segment.index,
                speaker: segment.speaker,
                text: segment.text,
                start_time: segment.start_time,
                end_time: segment.end_time,
                duration: segment.duration,
                word_count: segment.word_count,
                segment_type: segment.segment_type,
                ...(options.include_confidence_scores && { confidence: 0.95 }), // Mock confidence
                ...(options.word_level_timestamps && { 
                    words: this.generateWordLevelTimestamps(segment.text, segment.start_time, segment.end_time)
                })
            })),
            statistics: {
                total_segments: timedSegments.length,
                total_duration: timedSegments.length > 0 ? timedSegments[timedSegments.length - 1].end_time : 0,
                average_segment_duration: timedSegments.length > 0 ? 
                    timedSegments.reduce((sum, seg) => sum + seg.duration, 0) / timedSegments.length : 0,
                words_per_minute: timedSegments.length > 0 ? 
                    (timedSegments.reduce((sum, seg) => sum + seg.word_count, 0) / 
                     (timedSegments[timedSegments.length - 1].end_time / 60)) : 0,
                speaker_distribution: this.calculateSpeakerDistribution(timedSegments)
            }
        };
    }

    generateWordLevelTimestamps(text, startTime, endTime) {
        const words = text.split(/\s+/);
        const duration = endTime - startTime;
        const timePerWord = duration / words.length;
        
        return words.map((word, index) => ({
            word: word.replace(/[^\w]/g, ''), // Remove punctuation for word
            start_time: startTime + (index * timePerWord),
            end_time: startTime + ((index + 1) * timePerWord),
            confidence: 0.9 + (Math.random() * 0.1) // Mock confidence between 0.9-1.0
        }));
    }

    calculateSpeakerDistribution(segments) {
        const distribution = {};
        
        segments.forEach(segment => {
            if (!distribution[segment.speaker]) {
                distribution[segment.speaker] = {
                    total_time: 0,
                    segment_count: 0,
                    word_count: 0
                };
            }
            
            distribution[segment.speaker].total_time += segment.duration;
            distribution[segment.speaker].segment_count += 1;
            distribution[segment.speaker].word_count += segment.word_count;
        });
        
        return distribution;
    }

    async generateTranscriptFormat(transcriptData, format, taskId, options) {
        const template = this.transcriptTemplates.get(format);
        
        if (!template) {
            throw new Error(`Unsupported transcript format: ${format}`);
        }

        const filename = `transcript_${taskId}${template.extension}`;
        const filePath = path.join(this.config.output_directory, format, filename);
        
        await template.generator(transcriptData, filePath, options);
        
        return filePath;
    }

    async generatePlainTextTranscript(transcriptData, filePath, options) {
        let content = '';
        
        // Header
        content += `${transcriptData.metadata.title}\n`;
        if (transcriptData.metadata.description) {
            content += `${transcriptData.metadata.description}\n`;
        }
        content += `\n`;
        
        if (transcriptData.metadata.host) {
            content += `Host: ${transcriptData.metadata.host}\n`;
        }
        
        if (transcriptData.metadata.guests.length > 0) {
            content += `Guests: ${transcriptData.metadata.guests.join(', ')}\n`;
        }
        
        content += `Date: ${transcriptData.metadata.recording_date}\n`;
        content += `Duration: ${this.formatDuration(transcriptData.metadata.duration)}\n`;
        content += `Total Words: ${transcriptData.metadata.total_words}\n`;
        content += '\n' + '='.repeat(50) + '\n\n';

        // Content
        transcriptData.segments.forEach(segment => {
            if (this.config.include_timestamps) {
                const timestamp = this.formatTimestamp(segment.start_time);
                content += `[${timestamp}] `;
            }
            
            if (this.config.include_speaker_labels) {
                content += `${segment.speaker}: `;
            }
            
            content += `${segment.text}\n\n`;
        });

        // Footer with statistics
        content += '\n' + '='.repeat(50) + '\n';
        content += 'TRANSCRIPT STATISTICS\n';
        content += '='.repeat(50) + '\n';
        content += `Total Segments: ${transcriptData.statistics.total_segments}\n`;
        content += `Total Duration: ${this.formatDuration(transcriptData.statistics.total_duration)}\n`;
        content += `Average Words Per Minute: ${Math.round(transcriptData.statistics.words_per_minute)}\n`;
        content += '\nSpeaker Distribution:\n';
        
        Object.entries(transcriptData.statistics.speaker_distribution).forEach(([speaker, stats]) => {
            const percentage = (stats.total_time / transcriptData.statistics.total_duration * 100).toFixed(1);
            content += `${speaker}: ${this.formatDuration(stats.total_time)} (${percentage}%)\n`;
        });

        await fs.writeFile(filePath, content, 'utf8');
    }

    async generateSRTTranscript(transcriptData, filePath, options) {
        let content = '';
        let subtitleIndex = 1;
        
        transcriptData.segments.forEach(segment => {
            content += `${subtitleIndex}\n`;
            
            const startTime = this.formatSRTTime(segment.start_time);
            const endTime = this.formatSRTTime(segment.end_time);
            content += `${startTime} --> ${endTime}\n`;
            
            let text = segment.text;
            if (this.config.include_speaker_labels) {
                text = `${segment.speaker}: ${text}`;
            }
            
            // Split long lines for readability
            const lines = this.splitTextForSubtitles(text, 80);
            content += lines.join('\n') + '\n\n';
            
            subtitleIndex++;
        });

        await fs.writeFile(filePath, content, 'utf8');
    }

    async generateVTTTranscript(transcriptData, filePath, options) {
        let content = 'WEBVTT\n\n';
        
        // Add metadata
        content += `NOTE\n`;
        content += `Title: ${transcriptData.metadata.title}\n`;
        if (transcriptData.metadata.description) {
            content += `Description: ${transcriptData.metadata.description}\n`;
        }
        content += `Generated: ${transcriptData.metadata.generated_at}\n\n`;
        
        transcriptData.segments.forEach((segment, index) => {
            // Optional cue identifier
            content += `${index + 1}\n`;
            
            const startTime = this.formatVTTTime(segment.start_time);
            const endTime = this.formatVTTTime(segment.end_time);
            content += `${startTime} --> ${endTime}\n`;
            
            let text = segment.text;
            if (this.config.include_speaker_labels) {
                text = `<v ${segment.speaker}>${text}`;
            }
            
            content += `${text}\n\n`;
        });

        await fs.writeFile(filePath, content, 'utf8');
    }

    async generateJSONTranscript(transcriptData, filePath, options) {
        const jsonData = {
            ...transcriptData,
            format_info: {
                generated_by: 'ActiveLog Podcast Generator',
                version: '1.0.0',
                format: 'json',
                generated_at: new Date().toISOString()
            }
        };

        await fs.writeFile(filePath, JSON.stringify(jsonData, null, 2), 'utf8');
    }

    async generateWordTranscript(transcriptData, filePath, options) {
        // This would require a Word document generation library like officegen
        // For now, we'll create a structured text file that could be imported
        let content = `PODCAST TRANSCRIPT\n\n`;
        content += `Title: ${transcriptData.metadata.title}\n`;
        content += `Host: ${transcriptData.metadata.host}\n`;
        content += `Date: ${transcriptData.metadata.recording_date}\n`;
        content += `Duration: ${this.formatDuration(transcriptData.metadata.duration)}\n\n`;
        
        transcriptData.segments.forEach(segment => {
            content += `${segment.speaker} [${this.formatTimestamp(segment.start_time)}]:\n`;
            content += `${segment.text}\n\n`;
        });

        await fs.writeFile(filePath.replace('.docx', '.txt'), content, 'utf8');
    }

    async generatePDFTranscript(transcriptData, filePath, options) {
        // This would require a PDF generation library
        // For now, we'll create a text file that could be converted to PDF
        await this.generatePlainTextTranscript(transcriptData, filePath.replace('.pdf', '.txt'), options);
    }

    formatTimestamp(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    formatSRTTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        const millis = Math.floor((seconds % 1) * 1000);
        
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')},${millis.toString().padStart(3, '0')}`;
    }

    formatVTTTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        const millis = Math.floor((seconds % 1) * 1000);
        
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${millis.toString().padStart(3, '0')}`;
    }

    formatDuration(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}h ${minutes}m ${secs}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${secs}s`;
        } else {
            return `${secs}s`;
        }
    }

    splitTextForSubtitles(text, maxLength) {
        const words = text.split(' ');
        const lines = [];
        let currentLine = '';
        
        words.forEach(word => {
            if ((currentLine + ' ' + word).length <= maxLength) {
                currentLine += (currentLine ? ' ' : '') + word;
            } else {
                if (currentLine) lines.push(currentLine);
                currentLine = word;
            }
        });
        
        if (currentLine) lines.push(currentLine);
        
        return lines;
    }

    async generateInteractiveTranscript(transcriptData, filePath, options) {
        // Generate an HTML interactive transcript
        const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${transcriptData.metadata.title} - Interactive Transcript</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .header { border-bottom: 2px solid #333; margin-bottom: 20px; padding-bottom: 10px; }
        .segment { margin-bottom: 15px; padding: 10px; border-left: 3px solid #007bff; }
        .segment:hover { background-color: #f8f9fa; }
        .timestamp { color: #666; font-size: 0.9em; cursor: pointer; }
        .speaker { font-weight: bold; color: #007bff; }
        .text { margin-top: 5px; line-height: 1.6; }
        .statistics { margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; }
        .clickable { cursor: pointer; text-decoration: underline; }
    </style>
</head>
<body>
    <div class="header">
        <h1>${transcriptData.metadata.title}</h1>
        <p><strong>Host:</strong> ${transcriptData.metadata.host}</p>
        <p><strong>Date:</strong> ${transcriptData.metadata.recording_date}</p>
        <p><strong>Duration:</strong> ${this.formatDuration(transcriptData.metadata.duration)}</p>
    </div>
    
    <div class="transcript">
        ${transcriptData.segments.map(segment => `
            <div class="segment" data-start="${segment.start_time}" data-end="${segment.end_time}">
                <div class="timestamp clickable" onclick="seekTo(${segment.start_time})">
                    ${this.formatTimestamp(segment.start_time)}
                </div>
                <div class="speaker">${segment.speaker}:</div>
                <div class="text">${segment.text}</div>
            </div>
        `).join('')}
    </div>
    
    <div class="statistics">
        <h3>Transcript Statistics</h3>
        <p><strong>Total Segments:</strong> ${transcriptData.statistics.total_segments}</p>
        <p><strong>Total Words:</strong> ${transcriptData.metadata.total_words}</p>
        <p><strong>Average WPM:</strong> ${Math.round(transcriptData.statistics.words_per_minute)}</p>
        
        <h4>Speaker Distribution:</h4>
        ${Object.entries(transcriptData.statistics.speaker_distribution).map(([speaker, stats]) => {
            const percentage = (stats.total_time / transcriptData.statistics.total_duration * 100).toFixed(1);
            return `<p><strong>${speaker}:</strong> ${this.formatDuration(stats.total_time)} (${percentage}%)</p>`;
        }).join('')}
    </div>

    <script>
        function seekTo(time) {
            // This would integrate with an audio player
            console.log('Seek to:', time);
            alert('Would seek to ' + time + ' seconds (requires audio player integration)');
        }
        
        // Highlight current segment during playback
        function highlightSegment(currentTime) {
            const segments = document.querySelectorAll('.segment');
            segments.forEach(segment => {
                const start = parseFloat(segment.dataset.start);
                const end = parseFloat(segment.dataset.end);
                
                if (currentTime >= start && currentTime <= end) {
                    segment.style.backgroundColor = '#fff3cd';
                } else {
                    segment.style.backgroundColor = '';
                }
            });
        }
    </script>
</body>
</html>`;

        await fs.writeFile(filePath.replace(path.extname(filePath), '.html'), html, 'utf8');
    }

    async generateTranscriptSummary(transcriptData) {
        // Generate a summary of the transcript
        const segments = transcriptData.segments;
        const summary = {
            key_topics: [],
            main_speakers: Object.keys(transcriptData.statistics.speaker_distribution),
            total_duration: transcriptData.metadata.duration,
            word_count: transcriptData.metadata.total_words,
            reading_time: Math.ceil(transcriptData.metadata.total_words / 200), // minutes at 200 WPM
            key_moments: []
        };

        // Identify key topics (simplified approach)
        const allText = segments.map(s => s.text).join(' ');
        const words = allText.toLowerCase().split(/\s+/);
        const wordFreq = {};
        
        words.forEach(word => {
            if (word.length > 4) { // Only consider longer words
                wordFreq[word] = (wordFreq[word] || 0) + 1;
            }
        });
        
        summary.key_topics = Object.entries(wordFreq)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 10)
            .map(([word, count]) => ({ word, frequency: count }));

        // Identify potential key moments (segments with questions, exclamations)
        summary.key_moments = segments
            .filter(segment => segment.text.includes('?') || segment.text.includes('!'))
            .slice(0, 5)
            .map(segment => ({
                timestamp: segment.start_time,
                speaker: segment.speaker,
                text: segment.text.substring(0, 100) + '...'
            }));

        return summary;
    }

    getTranscriptFormats() {
        return Array.from(this.transcriptTemplates.values()).map(template => ({
            id: template.id,
            name: template.name,
            extension: template.extension,
            mime_type: template.mime_type,
            supports_timestamps: template.supports_timestamps,
            supports_speakers: template.supports_speakers,
            supports_metadata: template.supports_metadata || false
        }));
    }

    getTranscriptionTask(taskId) {
        return this.transcriptionTasks.get(taskId);
    }

    getGeneratedTranscript(taskId) {
        return this.generatedTranscripts.get(taskId);
    }

    async exportTranscript(taskId, format, customOptions = {}) {
        const transcript = this.generatedTranscripts.get(taskId);
        
        if (!transcript) {
            throw new Error(`Transcript not found: ${taskId}`);
        }

        const exportId = uuidv4();
        const exportPath = await this.generateTranscriptFormat(
            transcript.transcript_data,
            format,
            exportId,
            customOptions
        );

        this.emit('transcript-exported', {
            taskId,
            exportId,
            format,
            exportPath
        });

        return {
            export_id: exportId,
            format: format,
            file_path: exportPath
        };
    }

    async searchTranscript(taskId, searchQuery, options = {}) {
        const transcript = this.generatedTranscripts.get(taskId);
        
        if (!transcript) {
            throw new Error(`Transcript not found: ${taskId}`);
        }

        const searchResults = [];
        const query = searchQuery.toLowerCase();
        const caseSensitive = options.case_sensitive || false;
        
        transcript.transcript_data.segments.forEach((segment, index) => {
            const text = caseSensitive ? segment.text : segment.text.toLowerCase();
            const searchText = caseSensitive ? searchQuery : query;
            
            if (text.includes(searchText)) {
                const beforeText = segment.text.substring(0, text.indexOf(searchText));
                const matchText = segment.text.substring(
                    beforeText.length, 
                    beforeText.length + searchQuery.length
                );
                const afterText = segment.text.substring(beforeText.length + searchQuery.length);
                
                searchResults.push({
                    segment_index: index,
                    speaker: segment.speaker,
                    timestamp: segment.start_time,
                    match: matchText,
                    context_before: beforeText.substring(-50),
                    context_after: afterText.substring(0, 50),
                    full_text: segment.text
                });
            }
        });

        return {
            query: searchQuery,
            results_count: searchResults.length,
            results: searchResults
        };
    }
}

export default TranscriptGenerator;