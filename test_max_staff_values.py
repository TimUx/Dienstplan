"""
Test to verify that max staff values have been increased to allow more flexibility.

This test verifies that all hardcoded max staff values are now 20 instead of
the previous restrictive values (8, 7, 5, 3), allowing the solver to find
solutions when users need more cross-team assignment flexibility.
"""

from entities import STANDARD_SHIFT_TYPES, ShiftType
from constraints import WEEKDAY_STAFFING, WEEKEND_STAFFING

def test_standard_shift_types_max_values():
    """Verify STANDARD_SHIFT_TYPES have high max values"""
    print("\n=== Testing STANDARD_SHIFT_TYPES Max Values ===")
    
    for shift_type in STANDARD_SHIFT_TYPES[:3]:  # F, S, N
        print(f"{shift_type.code}: weekday_max={shift_type.max_staff_weekday}, weekend_max={shift_type.max_staff_weekend}")
        
        # Verify max values are at least 20 (high flexibility)
        assert shift_type.max_staff_weekday >= 20, \
            f"{shift_type.code} max_staff_weekday should be >= 20, got {shift_type.max_staff_weekday}"
        assert shift_type.max_staff_weekend >= 20, \
            f"{shift_type.code} max_staff_weekend should be >= 20, got {shift_type.max_staff_weekend}"
    
    print("✓ All STANDARD_SHIFT_TYPES have max values >= 20")


def test_weekday_staffing_max_values():
    """Verify WEEKDAY_STAFFING fallback has high max values"""
    print("\n=== Testing WEEKDAY_STAFFING Max Values ===")
    
    for shift_code in ["F", "S", "N"]:
        max_val = WEEKDAY_STAFFING[shift_code]["max"]
        print(f"{shift_code}: max={max_val}")
        
        # Verify max values are at least 20 (high flexibility)
        assert max_val >= 20, \
            f"{shift_code} max should be >= 20, got {max_val}"
    
    print("✓ All WEEKDAY_STAFFING max values >= 20")


def test_weekend_staffing_max_values():
    """Verify WEEKEND_STAFFING fallback has high max values"""
    print("\n=== Testing WEEKEND_STAFFING Max Values ===")
    
    for shift_code in ["F", "S", "N"]:
        max_val = WEEKEND_STAFFING[shift_code]["max"]
        print(f"{shift_code}: max={max_val}")
        
        # Verify max values are at least 20 (high flexibility)
        assert max_val >= 20, \
            f"{shift_code} max should be >= 20, got {max_val}"
    
    print("✓ All WEEKEND_STAFFING max values >= 20")


def test_shift_type_dataclass_defaults():
    """Verify ShiftType dataclass defaults have high max values"""
    print("\n=== Testing ShiftType Dataclass Defaults ===")
    
    # Create a ShiftType with minimal parameters to test defaults
    test_shift = ShiftType(
        id=999,
        code="TEST",
        name="Test Shift",
        start_time="08:00",
        end_time="16:00"
    )
    
    print(f"Default max_staff_weekday: {test_shift.max_staff_weekday}")
    print(f"Default max_staff_weekend: {test_shift.max_staff_weekend}")
    
    # Verify default max values are at least 20 (high flexibility)
    assert test_shift.max_staff_weekday >= 20, \
        f"Default max_staff_weekday should be >= 20, got {test_shift.max_staff_weekday}"
    assert test_shift.max_staff_weekend >= 20, \
        f"Default max_staff_weekend should be >= 20, got {test_shift.max_staff_weekend}"
    
    print("✓ ShiftType dataclass defaults have max values >= 20")


def main():
    """Run all verification tests"""
    print("=" * 60)
    print("VERIFYING MAX STAFF VALUES HAVE BEEN INCREASED")
    print("=" * 60)
    
    test_standard_shift_types_max_values()
    test_weekday_staffing_max_values()
    test_weekend_staffing_max_values()
    test_shift_type_dataclass_defaults()
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED")
    print("=" * 60)
    print("\nResult: All hardcoded max staff values are now >= 20")
    print("This allows maximum flexibility for cross-team assignments")
    print("and ensures the solver won't be blocked by restrictive constraints.")


if __name__ == "__main__":
    main()
