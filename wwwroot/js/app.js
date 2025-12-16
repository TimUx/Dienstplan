// API Base URL
const API_BASE = window.location.origin + '/api';

// State
let currentDate = new Date();
let currentView = 'week';
let currentUser = null;
let userRoles = [];

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    initializeDatePickers();
    checkAuthenticationStatus();
});

// Authentication functions
async function checkAuthenticationStatus() {
    try {
        const response = await fetch(`${API_BASE}/auth/current-user`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const user = await response.json();
            currentUser = user;
            userRoles = user.roles || [];
            updateUIForAuthenticatedUser(user);
        } else {
            updateUIForAnonymousUser();
        }
    } catch (error) {
        console.error('Error checking authentication:', error);
        updateUIForAnonymousUser();
    }
    
    // Load initial view
    loadSchedule();
}

function updateUIForAuthenticatedUser(user) {
    document.getElementById('user-info').style.display = 'flex';
    document.getElementById('login-prompt').style.display = 'none';
    document.getElementById('user-name').textContent = user.fullName || user.email;
    
    // Show/hide role-specific elements
    const isAdmin = userRoles.includes('Admin');
    const isDisponent = userRoles.includes('Disponent');
    
    // Show admin-only elements
    document.querySelectorAll('.admin-only').forEach(el => {
        if (isAdmin || isDisponent) {
            el.style.display = '';
        } else {
            el.style.display = 'none';
        }
    });
    
    if (isAdmin) {
        document.body.classList.add('admin');
        document.getElementById('nav-admin').style.display = 'inline-block';
        document.getElementById('nav-absences').style.display = 'inline-block';
        document.getElementById('nav-shiftexchange').style.display = 'inline-block';
    } else if (isDisponent) {
        document.body.classList.add('disponent');
        document.getElementById('nav-absences').style.display = 'inline-block';
        document.getElementById('nav-shiftexchange').style.display = 'inline-block';
    } else {
        // Mitarbeiter can also access vacation and shift exchange
        document.getElementById('nav-absences').style.display = 'inline-block';
        document.getElementById('nav-shiftexchange').style.display = 'inline-block';
    }
}

function updateUIForAnonymousUser() {
    document.getElementById('user-info').style.display = 'none';
    document.getElementById('login-prompt').style.display = 'block';
    currentUser = null;
    userRoles = [];
    document.body.classList.remove('admin', 'disponent');
    document.getElementById('nav-admin').style.display = 'none';
    document.getElementById('nav-absences').style.display = 'none';
    document.getElementById('nav-shiftexchange').style.display = 'none';
}

function showLoginModal() {
    document.getElementById('loginModal').style.display = 'block';
    document.getElementById('loginError').style.display = 'none';
}

function closeLoginModal() {
    document.getElementById('loginModal').style.display = 'none';
    document.getElementById('loginForm').reset();
    document.getElementById('loginError').style.display = 'none';
}

async function login(event) {
    event.preventDefault();
    
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    const rememberMe = document.getElementById('rememberMe').checked;
    
    const errorDiv = document.getElementById('loginError');
    errorDiv.style.display = 'none';
    
    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                email: email,
                password: password,
                rememberMe: rememberMe
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            currentUser = data.user;
            userRoles = data.user.roles || [];
            updateUIForAuthenticatedUser(data.user);
            closeLoginModal();
            // Reload current view to show authorized content
            showView('schedule');
        } else {
            errorDiv.textContent = data.error || 'Anmeldung fehlgeschlagen';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        errorDiv.textContent = 'Netzwerkfehler: ' + error.message;
        errorDiv.style.display = 'block';
    }
}

async function logout() {
    try {
        await fetch(`${API_BASE}/auth/logout`, {
            method: 'POST',
            credentials: 'include'
        });
        
        updateUIForAnonymousUser();
        // Reload schedule view
        showView('schedule');
    } catch (error) {
        console.error('Logout error:', error);
    }
}

function isAuthenticated() {
    return currentUser !== null;
}

function hasRole(role) {
    return userRoles.includes(role);
}

function canEditEmployees() {
    return hasRole('Admin') || hasRole('Disponent');
}

function canPlanShifts() {
    return hasRole('Admin') || hasRole('Disponent');
}

function initializeDatePickers() {
    // Get Monday of current week
    const today = new Date();
    const dayOfWeek = today.getDay(); // 0 = Sunday, 1 = Monday, etc.
    // Calculate days to Monday: Sunday needs to go back 6 days, other days use (1 - dayOfWeek)
    const DAYS_FROM_SUNDAY_TO_MONDAY = -6;
    const daysToMonday = dayOfWeek === 0 ? DAYS_FROM_SUNDAY_TO_MONDAY : 1 - dayOfWeek;
    const monday = new Date(today);
    monday.setDate(today.getDate() + daysToMonday);
    
    const mondayStr = monday.toISOString().split('T')[0];
    document.getElementById('startDate').value = mondayStr;
    
    const todayStr = new Date().toISOString().split('T')[0];
    const lastMonth = new Date();
    lastMonth.setMonth(lastMonth.getMonth() - 1);
    document.getElementById('statsStartDate').value = lastMonth.toISOString().split('T')[0];
    document.getElementById('statsEndDate').value = todayStr;
    
    // Initialize month and year selects
    const currentDate = new Date();
    const currentMonth = currentDate.getMonth() + 1;
    const currentYear = currentDate.getFullYear();
    
    // Set current month for month view
    if (document.getElementById('monthSelect')) {
        document.getElementById('monthSelect').value = currentMonth;
    }
    
    // Populate year selects (current year - 1 to current year + 2)
    const yearSelects = ['monthYearSelect', 'yearSelect', 'planMonthYear', 'planYear'];
    yearSelects.forEach(selectId => {
        const select = document.getElementById(selectId);
        if (select) {
            select.innerHTML = '';
            for (let year = currentYear - 1; year <= currentYear + 2; year++) {
                const option = document.createElement('option');
                option.value = year;
                option.textContent = year;
                if (year === currentYear) {
                    option.selected = true;
                }
                select.appendChild(option);
            }
        }
    });
    
    // Initialize plan month to current month
    if (document.getElementById('planMonth')) {
        document.getElementById('planMonth').value = currentMonth;
    }
}

// View Navigation
function showView(viewName) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    
    document.getElementById(`${viewName}-view`).classList.add('active');
    
    // Find and activate the corresponding nav button
    const navButtons = document.querySelectorAll('.nav-btn');
    navButtons.forEach(btn => {
        if (btn.getAttribute('onclick') === `showView('${viewName}')`) {
            btn.classList.add('active');
        }
    });
    
    // Load content based on view
    if (viewName === 'schedule') {
        loadSchedule();
    } else if (viewName === 'employees') {
        loadEmployees();
    } else if (viewName === 'teams') {
        loadTeams();
    } else if (viewName === 'absences') {
        // Load vacation tab by default
        switchAbsenceTab('vacation');
    } else if (viewName === 'vacations') {
        // Redirect old 'vacations' view to new 'absences' view
        showView('absences');
        return;
    } else if (viewName === 'shiftexchange') {
        loadShiftExchanges('available');
    } else if (viewName === 'statistics') {
        loadStatistics();
    } else if (viewName === 'admin') {
        loadAdminView();
    } else if (viewName === 'manual') {
        initializeManualAnchors();
    }
}

function loadAdminView() {
    // Load users tab by default (it will be active)
    loadUsers();
}

// Initialize smooth scrolling for manual anchors
function initializeManualAnchors() {
    document.querySelectorAll('.manual-toc a').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}

// Schedule Management
function switchScheduleView(view, tabElement) {
    // Update active tab
    document.querySelectorAll('.schedule-tab').forEach(t => t.classList.remove('active'));
    tabElement.classList.add('active');
    
    // Update currentView state
    currentView = view;
    
    // Show/hide appropriate controls
    document.getElementById('week-controls').style.display = view === 'week' ? 'flex' : 'none';
    document.getElementById('month-controls').style.display = view === 'month' ? 'flex' : 'none';
    document.getElementById('year-controls').style.display = view === 'year' ? 'flex' : 'none';
    
    // Load schedule for new view
    loadSchedule();
}

function changeDate(days) {
    const dateInput = document.getElementById('startDate');
    const date = new Date(dateInput.value);
    date.setDate(date.getDate() + (days * 7));
    dateInput.value = date.toISOString().split('T')[0];
    loadSchedule();
}

function changeMonth(delta) {
    const monthSelect = document.getElementById('monthSelect');
    const yearSelect = document.getElementById('monthYearSelect');
    
    let month = parseInt(monthSelect.value);
    let year = parseInt(yearSelect.value);
    
    month += delta;
    
    if (month > 12) {
        month = 1;
        year++;
    } else if (month < 1) {
        month = 12;
        year--;
    }
    
    monthSelect.value = month;
    yearSelect.value = year;
    
    loadSchedule();
}

function changeYear(delta) {
    const yearSelect = document.getElementById('yearSelect');
    let year = parseInt(yearSelect.value);
    year += delta;
    yearSelect.value = year;
    loadSchedule();
}

async function loadSchedule() {
    let startDate, viewType;
    
    if (currentView === 'week') {
        startDate = document.getElementById('startDate').value;
        viewType = 'week';
    } else if (currentView === 'month') {
        const month = document.getElementById('monthSelect').value;
        const year = document.getElementById('monthYearSelect').value;
        startDate = `${year}-${month.padStart(2, '0')}-01`;
        viewType = 'month';
    } else if (currentView === 'year') {
        const year = document.getElementById('yearSelect').value;
        startDate = `${year}-01-01`;
        viewType = 'year';
    }
    
    const content = document.getElementById('schedule-content');
    content.innerHTML = '<p class="loading">Lade Dienstplan...</p>';
    
    try {
        // Load both schedule and all employees
        const [scheduleResponse, employeesResponse] = await Promise.all([
            fetch(`${API_BASE}/shifts/schedule?startDate=${startDate}&view=${viewType}`),
            fetch(`${API_BASE}/employees`)
        ]);
        
        const data = await scheduleResponse.json();
        const employees = await employeesResponse.json();
        
        displaySchedule(data, employees);
    } catch (error) {
        content.innerHTML = `<p class="error">Fehler beim Laden: ${error.message}</p>`;
    }
}

function displaySchedule(data, employees) {
    const content = document.getElementById('schedule-content');
    const viewType = currentView;
    
    // Store shifts globally for editing
    allShifts = data.assignments;
    
    // Always show employees, even if no shifts are planned yet
    // Display based on view type
    if (viewType === 'week') {
        content.innerHTML = displayWeekView(data, employees);
    } else if (viewType === 'month') {
        content.innerHTML = displayMonthView(data, employees);
    } else if (viewType === 'year') {
        content.innerHTML = displayYearView(data, employees);
    }
}

function displayWeekView(data, employees) {
    // Group assignments by team and employee, including absences
    const teamGroups = groupByTeamAndEmployee(data.assignments, employees, data.absences || []);
    
    // Get all dates in the range (from backend, already aligned to Monday-Sunday)
    const dates = getUniqueDates(data.assignments);
    
    // If no assignments yet, generate dates from startDate to endDate
    if (dates.length === 0 && data.startDate && data.endDate) {
        dates.push(...generateDateRange(data.startDate, data.endDate));
    }
    
    dates.sort();
    
    if (dates.length === 0) {
        return '<p>Keine Schichten im ausgewählten Zeitraum.</p>';
    }
    
    // Get week info from first date for header
    const firstDate = new Date(dates[0]);
    const weekNumber = getWeekNumber(firstDate);
    const year = firstDate.getFullYear();
    
    // Build table with header
    let html = `<div class="month-header"><h3>Woche: KW ${weekNumber} ${year}</h3></div>`;
    html += '<table class="calendar-table week-view"><thead><tr>';
    html += '<th class="team-column">Team / Person</th>';
    
    // Add date columns
    dates.forEach(dateStr => {
        const date = new Date(dateStr);
        const dayName = date.toLocaleDateString('de-DE', { weekday: 'short' });
        const dayNum = date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' });
        const isSunday = date.getDay() === 0;
        const isHoliday = isHessianHoliday(date);
        const columnClass = (isSunday || isHoliday) ? 'date-column sunday-column' : 'date-column';
        html += `<th class="${columnClass}">${dayName}<br>${dayNum}</th>`;
    });
    
    html += '</tr></thead><tbody>';
    
    // Add rows for each team and employee
    teamGroups.forEach(team => {
        // Team header row
        html += `<tr class="team-row"><td colspan="${dates.length + 1}" class="team-header">${team.teamName}</td></tr>`;
        
        // Employee rows
        team.employees.forEach(employee => {
            html += '<tr class="employee-row">';
            html += `<td class="employee-name">  - ${employee.name}</td>`;
            
            // Add shift cells for each date
            dates.forEach(dateStr => {
                const date = new Date(dateStr);
                const isSunday = date.getDay() === 0;
                const isHoliday = isHessianHoliday(date);
                const shifts = employee.shifts[dateStr] || [];
                
                // Check if employee has absence on this date
                const absence = getAbsenceForDate(employee.absences || [], dateStr);
                
                let content = '';
                if (absence) {
                    // Show absence badge (AU for sick, U for vacation, L for training)
                    const absenceCode = getAbsenceCode(absence.type);
                    content = `<span class="shift-badge shift-${absenceCode}" title="${absence.type}: ${absence.notes || ''}">${absenceCode}</span>`;
                } else {
                    // Show regular shifts
                    content = shifts.map(s => createShiftBadge(s)).join(' ');
                }
                
                const cellClass = (isSunday || isHoliday) ? 'shift-cell sunday-cell' : 'shift-cell';
                html += `<td class="${cellClass}">${content}</td>`;
            });
            
            html += '</tr>';
        });
    });
    
    html += '</tbody></table>';
    return html;
}

