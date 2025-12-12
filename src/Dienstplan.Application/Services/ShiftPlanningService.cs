using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;
using Dienstplan.Domain.Rules;
using Dienstplan.Application.Helpers;

namespace Dienstplan.Application.Services;

public class ShiftPlanningService : IShiftPlanningService
{
    private readonly IEmployeeRepository _employeeRepository;
    private readonly IShiftAssignmentRepository _shiftAssignmentRepository;
    private readonly IAbsenceRepository _absenceRepository;

    public ShiftPlanningService(
        IEmployeeRepository employeeRepository,
        IShiftAssignmentRepository shiftAssignmentRepository,
        IAbsenceRepository absenceRepository)
    {
        _employeeRepository = employeeRepository;
        _shiftAssignmentRepository = shiftAssignmentRepository;
        _absenceRepository = absenceRepository;
    }

    public async Task<List<ShiftAssignment>> PlanShifts(DateTime startDate, DateTime endDate, bool force = false)
    {
        var assignments = new List<ShiftAssignment>();
        
        // Get existing assignments (including fixed ones)
        var existingAssignments = (await _shiftAssignmentRepository.GetByDateRangeAsync(startDate, endDate)).ToList();
        
        // Keep fixed assignments and existing assignments if not forcing
        var keptAssignments = force 
            ? existingAssignments.Where(a => a.IsFixed).ToList()
            : existingAssignments;
        
        assignments.AddRange(keptAssignments);
        
        // Get dates that already have assignments (to skip if not forcing)
        var datesWithAssignments = keptAssignments.Select(a => a.Date.Date).Distinct().ToHashSet();
        
        var employees = (await _employeeRepository.GetAllAsync())
            .Where(e => !e.IsSpringer) // Exclude Springers from regular planning
            .ToList();
            
        var absences = await _absenceRepository.GetByDateRangeAsync(startDate, endDate);
        
        // Plan week by week to ensure proper rotation
        var currentDate = startDate;
        while (currentDate <= endDate)
        {
            var (weekStart, weekEnd) = DateHelper.GetWeekViewDateRange(currentDate);
            
            // Don't plan beyond the requested end date
            if (weekStart > endDate)
                break;
            
            weekEnd = weekEnd > endDate ? endDate : weekEnd;
            
            // Check if this week needs planning
            var weekDates = Enumerable.Range(0, (weekEnd - weekStart).Days + 1)
                .Select(d => weekStart.AddDays(d))
                .ToList();
            
            // Skip if all days in this week already have assignments
            if (!force && weekDates.All(d => datesWithAssignments.Contains(d.Date)))
            {
                currentDate = weekEnd.AddDays(1);
                continue;
            }
            
            // Plan the entire week with rotation pattern
            var weekAssignments = await PlanWeekWithRotation(weekStart, weekEnd, employees, absences.ToList(), datesWithAssignments);
            assignments.AddRange(weekAssignments);
            
            currentDate = weekEnd.AddDays(1);
        }
        
        return assignments;
    }

    private async Task<List<ShiftAssignment>> PlanWeekWithRotation(
        DateTime weekStart, 
        DateTime weekEnd, 
        List<Employee> allEmployees, 
        List<Absence> absences,
        HashSet<DateTime> datesWithAssignments)
    {
        var assignments = new List<ShiftAssignment>();
        
        // Group employees by team for fair distribution
        var employeesByTeam = allEmployees.GroupBy(e => e.TeamId ?? 0).ToList();
        
        // For each day of the week, assign shifts following the rotation pattern
        for (var date = weekStart; date <= weekEnd; date = date.AddDays(1))
        {
            // Skip if date already has assignments (fixed assignments)
            if (datesWithAssignments.Contains(date.Date))
                continue;
            
            var isWeekend = date.DayOfWeek == DayOfWeek.Saturday || date.DayOfWeek == DayOfWeek.Sunday;
            
            // Get available employees for this date
            var availableEmployees = allEmployees.Where(e => 
                !absences.Any(a => a.EmployeeId == e.Id && 
                                   a.StartDate <= date && 
                                   a.EndDate >= date)).ToList();
            
            if (availableEmployees.Count == 0)
                continue;
            
            // Determine required shifts and counts
            var shiftRequirements = GetShiftRequirements(isWeekend);
            
            // Get all existing assignments to check rotation and constraints
            var allExistingAssignments = await _shiftAssignmentRepository.GetByDateRangeAsync(weekStart, date.AddDays(1));
            
            // Assign shifts following the ideal rotation: Früh → Nacht → Spät
            var dayAssignments = await AssignShiftsWithRotation(
                date, 
                availableEmployees, 
                shiftRequirements,
                allExistingAssignments.ToList());
            
            assignments.AddRange(dayAssignments);
        }
        
        return assignments;
    }

