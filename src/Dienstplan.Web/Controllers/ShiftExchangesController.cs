using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Dienstplan.Application.DTOs;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;
using Dienstplan.Infrastructure.Identity;

namespace Dienstplan.Web.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class ShiftExchangesController : ControllerBase
{
    private readonly IShiftExchangeRepository _exchangeRepository;
    private readonly IShiftAssignmentRepository _shiftRepository;
    private readonly IEmployeeRepository _employeeRepository;
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly IAuditService _auditService;

    public ShiftExchangesController(
        IShiftExchangeRepository exchangeRepository,
        IShiftAssignmentRepository shiftRepository,
        IEmployeeRepository employeeRepository,
        UserManager<ApplicationUser> userManager,
        IAuditService auditService)
    {
        _exchangeRepository = exchangeRepository;
        _shiftRepository = shiftRepository;
        _employeeRepository = employeeRepository;
        _userManager = userManager;
        _auditService = auditService;
    }

    /// <summary>
    /// Get all available shift exchanges
    /// </summary>
    [HttpGet("available")]
    public async Task<ActionResult<IEnumerable<ShiftExchangeDto>>> GetAvailableExchanges()
    {
        var exchanges = await _exchangeRepository.GetAvailableExchangesAsync();
        var dtos = exchanges.Select(MapToDto).ToList();
        return Ok(dtos);
    }

    /// <summary>
    /// Get exchanges for a specific employee (offering or requesting)
    /// </summary>
    [HttpGet("employee/{employeeId}")]
    public async Task<ActionResult<IEnumerable<ShiftExchangeDto>>> GetEmployeeExchanges(int employeeId)
    {
        var offering = await _exchangeRepository.GetByOfferingEmployeeIdAsync(employeeId);
        var requesting = await _exchangeRepository.GetByRequestingEmployeeIdAsync(employeeId);
        
        var all = offering.Union(requesting).OrderByDescending(e => e.CreatedAt);
        var dtos = all.Select(MapToDto).ToList();
        
        return Ok(dtos);
    }

    /// <summary>
    /// Get pending exchanges (Disponent/Admin only)
    /// </summary>
    [HttpGet("pending")]
    [Authorize(Roles = "Admin,Disponent")]
    public async Task<ActionResult<IEnumerable<ShiftExchangeDto>>> GetPendingExchanges()
    {
        var exchanges = await _exchangeRepository.GetByStatusAsync(ShiftExchangeStatus.Angefragt);
        var dtos = exchanges.Select(MapToDto).ToList();
        return Ok(dtos);
    }

    /// <summary>
    /// Offer a shift for exchange
    /// </summary>
    [HttpPost]
    public async Task<ActionResult<ShiftExchangeDto>> OfferShift([FromBody] CreateShiftExchangeDto dto)
    {
        // Verify shift assignment exists
        var shift = await _shiftRepository.GetByIdAsync(dto.ShiftAssignmentId);
        if (shift == null)
        {
            return NotFound(new { error = "Schicht nicht gefunden" });
        }

        // Check if shift is in the future
        if (shift.Date < DateTime.Today)
        {
            return BadRequest(new { error = "Vergangene Schichten können nicht getauscht werden" });
        }

        // Check if shift is already offered for exchange
        var existing = await _exchangeRepository.GetAllAsync();
        if (existing.Any(e => e.ShiftAssignmentId == dto.ShiftAssignmentId && 
                             (e.Status == ShiftExchangeStatus.Angeboten || e.Status == ShiftExchangeStatus.Angefragt)))
        {
            return BadRequest(new { error = "Diese Schicht wird bereits zum Tausch angeboten" });
        }

        var exchange = new ShiftExchange
        {
            OfferingEmployeeId = shift.EmployeeId,
            ShiftAssignmentId = dto.ShiftAssignmentId,
            OfferingReason = dto.OfferingReason,
            Status = ShiftExchangeStatus.Angeboten,
            CreatedAt = DateTime.UtcNow
        };

        var created = await _exchangeRepository.AddAsync(exchange);
        
        // Log the creation
        await _auditService.LogCreatedAsync(created, User.Identity?.Name ?? "System", User.Identity?.Name ?? "System");
        
        var resultDto = MapToDto(created);
        
        return CreatedAtAction(nameof(GetEmployeeExchanges), new { employeeId = shift.EmployeeId }, resultDto);
    }

