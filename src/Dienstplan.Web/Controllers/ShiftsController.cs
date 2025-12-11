using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Dienstplan.Application.DTOs;
using Dienstplan.Application.Services;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;

namespace Dienstplan.Web.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class ShiftsController : ControllerBase
{
    private readonly IShiftAssignmentRepository _shiftRepository;
    private readonly IAbsenceRepository _absenceRepository;
    private readonly IShiftPlanningService _planningService;
    private readonly IPdfExportService _pdfExportService;

    public ShiftsController(
        IShiftAssignmentRepository shiftRepository,
        IAbsenceRepository absenceRepository,
        IShiftPlanningService planningService,
        IPdfExportService pdfExportService)
    {
        _shiftRepository = shiftRepository;
        _absenceRepository = absenceRepository;
        _planningService = planningService;
        _pdfExportService = pdfExportService;
    }

    [HttpGet("schedule")]
    [AllowAnonymous] // Allow all to view schedules
    public async Task<ActionResult<ScheduleViewDto>> GetSchedule(
        [FromQuery] DateTime? startDate,
        [FromQuery] DateTime? endDate,
        [FromQuery] string view = "week")
    {
        var start = startDate ?? DateTime.Today;
        var end = endDate ?? view switch
        {
            "week" => start.AddDays(7),
            "month" => start.AddMonths(1),
            "year" => start.AddYears(1),
            _ => start.AddDays(7)
        };

        var assignments = await _shiftRepository.GetByDateRangeAsync(start, end);
        var absences = await _absenceRepository.GetByDateRangeAsync(start, end);

        return Ok(new ScheduleViewDto
        {
            StartDate = start,
            EndDate = end,
            Assignments = assignments.Select(a => new ShiftAssignmentDto
            {
                Id = a.Id,
                EmployeeId = a.EmployeeId,
                EmployeeName = a.Employee.FullName,
                ShiftTypeId = a.ShiftTypeId,
                ShiftCode = a.ShiftType.Code,
                ShiftName = a.ShiftType.Name,
                Date = a.Date,
                IsManual = a.IsManual,
                IsSpringerAssignment = a.IsSpringerAssignment,
                Notes = a.Notes
            }).ToList(),
            Absences = absences.Select(a => new AbsenceDto
            {
                Id = a.Id,
                EmployeeId = a.EmployeeId,
                EmployeeName = a.Employee.FullName,
                Type = a.Type.ToString(),
                StartDate = a.StartDate,
                EndDate = a.EndDate,
                Notes = a.Notes
            }).ToList()
        });
    }

    [HttpPost("plan")]
    [Authorize(Roles = "Admin,Disponent")]
    public async Task<ActionResult<List<ShiftAssignmentDto>>> PlanShifts(
        [FromQuery] DateTime startDate,
        [FromQuery] DateTime endDate,
        [FromQuery] bool force = false)
    {
        var assignments = await _planningService.PlanShifts(startDate, endDate, force);
        
        var dtos = assignments.Select(a => new ShiftAssignmentDto
        {
            Id = a.Id,
            EmployeeId = a.EmployeeId,
            EmployeeName = a.Employee?.FullName ?? "",
            ShiftTypeId = a.ShiftTypeId,
            ShiftCode = a.ShiftType?.Code ?? "",
            ShiftName = a.ShiftType?.Name ?? "",
            Date = a.Date,
            IsManual = a.IsManual,
            IsSpringerAssignment = a.IsSpringerAssignment
        }).ToList();
        
        return Ok(dtos);
    }

    [HttpPost("assignments")]
    public async Task<ActionResult<ShiftAssignmentDto>> CreateAssignment(ShiftAssignmentDto dto)
    {
        var assignment = new ShiftAssignment
        {
            EmployeeId = dto.EmployeeId,
            ShiftTypeId = dto.ShiftTypeId,
            Date = dto.Date,
            IsManual = true,
            Notes = dto.Notes
        };

        var (isValid, errorMessage) = await _planningService.ValidateShiftAssignment(assignment);
        if (!isValid)
        {
            return BadRequest(new { error = errorMessage });
        }

        var created = await _shiftRepository.AddAsync(assignment);
        dto.Id = created.Id;
        return CreatedAtAction(nameof(GetSchedule), dto);
    }

    [HttpDelete("assignments/{id}")]
    public async Task<IActionResult> DeleteAssignment(int id)
    {
        await _shiftRepository.DeleteAsync(id);
        return NoContent();
    }

    [HttpPost("springer/{employeeId}")]
    public async Task<ActionResult<ShiftAssignmentDto>> AssignSpringer(int employeeId, [FromQuery] DateTime date)
    {
        var assignment = await _planningService.AssignSpringer(employeeId, date);
        if (assignment == null)
        {
            return NotFound(new { error = "Kein verfügbarer Springer gefunden" });
        }

        return Ok(new ShiftAssignmentDto
        {
            Id = assignment.Id,
            EmployeeId = assignment.EmployeeId,
            ShiftTypeId = assignment.ShiftTypeId,
            Date = assignment.Date,
            IsSpringerAssignment = true
        });
    }

    [HttpGet("export/pdf")]
    [AllowAnonymous] // Allow all to export PDF
    public async Task<IActionResult> ExportScheduleToPdf(
        [FromQuery] DateTime? startDate,
        [FromQuery] DateTime? endDate)
    {
        var start = startDate ?? DateTime.Today;
        var end = endDate ?? start.AddDays(30);

        try
        {
            var pdfBytes = await _pdfExportService.ExportScheduleToPdfAsync(start, end);
            
            var fileName = $"Dienstplan_{start:yyyy-MM-dd}_bis_{end:yyyy-MM-dd}.pdf";
            return File(pdfBytes, "application/pdf", fileName);
        }
        catch (Exception ex)
        {
            return BadRequest(new { error = $"Fehler beim Erstellen des PDFs: {ex.Message}" });
        }
    }
}