    private async Task<List<ShiftAssignment>> AssignShiftsWithRotation(
        DateTime date,
        List<Employee> availableEmployees,
        List<(string ShiftCode, int Count)> shiftRequirements,
        List<ShiftAssignment> existingAssignments)
    {
        var assignments = new List<ShiftAssignment>();
        var assignedEmployeeIds = new HashSet<int>();
        
        // Sort employees by their last shift date to distribute work fairly
        var sortedEmployees = await SortEmployeesByWorkload(availableEmployees, date);
        
        // For each required shift type in rotation order
        foreach (var (shiftCode, count) in shiftRequirements)
        {
            int assigned = 0;
            
            foreach (var employee in sortedEmployees)
            {
                if (assigned >= count)
                    break;
                
                // Skip if employee already assigned today
                if (assignedEmployeeIds.Contains(employee.Id))
                    continue;
                
                // Create potential assignment
                var assignment = new ShiftAssignment
                {
                    EmployeeId = employee.Id,
                    ShiftTypeId = GetShiftTypeIdByCode(shiftCode),
                    Date = date,
                    IsManual = false
                };
                
                // Validate assignment against all rules
                var (isValid, _) = await ValidateShiftAssignment(assignment);
                
                if (isValid)
                {
                    assignments.Add(assignment);
                    assignedEmployeeIds.Add(employee.Id);
                    assigned++;
                }
            }
            
            // If we couldn't fill the requirement, try with relaxed validation
            // Still check critical safety rules (rest periods, consecutive shifts)
            if (assigned < count)
            {
                foreach (var employee in sortedEmployees)
                {
                    if (assigned >= count)
                        break;
                    
                    if (assignedEmployeeIds.Contains(employee.Id))
                        continue;
                    
                    var assignment = new ShiftAssignment
                    {
                        EmployeeId = employee.Id,
                        ShiftTypeId = GetShiftTypeIdByCode(shiftCode),
                        Date = date,
                        IsManual = false
                    };
                    
                    // Check critical safety rules (absence, rest periods, consecutive shifts)
                    var hasAbsence = await HasAbsenceOnDate(employee.Id, date);
                    if (!hasAbsence)
                    {
                        // Check forbidden transitions (rest periods)
                        var previousShift = await _shiftAssignmentRepository.GetByEmployeeAndDateAsync(
                            employee.Id, date.AddDays(-1));
                        
                        bool isSafeTransition = true;
                        if (previousShift != null)
                        {
                            var previousShiftCode = GetShiftCodeById(previousShift.ShiftTypeId);
                            if (ShiftRules.ForbiddenTransitions.ContainsKey(previousShiftCode))
                            {
                                isSafeTransition = !ShiftRules.ForbiddenTransitions[previousShiftCode].Contains(shiftCode);
                            }
                        }
                        
                        // Check maximum consecutive shifts
                        var employeeAllAssignments = (await _shiftAssignmentRepository.GetByEmployeeIdAsync(employee.Id))
                            .OrderBy(a => a.Date)
                            .ToList();
                        var consecutiveShifts = CountConsecutiveShifts(employeeAllAssignments, date);
                        
                        if (isSafeTransition && consecutiveShifts < ShiftRules.MaximumConsecutiveShifts)
                        {
                            assignments.Add(assignment);
                            assignedEmployeeIds.Add(employee.Id);
                            assigned++;
                        }
                    }
                }
            }
        }
        
        return assignments;
    }

