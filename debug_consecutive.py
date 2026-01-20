"""
Analyze consecutive days constraint interaction.
"""

num_days = 31
days_needed = 22.1
max_consecutive = 6

print("=" * 80)
print("CONSECUTIVE DAYS CONSTRAINT ANALYSIS")
print("=" * 80)

print(f"\nRequirement:")
print(f"  Days needed: {days_needed:.1f} out of {num_days} days")
print(f"  Maximum consecutive working days: {max_consecutive}")

# Best case pattern: work 6, rest 1, work 6, rest 1, ...
best_case_days = 0
current_day = 0
while current_day < num_days:
    work_block = min(max_consecutive, num_days - current_day)
    best_case_days += work_block
    current_day += work_block + 1  # work + 1 rest day

print(f"\nBest case scenario (work {max_consecutive}, rest 1, repeat):")
print(f"  Can work up to: {best_case_days} days")
print(f"  Meets requirement: {best_case_days >= days_needed}")

# Calculate minimum rest days needed
if days_needed > max_consecutive:
    # Need to break into blocks
    num_blocks = int((days_needed + max_consecutive - 1) / max_consecutive)  # Ceiling division
    min_rest_days = num_blocks - 1
    total_days_needed = days_needed + min_rest_days
    
    print(f"\nWith {days_needed:.1f} days needed and max {max_consecutive} consecutive:")
    print(f"  Need {num_blocks} blocks of work")
    print(f"  Minimum rest days between blocks: {min_rest_days}")
    print(f"  Total days span needed: {total_days_needed:.1f}")
    print(f"  Fits in {num_days} days: {total_days_needed <= num_days}")

print("\n" + "=" * 80)
