"""
Test the LLM client.
"""
import asyncio
import os
import sys
import json
from dotenv import load_dotenv

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm import LLMClient, LLMConfig, LLMProvider

# Load environment variables
load_dotenv()


async def test_openai():
    """Test the OpenAI client."""
    config = LLMConfig(
        provider=LLMProvider.OPENAI,
        model_name="gpt-3.5-turbo",
        api_key=os.environ.get("OPENAI_API_KEY"),
        max_tokens=100,
        temperature=0.7
    )
    
    client = LLMClient(reasoning_config=config, task_config=config)
    
    try:
        response = await client.generate("Hello, world!")
        print(f"OpenAI response: {response}")
    except Exception as e:
        print(f"Error with OpenAI: {e}")
    finally:
        await client.close()


async def test_anthropic():
    """Test the Anthropic client."""
    config = LLMConfig(
        provider=LLMProvider.ANTHROPIC,
        model_name="claude-3-haiku-20240307",
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        max_tokens=100,
        temperature=0.7
    )
    
    client = LLMClient(reasoning_config=config, task_config=config)
    
    try:
        response = await client.generate("Hello, world!")
        print(f"Anthropic response: {response}")
    except Exception as e:
        print(f"Error with Anthropic: {e}")
    finally:
        await client.close()


async def test_ollama():
    """Test the Ollama client."""
    config = LLMConfig(
        provider=LLMProvider.OLLAMA,
        model_name="llama3",
        api_base="http://localhost:11434",
        max_tokens=100,
        temperature=0.7
    )
    
    client = LLMClient(reasoning_config=config, task_config=config)
    
    try:
        response = await client.generate("Hello, world!")
        print(f"Ollama response: {response}")
    except Exception as e:
        print(f"Error with Ollama: {e}")
    finally:
        await client.close()


async def test_config_file():
    """Test loading from a config file."""
    # Create a temporary config file
    config = {
        "reasoning_model": {
            "provider": "openai",
            "model_name": "gpt-3.5-turbo",
            "max_tokens": 100,
            "temperature": 0.7
        },
        "task_model": {
            "provider": "openai",
            "model_name": "gpt-3.5-turbo",
            "max_tokens": 50,
            "temperature": 0.5
        }
    }
    
    with open("test_config.json", "w") as f:
        json.dump(config, f)
    
    client = LLMClient(config_path="test_config.json")
    
    try:
        # Test reasoning model
        response = await client.generate("Hello from reasoning model!", use_reasoning_model=True)
        print(f"Reasoning model response: {response}")
        
        # Test task model
        response = await client.generate("Hello from task model!", use_reasoning_model=False)
        print(f"Task model response: {response}")
    except Exception as e:
        print(f"Error with config file: {e}")
    finally:
        await client.close()
        os.remove("test_config.json")


async def main():
    """Run the tests."""
    # Test OpenAI if API key is available
    if os.environ.get("OPENAI_API_KEY"):
        print("Testing OpenAI...")
        await test_openai()
    else:
        print("Skipping OpenAI test (no API key)")
    
    # Test Anthropic if API key is available
    if os.environ.get("ANTHROPIC_API_KEY"):
        print("\nTesting Anthropic...")
        await test_anthropic()
    else:
        print("\nSkipping Anthropic test (no API key)")
    
    # Test Ollama if it's running
    print("\nTesting Ollama...")
    await test_ollama()
    
    # Test config file
    if os.environ.get("OPENAI_API_KEY"):
        print("\nTesting config file...")
        await test_config_file()
    else:
        print("\nSkipping config file test (no OpenAI API key)")


if __name__ == "__main__":
    asyncio.run(main())