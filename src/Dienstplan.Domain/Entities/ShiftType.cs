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
    public const string Frueh = "F";
    public const string Spaet = "S";
    public const string Nacht = "N";
    public const string Zwischendienst = "ZD";
    public const string TA = "TA";
    public const string TD = "TD";
    public const string EH_A = "EH_A";
    public const string BMT = "BMT";
    public const string BSB = "BSB";
}
