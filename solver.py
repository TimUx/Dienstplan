"""
Solver for the TEAM-BASED shift planning problem using OR-Tools CP-SAT.
Configures and runs the solver, returns solution.
"""

from ortools.sat.python import cp_model
from datetime import date, datetime, timedelta
import os
import time
from typing import List, Dict, Tuple, Optional
from entities import Employee, ShiftAssignment, RelaxedConstraint, STANDARD_SHIFT_TYPES, get_shift_type_by_id
from model import ShiftPlanningModel
from planning_report import (
    PlanningReport,
    RuleViolation,
    RelaxedConstraint as PlanningRelaxedConstraint,
    AbsenceInfo,
    AbsenceImpact,
)
from validation import validate_shift_plan
from constraints import (
    add_team_shift_assignment_constraints,
    add_team_rotation_constraints,
    add_employee_weekly_rotation_order_constraints,
    add_employee_team_linkage_constraints,
    add_staffing_constraints,
    add_rest_time_constraints,
    add_consecutive_shifts_constraints,
    add_working_hours_constraints,
    add_weekly_available_employee_constraint,
    add_fairness_objectives,
    add_weekly_shift_type_limit_constraints,
    add_weekend_shift_consistency_constraints,
    add_team_night_shift_consistency_constraints,
    add_shift_sequence_grouping_constraints,
    add_minimum_consecutive_weekday_shifts_constraints,
    add_cross_shift_capacity_enforcement,
    add_total_weekend_staffing_limit
)


def _default_num_workers() -> int:
    """Return a sensible default for the number of CP-SAT search workers.

    Uses all logical CPU cores reported by the OS, capped at 16 (diminishing
    returns above that for CP-SAT) and floored at 1.  Falls back to 4 if the
    OS cannot determine the core count.
    """
    cpu_count = os.cpu_count()
    if cpu_count is None or cpu_count < 1:
        return 4  # safe fallback when os.cpu_count() is unavailable
    return min(cpu_count, 16)


# Soft constraint penalty weights - Priority hierarchy (highest to lowest):
# 1. Operational constraints (200-20000): Rest time, shift grouping, etc. - CRITICAL for safety/compliance
# 2. DAILY_SHIFT_RATIO (200): Enforce shift ordering based on max_staff (F >= S >= N on weekdays)
# 3. TOTAL_WEEKEND_LIMIT (150): Limit total weekend employees to max 12 (NEW)
# 4. CROSS_SHIFT_CAPACITY (150): Prevent overstaffing low-capacity shifts when high-capacity have space
#                                 Ensures N shift doesn't overflow when F/S have available slots
# 5. HOURS_SHORTAGE (100): Employees MUST reach 192h monthly target
# 6. TEAM_PRIORITY (50): Keep teams together, avoid cross-team when team has capacity
# 7. WEEKEND_OVERSTAFFING (50): Strongly discourage weekend overstaffing per shift
# 8. WEEKDAY_UNDERSTAFFING (dynamic 18-45): Encourage filling weekdays to capacity (scaled by max_staff)
# 9. SHIFT_PREFERENCE (±25): Reward high-capacity shifts, penalize low-capacity shifts
# 10. WEEKDAY_OVERSTAFFING (1): Allow weekday overstaffing if needed for target hours
#
# NEW: TOTAL_WEEKEND_LIMIT enforces the requirement "Ein Maximum von 12 Mitarbeitern an 
# Wochenenden sollte nicht überschritten werden" (max 12 employees on weekends total).
# This is separate from per-shift weekend limits and has very high priority (150).
#
# PRIORITY EXPLANATION (per requirements):
# Cross-shift capacity enforcement is prioritized above hours shortage to ensure:
#   "Solange in den anderen Schichten laut Maximale Mitarbeiter Option noch Plätze frei sind,
#    soll die Maximale Grenze der N Schicht nicht überschritten werden."
# Translation: As long as other shifts have free slots, the N shift maximum must not be exceeded.
#
# The solver will prefer:
#   1. Respect operational constraints (rest time, shift grouping, etc.) - CRITICAL
#   2. Maintain correct shift ordering (highest capacity shift gets most workers)
#   3. Limit total weekend employees to 12 (NEW)
#   4. Prevent overstaffing N when F/S have capacity
#   5. Meet target hours for employees
#   6. Fill weekdays to max capacity
# This ensures shifts are distributed according to configured capacities while maintaining
# operational safety and compliance.
#
# SHIFT DISTRIBUTION (dynamic based on max_staff from database):
# Daily ratio constraints ensure F >= S >= N (or other orderings based on max_staff)
# Cross-shift capacity enforcement prevents exceeding N max when F/S have space
# Understaffing weights and shift preferences are calculated proportionally to max_staff
# to ensure shifts with higher capacity get more assignments (F > S > N typically)
HOURS_SHORTAGE_PENALTY_WEIGHT = 100
TEAM_PRIORITY_VIOLATION_WEIGHT = 50  # Must be higher than understaffing weights
WEEKDAY_OVERSTAFFING_PENALTY_WEIGHT = 1
WEEKEND_OVERSTAFFING_PENALTY_WEIGHT = 50
TOTAL_WEEKEND_LIMIT_PENALTY_WEIGHT = 150  # NEW: Limit total weekend employees to 12
# Dynamic weights calculated from shift types:
UNDERSTAFFING_BASE_WEIGHT = 5  # Baseline, scaled by (max_staff / min_max_staff) * multiplier
UNDERSTAFFING_WEIGHT_MULTIPLIER = 4.5  # Ensures sufficient separation to respect max_staff ratios
                                        # Higher value = stronger preference for high-capacity shifts
                                        # Calibrated to achieve ~1.78:1.22:1.0 ratio with 8:6:4 max_staff
SHIFT_PREFERENCE_BASE_WEIGHT = 25  # Additional incentive for high-capacity shifts (reward/penalty)
                                    # Must stay < TEAM_PRIORITY (50) to preserve team cohesion
CROSS_SHIFT_CAPACITY_VIOLATION_WEIGHT = 150  # NEW: Penalty for overstaffing low-capacity shifts when 
                                              # high-capacity shifts have space. MUST be higher than 
                                              # HOURS_SHORTAGE (100) to prevent N overflow when F/S have capacity

# Fallback penalty weight: used when minimum staffing is relaxed to a soft constraint.
# Must be extremely high to signal a severely sub-optimal plan to the user.
MIN_STAFFING_RELAXED_PENALTY_WEIGHT = 200_000

# Expected performance improvements from solver optimizations:
# - Warmstart hints (AddHint): 20-40% faster first feasible solution on re-planning.
#   The solver starts near a known-good solution instead of from scratch.
# - Solution callbacks: Real-time logging of each improving solution; when the solver
#   hits the time limit with status FEASIBLE, the best solution found is already
#   retained by the solver and accessible via solver.Value(). The callback provides
#   visibility into how quickly and how much the objective improved over time.
#   For fallback stages (relaxation_level > 0) the callback calls StopSearch()
#   immediately after the first feasible solution – no optimization needed there.
# - PORTFOLIO strategy (default): Runs multiple parallel workers with different
#   heuristics; typically 10-30% faster than FIXED_SEARCH on large diverse instances.
# - FIXED_SEARCH strategy: Deterministic ordering; useful for debugging or comparing
#   solutions across runs. May be slower on heterogeneous instances.
# - linearization_level=2: Stronger LP relaxation provides tighter lower bounds,
#   enabling faster pruning; typically speeds up scheduling problems by 15-40%.
# - interleave_search=True (PORTFOLIO + ≥4 workers): Distributes wall-clock time
#   more evenly across sub-solvers so no single worker monopolises the budget.
# - symmetry_level=2: Automatic symmetry-breaking reduces equivalent subtrees;
#   particularly effective for the repeated team/week structure of this model.
# - random_seed: Fixes the pseudo-random choices inside CP-SAT for reproducible
#   results across runs with identical inputs.


class ShiftPlanSolutionCallback(cp_model.CpSolverSolutionCallback):
    """
    Callback that logs each improving solution found during CP-SAT search.

    Performance benefit: Called by the solver whenever a new (better) feasible
    solution is found. Logs each improvement with objective value and elapsed time,
    providing visibility into solver progress. The solver itself retains the best
    solution for retrieval via solver.Value() after the search completes.

    When the solver reaches its time limit with status FEASIBLE, the best solution
    found during the search is automatically retained by the solver object - no
    separate storage in this callback is required. The callback serves primarily
    as a progress monitor.

    When ``stop_after_first_feasible=True`` the search is halted immediately after
    the very first solution is found.  This is the correct behaviour for fallback
    stages (relaxation_level > 0) where feasibility – not optimality – is the goal
    and further optimisation would only waste time.
    """

    def __init__(self, stop_after_first_feasible: bool = False):
        super().__init__()
        self._solution_count = 0
        self._best_objective = None  # None until first solution found (works for both min and max)
        self._start_time = None
        self._stop_after_first_feasible = stop_after_first_feasible

    def OnSolutionCallback(self):
        """Called by the solver each time a new improving solution is found."""
        current_time = time.time()
        if self._start_time is None:
            self._start_time = current_time

        elapsed = current_time - self._start_time
        current_obj = self.ObjectiveValue()

        # Track only improving solutions (lower objective = better for minimization).
        # _best_objective starts as None so the first solution is always recorded.
        if self._best_objective is None or current_obj < self._best_objective:
            self._best_objective = current_obj
            self._solution_count += 1
            print(f"  → Solution #{self._solution_count}: objective={current_obj:.0f}, elapsed={elapsed:.1f}s")

        # For fallback stages feasibility is sufficient; stop as soon as we have one.
        if self._stop_after_first_feasible and self._solution_count >= 1:
            self.StopSearch()

    @property
    def solution_count(self) -> int:
        """Total number of improving solutions found during the search."""
        return self._solution_count

    @property
    def best_objective(self) -> Optional[float]:
        """Best (lowest) objective value found so far, or None if no solution yet."""
        return self._best_objective


