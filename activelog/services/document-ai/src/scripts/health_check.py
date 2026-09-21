#!/usr/bin/env python3

import json
import sys
import importlib
import traceback

def check_dependencies():
    """Check if all required Python dependencies are available."""
    required_packages = [
        'PyPDF2', 'pdfplumber', 'fitz', 'pdf2image', 'pytesseract',
        'pillow', 'numpy', 'pandas', 'openpyxl', 'beautifulsoup4',
        'spacy', 'nltk', 'transformers', 'torch', 'langdetect',
        'googletrans', 'chromadb', 'faiss', 'sentence_transformers',
        'tabula', 'camelot', 'scikit_learn'
    ]
    
    available = {}
    missing = []
    
    for package in required_packages:
        try:
            if package == 'fitz':
                importlib.import_module('fitz')
            elif package == 'pillow':
                importlib.import_module('PIL')
            elif package == 'beautifulsoup4':
                importlib.import_module('bs4')
            elif package == 'scikit_learn':
                importlib.import_module('sklearn')
            else:
                importlib.import_module(package)
            available[package] = True
        except ImportError:
            available[package] = False
            missing.append(package)
    
    return available, missing

def check_models():
    """Check if required models are available."""
    models_status = {}
    
    # Check spaCy models
    try:
        import spacy
        try:
            nlp = spacy.load("en_core_web_sm")
            models_status['spacy_en'] = True
        except OSError:
            models_status['spacy_en'] = False
    except:
        models_status['spacy_en'] = False
    
    # Check NLTK data
    try:
        import nltk
        try:
            nltk.data.find('tokenizers/punkt')
            models_status['nltk_punkt'] = True
        except LookupError:
            models_status['nltk_punkt'] = False
        
        try:
            nltk.data.find('taggers/averaged_perceptron_tagger')
            models_status['nltk_pos'] = True
        except LookupError:
            models_status['nltk_pos'] = False
        
        try:
            nltk.data.find('chunkers/maxent_ne_chunker')
            models_status['nltk_ner'] = True
        except LookupError:
            models_status['nltk_ner'] = False
    except:
        models_status['nltk_punkt'] = False
        models_status['nltk_pos'] = False
        models_status['nltk_ner'] = False
    
    return models_status

def check_system_tools():
    """Check if system tools are available."""
    tools_status = {}
    
    # Check Tesseract
    try:
        import pytesseract
        tesseract_version = pytesseract.get_tesseract_version()
        tools_status['tesseract'] = {
            'available': True,
            'version': str(tesseract_version)
        }
    except Exception as e:
        tools_status['tesseract'] = {
            'available': False,
            'error': str(e)
        }
    
    # Check Java (for tabula)
    import subprocess
    try:
        result = subprocess.run(['java', '-version'], 
                              capture_output=True, text=True, timeout=5)
        tools_status['java'] = {
            'available': result.returncode == 0,
            'version': result.stderr.split('\n')[0] if result.returncode == 0 else None
        }
    except Exception as e:
        tools_status['java'] = {
            'available': False,
            'error': str(e)
        }
    
    return tools_status

def main():
    try:
        # Check dependencies
        available_packages, missing_packages = check_dependencies()
        
        # Check models
        models_status = check_models()
        
        # Check system tools
        tools_status = check_system_tools()
        
        # Overall health status
        all_critical_available = all([
            available_packages.get('PyPDF2', False),
            available_packages.get('pytesseract', False),
            available_packages.get('spacy', False),
            available_packages.get('transformers', False)
        ])
        
        health_status = {
            'status': 'healthy' if all_critical_available else 'degraded',
            'timestamp': str(datetime.now()) if 'datetime' in globals() else None,
            'dependencies': {
                'available': available_packages,
                'missing': missing_packages,
                'critical_missing': len(missing_packages) > 0
            },
            'models': models_status,
            'system_tools': tools_status,
            'recommendations': []
        }
        
        # Add recommendations
        if missing_packages:
            health_status['recommendations'].append(
                f"Install missing packages: {', '.join(missing_packages)}"
            )
        
        if not models_status.get('spacy_en', False):
            health_status['recommendations'].append(
                "Download spaCy English model: python -m spacy download en_core_web_sm"
            )
        
        if not models_status.get('nltk_punkt', False):
            health_status['recommendations'].append(
                "Download NLTK data: python -c \"import nltk; nltk.download('punkt'); nltk.download('averaged_perceptron_tagger'); nltk.download('maxent_ne_chunker'); nltk.download('words')\""
            )
        
        if not tools_status.get('tesseract', {}).get('available', False):
            health_status['recommendations'].append(
                "Install Tesseract OCR: apt-get install tesseract-ocr (Ubuntu/Debian) or brew install tesseract (macOS)"
            )
        
        print(json.dumps(health_status, indent=2))
        
    except Exception as e:
        error_response = {
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc()
        }
        print(json.dumps(error_response, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()