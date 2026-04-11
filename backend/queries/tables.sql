CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS candidate_details (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    filename VARCHAR,
    name VARCHAR,
    email VARCHAR,
    phone VARCHAR,
    experience VARCHAR,
    profiles JSON,
    match_score FLOAT,
    missing_skills JSON,
    strengths JSON,
    job_description TEXT,
    github_url VARCHAR,
    leetcode_url VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