class ShiftPlanningSolver:
    """
    Solver for the shift planning problem.
    """
    
    def __init__(
        self,
        planning_model: ShiftPlanningModel,
        time_limit_seconds: Optional[int] = None,
        num_workers: Optional[int] = None,
        global_settings: Dict = None,
        db_path: str = "dienstplan.db",
        search_strategy: str = "PORTFOLIO",
        warm_start_shifts: Optional[Dict[Tuple[int, date], str]] = None,
        relaxation_level: int = 0,
        random_seed: Optional[int] = None,
    ):
        """
        Initialize the solver.
        
        Args:
            planning_model: The shift planning model
            time_limit_seconds: Maximum time for solver in seconds. None (default) means no limit.
            num_workers: Number of parallel workers for solver. None (default) uses
                _default_num_workers() which auto-detects available CPU cores (capped at 16).
            global_settings: Dict with global settings from database (optional)
                - min_rest_hours: Min rest hours between shifts (default 11)
                Note: Max consecutive shift settings are now per-shift-type (see ShiftType.max_consecutive_days)
            db_path: Path to database file for loading rotation patterns (default: dienstplan.db)
            search_strategy: Search branching strategy for the solver. Options:
                - "PORTFOLIO" (default): Runs multiple parallel heuristics; best for
                  complex multi-team problems with num_workers > 1. Typically 10-30%
                  faster than FIXED_SEARCH on diverse problem instances.
                - "FIXED_SEARCH": Deterministic variable/value ordering. Useful for
                  debugging, reproducibility comparisons, or simpler instances.
                - "AUTOMATIC": Let OR-Tools choose the strategy automatically.
            warm_start_shifts: Optional dict mapping (employee_id, date) -> shift_code
                for previous shift assignments to use as solver hints (AddHint).
                Typically populated with the previous month's complete schedule.
                Expected improvement: 20-40% reduction in time to first feasible
                solution for re-planning scenarios where the shift structure is similar
                to the previous period (same rotation pattern, same team composition).
            relaxation_level: Controls which hard constraints are relaxed for fallback solving.
                - 0 (default): All hard constraints enforced normally (normal solve).
                - 1: Minimum staffing (H3) is treated as a soft constraint with a very
                     high penalty weight (MIN_STAFFING_RELAXED_PENALTY_WEIGHT).
                - 2: Minimum staffing soft + team rotation pattern constraints are skipped,
                     allowing teams to use any shift assignment each week.
            random_seed: Optional integer seed for the CP-SAT pseudo-random number generator.
                When set, results are reproducible across identical runs. Useful for
                regression testing and performance comparisons. None (default) lets
                OR-Tools choose its own seed (non-deterministic).
        """
        self.planning_model = planning_model
        self.time_limit_seconds = time_limit_seconds
        self.num_workers = num_workers if num_workers is not None else _default_num_workers()
        self.solution = None
        self.status = None
        self.db_path = db_path
        self.search_strategy = search_strategy
        self.warm_start_shifts = warm_start_shifts
        self.relaxation_level = relaxation_level
        self.random_seed = random_seed
        # Records which constraints were relaxed (populated by add_all_constraints)
        self.relaxed_constraints: List[str] = []
        # Penalty groups: category name → list of (cp_var, weight) tuples.
        # Populated during add_all_constraints; used by compute_penalty_breakdown().
        self.penalty_groups: Dict[str, List[Tuple]] = {}
        
        # Store global settings
        if global_settings is None:
            global_settings = {}
        # Note: max_consecutive_shifts_weeks and max_consecutive_night_shifts_weeks are deprecated
        # These settings are now configured per shift type (ShiftType.max_consecutive_days)
        self.min_rest_hours = global_settings.get('min_rest_hours', 11)
    
    def add_all_constraints(self):
        """
        Add all constraints to the TEAM-BASED model with CROSS-TEAM support.
        """
        model = self.planning_model.get_model()
        (team_shift, employee_active, employee_weekend_shift, 
         employee_cross_team_shift, employee_cross_team_weekend) = self.planning_model.get_variables()
        employees = self.planning_model.employees
        teams = self.planning_model.teams
        dates = self.planning_model.dates
        weeks = self.planning_model.weeks
        shift_codes = self.planning_model.shift_codes
        absences = self.planning_model.absences
        shift_types = self.planning_model.shift_types
        
        # Get locked assignments
        locked_team_shift = self.planning_model.locked_team_shift
        
        print("Adding constraints...")
        
        # CORE TEAM-BASED CONSTRAINTS
        print("  - Team shift assignment (exactly one shift per team per week)")
        add_team_shift_assignment_constraints(model, team_shift, teams, weeks, shift_codes, shift_types)
        
        # Try to load rotation patterns from database
        rotation_patterns = None
        try:
            from data_loader import load_rotation_groups_from_db
            rotation_patterns = load_rotation_groups_from_db(self.db_path)
            if rotation_patterns:
                print(f"  - Team rotation (DATABASE-DRIVEN: {len(rotation_patterns)} rotation pattern(s) loaded)")
                for group_id, pattern in rotation_patterns.items():
                    print(f"    • Rotation group {group_id}: {' → '.join(pattern)}")
            else:
                print("  - Team rotation (FALLBACK: Using hardcoded F → N → S pattern)")
        except Exception as e:
            print(f"  - Team rotation (FALLBACK: Database load failed, using hardcoded F → N → S pattern)")
            print(f"    Error: {e}")
            rotation_patterns = None
        
        # Level 2+: skip the hard rotation pattern constraint so teams can use any shift order
        if self.relaxation_level >= 2:
            print("  - [FALLBACK 2] Team rotation constraint SKIPPED (relaxed for feasibility)")
            self.relaxed_constraints.append(
                "Teamrotation (F→N→S): Reihenfolge nicht mehr erzwungen – Teams können beliebige Schichten wählen"
            )
        else:
            add_team_rotation_constraints(model, team_shift, teams, weeks, shift_codes, locked_team_shift, shift_types, rotation_patterns)
        
        print("  - Employee weekly rotation order (enforce F → N → S transition order)")
        rotation_order_penalties = add_employee_weekly_rotation_order_constraints(
            model, employee_active, employee_weekend_shift, team_shift,
            employee_cross_team_shift, employee_cross_team_weekend,
            employees, teams, dates, weeks, shift_codes)
        
        print("  - Employee-team linkage (derive employee activity from team shifts)")
        add_employee_team_linkage_constraints(model, team_shift, employee_active, employee_cross_team_shift, employees, teams, dates, weeks, shift_codes, absences, employee_weekend_shift, employee_cross_team_weekend)
        
        # STAFFING AND WORKING CONDITIONS
        relax_min = self.relaxation_level >= 1
        if relax_min:
            print("  - Staffing requirements (min SOFT with penalty 200000 / max soft, including cross-team)")
            self.relaxed_constraints.append(
                "Mindestbesetzung (H3): Als Soft-Constraint mit Strafgewicht 200.000 behandelt – Unterschreitungen sind möglich"
            )
        else:
            print("  - Staffing requirements (min hard / max soft, including cross-team)")
        # NEW: Collect separate penalties for weekday/weekend overstaffing and weekday understaffing by shift
        # Also collect team priority violations (cross-team usage when team has capacity)
        weekday_overstaffing, weekend_overstaffing, weekday_understaffing_by_shift, team_priority_violations, min_staffing_violations = add_staffing_constraints(
            model, employee_active, employee_weekend_shift, team_shift, 
            employee_cross_team_shift, employee_cross_team_weekend, 
            employees, teams, dates, weeks, shift_codes, shift_types,
            relax_min_staffing=relax_min)
        
        print("  - Total weekend staffing limit (max 12 employees across all shifts)")
        total_weekend_overstaffing = add_total_weekend_staffing_limit(
            model, employee_active, employee_weekend_shift, 
            employee_cross_team_shift, employee_cross_team_weekend, team_shift,
            employees, teams, dates, weeks, shift_codes, max_total_weekend_staff=12)
        
        print("  - Cross-shift capacity enforcement (prevent N overflow when F/S have capacity)")
        cross_shift_capacity_violations = add_cross_shift_capacity_enforcement(
            model, employee_active, employee_weekend_shift, team_shift,
            employee_cross_team_shift, employee_cross_team_weekend,
            employees, teams, dates, weeks, shift_codes, shift_types)
        
        print("  - Daily shift ratio constraints (ensure F >= S on weekdays)")
        from constraints import add_daily_shift_ratio_constraints
        daily_ratio_violations = add_daily_shift_ratio_constraints(
            model, employee_active, employee_weekend_shift, team_shift,
            employee_cross_team_shift, employee_cross_team_weekend,
            employees, teams, dates, weeks, shift_codes, shift_types)
        
        print("  - Rest time constraints (11h min, soft penalties for violations)")
        rest_violation_penalties = add_rest_time_constraints(model, employee_active, employee_weekend_shift, team_shift, 
                                 employee_cross_team_shift, employee_cross_team_weekend, 
                                 employees, dates, weeks, shift_codes, teams,
                                 previous_employee_shifts=self.planning_model.previous_employee_shifts)
        
        # Shift stability constraint (prevent shift hopping)
        print("  - Shift stability constraints (prevent rapid shift changes like N→S→N)")
        from constraints import add_shift_stability_constraints
        shift_hopping_penalties = add_shift_stability_constraints(
            model, employee_active, employee_weekend_shift, team_shift,
            employee_cross_team_shift, employee_cross_team_weekend,
            employees, dates, weeks, shift_codes, teams)
        
        # Shift sequence grouping constraint (prevent isolated shift types)
        print("  - Shift sequence grouping constraints (prevent isolated shift types like S-S-F-S-S)")
        print("    * Including ultra-high penalties (20000) for A-B-A patterns within 10-day windows")
        shift_grouping_penalties = add_shift_sequence_grouping_constraints(
            model, employee_active, employee_weekend_shift, team_shift,
            employee_cross_team_shift, employee_cross_team_weekend,
            employees, dates, weeks, shift_codes, teams)
        
        # Minimum consecutive weekday shifts constraint (enforce at least 2 consecutive days for same shift during weekdays)
        print("  - Minimum consecutive weekday shifts constraints (min 2 consecutive days for same shift Mon-Fri)")
        min_consecutive_weekday_penalties = add_minimum_consecutive_weekday_shifts_constraints(
            model, employee_active, employee_weekend_shift, team_shift,
            employee_cross_team_shift, employee_cross_team_weekend,
            employees, dates, weeks, shift_codes, teams)
        
        # Weekly shift type limit constraint (max 2 different shift types per week)
        print("  - Weekly shift type limit constraints (max 2 shift types per week)")
        weekly_shift_type_penalties = add_weekly_shift_type_limit_constraints(
            model, employee_active, employee_weekend_shift, team_shift,
            employee_cross_team_shift, employee_cross_team_weekend,
            employees, teams, dates, weeks, shift_codes, max_shift_types_per_week=2)
        
        # Weekend shift consistency constraint (no shift type changes within weekends)
        print("  - Weekend shift consistency constraints (prevent shift changes Fri→Sat/Sun)")
        weekend_consistency_penalties = add_weekend_shift_consistency_constraints(
            model, employee_active, employee_weekend_shift, team_shift,
            employee_cross_team_shift, employee_cross_team_weekend,
            employees, teams, dates, weeks, shift_codes)
        
        # Team night shift consistency constraint (discourage cross-team night shifts)
        print("  - Team night shift consistency constraints (night shifts stay in night shift teams)")
        night_team_consistency_penalties = add_team_night_shift_consistency_constraints(
            model, employee_active, employee_weekend_shift, team_shift,
            employee_cross_team_shift, employee_cross_team_weekend,
            employees, teams, dates, weeks, shift_codes)
        
        # Consecutive shifts constraint (HARD within period, SOFT for cross-month boundaries)
        # Limits consecutive working days per shift type (HARD: model.Add constraints)
        # Cross-month boundary violations are high-weight soft (50,000 per violation)
        print("  - Consecutive shifts constraints (HARD within period: max consecutive days per shift type)")
        consecutive_violation_penalties = add_consecutive_shifts_constraints(
            model, employee_active, employee_weekend_shift, team_shift,
            employee_cross_team_shift, employee_cross_team_weekend, 
            employees, teams, dates, weeks, shift_codes, shift_types,
            self.planning_model.previous_employee_shifts)
        
        print("  - Working hours constraints (HARD: min 192h/month, SOFT: proportional target)")
        hours_shortage_objectives = add_working_hours_constraints(
            model, employee_active, employee_weekend_shift, team_shift, 
            employee_cross_team_shift, employee_cross_team_weekend, 
            employees, teams, dates, weeks, shift_codes, shift_types, absences)
        
        # BLOCK SCHEDULING FOR CROSS-TEAM
        print("  - Weekly block constraints (Mon-Fri blocks for cross-team assignments)")
        from constraints import add_weekly_block_constraints
        add_weekly_block_constraints(model, employee_active, employee_cross_team_shift, 
                                    employees, dates, weeks, shift_codes, absences)
        
        # BLOCK SCHEDULING FOR TEAM MEMBERS (FLEXIBLE)
        print("  - Team member block constraints (prevent isolated days, encourage full blocks)")
        from constraints import add_team_member_block_constraints
        block_objective_vars = add_team_member_block_constraints(
            model, employee_active, employee_weekend_shift, team_shift,
            employees, teams, dates, weeks, shift_codes, absences)
        
        # DISABLED: Weekly available employee constraint - conflicts with configured weekly_working_hours requirement
        # The constraint forces at least 1 employee to have 0 working days per week,
        # which prevents employees from reaching their target hours (e.g., 48h/week = 6 days)
        # See WORKING_HOURS_FIX.md for full analysis
        # 
        # print("  - Weekly available employee constraint (at least 1 free per week)")
        # add_weekly_available_employee_constraint(model, employee_active, employee_weekend_shift, employees, teams, weeks)
        
        # SOFT CONSTRAINTS (OPTIMIZATION)
        print("  - Fairness objectives (per-employee, year-long, including block scheduling)")
        objective_terms = add_fairness_objectives(
            model, employee_active, employee_weekend_shift, team_shift,
            employee_cross_team_shift, employee_cross_team_weekend,
            employees, teams, dates, weeks, shift_codes,
            self.planning_model.ytd_weekend_counts,
            self.planning_model.ytd_night_counts,
            self.planning_model.ytd_holiday_counts
        )
        
        # Add block scheduling objectives (encourage full blocks)
        # These are bonuses, so we want to maximize them (minimize negative sum)
        if block_objective_vars:
            print(f"  Adding {len(block_objective_vars)} block scheduling bonus objectives...")
            for bonus_var in block_objective_vars:
                objective_terms.append(-bonus_var)  # Negative because we minimize
            self.penalty_groups.setdefault("Blockplanung Bonus (negativ = Belohnung)", []).extend(
                (v, -1) for v in block_objective_vars
            )
        
        # Add consecutive shifts cross-month boundary penalties (high-weight soft, 50,000 per violation)
        if consecutive_violation_penalties:
            print(f"  Adding {len(consecutive_violation_penalties)} consecutive shifts cross-month boundary penalties (weight 50,000)...")
            for penalty_var in consecutive_violation_penalties:
                objective_terms.append(penalty_var)  # Already weighted (50,000 per cross-month violation)
            self.penalty_groups.setdefault("Aufeinanderfolgende Schichten (Monatsgrenze)", []).extend(
                (v, 1) for v in consecutive_violation_penalties
            )
        
        # Add rest time violation penalties (strongly discourage but allow for feasibility)
        if rest_violation_penalties:
            print(f"  Adding {len(rest_violation_penalties)} rest time violation penalties...")
            for penalty_var in rest_violation_penalties:
                objective_terms.append(penalty_var)  # Already weighted (50 or 500 per violation)
            self.penalty_groups.setdefault("Ruhezeiten-Verletzung", []).extend(
                (v, 1) for v in rest_violation_penalties
            )
        
        # Add rotation order violation penalties (VERY STRONGLY discourage breaking F → N → S order)
        if rotation_order_penalties:
            print(f"  Adding {len(rotation_order_penalties)} rotation order violation penalties...")
            for penalty_var in rotation_order_penalties:
                objective_terms.append(penalty_var)  # Already weighted (10000 per violation)
            self.penalty_groups.setdefault("Rotationsreihenfolge (F→N→S)", []).extend(
                (v, 1) for v in rotation_order_penalties
            )
        
        # Add shift hopping penalties (discourage rapid shift changes)
        if shift_hopping_penalties:
            print(f"  Adding {len(shift_hopping_penalties)} shift hopping penalties...")
            for penalty_var in shift_hopping_penalties:
                objective_terms.append(penalty_var)  # Already weighted (200 per hopping pattern)
            self.penalty_groups.setdefault("Schicht-Hopping", []).extend(
                (v, 1) for v in shift_hopping_penalties
            )
        
        # Add shift grouping penalties (prevent isolated shift types)
        if shift_grouping_penalties:
            print(f"  Adding {len(shift_grouping_penalties)} shift grouping penalties...")
            for penalty_var in shift_grouping_penalties:
                objective_terms.append(penalty_var)  # Already weighted (100000-500000 per isolation)
            self.penalty_groups.setdefault("Schichtgruppierung (isolierte Typen)", []).extend(
                (v, 1) for v in shift_grouping_penalties
            )
        
        # Add minimum consecutive weekday shifts penalties (strongly enforce min 2 consecutive days during weekdays)
        if min_consecutive_weekday_penalties:
            print(f"  Adding {len(min_consecutive_weekday_penalties)} minimum consecutive weekday shift penalties...")
            for penalty_var in min_consecutive_weekday_penalties:
                objective_terms.append(penalty_var)  # Already weighted (6000-8000 per violation)
            self.penalty_groups.setdefault("Min. aufeinanderfolgende Werktags-Schichten", []).extend(
                (v, 1) for v in min_consecutive_weekday_penalties
            )
        
        # Add weekly shift type limit penalties (strongly discourage > 2 shift types per week)
        if weekly_shift_type_penalties:
            print(f"  Adding {len(weekly_shift_type_penalties)} weekly shift type diversity penalties...")
            for penalty_var in weekly_shift_type_penalties:
                objective_terms.append(penalty_var)  # Already weighted (500 per violation)
            self.penalty_groups.setdefault("Wöchentliche Schichttyp-Vielfalt", []).extend(
                (v, 1) for v in weekly_shift_type_penalties
            )
        
        # Add weekend consistency penalties (discourage shift changes from Fri to Sat/Sun)
        if weekend_consistency_penalties:
            print(f"  Adding {len(weekend_consistency_penalties)} weekend consistency penalties...")
            for penalty_var in weekend_consistency_penalties:
                objective_terms.append(penalty_var)  # Already weighted (300 per mismatch)
            self.penalty_groups.setdefault("Wochenend-Konsistenz", []).extend(
                (v, 1) for v in weekend_consistency_penalties
            )
        
        # Add team night shift consistency penalties (strongly discourage cross-team night shifts)
        if night_team_consistency_penalties:
            print(f"  Adding {len(night_team_consistency_penalties)} team night shift consistency penalties...")
            for penalty_var in night_team_consistency_penalties:
                objective_terms.append(penalty_var)  # Already weighted (600 per violation)
            self.penalty_groups.setdefault("Nachtschicht-Team-Konsistenz", []).extend(
                (v, 1) for v in night_team_consistency_penalties
            )
        
        # Add daily shift ratio penalties (enforce shift ordering based on max_staff capacity)
        if daily_ratio_violations:
            print(f"  Adding {len(daily_ratio_violations)} daily shift ratio penalties (enforce capacity-based ordering)...")
            for penalty_var in daily_ratio_violations:
                objective_terms.append(penalty_var)  # Already weighted (200 per violation - higher than hours shortage)
            self.penalty_groups.setdefault("Tagesschicht-Verhältnis (Kapazitätsreihenfolge)", []).extend(
                (v, 1) for v in daily_ratio_violations
            )
        
        # Add cross-shift capacity violation penalties (prevent overstaffing low-capacity shifts when high-capacity have space)
        if cross_shift_capacity_violations:
            print(f"  Adding {len(cross_shift_capacity_violations)} cross-shift capacity violation penalties (weight {CROSS_SHIFT_CAPACITY_VIOLATION_WEIGHT}x)...")
            for penalty_var in cross_shift_capacity_violations:
                objective_terms.append(penalty_var * CROSS_SHIFT_CAPACITY_VIOLATION_WEIGHT)
            self.penalty_groups.setdefault("Schicht-Kapazitätsüberschreitung (N-Overflow)", []).extend(
                (v, CROSS_SHIFT_CAPACITY_VIOLATION_WEIGHT) for v in cross_shift_capacity_violations
            )
        
        # Add minimum staffing violation penalties (only active when min staffing is relaxed)
        # Weight MIN_STAFFING_RELAXED_PENALTY_WEIGHT (200,000) is intentionally very high so
        # the solver treats understaffing as an extreme last resort.
        if min_staffing_violations:
            print(f"  Adding {len(min_staffing_violations)} minimum staffing violation penalties (weight {MIN_STAFFING_RELAXED_PENALTY_WEIGHT}x - FALLBACK MODE)...")
            for viol_var in min_staffing_violations:
                objective_terms.append(viol_var * MIN_STAFFING_RELAXED_PENALTY_WEIGHT)
            self.penalty_groups.setdefault("Mindestbesetzung (Fallback-Modus)", []).extend(
                (v, MIN_STAFFING_RELAXED_PENALTY_WEIGHT) for v in min_staffing_violations
            )
        
        # Add hours shortage objectives (minimize shortage from target hours)
        # HIGHEST PRIORITY: Employees must reach their 192h minimum target
        # Weight defined at module level as HOURS_SHORTAGE_PENALTY_WEIGHT
        if hours_shortage_objectives:
            print(f"  Adding {len(hours_shortage_objectives)} target hours shortage penalties (weight {HOURS_SHORTAGE_PENALTY_WEIGHT}x - HIGHEST PRIORITY)...")
            for shortage_var in hours_shortage_objectives:
                objective_terms.append(shortage_var * HOURS_SHORTAGE_PENALTY_WEIGHT)
            self.penalty_groups.setdefault("Stunden-Ziel-Unterschreitung", []).extend(
                (v, HOURS_SHORTAGE_PENALTY_WEIGHT) for v in hours_shortage_objectives
            )
        
        # Calculate total days once for temporal weighting calculations
        total_days = len(dates)
        
        # Add overstaffing penalties - strongly discourage weekend overstaffing
        # Per requirements: Fill weekdays to capacity BEFORE overstaffing weekends
        # Weekend overstaffing (50) must be MORE expensive than weekday understaffing (20/12/5)
        # This ensures weekdays are filled to max capacity before any weekend overstaffing
        # Weights defined at module level for easy adjustment
        if weekday_overstaffing:
            print(f"  Adding {len(weekday_overstaffing)} weekday overstaffing penalties (weight {WEEKDAY_OVERSTAFFING_PENALTY_WEIGHT}x - acceptable if needed)...")
            for overstaff_var in weekday_overstaffing:
                objective_terms.append(overstaff_var * WEEKDAY_OVERSTAFFING_PENALTY_WEIGHT)
            self.penalty_groups.setdefault("Werktag-Überbesetzung", []).extend(
                (v, WEEKDAY_OVERSTAFFING_PENALTY_WEIGHT) for v in weekday_overstaffing
            )
        
        if weekend_overstaffing:
            print(f"  Adding {len(weekend_overstaffing)} weekend overstaffing penalties (base weight {WEEKEND_OVERSTAFFING_PENALTY_WEIGHT}x with temporal bias - STRONGLY avoid late month)...")
            for overstaff_var, overstaff_date in weekend_overstaffing:
                # Calculate day index (0-based) within the planning period
                day_index = dates.index(overstaff_date)
                
                # Calculate temporal multiplier for OVERSTAFFING: ranges from 0.5 (early) to 2.0 (late)
                # Formula: 0.5 + 1.5 * (day_index / total_days)
                # Day 0: 0.5x (less penalty early), Middle: 1.25x, Last day: 2.0x (strong penalty late)
                # This makes overstaffing late weekends MUCH more expensive than early weekends
                temporal_multiplier = 0.5 + 1.5 * (day_index / len(dates))
                
                # Apply both base weight and temporal multiplier
                # Use round() instead of int() to preserve precision
                final_weight = round(WEEKEND_OVERSTAFFING_PENALTY_WEIGHT * temporal_multiplier)
                
                objective_terms.append(overstaff_var * final_weight)
                self.penalty_groups.setdefault("Wochenend-Überbesetzung (zeitgewichtet)", []).append(
                    (overstaff_var, final_weight)
                )
        
        # Add TOTAL weekend staffing limit penalties (NEW: max 12 employees across all shifts)
        # This has VERY HIGH priority (150) - higher than hours shortage (100)
        # This ensures weekends never exceed 12 total employees unless absolutely critical
        if total_weekend_overstaffing:
            print(f"  Adding {len(total_weekend_overstaffing)} total weekend staffing limit penalties (weight {TOTAL_WEEKEND_LIMIT_PENALTY_WEIGHT}x - CRITICAL limit)...")
            for overstaff_var, overstaff_date in total_weekend_overstaffing:
                # Apply high priority weight to enforce max 12 total employees on weekends
                objective_terms.append(overstaff_var * TOTAL_WEEKEND_LIMIT_PENALTY_WEIGHT)
            self.penalty_groups.setdefault("Gesamtes Wochenend-Limit (max 12)", []).extend(
                (v, TOTAL_WEEKEND_LIMIT_PENALTY_WEIGHT) for v, _ in total_weekend_overstaffing
            )
        
        # Add weekday understaffing penalties with SHIFT-SPECIFIC PRIORITY weights
        # AND TEMPORAL BIAS (prefer earlier dates)
        # Priority order is calculated dynamically based on max_staff values from database
        # Shifts with higher max_staff get higher priority (more people to assign)
        # Temporal order: Earlier dates > Later dates (to avoid clustering shifts at month end)
        # Higher weight = higher priority to fill
        # Use VERY strong differentials to ensure priority overrides other soft constraints
        
        # DYNAMIC CALCULATION: Build priority weights based on max_staff_weekday from database
        # This ensures the distribution respects the configured shift capacity ratios
        # For example: if F has max 8 and S has max 6, F gets proportionally higher priority
        shift_priority_weights = {}
        
        # Find the shift with the smallest max_staff to use as baseline
        max_staff_values = {}
        for st in shift_types:
            if st.code in shift_codes:
                max_staff_values[st.code] = st.max_staff_weekday
        
        if max_staff_values:
            min_max_staff = min(max_staff_values.values())
            # Calculate weights proportional to max_staff, with UNDERSTAFFING_BASE_WEIGHT as baseline
            # Scale by (max_staff / min_max_staff) * UNDERSTAFFING_WEIGHT_MULTIPLIER
            # Example: if min_max_staff=4 and a shift has max_staff=8:
            #   weight = 5 * (8/4) * 2.5 = 25
            # This creates proper priority ratios: F(8) gets higher weight than S(6)
            # The multiplier (2.5) ensures sufficient separation while staying below
            # TEAM_PRIORITY_VIOLATION_WEIGHT (50) to preserve team cohesion
            #
            # SAFETY: Cap weights to stay below team priority to maintain documented hierarchy
            max_allowed_weight = TEAM_PRIORITY_VIOLATION_WEIGHT - 1
            for shift_code, max_staff in max_staff_values.items():
                calculated_weight = UNDERSTAFFING_BASE_WEIGHT * (max_staff / min_max_staff) * UNDERSTAFFING_WEIGHT_MULTIPLIER
                shift_priority_weights[shift_code] = min(round(calculated_weight), max_allowed_weight)
            print(f"  Calculated dynamic shift priority weights based on max_staff: {shift_priority_weights}")
        else:
            # Fallback to original hardcoded weights if no shift types available
            shift_priority_weights = {
                'F': 20,  # Früh/Early - highest priority (4x night)
                'S': 12,  # Spät/Late - medium priority (2.4x night)
                'N': 5    # Nacht/Night - lowest priority (baseline)
            }
        
        # Calculate temporal weighting factor
        # Earlier dates get higher penalties for understaffing, encouraging solver to fill them first
        # This prevents clustering of shifts at the end of the month
        # (total_days already calculated above)
        
        for shift_code, understaffing_list in weekday_understaffing_by_shift.items():
            if understaffing_list:
                base_weight = shift_priority_weights.get(shift_code, 5)  # Default to 5 if shift not in priority map
                shift_name = {'F': 'Früh', 'S': 'Spät', 'N': 'Nacht'}.get(shift_code, shift_code)
                print(f"  Adding {len(understaffing_list)} {shift_name} ({shift_code}) weekday understaffing penalties (base weight {base_weight}x with temporal bias)...")
                
                for understaff_var, understaff_date in understaffing_list:
                    # Calculate day index (0-based) within the planning period
                    day_index = dates.index(understaff_date)
                    
                    # Calculate temporal multiplier: ranges from 1.5 (early) to 0.5 (late)
                    # Formula: 1.5 - (day_index / total_days)
                    # Day 0: 1.5x, Middle day: 1.0x, Last day: 0.5x
                    # This makes understaffing early days more expensive than late days
                    temporal_multiplier = 1.5 - (day_index / total_days)
                    
                    # Apply both shift priority weight and temporal multiplier
                    # Use round() instead of int() to preserve precision
                    final_weight = round(base_weight * temporal_multiplier)
                    
                    objective_terms.append(understaff_var * final_weight)
                    self.penalty_groups.setdefault(
                        f"Werktag-Unterbesetzung {shift_name} ({shift_code})", []
                    ).append((understaff_var, final_weight))
        
        # NEW: Add team priority violation penalties
        # Strongly penalize using cross-team workers when own team has unfilled capacity
        # Weight defined at module level as TEAM_PRIORITY_VIOLATION_WEIGHT
        # This weight MUST be higher than all understaffing penalties (which are dynamically calculated)
        # to guarantee team cohesion takes priority over shift filling optimization
        if team_priority_violations:
            print(f"  Adding {len(team_priority_violations)} team priority violation penalties (weight {TEAM_PRIORITY_VIOLATION_WEIGHT}x)...")
            for violation_var in team_priority_violations:
                objective_terms.append(violation_var * TEAM_PRIORITY_VIOLATION_WEIGHT)
            self.penalty_groups.setdefault("Team-Priorität (Cross-Team)", []).extend(
                (v, TEAM_PRIORITY_VIOLATION_WEIGHT) for v in team_priority_violations
            )
        
        # NEW: Add shift type preference objective based on max_staff ratios
        # Count total staff assigned to each shift and apply inverse priority weights
        # Shifts with higher max_staff get rewarded (negative penalty = bonus)
        # Shifts with lower max_staff get penalized to discourage overuse
        print("  Adding shift type preference objectives (proportional to max_staff)...")
        shift_penalty_weights = {}
        
        # Calculate penalty/reward weights based on max_staff values
        # Shifts with higher max_staff get negative weights (rewards)
        # Shifts with lower max_staff get positive weights (penalties)
        # Weight magnitude defined as SHIFT_PREFERENCE_BASE_WEIGHT to balance with team priority
        if max_staff_values:
            max_of_max_staff = max(max_staff_values.values())
            for shift_code, max_staff in max_staff_values.items():
                # Formula: SHIFT_PREFERENCE_BASE_WEIGHT * (1 - 2 * max_staff / max_of_max_staff)
                # Range: [-SHIFT_PREFERENCE_BASE_WEIGHT, +SHIFT_PREFERENCE_BASE_WEIGHT]
                # If max_staff = max_of_max_staff: 15 * (1 - 2) = -15 (maximum reward)
                # If max_staff = max_of_max_staff/2: 15 * (1 - 1) = 0 (neutral)
                # If max_staff → 0: approaches +15 (maximum penalty, though unrealistic)
                # This balances shift preference with team cohesion (TEAM_PRIORITY_VIOLATION_WEIGHT = 50)
                shift_penalty_weights[shift_code] = round(
                    SHIFT_PREFERENCE_BASE_WEIGHT * (1 - 2 * max_staff / max_of_max_staff)
                )
            print(f"    Shift penalty/reward weights (negative=reward): {shift_penalty_weights}")
        else:
            # Fallback to original hardcoded weights
            shift_penalty_weights = {
                'F': -3,  # Früh/Early - REWARD (negative penalty = bonus)
                'S': 1,   # Spät/Late - slight penalty (less preferred than F)
                'N': 3    # Nacht/Night - stronger PENALTY (discourage when possible)
            }
        
        # Pre-build day→week_idx map for O(1) lookup (avoid re-scanning weeks per date)
        date_to_week_idx: Dict[date, int] = {}
        for w_idx, week_dates in enumerate(weeks):
            for wd in week_dates:
                date_to_week_idx[wd] = w_idx

        # Pre-build per-team, per-day count of active members (constant — not a CP var)
        # active_team_members[team_id][d] = number of employees in team that have an
        # employee_active entry for date d (i.e., are not absent on that day).
        active_team_members: Dict[int, Dict[date, int]] = {}
        for team in teams:
            active_team_members[team.id] = {}
            for d in dates:
                if d.weekday() >= 5:
                    continue
                count = sum(
                    1 for emp in employees
                    if emp.team_id == team.id and (emp.id, d) in employee_active
                )
                if count:
                    active_team_members[team.id][d] = count

        # Build shift preference objective using team-level linear terms.
        # This replaces the previous per-employee bool × bool multiplication approach
        # (O(employees × weekdays × shifts) non-linear constraints) with O(teams × weeks
        # × shifts) linear coefficient additions — dramatically reducing model complexity.
        for d in dates:
            if d.weekday() >= 5:  # Skip weekends
                continue

            week_idx = date_to_week_idx.get(d)
            if week_idx is None:
                continue

            for shift in shift_codes:
                if shift not in shift_penalty_weights:
                    continue

                weight = shift_penalty_weights[shift]

                # Team-level contribution: team_shift[t,w,s] * active_count (linear)
                for team in teams:
                    if (team.id, week_idx, shift) not in team_shift:
                        continue
                    count = active_team_members.get(team.id, {}).get(d, 0)
                    if count:
                        # team_shift is a BoolVar; multiplying by constant count is linear.
                        objective_terms.append(team_shift[(team.id, week_idx, shift)] * (count * weight))

                # Cross-team workers: these are individual BoolVars, add directly.
                for emp in employees:
                    if (emp.id, d, shift) in employee_cross_team_shift:
                        objective_terms.append(employee_cross_team_shift[(emp.id, d, shift)] * weight)
        
        # NEW: Add temporal penalty for weekend work (discourage working late-month weekends)
        # This encourages distributing weekend shifts earlier in the month
        # Apply to BOTH regular team weekend work AND cross-team weekend work
        print("  Adding temporal weekend work penalties (discourage late-month weekends)...")
        weekend_work_penalties = 0
        # (total_days already calculated above)
        
        # Penalize regular team weekend assignments
        for emp in employees:
            for d in dates:
                if d.weekday() < 5:  # Skip weekdays
                    continue
                
                if (emp.id, d) not in employee_weekend_shift:
                    continue
                
                # Calculate temporal weight for this date
                day_index = dates.index(d)
                # Temporal multiplier: 0 (early) to 1000 (late)
                # Day 0: 0x penalty, Last day: 1000x
                # Very strong penalty to ensure late weekend work is avoided
                temporal_weight = 1000.0 * (day_index / total_days)
                
                if temporal_weight > 0:
                    # Penalize this employee working this late weekend
                    # employee_weekend_shift is 1 if working, 0 if not
                    # Use round() to preserve precision
                    final_w = round(temporal_weight)
                    objective_terms.append(employee_weekend_shift[(emp.id, d)] * final_w)
                    self.penalty_groups.setdefault("Späte Wochenendarbeit (zeitgewichtet)", []).append(
                        (employee_weekend_shift[(emp.id, d)], final_w)
                    )
                    weekend_work_penalties += 1
        
        # ALSO penalize cross-team weekend assignments with same temporal penalty
        for emp in employees:
            for d in dates:
                if d.weekday() < 5:  # Skip weekdays
                    continue
                
                # Check all possible cross-team weekend assignments for this employee/date
                for shift in shift_codes:
                    if (emp.id, d, shift) not in employee_cross_team_weekend:
                        continue
                    
                    # Calculate temporal weight for this date
                    day_index = dates.index(d)
                    temporal_weight = 1000.0 * (day_index / total_days)
                    
                    if temporal_weight > 0:
                        # Penalize cross-team weekend work with same temporal penalty
                        final_w = round(temporal_weight)
                        objective_terms.append(employee_cross_team_weekend[(emp.id, d, shift)] * final_w)
                        self.penalty_groups.setdefault("Späte Wochenendarbeit (zeitgewichtet)", []).append(
                            (employee_cross_team_weekend[(emp.id, d, shift)], final_w)
                        )
                        weekend_work_penalties += 1
        
        print(f"  Added {weekend_work_penalties} temporal weekend work penalties")
        
        # Set objective function (minimize sum of objective terms)
        if objective_terms:
            model.Minimize(sum(objective_terms))
        
        print("All constraints added successfully!")
    
    def _add_warm_start_hints(self):
        """
        Apply warmstart hints to the CP model from previous shift assignments.

        Performance benefit: Providing a good initial solution as hints reduces the
        time to find the first feasible solution by 20-40% for re-planning scenarios
        where the previous period's shift structure (rotation pattern, team composition)
        is similar to the current one. Even partially correct hints help the solver
        by narrowing the initial search space.

        Hint sources (combined, with warm_start_shifts taking precedence):
          1. planning_model.locked_employee_shift: Existing assignments for the current
             period (already enforced as hard constraints; hinting them is harmless and
             also helps derive team-level shift hints which are NOT separately locked).
          2. warm_start_shifts: External previous-month assignments (if provided).
             These are the most valuable for warmstarting fresh planning runs.

        Variables hinted:
          - team_shift[team, week, shift]: Inferred by majority vote from employee data.
            This is the most impactful hint because all other assignment variables are
            derived from or constrained by the team's weekly shift.
          - employee_active[emp, date]: Weekday activity (1 = working, 0 = off).
          - employee_weekend_shift[emp, date]: Weekend activity (1 = working, 0 = off).
        """
        model = self.planning_model.get_model()
        (team_shift, employee_active, employee_weekend_shift,
         employee_cross_team_shift, employee_cross_team_weekend) = self.planning_model.get_variables()
        employees = self.planning_model.employees
        weeks = self.planning_model.weeks

        # Combine available hint data; warm_start_shifts overrides locked_employee_shift
        hint_data: Dict[Tuple[int, date], str] = {}
        if self.planning_model.locked_employee_shift:
            hint_data.update(self.planning_model.locked_employee_shift)
        if self.warm_start_shifts:
            hint_data.update(self.warm_start_shifts)

        if not hint_data:
            return

        # Build employee -> team mapping for efficiency
        emp_to_team = {emp.id: emp.team_id for emp in employees if emp.team_id}

        # Derive team/week -> shift hints via majority vote over employee assignments.
        # For each (team, week) pair, count how many employee records suggest each shift.
        # Using majority vote handles partial data and occasional mismatches gracefully.
        team_week_shift_votes: Dict[Tuple[int, int], Dict[str, int]] = {}

        for (emp_id, d), shift_code in hint_data.items():
            if not shift_code or shift_code == "OFF":
                continue
            team_id = emp_to_team.get(emp_id)
            if team_id is None:
                continue
            week_idx = None
            for w_idx, week_dates in enumerate(weeks):
                if d in week_dates:
                    week_idx = w_idx
                    break
            if week_idx is None:
                continue
            key = (team_id, week_idx)
            if key not in team_week_shift_votes:
                team_week_shift_votes[key] = {}
            team_week_shift_votes[key][shift_code] = (
                team_week_shift_votes[key].get(shift_code, 0) + 1
            )

        hint_count = 0

        # Apply team_shift hints: winning shift = 1, all others = 0
        for (team_id, week_idx), votes in team_week_shift_votes.items():
            if not votes:
                continue
            # Tie-break by shift_code name for deterministic results across runs
            best_shift = max(votes.items(), key=lambda x: (x[1], x[0]))[0]
            for shift_code in self.planning_model.shift_codes:
                if (team_id, week_idx, shift_code) in team_shift:
                    model.add_hint(team_shift[(team_id, week_idx, shift_code)],
                                   1 if shift_code == best_shift else 0)
                    hint_count += 1

        # Apply employee_active hints for weekdays
        for (emp_id, d), shift_code in hint_data.items():
            if d.weekday() >= 5:
                continue
            if (emp_id, d) in employee_active:
                model.add_hint(employee_active[(emp_id, d)],
                               1 if shift_code and shift_code != "OFF" else 0)
                hint_count += 1

        # Apply employee_weekend_shift hints for weekends
        for (emp_id, d), shift_code in hint_data.items():
            if d.weekday() < 5:
                continue
            if (emp_id, d) in employee_weekend_shift:
                model.add_hint(employee_weekend_shift[(emp_id, d)],
                               1 if shift_code and shift_code != "OFF" else 0)
                hint_count += 1

        print(f"  Applied {hint_count} warmstart hints from {len(hint_data)} previous shift assignments")

    def compute_penalty_breakdown(self) -> Dict[str, float]:
        """
        Evaluate each tracked penalty group against the current solution.

        Must be called after a successful solve (self.solution is set).

        Returns:
            Dict mapping category name → total weighted penalty value.
            Only categories with a non-zero total are included.
        """
        if self.solution is None or self.status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return {}

        breakdown: Dict[str, float] = {}
        for category, var_weight_pairs in self.penalty_groups.items():
            total = 0.0
            for var, weight in var_weight_pairs:
                total += self.solution.Value(var) * weight
            if total != 0.0:
                breakdown[category] = total
        return breakdown

    def diagnose_infeasibility(self) -> Dict[str, any]:
        """
        Diagnose potential causes of infeasibility by analyzing the model configuration.
        
        Returns:
            Dictionary with diagnostic information about potential constraint violations
        """
        employees = self.planning_model.employees
        teams = self.planning_model.teams
        dates = self.planning_model.dates
        absences = self.planning_model.absences
        shift_types = self.planning_model.shift_types
        shift_codes = self.planning_model.shift_codes
        weeks = self.planning_model.weeks
        
        diagnostics = {
            'total_employees': len(employees),
            'total_teams': len(teams),
            'planning_days': len(dates),
            'planning_weeks': len(dates) / 7.0,  # Actual weeks, not calendar weeks
            'total_absences': len(absences),
            'potential_issues': []
        }
        
        # Check absence impact - optimized to avoid O(absences × dates)
        # Build a set of (employee_id, date) tuples for all absences
        absent_employee_dates = set()
        for absence in absences:
            for d in dates:
                if absence.start_date <= d <= absence.end_date:
                    absent_employee_dates.add((absence.employee_id, d))
        
        # Count unique employees who have ANY absence during the planning period
        employees_with_absences = set(emp_id for emp_id, _ in absent_employee_dates)
        
        # Calculate average daily absence rate (more accurate than counting employees)
        total_employee_days = len(employees) * len(dates)
        absent_days = len(absent_employee_dates)
        absence_ratio = absent_days / total_employee_days if total_employee_days > 0 else 0
        
        # For display: count employees who are absent for a significant portion of the period
        # (more than 50% of days). Group by employee_id for better performance.
        employee_absence_counts = {}
        for emp_id, _ in absent_employee_dates:
            employee_absence_counts[emp_id] = employee_absence_counts.get(emp_id, 0) + 1
        
        significantly_absent = sum(1 for count in employee_absence_counts.values() if count > len(dates) / 2)
        
        diagnostics['total_employees'] = len(employees)  # All employees in the system
        diagnostics['employees_with_absences'] = len(employees_with_absences)
        diagnostics['significantly_absent_employees'] = significantly_absent
        diagnostics['total_absence_days'] = absent_days
        diagnostics['absence_ratio'] = absence_ratio
        
        # Deprecated: Keep for backward compatibility with existing code
        diagnostics['available_employees'] = len(employees)
        diagnostics['absent_employees'] = len(employees_with_absences)
        
        # Build staffing requirements from shift_types (database configuration)
        if not shift_types:
            raise ValueError("shift_types is required for diagnostics - must be loaded from database")
        
        staffing_weekday = {}
        for st in shift_types:
            if st.code in shift_codes:
                staffing_weekday[st.code] = {
                    "min": st.min_staff_weekday,
                    "max": st.max_staff_weekday
                }
        
        # Check staffing feasibility per shift
        diagnostics['shift_analysis'] = {}
        for shift_code in shift_codes:
            if shift_code not in staffing_weekday:
                continue
            
            min_required = staffing_weekday[shift_code]["min"]
            
            # Count employees in teams that can work this shift
            eligible_employees = 0
            for team in teams:
                # Check if team can work this shift
                if team.allowed_shift_type_ids:
                    # Team has restrictions
                    shift_type = None
                    if shift_types:
                        for st in shift_types:
                            if st.code == shift_code:
                                shift_type = st
                                break
                    
                    if shift_type and shift_type.id in team.allowed_shift_type_ids:
                        # Team can work this shift
                        eligible_employees += len([e for e in employees if e.team_id == team.id])
                else:
                    # Team can work all shifts (backward compatible)
                    eligible_employees += len([e for e in employees if e.team_id == team.id])
            
            diagnostics['shift_analysis'][shift_code] = {
                'min_required': min_required,
                'eligible_employees': eligible_employees,
                'is_feasible': eligible_employees >= min_required
            }
            
            if eligible_employees < min_required:
                diagnostics['potential_issues'].append(
                    f"Schicht {shift_code}: Benötigt {min_required} Mitarbeiter, nur {eligible_employees} verfügbar"
                )
        
        # Check team sizes and rotation feasibility
        diagnostics['team_analysis'] = {}
        rotation_shifts = ['F', 'N', 'S']
        teams_in_rotation = 0
        
        for team in teams:
            team_size = len([e for e in employees if e.team_id == team.id])
            
            # Check if team participates in F-N-S rotation
            can_rotate = True
            if team.allowed_shift_type_ids and shift_types:
                # Check if team has all rotation shifts
                rotation_shift_ids = []
                for st in shift_types:
                    if st.code in rotation_shifts:
                        rotation_shift_ids.append(st.id)
                
                can_rotate = all(sid in team.allowed_shift_type_ids for sid in rotation_shift_ids)
            
            if can_rotate:
                teams_in_rotation += 1
            
            diagnostics['team_analysis'][team.name] = {
                'size': team_size,
                'allowed_shifts': team.allowed_shift_type_ids if team.allowed_shift_type_ids else "all",
                'participates_in_rotation': can_rotate
            }
            
            if team_size < 3:
                diagnostics['potential_issues'].append(
                    f"Team {team.name} hat nur {team_size} Mitglieder (möglicherweise zu klein für Rotation)"
                )
        
        # Check if rotation pattern can be satisfied
        # Need at least 3 teams for F-N-S rotation to meet all shift requirements simultaneously
        if teams_in_rotation < 3:
            diagnostics['potential_issues'].append(
                f"Nur {teams_in_rotation} Teams können F-N-S-Rotation durchführen (3 empfohlen für gleichzeitige Abdeckung)"
            )
        
        # Check for excessive absences
        if absence_ratio > 0.3:
            diagnostics['potential_issues'].append(
                f"Hohe Abwesenheitsrate: {absence_ratio*100:.1f}% aller Mitarbeitertage sind durch Abwesenheiten belegt"
            )
        
        # Check planning period constraints
        actual_weeks = len(dates) / 7.0
        if actual_weeks < 3:
            diagnostics['potential_issues'].append(
                f"Planungszeitraum ist nur {actual_weeks:.1f} Woche(n). Rotationsmuster (F→N→S) funktioniert am besten mit 3+ Wochen."
            )
        
        # Additional feasibility checks based on working hours and constraints
        # Check if total available working capacity meets minimum requirements
        # Note: This is a simplified capacity check based on shift minimums and max consecutive days.
        # It doesn't account for complex constraint interactions (rest times, weekend patterns, etc.)
        # but provides a useful upper-bound feasibility check.
        
        # Constants for capacity calculation
        # Note: MIN_CAPACITY_RATIO is a heuristic warning threshold, not a hard constraint.
        # The solver will still attempt planning even if capacity is below this threshold.
        MIN_CAPACITY_RATIO = 1.1  # Recommended 10% buffer for better feasibility (was 1.2)
        MAX_TEAM_SIZE_IMBALANCE_RATIO = 2.0  # Max ratio between largest and smallest team
        
        total_shifts_needed = len(dates) * len(shift_codes)  # Total shift slots
        total_employee_capacity = len(employees) * len(dates)
        available_capacity = total_employee_capacity - absent_days
        
        # Each employee can work max 6 consecutive days, so effective capacity is reduced
        max_consecutive = 6
        # Note: Using calendar weeks here (not actual weeks) to count rest periods needed.
        # Each calendar week requires one rest day, regardless of whether it's a full week.
        weeks_in_period = len(weeks)
        effective_capacity_per_employee = min(
            len(dates),  # Can't work more days than exist
            (weeks_in_period * max_consecutive)  # Max consecutive constraint (approx)
        )
        total_effective_capacity = len(employees) * effective_capacity_per_employee - absent_days
        
        # Check if we have enough theoretical capacity
        # Need at least min_staff per shift per day
        min_capacity_needed = 0
        for shift_code in shift_codes:
            if shift_code in staffing_weekday:
                min_staff = staffing_weekday[shift_code]["min"]
                # Simplified: assume each shift needs min_staff for all days
                # This doesn't distinguish weekday/weekend but provides a conservative estimate
                min_capacity_needed += min_staff * len(dates)
        
        capacity_ratio = total_effective_capacity / min_capacity_needed if min_capacity_needed > 0 else 0
        
        if capacity_ratio < MIN_CAPACITY_RATIO:
            diagnostics['potential_issues'].append(
                f"Knappe Personalkapazität: {capacity_ratio:.2f}x der Mindestanforderung (empfohlen: ≥{MIN_CAPACITY_RATIO}x für optimale Planbarkeit). "
                f"Effektive Kapazität: {total_effective_capacity} Mitarbeitertage, "
                f"Mindestbedarf: {min_capacity_needed} Mitarbeitertage. "
                f"Planung kann trotzdem funktionieren, erfordert aber möglicherweise mehr Lösungszeit."
            )
        
        # Check for specific constraint violations
        # If many employees are on the same team, rotation might be too rigid
        team_sizes = [len([e for e in employees if e.team_id == t.id]) for t in teams]
        if team_sizes:
            max_team_size = max(team_sizes)
            min_team_size = min(team_sizes)
            if max_team_size > min_team_size * MAX_TEAM_SIZE_IMBALANCE_RATIO:
                diagnostics['potential_issues'].append(
                    f"Ungleiche Teamgrößen: Größtes Team hat {max_team_size} Mitglieder, "
                    f"kleinstes nur {min_team_size}. Dies kann zu Planungsproblemen führen."
                )
        
        # NEW: Check for partial week conflicts
        # Partial weeks (< 7 days) can create impossible situations with team rotation
        week_sizes = [len(week) for week in weeks]
        partial_weeks = [i for i, size in enumerate(week_sizes) if size < 7]
        
        if partial_weeks:
            # Check if partial weeks could conflict with staffing requirements
            for week_idx in partial_weeks:
                week = weeks[week_idx]
                week_size = len(week)
                weekdays_in_week = sum(1 for d in week if d.weekday() < 5)
                weekends_in_week = week_size - weekdays_in_week
                
                # Calculate minimum staff needed for this partial week
                # Check how many teams participate in F→N→S rotation
                rotation_shift_codes = ['F', 'N', 'S']
                participating_teams = sum(1 for t in teams if all(
                    code in shift_codes for code in rotation_shift_codes
                ))
                
                if participating_teams >= len(rotation_shift_codes):
                    # Each team will be assigned one shift for this week
                    # Check if smallest team can meet staffing requirements
                    if team_sizes:
                        smallest_team = min(team_sizes)
                        
                        # Check against shift requirements
                        for shift_code in shift_codes:
                            if shift_code not in staffing_weekday:
                                continue
                            
                            min_weekday = staffing_weekday[shift_code]["min"]
                            
                            # For a partial week, a team might need to provide min_weekday staff
                            # on all weekdays in that week
                            if weekdays_in_week > 0 and smallest_team < min_weekday:
                                # CRITICAL: Team too small to meet minimum staffing
                                diagnostics['potential_issues'].append(
                                    f"Woche {week_idx + 1} ({week[0].strftime('%d.%m')} - {week[-1].strftime('%d.%m')}) "
                                    f"ist eine Teilwoche mit nur {week_size} Tagen ({weekdays_in_week} Werktage). "
                                    f"Kleinstes Team ({smallest_team} Mitarbeiter) kann Mindestbesetzung von "
                                    f"{min_weekday} für Schicht {shift_code} nicht erfüllen. "
                                    f"Dies macht die Rotation unmöglich."
                                )
                                break  # Only report once per partial week
        
        # NEW: Check if planning period starts on a day other than Sunday
        # This creates a partial first week which can cause rotation conflicts
        # NOTE: In the Web UI, this is automatically handled by extending to complete weeks
        first_date = dates[0]
        last_date = dates[-1]
        if first_date.weekday() != 6:  # Not Sunday
            # Calculate days in first week (from first_date until Saturday)
            days_in_first_week = 6 - first_date.weekday()
            if days_in_first_week <= 0:
                days_in_first_week = 7 + days_in_first_week
            diagnostics['potential_issues'].append(
                f"Planungszeitraum beginnt am {first_date.strftime('%A, %d.%m.%Y')} "
                f"(nicht Sonntag). Dies erzeugt eine unvollständige erste Woche mit nur "
                f"{days_in_first_week} Tagen, was zu Konflikten mit der Team-Rotation und "
                f"Mindestbesetzungsanforderungen führen kann. "
                f"HINWEIS: Das System erweitert automatisch auf vollständige Wochen (So-Sa) "
                f"und berücksichtigt bereits geplante Tage aus dem Vormonat."
            )
        
        # NEW: Check if last week is also partial
        if last_date.weekday() != 5 and len(weeks) > 0:  # Not Saturday
            last_week_size = len(weeks[-1])
            if last_week_size < 7:
                diagnostics['potential_issues'].append(
                    f"Planungszeitraum endet am {last_date.strftime('%A, %d.%m.%Y')} "
                    f"(nicht Sonntag). Dies erzeugt eine unvollständige letzte Woche mit nur "
                    f"{last_week_size} Tagen, was zu Planungsproblemen führen kann. "
                    f"HINWEIS: Das System erweitert automatisch auf vollständige Wochen (Mo-So) "
                    f"und plant monatsübergreifend bis zum nächsten Sonntag."
                )
        
        # NEW: Check rotation pattern feasibility with actual planning weeks
        # If we have exactly 5 weeks and teams rotate F→N→S, check if this creates conflicts
        if len(weeks) == 5 and len(teams) == 3:
            # With 3 teams and F→N→S rotation, week pattern repeats every 3 weeks
            # Having 5 weeks means some teams will have same shift type 2 times (weeks 0,3 and 1,4 or 2,5)
            # This is fine normally, but with partial weeks it can create problems
            if len(partial_weeks) >= 2:
                diagnostics['potential_issues'].append(
                    f"Planungszeitraum hat {len(weeks)} Wochen mit {len(partial_weeks)} Teilwochen. "
                    f"Bei 3-Team-Rotation (F→N→S) kann dies zu Konflikten führen, da manche Teams "
                    f"dieselbe Schicht mehrmals übernehmen müssen und Teilwochen die Besetzung erschweren."
                )
        
        return diagnostics
    
    def solve(self) -> bool:
        """
        Solve the shift planning problem.

        Applies warmstart hints (if available) and uses a solution callback to log
        intermediate improvements. The search strategy (PORTFOLIO / FIXED_SEARCH /
        AUTOMATIC) is set on the solver before solving starts.

        Additional solver tuning applied here:
          - linearization_level=2: stronger LP relaxation for tighter bounds and
            faster pruning (typically 15-40% speedup on scheduling problems).
          - interleave_search=True (PORTFOLIO + ≥4 workers): distributes time
            evenly across parallel sub-solvers.
          - symmetry_level=2: automatic symmetry-breaking for the repeated
            team/week structure in this model.
          - random_seed: when set, makes the search fully reproducible.
          - stop_after_first_feasible callback (relaxation_level > 0): for fallback
            stages feasibility is the goal; halting early avoids wasted optimisation.
        
        Returns:
            True if a solution was found, False otherwise
        """
        model = self.planning_model.get_model()
        
        # Configure solver
        solver = cp_model.CpSolver()
        if self.time_limit_seconds is not None:
            solver.parameters.max_time_in_seconds = self.time_limit_seconds
        solver.parameters.num_search_workers = self.num_workers
        solver.parameters.log_search_progress = True

        # Stronger LP relaxation: level 2 provides tighter lower bounds via a more
        # aggressive linearisation of the Boolean objective, enabling faster pruning.
        # Level 1 is the OR-Tools default; level 2 is typically 15-40% faster on
        # scheduling/covering problems like this one.
        solver.parameters.linearization_level = 2

        # Symmetry breaking: automatically detect and break symmetries in the model.
        # The repeated team/week structure of this problem has many equivalent
        # sub-trees; level 2 is the most aggressive OR-Tools setting.
        solver.parameters.symmetry_level = 2

        # Apply search branching strategy
        # PORTFOLIO (default): parallel workers each use a different heuristic; best
        #   for complex, heterogeneous problems and num_workers > 1.
        # FIXED_SEARCH: deterministic variable/value ordering; useful for reproducibility.
        # AUTOMATIC: let OR-Tools choose based on the problem structure.
        strategy_map = {
            "PORTFOLIO": solver.parameters.PORTFOLIO_SEARCH,
            "FIXED_SEARCH": solver.parameters.FIXED_SEARCH,
            "AUTOMATIC": solver.parameters.AUTOMATIC_SEARCH,
        }
        branching = strategy_map.get(self.search_strategy.upper(),
                                     solver.parameters.PORTFOLIO_SEARCH)
        solver.parameters.search_branching = branching

        # Interleaved search distributes wall-clock time more evenly across the
        # parallel sub-solvers in PORTFOLIO mode, preventing one worker from
        # monopolising the time budget.  Only effective with multiple workers.
        is_portfolio = (solver.parameters.search_branching
                        == solver.parameters.PORTFOLIO_SEARCH)
        if is_portfolio and self.num_workers >= 4:
            solver.parameters.interleave_search = True

        # Optional reproducibility: fix the pseudo-random seed so that identical
        # inputs always yield identical solver behaviour.
        if self.random_seed is not None:
            solver.parameters.random_seed = self.random_seed

        print("\n" + "=" * 60)
        print("STARTING SOLVER")
        print("=" * 60)
        print(f"Time limit: {'unlimited' if self.time_limit_seconds is None else f'{self.time_limit_seconds} seconds'}")
        print(f"Parallel workers: {self.num_workers}")
        print(f"Search strategy: {self.search_strategy}")
        print(f"Linearization level: 2  (stronger LP relaxation)")
        print(f"Symmetry level: 2  (automatic symmetry-breaking)")
        if is_portfolio and self.num_workers >= 4:
            print("Interleaved search: enabled")
        if self.random_seed is not None:
            print(f"Random seed: {self.random_seed}")
        if self.relaxation_level > 0:
            print(f"Stop-after-first-feasible: enabled (fallback stage {self.relaxation_level})")

        # Apply warmstart hints to bias the solver toward a known-good starting point.
        # Expected benefit: 20-40% faster first feasible solution on re-planning runs.
        has_hints = (self.warm_start_shifts or self.planning_model.locked_employee_shift)
        if has_hints:
            print("Applying warmstart hints from previous shift assignments...")
            self._add_warm_start_hints()
        else:
            print("No warmstart hints available (fresh planning run)")
        print()
        
        # Create solution callback for logging intermediate solutions.
        # For fallback stages (relaxation_level > 0) the callback will call StopSearch()
        # as soon as the first feasible solution is found – optimisation is not needed there.
        stop_early = (self.relaxation_level > 0)
        callback = ShiftPlanSolutionCallback(stop_after_first_feasible=stop_early)

        # Solve with callback so each new improving solution is logged immediately.
        # The solver retains the best solution found; if it times out with status
        # FEASIBLE, solver.Value() still returns the best assignment found so far.
        self.status = solver.Solve(model, callback)
        self.solution = solver
        
        # Print results
        print("\n" + "=" * 60)
        print("SOLVER RESULTS")
        print("=" * 60)
        
        if self.status == cp_model.OPTIMAL:
            print("✓ OPTIMAL solution found!")
        elif self.status == cp_model.FEASIBLE:
            print("✓ FEASIBLE solution found (not proven optimal)")
        elif self.status == cp_model.INFEASIBLE:
            print("✗ INFEASIBLE - No solution exists!")
            print("\nRunning diagnostics to identify the issue...")
            diagnostics = self.diagnose_infeasibility()
            
            print(f"\nModel Statistics:")
            print(f"  - Total employees: {diagnostics['total_employees']}")
            print(f"  - Available employees: {diagnostics['available_employees']}")
            print(f"  - Absent employees: {diagnostics['absent_employees']}")
            print(f"  - Planning period: {diagnostics['planning_days']} days")
            
            if diagnostics['potential_issues']:
                print(f"\n⚠️  Potential Issues Detected ({len(diagnostics['potential_issues'])}):")
                for issue in diagnostics['potential_issues']:
                    print(f"  • {issue}")
            
            print(f"\nShift Staffing Analysis:")
            for shift_code, analysis in diagnostics['shift_analysis'].items():
                status = "✓" if analysis['is_feasible'] else "✗"
                print(f"  {status} {shift_code}: {analysis['eligible_employees']} eligible / {analysis['min_required']} required")
            
            print(f"\nTeam Configuration:")
            for team_name, info in diagnostics['team_analysis'].items():
                allowed = info['allowed_shifts'] if isinstance(info['allowed_shifts'], str) else f"{len(info['allowed_shifts'])} specific shifts"
                print(f"  - {team_name}: {info['size']} members, allowed shifts: {allowed}")
            
            # Store diagnostics for later use
            self.diagnostics = diagnostics
            return False
        elif self.status == cp_model.MODEL_INVALID:
            print("✗ MODEL INVALID - Check constraints!")
            return False
        else:
            print(f"✗ Unknown status: {self.status}")
            return False
        
        print(f"\nSolver statistics:")
        print(f"  - Wall time: {solver.WallTime():.2f} seconds")
        print(f"  - Branches: {solver.NumBranches()}")
        print(f"  - Conflicts: {solver.NumConflicts()}")
        if self.status == cp_model.OPTIMAL or self.status == cp_model.FEASIBLE:
            print(f"  - Objective value: {solver.ObjectiveValue()}")
        print(f"  - Intermediate solutions found: {callback.solution_count}")
        if callback.solution_count > 0:
            print(f"  - Best objective via callback: {callback.best_objective:.0f}")
        
        print("=" * 60)
        
        return True
    
    def extract_solution(self) -> Tuple[List[ShiftAssignment], Dict[Tuple[int, date], str]]:
        """
        Extract shift assignments from the TEAM-BASED solution with CROSS-TEAM support.
        
        Returns:
            Tuple of (shift_assignments, complete_schedule)
            where:
            - shift_assignments: List of ShiftAssignment objects (includes cross-team assignments)
            - complete_schedule: dict mapping (employee_id, date) to shift_code or "OFF"
                                 This ensures ALL employees appear for ALL days
        """
        if not self.solution or self.status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return [], {}
        
        (team_shift, employee_active, employee_weekend_shift, 
         employee_cross_team_shift, employee_cross_team_weekend) = self.planning_model.get_variables()
        employees = self.planning_model.employees
        teams = self.planning_model.teams
        dates = self.planning_model.dates
        weeks = self.planning_model.weeks
        shift_codes = self.planning_model.shift_codes
        absences = self.planning_model.absences
        
        assignments = []
        assignment_id = 1
        
        # Complete schedule: every employee, every day
        complete_schedule = {}
        
        # Track assigned shifts to prevent double assignments (safety check)
        # Maps (employee_id, date) -> shift_type_id
        assigned_shifts = {}
        
        # Helper function to safely add assignment (prevents double shifts)
        def try_add_assignment(emp_id, shift_type_id, d, notes=None):
            """
            Try to add an assignment, preventing double shifts.
            Returns True if added, False if prevented.
            """
            nonlocal assignment_id, assignments, assigned_shifts
            
            # Safety check: prevent double assignment
            if (emp_id, d) in assigned_shifts:
                print(f"WARNING: Double shift assignment prevented for employee {emp_id} on {d}")
                print(f"  Already assigned: {assigned_shifts[(emp_id, d)]}, attempted: {shift_type_id}")
                return False
            
            # Create and add assignment
            assignment = ShiftAssignment(
                id=assignment_id,
                employee_id=emp_id,
                shift_type_id=shift_type_id,
                date=d,
                notes=notes
            )
            assignments.append(assignment)
            assigned_shifts[(emp_id, d)] = shift_type_id
            assignment_id += 1
            return True
        
        # Extract shift assignments based on team shifts and employee activity
        for emp in employees:
            # Regular team members
            if not emp.team_id:
                continue
            
            # Find employee's team
            team = None
            for t in teams:
                if t.id == emp.team_id:
                    team = t
                    break
            
            if not team:
                continue
            
            # For each date, check if employee is active
            for d in dates:
                weekday = d.weekday()
                
                if weekday < 5:  # WEEKDAY (Mon-Fri): Use team shift
                    if (emp.id, d) not in employee_active:
                        continue
                    
                    if self.solution.Value(employee_active[(emp.id, d)]) == 0:
                        continue  # Not working this day
                    
                    # Find which week this date belongs to
                    week_idx = self.planning_model.get_week_index(d)
                    
                    # Find which shift the team has this week
                    team_shift_code = None
                    for shift_code in shift_codes:
                        if (team.id, week_idx, shift_code) in team_shift:
                            if self.solution.Value(team_shift[(team.id, week_idx, shift_code)]) == 1:
                                team_shift_code = shift_code
                                break
                    
                    if not team_shift_code:
                        continue  # No shift found
                    
                    # Find shift type ID
                    shift_type_id = None
                    for st in STANDARD_SHIFT_TYPES:
                        if st.code == team_shift_code:
                            shift_type_id = st.id
                            break
                    
                    if shift_type_id:
                        try_add_assignment(emp.id, shift_type_id, d)
                
                else:  # WEEKEND (Sat-Sun): Use team shift type with individual presence
                    # Check if employee is working this weekend day
                    if (emp.id, d) not in employee_weekend_shift:
                        continue
                    
                    if self.solution.Value(employee_weekend_shift[(emp.id, d)]) == 0:
                        continue  # Not working this weekend day
                    
                    # Find which week this date belongs to
                    week_idx = self.planning_model.get_week_index(d)
                    
                    # Find which shift the team has this week (same for weekends)
                    team_shift_code = None
                    for shift_code in shift_codes:
                        if (team.id, week_idx, shift_code) in team_shift:
                            if self.solution.Value(team_shift[(team.id, week_idx, shift_code)]) == 1:
                                team_shift_code = shift_code
                                break
                    
                    if not team_shift_code:
                        continue  # No shift found
                    
                    # Find shift type ID
                    shift_type_id = None
                    for st in STANDARD_SHIFT_TYPES:
                        if st.code == team_shift_code:
                            shift_type_id = st.id
                            break
                    
                    if shift_type_id:
                        try_add_assignment(emp.id, shift_type_id, d)
        
        # Extract CROSS-TEAM assignments (NEW)
        # These are employees working shifts from other teams to meet their monthly hours
        for emp in employees:
            if not emp.team_id:
                continue
            
            for d in dates:
                weekday = d.weekday()
                
                if weekday < 5:  # WEEKDAY cross-team
                    # Check all shift codes this employee can work cross-team
                    for shift_code in shift_codes:
                        if (emp.id, d, shift_code) not in employee_cross_team_shift:
                            continue
                        
                        if self.solution.Value(employee_cross_team_shift[(emp.id, d, shift_code)]) == 1:
                            # Find shift type ID
                            shift_type_id = None
                            for st in STANDARD_SHIFT_TYPES:
                                if st.code == shift_code:
                                    shift_type_id = st.id
                                    break
                            
                            if shift_type_id:
                                if try_add_assignment(emp.id, shift_type_id, d, "Cross-team assignment"):
                                    break  # Only one shift per day
                
                else:  # WEEKEND cross-team
                    # Check all shift codes this employee can work cross-team on weekends
                    for shift_code in shift_codes:
                        if (emp.id, d, shift_code) not in employee_cross_team_weekend:
                            continue
                        
                        if self.solution.Value(employee_cross_team_weekend[(emp.id, d, shift_code)]) == 1:
                            # Find shift type ID
                            shift_type_id = None
                            for st in STANDARD_SHIFT_TYPES:
                                if st.code == shift_code:
                                    shift_type_id = st.id
                                    break
                            
                            if shift_type_id:
                                if try_add_assignment(emp.id, shift_type_id, d, "Cross-team weekend assignment"):
                                    break  # Only one shift per day
        
        # Build complete schedule: every employee for every day
        # This ensures ALL employees appear in the output, even without shifts
        # 
        # CRITICAL: Absences (U, AU, L) ALWAYS take priority over shifts
        # This is mandated by requirement #1 in the problem statement:
        # "Absence codes (U, AU, L) ALWAYS override regular shifts and TD"
        # 
        # Priority order (highest to lowest):
        # 1. Absence (U, AU, L)
        # 2. TD (Day Duty)
        # 3. Regular shifts (F, S, N)
        # 4. OFF (no assignment)
        for emp in employees:
            for d in dates:
                # PRIORITY 1: Check if employee is absent (HIGHEST PRIORITY)
                # Absences ALWAYS override shifts and TD
                absence = None
                for abs in absences:
                    if abs.employee_id == emp.id and abs.overlaps_date(d):
                        absence = abs
                        break
                
                if absence:
                    # Mark as ABSENT (consistent with complete_schedule contract)
                    complete_schedule[(emp.id, d)] = "ABSENT"
                    continue
                
                # PRIORITY 2: Check if employee has a shift assignment
                has_assignment = False
                for assignment in assignments:
                    if assignment.employee_id == emp.id and assignment.date == d:
                        # Get shift code
                        shift_type = next((st for st in STANDARD_SHIFT_TYPES if st.id == assignment.shift_type_id), None)
                        if shift_type:
                            complete_schedule[(emp.id, d)] = shift_type.code
                            has_assignment = True
                            break
                
                # PRIORITY 3: No assignment - mark as OFF
                if not has_assignment:
                    complete_schedule[(emp.id, d)] = "OFF"
        
        return assignments, complete_schedule
    
    def print_planning_summary(
        self,
        assignments: List[ShiftAssignment],
        complete_schedule: Dict[Tuple[int, date], str]
    ):
        """
        Print a comprehensive summary of the planning results.
        
        Shows:
        - Planning period details (days, weeks)
        - Shift distribution per shift type
        - Required monthly working hours per employee
        - Actual hours worked per employee
        """
        if not self.solution or self.status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return
        
        from collections import defaultdict
        from datetime import timedelta
        
        employees = self.planning_model.employees
        dates = self.planning_model.dates
        weeks = self.planning_model.weeks
        shift_types = self.planning_model.shift_types
        absences = self.planning_model.absences
        
        print("\n" + "=" * 80)
        print("SCHICHTPLAN ZUSAMMENFASSUNG (PLANNING SUMMARY)")
        print("=" * 80)
        
        # Planning period details
        start_date = dates[0]
        end_date = dates[-1]
        total_days = len(dates)
        total_weeks = len(weeks)
        
        # Determine month name from the original (requested) planning start date,
        # not from dates[0] which may be in the previous month because the planning
        # window is extended to cover complete calendar weeks.
        month_names = ["Januar", "Februar", "März", "April", "Mai", "Juni", 
                      "Juli", "August", "September", "Oktober", "November", "Dezember"]
        target_date = getattr(self.planning_model, 'original_start_date', None)
        if target_date is None:
            # Fallback: original_start_date is always set by ShiftPlanningModel.__init__,
            # so this branch should never be reached in production.
            print("WARNING: original_start_date not found on planning_model, falling back to dates[0]")
            target_date = start_date
        month_name = month_names[target_date.month - 1]
        
        print(f"\nPlanungszeitraum:")
        print(f"  Von: {start_date.strftime('%d.%m.%Y')} ({start_date.strftime('%A')})")
        print(f"  Bis: {end_date.strftime('%d.%m.%Y')} ({end_date.strftime('%A')})")
        print(f"  Tage im Planungszeitraum: {total_days}")
        print(f"  Wochen im Planungszeitraum: {total_weeks}")
        print(f"  Monat: {month_name} {target_date.year}")
        
        # Count shifts per shift type
        shift_counts = defaultdict(int)
        for assignment in assignments:
            shift_type = get_shift_type_by_id(assignment.shift_type_id)
            if shift_type:
                shift_counts[shift_type.code] += 1
        
        print(f"\nAnzahl Schichten je Schichtart:")
        for shift_code in sorted(shift_counts.keys()):
            count = shift_counts[shift_code]
            shift_type = next((st for st in shift_types if st.code == shift_code), None)
            shift_name = shift_type.name if shift_type else shift_code
            print(f"  {shift_code} ({shift_name}): {count} Schichten")
        
        # Calculate required and actual hours per employee
        print(f"\nMonatliche Arbeitsstunden je Mitarbeiter:")
        print(f"  {'Mitarbeiter':<30} {'Soll (h)':<12} {'Ist (h)':<12} {'Differenz':<12} {'Tage':<8}")
        print(f"  {'-' * 74}")
        
        emp_hours = {}
        emp_days = {}
        
        for assignment in assignments:
            emp_id = assignment.employee_id
            shift_type = get_shift_type_by_id(assignment.shift_type_id)
            
            if emp_id not in emp_hours:
                emp_hours[emp_id] = 0
                emp_days[emp_id] = set()
            
            emp_hours[emp_id] += shift_type.hours
            emp_days[emp_id].add(assignment.date)
        
        # Calculate required hours for each employee
        for emp in sorted(employees, key=lambda e: e.full_name):
            if not emp.team_id:
                continue  # Skip employees without teams
            
            # Find employee's shift type to get weekly working hours
            weekly_hours = 40.0  # Default
            if shift_types:
                # Use first shift type as default
                for st in shift_types:
                    if st.code in ['F', 'S', 'N']:
                        weekly_hours = st.weekly_working_hours
                        break
            
            # Count days without absence for this employee
            days_without_absence = 0
            for d in dates:
                is_absent = any(abs.employee_id == emp.id and abs.overlaps_date(d) 
                              for abs in absences)
                if not is_absent:
                    days_without_absence += 1
            
            # Calculate required hours: (weekly_hours / 7) × days_without_absence
            required_hours = (weekly_hours / 7.0) * days_without_absence
            
            # Get actual hours
            actual_hours = emp_hours.get(emp.id, 0)
            actual_days = len(emp_days.get(emp.id, set()))
            
            # Calculate difference
            diff = actual_hours - required_hours
            diff_str = f"+{diff:.1f}" if diff >= 0 else f"{diff:.1f}"
            
            # Only show employees with hours
            if actual_hours > 0 or days_without_absence > 0:
                print(f"  {emp.full_name:<30} {required_hours:>10.1f}h  {actual_hours:>10.1f}h  {diff_str:>10}h  {actual_days:>6}")
        
        # Summary statistics
        total_assignments = len(assignments)
        total_employees_working = len(emp_hours)
        
        print(f"\nGesamtstatistik:")
        print(f"  Gesamtanzahl Schichtzuweisungen: {total_assignments}")
        print(f"  Anzahl arbeitender Mitarbeiter: {total_employees_working}/{len([e for e in employees if e.team_id])}")
        
        avg_hours = sum(emp_hours.values()) / len(emp_hours) if emp_hours else 0
        print(f"  Durchschnittliche Stunden pro Mitarbeiter: {avg_hours:.1f}h")
        
        print("=" * 80)
    
    def get_statistics(self) -> Dict[str, any]:
        """
        Get solution statistics.
        
        Returns:
            Dictionary with statistics
        """
        if not self.solution:
            return {}
        
        return {
            "status": "OPTIMAL" if self.status == cp_model.OPTIMAL else "FEASIBLE",
            "wall_time": self.solution.WallTime(),
            "branches": self.solution.NumBranches(),
            "conflicts": self.solution.NumConflicts(),
            "objective_value": self.solution.ObjectiveValue() if self.status in [cp_model.OPTIMAL, cp_model.FEASIBLE] else None
        }


