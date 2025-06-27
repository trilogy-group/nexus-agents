"""
Web server for the Nexus Agents system.
"""
import argparse
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Create the FastAPI app
app = FastAPI(title="Nexus Agents Web UI", description="Web UI for the Nexus Agents system")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the static files
app.mount("/", StaticFiles(directory="static", html=True), name="static")


def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Nexus Agents Web UI Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=12001, help="Port to bind to")
    args = parser.parse_args()
    
    # Start the web server
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()