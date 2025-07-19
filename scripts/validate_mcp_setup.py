#!/usr/bin/env python3
"""
Validate MCP server setup and API keys
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def load_mcp_config():
    """Load MCP configuration"""
    config_path = Path(__file__).parent.parent / "config" / "mcp_config.json"
    with open(config_path, 'r') as f:
        return json.load(f)

def check_api_keys(config):
    """Check if required API keys are present"""
    missing_keys = []
    
    # Config has servers as top-level keys, not nested under 'mcp_servers'
    for server_name, server_config in config.items():
        if not server_config.get('enabled', False):
            continue
            
        # Check for API keys in env section
        env_vars = server_config.get('env', {})
        for env_var, default_value in env_vars.items():
            if not os.getenv(env_var) and default_value == "":
                missing_keys.append(f"{server_name}: {env_var}")
    
    return missing_keys

def check_server_availability(config):
    """Check if MCP servers are available"""
    unavailable_servers = []
    
    for server_name, server_config in config.items():
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
