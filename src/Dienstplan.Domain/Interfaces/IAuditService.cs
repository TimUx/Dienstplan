using Dienstplan.Domain.Entities;

namespace Dienstplan.Domain.Interfaces;

/// <summary>
/// Service interface for audit logging
/// </summary>
public interface IAuditService
{
    /// <summary>
    /// Logs an audit entry for entity creation
    /// </summary>
    Task LogCreatedAsync<T>(T entity, string userId, string userName, string? ipAddress = null) where T : class;
    
    /// <summary>
    /// Logs an audit entry for entity update
    /// </summary>
    Task LogUpdatedAsync<T>(T oldEntity, T newEntity, string userId, string userName, string? ipAddress = null) where T : class;
    
    /// <summary>
    /// Logs an audit entry for entity deletion
    /// </summary>
    Task LogDeletedAsync<T>(T entity, string userId, string userName, string? ipAddress = null) where T : class;
}