function displayMonthView(data, employees) {
    // Group assignments by team and employee, including absences
    const teamGroups = groupByTeamAndEmployee(data.assignments, employees, data.absences || []);
    
    // Get all dates and organize by calendar weeks
    const dates = getUniqueDates(data.assignments);
    
    // If no assignments yet, generate dates from startDate to endDate
    if (dates.length === 0 && data.startDate && data.endDate) {
        dates.push(...generateDateRange(data.startDate, data.endDate));
    }
    
    dates.sort();
    
    if (dates.length === 0) {
        return '<p>Keine Schichten im ausgewählten Zeitraum.</p>';
    }
    
    // Group dates by calendar week
    const weekGroups = groupDatesByWeek(dates);
    
    // Get month name from first date
    const firstDate = new Date(dates[0]);
    const monthName = firstDate.toLocaleDateString('de-DE', { month: 'long', year: 'numeric' });
    
    let html = `<div class="month-header"><h3>Monat: ${monthName}</h3></div>`;
    html += '<table class="calendar-table month-view"><thead><tr>';
    html += '<th class="team-column">Team / Mitarbeiter</th>';
    
    // Add all weeks horizontally - each week shows all its days
    weekGroups.forEach(week => {
        week.days.forEach(day => {
            const date = new Date(day);
            const dayName = date.toLocaleDateString('de-DE', { weekday: 'short' });
            const dayNum = date.getDate();
            const isSunday = date.getDay() === 0;
            const isHoliday = isHessianHoliday(date);
            const columnClass = (isSunday || isHoliday) ? 'date-column sunday-column' : 'date-column';
            html += `<th class="${columnClass}">${dayName} ${dayNum}</th>`;
        });
    });
    
    html += '</tr></thead><tbody>';
    
    // Add rows for each team and employee
    teamGroups.forEach(team => {
        // Calculate total number of days across all weeks
        const totalDays = weekGroups.reduce((sum, w) => sum + w.days.length, 0);
        // Team header row
        html += `<tr class="team-row"><td colspan="${totalDays + 1}" class="team-header">${team.teamName}</td></tr>`;
        
        // Employee rows
        team.employees.forEach(employee => {
            html += '<tr class="employee-row">';
            html += `<td class="employee-name">  - ${employee.name}</td>`;
            
            // Add shift cells for all days across all weeks
            weekGroups.forEach(week => {
                week.days.forEach(dateStr => {
                    const date = new Date(dateStr);
                    const isSunday = date.getDay() === 0;
                    const isHoliday = isHessianHoliday(date);
                    const shifts = employee.shifts[dateStr] || [];
                    
                    // Check if employee has absence on this date
                    const absence = getAbsenceForDate(employee.absences || [], dateStr);
                    
                    let content = '';
                    if (absence) {
                        // Show absence badge (AU for sick, U for vacation, L for training)
                        const absenceCode = getAbsenceCode(absence.type);
                        content = `<span class="shift-badge shift-${absenceCode}" title="${absence.type}: ${absence.notes || ''}">${absenceCode}</span>`;
                    } else {
                        // Show regular shifts
                        content = shifts.map(s => createShiftBadge(s)).join(' ');
                    }
                    
                    const cellClass = (isSunday || isHoliday) ? 'shift-cell sunday-cell' : 'shift-cell';
                    html += `<td class="${cellClass}">${content}</td>`;
                });
            });
            
            html += '</tr>';
        });
    });
    
    html += '</tbody></table>';
    return html;
}

function displayYearView(data, employees) {
    // Group assignments by team and employee, including absences
    const teamGroups = groupByTeamAndEmployee(data.assignments, employees, data.absences || []);
    
    // Get all dates and organize by months and weeks
    const dates = getUniqueDates(data.assignments);
    
    // If no assignments yet, generate dates from startDate to endDate
    if (dates.length === 0 && data.startDate && data.endDate) {
        dates.push(...generateDateRange(data.startDate, data.endDate));
    }
    
    dates.sort();
    
    if (dates.length === 0) {
        return '<p>Keine Schichten im ausgewählten Zeitraum.</p>';
    }
    
    // Group dates by month
    const monthGroups = groupDatesByMonth(dates);
    
    // Get year from first date for main header
    const firstDate = new Date(dates[0]);
    const year = firstDate.getFullYear();
    
    let html = `<div class="month-header"><h3>Jahr: ${year}</h3></div>`;
    html += '<div class="year-view-container">';
    
    // Create a table for each month
    monthGroups.forEach(month => {
        const monthDate = new Date(month.dates[0]);
        const monthName = monthDate.toLocaleDateString('de-DE', { month: 'long' });
        
        html += `<div class="month-section">`;
        html += `<div class="month-header"><h3>${monthName}</h3></div>`;
        html += '<table class="calendar-table year-view"><thead><tr>';
        html += '<th class="team-column">Team / Mitarbeiter</th>';
        
        // Add week columns - all weeks for the month horizontally
        month.weeks.forEach(week => {
            html += `<th class="week-column">KW ${week}</th>`;
        });
        
        html += '</tr></thead><tbody>';
        
        // Add rows for each team and employee
        teamGroups.forEach(team => {
            // Team header row
            html += `<tr class="team-row"><td colspan="${month.weeks.length + 1}" class="team-header">${team.teamName}</td></tr>`;
            
            // Employee rows
            team.employees.forEach(employee => {
                html += '<tr class="employee-row">';
                html += `<td class="employee-name">  - ${employee.name}</td>`;
                
                // Add shift cells for each week
                month.weeks.forEach(weekNum => {
                    const weekDates = month.dates.filter(d => getWeekNumber(new Date(d)) === weekNum);
                    const shifts = [];
                    let hasAbsence = false;
                    let absenceCode = '';
                    
                    weekDates.forEach(dateStr => {
                        // Check for absence first
                        const absence = getAbsenceForDate(employee.absences || [], dateStr);
                        if (absence) {
                            hasAbsence = true;
                            absenceCode = getAbsenceCode(absence.type);
                        } else if (employee.shifts[dateStr]) {
                            shifts.push(...employee.shifts[dateStr]);
                        }
                    });
                    
                    let content = '';
                    if (hasAbsence) {
                        content = `<span class="shift-badge shift-${absenceCode}">${absenceCode}</span>`;
                    } else {
                        content = shifts.map(s => createShiftBadge(s)).join(' ');
                    }
                    
                    html += `<td class="shift-cell">${content}</td>`;
                });
                
                html += '</tr>';
            });
        });
        
        html += '</tbody></table></div>';
    });
    
    html += '</div>';
    return html;
}

// Helper functions

// Constant for employees without team assignment
const UNASSIGNED_TEAM_ID = -1; // Must match Python backend value

// Absence type constants (must match database enum)
const ABSENCE_TYPES = {
    AU: 1,  // Arbeitsunfähigkeit / Sick Leave (Krank)
    U: 2,   // Urlaub / Vacation
    L: 3    // Lehrgang / Training
};

/**
 * Get absence code from absence type string
 * @param {string} typeString - Type string from API (e.g., "Krank / AU", "Urlaub", "Lehrgang")
 * @returns {string} Absence code (AU, U, or L)
 */
function getAbsenceCode(typeString) {
    if (typeString === 'Krank / AU' || typeString === 'Krank') {
        return 'AU';
    } else if (typeString === 'Urlaub') {
        return 'U';
    } else if (typeString === 'Lehrgang') {
        return 'L';
    }
    return 'A'; // Default for unknown types
}

/**
 * Create a shift badge HTML element with appropriate styling and onclick handlers
 * @param {object} shift - Shift object with id, shiftCode, shiftName, isFixed
 * @returns {string} HTML for shift badge
 */
function createShiftBadge(shift) {
    if (!shift || !shift.shiftCode) {
        return '';
    }
    
    const canEdit = canPlanShifts();
    const shiftId = shift.id ? parseInt(shift.id) : null;
    const shiftCode = escapeHtml(shift.shiftCode);
    const shiftName = escapeHtml(shift.shiftName || shiftCode);
    const isFixed = shift.isFixed;
    const lockIcon = isFixed ? '🔒' : '';
    const badgeClass = isFixed ? 'shift-badge-fixed' : '';
    
    // Only add onclick if we have a valid ID and user can edit
    const onclickAttr = (canEdit && shiftId) 
        ? `onclick="editShiftAssignment(${shiftId})" style="cursor:pointer;"` 
        : '';
    
    return `<span class="shift-badge shift-${shiftCode} ${badgeClass}" title="${shiftName}${isFixed ? ' (Fixiert)' : ''}" ${onclickAttr}>${lockIcon}${shiftCode}</span>`;
}

// Constants for team IDs
const VIRTUAL_TEAM_BRANDMELDEANLAGE_ID = 99; // Virtual team ID for fire alarm system (must match database ID)

/**
 * Formats employee display name with personnel number in parentheses
 * @param {string} employeeName - The employee's name
 * @param {string} personalnummer - The employee's personnel number
 * @returns {string} Formatted name like "Max Müller (PN001)" or just the name if no personnel number
 */
function formatEmployeeDisplayName(employeeName, personalnummer) {
    return personalnummer ? `${employeeName} (${personalnummer})` : employeeName;
}

/**
 * Ensures the virtual Brandmeldeanlage team exists in the teams object
 * @param {Object} teams - The teams object to check and update
 */
function ensureVirtualTeam(teams) {
    if (!teams[VIRTUAL_TEAM_BRANDMELDEANLAGE_ID]) {
        teams[VIRTUAL_TEAM_BRANDMELDEANLAGE_ID] = {
            teamId: VIRTUAL_TEAM_BRANDMELDEANLAGE_ID,
            teamName: 'Brandmeldeanlage',
            employees: {}
        };
    }
}

/**
 * Check if employee should be excluded from "Ohne Team" because they belong to virtual team
 * @param {Object} emp - Employee object
 * @returns {boolean} True if employee should be excluded from "Ohne Team"
 */
function shouldExcludeFromUnassigned(emp) {
    // Employees with special functions (BMT/BSB) should only appear in virtual team, not "Ohne Team"
    return !emp.teamId && (emp.isBrandmeldetechniker || emp.isBrandschutzbeauftragter);
}

function groupByTeamAndEmployee(assignments, allEmployees, absences = []) {
    const teams = {};
    
    // Create employee lookup map for better performance
    const employeeMap = new Map(allEmployees.map(emp => [emp.id, emp]));
    
    // First, create team structure with all employees
    allEmployees.forEach(emp => {
        // No longer skip Springers - they should be displayed in their teams
        
        // Skip employees with special functions but no team - they belong only to virtual team
        if (shouldExcludeFromUnassigned(emp)) {
            // Don't add to "Ohne Team" - will be added to virtual team below
        } else {
            // Determine which team(s) this employee belongs to
            const teamId = emp.teamId || UNASSIGNED_TEAM_ID;
            const teamName = emp.teamName || 'Ohne Team';
            
            if (!teams[teamId]) {
                teams[teamId] = {
                    teamId: teamId,
                    teamName: teamName,
                    employees: {}
                };
            }
            
            if (!teams[teamId].employees[emp.id]) {
                // Include personnel number in parentheses after the name
                const displayName = formatEmployeeDisplayName(
                    emp.fullName || `${emp.vorname} ${emp.name}`,
                    emp.personalnummer
                );
                teams[teamId].employees[emp.id] = {
                    id: emp.id,
                    name: displayName,
                    personalnummer: emp.personalnummer,
                    shifts: {},
                    absences: [] // Store absences for this employee
                };
            }
        }
        
        // Also add BSB/MBT employees to virtual "Brandmeldeanlage" team
        if (emp.isBrandmeldetechniker || emp.isBrandschutzbeauftragter) {
            ensureVirtualTeam(teams);
            
            if (!teams[VIRTUAL_TEAM_BRANDMELDEANLAGE_ID].employees[emp.id]) {
                const displayName = formatEmployeeDisplayName(
                    emp.fullName || `${emp.vorname} ${emp.name}`,
                    emp.personalnummer
                );
                teams[VIRTUAL_TEAM_BRANDMELDEANLAGE_ID].employees[emp.id] = {
                    id: emp.id,
                    name: displayName,
                    personalnummer: emp.personalnummer,
                    shifts: {},
                    absences: []
                };
            }
        }
    });
    
    // Then, add shift assignments to the employees
    assignments.forEach(a => {
        const teamId = a.teamId || UNASSIGNED_TEAM_ID;
        
        // Ensure team exists (in case assignment has a team not in allEmployees)
        if (!teams[teamId]) {
            const teamName = 'Ohne Team'; // Will be updated if we find the employee
            teams[teamId] = {
                teamId: teamId,
                teamName: teamName,
                employees: {}
            };
        }
        
        // Ensure employee exists in the team
        if (!teams[teamId].employees[a.employeeId]) {
            // Find employee to get team name and personnel number using map
            const employee = employeeMap.get(a.employeeId);
            const correctTeamName = employee?.teamName || 'Ohne Team';
            teams[teamId].teamName = correctTeamName;
            
            const displayName = formatEmployeeDisplayName(
                a.employeeName,
                employee?.personalnummer || ''
            );
            
            teams[teamId].employees[a.employeeId] = {
                id: a.employeeId,
                name: displayName,
                personalnummer: employee?.personalnummer || '',
                shifts: {},
                absences: []
            };
        }
        
        const dateKey = a.date.split('T')[0];
        if (!teams[teamId].employees[a.employeeId].shifts[dateKey]) {
            teams[teamId].employees[a.employeeId].shifts[dateKey] = [];
        }
        teams[teamId].employees[a.employeeId].shifts[dateKey].push(a);
        
        // If this is a BSB or MBT shift, also add to virtual "Brandmeldeanlage" team
        if (a.shiftCode === 'BSB' || a.shiftCode === 'BMT') {
            ensureVirtualTeam(teams);
            
            if (!teams[VIRTUAL_TEAM_BRANDMELDEANLAGE_ID].employees[a.employeeId]) {
                const employee = employeeMap.get(a.employeeId);
                const displayName = formatEmployeeDisplayName(
                    a.employeeName,
                    employee?.personalnummer || ''
                );
                
                teams[VIRTUAL_TEAM_BRANDMELDEANLAGE_ID].employees[a.employeeId] = {
                    id: a.employeeId,
                    name: displayName,
                    personalnummer: employee?.personalnummer || '',
                    shifts: {},
                    absences: []
                };
            }
            
            if (!teams[VIRTUAL_TEAM_BRANDMELDEANLAGE_ID].employees[a.employeeId].shifts[dateKey]) {
                teams[VIRTUAL_TEAM_BRANDMELDEANLAGE_ID].employees[a.employeeId].shifts[dateKey] = [];
            }
            teams[VIRTUAL_TEAM_BRANDMELDEANLAGE_ID].employees[a.employeeId].shifts[dateKey].push(a);
        }
    });
    
    // Add absences to the employees
    absences.forEach(absence => {
        const teamId = absence.teamId || UNASSIGNED_TEAM_ID;
        
        // Ensure team exists for absence
        if (!teams[teamId]) {
            teams[teamId] = {
                teamId: teamId,
                teamName: 'Ohne Team',
                employees: {}
            };
        }
        
        // Ensure employee exists for absence
        if (!teams[teamId].employees[absence.employeeId]) {
            // Find employee to get personnel number using map
            const employee = employeeMap.get(absence.employeeId);
            const displayName = formatEmployeeDisplayName(
                absence.employeeName,
                employee?.personalnummer || ''
            );
            
            // Create employee entry if not exists
            teams[teamId].employees[absence.employeeId] = {
                id: absence.employeeId,
                name: displayName,
                personalnummer: employee?.personalnummer || '',
                shifts: {},
                absences: []
            };
        }
        
        teams[teamId].employees[absence.employeeId].absences.push(absence);
        
        // If employee has BSB/MBT qualification, also add to virtual "Brandmeldeanlage" team
        const employee = employeeMap.get(absence.employeeId);
        if (employee && (employee.isBrandmeldetechniker || employee.isBrandschutzbeauftragter)) {
            ensureVirtualTeam(teams);
            
            if (!teams[VIRTUAL_TEAM_BRANDMELDEANLAGE_ID].employees[absence.employeeId]) {
                const displayName = formatEmployeeDisplayName(
                    absence.employeeName,
                    employee.personalnummer || ''
                );
                
                teams[VIRTUAL_TEAM_BRANDMELDEANLAGE_ID].employees[absence.employeeId] = {
                    id: absence.employeeId,
                    name: displayName,
                    personalnummer: employee.personalnummer || '',
                    shifts: {},
                    absences: []
                };
            }
            
            teams[VIRTUAL_TEAM_BRANDMELDEANLAGE_ID].employees[absence.employeeId].absences.push(absence);
        }
    });
    
    // Convert to array and sort
    return Object.values(teams).map(team => ({
        teamId: team.teamId,
        teamName: team.teamName,
        employees: Object.values(team.employees).sort((a, b) => a.name.localeCompare(b.name))
    })).sort((a, b) => {
        // Put "Brandmeldeanlage" near the top (after regular teams, before "Ohne Team")
        if (a.teamId === VIRTUAL_TEAM_BRANDMELDEANLAGE_ID && b.teamId !== UNASSIGNED_TEAM_ID) return 1;
        if (b.teamId === VIRTUAL_TEAM_BRANDMELDEANLAGE_ID && a.teamId !== UNASSIGNED_TEAM_ID) return -1;
        // Put "Ohne Team" at the end
        if (a.teamId === UNASSIGNED_TEAM_ID) return 1;
        if (b.teamId === UNASSIGNED_TEAM_ID) return -1;
        return a.teamName.localeCompare(b.teamName);
    });
}

