const express = require('express');
const multer = require('multer');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const path = require('path');
const fs = require('fs').promises;
const { v4: uuidv4 } = require('uuid');
const { spawn } = require('child_process');
const winston = require('winston');

class DocumentAIServer {
    constructor() {
        this.app = express();
        this.port = process.env.PORT || 8008;
        
        // Initialize logger
        this.logger = winston.createLogger({
            level: 'info',
            format: winston.format.combine(
                winston.format.timestamp(),
                winston.format.json()
            ),
            transports: [
                new winston.transports.File({ filename: './logs/document-ai.log' }),
                new winston.transports.Console()
            ]
        });
        
        this.setupMiddleware();
        this.setupRoutes();
        this.initializeDirectories();
    }

    async initializeDirectories() {
        const directories = [
            './logs',
            './temp/uploads',
            './output/extracted',
            './output/classified',
            './output/entities',
            './output/summaries',
            './output/tables',
            './output/language',
            './output/vectors'
        ];

        for (const dir of directories) {
            try {
                await fs.mkdir(dir, { recursive: true });
            } catch (error) {
                this.logger.warn(`Failed to create directory ${dir}:`, error.message);
            }
        }
    }

    setupMiddleware() {
        // Security middleware
        this.app.use(helmet());
        
        // CORS
        this.app.use(cors({
            origin: process.env.CORS_ORIGINS ? process.env.CORS_ORIGINS.split(',') : '*',
            credentials: true
        }));
        
        // Compression
        this.app.use(compression());
        
        // Body parsing
        this.app.use(express.json({ limit: '50mb' }));
        this.app.use(express.urlencoded({ extended: true, limit: '50mb' }));
        
        // File upload configuration
        const storage = multer.diskStorage({
            destination: async (req, file, cb) => {
                const uploadDir = './temp/uploads';
                await fs.mkdir(uploadDir, { recursive: true });
                cb(null, uploadDir);
            },
            filename: (req, file, cb) => {
                const uniqueName = `${uuidv4()}_${file.originalname}`;
                cb(null, uniqueName);
            }
        });

        this.upload = multer({
            storage,
            limits: {
                fileSize: 100 * 1024 * 1024, // 100MB limit
            },
            fileFilter: (req, file, cb) => {
                const allowedTypes = [
                    'application/pdf',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'application/vnd.ms-excel',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'text/plain',
                    'text/csv',
                    'image/png',
                    'image/jpeg',
                    'image/tiff'
                ];
                
                if (allowedTypes.includes(file.mimetype)) {
                    cb(null, true);
                } else {
                    cb(new Error(`Unsupported file type: ${file.mimetype}`));
                }
            }
        });

        // Static file serving
        this.app.use('/output', express.static('./output'));
        this.app.use('/docs', express.static('./docs'));
    }

