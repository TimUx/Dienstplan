using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using Dienstplan.Application.DTOs;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;

namespace Dienstplan.Web.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class TeamsController : ControllerBase
{
    private readonly ITeamRepository _repository;

    public TeamsController(ITeamRepository repository)
    {
        _repository = repository;
    }

    [HttpGet]
    [AllowAnonymous] // Allow read access for all users
    public async Task<ActionResult<IEnumerable<TeamDto>>> GetAll()
    {
        var teams = await _repository.GetAllAsync();
        var dtos = teams.Select(t => new TeamDto
        {
            Id = t.Id,
            Name = t.Name,
            Description = t.Description,
            EmployeeCount = t.Employees.Count
        });
        return Ok(dtos);
    }

    [HttpGet("{id}")]
    [AllowAnonymous]
    public async Task<ActionResult<TeamDto>> GetById(int id)
    {
        var team = await _repository.GetByIdAsync(id);
        if (team == null)
            return NotFound();

        return Ok(new TeamDto
        {
            Id = team.Id,
            Name = team.Name,
            Description = team.Description,
            EmployeeCount = team.Employees.Count
        });
    }

    [HttpPost]
    [Authorize(Roles = "Admin")]
    public async Task<ActionResult<TeamDto>> Create(TeamDto dto)
    {
        // Check if team name already exists
        var existingTeam = await _repository.GetByNameAsync(dto.Name);
        if (existingTeam != null)
        {
            return BadRequest(new { error = "Ein Team mit diesem Namen existiert bereits" });
        }

        var team = new Team
        {
            Name = dto.Name,
            Description = dto.Description
        };

        var created = await _repository.AddAsync(team);
        dto.Id = created.Id;
        dto.EmployeeCount = 0;
        return CreatedAtAction(nameof(GetById), new { id = created.Id }, dto);
    }

    [HttpPut("{id}")]
    [Authorize(Roles = "Admin")]
    public async Task<ActionResult<TeamDto>> Update(int id, TeamDto dto)
    {
        var team = await _repository.GetByIdAsync(id);
        if (team == null)
            return NotFound();

        // Check if new name conflicts with another team
        if (team.Name != dto.Name)
        {
            var existingTeam = await _repository.GetByNameAsync(dto.Name);
            if (existingTeam != null && existingTeam.Id != id)
            {
                return BadRequest(new { error = "Ein Team mit diesem Namen existiert bereits" });
            }
        }

        team.Name = dto.Name;
        team.Description = dto.Description;

        await _repository.UpdateAsync(team);
        dto.EmployeeCount = team.Employees.Count;
        return Ok(dto);
    }

    [HttpDelete("{id}")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> Delete(int id)
    {
        var team = await _repository.GetByIdAsync(id);
        if (team == null)
            return NotFound();

        // Check if team has employees
        if (team.Employees.Any())
        {
            return BadRequest(new { error = "Team kann nicht gelöscht werden, da es noch Mitarbeiter enthält" });
        }

        await _repository.DeleteAsync(id);
        return NoContent();
    }
}