function getUniqueDates(assignments) {
    const dates = new Set();
    assignments.forEach(a => {
        dates.add(a.date.split('T')[0]);
    });
    return Array.from(dates);
}

/**
 * Generate a range of dates from start to end
 * @param {Date|string} start - Start date
 * @param {Date|string} end - End date
 * @returns {string[]} Array of date strings in ISO format (YYYY-MM-DD)
 */
function generateDateRange(start, end) {
    const dates = [];
    const startDate = typeof start === 'string' ? new Date(start) : start;
    const endDate = typeof end === 'string' ? new Date(end) : end;
    
    // Create a new Date object for each iteration to prevent mutation issues
    for (let d = new Date(startDate); d <= endDate; d = new Date(d.getTime() + 86400000)) {
        dates.push(d.toISOString().split('T')[0]);
    }
    return dates;
}

/**
 * Check if employee has an absence on a specific date
 * @param {Array} absences - Array of absence objects
 * @param {string} dateStr - Date string in ISO format (YYYY-MM-DD)
 * @returns {Object|null} Absence object if found, null otherwise
 */
function getAbsenceForDate(absences, dateStr) {
    if (!absences || absences.length === 0) {
        return null;
    }
    
    const checkDate = new Date(dateStr);
    checkDate.setHours(0, 0, 0, 0);
    
    for (const absence of absences) {
        const startDate = new Date(absence.startDate);
        const endDate = new Date(absence.endDate);
        startDate.setHours(0, 0, 0, 0);
        endDate.setHours(0, 0, 0, 0);
        
        if (checkDate >= startDate && checkDate <= endDate) {
            return absence;
        }
    }
    
    return null;
}

/**
 * Calculate ISO 8601 week number for a given date
 * ISO 8601 week starts on Monday and the first week of the year is the week containing the first Thursday
 * @param {Date} date - The date to calculate the week number for
 * @returns {number} The ISO 8601 week number
 */
function getWeekNumber(date) {
    // Create a copy of the date in UTC
    const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
    // ISO 8601 week starts on Monday (day 1), Sunday is day 7
    const dayNum = d.getUTCDay() || 7;
    // Set to the nearest Thursday (current date + 4 - current day number)
    // This ensures we're in the correct week according to ISO 8601
    d.setUTCDate(d.getUTCDate() + 4 - dayNum);
    // Get first day of year
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    // Calculate week number: days since year start divided by 7, rounded up
    return Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
}

function groupDatesByWeek(dates) {
    const weeks = {};
    
    dates.forEach(dateStr => {
        const date = new Date(dateStr);
        const weekNum = getWeekNumber(date);
        
        if (!weeks[weekNum]) {
            weeks[weekNum] = {
                weekNumber: weekNum,
                days: []
            };
        }
        weeks[weekNum].days.push(dateStr);
    });
    
    return Object.values(weeks).sort((a, b) => a.weekNumber - b.weekNumber);
}

function groupDatesByMonth(dates) {
    const months = {};
    
    dates.forEach(dateStr => {
        const date = new Date(dateStr);
        const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
        
        if (!months[monthKey]) {
            months[monthKey] = {
                key: monthKey,
                dates: [],
                weeks: new Set()
            };
        }
        months[monthKey].dates.push(dateStr);
        months[monthKey].weeks.add(getWeekNumber(date));
    });
    
    // Convert weeks to sorted array
    return Object.values(months).map(month => ({
        ...month,
        weeks: Array.from(month.weeks).sort((a, b) => a - b)
    })).sort((a, b) => a.key.localeCompare(b.key));
}

/**
 * Calculate Easter Sunday for a given year using the Meeus/Jones/Butcher algorithm
 * @param {number} year - The year to calculate Easter for
 * @returns {Date} Easter Sunday date
 */
function calculateEaster(year) {
    const a = year % 19;
    const b = Math.floor(year / 100);
    const c = year % 100;
    const d = Math.floor(b / 4);
    const e = b % 4;
    const f = Math.floor((b + 8) / 25);
    const g = Math.floor((b - f + 1) / 3);
    const h = (19 * a + b - d - g + 15) % 30;
    const i = Math.floor(c / 4);
    const k = c % 4;
    const l = (32 + 2 * e + 2 * i - h - k) % 7;
    const m = Math.floor((a + 11 * h + 22 * l) / 451);
    const month = Math.floor((h + l - 7 * m + 114) / 31);
    const day = ((h + l - 7 * m + 114) % 31) + 1;
    return new Date(year, month - 1, day);
}

/**
 * Check if a date is a public holiday in Hessen (Germany)
 * @param {Date} date - The date to check
 * @returns {boolean} True if the date is a Hessian public holiday
 */
function isHessianHoliday(date) {
    const year = date.getFullYear();
    const month = date.getMonth(); // 0-indexed
    const day = date.getDate();
    
    // Fixed holidays
    const fixedHolidays = [
        [0, 1],   // Neujahr (1. Januar)
        [4, 1],   // Tag der Arbeit (1. Mai)
        [9, 3],   // Tag der Deutschen Einheit (3. Oktober)
        [11, 25], // 1. Weihnachtstag (25. Dezember)
        [11, 26]  // 2. Weihnachtstag (26. Dezember)
    ];
    
    for (const [m, d] of fixedHolidays) {
        if (month === m && day === d) {
            return true;
        }
    }
    
    // Easter-dependent holidays
    const easter = calculateEaster(year);
    const easterTime = easter.getTime();
    const dateTime = date.getTime();
    const oneDay = 24 * 60 * 60 * 1000;
    
    // Karfreitag (Good Friday) - 2 days before Easter
    if (dateTime === easterTime - 2 * oneDay) {
        return true;
    }
    
    // Ostermontag (Easter Monday) - 1 day after Easter
    if (dateTime === easterTime + 1 * oneDay) {
        return true;
    }
    
    // Christi Himmelfahrt (Ascension Day) - 39 days after Easter
    if (dateTime === easterTime + 39 * oneDay) {
        return true;
    }
    
    // Pfingstmontag (Whit Monday) - 50 days after Easter
    if (dateTime === easterTime + 50 * oneDay) {
        return true;
    }
    
    // Fronleichnam (Corpus Christi) - 60 days after Easter (Hessen-specific)
    if (dateTime === easterTime + 60 * oneDay) {
        return true;
    }
    
    return false;
}

// Plan Shifts Modal Functions
function showPlanShiftsModal() {
    if (!canPlanShifts()) {
        alert('Sie haben keine Berechtigung, Schichten zu planen. Bitte melden Sie sich als Admin oder Disponent an.');
        return;
    }
    
    document.getElementById('planShiftsModal').style.display = 'block';
}

function closePlanShiftsModal() {
    document.getElementById('planShiftsModal').style.display = 'none';
    document.getElementById('planShiftsForm').reset();
    document.getElementById('monthPlanFields').style.display = 'none';
    document.getElementById('yearPlanFields').style.display = 'none';
}

function updatePlanPeriodFields() {
    const periodType = document.getElementById('planPeriodType').value;
    
    document.getElementById('monthPlanFields').style.display = periodType === 'month' ? 'block' : 'none';
    document.getElementById('yearPlanFields').style.display = periodType === 'year' ? 'block' : 'none';
}

async function executePlanShifts(event) {
    event.preventDefault();
    
    if (!canPlanShifts()) {
        alert('Sie haben keine Berechtigung, Schichten zu planen.');
        return;
    }
    
    const periodType = document.getElementById('planPeriodType').value;
    const force = document.getElementById('planForceOverwrite').checked;
    
    let startDate, endDate;
    
    if (periodType === 'month') {
        const month = document.getElementById('planMonth').value;
        const year = document.getElementById('planMonthYear').value;
        
        startDate = new Date(year, month - 1, 1);
        endDate = new Date(year, month, 0); // Last day of month
    } else if (periodType === 'year') {
        const year = document.getElementById('planYear').value;
        
        startDate = new Date(year, 0, 1);
        endDate = new Date(year, 11, 31);
    } else {
        alert('Bitte wählen Sie einen Planungszeitraum aus.');
        return;
    }
    
    const startDateStr = startDate.toISOString().split('T')[0];
    const endDateStr = endDate.toISOString().split('T')[0];
    
    // Show confirmation
    const periodText = periodType === 'month' 
        ? `${startDate.toLocaleDateString('de-DE', { month: 'long', year: 'numeric' })}`
        : `Jahr ${startDate.getFullYear()}`;
    
    const confirmText = force 
        ? `Möchten Sie wirklich alle Schichten für ${periodText} neu planen? Bestehende Schichten werden überschrieben (außer feste Schichten).`
        : `Möchten Sie Schichten für ${periodText} planen? Bereits geplante Tage werden übersprungen.`;
    
    if (!confirm(confirmText)) {
        return;
    }
    
    try {
        const response = await fetch(
            `${API_BASE}/shifts/plan?startDate=${startDateStr}&endDate=${endDateStr}&force=${force}`,
            { 
                method: 'POST',
                credentials: 'include'
            }
        );
        
        if (response.ok) {
            const data = await response.json();
            alert(`Erfolgreich! ${data.assignmentsCount || 0} Schichten wurden geplant.`);
            closePlanShiftsModal();
            loadSchedule();
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an, um Schichten zu planen.');
        } else if (response.status === 403) {
            alert('Sie haben keine Berechtigung, Schichten zu planen.');
        } else {
            const error = await response.json();
            alert(`Fehler beim Planen der Schichten: ${error.error || 'Unbekannter Fehler'}`);
        }
    } catch (error) {
        alert(`Fehler: ${error.message}`);
    }
}

async function planShifts() {
    // Legacy function - redirect to modal
    showPlanShiftsModal();
}

