#!/usr/bin/env python3
"""
Simplified real research workflow test that bypasses complex agent infrastructure
and focuses on testing the core research pipeline with live API calls.
"""

import asyncio
import os
import sys
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file first
load_dotenv(override=True)

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.llm import LLMClient, LLMConfig, LLMProvider
from src.mcp_client import MCPClient


async def test_simplified_research_workflow(verbose=False):
    """Test core research workflow components with live API calls."""
    print("🔬 Testing SIMPLIFIED Real Research Workflow...")
    print("=" * 60)
    
    # Check if we have the necessary API keys
    required_keys = {
        'OPENAI_API_KEY': 'OpenAI LLM',
        'FIRECRAWL_API_KEY': 'Firecrawl scraping',
        'EXA_API_KEY': 'Exa search'
    }
    
    missing_keys = []
    for key, description in required_keys.items():
        if not os.getenv(key):
            missing_keys.append(f"{key} (for {description})")
    
    if missing_keys:
        print("❌ Missing required API keys:")
        for key in missing_keys:
            print(f"   - {key}")
        print("\n💡 Set these in your .env file for real testing")
        return False
    
    print("✅ All required API keys found - performing real research!")
    
    try:
        # Step 1: Initialize LLM Client
        print("\n🧠 1. Initializing LLM Client...")
        llm_config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4",
            api_key=os.getenv("OPENAI_API_KEY")
        )
        llm_client = LLMClient(reasoning_config=llm_config, task_config=llm_config)
        print("✅ LLM Client initialized")
        
        # Step 2: Initialize MCP Client  
        print("\n🔗 2. Initializing MCP Client...")
        mcp_client = MCPClient()
        print("✅ MCP Client initialized")
        
        # Step 3: Test Topic Decomposition
        print("\n📋 3. Testing Topic Decomposition...")
        research_query = "What are the key benefits and challenges of renewable energy adoption in 2024?"
        decomposition = await test_topic_decomposition(llm_client, research_query, verbose)
        if not decomposition:
            return False
        
        # Step 4: Test Research Search
        print("\n🔍 4. Testing Research Search...")
        search_results = await test_research_search(mcp_client, research_query, verbose)
        if not search_results:
            return False
        
        # Step 5: Test Content Analysis
        print("\n🧠 5. Testing Content Analysis...")
        analysis = await test_content_analysis(llm_client, search_results, research_query, verbose)
        if not analysis:
            return False
        
        # Step 6: Test Final Synthesis
        print("\n📝 6. Testing Final Synthesis...")
        final_report = await test_final_synthesis(llm_client, research_query, decomposition, search_results, analysis, verbose)
        if not final_report:
            return False
        
        # Success Summary
        print("\n" + "=" * 60)
        print("🎉 SIMPLIFIED RESEARCH WORKFLOW: SUCCESS!")
        print("=" * 60)
        print("✅ Topic decomposition: Working with real LLM")
        print("✅ Research search: Working with live MCP servers")
        print("✅ Content analysis: Working with real LLM")
        print("✅ Final synthesis: Working with real LLM")
        print("✅ End-to-end pipeline: Fully functional")
        print(f"📊 Final report length: {len(final_report)} characters")
        
        if verbose:
            print(f"\n📄 Full Final Report ({len(final_report)} chars):\n{final_report}")
        else:
            print(f"\n📄 Final Report Preview:")
            print("-" * 40)
            preview = final_report[:500] + "..." if len(final_report) > 500 else final_report
            print(preview)
            print("-" * 40)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Simplified research workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_topic_decomposition(llm_client, research_query, verbose):
    """Test topic decomposition with real LLM."""
    try:
        print("   🧠 Requesting topic decomposition...")
        
        prompt = f"""
        Decompose this research query into a structured breakdown:
        
        Query: {research_query}
        
        Provide a JSON response with:
        - main_topic: The primary research focus
        - subtopics: List of 3-5 key subtopics to investigate
        - research_questions: Specific questions for each subtopic
        
        Return only valid JSON.
        """
        
        response = await llm_client.generate(
            prompt=prompt,
            use_reasoning_model=True
        )
        
        if response and len(response) > 100:
            print(f"   ✅ Decomposition successful ({len(response)} chars)")
            if verbose:
                print(f"   📋 Decomposition ({len(response)} chars): {response[:300]}...")
            else:
                print(f"   📊 Generated {len(response)} chars of structured research plan")
            return response
        else:
            print("   ❌ Insufficient decomposition content")
            return None
            
    except Exception as e:
        print(f"   ❌ Decomposition error: {e}")
        return None


