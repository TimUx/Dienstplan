namespace Dienstplan.Domain.Entities;

/// <summary>
/// Represents a shift assignment to an employee
/// </summary>
public class ShiftAssignment
{
    public int Id { get; set; }
    
    public int EmployeeId { get; set; }
    public Employee Employee { get; set; } = null!;
    
    public int ShiftTypeId { get; set; }
    public ShiftType ShiftType { get; set; } = null!;
    
    public DateTime Date { get; set; }
    
    /// <summary>
    /// Indicates if this assignment was manually set (overriding automatic planning)
    /// </summary>
    public bool IsManual { get; set; }
    
    /// <summary>
    /// Indicates if this is a Springer (backup) assignment
    /// </summary>
    public bool IsSpringerAssignment { get; set; }
    
    public string? Notes { get; set; }
}
