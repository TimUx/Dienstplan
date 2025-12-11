namespace Dienstplan.Domain.Entities;

public enum AuditAction
{
    Created,
    Updated,
    Deleted
}

public class AuditLog
{
    public int Id { get; set; }
    public required string EntityName { get; set; }
    public required string EntityId { get; set; }
    public required AuditAction Action { get; set; }
    public string? Changes { get; set; } // JSON string with changes
    public required string UserId { get; set; }
    public required string UserName { get; set; }
    public DateTime Timestamp { get; set; }
    public string? IpAddress { get; set; }
}
