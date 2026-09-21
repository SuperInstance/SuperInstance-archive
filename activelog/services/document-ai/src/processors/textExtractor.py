#!/usr/bin/env python3
"""
PDF Text Extraction and OCR Processing Module
Supports text extraction from PDFs, images, and scanned documents
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import tempfile
import magic
import chardet

# PDF Processing
import PyPDF2
import fitz  # PyMuPDF
import pdfplumber
from pdf2image import convert_from_path

# OCR and Image Processing
import pytesseract
from PIL import Image
import cv2
import numpy as np

# Document Processing
from docx import Document
import openpyxl
import pandas as pd

# Language Detection
from langdetect import detect, DetectorFactory
DetectorFactory.seed = 0

# Utilities
from datetime import datetime
import uuid

class TextExtractor:
    """Main class for text extraction from various document formats"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.output_dir = self.config.get('output_dir', './output/extracted')
        self.temp_dir = self.config.get('temp_dir', './temp/extraction')
        self.ocr_languages = self.config.get('ocr_languages', ['eng'])
        self.ocr_confidence = self.config.get('ocr_confidence', 30)
        
        # Ensure directories exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def extract_text(self, file_path: str, options: Dict = None) -> Dict:
        """
        Main text extraction method that routes to appropriate processor
        """
        options = options or {}
        session_id = str(uuid.uuid4())
        
        try:
            # Detect file type
            file_type = self._detect_file_type(file_path)
            
            self.logger.info(f"Extracting text from {file_path} (type: {file_type}, session: {session_id})")
            
            # Route to appropriate processor
            if file_type == 'pdf':
                result = self._extract_from_pdf(file_path, options, session_id)
            elif file_type in ['image', 'png', 'jpg', 'jpeg', 'tiff', 'bmp']:
                result = self._extract_from_image(file_path, options, session_id)
            elif file_type == 'docx':
                result = self._extract_from_docx(file_path, options, session_id)
            elif file_type in ['xlsx', 'xls']:
                result = self._extract_from_excel(file_path, options, session_id)
            elif file_type == 'txt':
                result = self._extract_from_text(file_path, options, session_id)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            # Add metadata
            result['session_id'] = session_id
            result['file_path'] = file_path
            result['file_type'] = file_type
            result['timestamp'] = datetime.now().isoformat()
            result['extraction_options'] = options
            
            # Save results
            self._save_extraction_results(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Text extraction failed for {file_path}: {str(e)}")
            return {
                'session_id': session_id,
                'error': str(e),
                'success': False,
                'file_path': file_path
            }
    
    def _detect_file_type(self, file_path: str) -> str:
        """Detect file type using magic numbers and extension"""
        try:
            mime = magic.from_file(file_path, mime=True)
            extension = Path(file_path).suffix.lower()
            
            if mime == 'application/pdf' or extension == '.pdf':
                return 'pdf'
            elif mime.startswith('image/') or extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                return 'image'
            elif mime == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' or extension == '.docx':
                return 'docx'
            elif mime in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel'] or extension in ['.xlsx', '.xls']:
                return 'xlsx'
            elif mime == 'text/plain' or extension == '.txt':
                return 'txt'
            else:
                return 'unknown'
                
        except Exception as e:
            self.logger.warning(f"Could not detect file type for {file_path}: {str(e)}")
            return Path(file_path).suffix.lower().replace('.', '')
    
    def _extract_from_pdf(self, file_path: str, options: Dict, session_id: str) -> Dict:
        """Extract text from PDF using multiple methods"""
        
        result = {
            'success': True,
            'method': 'pdf',
            'pages': [],
            'full_text': '',
            'metadata': {},
            'statistics': {}
        }
        
        try:
            # Method 1: Try PyPDF2 for text-based PDFs
            pypdf_text = self._extract_pdf_pypdf2(file_path)
            
            # Method 2: Try PyMuPDF for better text extraction
            pymupdf_text = self._extract_pdf_pymupdf(file_path)
            
            # Method 3: Try pdfplumber for structured extraction
            pdfplumber_result = self._extract_pdf_pdfplumber(file_path)
            
            # Choose best method based on text quality
            if len(pymupdf_text.strip()) > len(pypdf_text.strip()):
                result['pages'] = pymupdf_text
                result['primary_method'] = 'pymupdf'
            else:
                result['pages'] = pypdf_text
                result['primary_method'] = 'pypdf2'
            
            # If minimal text found, try OCR
            total_text = ''.join([page.get('text', '') for page in result['pages']])
            if len(total_text.strip()) < 100 or options.get('force_ocr', False):
                self.logger.info("Minimal text found, attempting OCR...")
                ocr_result = self._extract_pdf_ocr(file_path, options, session_id)
                result['pages'] = ocr_result['pages']
                result['primary_method'] = 'ocr'
                result['ocr_applied'] = True
            
            # Combine all text
            result['full_text'] = '\n\n'.join([page.get('text', '') for page in result['pages']])
            
            # Add pdfplumber structured data if available
            if pdfplumber_result:
                result['structured_data'] = pdfplumber_result
            
            # Extract metadata
            result['metadata'] = self._extract_pdf_metadata(file_path)
            
            # Calculate statistics
            result['statistics'] = self._calculate_text_statistics(result['full_text'])
            
            return result
            
        except Exception as e:
            self.logger.error(f"PDF extraction failed: {str(e)}")
            result['success'] = False
            result['error'] = str(e)
            return result
    
    def _extract_pdf_pypdf2(self, file_path: str) -> List[Dict]:
        """Extract text using PyPDF2"""
        pages = []
        
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(reader.pages):
                    text = page.extract_text()
                    pages.append({
                        'page_number': page_num + 1,
                        'text': text,
                        'method': 'pypdf2'
                    })
                    
        except Exception as e:
            self.logger.warning(f"PyPDF2 extraction failed: {str(e)}")
            
        return pages
    
    def _extract_pdf_pymupdf(self, file_path: str) -> List[Dict]:
        """Extract text using PyMuPDF (fitz)"""
        pages = []
        
        try:
            doc = fitz.open(file_path)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                
                # Extract additional information
                blocks = page.get_text("dict")
                images = page.get_images()
                
                pages.append({
                    'page_number': page_num + 1,
                    'text': text,
                    'method': 'pymupdf',
                    'blocks': len(blocks.get('blocks', [])),
                    'images': len(images),
                    'char_count': len(text)
                })
                
            doc.close()
            
        except Exception as e:
            self.logger.warning(f"PyMuPDF extraction failed: {str(e)}")
            
        return pages
    
    def _extract_pdf_pdfplumber(self, file_path: str) -> Dict:
        """Extract structured data using pdfplumber"""
        
        try:
            with pdfplumber.open(file_path) as pdf:
                tables = []
                metadata = {
                    'pages': len(pdf.pages),
                    'tables_found': 0
                }
                
                for page_num, page in enumerate(pdf.pages):
                    # Extract tables
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table_num, table in enumerate(page_tables):
                            tables.append({
                                'page': page_num + 1,
                                'table': table_num + 1,
                                'data': table,
                                'rows': len(table),
                                'columns': len(table[0]) if table else 0
                            })
                
                metadata['tables_found'] = len(tables)
                
                return {
                    'tables': tables,
                    'metadata': metadata
                }
                
        except Exception as e:
            self.logger.warning(f"pdfplumber extraction failed: {str(e)}")
            return {}
    
    def _extract_pdf_ocr(self, file_path: str, options: Dict, session_id: str) -> Dict:
        """Extract text using OCR on PDF pages converted to images"""
        
        try:
            # Convert PDF to images
            images = convert_from_path(file_path, dpi=300, fmt='PNG')
            
            pages = []
            for page_num, image in enumerate(images):
                # Save temporary image
                temp_image_path = os.path.join(self.temp_dir, f'{session_id}_page_{page_num + 1}.png')
                image.save(temp_image_path)
                
                # Extract text using OCR
                ocr_result = self._extract_from_image(temp_image_path, options, session_id)
                
                pages.append({
                    'page_number': page_num + 1,
                    'text': ocr_result.get('text', ''),
                    'method': 'ocr',
                    'confidence': ocr_result.get('confidence', 0),
                    'words': ocr_result.get('words', [])
                })
                
                # Clean up temporary file
                try:
                    os.remove(temp_image_path)
                except:
                    pass
            
            return {'pages': pages}
            
        except Exception as e:
            self.logger.error(f"PDF OCR failed: {str(e)}")
            return {'pages': []}
    
    def _extract_from_image(self, file_path: str, options: Dict, session_id: str) -> Dict:
        """Extract text from image using OCR"""
        
        result = {
            'success': True,
            'method': 'ocr',
            'text': '',
            'confidence': 0,
            'words': [],
            'languages': []
        }
        
        try:
            # Preprocess image
            processed_image = self._preprocess_image(file_path, options)
            
            # Configure Tesseract
            custom_config = self._build_tesseract_config(options)
            
            # Extract text
            text = pytesseract.image_to_string(processed_image, config=custom_config)
            result['text'] = text
            
            # Get detailed OCR data
            data = pytesseract.image_to_data(processed_image, config=custom_config, output_type=pytesseract.Output.DICT)
            
            # Process word-level data
            words = []
            confidences = []
            
            for i, word in enumerate(data['text']):
                if word.strip():
                    confidence = int(data['conf'][i])
                    if confidence >= self.ocr_confidence:
                        words.append({
                            'text': word,
                            'confidence': confidence,
                            'bbox': {
                                'left': data['left'][i],
                                'top': data['top'][i],
                                'width': data['width'][i],
                                'height': data['height'][i]
                            }
                        })
                        confidences.append(confidence)
            
            result['words'] = words
            result['confidence'] = sum(confidences) / len(confidences) if confidences else 0
            
            # Detect language
            if text.strip():
                try:
                    detected_lang = detect(text)
                    result['languages'] = [detected_lang]
                except:
                    result['languages'] = ['unknown']
            
            return result
            
        except Exception as e:
            self.logger.error(f"Image OCR failed: {str(e)}")
            result['success'] = False
            result['error'] = str(e)
            return result
    
    def _preprocess_image(self, file_path: str, options: Dict) -> Image.Image:
        """Preprocess image for better OCR results"""
        
        # Load image
        image = Image.open(file_path)
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to OpenCV format for processing
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Apply preprocessing based on options
        if options.get('denoise', True):
            cv_image = cv2.fastNlMeansDenoisingColored(cv_image, None, 10, 10, 7, 21)
        
        if options.get('sharpen', False):
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            cv_image = cv2.filter2D(cv_image, -1, kernel)
        
        if options.get('enhance_contrast', True):
            # Convert to LAB color space
            lab = cv2.cvtColor(cv_image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # Apply CLAHE to L channel
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            l = clahe.apply(l)
            
            # Merge channels and convert back
            lab = cv2.merge([l, a, b])
            cv_image = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        # Convert back to PIL Image
        processed_image = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
        
        # Resize if image is too small
        width, height = processed_image.size
        if width < 300 or height < 300:
            scale_factor = max(300 / width, 300 / height)
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            processed_image = processed_image.resize((new_width, new_height), Image.LANCZOS)
        
        return processed_image
    
    def _build_tesseract_config(self, options: Dict) -> str:
        """Build Tesseract configuration string"""
        
        config_parts = []
        
        # Language configuration
        languages = options.get('languages', self.ocr_languages)
        if languages:
            config_parts.append(f'-l {"+".join(languages)}')
        
        # PSM (Page Segmentation Mode)
        psm = options.get('psm', 3)  # Default: fully automatic page segmentation
        config_parts.append(f'--psm {psm}')
        
        # OEM (OCR Engine Mode)
        oem = options.get('oem', 3)  # Default: both Legacy and LSTM engines
        config_parts.append(f'--oem {oem}')
        
        # Additional configurations
        if options.get('digits_only', False):
            config_parts.append('-c tessedit_char_whitelist=0123456789')
        
        if options.get('preserve_interword_spaces', True):
            config_parts.append('-c preserve_interword_spaces=1')
        
        return ' '.join(config_parts)
    
    def _extract_from_docx(self, file_path: str, options: Dict, session_id: str) -> Dict:
        """Extract text from DOCX files"""
        
        result = {
            'success': True,
            'method': 'docx',
            'text': '',
            'paragraphs': [],
            'tables': [],
            'metadata': {}
        }
        
        try:
            doc = Document(file_path)
            
            # Extract paragraphs
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append({
                        'text': para.text,
                        'style': para.style.name if para.style else None
                    })
            
            result['paragraphs'] = paragraphs
            result['text'] = '\n'.join([p['text'] for p in paragraphs])
            
            # Extract tables
            tables = []
            for table_num, table in enumerate(doc.tables):
                table_data = []
                for row in table.rows:
                    row_data = [cell.text for cell in row.cells]
                    table_data.append(row_data)
                
                tables.append({
                    'table_number': table_num + 1,
                    'data': table_data,
                    'rows': len(table_data),
                    'columns': len(table_data[0]) if table_data else 0
                })
            
            result['tables'] = tables
            
            # Extract metadata
            core_props = doc.core_properties
            result['metadata'] = {
                'author': core_props.author,
                'title': core_props.title,
                'subject': core_props.subject,
                'created': core_props.created.isoformat() if core_props.created else None,
                'modified': core_props.modified.isoformat() if core_props.modified else None
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"DOCX extraction failed: {str(e)}")
            result['success'] = False
            result['error'] = str(e)
            return result
    
    def _extract_from_excel(self, file_path: str, options: Dict, session_id: str) -> Dict:
        """Extract text from Excel files"""
        
        result = {
            'success': True,
            'method': 'excel',
            'text': '',
            'sheets': [],
            'metadata': {}
        }
        
        try:
            # Read Excel file
            excel_file = pd.ExcelFile(file_path)
            
            sheets = []
            all_text = []
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # Convert DataFrame to text
                sheet_text = df.to_string(index=False)
                all_text.append(f"Sheet: {sheet_name}\n{sheet_text}")
                
                sheets.append({
                    'name': sheet_name,
                    'text': sheet_text,
                    'rows': len(df),
                    'columns': len(df.columns),
                    'data': df.to_dict('records') if len(df) <= 1000 else None  # Limit data size
                })
            
            result['sheets'] = sheets
            result['text'] = '\n\n'.join(all_text)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Excel extraction failed: {str(e)}")
            result['success'] = False
            result['error'] = str(e)
            return result
    
    def _extract_from_text(self, file_path: str, options: Dict, session_id: str) -> Dict:
        """Extract text from plain text files"""
        
        result = {
            'success': True,
            'method': 'text',
            'text': '',
            'encoding': 'utf-8',
            'metadata': {}
        }
        
        try:
            # Detect encoding
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                encoding_result = chardet.detect(raw_data)
                encoding = encoding_result['encoding'] or 'utf-8'
            
            # Read text file
            with open(file_path, 'r', encoding=encoding) as f:
                text = f.read()
            
            result['text'] = text
            result['encoding'] = encoding
            result['metadata'] = {
                'file_size': os.path.getsize(file_path),
                'line_count': len(text.split('\n')),
                'word_count': len(text.split())
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Text extraction failed: {str(e)}")
            result['success'] = False
            result['error'] = str(e)
            return result
    
    def _extract_pdf_metadata(self, file_path: str) -> Dict:
        """Extract metadata from PDF"""
        
        metadata = {}
        
        try:
            # Using PyPDF2
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                if reader.metadata:
                    metadata.update({
                        'title': reader.metadata.get('/Title'),
                        'author': reader.metadata.get('/Author'),
                        'subject': reader.metadata.get('/Subject'),
                        'creator': reader.metadata.get('/Creator'),
                        'producer': reader.metadata.get('/Producer'),
                        'creation_date': reader.metadata.get('/CreationDate'),
                        'modification_date': reader.metadata.get('/ModDate')
                    })
                
                metadata['page_count'] = len(reader.pages)
                metadata['encrypted'] = reader.is_encrypted
            
            # Using PyMuPDF for additional metadata
            try:
                doc = fitz.open(file_path)
                pymupdf_metadata = doc.metadata
                metadata.update(pymupdf_metadata)
                doc.close()
            except:
                pass
                
        except Exception as e:
            self.logger.warning(f"Metadata extraction failed: {str(e)}")
        
        return metadata
    
    def _calculate_text_statistics(self, text: str) -> Dict:
        """Calculate text statistics"""
        
        if not text:
            return {
                'character_count': 0,
                'word_count': 0,
                'paragraph_count': 0,
                'line_count': 0,
                'avg_words_per_sentence': 0
            }
        
        words = text.split()
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        lines = text.split('\n')
        sentences = [s for s in text.replace('!', '.').replace('?', '.').split('.') if s.strip()]
        
        return {
            'character_count': len(text),
            'word_count': len(words),
            'paragraph_count': len(paragraphs),
            'line_count': len(lines),
            'sentence_count': len(sentences),
            'avg_words_per_sentence': len(words) / len(sentences) if sentences else 0,
            'avg_chars_per_word': len(text) / len(words) if words else 0
        }
    
    def _save_extraction_results(self, result: Dict):
        """Save extraction results to file"""
        
        try:
            output_file = os.path.join(
                self.output_dir, 
                f"extraction_{result['session_id']}.json"
            )
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Extraction results saved to {output_file}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save extraction results: {str(e)}")

def main():
    """Command line interface for text extraction"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract text from documents')
    parser.add_argument('file_path', help='Path to the document file')
    parser.add_argument('--output-dir', default='./output/extracted', help='Output directory')
    parser.add_argument('--ocr-languages', default='eng', help='OCR languages (comma-separated)')
    parser.add_argument('--force-ocr', action='store_true', help='Force OCR even for text PDFs')
    parser.add_argument('--denoise', action='store_true', default=True, help='Apply denoising to images')
    parser.add_argument('--enhance-contrast', action='store_true', default=True, help='Enhance image contrast')
    
    args = parser.parse_args()
    
    # Configure extractor
    config = {
        'output_dir': args.output_dir,
        'ocr_languages': args.ocr_languages.split(',')
    }
    
    options = {
        'force_ocr': args.force_ocr,
        'denoise': args.denoise,
        'enhance_contrast': args.enhance_contrast
    }
    
    # Extract text
    extractor = TextExtractor(config)
    result = extractor.extract_text(args.file_path, options)
    
    # Print results
    if result.get('success', False):
        print(f"✓ Text extraction successful")
        print(f"  Method: {result.get('method', 'unknown')}")
        print(f"  Characters: {len(result.get('full_text', result.get('text', '')))}")
        print(f"  Session ID: {result.get('session_id')}")
        
        if result.get('method') == 'pdf':
            print(f"  Pages: {len(result.get('pages', []))}")
            if result.get('ocr_applied'):
                print(f"  OCR applied: Yes")
        
        if result.get('statistics'):
            stats = result['statistics']
            print(f"  Words: {stats.get('word_count', 0)}")
            print(f"  Paragraphs: {stats.get('paragraph_count', 0)}")
    else:
        print(f"✗ Text extraction failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)

if __name__ == '__main__':
    main()