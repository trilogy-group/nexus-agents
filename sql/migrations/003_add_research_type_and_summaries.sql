-- Migration: Add research_type and source_summaries for integrated workflow

-- Add research_type to research_tasks
ALTER TABLE research_tasks 
ADD COLUMN IF NOT EXISTS research_type VARCHAR(50) DEFAULT 'analytical_report';

-- Add aggregation_config for data aggregation tasks
ALTER TABLE research_tasks 
ADD COLUMN IF NOT EXISTS aggregation_config JSONB;

-- Add external_resource for future Google Sheets integration
ALTER TABLE research_tasks 
ADD COLUMN IF NOT EXISTS external_resource TEXT;

-- Add new columns to existing source_summaries table for integrated workflow
ALTER TABLE source_summaries 
ADD COLUMN IF NOT EXISTS task_id VARCHAR(255);

ALTER TABLE source_summaries 
ADD COLUMN IF NOT EXISTS subtopic TEXT;

ALTER TABLE source_summaries 
ADD COLUMN IF NOT EXISTS dok_level INTEGER DEFAULT 1;

ALTER TABLE source_summaries 
ADD COLUMN IF NOT EXISTS facts JSONB DEFAULT '[]'::jsonb;

ALTER TABLE source_summaries 
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_source_summaries_task_id ON source_summaries(task_id);
CREATE INDEX IF NOT EXISTS idx_source_summaries_subtopic ON source_summaries(subtopic);

-- Create data_aggregation_results table for future data aggregation
CREATE TABLE IF NOT EXISTS data_aggregation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id VARCHAR(255) REFERENCES research_tasks(task_id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    entity_data JSONB NOT NULL,  -- Flexible storage for entity attributes
    unique_identifier TEXT,  -- e.g., NCES_ID for schools
    search_context JSONB,  -- {location, subspace, query}
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for data aggregation
CREATE INDEX IF NOT EXISTS idx_aggregation_task ON data_aggregation_results(task_id);
CREATE INDEX IF NOT EXISTS idx_aggregation_identifier ON data_aggregation_results(unique_identifier);
CREATE INDEX IF NOT EXISTS idx_entity_data_gin ON data_aggregation_results USING GIN (entity_data);

-- Add comment to track migration
COMMENT ON TABLE source_summaries IS 'Stores summarized content for analytical reports with DOK taxonomy integration';
COMMENT ON TABLE data_aggregation_results IS 'Stores structured entity data for data aggregation research type';
