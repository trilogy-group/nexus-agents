#!/bin/bash

# MCP Servers Setup Script
# This script installs and builds official MCP servers for Nexus Agents

set -e  # Exit on any error

echo "🚀 Setting up MCP Servers for Nexus Agents..."

# Create necessary directories
mkdir -p external_mcp_servers
mkdir -p logs

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check required dependencies
echo "📋 Checking dependencies..."

if ! command_exists node; then
    echo "❌ Node.js is required but not installed. Please install Node.js 18+ and try again."
    exit 1
fi

if ! command_exists npm; then
    echo "❌ npm is required but not installed. Please install npm and try again."
    exit 1
fi

if ! command_exists python3; then
    echo "❌ Python 3 is required but not installed. Please install Python 3.11+ and try again."
    exit 1
fi

if ! command_exists uv; then
    echo "❌ uv is required but not installed. Please install uv and try again."
    echo "   Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ All dependencies found"

# Install Node.js MCP servers
echo "📦 Installing Node.js MCP servers..."

# Firecrawl MCP Server
echo "Installing Firecrawl MCP server..."
if [ ! -d "external_mcp_servers/firecrawl-mcp" ]; then
    git clone https://github.com/mendableai/firecrawl-mcp-server external_mcp_servers/firecrawl-mcp
fi
cd external_mcp_servers/firecrawl-mcp
npm install --yes
npm run build
npm link --force
cd ../..

# Exa MCP Server
echo "Installing Exa MCP server..."
if [ ! -d "external_mcp_servers/exa-mcp" ]; then
    git clone https://github.com/exa-labs/exa-mcp-server external_mcp_servers/exa-mcp
fi
cd external_mcp_servers/exa-mcp
npm install --yes
# Set non-interactive mode for npx
export CI=true
export npm_config_yes=true
npm run build
npm link --force
cd ../..

# Perplexity MCP Server
echo "Installing Perplexity MCP server..."
if [ ! -d "external_mcp_servers/perplexity-mcp" ]; then
    git clone https://github.com/ppl-ai/modelcontextprotocol external_mcp_servers/perplexity-mcp
fi
cd external_mcp_servers/perplexity-mcp/perplexity-ask
npm install --yes
npm run build
npm link --force
cd ../../..

# Python MCP servers
echo "📦 Installing Python MCP servers..."

echo "✅ All MCP servers installed successfully!"

# Install Python dependencies for the main project
echo "📦 Installing Python dependencies with uv..."
uv add mcp

# Create a validation script
cat > scripts/validate_mcp_setup.py << 'EOF'
#!/usr/bin/env python3
"""
Validate MCP server setup and API keys
"""
import json
import os
import subprocess
import sys
from pathlib import Path

def load_mcp_config():
    """Load MCP configuration"""
    config_path = Path(__file__).parent.parent / "config" / "mcp_config.json"
    with open(config_path, 'r') as f:
        return json.load(f)

def check_api_keys(config):
    """Check if required API keys are present"""
    missing_keys = []
    
    for server_name, server_config in config['mcp_servers'].items():
        if not server_config.get('enabled', False):
            continue
            
        for env_var in server_config.get('required_env_vars', []):
            if not os.getenv(env_var):
                missing_keys.append(f"{server_name}: {env_var}")
    
    return missing_keys

def check_server_availability(config):
    """Check if MCP servers are available"""
    unavailable_servers = []
    
    for server_name, server_config in config['mcp_servers'].items():
        if not server_config.get('enabled', False):
            continue
            
        try:
            if server_config['type'] == 'node':
                # Check if npm package is available
                result = subprocess.run(
                    ['npm', 'list', '-g', server_config['package']], 
                    capture_output=True, 
                    text=True
                )
                if result.returncode != 0:
                    unavailable_servers.append(server_name)
            elif server_config['type'] == 'python':
                # Check if Python package is available
                result = subprocess.run(
                    ['uv', 'run', 'python', '-c', f'import {server_config["package"].replace("-", "_")}'], 
                    capture_output=True, 
                    text=True
                )
                if result.returncode != 0:
                    unavailable_servers.append(server_name)
        except Exception:
            unavailable_servers.append(server_name)
    
    return unavailable_servers

def main():
    """Main validation function"""
    print("🔍 Validating MCP server setup...")
    
    try:
        config = load_mcp_config()
    except Exception as e:
        print(f"❌ Failed to load MCP configuration: {e}")
        return False
    
    # Check API keys
    missing_keys = check_api_keys(config)
    if missing_keys:
        print("⚠️  Missing required API keys:")
        for key in missing_keys:
            print(f"   - {key}")
        print("\nPlease set these environment variables before running the application.")
        return False
    
    # Check server availability
    unavailable_servers = check_server_availability(config)
    if unavailable_servers:
        print("❌ Unavailable MCP servers:")
        for server in unavailable_servers:
            print(f"   - {server}")
        print("\nPlease run 'scripts/setup_mcp_servers.sh' to install missing servers.")
        return False
    
    print("✅ All MCP servers are properly configured and available!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
EOF

chmod +x scripts/validate_mcp_setup.py

echo "🎉 MCP server setup complete!"
echo ""
echo "Next steps:"
echo "1. Set your API keys in environment variables:"
echo "   - FIRECRAWL_API_KEY"
echo "   - EXA_API_KEY" 
echo "   - PERPLEXITY_API_KEY"
echo ""
echo "2. Run validation: uv run python scripts/validate_mcp_setup.py"
echo "3. Start Nexus Agents: uv run python main.py"
