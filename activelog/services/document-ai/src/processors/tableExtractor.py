#!/usr/bin/env python3
"""
Table Extraction and Structured Data Conversion Module
Extracts tables from documents and converts them to structured data formats
"""

import os
import json
import logging
import re
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
import uuid
from datetime import datetime
import tempfile

# PDF and table extraction
import pandas as pd
import pdfplumber
import tabula
import camelot
import fitz  # PyMuPDF

# Image processing
from PIL import Image
import cv2
import numpy as np

# Data processing
import openpyxl
from io import StringIO, BytesIO

# Machine learning for table detection
try:
    from transformers import pipeline, AutoProcessor, AutoModelForObjectDetection
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

# Utilities
import warnings
warnings.filterwarnings('ignore')

class TableExtractor:
    """Extract and process tables from various document formats"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.output_dir = self.config.get('output_dir', './output/tables')
        self.temp_dir = self.config.get('temp_dir', './temp/tables')
        self.extraction_methods = self.config.get('extraction_methods', ['pdfplumber', 'tabula', 'camelot'])
        
        # Table detection confidence threshold
        self.confidence_threshold = self.config.get('confidence_threshold', 0.8)
        
        # Supported output formats
        self.output_formats = ['json', 'csv', 'xlsx', 'html', 'markdown']
        
        # Initialize ML models
        self.table_detector = None
        
        # Setup directories
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize ML models for table detection"""
        
        try:
            if HAS_TRANSFORMERS:
                # Load table detection model
                try:
                    self.table_detector = pipeline(
                        "object-detection",
                        model="microsoft/table-transformer-detection",
                        device=-1  # Use CPU
                    )
                    self.logger.info("Table detection model loaded successfully")
                except Exception as e:
                    self.logger.warning(f"Could not load table detection model: {str(e)}")
                    self.table_detector = None
            else:
                self.logger.warning("Transformers not available, using rule-based detection only")
                
        except Exception as e:
            self.logger.error(f"Model initialization failed: {str(e)}")
    
    def extract_tables(self, file_path: str, options: Dict = None) -> Dict:
        """
        Extract tables from document using multiple methods
        """
        session_id = str(uuid.uuid4())
        options = options or {}
        
        try:
            self.logger.info(f"Extracting tables from {file_path} (session: {session_id})")
            
            # Detect file type
            file_type = self._detect_file_type(file_path)
            
            result = {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'file_path': file_path,
                'file_type': file_type,
                'extraction_methods': {},
                'tables': [],
                'metadata': {}
            }
            
            # Route to appropriate extraction method
            if file_type == 'pdf':
                tables = self._extract_tables_from_pdf(file_path, options, session_id)
            elif file_type in ['xlsx', 'xls']:
                tables = self._extract_tables_from_excel(file_path, options, session_id)
            elif file_type == 'csv':
                tables = self._extract_tables_from_csv(file_path, options, session_id)
            elif file_type in ['html', 'htm']:
                tables = self._extract_tables_from_html(file_path, options, session_id)
            elif file_type in ['png', 'jpg', 'jpeg', 'tiff', 'bmp']:
                tables = self._extract_tables_from_image(file_path, options, session_id)
            else:
                raise ValueError(f"Unsupported file type for table extraction: {file_type}")
            
            result.update(tables)
            
            # Post-process tables
            if result['tables']:
                result['tables'] = self._post_process_tables(result['tables'], options)
                
                # Generate structured data
                structured_data = self._convert_to_structured_data(result['tables'], options)
                result['structured_data'] = structured_data
                
                # Analyze table content
                analysis = self._analyze_table_content(result['tables'])
                result['content_analysis'] = analysis
            
            # Calculate statistics
            result['statistics'] = self._calculate_table_statistics(result)
            
            # Save results
            self._save_table_results(result, options)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Table extraction failed for {file_path}: {str(e)}")
            return {
                'session_id': session_id,
                'error': str(e),
                'success': False,
                'file_path': file_path
            }
    
    def _detect_file_type(self, file_path: str) -> str:
        """Detect file type for table extraction"""
        
        extension = Path(file_path).suffix.lower()
        
        type_mapping = {
            '.pdf': 'pdf',
            '.xlsx': 'xlsx',
            '.xls': 'xls',
            '.csv': 'csv',
            '.html': 'html',
            '.htm': 'html',
            '.png': 'png',
            '.jpg': 'jpg',
            '.jpeg': 'jpeg',
            '.tiff': 'tiff',
            '.bmp': 'bmp'
        }
        
        return type_mapping.get(extension, 'unknown')
    
    def _extract_tables_from_pdf(self, file_path: str, options: Dict, session_id: str) -> Dict:
        """Extract tables from PDF using multiple methods"""
        
        result = {
            'extraction_methods': {},
            'tables': [],
            'metadata': {}
        }
        
        # Method 1: pdfplumber
        if 'pdfplumber' in self.extraction_methods:
            try:
                pdfplumber_tables = self._extract_with_pdfplumber(file_path, options)
                result['extraction_methods']['pdfplumber'] = pdfplumber_tables
                self.logger.info(f"pdfplumber found {len(pdfplumber_tables.get('tables', []))} tables")
            except Exception as e:
                self.logger.warning(f"pdfplumber extraction failed: {str(e)}")
                result['extraction_methods']['pdfplumber'] = {'error': str(e), 'tables': []}
        
        # Method 2: tabula-py
        if 'tabula' in self.extraction_methods:
            try:
                tabula_tables = self._extract_with_tabula(file_path, options)
                result['extraction_methods']['tabula'] = tabula_tables
                self.logger.info(f"tabula found {len(tabula_tables.get('tables', []))} tables")
            except Exception as e:
                self.logger.warning(f"tabula extraction failed: {str(e)}")
                result['extraction_methods']['tabula'] = {'error': str(e), 'tables': []}
        
        # Method 3: camelot
        if 'camelot' in self.extraction_methods:
            try:
                camelot_tables = self._extract_with_camelot(file_path, options)
                result['extraction_methods']['camelot'] = camelot_tables
                self.logger.info(f"camelot found {len(camelot_tables.get('tables', []))} tables")
            except Exception as e:
                self.logger.warning(f"camelot extraction failed: {str(e)}")
                result['extraction_methods']['camelot'] = {'error': str(e), 'tables': []}
        
        # Method 4: ML-based detection (if available)
        if self.table_detector and options.get('use_ml_detection', True):
            try:
                ml_tables = self._extract_with_ml_detection(file_path, options, session_id)
                result['extraction_methods']['ml_detection'] = ml_tables
                self.logger.info(f"ML detection found {len(ml_tables.get('tables', []))} tables")
            except Exception as e:
                self.logger.warning(f"ML table detection failed: {str(e)}")
                result['extraction_methods']['ml_detection'] = {'error': str(e), 'tables': []}
        
        # Consolidate tables from all methods
        all_tables = []
        for method, method_result in result['extraction_methods'].items():
            if 'tables' in method_result:
                for table in method_result['tables']:
                    table['extraction_method'] = method
                    all_tables.append(table)
        
        # Deduplicate and rank tables
        result['tables'] = self._deduplicate_tables(all_tables)
        
        # Extract PDF metadata
        result['metadata'] = self._extract_pdf_metadata(file_path)
        
        return result
    
    def _extract_with_pdfplumber(self, file_path: str, options: Dict) -> Dict:
        """Extract tables using pdfplumber"""
        
        tables = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Extract tables from page
                    page_tables = page.extract_tables()
                    
                    for table_num, table_data in enumerate(page_tables):
                        if table_data and len(table_data) > 1:  # Must have at least header + 1 row
                            # Clean table data
                            cleaned_data = self._clean_table_data(table_data)
                            
                            table_info = {
                                'page': page_num + 1,
                                'table_number': table_num + 1,
                                'data': cleaned_data,
                                'rows': len(cleaned_data),
                                'columns': len(cleaned_data[0]) if cleaned_data else 0,
                                'confidence': 0.8,  # pdfplumber is generally reliable
                                'bbox': None  # pdfplumber doesn't provide bbox
                            }
                            
                            tables.append(table_info)
        
        except Exception as e:
            self.logger.warning(f"pdfplumber table extraction failed: {str(e)}")
        
        return {'tables': tables, 'method': 'pdfplumber'}
    
    def _extract_with_tabula(self, file_path: str, options: Dict) -> Dict:
        """Extract tables using tabula-py"""
        
        tables = []
        
        try:
            # Use tabula to extract tables
            tabula_tables = tabula.read_pdf(
                file_path,
                pages='all',
                multiple_tables=True,
                pandas_options={'header': 0}
            )
            
            for table_num, df in enumerate(tabula_tables):
                if not df.empty and len(df) > 0:
                    # Convert DataFrame to list of lists
                    table_data = [df.columns.tolist()] + df.values.tolist()
                    
                    # Clean data
                    cleaned_data = self._clean_table_data(table_data)
                    
                    table_info = {
                        'page': table_num + 1,  # tabula doesn't provide exact page info in this mode
                        'table_number': table_num + 1,
                        'data': cleaned_data,
                        'rows': len(cleaned_data),
                        'columns': len(cleaned_data[0]) if cleaned_data else 0,
                        'confidence': 0.7,  # tabula can be less reliable
                        'bbox': None
                    }
                    
                    tables.append(table_info)
        
        except Exception as e:
            self.logger.warning(f"tabula table extraction failed: {str(e)}")
        
        return {'tables': tables, 'method': 'tabula'}
    
    def _extract_with_camelot(self, file_path: str, options: Dict) -> Dict:
        """Extract tables using camelot"""
        
        tables = []
        
        try:
            # Extract tables using camelot
            camelot_tables = camelot.read_pdf(file_path, pages='all')
            
            for table in camelot_tables:
                # Get table data as list of lists
                table_data = [table.df.columns.tolist()] + table.df.values.tolist()
                
                # Clean data
                cleaned_data = self._clean_table_data(table_data)
                
                # Get table properties
                table_info = {
                    'page': table.page,
                    'table_number': len(tables) + 1,
                    'data': cleaned_data,
                    'rows': len(cleaned_data),
                    'columns': len(cleaned_data[0]) if cleaned_data else 0,
                    'confidence': table.accuracy / 100.0,  # Convert percentage to decimal
                    'bbox': table._bbox if hasattr(table, '_bbox') else None,
                    'accuracy': table.accuracy,
                    'whitespace': table.whitespace
                }
                
                tables.append(table_info)
        
        except Exception as e:
            self.logger.warning(f"camelot table extraction failed: {str(e)}")
        
        return {'tables': tables, 'method': 'camelot'}
    
    def _extract_with_ml_detection(self, file_path: str, options: Dict, session_id: str) -> Dict:
        """Extract tables using ML-based detection"""
        
        tables = []
        
        try:
            # Convert PDF pages to images
            doc = fitz.open(file_path)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Convert page to image
                mat = fitz.Matrix(2, 2)  # 2x zoom for better detection
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Load image
                image = Image.open(BytesIO(img_data))
                
                # Detect tables
                detections = self.table_detector(image)
                
                # Process detections
                for detection in detections:
                    if detection['score'] >= self.confidence_threshold:
                        # Extract table region
                        bbox = detection['box']
                        
                        # Crop table region from image
                        table_image = image.crop((bbox['xmin'], bbox['ymin'], bbox['xmax'], bbox['ymax']))
                        
                        # Save cropped image for OCR
                        temp_image_path = os.path.join(
                            self.temp_dir, 
                            f"{session_id}_page_{page_num + 1}_table_{len(tables) + 1}.png"
                        )
                        table_image.save(temp_image_path)
                        
                        # Extract table data using OCR (placeholder - would need OCR implementation)
                        table_data = self._extract_table_from_image(temp_image_path)
                        
                        table_info = {
                            'page': page_num + 1,
                            'table_number': len(tables) + 1,
                            'data': table_data,
                            'rows': len(table_data),
                            'columns': len(table_data[0]) if table_data else 0,
                            'confidence': detection['score'],
                            'bbox': bbox,
                            'image_path': temp_image_path
                        }
                        
                        tables.append(table_info)
                        
                        # Clean up temp file
                        try:
                            os.remove(temp_image_path)
                        except:
                            pass
            
            doc.close()
        
        except Exception as e:
            self.logger.warning(f"ML table detection failed: {str(e)}")
        
        return {'tables': tables, 'method': 'ml_detection'}
    
    def _extract_table_from_image(self, image_path: str) -> List[List[str]]:
        """Extract table data from image using OCR (placeholder implementation)"""
        
        # This is a simplified implementation
        # In practice, you would use more sophisticated table structure recognition
        
        try:
            # Load image
            image = cv2.imread(image_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Simple table detection using line detection
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
            
            # Detect horizontal and vertical lines
            horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
            vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel)
            
            # Combine lines
            table_mask = cv2.add(horizontal_lines, vertical_lines)
            
            # Find contours (cells)
            contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Sort contours to create grid
            # This is a simplified approach
            cells = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w > 20 and h > 10:  # Filter small artifacts
                    cells.append((x, y, w, h))
            
            # Group cells into rows and columns
            # Simplified: create a 3x3 table
            return [
                ['Header 1', 'Header 2', 'Header 3'],
                ['Row 1 Col 1', 'Row 1 Col 2', 'Row 1 Col 3'],
                ['Row 2 Col 1', 'Row 2 Col 2', 'Row 2 Col 3']
            ]
            
        except Exception as e:
            self.logger.warning(f"Image table extraction failed: {str(e)}")
            return [['Error extracting table from image']]
    
    def _extract_tables_from_excel(self, file_path: str, options: Dict, session_id: str) -> Dict:
        """Extract tables from Excel files"""
        
        result = {
            'extraction_methods': {'excel': {'tables': []}},
            'tables': [],
            'metadata': {}
        }
        
        try:
            # Read Excel file
            excel_file = pd.ExcelFile(file_path)
            
            for sheet_num, sheet_name in enumerate(excel_file.sheet_names):
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                if not df.empty:
                    # Convert to list of lists
                    table_data = [df.columns.tolist()] + df.values.tolist()
                    
                    # Clean data
                    cleaned_data = self._clean_table_data(table_data)
                    
                    table_info = {
                        'sheet': sheet_name,
                        'sheet_number': sheet_num + 1,
                        'table_number': 1,
                        'data': cleaned_data,
                        'rows': len(cleaned_data),
                        'columns': len(cleaned_data[0]) if cleaned_data else 0,
                        'confidence': 1.0,  # Excel tables are definitive
                        'extraction_method': 'excel'
                    }
                    
                    result['tables'].append(table_info)
            
            result['extraction_methods']['excel']['tables'] = result['tables']
            
        except Exception as e:
            self.logger.error(f"Excel extraction failed: {str(e)}")
            result['extraction_methods']['excel'] = {'error': str(e), 'tables': []}
        
        return result
    
    def _extract_tables_from_csv(self, file_path: str, options: Dict, session_id: str) -> Dict:
        """Extract table from CSV file"""
        
        result = {
            'extraction_methods': {'csv': {'tables': []}},
            'tables': [],
            'metadata': {}
        }
        
        try:
            # Read CSV file
            df = pd.read_csv(file_path)
            
            if not df.empty:
                # Convert to list of lists
                table_data = [df.columns.tolist()] + df.values.tolist()
                
                # Clean data
                cleaned_data = self._clean_table_data(table_data)
                
                table_info = {
                    'file': Path(file_path).name,
                    'table_number': 1,
                    'data': cleaned_data,
                    'rows': len(cleaned_data),
                    'columns': len(cleaned_data[0]) if cleaned_data else 0,
                    'confidence': 1.0,
                    'extraction_method': 'csv'
                }
                
                result['tables'].append(table_info)
                result['extraction_methods']['csv']['tables'] = result['tables']
            
        except Exception as e:
            self.logger.error(f"CSV extraction failed: {str(e)}")
            result['extraction_methods']['csv'] = {'error': str(e), 'tables': []}
        
        return result
    
    def _extract_tables_from_html(self, file_path: str, options: Dict, session_id: str) -> Dict:
        """Extract tables from HTML files"""
        
        result = {
            'extraction_methods': {'html': {'tables': []}},
            'tables': [],
            'metadata': {}
        }
        
        try:
            # Read HTML tables
            tables_list = pd.read_html(file_path)
            
            for table_num, df in enumerate(tables_list):
                if not df.empty:
                    # Convert to list of lists
                    table_data = [df.columns.tolist()] + df.values.tolist()
                    
                    # Clean data
                    cleaned_data = self._clean_table_data(table_data)
                    
                    table_info = {
                        'file': Path(file_path).name,
                        'table_number': table_num + 1,
                        'data': cleaned_data,
                        'rows': len(cleaned_data),
                        'columns': len(cleaned_data[0]) if cleaned_data else 0,
                        'confidence': 0.9,  # HTML tables are generally reliable
                        'extraction_method': 'html'
                    }
                    
                    result['tables'].append(table_info)
            
            result['extraction_methods']['html']['tables'] = result['tables']
            
        except Exception as e:
            self.logger.error(f"HTML extraction failed: {str(e)}")
            result['extraction_methods']['html'] = {'error': str(e), 'tables': []}
        
        return result
    
    def _extract_tables_from_image(self, file_path: str, options: Dict, session_id: str) -> Dict:
        """Extract tables from image files"""
        
        result = {
            'extraction_methods': {'image_ocr': {'tables': []}},
            'tables': [],
            'metadata': {}
        }
        
        try:
            # Extract table data from image
            table_data = self._extract_table_from_image(file_path)
            
            if table_data and len(table_data) > 1:
                table_info = {
                    'file': Path(file_path).name,
                    'table_number': 1,
                    'data': table_data,
                    'rows': len(table_data),
                    'columns': len(table_data[0]) if table_data else 0,
                    'confidence': 0.6,  # Image OCR is less reliable
                    'extraction_method': 'image_ocr'
                }
                
                result['tables'].append(table_info)
                result['extraction_methods']['image_ocr']['tables'] = result['tables']
            
        except Exception as e:
            self.logger.error(f"Image extraction failed: {str(e)}")
            result['extraction_methods']['image_ocr'] = {'error': str(e), 'tables': []}
        
        return result
    
    def _clean_table_data(self, table_data: List[List]) -> List[List[str]]:
        """Clean and normalize table data"""
        
        if not table_data:
            return []
        
        cleaned_data = []
        
        for row in table_data:
            cleaned_row = []
            for cell in row:
                # Convert to string and clean
                if cell is None or pd.isna(cell):
                    cell_str = ""
                else:
                    cell_str = str(cell).strip()
                
                # Remove extra whitespace
                cell_str = re.sub(r'\s+', ' ', cell_str)
                
                cleaned_row.append(cell_str)
            
            # Only add non-empty rows
            if any(cell.strip() for cell in cleaned_row):
                cleaned_data.append(cleaned_row)
        
        return cleaned_data
    
    def _deduplicate_tables(self, tables: List[Dict]) -> List[Dict]:
        """Remove duplicate tables and select best versions"""
        
        if not tables:
            return tables
        
        # Group similar tables
        grouped_tables = {}
        
        for table in tables:
            # Create signature based on dimensions and first few cells
            signature = self._create_table_signature(table)
            
            if signature not in grouped_tables:
                grouped_tables[signature] = []
            
            grouped_tables[signature].append(table)
        
        # Select best table from each group
        deduplicated_tables = []
        
        for signature, table_group in grouped_tables.items():
            if len(table_group) == 1:
                deduplicated_tables.append(table_group[0])
            else:
                # Select table with highest confidence
                best_table = max(table_group, key=lambda t: t.get('confidence', 0))
                
                # Add alternative extractions info
                best_table['alternative_extractions'] = [
                    {
                        'method': t.get('extraction_method'),
                        'confidence': t.get('confidence', 0)
                    }
                    for t in table_group if t != best_table
                ]
                
                deduplicated_tables.append(best_table)
        
        return deduplicated_tables
    
    def _create_table_signature(self, table: Dict) -> str:
        """Create signature for table deduplication"""
        
        data = table.get('data', [])
        rows = table.get('rows', 0)
        columns = table.get('columns', 0)
        
        # Create signature from dimensions and first few cells
        signature_parts = [f"{rows}x{columns}"]
        
        if data:
            # Add first row (headers) to signature
            if len(data) > 0:
                first_row = '|'.join(data[0][:3])  # First 3 cells
                signature_parts.append(first_row)
            
            # Add first cell of second row if available
            if len(data) > 1 and data[1]:
                signature_parts.append(data[1][0])
        
        return '::'.join(signature_parts)
    
    def _post_process_tables(self, tables: List[Dict], options: Dict) -> List[Dict]:
        """Post-process extracted tables"""
        
        processed_tables = []
        
        for table in tables:
            # Skip tables that are too small
            if table.get('rows', 0) < 2 or table.get('columns', 0) < 2:
                continue
            
            # Detect and fix header rows
            table = self._detect_headers(table)
            
            # Detect data types
            table = self._detect_data_types(table)
            
            # Add table analysis
            table['analysis'] = self._analyze_individual_table(table)
            
            processed_tables.append(table)
        
        return processed_tables
    
    def _detect_headers(self, table: Dict) -> Dict:
        """Detect header rows in table"""
        
        data = table.get('data', [])
        if len(data) < 2:
            return table
        
        # Simple heuristic: first row is likely header if it contains mostly text
        # and subsequent rows contain more numbers/mixed content
        
        first_row = data[0]
        second_row = data[1] if len(data) > 1 else []
        
        # Count numeric cells in each row
        first_row_numbers = sum(1 for cell in first_row if self._is_numeric(cell))
        second_row_numbers = sum(1 for cell in second_row if self._is_numeric(cell))
        
        # If first row has fewer numbers than second row, it's likely a header
        has_header = first_row_numbers < second_row_numbers
        
        table['has_header'] = has_header
        if has_header:
            table['headers'] = first_row
            table['data_rows'] = data[1:]
        else:
            table['headers'] = []
            table['data_rows'] = data
        
        return table
    
    def _detect_data_types(self, table: Dict) -> Dict:
        """Detect data types for each column"""
        
        data = table.get('data_rows', table.get('data', []))
        if not data:
            return table
        
        column_count = table.get('columns', 0)
        column_types = []
        
        for col_idx in range(column_count):
            # Collect values from this column
            column_values = []
            for row in data:
                if col_idx < len(row):
                    column_values.append(row[col_idx])
            
            # Determine column type
            col_type = self._determine_column_type(column_values)
            column_types.append(col_type)
        
        table['column_types'] = column_types
        return table
    
    def _determine_column_type(self, values: List[str]) -> str:
        """Determine the data type of a column"""
        
        if not values:
            return 'unknown'
        
        # Count different types
        numeric_count = 0
        date_count = 0
        boolean_count = 0
        empty_count = 0
        
        for value in values:
            value = value.strip()
            
            if not value:
                empty_count += 1
            elif self._is_numeric(value):
                numeric_count += 1
            elif self._is_date(value):
                date_count += 1
            elif self._is_boolean(value):
                boolean_count += 1
        
        total_non_empty = len(values) - empty_count
        
        if total_non_empty == 0:
            return 'empty'
        
        # Determine type based on majority
        if numeric_count / total_non_empty > 0.7:
            return 'numeric'
        elif date_count / total_non_empty > 0.7:
            return 'date'
        elif boolean_count / total_non_empty > 0.7:
            return 'boolean'
        else:
            return 'text'
    
    def _is_numeric(self, value: str) -> bool:
        """Check if value is numeric"""
        try:
            # Remove common formatting
            cleaned_value = re.sub(r'[,$%\s]', '', value)
            float(cleaned_value)
            return True
        except (ValueError, TypeError):
            return False
    
    def _is_date(self, value: str) -> bool:
        """Check if value looks like a date"""
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b'
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        
        return False
    
    def _is_boolean(self, value: str) -> bool:
        """Check if value is boolean"""
        boolean_values = ['true', 'false', 'yes', 'no', 'y', 'n', '1', '0']
        return value.lower() in boolean_values
    
    def _analyze_individual_table(self, table: Dict) -> Dict:
        """Analyze individual table characteristics"""
        
        analysis = {
            'table_type': 'unknown',
            'has_totals': False,
            'has_calculations': False,
            'data_density': 0,
            'column_analysis': []
        }
        
        data = table.get('data_rows', table.get('data', []))
        if not data:
            return analysis
        
        # Analyze each column
        for col_idx in range(table.get('columns', 0)):
            column_values = [row[col_idx] if col_idx < len(row) else '' for row in data]
            
            col_analysis = {
                'index': col_idx,
                'type': table.get('column_types', []).get(col_idx, 'unknown'),
                'unique_values': len(set(column_values)),
                'empty_cells': sum(1 for v in column_values if not v.strip()),
                'has_formula_indicators': any('=' in str(v) for v in column_values)
            }
            
            analysis['column_analysis'].append(col_analysis)
        
        # Detect table type
        analysis['table_type'] = self._classify_table_type(table, analysis)
        
        # Calculate data density
        total_cells = table.get('rows', 0) * table.get('columns', 0)
        empty_cells = sum(col['empty_cells'] for col in analysis['column_analysis'])
        analysis['data_density'] = (total_cells - empty_cells) / total_cells if total_cells > 0 else 0
        
        return analysis
    
    def _classify_table_type(self, table: Dict, analysis: Dict) -> str:
        """Classify the type of table based on content"""
        
        headers = table.get('headers', [])
        
        # Look for common table types based on headers
        header_text = ' '.join(headers).lower()
        
        if any(word in header_text for word in ['date', 'time', 'month', 'year']):
            if any(word in header_text for word in ['amount', 'total', 'cost', 'price', 'revenue']):
                return 'financial_time_series'
            else:
                return 'time_series'
        
        if any(word in header_text for word in ['name', 'person', 'employee', 'customer']):
            return 'contact_list'
        
        if any(word in header_text for word in ['product', 'item', 'inventory', 'stock']):
            return 'inventory'
        
        if any(word in header_text for word in ['invoice', 'bill', 'payment', 'transaction']):
            return 'financial'
        
        # Check column types
        numeric_columns = sum(1 for col in analysis['column_analysis'] if col['type'] == 'numeric')
        total_columns = len(analysis['column_analysis'])
        
        if numeric_columns / total_columns > 0.6:
            return 'numerical_data'
        
        return 'general'
    
    def _convert_to_structured_data(self, tables: List[Dict], options: Dict) -> Dict:
        """Convert tables to structured data formats"""
        
        structured_data = {
            'formats': {},
            'schemas': [],
            'relationships': []
        }
        
        for table_idx, table in enumerate(tables):
            table_id = f"table_{table_idx + 1}"
            
            # Convert to different formats
            formats = {}
            
            # JSON format
            formats['json'] = self._convert_table_to_json(table)
            
            # DataFrame-like structure
            formats['records'] = self._convert_table_to_records(table)
            
            # Schema definition
            schema = self._generate_table_schema(table, table_id)
            structured_data['schemas'].append(schema)
            
            structured_data['formats'][table_id] = formats
        
        # Detect relationships between tables
        if len(tables) > 1:
            relationships = self._detect_table_relationships(tables)
            structured_data['relationships'] = relationships
        
        return structured_data
    
    def _convert_table_to_json(self, table: Dict) -> Dict:
        """Convert table to JSON format"""
        
        headers = table.get('headers', [])
        data_rows = table.get('data_rows', table.get('data', []))
        
        if not headers and data_rows:
            # Use first row as headers if no headers detected
            headers = data_rows[0]
            data_rows = data_rows[1:]
        
        # Convert to list of dictionaries
        records = []
        for row in data_rows:
            record = {}
            for col_idx, header in enumerate(headers):
                value = row[col_idx] if col_idx < len(row) else ''
                
                # Convert value based on detected type
                column_types = table.get('column_types', [])
                if col_idx < len(column_types):
                    value = self._convert_value_by_type(value, column_types[col_idx])
                
                record[header or f'column_{col_idx + 1}'] = value
            
            records.append(record)
        
        return {
            'headers': headers,
            'records': records,
            'row_count': len(records),
            'column_count': len(headers)
        }
    
    def _convert_table_to_records(self, table: Dict) -> List[List]:
        """Convert table to simple records format"""
        
        data = table.get('data', [])
        
        # Apply type conversion
        converted_data = []
        column_types = table.get('column_types', [])
        
        for row in data:
            converted_row = []
            for col_idx, cell in enumerate(row):
                if col_idx < len(column_types):
                    converted_value = self._convert_value_by_type(cell, column_types[col_idx])
                else:
                    converted_value = cell
                converted_row.append(converted_value)
            
            converted_data.append(converted_row)
        
        return converted_data
    
    def _convert_value_by_type(self, value: str, data_type: str):
        """Convert string value to appropriate type"""
        
        if not value or not value.strip():
            return None
        
        value = value.strip()
        
        try:
            if data_type == 'numeric':
                # Remove formatting and convert to number
                cleaned_value = re.sub(r'[,$%\s]', '', value)
                if '.' in cleaned_value:
                    return float(cleaned_value)
                else:
                    return int(cleaned_value)
            
            elif data_type == 'boolean':
                return value.lower() in ['true', 'yes', 'y', '1']
            
            elif data_type == 'date':
                # Would need proper date parsing here
                return value
            
            else:
                return value
                
        except (ValueError, TypeError):
            return value
    
    def _generate_table_schema(self, table: Dict, table_id: str) -> Dict:
        """Generate schema definition for table"""
        
        headers = table.get('headers', [])
        column_types = table.get('column_types', [])
        analysis = table.get('analysis', {})
        
        fields = []
        for col_idx, header in enumerate(headers):
            field = {
                'name': header or f'column_{col_idx + 1}',
                'type': column_types[col_idx] if col_idx < len(column_types) else 'text',
                'index': col_idx,
                'nullable': True  # Default assumption
            }
            
            # Add column-specific analysis
            if col_idx < len(analysis.get('column_analysis', [])):
                col_analysis = analysis['column_analysis'][col_idx]
                field.update({
                    'unique_values': col_analysis.get('unique_values', 0),
                    'empty_cells': col_analysis.get('empty_cells', 0)
                })
            
            fields.append(field)
        
        return {
            'table_id': table_id,
            'table_type': analysis.get('table_type', 'unknown'),
            'fields': fields,
            'row_count': table.get('rows', 0),
            'column_count': table.get('columns', 0),
            'has_header': table.get('has_header', False)
        }
    
    def _detect_table_relationships(self, tables: List[Dict]) -> List[Dict]:
        """Detect relationships between tables"""
        
        relationships = []
        
        # Simple relationship detection based on common columns
        for i, table1 in enumerate(tables):
            for j, table2 in enumerate(tables[i+1:], i+1):
                headers1 = set(table1.get('headers', []))
                headers2 = set(table2.get('headers', []))
                
                # Find common headers
                common_headers = headers1.intersection(headers2)
                
                if common_headers:
                    relationship = {
                        'table1_index': i,
                        'table2_index': j,
                        'relationship_type': 'common_columns',
                        'common_columns': list(common_headers),
                        'strength': len(common_headers) / max(len(headers1), len(headers2))
                    }
                    
                    relationships.append(relationship)
        
        return relationships
    
    def _analyze_table_content(self, tables: List[Dict]) -> Dict:
        """Analyze content across all tables"""
        
        analysis = {
            'total_tables': len(tables),
            'table_types': {},
            'total_rows': 0,
            'total_columns': 0,
            'data_type_distribution': {},
            'quality_metrics': {}
        }
        
        # Aggregate statistics
        for table in tables:
            analysis['total_rows'] += table.get('rows', 0)
            analysis['total_columns'] += table.get('columns', 0)
            
            # Table type distribution
            table_type = table.get('analysis', {}).get('table_type', 'unknown')
            if table_type not in analysis['table_types']:
                analysis['table_types'][table_type] = 0
            analysis['table_types'][table_type] += 1
            
            # Data type distribution
            for col_type in table.get('column_types', []):
                if col_type not in analysis['data_type_distribution']:
                    analysis['data_type_distribution'][col_type] = 0
                analysis['data_type_distribution'][col_type] += 1
        
        # Quality metrics
        if tables:
            avg_confidence = sum(table.get('confidence', 0) for table in tables) / len(tables)
            avg_data_density = sum(table.get('analysis', {}).get('data_density', 0) for table in tables) / len(tables)
            
            analysis['quality_metrics'] = {
                'average_confidence': avg_confidence,
                'average_data_density': avg_data_density,
                'tables_with_headers': sum(1 for table in tables if table.get('has_header', False))
            }
        
        return analysis
    
    def _calculate_table_statistics(self, result: Dict) -> Dict:
        """Calculate extraction statistics"""
        
        stats = {
            'extraction_summary': {
                'total_tables_found': len(result.get('tables', [])),
                'methods_used': len(result.get('extraction_methods', {})),
                'successful_methods': len([m for m in result.get('extraction_methods', {}).values() if 'error' not in m])
            },
            'method_performance': {},
            'table_distribution': {}
        }
        
        # Method performance
        for method, method_result in result.get('extraction_methods', {}).items():
            if 'error' in method_result:
                stats['method_performance'][method] = {
                    'status': 'failed',
                    'error': method_result['error']
                }
            else:
                table_count = len(method_result.get('tables', []))
                stats['method_performance'][method] = {
                    'status': 'success',
                    'tables_found': table_count
                }
        
        # Table size distribution
        if result.get('tables'):
            sizes = [(table.get('rows', 0), table.get('columns', 0)) for table in result['tables']]
            stats['table_distribution'] = {
                'size_range': {
                    'min_rows': min(size[0] for size in sizes),
                    'max_rows': max(size[0] for size in sizes),
                    'min_columns': min(size[1] for size in sizes),
                    'max_columns': max(size[1] for size in sizes)
                },
                'average_size': {
                    'rows': sum(size[0] for size in sizes) / len(sizes),
                    'columns': sum(size[1] for size in sizes) / len(sizes)
                }
            }
        
        return stats
    
    def _extract_pdf_metadata(self, file_path: str) -> Dict:
        """Extract metadata from PDF"""
        
        metadata = {}
        
        try:
            doc = fitz.open(file_path)
            metadata = doc.metadata
            metadata['page_count'] = len(doc)
            doc.close()
        except Exception as e:
            self.logger.warning(f"Failed to extract PDF metadata: {str(e)}")
        
        return metadata
    
    def _save_table_results(self, results: Dict, options: Dict):
        """Save table extraction results"""
        
        try:
            session_id = results['session_id']
            
            # Save main results as JSON
            output_file = os.path.join(self.output_dir, f"tables_{session_id}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Table results saved to {output_file}")
            
            # Save individual tables in requested formats
            output_formats = options.get('output_formats', ['csv', 'json'])
            
            for table_idx, table in enumerate(results.get('tables', [])):
                table_id = f"table_{table_idx + 1}"
                
                for fmt in output_formats:
                    if fmt in self.output_formats:
                        self._save_table_in_format(table, table_id, session_id, fmt)
            
        except Exception as e:
            self.logger.warning(f"Failed to save table results: {str(e)}")
    
    def _save_table_in_format(self, table: Dict, table_id: str, session_id: str, format: str):
        """Save individual table in specified format"""
        
        try:
            if format == 'csv':
                filename = f"{session_id}_{table_id}.csv"
                filepath = os.path.join(self.output_dir, filename)
                
                # Convert to DataFrame and save
                headers = table.get('headers', [])
                data_rows = table.get('data_rows', table.get('data', []))
                
                if headers and data_rows:
                    df = pd.DataFrame(data_rows, columns=headers)
                else:
                    df = pd.DataFrame(data_rows)
                
                df.to_csv(filepath, index=False)
            
            elif format == 'xlsx':
                filename = f"{session_id}_{table_id}.xlsx"
                filepath = os.path.join(self.output_dir, filename)
                
                headers = table.get('headers', [])
                data_rows = table.get('data_rows', table.get('data', []))
                
                if headers and data_rows:
                    df = pd.DataFrame(data_rows, columns=headers)
                else:
                    df = pd.DataFrame(data_rows)
                
                df.to_excel(filepath, index=False)
            
            elif format == 'json':
                filename = f"{session_id}_{table_id}.json"
                filepath = os.path.join(self.output_dir, filename)
                
                table_json = self._convert_table_to_json(table)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(table_json, f, indent=2, ensure_ascii=False, default=str)
            
            elif format == 'html':
                filename = f"{session_id}_{table_id}.html"
                filepath = os.path.join(self.output_dir, filename)
                
                headers = table.get('headers', [])
                data_rows = table.get('data_rows', table.get('data', []))
                
                if headers and data_rows:
                    df = pd.DataFrame(data_rows, columns=headers)
                else:
                    df = pd.DataFrame(data_rows)
                
                html_content = df.to_html(index=False)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(html_content)
            
            elif format == 'markdown':
                filename = f"{session_id}_{table_id}.md"
                filepath = os.path.join(self.output_dir, filename)
                
                headers = table.get('headers', [])
                data_rows = table.get('data_rows', table.get('data', []))
                
                markdown_content = self._convert_table_to_markdown(headers, data_rows)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                    
        except Exception as e:
            self.logger.warning(f"Failed to save table in {format} format: {str(e)}")
    
    def _convert_table_to_markdown(self, headers: List[str], data_rows: List[List[str]]) -> str:
        """Convert table to Markdown format"""
        
        if not headers or not data_rows:
            return ""
        
        # Create header row
        header_row = "| " + " | ".join(headers) + " |"
        
        # Create separator row
        separator_row = "| " + " | ".join(["---"] * len(headers)) + " |"
        
        # Create data rows
        markdown_rows = [header_row, separator_row]
        
        for row in data_rows:
            # Pad row to match header length
            padded_row = row + [""] * (len(headers) - len(row))
            markdown_row = "| " + " | ".join(padded_row[:len(headers)]) + " |"
            markdown_rows.append(markdown_row)
        
        return "\n".join(markdown_rows)

