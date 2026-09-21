#!/usr/bin/env python3
"""
System Cleanup and Dependency Optimizer
Removes unused code, optimizes imports, and cleans up redundant dependencies
"""

import os
import sys
import re
import json
import shutil
from pathlib import Path
from typing import Set, Dict, List
import subprocess

class SystemCleaner:
    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)
        self.removed_files = []
        self.optimized_files = []
        self.cleaned_dependencies = {}
        
    def clean_python_cache(self):
        """Remove Python cache files and directories"""
        print("🧹 Cleaning Python cache files...")
        
        cache_patterns = [
            "**/__pycache__",
            "**/*.pyc", 
            "**/*.pyo",
            "**/.pytest_cache",
            "**/*.egg-info"
        ]
        
        for pattern in cache_patterns:
            for path in self.root_dir.glob(pattern):
                if path.is_dir():
                    shutil.rmtree(path)
                    print(f"  Removed directory: {path}")
                else:
                    path.unlink()
                    print(f"  Removed file: {path}")
                self.removed_files.append(str(path))
    
    def clean_log_files(self, days_old: int = 7):
        """Clean old log files"""
        print(f"🧹 Cleaning log files older than {days_old} days...")
        
        import time
        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        
        for log_file in self.root_dir.glob("**/*.log"):
            try:
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    print(f"  Removed old log: {log_file}")
                    self.removed_files.append(str(log_file))
            except OSError:
                pass
    
    def optimize_python_imports(self):
        """Optimize Python imports and remove unused ones"""
        print("🐍 Optimizing Python imports...")
        
        for py_file in self.root_dir.glob("**/*.py"):
            if "venv" in str(py_file) or "node_modules" in str(py_file):
                continue
                
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                original_content = content
                
                # Remove duplicate imports
                lines = content.split('\n')
                import_lines = []
                other_lines = []
                seen_imports = set()
                
                for line in lines:
                    stripped = line.strip()
                    if (stripped.startswith('import ') or stripped.startswith('from ')) and not stripped.startswith('#'):
                        if stripped not in seen_imports:
                            seen_imports.add(stripped)
                            import_lines.append(line)
                    else:
                        other_lines.append(line)
                
                # Separate standard library, third-party, and local imports
                stdlib_imports = []
                thirdparty_imports = []
                local_imports = []
                
                python_stdlib = {
                    'os', 'sys', 'json', 'time', 'datetime', 'logging', 're', 'collections',
                    'typing', 'pathlib', 'subprocess', 'threading', 'asyncio', 'sqlite3',
                    'hashlib', 'base64', 'io', 'pickle', 'contextlib', 'functools', 'itertools'
                }
                
                for imp in import_lines:
                    module_name = self._extract_module_name(imp.strip())
                    if module_name in python_stdlib:
                        stdlib_imports.append(imp)
                    elif '.' in module_name or module_name.startswith('services/'):
                        local_imports.append(imp)
                    else:
                        thirdparty_imports.append(imp)
                
                # Reconstruct file with organized imports
                organized_imports = []
                if stdlib_imports:
                    organized_imports.extend(sorted(stdlib_imports))
                    organized_imports.append('')
                if thirdparty_imports:
                    organized_imports.extend(sorted(thirdparty_imports))
                    organized_imports.append('')
                if local_imports:
                    organized_imports.extend(sorted(local_imports))
                    organized_imports.append('')
                
                new_content = '\n'.join(organized_imports + other_lines)
                
                if new_content != original_content:
                    with open(py_file, 'w') as f:
                        f.write(new_content)
                    print(f"  Optimized imports in: {py_file}")
                    self.optimized_files.append(str(py_file))
                    
            except Exception as e:
                print(f"  Warning: Could not optimize {py_file}: {e}")
    
    def _extract_module_name(self, import_line: str) -> str:
        """Extract module name from import statement"""
        if import_line.startswith('from '):
            # from module import ...
            return import_line.split()[1]
        elif import_line.startswith('import '):
            # import module
            module = import_line.split()[1].split('.')[0]
            return module.split(' as ')[0]
        return ""
    
    def clean_unused_dependencies(self):
        """Find and report unused dependencies in package.json files"""
        print("📦 Analyzing JavaScript dependencies...")
        
        for package_file in self.root_dir.glob("**/package.json"):
            if "node_modules" in str(package_file):
                continue
                
            try:
                with open(package_file, 'r') as f:
                    package_data = json.load(f)
                
                dependencies = package_data.get('dependencies', {})
                dev_dependencies = package_data.get('devDependencies', {})
                
                # Find JavaScript files in the same directory
                js_files = []
                package_dir = package_file.parent
                for ext in ['**/*.js', '**/*.jsx', '**/*.ts', '**/*.tsx']:
                    js_files.extend(package_dir.glob(ext))
                
                # Read all JS content to find imports
                all_js_content = ""
                for js_file in js_files:
                    if "node_modules" not in str(js_file):
                        try:
                            with open(js_file, 'r') as f:
                                all_js_content += f.read() + "\n"
                        except:
                            pass
                
                # Find potentially unused dependencies
                unused_deps = []
                for dep_name in dependencies:
                    # Simple check if dependency is imported/required
                    import_patterns = [
                        f"import.*from.*['\"{dep_name}]",
                        f"require\\(['\"{dep_name}]",
                        f"import.*['\"{dep_name}]"
                    ]
                    
                    found = False
                    for pattern in import_patterns:
                        if re.search(pattern, all_js_content, re.IGNORECASE):
                            found = True
                            break
                    
                    if not found and dep_name not in ['react', 'react-dom', 'next']:  # Keep essential deps
                        unused_deps.append(dep_name)
                
                if unused_deps:
                    self.cleaned_dependencies[str(package_file)] = unused_deps
                    print(f"  Potentially unused deps in {package_file}: {unused_deps}")
                    
            except Exception as e:
                print(f"  Warning: Could not analyze {package_file}: {e}")
    
    def remove_empty_directories(self):
        """Remove empty directories"""
        print("📁 Removing empty directories...")
        
        for path in self.root_dir.rglob('*'):
            if path.is_dir() and not any(path.iterdir()):
                if path.name not in ['.git', 'node_modules', '__pycache__']:
                    try:
                        path.rmdir()
                        print(f"  Removed empty directory: {path}")
                        self.removed_files.append(str(path))
                    except OSError:
                        pass
    
    def find_duplicate_files(self):
        """Find potential duplicate files"""
        print("🔍 Finding duplicate files...")
        
        file_sizes = {}
        for file_path in self.root_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix in ['.py', '.js', '.css']:
                try:
                    size = file_path.stat().st_size
                    if size in file_sizes:
                        file_sizes[size].append(file_path)
                    else:
                        file_sizes[size] = [file_path]
                except OSError:
                    pass
        
        # Find files with same size (potential duplicates)
        potential_duplicates = {size: files for size, files in file_sizes.items() if len(files) > 1}
        
        for size, files in potential_duplicates.items():
            if size > 1024:  # Only check files larger than 1KB
                print(f"  Potential duplicates ({size} bytes): {[str(f) for f in files]}")
    
    def optimize_service_configs(self):
        """Optimize service configuration files"""
        print("⚙️ Optimizing service configurations...")
        
        # Common optimizations for Python service main files
        for main_file in self.root_dir.glob("**/services/*/main.py"):
            try:
                with open(main_file, 'r') as f:
                    content = f.read()
                
                # Check for common performance issues
                if 'time.sleep' in content and 'asyncio' in content:
                    print(f"  ⚠️  Found blocking sleep in async service: {main_file}")
                
                if 'sqlite3.connect' in content and content.count('sqlite3.connect') > 3:
                    print(f"  ⚠️  Many DB connections in: {main_file} - consider connection pooling")
                
                if 'while True:' in content:
                    print(f"  ℹ️  Found infinite loop in: {main_file} - ensure proper error handling")
                    
            except Exception as e:
                pass
    
    def generate_cleanup_report(self):
        """Generate cleanup report"""
        report_file = self.root_dir / "cleanup_report.json"
        
        report = {
            "timestamp": str(subprocess.check_output(['date'], text=True).strip()),
            "removed_files": self.removed_files,
            "optimized_files": self.optimized_files,
            "cleaned_dependencies": self.cleaned_dependencies,
            "statistics": {
                "files_removed": len(self.removed_files),
                "files_optimized": len(self.optimized_files),
                "packages_with_unused_deps": len(self.cleaned_dependencies)
            }
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📊 Cleanup report saved to: {report_file}")
        return report
    
    def run_full_cleanup(self):
        """Run all cleanup operations"""
        print("🚀 Starting full system cleanup...")
        print("=" * 50)
        
        self.clean_python_cache()
        print()
        
        self.clean_log_files()
        print()
        
        self.optimize_python_imports()
        print()
        
        self.clean_unused_dependencies()
        print()
        
        self.remove_empty_directories()
        print()
        
        self.find_duplicate_files()
        print()
        
        self.optimize_service_configs()
        print()
        
        report = self.generate_cleanup_report()
        print()
        
        print("✨ Cleanup Summary:")
        print(f"  - Files removed: {report['statistics']['files_removed']}")
        print(f"  - Files optimized: {report['statistics']['files_optimized']}")
        print(f"  - Packages with unused deps: {report['statistics']['packages_with_unused_deps']}")
        print()
        print("🎉 System cleanup completed!")

def main():
    if len(sys.argv) > 1:
        root_dir = sys.argv[1]
    else:
        root_dir = "."
    
    cleaner = SystemCleaner(root_dir)
    cleaner.run_full_cleanup()

if __name__ == "__main__":
    main()