namespace Dienstplan.Domain.Entities;

/// <summary>
/// Represents an employee (Mitarbeiter) in the shift scheduling system
/// </summary>
public class Employee
{
    public int Id { get; set; }
    
    /// <summary>
    /// First name (Vorname) - required field
    /// </summary>
    public string Vorname { get; set; } = string.Empty;
    
    /// <summary>
    /// Last name (Name) - required field
    /// </summary>
    public string Name { get; set; } = string.Empty;
    
    /// <summary>
    /// Personnel number (Personalnummer) - required field
    /// </summary>
    public string Personalnummer { get; set; } = string.Empty;
    
    /// <summary>
    /// Indicates if this employee is a backup worker (Springer)
    /// </summary>
    public bool IsSpringer { get; set; }
    
    /// <summary>
    /// Team assignment
    /// </summary>
    public int? TeamId { get; set; }
    public Team? Team { get; set; }
    
    /// <summary>
    /// Absences for this employee
    /// </summary>
    public ICollection<Absence> Absences { get; set; } = new List<Absence>();
    
    /// <summary>
    /// Shift assignments for this employee
    /// </summary>
    public ICollection<ShiftAssignment> ShiftAssignments { get; set; } = new List<ShiftAssignment>();
    
    /// <summary>
    /// Full display name
    /// </summary>
    public string FullName => $"{Vorname} {Name}";
}
