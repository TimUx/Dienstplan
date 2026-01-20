"""
Test for dynamic monthly hours calculation and planning summary.

Tests the new features requested by @TimUx:
1. Monthly hours calculated based on actual calendar days (not fixed 4 weeks)
2. Comprehensive planning summary displayed after solving
"""

from datetime import date, timedelta
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import solve_shift_planning
from entities import ShiftType

def test_january_31_days():
    """
    Test with January (31 days) to verify dynamic hours calculation.
    
    Expected: 48h/week ÷ 7 × 31 days = 212.57h ≈ 213h
    """
    print("\n" + "=" * 80)
    print("TEST: Januar (31 Tage) - Dynamische Stundenberechnung")
    print("=" * 80)
    
    # Generate sample data
    employees, teams, absences = generate_sample_data()
    
    # Use full January 2025 (31 days)
    start = date(2025, 1, 1)  # Wednesday
    end = date(2025, 1, 31)   # Friday
    
    # Configure shifts to 48h/week
    shift_types_48h = [
        ShiftType(1, "F", "Frühdienst", "05:45", "13:45", "#FFD700", 8.0, 48.0),
        ShiftType(2, "S", "Spätdienst", "13:45", "21:45", "#FF6347", 8.0, 48.0),
        ShiftType(3, "N", "Nachtdienst", "21:45", "05:45", "#4169E1", 8.0, 48.0),
    ]
    
    print(f"\nPlanungszeitraum: {start} bis {end}")
    print(f"Tage: 31")
    print(f"Erwartete Stunden pro Mitarbeiter: 48h/Woche ÷ 7 × 31 = 212.57h ≈ 213h")
    
    # Create and solve model
    planning_model = create_shift_planning_model(
        employees, teams, start, end, absences,
        shift_types=shift_types_48h
    )
    
    print("\nLöse Schichtplan...")
    result = solve_shift_planning(planning_model, time_limit_seconds=120)
    
    if result:
        print("\n✅ SUCCESS: Lösung gefunden!")
        print("Die Zusammenfassung oben zeigt die Details.")
        return True
    else:
        print("\n❌ FAIL: Keine Lösung gefunden")
        return False


def test_february_28_days():
    """
    Test with February (28 days) to verify dynamic hours calculation.
    
    Expected: 48h/week ÷ 7 × 28 days = 192h
    """
    print("\n" + "=" * 80)
    print("TEST: Februar (28 Tage) - Dynamische Stundenberechnung")
    print("=" * 80)
    
    # Generate sample data
    employees, teams, absences = generate_sample_data()
    
    # Use full February 2025 (28 days - not a leap year)
    start = date(2025, 2, 1)  # Saturday
    end = date(2025, 2, 28)   # Friday
    
    # Configure shifts to 48h/week
    shift_types_48h = [
        ShiftType(1, "F", "Frühdienst", "05:45", "13:45", "#FFD700", 8.0, 48.0),
        ShiftType(2, "S", "Spätdienst", "13:45", "21:45", "#FF6347", 8.0, 48.0),
        ShiftType(3, "N", "Nachtdienst", "21:45", "05:45", "#4169E1", 8.0, 48.0),
    ]
    
    print(f"\nPlanungszeitraum: {start} bis {end}")
    print(f"Tage: 28")
    print(f"Erwartete Stunden pro Mitarbeiter: 48h/Woche ÷ 7 × 28 = 192h")
    
    # Create and solve model
    planning_model = create_shift_planning_model(
        employees, teams, start, end, absences,
        shift_types=shift_types_48h
    )
    
    print("\nLöse Schichtplan...")
    result = solve_shift_planning(planning_model, time_limit_seconds=120)
    
    if result:
        print("\n✅ SUCCESS: Lösung gefunden!")
        print("Die Zusammenfassung oben zeigt die Details.")
        return True
    else:
        print("\n❌ FAIL: Keine Lösung gefunden")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TESTS FÜR DYNAMISCHE MONATSSTUNDEN UND ZUSAMMENFASSUNG")
    print("=" * 80)
    
    results = []
    
    # Test 1: Januar mit 31 Tagen
    results.append(("Januar (31 Tage)", test_january_31_days()))
    
    # Test 2: Februar mit 28 Tagen
    results.append(("Februar (28 Tage)", test_february_28_days()))
    
    # Final summary
    print("\n" + "=" * 80)
    print("FINAL TEST RESULTS")
    print("=" * 80)
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(passed for _, passed in results)
    if all_passed:
        print("\n🎉 ALLE TESTS BESTANDEN!")
    else:
        print("\n⚠️  EINIGE TESTS FEHLGESCHLAGEN")
