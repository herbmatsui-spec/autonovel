-- Enable pgvector (v5.0: Standard PostgreSQL 16 + pgvector)
-- Apache AGE extension removed in favor of relational memory & foreshadowing tables.
CREATE EXTENSION IF NOT EXISTS vector;
