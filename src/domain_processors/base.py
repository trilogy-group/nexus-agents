"""Base class for domain-specific processors."""

from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional

from ..orchestration.task_types import Task


class DomainProcessor(ABC):
    """Base class for domain-specific processors."""
    
    @abstractmethod
    def matches_domain(self, query: str) -> bool:
        """Check if this processor handles the query."""
        pass
    
    @abstractmethod
    async def process(self, task: Task) -> Any:
        """Domain-specific processing logic."""
        pass
    
    async def extract_entities(self, 
                              content: str, 
                              attributes: List[str]) -> List[Dict[str, Any]]:
        """Extract entities with domain-specific knowledge.
        
        Override this method in subclasses for domain-specific extraction.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement extract_entities"
        )
    
    async def resolve_entities(self, 
                              entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Resolve entity duplicates with domain-specific logic.
        
        Override this method in subclasses for domain-specific resolution.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement resolve_entities"
        )
    
    def get_specialized_sources(self) -> Dict[str, str]:
        """Get domain-specific data sources.
        
        Override this method to provide specialized sources.
        """
        return {}
    
    def get_unique_identifier_field(self) -> Optional[str]:
        """Get the field name used as unique identifier for this domain.
        
        Override this method to specify domain-specific unique ID.
        """
        return None
