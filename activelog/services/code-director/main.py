#!/usr/bin/env python3
"""
Code Director System
Port: 8446

Advanced AI-powered development assistant with:
- Automated code generation
- Architecture analysis & optimization
- Bug detection & fixing
- Code refactoring & modernization
- Documentation generation
- Performance optimization
- Security vulnerability scanning
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import uvicorn
from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import os
import ast
import subprocess
from pathlib import Path

from core.code_analyzer import CodeAnalyzer
from core.code_generator import CodeGenerator
from core.bug_detector import BugDetector
from models.code_types import (
    Project, CodeFile, AnalysisResult, GenerationRequest,
    BugReport, RefactoringSuggestion, SecurityVulnerability
)
from analyzers.architecture_analyzer import ArchitectureAnalyzer
from analyzers.performance_analyzer import PerformanceAnalyzer
from analyzers.security_scanner import SecurityScanner
from generators.documentation_generator import DocumentationGenerator
from utils.code_formatter import CodeFormatter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CodeDirectorSystem:
    def __init__(self, port: int = 8446):
        self.port = port
        self.app = FastAPI(title="Code Director System")
        self.projects: Dict[str, Project] = {}
        self.analysis_cache: Dict[str, AnalysisResult] = {}
        self.websocket_connections: List[WebSocket] = []
        
        # Core components
        self.code_analyzer = CodeAnalyzer()
        self.code_generator = CodeGenerator()
        self.bug_detector = BugDetector()
        self.architecture_analyzer = ArchitectureAnalyzer()
        self.performance_analyzer = PerformanceAnalyzer()
        self.security_scanner = SecurityScanner()
        self.documentation_generator = DocumentationGenerator()
        self.code_formatter = CodeFormatter()
        
        self._setup_routes()
        self._setup_middleware()
        
    def _setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        
        @self.app.get("/")
        async def root():
            return {
                "system": "Code Director - AI Development Assistant",
                "version": "1.0.0",
                "active_projects": len(self.projects),
                "cached_analyses": len(self.analysis_cache),
                "capabilities": [
                    "Code Generation",
                    "Architecture Analysis",
                    "Bug Detection",
                    "Performance Optimization",
                    "Security Scanning",
                    "Documentation Generation",
                    "Code Refactoring"
                ],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Project Management Routes
        @self.app.post("/projects")
        async def create_project(project_data: dict):
            project_id = await self._create_project(project_data)
            
            if project_id:
                await self._broadcast_update("project_created", {
                    "project_id": project_id,
                    "name": project_data.get("name")
                })
                return {"project_id": project_id, "status": "created"}
            else:
                raise HTTPException(status_code=400, detail="Failed to create project")
        
        @self.app.get("/projects")
        async def get_projects():
            projects_data = []
            for project_id, project in self.projects.items():
                project_summary = await self._get_project_summary(project_id)
                projects_data.append(project_summary)
            
            return {"projects": projects_data, "total": len(projects_data)}
        
        @self.app.get("/projects/{project_id}")
        async def get_project_details(project_id: str):
            if project_id not in self.projects:
                raise HTTPException(status_code=404, detail="Project not found")
            
            details = await self._get_project_details(project_id)
            return details
        
        @self.app.post("/projects/{project_id}/scan")
        async def scan_project_directory(project_id: str, scan_data: dict, background_tasks: BackgroundTasks):
            if project_id not in self.projects:
                raise HTTPException(status_code=404, detail="Project not found")
            
            background_tasks.add_task(self._scan_project_directory, project_id, scan_data.get("directory_path"))
            return {"status": "scan_initiated", "project_id": project_id}
        
        # Code Analysis Routes
        @self.app.post("/analysis/analyze-file")
        async def analyze_code_file(analysis_request: dict):
            analysis_id = await self._analyze_code_file(analysis_request)
            
            if analysis_id:
                return {"analysis_id": analysis_id, "status": "analyzing"}
            else:
                raise HTTPException(status_code=400, detail="Failed to start analysis")
        
        @self.app.get("/analysis/{analysis_id}")
        async def get_analysis_result(analysis_id: str):
            if analysis_id not in self.analysis_cache:
                raise HTTPException(status_code=404, detail="Analysis not found")
            
            return self.analysis_cache[analysis_id].to_dict()
        
        @self.app.post("/analysis/architecture/{project_id}")
        async def analyze_architecture(project_id: str, background_tasks: BackgroundTasks):
            if project_id not in self.projects:
                raise HTTPException(status_code=404, detail="Project not found")
            
            background_tasks.add_task(self._analyze_project_architecture, project_id)
            return {"status": "architecture_analysis_initiated", "project_id": project_id}
        
        @self.app.post("/analysis/performance/{project_id}")
        async def analyze_performance(project_id: str, background_tasks: BackgroundTasks):
            if project_id not in self.projects:
                raise HTTPException(status_code=404, detail="Project not found")
            
            background_tasks.add_task(self._analyze_project_performance, project_id)
            return {"status": "performance_analysis_initiated", "project_id": project_id}
        
        @self.app.post("/analysis/security/{project_id}")
        async def scan_security(project_id: str, background_tasks: BackgroundTasks):
            if project_id not in self.projects:
                raise HTTPException(status_code=404, detail="Project not found")
            
            background_tasks.add_task(self._scan_project_security, project_id)
            return {"status": "security_scan_initiated", "project_id": project_id}
        
        # Code Generation Routes
        @self.app.post("/generation/generate-code")
        async def generate_code(generation_request: dict, background_tasks: BackgroundTasks):
            generation_id = f"gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            background_tasks.add_task(self._generate_code, generation_id, generation_request)
            return {"generation_id": generation_id, "status": "generation_initiated"}
        
        @self.app.post("/generation/generate-tests")
        async def generate_tests(test_request: dict, background_tasks: BackgroundTasks):
            generation_id = f"test_gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            background_tasks.add_task(self._generate_tests, generation_id, test_request)
            return {"generation_id": generation_id, "status": "test_generation_initiated"}
        
        @self.app.post("/generation/generate-docs")
        async def generate_documentation(docs_request: dict, background_tasks: BackgroundTasks):
            if docs_request.get("project_id") and docs_request["project_id"] not in self.projects:
                raise HTTPException(status_code=404, detail="Project not found")
            
            generation_id = f"docs_gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            background_tasks.add_task(self._generate_documentation, generation_id, docs_request)
            return {"generation_id": generation_id, "status": "documentation_generation_initiated"}
        
        # Bug Detection Routes
        @self.app.post("/bugs/detect/{project_id}")
        async def detect_bugs(project_id: str, background_tasks: BackgroundTasks):
            if project_id not in self.projects:
                raise HTTPException(status_code=404, detail="Project not found")
            
            background_tasks.add_task(self._detect_project_bugs, project_id)
            return {"status": "bug_detection_initiated", "project_id": project_id}
        
        @self.app.get("/bugs/{project_id}")
        async def get_project_bugs(project_id: str):
            if project_id not in self.projects:
                raise HTTPException(status_code=404, detail="Project not found")
            
            bugs = await self._get_project_bug_reports(project_id)
            return {"bugs": bugs, "total": len(bugs)}
        
        @self.app.post("/bugs/fix")
        async def suggest_bug_fixes(bug_fix_request: dict, background_tasks: BackgroundTasks):
            fix_id = f"fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            background_tasks.add_task(self._suggest_bug_fixes, fix_id, bug_fix_request)
            return {"fix_id": fix_id, "status": "fix_analysis_initiated"}
        
        # Refactoring Routes
        @self.app.post("/refactoring/suggest/{project_id}")
        async def suggest_refactoring(project_id: str, background_tasks: BackgroundTasks):
            if project_id not in self.projects:
                raise HTTPException(status_code=404, detail="Project not found")
            
            background_tasks.add_task(self._suggest_refactoring, project_id)
            return {"status": "refactoring_analysis_initiated", "project_id": project_id}
        
        @self.app.post("/refactoring/apply")
        async def apply_refactoring(refactoring_request: dict, background_tasks: BackgroundTasks):
            refactoring_id = f"refactor_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            background_tasks.add_task(self._apply_refactoring, refactoring_id, refactoring_request)
            return {"refactoring_id": refactoring_id, "status": "refactoring_initiated"}
        
        # Code Quality Routes
        @self.app.post("/quality/format/{project_id}")
        async def format_project_code(project_id: str, format_options: dict = None):
            if project_id not in self.projects:
                raise HTTPException(status_code=404, detail="Project not found")
            
            formatted_files = await self._format_project_code(project_id, format_options or {})
            return {"formatted_files": formatted_files, "total": len(formatted_files)}
        
        @self.app.post("/quality/lint/{project_id}")
        async def lint_project(project_id: str, background_tasks: BackgroundTasks):
            if project_id not in self.projects:
                raise HTTPException(status_code=404, detail="Project not found")
            
            background_tasks.add_task(self._lint_project, project_id)
            return {"status": "linting_initiated", "project_id": project_id}
        
        # File Upload Routes
        @self.app.post("/upload/file")
        async def upload_code_file(file: UploadFile = File(...), project_id: str = None):
            if project_id and project_id not in self.projects:
                raise HTTPException(status_code=404, detail="Project not found")
            
            file_id = await self._process_uploaded_file(file, project_id)
            
            if file_id:
                return {"file_id": file_id, "filename": file.filename, "status": "uploaded"}
            else:
                raise HTTPException(status_code=400, detail="Failed to process file")
        
        # AI Assistance Routes
        @self.app.post("/ai/ask")
        async def ask_ai_assistant(question_data: dict):
            response = await self._process_ai_question(question_data)
            return {"response": response, "timestamp": datetime.now(timezone.utc).isoformat()}
        
        @self.app.post("/ai/explain-code")
        async def explain_code(code_data: dict):
            explanation = await self._explain_code_snippet(code_data)
            return {"explanation": explanation}
        
        @self.app.post("/ai/optimize-code")
        async def optimize_code(optimization_request: dict, background_tasks: BackgroundTasks):
            optimization_id = f"opt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            background_tasks.add_task(self._optimize_code, optimization_id, optimization_request)
            return {"optimization_id": optimization_id, "status": "optimization_initiated"}
        
        # WebSocket for real-time updates
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    data = await websocket.receive_text()
                    logger.info(f"Received websocket message: {data}")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            finally:
                self.websocket_connections.remove(websocket)
        
        @self.app.get("/health")
        async def health_check():
            component_health = {
                "code_analyzer": self.code_analyzer.is_operational(),
                "code_generator": self.code_generator.is_active(),
                "bug_detector": self.bug_detector.is_healthy(),
                "architecture_analyzer": await self.architecture_analyzer.get_status(),
                "security_scanner": self.security_scanner.is_operational()
            }
            
            overall_healthy = all(component_health.values())
            
            return {
                "status": "healthy" if overall_healthy else "degraded",
                "components": component_health,
                "active_projects": len(self.projects),
                "cached_analyses": len(self.analysis_cache),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _create_project(self, project_data: dict) -> Optional[str]:
        """Create new project"""
        try:
            project_id = f"proj_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            project = Project(
                project_id=project_id,
                name=project_data["name"],
                description=project_data.get("description", ""),
                language=project_data.get("language", "python"),
                framework=project_data.get("framework"),
                repository_url=project_data.get("repository_url"),
                local_path=project_data.get("local_path"),
                created_at=datetime.now(timezone.utc)
            )
            
            self.projects[project_id] = project
            
            logger.info(f"Created project: {project.name} ({project_id})")
            return project_id
            
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            return None
    
    async def _get_project_summary(self, project_id: str) -> dict:
        """Get project summary information"""
        project = self.projects[project_id]
        
        return {
            "project_id": project_id,
            "name": project.name,
            "description": project.description,
            "language": project.language,
            "framework": project.framework,
            "files_count": len(project.files),
            "last_analyzed": project.last_analyzed.isoformat() if project.last_analyzed else None,
            "created_at": project.created_at.isoformat(),
            "status": project.status
        }
    
    async def _get_project_details(self, project_id: str) -> dict:
        """Get detailed project information"""
        project = self.projects[project_id]
        
        # Get recent analyses
        recent_analyses = [
            analysis for analysis in self.analysis_cache.values()
            if analysis.project_id == project_id
        ][-10:]  # Last 10 analyses
        
        return {
            "project_id": project_id,
            "name": project.name,
            "description": project.description,
            "language": project.language,
            "framework": project.framework,
            "repository_url": project.repository_url,
            "local_path": project.local_path,
            "files": [
                {
                    "file_path": file.file_path,
                    "language": file.language,
                    "lines_of_code": file.lines_of_code,
                    "last_modified": file.last_modified.isoformat(),
                    "analysis_status": file.analysis_status
                }
                for file in project.files
            ],
            "recent_analyses": [
                {
                    "analysis_id": analysis.analysis_id,
                    "analysis_type": analysis.analysis_type,
                    "timestamp": analysis.timestamp.isoformat(),
                    "issues_found": len(analysis.issues)
                }
                for analysis in recent_analyses
            ],
            "created_at": project.created_at.isoformat(),
            "last_analyzed": project.last_analyzed.isoformat() if project.last_analyzed else None,
            "status": project.status
        }
    
    async def _scan_project_directory(self, project_id: str, directory_path: str):
        """Scan project directory for code files (background task)"""
        try:
            project = self.projects[project_id]
            logger.info(f"Scanning directory: {directory_path} for project {project_id}")
            
            if not os.path.exists(directory_path):
                logger.error(f"Directory not found: {directory_path}")
                return
            
            code_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs', '.rb', '.php'}
            scanned_files = []
            
            for root, dirs, files in os.walk(directory_path):
                # Skip common non-source directories
                dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    file_ext = os.path.splitext(file)[1].lower()
                    
                    if file_ext in code_extensions:
                        try:
                            # Get file stats
                            stat = os.stat(file_path)
                            
                            # Count lines of code
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                lines = f.readlines()
                                loc = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
                            
                            # Determine language
                            language_map = {
                                '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
                                '.java': 'java', '.cpp': 'cpp', '.c': 'c', '.go': 'go',
                                '.rs': 'rust', '.rb': 'ruby', '.php': 'php'
                            }
                            
                            code_file = CodeFile(
                                file_path=file_path,
                                relative_path=os.path.relpath(file_path, directory_path),
                                language=language_map.get(file_ext, 'unknown'),
                                lines_of_code=loc,
                                last_modified=datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                            )
                            
                            project.files.append(code_file)
                            scanned_files.append(file_path)
                            
                        except Exception as e:
                            logger.error(f"Error processing file {file_path}: {e}")
            
            project.local_path = directory_path
            project.status = "scanned"
            
            await self._broadcast_update("project_scanned", {
                "project_id": project_id,
                "files_found": len(scanned_files),
                "directory_path": directory_path
            })
            
            logger.info(f"Scanned {len(scanned_files)} files for project {project_id}")
            
        except Exception as e:
            logger.error(f"Directory scan failed for project {project_id}: {e}")
    
    async def _analyze_code_file(self, analysis_request: dict) -> Optional[str]:
        """Analyze individual code file"""
        try:
            analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.analysis_cache)+1:03d}"
            
            file_path = analysis_request["file_path"]
            analysis_type = analysis_request.get("analysis_type", "comprehensive")
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Perform analysis based on file type
            issues = []
            suggestions = []
            metrics = {}
            
            # Basic syntax analysis for Python files
            if file_path.endswith('.py'):
                try:
                    ast.parse(content)
                    issues.append({
                        "type": "info",
                        "message": "Python syntax is valid",
                        "line": 0,
                        "severity": "info"
                    })
                except SyntaxError as e:
                    issues.append({
                        "type": "syntax_error",
                        "message": f"Syntax error: {e.msg}",
                        "line": e.lineno or 0,
                        "severity": "error"
                    })
                
                # Count basic metrics
                lines = content.split('\n')
                metrics = {
                    "lines_of_code": len([line for line in lines if line.strip() and not line.strip().startswith('#')]),
                    "comment_lines": len([line for line in lines if line.strip().startswith('#')]),
                    "blank_lines": len([line for line in lines if not line.strip()]),
                    "functions": len([line for line in lines if line.strip().startswith('def ')]),
                    "classes": len([line for line in lines if line.strip().startswith('class ')])
                }
                
                # Basic suggestions
                if metrics["comment_lines"] / max(1, metrics["lines_of_code"]) < 0.1:
                    suggestions.append({
                        "type": "documentation",
                        "message": "Consider adding more comments and documentation",
                        "priority": "medium"
                    })
            
            # Create analysis result
            analysis_result = AnalysisResult(
                analysis_id=analysis_id,
                project_id=analysis_request.get("project_id"),
                file_path=file_path,
                analysis_type=analysis_type,
                issues=issues,
                suggestions=suggestions,
                metrics=metrics,
                timestamp=datetime.now(timezone.utc)
            )
            
            self.analysis_cache[analysis_id] = analysis_result
            
            logger.info(f"Analyzed file: {file_path} - found {len(issues)} issues")
            return analysis_id
            
        except Exception as e:
            logger.error(f"Code analysis failed: {e}")
            return None
    
    async def _analyze_project_architecture(self, project_id: str):
        """Analyze project architecture (background task)"""
        try:
            project = self.projects[project_id]
            logger.info(f"Analyzing architecture for project: {project_id}")
            
            # Simulate architecture analysis
            await asyncio.sleep(3)
            
            analysis_result = await self.architecture_analyzer.analyze_project(project)
            
            # Cache analysis result
            analysis_id = f"arch_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.analysis_cache[analysis_id] = analysis_result
            
            await self._broadcast_update("architecture_analyzed", {
                "project_id": project_id,
                "analysis_id": analysis_id,
                "architecture_score": analysis_result.metrics.get("architecture_score", 75)
            })
            
            logger.info(f"Architecture analysis completed for project: {project_id}")
            
        except Exception as e:
            logger.error(f"Architecture analysis failed for project {project_id}: {e}")
    
    async def _analyze_project_performance(self, project_id: str):
        """Analyze project performance (background task)"""
        try:
            project = self.projects[project_id]
            logger.info(f"Analyzing performance for project: {project_id}")
            
            # Simulate performance analysis
            await asyncio.sleep(2)
            
            analysis_result = await self.performance_analyzer.analyze_project(project)
            
            # Cache analysis result
            analysis_id = f"perf_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.analysis_cache[analysis_id] = analysis_result
            
            await self._broadcast_update("performance_analyzed", {
                "project_id": project_id,
                "analysis_id": analysis_id,
                "performance_score": analysis_result.metrics.get("performance_score", 82)
            })
            
            logger.info(f"Performance analysis completed for project: {project_id}")
            
        except Exception as e:
            logger.error(f"Performance analysis failed for project {project_id}: {e}")
    
    async def _scan_project_security(self, project_id: str):
        """Scan project for security vulnerabilities (background task)"""
        try:
            project = self.projects[project_id]
            logger.info(f"Scanning security for project: {project_id}")
            
            # Simulate security scan
            await asyncio.sleep(4)
            
            vulnerabilities = await self.security_scanner.scan_project(project)
            
            # Create analysis result
            analysis_result = AnalysisResult(
                analysis_id=f"sec_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                project_id=project_id,
                analysis_type="security",
                issues=[vuln.to_dict() for vuln in vulnerabilities],
                timestamp=datetime.now(timezone.utc)
            )
            
            self.analysis_cache[analysis_result.analysis_id] = analysis_result
            
            critical_vulns = [v for v in vulnerabilities if v.severity == "critical"]
            
            await self._broadcast_update("security_scanned", {
                "project_id": project_id,
                "analysis_id": analysis_result.analysis_id,
                "vulnerabilities_found": len(vulnerabilities),
                "critical_vulnerabilities": len(critical_vulns)
            })
            
            logger.info(f"Security scan completed for project: {project_id} - found {len(vulnerabilities)} vulnerabilities")
            
        except Exception as e:
            logger.error(f"Security scan failed for project {project_id}: {e}")
    
    async def _generate_code(self, generation_id: str, generation_request: dict):
        """Generate code (background task)"""
        try:
            logger.info(f"Generating code: {generation_id}")
            
            # Simulate code generation
            await asyncio.sleep(3)
            
            generated_code = await self.code_generator.generate_code(
                GenerationRequest(
                    request_id=generation_id,
                    description=generation_request["description"],
                    language=generation_request.get("language", "python"),
                    framework=generation_request.get("framework"),
                    specifications=generation_request.get("specifications", {}),
                    timestamp=datetime.now(timezone.utc)
                )
            )
            
            await self._broadcast_update("code_generated", {
                "generation_id": generation_id,
                "code_length": len(generated_code.get("code", "")),
                "files_generated": len(generated_code.get("files", []))
            })
            
            logger.info(f"Code generation completed: {generation_id}")
            
        except Exception as e:
            logger.error(f"Code generation failed {generation_id}: {e}")
    
    async def _generate_tests(self, generation_id: str, test_request: dict):
        """Generate test code (background task)"""
        try:
            logger.info(f"Generating tests: {generation_id}")
            
            # Simulate test generation
            await asyncio.sleep(2)
            
            test_code = await self.code_generator.generate_tests(test_request)
            
            await self._broadcast_update("tests_generated", {
                "generation_id": generation_id,
                "test_cases_generated": test_code.get("test_count", 0),
                "coverage_estimate": test_code.get("coverage_estimate", 80)
            })
            
            logger.info(f"Test generation completed: {generation_id}")
            
        except Exception as e:
            logger.error(f"Test generation failed {generation_id}: {e}")
    
    async def _generate_documentation(self, generation_id: str, docs_request: dict):
        """Generate documentation (background task)"""
        try:
            logger.info(f"Generating documentation: {generation_id}")
            
            # Simulate documentation generation
            await asyncio.sleep(2)
            
            documentation = await self.documentation_generator.generate_docs(docs_request)
            
            await self._broadcast_update("documentation_generated", {
                "generation_id": generation_id,
                "docs_pages": documentation.get("pages_count", 0),
                "format": docs_request.get("format", "markdown")
            })
            
            logger.info(f"Documentation generation completed: {generation_id}")
            
        except Exception as e:
            logger.error(f"Documentation generation failed {generation_id}: {e}")
    
    async def _detect_project_bugs(self, project_id: str):
        """Detect bugs in project (background task)"""
        try:
            project = self.projects[project_id]
            logger.info(f"Detecting bugs for project: {project_id}")
            
            # Simulate bug detection
            await asyncio.sleep(3)
            
            bug_reports = await self.bug_detector.detect_bugs(project)
            
            await self._broadcast_update("bugs_detected", {
                "project_id": project_id,
                "bugs_found": len(bug_reports),
                "critical_bugs": len([b for b in bug_reports if b.severity == "critical"])
            })
            
            logger.info(f"Bug detection completed for project: {project_id} - found {len(bug_reports)} bugs")
            
        except Exception as e:
            logger.error(f"Bug detection failed for project {project_id}: {e}")
    
    async def _get_project_bug_reports(self, project_id: str) -> List[dict]:
        """Get bug reports for project"""
        # Simulate returning cached bug reports
        return [
            {
                "bug_id": "BUG_001",
                "type": "null_pointer",
                "severity": "high",
                "file": "/path/to/file.py",
                "line": 42,
                "message": "Potential null pointer dereference",
                "fix_suggestion": "Add null check before accessing object"
            },
            {
                "bug_id": "BUG_002",
                "type": "memory_leak",
                "severity": "medium",
                "file": "/path/to/another_file.py",
                "line": 128,
                "message": "Resource not properly released",
                "fix_suggestion": "Use context manager or try-finally block"
            }
        ]
    
    async def _suggest_bug_fixes(self, fix_id: str, bug_fix_request: dict):
        """Suggest bug fixes (background task)"""
        try:
            logger.info(f"Suggesting bug fixes: {fix_id}")
            
            # Simulate fix suggestion generation
            await asyncio.sleep(2)
            
            await self._broadcast_update("bug_fixes_suggested", {
                "fix_id": fix_id,
                "fixes_suggested": 3,
                "automated_fix_available": True
            })
            
            logger.info(f"Bug fix suggestions completed: {fix_id}")
            
        except Exception as e:
            logger.error(f"Bug fix suggestion failed {fix_id}: {e}")
    
    async def _suggest_refactoring(self, project_id: str):
        """Suggest refactoring opportunities (background task)"""
        try:
            project = self.projects[project_id]
            logger.info(f"Suggesting refactoring for project: {project_id}")
            
            # Simulate refactoring analysis
            await asyncio.sleep(3)
            
            await self._broadcast_update("refactoring_suggested", {
                "project_id": project_id,
                "suggestions_count": 5,
                "potential_improvements": ["Extract method", "Simplify conditions", "Remove duplicates"]
            })
            
            logger.info(f"Refactoring suggestions completed for project: {project_id}")
            
        except Exception as e:
            logger.error(f"Refactoring suggestion failed for project {project_id}: {e}")
    
    async def _apply_refactoring(self, refactoring_id: str, refactoring_request: dict):
        """Apply refactoring changes (background task)"""
        try:
            logger.info(f"Applying refactoring: {refactoring_id}")
            
            # Simulate refactoring application
            await asyncio.sleep(3)
            
            await self._broadcast_update("refactoring_applied", {
                "refactoring_id": refactoring_id,
                "files_modified": 3,
                "lines_changed": 45
            })
            
            logger.info(f"Refactoring application completed: {refactoring_id}")
            
        except Exception as e:
            logger.error(f"Refactoring application failed {refactoring_id}: {e}")
    
    async def _format_project_code(self, project_id: str, format_options: dict) -> List[str]:
        """Format project code"""
        try:
            project = self.projects[project_id]
            formatted_files = []
            
            for code_file in project.files:
                if code_file.language == "python":
                    # Simulate code formatting
                    formatted_files.append(code_file.file_path)
            
            logger.info(f"Formatted {len(formatted_files)} files for project: {project_id}")
            return formatted_files
            
        except Exception as e:
            logger.error(f"Code formatting failed for project {project_id}: {e}")
            return []
    
    async def _lint_project(self, project_id: str):
        """Lint project code (background task)"""
        try:
            project = self.projects[project_id]
            logger.info(f"Linting project: {project_id}")
            
            # Simulate linting
            await asyncio.sleep(2)
            
            await self._broadcast_update("project_linted", {
                "project_id": project_id,
                "files_linted": len(project.files),
                "issues_found": 12,
                "warnings": 8,
                "errors": 4
            })
            
            logger.info(f"Linting completed for project: {project_id}")
            
        except Exception as e:
            logger.error(f"Linting failed for project {project_id}: {e}")
    
    async def _process_uploaded_file(self, file: UploadFile, project_id: Optional[str]) -> Optional[str]:
        """Process uploaded code file"""
        try:
            # Read file content
            content = await file.read()
            
            # Create temporary file ID
            file_id = f"file_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # If project specified, add to project files
            if project_id and project_id in self.projects:
                code_file = CodeFile(
                    file_path=f"/tmp/{file.filename}",
                    relative_path=file.filename,
                    language=self._detect_language(file.filename),
                    lines_of_code=len(content.decode('utf-8', errors='ignore').split('\n')),
                    last_modified=datetime.now(timezone.utc)
                )
                
                self.projects[project_id].files.append(code_file)
            
            logger.info(f"Processed uploaded file: {file.filename} ({file_id})")
            return file_id
            
        except Exception as e:
            logger.error(f"File upload processing failed: {e}")
            return None
    
    def _detect_language(self, filename: str) -> str:
        """Detect programming language from filename"""
        extension_map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.java': 'java', '.cpp': 'cpp', '.c': 'c', '.go': 'go',
            '.rs': 'rust', '.rb': 'ruby', '.php': 'php',
            '.html': 'html', '.css': 'css', '.json': 'json'
        }
        
        ext = os.path.splitext(filename)[1].lower()
        return extension_map.get(ext, 'unknown')
    
    async def _process_ai_question(self, question_data: dict) -> str:
        """Process AI assistant question"""
        question = question_data.get("question", "")
        context = question_data.get("context", {})
        
        # Simulate AI response generation
        responses = [
            "Based on your code structure, I recommend implementing a factory pattern here.",
            "This function could be optimized by using list comprehensions instead of loops.",
            "Consider adding error handling and input validation to make this more robust.",
            "The current approach works, but you might want to consider using async/await for better performance.",
            "This code follows good practices. You might want to add some unit tests to ensure reliability."
        ]
        
        import random
        return random.choice(responses)
    
    async def _explain_code_snippet(self, code_data: dict) -> str:
        """Explain code snippet"""
        code = code_data.get("code", "")
        language = code_data.get("language", "python")
        
        # Simulate code explanation
        explanations = [
            "This code defines a function that processes user input and returns a formatted result.",
            "This is a class implementation that follows the singleton pattern for managing resources.",
            "This code snippet implements error handling and logging for robust application behavior.",
            "This function uses modern language features to efficiently process data structures.",
            "This code demonstrates best practices for working with external APIs and data validation."
        ]
        
        import random
        return random.choice(explanations)
    
    async def _optimize_code(self, optimization_id: str, optimization_request: dict):
        """Optimize code (background task)"""
        try:
            logger.info(f"Optimizing code: {optimization_id}")
            
            # Simulate code optimization
            await asyncio.sleep(2)
            
            await self._broadcast_update("code_optimized", {
                "optimization_id": optimization_id,
                "performance_improvement": "15%",
                "memory_reduction": "8%",
                "optimizations_applied": 3
            })
            
            logger.info(f"Code optimization completed: {optimization_id}")
            
        except Exception as e:
            logger.error(f"Code optimization failed {optimization_id}: {e}")
    
    async def _broadcast_update(self, event_type: str, data: dict):
        if not self.websocket_connections:
            return
        
        message = {
            "event": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        disconnected = []
        for ws in self.websocket_connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {e}")
                disconnected.append(ws)
        
        for ws in disconnected:
            self.websocket_connections.remove(ws)
    
    def run(self):
        """Start the code director system"""
        logger.info(f"Starting Code Director System on port {self.port}")
        uvicorn.run(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )

if __name__ == "__main__":
    CodeDirectorSystem().run()