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
    
    /// <summary>
    /// Indicates if this is a fixed assignment (e.g., for holidays) that should not be changed by automatic planning
    /// </summary>
    public bool IsFixed { get; set; }
    
    public string? Notes { get; set; }
    
    /// <summary>
    /// When the assignment was created
    /// </summary>
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    
    /// <summary>
    /// When the assignment was last modified
    /// </summary>
    public DateTime? ModifiedAt { get; set; }
    
    /// <summary>
    /// User who created this assignment
    /// </summary>
    public string? CreatedBy { get; set; }
    
    /// <summary>
    /// User who last modified this assignment
    /// </summary>
    public string? ModifiedBy { get; set; }
}
