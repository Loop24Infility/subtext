-- Subtext — signal database schema
-- Postgres / Supabase (pgvector extension needed for embeddings, added in Phase 3)

CREATE TABLE companies (
    id            SERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    nse_symbol    TEXT UNIQUE,
    bse_code      TEXT,
    sector        TEXT
);

CREATE TABLE transcripts (
    id            SERIAL PRIMARY KEY,
    company_id    INTEGER REFERENCES companies(id),
    quarter       TEXT NOT NULL,       -- e.g. 'Q1FY26'
    call_date     DATE,
    raw_text      TEXT NOT NULL,
    source_url    TEXT,
    fetched_at    TIMESTAMP DEFAULT now()
);

CREATE TABLE filings (
    id            SERIAL PRIMARY KEY,
    company_id    INTEGER REFERENCES companies(id),
    filing_type   TEXT,                -- e.g. 'annual_report', 'quarterly_result'
    filing_date   DATE,
    raw_text      TEXT NOT NULL,
    source_url    TEXT,
    fetched_at    TIMESTAMP DEFAULT now()
);

CREATE TABLE speaker_tone_scores (
    id              SERIAL PRIMARY KEY,
    transcript_id   INTEGER REFERENCES transcripts(id),
    company_id      INTEGER REFERENCES companies(id),
    executive_name  TEXT NOT NULL,
    executive_role  TEXT,              -- 'CEO', 'CFO', etc.
    quarter         TEXT NOT NULL,
    tone_score      NUMERIC,           -- output of extraction/ pipeline
    computed_at     TIMESTAMP DEFAULT now()
);

CREATE TABLE baseline_deviation_scores (
    id                SERIAL PRIMARY KEY,
    company_id        INTEGER REFERENCES companies(id),
    executive_name    TEXT NOT NULL,
    quarter           TEXT NOT NULL,
    current_tone      NUMERIC,
    baseline_mean     NUMERIC,
    baseline_stdev    NUMERIC,
    deviation_score   NUMERIC,
    flag              TEXT,
    computed_at       TIMESTAMP DEFAULT now()
);

CREATE TABLE credibility_scores (
    id            SERIAL PRIMARY KEY,
    company_id    INTEGER REFERENCES companies(id),
    quarter       TEXT NOT NULL,
    score         NUMERIC,
    features_json JSONB,
    computed_at   TIMESTAMP DEFAULT now()
);

CREATE TABLE extracted_events (
    id            SERIAL PRIMARY KEY,
    company_id    INTEGER REFERENCES companies(id),
    source_type   TEXT,                -- 'transcript' or 'filing'
    source_id     INTEGER,
    event_type    TEXT,                -- 'guidance_cut', 'management_change', 'M&A', etc.
    description   TEXT,
    confidence    NUMERIC,
    extracted_at  TIMESTAMP DEFAULT now()
);
