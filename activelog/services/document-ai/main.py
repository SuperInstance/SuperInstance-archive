"""
FastAPI main application for document AI service
"""

import os
import asyncio
import logging
import hashlib
import tempfile
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from datetime import datetime
import aiofiles
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Query, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.config import settings, DOCUMENT_TYPES, LANGUAGE_CONFIGS
from core.database import DatabaseManager
from core.logging import setup_logging
from models.document_models import *
from extractors.text_extractor import TextExtractor
from classifiers.document_classifier import DocumentClassifier
from processors.ner_processor import NERProcessor
from processors.summarization_processor import SummarizationProcessor
from processors.table_extractor import TableExtractor
from vector_db.vector_manager import VectorDatabaseManager

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

# Global instances
db_manager = None
text_extractor = None
document_classifier = None
ner_processor = None
summarization_processor = None
table_extractor = None
vector_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global db_manager, text_extractor, document_classifier, ner_processor
    global summarization_processor, table_extractor, vector_manager
    
    try:
        logger.info("Starting document AI service...")
        
        # Initialize database
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Initialize processors
        text_extractor = TextExtractor(db_manager)
        document_classifier = DocumentClassifier(db_manager)
        ner_processor = NERProcessor(db_manager)
        summarization_processor = SummarizationProcessor(db_manager)
        table_extractor = TableExtractor(db_manager)
        vector_manager = VectorDatabaseManager(db_manager)
        
        logger.info("Document AI service started successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start document AI service: {str(e)}")
        raise
    
    finally:
        logger.info("Shutting down document AI service...")
        
        # Close database connections
        if db_manager:
            await db_manager.close()
        
        logger.info("Document AI service stopped")

