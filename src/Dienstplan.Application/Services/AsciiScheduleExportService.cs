using System.Text;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;

namespace Dienstplan.Application.Services;

/// <summary>
/// Service for exporting shift schedules in ASCII format
/// </summary>
public class AsciiScheduleExportService
{
    private readonly IEmployeeRepository _employeeRepository;
    private readonly IShiftAssignmentRepository _shiftAssignmentRepository;
    private readonly IRepository<Team> _teamRepository;

    public AsciiScheduleExportService(
        IEmployeeRepository employeeRepository,
        IShiftAssignmentRepository shiftAssignmentRepository,
        IRepository<Team> teamRepository)
    {
        _employeeRepository = employeeRepository;
        _shiftAssignmentRepository = shiftAssignmentRepository;
        _teamRepository = teamRepository;
    }

    /// <summary>
    /// Generates an ASCII formatted schedule for the given date range
    /// </summary>
    public async Task<string> GenerateAsciiSchedule(DateTime startDate, DateTime endDate)
    {
        var sb = new StringBuilder();
        
        // Get all data
        var teams = (await _teamRepository.GetAllAsync()).OrderBy(t => t.Id).ToList();
        var allEmployees = (await _employeeRepository.GetAllAsync()).ToList();
        var assignments = (await _shiftAssignmentRepository.GetByDateRangeAsync(startDate, endDate)).ToList();
        
        // Generate header with week numbers and dates
        GenerateHeader(sb, startDate, endDate);
        
        // Generate team sections
        foreach (var team in teams.Where(t => t.Employees.Any()))
        {
            GenerateTeamSection(sb, team, startDate, endDate, assignments);
        }
        
        // Generate springer section (employees without team or marked as springer)
        GenerateSpringerSection(sb, allEmployees, startDate, endDate, assignments);
        
        // Generate special functions section
        GenerateSpecialFunctionsSection(sb, allEmployees, startDate, endDate, assignments);
        
        // Generate legend
        GenerateLegend(sb);
        
        return sb.ToString();
    }

    private void GenerateHeader(StringBuilder sb, DateTime startDate, DateTime endDate)
    {
        var dates = GetDateRange(startDate, endDate).ToList();
        
        // Week numbers and dates row
        sb.Append("KW/Datum  ");
        foreach (var date in dates)
        {
            var weekNumber = GetWeekNumber(date);
            var dayOfWeek = GetGermanDayOfWeek(date.DayOfWeek);
            sb.Append($"| {date.Day:D2} {dayOfWeek} ");
        }
        sb.AppendLine("|");
        
        // Separator line
        sb.Append("----------");
        foreach (var date in dates)
        {
            sb.Append("|-------");
        }
        sb.AppendLine("|");
    }

    private void GenerateTeamSection(StringBuilder sb, Team team, DateTime startDate, DateTime endDate, 
        List<ShiftAssignment> allAssignments)
    {
        sb.AppendLine($"\n{team.Name}");
        
        var teamEmployees = team.Employees.Where(e => !e.IsSpringer).OrderBy(e => e.Name).ToList();
        
        foreach (var employee in teamEmployees)
        {
            GenerateEmployeeLine(sb, employee, startDate, endDate, allAssignments);
        }
    }

    private void GenerateSpringerSection(StringBuilder sb, List<Employee> allEmployees, 
        DateTime startDate, DateTime endDate, List<ShiftAssignment> allAssignments)
    {
        var springers = allEmployees.Where(e => e.IsSpringer).OrderBy(e => e.Name).ToList();
        
        if (!springers.Any())
            return;
        
        sb.AppendLine("\nSpringer (teamübergreifend)");
        
        foreach (var springer in springers)
        {
            GenerateEmployeeLine(sb, springer, startDate, endDate, allAssignments, markAsSpringer: true);
        }
    }

