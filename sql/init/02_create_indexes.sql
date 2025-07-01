-- Nexus Agents PostgreSQL Indexes
-- Performance indexes for concurrent operations

BEGIN;

-- Core table indexes for better performance
CREATE INDEX IF NOT EXISTS idx_tasks_status ON research_tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_created ON research_tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_tasks_updated ON research_tasks(updated_at);

CREATE INDEX IF NOT EXISTS idx_subtasks_task ON research_subtasks(task_id);
CREATE INDEX IF NOT EXISTS idx_subtasks_status ON research_subtasks(status);
CREATE INDEX IF NOT EXISTS idx_subtasks_agent ON research_subtasks(assigned_agent);

CREATE INDEX IF NOT EXISTS idx_artifacts_task ON artifacts(task_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_subtask ON artifacts(subtask_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(type);
CREATE INDEX IF NOT EXISTS idx_artifacts_format ON artifacts(format);

CREATE INDEX IF NOT EXISTS idx_sources_url ON sources(url);
CREATE INDEX IF NOT EXISTS idx_sources_provider ON sources(provider);
CREATE INDEX IF NOT EXISTS idx_sources_type ON sources(source_type);
CREATE INDEX IF NOT EXISTS idx_sources_hash ON sources(content_hash);

CREATE INDEX IF NOT EXISTS idx_search_query_provider ON search_results(query, provider);
CREATE INDEX IF NOT EXISTS idx_search_expires ON search_results(expires_at);

-- Operation tracking indexes (critical for multi-agent concurrency)
CREATE INDEX IF NOT EXISTS idx_operations_task ON task_operations(task_id);
CREATE INDEX IF NOT EXISTS idx_operations_status ON task_operations(status);
CREATE INDEX IF NOT EXISTS idx_operations_type ON task_operations(operation_type);
CREATE INDEX IF NOT EXISTS idx_operations_agent ON task_operations(agent_type);
CREATE INDEX IF NOT EXISTS idx_operations_started ON task_operations(started_at);

CREATE INDEX IF NOT EXISTS idx_evidence_operation ON operation_evidence(operation_id);
CREATE INDEX IF NOT EXISTS idx_evidence_type ON operation_evidence(evidence_type);
CREATE INDEX IF NOT EXISTS idx_evidence_provider ON operation_evidence(provider);
CREATE INDEX IF NOT EXISTS idx_evidence_created ON operation_evidence(created_at);

CREATE INDEX IF NOT EXISTS idx_dependencies_operation ON operation_dependencies(operation_id);
CREATE INDEX IF NOT EXISTS idx_dependencies_depends_on ON operation_dependencies(depends_on_operation_id);

-- JSONB indexes for better JSON query performance
CREATE INDEX IF NOT EXISTS idx_tasks_metadata_gin ON research_tasks USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_operations_input_gin ON task_operations USING GIN (input_data);
CREATE INDEX IF NOT EXISTS idx_operations_output_gin ON task_operations USING GIN (output_data);
CREATE INDEX IF NOT EXISTS idx_evidence_data_gin ON operation_evidence USING GIN (evidence_data);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_operations_task_status ON task_operations(task_id, status);
CREATE INDEX IF NOT EXISTS idx_operations_task_type ON task_operations(task_id, operation_type);
CREATE INDEX IF NOT EXISTS idx_evidence_operation_type ON operation_evidence(operation_id, evidence_type);

COMMIT;
