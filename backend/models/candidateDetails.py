CREATE TYPE candidate_status AS ENUM ('not selected', 'selected', 'waiting');

CREATE TABLE candidateDetails (
    cand_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    validation_status BOOLEAN,
    pdf_url TEXT, 
    status VARCHAR(20) CHECK (status IN ('not selected', 'selected', 'waiting')),
    saved_at TIMESTAMP DEFAULT NOW()
);