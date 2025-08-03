-- Migration to add indexes for efficient sources metadata querying
-- Critical for data aggregation task result collection

BEGIN;

-- Add GIN index on sources metadata for efficient JSON queries
-- This enables fast metadata->>'task_id' lookups
CREATE INDEX IF NOT EXISTS idx_sources_metadata_gin ON sources USING GIN (metadata);

-- Add composite index for task_id and accessed_at for ordered retrieval
-- This optimizes the ORDER BY accessed_at DESC query pattern
CREATE INDEX IF NOT EXISTS idx_sources_task_id_accessed ON sources ((metadata->>'task_id'), accessed_at DESC);

-- Add index on reliability_score for data aggregation filtering
CREATE INDEX IF NOT EXISTS idx_sources_reliability ON sources (reliability_score);

COMMIT;
