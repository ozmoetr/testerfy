#!/usr/bin/env python3
"""
Testerfy Daemon Manager
A simple script to manage the Testerfy background process.
"""

import os
import sys
import signal
import subprocess
import time

PID_FILE = os.path.expanduser("~/.testerfy/testerfy.pid")
LOG_FILE = os.path.expanduser("~/.testerfy/testerfy.log")

def get_pid():
    """Get the PID from the PID file if it exists."""
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r') as f:
                return int(f.read().strip())
    except (ValueError, IOError):
        pass
    return None

def is_running(pid):
    """Check if a process with the given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def start():
    """Start Testerfy in the background."""
    pid = get_pid()
    if pid and is_running(pid):
        print("Testerfy is already running (PID: {})".format(pid))
        return
    
    print("Starting Testerfy...")
    try:
        # Start the main script
        subprocess.Popen([sys.executable, "main.py"], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL,
                        preexec_fn=os.setsid)
        
        # Wait a moment for the process to start
        time.sleep(2)
        
        pid = get_pid()
        if pid and is_running(pid):
            print("Testerfy started successfully (PID: {})".format(pid))
            print("Check your system tray for the Testerfy icon.")
        else:
            print("Testerfy may have failed to start. Check the log file: {}".format(LOG_FILE))
            
    except Exception as e:
        print("Failed to start Testerfy: {}".format(e))

def stop():
    """Stop the running Testerfy process."""
    pid = get_pid()
    if not pid:
        print("Testerfy is not running (no PID file found)")
        return
    
    if not is_running(pid):
        print("Testerfy is not running (PID {} not found)".format(pid))
        # Clean up stale PID file
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
        return
    
    print("Stopping Testerfy (PID: {})...".format(pid))
    try:
        # Send SIGTERM first
        os.kill(pid, signal.SIGTERM)
        
        # Wait for graceful shutdown
        for i in range(10):
            if not is_running(pid):
                print("Testerfy stopped successfully")
                # Clean up PID file
                try:
                    os.remove(PID_FILE)
                except OSError:
                    pass
                return
            time.sleep(1)
        
        # Force kill if still running
        print("Force killing Testerfy...")
        os.kill(pid, signal.SIGKILL)
        time.sleep(1)
        
        if not is_running(pid):
            print("Testerfy force stopped")
            try:
                os.remove(PID_FILE)
            except OSError:
                pass
        else:
            print("Failed to stop Testerfy")
            
    except OSError as e:
        print("Failed to stop Testerfy: {}".format(e))

def status():
    """Show the status of Testerfy."""
    pid = get_pid()
    if not pid:
        print("Testerfy is not running (no PID file found)")
        return
    
    if is_running(pid):
        print("Testerfy is running (PID: {})".format(pid))
        print("Check your system tray for the Testerfy icon.")
    else:
        print("Testerfy is not running (PID {} not found)".format(pid))
        print("The PID file may be stale.")

def restart():
    """Restart Testerfy."""
    print("Restarting Testerfy...")
    stop()
    time.sleep(2)
    start()

def main():
    if len(sys.argv) != 2:
        print("Usage: {} {{start|stop|restart|status}}".format(sys.argv[0]))
        print("\nCommands:")
        print("  start   - Start Testerfy in the background")
        print("  stop    - Stop the running Testerfy process")
        print("  restart - Restart Testerfy")
        print("  status  - Show the current status of Testerfy")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "start":
        start()
    elif command == "stop":
        stop()
    elif command == "restart":
        restart()
    elif command == "status":
        status()
    else:
        print("Unknown command: {}".format(command))
        sys.exit(1)

if __name__ == "__main__":
    main() 