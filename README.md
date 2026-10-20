# Subtext — NLP Divergence Engine for Indian Equity Research

## What actually runs where

This repo was scaffolded in a sandboxed environment with no internet access
beyond package registries — so it couldn't reach NSE/BSE or huggingface.co to
test data-fetching or model downloads live. Here's the honest split:

| File | Status | Needs |
|---|---|---|
| `divergence/baseline_model.py` | **Built and verified — runs as-is** | nothing, pure Python |
| `db/schema.sql` | Ready to apply | a Postgres/Supabase instance |
| `ingestion/fetch_announcements.py` | Structured, untested live | network access to nseindia.com |
| `extraction/tone_pipeline.py` | Structured, untested live | network access to huggingface.co (downloads FinBERT) |

## Setup (on your own machine, or in Claude Code)

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# sanity check the piece that doesn't need network:
python3 divergence/baseline_model.py

# create the DB (point at your Supabase Postgres connection string; run once for a new database)
psql "$SUPABASE_DB_URL" -f db/schema.sql

# run the actual data pull (SUPABASE_DB_URL must be set in the environment)
python3 ingestion/fetch_announcements.py

# run the extraction pipeline (downloads FinBERT on first call)
python3 extraction/tone_pipeline.py
```

The fetcher saves a timestamped raw JSON snapshot under `data/raw/` before
writing each announcement to the existing `companies` and `filings` tables.
It skips exact announcement duplicates on later runs. Keep the connection URL
private and do not commit it.

## This week's order of operations

1. Run `baseline_model.py` locally to confirm it behaves the same as it did
   in testing — it should.
2. Stand up the Supabase project, apply `schema.sql`.
3. Run `fetch_announcements.py` against the 10-company pilot list. It saves
   raw output into `data/raw/` before writing announcement records to the DB;
   keep this audit trail before parsing anything.
4. Pull 2-3 years of historical concall transcripts for the same 10 companies
   (transcripts aren't on the announcements endpoint — most companies post
   PDFs on their own investor-relations pages; that's a per-company scraping
   job, not a single NSE API call).
5. Run `tone_pipeline.py` over the historical transcripts to backfill
   `speaker_tone_scores` — this is what gives `baseline_model.py` real
   history to score against instead of the toy example.
6. Once 3+ quarters exist per executive, start generating real
   `baseline_deviation_scores` and eyeball whether the flags look sane before
   trusting them.

## Recommended: move this to Claude Code

This chat's sandbox resets between tasks and can't reach the sites this
project actually needs. For the sustained build from here — iterating on the
pipeline, running it against live data, committing to git — Claude Code (in
the desktop app, VS Code, or terminal) gives you a persistent repo and full
network access, and I can keep working in it alongside you turn by turn.
