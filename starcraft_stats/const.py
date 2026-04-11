"""Project-wide constants."""

from datetime import UTC, datetime

# All per-project and all-projects CSVs start from this date. Every CSV must
# share the same start date so that the frontend chart, which aligns series by
# array index rather than date value, renders all lines in sync.
CSV_START_DATE = datetime(year=2021, month=1, day=1, tzinfo=UTC)
