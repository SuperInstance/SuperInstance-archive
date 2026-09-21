#!/usr/bin/env python3
"""
ActiveLog Simple Troubleshooter
Automatically detects and fixes common issues
"""

import os
import sys
import json
import subprocess
import time
import socket
from pathlib import Path
from typing import List, Dict, Tuple
import logging

# Colors for output
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class SimpleTroubleshooter:
    def __init__(self):
        self.issues_found = []
        self.fixes_applied = []
        
    def print_header(self, text):
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    def print_success(self, text):
        print(f"{Colors.GREEN}✅ {text}{Colors.END}")
    
    def print_warning(self, text):
        print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")
    
    def print_error(self, text):
        print(f"{Colors.RED}❌ {text}{Colors.END}")
    
    def print_info(self, text):
        print(f"{Colors.CYAN}ℹ️  {text}{Colors.END}")
    
    def print_fix(self, text):
        print(f"{Colors.PURPLE}🔧 {text}{Colors.END}")
    
    def run_command(self, command: str, description: str = "") -> bool:
        """Run a command and return success status"""
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False
    
    def check_port(self, port: int) -> bool:
        """Check if a port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except:
            return False
    
    def check_python_modules(self) -> List[str]:
        """Check for missing Python modules"""
        required_modules = [
            'fastapi', 'uvicorn', 'psutil', 'asyncio', 'aiohttp'
        ]
        
        missing_modules = []
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
        
        return missing_modules
    
    def check_file_permissions(self) -> List[str]:
        """Check for permission issues"""
        permission_issues = []
        
        # Check if scripts are executable
        scripts_to_check = [
            'start_activelog.sh', 'start_optimized.sh', 'start_thin_client.sh',
            'stop_activelog.sh', 'activelog'
        ]
        
        for script in scripts_to_check:
            script_path = Path(script)
            if script_path.exists() and not os.access(script_path, os.X_OK):
                permission_issues.append(script)
        
        return permission_issues
    
    def check_disk_space(self) -> bool:
        """Check if there's enough disk space"""
        try:
            import psutil
            disk = psutil.disk_usage('.')
            free_gb = disk.free / (1024**3)
            return free_gb > 1.0  # At least 1GB free
        except:
            return True  # Assume OK if can't check
    
    def check_memory(self) -> bool:
        """Check if there's enough memory"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            return available_gb > 0.5  # At least 500MB available
        except:
            return True  # Assume OK if can't check
    
    def check_services_status(self) -> Dict[str, bool]:
        """Check status of ActiveLog services"""
        services = {
            'auth': 8002,
            'api-gateway': 8088,
            'file-sync': 8000,
            'ai-orchestrator': 8001
        }
        
        status = {}
        for service, port in services.items():
            pid_file = Path(f"pids/{service}.pid")
            is_running = False
            
            if pid_file.exists():
                try:
                    with open(pid_file) as f:
                        pid = int(f.read().strip())
                    # Check if process exists
                    try:
                        import psutil
                        is_running = psutil.pid_exists(pid)
                    except ImportError:
                        # Fallback: check if port is responding
                        is_running = self.check_port(port)
                except:
                    pass
            
            status[service] = is_running
        
        return status
    
    def diagnose_startup_issues(self):
        """Diagnose common startup issues"""
        self.print_header("🔍 Diagnosing Startup Issues")
        
        # Check 1: Python modules
        missing_modules = self.check_python_modules()
        if missing_modules:
            self.issues_found.append(f"Missing Python modules: {', '.join(missing_modules)}")
            self.print_error(f"Missing required modules: {', '.join(missing_modules)}")
        else:
            self.print_success("All required Python modules are installed")
        
        # Check 2: File permissions
        permission_issues = self.check_file_permissions()
        if permission_issues:
            self.issues_found.append(f"Permission issues: {', '.join(permission_issues)}")
            self.print_error(f"Scripts not executable: {', '.join(permission_issues)}")
        else:
            self.print_success("File permissions are correct")
        
        # Check 3: Configuration files
        config_files = ['activelog_config.json', 'device_optimized_config.json']
        missing_configs = [f for f in config_files if not Path(f).exists()]
        if missing_configs:
            self.issues_found.append("Missing configuration files")
            self.print_warning(f"Missing config files: {', '.join(missing_configs)}")
        else:
            self.print_success("Configuration files found")
        
        # Check 4: Service directories
        service_dirs = ['services/auth', 'services/api-gateway']
        missing_dirs = [d for d in service_dirs if not Path(d).exists()]
        if missing_dirs:
            self.issues_found.append("Missing service directories")
            self.print_error(f"Missing directories: {', '.join(missing_dirs)}")
        else:
            self.print_success("Service directories found")
    
    def diagnose_performance_issues(self):
        """Diagnose performance-related issues"""
        self.print_header("⚡ Diagnosing Performance Issues")
        
        # Check 1: System resources
        if not self.check_disk_space():
            self.issues_found.append("Low disk space")
            self.print_error("Low disk space (less than 1GB free)")
        else:
            self.print_success("Sufficient disk space available")
        
        if not self.check_memory():
            self.issues_found.append("Low memory")
            self.print_error("Low memory (less than 500MB available)")
        else:
            self.print_success("Sufficient memory available")
        
        # Check 2: Port conflicts
        common_ports = [8000, 8001, 8002, 8088, 3000]
        port_conflicts = []
        
        for port in common_ports:
            if self.check_port(port):
                port_conflicts.append(port)
        
        if port_conflicts:
            self.issues_found.append(f"Port conflicts: {port_conflicts}")
            self.print_warning(f"Ports already in use: {', '.join(map(str, port_conflicts))}")
        else:
            self.print_success("No port conflicts detected")
        
        # Check 3: Service status
        service_status = self.check_services_status()
        stopped_services = [name for name, running in service_status.items() if not running]
        
        if stopped_services:
            self.issues_found.append(f"Stopped services: {stopped_services}")
            self.print_warning(f"Services not running: {', '.join(stopped_services)}")
        else:
            self.print_success("All services are running")
    
    def diagnose_configuration_issues(self):
        """Diagnose configuration-related issues"""
        self.print_header("⚙️ Diagnosing Configuration Issues")
        
        # Check setup completion
        if not Path("activelog_config.json").exists():
            self.issues_found.append("Setup not completed")
            self.print_error("ActiveLog setup not completed")
        else:
            try:
                with open("activelog_config.json") as f:
                    config = json.load(f)
                
                if not config.get("setup_date"):
                    self.issues_found.append("Incomplete setup")
                    self.print_warning("Setup appears incomplete")
                else:
                    self.print_success("Setup completed successfully")
            except json.JSONDecodeError:
                self.issues_found.append("Corrupted configuration")
                self.print_error("Configuration file is corrupted")
        
        # Check optimizations
        if not Path("device_optimized_config.json").exists():
            self.issues_found.append("Device optimization not applied")
            self.print_warning("Device optimization not applied")
        else:
            self.print_success("Device optimization configured")
    
    def apply_automatic_fixes(self):
        """Apply automatic fixes for common issues"""
        self.print_header("🔧 Applying Automatic Fixes")
        
        # Fix 1: Install missing modules
        missing_modules = self.check_python_modules()
        if missing_modules:
            self.print_fix(f"Installing missing modules: {', '.join(missing_modules)}")
            pip_cmd = f"{sys.executable} -m pip install {' '.join(missing_modules)}"
            if self.run_command(pip_cmd):
                self.fixes_applied.append("Installed missing Python modules")
                self.print_success("Python modules installed")
            else:
                self.print_error("Failed to install Python modules")
        
        # Fix 2: Fix file permissions
        permission_issues = self.check_file_permissions()
        if permission_issues:
            self.print_fix("Fixing file permissions")
            for script in permission_issues:
                if self.run_command(f"chmod +x {script}"):
                    self.fixes_applied.append(f"Fixed permissions for {script}")
            self.print_success("File permissions fixed")
        
        # Fix 3: Create missing directories
        required_dirs = ['pids', 'logs', 'cache', 'services']
        for directory in required_dirs:
            if not Path(directory).exists():
                self.print_fix(f"Creating missing directory: {directory}")
                Path(directory).mkdir(parents=True, exist_ok=True)
                self.fixes_applied.append(f"Created directory {directory}")
        
        # Fix 4: Run setup if not completed
        if not Path("activelog_config.json").exists():
            self.print_fix("Running initial setup")
            if self.run_command(f"{sys.executable} easy_setup.py --apply-config"):
                self.fixes_applied.append("Completed initial setup")
                self.print_success("Initial setup completed")
        
        # Fix 5: Apply device optimization
        if not Path("device_optimized_config.json").exists():
            self.print_fix("Applying device optimization")
            if self.run_command(f"{sys.executable} device_optimization_manager.py"):
                self.fixes_applied.append("Applied device optimization")
                self.print_success("Device optimization applied")
        
        # Fix 6: Clean up stale PID files
        pid_files = Path("pids").glob("*.pid") if Path("pids").exists() else []
        stale_pids = []
        
        for pid_file in pid_files:
            try:
                with open(pid_file) as f:
                    pid = int(f.read().strip())
                try:
                    import psutil
                    if not psutil.pid_exists(pid):
                        stale_pids.append(pid_file)
                except ImportError:
                    # Can't check, assume stale after 1 hour
                    if time.time() - pid_file.stat().st_mtime > 3600:
                        stale_pids.append(pid_file)
            except:
                stale_pids.append(pid_file)
        
        if stale_pids:
            self.print_fix(f"Cleaning up {len(stale_pids)} stale PID files")
            for pid_file in stale_pids:
                pid_file.unlink()
            self.fixes_applied.append("Cleaned up stale PID files")
    
    def provide_manual_fixes(self):
        """Provide manual fix suggestions"""
        self.print_header("📋 Manual Fix Suggestions")
        
        if not self.issues_found:
            self.print_success("No issues found that require manual intervention!")
            return
        
        print(f"{Colors.CYAN}Issues that may require manual attention:{Colors.END}\n")
        
        # Port conflicts
        service_status = self.check_services_status()
        if "Port conflicts" in str(self.issues_found):
            print(f"{Colors.YELLOW}🔧 Port Conflicts:{Colors.END}")
            print("   • Stop other applications using ports 8000-8003, 8088")
            print("   • Or modify port settings in service configurations")
            print("   • Run: netstat -tulpn | grep :8000")
            print()
        
        # Low resources
        if "Low disk space" in str(self.issues_found):
            print(f"{Colors.YELLOW}🔧 Low Disk Space:{Colors.END}")
            print("   • Clean up temporary files: ./cleanup_system.py")
            print("   • Remove old log files from logs/ directory")
            print("   • Consider moving to a device with more storage")
            print()
        
        if "Low memory" in str(self.issues_found):
            print(f"{Colors.YELLOW}🔧 Low Memory:{Colors.END}")
            print("   • Close unnecessary applications")
            print("   • Enable cloud offloading: activelog setup")
            print("   • Consider using thin client mode")
            print()
        
        # Service issues
        stopped_services = [name for name, running in service_status.items() if not running]
        if stopped_services:
            print(f"{Colors.YELLOW}🔧 Stopped Services:{Colors.END}")
            for service in stopped_services:
                print(f"   • Start {service}: activelog start")
            print("   • Check logs in logs/ directory for error details")
            print()
        
        # Setup issues
        if "Setup not completed" in str(self.issues_found):
            print(f"{Colors.YELLOW}🔧 Setup Issues:{Colors.END}")
            print("   • Run the setup wizard: activelog setup")
            print("   • Or run: python3 easy_setup.py")
            print()
    
    def generate_health_report(self):
        """Generate a comprehensive health report"""
        self.print_header("📊 ActiveLog Health Report")
        
        # System overview
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('.')
            
            print(f"{Colors.CYAN}System Resources:{Colors.END}")
            print(f"   CPU Usage: {cpu:.1f}%")
            print(f"   Memory: {memory.percent:.1f}% ({memory.used/1024**3:.1f}GB / {memory.total/1024**3:.1f}GB)")
            print(f"   Disk: {disk.percent:.1f}% ({disk.free/1024**3:.1f}GB free)")
            print()
        except ImportError:
            print(f"{Colors.YELLOW}System resource monitoring not available{Colors.END}\n")
        
        # Service status
        service_status = self.check_services_status()
        print(f"{Colors.CYAN}Service Status:{Colors.END}")
        for service, running in service_status.items():
            status_icon = "✅" if running else "❌"
            print(f"   {status_icon} {service.replace('-', ' ').title()}")
        print()
        
        # Configuration status
        config_files = {
            "Main Config": "activelog_config.json",
            "Device Optimization": "device_optimized_config.json", 
            "Cloud Setup": "cloud_setup.json"
        }
        
        print(f"{Colors.CYAN}Configuration Status:{Colors.END}")
        for name, filename in config_files.items():
            exists = Path(filename).exists()
            status_icon = "✅" if exists else "❌"
            print(f"   {status_icon} {name}")
        print()
        
        # Overall health
        running_services = sum(service_status.values())
        total_services = len(service_status)
        health_score = (running_services / total_services) * 100
        
        if health_score >= 80:
            health_color = Colors.GREEN
            health_status = "Excellent"
        elif health_score >= 60:
            health_color = Colors.YELLOW
            health_status = "Good"
        else:
            health_color = Colors.RED
            health_status = "Needs Attention"
        
        print(f"{Colors.BOLD}Overall Health: {health_color}{health_status} ({health_score:.0f}%){Colors.END}")
    
    def run_full_diagnosis(self):
        """Run complete diagnosis and repair"""
        print(f"""
{Colors.BLUE}{Colors.BOLD}
    ___        _   _           _                 
   / _ \      | | (_)         | |                
  / /_\ \  ___| |_ ___   _____| |     ___   __ _ 
  |  _  | / __| __| \ \ / / _ \ |    / _ \ / _` |
  | | | || (__| |_| |\ V /  __/ |___| (_) | (_| |
  \_| |_/ \___|\__|_| \_/ \___|______/\___/ \__, |
                                            __/ |
                                           |___/ 
{Colors.END}
{Colors.CYAN}Troubleshooter - Automatically fixing issues!{Colors.END}
        """)
        
        # Run all diagnostic checks
        self.diagnose_startup_issues()
        self.diagnose_performance_issues()
        self.diagnose_configuration_issues()
        
        # Apply automatic fixes
        self.apply_automatic_fixes()
        
        # Show manual fix suggestions
        self.provide_manual_fixes()
        
        # Generate health report
        self.generate_health_report()
        
        # Summary
        self.print_header("🎯 Troubleshooting Summary")
        
        print(f"{Colors.RED}Issues Found: {len(self.issues_found)}{Colors.END}")
        for issue in self.issues_found:
            print(f"   • {issue}")
        
        print(f"\n{Colors.GREEN}Fixes Applied: {len(self.fixes_applied)}{Colors.END}")
        for fix in self.fixes_applied:
            print(f"   • {fix}")
        
        if self.fixes_applied:
            print(f"\n{Colors.CYAN}💡 Recommendation: Restart ActiveLog to apply fixes{Colors.END}")
            print(f"{Colors.CYAN}   activelog restart{Colors.END}")
        
        if not self.issues_found:
            print(f"\n{Colors.GREEN}🎉 No issues found! ActiveLog is healthy.{Colors.END}")

def main():
    """Main troubleshooter function"""
    troubleshooter = SimpleTroubleshooter()
    
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        # Quick health check
        troubleshooter.generate_health_report()
    else:
        # Full diagnosis
        troubleshooter.run_full_diagnosis()

if __name__ == "__main__":
    main()