# ---------------------------------------------------------------------------
# Helper functions used by solve_shift_planning()
# ---------------------------------------------------------------------------

def _print_relaxation_summary(relaxed_constraints: List[str]) -> None:
    """Print a summary of which constraints were relaxed during fallback solving."""
    if not relaxed_constraints:
        return
    print("\n" + "=" * 60)
    print("⚠️  ABWEICHUNGSBERICHT – Folgende Regeln wurden entspannt:")
    print("=" * 60)
    for i, constraint in enumerate(relaxed_constraints, 1):
        print(f"  {i}. {constraint}")
    print("=" * 60)


def create_emergency_plan(
    available_employees: List[Employee],
    dates: List[date],
    shift_types: List,
    absences: List,
) -> Tuple[List[ShiftAssignment], List[RelaxedConstraint]]:
    """
    Greedy emergency plan – last-resort fallback without OR-Tools.

    Creates a minimal but complete shift plan when all constraint-relaxation
    stages of the CP-SAT solver have failed.  The algorithm is intentionally
    simple and fast; correctness (every available employee gets a shift every
    day) is preferred over optimality.

    Strategy:
    ──────────
    1. Build an absence lookup so absent employees are never scheduled.
    2. For every date (in chronological order) and every shift type that is
       active on that date, collect employees who are available (not absent)
       and not yet assigned on that day.
    3. Before assigning an employee to a shift, check whether the 11-hour
       minimum rest time since their last assignment is satisfied.
       • Employees that satisfy the rest time are preferred.
       • If no rested employee is available the rest-violating employee is
         assigned anyway and a RelaxedConstraint is recorded.
    4. Every rule deviation is captured as a RelaxedConstraint that states
       what was violated and why ("Notfallabweichung").

    Args:
        available_employees: All employees to consider for scheduling.
        dates:               Sorted list of planning dates.
        shift_types:         Shift-type definitions (ShiftType objects).
        absences:            All absence records covering the planning period.

    Returns:
        assignments:          List[ShiftAssignment] – one entry per employee
                              per working day (absent employees are skipped).
        relaxed_constraints:  List[RelaxedConstraint] – one entry per rule
                              violation, explaining what was violated and why.
    """

    # ------------------------------------------------------------------ #
    # Helper: parse "HH:MM" into a datetime on a given date               #
    # ------------------------------------------------------------------ #
    def _parse_time(time_str: str):
        """Parse 'HH:MM' using strptime for robustness."""
        return datetime.strptime(time_str, "%H:%M").time()

    def _shift_end_dt(assignment_date: date, st) -> datetime:
        """Return the wall-clock datetime when *st* ends on *assignment_date*."""
        end = datetime.combine(assignment_date, _parse_time(st.end_time))
        start = datetime.combine(assignment_date, _parse_time(st.start_time))
        # Overnight shift: end time is on the next calendar day
        if end <= start:
            end += timedelta(days=1)
        return end

    def _shift_start_dt(assignment_date: date, st) -> datetime:
        return datetime.combine(assignment_date, _parse_time(st.start_time))

    MIN_REST_HOURS = 11

    # ------------------------------------------------------------------ #
    # Build absence lookup: (employee_id, date) → absence object          #
    # Iterates over (absence, date) pairs; suitable for the bounded        #
    # planning periods used by the emergency fallback.                     #
    # ------------------------------------------------------------------ #
    absence_lookup: Dict[Tuple[int, date], object] = {}
    for absence in absences:
        for d in dates:
            if absence.start_date <= d <= absence.end_date:
                absence_lookup[(absence.employee_id, d)] = absence

    # ------------------------------------------------------------------ #
    # Determine which shift types are active on a given date.             #
    # Falls back to all shift types when none match the weekday flags     #
    # (e.g. non-standard configurations) to guarantee every day gets     #
    # at least one shift to assign.                                       #
    # ------------------------------------------------------------------ #
    def _active_shifts(d: date) -> List:
        active = [st for st in shift_types if st.works_on_date(d)]
        return active if active else list(shift_types)

    # ------------------------------------------------------------------ #
    # Main greedy loop                                                     #
    # ------------------------------------------------------------------ #
    assignments: List[ShiftAssignment] = []
    relaxed_constraints: List[RelaxedConstraint] = []
    assignment_id = 1

    # Track the last assigned shift per employee for rest-time checks.
    # Maps employee_id → (end_datetime of last shift)
    last_shift_end: Dict[int, datetime] = {}

    # Tracks which employees are already assigned on a given date so that
    # no employee receives more than one shift per day.
    assigned_today: Dict[date, set] = {}

    for d in sorted(dates):
        assigned_today[d] = set()
        active_shifts = _active_shifts(d)

        # Employees available on this date (not absent, has a team)
        available = [
            emp for emp in available_employees
            if emp.team_id is not None and (emp.id, d) not in absence_lookup
        ]

        if not available or not active_shifts:
            continue

        # Round-robin index to distribute employees evenly across shift types
        shift_count = len(active_shifts)
        emp_shift_index: Dict[int, int] = {
            emp.id: idx % shift_count for idx, emp in enumerate(available)
        }

        # Sort employees: those satisfying rest time first, rest-violators last.
        def _rest_ok(emp) -> bool:
            if emp.id not in last_shift_end:
                return True
            # Try each candidate shift; the preferred shift is at emp_shift_index
            preferred_st = active_shifts[emp_shift_index[emp.id]]
            start = _shift_start_dt(d, preferred_st)
            return (start - last_shift_end[emp.id]).total_seconds() >= MIN_REST_HOURS * 3600

        available.sort(key=lambda e: (0 if _rest_ok(e) else 1, e.id))

        for emp in available:
            if emp.id in assigned_today[d]:
                continue

            preferred_idx = emp_shift_index[emp.id]
            chosen_st = None

            # Try to find a shift that does not violate the rest time.
            for offset in range(shift_count):
                candidate = active_shifts[(preferred_idx + offset) % shift_count]
                start_dt = _shift_start_dt(d, candidate)
                if emp.id not in last_shift_end or \
                        (start_dt - last_shift_end[emp.id]).total_seconds() >= MIN_REST_HOURS * 3600:
                    chosen_st = candidate
                    break

            rest_violated = False
            if chosen_st is None:
                # No rest-compliant shift found; fall back to preferred shift and document the violation.
                chosen_st = active_shifts[preferred_idx]
                rest_violated = True

            # Record rest-time violation.
            if rest_violated:
                prev_end = last_shift_end[emp.id]
                actual_rest_h = (
                    _shift_start_dt(d, chosen_st) - prev_end
                ).total_seconds() / 3600
                relaxed_constraints.append(RelaxedConstraint(
                    constraint_name="Ruhezeit (11h)",
                    reason=(
                        f"Nicht genügend ausgeruhte Mitarbeiter verfügbar – "
                        f"Ruhezeit {actual_rest_h:.1f}h statt 11h (Notfallabweichung)"
                    ),
                    description=(
                        f"Mitarbeiter {emp.full_name} (ID {emp.id}) wurde der "
                        f"Schicht {chosen_st.code} am {d.isoformat()} zugewiesen "
                        f"obwohl die Mindestruhezeit von 11h unterschritten wurde."
                    ),
                    employee_id=emp.id,
                    employee_name=emp.full_name,
                    date=d,
                    shift_code=chosen_st.code,
                ))

            assignments.append(ShiftAssignment(
                id=assignment_id,
                employee_id=emp.id,
                shift_type_id=chosen_st.id,
                date=d,
                notes="Notfallplan (greedy)",
            ))
            assigned_today[d].add(emp.id)
            last_shift_end[emp.id] = _shift_end_dt(d, chosen_st)
            assignment_id += 1

    print(
        f"  Notfallplan erstellt: {len(assignments)} Schichtzuweisungen "
        f"für {len(available_employees)} Mitarbeiter über {len(dates)} Tage "
        f"({len(relaxed_constraints)} Notfallabweichungen)."
    )
    return assignments, relaxed_constraints