// PDF Export
async function exportScheduleToPdf() {
    let startDate, endDate;
    
    if (currentView === 'week') {
        const startDateInput = document.getElementById('startDate');
        startDate = startDateInput.value;
        
        if (!startDate) {
            alert('Bitte wählen Sie ein Startdatum aus.');
            return;
        }
        
        const end = new Date(startDate);
        end.setDate(end.getDate() + 7);
        endDate = end.toISOString().split('T')[0];
    } else if (currentView === 'month') {
        const month = document.getElementById('monthSelect').value;
        const year = document.getElementById('monthYearSelect').value;
        
        startDate = `${year}-${month.padStart(2, '0')}-01`;
        const end = new Date(year, month, 0); // Last day of month
        endDate = end.toISOString().split('T')[0];
    } else if (currentView === 'year') {
        const year = document.getElementById('yearSelect').value;
        
        startDate = `${year}-01-01`;
        endDate = `${year}-12-31`;
    }
    
    try {
        // Use fetch to download PDF with authentication, passing the current view type
        const response = await fetch(`${API_BASE}/shifts/export/pdf?startDate=${startDate}&endDate=${endDate}&view=${currentView}`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `Dienstplan_${startDate}_bis_${endDate}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an, um den Dienstplan als PDF zu exportieren.');
        } else if (response.status === 501) {
            const error = await response.json();
            alert(error.error || 'PDF-Export ist noch nicht implementiert.');
        } else {
            alert('Fehler beim PDF-Export. Bitte versuchen Sie es erneut.');
        }
    } catch (error) {
        alert(`Fehler beim PDF-Export: ${error.message}`);
    }
}

async function exportScheduleToExcel() {
    let startDate, endDate;
    
    if (currentView === 'week') {
        const startDateInput = document.getElementById('startDate');
        startDate = startDateInput.value;
        
        if (!startDate) {
            alert('Bitte wählen Sie ein Startdatum aus.');
            return;
        }
        
        const end = new Date(startDate);
        end.setDate(end.getDate() + 7);
        endDate = end.toISOString().split('T')[0];
    } else if (currentView === 'month') {
        const month = document.getElementById('monthSelect').value;
        const year = document.getElementById('monthYearSelect').value;
        
        startDate = `${year}-${month.padStart(2, '0')}-01`;
        const end = new Date(year, month, 0); // Last day of month
        endDate = end.toISOString().split('T')[0];
    } else if (currentView === 'year') {
        const year = document.getElementById('yearSelect').value;
        
        startDate = `${year}-01-01`;
        endDate = `${year}-12-31`;
    }
    
    try {
        // Use fetch to download Excel with authentication, passing the current view type
        const response = await fetch(`${API_BASE}/shifts/export/excel?startDate=${startDate}&endDate=${endDate}&view=${currentView}`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `Dienstplan_${startDate}_bis_${endDate}.xlsx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an, um den Dienstplan als Excel zu exportieren.');
        } else if (response.status === 501) {
            const error = await response.json();
            alert(error.error || 'Excel-Export ist noch nicht implementiert.');
        } else {
            alert('Fehler beim Excel-Export. Bitte versuchen Sie es erneut.');
        }
    } catch (error) {
        alert(`Fehler beim Excel-Export: ${error.message}`);
    }
}

async function exportScheduleToCsv() {
    let startDate, endDate;
    
    if (currentView === 'week') {
        const startDateInput = document.getElementById('startDate');
        startDate = startDateInput.value;
        
        if (!startDate) {
            alert('Bitte wählen Sie ein Startdatum aus.');
            return;
        }
        
        const end = new Date(startDate);
        end.setDate(end.getDate() + 7);
        endDate = end.toISOString().split('T')[0];
    } else if (currentView === 'month') {
        const month = document.getElementById('monthSelect').value;
        const year = document.getElementById('monthYearSelect').value;
        
        startDate = `${year}-${month.padStart(2, '0')}-01`;
        const end = new Date(year, month, 0); // Last day of month
        endDate = end.toISOString().split('T')[0];
    } else if (currentView === 'year') {
        const year = document.getElementById('yearSelect').value;
        
        startDate = `${year}-01-01`;
        endDate = `${year}-12-31`;
    }
    
    try {
        const response = await fetch(`${API_BASE}/shifts/export/csv?startDate=${startDate}&endDate=${endDate}`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `Dienstplan_${startDate}_bis_${endDate}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            alert('Fehler beim CSV-Export. Bitte versuchen Sie es erneut.');
        }
    } catch (error) {
        alert(`Fehler beim CSV-Export: ${error.message}`);
    }
}

// Employee Management
async function loadEmployees() {
    const content = document.getElementById('employees-content');
    content.innerHTML = '<p class="loading">Lade Mitarbeiter...</p>';
    
    try {
        const response = await fetch(`${API_BASE}/employees`);
        const employees = await response.json();
        
        // Cache employees for shift assignment modal
        cachedEmployees = employees;
        
        displayEmployees(employees);
    } catch (error) {
        content.innerHTML = `<p class="error">Fehler beim Laden: ${error.message}</p>`;
    }
}

function displayEmployees(employees) {
    const content = document.getElementById('employees-content');
    
    if (employees.length === 0) {
        content.innerHTML = '<p>Keine Mitarbeiter vorhanden.</p>';
        return;
    }
    
    const canEdit = canEditEmployees();
    const isAdmin = hasRole('Admin');
    
    let html = '<div class="employees-grid">';
    employees.forEach(e => {
        const birthdateStr = e.geburtsdatum ? new Date(e.geburtsdatum).toLocaleDateString('de-DE') : 'Nicht angegeben';
        html += `
            <div class="employee-card">
                <h3>${e.vorname} ${e.name}</h3>
                <div class="employee-info">
                    <span><strong>Personalnr:</strong> ${e.personalnummer}</span>
                    ${e.email ? `<span><strong>E-Mail:</strong> ${e.email}</span>` : ''}
                    ${e.geburtsdatum ? `<span><strong>Geburtsdatum:</strong> ${birthdateStr}</span>` : ''}
                    <span><strong>Team:</strong> ${e.teamName || 'Kein Team'}</span>
                    <div class="badge-row">
                        ${e.isSpringer ? '<span class="badge badge-springer">Springer</span>' : ''}
                        ${e.isFerienjobber ? '<span class="badge badge-ferienjobber">Ferienjobber</span>' : ''}
                        ${e.isBrandmeldetechniker ? '<span class="badge badge-bmt">BMT</span>' : ''}
                        ${e.isBrandschutzbeauftragter ? '<span class="badge badge-bsb">BSB</span>' : ''}
                    </div>
                </div>
                ${canEdit ? `
                    <div class="card-actions">
                        <button onclick="editEmployee(${e.id})" class="btn-small btn-edit">✏️ Bearbeiten</button>
                        ${isAdmin ? `<button onclick="deleteEmployee(${e.id}, '${e.vorname} ${e.name}')" class="btn-small btn-delete">🗑️ Löschen</button>` : ''}
                    </div>
                ` : ''}
            </div>
        `;
    });
    html += '</div>';
    
    content.innerHTML = html;
}

async function showAddEmployeeModal() {
    if (!canEditEmployees()) {
        alert('Sie haben keine Berechtigung, Mitarbeiter hinzuzufügen. Bitte melden Sie sich als Admin oder Disponent an.');
        return;
    }
    
    // Reset form
    document.getElementById('employeeForm').reset();
    document.getElementById('employeeId').value = '';
    document.getElementById('employeeModalTitle').textContent = 'Mitarbeiter hinzufügen';
    
    // Load teams for dropdown
    await loadTeamsForDropdown();
    
    document.getElementById('employeeModal').style.display = 'block';
}

async function editEmployee(id) {
    if (!canEditEmployees()) {
        alert('Sie haben keine Berechtigung, Mitarbeiter zu bearbeiten.');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/employees/${id}`);
        if (!response.ok) {
            alert('Fehler beim Laden der Mitarbeiterdaten');
            return;
        }
        
        const employee = await response.json();
        
        // Load teams for dropdown
        await loadTeamsForDropdown();
        
        // Fill form with employee data
        document.getElementById('employeeId').value = employee.id;
        document.getElementById('vorname').value = employee.vorname;
        document.getElementById('name').value = employee.name;
        document.getElementById('personalnummer').value = employee.personalnummer;
        document.getElementById('email').value = employee.email || '';
        document.getElementById('geburtsdatum').value = employee.geburtsdatum ? employee.geburtsdatum.split('T')[0] : '';
        document.getElementById('teamId').value = employee.teamId || '';
        document.getElementById('isSpringer').checked = employee.isSpringer;
        document.getElementById('isFerienjobber').checked = employee.isFerienjobber;
        document.getElementById('isBrandmeldetechniker').checked = employee.isBrandmeldetechniker || false;
        document.getElementById('isBrandschutzbeauftragter').checked = employee.isBrandschutzbeauftragter || false;
        // TD qualification is now automatic based on BMT or BSB
        
        document.getElementById('employeeModalTitle').textContent = 'Mitarbeiter bearbeiten';
        document.getElementById('employeeModal').style.display = 'block';
    } catch (error) {
        alert(`Fehler: ${error.message}`);
    }
}

async function deleteEmployee(id, name) {
    if (!hasRole('Admin')) {
        alert('Nur Administratoren können Mitarbeiter löschen.');
        return;
    }
    
    if (!confirm(`Möchten Sie den Mitarbeiter "${name}" wirklich löschen?\n\nAchtung: Alle zugehörigen Schichten und Abwesenheiten werden ebenfalls gelöscht!`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/employees/${id}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (response.ok) {
            alert('Mitarbeiter erfolgreich gelöscht!');
            loadEmployees();
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an.');
        } else if (response.status === 403) {
            alert('Sie haben keine Berechtigung zum Löschen.');
        } else {
            alert('Fehler beim Löschen');
        }
    } catch (error) {
        alert(`Fehler: ${error.message}`);
    }
}

async function loadTeamsForDropdown() {
    try {
        const response = await fetch(`${API_BASE}/teams`);
        const teams = await response.json();
        
        const select = document.getElementById('teamId');
        select.innerHTML = '<option value="">Kein Team</option>';
        teams.forEach(team => {
            select.innerHTML += `<option value="${team.id}">${team.name}</option>`;
        });
    } catch (error) {
        console.error('Fehler beim Laden der Teams:', error);
    }
}

function closeEmployeeModal() {
    document.getElementById('employeeModal').style.display = 'none';
    document.getElementById('employeeForm').reset();
}

async function saveEmployee(event) {
    event.preventDefault();
    
    const id = document.getElementById('employeeId').value;
    const employee = {
        vorname: document.getElementById('vorname').value,
        name: document.getElementById('name').value,
        personalnummer: document.getElementById('personalnummer').value,
        email: document.getElementById('email').value || null,
        geburtsdatum: document.getElementById('geburtsdatum').value || null,
        teamId: document.getElementById('teamId').value ? parseInt(document.getElementById('teamId').value) : null,
        isSpringer: document.getElementById('isSpringer').checked,
        isFerienjobber: document.getElementById('isFerienjobber').checked,
        isBrandmeldetechniker: document.getElementById('isBrandmeldetechniker').checked,
        isBrandschutzbeauftragter: document.getElementById('isBrandschutzbeauftragter').checked
        // isTdQualified is calculated automatically on the server based on BMT or BSB
    };
    
    try {
        const url = id ? `${API_BASE}/employees/${id}` : `${API_BASE}/employees`;
        const method = id ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(employee)
        });
        
        if (response.ok) {
            alert(id ? 'Mitarbeiter erfolgreich aktualisiert!' : 'Mitarbeiter erfolgreich hinzugefügt!');
            closeEmployeeModal();
            loadEmployees();
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an.');
        } else if (response.status === 403) {
            alert('Sie haben keine Berechtigung für diese Aktion.');
        } else {
            const error = await response.json();
            alert(`Fehler beim Speichern: ${error.message || 'Unbekannter Fehler'}`);
        }
    } catch (error) {
        alert(`Fehler: ${error.message}`);
    }
}

// Statistics
async function loadStatistics() {
    const startDate = document.getElementById('statsStartDate').value;
    const endDate = document.getElementById('statsEndDate').value;
    
    const content = document.getElementById('statistics-content');
    content.innerHTML = '<p class="loading">Lade Statistiken...</p>';
    
    try {
        const response = await fetch(`${API_BASE}/statistics/dashboard?startDate=${startDate}&endDate=${endDate}`);
        const stats = await response.json();
        
        displayStatistics(stats);
    } catch (error) {
        content.innerHTML = `<p class="error">Fehler beim Laden: ${error.message}</p>`;
    }
}

function displayStatistics(stats) {
    const content = document.getElementById('statistics-content');
    
    let html = '<div class="statistics-grid">';
    
    // Work Hours
    html += '<div class="stat-card"><h3>⏱️ Arbeitsstunden</h3>';
    stats.employeeWorkHours.slice(0, 10).forEach(e => {
        html += `<div class="stat-item">
            <span>${e.employeeName}</span>
            <span>${e.totalHours.toFixed(1)}h (${e.shiftCount} Schichten)</span>
        </div>`;
    });
    html += '</div>';
    
    // Team Shift Distribution
    html += '<div class="stat-card"><h3>👥 Schichtverteilung pro Team</h3>';
    stats.teamShiftDistribution.forEach(t => {
        html += `<div class="stat-item"><strong>${t.teamName}</strong></div>`;
        Object.entries(t.shiftCounts).forEach(([code, count]) => {
            html += `<div class="stat-item">
                <span class="shift-badge shift-${code}">${code}</span>
                <span>${count}x</span>
            </div>`;
        });
    });
    html += '</div>';
    
    // Absence Days
    html += '<div class="stat-card"><h3>📅 Fehltage</h3>';
    stats.employeeAbsenceDays.slice(0, 10).forEach(e => {
        html += `<div class="stat-item">
            <span>${e.employeeName}</span>
            <span>${e.totalDays} Tage</span>
        </div>`;
    });
    html += '</div>';
    
    // Team Workload
    html += '<div class="stat-card"><h3>📊 Team Auslastung</h3>';
    stats.teamWorkload.forEach(t => {
        html += `<div class="stat-item">
            <span>${t.teamName}</span>
            <span>⌀ ${t.averageShiftsPerEmployee.toFixed(1)} Schichten/MA</span>
        </div>`;
    });
    html += '</div>';
    
    html += '</div>';
    content.innerHTML = html;
}


// Teams View Functions
async function loadTeams() {
    const content = document.getElementById('teams-content');
    content.innerHTML = '<p class="loading">Lade Teams...</p>';
    
    try {
        const response = await fetch(`${API_BASE}/teams`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const teams = await response.json();
            displayTeams(teams);
        } else {
            content.innerHTML = '<p class="error">Fehler beim Laden der Teams.</p>';
        }
    } catch (error) {
        console.error('Error loading teams:', error);
        content.innerHTML = '<p class="error">Fehler beim Laden der Teams.</p>';
    }
}

