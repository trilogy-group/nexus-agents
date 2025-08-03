"""Search space enumerator for data aggregation tasks."""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json
import uuid

from src.llm import LLMClient


logger = logging.getLogger(__name__)


@dataclass
class SearchSubspace:
    """Represents a subspace of the search space."""
    id: str
    query: str
    metadata: Dict[str, Any]


class SearchSpaceEnumerator:
    """Dynamically decomposes search space using LLM with proper geographic hierarchies."""
    
    def __init__(self, llm_client: LLMClient):
        """Initialize the search space enumerator."""
        self.llm_client = llm_client
    
    async def enumerate(self, 
                       base_query: str, 
                       search_space: str) -> List[SearchSubspace]:
        """
        Enumerate search subspaces based on the base query and search space using LLM.
        
        Args:
            base_query: The base entity query (e.g., "private schools")
            search_space: The search space constraint (e.g., "in California")
            
        Returns:
            List of SearchSubspace objects
        """
        logger.info(f"Enumerating search space for '{base_query}' in '{search_space}'")
        
        # Use LLM to dynamically enumerate search space for any geography
        prompt = f"""
You are a geographic search space analyzer. Your task is to decompose the given search space into appropriate subspaces for data aggregation.

Entities to search for: {base_query}
Search space constraint: {search_space}

Instructions:
1. Focus ONLY on decomposing the search space ("{search_space}"), not on the entities
2. Determine what geographic level the search space represents (country, state, province, department, etc.)
3. Provide an exhaustive, complete enumeration of the next hierarchical level down
4. For any geographic area, enumerate ALL sub-areas at the next level (not just samples)
5. Return structured JSON with subspace definitions

Examples of proper decomposition:
- If search space is "Colombia", enumerate all departments: "Amazonas", "Antioquia", "Arauca", etc.
- If search space is "Canada", enumerate all provinces: "Ontario", "Quebec", "British Columbia", etc.
- If search space is "California", enumerate all counties: "Alameda County", "Orange County", etc.
- If search space is "United States", enumerate all states: "Alabama", "Alaska", "Arizona", etc.

Expected JSON Output Format:
{{
  "decomposition_type": "country_to_states|state_to_counties|country_to_provinces|country_to_departments|direct",
  "subspaces": [
    {{
      "id": "unique_identifier",
      "query": "{base_query} in [subspace_name]",
      "metadata": {{
        "type": "subspace_type",
        "parent": "{search_space}",
        "name": "specific_subspace_name",
        "level": "hierarchical_level"
      }}
    }},
    ...
  ]
}}

Return only the JSON object with the complete enumeration, no other text or explanations.
"""

        try:
            # Get LLM response for geographic decomposition
            response = await self.llm_client.generate(
                prompt, 
                use_reasoning_model=False
            )
            
            # Try to parse LLM response as JSON
            try:
                # Clean response - remove markdown code blocks if present
                clean_response = response.strip()
                if clean_response.startswith('```json'):
                    clean_response = clean_response[7:]  # Remove ```json
                if clean_response.startswith('```'):
                    clean_response = clean_response[3:]  # Remove ```
                if clean_response.endswith('```'):
                    clean_response = clean_response[:-3]  # Remove trailing ```
                clean_response = clean_response.strip()
                
                logger.info(f"Attempting to parse cleaned JSON response (length: {len(clean_response)})")
                logger.debug(f"First 200 chars: {clean_response[:200]}...")
                logger.debug(f"Last 200 chars: ...{clean_response[-200:]}")
                
                decomposition_result = json.loads(clean_response)
                subspaces_data = decomposition_result.get("subspaces", [])
                
                # Convert to SearchSubspace objects
                subspaces = []
                for subspace_data in subspaces_data:
                    subspace = SearchSubspace(
                        id=subspace_data["id"],
                        query=subspace_data["query"],
                        metadata=subspace_data["metadata"]
                    )
                    subspaces.append(subspace)
                
                if subspaces:
                    logger.info(f"LLM-generated geographic enumeration with {len(subspaces)} subspaces")
                    return subspaces
                    
            except (json.JSONDecodeError, KeyError) as parse_error:
                logger.warning(f"Failed to parse LLM geographic response: {parse_error}")
                logger.warning(f"LLM response was: {response}")
            
            # If LLM fails to provide proper geographic enumeration, fall back to direct search
            logger.warning("LLM geographic enumeration failed, using direct search")
            return [
                SearchSubspace(
                    id="direct_fallback",
                    query=f"{base_query} {search_space}",
                    metadata={
                        "type": "direct",
                        "query": f"{base_query} {search_space}",
                        "search_space": search_space
                    }
                )
            ]
            
        except Exception as e:
            logger.error(f"Error in LLM-based search space enumeration: {str(e)}")
            # Fallback to direct search on any error
            return [
                SearchSubspace(
                    id="error_fallback",
                    query=f"{base_query} {search_space}",
                    metadata={
                        "type": "direct",
                        "query": f"{base_query} {search_space}",
                        "error": str(e)
                    }
                )
            ]
