const path = require('path');

module.exports = {
  server: {
    port: process.env.PORT || 8008,
    host: process.env.HOST || 'localhost',
    cors: {
      origin: process.env.CORS_ORIGIN || '*',
      credentials: true
    }
  },
  
  processing: {
    maxFileSize: process.env.MAX_FILE_SIZE || '50MB',
    supportedFormats: [
      'pdf', 'docx', 'doc', 'txt', 'xlsx', 'xls', 'csv',
      'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'html', 'htm'
    ],
    tempDir: process.env.TEMP_DIR || path.join(__dirname, '../../temp'),
    outputDir: process.env.OUTPUT_DIR || path.join(__dirname, '../../output')
  },
  
  ai: {
    enableGPUAcceleration: process.env.ENABLE_GPU === 'true',
    modelCacheDir: process.env.MODEL_CACHE_DIR || path.join(__dirname, '../../models'),
    
    classification: {
      confidence_threshold: parseFloat(process.env.CLASSIFICATION_THRESHOLD) || 0.7,
      ensemble_weights: {
        rule_based: 0.3,
        statistical: 0.3,
        transformer: 0.4
      }
    },
    
    ner: {
      confidence_threshold: parseFloat(process.env.NER_THRESHOLD) || 0.8,
      enable_custom_patterns: process.env.ENABLE_CUSTOM_NER !== 'false'
    },
    
    summarization: {
      max_length: parseInt(process.env.SUMMARY_MAX_LENGTH) || 150,
      min_length: parseInt(process.env.SUMMARY_MIN_LENGTH) || 50,
      enable_abstractive: process.env.ENABLE_ABSTRACTIVE !== 'false'
    }
  },
  
  vectordb: {
    default_provider: process.env.VECTOR_DB_PROVIDER || 'chromadb',
    chromadb: {
      persist_directory: process.env.CHROMADB_PERSIST_DIR || path.join(__dirname, '../../data/chromadb'),
      collection_name: process.env.CHROMADB_COLLECTION || 'documents'
    },
    faiss: {
      index_path: process.env.FAISS_INDEX_PATH || path.join(__dirname, '../../data/faiss'),
      dimension: parseInt(process.env.EMBEDDING_DIMENSION) || 384
    }
  },
  
  language: {
    default_language: process.env.DEFAULT_LANGUAGE || 'en',
    enable_translation: process.env.ENABLE_TRANSLATION !== 'false',
    translation_provider: process.env.TRANSLATION_PROVIDER || 'google'
  },
  
  ocr: {
    tesseract_path: process.env.TESSERACT_PATH || 'tesseract',
    languages: process.env.OCR_LANGUAGES || 'eng',
    dpi: parseInt(process.env.OCR_DPI) || 300,
    enhance_images: process.env.OCR_ENHANCE !== 'false'
  },
  
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    file: process.env.LOG_FILE || path.join(__dirname, '../../logs/app.log'),
    max_files: parseInt(process.env.LOG_MAX_FILES) || 5,
    max_size: process.env.LOG_MAX_SIZE || '10m'
  }
};