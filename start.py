"""
Start script for the Nexus Agents system.
"""
import argparse
import os
import subprocess
import sys
import time
from dotenv import load_dotenv


def main():
    """Main entry point."""
    # Load environment variables from .env if present
    load_dotenv()

    # Parse command line arguments (env-backed defaults)
    parser = argparse.ArgumentParser(description="Start the Nexus Agents system")
    parser.add_argument("--api-host", default=os.getenv("API_HOST", "0.0.0.0"), help="Host for the API server")
    parser.add_argument("--api-port", type=int, default=int(os.getenv("API_PORT", "12000")), help="Port for the API server")
    parser.add_argument("--web-host", default=os.getenv("FRONTEND_HOST", "localhost"), help="Host for the frontend server")
    parser.add_argument("--web-port", type=int, default=int(os.getenv("FRONTEND_PORT", "3000")), help="Port for the frontend server")
    args = parser.parse_args()

    # Start the API server
    api_process = subprocess.Popen([
        sys.executable, "api.py",
        "--host", args.api_host,
        "--port", str(args.api_port)
    ])

    # Start the Next.js frontend (dev) with proper environment for API URL
    frontend_env = os.environ.copy()
    frontend_env["PORT"] = str(args.web_port)
    # Expose API connection details to the browser
    frontend_env["NEXT_PUBLIC_API_HOST"] = os.getenv("NEXT_PUBLIC_API_HOST", "localhost")
    frontend_env["NEXT_PUBLIC_API_PORT"] = os.getenv("NEXT_PUBLIC_API_PORT", str(args.api_port))

    web_process = subprocess.Popen(
        ["npm", "run", "dev", "--", "--hostname", args.web_host, "-p", str(args.web_port)],
        cwd=os.path.join(os.path.dirname(__file__), "nexus-frontend"),
        env=frontend_env,
    )

    print(f"API server running at http://{args.api_host}:{args.api_port}")
    print(f"Frontend (Next.js) running at http://{args.web_host}:{args.web_port}")
    print(f"Monitoring WS endpoint: ws://{frontend_env['NEXT_PUBLIC_API_HOST']}:{frontend_env['NEXT_PUBLIC_API_PORT']}/ws/monitor")

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