async def test_research_search(mcp_client, research_query, verbose):
    """Test research search with live MCP servers."""
    try:
        print("   🔍 Performing searches...")
        
        search_results = {}
        
        # Test Exa search
        print("   🌐 Testing Exa search...")
        try:
            exa_result = await mcp_client.call_tool(
                "exa",
                "npx exa-mcp-server",
                "web_search_exa",
                {"query": research_query, "num_results": 5},
                {'EXA_API_KEY': os.getenv('EXA_API_KEY')}
            )
            if exa_result and 'content' in str(exa_result):
                search_results['exa'] = exa_result
                print(f"   ✅ Exa search successful")
                if verbose:
                    print(f"   📄 Content preview: {str(exa_result)[:200]}...")
                else:
                    print(f"   📊 Retrieved {len(str(exa_result))} characters")
            else:
                print(f"   ⚠️  Exa search returned: {str(exa_result)[:100] if exa_result else 'None'}...")
        except Exception as e:
            print(f"   ⚠️  Exa search error: {e}")
        
        # Test Firecrawl scraping
        print("   📄 Testing Firecrawl scraping...")
        try:
            firecrawl_result = await mcp_client.call_tool(
                "firecrawl",
                "npx -y firecrawl-mcp",
                "firecrawl_scrape",
                {
                    "url": "https://en.wikipedia.org/wiki/Renewable_energy",
                    "formats": ["markdown"]
                },
                {'FIRECRAWL_API_KEY': os.getenv('FIRECRAWL_API_KEY')}
            )
            if firecrawl_result and 'content' in str(firecrawl_result):
                search_results['firecrawl'] = firecrawl_result
                print(f"   ✅ Firecrawl scraping successful")
                if verbose:
                    print(f"   📄 Content preview: {str(firecrawl_result)[:200]}...")
                else:
                    print(f"   📊 Retrieved {len(str(firecrawl_result))} characters")
            else:
                print(f"   ⚠️  Firecrawl returned: {str(firecrawl_result)[:100] if firecrawl_result else 'None'}...")
        except Exception as e:
            print(f"   ⚠️  Firecrawl error: {e}")
        
        # Test Perplexity research
        print("   🔮 Testing Perplexity research...")
        try:
            perplexity_result = await mcp_client.call_tool(
                "perplexity",
                "npx mcp-server-perplexity-ask",
                "perplexity_research",
                {
                    "messages": [
                        {"role": "user", "content": research_query}
                    ]
                },
                {'PERPLEXITY_API_KEY': os.getenv('PERPLEXITY_API_KEY')}
            )
            if perplexity_result and 'content' in str(perplexity_result):
                search_results['perplexity'] = perplexity_result
                print(f"   ✅ Perplexity research successful")
                if verbose:
                    print(f"   📄 Content preview: {str(perplexity_result)[:200]}...")
                else:
                    print(f"   📊 Retrieved {len(str(perplexity_result))} characters")
            else:
                print(f"   ⚠️  Perplexity returned: {str(perplexity_result)[:100] if perplexity_result else 'None'}...")
        except Exception as e:
            print(f"   ⚠️  Perplexity error: {e}")
        
        if search_results:
            total_content = sum(len(str(result)) for result in search_results.values())
            print(f"   📊 Total content: {total_content} characters from {len(search_results)} sources")
            return search_results
        else:
            print("   ❌ No search results obtained")
            return None
            
    except Exception as e:
        print(f"   ❌ Research search error: {e}")
        return None


async def test_content_analysis(llm_client, search_results, research_query, verbose):
    """Test content analysis with real LLM."""
    try:
        print("   🔬 Analyzing content...")
        
        # Prepare content for analysis
        content_summary = f"Research Query: {research_query}\n\n"
        for provider, result in search_results.items():
            content_summary += f"--- {provider.upper()} DATA ---\n"
            result_text = str(result)
            if len(result_text) > 1500:
                content_summary += result_text[:1500] + "...\n\n"
            else:
                content_summary += result_text + "\n\n"
        
        analysis_prompt = f"""
        Analyze the following research data and extract key insights:
        
        {content_summary}
        
        Provide a structured analysis including:
        1. Key benefits identified
        2. Main challenges identified
        3. Supporting evidence
        4. Data quality assessment
        
        Be comprehensive but concise.
        """
        
        analysis = await llm_client.generate(
            prompt=analysis_prompt,
            use_reasoning_model=True
        )
        
        if analysis and len(analysis) > 200:
            print("   ✅ Content analysis successful")
            if verbose:
                print(f"   🔬 Analysis ({len(analysis)} chars): {analysis[:300]}...")
            else:
                print(f"   📊 Generated {len(analysis)} chars of analysis")
            return analysis
        else:
            print("   ❌ Insufficient analysis content")
            return None
            
    except Exception as e:
        print(f"   ❌ Content analysis error: {e}")
        return None


async def test_final_synthesis(llm_client, research_query, decomposition, search_results, analysis, verbose):
    """Test final synthesis with real LLM."""
    try:
        print("   📝 Generating final synthesis...")
        
        synthesis_prompt = f"""
        Create a comprehensive research report based on the following:
        
        Original Query: {research_query}
        
        Topic Decomposition: {str(decomposition)[:800]}...
        
        Content Analysis: {str(analysis)[:1000]}...
        
        Data Sources: {len(search_results)} providers
        
        Create a well-structured report with:
        1. Executive Summary
        2. Key Findings
        3. Benefits and Challenges
        4. Conclusions and Recommendations
        5. Methodology Notes
        
        Make it professional and comprehensive (minimum 1000 words).
        """
        
        synthesis = await llm_client.generate(
            prompt=synthesis_prompt,
            use_reasoning_model=True
        )
        
        if synthesis and len(synthesis) > 500:
            print("   ✅ Final synthesis successful")
            if verbose:
                print(f"   📝 Full report ({len(synthesis)} chars):\n{synthesis}")
            else:
                print(f"   📊 Generated comprehensive report ({len(synthesis)} chars)")
                # Show preview even in non-verbose mode
                print(f"\n📄 Final Report Preview:")
                print("-" * 40)
                preview = synthesis[:500] + "..." if len(synthesis) > 500 else synthesis
                print(preview)
                print("-" * 40)
            return synthesis
        else:
            print("   ❌ Insufficient synthesis content")
            return None
            
    except Exception as e:
        print(f"   ❌ Final synthesis error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description='Test simplified real research workflow with live APIs and LLM reasoning')
    parser.add_argument('-v', '--verbose', action='store_true', 
                       help='Show detailed output including full content previews and complete report')
    args = parser.parse_args()
    
    success = asyncio.run(test_simplified_research_workflow(verbose=args.verbose))
    
    if success:
        print(f"\n🎉 Simplified research workflow test: {'DETAILED ' if args.verbose else ''}SUCCESS!")
        sys.exit(0)
    else:
        print(f"\n❌ Simplified research workflow test: FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()