def main():
    """Command line interface for table extraction"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract tables from documents')
    parser.add_argument('file_path', help='Path to the document file')
    parser.add_argument('--output-dir', default='./output/tables', help='Output directory')
    parser.add_argument('--methods', nargs='+', default=['pdfplumber', 'tabula'], 
                       help='Extraction methods to use')
    parser.add_argument('--output-formats', nargs='+', default=['csv', 'json'], 
                       help='Output formats for tables')
    parser.add_argument('--confidence-threshold', type=float, default=0.8, 
                       help='Confidence threshold for ML detection')
    
    args = parser.parse_args()
    
    # Configure extractor
    config = {
        'output_dir': args.output_dir,
        'extraction_methods': args.methods,
        'confidence_threshold': args.confidence_threshold
    }
    
    options = {
        'output_formats': args.output_formats
    }
    
    # Extract tables
    extractor = TableExtractor(config)
    result = extractor.extract_tables(args.file_path, options)
    
    # Print results
    if 'tables' in result:
        print(f"✓ Table extraction completed")
        print(f"  Session ID: {result['session_id']}")
        print(f"  Tables found: {len(result['tables'])}")
        print(f"  Methods used: {list(result.get('extraction_methods', {}).keys())}")
        
        for i, table in enumerate(result['tables']):
            print(f"\n  Table {i + 1}:")
            print(f"    Size: {table.get('rows', 0)} rows × {table.get('columns', 0)} columns")
            print(f"    Method: {table.get('extraction_method', 'unknown')}")
            print(f"    Confidence: {table.get('confidence', 0):.2f}")
            if table.get('analysis'):
                print(f"    Type: {table['analysis'].get('table_type', 'unknown')}")
    else:
        print(f"✗ Table extraction failed: {result.get('error', 'Unknown error')}")

if __name__ == '__main__':
    main()