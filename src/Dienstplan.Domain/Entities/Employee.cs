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
    /// Email address for notifications
    /// </summary>
    public string? Email { get; set; }
    
    /// <summary>
    /// Birth date (Geburtsdatum)
    /// </summary>
    public DateTime? Geburtsdatum { get; set; }
    
    /// <summary>
    /// Function/Role of the employee (e.g., Brandmeldetechniker, Brandschutzbeauftragter)
    /// </summary>
    public string? Funktion { get; set; }
    
    /// <summary>
    /// Indicates if this employee is a backup worker (Springer)
    /// </summary>
    public bool IsSpringer { get; set; }
    
    /// <summary>
    /// Indicates if this is a temporary worker (Ferienjobber)
    /// </summary>
    public bool IsFerienjobber { get; set; }
    
    /// <summary>
    /// Indicates if this employee is qualified as Brandmeldetechniker (BMT)
    /// </summary>
    public bool IsBrandmeldetechniker { get; set; }
    
    /// <summary>
    /// Indicates if this employee is qualified as Brandschutzbeauftragter (BSB)
    /// </summary>
    public bool IsBrandschutzbeauftragter { get; set; }
    
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
    /// Vacation requests for this employee
    /// </summary>
    public ICollection<VacationRequest> VacationRequests { get; set; } = new List<VacationRequest>();
    
    /// <summary>
    /// Shift assignments for this employee
    /// </summary>
    public ICollection<ShiftAssignment> ShiftAssignments { get; set; } = new List<ShiftAssignment>();
    
    /// <summary>
    /// Full display name
    /// </summary>
    public string FullName => $"{Vorname} {Name}";
}
