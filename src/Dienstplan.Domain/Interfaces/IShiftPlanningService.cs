using Dienstplan.Domain.Entities;

namespace Dienstplan.Domain.Interfaces;

/// <summary>
/// Service for automatic shift planning
/// </summary>
public interface IShiftPlanningService
{
    /// <summary>
    /// Plans shifts for a given date range
    /// </summary>
    Task<List<ShiftAssignment>> PlanShifts(DateTime startDate, DateTime endDate, bool force = false);
    
    /// <summary>
    /// Validates if a shift assignment is allowed
    /// </summary>
    Task<(bool IsValid, string? ErrorMessage)> ValidateShiftAssignment(ShiftAssignment assignment);
    
    /// <summary>
    /// Assigns a Springer (backup) for an absent employee
    /// </summary>
    Task<ShiftAssignment?> AssignSpringer(int employeeId, DateTime date);
}
