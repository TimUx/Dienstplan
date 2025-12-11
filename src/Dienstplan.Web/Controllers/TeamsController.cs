using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;
using Dienstplan.Application.DTOs;

namespace Dienstplan.Web.Controllers;

[ApiController]
[Route("api/[controller]")]
public class TeamsController : ControllerBase
{
    private readonly IRepository<Team> _teamRepository;
    private readonly IRepository<Employee> _employeeRepository;

    public TeamsController(IRepository<Team> teamRepository, IRepository<Employee> employeeRepository)
    {
        _teamRepository = teamRepository;
        _employeeRepository = employeeRepository;
    }

    [HttpGet]
    public async Task<ActionResult<IEnumerable<TeamDto>>> GetTeams()
    {
        var teams = await _teamRepository.GetAllAsync();
        var employees = await _employeeRepository.GetAllAsync();
        
        var teamDtos = teams.Select(t => new TeamDto
        {
            Id = t.Id,
            Name = t.Name,
            Description = t.Description,
            Email = t.Email,
            EmployeeCount = employees.Count(e => e.TeamId == t.Id)
        }).ToList();

        return Ok(teamDtos);
    }

    [HttpGet("{id}")]
    public async Task<ActionResult<TeamDto>> GetTeam(int id)
    {
        var team = await _teamRepository.GetByIdAsync(id);
        if (team == null)
        {
            return NotFound();
        }

        var employees = await _employeeRepository.GetAllAsync();
        
        var teamDto = new TeamDto
        {
            Id = team.Id,
            Name = team.Name,
            Description = team.Description,
            Email = team.Email,
            EmployeeCount = employees.Count(e => e.TeamId == team.Id)
        };

        return Ok(teamDto);
    }

    [HttpPost]
    [Authorize(Roles = "Admin,Disponent")]
    public async Task<ActionResult<TeamDto>> CreateTeam(CreateTeamDto dto)
    {
        var team = new Team
        {
            Name = dto.Name,
            Description = dto.Description,
            Email = dto.Email
        };

        team = await _teamRepository.AddAsync(team);
        
        var teamDto = new TeamDto
        {
            Id = team.Id,
            Name = team.Name,
            Description = team.Description,
            Email = team.Email,
            EmployeeCount = 0
        };

        return CreatedAtAction(nameof(GetTeam), new { id = team.Id }, teamDto);
    }

    [HttpPut("{id}")]
    [Authorize(Roles = "Admin,Disponent")]
    public async Task<IActionResult> UpdateTeam(int id, UpdateTeamDto dto)
    {
        var team = await _teamRepository.GetByIdAsync(id);
        if (team == null)
        {
            return NotFound();
        }

        team.Name = dto.Name;
        team.Description = dto.Description;
        team.Email = dto.Email;

        await _teamRepository.UpdateAsync(team);

        return NoContent();
    }

    [HttpDelete("{id}")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> DeleteTeam(int id)
    {
        var team = await _teamRepository.GetByIdAsync(id);
        if (team == null)
        {
            return NotFound();
        }

        await _teamRepository.DeleteAsync(id);

        return NoContent();
    }
}
