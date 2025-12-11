using Microsoft.EntityFrameworkCore;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;
using Dienstplan.Infrastructure.Data;

namespace Dienstplan.Infrastructure.Repositories;

public class EmailSettingsRepository : IEmailSettingsRepository
{
    private readonly DienstplanDbContext _context;

    public EmailSettingsRepository(DienstplanDbContext context)
    {
        _context = context;
    }

    public async Task<EmailSettings?> GetByIdAsync(int id)
    {
        return await _context.EmailSettings.FindAsync(id);
    }

    public async Task<IEnumerable<EmailSettings>> GetAllAsync()
    {
        return await _context.EmailSettings
            .OrderByDescending(e => e.IsActive)
            .ThenByDescending(e => e.CreatedAt)
            .ToListAsync();
    }

    public async Task<EmailSettings> AddAsync(EmailSettings entity)
    {
        // Deactivate all other settings when adding a new active one
        if (entity.IsActive)
        {
            var activeSettings = await _context.EmailSettings
                .Where(e => e.IsActive)
                .ToListAsync();
            
            foreach (var settings in activeSettings)
            {
                settings.IsActive = false;
                settings.UpdatedAt = DateTime.UtcNow;
            }
        }

        _context.EmailSettings.Add(entity);
        await _context.SaveChangesAsync();
        return entity;
    }

    public async Task<EmailSettings> UpdateAsync(EmailSettings entity)
    {
        entity.UpdatedAt = DateTime.UtcNow;
        
        // Deactivate all other settings if this one is being activated
        if (entity.IsActive)
        {
            var otherActiveSettings = await _context.EmailSettings
                .Where(e => e.IsActive && e.Id != entity.Id)
                .ToListAsync();
            
            foreach (var settings in otherActiveSettings)
            {
                settings.IsActive = false;
                settings.UpdatedAt = DateTime.UtcNow;
            }
        }

        _context.Entry(entity).State = EntityState.Modified;
        await _context.SaveChangesAsync();
        return entity;
    }

    public async Task DeleteAsync(int id)
    {
        var settings = await _context.EmailSettings.FindAsync(id);
        if (settings != null)
        {
            _context.EmailSettings.Remove(settings);
            await _context.SaveChangesAsync();
        }
    }

    public async Task<EmailSettings?> GetActiveSettingsAsync()
    {
        return await _context.EmailSettings
            .FirstOrDefaultAsync(e => e.IsActive);
    }
}
