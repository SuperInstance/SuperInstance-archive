#!/usr/bin/env python3
"""
Simple public access setup without tunnel passwords
"""

import subprocess
import time
import sys
import signal

def signal_handler(sig, frame):
    print('\n🛑 Shutting down tunnels...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Kill existing tunnels
subprocess.run(["pkill", "-f", "localtunnel"], stderr=subprocess.DEVNULL)
time.sleep(2)

print("🌐 Starting simple tunnels without password requirements...")

# Start web tunnel with a simple random subdomain
web_process = subprocess.Popen([
    "npx", "localtunnel", 
    "--port", "8105"
], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

print("⏳ Waiting for tunnel URL...")
web_url = None

# Get the URL
for i in range(20):
    time.sleep(1)
    if web_process.poll() is not None:
        print("❌ Tunnel process failed")
        break
    
    try:
        line = web_process.stdout.readline()
        if line and "https://" in line:
            web_url = line.strip().replace("your url is: ", "")
            break
    except:
        continue

if web_url:
    print(f"\n🎉 DMLog Web Portal is now accessible:")
    print(f"🌐 URL: {web_url}")
    print(f"👥 Login: Max/Snow or Casey/Snow")
    print(f"\n📋 Instructions:")
    print(f"1. Go to: {web_url}")
    print(f"2. If you see a tunnel screen, just click 'Continue' or click your IP")
    print(f"3. Login with Max/Snow or Casey/Snow")
    print(f"\n🔄 Keeping tunnel alive... (Press Ctrl+C to stop)")
    
    try:
        while True:
            time.sleep(30)
            if web_process.poll() is not None:
                print("❌ Tunnel died, restarting...")
                break
            print(f"✅ {time.strftime('%H:%M:%S')} - Tunnel active")
    except KeyboardInterrupt:
        print("\n🛑 Stopping tunnel...")
        web_process.terminate()
else:
    print("❌ Failed to get tunnel URL")

print("✅ Done")