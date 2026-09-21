# Document AI Service

Advanced document processing and analysis service with AI-powered capabilities.

## Features

- **PDF Text Extraction & OCR**: Extract text using PyPDF2, pdfplumber, and Tesseract OCR
- **Document Classification**: Classify documents as invoices, contracts, resumes, etc.
- **Named Entity Recognition**: Extract people, organizations, dates, amounts, emails, phone numbers
- **Document Summarization**: Generate extractive and abstractive summaries using LLMs
- **Table Extraction**: Extract and structure tables using multiple methods
- **Multi-Language Support**: Process documents in 9+ languages
- **Vector Database Integration**: Semantic search using ChromaDB, Pinecone, or Weaviate

## Installation

1. Install system dependencies:
```bash
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng poppler-utils
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

3. Set environment variables:
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/activelog"
export SERVICE_PORT=8008
```

## Usage

### Start Service
```bash
python run.py
```

### Upload and Process Document
```python
import requests

# Upload
with open('document.pdf', 'rb') as f:
    response = requests.post('http://localhost:8008/documents/upload', files={'file': f})
job_id = response.json()['job_id']

# Process
requests.post(f'http://localhost:8008/documents/{job_id}/process')

# Get results
results = requests.get(f'http://localhost:8008/documents/{job_id}/results')
```

### Semantic Search
```python
response = requests.post('http://localhost:8008/search/semantic', json={
    'query': 'contract terms and conditions',
    'limit': 10
})
```

## API Endpoints

- `POST /documents/upload` - Upload document
- `POST /documents/{job_id}/process` - Start processing
- `GET /documents/{job_id}/results` - Get results
- `POST /search/semantic` - Semantic search
- `POST /search/text` - Text search
- `GET /health` - Health check

## Supported Features

- **Document Types**: invoice, contract, resume, report, letter, financial_statement, legal_document, technical_manual, academic_paper
- **Languages**: English, Spanish, French, German, Italian, Portuguese, Russian, Chinese, Japanese
- **File Formats**: PDF, TXT, DOCX, DOC, RTF, ODT
- **Vector Databases**: ChromaDB, Pinecone, Weaviate