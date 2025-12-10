using Microsoft.AspNetCore.Mvc;
using Dienstplan.Application.DTOs;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;

namespace Dienstplan.Web.Controllers;

[ApiController]
[Route("api/[controller]")]
public class EmployeesController : ControllerBase
{
    private readonly IEmployeeRepository _repository;

    public EmployeesController(IEmployeeRepository repository)
    {
        _repository = repository;
    }

    [HttpGet]
    public async Task<ActionResult<IEnumerable<EmployeeDto>>> GetAll()
    {
        var employees = await _repository.GetAllAsync();
        var dtos = employees.Select(e => new EmployeeDto
        {
            Id = e.Id,
            Vorname = e.Vorname,
            Name = e.Name,
            Personalnummer = e.Personalnummer,
            IsSpringer = e.IsSpringer,
            TeamId = e.TeamId,
            TeamName = e.Team?.Name
        });
        return Ok(dtos);
    }

    [HttpGet("{id}")]
    public async Task<ActionResult<EmployeeDto>> GetById(int id)
    {
        var employee = await _repository.GetByIdAsync(id);
        if (employee == null)
            return NotFound();

        return Ok(new EmployeeDto
        {
            Id = employee.Id,
            Vorname = employee.Vorname,
            Name = employee.Name,
            Personalnummer = employee.Personalnummer,
            IsSpringer = employee.IsSpringer,
            TeamId = employee.TeamId,
            TeamName = employee.Team?.Name
        });
    }

    [HttpGet("springers")]
    public async Task<ActionResult<IEnumerable<EmployeeDto>>> GetSpringers()
    {
        var springers = await _repository.GetSpringersAsync();
        var dtos = springers.Select(e => new EmployeeDto
        {
            Id = e.Id,
            Vorname = e.Vorname,
            Name = e.Name,
            Personalnummer = e.Personalnummer,
            IsSpringer = e.IsSpringer,
            TeamId = e.TeamId,
            TeamName = e.Team?.Name
        });
        return Ok(dtos);
    }

    [HttpPost]
    public async Task<ActionResult<EmployeeDto>> Create(EmployeeDto dto)
    {
        var employee = new Employee
        {
            Vorname = dto.Vorname,
            Name = dto.Name,
            Personalnummer = dto.Personalnummer,
            IsSpringer = dto.IsSpringer,
            TeamId = dto.TeamId
        };

        var created = await _repository.AddAsync(employee);
        dto.Id = created.Id;
        return CreatedAtAction(nameof(GetById), new { id = created.Id }, dto);
    }

    [HttpPut("{id}")]
    public async Task<ActionResult<EmployeeDto>> Update(int id, EmployeeDto dto)
    {
        var employee = await _repository.GetByIdAsync(id);
        if (employee == null)
            return NotFound();

        employee.Vorname = dto.Vorname;
        employee.Name = dto.Name;
        employee.Personalnummer = dto.Personalnummer;
        employee.IsSpringer = dto.IsSpringer;
        employee.TeamId = dto.TeamId;

        await _repository.UpdateAsync(employee);
        return Ok(dto);
    }

    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(int id)
    {
        var employee = await _repository.GetByIdAsync(id);
        if (employee == null)
            return NotFound();

        await _repository.DeleteAsync(id);
        return NoContent();
    }
}