    setupRoutes() {
        // Health check
        this.app.get('/health', (req, res) => {
            res.json({
                status: 'healthy',
                timestamp: new Date().toISOString(),
                version: '1.0.0',
                services: {
                    'text_extraction': 'available',
                    'classification': 'available',
                    'ner': 'available',
                    'summarization': 'available',
                    'table_extraction': 'available',
                    'language_support': 'available',
                    'vector_search': 'available'
                }
            });
        });

        // Service status
        this.app.get('/api/status', (req, res) => {
            res.json({
                server: 'document-ai',
                port: this.port,
                uptime: process.uptime(),
                memory_usage: process.memoryUsage(),
                node_version: process.version,
                supported_formats: [
                    'PDF', 'DOCX', 'XLSX', 'CSV', 'TXT', 'PNG', 'JPEG', 'TIFF'
                ],
                capabilities: [
                    'text_extraction', 'ocr', 'classification', 'ner',
                    'summarization', 'table_extraction', 'translation',
                    'semantic_search', 'document_clustering'
                ]
            });
        });

        // Document upload and processing
        this.app.post('/api/upload', this.upload.single('document'), async (req, res) => {
            try {
                if (!req.file) {
                    return res.status(400).json({ error: 'No document file provided' });
                }

                const sessionId = uuidv4();
                const processingOptions = JSON.parse(req.body.options || '{}');

                this.logger.info(`Document uploaded for processing: ${req.file.originalname} (session: ${sessionId})`);

                // Start processing pipeline
                const result = await this.processDocument(req.file.path, sessionId, processingOptions);

                res.json({
                    session_id: sessionId,
                    status: 'processing_started',
                    file_info: {
                        original_name: req.file.originalname,
                        size: req.file.size,
                        type: req.file.mimetype
                    },
                    ...result
                });

            } catch (error) {
                this.logger.error('Document upload failed:', error);
                res.status(500).json({ error: error.message });
            }
        });

        // Text extraction endpoint
        this.app.post('/api/extract-text', this.upload.single('document'), async (req, res) => {
            try {
                const options = JSON.parse(req.body.options || '{}');
                const result = await this.callPythonScript('textExtractor.py', req.file.path, options);
                res.json(result);
            } catch (error) {
                this.logger.error('Text extraction failed:', error);
                res.status(500).json({ error: error.message });
            }
        });

        // Document classification endpoint
        this.app.post('/api/classify', async (req, res) => {
            try {
                const { text, metadata = {}, options = {} } = req.body;
                
                if (!text) {
                    return res.status(400).json({ error: 'Text is required for classification' });
                }

                const result = await this.callPythonScript('documentClassifier.py', text, { metadata, options });
                res.json(result);
            } catch (error) {
                this.logger.error('Document classification failed:', error);
                res.status(500).json({ error: error.message });
            }
        });

        // Named entity extraction endpoint
        this.app.post('/api/extract-entities', async (req, res) => {
            try {
                const { text, options = {} } = req.body;
                
                if (!text) {
                    return res.status(400).json({ error: 'Text is required for entity extraction' });
                }

                const result = await this.callPythonScript('nerExtractor.py', text, options);
                res.json(result);
            } catch (error) {
                this.logger.error('Entity extraction failed:', error);
                res.status(500).json({ error: error.message });
            }
        });

        // Document summarization endpoint
        this.app.post('/api/summarize', async (req, res) => {
            try {
                const { text, metadata = {}, options = {} } = req.body;
                
                if (!text) {
                    return res.status(400).json({ error: 'Text is required for summarization' });
                }

                const result = await this.callPythonScript('documentSummarizer.py', text, { metadata, options });
                res.json(result);
            } catch (error) {
                this.logger.error('Document summarization failed:', error);
                res.status(500).json({ error: error.message });
            }
        });

        // Table extraction endpoint
        this.app.post('/api/extract-tables', this.upload.single('document'), async (req, res) => {
            try {
                const options = JSON.parse(req.body.options || '{}');
                const result = await this.callPythonScript('tableExtractor.py', req.file.path, options);
                res.json(result);
            } catch (error) {
                this.logger.error('Table extraction failed:', error);
                res.status(500).json({ error: error.message });
            }
        });

        // Language detection endpoint
        this.app.post('/api/detect-language', async (req, res) => {
            try {
                const { text, options = {} } = req.body;
                
                if (!text) {
                    return res.status(400).json({ error: 'Text is required for language detection' });
                }

                const result = await this.callPythonScript('languageSupport.py', text, { action: 'detect', options });
                res.json(result);
            } catch (error) {
                this.logger.error('Language detection failed:', error);
                res.status(500).json({ error: error.message });
            }
        });

        // Translation endpoint
        this.app.post('/api/translate', async (req, res) => {
            try {
                const { text, target_language = 'en', source_language = null, options = {} } = req.body;
                
                if (!text) {
                    return res.status(400).json({ error: 'Text is required for translation' });
                }

                const result = await this.callPythonScript('languageSupport.py', text, {
                    action: 'translate',
                    target_language,
                    source_language,
                    options
                });
                res.json(result);
            } catch (error) {
                this.logger.error('Translation failed:', error);
                res.status(500).json({ error: error.message });
            }
        });

        // Vector search endpoints
        this.app.post('/api/create-embeddings', async (req, res) => {
            try {
                const { text, metadata = {}, options = {} } = req.body;
                
                if (!text) {
                    return res.status(400).json({ error: 'Text is required for creating embeddings' });
                }

                const result = await this.callPythonScript('vectorSearch.py', text, {
                    action: 'embed',
                    metadata,
                    options
                });
                res.json(result);
            } catch (error) {
                this.logger.error('Embedding creation failed:', error);
                res.status(500).json({ error: error.message });
            }
        });

        this.app.post('/api/semantic-search', async (req, res) => {
            try {
                const { query, top_k = 10, filters = {}, options = {} } = req.body;
                
                if (!query) {
                    return res.status(400).json({ error: 'Query is required for semantic search' });
                }

                const result = await this.callPythonScript('vectorSearch.py', query, {
                    action: 'search',
                    top_k,
                    filters,
                    options
                });
                res.json(result);
            } catch (error) {
                this.logger.error('Semantic search failed:', error);
                res.status(500).json({ error: error.message });
            }
        });

        this.app.post('/api/cluster-documents', async (req, res) => {
            try {
                const { session_ids = [], cluster_count = 5, options = {} } = req.body;

                const result = await this.callPythonScript('vectorSearch.py', '', {
                    action: 'cluster',
                    session_ids,
                    cluster_count,
                    options
                });
                res.json(result);
            } catch (error) {
                this.logger.error('Document clustering failed:', error);
                res.status(500).json({ error: error.message });
            }
        });

        // Combined processing pipeline
        this.app.post('/api/process-document', this.upload.single('document'), async (req, res) => {
            try {
                if (!req.file) {
                    return res.status(400).json({ error: 'No document file provided' });
                }

                const sessionId = uuidv4();
                const options = JSON.parse(req.body.options || '{}');

                const pipeline = options.pipeline || [
                    'extract_text', 'classify', 'extract_entities', 
                    'summarize', 'extract_tables', 'create_embeddings'
                ];

                this.logger.info(`Starting document processing pipeline for ${req.file.originalname} (session: ${sessionId})`);

                const result = await this.runProcessingPipeline(req.file.path, sessionId, pipeline, options);

                res.json({
                    session_id: sessionId,
                    file_info: {
                        original_name: req.file.originalname,
                        size: req.file.size,
                        type: req.file.mimetype
                    },
                    pipeline_results: result
                });

            } catch (error) {
                this.logger.error('Document processing pipeline failed:', error);
                res.status(500).json({ error: error.message });
            }
        });

        // Results retrieval
        this.app.get('/api/results/:sessionId', async (req, res) => {
            try {
                const { sessionId } = req.params;
                const results = await this.getSessionResults(sessionId);
                
                if (!results) {
                    return res.status(404).json({ error: 'Results not found' });
                }

                res.json(results);
            } catch (error) {
                this.logger.error('Results retrieval failed:', error);
                res.status(500).json({ error: error.message });
            }
        });

        // Batch processing
        this.app.post('/api/batch-process', this.upload.array('documents', 10), async (req, res) => {
            try {
                if (!req.files || req.files.length === 0) {
                    return res.status(400).json({ error: 'No documents provided' });
                }

                const batchId = uuidv4();
                const options = JSON.parse(req.body.options || '{}');

                this.logger.info(`Starting batch processing for ${req.files.length} documents (batch: ${batchId})`);

                const batchResults = [];

                for (const file of req.files) {
                    const sessionId = uuidv4();
                    try {
                        const result = await this.processDocument(file.path, sessionId, options);
                        batchResults.push({
                            session_id: sessionId,
                            filename: file.originalname,
                            status: 'completed',
                            result
                        });
                    } catch (error) {
                        this.logger.error(`Batch processing failed for ${file.originalname}:`, error);
                        batchResults.push({
                            session_id: sessionId,
                            filename: file.originalname,
                            status: 'failed',
                            error: error.message
                        });
                    }
                }

                res.json({
                    batch_id: batchId,
                    total_documents: req.files.length,
                    results: batchResults,
                    summary: {
                        successful: batchResults.filter(r => r.status === 'completed').length,
                        failed: batchResults.filter(r => r.status === 'failed').length
                    }
                });

            } catch (error) {
                this.logger.error('Batch processing failed:', error);
                res.status(500).json({ error: error.message });
            }
        });

        // Error handling middleware
        this.app.use((err, req, res, next) => {
            this.logger.error('Unhandled error:', err);
            res.status(500).json({
                error: 'Internal server error',
                message: err.message
            });
        });

        // 404 handler
        this.app.use((req, res) => {
            res.status(404).json({
                error: 'Not found',
                path: req.path,
                available_endpoints: [
                    'GET /health',
                    'GET /api/status',
                    'POST /api/upload',
                    'POST /api/extract-text',
                    'POST /api/classify',
                    'POST /api/extract-entities',
                    'POST /api/summarize',
                    'POST /api/extract-tables',
                    'POST /api/detect-language',
                    'POST /api/translate',
                    'POST /api/create-embeddings',
                    'POST /api/semantic-search',
                    'POST /api/cluster-documents',
                    'POST /api/process-document',
                    'GET /api/results/:sessionId',
                    'POST /api/batch-process'
                ]
            });
        });
    }

