-- Migration: Increase VARCHAR limits for better user experience
-- This migration increases character limits for the research query for greater context.

BEGIN;

-- Increase research_query limit from 1000 to 10000 characters
ALTER TABLE research_tasks 
ALTER COLUMN research_query TYPE VARCHAR(10000);

COMMIT;