def _create_greedy_emergency_plan(
    planning_model: ShiftPlanningModel,
) -> Tuple[List[ShiftAssignment], Dict[Tuple[int, date], str]]:
    """
    Stage 4 emergency fallback: build a minimal shift plan using a greedy algorithm
    without OR-Tools. This guarantees a non-empty result even when the CP-SAT solver
    cannot find any feasible solution in all relaxed configurations.

    Strategy:
    - For each day, collect employees who are not absent.
    - Round-robin distribute available employees across active shift types for that day.
    - Respects absences (employees on U/AU/L are never assigned shifts).
    - Does NOT enforce minimum staffing, rotation order, rest times, or hours targets.

    Returns:
        Tuple of (assignments, complete_schedule) – same format as extract_solution().
    """
    employees = planning_model.employees
    dates = planning_model.dates
    absences = planning_model.absences
    shift_types = planning_model.shift_types
    shift_codes = planning_model.shift_codes

    # Build fast absence lookup: (emp_id, date) -> absence
    absence_lookup: Dict[Tuple[int, date], object] = {}
    for absence in absences:
        for d in dates:
            if absence.start_date <= d <= absence.end_date:
                absence_lookup[(absence.employee_id, d)] = absence

    # Only schedule shifts that are active for the day type
    def active_shifts_for_day(d: date) -> List[str]:
        result = []
        for st in shift_types:
            if st.code in shift_codes and st.works_on_date(d):
                result.append(st.code)
        return result or list(shift_codes)  # fallback: all shifts

    assignments: List[ShiftAssignment] = []
    complete_schedule: Dict[Tuple[int, date], str] = {}
    assignment_id = 1
    already_assigned: Dict[Tuple[int, date], str] = {}

    # Track which employees are available (not absent) per day
    for d in dates:
        available = [
            emp for emp in employees
            if emp.team_id and (emp.id, d) not in absence_lookup
        ]
        day_shift_codes = active_shifts_for_day(d)

        for idx, emp in enumerate(available):
            if (emp.id, d) in already_assigned:
                continue
            # Round-robin assignment across shift types
            shift_code = day_shift_codes[idx % len(day_shift_codes)]
            shift_type = next((st for st in shift_types if st.code == shift_code), None)
            if shift_type is None:
                continue
            assignments.append(ShiftAssignment(
                id=assignment_id,
                employee_id=emp.id,
                shift_type_id=shift_type.id,
                date=d,
                notes="Notfallplan (greedy)",
            ))
            already_assigned[(emp.id, d)] = shift_code
            assignment_id += 1

    # Build complete_schedule: every employee × every date
    for emp in employees:
        for d in dates:
            if (emp.id, d) in absence_lookup:
                complete_schedule[(emp.id, d)] = "ABSENT"
            elif (emp.id, d) in already_assigned:
                complete_schedule[(emp.id, d)] = already_assigned[(emp.id, d)]
            else:
                complete_schedule[(emp.id, d)] = "OFF"

    print(f"  Notfallplan erstellt: {len(assignments)} Schichtzuweisungen für {len(employees)} Mitarbeiter über {len(dates)} Tage.")
    return assignments, complete_schedule


