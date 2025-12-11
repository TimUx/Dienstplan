using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;
using Dienstplan.Application.DTOs;

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
    public async Task<ActionResult<PaginatedResult<AuditLogDto>>> GetAll(
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 50,
        [FromQuery] string? entityName = null,
        [FromQuery] string? action = null,
        [FromQuery] DateTime? startDate = null,
        [FromQuery] DateTime? endDate = null,
        [FromQuery] string? userId = null)
    {
        // Validate pagination parameters
        if (page < 1) page = 1;
        if (pageSize < 1) pageSize = 50;
        if (pageSize > 100) pageSize = 100;

        var (items, totalCount) = await _auditLogRepository.SearchAsync(
            page, 
            pageSize, 
            entityName, 
            action, 
            startDate, 
            endDate, 
            userId);

        var result = new PaginatedResult<AuditLogDto>
        {
            Items = items.Select(a => new AuditLogDto
            {
                Id = a.Id,
                EntityName = a.EntityName,
                EntityId = a.EntityId,
                Action = a.Action.ToString(),
                Changes = a.Changes,
                UserId = a.UserId,
                UserName = a.UserName,
                Timestamp = a.Timestamp,
                IpAddress = a.IpAddress
            }).ToList(),
            TotalCount = totalCount,
            Page = page,
            PageSize = pageSize
        };

        return Ok(result);
    }

    [HttpGet("recent/{count}")]
    [Authorize(Roles = "Admin")]
    public async Task<ActionResult<IEnumerable<AuditLogDto>>> GetRecent(int count = 100)
    {
        var auditLogs = await _auditLogRepository.GetRecentAsync(count);
        var dtos = auditLogs.Select(a => new AuditLogDto
        {
            Id = a.Id,
            EntityName = a.EntityName,
            EntityId = a.EntityId,
            Action = a.Action.ToString(),
            Changes = a.Changes,
            UserId = a.UserId,
            UserName = a.UserName,
            Timestamp = a.Timestamp,
            IpAddress = a.IpAddress
        });
        return Ok(dtos);
    }

    [HttpGet("entity/{entityName}/{entityId}")]
    [Authorize(Roles = "Admin,Disponent")]
    public async Task<ActionResult<IEnumerable<AuditLogDto>>> GetByEntity(string entityName, string entityId)
    {
        var auditLogs = await _auditLogRepository.GetByEntityAsync(entityName, entityId);
        var dtos = auditLogs.Select(a => new AuditLogDto
        {
            Id = a.Id,
            EntityName = a.EntityName,
            EntityId = a.EntityId,
            Action = a.Action.ToString(),
            Changes = a.Changes,
            UserId = a.UserId,
            UserName = a.UserName,
            Timestamp = a.Timestamp,
            IpAddress = a.IpAddress
        });
        return Ok(dtos);
    }

    [HttpGet("user/{userId}")]
    [Authorize(Roles = "Admin")]
    public async Task<ActionResult<IEnumerable<AuditLogDto>>> GetByUser(string userId)
    {
        var auditLogs = await _auditLogRepository.GetByUserAsync(userId);
        var dtos = auditLogs.Select(a => new AuditLogDto
        {
            Id = a.Id,
            EntityName = a.EntityName,
            EntityId = a.EntityId,
            Action = a.Action.ToString(),
            Changes = a.Changes,
            UserId = a.UserId,
            UserName = a.UserName,
            Timestamp = a.Timestamp,
            IpAddress = a.IpAddress
        });
        return Ok(dtos);
    }
}
