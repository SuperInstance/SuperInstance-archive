#!/usr/bin/env python3
"""
ActiveLog Easy Setup Wizard
Simple, guided setup for all ActiveLog features with automatic optimization
"""

import os
import sys
import json
import asyncio
import subprocess
import platform
import psutil
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Colorful console output
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

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.CYAN}ℹ️  {text}{Colors.END}")

def print_step(step, text):
    print(f"{Colors.PURPLE}{Colors.BOLD}Step {step}:{Colors.END} {text}")

class EasySetupWizard:
    def __init__(self):
        self.device_info = None
        self.user_preferences = {}
        self.selected_features = []
        self.cloud_config = {}
        
    def detect_device_automatically(self):
        """Automatically detect device capabilities"""
        print_step(1, "Detecting your device...")
        
        cpu_count = psutil.cpu_count(logical=False)
        memory_gb = psutil.virtual_memory().total / (1024**3)
        platform_name = platform.system()
        architecture = platform.machine()
        
        # Determine device type
        if memory_gb >= 16 and cpu_count >= 8:
            device_type = "🖥️  High-End Desktop/Server"
            performance_tier = "high"
            color = Colors.GREEN
        elif memory_gb >= 8 and cpu_count >= 4:
            device_type = "💻 Standard Laptop/Desktop"
            performance_tier = "medium"
            color = Colors.BLUE
        elif memory_gb >= 4 and cpu_count >= 2:
            device_type = "📱 Low-End Device/Tablet"
            performance_tier = "low"
            color = Colors.YELLOW
        else:
            device_type = "🔧 Embedded/IoT Device"
            performance_tier = "embedded"
            color = Colors.RED
        
        self.device_info = {
            "type": device_type,
            "tier": performance_tier,
            "cpu_cores": cpu_count,
            "memory_gb": memory_gb,
            "platform": platform_name,
            "architecture": architecture
        }
        
        print(f"\n{color}Device detected: {device_type}{Colors.END}")
        print(f"   CPU Cores: {cpu_count}")
        print(f"   Memory: {memory_gb:.1f} GB")
        print(f"   Platform: {platform_name} ({architecture})")
        
        return True
    
    def ask_simple_questions(self):
        """Ask user simple questions about their needs"""
        print_step(2, "Let's understand what you need...")
        
        print("\n📋 What do you want to use ActiveLog for? (select all that apply)")
        options = [
            ("📁 File management and sync", "file_management"),
            ("🤖 AI-powered features", "ai_features"),
            ("📊 Data analysis and reporting", "data_analysis"),
            ("🌐 Web development", "web_development"),
            ("📱 Mobile app development", "mobile_development"),
            ("🔧 IoT/Embedded projects", "iot_embedded"),
            ("☁️  Cloud computing", "cloud_computing"),
            ("🎮 Game development", "game_development")
        ]
        
        for i, (desc, key) in enumerate(options, 1):
            print(f"   {i}. {desc}")
        
        while True:
            try:
                choices = input(f"\n{Colors.CYAN}Enter numbers separated by commas (e.g., 1,3,5): {Colors.END}").strip()
                if not choices:
                    print_warning("Please select at least one option")
                    continue
                
                selected_indices = [int(x.strip()) for x in choices.split(',')]
                self.selected_features = [options[i-1][1] for i in selected_indices if 1 <= i <= len(options)]
                break
            except (ValueError, IndexError):
                print_error("Please enter valid numbers separated by commas")
        
        print_success(f"Selected {len(self.selected_features)} features")
        
        # Ask about cloud preferences for low-end devices
        if self.device_info["tier"] in ["low", "embedded"]:
            print(f"\n{Colors.YELLOW}💡 Your device would benefit from cloud computing!{Colors.END}")
            cloud_choice = input(f"{Colors.CYAN}Use cloud computing to boost performance? (y/n): {Colors.END}").lower()
            self.user_preferences["use_cloud"] = cloud_choice.startswith('y')
        else:
            self.user_preferences["use_cloud"] = False
        
        # Ask about complexity preference
        print(f"\n🎛️  How much control do you want?")
        print("   1. 🚀 Just make it work (automatic everything)")
        print("   2. ⚙️  Some control (guided setup)")
        print("   3. 🔧 Full control (advanced configuration)")
        
        while True:
            try:
                control_choice = int(input(f"{Colors.CYAN}Choose (1-3): {Colors.END}"))
                if 1 <= control_choice <= 3:
                    control_levels = ["automatic", "guided", "advanced"]
                    self.user_preferences["control_level"] = control_levels[control_choice - 1]
                    break
                else:
                    print_error("Please enter 1, 2, or 3")
            except ValueError:
                print_error("Please enter a valid number")
    
    def generate_recommendations(self):
        """Generate personalized recommendations"""
        print_step(3, "Generating personalized recommendations...")
        
        recommendations = {
            "startup_script": None,
            "services_to_enable": [],
            "cloud_features": [],
            "optimizations": [],
            "estimated_resources": {}
        }
        
        # Base recommendations based on device tier
        if self.device_info["tier"] == "high":
            recommendations["startup_script"] = "start_optimized.sh"
            recommendations["services_to_enable"] = ["all"]
            recommendations["optimizations"] = ["advanced_caching", "ml_optimization", "parallel_processing"]
            recommendations["estimated_resources"] = {"memory": "2-4GB", "cpu": "30-50%"}
            
        elif self.device_info["tier"] == "medium":
            recommendations["startup_script"] = "start_optimized.sh"
            recommendations["services_to_enable"] = ["core", "ai-orchestrator", "metadata"]
            recommendations["optimizations"] = ["connection_pooling", "smart_caching", "resource_limits"]
            recommendations["estimated_resources"] = {"memory": "1-2GB", "cpu": "20-40%"}
            
        elif self.device_info["tier"] == "low":
            recommendations["startup_script"] = "start_thin_client.sh"
            recommendations["services_to_enable"] = ["essential_only"]
            recommendations["cloud_features"] = ["ai_processing", "data_analysis", "image_processing"]
            recommendations["optimizations"] = ["aggressive_caching", "compression", "cloud_offloading"]
            recommendations["estimated_resources"] = {"memory": "200-500MB", "cpu": "10-20%"}
            
        else:  # embedded
            recommendations["startup_script"] = "start_minimal.sh"
            recommendations["services_to_enable"] = ["auth", "api-gateway"]
            recommendations["cloud_features"] = ["everything_intensive"]
            recommendations["optimizations"] = ["minimal_footprint", "power_saving", "cloud_first"]
            recommendations["estimated_resources"] = {"memory": "50-200MB", "cpu": "5-15%"}
        
        # Feature-specific recommendations
        if "ai_features" in self.selected_features and self.device_info["tier"] in ["low", "embedded"]:
            recommendations["cloud_features"].extend(["ml_inference", "nlp_processing"])
        
        if "data_analysis" in self.selected_features:
            recommendations["services_to_enable"].append("analytics")
            
        if "mobile_development" in self.selected_features:
            recommendations["optimizations"].append("pwa_support")
        
        self.recommendations = recommendations
        return recommendations
    
    def display_recommendations(self):
        """Display recommendations in a user-friendly way"""
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎯 Here's what we recommend for your setup:{Colors.END}")
        
        rec = self.recommendations
        
        print(f"\n{Colors.CYAN}📋 Configuration Summary:{Colors.END}")
        print(f"   Startup Mode: {rec['startup_script']}")
        print(f"   Services: {', '.join(rec['services_to_enable'])}")
        print(f"   Resource Usage: ~{rec['estimated_resources']['memory']} RAM, ~{rec['estimated_resources']['cpu']} CPU")
        
        if rec["cloud_features"]:
            print(f"\n{Colors.YELLOW}☁️  Cloud Features (saves resources on your device):{Colors.END}")
            for feature in rec["cloud_features"]:
                print(f"   • {feature.replace('_', ' ').title()}")
        
        print(f"\n{Colors.PURPLE}⚡ Optimizations to be applied:{Colors.END}")
        for opt in rec["optimizations"]:
            print(f"   • {opt.replace('_', ' ').title()}")
        
        if self.user_preferences.get("use_cloud"):
            print(f"\n{Colors.BLUE}💰 Estimated cloud costs: $0.01-0.20/hour (only when using AI features){Colors.END}")
    
    def setup_cloud_config(self):
        """Simple cloud configuration"""
        if not self.user_preferences.get("use_cloud"):
            return
        
        print_step(4, "Setting up cloud computing (optional)...")
        
        print(f"\n{Colors.CYAN}We can set up cloud computing for you automatically, or you can configure it later.{Colors.END}")
        print("Cloud computing helps by:")
        print("   • Running AI tasks faster")
        print("   • Processing large files")
        print("   • Saving battery on mobile devices")
        print("   • Reducing memory usage")
        
        auto_setup = input(f"\n{Colors.CYAN}Set up cloud computing now? (y/n): {Colors.END}").lower().startswith('y')
        
        if auto_setup:
            print(f"\n{Colors.INFO}For now, we'll create placeholder configuration.{Colors.END}")
            print(f"You can add your cloud API keys later in 'cloud_providers.json'")
            
            self.cloud_config = {
                "enabled": True,
                "auto_detect_best_provider": True,
                "cost_limit_per_hour": 1.0,
                "preferred_providers": ["edge_compute", "aws_lambda"],
                "fallback_to_local": True
            }
        else:
            print_info("Cloud setup skipped - you can enable it later")
    
    def create_configuration_files(self):
        """Create all necessary configuration files"""
        print_step(5, "Creating your personalized configuration...")
        
        # Create main config
        main_config = {
            "device_profile": self.device_info,
            "user_preferences": self.user_preferences,
            "selected_features": self.selected_features,
            "recommendations": self.recommendations,
            "setup_date": str(asyncio.get_event_loop().time()),
            "version": "1.0"
        }
        
        with open("activelog_config.json", 'w') as f:
            json.dump(main_config, f, indent=2)
        
        # Create cloud config if needed
        if self.cloud_config:
            with open("cloud_setup.json", 'w') as f:
                json.dump(self.cloud_config, f, indent=2)
        
        # Create simple startup script
        self.create_simple_startup_script()
        
        print_success("Configuration files created")
    
    def create_simple_startup_script(self):
        """Create a simple startup script based on user needs"""
        script_name = "start_activelog.sh"
        
        script_content = f"""#!/bin/bash
# ActiveLog Easy Startup Script
# Generated for: {self.device_info['type']} 
# Setup date: $(date)

echo "🚀 Starting ActiveLog..."
echo "Device: {self.device_info['type']}"
echo "Mode: {self.recommendations['startup_script']}"

# Check if this is first run
if [ ! -f ".activelog_initialized" ]; then
    echo "🔧 First time setup..."
    python3 easy_setup.py --apply-config
    touch .activelog_initialized
fi

# Start based on device tier
"""
        
        if self.device_info["tier"] == "embedded":
            script_content += """
echo "Starting minimal mode for embedded device..."
python3 smart_service_manager.py start-critical
"""
        elif self.device_info["tier"] == "low":
            script_content += """
echo "Starting thin client mode for low-end device..."
./start_thin_client.sh
"""
        else:
            script_content += """
echo "Starting optimized mode..."
./start_optimized.sh
"""
        
        script_content += """
# Show status
echo ""
echo "✅ ActiveLog is running!"
echo "📊 Dashboard: http://localhost:8088"
echo "🎛️  Control Panel: http://localhost:3000"
echo ""
echo "Commands:"
echo "  ./start_activelog.sh     - Start system"
echo "  python3 easy_setup.py   - Reconfigure"
echo "  python3 monitor.py      - Monitor performance"
"""
        
        with open(script_name, 'w') as f:
            f.write(script_content)
        os.chmod(script_name, 0o755)
        
        print_success(f"Simple startup script created: {script_name}")
    
    def apply_optimizations(self):
        """Apply the recommended optimizations automatically"""
        print_step(6, "Applying optimizations...")
        
        try:
            # Run device optimization
            print("   Optimizing for your device...")
            subprocess.run([sys.executable, "device_optimization_manager.py"], 
                          capture_output=True, check=True)
            print_success("Device optimization applied")
            
            # Set up cloud offloading if requested
            if self.user_preferences.get("use_cloud"):
                print("   Setting up cloud computing...")
                subprocess.run([sys.executable, "cloud_compute_offloader.py"], 
                              capture_output=True, timeout=30)
                print_success("Cloud offloading configured")
            
            # Run system cleanup
            print("   Cleaning up system...")
            subprocess.run([sys.executable, "cleanup_system.py"], 
                          capture_output=True, check=True)
            print_success("System cleanup completed")
            
        except subprocess.CalledProcessError as e:
            print_warning(f"Some optimizations may not have applied completely")
        except subprocess.TimeoutExpired:
            print_warning("Cloud setup timed out - you can configure it manually later")
    
    def create_easy_controls(self):
        """Create easy control scripts"""
        print("   Creating easy control scripts...")
        
        # Simple monitor script
        monitor_script = """#!/usr/bin/env python3
import subprocess
import sys
import webbrowser
import time

print("🔍 Opening ActiveLog monitoring...")

# Start performance monitor in background
try:
    subprocess.Popen([sys.executable, "performance_monitor.py"])
    time.sleep(2)
    
    # Try to open dashboard
    try:
        webbrowser.open("performance_dashboard.html")
    except:
        print("Dashboard available at: performance_dashboard.html")
        
except Exception as e:
    print(f"Monitor not available: {e}")
    print("You can check system status manually:")
    print("  ps aux | grep python")
    print("  curl http://localhost:8088/health")
"""
        
        with open("monitor.py", 'w') as f:
            f.write(monitor_script)
        os.chmod("monitor.py", 0o755)
        
        # Simple stop script
        stop_script = """#!/bin/bash
echo "🛑 Stopping ActiveLog services..."

# Kill all related processes
pkill -f "python3.*main.py" 2>/dev/null || true
pkill -f "npm start" 2>/dev/null || true

# Clean up PID files
rm -f pids/*.pid 2>/dev/null || true

echo "✅ ActiveLog stopped"
"""
        
        with open("stop_activelog.sh", 'w') as f:
            f.write(stop_script)
        os.chmod("stop_activelog.sh", 0o755)
        
        print_success("Easy control scripts created")
    
    def run_complete_setup(self):
        """Run the complete setup wizard"""
        print_header("ActiveLog Easy Setup Wizard")
        print(f"{Colors.CYAN}Welcome! Let's get ActiveLog optimized for your device in just a few steps.{Colors.END}")
        
        try:
            # Step 1: Device detection
            self.detect_device_automatically()
            
            # Step 2: User preferences
            self.ask_simple_questions()
            
            # Step 3: Generate recommendations
            self.generate_recommendations()
            self.display_recommendations()
            
            # Confirm with user
            print(f"\n{Colors.YELLOW}Does this look good?{Colors.END}")
            confirm = input(f"{Colors.CYAN}Proceed with setup? (y/n): {Colors.END}").lower()
            
            if not confirm.startswith('y'):
                print_info("Setup cancelled. Run 'python3 easy_setup.py' to try again.")
                return False
            
            # Step 4: Cloud setup (if needed)
            self.setup_cloud_config()
            
            # Step 5: Create configurations
            self.create_configuration_files()
            
            # Step 6: Apply optimizations
            self.apply_optimizations()
            
            # Step 7: Create control scripts
            self.create_easy_controls()
            
            # Success message
            print_header("Setup Complete!")
            print(f"{Colors.GREEN}{Colors.BOLD}🎉 ActiveLog is ready to use!{Colors.END}")
            
            print(f"\n{Colors.CYAN}Quick Start:{Colors.END}")
            print(f"   {Colors.BOLD}./start_activelog.sh{Colors.END}     - Start ActiveLog")
            print(f"   {Colors.BOLD}python3 monitor.py{Colors.END}      - Monitor performance")
            print(f"   {Colors.BOLD}./stop_activelog.sh{Colors.END}     - Stop all services")
            
            print(f"\n{Colors.CYAN}Web Interfaces:{Colors.END}")
            print(f"   📊 Dashboard: http://localhost:8088")
            print(f"   🎛️  Control Panel: http://localhost:3000")
            
            if self.user_preferences.get("use_cloud"):
                print(f"\n{Colors.YELLOW}☁️  Cloud Computing:{Colors.END}")
                print(f"   Add your cloud API keys to 'cloud_providers.json'")
                print(f"   Estimated cost: $0.01-0.20/hour when using AI features")
            
            print(f"\n{Colors.PURPLE}💡 Tips:{Colors.END}")
            print(f"   • Run 'python3 easy_setup.py' anytime to reconfigure")
            print(f"   • Check 'performance_dashboard.html' for system health")
            print(f"   • All settings are in 'activelog_config.json'")
            
            # Ask if user wants to start now
            start_now = input(f"\n{Colors.CYAN}Start ActiveLog now? (y/n): {Colors.END}").lower()
            if start_now.startswith('y'):
                print("\n🚀 Starting ActiveLog...")
                subprocess.run(["./start_activelog.sh"])
            
            return True
            
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Setup interrupted by user{Colors.END}")
            return False
        except Exception as e:
            print_error(f"Setup failed: {e}")
            return False

def main():
    """Main setup function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--apply-config":
        # Apply existing configuration
        try:
            with open("activelog_config.json") as f:
                config = json.load(f)
            print_info("Applying existing configuration...")
            # Apply optimizations based on stored config
            subprocess.run([sys.executable, "device_optimization_manager.py"], 
                          capture_output=True)
            print_success("Configuration applied")
        except FileNotFoundError:
            print_error("No configuration found. Please run setup first.")
        return
    
    # Run setup wizard
    wizard = EasySetupWizard()
    wizard.run_complete_setup()

if __name__ == "__main__":
    main()