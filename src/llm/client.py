"""
LLM client implementation for the Nexus Agents system.

This module provides a client for interacting with various language model providers.
"""
import os
import json
import logging
import asyncio
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env file first - this should take precedence over environment variables
load_dotenv(override=True)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Enum representing the supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    XAI = "xai"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"


class LLMConfig(BaseModel):
    """Configuration for an LLM provider."""
    provider: LLMProvider
    model_name: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 1.0
    top_p: float = 1.0
    additional_params: Dict[str, Any] = Field(default_factory=dict)


class LLMClient:
    """A client for interacting with language models from various providers."""
    
    def __init__(self, 
                 reasoning_config: Optional[LLMConfig] = None, 
                 task_config: Optional[LLMConfig] = None,
                 config_path: Optional[str] = None):
        """
        Initialize the LLM client.
        
        Args:
            reasoning_config: Configuration for the reasoning model.
            task_config: Configuration for the task model.
            config_path: Path to a JSON configuration file.
        """
        self.clients = {}
        
        # Load configuration from file if provided
        if config_path and os.path.exists(config_path):
            self._load_config(config_path)
        else:
            # Use provided configurations or defaults
            self.reasoning_config = reasoning_config or self._get_default_reasoning_config()
            self.task_config = task_config or self._get_default_task_config()
        
        # Initialize the clients
        self._initialize_clients()
    
    def _load_config(self, config_path: str):
        """Load configuration from a JSON file."""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            self.reasoning_config = LLMConfig(**config.get("reasoning_model", {}))
            self.task_config = LLMConfig(**config.get("task_model", {}))
            
            logger.info(f"Loaded LLM configuration from {config_path}")
        except Exception as e:
            logger.error(f"Error loading LLM configuration from {config_path}: {e}")
            # Fall back to defaults
            self.reasoning_config = self._get_default_reasoning_config()
            self.task_config = self._get_default_task_config()
    
    def _get_default_reasoning_config(self) -> LLMConfig:
        """Get the default configuration for the reasoning model."""
        # Try to get API key from environment
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        
        if openai_api_key:
            return LLMConfig(
                provider=LLMProvider.OPENAI,
                model_name="gpt-4-turbo",
                api_key=openai_api_key,
                max_tokens=4096,
                temperature=1.0
            )
        else:
            # Fall back to Ollama if no API key is available
            return LLMConfig(
                provider=LLMProvider.OLLAMA,
                model_name="llama3",
                api_base="http://localhost:11434",
                max_tokens=4096,
                temperature=1.0
            )
    
    def _get_default_task_config(self) -> LLMConfig:
        """Get the default configuration for the task model."""
        # Try to get API key from environment
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        
        if openai_api_key:
            return LLMConfig(
                provider=LLMProvider.OPENAI,
                model_name="gpt-3.5-turbo",
                api_key=openai_api_key,
                max_tokens=2048,
                temperature=1.0
            )
        else:
            # Fall back to Ollama if no API key is available
            return LLMConfig(
                provider=LLMProvider.OLLAMA,
                model_name="mistral",
                api_base="http://localhost:11434",
                max_tokens=2048,
                temperature=1.0
            )
    
    def _get_token_param(self, model_name: str, tokens: int) -> Dict[str, int]:
        """
        Returns the correct token parameter based on the model name.
        Handles the breaking change in the OpenAI API for newer models.
        Model-specific change: o1, o3, o4 models require 'max_completion_tokens'
        while older models (GPT-3.5, GPT-4, GPT-4o) still use 'max_tokens'.
        """
        # Models that require the new 'max_completion_tokens' parameter
        new_token_models = ["o1", "o3", "o4"]
        
        if any(model_name.startswith(prefix) for prefix in new_token_models):
            return {"max_completion_tokens": tokens}
        else:
            return {"max_tokens": tokens}

    def _initialize_clients(self):
        """Initialize the LLM clients for each provider."""
        # Initialize OpenAI client if needed
        if self.reasoning_config.provider == LLMProvider.OPENAI or self.task_config.provider == LLMProvider.OPENAI:
            self._initialize_openai_client()
        
        # Initialize Anthropic client if needed
        if self.reasoning_config.provider == LLMProvider.ANTHROPIC or self.task_config.provider == LLMProvider.ANTHROPIC:
            self._initialize_anthropic_client()
        
        # Initialize Google client if needed
        if self.reasoning_config.provider == LLMProvider.GOOGLE or self.task_config.provider == LLMProvider.GOOGLE:
            self._initialize_google_client()
        
        # Initialize xAI client if needed
        if self.reasoning_config.provider == LLMProvider.XAI or self.task_config.provider == LLMProvider.XAI:
            self._initialize_xai_client()
        
        # Initialize OpenRouter client if needed
        if self.reasoning_config.provider == LLMProvider.OPENROUTER or self.task_config.provider == LLMProvider.OPENROUTER:
            self._initialize_openrouter_client()
        
        # Initialize Ollama client if needed
        if self.reasoning_config.provider == LLMProvider.OLLAMA or self.task_config.provider == LLMProvider.OLLAMA:
            self._initialize_ollama_client()
    
    def _initialize_openai_client(self):
        """Initialize the OpenAI client."""
        try:
            import openai
            
            # Get API key from config or environment
            api_key = None
            
            # Try reasoning config first
            if self.reasoning_config and self.reasoning_config.provider == LLMProvider.OPENAI and self.reasoning_config.api_key:
                api_key = self.reasoning_config.api_key
            # Try task config next
            elif self.task_config and self.task_config.provider == LLMProvider.OPENAI and self.task_config.api_key:
                api_key = self.task_config.api_key
            # Fall back to environment variable
            if not api_key:
                api_key = os.environ.get("OPENAI_API_KEY")
            
            # Get API base from config or use default
            api_base = (self.reasoning_config.api_base if self.reasoning_config.provider == LLMProvider.OPENAI else
                       self.task_config.api_base if self.task_config.provider == LLMProvider.OPENAI else
                       None)
            
            if not api_key:
                logger.error("OpenAI API key not found")
                return
            
            client = openai.AsyncOpenAI(api_key=api_key)
            if api_base:
                client.base_url = api_base
            
            self.clients[LLMProvider.OPENAI] = client
            logger.info("Initialized OpenAI client")
        except ImportError:
            logger.error("OpenAI package not installed. Please install it with 'pip install openai'")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {e}")
    
    def _initialize_anthropic_client(self):
        """Initialize the Anthropic client."""
        try:
            import anthropic
            
            # Get API key from config or environment
            api_key = None
            
            # Try reasoning config first
            if self.reasoning_config and self.reasoning_config.provider == LLMProvider.ANTHROPIC and self.reasoning_config.api_key:
                api_key = self.reasoning_config.api_key
            # Try task config next
            elif self.task_config and self.task_config.provider == LLMProvider.ANTHROPIC and self.task_config.api_key:
                api_key = self.task_config.api_key
            # Fall back to environment variable
            if not api_key:
                api_key = os.environ.get("ANTHROPIC_API_KEY")
            
            # Get API base from config or use default
            api_base = (self.reasoning_config.api_base if self.reasoning_config.provider == LLMProvider.ANTHROPIC else
                       self.task_config.api_base if self.task_config.provider == LLMProvider.ANTHROPIC else
                       None)
            
            if not api_key:
                logger.error("Anthropic API key not found")
                return
            
            client = anthropic.AsyncAnthropic(api_key=api_key)
            if api_base:
                client.base_url = api_base
            
            self.clients[LLMProvider.ANTHROPIC] = client
            logger.info("Initialized Anthropic client")
        except ImportError:
            logger.error("Anthropic package not installed. Please install it with 'pip install anthropic'")
        except Exception as e:
            logger.error(f"Error initializing Anthropic client: {e}")
    
    def _initialize_google_client(self):
        """Initialize the Google client."""
        try:
            import google.generativeai as genai
            
            # Get API key from config or environment
            api_key = None
            
            # Try reasoning config first
            if self.reasoning_config and self.reasoning_config.provider == LLMProvider.GOOGLE and self.reasoning_config.api_key:
                api_key = self.reasoning_config.api_key
            # Try task config next
            elif self.task_config and self.task_config.provider == LLMProvider.GOOGLE and self.task_config.api_key:
                api_key = self.task_config.api_key
            # Fall back to environment variable
            if not api_key:
                api_key = os.environ.get("GOOGLE_API_KEY")
            
            if not api_key:
                logger.error("Google API key not found")
                return
            
            genai.configure(api_key=api_key)
            self.clients[LLMProvider.GOOGLE] = genai
            logger.info("Initialized Google client")
        except ImportError:
            logger.error("Google Generative AI package not installed. Please install it with 'pip install google-generativeai'")
        except Exception as e:
            logger.error(f"Error initializing Google client: {e}")
    
    def _initialize_xai_client(self):
        """Initialize the xAI client."""
        try:
            import openai
            
            # Get API key from config or environment
            api_key = None
            
            # Try reasoning config first
            if self.reasoning_config and self.reasoning_config.provider == LLMProvider.XAI and self.reasoning_config.api_key:
                api_key = self.reasoning_config.api_key
            # Try task config next
            elif self.task_config and self.task_config.provider == LLMProvider.XAI and self.task_config.api_key:
                api_key = self.task_config.api_key
            # Fall back to environment variable
            if not api_key:
                api_key = os.environ.get("XAI_API_KEY")
            
            # Get API base from config or use default
            api_base = (self.reasoning_config.api_base if self.reasoning_config.provider == LLMProvider.XAI else
                       self.task_config.api_base if self.task_config.provider == LLMProvider.XAI else
                       "https://api.groq.com/openai/v1")
            
            if not api_key:
                logger.error("xAI API key not found")
                return
            
            client = openai.AsyncOpenAI(api_key=api_key, base_url=api_base)
            self.clients[LLMProvider.XAI] = client
            logger.info("Initialized xAI client")
        except ImportError:
            logger.error("OpenAI package not installed. Please install it with 'pip install openai'")
        except Exception as e:
            logger.error(f"Error initializing xAI client: {e}")
    
    def _initialize_openrouter_client(self):
        """Initialize the OpenRouter client."""
        try:
            import openai
            
            # Get API key from config or environment
            api_key = None
            
            # Try reasoning config first
            if self.reasoning_config and self.reasoning_config.provider == LLMProvider.OPENROUTER and self.reasoning_config.api_key:
                api_key = self.reasoning_config.api_key
            # Try task config next
            elif self.task_config and self.task_config.provider == LLMProvider.OPENROUTER and self.task_config.api_key:
                api_key = self.task_config.api_key
            # Fall back to environment variable
            if not api_key:
                api_key = os.environ.get("OPENROUTER_API_KEY")
            
            if not api_key:
                logger.error("OpenRouter API key not found")
                return
            
            client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1"
            )
            
            self.clients[LLMProvider.OPENROUTER] = client
            logger.info("Initialized OpenRouter client")
        except ImportError:
            logger.error("OpenAI package not installed. Please install it with 'pip install openai'")
        except Exception as e:
            logger.error(f"Error initializing OpenRouter client: {e}")
    
    def _initialize_ollama_client(self):
        """Initialize the Ollama client."""
        try:
            import aiohttp
            
            # Get API base from config or use default
            api_base = (self.reasoning_config.api_base if self.reasoning_config.provider == LLMProvider.OLLAMA else
                       self.task_config.api_base if self.task_config.provider == LLMProvider.OLLAMA else
                       "http://localhost:11434")
            
            # Create a session for Ollama
            session = aiohttp.ClientSession(base_url=api_base)
            self.clients[LLMProvider.OLLAMA] = session
            logger.info("Initialized Ollama client")
        except ImportError:
            logger.error("aiohttp package not installed. Please install it with 'pip install aiohttp'")
        except Exception as e:
            logger.error(f"Error initializing Ollama client: {e}")
    
    async def generate(self, prompt: str, use_reasoning_model: bool = True) -> str:
        """
        Generate text from a prompt.
        
        Args:
            prompt: The prompt to generate from.
            use_reasoning_model: Whether to use the reasoning model (True) or the task model (False).
            
        Returns:
            The generated text.
        """
        config = self.reasoning_config if use_reasoning_model else self.task_config
        
        try:
            if config.provider == LLMProvider.OPENAI:
                return await self._generate_openai(prompt, config)
            elif config.provider == LLMProvider.ANTHROPIC:
                return await self._generate_anthropic(prompt, config)
            elif config.provider == LLMProvider.GOOGLE:
                return await self._generate_google(prompt, config)
            elif config.provider == LLMProvider.XAI:
                return await self._generate_xai(prompt, config)
            elif config.provider == LLMProvider.OPENROUTER:
                return await self._generate_openrouter(prompt, config)
            elif config.provider == LLMProvider.OLLAMA:
                return await self._generate_ollama(prompt, config)
            else:
                logger.error(f"Unsupported provider: {config.provider}")
                return f"Error: Unsupported provider {config.provider}"
        except Exception as e:
            logger.error(f"Error generating text: {e}")
            return f"Error generating text: {str(e)}"
    
    async def _generate_openai(self, prompt: str, config: LLMConfig) -> str:
        """Generate text using OpenAI."""
        client = self.clients.get(LLMProvider.OPENAI)
        if not client:
            return "Error: OpenAI client not initialized"
        
        token_params = self._get_token_param(config.model_name, config.max_tokens)

        params = {
            "model": config.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "top_p": config.top_p,
            **token_params,
            **config.additional_params
        }
        if config.temperature is not None:
            params["temperature"] = config.temperature
        
        response = await client.chat.completions.create(**params)
        
        return response.choices[0].message.content
    
    async def _generate_anthropic(self, prompt: str, config: LLMConfig) -> str:
        """Generate text using Anthropic."""
        client = self.clients.get(LLMProvider.ANTHROPIC)
        if not client:
            return "Error: Anthropic client not initialized"
        
        response = await client.messages.create(
            model=config.model_name,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            messages=[{"role": "user", "content": prompt}],
            **config.additional_params
        )
        
        return response.content[0].text
    
    async def _generate_google(self, prompt: str, config: LLMConfig) -> str:
        """Generate text using Google."""
        genai = self.clients.get(LLMProvider.GOOGLE)
        if not genai:
            return "Error: Google client not initialized"
        
        model = genai.GenerativeModel(config.model_name)
        response = await asyncio.to_thread(
            model.generate_content,
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=config.temperature,
                top_p=config.top_p,
                max_output_tokens=config.max_tokens,
                **config.additional_params
            )
        )
        
        return response.text
    
    async def _generate_xai(self, prompt: str, config: LLMConfig) -> str:
        """Generate text using xAI."""
        client = self.clients.get(LLMProvider.XAI)
        if not client:
            return "Error: xAI client not initialized"
        
        token_params = self._get_token_param(config.model_name, config.max_tokens)

        params = {
            "model": config.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "top_p": config.top_p,
            **token_params,
            **config.additional_params
        }
        if config.temperature is not None:
            params["temperature"] = config.temperature
        
        response = await client.chat.completions.create(**params)
        
        return response.choices[0].message.content
    
    async def _generate_openrouter(self, prompt: str, config: LLMConfig) -> str:
        """Generate text using OpenRouter."""
        client = self.clients.get(LLMProvider.OPENROUTER)
        if not client:
            return "Error: OpenRouter client not initialized"
        
        token_params = self._get_token_param(config.model_name, config.max_tokens)

        params = {
            "model": config.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "top_p": config.top_p,
            **token_params,
            **config.additional_params
        }
        if config.temperature is not None:
            params["temperature"] = config.temperature
        
        response = await client.chat.completions.create(**params)
        
        return response.choices[0].message.content
    
    async def _generate_ollama(self, prompt: str, config: LLMConfig) -> str:
        """Generate text using Ollama."""
        session = self.clients.get(LLMProvider.OLLAMA)
        if not session:
            return "Error: Ollama client not initialized"
        
        try:
            async with session.post(
                "/api/generate",
                json={
                    "model": config.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": config.temperature,
                        "top_p": config.top_p,
                        "num_predict": config.max_tokens,
                        **config.additional_params
                    }
                }
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return f"Error from Ollama: {error_text}"
                
                result = await response.json()
                return result.get("response", "")
        except Exception as e:
            return f"Error with Ollama request: {str(e)}"
    
    async def close(self):
        """Close all clients."""
        for provider, client in self.clients.items():
            try:
                if provider == LLMProvider.OLLAMA:
                    await client.close()
            except Exception as e:
                logger.error(f"Error closing {provider} client: {e}")