function displayTeams(teams) {
    const content = document.getElementById('teams-content');
    
    if (teams.length === 0) {
        content.innerHTML = '<p>Keine Teams vorhanden.</p>';
        return;
    }
    
    const canEdit = canEditEmployees();
    const isAdmin = hasRole('Admin');
    
    let html = '<div class="grid">';
    teams.forEach(team => {
        const virtualBadge = team.isVirtual ? '<span style="background: #999; color: white; padding: 2px 8px; border-radius: 3px; font-size: 0.8em; margin-left: 8px;">Virtuell</span>' : '';
        const teamName = escapeHtml(team.name);
        const teamDesc = escapeHtml(team.description || 'Keine Beschreibung');
        const teamEmail = escapeHtml(team.email || 'Nicht angegeben');
        
        html += `
            <div class="card">
                <h3>${teamName}${virtualBadge}</h3>
                <p>${teamDesc}</p>
                <p><strong>E-Mail:</strong> ${teamEmail}</p>
                <p><strong>Mitarbeiter:</strong> ${team.employeeCount || 0}</p>
                ${canEdit ? `
                    <div class="card-actions">
                        <button onclick="editTeam(${team.id})" class="btn-small btn-edit">✏️ Bearbeiten</button>
                        ${isAdmin ? `<button onclick="deleteTeam(${team.id}, ${JSON.stringify(team.name)})" class="btn-small btn-delete">🗑️ Löschen</button>` : ''}
                    </div>
                ` : ''}
            </div>
        `;
    });
    html += '</div>';
    content.innerHTML = html;
}

async function showAddTeamModal() {
    if (!canEditEmployees()) {
        alert('Sie haben keine Berechtigung, Teams hinzuzufügen.');
        return;
    }
    
    document.getElementById('teamForm').reset();
    document.getElementById('teamId').value = '';
    document.getElementById('teamModalTitle').textContent = 'Team hinzufügen';
    document.getElementById('teamModal').style.display = 'block';
}

async function editTeam(id) {
    if (!canEditEmployees()) {
        alert('Sie haben keine Berechtigung, Teams zu bearbeiten.');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/teams/${id}`, {
            credentials: 'include'
        });
        if (!response.ok) {
            alert('Fehler beim Laden der Teamdaten');
            return;
        }
        
        const team = await response.json();
        
        document.getElementById('teamId').value = team.id;
        document.getElementById('teamName').value = team.name;
        document.getElementById('teamDescription').value = team.description || '';
        document.getElementById('teamEmail').value = team.email || '';
        document.getElementById('teamIsVirtual').checked = team.isVirtual || false;
        
        document.getElementById('teamModalTitle').textContent = 'Team bearbeiten';
        document.getElementById('teamModal').style.display = 'block';
    } catch (error) {
        alert(`Fehler: ${error.message}`);
    }
}

async function deleteTeam(id, name) {
    if (!hasRole('Admin')) {
        alert('Nur Administratoren können Teams löschen.');
        return;
    }
    
    if (!confirm(`Möchten Sie das Team "${name}" wirklich löschen?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/teams/${id}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (response.ok) {
            alert('Team erfolgreich gelöscht!');
            loadTeams();
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an.');
        } else if (response.status === 403) {
            alert('Sie haben keine Berechtigung zum Löschen.');
        } else {
            alert('Fehler beim Löschen');
        }
    } catch (error) {
        alert(`Fehler: ${error.message}`);
    }
}

function closeTeamModal() {
    document.getElementById('teamModal').style.display = 'none';
    document.getElementById('teamForm').reset();
}

async function saveTeam(event) {
    event.preventDefault();
    
    const id = document.getElementById('teamId').value;
    const team = {
        name: document.getElementById('teamName').value,
        description: document.getElementById('teamDescription').value || null,
        email: document.getElementById('teamEmail').value || null,
        isVirtual: document.getElementById('teamIsVirtual').checked
    };
    
    try {
        const url = id ? `${API_BASE}/teams/${id}` : `${API_BASE}/teams`;
        const method = id ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(team)
        });
        
        if (response.ok) {
            alert(id ? 'Team erfolgreich aktualisiert!' : 'Team erfolgreich hinzugefügt!');
            closeTeamModal();
            loadTeams();
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an.');
        } else if (response.status === 403) {
            alert('Sie haben keine Berechtigung für diese Aktion.');
        } else {
            alert('Fehler beim Speichern');
        }
    } catch (error) {
        alert(`Fehler: ${error.message}`);
    }
}

// Vacation Management Functions
// Vacation Management Functions (no longer needed, vacations are separate)
async function loadVacationRequests(filter = 'all') {
    const content = document.getElementById('vacation-requests-content');
    content.innerHTML = '<p class="loading">Lade Urlaubsanträge...</p>';
    
    try {
        let url = `${API_BASE}/vacationrequests`;
        if (filter === 'pending') {
            url += '/pending';
        } else if (filter === 'my' && currentUser) {
            // Load only current user's requests - for now load all and filter
            url = `${API_BASE}/vacationrequests`;
        }
        
        const response = await fetch(url, {
            credentials: 'include'
        });
        
        if (response.ok) {
            let requests = await response.json();
            // Filter for 'my' requests if needed
            if (filter === 'my' && currentUser) {
                requests = requests.filter(r => r.employeeEmail === currentUser.email);
            }
            displayVacationRequests(requests);
        } else if (response.status === 401) {
            content.innerHTML = '<p class="error">Bitte melden Sie sich an.</p>';
        } else {
            content.innerHTML = '<p class="error">Fehler beim Laden der Urlaubsanträge.</p>';
        }
    } catch (error) {
        console.error('Error loading vacation requests:', error);
        content.innerHTML = '<p class="error">Fehler beim Laden der Urlaubsanträge.</p>';
    }
}

function displayVacationRequests(requests) {
    const content = document.getElementById('vacation-requests-content');
    
    if (requests.length === 0) {
        content.innerHTML = '<p>Keine Urlaubsanträge vorhanden.</p>';
        return;
    }
    
    const canProcess = hasRole('Admin') || hasRole('Disponent');
    
    let html = '<table class="data-table"><thead><tr><th>Mitarbeiter</th><th>Von</th><th>Bis</th><th>Status</th><th>Notizen</th><th>Erstellt</th>';
    if (canProcess) html += '<th>Aktionen</th>';
    html += '</tr></thead><tbody>';
    
    requests.forEach(req => {
        const statusClass = req.status === 'Genehmigt' ? 'success' : req.status === 'NichtGenehmigt' ? 'danger' : 'warning';
        html += `
            <tr>
                <td>${req.employeeName || 'Unbekannt'}</td>
                <td>${new Date(req.startDate).toLocaleDateString('de-DE')}</td>
                <td>${new Date(req.endDate).toLocaleDateString('de-DE')}</td>
                <td><span class="badge ${statusClass}">${req.status}</span></td>
                <td>${req.notes || '-'}</td>
                <td>${new Date(req.createdAt).toLocaleDateString('de-DE')}</td>`;
        
        if (canProcess && req.status === 'InBearbeitung') {
            html += `
                <td>
                    <button onclick="processVacationRequest(${req.id}, 'Genehmigt')" class="btn-small btn-success">✓ Genehmigen</button>
                    <button onclick="processVacationRequest(${req.id}, 'NichtGenehmigt')" class="btn-small btn-danger">✗ Ablehnen</button>
                </td>`;
        } else if (canProcess) {
            html += '<td>-</td>';
        }
        
        html += '</tr>';
    });
    html += '</tbody></table>';
    content.innerHTML = html;
}

async function showAddVacationRequestModal() {
    // Load employees for dropdown
    try {
        const response = await fetch(`${API_BASE}/employees`);
        if (response.ok) {
            const employees = await response.json();
            const select = document.getElementById('vacationEmployeeId');
            select.innerHTML = '<option value="">Mitarbeiter wählen...</option>';
            employees.forEach(emp => {
                const teamInfo = emp.teamName ? ` (${emp.teamName})` : '';
                const funktionInfo = emp.funktion ? ` - ${emp.funktion}` : '';
                select.innerHTML += `<option value="${emp.id}">${emp.vorname} ${emp.name} (PN: ${emp.personalnummer})${teamInfo}${funktionInfo}</option>`;
            });
        }
    } catch (error) {
        console.error('Error loading employees:', error);
    }
    
    document.getElementById('vacationRequestForm').reset();
    document.getElementById('vacationRequestModal').style.display = 'block';
}

function closeVacationRequestModal() {
    document.getElementById('vacationRequestModal').style.display = 'none';
    document.getElementById('vacationRequestForm').reset();
}

async function saveVacationRequest(event) {
    event.preventDefault();
    
    const request = {
        employeeId: parseInt(document.getElementById('vacationEmployeeId').value),
        startDate: document.getElementById('vacationStartDate').value,
        endDate: document.getElementById('vacationEndDate').value,
        notes: document.getElementById('vacationNotes').value || null
    };
    
    try {
        const response = await fetch(`${API_BASE}/vacationrequests`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(request)
        });
        
        if (response.ok) {
            alert('Urlaubsantrag erfolgreich eingereicht!');
            closeVacationRequestModal();
            loadVacationRequests('all');
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an.');
        } else {
            alert('Fehler beim Speichern des Urlaubsantrags.');
        }
    } catch (error) {
        alert(`Fehler: ${error.message}`);
    }
}

