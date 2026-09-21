#!/usr/bin/env python3
"""
Quick import fixer for dmlog-core service
Converts relative imports to absolute imports for SuperInstance compatibility
"""

import os
import re
from pathlib import Path

def fix_imports(file_path: Path):
    """Fix relative imports in a Python file"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Fix relative imports from ..services to services
        content = re.sub(r'from \.\.services\.', 'from services.', content)
        
        # Fix relative imports from ..models to models  
        content = re.sub(r'from \.\.models\.', 'from models.', content)
        
        # Fix relative imports from ..config to config
        content = re.sub(r'from \.\.config', 'from config', content)
        
        # Fix relative imports from ..database to database
        content = re.sub(r'from \.\.database', 'from database', content)
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Fixed imports in {file_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False

def main():
    """Fix all imports in dmlog-core"""
    dmlog_path = Path('/home/activeloguser/activelog/services/dmlog-core')
    
    if not dmlog_path.exists():
        print("❌ dmlog-core directory not found")
        return
    
    print("🔧 Fixing dmlog-core relative imports...")
    
    # Find all Python files with relative imports
    python_files = []
    for pattern in ['**/*.py']:
        python_files.extend(dmlog_path.glob(pattern))
    
    fixed_count = 0
    total_count = 0
    
    for py_file in python_files:
        if '__pycache__' in str(py_file):
            continue
            
        # Check if file has relative imports
        try:
            with open(py_file, 'r') as f:
                content = f.read()
            
            if 'from ..' in content:
                total_count += 1
                if fix_imports(py_file):
                    fixed_count += 1
                    
        except Exception as e:
            print(f"⚠️  Could not read {py_file}: {e}")
    
    print(f"\n🎉 Import fixing complete!")
    print(f"📊 Fixed {fixed_count}/{total_count} files")
    
    if fixed_count == total_count:
        print("✅ All imports fixed successfully")
        return True
    else:
        print("⚠️  Some files may need manual review")
        return False

if __name__ == "__main__":
    main()