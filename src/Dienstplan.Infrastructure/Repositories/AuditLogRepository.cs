using Microsoft.EntityFrameworkCore;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;
using Dienstplan.Infrastructure.Data;

namespace Dienstplan.Infrastructure.Repositories;

public class AuditLogRepository : Repository<AuditLog>, IAuditLogRepository
{
    public AuditLogRepository(DienstplanDbContext context) : base(context)
    {
    }

    public async Task<IEnumerable<AuditLog>> GetByEntityAsync(string entityName, string entityId)
    {
        return await _dbSet
            .Where(a => a.EntityName == entityName && a.EntityId == entityId)
            .OrderByDescending(a => a.Timestamp)
            .ToListAsync();
    }

    public async Task<IEnumerable<AuditLog>> GetByUserAsync(string userId)
    {
        return await _dbSet
            .Where(a => a.UserId == userId)
            .OrderByDescending(a => a.Timestamp)
            .ToListAsync();
    }

    public async Task<IEnumerable<AuditLog>> GetRecentAsync(int count)
    {
        return await _dbSet
            .OrderByDescending(a => a.Timestamp)
            .Take(count)
            .ToListAsync();
    }

    public async Task<(IEnumerable<AuditLog> Items, int TotalCount)> GetPagedAsync(int page, int pageSize)
    {
        var query = _dbSet.OrderByDescending(a => a.Timestamp);
        
        var totalCount = await query.CountAsync();
        var items = await query
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync();

        return (items, totalCount);
    }

    public async Task<(IEnumerable<AuditLog> Items, int TotalCount)> SearchAsync(
        int page,
        int pageSize,
        string? entityName = null,
        string? action = null,
        DateTime? startDate = null,
        DateTime? endDate = null,
        string? userId = null)
    {
        var query = _dbSet.AsQueryable();

        // Apply filters
        if (!string.IsNullOrEmpty(entityName))
        {
            query = query.Where(a => a.EntityName.Contains(entityName));
        }

        if (!string.IsNullOrEmpty(action))
        {
            if (Enum.TryParse<AuditAction>(action, true, out var auditAction))
            {
                query = query.Where(a => a.Action == auditAction);
            }
        }

        if (startDate.HasValue)
        {
            query = query.Where(a => a.Timestamp >= startDate.Value);
        }

        if (endDate.HasValue)
        {
            query = query.Where(a => a.Timestamp <= endDate.Value);
        }

        if (!string.IsNullOrEmpty(userId))
        {
            query = query.Where(a => a.UserId == userId);
        }

        query = query.OrderByDescending(a => a.Timestamp);

        var totalCount = await query.CountAsync();
        var items = await query
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync();

        return (items, totalCount);
    }
}
