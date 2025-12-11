using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Dienstplan.Application.DTOs;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;

namespace Dienstplan.Web.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize] // Require authentication for all endpoints
public class EmployeesController : ControllerBase
{
    private readonly IEmployeeRepository _repository;

    public EmployeesController(IEmployeeRepository repository)
    {
        _repository = repository;
    }

    [HttpGet]
    [AllowAnonymous] // Allow read access for all users
    public async Task<ActionResult<IEnumerable<EmployeeDto>>> GetAll()
    {
        var employees = await _repository.GetAllAsync();
        var dtos = employees.Select(e => new EmployeeDto
        {
            Id = e.Id,
            Vorname = e.Vorname,
            Name = e.Name,
            Personalnummer = e.Personalnummer,
            Email = e.Email,
            Geburtsdatum = e.Geburtsdatum,
            Funktion = e.Funktion,
            IsSpringer = e.IsSpringer,
            IsFerienjobber = e.IsFerienjobber,
            TeamId = e.TeamId,
            TeamName = e.Team?.Name
        });
        return Ok(dtos);
    }

    [HttpGet("{id}")]
    [AllowAnonymous]
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
            Email = employee.Email,
            Geburtsdatum = employee.Geburtsdatum,
            Funktion = employee.Funktion,
            IsSpringer = employee.IsSpringer,
            IsFerienjobber = employee.IsFerienjobber,
            TeamId = employee.TeamId,
            TeamName = employee.Team?.Name
        });
    }

    [HttpGet("springers")]
    [AllowAnonymous]
    public async Task<ActionResult<IEnumerable<EmployeeDto>>> GetSpringers()
    {
        var springers = await _repository.GetSpringersAsync();
        var dtos = springers.Select(e => new EmployeeDto
        {
            Id = e.Id,
            Vorname = e.Vorname,
            Name = e.Name,
            Personalnummer = e.Personalnummer,
            Email = e.Email,
            Geburtsdatum = e.Geburtsdatum,
            Funktion = e.Funktion,
            IsSpringer = e.IsSpringer,
            IsFerienjobber = e.IsFerienjobber,
            TeamId = e.TeamId,
            TeamName = e.Team?.Name
        });
        return Ok(dtos);
    }

    [HttpGet("search")]
    [AllowAnonymous]
    public async Task<ActionResult<PaginatedResult<EmployeeDto>>> Search(
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 50,
        [FromQuery] string? searchTerm = null,
        [FromQuery] int? teamId = null,
        [FromQuery] bool? isSpringer = null)
    {
        // Validate pagination parameters
        if (page < 1) page = 1;
        if (pageSize < 1) pageSize = 50;
        if (pageSize > 100) pageSize = 100;

        var (items, totalCount) = await _repository.SearchAsync(page, pageSize, searchTerm, teamId, isSpringer);

        var result = new PaginatedResult<EmployeeDto>
        {
            Items = items.Select(e => new EmployeeDto
            {
                Id = e.Id,
                Vorname = e.Vorname,
                Name = e.Name,
                Personalnummer = e.Personalnummer,
                Email = e.Email,
                Geburtsdatum = e.Geburtsdatum,
                Funktion = e.Funktion,
                IsSpringer = e.IsSpringer,
                IsFerienjobber = e.IsFerienjobber,
                TeamId = e.TeamId,
                TeamName = e.Team?.Name
            }).ToList(),
            TotalCount = totalCount,
            Page = page,
            PageSize = pageSize
        };

        return Ok(result);
    }

    [HttpPost]
    [Authorize(Roles = "Admin,Disponent")]
    public async Task<ActionResult<EmployeeDto>> Create(EmployeeDto dto)
    {
        var employee = new Employee
        {
            Vorname = dto.Vorname,
            Name = dto.Name,
            Personalnummer = dto.Personalnummer,
            Email = dto.Email,
            Geburtsdatum = dto.Geburtsdatum,
            Funktion = dto.Funktion,
            IsSpringer = dto.IsSpringer,
            IsFerienjobber = dto.IsFerienjobber,
            TeamId = dto.TeamId
        };

        var created = await _repository.AddAsync(employee);
        dto.Id = created.Id;
        return CreatedAtAction(nameof(GetById), new { id = created.Id }, dto);
    }

    [HttpPut("{id}")]
    [Authorize(Roles = "Admin,Disponent")]
    public async Task<ActionResult<EmployeeDto>> Update(int id, EmployeeDto dto)
    {
        var employee = await _repository.GetByIdAsync(id);
        if (employee == null)
            return NotFound();

        employee.Vorname = dto.Vorname;
        employee.Name = dto.Name;
        employee.Personalnummer = dto.Personalnummer;
        employee.Email = dto.Email;
        employee.Geburtsdatum = dto.Geburtsdatum;
        employee.Funktion = dto.Funktion;
        employee.IsSpringer = dto.IsSpringer;
        employee.IsFerienjobber = dto.IsFerienjobber;
        employee.TeamId = dto.TeamId;

        await _repository.UpdateAsync(employee);
        return Ok(dto);
    }

    [HttpDelete("{id}")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> Delete(int id)
    {
        var employee = await _repository.GetByIdAsync(id);
        if (employee == null)
            return NotFound();

        await _repository.DeleteAsync(id);
        return NoContent();
    }
}
