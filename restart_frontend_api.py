"""
Restart script for Frontend API Server
Kills all processes on port 5001 and starts a fresh server
"""
import subprocess
import time
import psutil
import sys

def kill_processes_on_port(port):
    """Kill all processes listening on the specified port"""
    killed = []
    for conn in psutil.net_connections():
        if conn.laddr.port == port and conn.status == 'LISTEN':
            try:
                process = psutil.Process(conn.pid)
                print(f"Killing process {conn.pid}: {process.name()}")
                process.kill()
                killed.append(conn.pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                print(f"Could not kill process {conn.pid}: {e}")

    if killed:
        print(f"Killed {len(killed)} process(es) on port {port}")
        time.sleep(2)
    else:
        print(f"No processes found on port {port}")

    return killed

def main():
    port = 5001

    print("=" * 60)
    print("Restarting Frontend API Server")
    print("=" * 60)

    # Kill existing processes
    kill_processes_on_port(port)

    # Start new server
    print(f"\nStarting Frontend API Server on port {port}...")
    subprocess.Popen([sys.executable, "frontend_api.py"], cwd=".")
    print("Server started!")

    # Wait and verify
    time.sleep(3)
    print("\nVerifying server is running...")
    for conn in psutil.net_connections():
        if conn.laddr.port == port and conn.status == 'LISTEN':
            print(f"Server is listening on port {port} (PID: {conn.pid})")
            break
    else:
        print(f"WARNING: No server found on port {port}")

if __name__ == "__main__":
    main()
