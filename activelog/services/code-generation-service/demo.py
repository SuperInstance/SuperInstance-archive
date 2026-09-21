#!/usr/bin/env python3
"""
Building Bots Network - Code Generation Service Demo

This demo showcases the comprehensive capabilities of the Building Bots Network
Code Generation Service, demonstrating construction excellence principles and
intelligent code generation across multiple languages and frameworks.
"""

import asyncio
import json
import time
import sys
from typing import Dict, Any
import aiohttp
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.syntax import Syntax
from rich.text import Text

# Initialize rich console for beautiful output
console = Console()

class CodeGenerationDemo:
    """Demo class for the Building Bots Network Code Generation Service"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def check_service_health(self) -> bool:
        """Check if the service is running and healthy"""
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    console.print("✅ Service is healthy and ready", style="green")
                    return True
                else:
                    console.print(f"❌ Service health check failed: {response.status}", style="red")
                    return False
        except Exception as e:
            console.print(f"❌ Failed to connect to service: {e}", style="red")
            return False
    
    async def show_service_capabilities(self):
        """Display service capabilities"""
        try:
            async with self.session.get(f"{self.base_url}/capabilities") as response:
                data = await response.json()
                
                console.print("\n")
                console.print(Panel.fit(
                    "🚀 Building Bots Network Code Generation Service Capabilities",
                    style="blue bold"
                ))
                
                # Languages table
                lang_table = Table(title="Supported Programming Languages", show_header=False)
                lang_table.add_column("Languages", style="cyan")
                
                # Group languages in rows of 4
                languages = data.get("languages", [])
                for i in range(0, len(languages), 4):
                    row = languages[i:i+4]
                    lang_table.add_row(" • ".join(row))
                
                console.print(lang_table)
                
                # Frameworks table
                fw_table = Table(title="Supported Frameworks", show_header=False)
                fw_table.add_column("Frameworks", style="green")
                
                frameworks = data.get("frameworks", [])
                for i in range(0, len(frameworks), 4):
                    row = frameworks[i:i+4]
                    fw_table.add_row(" • ".join(row))
                
                console.print(fw_table)
                
                # Features
                features_text = Text("\n🎯 Key Features:\n", style="yellow bold")
                for feature in data.get("features", []):
                    features_text.append(f"  • {feature}\n", style="white")
                
                console.print(Panel(features_text, title="Service Features"))
                
        except Exception as e:
            console.print(f"❌ Failed to get capabilities: {e}", style="red")
    
    async def demo_python_generation(self):
        """Demonstrate Python code generation"""
        console.print("\n" + "="*80)
        console.print("🐍 PYTHON CODE GENERATION DEMO", style="blue bold")
        console.print("="*80)
        
        request_data = {
            "prompt": "Create a FastAPI web service for a task management system with CRUD operations, authentication, and database integration. Include error handling, logging, and comprehensive documentation.",
            "language": "python",
            "framework": "fastapi",
            "complexity": "complex",
            "include_tests": True,
            "include_docs": True,
            "temperature": 0.1
        }
        
        await self._generate_and_display_code(request_data, "Python FastAPI Service")
    
    async def demo_javascript_generation(self):
        """Demonstrate JavaScript code generation"""
        console.print("\n" + "="*80)
        console.print("⚡ JAVASCRIPT CODE GENERATION DEMO", style="yellow bold")
        console.print("="*80)
        
        request_data = {
            "prompt": "Create a React component for a real-time chat interface with TypeScript, including message history, user typing indicators, emoji support, and responsive design.",
            "language": "typescript",
            "framework": "react",
            "complexity": "moderate",
            "include_tests": True,
            "include_docs": True,
            "temperature": 0.1
        }
        
        await self._generate_and_display_code(request_data, "React Chat Component")
    
    async def demo_rust_generation(self):
        """Demonstrate Rust code generation"""
        console.print("\n" + "="*80)
        console.print("🦀 RUST CODE GENERATION DEMO", style="red bold")
        console.print("="*80)
        
        request_data = {
            "prompt": "Create a high-performance HTTP server in Rust using Tokio and Axum, with middleware for authentication, rate limiting, and request logging. Include error handling and graceful shutdown.",
            "language": "rust",
            "complexity": "complex",
            "include_tests": True,
            "include_docs": True,
            "temperature": 0.1
        }
        
        await self._generate_and_display_code(request_data, "Rust HTTP Server")
    
    async def demo_code_analysis(self):
        """Demonstrate code analysis capabilities"""
        console.print("\n" + "="*80)
        console.print("🔍 CODE ANALYSIS DEMO", style="magenta bold")
        console.print("="*80)
        
        # Sample code with some issues
        sample_code = '''
def process_user_data(data):
    password = "hardcoded_password"
    query = "SELECT * FROM users WHERE id = %s" % data['user_id']
    
    result = ""
    for item in data['items']:
        result += str(item) + ","
    
    try:
        cursor.execute(query)
        return cursor.fetchall()
    except:
        pass
    
    return result
'''
        
        request_data = {
            "code": sample_code,
            "language": "python"
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Analyzing code...", total=None)
            
            try:
                async with self.session.post(
                    f"{self.base_url}/analyze",
                    json=request_data
                ) as response:
                    if response.status == 200:
                        analysis = await response.json()
                        progress.update(task, completed=True)
                        
                        self._display_code_analysis(sample_code, analysis)
                    else:
                        console.print(f"❌ Analysis failed: {response.status}", style="red")
            
            except Exception as e:
                console.print(f"❌ Analysis error: {e}", style="red")
    
    async def demo_code_improvement(self):
        """Demonstrate code improvement capabilities"""
        console.print("\n" + "="*80)
        console.print("⚡ CODE IMPROVEMENT DEMO", style="green bold")
        console.print("="*80)
        
        # Sample code that needs improvement
        original_code = '''
def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)

def main():
    for i in range(35):
        print(fib(i))
'''
        
        request_data = {
            "code": original_code,
            "language": "python",
            "focus_areas": ["performance", "readability"]
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Improving code...", total=None)
            
            try:
                async with self.session.post(
                    f"{self.base_url}/improve",
                    json=request_data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        progress.update(task, completed=True)
                        
                        self._display_code_improvement(original_code, result)
                    else:
                        console.print(f"❌ Improvement failed: {response.status}", style="red")
            
            except Exception as e:
                console.print(f"❌ Improvement error: {e}", style="red")
    
    async def demo_service_statistics(self):
        """Display service statistics"""
        console.print("\n" + "="*80)
        console.print("📊 SERVICE STATISTICS", style="cyan bold")
        console.print("="*80)
        
        try:
            async with self.session.get(f"{self.base_url}/statistics") as response:
                if response.status == 200:
                    stats = await response.json()
                    
                    # Create statistics table
                    stats_table = Table(title="Service Performance Metrics")
                    stats_table.add_column("Metric", style="cyan", no_wrap=True)
                    stats_table.add_column("Value", style="magenta")
                    
                    stats_table.add_row("Total Generations", str(stats.get("total_generations", 0)))
                    stats_table.add_row("Average Quality Score", f"{stats.get('average_quality_score', 0):.2f}")
                    stats_table.add_row("Service Status", stats.get("service_uptime", "Unknown"))
                    stats_table.add_row("Last Updated", stats.get("last_updated", "Unknown"))
                    
                    console.print(stats_table)
                    
                    # Language distribution
                    if stats.get("language_distribution"):
                        lang_dist = Table(title="Language Usage Distribution")
                        lang_dist.add_column("Language", style="green")
                        lang_dist.add_column("Usage Count", style="yellow")
                        
                        for lang, count in stats["language_distribution"].items():
                            lang_dist.add_row(lang, str(count))
                        
                        console.print(lang_dist)
                
        except Exception as e:
            console.print(f"❌ Failed to get statistics: {e}", style="red")
    
    async def _generate_and_display_code(self, request_data: Dict[str, Any], title: str):
        """Generate code and display results"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Generating {title}...", total=None)
            
            start_time = time.time()
            
            try:
                async with self.session.post(
                    f"{self.base_url}/generate",
                    json=request_data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        generation_time = time.time() - start_time
                        progress.update(task, completed=True)
                        
                        self._display_generation_result(result, title, generation_time)
                    else:
                        error_text = await response.text()
                        console.print(f"❌ Generation failed: {response.status} - {error_text}", style="red")
            
            except Exception as e:
                console.print(f"❌ Generation error: {e}", style="red")
    
    def _display_generation_result(self, result: Dict[str, Any], title: str, generation_time: float):
        """Display code generation result"""
        console.print(f"\n✅ {title} Generated Successfully!")
        console.print(f"⏱️  Generation Time: {generation_time:.2f}s")
        console.print(f"🤖 AI Provider: {result.get('provider_used', 'Unknown')}")
        console.print(f"⭐ Quality Score: {result.get('quality_score', 0):.2f}/1.0")
        
        # Display generated code
        code = result.get('code', '')
        language = result.get('language', 'text')
        
        if code:
            syntax = Syntax(code[:2000], language, theme="monokai", line_numbers=True)
            console.print(Panel(syntax, title=f"Generated {language.title()} Code"))
        
        # Display analysis
        analysis = result.get('analysis', {})
        if analysis:
            analysis_table = Table(title="Code Quality Analysis")
            analysis_table.add_column("Metric", style="cyan")
            analysis_table.add_column("Score", style="yellow")
            
            analysis_table.add_row("Quality", f"{analysis.get('quality_score', 0):.2f}")
            analysis_table.add_row("Complexity", f"{analysis.get('complexity_score', 0):.2f}")
            analysis_table.add_row("Maintainability", f"{analysis.get('maintainability_score', 0):.2f}")
            analysis_table.add_row("Documentation", f"{analysis.get('documentation_score', 0):.2f}")
            
            console.print(analysis_table)
        
        # Display suggestions
        suggestions = result.get('suggestions', [])
        if suggestions:
            console.print("\n💡 Improvement Suggestions:")
            for i, suggestion in enumerate(suggestions[:3], 1):
                console.print(f"  {i}. {suggestion}", style="yellow")
        
        # Display tests if available
        tests = result.get('tests', '')
        if tests and len(tests) > 50:
            console.print("\n🧪 Generated Tests Preview:")
            test_syntax = Syntax(tests[:500] + "...", language, theme="monokai")
            console.print(Panel(test_syntax, title="Unit Tests"))
    
    def _display_code_analysis(self, code: str, analysis: Dict[str, Any]):
        """Display code analysis results"""
        console.print("✅ Code Analysis Complete!")
        
        # Original code
        syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title="Original Code"))
        
        # Analysis results table
        analysis_table = Table(title="Analysis Results")
        analysis_table.add_column("Metric", style="cyan")
        analysis_table.add_column("Score", style="yellow")
        analysis_table.add_column("Status", style="white")
        
        quality = analysis.get('quality_score', 0)
        complexity = analysis.get('complexity_score', 0)
        maintainability = analysis.get('maintainability_score', 0)
        
        analysis_table.add_row("Quality Score", f"{quality:.2f}", "🟢" if quality > 0.7 else "🟡" if quality > 0.5 else "🔴")
        analysis_table.add_row("Complexity", f"{complexity:.2f}", "🟢" if complexity < 0.5 else "🟡" if complexity < 0.8 else "🔴")
        analysis_table.add_row("Maintainability", f"{maintainability:.2f}", "🟢" if maintainability > 0.7 else "🟡" if maintainability > 0.5 else "🔴")
        
        console.print(analysis_table)
        
        # Security issues
        security_issues = analysis.get('security_issues', [])
        if security_issues:
            console.print("\n🚨 Security Issues Found:")
            for issue in security_issues:
                console.print(f"  • Line {issue.get('line', '?')}: {issue.get('type', 'Unknown')} - {issue.get('description', '')}", style="red")
        
        # Performance suggestions
        perf_suggestions = analysis.get('performance_suggestions', [])
        if perf_suggestions:
            console.print("\n⚡ Performance Suggestions:")
            for suggestion in perf_suggestions:
                console.print(f"  • {suggestion}", style="yellow")
    
    def _display_code_improvement(self, original_code: str, result: Dict[str, Any]):
        """Display code improvement results"""
        console.print("✅ Code Improvement Complete!")
        
        # Original code
        original_syntax = Syntax(original_code, "python", theme="monokai", line_numbers=True)
        console.print(Panel(original_syntax, title="Original Code"))
        
        # Improved code
        improved_code = result.get('improved_code', '')
        if improved_code:
            improved_syntax = Syntax(improved_code, "python", theme="monokai", line_numbers=True)
            console.print(Panel(improved_syntax, title="Improved Code"))
        
        # Comparison table
        original_analysis = result.get('original_analysis', {})
        new_analysis = result.get('new_analysis', {})
        
        if original_analysis and new_analysis:
            comparison_table = Table(title="Improvement Comparison")
            comparison_table.add_column("Metric", style="cyan")
            comparison_table.add_column("Original", style="red")
            comparison_table.add_column("Improved", style="green")
            comparison_table.add_column("Change", style="yellow")
            
            orig_quality = original_analysis.get('quality_score', 0)
            new_quality = new_analysis.get('quality_score', 0)
            quality_change = new_quality - orig_quality
            
            orig_complexity = original_analysis.get('complexity_score', 0)
            new_complexity = new_analysis.get('complexity_score', 0)
            complexity_change = new_complexity - orig_complexity
            
            comparison_table.add_row(
                "Quality Score",
                f"{orig_quality:.2f}",
                f"{new_quality:.2f}",
                f"{quality_change:+.2f}"
            )
            
            comparison_table.add_row(
                "Complexity",
                f"{orig_complexity:.2f}",
                f"{new_complexity:.2f}",
                f"{complexity_change:+.2f}"
            )
            
            console.print(comparison_table)
        
        # Improvements made
        improvements = result.get('improvements', [])
        if improvements:
            console.print("\n🔧 Improvements Applied:")
            for improvement in improvements:
                console.print(f"  • {improvement}", style="green")