    private async Task<List<Employee>> SortEmployeesByWorkload(List<Employee> employees, DateTime upToDate)
    {
        // Get shift assignments for the past 30 days to calculate workload
        var startDate = upToDate.AddDays(-30);
        var allAssignments = await _shiftAssignmentRepository.GetByDateRangeAsync(startDate, upToDate);
        
        // Count assignments per employee
        var workloadMap = employees.ToDictionary(e => e.Id, e => 0);
        
        foreach (var assignment in allAssignments)
        {
            if (workloadMap.ContainsKey(assignment.EmployeeId))
            {
                workloadMap[assignment.EmployeeId]++;
            }
        }
        
        // Get the last shift for each employee to implement rotation
        var lastShiftMap = new Dictionary<int, (DateTime Date, string ShiftCode)>();
        
        foreach (var employee in employees)
        {
            var employeeAssignments = allAssignments
                .Where(a => a.EmployeeId == employee.Id)
                .OrderByDescending(a => a.Date)
                .ToList();
            
            if (employeeAssignments.Any())
            {
                var lastShift = employeeAssignments.First();
                var shiftCode = GetShiftCodeById(lastShift.ShiftTypeId);
                lastShiftMap[employee.Id] = (lastShift.Date, shiftCode);
            }
        }
        
        // Sort by workload (ascending) and last shift date (ascending)
        return employees.OrderBy(e => workloadMap[e.Id])
            .ThenBy(e => lastShiftMap.ContainsKey(e.Id) ? lastShiftMap[e.Id].Date : DateTime.MinValue)
            .ToList();
    }

    private async Task<bool> HasAbsenceOnDate(int employeeId, DateTime date)
    {
        var absences = await _absenceRepository.GetByEmployeeIdAsync(employeeId);
        return absences.Any(a => a.StartDate <= date && a.EndDate >= date);
    }

    private List<(string ShiftCode, int Count)> GetShiftRequirements(bool isWeekend)
    {
        if (isWeekend)
        {
            // Weekend: minimum staffing for all shifts in rotation order (Früh → Nacht → Spät)
            return new List<(string, int)>
            {
                (ShiftTypeCodes.Frueh, ShiftRules.WeekendStaffing.MinPerShift),
                (ShiftTypeCodes.Nacht, ShiftRules.WeekendStaffing.MinPerShift),
                (ShiftTypeCodes.Spaet, ShiftRules.WeekendStaffing.MinPerShift)
            };
        }
        else
        {
            // Weekday: minimum staffing following rotation pattern Früh → Nacht → Spät
            return new List<(string, int)>
            {
                (ShiftTypeCodes.Frueh, ShiftRules.WeekdayStaffing.FruehMin),
                (ShiftTypeCodes.Nacht, ShiftRules.WeekdayStaffing.NachtMin),
                (ShiftTypeCodes.Spaet, ShiftRules.WeekdayStaffing.SpaetMin)
            };
        }
    }

    public async Task<(bool IsValid, string? ErrorMessage)> ValidateShiftAssignment(ShiftAssignment assignment)
    {
        // Check if employee is absent
        var absences = await _absenceRepository.GetByEmployeeIdAsync(assignment.EmployeeId);
        if (absences.Any(a => a.StartDate <= assignment.Date && a.EndDate >= assignment.Date))
        {
            return (false, "Mitarbeiter ist an diesem Tag abwesend");
        }
        
        // Get all assignments for this employee to check consecutive shifts
        var employeeAssignments = (await _shiftAssignmentRepository.GetByEmployeeIdAsync(assignment.EmployeeId))
            .OrderBy(a => a.Date)
            .ToList();
        
        var currentShiftCode = GetShiftCodeById(assignment.ShiftTypeId);
        
        // Get previous shift
        var previousShift = await _shiftAssignmentRepository.GetByEmployeeAndDateAsync(
            assignment.EmployeeId, 
            assignment.Date.AddDays(-1));
        
        if (previousShift != null)
        {
            var previousShiftCode = GetShiftCodeById(previousShift.ShiftTypeId);
            
            // Check forbidden transitions
            if (ShiftRules.ForbiddenTransitions.ContainsKey(previousShiftCode))
            {
                if (ShiftRules.ForbiddenTransitions[previousShiftCode].Contains(currentShiftCode))
                {
                    return (false, $"Verbotener Schichtwechsel: {previousShiftCode} → {currentShiftCode}");
                }
            }
            
            // Check for same shift twice in a row
            if (previousShiftCode == currentShiftCode)
            {
                return (false, "Dieselbe Schicht darf nicht zweimal hintereinander zugewiesen werden");
            }
        }
        
        // Check maximum consecutive shifts
        var consecutiveShifts = CountConsecutiveShifts(employeeAssignments, assignment.Date);
        if (consecutiveShifts >= ShiftRules.MaximumConsecutiveShifts)
        {
            return (false, $"Maximum von {ShiftRules.MaximumConsecutiveShifts} aufeinanderfolgenden Schichten erreicht");
        }
        
        // Check maximum consecutive night shifts
        if (currentShiftCode == ShiftTypeCodes.Nacht)
        {
            var consecutiveNightShifts = CountConsecutiveNightShifts(employeeAssignments, assignment.Date);
            if (consecutiveNightShifts >= ShiftRules.MaximumConsecutiveNightShifts)
            {
                return (false, $"Maximum von {ShiftRules.MaximumConsecutiveNightShifts} aufeinanderfolgenden Nachtschichten erreicht");
            }
        }
        
        return (true, null);
    }
    
