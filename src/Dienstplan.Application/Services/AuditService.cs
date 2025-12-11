using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;

namespace Dienstplan.Application.Services;

/// <summary>
/// Service for automatic audit logging of entity changes
/// </summary>
public class AuditService : IAuditService
{
    private readonly IAuditLogRepository _auditLogRepository;
    private readonly IHttpContextAccessor _httpContextAccessor;

    public AuditService(
        IAuditLogRepository auditLogRepository,
        IHttpContextAccessor httpContextAccessor)
    {
        _auditLogRepository = auditLogRepository;
        _httpContextAccessor = httpContextAccessor;
    }

    public async Task LogCreatedAsync<T>(T entity, string userId, string userName, string? ipAddress = null) where T : class
    {
        var auditLog = new AuditLog
        {
            EntityName = typeof(T).Name,
            EntityId = GetEntityId(entity),
            Action = AuditAction.Created,
            Changes = SerializeEntity(entity),
            UserId = userId,
            UserName = userName,
            Timestamp = DateTime.UtcNow,
            IpAddress = ipAddress ?? GetIpAddress()
        };

        await _auditLogRepository.AddAsync(auditLog);
    }

    public async Task LogUpdatedAsync<T>(T oldEntity, T newEntity, string userId, string userName, string? ipAddress = null) where T : class
    {
        var changes = CompareEntities(oldEntity, newEntity);
        
        var auditLog = new AuditLog
        {
            EntityName = typeof(T).Name,
            EntityId = GetEntityId(newEntity),
            Action = AuditAction.Updated,
            Changes = JsonSerializer.Serialize(changes, new JsonSerializerOptions { WriteIndented = true }),
            UserId = userId,
            UserName = userName,
            Timestamp = DateTime.UtcNow,
            IpAddress = ipAddress ?? GetIpAddress()
        };

        await _auditLogRepository.AddAsync(auditLog);
    }

    public async Task LogDeletedAsync<T>(T entity, string userId, string userName, string? ipAddress = null) where T : class
    {
        var auditLog = new AuditLog
        {
            EntityName = typeof(T).Name,
            EntityId = GetEntityId(entity),
            Action = AuditAction.Deleted,
            Changes = SerializeEntity(entity),
            UserId = userId,
            UserName = userName,
            Timestamp = DateTime.UtcNow,
            IpAddress = ipAddress ?? GetIpAddress()
        };

        await _auditLogRepository.AddAsync(auditLog);
    }

    private string GetEntityId(object entity)
    {
        var idProperty = entity.GetType().GetProperty("Id");
        return idProperty?.GetValue(entity)?.ToString() ?? "Unknown";
    }

    private string SerializeEntity(object entity)
    {
        try
        {
            var options = new JsonSerializerOptions 
            { 
                WriteIndented = true,
                ReferenceHandler = System.Text.Json.Serialization.ReferenceHandler.IgnoreCycles
            };
            return JsonSerializer.Serialize(entity, options);
        }
        catch
        {
            return "Serialization failed";
        }
    }

    private Dictionary<string, object?> CompareEntities<T>(T oldEntity, T newEntity) where T : class
    {
        var changes = new Dictionary<string, object?>();
        var properties = typeof(T).GetProperties();

        foreach (var property in properties)
        {
            // Skip navigation properties and complex types
            if (property.PropertyType.IsClass && 
                property.PropertyType != typeof(string) && 
                !property.PropertyType.IsArray)
            {
                continue;
            }

            var oldValue = property.GetValue(oldEntity);
            var newValue = property.GetValue(newEntity);

            if (!Equals(oldValue, newValue))
            {
                changes[property.Name] = new
                {
                    Old = oldValue,
                    New = newValue
                };
            }
        }

        return changes;
    }

    private string? GetIpAddress()
    {
        try
        {
            var context = _httpContextAccessor.HttpContext;
            if (context == null) return null;

            var ipAddress = context.Request.Headers["X-Forwarded-For"].FirstOrDefault();
            if (string.IsNullOrEmpty(ipAddress))
            {
                ipAddress = context.Connection.RemoteIpAddress?.ToString();
            }

            return ipAddress;
        }
        catch
        {
            return null;
        }
    }
}