# ---------------------------------------------------------------------------
# PlanningReport helper functions
# ---------------------------------------------------------------------------

def _parse_relaxed_constraints(strings: List[str]) -> List[PlanningRelaxedConstraint]:
    """Convert a list of 'name: reason' strings to PlanningRelaxedConstraint objects."""
    result = []
    for s in strings:
        parts = s.split(": ", 1)
        name = parts[0]
        reason = parts[1] if len(parts) > 1 else ""
        result.append(PlanningRelaxedConstraint(constraint_name=name, reason=reason))
    return result


def _validation_result_to_rule_violations(
    validation_result,
    absences,
    employees,
) -> List[RuleViolation]:
    """
    Convert a ValidationResult into a list of RuleViolation objects.

    Uses the structured cause_type and cause fields already attached to each
    ViolationEntry during validation. Falls back to absence-name matching for
    entries without an explicit cause.
    """
    emp_absences: Dict[str, list] = {}
    for absence in absences:
        emp = next((e for e in employees if e.id == absence.employee_id), None)
        if emp:
            emp_absences.setdefault(emp.full_name, []).append(absence)

    def _find_absence_cause(description: str) -> str:
        for emp_name, abs_list in emp_absences.items():
            if emp_name in description:
                causes = [
                    f"Abwesenheit ({a.get_code()}): {a.start_date} – {a.end_date}"
                    for a in abs_list
                ]
                return "; ".join(causes)
        return ""

    violations: List[RuleViolation] = []
    for v in validation_result.violations:
        cause = v.cause if v.cause else _find_absence_cause(v.message)
        violations.append(RuleViolation(
            rule_id="VALIDATION_HARD",
            description=v.message,
            severity="HARD",
            affected_dates=[],
            cause=cause,
            impact=v.message,
            cause_type=v.cause_type,
        ))
    for v in validation_result.warnings:
        cause = v.cause if v.cause else _find_absence_cause(v.message)
        violations.append(RuleViolation(
            rule_id="VALIDATION_SOFT",
            description=v.message,
            severity="SOFT_LOW",
            affected_dates=[],
            cause=cause,
            impact=v.message,
            cause_type=v.cause_type,
        ))
    return violations


