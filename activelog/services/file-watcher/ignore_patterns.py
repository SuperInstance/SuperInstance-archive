"""
Ignore patterns implementation (.gitignore style)
Handles pattern matching for files and directories to ignore during watching
"""
import os
import re
import fnmatch
from typing import List, Set, Optional, Dict, Pattern
from pathlib import Path
import pathspec
import logging

logger = logging.getLogger(__name__)

class IgnorePatternMatcher:
    """Handles .gitignore style pattern matching"""
    
    def __init__(self):
        self.global_patterns: List[str] = []
        self.directory_patterns: Dict[str, List[str]] = {}
        self.compiled_specs: Dict[str, pathspec.PathSpec] = {}
        
        # Default ignore patterns
        self.default_patterns = [
            # System files
            '.DS_Store',
            'Thumbs.db',
            'desktop.ini',
            
            # Temporary files
            '*.tmp',
            '*.temp',
            '*.swp',
            '*.swo',
            '*~',
            
            # Version control
            '.git/',
            '.svn/',
            '.hg/',
            '.bzr/',
            
            # IDE and editor files
            '.vscode/',
            '.idea/',
            '*.sublime-*',
            
            # Build and dependency directories
            'node_modules/',
            '__pycache__/',
            '*.pyc',
            '.tox/',
            'dist/',
            'build/',
            
            # Logs
            '*.log',
            'logs/',
            
            # OS generated files
            '*.lnk',
            '*.url',
            
            # ActiveLog specific
            '.activelog/',
            '.activelog-cache/',
            '.activelog-temp/'
        ]
        
        self.load_default_patterns()
    
    def load_default_patterns(self):
        """Load default ignore patterns"""
        self.global_patterns = self.default_patterns.copy()
        self._compile_global_spec()
    
    def add_global_pattern(self, pattern: str):
        """Add a global ignore pattern"""
        if pattern not in self.global_patterns:
            self.global_patterns.append(pattern)
            self._compile_global_spec()
    
    def add_global_patterns(self, patterns: List[str]):
        """Add multiple global ignore patterns"""
        for pattern in patterns:
            if pattern not in self.global_patterns:
                self.global_patterns.append(pattern)
        self._compile_global_spec()
    
    def load_ignore_file(self, file_path: str, directory: Optional[str] = None):
        """Load patterns from an ignore file (like .gitignore)"""
        try:
            if not os.path.exists(file_path):
                return
            
            patterns = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    patterns.append(line)
            
            if directory:
                # Directory-specific patterns
                if directory not in self.directory_patterns:
                    self.directory_patterns[directory] = []
                
                self.directory_patterns[directory].extend(patterns)
                self._compile_directory_spec(directory)
            else:
                # Global patterns
                self.add_global_patterns(patterns)
            
            logger.info(f"Loaded {len(patterns)} patterns from {file_path}")
            
        except Exception as e:
            logger.warning(f"Failed to load ignore file {file_path}: {e}")
    
    def load_directory_ignore_files(self, directory: str, ignore_filename: str = ".activelog-ignore"):
        """Load ignore files from directory and its parents"""
        directory = os.path.abspath(directory)
        
        # Look for ignore files in directory hierarchy
        current_dir = directory
        while current_dir != os.path.dirname(current_dir):  # Not at root
            ignore_file = os.path.join(current_dir, ignore_filename)
            if os.path.exists(ignore_file):
                self.load_ignore_file(ignore_file, current_dir)
            
            # Also check for .gitignore
            gitignore_file = os.path.join(current_dir, '.gitignore')
            if os.path.exists(gitignore_file):
                self.load_ignore_file(gitignore_file, current_dir)
            
            current_dir = os.path.dirname(current_dir)
    
    def _compile_global_spec(self):
        """Compile global patterns into PathSpec"""
        try:
            self.compiled_specs['global'] = pathspec.PathSpec.from_lines('gitwildmatch', self.global_patterns)
        except Exception as e:
            logger.warning(f"Failed to compile global patterns: {e}")
            self.compiled_specs['global'] = pathspec.PathSpec([])
    
    def _compile_directory_spec(self, directory: str):
        """Compile directory-specific patterns into PathSpec"""
        try:
            patterns = self.directory_patterns.get(directory, [])
            self.compiled_specs[directory] = pathspec.PathSpec.from_lines('gitwildmatch', patterns)
        except Exception as e:
            logger.warning(f"Failed to compile patterns for {directory}: {e}")
            self.compiled_specs[directory] = pathspec.PathSpec([])
    
    def should_ignore(self, file_path: str, base_directory: Optional[str] = None) -> bool:
        """Check if a file should be ignored"""
        
        # Normalize path
        file_path = os.path.normpath(file_path)
        
        # Check global patterns
        relative_path = file_path
        if base_directory:
            try:
                relative_path = os.path.relpath(file_path, base_directory)
            except ValueError:
                # Different drives on Windows, use absolute path
                relative_path = file_path
        
        # Check global ignore patterns
        global_spec = self.compiled_specs.get('global')
        if global_spec and global_spec.match_file(relative_path):
            return True
        
        # Check directory-specific patterns
        if base_directory:
            # Check patterns for this directory and its parents
            current_dir = os.path.dirname(file_path)
            while current_dir and current_dir != os.path.dirname(current_dir):
                dir_spec = self.compiled_specs.get(current_dir)
                if dir_spec:
                    try:
                        check_path = os.path.relpath(file_path, current_dir)
                        if dir_spec.match_file(check_path):
                            return True
                    except ValueError:
                        pass
                
                current_dir = os.path.dirname(current_dir)
        
        return False
    
    def filter_paths(self, paths: List[str], base_directory: Optional[str] = None) -> List[str]:
        """Filter a list of paths, removing ignored ones"""
        return [path for path in paths if not self.should_ignore(path, base_directory)]
    
    def get_patterns_for_directory(self, directory: str) -> List[str]:
        """Get all applicable patterns for a directory"""
        patterns = self.global_patterns.copy()
        
        # Add directory-specific patterns
        if directory in self.directory_patterns:
            patterns.extend(self.directory_patterns[directory])
        
        return patterns
    
    def add_pattern_for_directory(self, directory: str, pattern: str):
        """Add a pattern specific to a directory"""
        if directory not in self.directory_patterns:
            self.directory_patterns[directory] = []
        
        if pattern not in self.directory_patterns[directory]:
            self.directory_patterns[directory].append(pattern)
            self._compile_directory_spec(directory)
    
    def remove_pattern_for_directory(self, directory: str, pattern: str):
        """Remove a pattern from a directory"""
        if directory in self.directory_patterns:
            try:
                self.directory_patterns[directory].remove(pattern)
                self._compile_directory_spec(directory)
            except ValueError:
                pass
    
    def clear_directory_patterns(self, directory: str):
        """Clear all patterns for a directory"""
        if directory in self.directory_patterns:
            del self.directory_patterns[directory]
        
        if directory in self.compiled_specs:
            del self.compiled_specs[directory]
    
    def get_statistics(self) -> Dict[str, int]:
        """Get statistics about loaded patterns"""
        return {
            'global_patterns': len(self.global_patterns),
            'directory_patterns': len(self.directory_patterns),
            'total_directories': len(self.directory_patterns),
            'total_patterns': len(self.global_patterns) + sum(len(patterns) for patterns in self.directory_patterns.values())
        }

