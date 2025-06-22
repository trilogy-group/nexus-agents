#!/usr/bin/env python3
"""
Simple test to verify MCP server availability.
"""
import asyncio
import subprocess
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def test_server_executable(server_name: str, command: list):
    """Test if a server command is executable."""
    print(f"\n--- Testing {server_name} server executable ---")
    
    try:
        # Try to start the process
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Give it a moment to start
        await asyncio.sleep(0.5)
        
        # Check if it's still running
        if process.returncode is None:
            print(f"✓ {server_name} server started successfully")
            
            # Terminate the process
            process.terminate()
            await process.wait()
            return True
        else:
            stderr = await process.stderr.read()
            print(f"✗ {server_name} server failed to start: {stderr.decode()}")
            return False
            
    except FileNotFoundError:
        print(f"✗ {server_name} server command not found: {' '.join(command)}")
        return False
    except Exception as e:
        print(f"✗ {server_name} server error: {e}")
        return False


async def main():
    """Test all MCP servers."""
    print("Testing MCP server executables...")
    
    servers = {
        "linkup": ["mcp-search-linkup"],
        "exa": ["node", str(Path(__file__).parent / "external_mcp_servers" / "exa-mcp" / ".smithery" / "index.cjs")],
        "perplexity": ["node", str(Path(__file__).parent / "external_mcp_servers" / "perplexity-official-mcp" / "perplexity-ask" / "dist" / "index.js")],
        "firecrawl": ["node", str(Path(__file__).parent / "external_mcp_servers" / "firecrawl-mcp" / "dist" / "index.js")]
    }
    
    results = {}
    for server_name, command in servers.items():
        results[server_name] = await test_server_executable(server_name, command)
    
    print("\n--- Summary ---")
    for server_name, success in results.items():
        status = "✓" if success else "✗"
        print(f"{status} {server_name}: {'Available' if success else 'Not available'}")
    
    return all(results.values())


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)