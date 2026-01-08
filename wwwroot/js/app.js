// API Base URL
const API_BASE = window.location.origin + '/api';

// State
let currentDate = new Date();
let currentView = 'week';
let currentUser = null;
let userRoles = [];
let multiSelectMode = false;
let selectedShifts = new Set(); // Set of shift IDs for multi-edit

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
        document.getElementById('nav-management').style.display = 'inline-block';
        document.getElementById('nav-statistics').style.display = 'inline-block';
        document.getElementById('nav-absences').style.display = 'inline-block';
        document.getElementById('nav-shiftexchange').style.display = 'inline-block';
        // Show admin-only tab in absences view
        const vacationYearApprovalsTab = document.getElementById('tab-vacation-year-approvals');
        if (vacationYearApprovalsTab) {
            vacationYearApprovalsTab.style.display = '';
        }
    } else if (isDisponent) {
        document.body.classList.add('disponent');
        document.getElementById('nav-absences').style.display = 'inline-block';
        document.getElementById('nav-shiftexchange').style.display = 'inline-block';
    } else {
        // Mitarbeiter can also access vacation and shift exchange
        document.getElementById('nav-absences').style.display = 'inline-block';
        document.getElementById('nav-shiftexchange').style.display = 'inline-block';
    }
    
    // Start notification polling for admins and dispatchers
    if (isAdmin || isDisponent) {
        startNotificationPolling();
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
    
    // Stop notification polling
    stopNotificationPolling();
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
    } else if (viewName === 'management') {
        // Load employees tab by default in management view
        switchManagementTab('employees');
    } else if (viewName === 'employees') {
        // Redirect old 'employees' view to new 'management' view
        showView('management');
        return;
    } else if (viewName === 'teams') {
        // Redirect old 'teams' view to new 'management' view
        showView('management');
        switchManagementTab('teams');
        return;
    } else if (viewName === 'absences') {
        // Load vacation tab by default
        switchAbsenceTab('vacation');
    } else if (viewName === 'vacations') {
        // Redirect old 'vacations' view to new 'absences' view
        showView('absences');
        return;
    } else if (viewName === 'shiftexchange') {
        loadShiftExchanges('available');
    } else if (viewName === 'vacationyearplan') {
        initVacationYearPlan();
        loadVacationYearPlan();
    } else if (viewName === 'statistics') {
        loadStatistics();
    } else if (viewName === 'admin') {
        loadAdminView();
    } else if (viewName === 'manual') {
        initializeManualAnchors();
    }
}

