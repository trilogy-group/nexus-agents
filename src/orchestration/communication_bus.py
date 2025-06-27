"""
Communication Bus for the Nexus Agents system.

This module provides a message-passing system that enables communication between agents.
It implements a pub-sub messaging system using Redis.
"""
import json
import asyncio
from typing import Any, Callable, Dict, List, Optional
import redis.asyncio as redis
from pydantic import BaseModel


class Message(BaseModel):
    """Model representing a message in the communication bus."""
    sender: str
    recipient: Optional[str] = None
    topic: str
    content: Dict[str, Any]
    message_id: str
    reply_to: Optional[str] = None
    conversation_id: Optional[str] = None


class CommunicationBus:
    """
    The Communication Bus is a message-passing system that enables communication between agents.
    It implements a pub-sub messaging system using Redis.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """Initialize the Communication Bus."""
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.running = False
        self.listener_task: Optional[asyncio.Task] = None
    
    async def connect(self):
        """Connect to Redis."""
        self.redis_client = redis.Redis.from_url(self.redis_url)
        self.pubsub = self.redis_client.pubsub()
        self.running = True
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.listener_task:
            self.running = False
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
        
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        
        if self.redis_client:
            await self.redis_client.close()
    
    async def publish_message(self, message: Any = None, **kwargs):
        """Publish a message to a topic.

        Supports three calling patterns for backward-compatibility:
        1. publish_message(Message(...))
        2. publish_message({...}) – dict with required message fields
        3. publish_message(sender="foo", topic="bar", content={...}, ...)
        """
        # Accept keyword-only construction
        if message is None:
            if not kwargs:
                raise ValueError("publish_message requires a Message/dict or keyword fields")
            candidate = kwargs
        else:
            # Merge positional and keyword overrides if both supplied
            if kwargs:
                if isinstance(message, Message):
                    candidate = {**message.model_dump(), **kwargs}
                elif isinstance(message, dict):
                    candidate = {**message, **kwargs}
                else:
                    raise ValueError("Unsupported message type with additional kwargs")
            else:
                candidate = message

        # Ensure we have a Message instance
        if isinstance(candidate, Message):
            msg_obj = candidate
        else:
            msg_obj = Message.model_validate(candidate)

        await self.publish(msg_obj)
    
    async def publish(self, message: Message):
        """Publish a message to a topic."""
        if not self.redis_client:
            await self.connect()
        
        message_json = message.model_dump_json()
        await self.redis_client.publish(message.topic, message_json)
    
    async def wait_for_message(self, *, topic: str, conversation_id: Optional[str] = None, reply_to: Optional[str] = None, timeout: int = 30) -> Message:
        """Wait for a single message matching the criteria.

        This is a lightweight helper primarily for synchronous request/response flows.
        """
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Message] = loop.create_future()

        async def _tmp_callback(msg: Message):
            if conversation_id and msg.conversation_id != conversation_id:
                return
            if reply_to and msg.reply_to != reply_to:
                return
            if not future.done():
                future.set_result(msg)

        # Subscribe and wait
        await self.subscribe(topic, _tmp_callback)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            await self.unsubscribe(topic, _tmp_callback)

    async def subscribe(self, topic: str, callback: Callable[[Message], None]):
        """Subscribe to a topic."""
        if not self.redis_client:
            await self.connect()
        
        if topic not in self.subscriptions:
            self.subscriptions[topic] = []
            await self.pubsub.subscribe(topic)
        
        self.subscriptions[topic].append(callback)
        
        if not self.listener_task or self.listener_task.done():
            self.listener_task = asyncio.create_task(self._listen())
    
    async def unsubscribe(self, topic: str, callback: Callable[[Message], None]):
        """Unsubscribe from a topic."""
        if topic in self.subscriptions:
            self.subscriptions[topic].remove(callback)
            
            if not self.subscriptions[topic]:
                del self.subscriptions[topic]
                await self.pubsub.unsubscribe(topic)
    
    async def _listen(self):
        """Listen for messages on subscribed topics."""
        while self.running:
            try:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    channel = message["channel"].decode("utf-8")
                    data = json.loads(message["data"].decode("utf-8"))
                    message_obj = Message.model_validate(data)
                    
                    if channel in self.subscriptions:
                        for callback in self.subscriptions[channel]:
                            asyncio.create_task(self._call_callback(callback, message_obj))
            except Exception as e:
                print(f"Error in message listener: {e}")
            
            await asyncio.sleep(0.01)
    
    async def _call_callback(self, callback: Callable[[Message], None], message: Message):
        """Call a callback with a message."""
        try:
            await callback(message)
        except Exception as e:
            print(f"Error in message callback: {e}")