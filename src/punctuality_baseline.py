"""
01_punctuality_baseline.py
First-pass analysis of Deutsche Bahn punctuality.

Data: piebro/deutsche-bahn-data on HuggingFace (CC BY 4.0, source: Deutsche Bahn).
Download first (see repo README):
    uv run --with "huggingface-hub" hf download piebro/deutsche-bahn-data \
        --repo-type=dataset --local-dir=. --include "monthly_processed_data/*"

Definitions (matching Deutsche Bahn's own convention):
  - A stop is "on time" if arrival delay < 6 minutes.
  - Cancellations are reported SEPARATELY, not folded into the delay average
    (a canceled train has no delay figure; averaging it in as 0 flatters the number).

Data caveats this script deliberately handles:
  - Coverage break: before 2025-11-02 only the ~100 biggest stations exist;
    all stations exist after. Comparing station counts across that date gives a
    fake jump, so this baseline stays inside the all-stations era.
  - Missing hours: some collection windows were skipped, so absence of a row
    does NOT mean no train ran. Don't infer service levels from row counts.
  - Timestamps are Europe/Berlin (CET/CEST) — watch the DST changeover if you
    later do hour-of-day work across March/October.

Run: uv run --with "duckdb,pandas" python src/01_punctuality_baseline.py
"""

import duckdb

DATA_GLOB = "data/monthly_processed_data/*.parquet"

# Stay inside the all-stations era to avoid the 2025-11-02 coverage break.
# Widen this once you've decided how to handle the earlier ~100-station period.
START, END = "2026-01-01", "2026-07-01"

con = duckdb.connect()

# 1. Punctuality by train type (non-canceled stops only).
by_type = con.execute(f"""
    SELECT
        train_type,
        count(*)                                         AS stops,
        round(100.0 * avg((delay_in_min < 6)::int), 1)   AS on_time_pct,
        round(avg(delay_in_min), 2)                      AS mean_delay_min
    FROM read_parquet('{DATA_GLOB}')
    WHERE NOT is_canceled
      AND time >= '{START}' AND time < '{END}'
    GROUP BY train_type
    HAVING count(*) > 5000          -- drop tiny, noisy train-type groups
    ORDER BY on_time_pct
""").df()
print("Punctuality by train type:\n", by_type, "\n")

# 2. Cancellation rate by train type (kept separate from the delay figure).
cancels = con.execute(f"""
    SELECT
        train_type,
        round(100.0 * avg(is_canceled::int), 2)          AS cancel_pct
    FROM read_parquet('{DATA_GLOB}')
    WHERE time >= '{START}' AND time < '{END}'
    GROUP BY train_type
    HAVING count(*) > 5000
    ORDER BY cancel_pct DESC
""").df()
print("Cancellation rate by train type:\n", cancels, "\n")

# 3. Punctuality by hour of day — is the network worse at rush hour?
by_hour = con.execute(f"""
    SELECT
        hour(time)                                       AS hour_of_day,
        round(100.0 * avg((delay_in_min < 6)::int), 1)   AS on_time_pct,
        count(*)                                         AS stops
    FROM read_parquet('{DATA_GLOB}')
    WHERE NOT is_canceled
      AND time >= '{START}' AND time < '{END}'
    GROUP BY hour_of_day
    ORDER BY hour_of_day
""").df()
print("Punctuality by hour of day:\n", by_hour)

# NEXT: the differentiator. Order each train's stops by train_line_station_num
# within train_line_ride_id and measure how delay evolves along the route —
# does a small starting delay compound? That's the question the public stats
# site doesn't answer, and the core of what makes this project yours.