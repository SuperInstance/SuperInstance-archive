"""
Table extraction and structured data conversion processor
"""

import re
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import cv2
from PIL import Image
import io
import tempfile
import os

# PDF processing
try:
    import pdfplumber
    import fitz  # PyMuPDF
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

# Table detection libraries
try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False

try:
    import tabula
    TABULA_AVAILABLE = True
except ImportError:
    TABULA_AVAILABLE = False

from ..core.config import settings
from ..core.database import DatabaseManager
from ..models.document_models import ExtractedTable, TableCell, BoundingBox

doc_logger = logging.getLogger('document_processing')

class TableExtractor:
    """Advanced table extraction from documents using multiple methods"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Table extraction methods
        self.rule_based_extractor = RuleBasedTableExtractor()
        self.cv_table_detector = None
        
        # Initialize CV-based detector if OpenCV is available
        try:
            self.cv_table_detector = CVTableDetector()
        except Exception as e:
            doc_logger.warning(f"CV table detector initialization failed: {str(e)}")
    
    async def extract_tables_from_document(self, job_id: str, file_path: str,
                                         page_texts: List[Dict] = None) -> List[ExtractedTable]:
        """
        Extract tables from document using multiple methods
        
        Args:
            job_id: Processing job ID
            file_path: Path to document file
            page_texts: List of page-wise text data
            
        Returns:
            List of extracted tables
        """
        try:
            doc_logger.info(f"Starting table extraction for job {job_id}: {file_path}")
            
            # Determine file type
            file_ext = os.path.splitext(file_path)[1].lower()
            
            all_tables = []
            
            # Extract based on file type
            if file_ext == '.pdf':
                # Try PDF-specific extraction methods
                tables = await self._extract_tables_from_pdf(job_id, file_path, page_texts)
                all_tables.extend(tables)
            elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                # Extract from image
                tables = await self._extract_tables_from_image(job_id, file_path)
                all_tables.extend(tables)
            elif page_texts:
                # Extract from text using rule-based methods
                tables = await self._extract_tables_from_text(job_id, page_texts)
                all_tables.extend(tables)
            
            # Post-process and validate tables
            processed_tables = self._post_process_tables(all_tables)
            
            # Save tables to database
            saved_tables = []
            for table_data in processed_tables:
                table_id = await self.db_manager.save_extracted_table(
                    job_id=job_id,
                    page_number=table_data['page_number'],
                    table_index=table_data['table_index'],
                    method=table_data['extraction_method'],
                    raw_data=table_data['raw_data'],
                    structured_data=table_data['structured_data'],
                    headers=table_data.get('headers', []),
                    row_count=table_data['row_count'],
                    column_count=table_data['column_count'],
                    confidence=table_data.get('confidence'),
                    bounding_box=table_data.get('bounding_box', {})
                )
                
                # Create cells
                cells = []
                if 'cells' in table_data:
                    for row_idx, row in enumerate(table_data['cells']):
                        cell_row = []
                        for col_idx, cell_data in enumerate(row):
                            if isinstance(cell_data, dict):
                                cell = TableCell(
                                    text=cell_data.get('text', ''),
                                    confidence=cell_data.get('confidence'),
                                    bounding_box=cell_data.get('bounding_box')
                                )
                            else:
                                cell = TableCell(text=str(cell_data))
                            cell_row.append(cell)
                        cells.append(cell_row)
                
                table = ExtractedTable(
                    table_id=table_id,
                    job_id=job_id,
                    page_number=table_data['page_number'],
                    table_index=table_data['table_index'],
                    extraction_method=table_data['extraction_method'],
                    raw_table_data=table_data['raw_data'],
                    structured_data=table_data['structured_data'],
                    column_headers=table_data.get('headers', []),
                    row_count=table_data['row_count'],
                    column_count=table_data['column_count'],
                    confidence_score=table_data.get('confidence'),
                    bounding_box=table_data.get('bounding_box'),
                    cells=cells,
                    created_at=table_data.get('created_at')
                )
                saved_tables.append(table)
            
            doc_logger.info(f"Table extraction completed for job {job_id}: {len(saved_tables)} tables")
            return saved_tables
            
        except Exception as e:
            doc_logger.error(f"Table extraction failed for job {job_id}: {str(e)}")
            raise
    
    async def _extract_tables_from_pdf(self, job_id: str, file_path: str,
                                     page_texts: List[Dict] = None) -> List[Dict]:
        """Extract tables from PDF using multiple methods"""
        
        all_tables = []
        
        # Method 1: pdfplumber (good for simple tables)
        if PDFPLUMBER_AVAILABLE:
            try:
                pdfplumber_tables = await self._extract_with_pdfplumber(file_path)
                all_tables.extend(pdfplumber_tables)
                doc_logger.info(f"pdfplumber found {len(pdfplumber_tables)} tables")
            except Exception as e:
                doc_logger.warning(f"pdfplumber extraction failed: {str(e)}")
        
        # Method 2: Camelot (good for lattice tables)
        if CAMELOT_AVAILABLE:
            try:
                camelot_tables = await self._extract_with_camelot(file_path)
                all_tables.extend(camelot_tables)
                doc_logger.info(f"Camelot found {len(camelot_tables)} tables")
            except Exception as e:
                doc_logger.warning(f"Camelot extraction failed: {str(e)}")
        
        # Method 3: Tabula (good for stream tables)
        if TABULA_AVAILABLE:
            try:
                tabula_tables = await self._extract_with_tabula(file_path)
                all_tables.extend(tabula_tables)
                doc_logger.info(f"Tabula found {len(tabula_tables)} tables")
            except Exception as e:
                doc_logger.warning(f"Tabula extraction failed: {str(e)}")
        
        # Method 4: CV-based detection on PDF pages as images
        if self.cv_table_detector:
            try:
                cv_tables = await self._extract_pdf_tables_with_cv(file_path)
                all_tables.extend(cv_tables)
                doc_logger.info(f"CV detection found {len(cv_tables)} tables")
            except Exception as e:
                doc_logger.warning(f"CV table detection failed: {str(e)}")
        
        # Method 5: Rule-based extraction from text
        if page_texts:
            try:
                text_tables = await self._extract_tables_from_text(job_id, page_texts)
                all_tables.extend(text_tables)
                doc_logger.info(f"Rule-based found {len(text_tables)} tables")
            except Exception as e:
                doc_logger.warning(f"Rule-based extraction failed: {str(e)}")
        
        return all_tables
    
    async def _extract_with_pdfplumber(self, file_path: str) -> List[Dict]:
        """Extract tables using pdfplumber"""
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self._pdfplumber_extract_sync, file_path
        )
    
    def _pdfplumber_extract_sync(self, file_path: str) -> List[Dict]:
        """Synchronous pdfplumber table extraction"""
        
        tables = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    
                    for table_idx, table_data in enumerate(page_tables):
                        if table_data and len(table_data) > 1:  # At least 2 rows
                            # Convert to structured format
                            structured_data = self._convert_to_structured_data(table_data)
                            
                            # Get table bounding box if available
                            bounding_box = {}
                            try:
                                table_bbox = page.find_tables()[table_idx].bbox
                                if table_bbox:
                                    bounding_box = {
                                        'x': table_bbox[0],
                                        'y': table_bbox[1], 
                                        'width': table_bbox[2] - table_bbox[0],
                                        'height': table_bbox[3] - table_bbox[1]
                                    }
                            except:
                                pass
                            
                            tables.append({
                                'page_number': page_num + 1,
                                'table_index': table_idx,
                                'extraction_method': 'pdfplumber',
                                'raw_data': table_data,
                                'structured_data': structured_data,
                                'headers': table_data[0] if table_data else [],
                                'row_count': len(table_data),
                                'column_count': len(table_data[0]) if table_data else 0,
                                'confidence': 0.8,
                                'bounding_box': bounding_box
                            })
        
        except Exception as e:
            doc_logger.error(f"pdfplumber extraction error: {str(e)}")
        
        return tables
    
    async def _extract_with_camelot(self, file_path: str) -> List[Dict]:
        """Extract tables using Camelot"""
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self._camelot_extract_sync, file_path
        )
    
    def _camelot_extract_sync(self, file_path: str) -> List[Dict]:
        """Synchronous Camelot table extraction"""
        
        tables = []
        
        try:
            # Try lattice method first (for tables with clear borders)
            lattice_tables = camelot.read_pdf(file_path, flavor='lattice', pages='all')
            
            for table_idx, table in enumerate(lattice_tables):
                if table.accuracy > 70:  # Only high-accuracy tables
                    df = table.df
                    
                    # Convert DataFrame to list format
                    raw_data = []
                    for _, row in df.iterrows():
                        raw_data.append(row.tolist())
                    
                    if raw_data and len(raw_data) > 1:
                        structured_data = self._convert_to_structured_data(raw_data)
                        
                        tables.append({
                            'page_number': table.page,
                            'table_index': table_idx,
                            'extraction_method': 'camelot_lattice',
                            'raw_data': raw_data,
                            'structured_data': structured_data,
                            'headers': raw_data[0] if raw_data else [],
                            'row_count': len(raw_data),
                            'column_count': len(raw_data[0]) if raw_data else 0,
                            'confidence': table.accuracy / 100.0,
                            'bounding_box': {}
                        })
            
            # Try stream method for tables without clear borders
            try:
                stream_tables = camelot.read_pdf(file_path, flavor='stream', pages='all')
                
                for table_idx, table in enumerate(stream_tables):
                    if table.accuracy > 60:  # Lower threshold for stream tables
                        df = table.df
                        
                        raw_data = []
                        for _, row in df.iterrows():
                            raw_data.append(row.tolist())
                        
                        if raw_data and len(raw_data) > 1:
                            structured_data = self._convert_to_structured_data(raw_data)
                            
                            # Check if this table is significantly different from lattice results
                            if not self._is_duplicate_table(tables, raw_data):
                                tables.append({
                                    'page_number': table.page,
                                    'table_index': len([t for t in tables if t['page_number'] == table.page]),
                                    'extraction_method': 'camelot_stream',
                                    'raw_data': raw_data,
                                    'structured_data': structured_data,
                                    'headers': raw_data[0] if raw_data else [],
                                    'row_count': len(raw_data),
                                    'column_count': len(raw_data[0]) if raw_data else 0,
                                    'confidence': table.accuracy / 100.0,
                                    'bounding_box': {}
                                })
            
            except Exception as e:
                doc_logger.warning(f"Camelot stream extraction failed: {str(e)}")
        
        except Exception as e:
            doc_logger.error(f"Camelot extraction error: {str(e)}")
        
        return tables
    
    async def _extract_with_tabula(self, file_path: str) -> List[Dict]:
        """Extract tables using Tabula"""
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self._tabula_extract_sync, file_path
        )
    
    def _tabula_extract_sync(self, file_path: str) -> List[Dict]:
        """Synchronous Tabula table extraction"""
        
        tables = []
        
        try:
            # Extract all tables from all pages
            dfs = tabula.read_pdf(file_path, pages='all', multiple_tables=True)
            
            page_num = 1  # Tabula doesn't provide page numbers easily
            
            for table_idx, df in enumerate(dfs):
                if not df.empty and len(df) > 1:
                    # Convert DataFrame to list format
                    raw_data = []
                    
                    # Add headers
                    headers = df.columns.tolist()
                    raw_data.append(headers)
                    
                    # Add data rows
                    for _, row in df.iterrows():
                        raw_data.append(row.tolist())
                    
                    structured_data = self._convert_to_structured_data(raw_data)
                    
                    tables.append({
                        'page_number': page_num,
                        'table_index': table_idx,
                        'extraction_method': 'tabula',
                        'raw_data': raw_data,
                        'structured_data': structured_data,
                        'headers': headers,
                        'row_count': len(raw_data),
                        'column_count': len(headers),
                        'confidence': 0.7,  # Tabula doesn't provide confidence
                        'bounding_box': {}
                    })
        
        except Exception as e:
            doc_logger.error(f"Tabula extraction error: {str(e)}")
        
        return tables
    
    async def _extract_pdf_tables_with_cv(self, file_path: str) -> List[Dict]:
        """Extract tables from PDF using computer vision"""
        
        if not self.cv_table_detector:
            return []
        
        tables = []
        
        try:
            # Convert PDF pages to images
            doc = fitz.open(file_path)
            
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                mat = fitz.Matrix(2, 2)  # 2x zoom for better detection
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Detect tables in image
                page_tables = await self._extract_tables_from_image_data(
                    img_data, page_num + 1
                )
                tables.extend(page_tables)
            
            doc.close()
        
        except Exception as e:
            doc_logger.error(f"CV PDF table extraction error: {str(e)}")
        
        return tables
    
    async def _extract_tables_from_image(self, job_id: str, file_path: str) -> List[Dict]:
        """Extract tables from image files"""
        
        if not self.cv_table_detector:
            return []
        
        try:
            with open(file_path, 'rb') as f:
                img_data = f.read()
            
            return await self._extract_tables_from_image_data(img_data, 1)
        
        except Exception as e:
            doc_logger.error(f"Image table extraction error: {str(e)}")
            return []
    
    async def _extract_tables_from_image_data(self, img_data: bytes, 
                                            page_number: int) -> List[Dict]:
        """Extract tables from image data using CV"""
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, 
            self.cv_table_detector.detect_tables, 
            img_data, 
            page_number
        )
    
    async def _extract_tables_from_text(self, job_id: str, 
                                      page_texts: List[Dict]) -> List[Dict]:
        """Extract tables from text using rule-based patterns"""
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, 
            self.rule_based_extractor.extract_tables, 
            page_texts
        )
    
    def _convert_to_structured_data(self, raw_data: List[List[str]]) -> Dict[str, Any]:
        """Convert raw table data to structured format"""
        
        if not raw_data or len(raw_data) < 2:
            return {}
        
        # Assume first row is headers
        headers = [str(cell).strip() for cell in raw_data[0]]
        
        # Convert to list of dictionaries
        structured_rows = []
        for row in raw_data[1:]:
            row_dict = {}
            for col_idx, cell_value in enumerate(row):
                header = headers[col_idx] if col_idx < len(headers) else f"Column_{col_idx}"
                row_dict[header] = str(cell_value).strip() if cell_value is not None else ""
            structured_rows.append(row_dict)
        
        return {
            'headers': headers,
            'rows': structured_rows,
            'summary': {
                'row_count': len(structured_rows),
                'column_count': len(headers),
                'data_types': self._analyze_data_types(structured_rows, headers)
            }
        }
    
    def _analyze_data_types(self, rows: List[Dict], headers: List[str]) -> Dict[str, str]:
        """Analyze data types in table columns"""
        
        data_types = {}
        
        for header in headers:
            column_values = [row.get(header, '') for row in rows if row.get(header, '').strip()]
            
            if not column_values:
                data_types[header] = 'empty'
                continue
            
            # Check for numeric data
            numeric_count = 0
            date_count = 0
            
            for value in column_values:
                # Check if numeric (including currency)
                if re.match(r'^[\$£€¥]?[\d,]+\.?\d*$', value.strip()):
                    numeric_count += 1
                # Check if date-like
                elif re.match(r'\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}', value.strip()):
                    date_count += 1
            
            total_values = len(column_values)
            
            if numeric_count / total_values > 0.7:
                data_types[header] = 'numeric'
            elif date_count / total_values > 0.5:
                data_types[header] = 'date'
            else:
                data_types[header] = 'text'
        
        return data_types
    
    def _is_duplicate_table(self, existing_tables: List[Dict], new_raw_data: List[List[str]]) -> bool:
        """Check if a table is a duplicate of existing ones"""
        
        if not new_raw_data or len(new_raw_data) < 2:
            return True
        
        new_content_hash = self._calculate_table_hash(new_raw_data)
        
        for table in existing_tables:
            existing_hash = self._calculate_table_hash(table['raw_data'])
            if new_content_hash == existing_hash:
                return True
        
        return False
    
    def _calculate_table_hash(self, raw_data: List[List[str]]) -> str:
        """Calculate hash of table content for duplicate detection"""
        
        # Flatten table content and create hash
        content_str = ''.join([''.join([str(cell) for cell in row]) for row in raw_data])
        return hashlib.md5(content_str.encode()).hexdigest()
    
    def _post_process_tables(self, tables: List[Dict]) -> List[Dict]:
        """Post-process extracted tables for quality and consistency"""
        
        processed_tables = []
        
        for table in tables:
            # Skip tables that are too small or empty
            if table['row_count'] < 2 or table['column_count'] < 2:
                continue
            
            # Clean empty rows and columns
            cleaned_table = self._clean_table_data(table)
            
            # Skip if cleaning removed too much data
            if cleaned_table['row_count'] < 2 or cleaned_table['column_count'] < 2:
                continue
            
            processed_tables.append(cleaned_table)
        
        # Remove duplicates
        return self._remove_duplicate_tables(processed_tables)
    
    def _clean_table_data(self, table: Dict) -> Dict:
        """Clean table data by removing empty rows/columns"""
        
        raw_data = table['raw_data']
        
        if not raw_data:
            return table
        
        # Remove completely empty rows
        cleaned_rows = []
        for row in raw_data:
            if any(str(cell).strip() for cell in row):
                cleaned_rows.append(row)
        
        if not cleaned_rows:
            return table
        
        # Remove completely empty columns
        num_cols = max(len(row) for row in cleaned_rows)
        
        non_empty_cols = []
        for col_idx in range(num_cols):
            has_data = False
            for row in cleaned_rows:
                if col_idx < len(row) and str(row[col_idx]).strip():
                    has_data = True
                    break
            if has_data:
                non_empty_cols.append(col_idx)
        
        # Rebuild table with only non-empty columns
        if non_empty_cols:
            cleaned_data = []
            for row in cleaned_rows:
                cleaned_row = [row[col_idx] if col_idx < len(row) else '' for col_idx in non_empty_cols]
                cleaned_data.append(cleaned_row)
            
            # Update table data
            table = table.copy()
            table['raw_data'] = cleaned_data
            table['structured_data'] = self._convert_to_structured_data(cleaned_data)
            table['row_count'] = len(cleaned_data)
            table['column_count'] = len(non_empty_cols)
            table['headers'] = cleaned_data[0] if cleaned_data else []
        
        return table
    
    def _remove_duplicate_tables(self, tables: List[Dict]) -> List[Dict]:
        """Remove duplicate tables from the list"""
        
        unique_tables = []
        seen_hashes = set()
        
        for table in tables:
            table_hash = self._calculate_table_hash(table['raw_data'])
            
            if table_hash not in seen_hashes:
                seen_hashes.add(table_hash)
                unique_tables.append(table)
        
        return unique_tables


class CVTableDetector:
    """Computer vision-based table detection"""
    
    def __init__(self):
        pass
    
    def detect_tables(self, img_data: bytes, page_number: int) -> List[Dict]:
        """Detect tables in image using OpenCV"""
        
        try:
            # Load image
            image = cv2.imdecode(np.frombuffer(img_data, np.uint8), cv2.IMREAD_COLOR)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detect horizontal and vertical lines
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
            
            # Find horizontal lines
            horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
            
            # Find vertical lines
            vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel)
            
            # Combine lines to form table structure
            table_structure = cv2.addWeighted(horizontal_lines, 0.5, vertical_lines, 0.5, 0.0)
            
            # Find contours (potential table regions)
            contours, _ = cv2.findContours(table_structure, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            tables = []
            
            for idx, contour in enumerate(contours):
                # Filter contours by area (tables should be reasonably large)
                area = cv2.contourArea(contour)
                if area < 1000:  # Minimum area threshold
                    continue
                
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # Extract table region
                table_roi = gray[y:y+h, x:x+w]
                
                # Try to extract text from table region using simple OCR
                table_data = self._extract_text_from_table_region(table_roi)
                
                if table_data and len(table_data) > 1:
                    tables.append({
                        'page_number': page_number,
                        'table_index': idx,
                        'extraction_method': 'cv_detection',
                        'raw_data': table_data,
                        'structured_data': {},  # Would need more sophisticated processing
                        'headers': table_data[0] if table_data else [],
                        'row_count': len(table_data),
                        'column_count': len(table_data[0]) if table_data else 0,
                        'confidence': 0.6,  # Lower confidence for CV detection
                        'bounding_box': {
                            'x': int(x),
                            'y': int(y),
                            'width': int(w),
                            'height': int(h)
                        }
                    })
            
            return tables
        
        except Exception as e:
            doc_logger.error(f"CV table detection error: {str(e)}")
            return []
    
    def _extract_text_from_table_region(self, table_roi: np.ndarray) -> List[List[str]]:
        """Extract text from detected table region"""
        
        # This is a simplified implementation
        # In practice, you'd want more sophisticated cell detection and OCR
        
        try:
            import pytesseract
            
            # Apply OCR to the table region
            text = pytesseract.image_to_string(table_roi)
            
            # Split into rows and columns (very basic)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            table_data = []
            for line in lines:
                # Simple column splitting by whitespace
                columns = line.split()
                if len(columns) > 1:
                    table_data.append(columns)
            
            return table_data[:10]  # Limit to 10 rows
        
        except Exception:
            return []


class RuleBasedTableExtractor:
    """Rule-based table extraction from text"""
    
    def __init__(self):
        # Patterns that indicate table-like data
        self.table_patterns = [
            r'^\s*\|.*\|.*\|.*$',  # Pipe-separated
            r'^\s*[^\s]+\s+[^\s]+\s+[^\s]+.*$',  # Space-separated columns
            r'^\s*\d+[\.\)]\s+.*$',  # Numbered lists with data
        ]
        
        self.compiled_patterns = [re.compile(pattern, re.MULTILINE) for pattern in self.table_patterns]
    
    def extract_tables(self, page_texts: List[Dict]) -> List[Dict]:
        """Extract tables from text using patterns"""
        
        tables = []
        
        for page_data in page_texts:
            page_num = page_data.get('page_number', 1)
            text = page_data.get('cleaned_text', '')
            
            if not text:
                continue
            
            # Look for table-like patterns
            potential_tables = self._find_table_regions(text)
            
            for table_idx, table_text in enumerate(potential_tables):
                table_data = self._parse_table_text(table_text)
                
                if table_data and len(table_data) > 1:
                    tables.append({
                        'page_number': page_num,
                        'table_index': table_idx,
                        'extraction_method': 'rule_based_text',
                        'raw_data': table_data,
                        'structured_data': {},
                        'headers': table_data[0] if table_data else [],
                        'row_count': len(table_data),
                        'column_count': len(table_data[0]) if table_data else 0,
                        'confidence': 0.5,  # Lower confidence for rule-based
                        'bounding_box': {}
                    })
        
        return tables
    
    def _find_table_regions(self, text: str) -> List[str]:
        """Find regions in text that look like tables"""
        
        lines = text.split('\n')
        table_regions = []
        current_table_lines = []
        
        for line in lines:
            # Check if line matches any table pattern
            is_table_line = any(pattern.match(line) for pattern in self.compiled_patterns)
            
            if is_table_line:
                current_table_lines.append(line)
            else:
                # End of potential table
                if len(current_table_lines) >= 3:  # At least 3 lines for a table
                    table_regions.append('\n'.join(current_table_lines))
                current_table_lines = []
        
        # Don't forget the last table
        if len(current_table_lines) >= 3:
            table_regions.append('\n'.join(current_table_lines))
        
        return table_regions
    
    def _parse_table_text(self, table_text: str) -> List[List[str]]:
        """Parse table text into structured data"""
        
        lines = table_text.split('\n')
        table_data = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try different parsing methods
            columns = None
            
            # Method 1: Pipe-separated
            if '|' in line:
                columns = [col.strip() for col in line.split('|') if col.strip()]
            
            # Method 2: Multiple consecutive spaces
            elif re.search(r'\s{2,}', line):
                columns = re.split(r'\s{2,}', line)
            
            # Method 3: Tab-separated
            elif '\t' in line:
                columns = [col.strip() for col in line.split('\t') if col.strip()]
            
            # Method 4: Single space (less reliable)
            else:
                words = line.split()
                if len(words) > 2:
                    columns = words
            
            if columns and len(columns) > 1:
                table_data.append(columns)
        
        # Ensure consistent column count
        if table_data:
            max_cols = max(len(row) for row in table_data)
            normalized_data = []
            
            for row in table_data:
                while len(row) < max_cols:
                    row.append('')
                normalized_data.append(row[:max_cols])
            
            return normalized_data
        
        return []