function loadAdminView() {
    // Load audit logs tab by default (it will be active)
    loadAuditLogs(1, 50);
    startAuditLogAutoRefresh(AUDIT_LOG_DEFAULT_REFRESH_INTERVAL);
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
        
        // Update approval status for month view
        if (currentView === 'month') {
            await updateApprovalStatus();
        }
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
    
    // Add vacation periods row (Ferienzeiten) at the very top
    if (data.vacationPeriods && data.vacationPeriods.length > 0) {
        html += '<tr class="vacation-period-row">';
        html += '<td class="vacation-period-label"><strong>🏖️ Ferien</strong></td>';
        
        dates.forEach(dateStr => {
            const date = new Date(dateStr);
            const activePeriods = data.vacationPeriods.filter(period => {
                const startDate = new Date(period.startDate);
                const endDate = new Date(period.endDate);
                return date >= startDate && date <= endDate;
            });
            
            let content = '';
            if (activePeriods.length > 0) {
                // Show vacation period name(s)
                activePeriods.forEach(period => {
                    content += `<div class="vacation-period-badge" style="background-color: ${period.colorCode};" title="${escapeHtml(period.name)}">${escapeHtml(period.name)}</div>`;
                });
            }
            
            const isSunday = date.getDay() === 0;
            const isHoliday = isHessianHoliday(date);
            const cellClass = (isSunday || isHoliday) ? 'vacation-period-cell sunday-cell' : 'vacation-period-cell';
            html += `<td class="${cellClass}">${content}</td>`;
        });
        
        html += '</tr>';
    }
    
    // Add rows for each team and employee
    teamGroups.forEach(team => {
        // Team header row
        html += `<tr class="team-row"><td colspan="${dates.length + 1}" class="team-header">${team.teamName}</td></tr>`;
        
        // Employee rows
        team.employees.forEach(employee => {
            html += '<tr class="employee-row">';
            html += `<td class="employee-name">  - ${employee.name}${employee.isTeamLeader ? ' ⭐' : ''}</td>`;
            
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
                    // Show absence badge with status-based color coding
                    content = createAbsenceBadge(absence);
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
    
    // Add vacation periods row (Ferienzeiten) at the very top
    if (data.vacationPeriods && data.vacationPeriods.length > 0) {
        const totalDays = weekGroups.reduce((sum, w) => sum + w.days.length, 0);
        html += '<tr class="vacation-period-row">';
        html += '<td class="vacation-period-label"><strong>🏖️ Ferien</strong></td>';
        
        weekGroups.forEach(week => {
            week.days.forEach(dateStr => {
                const date = new Date(dateStr);
                const activePeriods = data.vacationPeriods.filter(period => {
                    const startDate = new Date(period.startDate);
                    const endDate = new Date(period.endDate);
                    return date >= startDate && date <= endDate;
                });
                
                let content = '';
                if (activePeriods.length > 0) {
                    // Show vacation period name(s) - abbreviated for month view
                    activePeriods.forEach(period => {
                        const shortName = period.name.length > 10 ? period.name.substring(0, 8) + '...' : period.name;
                        content += `<div class="vacation-period-badge-compact" style="background-color: ${period.colorCode};" title="${escapeHtml(period.name)}">${escapeHtml(shortName)}</div>`;
                    });
                }
                
                const isSunday = date.getDay() === 0;
                const isHoliday = isHessianHoliday(date);
                const cellClass = (isSunday || isHoliday) ? 'vacation-period-cell sunday-cell' : 'vacation-period-cell';
                html += `<td class="${cellClass}">${content}</td>`;
            });
        });
        
        html += '</tr>';
    }
    
    // Add rows for each team and employee
    teamGroups.forEach(team => {
        // Calculate total number of days across all weeks
        const totalDays = weekGroups.reduce((sum, w) => sum + w.days.length, 0);
        // Team header row
        html += `<tr class="team-row"><td colspan="${totalDays + 1}" class="team-header">${team.teamName}</td></tr>`;
        
        // Employee rows
        team.employees.forEach(employee => {
            html += '<tr class="employee-row">';
            html += `<td class="employee-name">  - ${employee.name}${employee.isTeamLeader ? ' ⭐' : ''}</td>`;
            
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
                        // Show absence badge with status-based color coding
                        content = createAbsenceBadge(absence);
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
        
        // Add vacation periods row (Ferienzeiten) at the very top of each month
        if (data.vacationPeriods && data.vacationPeriods.length > 0) {
            html += '<tr class="vacation-period-row">';
            html += '<td class="vacation-period-label"><strong>🏖️ Ferien</strong></td>';
            
            month.weeks.forEach(weekNum => {
                const weekDates = month.dates.filter(d => getWeekNumber(new Date(d)) === weekNum);
                const activePeriods = [];
                
                weekDates.forEach(dateStr => {
                    const date = new Date(dateStr);
                    data.vacationPeriods.forEach(period => {
                        const startDate = new Date(period.startDate);
                        const endDate = new Date(period.endDate);
                        if (date >= startDate && date <= endDate && !activePeriods.find(p => p.id === period.id)) {
                            activePeriods.push(period);
                        }
                    });
                });
                
                let content = '';
                if (activePeriods.length > 0) {
                    // Show just an indicator for year view
                    content = '<div class="vacation-period-indicator" title="' + activePeriods.map(p => escapeHtml(p.name)).join(', ') + '">🏖️</div>';
                }
                
                html += `<td class="vacation-period-cell">${content}</td>`;
            });
            
            html += '</tr>';
        }
        
        // Add rows for each team and employee
        teamGroups.forEach(team => {
            // Team header row
            html += `<tr class="team-row"><td colspan="${month.weeks.length + 1}" class="team-header">${team.teamName}</td></tr>`;
            
            // Employee rows
            team.employees.forEach(employee => {
                html += '<tr class="employee-row">';
                html += `<td class="employee-name">  - ${employee.name}${employee.isTeamLeader ? ' ⭐' : ''}</td>`;
                
                // Add shift cells for each week
                month.weeks.forEach(weekNum => {
                    const weekDates = month.dates.filter(d => getWeekNumber(new Date(d)) === weekNum);
                    const shifts = [];
                    let hasAbsence = false;
                    let absenceForDisplay = null;
                    
                    weekDates.forEach(dateStr => {
                        // Check for absence first
                        const absence = getAbsenceForDate(employee.absences || [], dateStr);
                        if (absence) {
                            hasAbsence = true;
                            absenceForDisplay = absence;  // Store the absence for display
                        } else if (employee.shifts[dateStr]) {
                            shifts.push(...employee.shifts[dateStr]);
                        }
                    });
                    
                    let content = '';
                    if (hasAbsence && absenceForDisplay) {
                        content = createAbsenceBadge(absenceForDisplay);
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
    } else if (typeString === 'Urlaub' || typeString.startsWith('Urlaub')) {
        return 'U';
    } else if (typeString === 'Lehrgang') {
        return 'L';
    }
    return 'A'; // Default for unknown types
}

/**
 * Create an absence badge HTML element with status-based color coding
 * @param {object} absence - Absence object with type, status, and notes
 * @returns {string} HTML for absence badge
 */
function createAbsenceBadge(absence) {
    if (!absence || !absence.type) {
        return '';
    }
    
    const absenceCode = getAbsenceCode(absence.type);
    let cssClass = `shift-badge shift-${absenceCode}`;
    
    // Apply status-based styling for vacation (Urlaub) entries
    if (absenceCode === 'U' && absence.status) {
        if (absence.status === 'InBearbeitung') {
            cssClass = 'shift-badge shift-U-pending';
        } else if (absence.status === 'Abgelehnt') {
            cssClass = 'shift-badge shift-U-rejected';
        }
        // 'Genehmigt' uses default shift-U (blue)
    }
    
    const title = `${absence.type}: ${absence.notes || ''}`;
    return `<span class="${cssClass}" title="${title}">${absenceCode}</span>`;
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
    
    // Check if this shift is selected in multi-select mode
    const isSelected = multiSelectMode && shiftId && selectedShifts.has(shiftId);
    const selectedClass = isSelected ? 'shift-selected' : '';
    
    // In multi-select mode, clicking toggles selection; otherwise, opens edit modal
    let onclickAttr = '';
    if (canEdit && shiftId) {
        if (multiSelectMode) {
            onclickAttr = `onclick="toggleShiftSelection(${shiftId}); return false;" style="cursor:pointer;"`;
        } else {
            onclickAttr = `onclick="editShiftAssignment(${shiftId})" style="cursor:pointer;"`;
        }
    }
    
    return `<span class="shift-badge shift-${shiftCode} ${badgeClass} ${selectedClass}" title="${shiftName}${isFixed ? ' (Fixiert)' : ''}" ${onclickAttr}>${lockIcon}${shiftCode}</span>`;
}

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
 * Determines if an employee should be excluded from the unassigned team listing.
 * Employees with special functions (BMT, BSB, Ferienjobber) but no regular team
 * belong only to virtual teams and should not appear in "Ohne Team".
 * @param {Object} emp - The employee object
 * @returns {boolean} True if employee should be excluded from unassigned team
 */
function shouldExcludeFromUnassigned(emp) {
    // If employee has a team, they should not be excluded
    if (emp.teamId && emp.teamId > 0) {
        return false;
    }
    
    // Exclude if employee has special functions and no team
    // These employees belong to virtual teams only
    return emp.isBrandmeldetechniker || emp.isBrandschutzbeauftragter || emp.isFerienjobber;
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
            // Skip - will be added to virtual team below
            return;
        }
        
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
                isTeamLeader: emp.isTeamLeader || false,
                shifts: {},
                absences: [] // Store absences for this employee
            };
        }
    });
    
    // Then, add shift assignments to the employees
    assignments.forEach(a => {
        // Find employee to check for special functions
        const employee = employeeMap.get(a.employeeId);
        
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
                    isTeamLeader: employee?.isTeamLeader || false,
                    shifts: {},
                    absences: []
                };
            }
            
            const dateKey = a.date.split('T')[0];
            if (!teams[teamId].employees[a.employeeId].shifts[dateKey]) {
                teams[teamId].employees[a.employeeId].shifts[dateKey] = [];
            }
            teams[teamId].employees[a.employeeId].shifts[dateKey].push(a);
    });
    
    // Add absences to the employees
    absences.forEach(absence => {
        // Find employee to check for special functions
        const employee = employeeMap.get(absence.employeeId);
        
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
                const displayName = formatEmployeeDisplayName(
                    absence.employeeName,
                    employee?.personalnummer || ''
                );
                
                // Create employee entry if not exists
                teams[teamId].employees[absence.employeeId] = {
                    id: absence.employeeId,
                    name: displayName,
                    personalnummer: employee?.personalnummer || '',
                    isTeamLeader: employee?.isTeamLeader || false,
                    shifts: {},
                    absences: []
                };
            }
            
            teams[teamId].employees[absence.employeeId].absences.push(absence);
    });
    
    // Convert to array and sort
    return Object.values(teams).map(team => ({
        teamId: team.teamId,
        teamName: team.teamName,
        employees: Object.values(team.employees).sort((a, b) => {
            // Team leaders always come first within their team
            if (a.isTeamLeader && !b.isTeamLeader) return -1;
            if (!a.isTeamLeader && b.isTeamLeader) return 1;
            // Then sort alphabetically by name
            return a.name.localeCompare(b.name);
        })
    })).sort((a, b) => {
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
}

async function executePlanShifts(event) {
    event.preventDefault();
    
    if (!canPlanShifts()) {
        alert('Sie haben keine Berechtigung, Schichten zu planen.');
        return;
    }
    
    const month = document.getElementById('planMonth').value;
    const year = document.getElementById('planMonthYear').value;
    const force = document.getElementById('planForceOverwrite').checked;
    
    if (!month || !year) {
        alert('Bitte wählen Sie Monat und Jahr aus.');
        return;
    }
    
    const startDate = new Date(year, month - 1, 1);
    const endDate = new Date(year, month, 0); // Last day of month
    
    // Format dates in local timezone to avoid timezone conversion issues
    const startDateStr = `${year}-${month.padStart(2, '0')}-01`;
    const endDateStr = `${year}-${month.padStart(2, '0')}-${endDate.getDate().toString().padStart(2, '0')}`;
    
    // Show confirmation
    const periodText = startDate.toLocaleDateString('de-DE', { month: 'long', year: 'numeric' });
    
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
            const successMsg = `Erfolgreich! ${data.assignmentsCount || 0} Schichten wurden für ${periodText} geplant.`;
            const reminderMsg = 'Hinweis: Der Dienstplan muss noch freigegeben werden, bevor er für normale Mitarbeiter sichtbar ist.';
            alert(`${successMsg}\n\n${reminderMsg}`);
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
        endDate = `${year}-${month.padStart(2, '0')}-${end.getDate().toString().padStart(2, '0')}`;
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
        endDate = `${year}-${month.padStart(2, '0')}-${end.getDate().toString().padStart(2, '0')}`;
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
        endDate = `${year}-${month.padStart(2, '0')}-${end.getDate().toString().padStart(2, '0')}`;
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
    
    // Show password field and make it required for new employees
    document.getElementById('employeePasswordGroup').style.display = 'block';
    document.getElementById('employeePassword').required = true;
    document.getElementById('employeePasswordLabel').textContent = 'Passwort*';
    
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
        document.getElementById('isTeamLeader').checked = employee.isTeamLeader || false;
        document.getElementById('isBrandmeldetechniker').checked = employee.isBrandmeldetechniker || false;
        document.getElementById('isBrandschutzbeauftragter').checked = employee.isBrandschutzbeauftragter || false;
        // TD qualification is now automatic based on BMT or BSB
        
        // Show password field but make it optional for editing
        document.getElementById('employeePasswordGroup').style.display = 'block';
        document.getElementById('employeePassword').required = false;
        document.getElementById('employeePassword').value = '';
        document.getElementById('employeePasswordLabel').textContent = 'Neues Passwort (optional)';
        
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
    const isEdit = !!id;
    const employee = {
        vorname: document.getElementById('vorname').value,
        name: document.getElementById('name').value,
        personalnummer: document.getElementById('personalnummer').value,
        email: document.getElementById('email').value || null,
        geburtsdatum: document.getElementById('geburtsdatum').value || null,
        teamId: document.getElementById('teamId').value ? parseInt(document.getElementById('teamId').value) : null,
        isSpringer: false,  // Always false since checkbox was removed
        isTeamLeader: document.getElementById('isTeamLeader').checked,
        isBrandmeldetechniker: document.getElementById('isBrandmeldetechniker').checked,
        isBrandschutzbeauftragter: document.getElementById('isBrandschutzbeauftragter').checked
        // isTdQualified is calculated automatically on the server based on BMT or BSB
    };
    
    // Include password for new employees or if provided when editing
    const password = document.getElementById('employeePassword').value;
    if (!isEdit || (isEdit && password)) {
        employee.password = password;
    }
    
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
                        ${isAdmin ? `<button onclick="deleteTeam(${team.id}, '${escapeHtml(team.name)}')" class="btn-small btn-delete">🗑️ Löschen</button>` : ''}
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
    document.getElementById('teamEditId').value = '';
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
        
        document.getElementById('teamEditId').value = team.id;
        document.getElementById('teamName').value = team.name;
        document.getElementById('teamDescription').value = team.description || '';
        document.getElementById('teamEmail').value = team.email || '';
        
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
        } else if (response.status === 400) {
            const errorData = await response.json();
            alert(errorData.error || 'Fehler beim Löschen');
        } else {
            const errorData = await response.json().catch(() => ({}));
            alert(errorData.error || 'Fehler beim Löschen');
        }
    } catch (error) {
        console.error('Error deleting team:', error);
        alert(`Fehler: ${error.message}`);
    }
}

function closeTeamModal() {
    document.getElementById('teamModal').style.display = 'none';
    document.getElementById('teamForm').reset();
}

async function saveTeam(event) {
    event.preventDefault();
    
    const idValue = document.getElementById('teamEditId').value;
    const id = idValue ? parseInt(idValue) : null;
    const team = {
        name: document.getElementById('teamName').value,
        description: document.getElementById('teamDescription').value || null,
        email: document.getElementById('teamEmail').value || null,
        isVirtual: false  // Always false since checkbox was removed
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
    document.querySelectorAll('#absences-view .tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all tab buttons
    document.querySelectorAll('#absences-view .tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab content
    const selectedTab = document.getElementById(`${tabName}-tab`);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Activate corresponding button
    const tabButtons = document.querySelectorAll('#absences-view .tab-btn');
    tabButtons.forEach((btn, index) => {
        const btnOnclick = btn.getAttribute('onclick');
        if (btnOnclick && btnOnclick.includes(`'${tabName}'`)) {
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
    } else if (tabName === 'vacation-periods') {
        loadVacationPeriods();
    } else if (tabName === 'vacation-year-approvals') {
        loadVacationYearApprovalsAbsence();
    }
}

// Switch Management Tab (for Verwaltung view)
function switchManagementTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('#management-view .tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all tab buttons
    document.querySelectorAll('#management-view .tabs:not(.sub-tabs) .tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab content
    const selectedTab = document.getElementById(`management-${tabName}-tab`);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Activate corresponding button
    const tabButtons = document.querySelectorAll('#management-view .tabs:not(.sub-tabs) .tab-btn');
    tabButtons.forEach(btn => {
        const btnOnclick = btn.getAttribute('onclick');
        if (btnOnclick && btnOnclick.includes(`'${tabName}'`)) {
            btn.classList.add('active');
        }
    });
    
    // Load content for the selected tab
    if (tabName === 'employees') {
        loadEmployees();
    } else if (tabName === 'teams') {
        loadTeams();
    } else if (tabName === 'shift-types') {
        switchShiftManagementTab('types'); // Default to types sub-tab
    }
}

function switchShiftManagementTab(subTabName) {
    // Hide all sub-tab contents in shift management
    document.querySelectorAll('#management-shift-types-tab > .tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all sub-tab buttons
    document.querySelectorAll('.sub-tabs .tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected sub-tab content
    if (subTabName === 'types') {
        document.getElementById('shift-types-content-tab').classList.add('active');
        loadShiftTypesManagement();
    } else if (subTabName === 'settings') {
        document.getElementById('shift-settings-content-tab').classList.add('active');
        loadGlobalSettings();
    }
    
    // Activate corresponding button
    document.querySelectorAll('.sub-tabs .tab-btn').forEach(btn => {
        const btnOnclick = btn.getAttribute('onclick');
        if (btnOnclick && btnOnclick.includes(`'${subTabName}'`)) {
            btn.classList.add('active');
        }
    });
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
            // Show password field but make it optional for editing
            document.getElementById('passwordGroup').style.display = 'block';
            document.getElementById('userPassword').required = false;
            document.getElementById('userPassword').value = '';
            document.getElementById('passwordLabel').textContent = 'Neues Passwort (optional)';
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
    document.getElementById('passwordLabel').textContent = 'Passwort*';
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
    
    // Include password for new users or if provided when editing
    const password = document.getElementById('userPassword').value;
    if (!isEdit || (isEdit && password)) {
        userData.password = password;
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
        const response = await fetch(`${API_BASE}/email-settings`, {
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
            <p><strong>SMTP Server:</strong> ${settings.smtpHost || 'Nicht konfiguriert'}:${settings.smtpPort || 587}</p>
            <p><strong>SSL/TLS:</strong> ${settings.useSsl ? 'Ja' : 'Nein'}</p>
            <p><strong>Absender:</strong> ${settings.senderEmail || 'Nicht konfiguriert'} ${settings.senderName ? `(${settings.senderName})` : ''}</p>
            <p><strong>Authentifizierung:</strong> ${settings.requiresAuthentication ? 'Ja' : 'Nein'}</p>
            ${settings.requiresAuthentication && settings.username ? `<p><strong>Benutzername:</strong> ${settings.username}</p>` : ''}
            <p><strong>Status:</strong> <span class="badge ${settings.isEnabled ? 'badge-success' : 'badge-warning'}">${settings.isEnabled ? 'Aktiviert' : 'Deaktiviert'}</span></p>
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
        const response = await fetch(`${API_BASE}/email-settings`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const settings = await response.json();
            // Fill form with existing settings
            document.getElementById('smtpServer').value = settings.smtpHost || '';
            document.getElementById('smtpPort').value = settings.smtpPort || 587;
            document.getElementById('smtpSecurity').value = settings.useSsl ? 'SSL' : 'NONE';
            document.getElementById('requiresAuth').checked = settings.requiresAuthentication !== false;
            document.getElementById('smtpUsername').value = settings.username || '';
            document.getElementById('senderEmail').value = settings.senderEmail || '';
            document.getElementById('senderName').value = settings.senderName || '';
            document.getElementById('replyToEmail').value = settings.replyToEmail || '';
            document.getElementById('emailEnabled').checked = settings.isEnabled !== false;
            // Don't fill password for security
        } else {
            // New settings, use defaults
            document.getElementById('emailSettingsForm').reset();
            document.getElementById('smtpPort').value = 587;
            document.getElementById('emailEnabled').checked = false;
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
        smtpHost: document.getElementById('smtpServer').value,
        smtpPort: parseInt(document.getElementById('smtpPort').value),
        useSsl: document.getElementById('smtpSecurity').value === 'SSL',
        requiresAuthentication: document.getElementById('requiresAuth').checked,
        username: document.getElementById('smtpUsername').value || null,
        password: document.getElementById('smtpPassword').value || null,
        senderEmail: document.getElementById('senderEmail').value,
        senderName: document.getElementById('senderName').value,
        replyToEmail: document.getElementById('replyToEmail').value || null,
        isEnabled: document.getElementById('emailEnabled') ? document.getElementById('emailEnabled').checked : true
    };
    
    try {
        const response = await fetch(`${API_BASE}/email-settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(settings)
        });
        
        if (response.ok) {
            alert('E-Mail-Einstellungen erfolgreich gespeichert!');
            closeEmailSettingsModal();
            loadEmailSettings();
        } else {
            const error = await response.json();
            alert(`Fehler beim Speichern: ${error.error || 'Unbekannter Fehler'}`);
        }
    } catch (error) {
        console.error('Error saving email settings:', error);
        alert(`Fehler: ${error.message}`);
    }
}

async function testEmailSettings() {
    const testEmail = prompt('Bitte geben Sie eine E-Mail-Adresse für den Test ein:');
    if (!testEmail) return;
    
    try {
        const response = await fetch(`${API_BASE}/email-settings/test`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ testEmail: testEmail })
        });
        
        if (response.ok) {
            alert(`Test-E-Mail wurde erfolgreich an ${testEmail} gesendet!`);
        } else {
            const error = await response.json();
            alert(`Fehler beim Senden der Test-E-Mail: ${error.error || 'Unbekannter Fehler'}`);
        }
    } catch (error) {
        console.error('Error testing email settings:', error);
        alert(`Fehler: ${error.message}`);
    }
}

function saveGlobalSettings() {
    const maxConsecutiveShifts = document.getElementById('setting-max-consecutive-shifts').value;
    const maxConsecutiveNights = document.getElementById('setting-max-consecutive-nights').value;
    
    // Store in localStorage for now (in production, these would be saved to a backend configuration)
    localStorage.setItem('maxConsecutiveShifts', maxConsecutiveShifts);
    localStorage.setItem('maxConsecutiveNights', maxConsecutiveNights);
    
    alert(`Einstellungen gespeichert:\n• Max aufeinanderfolgende Schichten: ${maxConsecutiveShifts}\n• Max aufeinanderfolgende Nachtschichten: ${maxConsecutiveNights}\n\nHinweis: Arbeitszeitgrenzen werden jetzt dynamisch aus den Schichteinstellungen berechnet.`);
}

// ===========================
// Vacation Periods (Ferienzeiten) Functions
// ===========================

async function loadVacationPeriods() {
    try {
        const response = await fetch(`${API_BASE}/vacation-periods`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const periods = await response.json();
            displayVacationPeriods(periods);
        } else {
            document.getElementById('vacation-periods-content').innerHTML = '<p class="error">Fehler beim Laden der Ferienzeiten.</p>';
        }
    } catch (error) {
        console.error('Error loading vacation periods:', error);
        document.getElementById('vacation-periods-content').innerHTML = '<p class="error">Fehler beim Laden der Ferienzeiten.</p>';
    }
}

function displayVacationPeriods(periods) {
    const content = document.getElementById('vacation-periods-content');
    
    if (periods.length === 0) {
        content.innerHTML = '<p>Keine Ferienzeiten definiert.</p>';
        return;
    }
    
    let html = '<table class="data-table"><thead><tr>';
    html += '<th>Name</th>';
    html += '<th>Von</th>';
    html += '<th>Bis</th>';
    html += '<th>Farbe</th>';
    html += '<th>Aktionen</th>';
    html += '</tr></thead><tbody>';
    
    periods.forEach(period => {
        const startDate = new Date(period.startDate).toLocaleDateString('de-DE');
        const endDate = new Date(period.endDate).toLocaleDateString('de-DE');
        
        html += '<tr>';
        html += `<td><strong>${escapeHtml(period.name)}</strong></td>`;
        html += `<td>${startDate}</td>`;
        html += `<td>${endDate}</td>`;
        html += `<td><span style="display:inline-block;width:30px;height:20px;background-color:${period.colorCode};border:1px solid #ccc;border-radius:3px;"></span></td>`;
        html += '<td class="actions">';
        html += `<button onclick="editVacationPeriod(${period.id})" class="btn-icon" title="Bearbeiten">✏️</button>`;
        
        if (hasRole('Admin')) {
            html += `<button onclick="deleteVacationPeriod(${period.id}, '${escapeHtml(period.name)}')" class="btn-icon" title="Löschen">🗑️</button>`;
        }
        
        html += '</td></tr>';
    });
    
    html += '</tbody></table>';
    content.innerHTML = html;
}

function showVacationPeriodModal(periodId = null) {
    if (!canPlanShifts()) {
        alert('Sie haben keine Berechtigung, Ferienzeiten zu verwalten.');
        return;
    }
    
    // Reset form
    document.getElementById('vacationPeriodForm').reset();
    document.getElementById('vacationPeriodId').value = '';
    document.getElementById('vacationPeriodColor').value = '#E8F5E9';
    
    if (periodId) {
        // Load existing period data for editing
        document.getElementById('vacationPeriodModalTitle').textContent = 'Ferienzeit bearbeiten';
        loadVacationPeriodForEdit(periodId);
    } else {
        // New period
        document.getElementById('vacationPeriodModalTitle').textContent = 'Ferienzeit hinzufügen';
    }
    
    document.getElementById('vacationPeriodModal').style.display = 'block';
}

async function loadVacationPeriodForEdit(periodId) {
    try {
        const response = await fetch(`${API_BASE}/vacation-periods/${periodId}`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const period = await response.json();
            document.getElementById('vacationPeriodId').value = period.id;
            document.getElementById('vacationPeriodName').value = period.name;
            document.getElementById('vacationPeriodStartDate').value = period.startDate;
            document.getElementById('vacationPeriodEndDate').value = period.endDate;
            document.getElementById('vacationPeriodColor').value = period.colorCode || '#E8F5E9';
        } else {
            alert('Fehler beim Laden der Ferienzeit.');
            closeVacationPeriodModal();
        }
    } catch (error) {
        console.error('Error loading vacation period:', error);
        alert('Fehler beim Laden der Ferienzeit.');
        closeVacationPeriodModal();
    }
}

function editVacationPeriod(periodId) {
    showVacationPeriodModal(periodId);
}

function closeVacationPeriodModal() {
    document.getElementById('vacationPeriodModal').style.display = 'none';
    document.getElementById('vacationPeriodForm').reset();
}

async function saveVacationPeriod(event) {
    event.preventDefault();
    
    const periodId = document.getElementById('vacationPeriodId').value;
    const isEdit = periodId !== '';
    
    const data = {
        name: document.getElementById('vacationPeriodName').value,
        startDate: document.getElementById('vacationPeriodStartDate').value,
        endDate: document.getElementById('vacationPeriodEndDate').value,
        colorCode: document.getElementById('vacationPeriodColor').value
    };
    
    try {
        const url = isEdit 
            ? `${API_BASE}/vacation-periods/${periodId}`
            : `${API_BASE}/vacation-periods`;
        
        const method = isEdit ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            closeVacationPeriodModal();
            loadVacationPeriods();
            // Reload schedule to show updated vacation periods
            loadSchedule();
            alert(isEdit ? 'Ferienzeit erfolgreich aktualisiert!' : 'Ferienzeit erfolgreich hinzugefügt!');
        } else {
            const error = await response.json();
            alert(`Fehler: ${error.error || 'Unbekannter Fehler'}`);
        }
    } catch (error) {
        console.error('Error saving vacation period:', error);
        alert('Fehler beim Speichern der Ferienzeit.');
    }
}

async function deleteVacationPeriod(periodId, periodName) {
    if (!hasRole('Admin')) {
        alert('Nur Administratoren können Ferienzeiten löschen.');
        return;
    }
    
    if (!confirm(`Möchten Sie die Ferienzeit "${periodName}" wirklich löschen?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/vacation-periods/${periodId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (response.ok) {
            loadVacationPeriods();
            // Reload schedule to remove deleted vacation period
            loadSchedule();
            alert('Ferienzeit erfolgreich gelöscht!');
        } else {
            const error = await response.json();
            alert(`Fehler: ${error.error || 'Unbekannter Fehler'}`);
        }
    } catch (error) {
        console.error('Error deleting vacation period:', error);
        alert('Fehler beim Löschen der Ferienzeit.');
    }
}

// ============================================================================
// SHIFT TYPE MANAGEMENT FUNCTIONS
// ============================================================================

async function loadShiftTypesAdmin() {
    try {
        const response = await fetch(`${API_BASE}/shifttypes`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Failed to load shift types');
        }
        
        const shiftTypes = await response.json();
        displayShiftTypes(shiftTypes);
    } catch (error) {
        console.error('Error loading shift types:', error);
        document.getElementById('shift-types-content').innerHTML = '<p class="error">Fehler beim Laden der Schichttypen.</p>';
    }
}

function displayShiftTypes(shiftTypes) {
    const container = document.getElementById('shift-types-content');
    
    if (shiftTypes.length === 0) {
        container.innerHTML = '<p class="info">Keine Schichttypen vorhanden. Klicken Sie auf "+ Schichttyp hinzufügen" um einen neuen Schichttyp anzulegen.</p>';
        return;
    }
    
    let html = '<table class="data-table"><thead><tr>';
    html += '<th>Kürzel</th><th>Name</th><th>Zeiten</th><th>Tagesstunden</th><th>Wochenstunden</th><th>Arbeitstage</th><th>Farbe</th><th>Status</th><th>Aktionen</th>';
    html += '</tr></thead><tbody>';
    
    shiftTypes.forEach(shift => {
        const isActive = shift.isActive !== false;
        const statusBadge = isActive ? '<span class="badge badge-success">Aktiv</span>' : '<span class="badge badge-secondary">Inaktiv</span>';
        
        // Build working days display
        const days = [];
        if (shift.worksMonday) days.push('Mo');
        if (shift.worksTuesday) days.push('Di');
        if (shift.worksWednesday) days.push('Mi');
        if (shift.worksThursday) days.push('Do');
        if (shift.worksFriday) days.push('Fr');
        if (shift.worksSaturday) days.push('Sa');
        if (shift.worksSunday) days.push('So');
        const workDays = days.length > 0 ? days.join(', ') : 'Keine';
        
        html += '<tr>';
        html += `<td><span class="shift-badge" style="background-color: ${shift.colorCode}">${escapeHtml(shift.code)}</span></td>`;
        html += `<td>${escapeHtml(shift.name)}</td>`;
        html += `<td>${shift.startTime} - ${shift.endTime}</td>`;
        html += `<td>${shift.durationHours}h</td>`;
        html += `<td>${shift.weeklyWorkingHours || 40.0}h</td>`;
        html += `<td><small>${workDays}</small></td>`;
        html += `<td><div class="color-preview" style="background-color: ${shift.colorCode}"></div></td>`;
        html += `<td>${statusBadge}</td>`;
        html += '<td class="actions">';
        html += `<button onclick="editShiftType(${shift.id})" class="btn-small btn-secondary">✏️ Bearbeiten</button> `;
        html += `<button onclick="showShiftTypeTeamsModal(${shift.id}, '${escapeHtml(shift.code)}')" class="btn-small btn-secondary">👥 Teams</button> `;
        html += `<button onclick="showShiftTypeRelationshipsModal(${shift.id}, '${escapeHtml(shift.code)}')" class="btn-small btn-secondary">🔗 Reihenfolge</button> `;
        html += `<button onclick="deleteShiftType(${shift.id}, '${escapeHtml(shift.code)}')" class="btn-small btn-danger">🗑️ Löschen</button>`;
        html += '</td>';
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

function showShiftTypeModal(shiftTypeId = null) {
    const modal = document.getElementById('shiftTypeModal');
    const title = document.getElementById('shiftTypeModalTitle');
    const form = document.getElementById('shiftTypeForm');
    
    form.reset();
    document.getElementById('shiftTypeId').value = '';
    
    if (shiftTypeId) {
        title.textContent = 'Schichttyp bearbeiten';
        loadShiftTypeForEdit(shiftTypeId);
    } else {
        title.textContent = 'Schichttyp hinzufügen';
    }
    
    modal.style.display = 'block';
}

async function loadShiftTypeForEdit(shiftTypeId) {
    try {
        const response = await fetch(`${API_BASE}/shifttypes/${shiftTypeId}`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Failed to load shift type');
        }
        
        const shiftType = await response.json();
        
        document.getElementById('shiftTypeId').value = shiftType.id;
        document.getElementById('shiftTypeCode').value = shiftType.code;
        document.getElementById('shiftTypeName').value = shiftType.name;
        document.getElementById('shiftTypeStartTime').value = shiftType.startTime;
        document.getElementById('shiftTypeEndTime').value = shiftType.endTime;
        document.getElementById('shiftTypeDuration').value = shiftType.durationHours;
        document.getElementById('shiftTypeColor').value = shiftType.colorCode;
        document.getElementById('shiftTypeMonday').checked = shiftType.worksMonday !== false;
        document.getElementById('shiftTypeTuesday').checked = shiftType.worksTuesday !== false;
        document.getElementById('shiftTypeWednesday').checked = shiftType.worksWednesday !== false;
        document.getElementById('shiftTypeThursday').checked = shiftType.worksThursday !== false;
        document.getElementById('shiftTypeFriday').checked = shiftType.worksFriday !== false;
        document.getElementById('shiftTypeSaturday').checked = shiftType.worksSaturday === true;
        document.getElementById('shiftTypeSunday').checked = shiftType.worksSunday === true;
        document.getElementById('shiftTypeWeeklyHours').value = shiftType.weeklyWorkingHours || 40.0;
        document.getElementById('shiftTypeMinStaffWeekday').value = shiftType.minStaffWeekday || 3;
        document.getElementById('shiftTypeMaxStaffWeekday').value = shiftType.maxStaffWeekday || 5;
        document.getElementById('shiftTypeMinStaffWeekend').value = shiftType.minStaffWeekend || 2;
        document.getElementById('shiftTypeMaxStaffWeekend').value = shiftType.maxStaffWeekend || 3;
        document.getElementById('shiftTypeIsActive').checked = shiftType.isActive !== false;
    } catch (error) {
        console.error('Error loading shift type:', error);
        alert('Fehler beim Laden des Schichttyps.');
        closeShiftTypeModal();
    }
}

function editShiftType(shiftTypeId) {
    showShiftTypeModal(shiftTypeId);
}

function closeShiftTypeModal() {
    document.getElementById('shiftTypeModal').style.display = 'none';
}

async function saveShiftType(event) {
    event.preventDefault();
    
    const shiftTypeId = document.getElementById('shiftTypeId').value;
    const minStaffWeekday = parseInt(document.getElementById('shiftTypeMinStaffWeekday').value);
    const maxStaffWeekday = parseInt(document.getElementById('shiftTypeMaxStaffWeekday').value);
    const minStaffWeekend = parseInt(document.getElementById('shiftTypeMinStaffWeekend').value);
    const maxStaffWeekend = parseInt(document.getElementById('shiftTypeMaxStaffWeekend').value);
    
    // Validate staffing requirements
    if (minStaffWeekday > maxStaffWeekday) {
        alert('Fehler: Minimale Personalstärke an Wochentagen darf nicht größer sein als die maximale Personalstärke.');
        return;
    }
    if (minStaffWeekend > maxStaffWeekend) {
        alert('Fehler: Minimale Personalstärke am Wochenende darf nicht größer sein als die maximale Personalstärke.');
        return;
    }
    
    const data = {
        code: document.getElementById('shiftTypeCode').value.trim().toUpperCase(),
        name: document.getElementById('shiftTypeName').value.trim(),
        startTime: document.getElementById('shiftTypeStartTime').value,
        endTime: document.getElementById('shiftTypeEndTime').value,
        durationHours: parseFloat(document.getElementById('shiftTypeDuration').value),
        colorCode: document.getElementById('shiftTypeColor').value,
        worksMonday: document.getElementById('shiftTypeMonday').checked,
        worksTuesday: document.getElementById('shiftTypeTuesday').checked,
        worksWednesday: document.getElementById('shiftTypeWednesday').checked,
        worksThursday: document.getElementById('shiftTypeThursday').checked,
        worksFriday: document.getElementById('shiftTypeFriday').checked,
        worksSaturday: document.getElementById('shiftTypeSaturday').checked,
        worksSunday: document.getElementById('shiftTypeSunday').checked,
        weeklyWorkingHours: parseFloat(document.getElementById('shiftTypeWeeklyHours').value),
        minStaffWeekday: minStaffWeekday,
        maxStaffWeekday: maxStaffWeekday,
        minStaffWeekend: minStaffWeekend,
        maxStaffWeekend: maxStaffWeekend,
        isActive: document.getElementById('shiftTypeIsActive').checked
    };
    
    try {
        const url = shiftTypeId ? `${API_BASE}/shifttypes/${shiftTypeId}` : `${API_BASE}/shifttypes`;
        const method = shiftTypeId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert(shiftTypeId ? 'Schichttyp erfolgreich aktualisiert!' : 'Schichttyp erfolgreich erstellt!');
            closeShiftTypeModal();
            loadShiftTypesAdmin();
        } else {
            alert(`Fehler: ${result.error || 'Unbekannter Fehler'}`);
        }
    } catch (error) {
        console.error('Error saving shift type:', error);
        alert('Fehler beim Speichern des Schichttyps.');
    }
}

async function deleteShiftType(shiftTypeId, shiftCode) {
    if (!confirm(`Möchten Sie den Schichttyp "${shiftCode}" wirklich löschen?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/shifttypes/${shiftTypeId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert('Schichttyp erfolgreich gelöscht!');
            loadShiftTypesAdmin();
        } else {
            alert(`Fehler: ${result.error || 'Unbekannter Fehler'}`);
        }
    } catch (error) {
        console.error('Error deleting shift type:', error);
        alert('Fehler beim Löschen des Schichttyps.');
    }
}

// Team-Shift Assignment Functions
async function showShiftTypeTeamsModal(shiftTypeId, shiftCode) {
    const modal = document.getElementById('shiftTypeTeamsModal');
    const title = document.getElementById('shiftTypeTeamsModalTitle');
    
    title.textContent = `Teams für Schicht "${shiftCode}" zuweisen`;
    document.getElementById('shiftTypeTeamsId').value = shiftTypeId;
    
    modal.style.display = 'block';
    
    await loadShiftTypeTeams(shiftTypeId);
}

async function loadShiftTypeTeams(shiftTypeId) {
    try {
        // Load all non-virtual teams
        const teamsResponse = await fetch(`${API_BASE}/teams`, {
            credentials: 'include'
        });
        
        if (!teamsResponse.ok) {
            throw new Error('Failed to load teams');
        }
        
        const allTeams = await teamsResponse.json();
        const nonVirtualTeams = allTeams.filter(t => !t.isVirtual);
        
        // Load assigned teams for this shift type
        const assignedResponse = await fetch(`${API_BASE}/shifttypes/${shiftTypeId}/teams`, {
            credentials: 'include'
        });
        
        if (!assignedResponse.ok) {
            throw new Error('Failed to load assigned teams');
        }
        
        const assignedTeams = await assignedResponse.json();
        const assignedTeamIds = assignedTeams.map(t => t.id);
        
        // Display checkboxes
        const container = document.getElementById('shiftTypeTeamsList');
        let html = '';
        
        nonVirtualTeams.forEach(team => {
            const isChecked = assignedTeamIds.includes(team.id);
            html += '<div class="checkbox-item">';
            html += `<label><input type="checkbox" name="team-${team.id}" value="${team.id}" ${isChecked ? 'checked' : ''}> ${escapeHtml(team.name)}</label>`;
            html += '</div>';
        });
        
        container.innerHTML = html || '<p>Keine Teams verfügbar.</p>';
    } catch (error) {
        console.error('Error loading shift type teams:', error);
        document.getElementById('shiftTypeTeamsList').innerHTML = '<p class="error">Fehler beim Laden der Teams.</p>';
    }
}

function closeShiftTypeTeamsModal() {
    document.getElementById('shiftTypeTeamsModal').style.display = 'none';
}

async function saveShiftTypeTeams(event) {
    event.preventDefault();
    
    const shiftTypeId = document.getElementById('shiftTypeTeamsId').value;
    const checkboxes = document.querySelectorAll('#shiftTypeTeamsList input[type="checkbox"]');
    const teamIds = Array.from(checkboxes)
        .filter(cb => cb.checked)
        .map(cb => parseInt(cb.value));
    
    try {
        const response = await fetch(`${API_BASE}/shifttypes/${shiftTypeId}/teams`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ teamIds })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert('Team-Zuweisungen erfolgreich gespeichert!');
            closeShiftTypeTeamsModal();
        } else {
            alert(`Fehler: ${result.error || 'Unbekannter Fehler'}`);
        }
    } catch (error) {
        console.error('Error saving shift type teams:', error);
        alert('Fehler beim Speichern der Team-Zuweisungen.');
    }
}

// Shift Type Relationships Functions
async function showShiftTypeRelationshipsModal(shiftTypeId, shiftCode) {
    const modal = document.getElementById('shiftTypeRelationshipsModal');
    const title = document.getElementById('shiftTypeRelationshipsModalTitle');
    
    title.textContent = `Schichtreihenfolge für "${shiftCode}" festlegen`;
    document.getElementById('shiftTypeRelationshipsId').value = shiftTypeId;
    
    modal.style.display = 'block';
    
    await loadShiftTypeRelationships(shiftTypeId);
}

async function loadShiftTypeRelationships(shiftTypeId) {
    try {
        // Load all shift types
        const allShiftsResponse = await fetch(`${API_BASE}/shifttypes`, {
            credentials: 'include'
        });
        
        if (!allShiftsResponse.ok) {
            throw new Error('Failed to load shift types');
        }
        
        const allShifts = await allShiftsResponse.json();
        const otherShifts = allShifts.filter(s => s.id != shiftTypeId);
        
        // Load existing relationships
        const relResponse = await fetch(`${API_BASE}/shifttypes/${shiftTypeId}/relationships`, {
            credentials: 'include'
        });
        
        if (!relResponse.ok) {
            throw new Error('Failed to load relationships');
        }
        
        const relationships = await relResponse.json();
        const relatedIds = relationships.map(r => r.id);
        
        // Display sortable list
        const container = document.getElementById('shiftTypeRelationshipsList');
        let html = '';
        
        // First add existing relationships in order
        relationships.forEach(rel => {
            html += '<div class="sortable-item" data-shift-id="' + rel.id + '">';
            html += '<span class="drag-handle">☰</span>';
            html += `<span class="shift-badge" style="background-color: ${rel.colorCode}">${escapeHtml(rel.code)}</span>`;
            html += `<span>${escapeHtml(rel.name)}</span>`;
            html += '</div>';
        });
        
        // Then add unrelated shifts as checkboxes
        const unrelatedShifts = otherShifts.filter(s => !relatedIds.includes(s.id));
        if (unrelatedShifts.length > 0) {
            html += '<div class="form-group" style="margin-top: 20px;"><label>Weitere Schichten hinzufügen:</label></div>';
            unrelatedShifts.forEach(shift => {
                html += '<div class="checkbox-item">';
                html += `<label><input type="checkbox" name="related-shift-${shift.id}" value="${shift.id}">`;
                html += `<span class="shift-badge" style="background-color: ${shift.colorCode}">${escapeHtml(shift.code)}</span> ${escapeHtml(shift.name)}`;
                html += '</label></div>';
            });
        }
        
        container.innerHTML = html || '<p>Keine weiteren Schichten verfügbar.</p>';
        
        // Make sortable (simple drag and drop)
        makeSortable();
    } catch (error) {
        console.error('Error loading shift type relationships:', error);
        document.getElementById('shiftTypeRelationshipsList').innerHTML = '<p class="error">Fehler beim Laden der Beziehungen.</p>';
    }
}

function makeSortable() {
    const container = document.getElementById('shiftTypeRelationshipsList');
    const items = container.querySelectorAll('.sortable-item');
    
    items.forEach(item => {
        item.draggable = true;
        
        item.addEventListener('dragstart', (e) => {
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/html', item.innerHTML);
            item.classList.add('dragging');
        });
        
        item.addEventListener('dragend', () => {
            item.classList.remove('dragging');
        });
        
        item.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            
            const dragging = container.querySelector('.dragging');
            const afterElement = getDragAfterElement(container, e.clientY);
            
            if (afterElement == null) {
                container.appendChild(dragging);
            } else {
                container.insertBefore(dragging, afterElement);
            }
        });
    });
}

function getDragAfterElement(container, y) {
    const draggableElements = [...container.querySelectorAll('.sortable-item:not(.dragging)')];
    
    return draggableElements.reduce((closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        
        if (offset < 0 && offset > closest.offset) {
            return { offset: offset, element: child };
        } else {
            return closest;
        }
    }, { offset: Number.NEGATIVE_INFINITY }).element;
}

function closeShiftTypeRelationshipsModal() {
    document.getElementById('shiftTypeRelationshipsModal').style.display = 'none';
}

async function saveShiftTypeRelationships(event) {
    event.preventDefault();
    
    const shiftTypeId = document.getElementById('shiftTypeRelationshipsId').value;
    const container = document.getElementById('shiftTypeRelationshipsList');
    
    // Get sorted items
    const sortedItems = container.querySelectorAll('.sortable-item');
    const relationships = Array.from(sortedItems).map((item, index) => ({
        shiftTypeId: parseInt(item.dataset.shiftId),
        displayOrder: index + 1
    }));
    
    // Get newly selected items
    const checkboxes = container.querySelectorAll('input[type="checkbox"]:checked');
    checkboxes.forEach((cb, index) => {
        relationships.push({
            shiftTypeId: parseInt(cb.value),
            displayOrder: relationships.length + 1
        });
    });
    
    try {
        const response = await fetch(`${API_BASE}/shifttypes/${shiftTypeId}/relationships`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ relationships })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert('Schichtreihenfolge erfolgreich gespeichert!');
            closeShiftTypeRelationshipsModal();
        } else {
            alert(`Fehler: ${result.error || 'Unbekannter Fehler'}`);
        }
    } catch (error) {
        console.error('Error saving shift type relationships:', error);
        alert('Fehler beim Speichern der Schichtreihenfolge.');
    }
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
            closeEditShiftModal();
            await loadSchedule();
            alert('Schicht erfolgreich gelöscht!');
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
        const entityNameTranslated = getEntityNameTranslation(log.entityName);
        
        html += '<tr>';
        html += `<td>${timestamp}</td>`;
        html += `<td>${escapeHtml(log.userName)}</td>`;
        html += `<td>${actionBadge}</td>`;
        html += `<td>${escapeHtml(entityNameTranslated)} (ID: ${escapeHtml(log.entityId)})</td>`;
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
        case 'BulkUpdate':
            return '<span class="badge badge-info">Mehrfach-Änderung</span>';
        default:
            return `<span class="badge">${escapeHtml(action)}</span>`;
    }
}

function getEntityNameTranslation(entityName) {
    const translations = {
        'Employee': 'Mitarbeiter',
        'Team': 'Team',
        'ShiftType': 'Schichttyp',
        'ShiftAssignment': 'Schichtzuweisung',
        'Absence': 'Abwesenheit',
        'VacationPeriod': 'Ferienzeit',
        'VacationRequest': 'Urlaubsantrag',
        'VacationYearApproval': 'Jahresurlaubsgenehmigung',
        'ShiftExchange': 'Diensttausch',
        'TeamShiftAssignment': 'Team-Schicht-Zuweisung',
        'ShiftTypeRelationship': 'Schichttyp-Beziehung'
    };
    
    if (!translations[entityName]) {
        console.warn(`Missing translation for entity: ${entityName}`);
    }
    
    return translations[entityName] || entityName;
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
    if (tabName === 'audit-logs') {
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
        html += `<td>${escapeHtml(getEntityNameTranslation(log.entityName))}</td>`;
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

// ============================================
// Multi-Select Mode for Batch Editing
// ============================================

/**
 * Toggle multi-select mode for batch editing shifts
 */
function toggleMultiSelectMode() {
    multiSelectMode = !multiSelectMode;
    selectedShifts.clear();
    
    // Update UI button states
    const toggleBtn = document.getElementById('multiSelectToggleBtn');
    const bulkEditBtn = document.getElementById('bulkEditBtn');
    const clearSelectionBtn = document.getElementById('clearSelectionBtn');
    
    if (toggleBtn) {
        toggleBtn.textContent = multiSelectMode ? '✓ Mehrfachauswahl aktiv' : '☑ Mehrfachauswahl';
        toggleBtn.classList.toggle('btn-active', multiSelectMode);
    }
    
    if (bulkEditBtn) {
        bulkEditBtn.style.display = multiSelectMode ? 'inline-block' : 'none';
    }
    
    if (clearSelectionBtn) {
        clearSelectionBtn.style.display = multiSelectMode ? 'inline-block' : 'none';
    }
    
    // Update counter
    updateSelectionCounter();
    
    // Reload the schedule to update shift badges
    loadSchedule();
}

/**
 * Toggle selection of a single shift
 * @param {number} shiftId - The shift ID to toggle
 */
function toggleShiftSelection(shiftId) {
    if (!multiSelectMode) {
        return;
    }
    
    if (selectedShifts.has(shiftId)) {
        selectedShifts.delete(shiftId);
    } else {
        selectedShifts.add(shiftId);
    }
    
    // Reload the schedule to update all shift badges
    // NOTE: This could be optimized to only update visual state without full reload,
    // but full reload ensures consistent state and is simpler for initial implementation
    loadSchedule();
    
    // Update selection counter
    updateSelectionCounter();
}

/**
 * Clear all selected shifts
 */
function clearShiftSelection() {
    selectedShifts.clear();
    loadSchedule();
    updateSelectionCounter();
}

/**
 * Update the selection counter display
 */
function updateSelectionCounter() {
    const counter = document.getElementById('selectionCounter');
    if (counter) {
        const count = selectedShifts.size;
        counter.textContent = count > 0 ? `${count} Schicht${count !== 1 ? 'en' : ''} ausgewählt` : '';
    }
}

/**
 * Open bulk edit modal for selected shifts
 */
async function showBulkEditModal() {
    if (selectedShifts.size === 0) {
        alert('Bitte wählen Sie mindestens eine Schicht aus.');
        return;
    }
    
    if (!canPlanShifts()) {
        alert('Sie haben keine Berechtigung, Schichten zu bearbeiten.');
        return;
    }
    
    // Load employees and shift types if not already loaded
    await loadEmployees();
    if (allShiftTypes.length === 0) {
        await loadShiftTypes();
    }
    
    // Get details of selected shifts
    const selectedShiftDetails = Array.from(selectedShifts).map(id => 
        allShifts.find(s => s.id === id)
    ).filter(s => s !== undefined);
    
    // Populate the bulk edit modal
    document.getElementById('bulkEditShiftCount').textContent = selectedShifts.size;
    
    // Populate employee dropdown
    const employeeSelect = document.getElementById('bulkEditEmployeeId');
    employeeSelect.innerHTML = '<option value="">Keine Änderung</option>';
    cachedEmployees.forEach(emp => {
        const option = document.createElement('option');
        option.value = emp.id;
        const teamInfo = emp.teamName ? ` (${emp.teamName})` : '';
        const funktionInfo = emp.funktion ? ` - ${emp.funktion}` : '';
        option.textContent = `${emp.vorname} ${emp.name} (PN: ${emp.personalnummer})${teamInfo}${funktionInfo}`;
        employeeSelect.appendChild(option);
    });
    
    // Populate shift type dropdown
    const shiftTypeSelect = document.getElementById('bulkEditShiftTypeId');
    shiftTypeSelect.innerHTML = '<option value="">Keine Änderung</option>';
    allShiftTypes.forEach(type => {
        const option = document.createElement('option');
        option.value = type.id;
        option.textContent = `${type.name} (${type.code})`;
        shiftTypeSelect.appendChild(option);
    });
    
    // Show selected shifts summary
    const summaryDiv = document.getElementById('bulkEditSummary');
    let summaryHtml = '<div style="max-height: 200px; overflow-y: auto; margin: 10px 0; padding: 10px; background: #f5f5f5; border-radius: 4px;">';
    summaryHtml += '<strong>Ausgewählte Schichten:</strong><ul style="margin: 5px 0; padding-left: 20px;">';
    
    selectedShiftDetails.forEach(shift => {
        const date = new Date(shift.date).toLocaleDateString('de-DE');
        summaryHtml += `<li>${shift.employeeName} - ${date} - ${shift.shiftCode}</li>`;
    });
    
    summaryHtml += '</ul></div>';
    summaryDiv.innerHTML = summaryHtml;
    
    // Clear form
    document.getElementById('bulkEditForm').reset();
    document.getElementById('bulkEditWarning').style.display = 'none';
    
    // Show modal
    document.getElementById('bulkEditModal').style.display = 'block';
}

/**
 * Close bulk edit modal
 */
function closeBulkEditModal() {
    document.getElementById('bulkEditModal').style.display = 'none';
    document.getElementById('bulkEditForm').reset();
    document.getElementById('bulkEditWarning').style.display = 'none';
}

/**
 * Save bulk edit changes
 */
async function saveBulkEdit(event) {
    event.preventDefault();
    
    const employeeId = document.getElementById('bulkEditEmployeeId').value;
    const shiftTypeId = document.getElementById('bulkEditShiftTypeId').value;
    const isFixedChecked = document.getElementById('bulkEditIsFixed').checked;
    const notes = document.getElementById('bulkEditNotes').value.trim();
    
    // Build the changes object
    const changes = {};
    if (employeeId) changes.employeeId = parseInt(employeeId);
    if (shiftTypeId) changes.shiftTypeId = parseInt(shiftTypeId);
    if (isFixedChecked) changes.isFixed = true;
    if (notes) changes.notes = notes;
    
    // Validate that at least one change is specified
    if (Object.keys(changes).length === 0) {
        alert('Bitte wählen Sie mindestens eine Änderung aus.');
        return;
    }
    
    // Confirm the bulk edit
    if (!confirm(`Möchten Sie ${selectedShifts.size} Schicht${selectedShifts.size !== 1 ? 'en' : ''} wirklich ändern?`)) {
        return;
    }
    
    try {
        // Send bulk update request
        const response = await fetch(`${API_BASE}/shifts/assignments/bulk`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                shiftIds: Array.from(selectedShifts),
                changes: changes
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            alert(`Erfolgreich ${result.updated || selectedShifts.size} Schicht${(result.updated || selectedShifts.size) !== 1 ? 'en' : ''} aktualisiert!`);
            closeBulkEditModal();
            
            // Deactivate multi-select mode if it's active
            if (multiSelectMode) {
                toggleMultiSelectMode();
            }
        } else if (response.status === 400) {
            const error = await response.json();
            document.getElementById('bulkEditWarningText').textContent = error.error || 'Validierungsfehler';
            document.getElementById('bulkEditWarning').style.display = 'block';
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an.');
        } else if (response.status === 403) {
            alert('Sie haben keine Berechtigung für diese Aktion.');
        } else {
            alert('Fehler beim Aktualisieren der Schichten.');
        }
    } catch (error) {
        console.error('Error saving bulk edit:', error);
        alert(`Fehler: ${error.message}`);
    }
}


// ============================================================================
// NOTIFICATION SYSTEM
// ============================================================================

let currentNotificationFilter = 'unread';

/**
 * Load notification count and update badge
 */
async function loadNotificationCount() {
    try {
        const response = await fetch(`${API_BASE}/notifications/count`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            const badge = document.getElementById('notification-badge');
            
            if (data.count > 0) {
                badge.textContent = data.count > 99 ? '99+' : data.count;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Error loading notification count:', error);
    }
}

/**
 * Show notification modal
 */
function showNotificationModal() {
    document.getElementById('notificationModal').style.display = 'block';
    currentNotificationFilter = 'unread';
    loadNotifications('unread');
}

/**
 * Close notification modal
 */
function closeNotificationModal() {
    document.getElementById('notificationModal').style.display = 'none';
}

/**
 * Filter notifications
 */
function filterNotifications(filter) {
    currentNotificationFilter = filter;
    
    // Update button states
    document.getElementById('filter-all').classList.toggle('active', filter === 'all');
    document.getElementById('filter-unread').classList.toggle('active', filter === 'unread');
    
    loadNotifications(filter);
}

/**
 * Load notifications
 */
async function loadNotifications(filter = 'unread') {
    const listContainer = document.getElementById('notification-list');
    listContainer.innerHTML = '<p class="loading">Lade Benachrichtigungen...</p>';
    
    try {
        const unreadOnly = filter === 'unread';
        const response = await fetch(`${API_BASE}/notifications?unreadOnly=${unreadOnly}&limit=50`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const notifications = await response.json();
            displayNotifications(notifications);
        } else if (response.status === 401) {
            listContainer.innerHTML = '<p class="notification-empty">Bitte melden Sie sich an.</p>';
        } else if (response.status === 403) {
            listContainer.innerHTML = '<p class="notification-empty">Keine Berechtigung.</p>';
        } else {
            listContainer.innerHTML = '<p class="notification-empty">Fehler beim Laden der Benachrichtigungen.</p>';
        }
    } catch (error) {
        console.error('Error loading notifications:', error);
        listContainer.innerHTML = '<p class="notification-empty">Fehler beim Laden der Benachrichtigungen.</p>';
    }
}

/**
 * Display notifications in the list
 */
function displayNotifications(notifications) {
    const listContainer = document.getElementById('notification-list');
    
    if (notifications.length === 0) {
        listContainer.innerHTML = `
            <div class="notification-empty">
                <div class="notification-empty-icon">✅</div>
                <p>Keine Benachrichtigungen vorhanden.</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    notifications.forEach(notification => {
        const unreadClass = notification.isRead ? '' : 'unread';
        const severityClass = `severity-${notification.severity}`;
        const date = new Date(notification.createdAt).toLocaleString('de-DE');
        
        html += `
            <div class="notification-item ${unreadClass} ${severityClass}">
                <div class="notification-item-header">
                    <h3 class="notification-item-title">${escapeHtml(notification.title)}</h3>
                    <span class="notification-severity ${notification.severity}">${notification.severity}</span>
                </div>
                <div class="notification-item-message">${escapeHtml(notification.message)}</div>
                <div class="notification-item-meta">
                    <span class="notification-item-date">${date}</span>
                    <div class="notification-item-actions">
                        ${!notification.isRead ? `
                            <button class="btn-mark-read" onclick="markNotificationRead(${notification.id})">
                                ✓ Als gelesen markieren
                            </button>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    });
    
    listContainer.innerHTML = html;
}

/**
 * Mark single notification as read
 */
async function markNotificationRead(notificationId) {
    try {
        const response = await fetch(`${API_BASE}/notifications/${notificationId}/read`, {
            method: 'POST',
            credentials: 'include'
        });
        
        if (response.ok) {
            // Reload notifications with current filter
            loadNotifications(currentNotificationFilter);
            // Update notification count
            loadNotificationCount();
        } else {
            alert('Fehler beim Markieren der Benachrichtigung.');
        }
    } catch (error) {
        console.error('Error marking notification as read:', error);
        alert('Fehler beim Markieren der Benachrichtigung.');
    }
}

/**
 * Mark all notifications as read
 */
async function markAllNotificationsRead() {
    if (!confirm('Möchten Sie wirklich alle Benachrichtigungen als gelesen markieren?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/notifications/mark-all-read`, {
            method: 'POST',
            credentials: 'include'
        });
        
        if (response.ok) {
            const result = await response.json();
            alert(`${result.count} Benachrichtigung${result.count !== 1 ? 'en' : ''} als gelesen markiert.`);
            // Reload notifications
            loadNotifications(currentNotificationFilter);
            // Update notification count
            loadNotificationCount();
        } else {
            alert('Fehler beim Markieren der Benachrichtigungen.');
        }
    } catch (error) {
        console.error('Error marking all notifications as read:', error);
        alert('Fehler beim Markieren der Benachrichtigungen.');
    }
}

/**
 * Helper function to escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Poll for new notifications every 60 seconds when user is logged in
const NOTIFICATION_POLL_INTERVAL_MS = 60000; // 60 seconds
let notificationPollInterval = null;

function startNotificationPolling() {
    // Clear any existing interval
    if (notificationPollInterval) {
        clearInterval(notificationPollInterval);
    }
    
    // Load initial count
    loadNotificationCount();
    
    // Poll every NOTIFICATION_POLL_INTERVAL_MS
    notificationPollInterval = setInterval(() => {
        loadNotificationCount();
    }, NOTIFICATION_POLL_INTERVAL_MS);
}

function stopNotificationPolling() {
    if (notificationPollInterval) {
        clearInterval(notificationPollInterval);
        notificationPollInterval = null;
    }
}

// ============================================================================
// VACATION YEAR PLAN FUNCTIONS
// ============================================================================

/**
 * Initialize the vacation year plan view
 */
function initVacationYearPlan() {
    const yearSelect = document.getElementById('vacationYearSelect');
    if (!yearSelect) return;
    
    // Populate years (current year +/- 5 years)
    const currentYear = new Date().getFullYear();
    yearSelect.innerHTML = '';
    for (let year = currentYear - 2; year <= currentYear + 5; year++) {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        if (year === currentYear) {
            option.selected = true;
        }
        yearSelect.appendChild(option);
    }
}

/**
 * Load vacation year plan for selected year
 */
async function loadVacationYearPlan() {
    const yearSelect = document.getElementById('vacationYearSelect');
    const year = yearSelect ? parseInt(yearSelect.value) : new Date().getFullYear();
    
    const statusDiv = document.getElementById('vacation-year-plan-status');
    const contentDiv = document.getElementById('vacation-year-plan-content');
    const legendDiv = document.getElementById('vacation-year-plan-legend');
    
    if (!contentDiv) return;
    
    contentDiv.innerHTML = '<p class="loading">Lade Urlaubsjahresplan...</p>';
    statusDiv.innerHTML = '';
    legendDiv.style.display = 'none';
    
    try {
        const response = await fetch(`${API_BASE}/vacationyearplan/${year}`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            
            if (!data.isApproved) {
                statusDiv.innerHTML = '<div class="warning-box"><strong>⚠️ Jahr nicht freigegeben</strong><p>Die Urlaubsdaten für dieses Jahr wurden noch nicht vom Administrator freigegeben.</p></div>';
                contentDiv.innerHTML = '<p>Keine Daten verfügbar.</p>';
                return;
            }
            
            // Show legend
            legendDiv.style.display = 'block';
            
            // Display vacation data
            displayVacationYearPlan(data, year);
            
        } else {
            contentDiv.innerHTML = '<p class="error">Fehler beim Laden des Urlaubsjahresplans.</p>';
        }
    } catch (error) {
        console.error('Error loading vacation year plan:', error);
        contentDiv.innerHTML = '<p class="error">Fehler beim Laden des Urlaubsjahresplans.</p>';
    }
}

/**
 * Display vacation year plan data
 */
function displayVacationYearPlan(data, year) {
    const contentDiv = document.getElementById('vacation-year-plan-content');
    
    // Combine all vacations
    const allVacations = [];
    
    // Add vacation requests
    if (data.vacationRequests && data.vacationRequests.length > 0) {
        allVacations.push(...data.vacationRequests);
    }
    
    // Add absences
    if (data.absences && data.absences.length > 0) {
        allVacations.push(...data.absences);
    }
    
    if (allVacations.length === 0) {
        contentDiv.innerHTML = `<p>Keine Urlaube für ${year} vorhanden.</p>`;
        return;
    }
    
    // Sort by start date
    allVacations.sort((a, b) => new Date(a.startDate) - new Date(b.startDate));
    
    // Group by employee
    const employeeVacations = {};
    allVacations.forEach(vac => {
        if (!employeeVacations[vac.employeeId]) {
            employeeVacations[vac.employeeId] = {
                name: vac.employeeName,
                teamName: vac.teamName,
                vacations: []
            };
        }
        employeeVacations[vac.employeeId].vacations.push(vac);
    });
    
    // Create HTML table
    let html = '<table class="data-table">';
    html += '<thead><tr>';
    html += '<th>Mitarbeiter</th>';
    html += '<th>Team</th>';
    html += '<th>Von</th>';
    html += '<th>Bis</th>';
    html += '<th>Tage</th>';
    html += '<th>Status</th>';
    html += '<th>Notizen</th>';
    html += '</tr></thead><tbody>';
    
    Object.values(employeeVacations).forEach(empData => {
        empData.vacations.forEach((vac, idx) => {
            const startDate = new Date(vac.startDate);
            const endDate = new Date(vac.endDate);
            const days = Math.floor((endDate - startDate) / (1000 * 60 * 60 * 24)) + 1;
            
            // Determine status badge
            let statusBadge = '';
            if (vac.status === 'Genehmigt') {
                statusBadge = '<span class="shift-badge shift-U">Genehmigt</span>';
            } else if (vac.status === 'InBearbeitung') {
                statusBadge = '<span class="shift-badge shift-U-pending">In Genehmigung</span>';
            } else if (vac.status === 'Abgelehnt') {
                statusBadge = '<span class="shift-badge shift-U-rejected">Abgelehnt</span>';
            }
            
            html += '<tr>';
            if (idx === 0) {
                html += `<td rowspan="${empData.vacations.length}">${escapeHtml(empData.name)}</td>`;
                html += `<td rowspan="${empData.vacations.length}">${escapeHtml(empData.teamName || '-')}</td>`;
            }
            html += `<td>${startDate.toLocaleDateString('de-DE')}</td>`;
            html += `<td>${endDate.toLocaleDateString('de-DE')}</td>`;
            html += `<td>${days}</td>`;
            html += `<td>${statusBadge}</td>`;
            html += `<td>${escapeHtml(vac.notes || '-')}</td>`;
            html += '</tr>';
        });
    });
    
    html += '</tbody></table>';
    contentDiv.innerHTML = html;
}

// ============================================================================
// VACATION YEAR APPROVAL ADMIN FUNCTIONS
// ============================================================================

/**
 * Load vacation year approvals (admin only)
 */
async function loadVacationYearApprovals() {
    const contentDiv = document.getElementById('vacation-year-approvals-content');
    if (!contentDiv) return;
    
    contentDiv.innerHTML = '<p class="loading">Lade Freigaben...</p>';
    
    try {
        const response = await fetch(`${API_BASE}/vacationyearapprovals`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const approvals = await response.json();
            displayVacationYearApprovals(approvals);
        } else {
            contentDiv.innerHTML = '<p class="error">Fehler beim Laden der Freigaben.</p>';
        }
    } catch (error) {
        console.error('Error loading vacation year approvals:', error);
        contentDiv.innerHTML = '<p class="error">Fehler beim Laden der Freigaben.</p>';
    }
}

/**
 * Display vacation year approvals table
 */
function displayVacationYearApprovals(approvals) {
    const contentDiv = document.getElementById('vacation-year-approvals-content');
    
    // Generate list of years (current year +/- 5 years)
    const currentYear = new Date().getFullYear();
    const years = [];
    for (let year = currentYear - 2; year <= currentYear + 5; year++) {
        const approval = approvals.find(a => a.year === year);
        years.push({
            year: year,
            isApproved: approval ? approval.isApproved : false,
            approvedBy: approval ? approval.approvedBy : null,
            approvedAt: approval ? approval.approvedAt : null,
            notes: approval ? approval.notes : null
        });
    }
    
    let html = '<table class="data-table">';
    html += '<thead><tr>';
    html += '<th>Jahr</th>';
    html += '<th>Status</th>';
    html += '<th>Freigegeben von</th>';
    html += '<th>Freigegeben am</th>';
    html += '<th>Aktionen</th>';
    html += '</tr></thead><tbody>';
    
    years.forEach(yearData => {
        html += '<tr>';
        html += `<td><strong>${yearData.year}</strong></td>`;
        
        if (yearData.isApproved) {
            html += '<td><span class="shift-badge shift-U">✓ Freigegeben</span></td>';
            html += `<td>${escapeHtml(yearData.approvedBy || '-')}</td>`;
            html += `<td>${yearData.approvedAt ? new Date(yearData.approvedAt).toLocaleDateString('de-DE') : '-'}</td>`;
            html += `<td><button onclick="toggleYearApproval(${yearData.year}, false)" class="btn-small btn-danger">Freigabe zurückziehen</button></td>`;
        } else {
            html += '<td><span class="shift-badge shift-U-rejected">✗ Nicht freigegeben</span></td>';
            html += '<td>-</td>';
            html += '<td>-</td>';
            html += `<td><button onclick="toggleYearApproval(${yearData.year}, true)" class="btn-small btn-primary">Freigeben</button></td>`;
        }
        
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    contentDiv.innerHTML = html;
}

/**
 * Toggle year approval status
 */
async function toggleYearApproval(year, approve) {
    const action = approve ? 'freigeben' : 'zurückziehen';
    
    if (!confirm(`Möchten Sie die Anzeige der Urlaubsdaten für das Jahr ${year} wirklich ${action}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/vacationyearapprovals`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                year: year,
                isApproved: approve
            })
        });
        
        if (response.ok) {
            alert(`Jahr ${year} wurde erfolgreich ${approve ? 'freigegeben' : 'gesperrt'}.`);
            loadVacationYearApprovals();
        } else {
            alert(`Fehler beim ${action} des Jahres.`);
        }
    } catch (error) {
        console.error(`Error toggling year approval:`, error);
        alert(`Fehler beim ${action} des Jahres.`);
    }
}

/**
 * Update approval status UI for current month
 */
async function updateApprovalStatus() {
    const month = document.getElementById('monthSelect').value;
    const year = document.getElementById('monthYearSelect').value;
    
    const statusElement = document.getElementById('approvalStatus');
    const buttonElement = document.getElementById('approvalButton');
    
    if (!statusElement || !buttonElement) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/shifts/plan/approvals/${year}/${month}`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            
            if (data.isApproved) {
                statusElement.textContent = '✓ Freigegeben';
                statusElement.style.backgroundColor = '#4CAF50';
                statusElement.style.color = 'white';
                statusElement.style.display = 'inline-block';
                
                if (isAdmin()) {
                    buttonElement.textContent = 'Freigabe zurückziehen';
                    buttonElement.style.display = 'inline-block';
                }
            } else if (data.exists) {
                statusElement.textContent = '⚠ Nicht freigegeben';
                statusElement.style.backgroundColor = '#FF9800';
                statusElement.style.color = 'white';
                statusElement.style.display = 'inline-block';
                
                if (isAdmin()) {
                    buttonElement.textContent = 'Dienstplan freigeben';
                    buttonElement.style.display = 'inline-block';
                }
            } else {
                // No plan exists for this month
                statusElement.style.display = 'none';
                buttonElement.style.display = 'none';
            }
        } else {
            statusElement.style.display = 'none';
            buttonElement.style.display = 'none';
        }
    } catch (error) {
        console.error('Error checking approval status:', error);
        statusElement.style.display = 'none';
        buttonElement.style.display = 'none';
    }
}

/**
 * Toggle plan approval for current month
 */
async function togglePlanApproval() {
    const month = document.getElementById('monthSelect').value;
    const year = document.getElementById('monthYearSelect').value;
    
    try {
        // Check current status
        const statusResponse = await fetch(`${API_BASE}/shifts/plan/approvals/${year}/${month}`, {
            credentials: 'include'
        });
        
        if (!statusResponse.ok) {
            alert('Fehler beim Abrufen des aktuellen Status.');
            return;
        }
        
        const statusData = await statusResponse.json();
        const currentlyApproved = statusData.isApproved;
        const newApprovalState = !currentlyApproved;
        
        const monthName = new Date(year, month - 1).toLocaleDateString('de-DE', { month: 'long', year: 'numeric' });
        const action = newApprovalState ? 'freigeben' : 'zurückziehen';
        
        if (!confirm(`Möchten Sie den Dienstplan für ${monthName} wirklich ${action}?`)) {
            return;
        }
        
        const response = await fetch(`${API_BASE}/shifts/plan/approvals/${year}/${month}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                isApproved: newApprovalState
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            alert(data.message || `Dienstplan wurde ${action}.`);
            await updateApprovalStatus();
            await loadSchedule();
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an.');
        } else if (response.status === 403) {
            alert('Sie haben keine Berechtigung, Dienstpläne freizugeben.');
        } else {
            const error = await response.json();
            alert(`Fehler: ${error.error || 'Unbekannter Fehler'}`);
        }
    } catch (error) {
        console.error('Error toggling approval:', error);
        alert(`Fehler beim ${action} des Dienstplans.`);
    }
}

/**
 * Check if current user is admin
 */
function isAdmin() {
    const currentUser = sessionStorage.getItem('currentUser');
    if (!currentUser) return false;
    
    try {
        const user = JSON.parse(currentUser);
        return user.roles && user.roles.includes('Admin');
    } catch {
        return false;
    }
}

/**
 * Load shift types for management view
 */
async function loadShiftTypesManagement() {
    try {
        const response = await fetch(`${API_BASE}/shifttypes`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Failed to load shift types');
        }
        
        const shiftTypes = await response.json();
        displayShiftTypesManagement(shiftTypes);
    } catch (error) {
        console.error('Error loading shift types:', error);
        document.getElementById('shift-types-management-content').innerHTML = '<p class="error">Fehler beim Laden der Schichttypen.</p>';
    }
}

/**
 * Display shift types in management view
 */
function displayShiftTypesManagement(shiftTypes) {
    const container = document.getElementById('shift-types-management-content');
    
    if (shiftTypes.length === 0) {
        container.innerHTML = '<p class="info">Keine Schichttypen vorhanden. Klicken Sie auf "+ Schichttyp hinzufügen" um einen neuen Schichttyp anzulegen.</p>';
        return;
    }
    
    let html = '<table class="data-table"><thead><tr>';
    html += '<th>Kürzel</th><th>Name</th><th>Zeiten</th><th>Tagesstunden</th><th>Wochenstunden</th><th>Arbeitstage</th><th>Farbe</th><th>Status</th><th>Aktionen</th>';
    html += '</tr></thead><tbody>';
    
    shiftTypes.forEach(shift => {
        const isActive = shift.isActive !== false;
        const statusBadge = isActive ? '<span class="badge badge-success">Aktiv</span>' : '<span class="badge badge-secondary">Inaktiv</span>';
        
        // Build working days display
        const days = [];
        if (shift.worksMonday) days.push('Mo');
        if (shift.worksTuesday) days.push('Di');
        if (shift.worksWednesday) days.push('Mi');
        if (shift.worksThursday) days.push('Do');
        if (shift.worksFriday) days.push('Fr');
        if (shift.worksSaturday) days.push('Sa');
        if (shift.worksSunday) days.push('So');
        const workDays = days.length > 0 ? days.join(', ') : 'Keine';
        
        html += '<tr>';
        html += `<td><span class="shift-badge" style="background-color: ${shift.colorCode}">${escapeHtml(shift.code)}</span></td>`;
        html += `<td>${escapeHtml(shift.name)}</td>`;
        html += `<td>${shift.startTime} - ${shift.endTime}</td>`;
        html += `<td>${shift.durationHours}h</td>`;
        html += `<td>${shift.weeklyWorkingHours || 40.0}h</td>`;
        html += `<td><small>${workDays}</small></td>`;
        html += `<td><div class="color-preview" style="background-color: ${shift.colorCode}"></div></td>`;
        html += `<td>${statusBadge}</td>`;
        html += '<td class="actions">';
        html += `<button onclick="editShiftType(${shift.id})" class="btn-small btn-secondary">✏️ Bearbeiten</button> `;
        html += `<button onclick="showShiftTypeTeamsModal(${shift.id}, '${escapeHtml(shift.code)}')" class="btn-small btn-secondary">👥 Teams</button> `;
        html += `<button onclick="showShiftTypeRelationshipsModal(${shift.id}, '${escapeHtml(shift.code)}')" class="btn-small btn-secondary">🔗 Reihenfolge</button> `;
        html += `<button onclick="deleteShiftType(${shift.id}, '${escapeHtml(shift.code)}')" class="btn-small btn-danger">🗑️ Löschen</button>`;
        html += '</td>';
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

// Global Settings Management Functions
async function loadGlobalSettings() {
    const container = document.getElementById('global-settings-content');
    container.innerHTML = '<p class="loading">Lade Einstellungen...</p>';
    
    try {
        const response = await fetch(`${API_BASE}/settings/global`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const settings = await response.json();
            displayGlobalSettings(settings);
        } else {
            container.innerHTML = '<p class="error">Fehler beim Laden der Einstellungen.</p>';
        }
    } catch (error) {
        console.error('Error loading global settings:', error);
        container.innerHTML = '<p class="error">Fehler beim Laden der Einstellungen.</p>';
    }
}

function displayGlobalSettings(settings) {
    const container = document.getElementById('global-settings-content');
    
    const isAdmin = hasRole('Admin');
    const readonly = !isAdmin ? 'readonly' : '';
    const disabledClass = !isAdmin ? 'disabled' : '';
    
    let html = '<div class="settings-form">';
    html += '<div class="info-box info">';
    html += '<p>ℹ️ Diese Einstellungen gelten für die automatische Schichtplanung und Validierung.</p>';
    html += '</div>';
    
    html += '<form id="global-settings-form" onsubmit="saveGlobalSettings(event)">';
    
    html += '<div class="form-group">';
    html += '<label for="maxConsecutiveShifts">Maximale aufeinanderfolgende Schichten:</label>';
    html += `<input type="number" id="maxConsecutiveShifts" name="maxConsecutiveShifts" 
             value="${settings.maxConsecutiveShifts || 6}" min="1" max="10" ${readonly} required>`;
    html += '<small>Standard: 6 Schichten (inkl. Wochenenden)</small>';
    html += '</div>';
    
    html += '<div class="form-group">';
    html += '<label for="maxConsecutiveNightShifts">Maximale aufeinanderfolgende Nachtschichten:</label>';
    html += `<input type="number" id="maxConsecutiveNightShifts" name="maxConsecutiveNightShifts" 
             value="${settings.maxConsecutiveNightShifts || 3}" min="1" max="10" ${readonly} required>`;
    html += '<small>Standard: 3 Nachtschichten</small>';
    html += '</div>';
    
    html += '<div class="form-group">';
    html += '<label for="minRestHoursBetweenShifts">Gesetzliche Ruhezeit zwischen Schichten (Stunden):</label>';
    html += `<input type="number" id="minRestHoursBetweenShifts" name="minRestHoursBetweenShifts" 
             value="${settings.minRestHoursBetweenShifts || 11}" min="8" max="24" ${readonly} required>`;
    html += '<small>Standard: 11 Stunden (gesetzlich vorgeschrieben)</small>';
    html += '</div>';
    
    if (settings.modifiedAt) {
        html += '<div class="form-group">';
        html += '<small class="text-muted">Zuletzt geändert: ' + new Date(settings.modifiedAt).toLocaleString('de-DE');
        if (settings.modifiedBy) {
            html += ' von ' + escapeHtml(settings.modifiedBy);
        }
        html += '</small>';
        html += '</div>';
    }
    
    if (isAdmin) {
        html += '<div class="form-actions">';
        html += '<button type="submit" class="btn-primary">💾 Einstellungen speichern</button>';
        html += '</div>';
    }
    
    html += '</form>';
    html += '</div>';
    
    container.innerHTML = html;
}

async function saveGlobalSettings(event) {
    event.preventDefault();
    
    if (!hasRole('Admin')) {
        alert('Nur Administratoren können Einstellungen ändern.');
        return;
    }
    
    const form = document.getElementById('global-settings-form');
    const formData = new FormData(form);
    
    const settings = {
        maxConsecutiveShifts: parseInt(formData.get('maxConsecutiveShifts')),
        maxConsecutiveNightShifts: parseInt(formData.get('maxConsecutiveNightShifts')),
        minRestHoursBetweenShifts: parseInt(formData.get('minRestHoursBetweenShifts'))
    };
    
    try {
        const response = await fetch(`${API_BASE}/settings/global`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(settings)
        });
        
        if (response.ok) {
            alert('Einstellungen erfolgreich gespeichert!');
            loadGlobalSettings(); // Reload to show updated values
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an.');
        } else if (response.status === 403) {
            alert('Sie haben keine Berechtigung für diese Aktion.');
        } else {
            const error = await response.json();
            alert(`Fehler beim Speichern: ${error.error || 'Unbekannter Fehler'}`);
        }
    } catch (error) {
        console.error('Error saving global settings:', error);
        alert(`Fehler: ${error.message}`);
    }
}

/**
 * Load vacation year approvals for absences view
 */
async function loadVacationYearApprovalsAbsence() {
    const contentDiv = document.getElementById('vacation-year-approvals-absence-content');
    if (!contentDiv) return;
    
    contentDiv.innerHTML = '<p class="loading">Lade Freigaben...</p>';
    
    try {
        const response = await fetch(`${API_BASE}/vacationyearapprovals`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const approvals = await response.json();
            displayVacationYearApprovalsAbsence(approvals);
        } else {
            contentDiv.innerHTML = '<p class="error">Fehler beim Laden der Freigaben.</p>';
        }
    } catch (error) {
        console.error('Error loading vacation year approvals:', error);
        contentDiv.innerHTML = '<p class="error">Fehler beim Laden der Freigaben.</p>';
    }
}

/**
 * Display vacation year approvals in absences view
 */
function displayVacationYearApprovalsAbsence(approvals) {
    const contentDiv = document.getElementById('vacation-year-approvals-absence-content');
    
    // Generate list of years (current year +/- 5 years)
    const currentYear = new Date().getFullYear();
    const years = [];
    for (let year = currentYear - 2; year <= currentYear + 5; year++) {
        const approval = approvals.find(a => a.year === year);
        years.push({
            year: year,
            isApproved: approval ? approval.isApproved : false,
            approvedBy: approval ? approval.approvedBy : null,
            approvedAt: approval ? approval.approvedAt : null,
            notes: approval ? approval.notes : null
        });
    }
    
    let html = '<table class="data-table">';
    html += '<thead><tr>';
    html += '<th>Jahr</th>';
    html += '<th>Status</th>';
    html += '<th>Freigegeben von</th>';
    html += '<th>Freigegeben am</th>';
    html += '<th>Aktionen</th>';
    html += '</tr></thead><tbody>';
    
    years.forEach(item => {
        html += '<tr>';
        html += `<td>${item.year}</td>`;
        
        if (item.isApproved) {
            html += '<td><span class="badge badge-success">✓ Freigegeben</span></td>';
        } else {
            html += '<td><span class="badge badge-warning">⊗ Nicht freigegeben</span></td>';
        }
        
        html += `<td>${item.approvedBy || '-'}</td>`;
        html += `<td>${item.approvedAt ? new Date(item.approvedAt).toLocaleDateString('de-DE') : '-'}</td>`;
        html += '<td class="actions">';
        
        if (item.isApproved) {
            html += `<button onclick="toggleYearApprovalAbsence(${item.year}, false)" class="btn-small btn-danger">🔒 Sperren</button>`;
        } else {
            html += `<button onclick="toggleYearApprovalAbsence(${item.year}, true)" class="btn-small btn-success">✓ Freigeben</button>`;
        }
        
        html += '</td>';
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    contentDiv.innerHTML = html;
}

/**
 * Toggle year approval status in absences view
 */
async function toggleYearApprovalAbsence(year, approve) {
    const action = approve ? 'Freigabe' : 'Sperrung';
    
    if (!confirm(`Möchten Sie das Jahr ${year} wirklich ${approve ? 'freigeben' : 'sperren'}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/vacationyearapprovals`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                year: year,
                isApproved: approve
            })
        });
        
        if (response.ok) {
            alert(`Jahr ${year} wurde erfolgreich ${approve ? 'freigegeben' : 'gesperrt'}.`);
            loadVacationYearApprovalsAbsence();
        } else {
            alert(`Fehler beim ${action} des Jahres.`);
        }
    } catch (error) {
        console.error(`Error toggling year approval:`, error);
        alert(`Fehler beim ${action} des Jahres.`);
    }
}

// ============================================================================
// PASSWORD MANAGEMENT FUNCTIONS
// ============================================================================

// Change Password Modal
function showChangePasswordModal() {
    document.getElementById('changePasswordForm').reset();
    document.getElementById('changePasswordError').style.display = 'none';
    document.getElementById('changePasswordSuccess').style.display = 'none';
    document.getElementById('changePasswordModal').style.display = 'block';
}

function closeChangePasswordModal() {
    document.getElementById('changePasswordModal').style.display = 'none';
    document.getElementById('changePasswordForm').reset();
}

async function submitChangePassword(event) {
    event.preventDefault();
    
    const currentPassword = document.getElementById('currentPassword').value;
    const newPassword = document.getElementById('changeNewPassword').value;
    const confirmPassword = document.getElementById('changeConfirmPassword').value;
    
    const errorDiv = document.getElementById('changePasswordError');
    const successDiv = document.getElementById('changePasswordSuccess');
    
    errorDiv.style.display = 'none';
    successDiv.style.display = 'none';
    
    // Validate passwords match
    if (newPassword !== confirmPassword) {
        errorDiv.textContent = 'Die neuen Passwörter stimmen nicht überein.';
        errorDiv.style.display = 'block';
        return;
    }
    
    // Validate password length
    if (newPassword.length < 8) {
        errorDiv.textContent = 'Das neue Passwort muss mindestens 8 Zeichen lang sein.';
        errorDiv.style.display = 'block';
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/auth/change-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                currentPassword: currentPassword,
                newPassword: newPassword
            })
        });
        
        if (response.ok) {
            successDiv.textContent = 'Passwort erfolgreich geändert!';
            successDiv.style.display = 'block';
            document.getElementById('changePasswordForm').reset();
            setTimeout(() => {
                closeChangePasswordModal();
            }, 2000);
        } else {
            const error = await response.json();
            errorDiv.textContent = error.error || 'Fehler beim Ändern des Passworts';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        console.error('Error changing password:', error);
        errorDiv.textContent = 'Fehler beim Ändern des Passworts';
        errorDiv.style.display = 'block';
    }
}

// Forgot Password Modal
function showForgotPasswordModal() {
    closeLoginModal();
    document.getElementById('forgotPasswordForm').reset();
    document.getElementById('forgotPasswordError').style.display = 'none';
    document.getElementById('forgotPasswordSuccess').style.display = 'none';
    document.getElementById('forgotPasswordModal').style.display = 'block';
}

function closeForgotPasswordModal() {
    document.getElementById('forgotPasswordModal').style.display = 'none';
    document.getElementById('forgotPasswordForm').reset();
}

async function submitForgotPassword(event) {
    event.preventDefault();
    
    const email = document.getElementById('forgotPasswordEmail').value;
    
    const errorDiv = document.getElementById('forgotPasswordError');
    const successDiv = document.getElementById('forgotPasswordSuccess');
    
    errorDiv.style.display = 'none';
    successDiv.style.display = 'none';
    
    try {
        const response = await fetch(`${API_BASE}/auth/forgot-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ email: email })
        });
        
        if (response.ok) {
            const data = await response.json();
            successDiv.textContent = data.message || 'Falls die E-Mail-Adresse existiert, wurde eine Anleitung zum Zurücksetzen des Passworts gesendet.';
            successDiv.style.display = 'block';
            document.getElementById('forgotPasswordForm').reset();
        } else {
            const error = await response.json();
            errorDiv.textContent = error.error || 'Fehler beim Anfordern des Passwort-Resets';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        console.error('Error requesting password reset:', error);
        errorDiv.textContent = 'Fehler beim Anfordern des Passwort-Resets';
        errorDiv.style.display = 'block';
    }
}

// Reset Password Modal (from URL hash)
function checkPasswordResetToken() {
    // Check if URL contains reset token
    const hash = window.location.hash;
    if (hash.startsWith('#/reset-password?token=')) {
        const token = hash.split('token=')[1];
        showResetPasswordModal(token);
    }
}

function showResetPasswordModal(token) {
    document.getElementById('resetToken').value = token;
    document.getElementById('resetPasswordForm').reset();
    document.getElementById('resetPasswordError').style.display = 'none';
    document.getElementById('resetPasswordSuccess').style.display = 'none';
    document.getElementById('resetPasswordModal').style.display = 'block';
    
    // Validate token
    validateResetToken(token);
}

function closeResetPasswordModal() {
    document.getElementById('resetPasswordModal').style.display = 'none';
    document.getElementById('resetPasswordForm').reset();
    // Clear the hash
    window.location.hash = '';
}

async function validateResetToken(token) {
    try {
        const response = await fetch(`${API_BASE}/auth/validate-reset-token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ token: token })
        });
        
        if (response.ok) {
            const data = await response.json();
            if (!data.valid) {
                const errorDiv = document.getElementById('resetPasswordError');
                errorDiv.textContent = 'Der Reset-Link ist ungültig oder abgelaufen.';
                errorDiv.style.display = 'block';
                // Disable the form
                document.getElementById('resetPasswordForm').querySelectorAll('input, button[type="submit"]').forEach(el => {
                    el.disabled = true;
                });
            }
        }
    } catch (error) {
        console.error('Error validating reset token:', error);
    }
}

async function submitResetPassword(event) {
    event.preventDefault();
    
    const token = document.getElementById('resetToken').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    const errorDiv = document.getElementById('resetPasswordError');
    const successDiv = document.getElementById('resetPasswordSuccess');
    
    errorDiv.style.display = 'none';
    successDiv.style.display = 'none';
    
    // Validate passwords match
    if (newPassword !== confirmPassword) {
        errorDiv.textContent = 'Die Passwörter stimmen nicht überein.';
        errorDiv.style.display = 'block';
        return;
    }
    
    // Validate password length
    if (newPassword.length < 8) {
        errorDiv.textContent = 'Das Passwort muss mindestens 8 Zeichen lang sein.';
        errorDiv.style.display = 'block';
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/auth/reset-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                token: token,
                newPassword: newPassword
            })
        });
        
        if (response.ok) {
            successDiv.textContent = 'Passwort erfolgreich zurückgesetzt! Sie können sich jetzt anmelden.';
            successDiv.style.display = 'block';
            document.getElementById('resetPasswordForm').reset();
            setTimeout(() => {
                closeResetPasswordModal();
                showLoginModal();
            }, 2000);
        } else {
            const error = await response.json();
            errorDiv.textContent = error.error || 'Fehler beim Zurücksetzen des Passworts';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        console.error('Error resetting password:', error);
        errorDiv.textContent = 'Fehler beim Zurücksetzen des Passworts';
        errorDiv.style.display = 'block';
    }
}

// Check for password reset token on page load
document.addEventListener('DOMContentLoaded', () => {
    checkPasswordResetToken();
});