def _build_planning_report(
    assignments: List[ShiftAssignment],
    complete_schedule: Dict,
    planning_model: "ShiftPlanningModel",
    status: str,
    objective_value: float,
    solver_time_seconds: float,
    relaxed_constraints_strs: List[str],
    penalty_breakdown: Optional[Dict[str, float]] = None,
) -> PlanningReport:
    """Build a PlanningReport from solver outputs and a fresh validation run."""
    start_date = planning_model.original_start_date
    end_date = planning_model.original_end_date

    # Absent employees list
    absent_employees_info: List[AbsenceInfo] = []
    for absence in planning_model.absences:
        emp = next((e for e in planning_model.employees if e.id == absence.employee_id), None)
        if emp:
            absent_employees_info.append(AbsenceInfo(
                employee_name=emp.full_name,
                absence_type=absence.get_code(),
                start_date=absence.start_date,
                end_date=absence.end_date,
                notes=absence.notes,
            ))

    # Available employees: those without a full-period absence
    absent_full_period_ids = {
        a.employee_id
        for a in planning_model.absences
        if a.start_date <= start_date and a.end_date >= end_date
    }
    available_employees = len(
        [e for e in planning_model.employees if e.id not in absent_full_period_ids]
    )

    # Shift count per code
    shifts_assigned: Dict[str, int] = {}
    for assignment in assignments:
        shift_type = get_shift_type_by_id(assignment.shift_type_id)
        code = shift_type.code if shift_type else str(assignment.shift_type_id)
        shifts_assigned[code] = shifts_assigned.get(code, 0) + 1

    # Relaxed constraints
    relaxed_constraints = _parse_relaxed_constraints(relaxed_constraints_strs)

    # Validate and convert to RuleViolation objects
    validation_result = validate_shift_plan(
        assignments=assignments,
        employees=planning_model.employees,
        absences=planning_model.absences,
        start_date=start_date,
        end_date=end_date,
        teams=planning_model.teams,
        complete_schedule=complete_schedule,
        locked_team_shift=planning_model.locked_team_shift,
        locked_employee_weekend=planning_model.locked_employee_weekend,
        shift_types=planning_model.shift_types,
    )
    rule_violations = _validation_result_to_rule_violations(
        validation_result, planning_model.absences, planning_model.employees
    )

    return PlanningReport(
        planning_period=(start_date, end_date),
        status=status,
        total_employees=len(planning_model.employees),
        available_employees=available_employees,
        absent_employees=absent_employees_info,
        shifts_assigned=shifts_assigned,
        rule_violations=rule_violations,
        relaxed_constraints=relaxed_constraints,
        absence_impact=analyze_absence_impact(
            employees=planning_model.employees,
            absences=planning_model.absences,
            dates=planning_model.dates,
            shift_requirements=planning_model.shift_types,
        ),
        objective_value=objective_value,
        solver_time_seconds=solver_time_seconds,
        penalty_breakdown=penalty_breakdown or {},
    )


