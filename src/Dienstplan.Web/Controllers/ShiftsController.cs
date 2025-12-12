using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Dienstplan.Application.DTOs;
using Dienstplan.Application.Services;
using Dienstplan.Application.Helpers;
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
    private readonly IExcelExportService _excelExportService;
    private readonly IAuditService _auditService;

    public ShiftsController(
        IShiftAssignmentRepository shiftRepository,
        IAbsenceRepository absenceRepository,
        IShiftPlanningService planningService,
        IPdfExportService pdfExportService,
        IExcelExportService excelExportService,
        IAuditService auditService)
    {
        _shiftRepository = shiftRepository;
        _absenceRepository = absenceRepository;
        _planningService = planningService;
        _pdfExportService = pdfExportService;
        _excelExportService = excelExportService;
        _auditService = auditService;
    }

    [HttpGet("schedule")]
    [AllowAnonymous] // Allow all to view schedules
    public async Task<ActionResult<ScheduleViewDto>> GetSchedule(
        [FromQuery] DateTime? startDate,
        [FromQuery] DateTime? endDate,
        [FromQuery] string view = "week")
    {
        var start = startDate ?? DateTime.Today;
        DateTime end;
        
        // Align dates to complete weeks (Monday to Sunday)
        if (view == "week")
        {
            // For week view, always show Monday to Sunday
            (start, end) = DateHelper.GetWeekViewDateRange(start);
        }
        else if (view == "month")
        {
            // For month view, show complete weeks from Monday before 1st to Sunday after last day
            var year = start.Year;
            var month = start.Month;
            (start, end) = DateHelper.GetMonthViewDateRange(year, month);
        }
        else if (view == "year")
        {
            // For year view, align to complete weeks for the entire year
            var yearStart = new DateTime(start.Year, 1, 1);
            var yearEnd = new DateTime(start.Year, 12, 31);
            (start, end) = DateHelper.AlignToCompleteWeeks(yearStart, yearEnd);
        }
        else
        {
            // Default: use provided end date or calculate it
            end = endDate ?? start.AddDays(7);
            (start, end) = DateHelper.AlignToCompleteWeeks(start, end);
        }

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
                TeamId = a.Employee.TeamId,
                TeamName = a.Employee.Team?.Name,
                ShiftTypeId = a.ShiftTypeId,
                ShiftCode = a.ShiftType.Code,
                ShiftName = a.ShiftType.Name,
                Date = a.Date,
                IsManual = a.IsManual,
                IsSpringerAssignment = a.IsSpringerAssignment,
                IsFixed = a.IsFixed,
                Notes = a.Notes,
                CreatedBy = a.CreatedBy,
                ModifiedBy = a.ModifiedBy
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
        
        // Delete existing non-fixed assignments if force is true
        if (force)
        {
            var existingAssignments = await _shiftRepository.GetByDateRangeAsync(startDate, endDate);
            var toDelete = existingAssignments.Where(a => !a.IsFixed).ToList();
            foreach (var assignment in toDelete)
            {
                // Log deletions during force replanning
                await _auditService.LogDeletedAsync(assignment, User.Identity?.Name ?? "System", User.Identity?.Name ?? "System");
                await _shiftRepository.DeleteAsync(assignment.Id);
            }
        }
        
        // Save new assignments that don't have an ID (new ones)
        var savedAssignments = new List<ShiftAssignment>();
        foreach (var assignment in assignments)
        {
            if (assignment.Id == 0)
            {
                assignment.CreatedBy = User.Identity?.Name;
                assignment.CreatedAt = DateTime.UtcNow;
                var saved = await _shiftRepository.AddAsync(assignment);
                
                // Log creation of planned shifts
                await _auditService.LogCreatedAsync(saved, User.Identity?.Name ?? "System", User.Identity?.Name ?? "System");
                
                savedAssignments.Add(saved);
            }
            else
            {
                savedAssignments.Add(assignment);
            }
        }
        
        var dtos = savedAssignments.Select(a => new ShiftAssignmentDto
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
    [Authorize(Roles = "Admin,Disponent")]
    public async Task<ActionResult<ShiftAssignmentDto>> CreateAssignment(ShiftAssignmentDto dto)
    {
        var assignment = new ShiftAssignment
        {
            EmployeeId = dto.EmployeeId,
            ShiftTypeId = dto.ShiftTypeId,
            Date = dto.Date,
            IsManual = true,
            IsFixed = dto.IsFixed,
            Notes = dto.Notes,
            CreatedBy = User.Identity?.Name,
            CreatedAt = DateTime.UtcNow
        };

        var (isValid, errorMessage) = await _planningService.ValidateShiftAssignment(assignment);
        if (!isValid)
        {
            return BadRequest(new { error = errorMessage, warning = true });
        }

        var created = await _shiftRepository.AddAsync(assignment);
        
        // Log the creation
        await _auditService.LogCreatedAsync(created, User.Identity?.Name ?? "System", User.Identity?.Name ?? "System");
        
        dto.Id = created.Id;
        return CreatedAtAction(nameof(GetSchedule), dto);
    }

    [HttpPut("assignments/{id}")]
    [Authorize(Roles = "Admin,Disponent")]
    public async Task<ActionResult<ShiftAssignmentDto>> UpdateAssignment(int id, ShiftAssignmentDto dto, [FromQuery] bool forceOverride = false)
    {
        var existing = await _shiftRepository.GetByIdAsync(id);
        if (existing == null)
        {
            return NotFound(new { error = "Schichtzuweisung nicht gefunden" });
        }

        // Store old entity for audit log
        var oldEntity = new ShiftAssignment
        {
            Id = existing.Id,
            EmployeeId = existing.EmployeeId,
            ShiftTypeId = existing.ShiftTypeId,
            Date = existing.Date,
            IsFixed = existing.IsFixed,
            Notes = existing.Notes,
            IsManual = existing.IsManual,
            IsSpringerAssignment = existing.IsSpringerAssignment
        };

        // Update fields
        existing.EmployeeId = dto.EmployeeId;
        existing.ShiftTypeId = dto.ShiftTypeId;
        existing.Date = dto.Date;
        existing.IsFixed = dto.IsFixed;
        existing.Notes = dto.Notes;
        existing.ModifiedBy = User.Identity?.Name;
        existing.ModifiedAt = DateTime.UtcNow;

        // Validate the change
        var (isValid, errorMessage) = await _planningService.ValidateShiftAssignment(existing);
        if (!isValid && !forceOverride)
        {
            return BadRequest(new { error = errorMessage, warning = true });
        }

        await _shiftRepository.UpdateAsync(existing);
        
        // Log the update
        await _auditService.LogUpdatedAsync(oldEntity, existing, User.Identity?.Name ?? "System", User.Identity?.Name ?? "System");
        
        return Ok(new ShiftAssignmentDto
        {
            Id = existing.Id,
            EmployeeId = existing.EmployeeId,
            EmployeeName = existing.Employee?.FullName ?? "",
            ShiftTypeId = existing.ShiftTypeId,
            ShiftCode = existing.ShiftType?.Code ?? "",
            ShiftName = existing.ShiftType?.Name ?? "",
            Date = existing.Date,
            IsManual = existing.IsManual,
            IsFixed = existing.IsFixed,
            Notes = existing.Notes,
            Warning = isValid ? null : errorMessage
        });
    }

    [HttpDelete("assignments/{id}")]
    [Authorize(Roles = "Admin,Disponent")]
    public async Task<IActionResult> DeleteAssignment(int id)
    {
        var assignment = await _shiftRepository.GetByIdAsync(id);
        if (assignment != null)
        {
            // Log the deletion before deleting
            await _auditService.LogDeletedAsync(assignment, User.Identity?.Name ?? "System", User.Identity?.Name ?? "System");
        }
        
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
    // Require authentication for PDF export to protect sensitive data
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
    
    [HttpGet("export/excel")]
    [AllowAnonymous] // Allow all to export to Excel
    public async Task<IActionResult> ExportScheduleToExcel(
        [FromQuery] DateTime? startDate,
        [FromQuery] DateTime? endDate)
    {
        var start = startDate ?? DateTime.Today;
        var end = endDate ?? start.AddDays(30);

        try
        {
            var excelBytes = await _excelExportService.ExportScheduleToExcelAsync(start, end);
            
            var fileName = $"Dienstplan_{start:yyyy-MM-dd}_bis_{end:yyyy-MM-dd}.xlsx";
            return File(excelBytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", fileName);
        }
        catch (Exception ex)
        {
            return BadRequest(new { error = $"Fehler beim Erstellen der Excel-Datei: {ex.Message}" });
        }
    }
}
