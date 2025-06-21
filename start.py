"""
Start script for the Nexus Agents system.
"""
import argparse
import os
import subprocess
import sys
import time


def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Start the Nexus Agents system")
    parser.add_argument("--api-host", default="0.0.0.0", help="Host for the API server")
    parser.add_argument("--api-port", type=int, default=12000, help="Port for the API server")
    parser.add_argument("--web-host", default="0.0.0.0", help="Host for the web server")
    parser.add_argument("--web-port", type=int, default=12001, help="Port for the web server")
    args = parser.parse_args()
    
    # Start the API server
    api_process = subprocess.Popen([
        sys.executable, "api.py",
        "--host", args.api_host,
        "--port", str(args.api_port)
    ])
    
    # Start the web server
    web_process = subprocess.Popen([
        sys.executable, "web/server.py",
        "--host", args.web_host,
        "--port", str(args.web_port)
    ])
    
    print(f"API server running at http://{args.api_host}:{args.api_port}")
    print(f"Web UI running at http://{args.web_host}:{args.web_port}")
    
    try:
        # Keep the servers running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Stop the servers
        api_process.terminate()
        web_process.terminate()
        
        print("Servers stopped")


if __name__ == "__main__":
    main()