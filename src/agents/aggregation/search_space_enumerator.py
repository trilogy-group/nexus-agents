"""Search space enumerator for data aggregation tasks."""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from src.llm import LLMClient


logger = logging.getLogger(__name__)


@dataclass
class SearchSubspace:
    """Represents a subspace of the search space."""
    id: str
    query: str
    metadata: Dict[str, Any]


class SearchSpaceEnumerator:
    """Dynamically decomposes search space using LLM."""
    
    def __init__(self, llm_client: LLMClient):
        """Initialize the search space enumerator."""
        self.llm_client = llm_client
    
    async def enumerate(self, 
                       base_query: str, 
                       search_space: str) -> List[SearchSubspace]:
        """
        Enumerate search subspaces based on the base query and search space.
        
        Args:
            base_query: The base entity query (e.g., "private schools")
            search_space: The search space constraint (e.g., "in the US")
            
        Returns:
            List of SearchSubspace objects
        """
        logger.info(f"Enumerating search space for '{base_query}' {search_space}")
        
        # Ask LLM to determine appropriate decomposition
        prompt = f"""
Analyze this data aggregation task and determine the appropriate search space decomposition:
Query: {base_query}
Search Space: {search_space}

Consider:
1. Expected number of entities
2. Geographic/categorical divisions
3. Search provider limitations

Recommend decomposition strategy and provide specific sub-queries:
"""
        
        try:
            response = await self.llm_client.generate(prompt, use_reasoning_model=False)
            
            # For now, we'll implement a simple decomposition strategy
            # In a real implementation, this would parse the LLM response
            # and create appropriate subspaces
            
            # Simple strategy: if search space mentions "US" or "United States",
            # decompose by states
            if any(keyword in search_space.lower() for keyword in ["us", "united states", "usa"]):
                subspaces = await self._decompose_by_states(base_query, search_space)
            else:
                # Direct search for smaller search spaces
                subspaces = [
                    SearchSubspace(
                        id="direct",
                        query=f"{base_query} {search_space}",
                        metadata={
                            "type": "direct",
                            "query": f"{base_query} {search_space}"
                        }
                    )
                ]
            
            logger.info(f"Enumerated {len(subspaces)} search subspaces")
            return subspaces
            
        except Exception as e:
            logger.error(f"Error enumerating search space: {str(e)}")
            # Fallback to direct search
            return [
                SearchSubspace(
                    id="fallback",
                    query=f"{base_query} {search_space}",
                    metadata={
                        "type": "direct",
                        "query": f"{base_query} {search_space}",
                        "error": str(e)
                    }
                )
            ]
    
    async def _decompose_by_states(self, base_query: str, search_space: str) -> List[SearchSubspace]:
        """Decompose search space by US states."""
        # Common US states for data aggregation tasks
        us_states = [
            "California", "Texas", "Florida", "New York", "Pennsylvania",
            "Illinois", "Ohio", "Georgia", "North Carolina", "Michigan",
            "New Jersey", "Virginia", "Washington", "Arizona", "Massachusetts",
            "Tennessee", "Indiana", "Missouri", "Maryland", "Wisconsin",
            "Colorado", "Minnesota", "South Carolina", "Alabama", "Louisiana",
            "Kentucky", "Oregon", "Oklahoma", "Connecticut", "Utah"
        ]
        
        subspaces = []
        import uuid
        
        for state in us_states:
            # Replace general US references with specific state
            state_search_space = search_space.lower().replace("us", state).replace("united states", state).replace("usa", state)
            query = f"{base_query} {state_search_space}"
            
            subspaces.append(
                SearchSubspace(
                    id=f"state_{uuid.uuid4().hex[:8]}",
                    query=query,
                    metadata={
                        "type": "state",
                        "state": state,
                        "query": query
                    }
                )
            )
        
        return subspaces
    
    async def _decompose_by_regions(self, base_query: str, search_space: str) -> List[SearchSubspace]:
        """Decompose search space by regions."""
        # This would be implemented with regional decomposition logic
        # For now, we'll return a simple regional decomposition
        regions = ["Northeast", "Southeast", "Midwest", "Southwest", "West"]
        
        subspaces = []
        import uuid
        
        for region in regions:
            query = f"{base_query} in the {region} region of {search_space}"
            subspaces.append(
                SearchSubspace(
                    id=f"region_{uuid.uuid4().hex[:8]}",
                    query=query,
                    metadata={
                        "type": "region",
                        "region": region,
                        "query": query
                    }
                )
            )
        
        return subspaces
