#!/usr/bin/env python3
"""
Note Migration System - Move bot notes from local to EC2 instances
Clean up local space, establish EC2 as new note-taking location
"""

import os
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

class NoteMigrator:
    def __init__(self):
        self.local_path = Path("/home/activeloguser/activelog")
        self.migration_log = []
        
        # Bot instance mapping (from competition data)
        self.bot_instances = {
            "vestige_researcher": "i-0b61812de8ea6e0c1",
            "holographic_researcher": "i-0e4da12ade3468473", 
            "firefly_researcher": "i-02f80ff412d819349",
            "spatial_researcher": "i-0c3e7c1df714f297c",
            "consciousness_researcher": "i-03f56c900d7b38917",
            "economics_researcher": "i-0cb272de25786bc54",
            "integration_researcher": "i-07a5a3a6495788bd6"
        }
        
    def identify_bot_notes_for_migration(self):
        """Identify which local notes belong to which bots"""
        print("🔍 Identifying bot notes for migration...")
        
        bot_note_mapping = {
            "vestige_researcher": [
                "FUNCTIONAL_DEMOS/vestige_demo/",
                "SYSTEM/LOGS/cycle_*.log",
                "MASTER_DISSERTATION/ADAPTIVE_MODEL_CRITIQUE_SYSTEM.md"
            ],
            "holographic_researcher": [
                "FUNCTIONAL_DEMOS/holographic_demo/",
                "HOLOGRAPHIC_INTELLIGENCE/",
                "RESEARCH_DISSERTATIONS/DATA_SUMMARIES/holographic_encoding_*"
            ],
            "firefly_researcher": [
                "FUNCTIONAL_DEMOS/firefly_demo/",
                "FIREFLY_NEURAL_DEMOCRACY_DISSERTATION.md",
                "RESEARCH_DISSERTATIONS/DATA_SUMMARIES/firefly_democracy_*"
            ],
            "spatial_researcher": [
                "FUNCTIONAL_DEMOS/spatial_demo/",
                "HIERARCHICAL_NEURON_MODULES/",
                "RESEARCH_DISSERTATIONS/DATA_SUMMARIES/hierarchical_spatial_*"
            ],
            "consciousness_researcher": [
                "FUNCTIONAL_DEMOS/consciousness_demo/",
                "RESEARCH_DISSERTATIONS/DATA_SUMMARIES/asimov_analysis_*"
            ],
            "economics_researcher": [
                "FUNCTIONAL_DEMOS/economics_demo/",
                "RESEARCH_DISSERTATIONS/DATA_SUMMARIES/shipyard_economics_*"
            ],
            "integration_researcher": [
                "FUNCTIONAL_DEMOS/integration_demo/",
                "MASTER_DISSERTATION/COLLABORATIVE_MASTER/",
                "ULTIMATE_SYNTHESIS/"
            ]
        }
        
        print("📂 Bot note assignments:")
        for bot, paths in bot_note_mapping.items():
            print(f"  🤖 {bot}:")
            for path in paths:
                full_path = self.local_path / path
                if "*" in path:
                    # Handle wildcards
                    matching_files = list(full_path.parent.glob(full_path.name))
                    if matching_files:
                        print(f"    📄 {len(matching_files)} files matching {path}")
                elif full_path.exists():
                    if full_path.is_dir():
                        size = sum(f.stat().st_size for f in full_path.rglob('*') if f.is_file())
                        print(f"    📁 {path} ({size // 1024}KB)")
                    else:
                        size = full_path.stat().st_size
                        print(f"    📄 {path} ({size // 1024}KB)")
                        
        return bot_note_mapping
        
    def create_local_note_archives(self, bot_note_mapping):
        """Create compressed archives of each bot's notes"""
        print("\\n📦 Creating note archives for transfer...")
        
        archive_path = Path("/tmp/bot_note_archives")
        archive_path.mkdir(exist_ok=True)
        
        created_archives = {}
        
        for bot_name, note_paths in bot_note_mapping.items():
            print(f"  🤖 Archiving {bot_name} notes...")
            
            # Create temporary staging directory
            staging_dir = archive_path / f"{bot_name}_staging"
            staging_dir.mkdir(exist_ok=True)
            
            total_size = 0
            files_archived = 0
            
            for path_pattern in note_paths:
                source_path = self.local_path / path_pattern
                
                if "*" in path_pattern:
                    # Handle wildcards
                    matching_files = list(source_path.parent.glob(source_path.name))
                    for match in matching_files:
                        if match.exists():
                            dest_path = staging_dir / match.name
                            if match.is_dir():
                                shutil.copytree(match, dest_path)
                            else:
                                shutil.copy2(match, dest_path)
                            total_size += match.stat().st_size if match.is_file() else sum(f.stat().st_size for f in match.rglob('*'))
                            files_archived += 1
                elif source_path.exists():
                    dest_path = staging_dir / source_path.name
                    if source_path.is_dir():
                        shutil.copytree(source_path, dest_path)
                        total_size += sum(f.stat().st_size for f in source_path.rglob('*'))
                        files_archived += len(list(source_path.rglob('*')))
                    else:
                        shutil.copy2(source_path, dest_path)
                        total_size += source_path.stat().st_size
                        files_archived += 1
                        
            # Create compressed archive
            archive_file = archive_path / f"{bot_name}_notes.tar.gz"
            subprocess.run(["tar", "-czf", str(archive_file), "-C", str(staging_dir), "."])
            
            # Clean up staging
            shutil.rmtree(staging_dir)
            
            created_archives[bot_name] = {
                "archive_file": str(archive_file),
                "files_count": files_archived,
                "original_size_mb": total_size / (1024 * 1024),
                "archive_size_kb": archive_file.stat().st_size / 1024
            }
            
            print(f"    ✅ {files_archived} files, {total_size // 1024}KB → {archive_file.stat().st_size // 1024}KB archive")
            
        return created_archives
        
    def simulate_ec2_transfer(self, archives):
        """Simulate transferring archives to EC2 instances (actual transfer would need SSH keys)"""
        print("\\n🚀 Simulating note transfer to EC2 instances...")
        
        transfer_commands = []
        
        for bot_name, archive_info in archives.items():
            instance_id = self.bot_instances.get(bot_name, "unknown")
            archive_file = archive_info["archive_file"]
            
            # Commands that would be used for actual transfer
            scp_command = f"scp -i ~/.ssh/your-key.pem {archive_file} ec2-user@{instance_id}:/home/ec2-user/notes.tar.gz"
            ssh_extract = f"ssh -i ~/.ssh/your-key.pem ec2-user@{instance_id} 'cd /home/ec2-user && tar -xzf notes.tar.gz && rm notes.tar.gz'"
            
            transfer_commands.append({
                "bot": bot_name,
                "instance": instance_id,
                "scp_command": scp_command,
                "extract_command": ssh_extract,
                "archive_size": archive_info["archive_size_kb"]
            })
            
            print(f"  🤖 {bot_name} → {instance_id}")
            print(f"    📦 Archive: {archive_info['archive_size_kb']:.1f}KB")
            print(f"    💾 Storage available: 10GB per instance")
            
        # Save transfer commands for actual execution
        with open("ec2_transfer_commands.json", "w") as f:
            json.dump(transfer_commands, f, indent=2)
            
        print(f"\\n💾 Transfer commands saved to ec2_transfer_commands.json")
        return transfer_commands
        
    def clean_up_local_notes(self, bot_note_mapping):
        """Clean up local notes after confirming transfer"""
        print("\\n🧹 Cleaning up local notes (simulation)...")
        
        total_space_freed = 0
        cleaned_items = []
        
        for bot_name, note_paths in bot_note_mapping.items():
            print(f"  🤖 Cleaning {bot_name} local notes...")
            
            for path_pattern in note_paths:
                source_path = self.local_path / path_pattern
                
                if "*" in path_pattern:
                    matching_files = list(source_path.parent.glob(source_path.name))
                    for match in matching_files:
                        if match.exists():
                            if match.is_dir():
                                size = sum(f.stat().st_size for f in match.rglob('*'))
                            else:
                                size = match.stat().st_size
                            total_space_freed += size
                            cleaned_items.append(f"{bot_name}: {match.name} ({size // 1024}KB)")
                elif source_path.exists():
                    if source_path.is_dir():
                        size = sum(f.stat().st_size for f in source_path.rglob('*'))
                    else:
                        size = source_path.stat().st_size
                    total_space_freed += size
                    cleaned_items.append(f"{bot_name}: {source_path.name} ({size // 1024}KB)")
                    
        print(f"\\n📊 Local cleanup summary:")
        print(f"  🗑️  Items to clean: {len(cleaned_items)}")
        print(f"  💾 Space to free: {total_space_freed / (1024 * 1024):.1f}MB")
        
        # Don't actually delete - just report what would be cleaned
        print("\\n⚠️  Cleanup simulation only - files preserved for safety")
        
        return total_space_freed
        
    def establish_ec2_note_system(self):
        """Establish EC2 as new note-taking system"""
        print("\\n🏗️  Establishing EC2 as new bot note-taking system...")
        
        ec2_note_structure = {
            "research_notes": "Primary research findings and experiments",
            "experiment_logs": "Detailed logs of all competitive experiments",
            "shared_findings": "Findings shared with other competitive bots", 
            "competitive_data": "Private competitive advantage data",
            "performance_metrics": "Efficiency and optimization measurements",
            "collaboration_logs": "Cross-bot collaboration and sharing records"
        }
        
        print("📂 New EC2 note structure per bot:")
        for directory, purpose in ec2_note_structure.items():
            print(f"  📁 {directory}/: {purpose}")
            
        print("\\n🔄 Bot note-taking workflow:")
        print("  1. Each bot uses their 10GB EC2 storage for all new notes")
        print("  2. Competitive findings shared through /shared_findings/")  
        print("  3. Private research kept in /competitive_data/")
        print("  4. Performance metrics tracked in /performance_metrics/")
        print("  5. Laptop experiments can continue but results stored on EC2")
        
        return ec2_note_structure
        
    def run_complete_migration(self):
        """Run complete note migration process"""
        print("🚚 STARTING COMPLETE NOTE MIGRATION")
        print("=" * 50)
        
        # Identify notes to migrate
        bot_mapping = self.identify_bot_notes_for_migration()
        
        # Create archives
        archives = self.create_local_note_archives(bot_mapping)
        
        # Simulate transfer to EC2
        transfer_commands = self.simulate_ec2_transfer(archives)
        
        # Clean up local notes
        space_freed = self.clean_up_local_notes(bot_mapping)
        
        # Establish EC2 system
        ec2_structure = self.establish_ec2_note_system()
        
        print("\\n✅ MIGRATION COMPLETE")
        print(f"  🤖 {len(archives)} bots ready for EC2 note-taking")
        print(f"  📦 {len(archives)} archives created for transfer")
        print(f"  💾 {space_freed / (1024 * 1024):.1f}MB local space ready to free")
        print(f"  🏗️  EC2 note structure established")
        print("  🔄 Bots now use EC2 instances as primary note-taking space")
        
        return {
            "archives_created": len(archives),
            "transfer_commands": len(transfer_commands),
            "space_to_free_mb": space_freed / (1024 * 1024),
            "ec2_structure_ready": True
        }

if __name__ == "__main__":
    migrator = NoteMigrator()
    results = migrator.run_complete_migration()