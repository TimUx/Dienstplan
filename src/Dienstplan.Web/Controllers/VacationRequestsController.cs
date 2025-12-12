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
public class VacationRequestsController : ControllerBase
{
    private readonly IVacationRequestRepository _vacationRequestRepository;
    private readonly IEmployeeRepository _employeeRepository;
    private readonly IAbsenceRepository _absenceRepository;
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly IAuditService _auditService;

    public VacationRequestsController(
        IVacationRequestRepository vacationRequestRepository,
        IEmployeeRepository employeeRepository,
        IAbsenceRepository absenceRepository,
        UserManager<ApplicationUser> userManager,
        IAuditService auditService)
    {
        _vacationRequestRepository = vacationRequestRepository;
        _employeeRepository = employeeRepository;
        _absenceRepository = absenceRepository;
        _userManager = userManager;
        _auditService = auditService;
    }

    /// <summary>
    /// Get all vacation requests (Disponent/Admin only)
    /// </summary>
    [HttpGet]
    [Authorize(Roles = "Admin,Disponent")]
    public async Task<ActionResult<IEnumerable<VacationRequestDto>>> GetAllRequests()
    {
        var requests = await _vacationRequestRepository.GetAllAsync();
        var dtos = requests.Select(MapToDto).ToList();
        return Ok(dtos);
    }

    /// <summary>
    /// Get vacation requests for a specific employee
    /// </summary>
    [HttpGet("employee/{employeeId}")]
    public async Task<ActionResult<IEnumerable<VacationRequestDto>>> GetEmployeeRequests(int employeeId)
    {
        // Users can only see their own requests unless they are Admin/Disponent
        if (!User.IsInRole("Admin") && !User.IsInRole("Disponent"))
        {
            // Get the current user's linked employee ID
            var currentUser = await _userManager.GetUserAsync(User);
            if (currentUser?.EmployeeId != employeeId)
            {
                return Forbid();
            }
        }

        var requests = await _vacationRequestRepository.GetByEmployeeIdAsync(employeeId);
        var dtos = requests.Select(MapToDto).ToList();
        return Ok(dtos);
    }

    /// <summary>
    /// Get pending vacation requests (Disponent/Admin only)
    /// </summary>
    [HttpGet("pending")]
    [Authorize(Roles = "Admin,Disponent")]
    public async Task<ActionResult<IEnumerable<VacationRequestDto>>> GetPendingRequests()
    {
        var requests = await _vacationRequestRepository.GetPendingRequestsAsync();
        var dtos = requests.Select(MapToDto).ToList();
        return Ok(dtos);
    }

    /// <summary>
    /// Create a new vacation request
    /// </summary>
    [HttpPost]
    public async Task<ActionResult<VacationRequestDto>> CreateRequest([FromBody] CreateVacationRequestDto dto)
    {
        // Validate dates
        if (dto.StartDate >= dto.EndDate)
        {
            return BadRequest(new { error = "Enddatum muss nach dem Startdatum liegen" });
        }

        // Verify employee exists
        var employee = await _employeeRepository.GetByIdAsync(dto.EmployeeId);
        if (employee == null)
        {
            return NotFound(new { error = "Mitarbeiter nicht gefunden" });
        }

        var vacationRequest = new VacationRequest
        {
            EmployeeId = dto.EmployeeId,
            StartDate = dto.StartDate,
            EndDate = dto.EndDate,
            Notes = dto.Notes,
            Status = VacationRequestStatus.InBearbeitung,
            CreatedAt = DateTime.UtcNow
        };

        var created = await _vacationRequestRepository.AddAsync(vacationRequest);
        
        // Log the creation
        await _auditService.LogCreatedAsync(created, User.Identity?.Name ?? "System", User.Identity?.Name ?? "System");
        
        var resultDto = MapToDto(created);
        
        return CreatedAtAction(nameof(GetEmployeeRequests), new { employeeId = dto.EmployeeId }, resultDto);
    }

    /// <summary>
    /// Update vacation request status (Disponent/Admin only)
    /// </summary>
    [HttpPut("{id}/status")]
    [Authorize(Roles = "Admin,Disponent")]
    public async Task<ActionResult<VacationRequestDto>> UpdateStatus(int id, [FromBody] UpdateVacationRequestStatusDto dto)
    {
        var request = await _vacationRequestRepository.GetByIdAsync(id);
        if (request == null)
        {
            return NotFound(new { error = "Urlaubsantrag nicht gefunden" });
        }

        // Store old entity for audit log
        var oldEntity = new VacationRequest
        {
            Id = request.Id,
            EmployeeId = request.EmployeeId,
            StartDate = request.StartDate,
            EndDate = request.EndDate,
            Status = request.Status,
            Notes = request.Notes,
            DisponentResponse = request.DisponentResponse,
            ProcessedBy = request.ProcessedBy,
            CreatedAt = request.CreatedAt,
            UpdatedAt = request.UpdatedAt
        };

        // Parse status
        if (!Enum.TryParse<VacationRequestStatus>(dto.Status, out var status))
        {
            return BadRequest(new { error = "Ungültiger Status" });
        }

        request.Status = status;
        request.DisponentResponse = dto.DisponentResponse;
        request.UpdatedAt = DateTime.UtcNow;
        request.ProcessedBy = User.Identity?.Name;

        await _vacationRequestRepository.UpdateAsync(request);
        
        // Log the update
        await _auditService.LogUpdatedAsync(oldEntity, request, User.Identity?.Name ?? "System", User.Identity?.Name ?? "System");

        // If approved, create an Absence entry
        if (status == VacationRequestStatus.Genehmigt)
        {
            var absence = new Absence
            {
                EmployeeId = request.EmployeeId,
                Type = AbsenceType.Urlaub,
                StartDate = request.StartDate,
                EndDate = request.EndDate,
                Notes = $"Genehmigter Urlaubsantrag #{request.Id}"
            };
            await _absenceRepository.AddAsync(absence);
        }

        var resultDto = MapToDto(request);
        return Ok(resultDto);
    }

    /// <summary>
    /// Delete a vacation request
    /// </summary>
    [HttpDelete("{id}")]
    public async Task<IActionResult> DeleteRequest(int id)
    {
        var request = await _vacationRequestRepository.GetByIdAsync(id);
        if (request == null)
        {
            return NotFound(new { error = "Urlaubsantrag nicht gefunden" });
        }

        // Only allow deletion if request is still pending or if user is Admin/Disponent
        if (request.Status != VacationRequestStatus.InBearbeitung && 
            !User.IsInRole("Admin") && !User.IsInRole("Disponent"))
        {
            return Forbid();
        }

        // Log the deletion before deleting
        await _auditService.LogDeletedAsync(request, User.Identity?.Name ?? "System", User.Identity?.Name ?? "System");

        await _vacationRequestRepository.DeleteAsync(id);
        return NoContent();
    }

    private static VacationRequestDto MapToDto(VacationRequest request)
    {
        return new VacationRequestDto
        {
            Id = request.Id,
            EmployeeId = request.EmployeeId,
            EmployeeName = request.Employee?.FullName ?? "",
            StartDate = request.StartDate,
            EndDate = request.EndDate,
            Status = request.Status.ToString(),
            Notes = request.Notes,
            DisponentResponse = request.DisponentResponse,
            CreatedAt = request.CreatedAt,
            UpdatedAt = request.UpdatedAt,
            ProcessedBy = request.ProcessedBy
        };
    }
}
