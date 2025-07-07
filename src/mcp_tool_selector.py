"""
MCP Tool Selector - Intelligent tool selection and argument construction using LLM
"""
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolSelection:
    """Represents a selected tool with constructed arguments"""
    server_name: str
    tool_name: str
    arguments: Dict[str, Any]
    reasoning: str


class MCPToolSelector:
    """Intelligent selector for MCP tools based on query context and tool capabilities"""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    async def select_tools_for_query(
        self, 
        query: str, 
        focus_area: str, 
        available_tools: Dict[str, List[Dict[str, Any]]],
        max_tools: int = 3
    ) -> List[ToolSelection]:
        """
        Select appropriate tools and construct arguments based on query and focus area.
        
        Args:
            query: The search query
            focus_area: The focus area/context for the search
            available_tools: Dict mapping server names to their available tools
            max_tools: Maximum number of tools to select
            
        Returns:
            List of selected tools with constructed arguments
        """
        # Build tool catalog for LLM
        tool_catalog = self._build_tool_catalog(available_tools)
        
        # Create prompt for tool selection
        prompt = f"""You are an expert at selecting appropriate search tools for research queries.

Given the following research query and focus area, select the most appropriate tools and construct their arguments.

Query: {query}
Focus Area: {focus_area}

Available Tools:
{tool_catalog}

For each selected tool, provide:
1. The server name and tool name
2. The complete arguments required by the tool's schema
3. Brief reasoning for why this tool is appropriate

Guidelines:
- Only select tools that are relevant to the query and focus area
- For general web searches, prefer tools like web_search, linkup_search, perplexity_research
- For company-specific searches, use company_research_exa or competitor_finder_exa with appropriate company names extracted from the query
- For academic searches, use research_paper_search_exa
- For crawling specific websites, use crawling_exa or firecrawl_search
- Construct complete arguments based on the tool's input schema
- If a tool requires specific parameters (like companyName), extract or infer them from the query
- Select at most {max_tools} tools

Return your response as a JSON array with this structure:
[
  {{
    "server_name": "server_name",
    "tool_name": "tool_name",
    "arguments": {{"param1": "value1", "param2": "value2"}},
    "reasoning": "Brief explanation"
  }}
]

Important: 
- If the query mentions specific companies, extract company names for company-specific tools
- If the focus area suggests academic research, prioritize research paper tools
- Always include required parameters based on the tool's schema
"""

        try:
            # Get LLM response
            response = await self.llm_client.generate(
                prompt,
                temperature=0.3,  # Lower temperature for more consistent tool selection
                response_format={"type": "json_object"}
            )
            
            # Parse response
            selections_data = json.loads(response)
            if isinstance(selections_data, dict) and "selections" in selections_data:
                selections_data = selections_data["selections"]
            elif not isinstance(selections_data, list):
                selections_data = [selections_data]
            
            # Convert to ToolSelection objects
            selections = []
            for item in selections_data[:max_tools]:
                if self._validate_tool_selection(item, available_tools):
                    selections.append(ToolSelection(
                        server_name=item["server_name"],
                        tool_name=item["tool_name"],
                        arguments=item["arguments"],
                        reasoning=item.get("reasoning", "")
                    ))
            
            # Fallback to generic web search if no tools selected
            if not selections:
                selections = self._get_fallback_selections(query, available_tools)
            
            logger.info(f"Selected {len(selections)} tools for query: {query}")
            for sel in selections:
                logger.info(f"  - {sel.server_name}.{sel.tool_name}: {sel.reasoning}")
            
            return selections
            
        except Exception as e:
            logger.error(f"Error in tool selection: {e}")
            # Return fallback selections
            return self._get_fallback_selections(query, available_tools)
    
    def _build_tool_catalog(self, available_tools: Dict[str, List[Dict[str, Any]]]) -> str:
        """Build a formatted catalog of available tools for the LLM"""
        catalog_lines = []
        
        for server_name, tools in available_tools.items():
            catalog_lines.append(f"\n{server_name}:")
            for tool in tools:
                tool_name = tool.get("name", "unknown")
                description = tool.get("description", "No description")
                
                # Extract required parameters from schema
                input_schema = tool.get("inputSchema", {})
                properties = input_schema.get("properties", {})
                required = input_schema.get("required", [])
                
                params_info = []
                for param_name, param_schema in properties.items():
                    param_type = param_schema.get("type", "string")
                    param_desc = param_schema.get("description", "")
                    is_required = param_name in required
                    
                    param_info = f"{param_name} ({param_type})"
                    if is_required:
                        param_info += " [REQUIRED]"
                    if param_desc:
                        param_info += f": {param_desc}"
                    params_info.append(f"    - {param_info}")
                
                catalog_lines.append(f"  • {tool_name}: {description}")
                if params_info:
                    catalog_lines.append("    Parameters:")
                    catalog_lines.extend(params_info)
        
        return "\n".join(catalog_lines)
    
    def _validate_tool_selection(self, selection: Dict[str, Any], available_tools: Dict[str, List[Dict[str, Any]]]) -> bool:
        """Validate that a tool selection is valid"""
        server_name = selection.get("server_name")
        tool_name = selection.get("tool_name")
        arguments = selection.get("arguments", {})
        
        if not server_name or not tool_name:
            return False
        
        # Check if server exists
        if server_name not in available_tools:
            logger.warning(f"Server {server_name} not found in available tools")
            return False
        
        # Find the tool
        server_tools = available_tools[server_name]
        tool = next((t for t in server_tools if t.get("name") == tool_name), None)
        
        if not tool:
            logger.warning(f"Tool {tool_name} not found in server {server_name}")
            return False
        
        # Validate required arguments
        input_schema = tool.get("inputSchema", {})
        required = input_schema.get("required", [])
        
        for req_param in required:
            if req_param not in arguments:
                logger.warning(f"Missing required parameter {req_param} for {server_name}.{tool_name}")
                return False
        
        return True
    
    def _get_fallback_selections(self, query: str, available_tools: Dict[str, List[Dict[str, Any]]]) -> List[ToolSelection]:
        """Get fallback tool selections for generic web search"""
        selections = []
        
        # Priority order for fallback search tools
        fallback_tools = [
            ("linkup", ["linkup_search", "search"]),
            ("perplexity", ["perplexity_research", "perplexity_ask"]),
            ("exa", ["web_search_exa", "exa_search"]),
            ("firecrawl", ["firecrawl_search"])
        ]
        
        for server_name, tool_names in fallback_tools:
            if server_name in available_tools:
                server_tools = available_tools[server_name]
                for tool_name in tool_names:
                    tool = next((t for t in server_tools if t.get("name") == tool_name), None)
                    if tool:
                        # Construct basic search arguments
                        args = self._construct_basic_search_args(tool, query)
                        selections.append(ToolSelection(
                            server_name=server_name,
                            tool_name=tool_name,
                            arguments=args,
                            reasoning="Fallback general web search"
                        ))
                        break
            
            if len(selections) >= 2:  # Limit fallback selections
                break
        
        return selections
    
    def _construct_basic_search_args(self, tool: Dict[str, Any], query: str, max_results: int = 5) -> Dict[str, Any]:
        """Construct basic search arguments based on tool schema"""
        args = {}
        
        # Get tool input schema
        input_schema = tool.get("inputSchema", {}).get("properties", {})
        
        # Map query parameter
        query_params = ["query", "q", "search", "term", "prompt", "messages"]
        for param in query_params:
            if param in input_schema:
                if param == "messages":
                    # Special handling for message-based tools
                    args[param] = [{"role": "user", "content": query}]
                else:
                    args[param] = query
                break
        
        # Map max results parameter
        result_params = ["max_results", "num_results", "limit", "count", "n"]
        for param in result_params:
            if param in input_schema:
                args[param] = max_results
                break
        
        return args
