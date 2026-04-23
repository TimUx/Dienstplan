"""Shared constants for CP-SAT shift planning constraints."""

# Default values used as fallback if database is not available
DEFAULT_MINIMUM_REST_HOURS = 11
DEFAULT_MAXIMUM_CONSECUTIVE_SHIFTS_WEEKS = 6  # In weeks
DEFAULT_MAXIMUM_CONSECUTIVE_NIGHT_SHIFTS_WEEKS = 3  # In weeks

DEFAULT_WEEKLY_HOURS = 48.0  # Default maximum weekly hours for constraint calculations
# Penalty weight for cross-month boundary consecutive shift violations.
CROSS_MONTH_BOUNDARY_PENALTY = 50000

DEFAULT_ROTATION_PATTERN = ["F", "N", "S"]  # Fallback when DB has no rotation config
