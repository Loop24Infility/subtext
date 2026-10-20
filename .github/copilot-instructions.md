# Copilot instructions for Subtext

## Project purpose

Subtext is a Python NLP engine for Indian equity research. The key idea is to compare an executive's current tone against their own historical baseline instead of against a generic sentiment scale.

The repo is organized as a small pipeline:

- `ingestion/` fetches raw market disclosures and announcements from external sources
- `extraction/` scores speaker tone from transcript text using a Hugging Face model
- `divergence/` computes whether the current tone is unusually positive or negative relative to that executive's history
- `db/schema.sql` defines the Postgres/Supabase tables that hold the raw and derived data
- `data/` is the expected audit/raw-data landing area before parsing

## Setup and validation commands

This repo does not currently define a project-wide test runner or lint config. Validation is currently a set of direct Python commands and data-pipeline entry points.

```bash
# create and activate a local venv
python3 -m venv venv && source venv/bin/activate

# install dependencies
pip install -r requirements.txt

# sanity-check the pure logic module (no external network required)
python3 divergence/baseline_model.py

# optional syntax validation across the project
python3 -m compileall divergence extraction ingestion

# apply the database schema to a local or Supabase Postgres instance
# Run once for a new database; skip if these tables already exist.
psql "$SUPABASE_DB_URL" -f db/schema.sql

# run the live data fetcher (requires internet access to NSE/BSE)
export SUPABASE_DB_URL="<your Postgres connection URL>"
python3 ingestion/fetch_announcements.py

# run the extraction pipeline (downloads FinBERT on first run)
python3 extraction/tone_pipeline.py
```

If you need a single validation target while working on the pure logic layer, use the baseline model entry point above; it is the repository's closest live sanity check.

## Architecture overview

The repo is intentionally split into three stages, and the stage boundaries matter:

1. Ingestion stage (`ingestion/fetch_announcements.py`)
   - Pulls corporate-announcement data for a fixed pilot universe of NSE symbols.
   - Uses a browser-like session pattern because NSE endpoints require cookies before returning JSON.
   - Saves a timestamped JSON archive under `data/raw/` before database writes.
   - Upserts the pilot symbols into `companies` and stores each raw announcement in `filings`; exact repeats are skipped.
   - Requires `SUPABASE_DB_URL` and the existing schema. It does not parse announcements into structured filing fields yet.

2. Extraction stage (`extraction/tone_pipeline.py`)
   - Converts transcript or filing text into per-speaker tone scores.
   - Uses `SpeakerTurn` dataclass objects and the `transformers.pipeline(...)` sentiment-analysis model.
   - Produces scores that map to a `-1..1` scale for the downstream baseline model.

3. Divergence stage (`divergence/baseline_model.py`)
   - Uses `DisclosureRecord` and `BaselineResult` dataclasses to compare the current quarter against the executive's prior quarters.
   - Calculates a z-score-like deviation from the executive's own distribution and flags unusual positive/negative moves.
   - This module is intentionally network-free and is the safest module to exercise in a constrained environment.

The database model (`db/schema.sql`) is the integration layer across these stages. The key tables are `speaker_tone_scores` and `baseline_deviation_scores`; those capture the outputs described above.

## Key conventions

- Treat network-dependent modules as separate from pure logic. `divergence/baseline_model.py` is the reference implementation and should work without internet or model downloads; `ingestion/` and `extraction/` are live-data code paths.
- Use the `quarter` field as a string such as `Q1FY26`; this is part of the data contract across schemas and calculations.
- Keep raw snapshots before parsing. The README explicitly calls for saving raw outputs into `data/raw/` before any transformation.
- Prefer explicit dataclasses for structured data boundaries: `DisclosureRecord` and `SpeakerTurn` are the repository's idiom for passing values between stages.
- Keep model and source logic distinct from database persistence. `db/schema.sql` defines storage boundaries, but the Python modules are not coupled to a specific ORM or application framework.
- Secrets and environment-specific credentials should be provided via environment variables such as `SUPABASE_DB_URL`; avoid hardcoding database URLs in source files.

## Working notes for future Copilot sessions

- Do not assume this repo has a standard web app or packaged CLI. It is a research/data pipeline with a few standalone Python entry points.
- Keep the live-data and offline-logic separation intact. The offline baseline logic should remain runnable without hitting NSE/BSE or Hugging Face.
- If you add new pipeline code, follow the same explicit, dataclass-driven contract style and preserve the quarter-based history logic described above.