    private void GenerateSpecialFunctionsSection(StringBuilder sb, List<Employee> allEmployees, 
        DateTime startDate, DateTime endDate, List<ShiftAssignment> allAssignments)
    {
        sb.AppendLine("\nZusatzfunktionen");
        
        var dates = GetDateRange(startDate, endDate).ToList();
        
        // BMT row
        var bmtEmployees = allEmployees.Where(e => e.IsBrandmeldetechniker).ToList();
        if (bmtEmployees.Any())
        {
            sb.Append("BMT           ");
            foreach (var date in dates)
            {
                var bmtAssignment = allAssignments
                    .Where(a => a.Date.Date == date.Date)
                    .Where(a => bmtEmployees.Any(e => e.Id == a.EmployeeId))
                    .FirstOrDefault(a => GetShiftCodeById(a.ShiftTypeId) == ShiftTypeCodes.BMT);
                
                var display = bmtAssignment != null 
                    ? $"{ShiftTypeCodes.BMT}" 
                    : "-";
                sb.Append($"| {display,-5} ");
            }
            sb.AppendLine("|");
        }
        
        // BSB row
        var bsbEmployees = allEmployees.Where(e => e.IsBrandschutzbeauftragter).ToList();
        if (bsbEmployees.Any())
        {
            sb.Append("BSB           ");
            foreach (var date in dates)
            {
                var bsbAssignment = allAssignments
                    .Where(a => a.Date.Date == date.Date)
                    .Where(a => bsbEmployees.Any(e => e.Id == a.EmployeeId))
                    .FirstOrDefault(a => GetShiftCodeById(a.ShiftTypeId) == ShiftTypeCodes.BSB);
                
                var display = bsbAssignment != null 
                    ? $"{ShiftTypeCodes.BSB}" 
                    : "-";
                sb.Append($"| {display,-5} ");
            }
            sb.AppendLine("|");
        }
    }

    private void GenerateEmployeeLine(StringBuilder sb, Employee employee, DateTime startDate, 
        DateTime endDate, List<ShiftAssignment> allAssignments, bool markAsSpringer = false)
    {
        var name = employee.Name;
        if (markAsSpringer)
            name += " (Spr)";
        
        sb.Append($"{name,-10}");
        
        var dates = GetDateRange(startDate, endDate).ToList();
        foreach (var date in dates)
        {
            var assignment = allAssignments
                .FirstOrDefault(a => a.EmployeeId == employee.Id && a.Date.Date == date.Date);
            
            var display = assignment != null 
                ? GetShiftCodeById(assignment.ShiftTypeId) 
                : "-";
            
            sb.Append($"| {display,-5} ");
        }
        sb.AppendLine("|");
    }

    private void GenerateLegend(StringBuilder sb)
    {
        sb.AppendLine("\n---------------------------------------------------------------");
        sb.AppendLine("Legende:");
        sb.AppendLine("F     = Früh (05:45–13:45)");
        sb.AppendLine("S     = Spät (13:45–21:45)");
        sb.AppendLine("N     = Nacht (21:45–05:45)");
        sb.AppendLine("Ur    = Urlaub");
        sb.AppendLine("-     = Frei");
        sb.AppendLine("TA    = Zwischendienst");
        sb.AppendLine("TD    = Technischer Dienst / Brandmeldetechnik");
        sb.AppendLine("EH_A  = Einsatzhilfe Alarm");
        sb.AppendLine("BMT   = Brandmeldetechniker (06:00-14:00, Mo-Fr)");
        sb.AppendLine("BSB   = Brandschutzbeauftragter (07:00-16:30, Mo-Fr, 9,5 Std.)");
    }

    private IEnumerable<DateTime> GetDateRange(DateTime startDate, DateTime endDate)
    {
        for (var date = startDate; date <= endDate; date = date.AddDays(1))
        {
            yield return date;
        }
    }

    private string GetGermanDayOfWeek(DayOfWeek day)
    {
        return day switch
        {
            DayOfWeek.Monday => "Mo",
            DayOfWeek.Tuesday => "Di",
            DayOfWeek.Wednesday => "Mi",
            DayOfWeek.Thursday => "Do",
            DayOfWeek.Friday => "Fr",
            DayOfWeek.Saturday => "Sa",
            DayOfWeek.Sunday => "So",
            _ => ""
        };
    }

    private int GetWeekNumber(DateTime date)
    {
        var culture = System.Globalization.CultureInfo.CurrentCulture;
        return culture.Calendar.GetWeekOfYear(date, 
            System.Globalization.CalendarWeekRule.FirstFourDayWeek, DayOfWeek.Monday);
    }

    private string GetShiftCodeById(int id)
    {
        return id switch
        {
            1 => ShiftTypeCodes.Frueh,
            2 => ShiftTypeCodes.Spaet,
            3 => ShiftTypeCodes.Nacht,
            4 => ShiftTypeCodes.Zwischendienst,
            5 => ShiftTypeCodes.BMT,
            6 => ShiftTypeCodes.BSB,
            _ => "?"
        };
    }
}