async function processVacationRequest(id, status) {
    const response = prompt(`${status === 'Genehmigt' ? 'Genehmigung' : 'Ablehnung'} - Optionale Antwort:`);
    
    try {
        const result = await fetch(`${API_BASE}/vacationrequests/${id}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                status: status,
                disponentResponse: response || null
            })
        });
        
        if (result.ok) {
            alert(`Urlaubsantrag wurde ${status === 'Genehmigt' ? 'genehmigt' : 'abgelehnt'}!`);
            loadVacationRequests('pending');
        } else if (result.status === 401) {
            alert('Bitte melden Sie sich an.');
        } else if (result.status === 403) {
            alert('Sie haben keine Berechtigung für diese Aktion.');
        } else {
            alert('Fehler beim Verarbeiten des Antrags.');
        }
    } catch (error) {
        alert(`Fehler: ${error.message}`);
    }
}

// Absence Management Tab Switching
function switchAbsenceTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab content
    const selectedTab = document.getElementById(`${tabName}-tab`);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Activate corresponding button
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach((btn, index) => {
        if ((tabName === 'vacation' && index === 0) ||
            (tabName === 'sick' && index === 1) ||
            (tabName === 'training' && index === 2)) {
            btn.classList.add('active');
        }
    });
    
    // Load content for the selected tab
    if (tabName === 'vacation') {
        loadVacationRequests('all');
    } else if (tabName === 'sick') {
        loadAbsences('AU');
    } else if (tabName === 'training') {
        loadAbsences('L');
    }
}

// Load Absences (AU or L)
async function loadAbsences(type) {
    const contentId = type === 'AU' ? 'sick-absences-content' : 'training-absences-content';
    const content = document.getElementById(contentId);
    content.innerHTML = '<p class="loading">Lade Abwesenheiten...</p>';
    
    try {
        const response = await fetch(`${API_BASE}/absences`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const absences = await response.json();
            // Filter by type
            const filteredAbsences = absences.filter(a => {
                if (type === 'AU') {
                    return a.type === 'Krank / AU' || a.type === 'Krank';
                } else if (type === 'L') {
                    return a.type === 'Lehrgang';
                }
                return false;
            });
            displayAbsences(filteredAbsences, type);
        } else {
            content.innerHTML = '<p class="error">Fehler beim Laden der Abwesenheiten.</p>';
        }
    } catch (error) {
        console.error('Error loading absences:', error);
        content.innerHTML = '<p class="error">Fehler beim Laden der Abwesenheiten.</p>';
    }
}

// Display Absences Table
function displayAbsences(absences, type) {
    const contentId = type === 'AU' ? 'sick-absences-content' : 'training-absences-content';
    const content = document.getElementById(contentId);
    
    if (absences.length === 0) {
        const typeName = type === 'AU' ? 'Arbeitsunfähigkeiten' : 'Lehrgänge';
        content.innerHTML = `<p>Keine ${typeName} vorhanden.</p>`;
        return;
    }
    
    const canDelete = hasRole('Admin') || hasRole('Disponent');
    
    let html = '<table class="data-table"><thead><tr>';
    html += '<th>Mitarbeiter</th>';
    html += '<th>Von</th>';
    html += '<th>Bis</th>';
    html += '<th>Notizen</th>';
    html += '<th>Erstellt</th>';
    if (canDelete) {
        html += '<th>Aktionen</th>';
    }
    html += '</tr></thead><tbody>';
    
    absences.forEach(absence => {
        html += '<tr>';
        html += `<td>${absence.employeeName || 'Unbekannt'}</td>`;
        html += `<td>${new Date(absence.startDate).toLocaleDateString('de-DE')}</td>`;
        html += `<td>${new Date(absence.endDate).toLocaleDateString('de-DE')}</td>`;
        html += `<td>${absence.notes || '-'}</td>`;
        // Only show creation date if available in the API response, otherwise hide column
        html += `<td>${absence.createdAt ? new Date(absence.createdAt).toLocaleDateString('de-DE') : '-'}</td>`;
        
        if (canDelete) {
            html += `<td><button onclick="deleteAbsence(${absence.id}, '${type}')" class="btn-small btn-danger">Löschen</button></td>`;
        }
        
        html += '</tr>';
    });
    html += '</tbody></table>';
    content.innerHTML = html;
}

// Show Add Absence Modal
async function showAddAbsenceModal(type) {
    // Load employees for dropdown
    try {
        const response = await fetch(`${API_BASE}/employees`);
        if (response.ok) {
            const employees = await response.json();
            const select = document.getElementById('absenceEmployeeId');
            select.innerHTML = '<option value="">Mitarbeiter wählen...</option>';
            employees.forEach(emp => {
                const teamInfo = emp.teamName ? ` (${emp.teamName})` : '';
                const funktionInfo = emp.funktion ? ` - ${emp.funktion}` : '';
                select.innerHTML += `<option value="${emp.id}">${emp.vorname} ${emp.name} (PN: ${emp.personalnummer})${teamInfo}${funktionInfo}</option>`;
            });
        }
    } catch (error) {
        console.error('Error loading employees:', error);
    }
    
    // Set modal title and type
    const modalTitle = document.getElementById('absenceModalTitle');
    if (type === 'AU') {
        modalTitle.textContent = 'Arbeitsunfähigkeit (AU) erfassen';
    } else if (type === 'L') {
        modalTitle.textContent = 'Lehrgang erfassen';
    }
    
    document.getElementById('absenceType').value = type;
    document.getElementById('absenceForm').reset();
    document.getElementById('absenceType').value = type; // Reset clears it, so set again
    document.getElementById('absenceModal').style.display = 'block';
}

// Close Absence Modal
function closeAbsenceModal() {
    document.getElementById('absenceModal').style.display = 'none';
    document.getElementById('absenceForm').reset();
}

// Save Absence
async function saveAbsence(event) {
    event.preventDefault();
    
    const type = document.getElementById('absenceType').value;
    const typeValue = type === 'AU' ? ABSENCE_TYPES.AU : ABSENCE_TYPES.L;
    
    const absence = {
        employeeId: parseInt(document.getElementById('absenceEmployeeId').value),
        type: typeValue,
        startDate: document.getElementById('absenceStartDate').value,
        endDate: document.getElementById('absenceEndDate').value,
        notes: document.getElementById('absenceNotes').value || null
    };
    
    try {
        const response = await fetch(`${API_BASE}/absences`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(absence)
        });
        
        if (response.ok) {
            alert('Abwesenheit erfolgreich erfasst!');
            closeAbsenceModal();
            loadAbsences(type);
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an.');
        } else if (response.status === 403) {
            alert('Sie haben keine Berechtigung für diese Aktion.');
        } else {
            alert('Fehler beim Speichern der Abwesenheit.');
        }
    } catch (error) {
        alert(`Fehler: ${error.message}`);
    }
}

// Delete Absence
async function deleteAbsence(id, type) {
    if (!confirm('Möchten Sie diese Abwesenheit wirklich löschen?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/absences/${id}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (response.ok) {
            alert('Abwesenheit erfolgreich gelöscht!');
            loadAbsences(type);
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an.');
        } else if (response.status === 403) {
            alert('Sie haben keine Berechtigung für diese Aktion.');
        } else {
            alert('Fehler beim Löschen der Abwesenheit.');
        }
    } catch (error) {
        alert(`Fehler: ${error.message}`);
    }
}

// Shift Exchange Functions
async function loadShiftExchanges(filter = 'available') {
    const content = document.getElementById('shift-exchanges-content');
    content.innerHTML = '<p class="loading">Lade Diensttausch-Angebote...</p>';
    
    try {
        let url = `${API_BASE}/shiftexchanges/${filter}`;
        if (filter === 'my') {
            // Load all and filter on client side
            url = `${API_BASE}/shiftexchanges/available`;
        }
        
        const response = await fetch(url, {
            credentials: 'include'
        });
        
        if (response.ok) {
            let exchanges = await response.json();
            displayShiftExchanges(exchanges, filter);
        } else if (response.status === 401) {
            content.innerHTML = '<p class="error">Bitte melden Sie sich an.</p>';
        } else {
            content.innerHTML = '<p class="error">Fehler beim Laden der Diensttausch-Angebote.</p>';
        }
    } catch (error) {
        console.error('Error loading shift exchanges:', error);
        content.innerHTML = '<p class="error">Fehler beim Laden der Diensttausch-Angebote.</p>';
    }
}

function displayShiftExchanges(exchanges, filter) {
    const content = document.getElementById('shift-exchanges-content');
    
    if (exchanges.length === 0) {
        content.innerHTML = '<p>Keine Diensttausch-Angebote vorhanden.</p>';
        return;
    }
    
    const canProcess = hasRole('Admin') || hasRole('Disponent');
    
    let html = '<table class="data-table"><thead><tr><th>Anbieter</th><th>Schicht-Datum</th><th>Schichttyp</th><th>Status</th><th>Grund</th><th>Erstellt</th>';
    if (canProcess || filter === 'available') html += '<th>Aktionen</th>';
    html += '</tr></thead><tbody>';
    
    exchanges.forEach(ex => {
        const statusClass = ex.status === 'Genehmigt' ? 'success' : ex.status === 'Abgelehnt' ? 'danger' : 'warning';
        html += `
            <tr>
                <td>${ex.offeringEmployeeName || 'Unbekannt'}</td>
                <td>${new Date(ex.shiftDate).toLocaleDateString('de-DE')}</td>
                <td><span class="shift-badge shift-${ex.shiftTypeCode}">${ex.shiftTypeCode}</span></td>
                <td><span class="badge ${statusClass}">${ex.status}</span></td>
                <td>${ex.offeringReason || '-'}</td>
                <td>${new Date(ex.createdAt).toLocaleDateString('de-DE')}</td>`;
        
        if (filter === 'available' && ex.status === 'Angeboten') {
            html += `
                <td>
                    <button onclick="requestShiftExchange(${ex.id})" class="btn-small btn-primary">Anfragen</button>
                </td>`;
        } else if (canProcess && ex.status === 'Angefragt') {
            html += `
                <td>
                    <button onclick="processShiftExchange(${ex.id}, 'Genehmigt')" class="btn-small btn-success">✓ Genehmigen</button>
                    <button onclick="processShiftExchange(${ex.id}, 'Abgelehnt')" class="btn-small btn-danger">✗ Ablehnen</button>
                </td>`;
        } else {
            html += '<td>-</td>';
        }
        
        html += '</tr>';
    });
    html += '</tbody></table>';
    content.innerHTML = html;
}

async function showOfferShiftExchangeModal() {
    // Load employees for dropdown
    try {
        const empResponse = await fetch(`${API_BASE}/employees`);
        if (empResponse.ok) {
            const employees = await empResponse.json();
            const select = document.getElementById('exchangeEmployeeId');
            select.innerHTML = '<option value="">Mitarbeiter wählen...</option>';
            employees.forEach(emp => {
                select.innerHTML += `<option value="${emp.id}">${emp.vorname} ${emp.name}</option>`;
            });
        }
        
        // Setup event listener for date/employee change to load shifts
        document.getElementById('exchangeDate').onchange = loadShiftsForExchange;
        document.getElementById('exchangeEmployeeId').onchange = loadShiftsForExchange;
        
    } catch (error) {
        console.error('Error loading employees:', error);
    }
    
    document.getElementById('shiftExchangeForm').reset();
    document.getElementById('shiftExchangeModal').style.display = 'block';
}

async function loadShiftsForExchange() {
    const date = document.getElementById('exchangeDate').value;
    const employeeId = document.getElementById('exchangeEmployeeId').value;
    const select = document.getElementById('exchangeShiftId');
    
    if (!date || !employeeId) {
        select.innerHTML = '<option value="">Zuerst Datum und Mitarbeiter wählen...</option>';
        return;
    }
    
    try {
        // Load schedule for that date
        const response = await fetch(`${API_BASE}/shifts/schedule?startDate=${date}&endDate=${date}`);
        if (response.ok) {
            const data = await response.json();
            const shifts = data.assignments.filter(a => 
                a.employeeId == employeeId && 
                a.date.startsWith(date)
            );
            
            select.innerHTML = '';
            if (shifts.length === 0) {
                select.innerHTML = '<option value="">Keine Schichten für diesen Tag gefunden</option>';
            } else {
                shifts.forEach(shift => {
                    select.innerHTML += `<option value="${shift.id}">${shift.shiftTypeName} (${shift.shiftTypeCode})</option>`;
                });
            }
        }
    } catch (error) {
        console.error('Error loading shifts:', error);
        select.innerHTML = '<option value="">Fehler beim Laden der Schichten</option>';
    }
}

function closeShiftExchangeModal() {
    document.getElementById('shiftExchangeModal').style.display = 'none';
    document.getElementById('shiftExchangeForm').reset();
}

async function saveShiftExchange(event) {
    event.preventDefault();
    
    const exchange = {
        shiftAssignmentId: parseInt(document.getElementById('exchangeShiftId').value),
        offeringReason: document.getElementById('exchangeReason').value || null
    };
    
    try {
        const response = await fetch(`${API_BASE}/shiftexchanges`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(exchange)
        });
        
        if (response.ok) {
            alert('Diensttausch erfolgreich angeboten!');
            closeShiftExchangeModal();
            loadShiftExchanges('available');
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an.');
        } else {
            alert('Fehler beim Anbieten des Diensttauschs.');
        }
    } catch (error) {
        alert(`Fehler: ${error.message}`);
    }
}

async function requestShiftExchange(id) {
    if (!currentUser) {
        alert('Bitte melden Sie sich an.');
        return;
    }
    
    // For simplicity, use current user's associated employee
    // In a real scenario, you'd need to properly map user to employee
    const employeeId = prompt('Bitte geben Sie Ihre Mitarbeiter-ID ein:');
    if (!employeeId) return;
    
    try {
        const response = await fetch(`${API_BASE}/shiftexchanges/${id}/request`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                requestingEmployeeId: parseInt(employeeId)
            })
        });
        
        if (response.ok) {
            alert('Diensttausch erfolgreich angefragt! Warten Sie auf die Genehmigung durch den Disponenten.');
            loadShiftExchanges('available');
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an.');
        } else {
            alert('Fehler beim Anfragen des Diensttauschs.');
        }
    } catch (error) {
        alert(`Fehler: ${error.message}`);
    }
}

async function processShiftExchange(id, status) {
    const notes = prompt(`${status === 'Genehmigt' ? 'Genehmigung' : 'Ablehnung'} - Optionale Notizen:`);
    
    try {
        const response = await fetch(`${API_BASE}/shiftexchanges/${id}/process`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                status: status,
                disponentNotes: notes || null
            })
        });
        
        if (response.ok) {
            alert(`Diensttausch wurde ${status === 'Genehmigt' ? 'genehmigt' : 'abgelehnt'}!`);
            loadShiftExchanges('pending');
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an.');
        } else if (response.status === 403) {
            alert('Sie haben keine Berechtigung für diese Aktion.');
        } else {
            alert('Fehler beim Verarbeiten des Tauschs.');
        }
    } catch (error) {
        alert(`Fehler: ${error.message}`);
    }
}

// Admin View Functions
async function loadAdminView() {
    loadUsers();
    loadEmailSettings();
}

async function loadUsers() {
    const content = document.getElementById('users-content');
    content.innerHTML = '<p class="loading">Lade Benutzer...</p>';
    
    try {
        const response = await fetch(`${API_BASE}/auth/users`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const users = await response.json();
            displayUsers(users);
        } else if (response.status === 401) {
            content.innerHTML = '<p class="error">Bitte melden Sie sich an.</p>';
        } else if (response.status === 403) {
            content.innerHTML = '<p class="error">Sie haben keine Berechtigung, Benutzer anzuzeigen.</p>';
        } else {
            content.innerHTML = '<p class="error">Fehler beim Laden der Benutzer.</p>';
        }
    } catch (error) {
        console.error('Error loading users:', error);
        content.innerHTML = '<p class="error">Fehler beim Laden der Benutzer.</p>';
    }
}

function displayUsers(users) {
    const content = document.getElementById('users-content');
    
    if (!users || users.length === 0) {
        content.innerHTML = '<p>Keine Benutzer gefunden.</p>';
        return;
    }
    
    let html = '<table class="data-table"><thead><tr>';
    html += '<th>Name</th><th>E-Mail</th><th>Rolle(n)</th><th>Status</th><th>Aktionen</th>';
    html += '</tr></thead><tbody>';
    
    users.forEach(user => {
        const isLocked = user.lockoutEnd && new Date(user.lockoutEnd) > new Date();
        const statusBadge = isLocked 
            ? '<span class="badge badge-error">Gesperrt</span>' 
            : '<span class="badge badge-success">Aktiv</span>';
        
        html += '<tr>';
        html += `<td>${escapeHtml(user.fullName || 'N/A')}</td>`;
        html += `<td>${escapeHtml(user.email || 'N/A')}</td>`;
        html += `<td>${escapeHtml(user.roles.join(', '))}</td>`;
        html += `<td>${statusBadge}</td>`;
        html += `<td>`;
        html += `<button onclick="editUser('${escapeHtml(user.id)}')" class="btn-small btn-primary">Bearbeiten</button> `;
        html += `<button onclick="deleteUser('${escapeHtml(user.id)}', '${escapeHtml(user.email)}')" class="btn-small btn-danger">Löschen</button>`;
        html += `</td>`;
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    content.innerHTML = html;
}

async function editUser(userId) {
    try {
        const response = await fetch(`${API_BASE}/auth/users/${userId}`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const user = await response.json();
            
            document.getElementById('userId').value = user.id;
            document.getElementById('userFullName').value = user.fullName;
            document.getElementById('userEmail').value = user.email;
            document.getElementById('userRole').value = user.roles[0] || 'Mitarbeiter';
            document.getElementById('userModalTitle').textContent = 'Benutzer bearbeiten';
            document.getElementById('passwordGroup').style.display = 'none';
            document.getElementById('userPassword').required = false;
            document.getElementById('userModal').style.display = 'block';
        } else {
            alert('Fehler beim Laden des Benutzers.');
        }
    } catch (error) {
        console.error('Error loading user:', error);
        alert('Fehler beim Laden des Benutzers.');
    }
}

async function deleteUser(userId, userEmail) {
    if (!confirm(`Möchten Sie den Benutzer "${userEmail}" wirklich löschen?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/auth/users/${userId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (response.ok) {
            alert('Benutzer erfolgreich gelöscht!');
            loadUsers();
        } else {
            const error = await response.json();
            alert(`Fehler beim Löschen: ${error.error || 'Unbekannter Fehler'}`);
        }
    } catch (error) {
        console.error('Error deleting user:', error);
        alert(`Fehler: ${error.message}`);
    }
}

async function showAddUserModal() {
    if (!hasRole('Admin')) {
        alert('Nur Administratoren können Benutzer hinzufügen.');
        return;
    }
    
    document.getElementById('userForm').reset();
    document.getElementById('userId').value = '';
    document.getElementById('userModalTitle').textContent = 'Benutzer hinzufügen';
    document.getElementById('passwordGroup').style.display = 'block';
    document.getElementById('userPassword').required = true;
    document.getElementById('userModal').style.display = 'block';
}

function closeUserModal() {
    document.getElementById('userModal').style.display = 'none';
    document.getElementById('userForm').reset();
}

async function saveUser(event) {
    event.preventDefault();
    
    const userId = document.getElementById('userId').value;
    const isEdit = userId !== '';
    
    const userData = {
        fullName: document.getElementById('userFullName').value,
        email: document.getElementById('userEmail').value,
        role: document.getElementById('userRole').value
    };
    
    // Only include password for new users
    if (!isEdit) {
        userData.password = document.getElementById('userPassword').value;
    }
    
    try {
        const url = isEdit ? `${API_BASE}/auth/users/${userId}` : `${API_BASE}/auth/register`;
        const method = isEdit ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(userData)
        });
        
        if (response.ok) {
            alert(isEdit ? 'Benutzer erfolgreich aktualisiert!' : 'Benutzer erfolgreich erstellt!');
            closeUserModal();
            loadUsers();
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an.');
        } else if (response.status === 403) {
            alert('Sie haben keine Berechtigung für diese Aktion.');
        } else {
            const error = await response.json();
            alert(`Fehler beim ${isEdit ? 'Aktualisieren' : 'Erstellen'}: ${error.error || 'Unbekannter Fehler'}`);
        }
    } catch (error) {
        alert(`Fehler: ${error.message}`);
    }
}

