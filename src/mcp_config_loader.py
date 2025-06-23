"""
MCP Configuration Loader
Handles loading and validation of MCP server configurations
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


class MCPConfigLoader:
    """Loads and validates MCP server configurations"""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "mcp_config.json"
        self.config_path = Path(config_path)
        self._config = None
    
    def load_config(self) -> Dict:
        """Load MCP configuration from JSON file"""
        if self._config is None:
            try:
                with open(self.config_path, 'r') as f:
                    self._config = json.load(f)
            except FileNotFoundError:
                raise FileNotFoundError(f"MCP configuration file not found: {self.config_path}")
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in MCP configuration: {e}")
        return self._config
    
    def get_enabled_servers(self) -> Dict[str, Dict]:
        """Get all enabled MCP servers from configuration"""
        config = self.load_config()
        enabled_servers = {}
        
        for server_name, server_config in config.items():
            if server_config.get('enabled', False):
                enabled_servers[server_name] = server_config
        
        return enabled_servers
    
    def get_server_config(self, server_name: str) -> Optional[Dict]:
        """Get configuration for a specific server"""
        config = self.load_config()
        server_config = config.get(server_name)
        
        # Only return enabled servers
        if server_config and server_config.get('enabled', False):
            return server_config
        
        return None
    
    def validate_api_keys(self, servers: Optional[Dict] = None) -> List[str]:
        """Validate that required API keys are present"""
        if servers is None:
            servers = self.get_enabled_servers()
        
        missing_keys = []
        
        for server_name, server_config in servers.items():
            env_config = server_config.get('env', {})
            for env_var in env_config.keys():
                if not os.getenv(env_var):
                    missing_keys.append(f"{server_name}: {env_var}")
        
        return missing_keys
    
    def check_server_availability(self, servers: Optional[Dict] = None) -> List[str]:
        """Check if MCP servers are available"""
        if servers is None:
            servers = self.get_enabled_servers()
        
        unavailable_servers = []
        
        for server_name, server_config in servers.items():
            try:
                if server_config['type'] == 'nodejs':
                    # Check if npm package is available globally or can be run with npx
                    result = subprocess.run(
                        ['npx', '--version'], 
                        capture_output=True, 
                        text=True
                    )
                    if result.returncode != 0:
                        unavailable_servers.append(server_name)
                elif server_config['type'] == 'python':
                    # Check if Python package is available
                    package_name = server_config['package'].replace('-', '_')
                    
                    # For external MCP servers, check from their directory
                    server_dir = Path('external_mcp_servers') / server_config.get('directory', server_name)
                    if server_dir.exists():
                        result = subprocess.run(
                            ['uv', 'run', 'python', '-c', f'import {package_name}'], 
                            capture_output=True, 
                            text=True,
                            cwd=server_dir
                        )
                    else:
                        # Fallback: check globally
                        result = subprocess.run(
                            ['uv', 'run', 'python', '-c', f'import {package_name}'], 
                            capture_output=True, 
                            text=True
                        )
                    
                    if result.returncode != 0:
                        unavailable_servers.append(server_name)
            except Exception:
                unavailable_servers.append(server_name)
        
        return unavailable_servers
    
    def validate_setup(self) -> tuple[bool, List[str]]:
        """Validate complete MCP setup"""
        errors = []
        
        try:
            servers = self.get_enabled_servers()
            
            # Check API keys
            missing_keys = self.validate_api_keys(servers)
            if missing_keys:
                errors.extend([f"Missing API key: {key}" for key in missing_keys])
            
            # Check server availability
            unavailable_servers = self.check_server_availability(servers)
            if unavailable_servers:
                errors.extend([f"Server unavailable: {server}" for server in unavailable_servers])
            
        except Exception as e:
            errors.append(f"Configuration error: {e}")
        
        return len(errors) == 0, errors
    
    def get_server_command_info(self, server_name: str) -> Optional[Dict]:
        """Get command information for a specific server"""
        servers = self.get_enabled_servers()
        return servers.get(server_name)
    
    def print_setup_status(self):
        """Print a human-readable setup status"""
        is_valid, errors = self.validate_setup()
        
        if is_valid:
            print("✅ All MCP servers are properly configured and available!")
            servers = self.get_enabled_servers()
            print(f"📊 Enabled servers: {', '.join(servers.keys())}")
        else:
            print("❌ MCP setup validation failed:")
            for error in errors:
                print(f"   - {error}")
            print("\nPlease run 'scripts/setup_mcp_servers.sh' and set required API keys.")
        
        return is_valid