    private int CountConsecutiveShifts(List<ShiftAssignment> assignments, DateTime fromDate)
    {
        int count = 0;
        var date = fromDate.AddDays(-1);
        
        while (assignments.Any(a => a.Date == date))
        {
            count++;
            date = date.AddDays(-1);
        }
        
        return count;
    }
    
    private int CountConsecutiveNightShifts(List<ShiftAssignment> assignments, DateTime fromDate)
    {
        int count = 0;
        var date = fromDate.AddDays(-1);
        
        while (true)
        {
            var assignment = assignments.FirstOrDefault(a => a.Date == date);
            if (assignment == null)
                break;
            
            var shiftCode = GetShiftCodeById(assignment.ShiftTypeId);
            if (shiftCode != ShiftTypeCodes.Nacht)
                break;
            
            count++;
            date = date.AddDays(-1);
        }
        
        return count;
    }

    public async Task<ShiftAssignment?> AssignSpringer(int employeeId, DateTime date)
    {
        // Find the shift that needs to be covered
        var originalAssignment = await _shiftAssignmentRepository.GetByEmployeeAndDateAsync(employeeId, date);
        if (originalAssignment == null)
        {
            return null;
        }
        
        // Get available Springers
        var springers = await _employeeRepository.GetSpringersAsync();
        var absences = await _absenceRepository.GetByDateRangeAsync(date, date);
        
        var availableSpringers = springers.Where(s => 
            !absences.Any(a => a.EmployeeId == s.Id && 
                               a.StartDate <= date && 
                               a.EndDate >= date)).ToList();
        
        if (!availableSpringers.Any())
        {
            return null;
        }
        
        // Assign first available Springer
        var springer = availableSpringers.First();
        var springerAssignment = new ShiftAssignment
        {
            EmployeeId = springer.Id,
            ShiftTypeId = originalAssignment.ShiftTypeId,
            Date = date,
            IsManual = false,
            IsSpringerAssignment = true
        };
        
        return await _shiftAssignmentRepository.AddAsync(springerAssignment);
    }
    
    /// <summary>
    /// Get shift type ID by code
    /// Note: These IDs correspond to the seeded shift types in DienstplanDbContext.SeedShiftTypes
    /// </summary>
    private int GetShiftTypeIdByCode(string code)
    {
        return code switch
        {
            ShiftTypeCodes.Frueh => 1,
            ShiftTypeCodes.Spaet => 2,
            ShiftTypeCodes.Nacht => 3,
            ShiftTypeCodes.Zwischendienst => 4,
            _ => 1
        };
    }
    
    /// <summary>
    /// Get shift code by type ID
    /// Note: These IDs correspond to the seeded shift types in DienstplanDbContext.SeedShiftTypes
    /// </summary>
    private string GetShiftCodeById(int id)
    {
        return id switch
        {
            1 => ShiftTypeCodes.Frueh,
            2 => ShiftTypeCodes.Spaet,
            3 => ShiftTypeCodes.Nacht,
            4 => ShiftTypeCodes.Zwischendienst,
            _ => ShiftTypeCodes.Frueh
        };
    }
}