async function loadEmailSettings() {
    const content = document.getElementById('email-settings-content');
    
    try {
        const response = await fetch(`${API_BASE}/emailsettings/active`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const settings = await response.json();
            displayEmailSettings(settings);
        } else if (response.status === 404) {
            content.innerHTML = `
                <div class="info-box">
                    <p><strong>Aktive Konfiguration:</strong> Noch keine E-Mail-Einstellungen konfiguriert.</p>
                    <p>Klicken Sie auf "E-Mail-Einstellungen bearbeiten" um eine neue Konfiguration zu erstellen.</p>
                </div>
            `;
        } else {
            content.innerHTML = `
                <div class="info-box">
                    <p><strong>Aktive Konfiguration:</strong> Noch keine E-Mail-Einstellungen konfiguriert.</p>
                    <p>Klicken Sie auf "E-Mail-Einstellungen bearbeiten" um eine neue Konfiguration zu erstellen.</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading email settings:', error);
        content.innerHTML = `
            <div class="info-box">
                <p><strong>Aktive Konfiguration:</strong> Noch keine E-Mail-Einstellungen konfiguriert.</p>
                <p>Klicken Sie auf "E-Mail-Einstellungen bearbeiten" um eine neue Konfiguration zu erstellen.</p>
            </div>
        `;
    }
}

function displayEmailSettings(settings) {
    const content = document.getElementById('email-settings-content');
    content.innerHTML = `
        <div class="info-box">
            <p><strong>SMTP Server:</strong> ${settings.smtpServer}:${settings.smtpPort}</p>
            <p><strong>Protokoll:</strong> ${settings.protocol}</p>
            <p><strong>Sicherheit:</strong> ${settings.securityProtocol}</p>
            <p><strong>Absender:</strong> ${settings.senderEmail} (${settings.senderName || 'Kein Name'})</p>
            <p><strong>Authentifizierung:</strong> ${settings.requiresAuthentication ? 'Ja' : 'Nein'}</p>
            ${settings.requiresAuthentication ? `<p><strong>Benutzername:</strong> ${settings.username}</p>` : ''}
            <p><strong>Status:</strong> <span class="badge badge-success">Aktiv</span></p>
        </div>
    `;
}

async function showEmailSettingsModal() {
    if (!hasRole('Admin')) {
        alert('Nur Administratoren können E-Mail-Einstellungen bearbeiten.');
        return;
    }
    
    // Try to load existing settings
    try {
        const response = await fetch(`${API_BASE}/emailsettings/active`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const settings = await response.json();
            // Fill form with existing settings
            document.getElementById('smtpServer').value = settings.smtpServer || '';
            document.getElementById('smtpPort').value = settings.smtpPort || 587;
            document.getElementById('smtpProtocol').value = settings.protocol || 'SMTP';
            document.getElementById('smtpSecurity').value = settings.securityProtocol || 'STARTTLS';
            document.getElementById('requiresAuth').checked = settings.requiresAuthentication !== false;
            document.getElementById('smtpUsername').value = settings.username || '';
            document.getElementById('senderEmail').value = settings.senderEmail || '';
            document.getElementById('senderName').value = settings.senderName || '';
            document.getElementById('replyToEmail').value = settings.replyToEmail || '';
            // Don't fill password for security
        } else {
            // New settings, use defaults
            document.getElementById('emailSettingsForm').reset();
        }
    } catch (error) {
        console.error('Error loading email settings:', error);
        document.getElementById('emailSettingsForm').reset();
    }
    
    // Setup auth toggle
    document.getElementById('requiresAuth').onchange = function() {
        document.getElementById('authFields').style.display = this.checked ? 'block' : 'none';
    };
    document.getElementById('authFields').style.display = document.getElementById('requiresAuth').checked ? 'block' : 'none';
    
    document.getElementById('emailSettingsModal').style.display = 'block';
}

function closeEmailSettingsModal() {
    document.getElementById('emailSettingsModal').style.display = 'none';
    document.getElementById('emailSettingsForm').reset();
}

async function saveEmailSettings(event) {
    event.preventDefault();
    
    const settings = {
        smtpServer: document.getElementById('smtpServer').value,
        smtpPort: parseInt(document.getElementById('smtpPort').value),
        protocol: document.getElementById('smtpProtocol').value,
        securityProtocol: document.getElementById('smtpSecurity').value,
        requiresAuthentication: document.getElementById('requiresAuth').checked,
        username: document.getElementById('smtpUsername').value || null,
        password: document.getElementById('smtpPassword').value || null,
        senderEmail: document.getElementById('senderEmail').value,
        senderName: document.getElementById('senderName').value,
        replyToEmail: document.getElementById('replyToEmail').value || null
    };
    
    try {
        const response = await fetch(`${API_BASE}/emailsettings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(settings)
        });
        
        if (response.ok) {
            alert('E-Mail-Einstellungen erfolgreich gespeichert!');
            closeEmailSettingsModal();
            loadEmailSettings();
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an.');
        } else if (response.status === 403) {
            alert('Sie haben keine Berechtigung für diese Aktion.');
        } else {
            alert('Fehler beim Speichern der E-Mail-Einstellungen.');
        }
    } catch (error) {
        alert(`Fehler: ${error.message}`);
    }
}

async function testEmailSettings() {
    alert('Test-E-Mail Funktion ist vorbereitet.\n\nIn der Produktion würde hier eine Test-E-Mail an die konfigurierte Adresse gesendet.');
}

function saveGlobalSettings() {
    const maxHoursMonth = document.getElementById('setting-max-hours-month').value;
    const maxHoursWeek = document.getElementById('setting-max-hours-week').value;
    const maxConsecutiveShifts = document.getElementById('setting-max-consecutive-shifts').value;
    const maxConsecutiveNights = document.getElementById('setting-max-consecutive-nights').value;
    
    // Store in localStorage for now (in production, these would be saved to a backend configuration)
    localStorage.setItem('maxHoursMonth', maxHoursMonth);
    localStorage.setItem('maxHoursWeek', maxHoursWeek);
    localStorage.setItem('maxConsecutiveShifts', maxConsecutiveShifts);
    localStorage.setItem('maxConsecutiveNights', maxConsecutiveNights);
    
    alert(`Globale Einstellungen gespeichert:\n• Max Stunden/Monat: ${maxHoursMonth}\n• Max Stunden/Woche: ${maxHoursWeek}\n• Max aufeinanderfolgende Schichten: ${maxConsecutiveShifts}\n• Max aufeinanderfolgende Nachtschichten: ${maxConsecutiveNights}\n\nHinweis: Diese Einstellungen werden lokal im Browser gespeichert.`);
}

// Helper function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Shift assignment editing functions
let allShiftTypes = [];
let allShifts = [];
let cachedEmployees = [];

async function loadShiftTypes() {
    try {
        const response = await fetch(`${API_BASE}/shifttypes`, {
            credentials: 'include'
        });
        if (response.ok) {
            allShiftTypes = await response.json();
        }
    } catch (error) {
        console.error('Error loading shift types:', error);
    }
}

async function editShiftAssignment(shiftId) {
    if (!canPlanShifts()) {
        alert('Sie haben keine Berechtigung, Schichten zu bearbeiten.');
        return;
    }

    // Find the shift in the cached data
    const shift = allShifts.find(s => s.id === shiftId);
    if (!shift) {
        alert('Schicht nicht gefunden.');
        return;
    }

    // Load employees and shift types if not already loaded
    await loadEmployees();
    if (allShiftTypes.length === 0) {
        await loadShiftTypes();
    }

    // Populate modal
    document.getElementById('editShiftId').value = shift.id;
    document.getElementById('editShiftEmployeeId').value = shift.employeeId;
    document.getElementById('editShiftDate').value = shift.date.split('T')[0];
    document.getElementById('editShiftTypeId').value = shift.shiftTypeId;
    document.getElementById('editShiftIsFixed').checked = shift.isFixed || false;
    document.getElementById('editShiftNotes').value = shift.notes || '';
    
    // Populate employee dropdown
    const employeeSelect = document.getElementById('editShiftEmployeeId');
    employeeSelect.innerHTML = '<option value="">Mitarbeiter wählen...</option>';
    cachedEmployees.forEach(emp => {
        const option = document.createElement('option');
        option.value = emp.id;
        const teamInfo = emp.teamName ? ` (${emp.teamName})` : '';
        const funktionInfo = emp.funktion ? ` - ${emp.funktion}` : '';
        option.textContent = `${emp.vorname} ${emp.name} (PN: ${emp.personalnummer})${teamInfo}${funktionInfo}`;
        employeeSelect.appendChild(option);
    });
    employeeSelect.value = shift.employeeId;

    // Populate shift type dropdown
    const shiftTypeSelect = document.getElementById('editShiftTypeId');
    shiftTypeSelect.innerHTML = '<option value="">Schichttyp wählen...</option>';
    allShiftTypes.forEach(type => {
        const option = document.createElement('option');
        option.value = type.id;
        option.textContent = `${type.name} (${type.code})`;
        shiftTypeSelect.appendChild(option);
    });
    shiftTypeSelect.value = shift.shiftTypeId;

    document.getElementById('editShiftWarning').style.display = 'none';
    document.getElementById('editShiftModalTitle').textContent = 'Schicht bearbeiten';
    document.getElementById('editShiftModal').style.display = 'block';
}

async function showNewShiftModal() {
    if (!canPlanShifts()) {
        alert('Sie haben keine Berechtigung, Schichten zu erstellen.');
        return;
    }

    // Load employees and shift types if not already loaded
    await loadEmployees();
    if (allShiftTypes.length === 0) {
        await loadShiftTypes();
    }

    // Clear modal for new shift
    document.getElementById('editShiftForm').reset();
    document.getElementById('editShiftId').value = '';
    
    // Set default date to current view date
    let defaultDate;
    if (currentView === 'week') {
        defaultDate = document.getElementById('startDate').value;
    } else if (currentView === 'month') {
        const month = document.getElementById('monthSelect').value;
        const year = document.getElementById('monthYearSelect').value;
        defaultDate = `${year}-${month.padStart(2, '0')}-01`;
    } else {
        defaultDate = new Date().toISOString().split('T')[0];
    }
    document.getElementById('editShiftDate').value = defaultDate;
    
    // Populate employee dropdown
    const employeeSelect = document.getElementById('editShiftEmployeeId');
    employeeSelect.innerHTML = '<option value="">Mitarbeiter wählen...</option>';
    cachedEmployees.forEach(emp => {
        const option = document.createElement('option');
        option.value = emp.id;
        const teamInfo = emp.teamName ? ` (${emp.teamName})` : '';
        const funktionInfo = emp.funktion ? ` - ${emp.funktion}` : '';
        option.textContent = `${emp.vorname} ${emp.name} (PN: ${emp.personalnummer})${teamInfo}${funktionInfo}`;
        employeeSelect.appendChild(option);
    });

    // Populate shift type dropdown
    const shiftTypeSelect = document.getElementById('editShiftTypeId');
    shiftTypeSelect.innerHTML = '<option value="">Schichttyp wählen...</option>';
    allShiftTypes.forEach(type => {
        const option = document.createElement('option');
        option.value = type.id;
        option.textContent = `${type.name} (${type.code})`;
        shiftTypeSelect.appendChild(option);
    });

    document.getElementById('editShiftWarning').style.display = 'none';
    document.getElementById('editShiftModalTitle').textContent = 'Neue Schicht erstellen';
    document.getElementById('editShiftModal').style.display = 'block';
}

function closeEditShiftModal() {
    document.getElementById('editShiftModal').style.display = 'none';
    document.getElementById('editShiftForm').reset();
    document.getElementById('editShiftWarning').style.display = 'none';
}

async function saveShiftAssignment(event) {
    event.preventDefault();

    const shiftId = document.getElementById('editShiftId').value;
    const isNewShift = !shiftId;
    
    const shiftData = {
        employeeId: parseInt(document.getElementById('editShiftEmployeeId').value),
        date: document.getElementById('editShiftDate').value,
        shiftTypeId: parseInt(document.getElementById('editShiftTypeId').value),
        isFixed: document.getElementById('editShiftIsFixed').checked,
        notes: document.getElementById('editShiftNotes').value
    };

    // Only include id for updates
    if (!isNewShift) {
        shiftData.id = parseInt(shiftId);
    }

    try {
        const url = isNewShift 
            ? `${API_BASE}/shifts/assignments`
            : `${API_BASE}/shifts/assignments/${shiftId}`;
        const method = isNewShift ? 'POST' : 'PUT';
        
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(shiftData)
        });

        if (response.ok) {
            alert(isNewShift ? 'Schicht erfolgreich erstellt!' : 'Schicht erfolgreich aktualisiert!');
            closeEditShiftModal();
            loadSchedule();
        } else if (response.status === 400) {
            const error = await response.json();
            if (error.warning) {
                // Show warning and ask for confirmation
                document.getElementById('editShiftWarningText').textContent = error.error;
                document.getElementById('editShiftWarning').style.display = 'block';
                
                if (confirm(`⚠️ Regelverstoß:\n\n${error.error}\n\nMöchten Sie die Änderung trotzdem vornehmen?`)) {
                    // Override validation - for now just try again
                    // In a real implementation, you'd add a 'force' parameter
                    alert('Erzwungene Änderungen sind noch nicht implementiert. Die Schicht muss den Regeln entsprechen.');
                }
            } else {
                alert(`Fehler: ${error.error}`);
            }
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an.');
        } else if (response.status === 403) {
            alert('Sie haben keine Berechtigung für diese Aktion.');
        } else {
            alert(isNewShift ? 'Fehler beim Erstellen der Schicht.' : 'Fehler beim Aktualisieren der Schicht.');
        }
    } catch (error) {
        console.error('Error saving shift:', error);
        alert(`Fehler: ${error.message}`);
    }
}

