using Microsoft.AspNetCore.Mvc;
using Dienstplan.Application.DTOs;
using Dienstplan.Application.Services;

namespace Dienstplan.Web.Controllers;

[ApiController]
[Route("api/[controller]")]
public class StatisticsController : ControllerBase
{
    private readonly IStatisticsService _statisticsService;

    public StatisticsController(IStatisticsService statisticsService)
    {
        _statisticsService = statisticsService;
    }

    [HttpGet("dashboard")]
    public async Task<ActionResult<DashboardStatisticsDto>> GetDashboard(
        [FromQuery] DateTime? startDate,
        [FromQuery] DateTime? endDate)
    {
        var start = startDate ?? DateTime.Today.AddMonths(-1);
        var end = endDate ?? DateTime.Today;

        var statistics = await _statisticsService.GetDashboardStatisticsAsync(start, end);
        return Ok(statistics);
    }
}
