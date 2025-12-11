namespace Dienstplan.Application.DTOs;

public class EmployeeDto
{
    public int Id { get; set; }
    public string Vorname { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string Personalnummer { get; set; } = string.Empty;
    public string? Email { get; set; }
    public DateTime? Geburtsdatum { get; set; }
    public string? Funktion { get; set; }
    public bool IsSpringer { get; set; }
    public bool IsFerienjobber { get; set; }
    public int? TeamId { get; set; }
    public string? TeamName { get; set; }
}

public class TeamDto
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
    public string? Email { get; set; }
    public int EmployeeCount { get; set; }
}

public class ShiftAssignmentDto
{
    public int Id { get; set; }
    public int EmployeeId { get; set; }
    public string EmployeeName { get; set; } = string.Empty;
    public int? TeamId { get; set; }
    public string? TeamName { get; set; }
    public int ShiftTypeId { get; set; }
    public string ShiftCode { get; set; } = string.Empty;
    public string ShiftName { get; set; } = string.Empty;
    public DateTime Date { get; set; }
    public bool IsManual { get; set; }
    public bool IsSpringerAssignment { get; set; }
    public bool IsFixed { get; set; }
    public string? Notes { get; set; }
    public string? CreatedBy { get; set; }
    public string? ModifiedBy { get; set; }
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

public class VacationRequestDto
{
    public int Id { get; set; }
    public int EmployeeId { get; set; }
    public string EmployeeName { get; set; } = string.Empty;
    public DateTime StartDate { get; set; }
    public DateTime EndDate { get; set; }
    public string Status { get; set; } = string.Empty;
    public string? Notes { get; set; }
    public string? DisponentResponse { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime? UpdatedAt { get; set; }
    public string? ProcessedBy { get; set; }
}

public class CreateVacationRequestDto
{
    public int EmployeeId { get; set; }
    public DateTime StartDate { get; set; }
    public DateTime EndDate { get; set; }
    public string? Notes { get; set; }
}

public class UpdateVacationRequestStatusDto
{
    public string Status { get; set; } = string.Empty;
    public string? DisponentResponse { get; set; }
}

public class ShiftExchangeDto
{
    public int Id { get; set; }
    public int OfferingEmployeeId { get; set; }
    public string OfferingEmployeeName { get; set; } = string.Empty;
    public int ShiftAssignmentId { get; set; }
    public DateTime ShiftDate { get; set; }
    public string ShiftCode { get; set; } = string.Empty;
    public string ShiftName { get; set; } = string.Empty;
    public int? RequestingEmployeeId { get; set; }
    public string? RequestingEmployeeName { get; set; }
    public string Status { get; set; } = string.Empty;
    public string? OfferingReason { get; set; }
    public string? DisponentNotes { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime? UpdatedAt { get; set; }
    public string? ProcessedBy { get; set; }
}

public class CreateShiftExchangeDto
{
    public int ShiftAssignmentId { get; set; }
    public string? OfferingReason { get; set; }
}

public class RequestShiftExchangeDto
{
    public int RequestingEmployeeId { get; set; }
}

public class ProcessShiftExchangeDto
{
    public string Status { get; set; } = string.Empty;
    public string? DisponentNotes { get; set; }
}

public class WeekendShiftStatisticsDto
{
    public int EmployeeId { get; set; }
    public string EmployeeName { get; set; } = string.Empty;
    public int SaturdayShifts { get; set; }
    public int SundayShifts { get; set; }
    public int TotalWeekendShifts { get; set; }
}

public class EmailSettingsDto
{
    public int Id { get; set; }
    public string SmtpServer { get; set; } = string.Empty;
    public int SmtpPort { get; set; }
    public string Protocol { get; set; } = "SMTP";
    public string SecurityProtocol { get; set; } = "STARTTLS";
    public bool RequiresAuthentication { get; set; }
    public string? Username { get; set; }
    public string? Password { get; set; }
    public string SenderEmail { get; set; } = string.Empty;
    public string? SenderName { get; set; }
    public string? ReplyToEmail { get; set; }
    public bool IsActive { get; set; }
}

public class CreateEmailSettingsDto
{
    public string SmtpServer { get; set; } = string.Empty;
    public int SmtpPort { get; set; } = 587;
    public string Protocol { get; set; } = "SMTP";
    public string SecurityProtocol { get; set; } = "STARTTLS";
    public bool RequiresAuthentication { get; set; } = true;
    public string? Username { get; set; }
    public string? Password { get; set; }
    public string SenderEmail { get; set; } = string.Empty;
    public string? SenderName { get; set; }
    public string? ReplyToEmail { get; set; }
}

public class CreateTeamDto
{
    public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
    public string? Email { get; set; }
}

public class UpdateTeamDto
{
    public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
    public string? Email { get; set; }
}