class PatternValidator:
    """Validates ignore patterns for correctness"""
    
    @staticmethod
    def validate_pattern(pattern: str) -> Dict[str, any]:
        """Validate a pattern and return validation result"""
        result = {
            'valid': True,
            'warnings': [],
            'errors': []
        }
        
        if not pattern or not pattern.strip():
            result['valid'] = False
            result['errors'].append("Pattern cannot be empty")
            return result
        
        pattern = pattern.strip()
        
        # Check for dangerous patterns
        if pattern in ['*', '**', '/']:
            result['valid'] = False
            result['errors'].append("Pattern would match everything")
            return result
        
        # Check for invalid characters
        invalid_chars = ['<', '>', '|', '"']
        for char in invalid_chars:
            if char in pattern:
                result['warnings'].append(f"Pattern contains potentially problematic character: {char}")
        
        # Try to compile the pattern
        try:
            pathspec.PathSpec.from_lines('gitwildmatch', [pattern])
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"Pattern compilation failed: {e}")
        
        # Check for common mistakes
        if pattern.startswith('./'):
            result['warnings'].append("Leading './' is unnecessary")
        
        if pattern.endswith('/') and not pattern.endswith('*/'):
            result['warnings'].append("Directory patterns should end with '/' or use '**/'")
        
        return result
    
    @staticmethod
    def suggest_improvements(pattern: str) -> List[str]:
        """Suggest improvements for a pattern"""
        suggestions = []
        
        if pattern.startswith('./'):
            suggestions.append(f"Remove leading './': {pattern[2:]}")
        
        if pattern.count('*') > 2 and '**' not in pattern:
            suggestions.append("Consider using '**' for recursive matching")
        
        if not pattern.startswith('/') and not pattern.startswith('*'):
            suggestions.append(f"Consider making absolute: /{pattern}")
        
        return suggestions

