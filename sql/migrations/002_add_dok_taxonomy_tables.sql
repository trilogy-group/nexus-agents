-- Bibliography Management and DOK Taxonomy Tables Migration
-- This migration adds support for Webb's Depth of Knowledge taxonomy
-- and comprehensive bibliography management

BEGIN;

-- Source summaries with DOK facts (DOK Level 1-2)
CREATE TABLE IF NOT EXISTS source_summaries (
    summary_id VARCHAR(255) PRIMARY KEY,
    source_id VARCHAR(255) NOT NULL,
    subtask_id VARCHAR(255),
    dok1_facts JSONB,  -- Array of extracted facts (DOK Level 1)
    summary TEXT NOT NULL,
    summarized_by VARCHAR(255),  -- Which agent performed summarization
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES sources(source_id) ON DELETE CASCADE,
    FOREIGN KEY (subtask_id) REFERENCES research_subtasks(subtask_id) ON DELETE CASCADE
);

-- Knowledge tree structure (DOK Level 1-2)
CREATE TABLE IF NOT EXISTS knowledge_nodes (
    node_id VARCHAR(255) PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL,
    parent_id VARCHAR(255),
    category VARCHAR(500) NOT NULL,
    subcategory VARCHAR(500),
    summary TEXT,
    dok_level INTEGER CHECK (dok_level IN (1, 2)),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES research_tasks(task_id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES knowledge_nodes(node_id) ON DELETE CASCADE
);

-- Link sources to knowledge nodes (many-to-many)
CREATE TABLE IF NOT EXISTS knowledge_node_sources (
    node_id VARCHAR(255) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    relevance_score DECIMAL(3,2) DEFAULT 1.0,
    PRIMARY KEY (node_id, source_id),
    FOREIGN KEY (node_id) REFERENCES knowledge_nodes(node_id) ON DELETE CASCADE,
    FOREIGN KEY (source_id) REFERENCES sources(source_id) ON DELETE CASCADE
);

-- Insights (DOK Level 3)
CREATE TABLE IF NOT EXISTS insights (
    insight_id VARCHAR(255) PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL,
    category VARCHAR(500) NOT NULL,
    insight_text TEXT NOT NULL,
    confidence_score DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES research_tasks(task_id) ON DELETE CASCADE
);

-- Link insights to sources (many-to-many)
CREATE TABLE IF NOT EXISTS insight_sources (
    insight_id VARCHAR(255) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    PRIMARY KEY (insight_id, source_id),
    FOREIGN KEY (insight_id) REFERENCES insights(insight_id) ON DELETE CASCADE,
    FOREIGN KEY (source_id) REFERENCES sources(source_id) ON DELETE CASCADE
);

-- Spiky POVs (DOK Level 4)
CREATE TABLE IF NOT EXISTS spiky_povs (
    pov_id VARCHAR(255) PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL,
    pov_type VARCHAR(10) CHECK (pov_type IN ('truth', 'myth')),
    statement TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES research_tasks(task_id) ON DELETE CASCADE
);

-- Link POVs to insights (many-to-many)
CREATE TABLE IF NOT EXISTS pov_insights (
    pov_id VARCHAR(255) NOT NULL,
    insight_id VARCHAR(255) NOT NULL,
    PRIMARY KEY (pov_id, insight_id),
    FOREIGN KEY (pov_id) REFERENCES spiky_povs(pov_id) ON DELETE CASCADE,
    FOREIGN KEY (insight_id) REFERENCES insights(insight_id) ON DELETE CASCADE
);

-- Track source usage in report sections
CREATE TABLE IF NOT EXISTS report_section_sources (
    report_section_id VARCHAR(255) PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL,
    section_type VARCHAR(100) NOT NULL, -- 'key_findings', 'evidence_analysis', 'causal_relationships', 'alternative_interpretations'
    source_ids JSONB NOT NULL, -- Array of source_ids used in this section
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES research_tasks(task_id) ON DELETE CASCADE
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_source_summaries_source_id ON source_summaries(source_id);
CREATE INDEX IF NOT EXISTS idx_source_summaries_subtask_id ON source_summaries(subtask_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_task_id ON knowledge_nodes(task_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_parent_id ON knowledge_nodes(parent_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_category ON knowledge_nodes(category);
CREATE INDEX IF NOT EXISTS idx_insights_task_id ON insights(task_id);
CREATE INDEX IF NOT EXISTS idx_insights_category ON insights(category);
CREATE INDEX IF NOT EXISTS idx_spiky_povs_task_id ON spiky_povs(task_id);
CREATE INDEX IF NOT EXISTS idx_spiky_povs_type ON spiky_povs(pov_type);
CREATE INDEX IF NOT EXISTS idx_report_section_sources_task_id ON report_section_sources(task_id);
CREATE INDEX IF NOT EXISTS idx_report_section_sources_section_type ON report_section_sources(section_type);

-- GIN indexes for JSONB fields
CREATE INDEX IF NOT EXISTS idx_source_summaries_dok1_facts ON source_summaries USING GIN (dok1_facts);
CREATE INDEX IF NOT EXISTS idx_report_section_sources_source_ids ON report_section_sources USING GIN (source_ids);

COMMIT;