# Create FastAPI application
app = FastAPI(
    title="Document AI Service",
    description="Advanced document processing and analysis with AI",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility functions
def calculate_file_hash(content: bytes) -> str:
    """Calculate SHA-256 hash of file content"""
    return hashlib.sha256(content).hexdigest()

async def detect_document_language(text: str) -> str:
    """Simple language detection (could be enhanced with langdetect library)"""
    
    # For now, return English as default
    # In production, you'd use a proper language detection library
    return "en"

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    
    try:
        db_healthy = await db_manager.health_check() if db_manager else False
        
        # Check vector database
        vector_healthy = True
        try:
            if vector_manager:
                await vector_manager.get_collection_stats()
        except Exception:
            vector_healthy = False
        
        status = "healthy" if (db_healthy and vector_healthy) else "degraded"
        
        return {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "database": "healthy" if db_healthy else "unhealthy",
            "vector_database": "healthy" if vector_healthy else "unhealthy",
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "version": "1.0.0"
        }

# Document upload endpoint
@app.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Form(default="default"),
    tenant_id: str = Form(default="default")
):
    """Upload a document for processing"""
    
    try:
        # Validate file type
        if not file.content_type:
            raise HTTPException(status_code=400, detail="Unable to determine file type")
        
        # Check file size
        content = await file.read()
        file_size = len(content)
        
        max_size = settings.processing.max_file_size_mb * 1024 * 1024
        if file_size > max_size:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size: {settings.processing.max_file_size_mb}MB"
            )
        
        # Check file format
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in settings.processing.supported_formats:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format. Supported: {settings.processing.supported_formats}"
            )
        
        # Calculate file hash for deduplication
        file_hash = calculate_file_hash(content)
        
        # Check if file already exists
        existing_jobs = await db_manager.execute_query("""
            SELECT job_id, status FROM document_processing_jobs 
            WHERE file_hash = $1 AND user_id = $2
            ORDER BY created_at DESC LIMIT 1
        """, file_hash, user_id)
        
        if existing_jobs:
            existing_job = existing_jobs[0]
            if existing_job['status'] == 'completed':
                return DocumentUploadResponse(
                    job_id=existing_job['job_id'],
                    filename=file.filename,
                    file_size=file_size,
                    file_hash=file_hash,
                    status=DocumentStatus.COMPLETED,
                    message="File already processed (duplicate detected)"
                )
        
        # Save uploaded file
        upload_dir = Path(settings.temp_dir) / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / f"{file_hash}_{file.filename}"
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Create processing job
        job_id = await db_manager.create_document_job(
            user_id=user_id,
            tenant_id=tenant_id,
            filename=file.filename,
            file_path=str(file_path),
            file_size=file_size,
            mime_type=file.content_type,
            file_hash=file_hash
        )
        
        logger.info(f"Document uploaded: {file.filename} (Job: {job_id})")
        
        return DocumentUploadResponse(
            job_id=job_id,
            filename=file.filename,
            file_size=file_size,
            file_hash=file_hash,
            status=DocumentStatus.PENDING,
            message="Document uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Document processing endpoint
@app.post("/documents/{job_id}/process")
async def process_document(
    job_id: str,
    background_tasks: BackgroundTasks,
    processing_options: DocumentProcessingRequest = DocumentProcessingRequest()
):
    """Start document processing for an uploaded document"""
    
    try:
        # Get job details
        job = await db_manager.get_job_details(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job['status'] not in ['pending', 'failed']:
            raise HTTPException(status_code=400, detail=f"Job already {job['status']}")
        
        # Start processing in background
        background_tasks.add_task(
            _process_document_background, 
            job_id, 
            job['file_path'],
            processing_options.processing_options
        )
        
        # Mark job as started
        await db_manager.start_job(job_id)
        
        return DocumentProcessingResponse(
            job_id=job_id,
            status=DocumentStatus.PROCESSING,
            message="Document processing started"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start document processing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def _process_document_background(job_id: str, file_path: str, 
                                     options: ProcessingOptions):
    """Background document processing task"""
    
    try:
        logger.info(f"Starting background processing for job {job_id}")
        
        # Step 1: Text extraction and OCR (20%)
        if options.extract_text:
            await db_manager.update_job_progress(job_id, 10)
            
            extracted_text_results = await text_extractor.extract_text_from_document(
                job_id, file_path, options.languages
            )
            
            # Get full text content
            full_text = ""
            page_texts = []
            
            for page_data in extracted_text_results.get('extracted_pages', []):
                full_text += page_data['cleaned_text'] + "\n"
                page_texts.append(page_data)
            
            await db_manager.update_job_progress(job_id, 20)
        else:
            full_text = ""
            page_texts = []
        
        # Step 2: Language detection
        if full_text:
            detected_language = await detect_document_language(full_text)
            if detected_language not in options.languages:
                options.languages.append(detected_language)
        
        # Step 3: Document classification (40%)
        if options.classify_document and full_text:
            classifications = await document_classifier.classify_document(
                job_id, full_text, {"file_path": file_path}
            )
            await db_manager.update_job_progress(job_id, 40)
        
        # Step 4: Named entity extraction (60%)
        if options.extract_entities and full_text:
            entities = await ner_processor.extract_entities(
                job_id, full_text, page_texts, 
                options.languages[0] if options.languages else 'en'
            )
            await db_manager.update_job_progress(job_id, 60)
        
        # Step 5: Table extraction (70%)
        if options.extract_tables:
            tables = await table_extractor.extract_tables_from_document(
                job_id, file_path, page_texts
            )
            await db_manager.update_job_progress(job_id, 70)
        
        # Step 6: Document summarization (85%)
        if options.generate_summary and full_text:
            # Determine document type for context-aware summarization
            doc_type = "other"
            if options.classify_document:
                try:
                    latest_classifications = await db_manager.get_job_classifications(job_id)
                    if latest_classifications:
                        doc_type = latest_classifications[0]['document_type']
                except:
                    pass
            
            summaries = await summarization_processor.generate_summaries(
                job_id, full_text, doc_type, options.summary_types
            )
            await db_manager.update_job_progress(job_id, 85)
        
        # Step 7: Vector embeddings for semantic search (95%)
        if options.create_embeddings and full_text:
            embeddings = await vector_manager.create_document_embeddings(
                job_id, full_text, page_texts
            )
            await db_manager.update_job_progress(job_id, 95)
        
        # Step 8: Save document metadata
        word_count = len(full_text.split()) if full_text else 0
        char_count = len(full_text) if full_text else 0
        
        # Get document type from classification
        document_type = "other"
        confidence_score = 0.0
        
        try:
            classifications = await db_manager.get_job_classifications(job_id)
            if classifications:
                document_type = classifications[0]['document_type']
                confidence_score = classifications[0]['confidence_score']
        except:
            pass
        
        metadata = {
            'page_count': len(page_texts) if page_texts else 1,
            'word_count': word_count,
            'character_count': char_count,
            'language': options.languages[0] if options.languages else 'en',
            'detected_languages': {lang: 1.0 for lang in options.languages},
            'document_type': document_type,
            'confidence_score': confidence_score
        }
        
        await db_manager.save_document_metadata(job_id, metadata)
        
        # Final completion (100%)
        await db_manager.update_job_status(job_id, 'completed', 100, None, {
            'processing_options': options.dict(),
            'completed_at': datetime.utcnow().isoformat(),
            'metadata': metadata
        })
        
        logger.info(f"Document processing completed for job {job_id}")
        
    except Exception as e:
        logger.error(f"Document processing failed for job {job_id}: {str(e)}")
        await db_manager.update_job_status(job_id, 'failed', None, str(e))

# Job status endpoint
@app.get("/documents/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get processing job status"""
    
    try:
        job = await db_manager.get_job_details(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get metadata if available
        metadata = None
        try:
            metadata_dict = await db_manager.get_job_metadata(job_id)
            if metadata_dict:
                metadata = DocumentMetadata(**metadata_dict)
        except:
            pass
        
        return JobStatusResponse(
            job_id=job_id,
            status=DocumentStatus(job['status']),
            progress=job['progress'],
            start_time=job['start_time'],
            end_time=job['end_time'],
            error_message=job['error_message'],
            metadata=metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Get processing results
@app.get("/documents/{job_id}/results", response_model=DocumentProcessingResults)
async def get_job_results(job_id: str):
    """Get complete processing results for a job"""
    
    try:
        job = await db_manager.get_job_details(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get document metadata
        metadata_dict = await db_manager.get_job_metadata(job_id)
        if not metadata_dict:
            raise HTTPException(status_code=404, detail="Document metadata not found")
        
        document_info = DocumentMetadata(**metadata_dict)
        
        # Get all processing results
        classifications_data = await db_manager.get_job_classifications(job_id)
        classifications = [
            DocumentClassification(**cls) for cls in classifications_data
        ]
        
        extracted_text_data = await db_manager.get_job_extracted_text(job_id)
        extracted_text = [
            ExtractedText(
                text_id=str(text['text_id']),
                job_id=text['job_id'],
                page_number=text['page_number'],
                extraction_method=ExtractionMethod(text['extraction_method']),
                raw_text=text['raw_text'],
                cleaned_text=text['cleaned_text'],
                confidence_score=text['confidence_score'],
                language=text['language'],
                word_count=text['word_count'],
                bounding_boxes=[BoundingBox(**bbox) for bbox in text.get('bounding_boxes', [])],
                created_at=text['created_at']
            ) for text in extracted_text_data
        ]
        
        entities_data = await db_manager.get_job_entities(job_id)
        named_entities = [
            NamedEntity(
                entity_id=str(entity['entity_id']),
                job_id=entity['job_id'],
                entity_text=entity['entity_text'],
                entity_type=EntityType(entity['entity_type']),
                start_position=entity['start_position'],
                end_position=entity['end_position'],
                confidence_score=entity['confidence_score'],
                page_number=entity['page_number'],
                context_text=entity['context_text'],
                normalized_value=entity['normalized_value'],
                created_at=entity['created_at']
            ) for entity in entities_data
        ]
        
        summaries_data = await db_manager.get_job_summaries(job_id)
        summaries = [
            DocumentSummary(
                summary_id=str(summary['summary_id']),
                job_id=summary['job_id'],
                summary_type=SummaryType(summary['summary_type']),
                summary_text=summary['summary_text'],
                key_points=summary.get('key_points', []),
                word_count=summary['word_count'],
                compression_ratio=summary.get('compression_ratio'),
                model_used=summary.get('model_used'),
                created_at=summary['created_at']
            ) for summary in summaries_data
        ]
        
        tables_data = await db_manager.get_job_tables(job_id)
        tables = [
            ExtractedTable(
                table_id=str(table['table_id']),
                job_id=table['job_id'],
                page_number=table['page_number'],
                table_index=table['table_index'],
                extraction_method=table['extraction_method'],
                raw_table_data=table['raw_table_data'],
                structured_data=table['structured_data'],
                column_headers=table.get('column_headers', []),
                row_count=table['row_count'],
                column_count=table['column_count'],
                confidence_score=table.get('confidence_score'),
                bounding_box=BoundingBox(**table['bounding_box']) if table.get('bounding_box') else None,
                cells=[],  # Would need to reconstruct from structured_data
                created_at=table['created_at']
            ) for table in tables_data
        ]
        
        # Count embeddings
        embeddings_count = 0
        try:
            embeddings_data = await db_manager.execute_query("""
                SELECT COUNT(*) as count FROM document_embeddings WHERE job_id = $1
            """, job_id)
            if embeddings_data:
                embeddings_count = embeddings_data[0]['count']
        except:
            pass
        
        return DocumentProcessingResults(
            job_id=job_id,
            status=DocumentStatus(job['status']),
            document_info=document_info,
            classifications=classifications,
            extracted_text=extracted_text,
            named_entities=named_entities,
            summaries=summaries,
            tables=tables,
            embeddings_count=embeddings_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Search endpoints
@app.post("/search/semantic", response_model=SemanticSearchResponse)
async def semantic_search(search_request: SearchRequest):
    """Perform semantic search across documents"""
    
    try:
        start_time = datetime.utcnow()
        
        if not vector_manager:
            raise HTTPException(status_code=503, detail="Vector database not available")
        
        # Perform semantic search
        results = await vector_manager.semantic_search(
            query=search_request.query,
            limit=search_request.limit,
            similarity_threshold=search_request.similarity_threshold
        )
        
        # Apply additional filters
        if search_request.document_types:
            doc_type_values = [dt.value for dt in search_request.document_types]
            results = [r for r in results if r.document_type in doc_type_values]
        
        search_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return SemanticSearchResponse(
            query=search_request.query,
            total_results=len(results),
            results=results,
            search_time_ms=search_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Semantic search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search/text", response_model=TextSearchResponse)
async def text_search(search_request: SearchRequest):
    """Perform text-based search across documents"""
    
    try:
        start_time = datetime.utcnow()
        
        # Search in extracted text
        results = await db_manager.search_documents_by_content(
            query=search_request.query,
            document_type=search_request.document_types[0].value if search_request.document_types else None,
            limit=search_request.limit
        )
        
        search_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return TextSearchResponse(
            query=search_request.query,
            total_results=len(results),
            results=results,
            search_time_ms=search_time
        )
        
    except Exception as e:
        logger.error(f"Text search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search/entities", response_model=EntitySearchResponse)
async def entity_search(search_request: EntitySearchRequest):
    """Search named entities across documents"""
    
    try:
        results = await db_manager.search_entities(
            entity_text=search_request.entity_text,
            entity_type=search_request.entity_type.value if search_request.entity_type else None,
            limit=search_request.limit
        )
        
        entities = [
            NamedEntity(
                entity_id=str(entity['entity_id']),
                job_id=entity['job_id'],
                entity_text=entity['entity_text'],
                entity_type=EntityType(entity['entity_type']),
                start_position=entity['start_position'],
                end_position=entity['end_position'],
                confidence_score=entity['confidence_score'],
                page_number=entity['page_number'],
                context_text=entity['context_text'],
                normalized_value=entity['normalized_value'],
                created_at=entity['created_at']
            ) for entity in results
        ]
        
        return EntitySearchResponse(
            total_results=len(entities),
            results=entities
        )
        
    except Exception as e:
        logger.error(f"Entity search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Analytics endpoint
@app.get("/analytics", response_model=DocumentAnalytics)
async def get_analytics():
    """Get document processing analytics"""
    
    try:
        # Get processing statistics
        stats = await db_manager.get_processing_statistics()
        
        # Count totals
        total_documents = 0
        if stats.get('jobs'):
            total_documents = sum(job['count'] for job in stats['jobs'])
        
        # Document types
        documents_by_type = {}
        if stats.get('document_types'):
            documents_by_type = {
                doc_type['document_type']: doc_type['count']
                for doc_type in stats['document_types']
            }
        
        # Languages (simplified)
        documents_by_language = {'en': total_documents}  # Placeholder
        
        # Entity statistics
        entity_stats = await db_manager.execute_query("""
            SELECT entity_type, COUNT(*) as count
            FROM named_entities ne
            JOIN document_processing_jobs dpj ON ne.job_id = dpj.job_id
            WHERE dpj.created_at >= NOW() - INTERVAL '30 days'
            GROUP BY entity_type
            ORDER BY count DESC
        """)
        
        entity_statistics = {
            entity['entity_type']: entity['count']
            for entity in entity_stats
        }
        
        # Confidence scores
        confidence_stats = await db_manager.execute_query("""
            SELECT 
                'classification' as type,
                AVG(confidence_score) as avg_confidence
            FROM document_classifications
            UNION ALL
            SELECT 
                'entities' as type,
                AVG(confidence_score) as avg_confidence
            FROM named_entities
            WHERE confidence_score IS NOT NULL
        """)
        
        average_confidence_scores = {
            conf['type']: float(conf['avg_confidence']) if conf['avg_confidence'] else 0.0
            for conf in confidence_stats
        }
        
        return DocumentAnalytics(
            total_documents=total_documents,
            documents_by_type=documents_by_type,
            documents_by_language=documents_by_language,
            processing_statistics=stats,
            entity_statistics=entity_statistics,
            average_confidence_scores=average_confidence_scores
        )
        
    except Exception as e:
        logger.error(f"Failed to get analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Configuration endpoints
@app.get("/config/document-types")
async def get_document_types():
    """Get available document types and their configurations"""
    return {
        "document_types": list(DOCUMENT_TYPES.keys()),
        "configurations": DOCUMENT_TYPES
    }

@app.get("/config/languages")
async def get_supported_languages():
    """Get supported languages"""
    return {
        "languages": LANGUAGE_CONFIGS,
        "ocr_languages": settings.ocr.supported_languages
    }

@app.get("/config/processing-options")
async def get_processing_options():
    """Get available processing options"""
    return {
        "summary_types": [st.value for st in SummaryType],
        "entity_types": [et.value for et in EntityType],
        "extraction_methods": [em.value for em in ExtractionMethod],
        "max_file_size_mb": settings.processing.max_file_size_mb,
        "supported_formats": settings.processing.supported_formats,
        "chunk_size": settings.processing.chunk_size
    }

if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.debug,
        log_config=None  # We handle logging ourselves
    )