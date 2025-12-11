using Microsoft.EntityFrameworkCore;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;
using Dienstplan.Infrastructure.Data;

namespace Dienstplan.Infrastructure.Repositories;

public class ShiftExchangeRepository : IShiftExchangeRepository
{
    private readonly DienstplanDbContext _context;

    public ShiftExchangeRepository(DienstplanDbContext context)
    {
        _context = context;
    }

    public async Task<ShiftExchange?> GetByIdAsync(int id)
    {
        return await _context.ShiftExchanges
            .Include(e => e.OfferingEmployee)
            .Include(e => e.RequestingEmployee)
            .Include(e => e.ShiftAssignment)
                .ThenInclude(s => s.ShiftType)
            .FirstOrDefaultAsync(e => e.Id == id);
    }

    public async Task<IEnumerable<ShiftExchange>> GetAllAsync()
    {
        return await _context.ShiftExchanges
            .Include(e => e.OfferingEmployee)
            .Include(e => e.RequestingEmployee)
            .Include(e => e.ShiftAssignment)
                .ThenInclude(s => s.ShiftType)
            .OrderByDescending(e => e.CreatedAt)
            .ToListAsync();
    }

    public async Task<ShiftExchange> AddAsync(ShiftExchange entity)
    {
        _context.ShiftExchanges.Add(entity);
        await _context.SaveChangesAsync();
        return entity;
    }

    public async Task<ShiftExchange> UpdateAsync(ShiftExchange entity)
    {
        entity.UpdatedAt = DateTime.UtcNow;
        _context.Entry(entity).State = EntityState.Modified;
        await _context.SaveChangesAsync();
        return entity;
    }

    public async Task DeleteAsync(int id)
    {
        var shiftExchange = await _context.ShiftExchanges.FindAsync(id);
        if (shiftExchange != null)
        {
            _context.ShiftExchanges.Remove(shiftExchange);
            await _context.SaveChangesAsync();
        }
    }

    public async Task<IEnumerable<ShiftExchange>> GetByOfferingEmployeeIdAsync(int employeeId)
    {
        return await _context.ShiftExchanges
            .Include(e => e.OfferingEmployee)
            .Include(e => e.RequestingEmployee)
            .Include(e => e.ShiftAssignment)
                .ThenInclude(s => s.ShiftType)
            .Where(e => e.OfferingEmployeeId == employeeId)
            .OrderByDescending(e => e.CreatedAt)
            .ToListAsync();
    }

    public async Task<IEnumerable<ShiftExchange>> GetByRequestingEmployeeIdAsync(int employeeId)
    {
        return await _context.ShiftExchanges
            .Include(e => e.OfferingEmployee)
            .Include(e => e.RequestingEmployee)
            .Include(e => e.ShiftAssignment)
                .ThenInclude(s => s.ShiftType)
            .Where(e => e.RequestingEmployeeId == employeeId)
            .OrderByDescending(e => e.CreatedAt)
            .ToListAsync();
    }

    public async Task<IEnumerable<ShiftExchange>> GetByStatusAsync(ShiftExchangeStatus status)
    {
        return await _context.ShiftExchanges
            .Include(e => e.OfferingEmployee)
            .Include(e => e.RequestingEmployee)
            .Include(e => e.ShiftAssignment)
                .ThenInclude(s => s.ShiftType)
            .Where(e => e.Status == status)
            .OrderByDescending(e => e.CreatedAt)
            .ToListAsync();
    }

    public async Task<IEnumerable<ShiftExchange>> GetAvailableExchangesAsync()
    {
        return await _context.ShiftExchanges
            .Include(e => e.OfferingEmployee)
            .Include(e => e.RequestingEmployee)
            .Include(e => e.ShiftAssignment)
                .ThenInclude(s => s.ShiftType)
            .Where(e => e.Status == ShiftExchangeStatus.Angeboten || e.Status == ShiftExchangeStatus.Angefragt)
            .OrderBy(e => e.ShiftAssignment.Date)
            .ToListAsync();
    }
}
