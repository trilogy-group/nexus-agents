#!/usr/bin/env python3
"""
Simple test MCP server for testing the MCP client implementation.
"""
from mcp.server.fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP("Test Server")


@mcp.tool()
def echo(message: str) -> str:
    """
    Echo a message back.
    
    Args:
        message: The message to echo
    
    Returns:
        The echoed message
    """
    return f"Echo: {message}"


@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """
    Add two numbers.
    
    Args:
        a: First number
        b: Second number
    
    Returns:
        The sum of a and b
    """
    return a + b


@mcp.resource("test://greeting/{name}")
def get_greeting(name: str) -> str:
    """
    Get a greeting for a name.
    
    Args:
        name: The name to greet
    
    Returns:
        A greeting message
    """
    return f"Hello, {name}! Welcome to the test MCP server."


if __name__ == "__main__":
    # Run the server
    mcp.run()