    async processDocument(filePath, sessionId, options = {}) {
        try {
            const results = {};

            // Step 1: Extract text
            if (options.extract_text !== false) {
                this.logger.info(`Extracting text (session: ${sessionId})`);
                results.text_extraction = await this.callPythonScript('textExtractor.py', filePath, options.text_extraction || {});
            }

            // Get extracted text for subsequent processing
            const extractedText = results.text_extraction?.full_text || results.text_extraction?.text || '';

            if (!extractedText) {
                throw new Error('No text extracted from document');
            }

            // Step 2: Classify document
            if (options.classify !== false) {
                this.logger.info(`Classifying document (session: ${sessionId})`);
                results.classification = await this.callPythonScript('documentClassifier.py', extractedText, options.classification || {});
            }

            // Step 3: Extract entities
            if (options.extract_entities !== false) {
                this.logger.info(`Extracting entities (session: ${sessionId})`);
                const nerOptions = { 
                    document_type: results.classification?.final_classification?.predicted_category,
                    ...options.entity_extraction 
                };
                results.entity_extraction = await this.callPythonScript('nerExtractor.py', extractedText, nerOptions);
            }

            // Step 4: Summarize
            if (options.summarize !== false) {
                this.logger.info(`Summarizing document (session: ${sessionId})`);
                const summaryOptions = {
                    metadata: {
                        document_type: results.classification?.final_classification?.predicted_category,
                        ...options.summarization?.metadata
                    },
                    ...options.summarization
                };
                results.summarization = await this.callPythonScript('documentSummarizer.py', extractedText, summaryOptions);
            }

            // Step 5: Extract tables
            if (options.extract_tables !== false) {
                this.logger.info(`Extracting tables (session: ${sessionId})`);
                results.table_extraction = await this.callPythonScript('tableExtractor.py', filePath, options.table_extraction || {});
            }

            // Step 6: Detect language
            if (options.detect_language !== false) {
                this.logger.info(`Detecting language (session: ${sessionId})`);
                results.language_detection = await this.callPythonScript('languageSupport.py', extractedText, { action: 'detect' });
            }

            // Step 7: Create embeddings
            if (options.create_embeddings !== false) {
                this.logger.info(`Creating embeddings (session: ${sessionId})`);
                const embeddingMetadata = {
                    session_id: sessionId,
                    document_type: results.classification?.final_classification?.predicted_category,
                    language: results.language_detection?.final_detection?.language,
                    ...options.embeddings?.metadata
                };
                results.embeddings = await this.callPythonScript('vectorSearch.py', extractedText, {
                    action: 'embed',
                    metadata: embeddingMetadata,
                    options: options.embeddings || {}
                });
            }

            // Save combined results
            await this.saveSessionResults(sessionId, results);

            return {
                status: 'completed',
                session_id: sessionId,
                processing_summary: {
                    steps_completed: Object.keys(results).length,
                    text_length: extractedText.length,
                    document_type: results.classification?.final_classification?.predicted_category || 'unknown',
                    language: results.language_detection?.final_detection?.language || 'unknown',
                    entities_found: results.entity_extraction?.statistics?.total_entities || 0,
                    tables_found: results.table_extraction?.tables?.length || 0
                },
                results
            };

        } catch (error) {
            this.logger.error(`Document processing failed (session: ${sessionId}):`, error);
            throw error;
        }
    }

