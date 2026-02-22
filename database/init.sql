-- Initialize CodeForge AI Database

-- Create database
CREATE DATABASE IF NOT EXISTS codeforge_db;

-- Create user
CREATE USER IF NOT EXISTS codeforge WITH PASSWORD 'codeforge';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE codeforge_db TO codeforge;

-- Extensions
\c codeforge_db;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- Comments
COMMENT ON DATABASE codeforge_db IS 'CodeForge AI - AI-Powered Development Platform';