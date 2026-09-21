"""
Text extraction from documents using multiple methods
"""

import os
import tempfile
import fitz  # PyMuPDF
import PyPDF2
import pytesseract
import pdfplumber
import docx
import zipfile
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import io
import base64

from ..core.config import settings, LANGUAGE_CONFIGS
from ..core.database import DatabaseManager
from ..models.document_models import ExtractedText, ExtractionMethod, BoundingBox

ocr_logger = logging.getLogger('ocr')

class TextExtractor:
    """Advanced text extraction from various document formats"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.executor = ThreadPoolExecutor(max_workers=settings.processing.max_concurrent_jobs)
        
        # OCR configuration
        self.tesseract_config = settings.ocr.tesseract_config
        self.confidence_threshold = settings.ocr.confidence_threshold
        
        # Set Tesseract command path if specified
        if settings.ocr.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = settings.ocr.tesseract_cmd
    
    async def extract_text_from_document(self, job_id: str, file_path: str, 
                                       languages: List[str] = None) -> Dict[str, Any]:
        """
        Extract text from document using the best available method
        
        Args:
            job_id: Processing job ID
            file_path: Path to document file
            languages: List of expected languages for OCR
            
        Returns:
            Dictionary containing extraction results
        """
        if languages is None:
            languages = ["en"]
        
        try:
            ocr_logger.info(f"Starting text extraction for job {job_id}: {file_path}")
            
            # Determine file type
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Initialize results
            results = {
                'job_id': job_id,
                'file_path': file_path,
                'extracted_pages': [],
                'total_pages': 0,
                'total_words': 0,
                'languages': languages,
                'extraction_methods': [],
                'confidence_scores': []
            }
            
            # Extract based on file type
            if file_ext == '.pdf':
                results = await self._extract_from_pdf(job_id, file_path, languages)
            elif file_ext in ['.docx', '.doc']:
                results = await self._extract_from_docx(job_id, file_path, languages)
            elif file_ext == '.txt':
                results = await self._extract_from_txt(job_id, file_path, languages)
            elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                results = await self._extract_from_image(job_id, file_path, languages)
            else:
                # Try PDF extraction as fallback
                results = await self._extract_from_pdf(job_id, file_path, languages)
            
            # Save results to database
            await self._save_extraction_results(job_id, results)
            
            ocr_logger.info(f"Text extraction completed for job {job_id}: {results['total_pages']} pages, {results['total_words']} words")
            return results
            
        except Exception as e:
            ocr_logger.error(f"Text extraction failed for job {job_id}: {str(e)}")
            raise
    
    async def _extract_from_pdf(self, job_id: str, file_path: str, 
                              languages: List[str]) -> Dict[str, Any]:
        """Extract text from PDF using multiple methods"""
        
        results = {
            'job_id': job_id,
            'file_path': file_path,
            'extracted_pages': [],
            'total_pages': 0,
            'total_words': 0,
            'languages': languages,
            'extraction_methods': [],
            'confidence_scores': []
        }
        
        try:
            # Method 1: Try PyMuPDF (fastest for text-based PDFs)
            fitz_results = await self._extract_pdf_with_fitz(file_path, languages)
            
            # Method 2: Try pdfplumber (better for complex layouts)
            plumber_results = await self._extract_pdf_with_plumber(file_path, languages)
            
            # Method 3: OCR fallback for image-based PDFs
            ocr_results = None
            
            # Decide which results to use based on text quality
            best_results = self._choose_best_extraction(fitz_results, plumber_results, ocr_results)
            
            # If extracted text is insufficient, use OCR
            if self._needs_ocr(best_results):
                ocr_logger.info(f"Text quality insufficient, applying OCR to job {job_id}")
                ocr_results = await self._extract_pdf_with_ocr(file_path, languages)
                best_results = self._merge_extraction_results(best_results, ocr_results)
            
            results.update(best_results)
            
        except Exception as e:
            ocr_logger.error(f"PDF extraction failed: {str(e)}")
            # Fallback to OCR
            try:
                ocr_results = await self._extract_pdf_with_ocr(file_path, languages)
                results.update(ocr_results)
            except Exception as ocr_error:
                ocr_logger.error(f"OCR fallback failed: {str(ocr_error)}")
                raise
        
        return results
    
    async def _extract_pdf_with_fitz(self, file_path: str, 
                                   languages: List[str]) -> Dict[str, Any]:
        """Extract text using PyMuPDF (fitz)"""
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self._fitz_extraction_sync, file_path, languages
        )
    
    def _fitz_extraction_sync(self, file_path: str, languages: List[str]) -> Dict[str, Any]:
        """Synchronous PyMuPDF extraction"""
        
        results = {
            'extracted_pages': [],
            'total_pages': 0,
            'total_words': 0,
            'extraction_methods': ['pymupdf'],
            'confidence_scores': []
        }
        
        try:
            doc = fitz.open(file_path)
            results['total_pages'] = doc.page_count
            
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                
                # Extract text
                text = page.get_text()
                
                # Extract text with positions
                text_dict = page.get_text("dict")
                blocks = text_dict.get("blocks", [])
                
                # Process text blocks to get bounding boxes
                bounding_boxes = []
                word_count = 0
                
                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line.get("spans", []):
                                if span.get("text", "").strip():
                                    bbox = BoundingBox(
                                        x=span["bbox"][0],
                                        y=span["bbox"][1],
                                        width=span["bbox"][2] - span["bbox"][0],
                                        height=span["bbox"][3] - span["bbox"][1],
                                        page_number=page_num + 1
                                    )
                                    bounding_boxes.append(bbox)
                                    word_count += len(span["text"].split())
                
                # Clean text
                cleaned_text = self._clean_text(text)
                
                page_result = {
                    'page_number': page_num + 1,
                    'raw_text': text,
                    'cleaned_text': cleaned_text,
                    'word_count': word_count,
                    'confidence_score': 0.95,  # High confidence for native text
                    'extraction_method': ExtractionMethod.PYPDF2,
                    'language': languages[0] if languages else 'en',
                    'bounding_boxes': bounding_boxes
                }
                
                results['extracted_pages'].append(page_result)
                results['total_words'] += word_count
                results['confidence_scores'].append(0.95)
            
            doc.close()
            
        except Exception as e:
            ocr_logger.warning(f"PyMuPDF extraction failed: {str(e)}")
            raise
        
        return results
    
    async def _extract_pdf_with_plumber(self, file_path: str, 
                                      languages: List[str]) -> Dict[str, Any]:
        """Extract text using pdfplumber"""
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self._plumber_extraction_sync, file_path, languages
        )
    
    def _plumber_extraction_sync(self, file_path: str, languages: List[str]) -> Dict[str, Any]:
        """Synchronous pdfplumber extraction"""
        
        results = {
            'extracted_pages': [],
            'total_pages': 0,
            'total_words': 0,
            'extraction_methods': ['pdfplumber'],
            'confidence_scores': []
        }
        
        try:
            with pdfplumber.open(file_path) as pdf:
                results['total_pages'] = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages):
                    # Extract text
                    text = page.extract_text() or ""
                    
                    # Extract words with positions
                    words = page.extract_words()
                    bounding_boxes = []
                    
                    for word_data in words:
                        bbox = BoundingBox(
                            x=word_data['x0'],
                            y=word_data['top'],
                            width=word_data['x1'] - word_data['x0'],
                            height=word_data['bottom'] - word_data['top'],
                            page_number=page_num + 1
                        )
                        bounding_boxes.append(bbox)
                    
                    # Clean text
                    cleaned_text = self._clean_text(text)
                    word_count = len(cleaned_text.split()) if cleaned_text else 0
                    
                    page_result = {
                        'page_number': page_num + 1,
                        'raw_text': text,
                        'cleaned_text': cleaned_text,
                        'word_count': word_count,
                        'confidence_score': 0.9,  # High confidence for structured extraction
                        'extraction_method': ExtractionMethod.PDFPLUMBER,
                        'language': languages[0] if languages else 'en',
                        'bounding_boxes': bounding_boxes
                    }
                    
                    results['extracted_pages'].append(page_result)
                    results['total_words'] += word_count
                    results['confidence_scores'].append(0.9)
            
        except Exception as e:
            ocr_logger.warning(f"pdfplumber extraction failed: {str(e)}")
            raise
        
        return results
    
    async def _extract_pdf_with_ocr(self, file_path: str, 
                                  languages: List[str]) -> Dict[str, Any]:
        """Extract text using OCR (for image-based PDFs)"""
        
        results = {
            'extracted_pages': [],
            'total_pages': 0,
            'total_words': 0,
            'extraction_methods': ['tesseract'],
            'confidence_scores': []
        }
        
        try:
            # Convert PDF pages to images
            doc = fitz.open(file_path)
            results['total_pages'] = doc.page_count
            
            # Prepare language codes for Tesseract
            tesseract_langs = []
            for lang in languages:
                lang_config = LANGUAGE_CONFIGS.get(lang, LANGUAGE_CONFIGS.get('en'))
                tesseract_langs.append(lang_config['tesseract_code'])
            
            tesseract_lang_param = '+'.join(tesseract_langs)
            
            for page_num in range(doc.page_count):
                try:
                    # Convert page to image
                    page = doc.load_page(page_num)
                    mat = fitz.Matrix(2, 2)  # 2x zoom for better OCR
                    pix = page.get_pixmap(matrix=mat)
                    img_data = pix.tobytes("png")
                    
                    # Process with OCR
                    page_result = await self._ocr_process_image(
                        img_data, page_num + 1, tesseract_lang_param, languages[0] if languages else 'en'
                    )
                    
                    results['extracted_pages'].append(page_result)
                    results['total_words'] += page_result['word_count']
                    results['confidence_scores'].append(page_result['confidence_score'])
                    
                except Exception as e:
                    ocr_logger.warning(f"OCR failed for page {page_num + 1}: {str(e)}")
                    # Add empty page result
                    empty_result = {
                        'page_number': page_num + 1,
                        'raw_text': "",
                        'cleaned_text': "",
                        'word_count': 0,
                        'confidence_score': 0.0,
                        'extraction_method': ExtractionMethod.TESSERACT,
                        'language': languages[0] if languages else 'en',
                        'bounding_boxes': []
                    }
                    results['extracted_pages'].append(empty_result)
                    results['confidence_scores'].append(0.0)
            
            doc.close()
            
        except Exception as e:
            ocr_logger.error(f"PDF OCR extraction failed: {str(e)}")
            raise
        
        return results
    
    async def _extract_from_docx(self, job_id: str, file_path: str, 
                               languages: List[str]) -> Dict[str, Any]:
        """Extract text from DOCX files"""
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self._docx_extraction_sync, file_path, languages
        )
    
    def _docx_extraction_sync(self, file_path: str, languages: List[str]) -> Dict[str, Any]:
        """Synchronous DOCX extraction"""
        
        results = {
            'extracted_pages': [],
            'total_pages': 1,  # DOCX is typically one continuous document
            'total_words': 0,
            'extraction_methods': ['python-docx'],
            'confidence_scores': []
        }
        
        try:
            doc = docx.Document(file_path)
            
            # Extract text from paragraphs
            full_text = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    full_text.append(paragraph.text)
            
            # Extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        full_text.append(' | '.join(row_text))
            
            raw_text = '\n'.join(full_text)
            cleaned_text = self._clean_text(raw_text)
            word_count = len(cleaned_text.split()) if cleaned_text else 0
            
            page_result = {
                'page_number': 1,
                'raw_text': raw_text,
                'cleaned_text': cleaned_text,
                'word_count': word_count,
                'confidence_score': 0.98,  # Very high confidence for structured documents
                'extraction_method': ExtractionMethod.PYPDF2,  # Using generic method enum
                'language': languages[0] if languages else 'en',
                'bounding_boxes': []  # DOCX doesn't have spatial coordinates
            }
            
            results['extracted_pages'].append(page_result)
            results['total_words'] = word_count
            results['confidence_scores'].append(0.98)
            
        except Exception as e:
            ocr_logger.error(f"DOCX extraction failed: {str(e)}")
            raise
        
        return results
    
    async def _extract_from_txt(self, job_id: str, file_path: str, 
                              languages: List[str]) -> Dict[str, Any]:
        """Extract text from plain text files"""
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self._txt_extraction_sync, file_path, languages
        )
    
    def _txt_extraction_sync(self, file_path: str, languages: List[str]) -> Dict[str, Any]:
        """Synchronous text file extraction"""
        
        results = {
            'extracted_pages': [],
            'total_pages': 1,
            'total_words': 0,
            'extraction_methods': ['plain_text'],
            'confidence_scores': []
        }
        
        try:
            # Try different encodings
            encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
            text_content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        text_content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if text_content is None:
                raise Exception("Could not decode text file with any supported encoding")
            
            cleaned_text = self._clean_text(text_content)
            word_count = len(cleaned_text.split()) if cleaned_text else 0
            
            page_result = {
                'page_number': 1,
                'raw_text': text_content,
                'cleaned_text': cleaned_text,
                'word_count': word_count,
                'confidence_score': 1.0,  # Perfect confidence for plain text
                'extraction_method': ExtractionMethod.PYPDF2,  # Using generic method
                'language': languages[0] if languages else 'en',
                'bounding_boxes': []
            }
            
            results['extracted_pages'].append(page_result)
            results['total_words'] = word_count
            results['confidence_scores'].append(1.0)
            
        except Exception as e:
            ocr_logger.error(f"Text file extraction failed: {str(e)}")
            raise
        
        return results
    
    async def _extract_from_image(self, job_id: str, file_path: str, 
                                languages: List[str]) -> Dict[str, Any]:
        """Extract text from image files using OCR"""
        
        results = {
            'extracted_pages': [],
            'total_pages': 1,
            'total_words': 0,
            'extraction_methods': ['tesseract'],
            'confidence_scores': []
        }
        
        try:
            # Prepare language codes for Tesseract
            tesseract_langs = []
            for lang in languages:
                lang_config = LANGUAGE_CONFIGS.get(lang, LANGUAGE_CONFIGS.get('en'))
                tesseract_langs.append(lang_config['tesseract_code'])
            
            tesseract_lang_param = '+'.join(tesseract_langs)
            
            # Read image file
            with open(file_path, 'rb') as f:
                img_data = f.read()
            
            # Process with OCR
            page_result = await self._ocr_process_image(
                img_data, 1, tesseract_lang_param, languages[0] if languages else 'en'
            )
            
            results['extracted_pages'].append(page_result)
            results['total_words'] = page_result['word_count']
            results['confidence_scores'].append(page_result['confidence_score'])
            
        except Exception as e:
            ocr_logger.error(f"Image OCR extraction failed: {str(e)}")
            raise
        
        return results
    
    async def _ocr_process_image(self, img_data: bytes, page_number: int, 
                               tesseract_lang: str, primary_language: str) -> Dict[str, Any]:
        """Process image data with OCR using multiple preprocessing methods"""
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self._ocr_process_sync, img_data, page_number, 
            tesseract_lang, primary_language
        )
    
    def _ocr_process_sync(self, img_data: bytes, page_number: int, 
                         tesseract_lang: str, primary_language: str) -> Dict[str, Any]:
        """Synchronous OCR processing with image preprocessing"""
        
        try:
            # Load image
            image = Image.open(io.BytesIO(img_data))
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Try multiple preprocessing approaches
            preprocessing_methods = [
                self._preprocess_basic,
                self._preprocess_enhanced,
                self._preprocess_denoised
            ]
            
            best_result = None
            best_confidence = 0
            
            for method in preprocessing_methods:
                try:
                    processed_image = method(image)
                    
                    # Run OCR
                    ocr_config = f'{self.tesseract_config} -l {tesseract_lang}'
                    
                    # Get detailed OCR data
                    ocr_data = pytesseract.image_to_data(
                        processed_image, 
                        config=ocr_config,
                        output_type=pytesseract.Output.DICT
                    )
                    
                    # Extract text and bounding boxes
                    full_text = []
                    bounding_boxes = []
                    word_confidences = []
                    
                    for i in range(len(ocr_data['text'])):
                        text = ocr_data['text'][i].strip()
                        confidence = int(ocr_data['conf'][i])
                        
                        if confidence >= self.confidence_threshold and len(text) > 0:
                            full_text.append(text)
                            word_confidences.append(confidence)
                            
                            bbox = BoundingBox(
                                x=float(ocr_data['left'][i]),
                                y=float(ocr_data['top'][i]),
                                width=float(ocr_data['width'][i]),
                                height=float(ocr_data['height'][i]),
                                page_number=page_number
                            )
                            bounding_boxes.append(bbox)
                    
                    # Calculate average confidence
                    avg_confidence = sum(word_confidences) / len(word_confidences) if word_confidences else 0
                    
                    # Combine text
                    raw_text = ' '.join(full_text)
                    cleaned_text = self._clean_text(raw_text)
                    
                    result = {
                        'page_number': page_number,
                        'raw_text': raw_text,
                        'cleaned_text': cleaned_text,
                        'word_count': len(cleaned_text.split()) if cleaned_text else 0,
                        'confidence_score': avg_confidence / 100.0,  # Convert to 0-1 scale
                        'extraction_method': ExtractionMethod.TESSERACT,
                        'language': primary_language,
                        'bounding_boxes': bounding_boxes,
                        'preprocessing_method': method.__name__
                    }
                    
                    # Keep the best result
                    if avg_confidence > best_confidence:
                        best_confidence = avg_confidence
                        best_result = result
                
                except Exception as e:
                    ocr_logger.warning(f"OCR preprocessing method {method.__name__} failed: {str(e)}")
                    continue
            
            if best_result is None:
                # Return empty result if all methods failed
                return {
                    'page_number': page_number,
                    'raw_text': "",
                    'cleaned_text': "",
                    'word_count': 0,
                    'confidence_score': 0.0,
                    'extraction_method': ExtractionMethod.TESSERACT,
                    'language': primary_language,
                    'bounding_boxes': []
                }
            
            return best_result
            
        except Exception as e:
            ocr_logger.error(f"OCR processing failed: {str(e)}")
            raise
    
    def _preprocess_basic(self, image: Image.Image) -> Image.Image:
        """Basic image preprocessing for OCR"""
        # Convert to grayscale
        gray = image.convert('L')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(1.5)
        
        return enhanced
    
    def _preprocess_enhanced(self, image: Image.Image) -> Image.Image:
        """Enhanced image preprocessing with sharpening"""
        # Convert to grayscale
        gray = image.convert('L')
        
        # Enhance contrast and sharpness
        contrast = ImageEnhance.Contrast(gray)
        enhanced = contrast.enhance(1.8)
        
        sharpness = ImageEnhance.Sharpness(enhanced)
        sharpened = sharpness.enhance(2.0)
        
        return sharpened
    
    def _preprocess_denoised(self, image: Image.Image) -> Image.Image:
        """Denoised preprocessing using OpenCV"""
        # Convert PIL to OpenCV format
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        
        # Apply denoising
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        # Convert back to PIL
        return Image.fromarray(enhanced)
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        import re
        
        # Replace multiple spaces/tabs with single space
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Replace multiple newlines with double newline
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Remove leading/trailing whitespace from lines
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Remove very short "lines" that are likely OCR artifacts
        lines = []
        for line in text.split('\n'):
            if len(line.strip()) >= 2 or len(lines) == 0:  # Keep first line even if short
                lines.append(line)
        
        return '\n'.join(lines).strip()
    
    def _choose_best_extraction(self, fitz_results: Dict, plumber_results: Dict, 
                              ocr_results: Optional[Dict]) -> Dict[str, Any]:
        """Choose the best extraction method based on text quality"""
        
        candidates = [fitz_results, plumber_results]
        if ocr_results:
            candidates.append(ocr_results)
        
        # Score each method
        best_score = 0
        best_results = fitz_results
        
        for results in candidates:
            if not results or not results.get('extracted_pages'):
                continue
            
            # Calculate quality score
            total_words = results.get('total_words', 0)
            avg_confidence = sum(results.get('confidence_scores', [0])) / len(results.get('confidence_scores', [1]))
            
            # Prefer methods with more text and higher confidence
            score = (total_words * 0.7) + (avg_confidence * 100 * 0.3)
            
            if score > best_score:
                best_score = score
                best_results = results
        
        return best_results
    
    def _needs_ocr(self, results: Dict[str, Any]) -> bool:
        """Determine if OCR is needed based on extraction results"""
        
        if not results or not results.get('extracted_pages'):
            return True
        
        total_words = results.get('total_words', 0)
        avg_confidence = sum(results.get('confidence_scores', [0])) / len(results.get('confidence_scores', [1]))
        
        # Use OCR if very few words extracted or low confidence
        return total_words < 10 or avg_confidence < 0.5
    
    def _merge_extraction_results(self, primary_results: Dict, ocr_results: Dict) -> Dict[str, Any]:
        """Merge primary extraction with OCR results"""
        
        if not primary_results or not primary_results.get('extracted_pages'):
            return ocr_results
        
        if not ocr_results or not ocr_results.get('extracted_pages'):
            return primary_results
        
        # Merge page by page, preferring OCR for pages with insufficient text
        merged_results = primary_results.copy()
        merged_results['extraction_methods'].extend(ocr_results.get('extraction_methods', []))
        
        ocr_pages = {p['page_number']: p for p in ocr_results['extracted_pages']}
        
        for i, page in enumerate(merged_results['extracted_pages']):
            page_num = page['page_number']
            
            # Use OCR if primary extraction has very few words
            if page['word_count'] < 5 and page_num in ocr_pages:
                ocr_page = ocr_pages[page_num]
                if ocr_page['word_count'] > page['word_count']:
                    merged_results['extracted_pages'][i] = ocr_page
                    merged_results['total_words'] += (ocr_page['word_count'] - page['word_count'])
        
        return merged_results
    
    async def _save_extraction_results(self, job_id: str, results: Dict[str, Any]):
        """Save extraction results to database"""
        
        try:
            for page_data in results.get('extracted_pages', []):
                await self.db_manager.save_extracted_text(
                    job_id=job_id,
                    page_number=page_data['page_number'],
                    method=page_data['extraction_method'].value,
                    raw_text=page_data['raw_text'],
                    cleaned_text=page_data['cleaned_text'],
                    confidence=page_data['confidence_score'],
                    language=page_data['language'],
                    word_count=page_data['word_count'],
                    bounding_boxes=[bbox.dict() for bbox in page_data.get('bounding_boxes', [])]
                )
            
            ocr_logger.info(f"Saved extraction results for job {job_id}")
            
        except Exception as e:
            ocr_logger.error(f"Failed to save extraction results: {str(e)}")
            raise