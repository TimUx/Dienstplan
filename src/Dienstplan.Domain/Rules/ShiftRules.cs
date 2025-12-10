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
    /// Forbidden shift transitions
    /// </summary>
    public static readonly Dictionary<string, List<string>> ForbiddenTransitions = new()
    {
        { ShiftTypeCodes.Spaet, new List<string> { ShiftTypeCodes.Frueh } },
        { ShiftTypeCodes.Nacht, new List<string> { ShiftTypeCodes.Spaet } }
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
    /// Staffing requirements for weekdays
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
    /// Staffing requirements for weekends
    /// </summary>
    public static class WeekendStaffing
    {
        public const int MaxPerShift = 3;
    }
}