    async runProcessingPipeline(filePath, sessionId, pipeline, options = {}) {
        const results = {};
        let extractedText = '';

        for (const step of pipeline) {
            try {
                this.logger.info(`Running pipeline step: ${step} (session: ${sessionId})`);

                switch (step) {
                    case 'extract_text':
                        results[step] = await this.callPythonScript('textExtractor.py', filePath, options.text_extraction || {});
                        extractedText = results[step]?.full_text || results[step]?.text || '';
                        break;

                    case 'classify':
                        if (!extractedText) throw new Error('Text extraction required before classification');
                        results[step] = await this.callPythonScript('documentClassifier.py', extractedText, options.classification || {});
                        break;

                    case 'extract_entities':
                        if (!extractedText) throw new Error('Text extraction required before entity extraction');
                        const nerOptions = { 
                            document_type: results.classify?.final_classification?.predicted_category,
                            ...options.entity_extraction 
                        };
                        results[step] = await this.callPythonScript('nerExtractor.py', extractedText, nerOptions);
                        break;

                    case 'summarize':
                        if (!extractedText) throw new Error('Text extraction required before summarization');
                        const summaryOptions = {
                            metadata: {
                                document_type: results.classify?.final_classification?.predicted_category,
                                ...options.summarization?.metadata
                            },
                            ...options.summarization
                        };
                        results[step] = await this.callPythonScript('documentSummarizer.py', extractedText, summaryOptions);
                        break;

                    case 'extract_tables':
                        results[step] = await this.callPythonScript('tableExtractor.py', filePath, options.table_extraction || {});
                        break;

                    case 'detect_language':
                        if (!extractedText) throw new Error('Text extraction required before language detection');
                        results[step] = await this.callPythonScript('languageSupport.py', extractedText, { action: 'detect' });
                        break;

                    case 'create_embeddings':
                        if (!extractedText) throw new Error('Text extraction required before creating embeddings');
                        const embeddingMetadata = {
                            session_id: sessionId,
                            document_type: results.classify?.final_classification?.predicted_category,
                            language: results.detect_language?.final_detection?.language,
                            ...options.embeddings?.metadata
                        };
                        results[step] = await this.callPythonScript('vectorSearch.py', extractedText, {
                            action: 'embed',
                            metadata: embeddingMetadata,
                            options: options.embeddings || {}
                        });
                        break;

                    default:
                        this.logger.warn(`Unknown pipeline step: ${step}`);
                }

            } catch (error) {
                this.logger.error(`Pipeline step ${step} failed (session: ${sessionId}):`, error);
                results[step] = { error: error.message, success: false };
            }
        }

        // Save pipeline results
        await this.saveSessionResults(sessionId, results);

        return results;
    }