async def main():
    """Main demo function"""
    console.print(Panel.fit(
        """
🚀 Building Bots Network
Code Generation Service Demo

Showcasing construction excellence through
intelligent code generation and analysis
        """,
        style="blue bold"
    ))
    
    # Check for service URL argument
    service_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    async with CodeGenerationDemo(service_url) as demo:
        # Check service health
        if not await demo.check_service_health():
            console.print("❌ Service is not available. Please start the service first.", style="red bold")
            console.print(f"Expected URL: {service_url}")
            return
        
        # Show capabilities
        await demo.show_service_capabilities()
        
        # Demo scenarios
        demos = [
            ("Python Code Generation", demo.demo_python_generation),
            ("JavaScript/TypeScript Generation", demo.demo_javascript_generation),
            ("Rust Code Generation", demo.demo_rust_generation),
            ("Code Analysis", demo.demo_code_analysis),
            ("Code Improvement", demo.demo_code_improvement),
            ("Service Statistics", demo.demo_service_statistics)
        ]
        
        for title, demo_func in demos:
            try:
                console.print(f"\n⏳ Running: {title}")
                await demo_func()
                
                # Pause between demos
                console.print("\n" + "─" * 80)
                await asyncio.sleep(1)
                
            except KeyboardInterrupt:
                console.print("\n👋 Demo interrupted by user", style="yellow")
                break
            except Exception as e:
                console.print(f"❌ Demo '{title}' failed: {e}", style="red")
                continue
        
        console.print("\n")
        console.print(Panel.fit(
            """
🎉 Demo Complete!

The Building Bots Network Code Generation Service
demonstrates construction excellence through:

• Multi-provider AI integration
• Comprehensive quality analysis  
• Security vulnerability detection
• Performance optimization
• Cross-language support
• ML-powered intelligence
• Production-ready output

Ready to build the future with intelligent code generation!
            """,
            style="green bold"
        ))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n👋 Demo terminated by user", style="yellow")
    except Exception as e:
        console.print(f"❌ Demo failed: {e}", style="red bold")