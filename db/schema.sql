-- Hirengine AI Database Initialization Schema
-- Target Database: PostgreSQL

-- 1. Create custom ENUM types
CREATE TYPE domain_type AS ENUM (
    'Oil & Gas', 
    'Railway', 
    'Information Technology', 
    'Healthcare', 
    'Electrical/Testing'
);

CREATE TYPE stage_type AS ENUM (
    'Screening', 
    'Shortlist', 
    'Interviewing', 
    'Offered', 
    'Hired', 
    'Rejected'
);

-- 2. Create Requisitions Table
CREATE TABLE requisitions (
    id SERIAL PRIMARY KEY,
    job_title VARCHAR(255) NOT NULL,
    location VARCHAR(255) NOT NULL,
    target_domain domain_type NOT NULL,
    job_description_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 3. Create Candidates Table
CREATE TABLE candidates (
    id SERIAL PRIMARY KEY,
    requisition_id INTEGER NOT NULL REFERENCES requisitions(id) ON DELETE CASCADE,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50) NOT NULL,
    passport_number VARCHAR(100),
    current_stage stage_type DEFAULT 'Screening' NOT NULL,
    total_experience_years NUMERIC(4,2) NOT NULL,
    relevant_experience_years NUMERIC(4,2) NOT NULL,
    match_score INTEGER CHECK (match_score >= 0 AND match_score <= 100) NOT NULL,
    skills_matrix TEXT[] NOT NULL,
    specialization_tags TEXT[] NOT NULL,
    industry_remarks TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 4. Create Performance GIN Indexes for Multi-Attribute Queries
-- GIN index on text array for sub-millisecond skill searches
CREATE INDEX idx_candidates_skills_matrix_gin ON candidates USING gin (skills_matrix);

-- GIN index on text array for specialization tag filtering
CREATE INDEX idx_candidates_specialization_tags_gin ON candidates USING gin (specialization_tags);

-- Standard B-Tree Indexes for Foreign Keys and Range Filters
CREATE INDEX idx_candidates_requisition_id ON candidates(requisition_id);
CREATE INDEX idx_candidates_match_score ON candidates(match_score);
CREATE INDEX idx_candidates_current_stage ON candidates(current_stage);
