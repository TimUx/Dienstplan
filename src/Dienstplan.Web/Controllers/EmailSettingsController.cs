using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Dienstplan.Application.DTOs;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;

namespace Dienstplan.Web.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize(Roles = "Admin")] // Only admins can manage email settings
public class EmailSettingsController : ControllerBase
{
    private readonly IEmailSettingsRepository _repository;
    private readonly IAuditService _auditService;

    public EmailSettingsController(IEmailSettingsRepository repository, IAuditService auditService)
    {
        _repository = repository;
        _auditService = auditService;
    }

    /// <summary>
    /// Get all email settings
    /// </summary>
    [HttpGet]
    public async Task<ActionResult<IEnumerable<EmailSettingsDto>>> GetAll()
    {
        var settings = await _repository.GetAllAsync();
        var dtos = settings.Select(MapToDto).ToList();
        return Ok(dtos);
    }

    /// <summary>
    /// Get active email settings
    /// </summary>
    [HttpGet("active")]
    public async Task<ActionResult<EmailSettingsDto>> GetActive()
    {
        var settings = await _repository.GetActiveSettingsAsync();
        if (settings == null)
        {
            return NotFound(new { error = "Keine aktiven E-Mail-Einstellungen gefunden" });
        }

        return Ok(MapToDto(settings));
    }

    /// <summary>
    /// Get email settings by ID
    /// </summary>
    [HttpGet("{id}")]
    public async Task<ActionResult<EmailSettingsDto>> GetById(int id)
    {
        var settings = await _repository.GetByIdAsync(id);
        if (settings == null)
        {
            return NotFound();
        }

        return Ok(MapToDto(settings));
    }

    /// <summary>
    /// Create new email settings
    /// </summary>
    [HttpPost]
    public async Task<ActionResult<EmailSettingsDto>> Create([FromBody] CreateEmailSettingsDto dto)
    {
        // Validate required fields
        if (string.IsNullOrWhiteSpace(dto.SmtpServer))
        {
            return BadRequest(new { error = "SMTP Server ist erforderlich" });
        }

        if (string.IsNullOrWhiteSpace(dto.SenderEmail))
        {
            return BadRequest(new { error = "Absenderadresse ist erforderlich" });
        }

        var settings = new EmailSettings
        {
            SmtpServer = dto.SmtpServer,
            SmtpPort = dto.SmtpPort,
            Protocol = dto.Protocol,
            SecurityProtocol = dto.SecurityProtocol,
            RequiresAuthentication = dto.RequiresAuthentication,
            Username = dto.Username,
            Password = dto.Password, // TODO: Encrypt password before storing
            SenderEmail = dto.SenderEmail,
            SenderName = dto.SenderName,
            ReplyToEmail = dto.ReplyToEmail,
            IsActive = true, // New settings are active by default
            CreatedAt = DateTime.UtcNow
        };

        var created = await _repository.AddAsync(settings);
        
        // Log the creation
        await _auditService.LogCreatedAsync(created, User.Identity?.Name ?? "System", User.Identity?.Name ?? "System");
        
        return CreatedAtAction(nameof(GetById), new { id = created.Id }, MapToDto(created));
    }

    /// <summary>
    /// Update email settings
    /// </summary>
    [HttpPut("{id}")]
    public async Task<ActionResult<EmailSettingsDto>> Update(int id, [FromBody] CreateEmailSettingsDto dto)
    {
        var settings = await _repository.GetByIdAsync(id);
        if (settings == null)
        {
            return NotFound();
        }

        // Store old entity for audit log (without password for security)
        var oldEntity = new EmailSettings
        {
            Id = settings.Id,
            SmtpServer = settings.SmtpServer,
            SmtpPort = settings.SmtpPort,
            Protocol = settings.Protocol,
            SecurityProtocol = settings.SecurityProtocol,
            RequiresAuthentication = settings.RequiresAuthentication,
            Username = settings.Username,
            Password = "***", // Don't log password
            SenderEmail = settings.SenderEmail,
            SenderName = settings.SenderName,
            ReplyToEmail = settings.ReplyToEmail,
            IsActive = settings.IsActive
        };

        settings.SmtpServer = dto.SmtpServer;
        settings.SmtpPort = dto.SmtpPort;
        settings.Protocol = dto.Protocol;
        settings.SecurityProtocol = dto.SecurityProtocol;
        settings.RequiresAuthentication = dto.RequiresAuthentication;
        settings.Username = dto.Username;
        
        // Only update password if provided
        if (!string.IsNullOrWhiteSpace(dto.Password))
        {
            settings.Password = dto.Password; // TODO: Encrypt password before storing
        }
        
        settings.SenderEmail = dto.SenderEmail;
        settings.SenderName = dto.SenderName;
        settings.ReplyToEmail = dto.ReplyToEmail;

        await _repository.UpdateAsync(settings);
        
        // Create new entity for audit log (without password)
        var newEntity = new EmailSettings
        {
            Id = settings.Id,
            SmtpServer = settings.SmtpServer,
            SmtpPort = settings.SmtpPort,
            Protocol = settings.Protocol,
            SecurityProtocol = settings.SecurityProtocol,
            RequiresAuthentication = settings.RequiresAuthentication,
            Username = settings.Username,
            Password = "***", // Don't log password
            SenderEmail = settings.SenderEmail,
            SenderName = settings.SenderName,
            ReplyToEmail = settings.ReplyToEmail,
            IsActive = settings.IsActive
        };
        
        // Log the update
        await _auditService.LogUpdatedAsync(oldEntity, newEntity, User.Identity?.Name ?? "System", User.Identity?.Name ?? "System");
        
        return Ok(MapToDto(settings));
    }

