using Microsoft.EntityFrameworkCore;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;
using Dienstplan.Infrastructure.Data;

namespace Dienstplan.Infrastructure.Repositories;

public class ShiftAssignmentRepository : IShiftAssignmentRepository
{
    private readonly DienstplanDbContext _context;

    public ShiftAssignmentRepository(DienstplanDbContext context)
    {
        _context = context;
    }

    public async Task<ShiftAssignment?> GetByIdAsync(int id)
    {
        return await _context.ShiftAssignments
            .Include(s => s.Employee)
            .Include(s => s.ShiftType)
            .FirstOrDefaultAsync(s => s.Id == id);
    }

    public async Task<IEnumerable<ShiftAssignment>> GetAllAsync()
    {
        return await _context.ShiftAssignments
            .Include(s => s.Employee)
            .Include(s => s.ShiftType)
            .ToListAsync();
    }

    public async Task<ShiftAssignment> AddAsync(ShiftAssignment entity)
    {
        _context.ShiftAssignments.Add(entity);
        await _context.SaveChangesAsync();
        return entity;
    }

    public async Task<ShiftAssignment> UpdateAsync(ShiftAssignment entity)
    {
        _context.Entry(entity).State = EntityState.Modified;
        await _context.SaveChangesAsync();
        return entity;
    }

    public async Task DeleteAsync(int id)
    {
        var assignment = await _context.ShiftAssignments.FindAsync(id);
        if (assignment != null)
        {
            _context.ShiftAssignments.Remove(assignment);
            await _context.SaveChangesAsync();
        }
    }

    public async Task<IEnumerable<ShiftAssignment>> GetByDateRangeAsync(DateTime startDate, DateTime endDate)
    {
        return await _context.ShiftAssignments
            .Include(s => s.Employee)
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
