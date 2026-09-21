#!/usr/bin/env python3
"""
SuperInstance Foreman Efficiency Monitor
Automated bot coordination and puzzle resolution system
"""

import json
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path

class ForemanMonitor:
    def __init__(self):
        self.base_path = Path("/home/activeloguser/activelog")
        self.task_queue_file = self.base_path / "shared_task_queue.json"
        self.puzzle_backlog_file = self.base_path / "puzzle_backlog.json"  
        self.dependency_tracker_file = self.base_path / "dependency_tracker.json"
        
    def load_json_file(self, filepath):
        """Load JSON file with error handling"""
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def save_json_file(self, filepath, data):
        """Save JSON file with error handling"""
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving {filepath}: {e}")
            return False
    
    def check_stuck_tasks(self):
        """Identify tasks stuck for > 30 minutes"""
        task_queue = self.load_json_file(self.task_queue_file)
        stuck_tasks = []
        current_time = datetime.now(timezone.utc)
        
        for task in task_queue.get('priority_queue', []):
            if task['status'] == 'in_progress' and 'started_at' in task:
                started = datetime.fromisoformat(task['started_at'].replace('Z', '+00:00'))
                duration = (current_time - started).total_seconds() / 60  # minutes
                
                if duration > 30:  # Stuck for > 30 minutes
                    stuck_tasks.append({
                        'task': task,
                        'stuck_duration': duration,
                        'needs_intervention': duration > 60
                    })
        
        return stuck_tasks
    
    def check_critical_blockers(self):
        """Identify critical path blockers"""
        dependency_tracker = self.load_json_file(self.dependency_tracker_file)
        critical_blockers = []
        
        for blocking_chain in dependency_tracker.get('blocking_chain', []):
            if blocking_chain.get('impact_severity') == 'critical':
                critical_blockers.append(blocking_chain)
                
        return critical_blockers
    
    def suggest_parallel_work(self):
        """Suggest work that can be done in parallel"""
        dependency_tracker = self.load_json_file(self.dependency_tracker_file)
        suggestions = []
        
        for task_id, task_data in dependency_tracker.get('dependency_graph', {}).items():
            if task_data['status'] == 'waiting':
                # Check if dependencies are being worked on
                dependencies_in_progress = True
                for req in task_data.get('requires', []):
                    dep_data = dependency_tracker['dependency_graph'].get(req, {})
                    if dep_data.get('status') != 'in_progress':
                        dependencies_in_progress = False
                        break
                
                if dependencies_in_progress:
                    suggestions.append({
                        'task': task_id,
                        'reason': 'Dependencies in progress, can prepare',
                        'preparatory_work': f"Study existing patterns for {task_id}"
                    })
        
        return suggestions
    
    def resolve_ssh_connectivity_puzzle(self):
        """Specific resolver for SSH connectivity issue"""
        try:
            # Check if alternative instance (35.85.21.186) is accessible
            result = subprocess.run([
                'ssh', '-o', 'ConnectTimeout=5', '-o', 'StrictHostKeyChecking=no',
                '-i', '/home/activeloguser/.ssh/personallog_key',
                'ubuntu@35.85.21.186', 'echo SSH_SUCCESS'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and 'SSH_SUCCESS' in result.stdout:
                # Update infrastructure.env to use working instance
                env_content = """MASTER_INSTANCE_ID=i-06149656a24cd0eda
VPC_ID=vpc-0463f5289ad81ca5e
SUBNET_ID=subnet-0496763b3fb523c1b
SECURITY_GROUP_ID=sg-05c39709a7b7923c1
PUBLIC_IP=35.85.21.186
PRIVATE_IP=10.0.1.12
AWS_ACCOUNT_ID=451523008183
SSH_WORKING=true"""
                
                with open('/tmp/infrastructure.env', 'w') as f:
                    f.write(env_content)
                
                # Update puzzle as resolved
                puzzle_data = self.load_json_file(self.puzzle_backlog_file)
                for puzzle in puzzle_data.get('active_puzzles', []):
                    if puzzle['id'] == 'ssh-timeout-instance':
                        puzzle['status'] = 'resolved'
                        puzzle['resolution'] = 'Switched to working instance 35.85.21.186'
                        puzzle['resolved_at'] = datetime.now(timezone.utc).isoformat()
                        break
                
                self.save_json_file(self.puzzle_backlog_file, puzzle_data)
                return True
                
        except Exception as e:
            print(f"SSH resolution attempt failed: {e}")
            
        return False
    
    def generate_efficiency_report(self):
        """Generate comprehensive efficiency report"""
        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'stuck_tasks': self.check_stuck_tasks(),
            'critical_blockers': self.check_critical_blockers(), 
            'parallel_work_suggestions': self.suggest_parallel_work(),
            'puzzle_resolution_attempts': []
        }
        
        # Attempt to resolve known puzzles
        if self.resolve_ssh_connectivity_puzzle():
            report['puzzle_resolution_attempts'].append({
                'puzzle': 'ssh-timeout-instance',
                'result': 'resolved',
                'action': 'Switched to working instance 35.85.21.186'
            })
        
        return report

def main():
    """Run foreman monitoring cycle"""
    monitor = ForemanMonitor()
    report = monitor.generate_efficiency_report()
    
    print("=== SuperInstance Foreman Efficiency Report ===")
    print(f"Generated: {report['timestamp']}")
    print()
    
    if report['stuck_tasks']:
        print("🚨 STUCK TASKS:")
        for stuck in report['stuck_tasks']:
            task = stuck['task']
            print(f"  - {task['title']} ({task['assigned_bot']}) stuck for {stuck['stuck_duration']:.1f} minutes")
        print()
    
    if report['critical_blockers']:
        print("🔥 CRITICAL BLOCKERS:")
        for blocker in report['critical_blockers']:
            print(f"  - {blocker['root_blocker']} blocking {len(blocker['cascade_blocks'])} tasks")
        print()
    
    if report['parallel_work_suggestions']:
        print("💡 PARALLEL WORK OPPORTUNITIES:")
        for suggestion in report['parallel_work_suggestions']:
            print(f"  - {suggestion['task']}: {suggestion['reason']}")
        print()
    
    if report['puzzle_resolution_attempts']:
        print("🔧 PUZZLE RESOLUTION ATTEMPTS:")
        for attempt in report['puzzle_resolution_attempts']:
            print(f"  - {attempt['puzzle']}: {attempt['result']} - {attempt['action']}")
        print()
    
    print("📊 Run './foreman_efficiency_monitor.py' for real-time monitoring")

if __name__ == "__main__":
    main()