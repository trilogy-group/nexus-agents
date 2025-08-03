-- Migration to add data aggregation tables and columns

-- Create table for data aggregation results
CREATE TABLE IF NOT EXISTS data_aggregation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES research_tasks(id),
    entity_type TEXT NOT NULL,
    entity_data JSONB NOT NULL,  -- {name, attributes, sources, confidence}
    unique_identifier TEXT,  -- e.g., NCES_ID for schools
    search_context JSONB,  -- {location, subspace, query}
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_aggregation_task ON data_aggregation_results(task_id);
CREATE INDEX IF NOT EXISTS idx_aggregation_identifier ON data_aggregation_results(unique_identifier);
CREATE INDEX IF NOT EXISTS idx_entity_data_gin ON data_aggregation_results USING GIN (entity_data);

-- Add columns to research_tasks table for data aggregation support
ALTER TABLE research_tasks ADD COLUMN IF NOT EXISTS research_type VARCHAR(50) DEFAULT 'analytical_report';
ALTER TABLE research_tasks ADD COLUMN IF NOT EXISTS aggregation_config JSONB;
ALTER TABLE research_tasks ADD COLUMN IF NOT EXISTS external_resource TEXT;
