namespace Dienstplan.Domain.Entities;

/// <summary>
/// Represents a vacation request (Urlaubswunsch) from an employee
/// </summary>
public class VacationRequest
{
    public int Id { get; set; }
    
    public int EmployeeId { get; set; }
    public Employee Employee { get; set; } = null!;
    
    public DateTime StartDate { get; set; }
    
    public DateTime EndDate { get; set; }
    
    /// <summary>
    /// Status of the vacation request
    /// </summary>
    public VacationRequestStatus Status { get; set; } = VacationRequestStatus.InBearbeitung;
    
    /// <summary>
    /// Notes from the employee
    /// </summary>
    public string? Notes { get; set; }
    
    /// <summary>
    /// Response/notes from the Disponent
    /// </summary>
    public string? DisponentResponse { get; set; }
    
    /// <summary>
    /// When the request was created
    /// </summary>
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    
    /// <summary>
    /// When the request was last updated
    /// </summary>
    public DateTime? UpdatedAt { get; set; }
    
    /// <summary>
    /// User who processed the request
    /// </summary>
    public string? ProcessedBy { get; set; }
}

/// <summary>
/// Status of a vacation request
/// </summary>
public enum VacationRequestStatus
{
    /// <summary>
    /// In processing (In Bearbeitung)
    /// </summary>
    InBearbeitung = 1,
    
    /// <summary>
    /// Approved (Genehmigt)
    /// </summary>
    Genehmigt = 2,
    
    /// <summary>
    /// Not approved/Rejected (Nicht genehmigt)
    /// </summary>
    NichtGenehmigt = 3
}
