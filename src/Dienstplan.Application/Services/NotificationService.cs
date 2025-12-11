using Dienstplan.Domain.Interfaces;

namespace Dienstplan.Application.Services;

/// <summary>
/// Placeholder implementation of notification service
/// TODO: Implement email sending with SMTP or email service provider
/// </summary>
public class NotificationService : INotificationService
{
    private readonly IEmployeeRepository _employeeRepository;
    private readonly IVacationRequestRepository _vacationRequestRepository;
    private readonly IShiftExchangeRepository _shiftExchangeRepository;
    private readonly IEmailSettingsRepository _emailSettingsRepository;

    public NotificationService(
        IEmployeeRepository employeeRepository,
        IVacationRequestRepository vacationRequestRepository,
        IShiftExchangeRepository shiftExchangeRepository,
        IEmailSettingsRepository emailSettingsRepository)
    {
        _employeeRepository = employeeRepository;
        _vacationRequestRepository = vacationRequestRepository;
        _shiftExchangeRepository = shiftExchangeRepository;
        _emailSettingsRepository = emailSettingsRepository;
    }

    public async Task<bool> SendEmailAsync(string to, string subject, string body)
    {
        // Get active email settings
        var settings = await _emailSettingsRepository.GetActiveSettingsAsync();
        if (settings == null)
        {
            // No email configuration available
            return false;
        }

        // TODO: Implement actual email sending using settings
        // Example: Use MailKit or System.Net.Mail with settings.SmtpServer, settings.SmtpPort, etc.
        await Task.CompletedTask;
        return true;
    }

    public async Task<bool> SendEmailToMultipleAsync(IEnumerable<string> recipients, string subject, string body)
    {
        // TODO: Implement actual email sending
        await Task.CompletedTask;
        return true;
    }

    public async Task NotifyScheduleChangeAsync(DateTime startDate, DateTime endDate, string changedBy)
    {
        var employees = await _employeeRepository.GetAllAsync();
        var emailAddresses = employees
            .Where(e => !string.IsNullOrWhiteSpace(e.Email))
            .Select(e => e.Email!)
            .ToList();

        if (!emailAddresses.Any())
        {
            return;
        }

        var subject = "Dienstplan wurde geändert";
        var body = $"Der Dienstplan für den Zeitraum {startDate:dd.MM.yyyy} bis {endDate:dd.MM.yyyy} wurde von {changedBy} geändert.";
        
        await SendEmailToMultipleAsync(emailAddresses, subject, body);
    }

    public async Task NotifyVacationRequestStatusAsync(int vacationRequestId, string status)
    {
        var request = await _vacationRequestRepository.GetByIdAsync(vacationRequestId);
        if (request == null || string.IsNullOrWhiteSpace(request.Employee?.Email))
            return;

        var subject = $"Urlaubsantrag {status}";
        var body = $"Ihr Urlaubsantrag für {request.StartDate:dd.MM.yyyy} bis {request.EndDate:dd.MM.yyyy} wurde {status}.";
        
        await SendEmailAsync(request.Employee.Email, subject, body);
    }

    public async Task NotifyShiftExchangeAsync(int shiftExchangeId, string action)
    {
        var exchange = await _shiftExchangeRepository.GetByIdAsync(shiftExchangeId);
        if (exchange == null)
            return;

        var subject = $"Diensttausch {action}";
        var body = $"Ein Diensttausch für den {exchange.ShiftAssignment?.Date:dd.MM.yyyy} wurde {action}.";
        
        // Notify offering employee
        if (!string.IsNullOrWhiteSpace(exchange.OfferingEmployee?.Email))
        {
            await SendEmailAsync(exchange.OfferingEmployee.Email, subject, body);
        }

        // Notify requesting employee if exists
        if (exchange.RequestingEmployee != null && !string.IsNullOrWhiteSpace(exchange.RequestingEmployee.Email))
        {
            await SendEmailAsync(exchange.RequestingEmployee.Email, subject, body);
        }
    }
}
