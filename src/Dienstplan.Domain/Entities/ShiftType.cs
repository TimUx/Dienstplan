namespace Dienstplan.Domain.Entities;

/// <summary>
/// Represents a shift type (Schichtart)
/// </summary>
public class ShiftType
{
    public int Id { get; set; }
    
    /// <summary>
    /// Short code (e.g., "F" for Früh, "S" for Spät, "N" for Nacht, "ZD" for Zwischendienst, "SRHT")
    /// </summary>
    public string Code { get; set; } = string.Empty;
    
    /// <summary>
    /// Full name (e.g., "Frühdienst", "Spätdienst")
    /// </summary>
    public string Name { get; set; } = string.Empty;
    
    /// <summary>
    /// Start time (e.g., 05:45 for early shift)
    /// </summary>
    public TimeSpan StartTime { get; set; }
    
    /// <summary>
    /// End time (e.g., 13:45 for early shift)
    /// </summary>
    public TimeSpan EndTime { get; set; }
    
    /// <summary>
    /// Color code for UI display (e.g., "#FFD700" for yellow)
    /// </summary>
    public string? ColorCode { get; set; }
}

/// <summary>
/// Pre-defined shift type codes
/// </summary>
public static class ShiftTypeCodes
{
    /// <summary>
    /// Frühdienst (Early shift): 05:45-13:45
    /// </summary>
    public const string Frueh = "F";
    
    /// <summary>
    /// Spätdienst (Late shift): 13:45-21:45
    /// </summary>
    public const string Spaet = "S";
    
    /// <summary>
    /// Nachtdienst (Night shift): 21:45-05:45
    /// </summary>
    public const string Nacht = "N";
    
    /// <summary>
    /// Zwischendienst (Intermediate shift): 08:00-16:00
    /// </summary>
    public const string Zwischendienst = "ZD";
    
    /// <summary>
    /// Technischer Assistent (Technical Assistant)
    /// </summary>
    public const string TA = "TA";
    
    /// <summary>
    /// Technischer Dienst / Brandmeldetechnik (Technical Service / Fire Alarm Technology)
    /// </summary>
    public const string TD = "TD";
    
    /// <summary>
    /// Einsatzhilfe Alarm (Emergency Response Support)
    /// </summary>
    public const string EH_A = "EH_A";
    
    /// <summary>
    /// Brandmeldetechniker (Fire Alarm Technician): Mon-Fri, 06:00-14:00
    /// </summary>
    public const string BMT = "BMT";
    
    /// <summary>
    /// Brandschutzbeauftragter (Fire Safety Officer): Mon-Fri, 9.5 hours
    /// </summary>
    public const string BSB = "BSB";
}
