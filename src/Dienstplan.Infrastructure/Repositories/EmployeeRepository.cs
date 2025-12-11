using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;
using Dienstplan.Infrastructure.Data;

namespace Dienstplan.Infrastructure.Repositories;

public class EmployeeRepository : AuditableRepository<Employee>, IEmployeeRepository
{
    private new readonly DienstplanDbContext _context;

    public EmployeeRepository(
        DienstplanDbContext context,
        IAuditService? auditService = null,
        IHttpContextAccessor? httpContextAccessor = null)
        : base(context, auditService, httpContextAccessor)
    {
        _context = context;
    }

    public new async Task<Employee?> GetByIdAsync(int id)
    {
        return await _context.Employees
            .Include(e => e.Team)
            .Include(e => e.Absences)
            .FirstOrDefaultAsync(e => e.Id == id);
    }

    public new async Task<IEnumerable<Employee>> GetAllAsync()
    {
        return await _context.Employees
            .Include(e => e.Team)
            .ToListAsync();
    }

    public async Task<IEnumerable<Employee>> GetSpringersAsync()
    {
        return await _context.Employees
            .Where(e => e.IsSpringer)
            .ToListAsync();
    }

    public async Task<IEnumerable<Employee>> GetByTeamIdAsync(int teamId)
    {
        return await _context.Employees
            .Where(e => e.TeamId == teamId)
            .ToListAsync();
    }

    public async Task<Employee?> GetByPersonalnummerAsync(string personalnummer)
    {
        return await _context.Employees
            .FirstOrDefaultAsync(e => e.Personalnummer == personalnummer);
    }

    public async Task<(IEnumerable<Employee> Items, int TotalCount)> SearchAsync(
        int page,
        int pageSize,
        string? searchTerm = null,
        int? teamId = null,
        bool? isSpringer = null)
    {
        var query = _context.Employees
            .Include(e => e.Team)
            .AsQueryable();

        // Apply search filter
        if (!string.IsNullOrEmpty(searchTerm))
        {
            query = query.Where(e =>
                e.Vorname.Contains(searchTerm) ||
                e.Name.Contains(searchTerm) ||
                e.Personalnummer.Contains(searchTerm) ||
                (e.Email != null && e.Email.Contains(searchTerm)));
        }

        // Apply team filter
        if (teamId.HasValue)
        {
            query = query.Where(e => e.TeamId == teamId.Value);
        }

        // Apply springer filter
        if (isSpringer.HasValue)
        {
            query = query.Where(e => e.IsSpringer == isSpringer.Value);
        }

        query = query.OrderBy(e => e.Name).ThenBy(e => e.Vorname);

        var totalCount = await query.CountAsync();
        var items = await query
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync();

        return (items, totalCount);
    }
}
