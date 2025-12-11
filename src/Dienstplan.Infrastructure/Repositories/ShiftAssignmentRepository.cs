using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;
using Dienstplan.Infrastructure.Data;

namespace Dienstplan.Infrastructure.Repositories;

public class ShiftAssignmentRepository : AuditableRepository<ShiftAssignment>, IShiftAssignmentRepository
{
    private new readonly DienstplanDbContext _context;

    public ShiftAssignmentRepository(
        DienstplanDbContext context,
        IAuditService? auditService = null,
        IHttpContextAccessor? httpContextAccessor = null)
        : base(context, auditService, httpContextAccessor)
    {
        _context = context;
    }

    public new async Task<ShiftAssignment?> GetByIdAsync(int id)
    {
        return await _context.ShiftAssignments
            .Include(s => s.Employee)
            .Include(s => s.ShiftType)
            .FirstOrDefaultAsync(s => s.Id == id);
    }

    public new async Task<IEnumerable<ShiftAssignment>> GetAllAsync()
    {
        return await _context.ShiftAssignments
            .Include(s => s.Employee)
            .Include(s => s.ShiftType)
            .ToListAsync();
    }

    public async Task<IEnumerable<ShiftAssignment>> GetByDateRangeAsync(DateTime startDate, DateTime endDate)
    {
        return await _context.ShiftAssignments
            .Include(s => s.Employee)
                .ThenInclude(e => e.Team)
            .Include(s => s.ShiftType)
            .Where(s => s.Date >= startDate && s.Date <= endDate)
            .OrderBy(s => s.Date)
            .ThenBy(s => s.Employee.Name)
            .ToListAsync();
    }

    public async Task<IEnumerable<ShiftAssignment>> GetByEmployeeIdAsync(int employeeId)
    {
        return await _context.ShiftAssignments
            .Include(s => s.ShiftType)
            .Where(s => s.EmployeeId == employeeId)
            .OrderBy(s => s.Date)
            .ToListAsync();
    }

    public async Task<ShiftAssignment?> GetByEmployeeAndDateAsync(int employeeId, DateTime date)
    {
        return await _context.ShiftAssignments
            .Include(s => s.ShiftType)
            .FirstOrDefaultAsync(s => s.EmployeeId == employeeId && s.Date.Date == date.Date);
    }
}
