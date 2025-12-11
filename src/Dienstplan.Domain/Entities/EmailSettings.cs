namespace Dienstplan.Domain.Entities;

/// <summary>
/// Email server configuration settings
/// </summary>
public class EmailSettings
{
    public int Id { get; set; }
    
    /// <summary>
    /// SMTP server hostname or IP address
    /// </summary>
    public string SmtpServer { get; set; } = string.Empty;
    
    /// <summary>
    /// SMTP server port (usually 25, 465, 587)
    /// </summary>
    public int SmtpPort { get; set; } = 587;
    
    /// <summary>
    /// Email protocol (SMTP, SMTPS)
    /// </summary>
    public string Protocol { get; set; } = "SMTP";
    
    /// <summary>
    /// Security protocol (None, SSL, TLS, STARTTLS)
    /// </summary>
    public string SecurityProtocol { get; set; } = "STARTTLS";
    
    /// <summary>
    /// Whether authentication is required
    /// </summary>
    public bool RequiresAuthentication { get; set; } = true;
    
    /// <summary>
    /// Username for SMTP authentication
    /// </summary>
    public string? Username { get; set; }
    
    /// <summary>
    /// Password for SMTP authentication (should be encrypted)
    /// </summary>
    public string? Password { get; set; }
    
    /// <summary>
    /// Default sender email address
    /// </summary>
    public string SenderEmail { get; set; } = string.Empty;
    
    /// <summary>
    /// Display name for sender
    /// </summary>
    public string? SenderName { get; set; }
    
    /// <summary>
    /// Reply-to email address
    /// </summary>
    public string? ReplyToEmail { get; set; }
    
    /// <summary>
    /// Whether these settings are currently active
    /// </summary>
    public bool IsActive { get; set; } = true;
    
    /// <summary>
    /// When these settings were created
    /// </summary>
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    
    /// <summary>
    /// When these settings were last updated
    /// </summary>
    public DateTime? UpdatedAt { get; set; }
}
