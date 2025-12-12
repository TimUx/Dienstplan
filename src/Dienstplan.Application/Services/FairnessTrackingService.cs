using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;

namespace Dienstplan.Application.Services;

/// <summary>
/// Service for tracking and ensuring fair distribution of shifts
/// </summary>
public class FairnessTrackingService
{
    private readonly IShiftAssignmentRepository _shiftAssignmentRepository;
    private readonly IEmployeeRepository _employeeRepository;

    public FairnessTrackingService(
        IShiftAssignmentRepository shiftAssignmentRepository,
        IEmployeeRepository employeeRepository)
    {
        _shiftAssignmentRepository = shiftAssignmentRepository;
        _employeeRepository = employeeRepository;
    }

    /// <summary>
    /// Gets weekend shift counts for each employee in a date range
    /// </summary>
    public async Task<Dictionary<int, (int SaturdayCount, int SundayCount)>> GetWeekendShiftCounts(
        DateTime startDate, DateTime endDate)
    {
        var assignments = await _shiftAssignmentRepository.GetByDateRangeAsync(startDate, endDate);
        var result = new Dictionary<int, (int, int)>();

        foreach (var assignment in assignments)
        {
            if (!result.ContainsKey(assignment.EmployeeId))
                result[assignment.EmployeeId] = (0, 0);

            if (assignment.Date.DayOfWeek == DayOfWeek.Saturday)
            {
                result[assignment.EmployeeId] = (
                    result[assignment.EmployeeId].Item1 + 1,
                    result[assignment.EmployeeId].Item2
                );
            }
            else if (assignment.Date.DayOfWeek == DayOfWeek.Sunday)
            {
                result[assignment.EmployeeId] = (
                    result[assignment.EmployeeId].Item1,
                    result[assignment.EmployeeId].Item2 + 1
                );
            }
        }

        return result;
    }

    /// <summary>
    /// Gets shift type counts for each employee
    /// </summary>
    public async Task<Dictionary<int, Dictionary<int, int>>> GetShiftTypeCounts(
        DateTime startDate, DateTime endDate)
    {
        var assignments = await _shiftAssignmentRepository.GetByDateRangeAsync(startDate, endDate);
        var result = new Dictionary<int, Dictionary<int, int>>();

        foreach (var assignment in assignments)
        {
            if (!result.ContainsKey(assignment.EmployeeId))
                result[assignment.EmployeeId] = new Dictionary<int, int>();

            if (!result[assignment.EmployeeId].ContainsKey(assignment.ShiftTypeId))
                result[assignment.EmployeeId][assignment.ShiftTypeId] = 0;

            result[assignment.EmployeeId][assignment.ShiftTypeId]++;
        }

        return result;
    }

    /// <summary>
    /// Gets employees sorted by who should get next weekend shift (for fairness)
    /// </summary>
    public async Task<List<Employee>> GetEmployeesByWeekendShiftPriority(
        List<Employee> employees, DateTime startDate, DateTime upToDate)
    {
        var weekendCounts = await GetWeekendShiftCounts(startDate, upToDate);

        return employees.OrderBy(e =>
        {
            if (!weekendCounts.ContainsKey(e.Id))
                return 0;

            return weekendCounts[e.Id].SaturdayCount + weekendCounts[e.Id].SundayCount;
        }).ToList();
    }

    /// <summary>
    /// Gets employees sorted by who should get a specific shift type next (for fairness)
    /// </summary>
    public async Task<List<Employee>> GetEmployeesByShiftTypePriority(
        List<Employee> employees, int shiftTypeId, DateTime startDate, DateTime upToDate)
    {
        var shiftTypeCounts = await GetShiftTypeCounts(startDate, upToDate);

        return employees.OrderBy(e =>
        {
            if (!shiftTypeCounts.ContainsKey(e.Id))
                return 0;

            if (!shiftTypeCounts[e.Id].ContainsKey(shiftTypeId))
                return 0;

            return shiftTypeCounts[e.Id][shiftTypeId];
        }).ToList();
    }

    /// <summary>
    /// Calculates total work hours for an employee in a date range
    /// </summary>
    public async Task<double> GetEmployeeWorkHours(int employeeId, DateTime startDate, DateTime endDate)
    {
        var assignments = (await _shiftAssignmentRepository.GetByEmployeeIdAsync(employeeId))
            .Where(a => a.Date >= startDate && a.Date <= endDate)
            .ToList();

        double totalHours = 0;

        foreach (var assignment in assignments)
        {
            totalHours += GetShiftHours(assignment.ShiftTypeId);
        }

        return totalHours;
    }

    /// <summary>
    /// Gets work hours for a specific week
    /// </summary>
    public async Task<double> GetEmployeeWeekHours(int employeeId, DateTime weekStart)
    {
        var weekEnd = weekStart.AddDays(6);
        return await GetEmployeeWorkHours(employeeId, weekStart, weekEnd);
    }

    /// <summary>
    /// Validates that an employee doesn't exceed monthly hour limit
    /// </summary>
    public async Task<(bool IsValid, string? ErrorMessage)> ValidateMonthlyHours(
        int employeeId, DateTime date, int proposedShiftTypeId)
    {
        var monthStart = new DateTime(date.Year, date.Month, 1);
        var monthEnd = monthStart.AddMonths(1).AddDays(-1);

        var currentHours = await GetEmployeeWorkHours(employeeId, monthStart, monthEnd);
        var proposedHours = GetShiftHours(proposedShiftTypeId);

        if (currentHours + proposedHours > 192)
        {
            return (false, $"Monatsstunden überschritten: {currentHours + proposedHours} > 192");
        }

        return (true, null);
    }

    /// <summary>
    /// Validates that an employee doesn't exceed weekly hour limit
    /// </summary>
    public async Task<(bool IsValid, string? ErrorMessage)> ValidateWeeklyHours(
        int employeeId, DateTime date, int proposedShiftTypeId)
    {
        // Get the start of the week (Monday)
        var daysToMonday = (int)date.DayOfWeek - (int)DayOfWeek.Monday;
        if (daysToMonday < 0) daysToMonday += 7;
        var weekStart = date.AddDays(-daysToMonday);

        var currentHours = await GetEmployeeWeekHours(employeeId, weekStart);
        var proposedHours = GetShiftHours(proposedShiftTypeId);

        if (currentHours + proposedHours > 48)
        {
            return (false, $"Wochenstunden überschritten: {currentHours + proposedHours} > 48");
        }

        return (true, null);
    }

    /// <summary>
    /// Gets the duration in hours for a shift type
    /// </summary>
    private double GetShiftHours(int shiftTypeId)
    {
        return shiftTypeId switch
        {
            1 => 8.0,  // Früh: 05:45-13:45
            2 => 8.0,  // Spät: 13:45-21:45
            3 => 8.0,  // Nacht: 21:45-05:45
            4 => 8.0,  // Zwischendienst: 08:00-16:00
            5 => 8.0,  // BMT: 06:00-14:00
            6 => 9.5,  // BSB: 07:00-16:30 (9.5 hours)
            _ => 8.0
        };
    }
}
