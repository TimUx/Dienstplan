using Microsoft.EntityFrameworkCore;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;
using Dienstplan.Infrastructure.Data;

namespace Dienstplan.Infrastructure.Repositories;

public class VacationRequestRepository : IVacationRequestRepository
{
    private readonly DienstplanDbContext _context;

    public VacationRequestRepository(DienstplanDbContext context)
    {
        _context = context;
    }

    public async Task<VacationRequest?> GetByIdAsync(int id)
    {
        return await _context.VacationRequests
            .Include(v => v.Employee)
            .FirstOrDefaultAsync(v => v.Id == id);
    }

    public async Task<IEnumerable<VacationRequest>> GetAllAsync()
    {
        return await _context.VacationRequests
            .Include(v => v.Employee)
            .OrderByDescending(v => v.CreatedAt)
            .ToListAsync();
    }

    public async Task<VacationRequest> AddAsync(VacationRequest entity)
    {
        _context.VacationRequests.Add(entity);
        await _context.SaveChangesAsync();
        return entity;
    }

    public async Task<VacationRequest> UpdateAsync(VacationRequest entity)
    {
        entity.UpdatedAt = DateTime.UtcNow;
        _context.Entry(entity).State = EntityState.Modified;
        await _context.SaveChangesAsync();
        return entity;
    }

    public async Task DeleteAsync(int id)
    {
        var vacationRequest = await _context.VacationRequests.FindAsync(id);
        if (vacationRequest != null)
        {
            _context.VacationRequests.Remove(vacationRequest);
            await _context.SaveChangesAsync();
        }
    }

    public async Task<IEnumerable<VacationRequest>> GetByEmployeeIdAsync(int employeeId)
    {
        return await _context.VacationRequests
            .Include(v => v.Employee)
            .Where(v => v.EmployeeId == employeeId)
            .OrderByDescending(v => v.CreatedAt)
            .ToListAsync();
    }

    public async Task<IEnumerable<VacationRequest>> GetByStatusAsync(VacationRequestStatus status)
    {
        return await _context.VacationRequests
            .Include(v => v.Employee)
            .Where(v => v.Status == status)
            .OrderByDescending(v => v.CreatedAt)
            .ToListAsync();
    }

    public async Task<IEnumerable<VacationRequest>> GetPendingRequestsAsync()
    {
        return await _context.VacationRequests
            .Include(v => v.Employee)
            .Where(v => v.Status == VacationRequestStatus.InBearbeitung)
            .OrderBy(v => v.CreatedAt)
            .ToListAsync();
    }
}
