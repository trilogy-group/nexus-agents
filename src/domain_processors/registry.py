"""Registry for domain-specific processors."""

from typing import List, Optional, Dict
import logging

from .base import DomainProcessor


logger = logging.getLogger(__name__)


class DomainProcessorRegistry:
    """Registry for managing domain-specific processors."""
    
    def __init__(self):
        self.processors: List[DomainProcessor] = []
        self._processor_map: Dict[str, DomainProcessor] = {}
    
    def register(self, processor: DomainProcessor, hint: Optional[str] = None):
        """Register a domain processor.
        
        Args:
            processor: The domain processor to register
            hint: Optional hint key for direct lookup (e.g., "education.private_schools")
        """
        self.processors.append(processor)
        
        if hint:
            self._processor_map[hint] = processor
            
        logger.info(f"Registered domain processor: {processor.__class__.__name__}")
    
    def get_processor(self, query: str) -> Optional[DomainProcessor]:
        """Get a processor that matches the query.
        
        Args:
            query: The query string to match against
            
        Returns:
            The first matching processor, or None if no match
        """
        # Check each processor
        for processor in self.processors:
            if processor.matches_domain(query):
                logger.info(f"Matched processor {processor.__class__.__name__} for query")
                return processor
        
        return None
    
    def get_processor_by_hint(self, hint: str) -> Optional[DomainProcessor]:
        """Get a processor by hint key.
        
        Args:
            hint: The hint key (e.g., "education.private_schools")
            
        Returns:
            The processor registered with this hint, or None
        """
        return self._processor_map.get(hint)
    
    def list_processors(self) -> List[str]:
        """List all registered processor names."""
        return [p.__class__.__name__ for p in self.processors]
    
    def clear(self):
        """Clear all registered processors."""
        self.processors.clear()
        self._processor_map.clear()


# Global registry instance
_global_registry = DomainProcessorRegistry()


def get_global_registry() -> DomainProcessorRegistry:
    """Get the global domain processor registry."""
    return _global_registry


def register_processor(processor: DomainProcessor, hint: Optional[str] = None):
    """Register a processor with the global registry."""
    _global_registry.register(processor, hint)
