# SubText — Project Documentation

**SubText** is an advanced Natural Language Processing (NLP) divergence engine built specifically for Indian equity research (NSE & BSE listed companies). It moves beyond traditional global sentiment analysis by detecting **abnormal shifts in executive and corporate tone** relative to historical baselines.

---

## 1. Executive Summary & Core Philosophy

Traditional financial NLP tools evaluate corporate earnings transcripts and regulatory filings against fixed global sentiment scales (e.g., positive vs. negative). However, this approach suffers from severe false positives and blind spots:
- **The Upbeat CEO:** A CEO who is chronically optimistic will always score "positive," masking sudden underlying business stress when their tone dips slightly toward neutral.
- **The Guarded CFO:** A conservative CFO who maintains a muted, factual tone will score "neutral" or "negative," even when reporting blowout financial results.

### The SubText Solution
SubText introduces **Executive & Company Baseline Modeling ("Abnormal Tone")**:
1. **Historical Anchoring:** Instead of a fixed global scale, SubText builds a multi-year historical tone distribution (mean and standard deviation) for each individual executive (CEO, CFO, MD) and company.
2. **Z-Score Deviation:** Current quarterly disclosures are scored against the executive's *own* historical baseline. The deviation (z-score) is the primary trading/research signal.
3. **Signal Flagging:** Significant positive ($\ge +1.5\sigma$) or negative ($\le -1.5\sigma$) deviations automatically trigger flags for deeper qualitative and quantitative review.

---

## 2. System Architecture & Components

```
┌──────────────────────────────────────────────────────────────────┐
│                   Data Ingestion Layer (`ingestion/`)                    │
│    NSE/BSE Announcements API (Session Cookies + Rate Limiting)           │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                  Database Persistence Layer (`db/schema.sql`)            │
│       PostgreSQL / Supabase (`companies`, `filings`, `transcripts`)      │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│             Extraction & Sentiment Pipeline (`extraction/`)              │
│       FinBERT Classifier (`ProsusAI/finbert`) → Speaker Tone Scores      │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│           Baseline & Divergence Engine (`divergence/`)                   │
│       Z-Score Deviation vs Executive History → Outlier Flags             │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│               Interactive Research Dashboard (`dashboard/`)              │
│       Tailwind CSS + SVG Divergence Charts + Executive Tone Drivers      │
└──────────────────────────────────────────────────────────────────────────┘
```

### Module Breakdown

#### 1. Ingestion (`ingestion/fetch_announcements.py`)
- Pulls corporate announcements for a pilot universe of top NSE-listed companies.
- Implements a two-step browser session initialization (cookie acquisition) required by NSE endpoints to avoid `401 Unauthorized` errors.
- Saves immutable raw JSON snapshots under `data/raw/` before parsing and upserting records into Supabase Postgres (`companies` and `filings` tables), preventing exact duplicate insertions.

#### 2. Extraction Pipeline (`extraction/tone_pipeline.py`)
- Utilizes **FinBERT** (`ProsusAI/finbert`), a state-of-the-art financial domain-specific BERT model.
- Processes earnings call transcripts turn-by-turn per speaker (CEO, CFO, etc.).
- Converts positive, neutral, and negative classification probabilities into a continuous $-1.0$ to $+1.0$ tone score.
- Persists per-speaker scores into the `speaker_tone_scores` database table.

#### 3. Divergence Engine (`divergence/baseline_model.py`)
- Pure Python logic module requiring no external network calls.
- Computes baseline mean and standard deviation from an executive's prior quarter tone scores (requiring a minimum history of 3 quarters).
- Computes z-score deviation:
  $$\text{Deviation Score} = \frac{\text{Current Tone} - \text{Baseline Mean}}{\text{Baseline StDev}}$$
- Assigns actionable flags (`UNUSUALLY POSITIVE vs. own history`, `UNUSUALLY NEGATIVE vs. own history`, or `within normal range`).

#### 4. Database Schema (`db/schema.sql`)
Designed for PostgreSQL / Supabase with support for vector embeddings (pgvector):
- `companies`: Master table for listed entities (`name`, `nse_symbol`, `bse_code`, `sector`).
- `transcripts`: Earnings call transcript storage (`quarter`, `call_date`, `raw_text`, `source_url`).
- `filings`: Regulatory announcement filings (`filing_type`, `filing_date`, `raw_text`).
- `speaker_tone_scores`: Per-executive quarterly sentiment scores.
- `baseline_deviation_scores`: Computed z-scores, historical means/stdevs, and divergence flags.
- `credibility_scores`: Holistic quarterly creditability and guidance reliability metrics.
- `extracted_events`: Structured event logs (`guidance_cut`, `management_change`, `M&A`).

#### 5. Interactive Dashboard (`dashboard/index.html`)
- Modern dark-mode interface built with Tailwind CSS, Plus Jakarta Sans, and JetBrains Mono.
- Interactive company quick-selector (TCS, INFY, RELIANCE, HDFCBANK, WIPRO).
- SVG-rendered quarterly divergence timeline charts displaying historical baseline ±1σ bands.
- Executive tone driver cards highlighting key statements contributing to positive/negative shifts.
- Comprehensive historical baseline and deviation ledger table.

---

## 3. Pilot Universe

SubText currently targets a high-liquidity pilot universe across Indian IT, Banking, Energy, and Conglomerates:
- **IT Services:** TCS, INFY, WIPRO, HCLTECH, TECHM
- **Banking & Financials:** HDFCBANK, ICICIBANK, BAJFINANCE
- **Energy & Conglomerates:** RELIANCE, TITAN

---

## 4. Setup and Installation Guide

### Prerequisites
- Python 3.9+
- PostgreSQL / Supabase instance

### Local Installation

```bash
# 1. Clone repository and create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run pure-Python baseline model unit verification (no network required)
python3 divergence/baseline_model.py

# 4. Apply database schema to your Supabase/Postgres instance
psql "$SUPABASE_DB_URL" -f db/schema.sql

# 5. Run data ingestion (requires network & valid SUPABASE_DB_URL)
export SUPABASE_DB_URL="postgresql://user:password@host:5432/dbname"
python3 ingestion/fetch_announcements.py

# 6. Run FinBERT extraction pipeline
python3 extraction/tone_pipeline.py
```

---

## 5. Operational Workflow & Order of Operations

1. **Verify Baseline Logic:** Run `python3 divergence/baseline_model.py` to confirm statistical outlier detection behaves correctly across guarded vs. upbeat executive archetypes.
2. **Initialize Database:** Provision Supabase and execute `db/schema.sql`.
3. **Ingest Announcements:** Run `fetch_announcements.py` against the pilot symbols, ensuring raw snapshots are archived in `data/raw/`.
4. **Backfill Transcripts:** Pull 2–3 years of historical earnings call transcripts from company Investor Relations portals.
5. **Score & Backfill Tone:** Run `tone_pipeline.py` over historical transcripts to populate `speaker_tone_scores`.
6. **Generate Signals:** Once 3+ quarters of history accumulate per executive, generate `baseline_deviation_scores` and monitor divergence signals via `dashboard/index.html`.
