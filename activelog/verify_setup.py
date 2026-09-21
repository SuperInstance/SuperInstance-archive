#!/usr/bin/env python3
"""
Quick verification that all ActiveLog easy-use features are properly set up
"""
import os
import sys
from pathlib import Path

def check_file_exists_executable(file_path, description):
    """Check if file exists and is executable"""
    if Path(file_path).exists():
        if os.access(file_path, os.X_OK):
            print(f"✅ {description}: {file_path}")
            return True
        else:
            print(f"⚠️  {description}: {file_path} (not executable)")
            return False
    else:
        print(f"❌ {description}: {file_path} (missing)")
        return False

def main():
    print("🔍 ActiveLog Setup Verification\n")
    
    essential_files = [
        ("./activelog", "Main CLI Interface"),
        ("./one_click_tools.py", "One-Click Tools"),
        ("./easy_setup.py", "Easy Setup Wizard"),
        ("./web_dashboard.py", "Web Dashboard"),
        ("./simple_troubleshooter.py", "Auto Troubleshooter"),
    ]
    
    optimization_files = [
        ("./advanced_optimizer.py", "Advanced ML Optimizer"),
        ("./device_optimization_manager.py", "Device-Specific Optimizer"),
        ("./cloud_compute_offloader.py", "Cloud Computing Integration"),
        ("./performance_monitor.py", "Performance Monitor"),
        ("./smart_service_manager.py", "Smart Service Manager"),
    ]
    
    documentation = [
        ("./EASY_SETUP_GUIDE.md", "User Guide"),
    ]
    
    # Check essential easy-use tools
    print("📋 Essential Easy-Use Tools:")
    essential_ok = 0
    for file_path, desc in essential_files:
        if check_file_exists_executable(file_path, desc):
            essential_ok += 1
    
    print(f"\n⚡ Performance Optimization Tools:")
    optimization_ok = 0
    for file_path, desc in optimization_files:
        if check_file_exists_executable(file_path, desc):
            optimization_ok += 1
    
    print(f"\n📚 Documentation:")
    docs_ok = 0
    for file_path, desc in documentation:
        if Path(file_path).exists():
            print(f"✅ {desc}: {file_path}")
            docs_ok += 1
        else:
            print(f"❌ {desc}: {file_path} (missing)")
    
    # Overall status
    print(f"\n🎯 Summary:")
    print(f"   Essential Tools: {essential_ok}/{len(essential_files)}")
    print(f"   Optimization Tools: {optimization_ok}/{len(optimization_files)}")
    print(f"   Documentation: {docs_ok}/{len(documentation)}")
    
    if essential_ok == len(essential_files):
        print(f"\n🎉 ActiveLog is ready to use!")
        print(f"   Quick start: ./activelog start")
        print(f"   Web interface: ./activelog dashboard")
        print(f"   Get help: ./activelog help")
        return True
    else:
        print(f"\n⚠️ Some essential files are missing or not executable")
        print(f"   Run: chmod +x *.py activelog")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)