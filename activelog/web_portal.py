#!/usr/bin/env python3
"""
ActiveLog AI Professor College Web Portal
- Download interface for all project documents
- Real-time debate chat interface 
- Bot participation monitoring
"""

from flask import Flask, render_template, send_file, jsonify, request
import os
from pathlib import Path
import json
from datetime import datetime
import re
import zipfile
import tempfile
import mimetypes

app = Flask(__name__, template_folder='templates', static_folder='static')
BASE_PATH = Path("/home/activeloguser/activelog")

class DocumentManager:
    def __init__(self):
        self.base_path = BASE_PATH
        
    def get_prioritized_documents(self):
        """Get documents prioritized by importance"""
        priority_docs = {
            "Master Dissertations": {
                "priority": 1,
                "patterns": ["**/MASTER_DISSERTATION*.md", "**/master_collaboration*.md"],
                "description": "Primary research compilations and collaborative dissertations"
            },
            "Executive Summaries": {
                "priority": 1.5,
                "patterns": ["**/REDACTIONS/1PAGE/*.md"],
                "description": "1-page executive summaries of dissertation key findings"
            },
            "Implementation Guides": {
                "priority": 1.6, 
                "patterns": ["**/REDACTIONS/10PAGE/*.md"],
                "description": "10-page technical implementation guides for practical application"
            },
            "White Papers": {
                "priority": 2, 
                "patterns": ["**/WHITE_PAPERS*.md", "**/white_paper*.md"],
                "description": "Technical implementation papers and research publications"
            },
            "Developer Guides": {
                "priority": 3,
                "patterns": ["**/DEVELOPER_GUIDE*.md", "**/COMPLETE_TECHNICAL*.md"],
                "description": "Implementation guides for professional developers"
            },
            "Funding & Business": {
                "priority": 4,
                "patterns": ["**/FUNDING*.md", "**/BUSINESS*.md", "**/ECONOMIC*.md"],
                "description": "Grant opportunities and business development materials"
            },
            "Research Archives": {
                "priority": 5,
                "patterns": ["ARCHIVES/DISSERTATIONS/*.md", "FUTURE_STUDIES/*.md"],
                "description": "Archived research and breakthrough innovations"
            },
            "Active Debates": {
                "priority": 6,
                "patterns": ["ACTIVE_RESEARCH/DEBATES/*.md"],
                "description": "Current AI professor debates and discussions"
            },
            "System Documents": {
                "priority": 7,
                "patterns": ["SYSTEM/**/*.py", "SYSTEM/**/*.json", "*.md"],
                "description": "System configuration and documentation files"
            }
        }
        
        categorized_docs = {}
        
        for category, info in priority_docs.items():
            files = []
            for pattern in info["patterns"]:
                matches = list(self.base_path.glob(pattern))
                for file_path in matches:
                    if file_path.is_file() and file_path.stat().st_size > 0:
                        files.append({
                            "name": file_path.name,
                            "path": str(file_path),
                            "relative_path": str(file_path.relative_to(self.base_path)),
                            "size": self.format_file_size(file_path.stat().st_size),
                            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                        })
            
            # Sort by modification time (newest first)
            files.sort(key=lambda x: x["modified"], reverse=True)
            
            if files:  # Only include categories with files
                categorized_docs[category] = {
                    "files": files,
                    "description": info["description"],
                    "priority": info["priority"]
                }
        
        return categorized_docs
    
    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def create_category_zip(self, category_files):
        """Create a zip file for a category of documents"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        
        with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_info in category_files:
                file_path = Path(file_info["path"])
                if file_path.exists():
                    # Use relative path as the name in zip
                    zipf.write(file_path, file_info["relative_path"])
        
        return temp_file.name

class EC2ExperimentTracker:
    def __init__(self):
        self.base_path = BASE_PATH
        self.experiment_log_path = self.base_path / "SYSTEM" / "LOGS" / "ec2_experiments.log"
    
    def log_experiment(self, bot_id, question, hypothesis, method, instance_count=1):
        """Log a new EC2 experiment"""
        experiment = {
            "timestamp": datetime.now().isoformat(),
            "bot_id": bot_id,
            "question": question,
            "hypothesis": hypothesis,
            "method": method,
            "instance_count": instance_count,
            "status": "active"
        }
        
        self.experiment_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.experiment_log_path, "a") as f:
            f.write(json.dumps(experiment) + "\n")
    
    def get_active_experiments(self):
        """Get all active EC2 experiments by bot"""
        experiments = []
        
        if self.experiment_log_path.exists():
            try:
                with open(self.experiment_log_path, "r") as f:
                    for line in f:
                        if line.strip():
                            exp = json.loads(line)
                            if exp.get("status") == "active":
                                experiments.append(exp)
            except Exception as e:
                print(f"Error reading experiments: {e}")
        
        # Group by bot_id and get most recent
        bot_experiments = {}
        for exp in experiments:
            bot_id = exp["bot_id"]
            if bot_id not in bot_experiments or exp["timestamp"] > bot_experiments[bot_id]["timestamp"]:
                bot_experiments[bot_id] = exp
        
        return list(bot_experiments.values())

class DebateMonitor:
    def __init__(self):
        self.base_path = BASE_PATH
        self.bot_patterns = {
            "PROF_CLAUDE_SWARMS": {"name": "Prof. Claude (Swarms)", "color": "#3498db"},
            "PROF_GPT_ECONOMICS": {"name": "Prof. GPT (Economics)", "color": "#e74c3c"},
            "PROF_CLAUDE_TENSOR": {"name": "Prof. Claude-Tensor", "color": "#9b59b6"},
            "PROF_GPT_FRAMEWORK": {"name": "Prof. GPT-Framework", "color": "#f39c12"},
            "DR_ASSEMBLY": {"name": "Dr. Assembly", "color": "#27ae60"},
            "DR_CAM_ASSEMBLY": {"name": "Dr. CAM-Assembly", "color": "#16a085"},
            "DR_SUPERINSTANCE": {"name": "Dr. SuperInstance-Tensor", "color": "#8e44ad"},
            "DR_SILENT_OBSERVER": {"name": "Dr. Silent-Observer", "color": "#2c3e50"},
            "DR_PRACTICAL": {"name": "Dr. Practical", "color": "#34495e"},
            "DR_APPLICATIONS": {"name": "Dr. Applications", "color": "#e67e22"},
            "DR_ACTIVE_BASH": {"name": "Dr. Active-Bash", "color": "#f1c40f"},
            "ASSISTANT_SKEPTIC": {"name": "Assistant Skeptic", "color": "#e67e22"},
            "DMLOG_DEVELOPER": {"name": "DMLog Developer", "color": "#2ecc71"},
            "GARBAGE_COLLECTOR": {"name": "Garbage Collector", "color": "#95a5a6"},
            "JUDGE_BOT": {"name": "Judge Bot", "color": "#8e44ad"}
        }
    
    def parse_debate_messages(self):
        """Parse debate messages from all sources"""
        messages = []
        
        # Parse main debate board
        debate_board = self.base_path / "ACTIVE_RESEARCH/DEBATES/AI_PROFESSOR_DEBATE_BOARD.md"
        if debate_board.exists():
            messages.extend(self.parse_markdown_messages(debate_board))
        
        # Parse system logs for bot activity
        log_dir = self.base_path / "SYSTEM/LOGS"
        if log_dir.exists():
            for log_file in log_dir.glob("*.log"):
                messages.extend(self.parse_log_messages(log_file))
        
        # Sort by timestamp (newest first) and limit for live viewing
        messages.sort(key=lambda x: x["timestamp"], reverse=True)
        return messages[:50]  # Recent 50 messages for live viewing
    
    def parse_markdown_messages(self, file_path):
        """Parse messages from markdown debate files"""
        messages = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for timestamped messages - improved pattern
            pattern = r'\[([^\]]+)\]\s*\[([^\]]+)\]:\s*(.+?)(?=\n\[|\n##|\Z)'
            matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
            
            # Also look for simpler patterns in case formatting varies
            if not matches:
                simple_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*\[([^\]]+)\]:\s*(.+?)(?=\n\d{4}-|\n##|\Z)'
                simple_matches = re.findall(simple_pattern, content, re.DOTALL | re.MULTILINE)
                for timestamp_str, bot_id, message_text in simple_matches:
                    matches.append((timestamp_str, bot_id, message_text))
            
            for timestamp_str, bot_id, message_text in matches:
                try:
                    # Parse timestamp
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    
                    bot_info = self.bot_patterns.get(bot_id, {
                        "name": bot_id.replace("_", " ").title(),
                        "color": "#2c3e50"
                    })
                    
                    messages.append({
                        "timestamp": timestamp,
                        "bot_id": bot_id,
                        "bot_name": bot_info["name"],
                        "bot_color": bot_info["color"],
                        "message": message_text.strip(),
                        "source": "debate"
                    })
                except ValueError:
                    continue
        
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
        
        return messages
    
    def parse_log_messages(self, file_path):
        """Parse messages from system log files"""
        messages = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line in lines[-100:]:  # Last 100 log entries
                line = line.strip()
                if not line:
                    continue
                
                # Look for timestamp patterns in logs
                timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})', line)
                if timestamp_match:
                    try:
                        timestamp_str = timestamp_match.group(1).replace('T', ' ')
                        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                        
                        messages.append({
                            "timestamp": timestamp,
                            "bot_id": "SYSTEM",
                            "bot_name": "System",
                            "bot_color": "#7f8c8d",
                            "message": line,
                            "source": "system"
                        })
                    except ValueError:
                        continue
        
        except Exception as e:
            print(f"Error parsing log {file_path}: {e}")
        
        return messages
    
    def get_bot_statistics(self):
        """Get participation statistics for each bot"""
        messages = self.parse_debate_messages()
        
        bot_stats = {}
        for message in messages:
            bot_id = message["bot_id"]
            if bot_id not in bot_stats:
                bot_stats[bot_id] = {
                    "name": message["bot_name"],
                    "color": message["bot_color"],
                    "message_count": 0,
                    "last_activity": message["timestamp"],
                    "avg_message_length": 0
                }
            
            bot_stats[bot_id]["message_count"] += 1
            bot_stats[bot_id]["avg_message_length"] += len(message["message"])
            
            if message["timestamp"] > bot_stats[bot_id]["last_activity"]:
                bot_stats[bot_id]["last_activity"] = message["timestamp"]
        
        # Calculate averages
        for bot_id in bot_stats:
            if bot_stats[bot_id]["message_count"] > 0:
                bot_stats[bot_id]["avg_message_length"] /= bot_stats[bot_id]["message_count"]
        
        return bot_stats

# Initialize managers
doc_manager = DocumentManager()
debate_monitor = DebateMonitor()
ec2_tracker = EC2ExperimentTracker()

@app.route('/')
def index():
    """Main portal page"""
    return render_template('index.html')

@app.route('/api/documents')
def get_documents():
    """Get all documents organized by priority"""
    return jsonify(doc_manager.get_prioritized_documents())

@app.route('/api/debates')
def get_debates():
    """Get recent debate messages"""
    messages = debate_monitor.parse_debate_messages()
    # Convert datetime objects to strings for JSON
    for message in messages:
        message["timestamp"] = message["timestamp"].isoformat()
    return jsonify(messages)

@app.route('/api/bot-stats')
def get_bot_stats():
    """Get bot participation statistics"""
    stats = debate_monitor.get_bot_statistics()
    # Convert datetime objects to strings for JSON
    for bot_id in stats:
        stats[bot_id]["last_activity"] = stats[bot_id]["last_activity"].isoformat()
    return jsonify(stats)

@app.route('/api/ec2-experiments')
def get_ec2_experiments():
    """Get active EC2 experiments by bot"""
    experiments = ec2_tracker.get_active_experiments()
    return jsonify(experiments)

@app.route('/download/file/<path:file_path>')
def download_file(file_path):
    """Download a specific file"""
    full_path = BASE_PATH / file_path
    if full_path.exists() and full_path.is_file():
        return send_file(str(full_path), as_attachment=True)
    return "File not found", 404

@app.route('/download/category/<category>')
def download_category(category):
    """Download all files in a category as zip"""
    docs = doc_manager.get_prioritized_documents()
    if category in docs:
        zip_path = doc_manager.create_category_zip(docs[category]["files"])
        return send_file(zip_path, as_attachment=True, 
                        download_name=f"{category.replace(' ', '_')}.zip")
    return "Category not found", 404

@app.route('/download/all')
def download_all():
    """Download all documents as a single zip"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    
    with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        docs = doc_manager.get_prioritized_documents()
        for category, info in docs.items():
            for file_info in info["files"]:
                file_path = Path(file_info["path"])
                if file_path.exists():
                    # Create category folders in zip
                    zip_path = f"{category}/{file_info['name']}"
                    zipf.write(file_path, zip_path)
    
    return send_file(temp_file.name, as_attachment=True,
                    download_name="ActiveLog_Complete_Archive.zip")

if __name__ == '__main__':
    # Create templates directory and files
    templates_dir = Path(__file__).parent / "templates"
    templates_dir.mkdir(exist_ok=True)
    
    # Create static directory for CSS
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)
    
    app.run(host='0.0.0.0', port=8080, debug=True)