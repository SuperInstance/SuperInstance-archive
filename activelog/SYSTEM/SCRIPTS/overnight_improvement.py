#!/usr/bin/env python3
"""
Overnight Improvement System - Python Controller
Manages autonomous research synthesis and project enhancement
"""

import argparse
import json
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

class OvernightImprovementSystem:
    def __init__(self, cycle_num, max_api_cost, storage_limit):
        self.cycle_num = cycle_num
        self.max_api_cost = max_api_cost
        self.storage_limit = storage_limit
        self.base_path = Path("/home/activeloguser/activelog")
        self.api_cost_used = 0
        
        # Setup logging
        log_path = self.base_path / "SYSTEM" / "LOGS" / f"cycle_{cycle_num}_{datetime.now().strftime('%H%M%S')}.log"
        logging.basicConfig(
            filename=log_path,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def check_storage_usage(self):
        """Check current storage usage"""
        try:
            result = subprocess.run(
                ['du', '-sm', str(self.base_path)], 
                capture_output=True, text=True, check=True
            )
            current_usage = int(result.stdout.split()[0])
            self.logger.info(f"Current storage usage: {current_usage}MB / {self.storage_limit}MB")
            return current_usage
        except Exception as e:
            self.logger.error(f"Failed to check storage usage: {e}")
            return 0
    
    def estimate_api_cost(self, prompt_length):
        """Estimate API cost for Claude call"""
        # Rough estimate: $0.015 per 1K input tokens, $0.075 per 1K output tokens
        # Assume average 2K input, 1K output per call = ~$0.105 per call
        return 0.11  # Conservative estimate per API call
    
    def run_claude_synthesis(self, task_description, input_files, max_output_tokens=2000):
        """Run Claude API synthesis task"""
        if self.api_cost_used + 0.11 > self.max_api_cost:
            self.logger.warning(f"API budget limit reached: ${self.api_cost_used:.2f} / ${self.max_api_cost}")
            return None
        
        try:
            # Create task prompt
            prompt = f"""
            Task: {task_description}
            
            Available files to analyze: {', '.join(input_files)}
            
            Please provide a concise synthesis focusing on:
            1. Key insights from the analyzed content
            2. Practical improvements that can be implemented
            3. Cross-connections between different research areas
            4. Next steps for development
            
            Output should be structured, actionable, and under {max_output_tokens} tokens.
            """
            
            # For demonstration, we'll simulate the Claude API call
            # In real implementation, you'd use the actual Claude API
            self.logger.info(f"Running Claude synthesis: {task_description}")
            self.api_cost_used += 0.11
            
            return {
                "task": task_description,
                "synthesis": "Simulated Claude synthesis output - in real implementation this would be Claude API response",
                "cost": 0.11,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            self.logger.error(f"Claude synthesis failed: {e}")
            return None
    
    def identify_improvement_opportunities(self):
        """Identify areas for improvement based on current project state"""
        opportunities = []
        
        # Check for incomplete research areas
        research_dirs = [
            "RESEARCH_DISSERTATIONS",
            "MASTER_DISSERTATION", 
            "CREATIVE_PROJECTS/SUPERINSTANCE_SERIES"
        ]
        
        for dir_name in research_dirs:
            dir_path = self.base_path / dir_name
            if dir_path.exists():
                files = list(dir_path.rglob("*.md"))
                self.logger.info(f"Found {len(files)} files in {dir_name}")
                
                # Look for files that could benefit from synthesis
                for file_path in files:
                    if file_path.stat().st_size > 1000:  # Files larger than 1KB
                        opportunities.append({
                            "type": "synthesis",
                            "description": f"Synthesize insights from {file_path.name}",
                            "file_path": str(file_path),
                            "priority": self.calculate_priority(file_path)
                        })
        
        # Sort by priority
        opportunities.sort(key=lambda x: x["priority"], reverse=True)
        return opportunities[:5]  # Top 5 opportunities per cycle
    
    def calculate_priority(self, file_path):
        """Calculate improvement priority for a file"""
        priority = 0
        
        # Recent files get higher priority
        age_days = (time.time() - file_path.stat().st_mtime) / 86400
        priority += max(0, 10 - age_days)
        
        # Larger files get moderate priority
        size_mb = file_path.stat().st_size / (1024 * 1024)
        priority += min(5, size_mb)
        
        # Certain keywords increase priority
        high_priority_keywords = [
            "synthesis", "breakthrough", "integration", "framework", 
            "superinstance", "vestige", "holographic", "democratic"
        ]
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore').lower()
            for keyword in high_priority_keywords:
                if keyword in content:
                    priority += 2
        except Exception:
            pass
        
        return priority
    
    def create_improvement_synthesis(self, opportunities):
        """Create synthesis documents for improvement opportunities"""
        syntheses = []
        
        for opp in opportunities:
            if self.api_cost_used >= self.max_api_cost:
                break
            
            self.logger.info(f"Processing opportunity: {opp['description']}")
            
            synthesis = self.run_claude_synthesis(
                task_description=opp['description'],
                input_files=[opp['file_path']],
                max_output_tokens=1500
            )
            
            if synthesis:
                syntheses.append(synthesis)
                
                # Save synthesis to file
                output_path = self.base_path / "SYSTEM" / "OVERNIGHT_IMPROVEMENTS" / f"cycle_{self.cycle_num}"
                output_path.mkdir(parents=True, exist_ok=True)
                
                synthesis_file = output_path / f"synthesis_{len(syntheses)}.json"
                with open(synthesis_file, 'w') as f:
                    json.dump(synthesis, f, indent=2)
        
        return syntheses
    
    def update_project_roadmap(self, syntheses):
        """Update project roadmap based on syntheses"""
        roadmap_path = self.base_path / "SYSTEM" / "PROJECT_ROADMAP.md"
        
        try:
            if roadmap_path.exists():
                current_roadmap = roadmap_path.read_text()
            else:
                current_roadmap = "# Project Roadmap\n\n"
            
            # Add new insights section
            new_section = f"\n## Overnight Cycle {self.cycle_num} Insights ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
            
            for i, synthesis in enumerate(syntheses, 1):
                new_section += f"### Synthesis {i}: {synthesis['task']}\n"
                new_section += f"{synthesis['synthesis']}\n\n"
            
            # Add to roadmap
            updated_roadmap = current_roadmap + new_section
            roadmap_path.write_text(updated_roadmap)
            
            self.logger.info(f"Updated project roadmap with {len(syntheses)} syntheses")
            
        except Exception as e:
            self.logger.error(f"Failed to update project roadmap: {e}")
    
    def cleanup_old_files(self):
        """Cleanup old files to manage storage"""
        try:
            # Remove temp files
            temp_files = list(self.base_path.rglob("*.tmp"))
            for temp_file in temp_files:
                temp_file.unlink()
                self.logger.info(f"Removed temp file: {temp_file}")
            
            # Compress large old files
            old_large_files = [
                f for f in self.base_path.rglob("*.md") 
                if f.stat().st_size > 100000 and  # > 100KB
                (time.time() - f.stat().st_mtime) > 86400  # > 1 day old
            ]
            
            for file_path in old_large_files[:5]:  # Limit to 5 files per cycle
                compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
                if not compressed_path.exists():
                    subprocess.run(['gzip', str(file_path)], check=True)
                    self.logger.info(f"Compressed: {file_path}")
        
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
    
    def run_cycle(self):
        """Run complete improvement cycle"""
        self.logger.info(f"Starting improvement cycle {self.cycle_num}")
        
        # Check initial storage
        storage_usage = self.check_storage_usage()
        if storage_usage > self.storage_limit * 0.9:  # 90% limit
            self.logger.warning("Storage nearly full, running cleanup")
            self.cleanup_old_files()
        
        # Identify improvement opportunities
        opportunities = self.identify_improvement_opportunities()
        self.logger.info(f"Found {len(opportunities)} improvement opportunities")
        
        # Create syntheses
        syntheses = self.create_improvement_synthesis(opportunities)
        self.logger.info(f"Created {len(syntheses)} syntheses, API cost: ${self.api_cost_used:.2f}")
        
        # Update project roadmap
        if syntheses:
            self.update_project_roadmap(syntheses)
        
        # Final storage check
        final_storage = self.check_storage_usage()
        self.logger.info(f"Cycle completed. Final storage: {final_storage}MB, API cost: ${self.api_cost_used:.2f}")
        
        return {
            "cycle": self.cycle_num,
            "opportunities_found": len(opportunities),
            "syntheses_created": len(syntheses),
            "api_cost": self.api_cost_used,
            "storage_usage": final_storage,
            "success": True
        }

def main():
    parser = argparse.ArgumentParser(description="Overnight Improvement System")
    parser.add_argument("--cycle", type=int, required=True, help="Cycle number")
    parser.add_argument("--max-api-cost", type=float, default=4.0, help="Maximum API cost per cycle")
    parser.add_argument("--storage-limit", type=int, default=8192, help="Storage limit in MB")
    
    args = parser.parse_args()
    
    try:
        system = OvernightImprovementSystem(
            cycle_num=args.cycle,
            max_api_cost=args.max_api_cost,
            storage_limit=args.storage_limit
        )
        
        result = system.run_cycle()
        
        # Output result for shell script
        print(f"Cycle {result['cycle']} completed successfully")
        print(f"API cost: ${result['api_cost']:.2f}")
        print(f"Storage usage: {result['storage_usage']}MB")
        
        return 0 if result['success'] else 1
    
    except Exception as e:
        print(f"Cycle failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())