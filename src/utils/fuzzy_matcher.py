


"""
Fuzzy matching utilities for entity deduplication.

This module provides fuzzy matching capabilities to identify and group similar entities
across different research tasks within a project.
"""

import logging
import re
from typing import List, Dict, Any, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class FuzzyMatcher:
    """Utility class for fuzzy entity matching and deduplication."""
    
    def __init__(self, similarity_threshold: float = 0.8):
        """Initialize the fuzzy matcher with a similarity threshold."""
        self.similarity_threshold = similarity_threshold
    
    async def group_similar_entities(self, entities: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Group similar entities based on fuzzy matching of their names and attributes.
        
        Args:
            entities: List of entities to group
            
        Returns:
            List of groups of similar entities
        """
        if not entities:
            return []
        
        # Create groups
        groups = []
        used_entities = set()
        
        for i, entity in enumerate(entities):
            if i in used_entities:
                continue
            
            # Get entity data
            entity_data = self._get_entity_data(entity)
            entity_name = entity_data.get('name', '').lower()
            
            # Create a new group with this entity
            current_group = [entity]
            used_entities.add(i)
            
            # Compare with remaining entities
            for j, other_entity in enumerate(entities):
                if j in used_entities or j <= i:
                    continue
                
                # Get other entity data
                other_entity_data = self._get_entity_data(other_entity)
                other_name = other_entity_data.get('name', '').lower()
                
                # Check if names are similar
                if self._is_similar(entity_name, other_name):
                    current_group.append(other_entity)
                    used_entities.add(j)
            
            groups.append(current_group)
        
        return groups
    
    def _get_entity_data(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Extract entity data from entity dictionary."""
        entity_data = entity.get('entity_data', {})
        if isinstance(entity_data, str):
            try:
                import json
                entity_data = json.loads(entity_data)
            except json.JSONDecodeError:
                entity_data = {}
        return entity_data
    
    def _is_similar(self, str1: str, str2: str) -> bool:
        """
        Check if two strings are similar based on the similarity threshold.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            True if strings are similar, False otherwise
        """
        if not str1 or not str2:
            return False
        
        # Normalize strings (remove extra whitespace, punctuation, etc.)
        normalized_str1 = self._normalize_string(str1)
        normalized_str2 = self._normalize_string(str2)
        
        # Calculate similarity ratio
        similarity = SequenceMatcher(None, normalized_str1, normalized_str2).ratio()
        
        return similarity >= self.similarity_threshold
    
    def _normalize_string(self, s: str) -> str:
        """
        Normalize a string for comparison.
        
        Args:
            s: String to normalize
            
        Returns:
            Normalized string
        """
        # Convert to lowercase
        s = s.lower()
        
        # Remove extra whitespace
        s = re.sub(r'\s+', ' ', s.strip())
        
        # Remove common punctuation
        s = re.sub(r'[^\w\s]', '', s)
        
        return s



