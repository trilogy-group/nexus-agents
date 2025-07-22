-- Migration: Add Projects Taxonomy
-- This migration adds the project concept as a top-level taxonomy for research tasks

-- Create projects table
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    user_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add project_id to research_tasks
ALTER TABLE research_tasks 
ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE CASCADE;

-- Create index for efficient queries
CREATE INDEX IF NOT EXISTS idx_research_tasks_project_id ON research_tasks(project_id);

-- Shared knowledge base tables
CREATE TABLE IF NOT EXISTS project_knowledge_graphs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    knowledge_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for project knowledge graphs
CREATE INDEX IF NOT EXISTS idx_project_knowledge_graphs_project_id ON project_knowledge_graphs(project_id);

-- Create a default project for existing tasks
INSERT INTO projects (id, name, description, user_id)
VALUES (
    '00000000-0000-0000-0000-000000000001'::UUID,
    'Default Project',
    'Default project for migrated research tasks',
    '00000000-0000-0000-0000-000000000000'::UUID
);

-- Migrate existing tasks to the default project
UPDATE research_tasks 
SET project_id = '00000000-0000-0000-0000-000000000001'::UUID 
WHERE project_id IS NULL;

-- Make project_id NOT NULL after migration
ALTER TABLE research_tasks 
ALTER COLUMN project_id SET NOT NULL;
