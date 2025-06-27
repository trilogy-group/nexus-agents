"""
Configuration for search providers in the Nexus Agents system.
"""
import os
import json
from typing import Dict, Any, Optional


class SearchProviderConfig:
    """
    Configuration for a search provider.
    """
    
    def __init__(self, name: str, api_key: str, url: str, enabled: bool = True):
        """
        Initialize the search provider configuration.
        
        Args:
            name: The name of the search provider.
            api_key: The API key for the search provider.
            url: The URL of the search provider's MCP server.
            enabled: Whether the search provider is enabled.
        """
        self.name = name
        self.api_key = api_key
        self.url = url
        self.enabled = enabled
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the configuration to a dictionary."""
        return {
            "name": self.name,
            "api_key": self.api_key,
            "url": self.url,
            "enabled": self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchProviderConfig':
        """Create a configuration from a dictionary."""
        return cls(
            name=data["name"],
            api_key=data["api_key"],
            url=data["url"],
            enabled=data.get("enabled", True)
        )


class SearchProvidersConfig:
    """
    Configuration for all search providers.
    """
    
    def __init__(self, providers: Dict[str, SearchProviderConfig] = None):
        """
        Initialize the search providers configuration.
        
        Args:
            providers: A dictionary of search provider configurations.
        """
        self.providers = providers or {}
    
    def add_provider(self, provider: SearchProviderConfig):
        """
        Add a search provider configuration.
        
        Args:
            provider: The search provider configuration to add.
        """
        self.providers[provider.name] = provider
    
    def get_provider(self, name: str) -> Optional[SearchProviderConfig]:
        """
        Get a search provider configuration by name.
        
        Args:
            name: The name of the search provider.
            
        Returns:
            The search provider configuration, or None if not found.
        """
        return self.providers.get(name)
    
    def get_enabled_providers(self) -> Dict[str, SearchProviderConfig]:
        """
        Get all enabled search provider configurations.
        
        Returns:
            A dictionary of enabled search provider configurations.
        """
        return {name: provider for name, provider in self.providers.items() if provider.enabled}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the configuration to a dictionary."""
        return {
            "providers": {name: provider.to_dict() for name, provider in self.providers.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchProvidersConfig':
        """Create a configuration from a dictionary."""
        providers = {}
        for name, provider_data in data.get("providers", {}).items():
            providers[name] = SearchProviderConfig.from_dict(provider_data)
        return cls(providers=providers)
    
    def save(self, path: str):
        """
        Save the configuration to a file.
        
        Args:
            path: The path to save the configuration to.
        """
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: str) -> 'SearchProvidersConfig':
        """
        Load the configuration from a file.
        
        Args:
            path: The path to load the configuration from.
            
        Returns:
            The loaded configuration.
        """
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    @classmethod
    def from_env(cls) -> 'SearchProvidersConfig':
        """
        Create a configuration from environment variables.
        
        Returns:
            The created configuration.
        """
        providers = {}
        
        # LinkUp
        linkup_api_key = os.environ.get("LINKUP_API_KEY")
        linkup_url = os.environ.get("LINKUP_URL", "https://api.linkup.ai/mcp")
        linkup_enabled = os.environ.get("LINKUP_ENABLED", "true").lower() == "true"
        
        if linkup_api_key:
            providers["linkup"] = SearchProviderConfig(
                name="linkup",
                api_key=linkup_api_key,
                url=linkup_url,
                enabled=linkup_enabled
            )
        
        # Exa
        exa_api_key = os.environ.get("EXA_API_KEY")
        exa_url = os.environ.get("EXA_URL", "https://api.exa.ai/mcp")
        exa_enabled = os.environ.get("EXA_ENABLED", "true").lower() == "true"
        
        if exa_api_key:
            providers["exa"] = SearchProviderConfig(
                name="exa",
                api_key=exa_api_key,
                url=exa_url,
                enabled=exa_enabled
            )
        
        # Perplexity
        perplexity_api_key = os.environ.get("PERPLEXITY_API_KEY")
        perplexity_url = os.environ.get("PERPLEXITY_URL", "https://api.perplexity.ai/mcp")
        perplexity_enabled = os.environ.get("PERPLEXITY_ENABLED", "true").lower() == "true"
        
        if perplexity_api_key:
            providers["perplexity"] = SearchProviderConfig(
                name="perplexity",
                api_key=perplexity_api_key,
                url=perplexity_url,
                enabled=perplexity_enabled
            )
        
        # Firecrawl
        firecrawl_api_key = os.environ.get("FIRECRAWL_API_KEY")
        firecrawl_url = os.environ.get("FIRECRAWL_URL", "https://api.firecrawl.dev/mcp")
        firecrawl_enabled = os.environ.get("FIRECRAWL_ENABLED", "true").lower() == "true"
        
        if firecrawl_api_key:
            providers["firecrawl"] = SearchProviderConfig(
                name="firecrawl",
                api_key=firecrawl_api_key,
                url=firecrawl_url,
                enabled=firecrawl_enabled
            )
        
        return cls(providers=providers)