class FileTypeFilter:
    """Filter files by type and extension"""
    
    def __init__(self):
        self.include_extensions: Set[str] = set()
        self.exclude_extensions: Set[str] = set()
        self.include_mimetypes: Set[str] = set()
        self.exclude_mimetypes: Set[str] = set()
        
        # Default excluded extensions
        self.default_exclude_extensions = {
            # Temporary and cache files
            '.tmp', '.temp', '.cache', '.bak', '.backup',
            
            # System files
            '.DS_Store', '.localized',
            
            # Lock files
            '.lock', '.lck',
            
            # Swap files
            '.swp', '.swo',
            
            # Log files (can be large)
            '.log',
        }
        
        self.exclude_extensions.update(self.default_exclude_extensions)
    
    def add_include_extension(self, extension: str):
        """Add an extension to include"""
        ext = extension.lower()
        if not ext.startswith('.'):
            ext = '.' + ext
        self.include_extensions.add(ext)
    
    def add_exclude_extension(self, extension: str):
        """Add an extension to exclude"""
        ext = extension.lower()
        if not ext.startswith('.'):
            ext = '.' + ext
        self.exclude_extensions.add(ext)
    
    def should_include_file(self, file_path: str) -> bool:
        """Check if file should be included based on type filters"""
        
        # Get file extension
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        # Check exclude list first
        if ext in self.exclude_extensions:
            return False
        
        # If include list is specified, file must be in it
        if self.include_extensions:
            return ext in self.include_extensions
        
        # No include filter specified, include by default
        return True
    
    def get_file_category(self, file_path: str) -> str:
        """Categorize file by extension"""
        
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        categories = {
            'document': {'.txt', '.doc', '.docx', '.pdf', '.rtf', '.odt', '.pages'},
            'spreadsheet': {'.xls', '.xlsx', '.csv', '.ods', '.numbers'},
            'presentation': {'.ppt', '.pptx', '.odp', '.key'},
            'image': {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg'},
            'video': {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv'},
            'audio': {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma'},
            'archive': {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'},
            'code': {'.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.go', '.rs'},
            'data': {'.json', '.xml', '.yaml', '.yml', '.sql', '.db'},
            'executable': {'.exe', '.msi', '.deb', '.rpm', '.dmg', '.app'},
            'temporary': {'.tmp', '.temp', '.cache', '.bak', '.swp'}
        }
        
        for category, extensions in categories.items():
            if ext in extensions:
                return category
        
        return 'other'

class SmartIgnoreManager:
    """Intelligent ignore pattern management"""
    
    def __init__(self):
        self.pattern_matcher = IgnorePatternMatcher()
        self.file_filter = FileTypeFilter()
        self.usage_stats: Dict[str, int] = {}
        
    def should_ignore_path(self, file_path: str, base_directory: Optional[str] = None) -> Dict[str, any]:
        """Comprehensive check if path should be ignored"""
        
        result = {
            'ignore': False,
            'reason': None,
            'category': None
        }
        
        # Check ignore patterns
        if self.pattern_matcher.should_ignore(file_path, base_directory):
            result['ignore'] = True
            result['reason'] = 'ignore_pattern'
            return result
        
        # Check file type filters
        if not self.file_filter.should_include_file(file_path):
            result['ignore'] = True
            result['reason'] = 'file_type_filter'
            result['category'] = self.file_filter.get_file_category(file_path)
            return result
        
        # File should be watched
        result['category'] = self.file_filter.get_file_category(file_path)
        return result
    
    def add_temporary_ignore(self, pattern: str, duration_seconds: int = 3600):
        """Add a temporary ignore pattern"""
        # This would be implemented with a time-based cleanup mechanism
        self.pattern_matcher.add_global_pattern(pattern)
        
        # Schedule removal (in a real implementation)
        # asyncio.get_event_loop().call_later(duration_seconds, self._remove_pattern, pattern)
    
    def learn_from_usage(self, file_path: str, ignored: bool):
        """Learn ignore patterns from user behavior"""
        
        # Track usage statistics
        category = self.file_filter.get_file_category(file_path)
        stat_key = f"{category}_{'ignored' if ignored else 'watched'}"
        
        self.usage_stats[stat_key] = self.usage_stats.get(stat_key, 0) + 1
        
        # Auto-suggest patterns based on usage
        if ignored and self.usage_stats.get(f"{category}_ignored", 0) > 10:
            # If we've ignored many files of this type, suggest excluding the category
            logger.info(f"Consider adding ignore pattern for {category} files")
    
    def get_suggested_patterns(self) -> List[str]:
        """Get suggested ignore patterns based on usage"""
        suggestions = []
        
        # Analyze usage statistics
        for stat_key, count in self.usage_stats.items():
            if stat_key.endswith('_ignored') and count > 20:
                category = stat_key.replace('_ignored', '')
                suggestions.append(f"Consider ignoring {category} files: *.{category}")
        
        return suggestions
    
    def export_patterns(self, file_path: str):
        """Export current patterns to an ignore file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("# ActiveLog ignore patterns\n")
                f.write("# Generated automatically\n\n")
                
                for pattern in self.pattern_matcher.global_patterns:
                    f.write(f"{pattern}\n")
            
            logger.info(f"Exported {len(self.pattern_matcher.global_patterns)} patterns to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to export patterns: {e}")
    
    def import_patterns(self, file_path: str):
        """Import patterns from an ignore file"""
        self.pattern_matcher.load_ignore_file(file_path)