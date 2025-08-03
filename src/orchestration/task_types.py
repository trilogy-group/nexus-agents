"""Task types and models for parallel processing."""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
import uuid


def utc_now() -> datetime:
    """Get current UTC datetime - replacement for deprecated datetime.utcnow()."""
    return datetime.now(timezone.utc)


class TaskType(Enum):
    """Types of tasks that can be processed."""
    SUMMARIZATION = "summarization"
    ENTITY_EXTRACTION = "entity_extraction"
    DOK_CATEGORIZATION = "dok_categorization"
    SEARCH_SPACE_ENUM = "search_space_enum"
    DATA_AGGREGATION_SEARCH = "data_aggregation_search"
    DATA_AGGREGATION_EXTRACT = "data_aggregation_extract"
    SEARCH = "search"
    REASONING = "reasoning"


class TaskStatus(Enum):
    """Status of a task."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class Task(BaseModel):
    """Task model for parallel processing."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: TaskType
    payload: Dict[str, Any]
    priority: int = 0  # Higher priority = processed first
    model_type: str = "task_model"  # "task_model" or "reasoning_model"
    provider: str = "openai"
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=utc_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    max_retries: int = 3
    parent_task_id: Optional[str] = None  # For subtask tracking
    
    model_config = ConfigDict(use_enum_values=True)


class TaskResult(BaseModel):
    """Result of task execution."""
    task_id: str
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_seconds: Optional[float] = None
    
    model_config = ConfigDict(use_enum_values=True)


class SourceSummary(BaseModel):
    """Summary of a source document."""
    id: str
    task_id: str
    source_id: str
    subtopic: str
    summary: str
    dok_level: int = 1
    facts: list[Dict[str, str]] = Field(default_factory=list)  # [{fact: "", evidence: ""}]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class SearchResultRef(BaseModel):
    """Reference to a search result (not full content)."""
    id: str
    metadata: Dict[str, Any]
    summary_task_id: Optional[str] = None  # ID of summarization task
