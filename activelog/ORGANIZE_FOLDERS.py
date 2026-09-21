#!/usr/bin/env python3
"""
Folder Organization System for AI Professor College
- Creates human and AI-readable folder structure
- Maintains clean organization under 100GB limit
- Facilitates easy understanding for future Claude bots
"""

import os
from pathlib import Path
import shutil
from datetime import datetime

class FolderOrganizer:
    def __init__(self, base_path="/home/activeloguser/activelog"):
        self.base_path = Path(base_path)
        self.create_folder_structure()
    
    def create_folder_structure(self):
        """Create organized folder structure"""
        folders = {
            # Core System Folders
            "ACTIVE_RESEARCH/": "Current ongoing research and debates",
            "ACTIVE_RESEARCH/PROFESSORS/": "Individual professor workspaces",
            "ACTIVE_RESEARCH/DEBATES/": "Active debate threads and discussions",
            "ACTIVE_RESEARCH/EXPERIMENTS/": "Current thought experiments and tests",
            
            # Archive and Storage
            "ARCHIVES/": "Compressed historical research",
            "ARCHIVES/DEBATES/": "Archived debate threads by date",
            "ARCHIVES/DISSERTATIONS/": "Completed dissertations and papers",
            "ARCHIVES/INSIGHTS/": "Key breakthrough insights",
            
            # Future Studies (High Value)
            "FUTURE_STUDIES/": "Critical innovations for future development",
            "FUTURE_STUDIES/BREAKTHROUGHS/": "Patent-worthy innovations",
            "FUTURE_STUDIES/IMPLEMENTATIONS/": "Practical implementation guides",
            "FUTURE_STUDIES/ROADMAPS/": "Development roadmaps and strategies",
            
            # System Management
            "SYSTEM/": "Bot management and orchestration",
            "SYSTEM/CONFIGS/": "Configuration files and settings",
            "SYSTEM/LOGS/": "System operation logs (auto-cleaned)",
            "SYSTEM/BACKUPS/": "System state backups",
            
            # Human Interface
            "HUMAN_READABLE/": "Simplified summaries for human consumption",
            "HUMAN_READABLE/SUMMARIES/": "Executive summaries of research",
            "HUMAN_READABLE/GUIDES/": "Implementation guides for developers",
            "HUMAN_READABLE/REPORTS/": "Progress reports and status updates",
            
            # AI Interface
            "AI_READABLE/": "Structured data for future AI systems",
            "AI_READABLE/KNOWLEDGE_GRAPHS/": "Structured knowledge representations",
            "AI_READABLE/CONTEXT_COMPRESSED/": "Ultra-compressed context for bot loading",
            "AI_READABLE/INSTRUCTION_SETS/": "Bot instruction templates and prompts"
        }
        
        for folder, description in folders.items():
            folder_path = self.base_path / folder
            folder_path.mkdir(parents=True, exist_ok=True)
            
            # Create README in each folder
            readme_path = folder_path / "README.md"
            if not readme_path.exists():
                with open(readme_path, 'w') as f:
                    f.write(f"# {folder.rstrip('/')}\n\n{description}\n\n")
                    f.write(f"Created: {datetime.now().isoformat()}\n")
        
        print("📁 Folder structure organized successfully")
    
    def organize_existing_files(self):
        """Move existing files to appropriate folders"""
        moves = {
            # Research documents
            "MASTER_DISSERTATION_COMPLETE.md": "ARCHIVES/DISSERTATIONS/",
            "TINY_FAST_BOT_SWARM_RESEARCH_5A.md": "ARCHIVES/DISSERTATIONS/",
            "TINY_FAST_BOT_SWARM_RESEARCH_5B.md": "ARCHIVES/DISSERTATIONS/",
            "OPENSOURCE_BOT_FRAMEWORK_RESEARCH_1.md": "ARCHIVES/DISSERTATIONS/",
            
            # Active debates
            "AI_PROFESSOR_DEBATE_BOARD.md": "ACTIVE_RESEARCH/DEBATES/",
            
            # System files
            "STORAGE_MONITOR.py": "SYSTEM/CONFIGS/",
            "STORAGE_CONFIG.json": "SYSTEM/CONFIGS/",
            
            # Future studies
            "FUTURE_STUDIES/*": "FUTURE_STUDIES/"
        }
        
        for source_pattern, dest_folder in moves.items():
            dest_path = self.base_path / dest_folder
            dest_path.mkdir(parents=True, exist_ok=True)
            
            # Handle wildcard patterns
            if "*" in source_pattern:
                source_dir = self.base_path / source_pattern.split("*")[0].rstrip("/")
                if source_dir.exists():
                    for item in source_dir.iterdir():
                        if item.is_file():
                            shutil.move(str(item), str(dest_path / item.name))
            else:
                source_file = self.base_path / source_pattern
                if source_file.exists():
                    shutil.move(str(source_file), str(dest_path / source_file.name))
        
        print("📂 Existing files organized successfully")

if __name__ == "__main__":
    organizer = FolderOrganizer()
    organizer.organize_existing_files()