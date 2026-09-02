-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable Apache AGE
CREATE EXTENSION IF NOT EXISTS age;
LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- Initialize default graph if not exists
SELECT create_graph('autonovel_graph');
