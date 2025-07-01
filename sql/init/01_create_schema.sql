-- Nexus Agents PostgreSQL Schema
-- Translated from DuckDB schema with PostgreSQL-specific optimizations

BEGIN;

-- Research tasks table (updated for orchestrator)
CREATE TABLE IF NOT EXISTS research_tasks (
    task_id VARCHAR(255) PRIMARY KEY,
    research_query TEXT NOT NULL,
    title VARCHAR(500),
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    user_id VARCHAR(255),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    metadata JSONB,
    decomposition JSONB,
    plan JSONB,
    results JSONB,
    summary JSONB,
    reasoning JSONB
);

-- Research reports table (final markdown reports)
CREATE TABLE IF NOT EXISTS research_reports (
    task_id VARCHAR(255) PRIMARY KEY,
    report_markdown TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES research_tasks(task_id) ON DELETE CASCADE
);

-- Research subtasks table
CREATE TABLE IF NOT EXISTS research_subtasks (
    subtask_id VARCHAR(255) PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL,
    topic VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    assigned_agent VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    key_questions JSONB,
    search_results JSONB,
    FOREIGN KEY (task_id) REFERENCES research_tasks(task_id) ON DELETE CASCADE
);

-- Artifacts table (for generated documents, reports, etc.)
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id VARCHAR(255) PRIMARY KEY,
    task_id VARCHAR(255),
    subtask_id VARCHAR(255),
    title VARCHAR(500) NOT NULL,
    type VARCHAR(100) NOT NULL, -- 'report', 'summary', 'document', 'data', etc.
    format VARCHAR(50) NOT NULL, -- 'json', 'markdown', 'pdf', 'docx', 'csv', etc.
    file_path VARCHAR(1000), -- Path to file on disk (for binary files)
    content JSONB, -- JSON content (for structured data)
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    size_bytes BIGINT,
    checksum VARCHAR(128),
    FOREIGN KEY (task_id) REFERENCES research_tasks(task_id) ON DELETE CASCADE,
    FOREIGN KEY (subtask_id) REFERENCES research_subtasks(subtask_id) ON DELETE CASCADE
);

-- Sources table (for tracking information sources)
CREATE TABLE IF NOT EXISTS sources (
    source_id VARCHAR(255) PRIMARY KEY,
    url VARCHAR(2000),
    title VARCHAR(500),
    description TEXT,
    source_type VARCHAR(100), -- 'web', 'document', 'api', etc.
    provider VARCHAR(100), -- 'linkup', 'exa', 'perplexity', 'firecrawl', etc.
    accessed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    content_hash VARCHAR(128),
    reliability_score DECIMAL(3,2) CHECK (reliability_score >= 0 AND reliability_score <= 1)
);

-- Search results table (for caching search results)
CREATE TABLE IF NOT EXISTS search_results (
    result_id VARCHAR(255) PRIMARY KEY,
    query VARCHAR(1000) NOT NULL,
    provider VARCHAR(100) NOT NULL,
    results JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ,
    metadata JSONB
);

-- Task Operations table (for tracking individual operations within a task)
CREATE TABLE IF NOT EXISTS task_operations (
    operation_id VARCHAR(255) PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL,
    operation_type VARCHAR(100) NOT NULL, -- 'decomposition', 'search', 'scraping', 'summarization', 'reasoning', 'artifact_generation'
    operation_name VARCHAR(500) NOT NULL, -- Human-readable name
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    agent_type VARCHAR(100), -- Which agent performed this operation
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    input_data JSONB, -- Input parameters/data for the operation
    output_data JSONB, -- Results/output from the operation
    error_message TEXT,
    metadata JSONB,
    FOREIGN KEY (task_id) REFERENCES research_tasks(task_id) ON DELETE CASCADE
);

-- Operation Evidence table (for detailed evidence of each operation)
CREATE TABLE IF NOT EXISTS operation_evidence (
    evidence_id VARCHAR(255) PRIMARY KEY,
    operation_id VARCHAR(255) NOT NULL,
    evidence_type VARCHAR(100) NOT NULL, -- 'search_query', 'search_results', 'scraped_content', 'llm_prompt', 'llm_response', 'generated_artifact'
    evidence_data JSONB NOT NULL, -- The actual evidence data
    source_url VARCHAR(2000), -- URL if applicable
    provider VARCHAR(100), -- Which provider/service generated this evidence
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    size_bytes BIGINT,
    metadata JSONB,
    FOREIGN KEY (operation_id) REFERENCES task_operations(operation_id) ON DELETE CASCADE
);

-- Operation Dependencies table (for tracking operation dependencies)
CREATE TABLE IF NOT EXISTS operation_dependencies (
    dependency_id VARCHAR(255) PRIMARY KEY,
    operation_id VARCHAR(255) NOT NULL, -- The operation that depends on another
    depends_on_operation_id VARCHAR(255) NOT NULL, -- The operation it depends on
    dependency_type VARCHAR(50) DEFAULT 'sequential', -- 'sequential', 'parallel', 'conditional'
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (operation_id) REFERENCES task_operations(operation_id) ON DELETE CASCADE,
    FOREIGN KEY (depends_on_operation_id) REFERENCES task_operations(operation_id) ON DELETE CASCADE
);

COMMIT;