    /// <summary>
    /// Request to take an offered shift
    /// </summary>
    [HttpPost("{id}/request")]
    public async Task<ActionResult<ShiftExchangeDto>> RequestExchange(int id, [FromBody] RequestShiftExchangeDto dto)
    {
        var exchange = await _exchangeRepository.GetByIdAsync(id);
        if (exchange == null)
        {
            return NotFound(new { error = "Tauschangebot nicht gefunden" });
        }

        if (exchange.Status != ShiftExchangeStatus.Angeboten)
        {
            return BadRequest(new { error = "Diese Schicht ist nicht mehr verfügbar" });
        }

        // Verify requesting employee exists
        var employee = await _employeeRepository.GetByIdAsync(dto.RequestingEmployeeId);
        if (employee == null)
        {
            return NotFound(new { error = "Mitarbeiter nicht gefunden" });
        }

        // Prevent employee from requesting their own shift
        if (exchange.OfferingEmployeeId == dto.RequestingEmployeeId)
        {
            return BadRequest(new { error = "Sie können Ihre eigene Schicht nicht anfordern" });
        }

        // Store old entity for audit log
        var oldEntity = new ShiftExchange
        {
            Id = exchange.Id,
            OfferingEmployeeId = exchange.OfferingEmployeeId,
            ShiftAssignmentId = exchange.ShiftAssignmentId,
            RequestingEmployeeId = exchange.RequestingEmployeeId,
            Status = exchange.Status,
            OfferingReason = exchange.OfferingReason,
            DisponentNotes = exchange.DisponentNotes,
            CreatedAt = exchange.CreatedAt,
            UpdatedAt = exchange.UpdatedAt,
            ProcessedBy = exchange.ProcessedBy
        };

        exchange.RequestingEmployeeId = dto.RequestingEmployeeId;
        exchange.Status = ShiftExchangeStatus.Angefragt;
        exchange.UpdatedAt = DateTime.UtcNow;

        await _exchangeRepository.UpdateAsync(exchange);
        
        // Log the update
        await _auditService.LogUpdatedAsync(oldEntity, exchange, User.Identity?.Name ?? "System", User.Identity?.Name ?? "System");
        
        var resultDto = MapToDto(exchange);
        return Ok(resultDto);
    }

    /// <summary>
    /// Process shift exchange (approve/reject) - Disponent/Admin only
    /// </summary>
    [HttpPut("{id}/process")]
    [Authorize(Roles = "Admin,Disponent")]
    public async Task<ActionResult<ShiftExchangeDto>> ProcessExchange(int id, [FromBody] ProcessShiftExchangeDto dto)
    {
        var exchange = await _exchangeRepository.GetByIdAsync(id);
        if (exchange == null)
        {
            return NotFound(new { error = "Tauschangebot nicht gefunden" });
        }

        if (exchange.Status != ShiftExchangeStatus.Angefragt)
        {
            return BadRequest(new { error = "Dieser Tausch kann nicht mehr bearbeitet werden" });
        }

        // Parse status
        if (!Enum.TryParse<ShiftExchangeStatus>(dto.Status, out var status))
        {
            return BadRequest(new { error = "Ungültiger Status" });
        }

        if (status != ShiftExchangeStatus.Genehmigt && status != ShiftExchangeStatus.Abgelehnt)
        {
            return BadRequest(new { error = "Status muss Genehmigt oder Abgelehnt sein" });
        }

        // Store old entity for audit log
        var oldEntity = new ShiftExchange
        {
            Id = exchange.Id,
            OfferingEmployeeId = exchange.OfferingEmployeeId,
            ShiftAssignmentId = exchange.ShiftAssignmentId,
            RequestingEmployeeId = exchange.RequestingEmployeeId,
            Status = exchange.Status,
            OfferingReason = exchange.OfferingReason,
            DisponentNotes = exchange.DisponentNotes,
            CreatedAt = exchange.CreatedAt,
            UpdatedAt = exchange.UpdatedAt,
            ProcessedBy = exchange.ProcessedBy
        };

        exchange.Status = status;
        exchange.DisponentNotes = dto.DisponentNotes;
        exchange.UpdatedAt = DateTime.UtcNow;
        exchange.ProcessedBy = User.Identity?.Name;

        await _exchangeRepository.UpdateAsync(exchange);
        
        // Log the update
        await _auditService.LogUpdatedAsync(oldEntity, exchange, User.Identity?.Name ?? "System", User.Identity?.Name ?? "System");

        // If approved, swap the shift assignment
        if (status == ShiftExchangeStatus.Genehmigt && exchange.RequestingEmployeeId.HasValue)
        {
            var shift = await _shiftRepository.GetByIdAsync(exchange.ShiftAssignmentId);
            if (shift != null)
            {
                shift.EmployeeId = exchange.RequestingEmployeeId.Value;
                shift.ModifiedAt = DateTime.UtcNow;
                shift.ModifiedBy = User.Identity?.Name;
                await _shiftRepository.UpdateAsync(shift);
            }

            exchange.Status = ShiftExchangeStatus.Abgeschlossen;
            await _exchangeRepository.UpdateAsync(exchange);
        }

        var resultDto = MapToDto(exchange);
        return Ok(resultDto);
    }

