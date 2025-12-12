using ClosedXML.Excel;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;
using static Dienstplan.Domain.Entities.ShiftTypeCodes;

namespace Dienstplan.Application.Services;

public interface IExcelExportService
{
    Task<byte[]> ExportScheduleToExcelAsync(DateTime startDate, DateTime endDate);
}

public class ExcelExportService : IExcelExportService
{
    private readonly IShiftAssignmentRepository _shiftAssignmentRepository;
    private readonly IEmployeeRepository _employeeRepository;
    private readonly IRepository<Team> _teamRepository;
    private readonly IAbsenceRepository _absenceRepository;

    public ExcelExportService(
        IShiftAssignmentRepository shiftAssignmentRepository,
        IEmployeeRepository employeeRepository,
        IRepository<Team> teamRepository,
        IAbsenceRepository absenceRepository)
    {
        _shiftAssignmentRepository = shiftAssignmentRepository;
        _employeeRepository = employeeRepository;
        _teamRepository = teamRepository;
        _absenceRepository = absenceRepository;
    }

    public async Task<byte[]> ExportScheduleToExcelAsync(DateTime startDate, DateTime endDate)
    {
        using var workbook = new XLWorkbook();
        var worksheet = workbook.Worksheets.Add("Dienstplan");

        // Get data
        var assignments = (await _shiftAssignmentRepository.GetByDateRangeAsync(startDate, endDate)).ToList();
        var employees = (await _employeeRepository.GetAllAsync()).OrderBy(e => e.TeamId).ThenBy(e => e.Name).ToList();
        var teams = (await _teamRepository.GetAllAsync()).OrderBy(t => t.Id).ToList();
        var absences = (await _absenceRepository.GetByDateRangeAsync(startDate, endDate)).ToList();

        // Generate date range
        var dates = new List<DateTime>();
        for (var date = startDate; date <= endDate; date = date.AddDays(1))
        {
            dates.Add(date);
        }

        // Set up header row with dates
        int currentCol = 2; // Start from column B (A is for employee names)
        worksheet.Cell(1, 1).Value = "Mitarbeiter";
        worksheet.Cell(1, 1).Style.Font.Bold = true;
        worksheet.Cell(1, 1).Style.Fill.BackgroundColor = XLColor.LightGray;
        worksheet.Cell(1, 1).Style.Border.OutsideBorder = XLBorderStyleValues.Thin;
        worksheet.Column(1).Width = 25; // Employee name column width

        foreach (var date in dates)
        {
            var cell = worksheet.Cell(1, currentCol);
            cell.Value = date.ToString("ddd\ndd.MM", System.Globalization.CultureInfo.GetCultureInfo("de-DE"));
            cell.Style.Font.Bold = true;
            cell.Style.Alignment.Horizontal = XLAlignmentHorizontalValues.Center;
            cell.Style.Alignment.WrapText = true;
            cell.Style.Fill.BackgroundColor = XLColor.LightGray;
            cell.Style.Border.OutsideBorder = XLBorderStyleValues.Thin;
            
            // Weekend highlighting
            if (date.DayOfWeek == DayOfWeek.Saturday || date.DayOfWeek == DayOfWeek.Sunday)
            {
                cell.Style.Fill.BackgroundColor = XLColor.LightBlue;
            }

            worksheet.Column(currentCol).Width = 12;
            currentCol++;
        }

        // Fill in employee rows
        int currentRow = 2;
        Team? lastTeam = null;

        foreach (var employee in employees)
        {
            // Add team header if team changed
            if (employee.TeamId.HasValue && employee.TeamId != lastTeam?.Id)
            {
                lastTeam = teams.FirstOrDefault(t => t.Id == employee.TeamId);
                if (lastTeam != null)
                {
                    var teamCell = worksheet.Cell(currentRow, 1);
                    teamCell.Value = lastTeam.Name;
                    teamCell.Style.Font.Bold = true;
                    teamCell.Style.Font.FontSize = 12;
                    teamCell.Style.Fill.BackgroundColor = XLColor.DarkGray;
                    teamCell.Style.Font.FontColor = XLColor.White;
                    
                    // Merge cells across the date range
                    worksheet.Range(currentRow, 1, currentRow, dates.Count + 1).Merge();
                    worksheet.Range(currentRow, 1, currentRow, dates.Count + 1).Style.Border.OutsideBorder = XLBorderStyleValues.Medium;
                    
                    currentRow++;
                }
            }

            // Employee name
            var nameCell = worksheet.Cell(currentRow, 1);
            nameCell.Value = employee.FullName + (employee.IsSpringer ? " (Spr)" : "");
            nameCell.Style.Border.OutsideBorder = XLBorderStyleValues.Thin;

            // Fill in shifts for each date
            currentCol = 2;
            foreach (var date in dates)
            {
                var cell = worksheet.Cell(currentRow, currentCol);
                
                // Check for absence
                var absence = absences.FirstOrDefault(a => 
                    a.EmployeeId == employee.Id && 
                    a.StartDate <= date && 
                    a.EndDate >= date);

                if (absence != null)
                {
                    cell.Value = "Ur";
                    cell.Style.Fill.BackgroundColor = XLColor.LightPink;
                    cell.Style.Font.FontColor = XLColor.DarkRed;
                }
                else
                {
                    // Check for shift assignment
                    var assignment = assignments.FirstOrDefault(a => 
                        a.EmployeeId == employee.Id && 
                        a.Date.Date == date.Date);

                    if (assignment != null)
                    {
                        cell.Value = assignment.ShiftType.Code;
                        
                        // Color based on shift type
                        var color = GetShiftColor(assignment.ShiftType.Code);
                        cell.Style.Fill.BackgroundColor = color;
                        
                        // Mark springer assignments
                        if (assignment.IsSpringerAssignment)
                        {
                            cell.Style.Font.FontColor = XLColor.Red;
                            cell.Style.Font.Bold = true;
                        }
                    }
                    else
                    {
                        cell.Value = "-";
                        cell.Style.Fill.BackgroundColor = XLColor.White;
                    }
                }

                cell.Style.Alignment.Horizontal = XLAlignmentHorizontalValues.Center;
                cell.Style.Alignment.Vertical = XLAlignmentVerticalValues.Center;
                cell.Style.Border.OutsideBorder = XLBorderStyleValues.Thin;
                
                currentCol++;
            }

            currentRow++;
        }

        // Add legend at the bottom
        currentRow += 2;
        var legendCell = worksheet.Cell(currentRow, 1);
        legendCell.Value = "Legende:";
        legendCell.Style.Font.Bold = true;
        currentRow++;

        var legendItems = new[]
        {
            (Frueh, "Früh (05:45-13:45)", XLColor.Gold),
            (Spaet, "Spät (13:45-21:45)", XLColor.Tomato),
            (Nacht, "Nacht (21:45-05:45)", XLColor.RoyalBlue),
            (Zwischendienst, "Zwischendienst (08:00-16:00)", XLColor.LimeGreen),
            (BMT, "Brandmeldetechniker", XLColor.Orange),
            (BSB, "Brandschutzbeauftragter", XLColor.Crimson),
            ("Ur", "Urlaub", XLColor.LightPink),
            ("-", "Frei", XLColor.White)
        };

        foreach (var (code, description, color) in legendItems)
        {
            worksheet.Cell(currentRow, 1).Value = code;
            worksheet.Cell(currentRow, 1).Style.Fill.BackgroundColor = color;
            worksheet.Cell(currentRow, 1).Style.Alignment.Horizontal = XLAlignmentHorizontalValues.Center;
            worksheet.Cell(currentRow, 1).Style.Border.OutsideBorder = XLBorderStyleValues.Thin;
            
            worksheet.Cell(currentRow, 2).Value = description;
            worksheet.Cell(currentRow, 2).Style.Border.OutsideBorder = XLBorderStyleValues.Thin;
            
            currentRow++;
        }

        // Set row heights
        worksheet.Row(1).Height = 30;
        for (int i = 2; i < currentRow; i++)
        {
            worksheet.Row(i).Height = 20;
        }

        // Auto-fit columns (but keep minimum widths)
        worksheet.Columns().AdjustToContents();

        // Save to memory stream
        using var stream = new MemoryStream();
        workbook.SaveAs(stream);
        return stream.ToArray();
    }

    private static XLColor GetShiftColor(string shiftCode)
    {
        return shiftCode switch
        {
            Frueh => XLColor.Gold,
            Spaet => XLColor.Tomato,
            Nacht => XLColor.RoyalBlue,
            Zwischendienst => XLColor.LimeGreen,
            BMT => XLColor.Orange,
            BSB => XLColor.Crimson,
            _ => XLColor.LightGray
        };
    }
}
