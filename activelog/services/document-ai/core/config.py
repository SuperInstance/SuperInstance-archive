"""
Configuration settings for document AI service
"""

import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings

class DatabaseConfig(BaseModel):
    """Database configuration"""
    url: str = Field(default="postgresql://activeloguser:SecurePass123!@localhost:5432/activelog")
    pool_size: int = Field(default=10)
    max_overflow: int = Field(default=20)

class VectorDatabaseConfig(BaseModel):
    """Vector database configuration"""
    provider: str = Field(default="chroma", description="chroma, pinecone, weaviate")
    chroma_host: str = Field(default="localhost")
    chroma_port: int = Field(default=8000)
    chroma_collection: str = Field(default="documents")
    
    # Pinecone settings
    pinecone_api_key: Optional[str] = None
    pinecone_environment: Optional[str] = None
    pinecone_index: str = Field(default="documents")
    
    # Weaviate settings
    weaviate_url: Optional[str] = None
    weaviate_api_key: Optional[str] = None

class AIModelConfig(BaseModel):
    """AI model configuration"""
    # LLM providers
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    huggingface_api_key: Optional[str] = None
    
    # Local models
    use_local_llm: bool = Field(default=False)
    local_llm_url: str = Field(default="http://localhost:11434")
    local_llm_model: str = Field(default="llama2")
    
    # Embedding models
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    embedding_dimension: int = Field(default=384)
    
    # NER models
    ner_model: str = Field(default="en_core_web_sm")
    multilingual_ner_model: str = Field(default="xx_ent_wiki_sm")

class OCRConfig(BaseModel):
    """OCR configuration"""
    tesseract_cmd: Optional[str] = None
    tesseract_config: str = Field(default='--oem 3 --psm 6')
    supported_languages: List[str] = Field(default=['eng', 'spa', 'fra', 'deu', 'ita', 'por', 'rus', 'chi_sim', 'jpn'])
    confidence_threshold: int = Field(default=30)

class ProcessingConfig(BaseModel):
    """Processing configuration"""
    max_concurrent_jobs: int = Field(default=5)
    max_file_size_mb: int = Field(default=100)
    supported_formats: List[str] = Field(default=['.pdf', '.txt', '.docx', '.doc', '.rtf', '.odt'])
    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=200)