    async callPythonScript(scriptName, input, options = {}) {
        return new Promise((resolve, reject) => {
            const scriptPath = path.join(__dirname, 'processors', scriptName);
            const args = [];
            
            // Handle different input types
            if (typeof input === 'string') {
                if (input.startsWith('./') || input.startsWith('/') || input.includes('temp/uploads')) {
                    // File path
                    args.push(input, '--file');
                } else {
                    // Text content - write to temp file
                    const tempFile = `./temp/input_${uuidv4()}.txt`;
                    require('fs').writeFileSync(tempFile, input);
                    args.push(tempFile, '--file');
                    
                    // Clean up temp file after processing
                    setTimeout(() => {
                        try {
                            require('fs').unlinkSync(tempFile);
                        } catch (e) {
                            // Ignore cleanup errors
                        }
                    }, 60000);
                }
            }

            // Add options as JSON
            if (Object.keys(options).length > 0) {
                args.push('--options', JSON.stringify(options));
            }

            const pythonProcess = spawn('python3', [scriptPath, ...args], {
                stdio: ['pipe', 'pipe', 'pipe']
            });

            let stdout = '';
            let stderr = '';

            pythonProcess.stdout.on('data', (data) => {
                stdout += data.toString();
            });

            pythonProcess.stderr.on('data', (data) => {
                stderr += data.toString();
            });

            pythonProcess.on('close', (code) => {
                if (code !== 0) {
                    this.logger.error(`Python script ${scriptName} failed with code ${code}:`, stderr);
                    reject(new Error(`Python script failed: ${stderr}`));
                } else {
                    try {
                        // Try to parse JSON output
                        const result = JSON.parse(stdout);
                        resolve(result);
                    } catch (parseError) {
                        // If not JSON, return raw output
                        resolve({ output: stdout, raw: true });
                    }
                }
            });

            pythonProcess.on('error', (error) => {
                this.logger.error(`Failed to spawn Python script ${scriptName}:`, error);
                reject(error);
            });
        });
    }

