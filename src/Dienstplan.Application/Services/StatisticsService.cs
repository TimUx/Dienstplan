using Dienstplan.Application.DTOs;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;

namespace Dienstplan.Application.Services;

public interface IStatisticsService
{
    Task<DashboardStatisticsDto> GetDashboardStatisticsAsync(DateTime startDate, DateTime endDate);
}

public class StatisticsService : IStatisticsService
{
    private readonly IEmployeeRepository _employeeRepository;
    private readonly IShiftAssignmentRepository _shiftAssignmentRepository;
    private readonly IAbsenceRepository _absenceRepository;

    public StatisticsService(
        IEmployeeRepository employeeRepository,
        IShiftAssignmentRepository shiftAssignmentRepository,
        IAbsenceRepository absenceRepository)
    {
        _employeeRepository = employeeRepository;
        _shiftAssignmentRepository = shiftAssignmentRepository;
        _absenceRepository = absenceRepository;
    }

    public async Task<DashboardStatisticsDto> GetDashboardStatisticsAsync(DateTime startDate, DateTime endDate)
    {
        var employees = (await _employeeRepository.GetAllAsync()).ToList();
        var assignments = (await _shiftAssignmentRepository.GetByDateRangeAsync(startDate, endDate)).ToList();
        var absences = (await _absenceRepository.GetByDateRangeAsync(startDate, endDate)).ToList();

        return new DashboardStatisticsDto
        {
            EmployeeWorkHours = CalculateEmployeeWorkHours(employees, assignments),
            TeamShiftDistribution = CalculateTeamShiftDistribution(employees, assignments),
            EmployeeAbsenceDays = CalculateEmployeeAbsenceDays(employees, absences),
            TeamWorkload = CalculateTeamWorkload(employees, assignments)
        };
    }

    private List<EmployeeWorkHoursDto> CalculateEmployeeWorkHours(List<Employee> employees, List<ShiftAssignment> assignments)
    {
        return employees.Select(e =>
        {
            var employeeAssignments = assignments.Where(a => a.EmployeeId == e.Id).ToList();
            var totalHours = employeeAssignments.Sum(a => CalculateShiftHours(a.ShiftType));
            
            return new EmployeeWorkHoursDto
            {
                EmployeeId = e.Id,
                EmployeeName = e.FullName,
                TotalHours = totalHours,
                ShiftCount = employeeAssignments.Count
            };
        }).OrderByDescending(e => e.TotalHours).ToList();
    }

    private List<TeamShiftDistributionDto> CalculateTeamShiftDistribution(List<Employee> employees, List<ShiftAssignment> assignments)
    {
        var teams = employees.Where(e => e.Team != null).GroupBy(e => e.Team);
        
        return teams.Select(teamGroup =>
        {
            var team = teamGroup.Key!;
            var teamEmployeeIds = teamGroup.Select(e => e.Id).ToList();
            var teamAssignments = assignments.Where(a => teamEmployeeIds.Contains(a.EmployeeId)).ToList();
            
            var shiftCounts = teamAssignments
                .GroupBy(a => a.ShiftType.Code)
                .ToDictionary(g => g.Key, g => g.Count());
            
            return new TeamShiftDistributionDto
            {
                TeamId = team.Id,
                TeamName = team.Name,
                ShiftCounts = shiftCounts
            };
        }).ToList();
    }

    private List<EmployeeAbsenceDaysDto> CalculateEmployeeAbsenceDays(List<Employee> employees, List<Absence> absences)
    {
        return employees.Select(e =>
        {
            var employeeAbsences = absences.Where(a => a.EmployeeId == e.Id).ToList();
            
            return new EmployeeAbsenceDaysDto
            {
                EmployeeId = e.Id,
                EmployeeName = e.FullName,
                KrankDays = CalculateAbsenceDays(employeeAbsences, AbsenceType.Krank),
                UrlaubDays = CalculateAbsenceDays(employeeAbsences, AbsenceType.Urlaub),
                LehrgangDays = CalculateAbsenceDays(employeeAbsences, AbsenceType.Lehrgang),
                TotalDays = employeeAbsences.Sum(a => (a.EndDate - a.StartDate).Days + 1)
            };
        }).Where(e => e.TotalDays > 0).OrderByDescending(e => e.TotalDays).ToList();
    }

    private List<TeamWorkloadDto> CalculateTeamWorkload(List<Employee> employees, List<ShiftAssignment> assignments)
    {
        var teams = employees.Where(e => e.Team != null).GroupBy(e => e.Team);
        
        return teams.Select(teamGroup =>
        {
            var team = teamGroup.Key!;
            var teamEmployees = teamGroup.ToList();
            var teamEmployeeIds = teamEmployees.Select(e => e.Id).ToList();
            var teamAssignments = assignments.Where(a => teamEmployeeIds.Contains(a.EmployeeId)).ToList();
            
            return new TeamWorkloadDto
            {
                TeamId = team.Id,
                TeamName = team.Name,
                TotalShifts = teamAssignments.Count,
                AverageShiftsPerEmployee = teamEmployees.Count > 0 ? 
                    (double)teamAssignments.Count / teamEmployees.Count : 0
            };
        }).ToList();
    }

    private double CalculateShiftHours(ShiftType shiftType)
    {
        var duration = shiftType.EndTime - shiftType.StartTime;
        
        // Handle night shifts that span midnight
        if (duration.TotalHours < 0)
        {
            duration = TimeSpan.FromHours(24) + duration;
        }
        
        return duration.TotalHours;
    }

    private int CalculateAbsenceDays(List<Absence> absences, AbsenceType type)
    {
        return absences
            .Where(a => a.Type == type)
            .Sum(a => (a.EndDate - a.StartDate).Days + 1);
    }
}
