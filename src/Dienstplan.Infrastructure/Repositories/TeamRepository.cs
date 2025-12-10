using Microsoft.EntityFrameworkCore;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;
using Dienstplan.Infrastructure.Data;

namespace Dienstplan.Infrastructure.Repositories;

public class TeamRepository : ITeamRepository
{
    private readonly DienstplanDbContext _context;

    public TeamRepository(DienstplanDbContext context)
    {
        _context = context;
    }

    public async Task<Team?> GetByIdAsync(int id)
    {
        return await _context.Teams
            .Include(t => t.Employees)
            .FirstOrDefaultAsync(t => t.Id == id);
    }

    public async Task<IEnumerable<Team>> GetAllAsync()
    {
        return await _context.Teams
            .Include(t => t.Employees)
            .ToListAsync();
    }

    public async Task<Team> AddAsync(Team entity)
    {
        _context.Teams.Add(entity);
        await _context.SaveChangesAsync();
        return entity;
    }

    public async Task<Team> UpdateAsync(Team entity)
    {
        _context.Teams.Update(entity);
        await _context.SaveChangesAsync();
        return entity;
    }

    public async Task DeleteAsync(int id)
    {
        var team = await _context.Teams.FindAsync(id);
        if (team != null)
        {
            _context.Teams.Remove(team);
            await _context.SaveChangesAsync();
        }
    }

    public async Task<Team?> GetByNameAsync(string name)
    {
        return await _context.Teams
            .FirstOrDefaultAsync(t => t.Name == name);
    }
}
