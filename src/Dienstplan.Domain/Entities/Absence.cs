namespace Dienstplan.Domain.Entities;

/// <summary>
/// Represents an absence (Abwesenheit) of an employee
/// </summary>
public class Absence
{
    public int Id { get; set; }
    
    public int EmployeeId { get; set; }
    public Employee Employee { get; set; } = null!;
    
    public AbsenceType Type { get; set; }
    
    public DateTime StartDate { get; set; }
    
    public DateTime EndDate { get; set; }
    
    public string? Notes { get; set; }
}

/// <summary>
/// Types of absence (Krank, Urlaub, Lehrgang)
/// </summary>
public enum AbsenceType
{
    /// <summary>
    /// Sick leave (Krank)
    /// </summary>
    Krank = 1,
    
    /// <summary>
    /// Vacation (Urlaub)
    /// </summary>
    Urlaub = 2,
    
    /// <summary>
    /// Training course (Lehrgang)
    /// </summary>
    Lehrgang = 3
}