class Settings(BaseSettings):
    """Main settings class"""
    
    # Service configuration
    service_name: str = Field(default="document-ai")
    service_port: int = Field(default=8008)
    debug: bool = Field(default=False)
    
    # API configuration
    api_v1_prefix: str = Field(default="/api/v1")
    
    # Database
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    
    # Vector database
    vector_db: VectorDatabaseConfig = Field(default_factory=VectorDatabaseConfig)
    
    # AI models
    ai_models: AIModelConfig = Field(default_factory=AIModelConfig)
    
    # OCR
    ocr: OCRConfig = Field(default_factory=OCRConfig)
    
    # Processing
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    
    # Storage paths
    temp_dir: str = Field(default="/tmp/document_ai")
    output_dir: str = Field(default="/var/lib/activelog/document_ai")
    
    # Logging
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="/var/log/activelog/document_ai.log")
    
    # Security
    api_key_header: str = Field(default="X-API-Key")
    allowed_origins: List[str] = Field(default=["*"])
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "env_nested_delimiter": "__"
    }
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    @field_validator("service_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not (1024 <= v <= 65535):
            raise ValueError("Port must be between 1024 and 65535")
        return v
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Create directories
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

# Global settings instance
settings = Settings()

# Environment-based overrides
if os.getenv('DATABASE_URL'):
    settings.database.url = os.getenv('DATABASE_URL')

if os.getenv('SERVICE_PORT'):
    settings.service_port = int(os.getenv('SERVICE_PORT'))

if os.getenv('OPENAI_API_KEY'):
    settings.ai_models.openai_api_key = os.getenv('OPENAI_API_KEY')

if os.getenv('ANTHROPIC_API_KEY'):
    settings.ai_models.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')

if os.getenv('HUGGINGFACE_API_KEY'):
    settings.ai_models.huggingface_api_key = os.getenv('HUGGINGFACE_API_KEY')

if os.getenv('PINECONE_API_KEY'):
    settings.vector_db.pinecone_api_key = os.getenv('PINECONE_API_KEY')

if os.getenv('PINECONE_ENVIRONMENT'):
    settings.vector_db.pinecone_environment = os.getenv('PINECONE_ENVIRONMENT')

# Document type configurations
DOCUMENT_TYPES = {
    "invoice": {
        "keywords": ["invoice", "bill", "payment", "due", "amount", "total", "tax", "subtotal"],
        "patterns": [r"\b(invoice|bill)\s*#?\s*\d+", r"\$\d+\.\d{2}", r"\btotal\s*:?\s*\$?\d+"],
        "required_entities": ["MONEY", "DATE", "ORG"]
    },
    "contract": {
        "keywords": ["agreement", "contract", "party", "parties", "terms", "conditions", "obligations"],
        "patterns": [r"\b(agreement|contract)\b", r"\bparty\s+(a|b|1|2)\b", r"\beffective\s+date\b"],
        "required_entities": ["PERSON", "ORG", "DATE"]
    },
    "resume": {
        "keywords": ["resume", "experience", "education", "skills", "employment", "qualifications"],
        "patterns": [r"\b(resume|cv|curriculum vitae)\b", r"\b\d{4}\s*-\s*\d{4}\b", r"\b(bachelor|master|phd)\b"],
        "required_entities": ["PERSON", "DATE", "ORG"]
    },
    "report": {
        "keywords": ["report", "analysis", "findings", "conclusion", "executive summary", "recommendations"],
        "patterns": [r"\b(report|analysis)\b", r"\bexecutive\s+summary\b", r"\bfindings\b"],
        "required_entities": ["DATE", "PERCENT", "CARDINAL"]
    },
    "letter": {
        "keywords": ["dear", "sincerely", "regards", "yours", "letter", "correspondence"],
        "patterns": [r"\bdear\s+\w+", r"\b(sincerely|regards|yours)\b", r"\bdate\s*:"],
        "required_entities": ["PERSON", "DATE"]
    },
    "financial_statement": {
        "keywords": ["balance sheet", "income statement", "cash flow", "assets", "liabilities", "equity"],
        "patterns": [r"\b(assets|liabilities|equity)\b", r"\$\d+", r"\b(revenue|expenses|profit)\b"],
        "required_entities": ["MONEY", "DATE", "PERCENT"]
    },
    "legal_document": {
        "keywords": ["whereas", "therefore", "plaintiff", "defendant", "court", "jurisdiction"],
        "patterns": [r"\bwhereas\b", r"\btherefore\b", r"\bcourt\s+of\b"],
        "required_entities": ["PERSON", "ORG", "DATE", "GPE"]
    },
    "technical_manual": {
        "keywords": ["manual", "instructions", "procedure", "step", "requirements", "specifications"],
        "patterns": [r"\bmanual\b", r"\bstep\s+\d+", r"\bprocedure\b"],
        "required_entities": ["CARDINAL", "DATE"]
    },
    "academic_paper": {
        "keywords": ["abstract", "methodology", "results", "conclusion", "references", "bibliography"],
        "patterns": [r"\babstract\b", r"\bmethodology\b", r"\breferences\b"],
        "required_entities": ["PERSON", "DATE", "ORG"]
    },
    "other": {
        "keywords": [],
        "patterns": [],
        "required_entities": []
    }
}

# Language configurations
LANGUAGE_CONFIGS = {
    "en": {
        "name": "English",
        "tesseract_code": "eng",
        "spacy_model": "en_core_web_sm",
        "iso_code": "en"
    },
    "es": {
        "name": "Spanish", 
        "tesseract_code": "spa",
        "spacy_model": "es_core_news_sm",
        "iso_code": "es"
    },
    "fr": {
        "name": "French",
        "tesseract_code": "fra", 
        "spacy_model": "fr_core_news_sm",
        "iso_code": "fr"
    },
    "de": {
        "name": "German",
        "tesseract_code": "deu",
        "spacy_model": "de_core_news_sm", 
        "iso_code": "de"
    },
    "it": {
        "name": "Italian",
        "tesseract_code": "ita",
        "spacy_model": "it_core_news_sm",
        "iso_code": "it"
    },
    "pt": {
        "name": "Portuguese",
        "tesseract_code": "por",
        "spacy_model": "pt_core_news_sm",
        "iso_code": "pt" 
    },
    "ru": {
        "name": "Russian",
        "tesseract_code": "rus",
        "spacy_model": "ru_core_news_sm",
        "iso_code": "ru"
    },
    "zh": {
        "name": "Chinese",
        "tesseract_code": "chi_sim",
        "spacy_model": "zh_core_web_sm",
        "iso_code": "zh"
    },
    "ja": {
        "name": "Japanese", 
        "tesseract_code": "jpn",
        "spacy_model": "ja_core_news_sm",
        "iso_code": "ja"
    }
}