async function deleteShiftAssignment() {
    const shiftId = document.getElementById('editShiftId').value;
    
    if (!confirm('Möchten Sie diese Schichtzuweisung wirklich löschen?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/shifts/assignments/${shiftId}`, {
            method: 'DELETE',
            credentials: 'include'
        });

        if (response.ok || response.status === 204) {
            alert('Schicht erfolgreich gelöscht!');
            closeEditShiftModal();
            loadSchedule();
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an.');
        } else if (response.status === 403) {
            alert('Sie haben keine Berechtigung für diese Aktion.');
        } else {
            alert('Fehler beim Löschen der Schicht.');
        }
    } catch (error) {
        console.error('Error deleting shift:', error);
        alert(`Fehler: ${error.message}`);
    }
}

async function toggleShiftFixed(shiftId) {
    if (!canPlanShifts()) {
        alert('Sie haben keine Berechtigung, Schichten zu sperren/entsperren.');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/shifts/assignments/${shiftId}/toggle-fixed`, {
            method: 'PUT',
            credentials: 'include'
        });

        if (response.ok) {
            const data = await response.json();
            const status = data.isFixed ? 'gesperrt' : 'entsperrt';
            alert(`Schicht erfolgreich ${status}!`);
            loadSchedule();
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an.');
        } else if (response.status === 403) {
            alert('Sie haben keine Berechtigung für diese Aktion.');
        } else {
            const error = await response.json();
            alert(`Fehler: ${error.error || 'Unbekannter Fehler'}`);
        }
    } catch (error) {
        console.error('Error toggling fixed status:', error);
        alert(`Fehler: ${error.message}`);
    }
}

// Audit Log functions
async function loadAuditLogs(count = 100) {
    const content = document.getElementById('audit-logs-content');
    content.innerHTML = '<p class="loading">Lade Änderungsprotokoll...</p>';
    
    try {
        const response = await fetch(`${API_BASE}/auditlogs/recent/${count}`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const logs = await response.json();
            displayAuditLogs(logs);
        } else if (response.status === 401) {
            content.innerHTML = '<p class="error">Bitte melden Sie sich an.</p>';
        } else if (response.status === 403) {
            content.innerHTML = '<p class="error">Sie haben keine Berechtigung, das Änderungsprotokoll anzuzeigen.</p>';
        } else {
            content.innerHTML = '<p class="error">Fehler beim Laden des Änderungsprotokolls.</p>';
        }
    } catch (error) {
        console.error('Error loading audit logs:', error);
        content.innerHTML = '<p class="error">Fehler beim Laden des Änderungsprotokolls.</p>';
    }
}

function displayAuditLogs(logs) {
    const content = document.getElementById('audit-logs-content');
    
    if (!logs || logs.length === 0) {
        content.innerHTML = '<p>Keine Einträge im Änderungsprotokoll gefunden.</p>';
        return;
    }
    
    let html = '<table class="data-table"><thead><tr>';
    html += '<th>Zeitstempel</th><th>Benutzer</th><th>Aktion</th><th>Entität</th><th>Details</th>';
    html += '</tr></thead><tbody>';
    
    logs.forEach(log => {
        const timestamp = new Date(log.timestamp).toLocaleString('de-DE');
        const actionBadge = getActionBadge(log.action);
        
        html += '<tr>';
        html += `<td>${timestamp}</td>`;
        html += `<td>${escapeHtml(log.userName)}</td>`;
        html += `<td>${actionBadge}</td>`;
        html += `<td>${escapeHtml(log.entityName)} (ID: ${escapeHtml(log.entityId)})</td>`;
        html += `<td><small>${log.changes ? escapeHtml(log.changes.substring(0, 100)) + '...' : '-'}</small></td>`;
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    content.innerHTML = html;
}

function getActionBadge(action) {
    switch(action) {
        case 'Created':
            return '<span class="badge badge-success">Erstellt</span>';
        case 'Updated':
            return '<span class="badge badge-warning">Aktualisiert</span>';
        case 'Deleted':
            return '<span class="badge badge-error">Gelöscht</span>';
        default:
            return `<span class="badge">${escapeHtml(action)}</span>`;
    }
}

// ===========================
// Admin Tab Navigation
// ===========================

function showAdminTab(tabName, clickedElement) {
    // Hide all tab contents
    const allTabContents = document.querySelectorAll('.admin-tab-content');
    allTabContents.forEach(content => content.classList.remove('active'));
    
    // Remove active class from all tabs
    const allTabs = document.querySelectorAll('.admin-tab');
    allTabs.forEach(tab => tab.classList.remove('active'));
    
    // Show selected tab content
    const selectedContent = document.getElementById(`admin-tab-${tabName}`);
    if (selectedContent) {
        selectedContent.classList.add('active');
    }
    
    // Add active class to selected tab
    // Use clickedElement if provided, otherwise find by onclick attribute
    if (clickedElement) {
        clickedElement.classList.add('active');
    } else {
        const tabButton = document.querySelector(`.admin-tab[onclick*="${tabName}"]`);
        if (tabButton) {
            tabButton.classList.add('active');
        }
    }
    
    // Load data for the selected tab if needed
    if (tabName === 'users') {
        stopAuditLogAutoRefresh(); // Stop auto-refresh when switching away from audit logs
        loadUsers();
    } else if (tabName === 'audit-logs') {
        loadAuditLogs(1, 50);
        startAuditLogAutoRefresh(AUDIT_LOG_DEFAULT_REFRESH_INTERVAL); // Start auto-refresh with default interval
    } else if (tabName === 'email') {
        stopAuditLogAutoRefresh(); // Stop auto-refresh when switching away from audit logs
        loadEmailSettings();
    } else {
        // Stop auto-refresh for any other tab
        stopAuditLogAutoRefresh();
    }
}

// ===========================
// Enhanced Audit Log Functions with Pagination and Filtering
// ===========================

const AUDIT_LOG_DEFAULT_REFRESH_INTERVAL = 60; // seconds
const AUDIT_LOG_MIN_REFRESH_INTERVAL = 5; // seconds

let currentAuditPage = 1;
let currentAuditPageSize = 50;
let currentAuditFilters = {};
let auditLogRefreshInterval = null; // Store interval ID for cleanup
let auditLogRefreshIntervalTime = AUDIT_LOG_DEFAULT_REFRESH_INTERVAL * 1000; // milliseconds

async function loadAuditLogs(page = 1, pageSize = 50) {
    const content = document.getElementById('audit-logs-content');
    content.innerHTML = '<p class="loading">Lade Änderungsprotokoll...</p>';
    
    currentAuditPage = page;
    currentAuditPageSize = pageSize;
    
    try {
        // Build query parameters
        let queryParams = new URLSearchParams({
            page: page,
            pageSize: pageSize
        });
        
        // Add filters if present
        if (currentAuditFilters.entityName) {
            queryParams.append('entityName', currentAuditFilters.entityName);
        }
        if (currentAuditFilters.action) {
            queryParams.append('action', currentAuditFilters.action);
        }
        if (currentAuditFilters.startDate) {
            queryParams.append('startDate', currentAuditFilters.startDate);
        }
        if (currentAuditFilters.endDate) {
            queryParams.append('endDate', currentAuditFilters.endDate);
        }
        
        const response = await fetch(`${API_BASE}/auditlogs?${queryParams.toString()}`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const result = await response.json();
            displayAuditLogsPaginated(result);
        } else if (response.status === 401) {
            content.innerHTML = '<p class="error">Bitte melden Sie sich an.</p>';
        } else if (response.status === 403) {
            content.innerHTML = '<p class="error">Sie haben keine Berechtigung, das Änderungsprotokoll anzuzeigen.</p>';
        } else {
            content.innerHTML = '<p class="error">Fehler beim Laden des Änderungsprotokolls.</p>';
        }
    } catch (error) {
        console.error('Error loading audit logs:', error);
        content.innerHTML = '<p class="error">Fehler beim Laden des Änderungsprotokolls.</p>';
    }
}

function displayAuditLogsPaginated(result) {
    const content = document.getElementById('audit-logs-content');
    const pagination = document.getElementById('audit-pagination');
    
    if (!result.items || result.items.length === 0) {
        content.innerHTML = '<p>Keine Einträge im Änderungsprotokoll gefunden.</p>';
        pagination.style.display = 'none';
        return;
    }
    
    // Display the audit logs table
    let html = '<table class="data-table"><thead><tr>';
    html += '<th>Zeitstempel</th>';
    html += '<th>Benutzer</th>';
    html += '<th>Entität</th>';
    html += '<th>Entität-ID</th>';
    html += '<th>Aktion</th>';
    html += '<th>Änderungen</th>';
    html += '</tr></thead><tbody>';
    
    result.items.forEach(log => {
        html += '<tr>';
        html += `<td>${new Date(log.timestamp).toLocaleString('de-DE')}</td>`;
        html += `<td>${escapeHtml(log.userName)}</td>`;
        html += `<td>${escapeHtml(log.entityName)}</td>`;
        html += `<td>${escapeHtml(log.entityId)}</td>`;
        html += `<td>${getActionBadge(log.action)}</td>`;
        html += `<td><pre class="changes-preview">${escapeHtml(log.changes?.substring(0, 100) || '')}${log.changes?.length > 100 ? '...' : ''}</pre></td>`;
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    content.innerHTML = html;
    
    // Update pagination
    pagination.style.display = 'flex';
    document.getElementById('audit-page-info').textContent = `Seite ${result.page} von ${result.totalPages} (${result.totalCount} Einträge)`;
    document.getElementById('audit-prev-btn').disabled = !result.hasPreviousPage;
    document.getElementById('audit-next-btn').disabled = !result.hasNextPage;
}

function applyAuditFilters() {
    currentAuditFilters = {
        entityName: document.getElementById('audit-filter-entity').value,
        action: document.getElementById('audit-filter-action').value,
        startDate: document.getElementById('audit-filter-start-date').value,
        endDate: document.getElementById('audit-filter-end-date').value
    };
    
    // Reset to page 1 when applying filters
    loadAuditLogs(1, currentAuditPageSize);
}

function clearAuditFilters() {
    document.getElementById('audit-filter-entity').value = '';
    document.getElementById('audit-filter-action').value = '';
    document.getElementById('audit-filter-start-date').value = '';
    document.getElementById('audit-filter-end-date').value = '';
    
    currentAuditFilters = {};
    loadAuditLogs(1, currentAuditPageSize);
}

function loadAuditLogsPreviousPage() {
    if (currentAuditPage > 1) {
        loadAuditLogs(currentAuditPage - 1, currentAuditPageSize);
    }
}

function loadAuditLogsNextPage() {
    loadAuditLogs(currentAuditPage + 1, currentAuditPageSize);
}

// ===========================
// Audit Log Auto-Refresh Functions
// ===========================

/**
 * Start automatic refresh of audit logs
 * @param {number} intervalSeconds - Refresh interval in seconds (default: 60)
 */
function startAuditLogAutoRefresh(intervalSeconds = 60) {
    // Stop any existing refresh interval
    stopAuditLogAutoRefresh();
    
    // Store the interval time
    auditLogRefreshIntervalTime = intervalSeconds * 1000;
    
    // Start the refresh interval
    auditLogRefreshInterval = setInterval(() => {
        // Only refresh if the audit logs tab is currently visible
        const auditLogsTab = document.getElementById('admin-tab-audit-logs');
        if (auditLogsTab && auditLogsTab.classList.contains('active')) {
            console.log('Auto-refreshing audit logs...');
            loadAuditLogs(currentAuditPage, currentAuditPageSize);
        }
    }, auditLogRefreshIntervalTime);
    
    // Update status indicator
    const statusElement = document.getElementById('audit-auto-refresh-status');
    if (statusElement) {
        statusElement.textContent = `🔄 Auto-Aktualisierung: Aktiv (${intervalSeconds}s)`;
        statusElement.style.color = '#4CAF50';
    }
    
    console.log(`Audit log auto-refresh started with ${intervalSeconds} second interval`);
}

/**
 * Stop automatic refresh of audit logs
 */
function stopAuditLogAutoRefresh() {
    if (auditLogRefreshInterval) {
        clearInterval(auditLogRefreshInterval);
        auditLogRefreshInterval = null;
        
        // Update status indicator
        const statusElement = document.getElementById('audit-auto-refresh-status');
        if (statusElement) {
            statusElement.textContent = '⏸ Auto-Aktualisierung: Inaktiv';
            statusElement.style.color = '#999';
        }
        
        console.log('Audit log auto-refresh stopped');
    }
}

/**
 * Change the auto-refresh interval
 * @param {number} intervalSeconds - New refresh interval in seconds
 */
function setAuditLogRefreshInterval(intervalSeconds) {
    if (intervalSeconds < AUDIT_LOG_MIN_REFRESH_INTERVAL) {
        console.warn(`Minimum refresh interval is ${AUDIT_LOG_MIN_REFRESH_INTERVAL} seconds`);
        intervalSeconds = AUDIT_LOG_MIN_REFRESH_INTERVAL;
    }
    
    auditLogRefreshIntervalTime = intervalSeconds * 1000;
    
    // Restart with new interval if auto-refresh is active
    if (auditLogRefreshInterval) {
        startAuditLogAutoRefresh(intervalSeconds);
    }
    
    console.log(`Audit log refresh interval set to ${intervalSeconds} seconds`);
}

