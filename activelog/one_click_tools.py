#!/usr/bin/env python3
"""
ActiveLog One-Click Tools
Simple command-line tools for common tasks with easy-to-remember commands
"""

import sys
import os
import subprocess
import json
import time
from pathlib import Path

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

def print_logo():
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
{Colors.CYAN}One-Click Tools - Making ActiveLog super easy!{Colors.END}
    """)

def run_command(command, description="Running command"):
    """Run a command with nice output"""
    print(f"{Colors.YELLOW}🔄 {description}...{Colors.END}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"{Colors.GREEN}✅ Success!{Colors.END}")
            if result.stdout:
                print(f"{Colors.CYAN}{result.stdout}{Colors.END}")
            return True
        else:
            print(f"{Colors.RED}❌ Failed!{Colors.END}")
            if result.stderr:
                print(f"{Colors.RED}{result.stderr}{Colors.END}")
            return False
    except subprocess.TimeoutExpired:
        print(f"{Colors.RED}❌ Command timed out{Colors.END}")
        return False
    except Exception as e:
        print(f"{Colors.RED}❌ Error: {e}{Colors.END}")
        return False

def check_setup():
    """Check if ActiveLog is set up"""
    return Path("activelog_config.json").exists()

def quick_start():
    """Quick start ActiveLog"""
    print_logo()
    print(f"{Colors.GREEN}🚀 Quick Starting ActiveLog...{Colors.END}\n")
    
    if not check_setup():
        print(f"{Colors.YELLOW}⚙️ First time? Running easy setup...{Colors.END}")
        if run_command("python3 easy_setup.py", "Running setup wizard"):
            print(f"{Colors.GREEN}Setup completed! Now starting ActiveLog...{Colors.END}")
        else:
            print(f"{Colors.RED}Setup failed. Please check the error above.{Colors.END}")
            return False
    
    # Start based on what's available
    if Path("start_activelog.sh").exists():
        return run_command("./start_activelog.sh", "Starting ActiveLog")
    elif Path("start_optimized.sh").exists():
        return run_command("./start_optimized.sh", "Starting optimized ActiveLog")
    elif Path("start_thin_client.sh").exists():
        return run_command("./start_thin_client.sh", "Starting thin client")
    else:
        print(f"{Colors.YELLOW}Creating basic startup script...{Colors.END}")
        create_basic_startup()
        return run_command("./start_activelog.sh", "Starting ActiveLog")

def create_basic_startup():
    """Create a basic startup script"""
    script_content = """#!/bin/bash
echo "🚀 Starting ActiveLog..."

# Start essential services
cd services/auth && python3 main.py &
echo "Auth service started"

cd ../../services/api-gateway && python3 main.py &
echo "API Gateway started"

