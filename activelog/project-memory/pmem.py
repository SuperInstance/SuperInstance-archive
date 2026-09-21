#!/usr/bin/env python3
"""
Project Memory CLI Interface

Command-line interface for the intelligent project memory system.
Provides quick access to optimized documentation and context management.
"""

import argparse
import sys
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

# Add project paths
sys.path.insert(0, str(Path(__file__).parent / "context"))
sys.path.insert(0, str(Path(__file__).parent / "views"))
sys.path.insert(0, str(Path(__file__).parent / "generator"))

from optimizer import ContextOptimizer, ConceptQuery, BotType, ViewLevel
from selector import ViewSelector, BotCapability, TaskType
from scanner import CodeScanner
from updater import DocumentationUpdater
from init_memory import ProjectMemoryInitializer

class ProjectMemoryCLI:
    """Command-line interface for project memory system."""
    
    def __init__(self, memory_path: str = None):
        self.memory_path = memory_path or "/home/activeloguser/activelog/project-memory"
        self.project_path = "/home/activeloguser/activelog"
        
        # Initialize components
        self.optimizer = ContextOptimizer(self.memory_path)
        self.selector = ViewSelector(self.memory_path)
        self.scanner = CodeScanner(self.project_path, self.memory_path)
        self.updater = DocumentationUpdater(self.project_path, self.memory_path)
    
    def query_concept(self, concept_id: str, bot_type: str = "advanced", 
                     max_tokens: int = 2000, include_deps: bool = True) -> Dict:
        """Query a specific concept with optimization."""
        
        try:
            bot_type_enum = BotType(bot_type.lower())
        except ValueError:
            bot_type_enum = BotType.ADVANCED
        
        query = ConceptQuery(
            concept_id=concept_id,
            bot_type=bot_type_enum,
            max_tokens=max_tokens,
            include_dependencies=include_deps,
            expand_level=ViewLevel.ADVANCED
        )
        
        response = self.optimizer.query_concept(query)
        
        return {
            "concept_id": response.concept_id,
            "content": response.content,
            "token_count": response.token_count,
            "compression_ratio": f"{response.compression_ratio:.1%}",
            "dependencies_loaded": response.dependencies_loaded,
            "related_concepts": response.related_concepts
        }
    
    def get_smart_view(self, concept_ids: List[str], bot_description: str,
                      user_query: str) -> Dict:
        """Get optimized view based on bot capabilities and query."""
        
        doc_package = self.selector.create_bot_specific_documentation(
            concept_ids, bot_description, user_query
        )
        
        # Load actual content for selected concepts
        content = {}
        total_tokens = 0
        
        for concept_id in doc_package["selected_concepts"]:
            try:
                concept_response = self.optimizer.query_concept(
                    ConceptQuery(
                        concept_id=concept_id,
                        bot_type=BotType(doc_package["bot_capability"]),
                        max_tokens=doc_package["token_budget"] // len(doc_package["selected_concepts"]),
                        expand_level=ViewLevel(doc_package["recommended_detail_level"])
                    )
                )
                content[concept_id] = concept_response.content
                total_tokens += concept_response.token_count
                
            except Exception as e:
                content[concept_id] = f"Error loading {concept_id}: {e}"
        
        return {
            "bot_analysis": {
                "detected_capability": doc_package["bot_capability"],
                "detected_task_type": doc_package["task_type"],
                "optimization_applied": doc_package["optimization_applied"]
            },
            "resource_usage": {
                "token_budget": doc_package["token_budget"],
                "tokens_used": total_tokens,
                "utilization": f"{total_tokens / doc_package['token_budget']:.1%}"
            },
            "selected_concepts": doc_package["selected_concepts"],
            "content": content
        }
    
    def scan_changes(self) -> Dict:
        """Scan for code changes and analyze impact."""
        changes = self.scanner.scan_for_changes()
        
        if not changes:
            return {"message": "No changes detected", "changes": []}
        
        impact_report = self.scanner.get_concept_impact_report(changes)
        outdated_concepts = self.scanner.get_outdated_concepts()
        
        return {
            "changes_found": len(changes),
            "concepts_affected": len(impact_report),
            "outdated_concepts": len(outdated_concepts),
            "recent_changes": [
                {
                    "file": change.file_path,
                    "type": change.change_type,
                    "affected_concepts": change.affected_concepts
                }
                for change in changes[:10]  # Show latest 10
            ],
            "impact_summary": {
                concept_id: {
                    "files_changed": len(impact["files_changed"]),
                    "change_types": impact["change_types"],
                    "total_changes": impact["total_changes"]
                }
                for concept_id, impact in list(impact_report.items())[:5]
            },
            "outdated_concepts": outdated_concepts[:10]
        }
    
    def update_documentation(self, auto_approve: bool = False) -> Dict:
        """Update documentation based on code changes."""
        changes = self.scanner.scan_for_changes()
        
        if not changes:
            return {"message": "No changes to process"}
        
        tasks = self.updater.analyze_update_needs(changes)
        
        if not auto_approve:
            return {
                "tasks_generated": len(tasks),
                "high_priority": len([t for t in tasks if t.priority == "high"]),
                "tasks": [
                    {
                        "concept_id": task.concept_id,
                        "priority": task.priority,
                        "task_type": task.task_type,
                        "reason": task.reason,
                        "files_affected": len(task.files_affected),
                        "effort": task.estimated_effort
                    }
                    for task in tasks[:10]
                ],
                "note": "Use --auto-approve to execute high priority tasks"
            }
        
        # Execute high priority tasks
        executed_tasks = []
        high_priority_tasks = [t for t in tasks if t.priority == "high"]
        
        for task in high_priority_tasks[:5]:  # Limit to 5 tasks
            success = self.updater.execute_update_task(task)
            executed_tasks.append({
                "concept_id": task.concept_id,
                "task_type": task.task_type,
                "success": success
            })
        
        return {
            "tasks_executed": len(executed_tasks),
            "results": executed_tasks
        }
    
    def get_system_stats(self) -> Dict:
        """Get system statistics and health info."""
        budget_info = self.optimizer.get_context_budget_info()
        
        # Count concepts
        manifest_file = Path(self.memory_path) / "context" / "manifest.json"
        concepts_count = 0
        if manifest_file.exists():
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
                concepts_count = len(manifest.get("concepts", {}))
        
        # Check documentation files
        knowledge_path = Path(self.memory_path) / "knowledge"
        doc_files = list(knowledge_path.rglob("*.md")) if knowledge_path.exists() else []
        
        return {
            "system_health": {
                "concepts_tracked": concepts_count,
                "documentation_files": len(doc_files),
                "memory_path_exists": Path(self.memory_path).exists(),
                "project_path_exists": Path(self.project_path).exists()
            },
            "optimization": budget_info,
            "recent_activity": manifest.get("usage_stats", {}) if 'manifest' in locals() else {}
        }
    
    def initialize_system(self, project_path: str = None, dry_run: bool = False) -> Dict:
        """Initialize project memory for a codebase."""
        target_path = project_path or self.project_path
        
        initializer = ProjectMemoryInitializer(target_path, self.memory_path)
        
        if dry_run:
            structure = initializer.analyze_project_structure()
            concepts = initializer.generate_concept_hierarchy(structure)
            
            return {
                "dry_run": True,
                "analysis": {
                    "services_found": len(structure.get("services", {})),
                    "frontends_found": len(structure.get("frontends", {})),
                    "concepts_would_generate": len(concepts),
                    "config_files": len(structure.get("core_files", {}).get("config_files", []))
                }
            }
        else:
            success = initializer.initialize_project_memory()
            return {"initialized": success}


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Project Memory - Intelligent codebase understanding system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pmem query CORE-001                           # Query core concept
  pmem query AUTH-001 --bot-type=simple        # Simple view of auth
  pmem view "I'm a code assistant" "fix auth bug" CORE-001,AUTH-001
  pmem scan                                     # Scan for code changes  
  pmem update --auto-approve                   # Update documentation
  pmem stats                                   # System statistics
  pmem init ~/my-project                       # Initialize new project
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Query command
    query_parser = subparsers.add_parser('query', help='Query a specific concept')
    query_parser.add_argument('concept_id', help='Concept ID to query (e.g., CORE-001)')
    query_parser.add_argument('--bot-type', choices=['simple', 'advanced', 'expert'], 
                             default='advanced', help='Bot capability type')
    query_parser.add_argument('--max-tokens', type=int, default=2000, 
                             help='Maximum tokens to use')
    query_parser.add_argument('--no-deps', action='store_true', 
                             help='Don\'t include dependencies')
    
    # View command
    view_parser = subparsers.add_parser('view', help='Get optimized view for bot')
    view_parser.add_argument('bot_description', help='Description of bot capabilities')
    view_parser.add_argument('user_query', help='User query or task description')
    view_parser.add_argument('concept_ids', help='Comma-separated concept IDs')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan for code changes')
    
    # Update command  
    update_parser = subparsers.add_parser('update', help='Update documentation')
    update_parser.add_argument('--auto-approve', action='store_true',
                              help='Automatically execute high priority updates')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show system statistics')
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize project memory')
    init_parser.add_argument('project_path', nargs='?', help='Path to project root')
    init_parser.add_argument('--dry-run', action='store_true',
                           help='Analyze only, don\'t create files')
    
    # Global options
    parser.add_argument('--memory-path', help='Override memory storage path')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize CLI
    cli = ProjectMemoryCLI(args.memory_path)
    
    try:
        # Execute commands
        if args.command == 'query':
            result = cli.query_concept(
                args.concept_id,
                args.bot_type,
                args.max_tokens,
                not args.no_deps
            )
            
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Concept: {result['concept_id']}")
                print(f"Tokens: {result['token_count']} (compression: {result['compression_ratio']})")
                if result['dependencies_loaded']:
                    print(f"Dependencies: {', '.join(result['dependencies_loaded'])}")
                print(f"\nContent:\n{result['content']}")
                if result['related_concepts']:
                    print(f"\nRelated: {', '.join(result['related_concepts'][:5])}")
        
        elif args.command == 'view':
            concept_ids = [cid.strip() for cid in args.concept_ids.split(',')]
            result = cli.get_smart_view(concept_ids, args.bot_description, args.user_query)
            
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Bot Analysis:")
                print(f"  Capability: {result['bot_analysis']['detected_capability']}")
                print(f"  Task Type: {result['bot_analysis']['detected_task_type']}")
                print(f"Resource Usage:")
                print(f"  Budget: {result['resource_usage']['token_budget']} tokens")
                print(f"  Used: {result['resource_usage']['tokens_used']} ({result['resource_usage']['utilization']})")
                print(f"\nSelected Concepts: {', '.join(result['selected_concepts'])}")
                print("\nContent:")
                for concept_id, content in result['content'].items():
                    print(f"\n--- {concept_id} ---")
                    print(content[:500] + "..." if len(content) > 500 else content)
        
        elif args.command == 'scan':
            result = cli.scan_changes()
            
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if result.get('changes_found', 0) == 0:
                    print("No changes detected")
                else:
                    print(f"Found {result['changes_found']} changes affecting {result['concepts_affected']} concepts")
                    if result['recent_changes']:
                        print("\nRecent Changes:")
                        for change in result['recent_changes'][:5]:
                            print(f"  {change['type']}: {change['file']}")
                            if change['affected_concepts']:
                                print(f"    Affects: {', '.join(change['affected_concepts'])}")
                    
                    if result['outdated_concepts']:
                        print(f"\nOutdated concepts: {', '.join(result['outdated_concepts'][:5])}")
        
        elif args.command == 'update':
            result = cli.update_documentation(args.auto_approve)
            
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if 'tasks_generated' in result:
                    print(f"Generated {result['tasks_generated']} update tasks")
                    print(f"High priority: {result.get('high_priority', 0)}")
                    if not args.auto_approve:
                        print("\nAdd --auto-approve to execute high priority tasks")
                elif 'tasks_executed' in result:
                    print(f"Executed {result['tasks_executed']} tasks")
                    for task_result in result['results']:
                        status = "✓" if task_result['success'] else "✗"
                        print(f"  {status} {task_result['concept_id']} ({task_result['task_type']})")
                else:
                    print(result.get('message', 'Update completed'))
        
        elif args.command == 'stats':
            result = cli.get_system_stats()
            
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                health = result['system_health']
                print(f"System Health:")
                print(f"  Concepts tracked: {health['concepts_tracked']}")
                print(f"  Documentation files: {health['documentation_files']}")
                print(f"  Memory system: {'✓' if health['memory_path_exists'] else '✗'}")
                print(f"  Project access: {'✓' if health['project_path_exists'] else '✗'}")
                
                opt = result['optimization']
                print(f"\nOptimization:")
                print(f"  Total concepts: {opt['total_concepts']}")
                print(f"  Simple view utilization: {opt['simple_utilization']:.1%}")
                print(f"  Advanced view utilization: {opt['advanced_utilization']:.1%}")
        
        elif args.command == 'init':
            result = cli.initialize_system(args.project_path, args.dry_run)
            
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if result.get('dry_run'):
                    analysis = result['analysis']
                    print(f"Dry Run Analysis:")
                    print(f"  Services: {analysis['services_found']}")
                    print(f"  Frontends: {analysis['frontends_found']}")
                    print(f"  Concepts to generate: {analysis['concepts_would_generate']}")
                    print(f"  Config files: {analysis['config_files']}")
                else:
                    status = "✓" if result['initialized'] else "✗"
                    print(f"Initialization: {status}")
    
    except KeyboardInterrupt:
        print("\nOperation cancelled")
        sys.exit(1)
    except Exception as e:
        if args.verbose:
            import traceback
            traceback.print_exc()
        else:
            print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()