using QuestPDF.Fluent;
using QuestPDF.Helpers;
using QuestPDF.Infrastructure;
using Dienstplan.Application.DTOs;

namespace Dienstplan.Application.Services;

/// <summary>
/// Service for exporting shift schedules to PDF using QuestPDF
/// </summary>
public class PdfExportService : IPdfExportService
{
    public PdfExportService()
    {
        // Configure QuestPDF license - using Community license
        QuestPDF.Settings.License = LicenseType.Community;
    }

    public Task<byte[]> GenerateSchedulePdfAsync(ScheduleViewDto schedule)
    {
        var pdfBytes = Document.Create(container =>
        {
            container.Page(page =>
            {
                page.Size(PageSizes.A4.Landscape());
                page.Margin(30);
                
                page.Header().Element(ComposeHeader);
                page.Content().Element(content => ComposeContent(content, schedule));
                page.Footer().AlignCenter().Text(text =>
                {
                    text.CurrentPageNumber();
                    text.Span(" / ");
                    text.TotalPages();
                });
            });
        }).GeneratePdf();
        
        return Task.FromResult(pdfBytes);
    }

    private void ComposeHeader(IContainer container)
    {
        container.Column(column =>
        {
            column.Item().Text("Dienstplan").FontSize(20).Bold().FontColor(Colors.Blue.Darken2);
            column.Item().PaddingTop(5).LineHorizontal(1).LineColor(Colors.Grey.Lighten1);
        });
    }

    private void ComposeContent(IContainer container, ScheduleViewDto schedule)
    {
        container.PaddingTop(10).Column(column =>
        {
            // Period information
            column.Item().Text($"Zeitraum: {schedule.StartDate:dd.MM.yyyy} - {schedule.EndDate:dd.MM.yyyy}")
                .FontSize(12).SemiBold();
            
            column.Item().PaddingTop(10);
            
            // Group assignments by date
            var assignmentsByDate = schedule.Assignments
                .GroupBy(a => a.Date.Date)
                .OrderBy(g => g.Key)
                .ToList();
            
            if (assignmentsByDate.Count == 0)
            {
                column.Item().Text("Keine Schichtzuweisungen für diesen Zeitraum.")
                    .FontSize(10).Italic();
                return;
            }
            
            // Create table
            column.Item().Table(table =>
            {
                // Define columns
                table.ColumnsDefinition(columns =>
                {
                    columns.ConstantColumn(80); // Date
                    columns.RelativeColumn(2); // Früh
                    columns.RelativeColumn(2); // Spät
                    columns.RelativeColumn(2); // Nacht
                    columns.RelativeColumn(2); // Other
                });
                
                // Header
                table.Header(header =>
                {
                    header.Cell().Element(CellStyle).Text("Datum").Bold();
                    header.Cell().Element(CellStyle).Text("Frühdienst").Bold();
                    header.Cell().Element(CellStyle).Text("Spätdienst").Bold();
                    header.Cell().Element(CellStyle).Text("Nachtdienst").Bold();
                    header.Cell().Element(CellStyle).Text("Sonstige").Bold();
                    
                    static IContainer CellStyle(IContainer container)
                    {
                        return container.BorderBottom(1).BorderColor(Colors.Grey.Lighten1)
                            .Padding(5).Background(Colors.Grey.Lighten3);
                    }
                });
                
                // Content rows
                foreach (var dateGroup in assignmentsByDate)
                {
                    var date = dateGroup.Key;
                    var dayAssignments = dateGroup.ToList();
                    
                    // Get assignments by shift type
                    var frueh = dayAssignments.Where(a => a.ShiftCode == "F").ToList();
                    var spaet = dayAssignments.Where(a => a.ShiftCode == "S").ToList();
                    var nacht = dayAssignments.Where(a => a.ShiftCode == "N").ToList();
                    var andere = dayAssignments.Where(a => a.ShiftCode != "F" && a.ShiftCode != "S" && a.ShiftCode != "N").ToList();
                    
                    // Get absences for this date
                    var dayAbsences = schedule.Absences
                        .Where(a => date >= a.StartDate.Date && date <= a.EndDate.Date)
                        .ToList();
                    
                    table.Cell().Element(CellStyle).Text(date.ToString("dd.MM.yyyy\nddd"));
                    table.Cell().Element(CellStyle).Text(FormatEmployeeList(frueh, dayAbsences));
                    table.Cell().Element(CellStyle).Text(FormatEmployeeList(spaet, dayAbsences));
                    table.Cell().Element(CellStyle).Text(FormatEmployeeList(nacht, dayAbsences));
                    table.Cell().Element(CellStyle).Text(FormatEmployeeList(andere, dayAbsences));
                    
                    static IContainer CellStyle(IContainer container)
                    {
                        return container.BorderBottom(1).BorderColor(Colors.Grey.Lighten2)
                            .Padding(5);
                    }
                }
            });
            
            // Legend for absences and springer assignments
            if (schedule.Absences.Any() || assignmentsByDate.Any(g => g.Any(a => a.IsSpringerAssignment)))
            {
                column.Item().PaddingTop(15).Text("Legende").FontSize(10).Bold();
                column.Item().PaddingTop(5).Column(legendColumn =>
                {
                    legendColumn.Item().Text("* = Abwesend (Urlaub/Krank/Lehrgang)").FontSize(8).Italic();
                    legendColumn.Item().Text("(S) = Springer-Einsatz").FontSize(8).Italic();
                });
            }
        });
    }

    private string FormatEmployeeList(List<ShiftAssignmentDto> assignments, List<AbsenceDto> absences)
    {
        if (assignments.Count == 0)
            return "-";
        
        var lines = new List<string>();
        foreach (var assignment in assignments.OrderBy(a => a.EmployeeName))
        {
            var name = assignment.EmployeeName;
            
            // Check if employee is absent
            var isAbsent = absences.Any(a => a.EmployeeId == assignment.EmployeeId);
            if (isAbsent)
            {
                name += " *";
            }
            
            // Mark Springer assignments
            if (assignment.IsSpringerAssignment)
            {
                name += " (S)";
            }
            
            lines.Add(name);
        }
        
        return string.Join("\n", lines);
    }
}
