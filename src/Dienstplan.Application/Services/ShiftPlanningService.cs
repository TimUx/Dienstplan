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
    private readonly SpringerManagementService? _springerService;
    private readonly FairnessTrackingService? _fairnessService;
    private readonly SpecialFunctionService? _specialFunctionService;

    public ShiftPlanningService(
        IEmployeeRepository employeeRepository,
        IShiftAssignmentRepository shiftAssignmentRepository,
        IAbsenceRepository absenceRepository,
        SpringerManagementService? springerService = null,
        FairnessTrackingService? fairnessService = null,
        SpecialFunctionService? specialFunctionService = null)
    {
        _employeeRepository = employeeRepository;
        _shiftAssignmentRepository = shiftAssignmentRepository;
        _absenceRepository = absenceRepository;
        _springerService = springerService;
        _fairnessService = fairnessService;
        _specialFunctionService = specialFunctionService;
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
        
        // Get all employees (excluding Springers from regular team rotation)
        var allEmployees = (await _employeeRepository.GetAllAsync()).ToList();
        var regularEmployees = allEmployees.Where(e => !e.IsSpringer).ToList();
            
        var absences = (await _absenceRepository.GetByDateRangeAsync(startDate, endDate)).ToList();
        
        // Get teams for weekly rotation
        var teams = GetTeamsForRotation(regularEmployees);
        
        if (teams.Count < 3)
        {
            // Fallback to old algorithm if we don't have 3 teams
            return await PlanShiftsLegacy(startDate, endDate, force, assignments, datesWithAssignments, regularEmployees, absences);
        }
        
        // Plan week by week with team-based rotation
        var currentDate = DateHelper.GetMondayOfWeek(startDate);
        var planEndDate = DateHelper.GetSundayOfWeek(endDate);
        
        while (currentDate <= planEndDate)
        {
            var weekEnd = currentDate.AddDays(6); // Sunday
            
            // Check if this week needs planning
            if (!force && Enumerable.Range(0, 7).All(d => datesWithAssignments.Contains(currentDate.AddDays(d).Date)))
            {
                currentDate = currentDate.AddDays(7);
                continue;
            }
            
            // Determine which shift type each team should work this week based on rotation
            var weekNumber = GetWeekNumber(currentDate);
            var teamShiftRotation = GetTeamShiftRotationForWeek(weekNumber);
            
            // Plan the entire week with team-based rotation
            var weekAssignments = await PlanWeekWithTeamRotation(
                currentDate, 
                weekEnd, 
                teams, 
                teamShiftRotation,
                absences,
                datesWithAssignments);
            
            assignments.AddRange(weekAssignments);
            
            // Add to dates with assignments
            foreach (var assignment in weekAssignments)
            {
                datesWithAssignments.Add(assignment.Date.Date);
            }
            
            currentDate = currentDate.AddDays(7);
        }
        
        // Plan special functions (BMT/BSB) if service available
        if (_specialFunctionService != null)
        {
            var bmtAssignments = await _specialFunctionService.AssignBMT(startDate, endDate);
            assignments.AddRange(bmtAssignments);
            
            var bsbAssignments = await _specialFunctionService.AssignBSB(startDate, endDate);
            assignments.AddRange(bsbAssignments);
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

    /// <summary>
    /// Gets teams organized for rotation (ensures 3 teams)
    /// </summary>
    private List<TeamRotation> GetTeamsForRotation(List<Employee> employees)
    {
        var teamGroups = employees
            .Where(e => e.TeamId.HasValue)
            .GroupBy(e => e.TeamId!.Value)
            .Select(g => new TeamRotation
            {
                TeamId = g.Key,
                TeamName = g.First().Team?.Name ?? $"Team {g.Key}",
                Members = g.ToList()
            })
            .OrderBy(t => t.TeamId)
            .ToList();
        
        return teamGroups;
    }
    
    /// <summary>
    /// Gets the ISO 8601 week number for a date
    /// </summary>
    private int GetWeekNumber(DateTime date)
    {
        var culture = System.Globalization.CultureInfo.CurrentCulture;
        var calendar = culture.Calendar;
        var calendarWeekRule = culture.DateTimeFormat.CalendarWeekRule;
        var firstDayOfWeek = culture.DateTimeFormat.FirstDayOfWeek;
        
        return calendar.GetWeekOfYear(date, calendarWeekRule, firstDayOfWeek);
    }
    
    /// <summary>
    /// Determines which shift type each team (0, 1, 2) should work in a given week
    /// Following the pattern:
    /// Week 1: Team 0→Früh, Team 1→Spät, Team 2→Nacht
    /// Week 2: Team 0→Nacht, Team 1→Früh, Team 2→Spät
    /// Week 3: Team 0→Spät, Team 1→Nacht, Team 2→Früh
    /// </summary>
    private Dictionary<int, string> GetTeamShiftRotationForWeek(int weekNumber)
    {
        // 3-week rotation cycle
        var rotationWeek = ((weekNumber - 1) % 3);
        
        var rotation = new Dictionary<int, string>();
        
        switch (rotationWeek)
        {
            case 0: // Week 1 pattern
                rotation[0] = ShiftTypeCodes.Frueh;
                rotation[1] = ShiftTypeCodes.Spaet;
                rotation[2] = ShiftTypeCodes.Nacht;
                break;
            case 1: // Week 2 pattern
                rotation[0] = ShiftTypeCodes.Nacht;
                rotation[1] = ShiftTypeCodes.Frueh;
                rotation[2] = ShiftTypeCodes.Spaet;
                break;
            case 2: // Week 3 pattern
                rotation[0] = ShiftTypeCodes.Spaet;
                rotation[1] = ShiftTypeCodes.Nacht;
                rotation[2] = ShiftTypeCodes.Frueh;
                break;
        }
        
        return rotation;
    }
    
    /// <summary>
    /// Plans a week using team-based rotation
    /// </summary>
    private async Task<List<ShiftAssignment>> PlanWeekWithTeamRotation(
        DateTime weekStart,
        DateTime weekEnd,
        List<TeamRotation> teams,
        Dictionary<int, string> teamShiftRotation,
        List<Absence> absences,
        HashSet<DateTime> datesWithAssignments)
    {
        var assignments = new List<ShiftAssignment>();
        
        for (var date = weekStart; date <= weekEnd; date = date.AddDays(1))
        {
            // Skip if date already has assignments
            if (datesWithAssignments.Contains(date.Date))
                continue;
            
            var isWeekend = date.DayOfWeek == DayOfWeek.Saturday || date.DayOfWeek == DayOfWeek.Sunday;
            var shiftRequirements = GetShiftRequirements(isWeekend);
            
            // For each shift requirement, assign from the appropriate team
            foreach (var (shiftCode, requiredCount) in shiftRequirements)
            {
                var shiftTypeId = GetShiftTypeIdByCode(shiftCode);
                
                // Find which team should work this shift this week
                var teamEntry = teamShiftRotation.FirstOrDefault(kvp => kvp.Value == shiftCode);
                var assignedTeamIndex = teamEntry.Value != null ? teamEntry.Key : -1;
                var assignedTeam = assignedTeamIndex >= 0 ? teams.ElementAtOrDefault(assignedTeamIndex) : null;
                
                if (assignedTeam == null)
                {
                    // Fallback: distribute across all teams
                    assignedTeam = teams.FirstOrDefault();
                    if (assignedTeam == null) continue;
                }
                
                // Get available members from the assigned team
                var availableMembers = assignedTeam.Members.Where(e =>
                    !absences.Any(a => a.EmployeeId == e.Id && 
                                     a.StartDate <= date && 
                                     a.EndDate >= date)).ToList();
                
                // Sort by workload for fairness
                var sortedMembers = await SortEmployeesByWorkload(availableMembers, date);
                
                int assigned = 0;
                foreach (var employee in sortedMembers)
                {
                    if (assigned >= requiredCount)
                        break;
                    
                    // Check if employee already has a shift today
                    if (assignments.Any(a => a.EmployeeId == employee.Id && a.Date.Date == date.Date))
                        continue;
                    
                    // Create assignment
                    var assignment = new ShiftAssignment
                    {
                        EmployeeId = employee.Id,
                        ShiftTypeId = shiftTypeId,
                        Date = date,
                        IsManual = false
                    };
                    
                    // Validate assignment
                    var (isValid, _) = await ValidateShiftAssignment(assignment);
                    
                    if (isValid)
                    {
                        assignments.Add(assignment);
                        assigned++;
                    }
                }
                
                // If we couldn't fill requirement from assigned team, use other teams
                if (assigned < requiredCount)
                {
                    var otherTeams = teams.Where(t => t.TeamId != assignedTeam.TeamId).ToList();
                    
                    foreach (var otherTeam in otherTeams)
                    {
                        if (assigned >= requiredCount)
                            break;
                        
                        var otherAvailableMembers = otherTeam.Members.Where(e =>
                            !absences.Any(a => a.EmployeeId == e.Id && 
                                             a.StartDate <= date && 
                                             a.EndDate >= date) &&
                            !assignments.Any(a => a.EmployeeId == e.Id && a.Date.Date == date.Date)).ToList();
                        
                        var otherSortedMembers = await SortEmployeesByWorkload(otherAvailableMembers, date);
                        
                        foreach (var employee in otherSortedMembers)
                        {
                            if (assigned >= requiredCount)
                                break;
                            
                            var assignment = new ShiftAssignment
                            {
                                EmployeeId = employee.Id,
                                ShiftTypeId = shiftTypeId,
                                Date = date,
                                IsManual = false
                            };
                            
                            var (isValid, _) = await ValidateShiftAssignment(assignment);
                            
                            if (isValid)
                            {
                                assignments.Add(assignment);
                                assigned++;
                            }
                        }
                    }
                }
            }
        }
        
        return assignments;
    }
    
    /// <summary>
    /// Fallback to legacy algorithm if teams aren't properly configured
    /// </summary>
    private async Task<List<ShiftAssignment>> PlanShiftsLegacy(
        DateTime startDate,
        DateTime endDate,
        bool force,
        List<ShiftAssignment> assignments,
        HashSet<DateTime> datesWithAssignments,
        List<Employee> employees,
        List<Absence> absences)
    {
        // Plan week by week to ensure proper rotation
        var currentDate = startDate;
        while (currentDate <= endDate)
        {
            var (weekStart, weekEnd) = DateHelper.GetWeekViewDateRange(currentDate);
            
            if (weekStart > endDate)
                break;
            
            weekEnd = weekEnd > endDate ? endDate : weekEnd;
            
            // Check if this week needs planning
            var weekDates = Enumerable.Range(0, (weekEnd - weekStart).Days + 1)
                .Select(d => weekStart.AddDays(d))
                .ToList();
            
            if (!force && weekDates.All(d => datesWithAssignments.Contains(d.Date)))
            {
                currentDate = weekEnd.AddDays(1);
                continue;
            }
            
            // Plan the entire week
            var weekAssignments = await PlanWeekWithRotation(weekStart, weekEnd, employees, absences, datesWithAssignments);
            assignments.AddRange(weekAssignments);
            
            currentDate = weekEnd.AddDays(1);
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
        
        // Sort employees by fairness if service available
        List<Employee> sortedEmployees;
        if (_fairnessService != null)
        {
            // For weekends, prioritize by weekend shift count
            if (date.DayOfWeek == DayOfWeek.Saturday || date.DayOfWeek == DayOfWeek.Sunday)
            {
                sortedEmployees = await _fairnessService.GetEmployeesByWeekendShiftPriority(
                    availableEmployees, date.AddDays(-90), date);
            }
            else
            {
                sortedEmployees = await SortEmployeesByWorkload(availableEmployees, date);
            }
        }
        else
        {
            sortedEmployees = await SortEmployeesByWorkload(availableEmployees, date);
        }
        
        // For each required shift type in rotation order
        foreach (var (shiftCode, count) in shiftRequirements)
        {
            int assigned = 0;
            var shiftTypeId = GetShiftTypeIdByCode(shiftCode);
            
            // If fairness service available, re-sort by this specific shift type
            List<Employee> candidatesForShift;
            if (_fairnessService != null && shiftCode != ShiftTypeCodes.Zwischendienst)
            {
                candidatesForShift = await _fairnessService.GetEmployeesByShiftTypePriority(
                    sortedEmployees, shiftTypeId, date.AddDays(-90), date);
            }
            else
            {
                candidatesForShift = sortedEmployees;
            }
            
            foreach (var employee in candidatesForShift)
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
                    ShiftTypeId = shiftTypeId,
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
                foreach (var employee in candidatesForShift)
                {
                    if (assigned >= count)
                        break;
                    
                    if (assignedEmployeeIds.Contains(employee.Id))
                        continue;
                    
                    var assignment = new ShiftAssignment
                    {
                        EmployeeId = employee.Id,
                        ShiftTypeId = shiftTypeId,
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
        
        // Validate springer availability if service available
        if (_springerService != null && assignments.Any())
        {
            var validation = await _springerService.ValidateSpringerAllocation(assignments, date);
            // Log warning if no springer available, but don't fail the planning
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
        
        // Validate monthly hours if fairness service is available
        if (_fairnessService != null)
        {
            var monthlyValidation = await _fairnessService.ValidateMonthlyHours(
                assignment.EmployeeId, assignment.Date, assignment.ShiftTypeId);
            
            if (!monthlyValidation.IsValid)
                return monthlyValidation;
        }
        
        // Validate weekly hours if fairness service is available
        if (_fairnessService != null)
        {
            var weeklyValidation = await _fairnessService.ValidateWeeklyHours(
                assignment.EmployeeId, assignment.Date, assignment.ShiftTypeId);
            
            if (!weeklyValidation.IsValid)
                return weeklyValidation;
        }
        
        // Get all assignments for this employee (including from previous months for cross-month checks)
        var lookbackDate = assignment.Date.AddDays(-30); // Look back 30 days for cross-month validation
        var employeeAssignments = (await _shiftAssignmentRepository.GetByDateRangeAsync(lookbackDate, assignment.Date.AddDays(1)))
            .Where(a => a.EmployeeId == assignment.EmployeeId)
            .OrderBy(a => a.Date)
            .ToList();
        
        var currentShiftCode = GetShiftCodeById(assignment.ShiftTypeId);
        
        // Get previous shift (check cross-month)
        var previousShift = await _shiftAssignmentRepository.GetByEmployeeAndDateAsync(
            assignment.EmployeeId, 
            assignment.Date.AddDays(-1));
        
        if (previousShift != null)
        {
            var previousShiftCode = GetShiftCodeById(previousShift.ShiftTypeId);
            
            // Check forbidden transitions (rest period violations)
            if (ShiftRules.ForbiddenTransitions.ContainsKey(previousShiftCode))
            {
                if (ShiftRules.ForbiddenTransitions[previousShiftCode].Contains(currentShiftCode))
                {
                    return (false, $"Verbotener Schichtwechsel: {previousShiftCode} → {currentShiftCode} (Ruhezeit-Verstoß)");
                }
            }
            
            // Check for same shift twice in a row
            if (previousShiftCode == currentShiftCode)
            {
                return (false, "Dieselbe Schicht darf nicht zweimal hintereinander zugewiesen werden");
            }
        }
        
        // Check maximum consecutive shifts (cross-month aware)
        var consecutiveShifts = CountConsecutiveShifts(employeeAssignments, assignment.Date);
        if (consecutiveShifts >= ShiftRules.MaximumConsecutiveShifts)
        {
            return (false, $"Maximum von {ShiftRules.MaximumConsecutiveShifts} aufeinanderfolgenden Schichten erreicht");
        }
        
        // Check if rest day is required after long shift series
        if (consecutiveShifts >= ShiftRules.MaximumConsecutiveShifts - 1)
        {
            // Check if employee had a rest day recently
            var lastRestDay = FindLastRestDay(employeeAssignments, assignment.Date);
            if (lastRestDay.HasValue)
            {
                var daysSinceRest = (assignment.Date - lastRestDay.Value).Days;
                if (daysSinceRest >= ShiftRules.MaximumConsecutiveShifts)
                {
                    return (false, $"Nach {ShiftRules.MaximumConsecutiveShifts} Schichten ist mindestens 1 Ruhetag erforderlich");
                }
            }
        }
        
        // Check maximum consecutive night shifts (cross-month aware)
        if (currentShiftCode == ShiftTypeCodes.Nacht)
        {
            var consecutiveNightShifts = CountConsecutiveNightShifts(employeeAssignments, assignment.Date);
            if (consecutiveNightShifts >= ShiftRules.MaximumConsecutiveNightShifts)
            {
                return (false, $"Maximum von {ShiftRules.MaximumConsecutiveNightShifts} aufeinanderfolgenden Nachtschichten erreicht");
            }
            
            // After max night shifts, require at least 1 rest day
            if (consecutiveNightShifts >= ShiftRules.MaximumConsecutiveNightShifts - 1)
            {
                var lastNightShiftSeries = FindLastNightShiftSeries(employeeAssignments, assignment.Date);
                if (lastNightShiftSeries >= ShiftRules.MaximumConsecutiveNightShifts - 1)
                {
                    return (false, $"Nach {ShiftRules.MaximumConsecutiveNightShifts} Nachtschichten ist mindestens 1 Ruhetag erforderlich");
                }
            }
        }
        
        return (true, null);
    }
    
    private DateTime? FindLastRestDay(List<ShiftAssignment> assignments, DateTime upToDate)
    {
        // Create a HashSet of dates with assignments for O(1) lookup
        var datesWithShifts = new HashSet<DateTime>(assignments.Select(a => a.Date.Date));
        var date = upToDate.AddDays(-1).Date;
        
        // Go back up to 30 days looking for a rest day
        for (int i = 0; i < 30; i++)
        {
            if (!datesWithShifts.Contains(date))
            {
                return date;
            }
            date = date.AddDays(-1);
        }
        
        return null;
    }
    
    private int FindLastNightShiftSeries(List<ShiftAssignment> assignments, DateTime upToDate)
    {
        // Create a dictionary for O(1) lookups by date
        var assignmentsByDate = assignments
            .Where(a => a.Date < upToDate)
            .GroupBy(a => a.Date.Date)
            .ToDictionary(g => g.Key, g => g.First());
        
        int count = 0;
        var date = upToDate.AddDays(-1).Date;
        
        // Count consecutive night shifts before this one
        while (assignmentsByDate.TryGetValue(date, out var assignment))
        {
            var shiftCode = GetShiftCodeById(assignment.ShiftTypeId);
            if (shiftCode == ShiftTypeCodes.Nacht)
            {
                count++;
                date = date.AddDays(-1);
            }
            else
            {
                break;
            }
        }
        
        return count;
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
        // Use SpringerManagementService if available
        if (_springerService != null)
        {
            return await _springerService.AssignSpringerForAbsence(employeeId, date);
        }
        
        // Fallback to original implementation
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
            ShiftTypeCodes.BMT => 5,
            ShiftTypeCodes.BSB => 6,
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
            5 => ShiftTypeCodes.BMT,
            6 => ShiftTypeCodes.BSB,
            _ => ShiftTypeCodes.Frueh
        };
    }
}

/// <summary>
/// Helper class to track team rotation
/// </summary>
internal class TeamRotation
{
    public int TeamId { get; set; }
    public string TeamName { get; set; } = string.Empty;
    public List<Employee> Members { get; set; } = new();
}
