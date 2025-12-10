using Microsoft.EntityFrameworkCore;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;
using Dienstplan.Infrastructure.Data;

namespace Dienstplan.Infrastructure.Repositories;

public class AbsenceRepository : IAbsenceRepository
{
    private readonly DienstplanDbContext _context;

    public AbsenceRepository(DienstplanDbContext context)
    {
        _context = context;
    }

    public async Task<Absence?> GetByIdAsync(int id)
    {
        return await _context.Absences
            .Include(a => a.Employee)
            .FirstOrDefaultAsync(a => a.Id == id);
    }

    public async Task<IEnumerable<Absence>> GetAllAsync()
    {
        return await _context.Absences
            .Include(a => a.Employee)
            .ToListAsync();
    }

    public async Task<Absence> AddAsync(Absence entity)
    {
        _context.Absences.Add(entity);
        await _context.SaveChangesAsync();
        return entity;
    }

    public async Task<Absence> UpdateAsync(Absence entity)
    {
        _context.Entry(entity).State = EntityState.Modified;
        await _context.SaveChangesAsync();
        return entity;
    }

    public async Task DeleteAsync(int id)
    {
        var absence = await _context.Absences.FindAsync(id);
        if (absence != null)
        {
            _context.Absences.Remove(absence);
            await _context.SaveChangesAsync();
        }
    }

    public async Task<IEnumerable<Absence>> GetByEmployeeIdAsync(int employeeId)
    {
        return await _context.Absences
            .Where(a => a.EmployeeId == employeeId)
            .OrderBy(a => a.StartDate)
            .ToListAsync();
    }

    public async Task<IEnumerable<Absence>> GetByDateRangeAsync(DateTime startDate, DateTime endDate)
    {
        return await _context.Absences
            .Include(a => a.Employee)
            .Where(a => a.StartDate <= endDate && a.EndDate >= startDate)
            .OrderBy(a => a.StartDate)
            .ToListAsync();
    }
}