def solve_shift_planning(
    planning_model: ShiftPlanningModel,
    time_limit_seconds: Optional[int] = None,
    num_workers: Optional[int] = None,
    global_settings: Dict = None,
    search_strategy: str = "PORTFOLIO",
    warm_start_shifts: Optional[Dict[Tuple[int, date], str]] = None,
    db_path: str = "dienstplan.db",
    random_seed: Optional[int] = None,
) -> Tuple[List[ShiftAssignment], Dict[Tuple[int, date], str], PlanningReport]:
    """
    Solve the shift planning problem.
    
    Args:
        planning_model: The shift planning model
        time_limit_seconds: Maximum time for solver in seconds. None (default) means no limit.
        num_workers: Number of parallel workers. None (default) auto-detects CPU cores via
            _default_num_workers() (all cores, capped at 16).
        global_settings: Dict with global settings from database (optional)
        search_strategy: Search branching strategy. Options:
            - "PORTFOLIO" (default): Parallel workers with different heuristics.
              Best for complex multi-team problems when num_workers > 1.
              Expected 10-30% faster than FIXED_SEARCH on diverse instances.
            - "FIXED_SEARCH": Deterministic variable ordering. Useful for
              debugging or when reproducibility is required.
            - "AUTOMATIC": Let OR-Tools choose automatically.
        warm_start_shifts: Optional dict of (employee_id, date) -> shift_code for
            previous shift assignments to use as solver hints (AddHint). Typically
            the previous month's complete schedule. Expected benefit: 20-40% faster
            first feasible solution on re-planning runs with similar structure.
        db_path: Path to the SQLite database file, used to load rotation group
            patterns. Defaults to "dienstplan.db".
        random_seed: Optional integer seed for the CP-SAT pseudo-random number
            generator. When set, results are reproducible across identical runs.
            Useful for regression testing and performance comparisons.
        
    Returns:
        Always returns a non-None 3-tuple of
        (shift_assignments, complete_schedule, planning_report).
        Uses a 4-stage fallback mechanism to guarantee a plan is always produced:
          Stage 1 – Normal: all hard + soft constraints.
          Stage 2 – Fallback 1: minimum staffing (H3) relaxed to soft with
                    penalty weight MIN_STAFFING_RELAXED_PENALTY_WEIGHT (200,000).
          Stage 3 – Fallback 2: minimum staffing soft + team rotation skipped.
          Stage 4 – Emergency plan: greedy assignment without OR-Tools.
        Which constraints were relaxed is printed via _print_relaxation_summary().
        - shift_assignments: List of ShiftAssignment objects for employees who work
        - complete_schedule: dict mapping (employee_id, date) to shift_code/"OFF"/"ABSENT"
                            ensuring ALL employees appear for ALL days
        - planning_report: PlanningReport with solver metrics, violations, and
                           relaxed constraints for this planning run
    """

    # Production default time limit for Stage 1: 20 minutes.
    # CP-SAT returns the best FEASIBLE solution found when the limit is reached,
    # so quality degrades gracefully instead of running forever.
    # Pass time_limit_seconds=0 to disable the time limit entirely; None uses this default.
    DEFAULT_STAGE1_TIME_LIMIT_SECONDS = 15 * 60  # 15 minutes (reduced from 20 to react faster)
    # Fallback stages get shorter individual limits so overall planning stays responsive.
    # Each fallback uses progressively fewer constraints, so less time is needed.
    DEFAULT_STAGE2_TIME_LIMIT_SECONDS = 8 * 60   # 8 minutes (min-staffing relaxed)
    DEFAULT_STAGE3_TIME_LIMIT_SECONDS = 5 * 60   # 5 minutes (rotation also relaxed)

    if time_limit_seconds == 0:
        # Explicit 0 means "no limit at all" for all stages
        stage1_limit = None
        stage2_limit = None
        stage3_limit = None
    elif time_limit_seconds is not None:
        # External override (e.g., test environments) applies to all stages
        stage1_limit = time_limit_seconds
        stage2_limit = time_limit_seconds
        stage3_limit = time_limit_seconds
    else:
        stage1_limit = DEFAULT_STAGE1_TIME_LIMIT_SECONDS
        stage2_limit = DEFAULT_STAGE2_TIME_LIMIT_SECONDS
        stage3_limit = DEFAULT_STAGE3_TIME_LIMIT_SECONDS

    def _make_solver(model: ShiftPlanningModel, level: int, limit=None) -> "ShiftPlanningSolver":
        return ShiftPlanningSolver(
            model, limit, num_workers, global_settings,
            db_path=db_path,
            search_strategy=search_strategy,
            warm_start_shifts=warm_start_shifts,
            relaxation_level=level,
            random_seed=random_seed,
        )

    def _rebuild_model() -> ShiftPlanningModel:
        """Return a fresh ShiftPlanningModel with identical configuration."""
        from model import ShiftPlanningModel as _SPM
        return _SPM(
            employees=planning_model.employees,
            teams=planning_model.teams,
            start_date=planning_model.original_start_date,
            end_date=planning_model.original_end_date,
            absences=planning_model.absences,
            shift_types=planning_model.shift_types,
            locked_team_shift=planning_model.locked_team_shift,
            locked_employee_weekend=planning_model.locked_employee_weekend,
            locked_absence=planning_model.locked_absence,
            locked_employee_shift=planning_model.locked_employee_shift,
            ytd_weekend_counts=planning_model.ytd_weekend_counts,
            ytd_night_counts=planning_model.ytd_night_counts,
            ytd_holiday_counts=planning_model.ytd_holiday_counts,
            previous_employee_shifts=planning_model.previous_employee_shifts,
        )

    # ------------------------------------------------------------------ #
    # Stage 1 – Normal solve                                              #
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 60)
    print("STUFE 1: Normaler Lösungsversuch (alle Hard-Constraints aktiv)")
    if stage1_limit:
        print(f"  Zeit-Limit: {stage1_limit} Sekunden "
              f"(beste FEASIBLE-Lösung wird bei Ablauf zurückgegeben)")
    print("=" * 60)
    s1 = _make_solver(planning_model, level=0, limit=stage1_limit)
    s1.add_all_constraints()
    if s1.solve():
        result = s1.extract_solution()
        s1.print_planning_summary(result[0], result[1])
        status = "OPTIMAL" if s1.status == cp_model.OPTIMAL else "FEASIBLE"
        report = _build_planning_report(
            assignments=result[0],
            complete_schedule=result[1],
            planning_model=planning_model,
            status=status,
            objective_value=s1.solution.ObjectiveValue() if s1.solution else 0.0,
            solver_time_seconds=s1.solution.WallTime() if s1.solution else 0.0,
            relaxed_constraints_strs=[],
            penalty_breakdown=s1.compute_penalty_breakdown(),
        )
        return result[0], result[1], report

    # ------------------------------------------------------------------ #
    # Stage 2 – Fallback 1: relax minimum staffing (H3)                  #
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 60)
    print("STUFE 2 (FALLBACK 1): Mindestbesetzung wird als Soft-Constraint behandelt")
    print("  Grund: Stufe 1 war INFEASIBLE oder hat keine Lösung innerhalb des Zeit-Limits gefunden")
    if stage2_limit:
        print(f"  Zeit-Limit: {stage2_limit} Sekunden")
    print("=" * 60)
    m2 = _rebuild_model()
    s2 = _make_solver(m2, level=1, limit=stage2_limit)
    s2.add_all_constraints()
    if s2.solve():
        result = s2.extract_solution()
        _print_relaxation_summary(s2.relaxed_constraints)
        s2.print_planning_summary(result[0], result[1])
        report = _build_planning_report(
            assignments=result[0],
            complete_schedule=result[1],
            planning_model=m2,
            status="FALLBACK_L1",
            objective_value=s2.solution.ObjectiveValue() if s2.solution else 0.0,
            solver_time_seconds=s2.solution.WallTime() if s2.solution else 0.0,
            relaxed_constraints_strs=s2.relaxed_constraints,
            penalty_breakdown=s2.compute_penalty_breakdown(),
        )
        return result[0], result[1], report

    # ------------------------------------------------------------------ #
    # Stage 3 – Fallback 2: relax staffing + skip rotation constraints   #
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 60)
    print("STUFE 3 (FALLBACK 2): Mindestbesetzung soft + Teamrotation deaktiviert")
    print("  Grund: Stufe 2 war INFEASIBLE oder hat keine Lösung innerhalb des Zeit-Limits gefunden")
    if stage3_limit:
        print(f"  Zeit-Limit: {stage3_limit} Sekunden")
    print("=" * 60)
    m3 = _rebuild_model()
    s3 = _make_solver(m3, level=2, limit=stage3_limit)
    s3.add_all_constraints()
    if s3.solve():
        result = s3.extract_solution()
        _print_relaxation_summary(s3.relaxed_constraints)
        s3.print_planning_summary(result[0], result[1])
        report = _build_planning_report(
            assignments=result[0],
            complete_schedule=result[1],
            planning_model=m3,
            status="FALLBACK_L2",
            objective_value=s3.solution.ObjectiveValue() if s3.solution else 0.0,
            solver_time_seconds=s3.solution.WallTime() if s3.solution else 0.0,
            relaxed_constraints_strs=s3.relaxed_constraints,
            penalty_breakdown=s3.compute_penalty_breakdown(),
        )
        return result[0], result[1], report

    # ------------------------------------------------------------------ #
    # Stage 4 – Emergency plan: greedy algorithm without OR-Tools         #
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 60)
    print("STUFE 4 (NOTFALLPLAN): Greedy-Algorithmus ohne OR-Tools")
    print("  Grund: Alle Solver-Stufen waren INFEASIBLE")
    print("=" * 60)
    greedy_relaxed = [
        "Mindestbesetzung (H3): nicht garantiert – nur verfügbare Mitarbeiter werden eingeplant",
        "Teamrotation (F→N→S): nicht eingehalten",
        "Ruhezeiten, Stunden-Ziele, Aufeinanderfolge-Regeln: nicht berücksichtigt",
    ]
    result = _create_greedy_emergency_plan(planning_model)
    _print_relaxation_summary(greedy_relaxed)
    report = _build_planning_report(
        assignments=result[0],
        complete_schedule=result[1],
        planning_model=planning_model,
        status="EMERGENCY",
        objective_value=0.0,
        solver_time_seconds=0.0,
        relaxed_constraints_strs=greedy_relaxed,
    )
    return result[0], result[1], report