    /// <summary>
    /// Activate email settings
    /// </summary>
    [HttpPut("{id}/activate")]
    public async Task<ActionResult<EmailSettingsDto>> Activate(int id)
    {
        var settings = await _repository.GetByIdAsync(id);
        if (settings == null)
        {
            return NotFound();
        }

        // Store old entity for audit log
        var oldEntity = new EmailSettings
        {
            Id = settings.Id,
            SmtpServer = settings.SmtpServer,
            SmtpPort = settings.SmtpPort,
            Protocol = settings.Protocol,
            SecurityProtocol = settings.SecurityProtocol,
            RequiresAuthentication = settings.RequiresAuthentication,
            Username = settings.Username,
            Password = "***",
            SenderEmail = settings.SenderEmail,
            SenderName = settings.SenderName,
            ReplyToEmail = settings.ReplyToEmail,
            IsActive = settings.IsActive
        };

        settings.IsActive = true;
        await _repository.UpdateAsync(settings);
        
        // Create new entity for audit log
        var newEntity = new EmailSettings
        {
            Id = settings.Id,
            SmtpServer = settings.SmtpServer,
            SmtpPort = settings.SmtpPort,
            Protocol = settings.Protocol,
            SecurityProtocol = settings.SecurityProtocol,
            RequiresAuthentication = settings.RequiresAuthentication,
            Username = settings.Username,
            Password = "***",
            SenderEmail = settings.SenderEmail,
            SenderName = settings.SenderName,
            ReplyToEmail = settings.ReplyToEmail,
            IsActive = settings.IsActive
        };
        
        // Log the update
        await _auditService.LogUpdatedAsync(oldEntity, newEntity, User.Identity?.Name ?? "System", User.Identity?.Name ?? "System");
        
        return Ok(MapToDto(settings));
    }

    /// <summary>
    /// Delete email settings
    /// </summary>
    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(int id)
    {
        var settings = await _repository.GetByIdAsync(id);
        if (settings == null)
        {
            return NotFound();
        }

        // Don't allow deleting active settings
        if (settings.IsActive)
        {
            return BadRequest(new { error = "Aktive E-Mail-Einstellungen können nicht gelöscht werden. Deaktivieren Sie sie zuerst." });
        }

        // Create entity for audit log (without password)
        var entityToLog = new EmailSettings
        {
            Id = settings.Id,
            SmtpServer = settings.SmtpServer,
            SmtpPort = settings.SmtpPort,
            Protocol = settings.Protocol,
            SecurityProtocol = settings.SecurityProtocol,
            RequiresAuthentication = settings.RequiresAuthentication,
            Username = settings.Username,
            Password = "***",
            SenderEmail = settings.SenderEmail,
            SenderName = settings.SenderName,
            ReplyToEmail = settings.ReplyToEmail,
            IsActive = settings.IsActive
        };
        
        // Log the deletion
        await _auditService.LogDeletedAsync(entityToLog, User.Identity?.Name ?? "System", User.Identity?.Name ?? "System");

        await _repository.DeleteAsync(id);
        return NoContent();
    }

    /// <summary>
    /// Test email settings by sending a test email
    /// </summary>
    [HttpPost("{id}/test")]
    public async Task<ActionResult> TestSettings(int id, [FromBody] TestEmailDto testDto)
    {
        var settings = await _repository.GetByIdAsync(id);
        if (settings == null)
        {
            return NotFound();
        }

        // TODO: Implement actual email sending test
        // For now, just validate the configuration exists
        return Ok(new { 
            success = true, 
            message = "E-Mail-Test-Funktion noch nicht implementiert. Konfiguration wurde gespeichert." 
        });
    }

    private static EmailSettingsDto MapToDto(EmailSettings settings)
    {
        return new EmailSettingsDto
        {
            Id = settings.Id,
            SmtpServer = settings.SmtpServer,
            SmtpPort = settings.SmtpPort,
            Protocol = settings.Protocol,
            SecurityProtocol = settings.SecurityProtocol,
            RequiresAuthentication = settings.RequiresAuthentication,
            Username = settings.Username,
            Password = "***", // Never return actual password
            SenderEmail = settings.SenderEmail,
            SenderName = settings.SenderName,
            ReplyToEmail = settings.ReplyToEmail,
            IsActive = settings.IsActive
        };
    }
}

public record TestEmailDto(string RecipientEmail);
