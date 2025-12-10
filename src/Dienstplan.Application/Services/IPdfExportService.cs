using Dienstplan.Application.DTOs;

namespace Dienstplan.Application.Services;

/// <summary>
/// Service for exporting shift schedules to PDF
/// </summary>
public interface IPdfExportService
{
    /// <summary>
    /// Generates a PDF of the shift schedule for the specified date range
    /// </summary>
    /// <param name="schedule">Schedule data to export</param>
    /// <returns>PDF as byte array</returns>
    Task<byte[]> GenerateSchedulePdfAsync(ScheduleViewDto schedule);
}
