"""
NOTE: this needs live internet access to nseindia.com / bseindia.com, which
this sandbox does not have (its network is locked to package registries only).
Correctly structured and ready to run — just run it on your own machine or in
Claude Code, not in this chat's sandbox.

Pulls corporate announcements for a fixed pilot universe of NSE symbols.
NSE requires a browser-like session (cookies from a first GET) before its
JSON endpoints will respond — the two-step pattern below is required, a
single direct request to the announcements endpoint will 401.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import requests

PILOT_SYMBOLS = [
    "TCS", "INFY", "WIPRO", "HCLTECH", "TECHM",
    "HDFCBANK", "ICICIBANK", "RELIANCE", "BAJFINANCE", "TITAN",
]

NSE_BASE = "https://www.nseindia.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    session.get(NSE_BASE, timeout=10)  # picks up cookies needed by the API calls below
    return session


def fetch_announcements(symbol: str, session: requests.Session) -> list[dict]:
    url = f"{NSE_BASE}/api/corporate-announcements"
    params = {"index": "equities", "symbol": symbol}
    resp = session.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def save_raw_snapshot(announcements_by_symbol: dict[str, list[dict]]) -> Path:
    raw_dir = Path(__file__).resolve().parents[1] / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot_path = raw_dir / f"nse_announcements_{timestamp}.json"
    snapshot_path.write_text(
        json.dumps(announcements_by_symbol, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return snapshot_path


def save_announcements_to_database(
    announcements_by_symbol: dict[str, list[dict]], database_url: str
) -> int:
    inserted_count = 0

    with psycopg2.connect(database_url) as connection:
        with connection.cursor() as cursor:
            for symbol, announcements in announcements_by_symbol.items():
                cursor.execute(
                    """
                    INSERT INTO companies (name, nse_symbol)
                    VALUES (%s, %s)
                    ON CONFLICT (nse_symbol)
                    DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                    """,
                    (symbol, symbol),
                )
                company_id = cursor.fetchone()[0]

                for announcement in announcements:
                    raw_text = json.dumps(
                        announcement, ensure_ascii=False, sort_keys=True
                    )
                    cursor.execute(
                        """
                        INSERT INTO filings (company_id, filing_type, raw_text)
                        SELECT %s, %s, %s
                        WHERE NOT EXISTS (
                            SELECT 1
                            FROM filings
                            WHERE company_id = %s
                              AND filing_type = %s
                              AND raw_text = %s
                        )
                        """,
                        (
                            company_id,
                            "nse_corporate_announcement",
                            raw_text,
                            company_id,
                            "nse_corporate_announcement",
                            raw_text,
                        ),
                    )
                    inserted_count += cursor.rowcount

    return inserted_count


def main() -> None:
    session = get_session()
    announcements_by_symbol = {}
    failures = []

    for symbol in PILOT_SYMBOLS:
        try:
            announcements_by_symbol[symbol] = fetch_announcements(symbol, session)
            print(f"{symbol}: {len(announcements_by_symbol[symbol])} announcements")
        except requests.RequestException as e:
            print(f"{symbol}: failed — {e}")
            failures.append(symbol)
        time.sleep(1)  # be polite — do not hammer the endpoint

    snapshot_path = save_raw_snapshot(announcements_by_symbol)
    print(f"Raw snapshot saved to {snapshot_path}")

    database_url = os.environ.get("SUPABASE_DB_URL")
    if not database_url:
        raise RuntimeError("Set SUPABASE_DB_URL to write announcements to Supabase.")

    inserted_count = save_announcements_to_database(
        announcements_by_symbol, database_url
    )
    print(f"Saved {inserted_count} new announcements to Supabase.")

    if failures:
        raise SystemExit(f"Announcement fetch failed for: {', '.join(failures)}")


if __name__ == "__main__":
    main()