def get_infeasibility_diagnostics(
    planning_model: ShiftPlanningModel
) -> Dict[str, any]:
    """
    Get diagnostic information about potential infeasibility without running the solver.
    
    This is useful for pre-checking if a planning configuration is likely to succeed.
    
    Args:
        planning_model: The shift planning model to analyze
        
    Returns:
        Dictionary with diagnostic information
    """
    solver = ShiftPlanningSolver(planning_model, time_limit_seconds=1, num_workers=1)
    return solver.diagnose_infeasibility()


def analyze_absence_impact(
    employees: List,
    absences: List,
    dates: List[date],
    shift_requirements: List,
) -> Dict[date, AbsenceImpact]:
    """
    Analysiert die Abwesenheitsauswirkungen für jeden Tag im Planungszeitraum.

    Diese Funktion ist unabhängig vom Solver-Status und wird sowohl für FEASIBLE-
    als auch für INFEASIBLE-Planungen aufgerufen, damit der PlanningReport
    Risikotage dokumentieren kann.

    Args:
        employees:          Liste aller Employee-Objekte im Planungszeitraum.
        absences:           Liste aller Absence-Objekte im Planungszeitraum.
        dates:              Geordnete Liste der zu analysierenden Datumsangaben.
        shift_requirements: Liste der ShiftType-Objekte (mit min_staff_weekday /
                            min_staff_weekend und works_on_date()).

    Returns:
        Dict[date, AbsenceImpact] – ein Eintrag pro Tag in ``dates``.
    """
    # Pre-compute per-day absence sets for O(1) lookup
    # Maps date -> set of employee_ids absent that day
    absent_per_day: Dict[date, set] = {d: set() for d in dates}
    for absence in absences:
        for d in dates:
            if absence.start_date <= d <= absence.end_date:
                absent_per_day[d].add(absence.employee_id)

    total_employees = len(employees)
    all_employee_ids = {e.id for e in employees}

    result: Dict[date, AbsenceImpact] = {}

    for d in dates:
        absent_ids = absent_per_day[d]
        absent_count = len(absent_ids)
        available_count = total_employees - absent_count
        absence_ratio = absent_count / total_employees if total_employees > 0 else 0.0

        # Determine which shifts are active on this day
        is_weekend = d.weekday() >= 5  # Saturday=5, Sunday=6
        active_shifts = [
            st for st in shift_requirements
            if st.works_on_date(d)
        ]

        # Calculate minimum staffing needed across all active shifts
        total_min_needed = 0
        affected_shift_codes: List[str] = []
        for st in active_shifts:
            min_needed = st.min_staff_weekend if is_weekend else st.min_staff_weekday
            total_min_needed += min_needed
            # A shift is "affected" when available staff is less than its minimum
            if available_count < min_needed:
                affected_shift_codes.append(st.code)

        # Can we theoretically staff all shifts at their minimums?
        min_staffing_reachable = (available_count >= total_min_needed)

        # Buffer ratio: how much slack exists relative to available staff.
        # buffer_ratio = (available - needed) / available
        # Negative means understaffed; < 0.20 triggers has_risk.
        if available_count > 0:
            buffer_ratio = (available_count - total_min_needed) / available_count
        else:
            buffer_ratio = -1.0  # No staff at all

        has_risk = buffer_ratio < 0.20

        result[d] = AbsenceImpact(
            date=d,
            total_employees=total_employees,
            absent_count=absent_count,
            absence_ratio=absence_ratio,
            affected_shift_codes=affected_shift_codes,
            min_staffing_reachable=min_staffing_reachable,
            has_risk=has_risk,
            available_count=available_count,
            buffer_ratio=buffer_ratio,
        )

    return result


if __name__ == "__main__":
    # Test solver
    from data_loader import generate_sample_data
    from model import create_shift_planning_model
    from datetime import timedelta
    
    print("Generating sample data...")
    employees, teams, absences = generate_sample_data()
    
    start = date.today()
    end = start + timedelta(days=13)  # 2 weeks
    
    print("Creating model...")
    planning_model = create_shift_planning_model(employees, teams, start, end, absences, shift_types=STANDARD_SHIFT_TYPES)
    planning_model.print_model_statistics()
    
    print("\nSolving...")
    result = solve_shift_planning(planning_model, time_limit_seconds=60)
    
    assignments, complete_schedule = result
    print(f"\n✓ Solution produced!")
    print(f"  - Total assignments: {len(assignments)}")
    print(f"  - Complete schedule entries: {len(complete_schedule)}")
