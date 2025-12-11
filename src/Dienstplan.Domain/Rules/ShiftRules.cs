using Dienstplan.Domain.Entities;

namespace Dienstplan.Domain.Rules;

/// <summary>
/// Defines the rules for shift planning
/// </summary>
public class ShiftRules
{
    /// <summary>
    /// Minimum rest hours between shifts (Ruhezeit)
    /// </summary>
    public const int MinimumRestHours = 11;
    
    /// <summary>
    /// Maximum consecutive shifts
    /// </summary>
    public const int MaximumConsecutiveShifts = 6;
    
    /// <summary>
    /// Maximum consecutive night shifts
    /// </summary>
    public const int MaximumConsecutiveNightShifts = 3;
    
    /// <summary>
    /// Maximum hours per month per employee
    /// </summary>
    public const int MaximumHoursPerMonth = 192;
    
    /// <summary>
    /// Maximum hours per week per employee
    /// </summary>
    public const int MaximumHoursPerWeek = 48;
    
    /// <summary>
    /// Forbidden shift transitions (must respect 11-hour rest period)
    /// Spät ends at 21:45, Früh starts at 05:45 = only 8 hours rest (forbidden)
    /// Nacht ends at 05:45, Früh starts at 05:45 = 0 hours rest (forbidden)
    /// </summary>
    public static readonly Dictionary<string, List<string>> ForbiddenTransitions = new()
    {
        { ShiftTypeCodes.Spaet, new List<string> { ShiftTypeCodes.Frueh } },
        { ShiftTypeCodes.Nacht, new List<string> { ShiftTypeCodes.Frueh } }
    };
    
    /// <summary>
    /// Ideal shift rotation pattern: Früh → Nacht → Spät
    /// </summary>
    public static readonly List<string> IdealRotation = new()
    {
        ShiftTypeCodes.Frueh,
        ShiftTypeCodes.Nacht,
        ShiftTypeCodes.Spaet
    };
    
    /// <summary>
    /// Staffing requirements for weekdays (Monday-Friday)
    /// </summary>
    public static class WeekdayStaffing
    {
        public const int FruehMin = 4;
        public const int FruehMax = 5;
        public const int SpaetMin = 3;
        public const int SpaetMax = 4;
        public const int NachtMin = 3;
        public const int NachtMax = 3;
    }
    
    /// <summary>
    /// Staffing requirements for weekends (Saturday-Sunday)
    /// </summary>
    public static class WeekendStaffing
    {
        public const int MinPerShift = 2;
        public const int MaxPerShift = 3;
    }
}