echo "✅ ActiveLog is running!"
echo "Dashboard: http://localhost:8088"
"""
    
    with open("start_activelog.sh", 'w') as f:
        f.write(script_content)
    os.chmod("start_activelog.sh", 0o755)

def quick_stop():
    """Quick stop ActiveLog"""
    print_logo()
    print(f"{Colors.RED}🛑 Stopping ActiveLog...{Colors.END}\n")
    
    if Path("stop_activelog.sh").exists():
        return run_command("./stop_activelog.sh", "Stopping ActiveLog")
    else:
        # Fallback stop method
        commands = [
            "pkill -f 'python3.*main.py'",
            "pkill -f 'npm start'",
            "rm -f pids/*.pid"
        ]
        
        success = True
        for cmd in commands:
            success &= run_command(cmd, "Stopping services")
        
        if success:
            print(f"{Colors.GREEN}✅ ActiveLog stopped successfully!{Colors.END}")
        return success

def quick_status():
    """Show ActiveLog status"""
    print_logo()
    print(f"{Colors.BLUE}📊 ActiveLog Status{Colors.END}\n")
    
    # Check if services are running
    services = {
        "Auth Service": 8002,
        "API Gateway": 8088,
        "File Sync": 8000,
        "AI Orchestrator": 8001
    }
    
    running_services = 0
    for service_name, port in services.items():
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                print(f"{Colors.GREEN}✅ {service_name} (port {port}){Colors.END}")
                running_services += 1
            else:
                print(f"{Colors.RED}❌ {service_name} (port {port}){Colors.END}")
        except:
            print(f"{Colors.RED}❌ {service_name} (port {port}) - Check failed{Colors.END}")
    
    # Show system resources
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        print(f"\n{Colors.CYAN}💻 System Resources:{Colors.END}")
        print(f"   CPU Usage: {cpu:.1f}%")
        print(f"   Memory Usage: {memory.percent:.1f}% ({memory.used/1024**3:.1f}GB / {memory.total/1024**3:.1f}GB)")
        
        # Overall status
        if running_services > 0:
            print(f"\n{Colors.GREEN}🎉 ActiveLog is running! ({running_services}/{len(services)} services){Colors.END}")
            print(f"{Colors.CYAN}Dashboard: http://localhost:8088{Colors.END}")
            print(f"{Colors.CYAN}Control Panel: http://localhost:3000{Colors.END}")
        else:
            print(f"\n{Colors.YELLOW}⚠️ ActiveLog is not running{Colors.END}")
            print(f"{Colors.CYAN}Run: activelog start{Colors.END}")
    except ImportError:
        print(f"\n{Colors.YELLOW}System resource monitoring not available (install psutil){Colors.END}")

def quick_optimize():
    """Quick system optimization"""
    print_logo()
    print(f"{Colors.PURPLE}⚡ Optimizing ActiveLog...{Colors.END}\n")
    
    optimizations = [
        ("python3 device_optimization_manager.py", "Optimizing for your device"),
        ("python3 cleanup_system.py", "Cleaning up system"),
        ("python3 optimize_system.sh", "Running system optimization")
    ]
    
    success_count = 0
    for command, description in optimizations:
        if Path(command.split()[1]).exists():
            if run_command(command, description):
                success_count += 1
        else:
            print(f"{Colors.YELLOW}⚠️ Skipping {description} (script not found){Colors.END}")
    
    print(f"\n{Colors.GREEN}🎯 Optimization completed! ({success_count}/{len(optimizations)} successful){Colors.END}")
    
    if success_count > 0:
        print(f"{Colors.CYAN}💡 Restart ActiveLog to apply optimizations:{Colors.END}")
        print(f"{Colors.CYAN}   activelog restart{Colors.END}")

def quick_restart():
    """Quick restart ActiveLog"""
    print_logo()
    print(f"{Colors.BLUE}🔄 Restarting ActiveLog...{Colors.END}\n")
    
    # Stop first
    quick_stop()
    time.sleep(3)
    
    # Then start
    return quick_start()

def quick_setup():
    """Run the easy setup wizard"""
    print_logo()
    print(f"{Colors.CYAN}⚙️ Running ActiveLog Setup Wizard...{Colors.END}\n")
    
    if run_command("python3 easy_setup.py", "Running setup wizard"):
        print(f"\n{Colors.GREEN}🎉 Setup completed!{Colors.END}")
        print(f"{Colors.CYAN}Ready to start ActiveLog:{Colors.END}")
        print(f"{Colors.CYAN}   activelog start{Colors.END}")
        return True
    else:
        print(f"{Colors.RED}❌ Setup failed{Colors.END}")
        return False

def quick_dashboard():
    """Open web dashboard"""
    print_logo()
    print(f"{Colors.BLUE}🌐 Starting Web Dashboard...{Colors.END}\n")
    
    if run_command("python3 web_dashboard.py &", "Starting web dashboard"):
        print(f"{Colors.GREEN}✅ Dashboard started!{Colors.END}")
        print(f"{Colors.CYAN}Open in browser: http://localhost:8080{Colors.END}")
        
        # Try to open in browser
        try:
            import webbrowser
            time.sleep(2)
            webbrowser.open("http://localhost:8080")
            print(f"{Colors.GREEN}🌐 Opening in browser...{Colors.END}")
        except:
            pass
        return True
    return False

def quick_help():
    """Show help information"""
    print_logo()
    print(f"{Colors.CYAN}📚 ActiveLog One-Click Commands:{Colors.END}\n")
    
    commands = [
        ("start", "🚀 Start ActiveLog (with auto-setup if needed)"),
        ("stop", "🛑 Stop all ActiveLog services"),
        ("restart", "🔄 Restart ActiveLog"),
        ("status", "📊 Show system status and running services"),
        ("optimize", "⚡ Optimize system performance"),
        ("setup", "⚙️ Run setup wizard"),
        ("dashboard", "🌐 Open web dashboard"),
        ("help", "📚 Show this help message"),
    ]
    
    for cmd, desc in commands:
        print(f"{Colors.GREEN}   activelog {cmd:<10}{Colors.END} - {desc}")
    
    print(f"\n{Colors.YELLOW}💡 Tips:{Colors.END}")
    print(f"   • First run will automatically set up ActiveLog for your device")
    print(f"   • Web dashboard provides a GUI for all features")
    print(f"   • Use 'status' to check if everything is working")
    print(f"   • Run 'optimize' after making changes to improve performance")
    
    print(f"\n{Colors.PURPLE}🔧 Advanced Commands:{Colors.END}")
    print(f"   python3 smart_service_manager.py - Advanced service management")
    print(f"   python3 performance_monitor.py   - Real-time monitoring")
    print(f"   python3 cloud_compute_offloader.py - Cloud computing setup")

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        quick_help()
        return
    
    command = sys.argv[1].lower()
    
    commands = {
        'start': quick_start,
        'stop': quick_stop,
        'restart': quick_restart,
        'status': quick_status,
        'optimize': quick_optimize,
        'setup': quick_setup,
        'dashboard': quick_dashboard,
        'help': quick_help,
    }
    
    if command in commands:
        try:
            success = commands[command]()
            if success is not None:
                sys.exit(0 if success else 1)
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}⚠️ Interrupted by user{Colors.END}")
            sys.exit(1)
        except Exception as e:
            print(f"\n{Colors.RED}❌ Unexpected error: {e}{Colors.END}")
            sys.exit(1)
    else:
        print(f"{Colors.RED}❌ Unknown command: {command}{Colors.END}")
        print(f"{Colors.CYAN}Run 'activelog help' for available commands{Colors.END}")
        sys.exit(1)

if __name__ == "__main__":
    main()