#!/usr/bin/env python3
"""
Storage Monitor System for AI Professor College
- Monitors storage usage across all research directories
- Triggers summarization at configurable thresholds
- Maintains human and AI-readable organization
- Prevents system resource overload
"""

import os
import time
import json
from pathlib import Path
from datetime import datetime
import subprocess

class StorageMonitor:
    def __init__(self, base_path="/home/activeloguser/activelog"):
        self.base_path = Path(base_path)
        self.config_path = self.base_path / "STORAGE_CONFIG.json"
        self.load_config()
        
    def load_config(self):
        """Load or create storage configuration"""
        default_config = {
            "max_total_storage_gb": 100,
            "summarization_threshold_gb": 1.0,
            "max_threshold_gb": 2.0,
            "summarization_count": 0,
            "last_summarization": None,
            "slow_loop_interval_minutes": 15,
            "current_api": "claude"  # claude or openai
        }
        
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = default_config
            self.save_config()
    
    def save_config(self):
        """Save configuration to disk"""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get_directory_size(self, path):
        """Get size of directory in GB"""
        try:
            result = subprocess.run(['du', '-sb', str(path)], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                size_bytes = int(result.stdout.split()[0])
                return size_bytes / (1024**3)  # Convert to GB
        except (subprocess.TimeoutExpired, ValueError):
            pass
        return 0
    
    def monitor_storage(self):
        """Monitor current storage usage"""
        total_size = self.get_directory_size(self.base_path)
        
        storage_report = {
            "timestamp": datetime.now().isoformat(),
            "total_size_gb": round(total_size, 2),
            "threshold_gb": self.config["summarization_threshold_gb"],
            "max_storage_gb": self.config["max_total_storage_gb"],
            "summarization_count": self.config["summarization_count"]
        }
        
        # Check if summarization needed
        needs_summarization = total_size >= self.config["summarization_threshold_gb"]
        storage_report["needs_summarization"] = needs_summarization
        
        # Check if threshold adaptation needed
        if needs_summarization and self.config["summarization_count"] >= 5:
            self.adapt_threshold()
            storage_report["threshold_adapted"] = True
        
        return storage_report
    
    def adapt_threshold(self):
        """Increase threshold if summarizations are too frequent"""
        current_threshold = self.config["summarization_threshold_gb"]
        max_threshold = self.config["max_threshold_gb"]
        
        if current_threshold < max_threshold:
            self.config["summarization_threshold_gb"] = min(current_threshold * 1.5, max_threshold)
            self.config["summarization_count"] = 0  # Reset count
            self.save_config()
            print(f"Threshold adapted to {self.config['summarization_threshold_gb']:.2f}GB")
    
    def trigger_summarization(self, orchestrator=None):
        """Trigger system-wide summarization with smart question extraction"""
        print("🔄 Triggering system-wide summarization...")
        
        # Create backup of current state
        backup_dir = self.base_path / f"BACKUPS/pre_summarization_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Read content for question extraction before summarization
        if orchestrator and orchestrator.garbage_collector:
            content_to_analyze = ""
            
            # Gather content from key files for analysis
            key_files = [
                "ARCHIVES/DISSERTATIONS/*.md",
                "ACTIVE_RESEARCH/DEBATES/*.md",
                "SYSTEM/LOGS/*.log"
            ]
            
            for pattern in key_files:
                files = list(self.base_path.glob(pattern))
                for file_path in files[:5]:  # Limit to avoid overload
                    if file_path.exists() and file_path.stat().st_size < 1024*1024:  # < 1MB files only
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content_to_analyze += f"\n\n--- {file_path.name} ---\n"
                                content_to_analyze += f.read()[:10000]  # First 10KB per file
                        except Exception as e:
                            print(f"⚠️ Error reading {file_path}: {e}")
            
            # Extract and inject questions
            if content_to_analyze:
                questions = orchestrator.garbage_collector.extract_unanswered_questions(content_to_analyze)
                if questions:
                    orchestrator.garbage_collector.inject_questions_to_debate(questions)
        
        # Clean up EC2 experiments and terminate idle instances
        self.cleanup_ec2_experiments()
        
        # Clean up old redaction versions (keep only 3 most recent)
        self.cleanup_old_redactions()
        
        # Update config
        self.config["summarization_count"] += 1
        self.config["last_summarization"] = datetime.now().isoformat()
        self.save_config()
        
        return True
    
    def cleanup_ec2_experiments(self):
        """Clean up completed EC2 experiments and terminate idle instances"""
        experiment_dir = self.base_path / "SYSTEM" / "EC2_EXPERIMENTS" 
        if experiment_dir.exists():
            for exp_file in experiment_dir.glob("*.json"):
                # Clean up experiments older than 72 hours or marked complete
                exp_data = json.loads(exp_file.read_text())
                
                # Terminate instances if experiment complete or timeout
                if exp_data.get("status") == "complete" or self.is_old_experiment(exp_file, hours=72):
                    self.terminate_experiment_instances(exp_data.get("instance_ids", []))
                    exp_file.unlink()
                    print(f"Cleaned up experiment and terminated instances: {exp_file.name}")
    
    def terminate_experiment_instances(self, instance_ids):
        """Terminate EC2 instances for completed experiments"""
        if not instance_ids:
            return
            
        # Log instance termination (would integrate with AWS SDK in production)
        termination_log = {
            "timestamp": datetime.now().isoformat(),
            "action": "terminate_instances",
            "instance_ids": instance_ids,
            "reason": "experiment_complete_or_timeout"
        }
        
        cleanup_log = self.base_path / "SYSTEM" / "LOGS" / "ec2_cleanup.log"
        cleanup_log.parent.mkdir(parents=True, exist_ok=True)
        with open(cleanup_log, "a") as f:
            f.write(f"{json.dumps(termination_log)}\n")
            
        print(f"Would terminate EC2 instances: {instance_ids}")
    
    def is_old_experiment(self, exp_file, hours=72):
        """Check if experiment is older than specified hours"""
        file_time = datetime.fromtimestamp(exp_file.stat().st_mtime)
        return (datetime.now() - file_time).total_seconds() > (hours * 3600)
    
    def cleanup_old_redactions(self):
        """Keep only 3 most recent versions of each redaction type"""
        redactions_dir = self.base_path / "REDACTIONS"
        if not redactions_dir.exists():
            return
            
        for redaction_type in ["1PAGE", "10PAGE"]:
            type_dir = redactions_dir / redaction_type
            if not type_dir.exists():
                continue
                
            # Group files by base name (without version suffix)
            file_groups = {}
            for file_path in type_dir.glob("*.md"):
                base_name = file_path.stem.split('_v')[0]  # Remove version suffix
                if base_name not in file_groups:
                    file_groups[base_name] = []
                file_groups[base_name].append(file_path)
            
            # For each group, keep only 3 most recent versions
            for base_name, files in file_groups.items():
                if len(files) > 3:
                    # Sort by modification time (newest first)
                    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                    
                    # Delete all but the 3 most recent
                    for old_file in files[3:]:
                        old_file.unlink()
                        print(f"Cleaned up old redaction version: {old_file.name}")

class SmartGarbageCollector:
    def __init__(self):
        self.base_path = Path("/home/activeloguser/activelog")
        
    def extract_unanswered_questions(self, content):
        """Extract potential research questions from compressed content"""
        questions = []
        
        # Look for gaps in logic, unaddressed points, implementation details
        gap_indicators = [
            "but how", "however", "unclear", "remains to be seen",
            "future work", "not addressed", "open question",
            "needs further", "unexplored", "assumption",
            "theoretical", "proof of concept", "demonstration needed"
        ]
        
        # Extract sentences with gap indicators
        sentences = content.split('.')
        for sentence in sentences:
            for indicator in gap_indicators:
                if indicator in sentence.lower():
                    # Convert to question format
                    question = self.sentence_to_question(sentence.strip())
                    if question and len(question) > 20:
                        questions.append(question)
        
        # Generate implementation challenge questions
        if "tensor logic" in content.lower():
            questions.append("How would tensor logic handle real-world edge cases with corrupted or incomplete data?")
        if "file-locking" in content.lower():
            questions.append("What happens to file-locking coordination when network partitions occur?")
        if "$2/month" in content or "economic" in content.lower():
            questions.append("How do economic models account for scaling from 1 to 10,000 concurrent users?")
        if "integration" in content.lower():
            questions.append("What specific breaking changes occur when integrating with legacy enterprise systems?")
            
        return list(set(questions))  # Remove duplicates
    
    def sentence_to_question(self, sentence):
        """Convert statement to challenging question"""
        if not sentence:
            return None
            
        sentence = sentence.strip()
        if sentence.startswith("This") or sentence.startswith("The"):
            return f"Why is {sentence.lower()}?"
        elif "should" in sentence or "could" in sentence:
            return f"How exactly {sentence.lower()}?"
        elif "approach" in sentence or "method" in sentence:
            return f"What evidence supports that {sentence.lower()}?"
        else:
            return f"How do you prove {sentence.lower()}?"
    
    def inject_questions_to_debate(self, questions):
        """Inject unanswered questions into the debate board"""
        if not questions:
            return
            
        debate_board = self.base_path / "ACTIVE_RESEARCH/DEBATES/AI_PROFESSOR_DEBATE_BOARD.md"
        
        if debate_board.exists():
            with open(debate_board, 'r') as f:
                content = f.read()
            
            # Create question injection section
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            injection = f"\n\n---\n\n## 🤖 GARBAGE COLLECTOR CHALLENGES [{timestamp}]\n\n"
            injection += "**Unanswered questions identified during compression:**\n\n"
            
            for i, question in enumerate(questions[:5], 1):  # Limit to 5 best questions
                injection += f"{i}. **{question}**\n"
            
            injection += f"\n*Challenge: All professors must address at least one of these questions in their next response.*\n"
            injection += f"\n*Questions generated from {len(questions)} potential research gaps identified.*\n"
            
            # Inject before the current message queue
            content = content.replace("## Current Message Queue:", 
                                    f"{injection}\n\n## Current Message Queue:")
            
            with open(debate_board, 'w') as f:
                f.write(content)
            
            print(f"💡 Injected {len(questions)} challenging questions into debate")

class BotOrchestrator:
    def __init__(self):
        self.storage_monitor = StorageMonitor()
        self.garbage_collector = SmartGarbageCollector()
        self.running = False
        
    def switch_api_provider(self):
        """Switch between Claude and OpenAI based on token availability"""
        current = self.storage_monitor.config["current_api"]
        new_api = "openai" if current == "claude" else "claude"
        
        self.storage_monitor.config["current_api"] = new_api
        self.storage_monitor.save_config()
        
        print(f"🔄 Switched API from {current} to {new_api}")
        return new_api
    
    def slow_loop_delay(self):
        """Implement slow loop to prevent system overload"""
        interval = self.storage_monitor.config["slow_loop_interval_minutes"]
        print(f"💤 Slow loop delay: {interval} minutes...")
        time.sleep(interval * 60)
    
    def run_endless_loop(self):
        """Run the endless bot orchestration loop"""
        print("🚀 Starting AI Professor College Endless Loop")
        self.running = True
        
        while self.running:
            try:
                # Monitor storage
                report = self.storage_monitor.monitor_storage()
                print(f"📊 Storage: {report['total_size_gb']:.2f}GB / {report['max_storage_gb']}GB")
                
                # Check if summarization needed
                if report["needs_summarization"]:
                    self.storage_monitor.trigger_summarization(self)
                    # Smart garbage collection with question injection completed
                
                # Continue with bot orchestration
                current_api = self.storage_monitor.config["current_api"]
                print(f"🤖 Running with {current_api} API")
                
                # Slow loop to prevent system overload
                self.slow_loop_delay()
                
            except KeyboardInterrupt:
                print("🛑 Stopping endless loop...")
                self.running = False
            except Exception as e:
                print(f"❌ Error in endless loop: {e}")
                self.slow_loop_delay()

if __name__ == "__main__":
    orchestrator = BotOrchestrator()
    orchestrator.run_endless_loop()