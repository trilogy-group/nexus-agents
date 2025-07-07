"""Token bucket rate limiter for LLM and MCP providers."""

import asyncio
import time
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = field(init=False)
    last_refill: float = field(init=False)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    
    def __post_init__(self):
        self.tokens = float(self.capacity)
        self.last_refill = time.time()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from bucket. Blocks until tokens available."""
        while True:
            async with self.lock:
                now = time.time()
                elapsed = now - self.last_refill
                
                # Refill bucket
                self.tokens = min(
                    self.capacity,
                    self.tokens + elapsed * self.refill_rate
                )
                self.last_refill = now
                
                # Check if we have enough tokens
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
            
            # Wait before retrying
            await asyncio.sleep(0.1)
    
    async def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without blocking."""
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            
            # Refill bucket
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.refill_rate
            )
            self.last_refill = now
            
            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


class RateLimiter:
    """Rate limiter for LLM and MCP providers."""
    
    # Default rate limits (requests per minute)
    DEFAULT_LLM_RATE_LIMIT = 500
    DEFAULT_MCP_RATE_LIMIT = 60
    
    def __init__(self):
        # LLM provider limits (requests per minute)
        self.llm_limits = {
            "default": self.DEFAULT_LLM_RATE_LIMIT,
            "gpt-4o": 500,
            "gpt-4o-mini": 1000,  # Higher limit for mini model
            "o3": 100,  # Conservative for expensive model
            "o4-mini": 1000  # Assuming similar to gpt-4o-mini
        }
        
        # MCP provider limits (searches per minute)
        self.mcp_limits = {
            "default": self.DEFAULT_MCP_RATE_LIMIT,
            "perplexity": 60,
            "linkup": 60,
            "exa": 60,
            "firecrawl": 30  # More conservative for scraping
        }
        
        # Initialize token buckets
        self.llm_buckets: Dict[str, TokenBucket] = {}
        self.mcp_buckets: Dict[str, TokenBucket] = {}
        
        self._initialize_buckets()
    
    def _initialize_buckets(self):
        """Initialize token buckets for all providers."""
        # LLM buckets
        for model, limit in self.llm_limits.items():
            # Convert per-minute to per-second
            refill_rate = limit / 60.0
            self.llm_buckets[model] = TokenBucket(
                capacity=limit,
                refill_rate=refill_rate
            )
        
        # MCP buckets
        for provider, limit in self.mcp_limits.items():
            refill_rate = limit / 60.0
            self.mcp_buckets[provider] = TokenBucket(
                capacity=limit,
                refill_rate=refill_rate
            )
    
    async def acquire_llm(self, model: str, tokens: int = 1) -> bool:
        """Acquire tokens for LLM model. Blocks until available."""
        bucket_key = model if model in self.llm_buckets else "default"
        bucket = self.llm_buckets[bucket_key]
        return await bucket.acquire(tokens)
    
    async def acquire_mcp(self, provider: str, tokens: int = 1) -> bool:
        """Acquire tokens for MCP provider. Blocks until available."""
        bucket_key = provider if provider in self.mcp_buckets else "default"
        bucket = self.mcp_buckets[bucket_key]
        return await bucket.acquire(tokens)
    
    async def try_acquire_llm(self, model: str, tokens: int = 1) -> bool:
        """Try to acquire LLM tokens without blocking."""
        bucket_key = model if model in self.llm_buckets else "default"
        bucket = self.llm_buckets[bucket_key]
        return await bucket.try_acquire(tokens)
    
    async def try_acquire_mcp(self, provider: str, tokens: int = 1) -> bool:
        """Try to acquire MCP tokens without blocking."""
        bucket_key = provider if provider in self.mcp_buckets else "default"
        bucket = self.mcp_buckets[bucket_key]
        return await bucket.try_acquire(tokens)
    
    def update_llm_limit(self, model: str, limit: int):
        """Update rate limit for LLM model."""
        self.llm_limits[model] = limit
        refill_rate = limit / 60.0
        self.llm_buckets[model] = TokenBucket(
            capacity=limit,
            refill_rate=refill_rate
        )
    
    def update_mcp_limit(self, provider: str, limit: int):
        """Update rate limit for MCP provider."""
        self.mcp_limits[provider] = limit
        refill_rate = limit / 60.0
        self.mcp_buckets[provider] = TokenBucket(
            capacity=limit,
            refill_rate=refill_rate
        )
