namespace Dienstplan.Application.DTOs;

public class EmployeeDto
{
    public int Id { get; set; }
    public string Vorname { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string Personalnummer { get; set; } = string.Empty;
    public bool IsSpringer { get; set; }
    public int? TeamId { get; set; }
    public string? TeamName { get; set; }
}

public class TeamDto
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
    public int EmployeeCount { get; set; }
}

public class ShiftAssignmentDto
{
    public int Id { get; set; }
    public int EmployeeId { get; set; }
    public string EmployeeName { get; set; } = string.Empty;
    public int ShiftTypeId { get; set; }
    public string ShiftCode { get; set; } = string.Empty;
    public string ShiftName { get; set; } = string.Empty;
    public DateTime Date { get; set; }
    public bool IsManual { get; set; }
    public bool IsSpringerAssignment { get; set; }
    public string? Notes { get; set; }
}

public class AbsenceDto
{
    public int Id { get; set; }
    public int EmployeeId { get; set; }
    public string EmployeeName { get; set; } = string.Empty;
    public string Type { get; set; } = string.Empty;
    public DateTime StartDate { get; set; }
    public DateTime EndDate { get; set; }
    public string? Notes { get; set; }
}

public class ScheduleViewDto
{
    public DateTime StartDate { get; set; }
    public DateTime EndDate { get; set; }
    public List<ShiftAssignmentDto> Assignments { get; set; } = new();
    public List<AbsenceDto> Absences { get; set; } = new();
}

public class DashboardStatisticsDto
{
    public List<EmployeeWorkHoursDto> EmployeeWorkHours { get; set; } = new();
    public List<TeamShiftDistributionDto> TeamShiftDistribution { get; set; } = new();
    public List<EmployeeAbsenceDaysDto> EmployeeAbsenceDays { get; set; } = new();
    public List<TeamWorkloadDto> TeamWorkload { get; set; } = new();
}

public class EmployeeWorkHoursDto
{
    public int EmployeeId { get; set; }
    public string EmployeeName { get; set; } = string.Empty;
    public double TotalHours { get; set; }
    public int ShiftCount { get; set; }
}

public class TeamShiftDistributionDto
{
    public int TeamId { get; set; }
    public string TeamName { get; set; } = string.Empty;
    public Dictionary<string, int> ShiftCounts { get; set; } = new();
}

public class EmployeeAbsenceDaysDto
{
    public int EmployeeId { get; set; }
    public string EmployeeName { get; set; } = string.Empty;
    public int KrankDays { get; set; }
    public int UrlaubDays { get; set; }
    public int LehrgangDays { get; set; }
    public int TotalDays { get; set; }
}

public class TeamWorkloadDto
{
    public int TeamId { get; set; }
    public string TeamName { get; set; } = string.Empty;
    public int TotalShifts { get; set; }
    public double AverageShiftsPerEmployee { get; set; }
}
