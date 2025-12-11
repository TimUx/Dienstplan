namespace Dienstplan.Domain.Entities;

/// <summary>
/// Represents a shift exchange request (Diensttausch)
/// </summary>
public class ShiftExchange
{
    public int Id { get; set; }
    
    /// <summary>
    /// Employee offering the shift
    /// </summary>
    public int OfferingEmployeeId { get; set; }
    public Employee OfferingEmployee { get; set; } = null!;
    
    /// <summary>
    /// The shift being offered for exchange
    /// </summary>
    public int ShiftAssignmentId { get; set; }
    public ShiftAssignment ShiftAssignment { get; set; } = null!;
    
    /// <summary>
    /// Employee who wants to take the shift (null if not yet claimed)
    /// </summary>
    public int? RequestingEmployeeId { get; set; }
    public Employee? RequestingEmployee { get; set; }
    
    /// <summary>
    /// Status of the exchange
    /// </summary>
    public ShiftExchangeStatus Status { get; set; } = ShiftExchangeStatus.Angeboten;
    
    /// <summary>
    /// Reason for the exchange from offering employee
    /// </summary>
    public string? OfferingReason { get; set; }
    
    /// <summary>
    /// Notes from the Disponent
    /// </summary>
    public string? DisponentNotes { get; set; }
    
    /// <summary>
    /// When the exchange was created
    /// </summary>
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    
    /// <summary>
    /// When the exchange was last updated
    /// </summary>
    public DateTime? UpdatedAt { get; set; }
    
    /// <summary>
    /// User who processed the exchange
    /// </summary>
    public string? ProcessedBy { get; set; }
}

/// <summary>
/// Status of a shift exchange
/// </summary>
public enum ShiftExchangeStatus
{
    /// <summary>
    /// Offered for exchange (Angeboten)
    /// </summary>
    Angeboten = 1,
    
    /// <summary>
    /// Requested by another employee (Angefragt)
    /// </summary>
    Angefragt = 2,
    
    /// <summary>
    /// Approved by Disponent (Genehmigt)
    /// </summary>
    Genehmigt = 3,
    
    /// <summary>
    /// Rejected by Disponent (Abgelehnt)
    /// </summary>
    Abgelehnt = 4,
    
    /// <summary>
    /// Cancelled by offering employee (Zurückgezogen)
    /// </summary>
    Zurueckgezogen = 5,
    
    /// <summary>
    /// Completed (Abgeschlossen)
    /// </summary>
    Abgeschlossen = 6
}
