namespace Dienstplan.Domain.Entities;

public class AuditLog
{
    public int Id { get; set; }
    public required string EntityName { get; set; }
    public required string EntityId { get; set; }
    public required string Action { get; set; } // Created, Updated, Deleted
    public string? Changes { get; set; } // JSON string with changes
    public required string UserId { get; set; }
    public required string UserName { get; set; }
    public DateTime Timestamp { get; set; }
    public string? IpAddress { get; set; }
}
