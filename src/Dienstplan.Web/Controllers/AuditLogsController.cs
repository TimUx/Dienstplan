using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;

namespace Dienstplan.Web.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AuditLogsController : ControllerBase
{
    private readonly IAuditLogRepository _auditLogRepository;

    public AuditLogsController(IAuditLogRepository auditLogRepository)
    {
        _auditLogRepository = auditLogRepository;
    }

    [HttpGet]
    [Authorize(Roles = "Admin")]
    public async Task<ActionResult<IEnumerable<AuditLog>>> GetAll()
    {
        var auditLogs = await _auditLogRepository.GetAllAsync();
        return Ok(auditLogs);
    }

    [HttpGet("recent/{count}")]
    [Authorize(Roles = "Admin")]
    public async Task<ActionResult<IEnumerable<AuditLog>>> GetRecent(int count = 100)
    {
        var auditLogs = await _auditLogRepository.GetRecentAsync(count);
        return Ok(auditLogs);
    }

    [HttpGet("entity/{entityName}/{entityId}")]
    [Authorize(Roles = "Admin,Disponent")]
    public async Task<ActionResult<IEnumerable<AuditLog>>> GetByEntity(string entityName, string entityId)
    {
        var auditLogs = await _auditLogRepository.GetByEntityAsync(entityName, entityId);
        return Ok(auditLogs);
    }

    [HttpGet("user/{userId}")]
    [Authorize(Roles = "Admin")]
    public async Task<ActionResult<IEnumerable<AuditLog>>> GetByUser(string userId)
    {
        var auditLogs = await _auditLogRepository.GetByUserAsync(userId);
        return Ok(auditLogs);
    }
}
