"""Entity resolver for data aggregation tasks."""

import logging
from typing import List, Dict, Any, Optional
from collections import defaultdict

from src.llm import LLMClient
from src.domain_processors.registry import get_global_registry


logger = logging.getLogger(__name__)


class EntityResolver:
    """Merge partial entity data from multiple sources."""
    
    def __init__(self, llm_client: LLMClient):
        """Initialize the entity resolver."""
        self.llm_client = llm_client
        self.domain_registry = get_global_registry()
        
    async def resolve_entities(self, 
                              entities: List[Dict[str, Any]],
                              domain_hint: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Resolve duplicates and merge complementary data.
        
        Args:
            entities: List of entity data to resolve
            domain_hint: Optional domain hint for specialized processing
            
        Returns:
            List of resolved entities
        """
        logger.info(f"Resolving {len(entities)} entities with domain hint: {domain_hint}")
        
        # Check for domain-specific resolver
        processor = None
        if domain_hint:
            processor = self.domain_registry.get_processor_by_hint(domain_hint)
            
        resolved_entities = []
        if processor and hasattr(processor, 'resolve_entities'):
            # Use domain-specific resolution
            logger.info(f"Using domain-specific resolver for {domain_hint}")
            resolved_entities = await processor.resolve_entities(entities)
        else:
            # Use general-purpose resolution
            logger.info("Using general-purpose entity resolution")
            resolved_entities = await self._general_resolution(entities)
        
        # Add unique identifiers to resolved entities if a domain processor is available
        if domain_hint and resolved_entities:
            processor = self.domain_registry.get_processor_by_hint(domain_hint)
            if processor:
                unique_id_field = processor.get_unique_identifier_field()
                if unique_id_field:
                    for entity in resolved_entities:
                        if "attributes" in entity:
                            unique_identifier = entity["attributes"].get(unique_id_field)
                            entity["unique_identifier"] = unique_identifier
        
        return resolved_entities
            
    async def _general_resolution(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        General entity resolution using name-based matching.
        
        Args:
            entities: List of entity data to resolve
            
        Returns:
            List of resolved entities
        """
        if not entities:
            return []
        
        # Group entities by name for potential merging
        by_name = defaultdict(list)
        
        for entity in entities:
            name = entity.get("name", "").strip().lower()
            if name:
                by_name[name].append(entity)
        
        # Merge entities with the same name
        resolved = []
        for name, group in by_name.items():
            if len(group) == 1:
                resolved.append(group[0])
            else:
                # Merge multiple entities with the same name
                merged = self._merge_by_name(group)
                resolved.append(merged)
        
        logger.info(f"Resolved to {len(resolved)} unique entities")
        return resolved
    
    def _merge_by_name(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple entities with the same name.
        
        Args:
            entities: List of entities with the same name
            
        Returns:
            Merged entity
        """
        if not entities:
            return {}
        
        # Start with the first entity
        merged = entities[0].copy()
        merged_attributes = merged.get("attributes", {}).copy()
        
        # Merge attributes from all entities
        for entity in entities[1:]:
            entity_attributes = entity.get("attributes", {})
            for key, value in entity_attributes.items():
                # If the attribute is missing in merged or is empty, take it from entity
                if not merged_attributes.get(key) and value:
                    merged_attributes[key] = value
                # If we have a better (more complete) value, use it
                elif value and len(str(value)) > len(str(merged_attributes.get(key, ""))):
                    merged_attributes[key] = value
        
        merged["attributes"] = merged_attributes
        
        # Calculate average confidence
        confidences = [entity.get("confidence", 0.0) for entity in entities]
        merged["confidence"] = sum(confidences) / len(confidences) if confidences else 0.0
        
        return merged
    
    async def _cluster_similar_entities(self, entities: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Cluster similar entities using LLM-based matching.
        
        Args:
            entities: List of entities to cluster
            
        Returns:
            List of entity clusters
        """
        # This would be implemented with LLM-based similarity matching
        # For now, we'll just group by name as a simple clustering approach
        by_name = defaultdict(list)
        
        for entity in entities:
            name = entity.get("name", "").strip().lower()
            if name:
                by_name[name].append(entity)
        
        return list(by_name.values())
    
    async def _merge_cluster(self, cluster: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge a cluster of similar entities.
        
        Args:
            cluster: List of similar entities
            
        Returns:
            Merged entity
        """
        # For now, we'll just merge by name
        return self._merge_by_name(cluster)