    async saveSessionResults(sessionId, results) {
        try {
            const resultsFile = `./output/session_results_${sessionId}.json`;
            await fs.writeFile(resultsFile, JSON.stringify({
                session_id: sessionId,
                timestamp: new Date().toISOString(),
                results
            }, null, 2));
            
            this.logger.info(`Session results saved: ${resultsFile}`);
        } catch (error) {
            this.logger.error(`Failed to save session results for ${sessionId}:`, error);
        }
    }

    async getSessionResults(sessionId) {
        try {
            const resultsFile = `./output/session_results_${sessionId}.json`;
            const data = await fs.readFile(resultsFile, 'utf8');
            return JSON.parse(data);
        } catch (error) {
            if (error.code === 'ENOENT') {
                return null; // File not found
            }
            this.logger.error(`Failed to retrieve session results for ${sessionId}:`, error);
            throw error;
        }
    }

    async start() {
        try {
            await this.initializeDirectories();

            this.server = this.app.listen(this.port, () => {
                this.logger.info(`Document AI Server started on port ${this.port}`);
                this.logger.info(`Health check: http://localhost:${this.port}/health`);
                this.logger.info(`API documentation: http://localhost:${this.port}/docs`);
                
                console.log(`
╔══════════════════════════════════════════════════════════════╗
║                    Document AI Service                       ║
║                                                              ║
║  🚀 Server running on port ${this.port}                             ║
║  📊 Health check: http://localhost:${this.port}/health                ║
║  📚 API docs: http://localhost:${this.port}/docs                     ║
║                                                              ║
║  Available Services:                                         ║
║  📄 Text Extraction & OCR                                   ║
║  🏷️  Document Classification                                 ║
║  🎯 Named Entity Recognition                                 ║
║  📝 Document Summarization                                   ║
║  📊 Table Extraction                                         ║
║  🌍 Multi-language Support                                   ║
║  🔍 Vector Search & Clustering                               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
                `);
            });

            // Graceful shutdown
            process.on('SIGTERM', () => this.gracefulShutdown());
            process.on('SIGINT', () => this.gracefulShutdown());

        } catch (error) {
            this.logger.error('Failed to start server:', error);
            process.exit(1);
        }
    }

    async gracefulShutdown() {
        this.logger.info('Shutting down gracefully...');

        if (this.server) {
            this.server.close(() => {
                this.logger.info('HTTP server closed');
                process.exit(0);
            });

            // Force shutdown after timeout
            setTimeout(() => {
                this.logger.error('Forced shutdown after timeout');
                process.exit(1);
            }, 30000);
        }
    }
}

// Start server if this file is run directly
if (require.main === module) {
    const server = new DocumentAIServer();
    server.start();
}

module.exports = DocumentAIServer;