using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Dienstplan.Application.DTOs;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;

namespace Dienstplan.Web.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class VacationRequestsController : ControllerBase
{
    private readonly IVacationRequestRepository _vacationRequestRepository;
    private readonly IEmployeeRepository _employeeRepository;
    private readonly IAbsenceRepository _absenceRepository;

    public VacationRequestsController(
        IVacationRequestRepository vacationRequestRepository,
        IEmployeeRepository employeeRepository,
        IAbsenceRepository absenceRepository)
    {
        _vacationRequestRepository = vacationRequestRepository;
        _employeeRepository = employeeRepository;
        _absenceRepository = absenceRepository;
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
            // TODO: Check if current user is linked to this employeeId
            // For now, allow if authenticated
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
