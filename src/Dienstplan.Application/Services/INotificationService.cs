namespace Dienstplan.Application.Services;

/// <summary>
/// Service for sending notifications and emails
/// </summary>
public interface INotificationService
{
    /// <summary>
    /// Send email notification to a single recipient
    /// </summary>
    Task<bool> SendEmailAsync(string to, string subject, string body);
    
    /// <summary>
    /// Send email notification to multiple recipients
    /// </summary>
    Task<bool> SendEmailToMultipleAsync(IEnumerable<string> recipients, string subject, string body);
    
    /// <summary>
    /// Notify all employees about schedule changes
    /// </summary>
    Task NotifyScheduleChangeAsync(DateTime startDate, DateTime endDate, string changedBy);
    
    /// <summary>
    /// Notify employee about vacation request status change
    /// </summary>
    Task NotifyVacationRequestStatusAsync(int vacationRequestId, string status);
    
    /// <summary>
    /// Notify employees about shift exchange
    /// </summary>
    Task NotifyShiftExchangeAsync(int shiftExchangeId, string action);
}
