using QuestPDF.Fluent;
using QuestPDF.Helpers;
using QuestPDF.Infrastructure;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;

namespace Dienstplan.Application.Services;

public interface IPdfExportService
{
    Task<byte[]> ExportScheduleToPdfAsync(DateTime startDate, DateTime endDate);
}

public class PdfExportService : IPdfExportService
{
    private readonly IShiftAssignmentRepository _shiftAssignmentRepository;
    private readonly IEmployeeRepository _employeeRepository;
    
    public PdfExportService(
        IShiftAssignmentRepository shiftAssignmentRepository,
        IEmployeeRepository employeeRepository)
    {
        _shiftAssignmentRepository = shiftAssignmentRepository;
        _employeeRepository = employeeRepository;
        
        // Set QuestPDF license to Community
        QuestPDF.Settings.License = LicenseType.Community;
    }
    
    public async Task<byte[]> ExportScheduleToPdfAsync(DateTime startDate, DateTime endDate)
    {
        var assignments = (await _shiftAssignmentRepository.GetByDateRangeAsync(startDate, endDate)).ToList();
        var employees = (await _employeeRepository.GetAllAsync()).ToList();
        
        var document = Document.Create(container =>
        {
            container.Page(page =>
            {
                page.Size(PageSizes.A4.Landscape());
                page.Margin(2, Unit.Centimetre);
                page.PageColor(Colors.White);
                page.DefaultTextStyle(x => x.FontSize(10));
                
                page.Header()
                    .Height(60)
                    .Background(Colors.Blue.Medium)
                    .Padding(10)
                    .AlignCenter()
                    .Text(text =>
                    {
                        text.Span("Dienstplan").FontSize(24).FontColor(Colors.White).Bold();
                        text.Span($"\n{startDate:dd.MM.yyyy} - {endDate:dd.MM.yyyy}").FontSize(12).FontColor(Colors.White);
                    });
                
                page.Content()
                    .Padding(10)
                    .Column(column =>
                    {
                        column.Spacing(10);
                        
                        // Group assignments by date
                        var groupedByDate = assignments
                            .GroupBy(a => a.Date.Date)
                            .OrderBy(g => g.Key)
                            .ToList();
                        
                        if (groupedByDate.Count == 0)
                        {
                            column.Item().Text("Keine Schichten im ausgewählten Zeitraum.").FontSize(12);
                        }
                        else
                        {
                            column.Item().Table(table =>
                            {
                                // Define columns
                                table.ColumnsDefinition(columns =>
                                {
                                    columns.RelativeColumn(2); // Date & Day
                                    columns.RelativeColumn(3); // Employee
                                    columns.RelativeColumn(2); // Shift
                                    columns.RelativeColumn(1); // Notes
                                });
                                
                                // Header
                                table.Header(header =>
                                {
                                    header.Cell().Background(Colors.Grey.Lighten2).Padding(5).Text("Datum").Bold();
                                    header.Cell().Background(Colors.Grey.Lighten2).Padding(5).Text("Mitarbeiter").Bold();
                                    header.Cell().Background(Colors.Grey.Lighten2).Padding(5).Text("Schicht").Bold();
                                    header.Cell().Background(Colors.Grey.Lighten2).Padding(5).Text("Hinweise").Bold();
                                });
                                
                                // Rows
                                foreach (var dateGroup in groupedByDate)
                                {
                                    var date = dateGroup.Key;
                                    var dayName = date.ToString("dddd, dd.MM.yyyy", System.Globalization.CultureInfo.GetCultureInfo("de-DE"));
                                    
                                    foreach (var assignment in dateGroup.OrderBy(a => a.Employee.Name))
                                    {
                                        // Get shift color
                                        var shiftColor = GetShiftColor(assignment.ShiftType.Code);
                                        
                                        table.Cell().BorderBottom(0.5f).BorderColor(Colors.Grey.Lighten2).Padding(5).Text(dayName);
                                        table.Cell().BorderBottom(0.5f).BorderColor(Colors.Grey.Lighten2).Padding(5).Text(assignment.Employee.FullName);
                                        table.Cell().BorderBottom(0.5f).BorderColor(Colors.Grey.Lighten2).Padding(5)
                                            .Background(shiftColor)
                                            .Text(text =>
                                            {
                                                text.Span($"{assignment.ShiftType.Code} - {assignment.ShiftType.Name}").Bold();
                                                text.Span($"\n{assignment.ShiftType.StartTime:hh\\:mm} - {assignment.ShiftType.EndTime:hh\\:mm}");
                                            });
                                        table.Cell().BorderBottom(0.5f).BorderColor(Colors.Grey.Lighten2).Padding(5)
                                            .Text(text =>
                                            {
                                                if (assignment.IsSpringerAssignment)
                                                {
                                                    text.Span("Springer").FontColor(Colors.Red.Medium).Bold();
                                                }
                                                if (!string.IsNullOrEmpty(assignment.Notes))
                                                {
                                                    text.Span(assignment.IsSpringerAssignment ? "\n" : "");
                                                    text.Span(assignment.Notes);
                                                }
                                            });
                                    }
                                }
                            });
                        }
                        
                        // Summary section
                        column.Item().PaddingTop(20).Text("Zusammenfassung").FontSize(14).Bold();
                        column.Item().Table(table =>
                        {
                            table.ColumnsDefinition(columns =>
                            {
                                columns.RelativeColumn(3);
                                columns.RelativeColumn(1);
                            });
                            
                            table.Header(header =>
                            {
                                header.Cell().Background(Colors.Grey.Lighten2).Padding(5).Text("Schichtart").Bold();
                                header.Cell().Background(Colors.Grey.Lighten2).Padding(5).Text("Anzahl").Bold();
                            });
                            
                            var shiftTypeCounts = assignments
                                .GroupBy(a => a.ShiftType.Name)
                                .Select(g => new { ShiftType = g.Key, Count = g.Count() })
                                .OrderByDescending(x => x.Count);
                            
                            foreach (var item in shiftTypeCounts)
                            {
                                table.Cell().BorderBottom(0.5f).BorderColor(Colors.Grey.Lighten2).Padding(5).Text(item.ShiftType);
                                table.Cell().BorderBottom(0.5f).BorderColor(Colors.Grey.Lighten2).Padding(5).Text(item.Count.ToString());
                            }
                        });
                    });
                
                page.Footer()
                    .Height(30)
                    .AlignCenter()
                    .Text(text =>
                    {
                        text.Span("Erstellt am: ").FontSize(8);
                        text.Span(DateTime.Now.ToString("dd.MM.yyyy HH:mm")).FontSize(8).Bold();
                        text.Span(" | Seite ").FontSize(8);
                        text.CurrentPageNumber().FontSize(8);
                        text.Span(" von ").FontSize(8);
                        text.TotalPages().FontSize(8);
                    });
            });
        });
        
        return document.GeneratePdf();
    }
    
    private static string GetShiftColor(string shiftCode)
    {
        return shiftCode switch
        {
            "F" => "#FFD700",  // Gold for Frühdienst
            "S" => "#FF6347",  // Tomato for Spätdienst
            "N" => "#4169E1",  // RoyalBlue for Nachtdienst
            "ZD" => "#32CD32", // LimeGreen for Zwischendienst
            _ => "#E0E0E0"     // LightGrey for others
        };
    }
}
