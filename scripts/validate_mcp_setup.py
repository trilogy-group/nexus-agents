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
    
    for server_name, server_config in config.items():
        if not server_config.get('enabled', False):
            continue
            
        env_config = server_config.get('env', {})
        for env_var in env_config.keys():
            if not os.getenv(env_var):
                missing_keys.append(f"{server_name}: {env_var}")
    
    return missing_keys

def check_server_availability(config):
    """Check if MCP servers are available"""
    unavailable_servers = []
    
    for server_name, server_config in config.items():
        if not server_config.get('enabled', False):
            continue
            
        try:
            if server_config['type'] == 'nodejs':
                # For Node.js servers, check if the external directory exists and package.json is present
                server_dir = Path('external_mcp_servers') / server_config.get('directory', server_name)
                if not server_dir.exists():
                    unavailable_servers.append(server_name)
                elif not (server_dir / 'package.json').exists():
                    unavailable_servers.append(server_name)
            elif server_config['type'] == 'python':
                # Check if Python package is available by importing from the correct directory
                server_dir = Path('external_mcp_servers') / server_config.get('directory', server_name)
                result = subprocess.run(
                    ['uv', 'run', 'python', '-c', f'import {server_config["package"].replace("-", "_")}'], 
                    capture_output=True, 
                    text=True,
                    cwd=server_dir if server_dir.exists() else None
                )
                if result.returncode != 0:
                    unavailable_servers.append(server_name)
        except Exception:
            unavailable_servers.append(server_name)
    
    return unavailable_servers

def main():
    """Main validation function"""
    print(" Validating MCP server setup...")
    
    try:
        config = load_mcp_config()
    except Exception as e:
        print(f" Failed to load MCP configuration: {e}")
        return False
    
    # Get enabled servers
    enabled_servers = [name for name, conf in config.items() if conf.get('enabled', False)]
    
    if not enabled_servers:
        print("  No MCP servers are enabled in the configuration.")
        print("Enable at least one server in config/mcp_config.json to use MCP functionality.")
        return True  # Not an error, just no servers enabled
    
    # Check API keys and server availability
    missing_keys = check_api_keys(config)
    unavailable_servers = check_server_availability(config)
    
    # Determine working servers (enabled, with API keys, and available)
    servers_with_missing_keys = {key.split(': ')[0] for key in missing_keys}
    working_servers = [
        server for server in enabled_servers 
        if server not in servers_with_missing_keys and server not in unavailable_servers
    ]
    
    # Show results
    has_issues = bool(missing_keys or unavailable_servers)
    
    if working_servers:
        print(" Working MCP servers:")
        for server in working_servers:
            print(f"   - {server}")
    
    if missing_keys:
        print("  MCP servers missing API keys:")
        for key in missing_keys:
            server_name = key.split(': ')[0]
            env_var = key.split(': ')[1]
            print(f"   - {server_name}: {env_var}")
    
    if unavailable_servers:
        print(" Unavailable MCP servers:")
        for server in unavailable_servers:
            print(f"   - {server}")
    
    if has_issues:
        if missing_keys:
            print("\nPlease set the missing environment variables before running the application.")
        if unavailable_servers:
            print("Please run 'scripts/setup_mcp_servers.sh' to install missing servers.")
        return False
    
    if not working_servers:
        print("  No MCP servers are fully operational.")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
