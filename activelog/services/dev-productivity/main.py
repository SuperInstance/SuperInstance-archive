#!/usr/bin/env python3
"""
Developer Productivity Tools and IDE Integrations
Provides code analysis, auto-completion, debugging tools, and IDE integrations
"""

import asyncio
import json
import logging
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import aiohttp
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket
from pydantic import BaseModel
import ast
import re
import gitpython as git
from jedi import Script
import pylint.lint
from mypy.api import run as mypy_run
import black
import isort
import autopep8

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Developer Productivity Suite", version="1.0.0")

class CodeAnalysisRequest(BaseModel):
    file_path: str
    content: Optional[str] = None
    analysis_type: str = "full"  # full, syntax, style, security

class AutocompleteRequest(BaseModel):
    file_path: str
    content: str
    line: int
    column: int

class RefactorRequest(BaseModel):
    file_path: str
    content: str
    refactor_type: str  # rename, extract_method, inline, etc.
    parameters: Dict[str, Any] = {}

class DebuggingSession(BaseModel):
    session_id: str
    file_path: str
    breakpoints: List[int]
    variables: Dict[str, Any] = {}

class DevProductivity:
    def __init__(self):
        self.db_path = Path(__file__).parent / "data" / "dev_productivity.db"
        self.cache_path = Path(__file__).parent / "cache"
        self.templates_path = Path(__file__).parent / "templates"
        
        # Create directories
        self.db_path.parent.mkdir(exist_ok=True)
        self.cache_path.mkdir(exist_ok=True)
        self.templates_path.mkdir(exist_ok=True)
        
        self._init_database()
        self._init_code_templates()
        
        # Active sessions
        self.debug_sessions = {}
        self.completion_cache = {}
        
        # Code analysis tools
        self.analyzers = {
            'syntax': self._analyze_syntax,
            'style': self._analyze_style,
            'security': self._analyze_security,
            'complexity': self._analyze_complexity,
            'dependencies': self._analyze_dependencies
        }
        
    def _init_database(self):
        """Initialize SQLite database for productivity data"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS code_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    analysis_type TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    issues_count INTEGER,
                    issues JSON,
                    metrics JSON,
                    suggestions JSON
                );
                
                CREATE TABLE IF NOT EXISTS code_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    lines_of_code INTEGER,
                    complexity_score REAL,
                    maintainability_index REAL,
                    test_coverage REAL,
                    dependencies_count INTEGER
                );
                
                CREATE TABLE IF NOT EXISTS refactoring_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    refactor_type TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    before_content TEXT,
                    after_content TEXT,
                    success BOOLEAN,
                    error_message TEXT
                );
                
                CREATE TABLE IF NOT EXISTS productivity_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    developer_id TEXT,
                    date DATE,
                    lines_written INTEGER,
                    lines_deleted INTEGER,
                    files_modified INTEGER,
                    commits_count INTEGER,
                    issues_fixed INTEGER,
                    time_coding_minutes INTEGER
                );
                
                CREATE TABLE IF NOT EXISTS code_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_name TEXT UNIQUE NOT NULL,
                    language TEXT NOT NULL,
                    category TEXT NOT NULL,
                    template_content TEXT NOT NULL,
                    variables JSON,
                    usage_count INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_analysis_file ON code_analysis(file_path);
                CREATE INDEX IF NOT EXISTS idx_metrics_date ON productivity_metrics(date);
            """)
            
    def _init_code_templates(self):
        """Initialize code templates"""
        templates = [
            {
                'template_name': 'fastapi_service',
                'language': 'python',
                'category': 'microservice',
                'template_content': '''#!/usr/bin/env python3
"""
{{service_name}} Service
{{description}}
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="{{service_name}}", version="1.0.0")

class {{model_name}}(BaseModel):
    {{model_fields}}

@app.on_startup
async def startup():
    """Initialize service"""
    logger.info("Starting {{service_name}} service")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "{{service_name}}"}

@app.get("/{{endpoint_name}}")
async def {{endpoint_function}}():
    """{{endpoint_description}}"""
    return {"message": "{{service_name}} is running"}

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", {{default_port}}))
    uvicorn.run(app, host="0.0.0.0", port=port)
''',
                'variables': {
                    'service_name': 'Service Name',
                    'description': 'Service Description',
                    'model_name': 'DataModel',
                    'model_fields': 'id: int\n    name: str',
                    'endpoint_name': 'data',
                    'endpoint_function': 'get_data',
                    'endpoint_description': 'Get service data',
                    'default_port': '8000'
                }
            },
            {
                'template_name': 'react_component',
                'language': 'javascript',
                'category': 'frontend',
                'template_content': '''import React, { useState, useEffect } from 'react';
import './{{component_name}}.css';

interface {{component_name}}Props {
  {{props_interface}}
}

const {{component_name}}: React.FC<{{component_name}}Props> = ({ {{props_destructure}} }) => {
  const [{{state_name}}, set{{state_name_capitalized}}] = useState({{initial_state}});

  useEffect(() => {
    // Component initialization
    {{use_effect_content}}
  }, []);

  const handle{{action_name}} = ({{action_params}}) => {
    {{action_logic}}
  };

  return (
    <div className="{{css_class}}">
      <h2>{{component_title}}</h2>
      {{component_content}}
    </div>
  );
};

export default {{component_name}};
''',
                'variables': {
                    'component_name': 'MyComponent',
                    'props_interface': 'title: string;',
                    'props_destructure': 'title',
                    'state_name': 'data',
                    'state_name_capitalized': 'Data',
                    'initial_state': 'null',
                    'use_effect_content': '// Initialize component',
                    'action_name': 'Action',
                    'action_params': 'event: React.MouseEvent',
                    'action_logic': '// Handle action',
                    'css_class': 'my-component',
                    'component_title': 'My Component',
                    'component_content': '<p>Component content</p>'
                }
            },
            {
                'template_name': 'database_model',
                'language': 'python',
                'category': 'database',
                'template_content': '''from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class {{model_name}}(Base):
    """{{model_description}}"""
    __tablename__ = '{{table_name}}'
    
    id = Column(Integer, primary_key=True, index=True)
    {{model_columns}}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<{{model_name}}(id={self.id}, {{repr_fields}})>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            {{to_dict_fields}}
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
''',
                'variables': {
                    'model_name': 'User',
                    'model_description': 'User model',
                    'table_name': 'users',
                    'model_columns': 'name = Column(String(100), nullable=False)\n    email = Column(String(255), unique=True, nullable=False)',
                    'repr_fields': 'name=self.name',
                    'to_dict_fields': "'name': self.name,\n            'email': self.email,"
                }
            }
        ]
        
        # Insert templates into database
        with sqlite3.connect(self.db_path) as conn:
            for template in templates:
                conn.execute("""
                    INSERT OR IGNORE INTO code_templates 
                    (template_name, language, category, template_content, variables)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    template['template_name'],
                    template['language'],
                    template['category'],
                    template['template_content'],
                    json.dumps(template['variables'])
                ))
                
    async def analyze_code(self, request: CodeAnalysisRequest) -> Dict[str, Any]:
        """Perform comprehensive code analysis"""
        file_path = Path(request.file_path)
        
        if not file_path.exists() and not request.content:
            raise HTTPException(status_code=404, detail="File not found and no content provided")
            
        # Get file content
        if request.content:
            content = request.content
        else:
            content = file_path.read_text()
            
        analysis_results = {
            'file_path': str(file_path),
            'timestamp': datetime.now().isoformat(),
            'analysis_type': request.analysis_type,
            'issues': [],
            'metrics': {},
            'suggestions': []
        }
        
        # Determine file language
        language = self._detect_language(file_path)
        analysis_results['language'] = language
        
        # Run appropriate analyzers
        if request.analysis_type == 'full':
            for analyzer_name, analyzer_func in self.analyzers.items():
                try:
                    results = await analyzer_func(content, file_path, language)
                    analysis_results[analyzer_name] = results
                except Exception as e:
                    logger.error(f"Error in {analyzer_name} analysis: {e}")
        else:
            if request.analysis_type in self.analyzers:
                results = await self.analyzers[request.analysis_type](content, file_path, language)
                analysis_results[request.analysis_type] = results
                
        # Store analysis results
        await self._store_analysis_results(analysis_results)
        
        return analysis_results
        
    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension"""
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'react',
            '.tsx': 'react-typescript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.sql': 'sql',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml'
        }
        return extension_map.get(file_path.suffix.lower(), 'unknown')
        
    async def _analyze_syntax(self, content: str, file_path: Path, language: str) -> Dict[str, Any]:
        """Analyze syntax errors and issues"""
        issues = []
        
        if language == 'python':
            try:
                ast.parse(content)
            except SyntaxError as e:
                issues.append({
                    'type': 'syntax_error',
                    'line': e.lineno,
                    'column': e.offset,
                    'message': e.msg,
                    'severity': 'error'
                })
        elif language in ['javascript', 'typescript']:
            # Use external tool for JS/TS syntax checking
            try:
                result = subprocess.run(['node', '-c'], input=content, text=True, capture_output=True)
                if result.returncode != 0:
                    issues.append({
                        'type': 'syntax_error',
                        'message': result.stderr,
                        'severity': 'error'
                    })
            except FileNotFoundError:
                logger.warning("Node.js not available for syntax checking")
                
        return {
            'issues': issues,
            'valid_syntax': len(issues) == 0
        }
        
    async def _analyze_style(self, content: str, file_path: Path, language: str) -> Dict[str, Any]:
        """Analyze code style and formatting"""
        issues = []
        suggestions = []
        
        if language == 'python':
            # Check with black
            try:
                formatted_content = black.format_str(content, mode=black.FileMode())
                if formatted_content != content:
                    suggestions.append({
                        'type': 'formatting',
                        'message': 'Code can be reformatted with Black',
                        'tool': 'black'
                    })
            except Exception as e:
                logger.warning(f"Black formatting check failed: {e}")
                
            # Check import sorting
            try:
                sorted_content = isort.code(content, show_diff=True)
                if sorted_content != content:
                    suggestions.append({
                        'type': 'import_sorting',
                        'message': 'Imports can be sorted with isort',
                        'tool': 'isort'
                    })
            except Exception as e:
                logger.warning(f"Import sorting check failed: {e}")
                
        return {
            'issues': issues,
            'suggestions': suggestions,
            'style_score': max(0, 100 - len(issues) * 10)
        }
        
    async def _analyze_security(self, content: str, file_path: Path, language: str) -> Dict[str, Any]:
        """Analyze security vulnerabilities"""
        issues = []
        
        if language == 'python':
            # Check for common security issues
            security_patterns = [
                (r'exec\s*\(', 'Use of exec() can be dangerous'),
                (r'eval\s*\(', 'Use of eval() can be dangerous'),
                (r'pickle\.loads?\s*\(', 'Pickle deserialization can be unsafe'),
                (r'subprocess\.call\s*\(.*shell=True', 'Shell=True in subprocess can be dangerous'),
                (r'os\.system\s*\(', 'os.system() can be dangerous'),
                (r'input\s*\([\'"][^\'"]*(password|secret)[^\'\"]*[\'"]', 'Sensitive input without masking'),
                (r'(?i)(password|secret|key)\s*=\s*[\'"][^\'"]+[\'"]', 'Hardcoded secrets detected')
            ]
            
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                for pattern, message in security_patterns:
                    if re.search(pattern, line):
                        issues.append({
                            'type': 'security_issue',
                            'line': line_num,
                            'message': message,
                            'severity': 'warning',
                            'code': line.strip()
                        })
                        
        return {
            'issues': issues,
            'security_score': max(0, 100 - len(issues) * 20)
        }
        
    async def _analyze_complexity(self, content: str, file_path: Path, language: str) -> Dict[str, Any]:
        """Analyze code complexity metrics"""
        if language == 'python':
            try:
                tree = ast.parse(content)
                complexity_analyzer = ComplexityAnalyzer()
                complexity_analyzer.visit(tree)
                
                return {
                    'cyclomatic_complexity': complexity_analyzer.complexity,
                    'function_count': complexity_analyzer.function_count,
                    'class_count': complexity_analyzer.class_count,
                    'max_function_complexity': complexity_analyzer.max_function_complexity,
                    'maintainability_index': self._calculate_maintainability_index(
                        complexity_analyzer.complexity,
                        len(content.split('\n')),
                        complexity_analyzer.function_count
                    )
                }
            except Exception as e:
                logger.error(f"Complexity analysis failed: {e}")
                return {'error': str(e)}
        
        return {'message': f'Complexity analysis not implemented for {language}'}
        
    async def _analyze_dependencies(self, content: str, file_path: Path, language: str) -> Dict[str, Any]:
        """Analyze code dependencies"""
        dependencies = []
        
        if language == 'python':
            import_pattern = r'^(?:from\s+(\S+)\s+)?import\s+(.+)$'
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                if line.startswith(('import ', 'from ')):
                    match = re.match(import_pattern, line)
                    if match:
                        module = match.group(1) or match.group(2).split('.')[0]
                        dependencies.append({
                            'module': module,
                            'type': 'import',
                            'line': line
                        })
                        
        elif language in ['javascript', 'typescript']:
            # Analyze JS/TS imports
            import_patterns = [
                r'import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]',
                r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
            ]
            
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    dependencies.append({
                        'module': match,
                        'type': 'import'
                    })
                    
        return {
            'dependencies': dependencies,
            'dependency_count': len(dependencies),
            'external_dependencies': [dep for dep in dependencies if not dep['module'].startswith('.')]
        }
        
    def _calculate_maintainability_index(self, complexity: int, lines_of_code: int, function_count: int) -> float:
        """Calculate maintainability index"""
        # Simplified maintainability index calculation
        if lines_of_code == 0:
            return 100.0
            
        volume = lines_of_code * 4.5  # Simplified Halstead volume
        difficulty = complexity if complexity > 0 else 1
        
        mi = 171 - 5.2 * (volume / 1000) - 0.23 * difficulty - 16.2 * (lines_of_code / 1000)
        return max(0, min(100, mi))
        
    async def _store_analysis_results(self, results: Dict[str, Any]):
        """Store analysis results in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO code_analysis 
                (file_path, analysis_type, issues_count, issues, metrics, suggestions)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                results['file_path'],
                results['analysis_type'],
                len(results.get('issues', [])),
                json.dumps(results.get('issues', [])),
                json.dumps(results.get('metrics', {})),
                json.dumps(results.get('suggestions', []))
            ))
            
    async def get_autocomplete(self, request: AutocompleteRequest) -> List[Dict[str, Any]]:
        """Get code autocompletion suggestions"""
        try:
            if self._detect_language(Path(request.file_path)) == 'python':
                script = Script(code=request.content, line=request.line, column=request.column, path=request.file_path)
                completions = script.completions()
                
                suggestions = []
                for completion in completions[:20]:  # Limit to top 20
                    suggestions.append({
                        'name': completion.name,
                        'complete': completion.complete,
                        'type': completion.type,
                        'description': completion.description,
                        'detail': getattr(completion, 'detail', '')
                    })
                    
                return suggestions
            else:
                return [{'message': f'Autocompletion not implemented for {self._detect_language(Path(request.file_path))}'}]
                
        except Exception as e:
            logger.error(f"Autocompletion error: {e}")
            return [{'error': str(e)}]
            
    async def refactor_code(self, request: RefactorRequest) -> Dict[str, Any]:
        """Perform code refactoring"""
        result = {
            'success': False,
            'original_content': request.content,
            'refactored_content': None,
            'changes': [],
            'error': None
        }
        
        try:
            if request.refactor_type == 'format':
                if self._detect_language(Path(request.file_path)) == 'python':
                    formatted = black.format_str(request.content, mode=black.FileMode())
                    sorted_imports = isort.code(formatted)
                    
                    result['refactored_content'] = sorted_imports
                    result['success'] = True
                    result['changes'] = ['Formatted with Black', 'Sorted imports with isort']
                    
        except Exception as e:
            result['error'] = str(e)
            
        # Store refactoring history
        await self._store_refactoring_result(request, result)
        
        return result
        
    async def _store_refactoring_result(self, request: RefactorRequest, result: Dict[str, Any]):
        """Store refactoring result in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO refactoring_history 
                (file_path, refactor_type, before_content, after_content, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                request.file_path,
                request.refactor_type,
                request.content,
                result.get('refactored_content'),
                result['success'],
                result.get('error')
            ))
            
    async def get_code_template(self, template_name: str, variables: Dict[str, str] = None) -> Dict[str, Any]:
        """Get and render code template"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            template = conn.execute("""
                SELECT * FROM code_templates WHERE template_name = ?
            """, (template_name,)).fetchone()
            
            if not template:
                raise HTTPException(status_code=404, detail="Template not found")
                
        template_content = template['template_content']
        template_variables = json.loads(template['variables'])
        
        # Merge provided variables with defaults
        if variables:
            template_variables.update(variables)
            
        # Render template
        for var_name, var_value in template_variables.items():
            placeholder = '{{' + var_name + '}}'
            template_content = template_content.replace(placeholder, str(var_value))
            
        # Update usage count
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE code_templates SET usage_count = usage_count + 1 
                WHERE template_name = ?
            """, (template_name,))
            
        return {
            'template_name': template_name,
            'language': template['language'],
            'category': template['category'],
            'content': template_content,
            'variables': template_variables
        }
        
    async def get_productivity_metrics(self, developer_id: str = None, days: int = 30) -> Dict[str, Any]:
        """Get developer productivity metrics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            where_clause = "WHERE date >= date('now', '-{} days')".format(days)
            if developer_id:
                where_clause += f" AND developer_id = '{developer_id}'"
                
            metrics = conn.execute(f"""
                SELECT 
                    AVG(lines_written) as avg_lines_written,
                    AVG(files_modified) as avg_files_modified,
                    AVG(commits_count) as avg_commits,
                    SUM(issues_fixed) as total_issues_fixed,
                    AVG(time_coding_minutes) as avg_coding_time
                FROM productivity_metrics 
                {where_clause}
            """).fetchone()
            
            recent_activity = conn.execute(f"""
                SELECT * FROM productivity_metrics 
                {where_clause}
                ORDER BY date DESC
                LIMIT 10
            """).fetchall()
            
        return {
            'period_days': days,
            'developer_id': developer_id,
            'averages': dict(metrics) if metrics else {},
            'recent_activity': [dict(row) for row in recent_activity]
        }

class ComplexityAnalyzer(ast.NodeVisitor):
    """AST visitor to calculate cyclomatic complexity"""
    
    def __init__(self):
        self.complexity = 0
        self.function_count = 0
        self.class_count = 0
        self.max_function_complexity = 0
        self.current_function_complexity = 0
        
    def visit_FunctionDef(self, node):
        self.function_count += 1
        old_complexity = self.current_function_complexity
        self.current_function_complexity = 1  # Base complexity
        
        self.generic_visit(node)
        
        self.max_function_complexity = max(
            self.max_function_complexity, 
            self.current_function_complexity
        )
        self.complexity += self.current_function_complexity
        self.current_function_complexity = old_complexity
        
    def visit_ClassDef(self, node):
        self.class_count += 1
        self.generic_visit(node)
        
    def visit_If(self, node):
        self.current_function_complexity += 1
        self.generic_visit(node)
        
    def visit_For(self, node):
        self.current_function_complexity += 1
        self.generic_visit(node)
        
    def visit_While(self, node):
        self.current_function_complexity += 1
        self.generic_visit(node)
        
    def visit_Try(self, node):
        self.current_function_complexity += 1
        self.generic_visit(node)

# Global dev productivity instance
dev_tools = DevProductivity()

@app.on_startup
async def startup():
    """Start developer productivity service"""
    logger.info("Starting Developer Productivity Suite")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "dev-productivity"}

@app.post("/analyze")
async def analyze_code_endpoint(request: CodeAnalysisRequest):
    """Analyze code for issues and metrics"""
    return await dev_tools.analyze_code(request)

@app.post("/autocomplete")
async def autocomplete_endpoint(request: AutocompleteRequest):
    """Get code autocompletion suggestions"""
    suggestions = await dev_tools.get_autocomplete(request)
    return {"suggestions": suggestions}

@app.post("/refactor")
async def refactor_endpoint(request: RefactorRequest):
    """Refactor code"""
    return await dev_tools.refactor_code(request)

@app.get("/templates")
async def list_templates():
    """List available code templates"""
    with sqlite3.connect(dev_tools.db_path) as conn:
        conn.row_factory = sqlite3.Row
        templates = conn.execute("""
            SELECT template_name, language, category, usage_count 
            FROM code_templates 
            ORDER BY usage_count DESC
        """).fetchall()
        
    return [dict(template) for template in templates]

@app.get("/templates/{template_name}")
async def get_template_endpoint(template_name: str, variables: Dict[str, str] = None):
    """Get and render a code template"""
    return await dev_tools.get_code_template(template_name, variables or {})

@app.get("/metrics/productivity")
async def productivity_metrics_endpoint(developer_id: str = None, days: int = 30):
    """Get productivity metrics"""
    return await dev_tools.get_productivity_metrics(developer_id, days)

@app.get("/metrics/code-quality")
async def code_quality_metrics():
    """Get code quality metrics"""
    with sqlite3.connect(dev_tools.db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        recent_analysis = conn.execute("""
            SELECT 
                AVG(issues_count) as avg_issues_per_file,
                COUNT(DISTINCT file_path) as files_analyzed,
                analysis_type,
                COUNT(*) as analysis_count
            FROM code_analysis 
            WHERE timestamp > datetime('now', '-7 days')
            GROUP BY analysis_type
        """).fetchall()
        
    return [dict(row) for row in recent_analysis]

@app.websocket("/ws/live-analysis")
async def websocket_live_analysis(websocket: WebSocket):
    """WebSocket for live code analysis"""
    await websocket.accept()
    
    try:
        while True:
            # Receive code content
            data = await websocket.receive_text()
            request_data = json.loads(data)
            
            # Perform quick analysis
            request = CodeAnalysisRequest(**request_data)
            analysis = await dev_tools.analyze_code(request)
            
            # Send results
            await websocket.send_text(json.dumps(analysis))
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8603))
    uvicorn.run(app, host="0.0.0.0", port=port)