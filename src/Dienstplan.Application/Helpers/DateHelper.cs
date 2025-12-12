namespace Dienstplan.Application.Helpers;

/// <summary>
/// Helper class for date calculations in shift planning
/// </summary>
public static class DateHelper
{
    /// <summary>
    /// Get the Monday of the week containing the given date (ISO 8601 week starts on Monday)
    /// </summary>
    public static DateTime GetMondayOfWeek(DateTime date)
    {
        // Get day of week (0 = Sunday, 1 = Monday, ..., 6 = Saturday)
        int dayOfWeek = (int)date.DayOfWeek;
        
        // Convert Sunday (0) to 7 to make Monday (1) the first day
        if (dayOfWeek == 0)
            dayOfWeek = 7;
        
        // Calculate days to subtract to get to Monday (1)
        int daysToSubtract = dayOfWeek - 1;
        
        return date.Date.AddDays(-daysToSubtract);
    }
    
    /// <summary>
    /// Get the Sunday of the week containing the given date
    /// </summary>
    public static DateTime GetSundayOfWeek(DateTime date)
    {
        var monday = GetMondayOfWeek(date);
        return monday.AddDays(6);
    }
    
    /// <summary>
    /// Adjust date range to align with complete weeks (Monday to Sunday)
    /// Used for both week and month views to ensure complete weeks are shown
    /// </summary>
    public static (DateTime Start, DateTime End) AlignToCompleteWeeks(DateTime start, DateTime end)
    {
        var alignedStart = GetMondayOfWeek(start);
        var alignedEnd = GetSundayOfWeek(end);
        return (alignedStart, alignedEnd);
    }
    
    /// <summary>
    /// Get date range for month view aligned to complete weeks
    /// If the 1st of the month is not a Monday, shows the Monday before
    /// If the last day of the month is not a Sunday, shows days up to the next Sunday
    /// </summary>
    public static (DateTime Start, DateTime End) GetMonthViewDateRange(int year, int month)
    {
        var firstDayOfMonth = new DateTime(year, month, 1);
        var lastDayOfMonth = new DateTime(year, month, DateTime.DaysInMonth(year, month));
        
        return AlignToCompleteWeeks(firstDayOfMonth, lastDayOfMonth);
    }
    
    /// <summary>
    /// Get date range for week view (always Monday to Sunday)
    /// </summary>
    public static (DateTime Start, DateTime End) GetWeekViewDateRange(DateTime referenceDate)
    {
        var monday = GetMondayOfWeek(referenceDate);
        var sunday = monday.AddDays(6);
        return (monday, sunday);
    }
}
