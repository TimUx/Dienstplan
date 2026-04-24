"""
Config for planning stage-metrics health scoring.
"""

# Solve-time threshold (seconds) to classify a Stage 1 solve as "fast" (green).
HEALTH_STAGE1_FAST_SOLVE_SECONDS = 120.0

# Stage buckets used by planning.py health evaluation.
HEALTH_GREEN_STAGES = {"STAGE_1"}
HEALTH_YELLOW_STAGES = {"STAGE_2", "STAGE_3"}
HEALTH_RED_STAGES = {"STAGE_4"}
