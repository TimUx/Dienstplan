"""
Realistic date ranges and identifiers aligned with ``db_init`` sample data.

Sample DB uses calendar 2025 for many seeded shift/absence examples; keep
these constants in one place so API tests stay consistent.
"""

from datetime import date

# Typical ISO week used in existing shift/schedule tests
SAMPLE_SCHEDULE_WEEK_MONDAY = date(2025, 1, 6)

# Dashboard / absence clipping tests in ``test_statistics.py``
SAMPLE_DASHBOARD_FEB_START = date(2025, 2, 1)
SAMPLE_DASHBOARD_FEB_END = date(2025, 2, 28)

# Planning job smoke tests (month with sample complexity)
SAMPLE_PLANNING_MONTH_START = date(2025, 3, 1)
SAMPLE_PLANNING_MONTH_END = date(2025, 3, 31)
