#!/usr/bin/env python3
"""
Run Both ELLA and LEON Servers
- ELLA: Guest-facing chat assistant (port 8000)
- LEON: Hotel management system (port 8001)
- Voice server: OpenAI Realtime API (port 8004)
"""

import subprocess
import sys
import time
import threading
import signal
import os
from pathlib import Path

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_colored(message, color):
    print(f"{color}{message}{Colors.ENDC}")

def run_server(script_name, server_name, port, color):
    """Run a server in a separate thread"""
    try:
        print_colored(f"🚀 Starting {server_name} on port {port}...", color)
        
        # Check if the script exists
        if not Path(script_name).exists():
            print_colored(f"❌ Error: {script_name} not found!", Colors.FAIL)
            return
        
        # Run the server
        process = subprocess.Popen(
            [sys.executable, script_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Stream output with color coding
        for line in iter(process.stdout.readline, ''):
            if line.strip():
                timestamp = time.strftime("%H:%M:%S")
                print_colored(f"[{timestamp}] {server_name}: {line.strip()}", color)
        
        process.wait()
        
    except KeyboardInterrupt:
        print_colored(f"🛑 Stopping {server_name}...", Colors.WARNING)
        if 'process' in locals():
            process.terminate()
    except Exception as e:
        print_colored(f"❌ Error running {server_name}: {e}", Colors.FAIL)

def check_ports():
    """Check if required ports are available"""
    import socket
    
    ports_to_check = [
        (8000, "ELLA Guest Assistant"),
        (8001, "LEON Hotel Manager"), 
        (8004, "Voice Server")
    ]
    
    for port, service in ports_to_check:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        
        if result == 0:
            print_colored(f"⚠️  Warning: Port {port} ({service}) is already in use", Colors.WARNING)
            return False
    
    return True

def main():
    print_colored("=" * 60, Colors.HEADER)
    print_colored("🏨 ELLA HOTEL SYSTEM - DUAL SERVER STARTUP", Colors.HEADER)
    print_colored("=" * 60, Colors.HEADER)
    print()
    
    print_colored("📋 Server Configuration:", Colors.OKBLUE)
    print_colored("   👩‍💼 ELLA (Guest Assistant)  → http://localhost:8000", Colors.OKGREEN)
    print_colored("   🏨 LEON (Hotel Manager)     → http://localhost:8001", Colors.OKCYAN)
    print_colored("   🗣️  Voice Server (Optional)  → http://localhost:8004", Colors.WARNING)
    print()
    
    # Check if ports are available
    if not check_ports():
        print_colored("❌ Please stop conflicting services and try again.", Colors.FAIL)
        return
    
    print_colored("🔍 Checking server files...", Colors.OKBLUE)
    
    # Check required files
    required_files = [
        ("main.py", "ELLA Guest Assistant"),
        ("leon_server.py", "LEON Hotel Manager"),
        ("voice_hotel.py", "Voice Server")
    ]
    
    available_servers = []
    for filename, description in required_files:
        if Path(filename).exists():
            print_colored(f"   ✅ {description}: {filename}", Colors.OKGREEN)
            available_servers.append((filename, description))
        else:
            print_colored(f"   ❌ {description}: {filename} not found", Colors.FAIL)
    
    if len(available_servers) < 2:
        print_colored("❌ Not enough servers available to run.", Colors.FAIL)
        return
    
    print()
    print_colored("🚀 Starting servers...", Colors.HEADER)
    print_colored("   Press Ctrl+C to stop all servers", Colors.WARNING)
    print()
    
    # Storage for server threads
    threads = []
    
    try:
        # Start ELLA (Guest Assistant)
        if ("main.py", "ELLA Guest Assistant") in available_servers:
            ella_thread = threading.Thread(
                target=run_server,
                args=("main.py", "ELLA", 8000, Colors.OKGREEN),
                daemon=True
            )
            ella_thread.start()
            threads.append(ella_thread)
            time.sleep(2)  # Stagger startup
        
        # Start LEON (Hotel Manager)
        if ("leon_server.py", "LEON Hotel Manager") in available_servers:
            leon_thread = threading.Thread(
                target=run_server,
                args=("leon_server.py", "LEON", 8001, Colors.OKCYAN),
                daemon=True
            )
            leon_thread.start()
            threads.append(leon_thread)
            time.sleep(2)  # Stagger startup
        
        # Start Voice Server (optional)
        if ("voice_hotel.py", "Voice Server") in available_servers:
            voice_thread = threading.Thread(
                target=run_server,
                args=("voice_hotel.py", "VOICE", 8004, Colors.WARNING),
                daemon=True
            )
            voice_thread.start()
            threads.append(voice_thread)
            time.sleep(2)  # Stagger startup
        
        print()
        print_colored("✅ All servers started successfully!", Colors.OKGREEN)
        print()
        print_colored("🌐 Access URLs:", Colors.HEADER)
        if ("main.py", "ELLA Guest Assistant") in available_servers:
            print_colored("   👩‍💼 ELLA Guest Interface:    http://localhost:8000", Colors.OKGREEN)
        if ("leon_server.py", "LEON Hotel Manager") in available_servers:
            print_colored("   🏨 LEON Management Dashboard: http://localhost:8001", Colors.OKCYAN)
        if ("voice_hotel.py", "Voice Server") in available_servers:
            print_colored("   🗣️  Voice Interface:          http://localhost:8004", Colors.WARNING)
        print()
        
        print_colored("🔧 System Roles:", Colors.OKBLUE)
        print_colored("   • ELLA: Guest-facing (READ-ONLY access + booking confirmations)", Colors.OKGREEN)
        print_colored("   • LEON: Hotel management (FULL database & media access)", Colors.OKCYAN)
        print_colored("   • Voice: Real-time conversation (bridges to ELLA chat)", Colors.WARNING)
        print()
        
        print_colored("📱 API Health Checks:", Colors.OKBLUE)
        print_colored("   • ELLA Health: http://localhost:8000/health", Colors.OKGREEN)
        print_colored("   • LEON Health: http://localhost:8001/health", Colors.OKCYAN)
        print_colored("   • Voice Health: http://localhost:8004/voice/health", Colors.WARNING)
        print_colored("   • ELLA Stats:  http://localhost:8000/api/stats", Colors.OKGREEN)
        print_colored("   • LEON Stats:  http://localhost:8001/api/stats", Colors.OKCYAN)
        print()
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print()
        print_colored("🛑 Shutdown signal received. Stopping all servers...", Colors.WARNING)
        print()
        
        # Wait for threads to finish
        for thread in threads:
            if thread.is_alive():
                thread.join(timeout=5)
        
        print_colored("✅ All servers stopped successfully.", Colors.OKGREEN)
        print_colored("👋 Thank you for using ELLA Hotel System!", Colors.HEADER)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print_colored(f"❌ Critical error: {e}", Colors.FAIL)
        sys.exit(1) 