    /// <summary>
    /// Cancel an offered shift exchange
    /// </summary>
    [HttpPut("{id}/cancel")]
    public async Task<ActionResult<ShiftExchangeDto>> CancelExchange(int id)
    {
        var exchange = await _exchangeRepository.GetByIdAsync(id);
        if (exchange == null)
        {
            return NotFound(new { error = "Tauschangebot nicht gefunden" });
        }

        // Only offering employee or Admin/Disponent can cancel
        if (!User.IsInRole("Admin") && !User.IsInRole("Disponent"))
        {
            var currentUser = await _userManager.GetUserAsync(User);
            if (currentUser?.EmployeeId != exchange.OfferingEmployeeId)
            {
                return Forbid();
            }
        }

        if (exchange.Status != ShiftExchangeStatus.Angeboten && exchange.Status != ShiftExchangeStatus.Angefragt)
        {
            return BadRequest(new { error = "Dieser Tausch kann nicht mehr zurückgezogen werden" });
        }

        // Store old entity for audit log
        var oldEntity = new ShiftExchange
        {
            Id = exchange.Id,
            OfferingEmployeeId = exchange.OfferingEmployeeId,
            ShiftAssignmentId = exchange.ShiftAssignmentId,
            RequestingEmployeeId = exchange.RequestingEmployeeId,
            Status = exchange.Status,
            OfferingReason = exchange.OfferingReason,
            DisponentNotes = exchange.DisponentNotes,
            CreatedAt = exchange.CreatedAt,
            UpdatedAt = exchange.UpdatedAt,
            ProcessedBy = exchange.ProcessedBy
        };

        exchange.Status = ShiftExchangeStatus.Zurueckgezogen;
        exchange.UpdatedAt = DateTime.UtcNow;

        await _exchangeRepository.UpdateAsync(exchange);
        
        // Log the update
        await _auditService.LogUpdatedAsync(oldEntity, exchange, User.Identity?.Name ?? "System", User.Identity?.Name ?? "System");
        
        var resultDto = MapToDto(exchange);
        return Ok(resultDto);
    }

    private static ShiftExchangeDto MapToDto(ShiftExchange exchange)
    {
        return new ShiftExchangeDto
        {
            Id = exchange.Id,
            OfferingEmployeeId = exchange.OfferingEmployeeId,
            OfferingEmployeeName = exchange.OfferingEmployee?.FullName ?? "",
            ShiftAssignmentId = exchange.ShiftAssignmentId,
            ShiftDate = exchange.ShiftAssignment?.Date ?? DateTime.MinValue,
            ShiftCode = exchange.ShiftAssignment?.ShiftType?.Code ?? "",
            ShiftName = exchange.ShiftAssignment?.ShiftType?.Name ?? "",
            RequestingEmployeeId = exchange.RequestingEmployeeId,
            RequestingEmployeeName = exchange.RequestingEmployee?.FullName ?? "",
            Status = exchange.Status.ToString(),
            OfferingReason = exchange.OfferingReason,
            DisponentNotes = exchange.DisponentNotes,
            CreatedAt = exchange.CreatedAt,
            UpdatedAt = exchange.UpdatedAt,
            ProcessedBy = exchange.ProcessedBy
        };
    }
}
