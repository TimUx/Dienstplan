using Microsoft.EntityFrameworkCore;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;
using Dienstplan.Infrastructure.Data;

namespace Dienstplan.Infrastructure.Repositories;

public class EmployeeRepository : IEmployeeRepository
{
    private readonly DienstplanDbContext _context;

    public EmployeeRepository(DienstplanDbContext context)
    {
        _context = context;
    }

    public async Task<Employee?> GetByIdAsync(int id)
    {
        return await _context.Employees
            .Include(e => e.Team)
            .Include(e => e.Absences)
            .FirstOrDefaultAsync(e => e.Id == id);
    }

    public async Task<IEnumerable<Employee>> GetAllAsync()
    {
        return await _context.Employees
            .Include(e => e.Team)
            .ToListAsync();
    }

    public async Task<Employee> AddAsync(Employee entity)
    {
        _context.Employees.Add(entity);
        await _context.SaveChangesAsync();
        return entity;
    }

    public async Task<Employee> UpdateAsync(Employee entity)
    {
        _context.Entry(entity).State = EntityState.Modified;
        await _context.SaveChangesAsync();
        return entity;
    }

    public async Task DeleteAsync(int id)
    {
        var employee = await _context.Employees.FindAsync(id);
        if (employee != null)
        {
            _context.Employees.Remove(employee);
            await _context.SaveChangesAsync();
        }
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
}
