using Microsoft.AspNetCore.Mvc;
using Dienstplan.Application.DTOs;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;

namespace Dienstplan.Web.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AbsencesController : ControllerBase
{
    private readonly IAbsenceRepository _repository;

    public AbsencesController(IAbsenceRepository repository)
    {
        _repository = repository;
    }

    [HttpGet]
    public async Task<ActionResult<IEnumerable<AbsenceDto>>> GetAll()
    {
        var absences = await _repository.GetAllAsync();
        var dtos = absences.Select(a => new AbsenceDto
        {
            Id = a.Id,
            EmployeeId = a.EmployeeId,
            EmployeeName = a.Employee.FullName,
            Type = a.Type.ToString(),
            StartDate = a.StartDate,
            EndDate = a.EndDate,
            Notes = a.Notes
        });
        return Ok(dtos);
    }

    [HttpGet("employee/{employeeId}")]
    public async Task<ActionResult<IEnumerable<AbsenceDto>>> GetByEmployee(int employeeId)
    {
        var absences = await _repository.GetByEmployeeIdAsync(employeeId);
        var dtos = absences.Select(a => new AbsenceDto
        {
            Id = a.Id,
            EmployeeId = a.EmployeeId,
            EmployeeName = a.Employee.FullName,
            Type = a.Type.ToString(),
            StartDate = a.StartDate,
            EndDate = a.EndDate,
            Notes = a.Notes
        });
        return Ok(dtos);
    }

    [HttpPost]
    public async Task<ActionResult<AbsenceDto>> Create(AbsenceDto dto)
    {
        var absence = new Absence
        {
            EmployeeId = dto.EmployeeId,
            Type = Enum.Parse<AbsenceType>(dto.Type),
            StartDate = dto.StartDate,
            EndDate = dto.EndDate,
            Notes = dto.Notes
        };

        var created = await _repository.AddAsync(absence);
        dto.Id = created.Id;
        return CreatedAtAction(nameof(GetAll), new { id = created.Id }, dto);
    }

    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(int id)
    {
        await _repository.DeleteAsync(id);
        return NoContent();
    }
}
