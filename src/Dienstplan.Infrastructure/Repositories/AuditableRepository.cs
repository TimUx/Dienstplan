using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;
using Dienstplan.Domain.Interfaces;
using Dienstplan.Infrastructure.Data;

namespace Dienstplan.Infrastructure.Repositories;

/// <summary>
/// Repository base class with automatic audit logging support
/// </summary>
public class AuditableRepository<T> : Repository<T> where T : class
{
    private readonly IAuditService? _auditService;
    private readonly IHttpContextAccessor? _httpContextAccessor;

    public AuditableRepository(
        DienstplanDbContext context,
        IAuditService? auditService = null,
        IHttpContextAccessor? httpContextAccessor = null) 
        : base(context)
    {
        _auditService = auditService;
        _httpContextAccessor = httpContextAccessor;
    }

    public override async Task<T> AddAsync(T entity)
    {
        var result = await base.AddAsync(entity);
        
        // Log the creation if audit service is available
        if (_auditService != null)
        {
            var (userId, userName) = GetUserInfo();
            await _auditService.LogCreatedAsync(entity, userId, userName);
        }
        
        return result;
    }

    public override async Task<T> UpdateAsync(T entity)
    {
        // Get the old entity for comparison
        T? oldEntity = null;
        if (_auditService != null)
        {
            var idProperty = typeof(T).GetProperty("Id");
            if (idProperty != null)
            {
                var id = idProperty.GetValue(entity);
                if (id != null)
                {
                    oldEntity = await _dbSet.AsNoTracking()
                        .FirstOrDefaultAsync(e => EF.Property<object>(e, "Id").Equals(id));
                }
            }
        }

        var result = await base.UpdateAsync(entity);
        
        // Log the update if audit service is available
        if (_auditService != null && oldEntity != null)
        {
            var (userId, userName) = GetUserInfo();
            await _auditService.LogUpdatedAsync(oldEntity, entity, userId, userName);
        }
        
        return result;
    }

    public override async Task DeleteAsync(int id)
    {
        // Get the entity before deletion for audit log
        T? entity = null;
        if (_auditService != null)
        {
            entity = await GetByIdAsync(id);
        }

        await base.DeleteAsync(id);
        
        // Log the deletion if audit service is available
        if (_auditService != null && entity != null)
        {
            var (userId, userName) = GetUserInfo();
            await _auditService.LogDeletedAsync(entity, userId, userName);
        }
    }

    private (string userId, string userName) GetUserInfo()
    {
        try
        {
            var context = _httpContextAccessor?.HttpContext;
            if (context?.User?.Identity?.IsAuthenticated == true)
            {
                var userId = context.User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value ?? "Unknown";
                var userName = context.User.Identity.Name ?? "Unknown";
                return (userId, userName);
            }
        }
        catch
        {
            // Fallback if unable to get user info
        }
        
        return ("System", "System");
    }
}
