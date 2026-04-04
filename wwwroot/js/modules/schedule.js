import { API_BASE, escapeHtml, formatLocalDate, getAbsenceCode, getContrastTextColor, generateDateRange, getUniqueDates, getWeekNumber, groupDatesByWeek, isHessianHoliday, YEAR_VIEW_SCROLL_PADDING, YEAR_VIEW_SCROLL_DELAY, groupByTeamAndEmployee, getAbsenceForDate, showToast } from './utils.js';
import { canPlanShifts, isAdmin } from './auth.js';
import { loadEmployees, cachedEmployees } from './employees.js';
import { showPlanningResultModal } from './planning_report.js';
import { store } from './store.js';

// ============================================================================
// MODULE STATE
// ============================================================================

export let currentView = 'month';
export let allShifts = [];
export let allShiftTypes = [];
export let multiSelectMode = false;
export let selectedShifts = new Set();

let _currentPlanJobId = null;

// ============================================================================
// DATE PICKERS & INIT
// ============================================================================

export function initializeDatePickers() {
    const today = new Date();
    const dayOfWeek = today.getDay();
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

    const currentDate = new Date();
    const currentMonth = currentDate.getMonth() + 1;
    const currentYear = currentDate.getFullYear();

    if (document.getElementById('monthSelect')) {
        document.getElementById('monthSelect').value = currentMonth;
    }

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

    if (document.getElementById('planMonth')) {
        document.getElementById('planMonth').value = currentMonth;
    }
}

// ============================================================================
// VIEW NAVIGATION
// ============================================================================

export function switchScheduleView(view, tabElement) {
    document.querySelectorAll('.schedule-tab').forEach(t => t.classList.remove('active'));
    tabElement.classList.add('active');

    currentView = view;
    store.setState('currentView', view);

    document.getElementById('week-controls').style.display = view === 'week' ? 'flex' : 'none';
    document.getElementById('month-controls').style.display = view === 'month' ? 'flex' : 'none';
    document.getElementById('year-controls').style.display = view === 'year' ? 'flex' : 'none';

    loadSchedule();
}

export function changeDate(days) {
    const dateInput = document.getElementById('startDate');
    const date = new Date(dateInput.value);
    date.setDate(date.getDate() + (days * 7));
    dateInput.value = date.toISOString().split('T')[0];
    loadSchedule();
}

export function changeMonth(delta) {
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

export function changeYear(delta) {
    const yearSelect = document.getElementById('yearSelect');
    let year = parseInt(yearSelect.value);
    year += delta;
    yearSelect.value = year;
    loadSchedule();
}

// ============================================================================
// SCHEDULE LOADING & DISPLAY
// ============================================================================

export async function loadSchedule() {
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
        const [scheduleResponse, employeesResponse] = await Promise.all([
            fetch(`${API_BASE}/shifts/schedule?startDate=${startDate}&view=${viewType}`),
            fetch(`${API_BASE}/employees`)
        ]);

        const data = await scheduleResponse.json();
        const employees = await employeesResponse.json();

        displaySchedule(data, employees);

        if (currentView === 'month') {
            await updateApprovalStatus();
        }
    } catch (error) {
        content.innerHTML = `<p class="error">Fehler beim Laden: ${error.message}</p>`;
    }
}

export function displaySchedule(data, employees) {
    const content = document.getElementById('schedule-content');

    allShifts = data.assignments;
    store.setState('allShifts', allShifts);

    if (currentView === 'week') {
        content.innerHTML = displayWeekView(data, employees);
    } else if (currentView === 'month') {
        content.innerHTML = displayMonthView(data, employees);
    } else if (currentView === 'year') {
        content.innerHTML = displayYearView(data, employees);
        requestAnimationFrame(() => {
            setTimeout(scrollYearViewToCurrentMonth, YEAR_VIEW_SCROLL_DELAY);
        });
    }
}

export function displayWeekView(data, employees) {
    const teamGroups = groupByTeamAndEmployee(data.assignments, employees, data.absences || []);

    let dates = [];
    if (data.startDate && data.endDate) {
        dates = generateDateRange(data.startDate, data.endDate);
    } else {
        dates = getUniqueDates(data.assignments);
    }
    dates.sort();

    if (dates.length === 0) {
        return '<p>Keine Schichten im ausgewählten Zeitraum.</p>';
    }

    const firstDate = new Date(dates[0]);
    const weekNumber = getWeekNumber(firstDate);
    const year = firstDate.getFullYear();

    let html = `<div class="month-header"><h3>Woche: KW ${weekNumber} ${year}</h3></div>`;
    html += '<table class="calendar-table week-view"><thead><tr>';
    html += '<th class="team-column">Team / Person</th>';

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

    teamGroups.forEach(team => {
        html += `<tr class="team-row"><td colspan="${dates.length + 1}" class="team-header">${team.teamName}</td></tr>`;

        team.employees.forEach(employee => {
            html += '<tr class="employee-row">';
            html += `<td class="employee-name">  - ${employee.name}${employee.isTeamLeader ? ' ⭐' : ''}</td>`;

            dates.forEach(dateStr => {
                const date = new Date(dateStr);
                const isSunday = date.getDay() === 0;
                const isHoliday = isHessianHoliday(date);
                const shifts = employee.shifts[dateStr] || [];
                const absence = getAbsenceForDate(employee.absences || [], dateStr);

                let cellContent = '';
                let cellClickable = '';

                if (absence) {
                    cellContent = createAbsenceBadge(absence);
                } else if (shifts.length > 0) {
                    cellContent = shifts.map(s => createShiftBadge(s)).join(' ');
                } else {
                    if (canPlanShifts()) {
                        cellClickable = ` onclick="showQuickEntryModal('${employee.id}', '${dateStr}')" style="cursor: pointer;"`;
                        cellContent = '<span class="empty-cell-placeholder">+</span>';
                    }
                }

                const cellClass = (isSunday || isHoliday) ? 'shift-cell sunday-cell' : 'shift-cell';
                html += `<td class="${cellClass}"${cellClickable}>${cellContent}</td>`;
            });

            html += '</tr>';
        });
    });

    html += '</tbody></table>';
    return html;
}

export function displayMonthView(data, employees) {
    const teamGroups = groupByTeamAndEmployee(data.assignments, employees, data.absences || []);

    let dates = [];
    if (data.startDate && data.endDate) {
        dates = generateDateRange(data.startDate, data.endDate);
    } else {
        dates = getUniqueDates(data.assignments);
    }
    dates.sort();

    if (dates.length === 0) {
        return '<p>Keine Schichten im ausgewählten Zeitraum.</p>';
    }

    const weekGroups = groupDatesByWeek(dates);
    const firstDate = new Date(dates[0]);
    const monthName = firstDate.toLocaleDateString('de-DE', { month: 'long', year: 'numeric' });

    let html = `<div class="month-header"><h3>Monat: ${monthName}</h3></div>`;
    html += '<table class="calendar-table month-view"><thead>';

    html += '<tr>';
    html += '<th class="team-column">KW</th>';
    weekGroups.forEach(week => {
        html += `<th class="week-number-header" colspan="${week.days.length}">KW ${week.weekNumber}</th>`;
    });
    html += '</tr>';

    html += '<tr>';
    html += '<th class="team-column">Team / Mitarbeiter</th>';
    weekGroups.forEach(week => {
        week.days.forEach(day => {
            const date = new Date(day);
            const dayName = date.toLocaleDateString('de-DE', { weekday: 'short' });
            const dayNum = date.getDate();
            const monthNum = date.getMonth() + 1;
            const isSunday = date.getDay() === 0;
            const isHoliday = isHessianHoliday(date);
            const columnClass = (isSunday || isHoliday) ? 'date-column sunday-column' : 'date-column';
            const isOtherMonth = date.getMonth() !== firstDate.getMonth();
            const dateClass = isOtherMonth ? ' other-month' : '';
            html += `<th class="${columnClass}${dateClass}">${dayName}<br>${dayNum}.${String(monthNum).padStart(2, '0')}</th>`;
        });
    });
    html += '</tr>';

    html += '</thead><tbody>';

    if (data.vacationPeriods && data.vacationPeriods.length > 0) {
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

    teamGroups.forEach(team => {
        const totalDays = weekGroups.reduce((sum, w) => sum + w.days.length, 0);
        html += `<tr class="team-row"><td colspan="${totalDays + 1}" class="team-header">${team.teamName}</td></tr>`;

        team.employees.forEach(employee => {
            html += '<tr class="employee-row">';
            html += `<td class="employee-name">  - ${employee.name}${employee.isTeamLeader ? ' ⭐' : ''}</td>`;

            weekGroups.forEach(week => {
                week.days.forEach(dateStr => {
                    const date = new Date(dateStr);
                    const isSunday = date.getDay() === 0;
                    const isHoliday = isHessianHoliday(date);
                    const shifts = employee.shifts[dateStr] || [];
                    const absence = getAbsenceForDate(employee.absences || [], dateStr);

                    let cellContent = '';
                    let cellClickable = '';

                    if (absence) {
                        cellContent = createAbsenceBadge(absence);
                    } else if (shifts.length > 0) {
                        cellContent = shifts.map(s => createShiftBadge(s)).join(' ');
                    } else {
                        if (canPlanShifts()) {
                            cellClickable = ` onclick="showQuickEntryModal('${employee.id}', '${dateStr}')" style="cursor: pointer;"`;
                            cellContent = '<span class="empty-cell-placeholder">+</span>';
                        }
                    }

                    const cellClass = (isSunday || isHoliday) ? 'shift-cell sunday-cell' : 'shift-cell';
                    html += `<td class="${cellClass}"${cellClickable}>${cellContent}</td>`;
                });
            });

            html += '</tr>';
        });
    });

    html += '</tbody></table>';
    return html;
}

export function displayYearView(data, employees) {
    const teamGroups = groupByTeamAndEmployee(data.assignments, employees, data.absences || []);

    let dates = [];
    if (data.startDate && data.endDate) {
        dates = generateDateRange(data.startDate, data.endDate);
    } else {
        dates = getUniqueDates(data.assignments);
    }
    dates.sort();

    if (dates.length === 0) {
        return '<p>Keine Schichten im ausgewählten Zeitraum.</p>';
    }

    const firstDate = new Date(dates[0]);
    const year = firstDate.getFullYear();
    const weekGroups = groupDatesByWeek(dates);

    let html = `<div class="month-header"><h3>Jahr: ${year}</h3></div>`;
    html += '<div class="year-view-horizontal-container" id="year-view-container">';
    html += '<table class="calendar-table year-view-horizontal"><thead>';

    html += '<tr>';
    html += '<th class="team-column sticky-column">KW</th>';
    weekGroups.forEach(week => {
        html += `<th class="week-number-header" colspan="${week.days.length}">KW ${week.weekNumber}</th>`;
    });
    html += '</tr>';

    html += '<tr>';
    html += '<th class="team-column sticky-column">Team / Mitarbeiter</th>';
    let currentMonth = -1;
    weekGroups.forEach(week => {
        week.days.forEach(day => {
            const date = new Date(day);
            const dayName = date.toLocaleDateString('de-DE', { weekday: 'short' });
            const dayNum = date.getDate();
            const monthNum = date.getMonth();
            const isSunday = date.getDay() === 0;
            const isHoliday = isHessianHoliday(date);

            const isMonthStart = (monthNum !== currentMonth);
            if (isMonthStart) {
                currentMonth = monthNum;
            }

            const columnClass = (isSunday || isHoliday) ? 'date-column sunday-column' : 'date-column';
            const monthStartClass = isMonthStart ? ' month-start' : '';
            html += `<th class="${columnClass}${monthStartClass}" data-month="${monthNum}">${dayName}<br>${dayNum}.</th>`;
        });
    });
    html += '</tr>';

    html += '</thead><tbody>';

    if (data.vacationPeriods && data.vacationPeriods.length > 0) {
        html += '<tr class="vacation-period-row">';
        html += '<td class="vacation-period-label sticky-column"><strong>🏖️ Ferien</strong></td>';

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
                    const shortName = activePeriods[0].name.slice(0, 3);
                    content = `<div class="vacation-period-badge-tiny" style="background-color: ${activePeriods[0].colorCode};" title="${activePeriods.map(p => escapeHtml(p.name)).join(', ')}">${escapeHtml(shortName)}</div>`;
                }

                const isSunday = date.getDay() === 0;
                const isHoliday = isHessianHoliday(date);
                const cellClass = (isSunday || isHoliday) ? 'vacation-period-cell sunday-cell' : 'vacation-period-cell';
                html += `<td class="${cellClass}">${content}</td>`;
            });
        });

        html += '</tr>';
    }

    teamGroups.forEach(team => {
        const totalDays = weekGroups.reduce((sum, w) => sum + w.days.length, 0);
        html += `<tr class="team-row"><td colspan="${totalDays + 1}" class="team-header sticky-column">${team.teamName}</td></tr>`;

        team.employees.forEach(employee => {
            html += '<tr class="employee-row">';
            html += `<td class="employee-name sticky-column">  - ${employee.name}${employee.isTeamLeader ? ' ⭐' : ''}</td>`;

            weekGroups.forEach(week => {
                week.days.forEach(dateStr => {
                    const date = new Date(dateStr);
                    const isSunday = date.getDay() === 0;
                    const isHoliday = isHessianHoliday(date);
                    const shifts = employee.shifts[dateStr] || [];
                    const absence = getAbsenceForDate(employee.absences || [], dateStr);

                    let cellContent = '';

                    if (absence) {
                        cellContent = `<span class="absence-badge-tiny" title="${escapeHtml(absence.type)}">${getAbsenceCode(absence.type)}</span>`;
                    } else if (shifts.length > 0) {
                        cellContent = shifts.map(s => `<span class="shift-badge-tiny" style="background-color: ${s.colorCode};" title="${escapeHtml(s.shiftName)}">${escapeHtml(s.shiftCode)}</span>`).join(' ');
                    }

                    const cellClass = (isSunday || isHoliday) ? 'shift-cell sunday-cell' : 'shift-cell';
                    html += `<td class="${cellClass}">${cellContent}</td>`;
                });
            });

            html += '</tr>';
        });
    });

    html += '</tbody></table></div>';
    return html;
}

function scrollYearViewToCurrentMonth() {
    const container = document.getElementById('year-view-container');
    if (!container) return;

    const currentMonth = new Date().getMonth();
    const monthStartCells = container.querySelectorAll(`th[data-month="${currentMonth}"]`);

    if (monthStartCells.length > 0 && container.scrollWidth > container.clientWidth) {
        const firstCell = monthStartCells[0];
        const cellLeft = firstCell.offsetLeft;
        container.scrollLeft = Math.max(0, cellLeft - YEAR_VIEW_SCROLL_PADDING);
    }
}

// ============================================================================
// SHIFT BADGE HELPERS
// ============================================================================

export function createAbsenceBadge(absence) {
    if (!absence || !absence.type) {
        return '';
    }

    const absenceCode = getAbsenceCode(absence.type);
    let cssClass = `shift-badge shift-${absenceCode}`;

    if (absenceCode === 'U' && absence.status) {
        if (absence.status === 'InBearbeitung') {
            cssClass = 'shift-badge shift-U-pending';
        } else if (absence.status === 'Abgelehnt') {
            cssClass = 'shift-badge shift-U-rejected';
        }
    }

    const title = `${absence.type}: ${absence.notes || ''}`;
    return `<span class="${cssClass}" title="${title}">${absenceCode}</span>`;
}

export function createShiftBadge(shift) {
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

    const isSelected = multiSelectMode && shiftId && selectedShifts.has(shiftId);
    const selectedClass = isSelected ? 'shift-selected' : '';

    const colorCode = shift.colorCode || '';
    let styleAttr = '';
    if (colorCode) {
        const textColor = getContrastTextColor(colorCode);
        styleAttr = `background-color: ${colorCode}; color: ${textColor};`;
    }

    let onclickAttr = '';
    if (canEdit && shiftId) {
        if (multiSelectMode) {
            onclickAttr = `onclick="toggleShiftSelection(${shiftId}); return false;" style="cursor:pointer; ${styleAttr}"`;
        } else {
            onclickAttr = `onclick="editShiftAssignment(${shiftId})" style="cursor:pointer; ${styleAttr}"`;
        }
    } else if (colorCode) {
        onclickAttr = `style="${styleAttr}"`;
    }

    return `<span class="shift-badge shift-${shiftCode} ${badgeClass} ${selectedClass}" title="${shiftName}${isFixed ? ' (Fixiert)' : ''}" ${onclickAttr}>${lockIcon}${shiftCode}</span>`;
}

// ============================================================================
// PLAN SHIFTS MODAL
// ============================================================================

export function showPlanShiftsModal() {
    if (!canPlanShifts()) {
        showToast('Sie haben keine Berechtigung, Schichten zu planen. Bitte melden Sie sich als Admin oder Disponent an.', 'error');
        return;
    }
    document.getElementById('planShiftsModal').style.display = 'block';
}

export function closePlanShiftsModal() {
    document.getElementById('planShiftsModal').style.display = 'none';
    document.getElementById('planShiftsForm').reset();
    document.getElementById('planningOverlay').classList.remove('active');
}

export async function executePlanShifts(event) {
    event.preventDefault();

    if (!canPlanShifts()) {
        showToast('Sie haben keine Berechtigung, Schichten zu planen.', 'error');
        return;
    }

    const month = document.getElementById('planMonth').value;
    const year = document.getElementById('planMonthYear').value;
    const force = document.getElementById('planForceOverwrite').checked;
    const timeLimit = parseInt(document.getElementById('planTimeLimit')?.value || '120', 10);

    if (!month || !year) {
        showToast('Bitte wählen Sie Monat und Jahr aus.', 'warning');
        return;
    }

    const startDate = new Date(year, month - 1, 1);
    const endDate = new Date(year, month, 0);

    const startDateStr = formatLocalDate(year, month, 1);
    const endDateStr = formatLocalDate(year, month, endDate.getDate());

    const periodText = startDate.toLocaleDateString('de-DE', { month: 'long', year: 'numeric' });

    const confirmText = force
        ? `Möchten Sie wirklich alle Schichten für ${periodText} neu planen? Bestehende Schichten werden überschrieben (außer feste Schichten).`
        : `Möchten Sie Schichten für ${periodText} planen? Bereits geplante Tage werden übersprungen.`;

    if (!confirm(confirmText)) {
        return;
    }

    const planningOverlay = document.getElementById('planningOverlay');
    const statusEl = document.getElementById('planningStatusMessage');
    const elapsedEl = document.getElementById('planningElapsedTime');
    planningOverlay.classList.add('active');
    statusEl.textContent = 'Planung wird gestartet…';
    elapsedEl.textContent = '';

    try {
        // Start the async planning job
        const startResponse = await fetch(
            `${API_BASE}/shifts/plan?startDate=${startDateStr}&endDate=${endDateStr}&force=${force}&timeLimit=${timeLimit}`,
            {
                method: 'POST',
                credentials: 'include'
            }
        );

        if (!startResponse.ok) {
            planningOverlay.classList.remove('active');
            if (startResponse.status === 401) {
                showToast('Bitte melden Sie sich an, um Schichten zu planen.', 'warning');
            } else if (startResponse.status === 403) {
                showToast('Sie haben keine Berechtigung, Schichten zu planen.', 'error');
            } else {
                const error = await startResponse.json();
                showToast(`Fehler beim Starten der Planung: ${error.error || 'Unbekannter Fehler'}`, 'error');
            }
            return;
        }

        const { jobId } = await startResponse.json();
        _currentPlanJobId = jobId;

        // Poll for status
        const pollInterval = 2000; // 2 seconds
        let elapsed = 0;

        const poll = async () => {
            try {
                const statusResponse = await fetch(
                    `${API_BASE}/shifts/plan/status/${jobId}`,
                    { credentials: 'include' }
                );

                if (!statusResponse.ok) {
                    planningOverlay.classList.remove('active');
                    showToast('Fehler beim Abrufen des Planungsstatus.', 'error');
                    return;
                }

                const job = await statusResponse.json();
                elapsed = job.elapsedSeconds || 0;

                // Update status message
                if (statusEl) statusEl.textContent = job.message || 'Schichten werden geplant…';
                if (elapsedEl) {
                    const mins = Math.floor(elapsed / 60);
                    const secs = elapsed % 60;
                    elapsedEl.textContent = mins > 0
                        ? `${mins} Min. ${secs} Sek. vergangen`
                        : `${secs} Sek. vergangen`;
                }

                if (job.status === 'running') {
                    if (elapsed >= 600) {
                        // Safety timeout: stop polling after 10 minutes
                        planningOverlay.classList.remove('active');
                        showToast('Die Planung dauert ungewöhnlich lange. Bitte überprüfen Sie den Server.', 'warning');
                        return;
                    }
                    setTimeout(poll, pollInterval);
                    return;
                }

                // Job finished
                planningOverlay.classList.remove('active');
                _currentPlanJobId = null;

                if (job.status === 'success') {
                    closePlanShiftsModal();
                    loadSchedule();
                    showPlanningResultModal(parseInt(year, 10), parseInt(month, 10), periodText);
                } else {
                    // Error
                    if (job.details) {
                        showToast(`Fehler beim Planen der Schichten: ${job.details}`, 'error');
                    } else {
                        showToast(`Fehler beim Planen der Schichten: ${job.message || 'Unbekannter Fehler'}`, 'error');
                    }
                }
            } catch (err) {
                planningOverlay.classList.remove('active');
                showToast(`Fehler: ${err.message}`, 'error');
            }
        };

        setTimeout(poll, pollInterval);

    } catch (error) {
        // Hide loading overlay on error
        planningOverlay.classList.remove('active');
        showToast(`Fehler: ${error.message}`, 'error');
    }
}

export function planShifts() {
    showPlanShiftsModal();
}

export async function cancelPlanning() {
    if (!_currentPlanJobId) return;

    try {
        await fetch(`${API_BASE}/shifts/plan/${_currentPlanJobId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
    } catch (e) {
        // ignore
    }

    const planningOverlay = document.getElementById('planningOverlay');
    if (planningOverlay) planningOverlay.classList.remove('active');
    _currentPlanJobId = null;
}

// ============================================================================
// EXPORTS (PDF / Excel / CSV)
// ============================================================================

export async function exportScheduleToPdf() {
    let startDate, endDate;

    if (currentView === 'week') {
        startDate = document.getElementById('startDate').value;
        if (!startDate) { showToast('Bitte wählen Sie ein Startdatum aus.', 'warning'); return; }
        const end = new Date(startDate);
        end.setDate(end.getDate() + 7);
        endDate = end.toISOString().split('T')[0];
    } else if (currentView === 'month') {
        const month = document.getElementById('monthSelect').value;
        const year = document.getElementById('monthYearSelect').value;
        startDate = formatLocalDate(year, month, 1);
        const end = new Date(year, month, 0);
        endDate = formatLocalDate(year, month, end.getDate());
    } else if (currentView === 'year') {
        const year = document.getElementById('yearSelect').value;
        startDate = `${year}-01-01`;
        endDate = `${year}-12-31`;
    }

    try {
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
            showToast('Bitte melden Sie sich an, um den Dienstplan als PDF zu exportieren.', 'warning');
        } else if (response.status === 501) {
            const error = await response.json();
            showToast(error.error || 'PDF-Export ist noch nicht implementiert.', 'error');
        } else {
            showToast('Fehler beim PDF-Export. Bitte versuchen Sie es erneut.', 'error');
        }
    } catch (error) {
        showToast(`Fehler beim PDF-Export: ${error.message}`, 'error');
    }
}

export async function exportScheduleToExcel() {
    let startDate, endDate;

    if (currentView === 'week') {
        startDate = document.getElementById('startDate').value;
        if (!startDate) { showToast('Bitte wählen Sie ein Startdatum aus.', 'warning'); return; }
        const end = new Date(startDate);
        end.setDate(end.getDate() + 7);
        endDate = end.toISOString().split('T')[0];
    } else if (currentView === 'month') {
        const month = document.getElementById('monthSelect').value;
        const year = document.getElementById('monthYearSelect').value;
        startDate = formatLocalDate(year, month, 1);
        const end = new Date(year, month, 0);
        endDate = formatLocalDate(year, month, end.getDate());
    } else if (currentView === 'year') {
        const year = document.getElementById('yearSelect').value;
        startDate = `${year}-01-01`;
        endDate = `${year}-12-31`;
    }

    try {
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
            showToast('Bitte melden Sie sich an, um den Dienstplan als Excel zu exportieren.', 'warning');
        } else if (response.status === 501) {
            const error = await response.json();
            showToast(error.error || 'Excel-Export ist noch nicht implementiert.', 'error');
        } else {
            showToast('Fehler beim Excel-Export. Bitte versuchen Sie es erneut.', 'error');
        }
    } catch (error) {
        showToast(`Fehler beim Excel-Export: ${error.message}`, 'error');
    }
}

export async function exportScheduleToCsv() {
    let startDate, endDate;

    if (currentView === 'week') {
        startDate = document.getElementById('startDate').value;
        if (!startDate) { showToast('Bitte wählen Sie ein Startdatum aus.', 'warning'); return; }
        const end = new Date(startDate);
        end.setDate(end.getDate() + 7);
        endDate = end.toISOString().split('T')[0];
    } else if (currentView === 'month') {
        const month = document.getElementById('monthSelect').value;
        const year = document.getElementById('monthYearSelect').value;
        startDate = formatLocalDate(year, month, 1);
        const end = new Date(year, month, 0);
        endDate = formatLocalDate(year, month, end.getDate());
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
            showToast('Fehler beim CSV-Export. Bitte versuchen Sie es erneut.', 'error');
        }
    } catch (error) {
        showToast(`Fehler beim CSV-Export: ${error.message}`, 'error');
    }
}

// ============================================================================
// SHIFT ASSIGNMENT EDITING
// ============================================================================

export async function loadShiftTypes() {
    try {
        const response = await fetch(`${API_BASE}/shifttypes`, {
            credentials: 'include'
        });
        if (response.ok) {
            allShiftTypes = await response.json();
            store.setState('cachedShiftTypes', allShiftTypes);
        }
    } catch (error) {
        console.error('Error loading shift types:', error);
    }
}

export async function editShiftAssignment(shiftId) {
    if (!canPlanShifts()) {
        showToast('Sie haben keine Berechtigung, Schichten zu bearbeiten.', 'error');
        return;
    }

    const shift = allShifts.find(s => s.id === shiftId);
    if (!shift) {
        showToast('Schicht nicht gefunden.', 'error');
        return;
    }

    await loadEmployees();
    if (allShiftTypes.length === 0) {
        await loadShiftTypes();
    }

    document.getElementById('editShiftId').value = shift.id;
    document.getElementById('editShiftEmployeeId').value = shift.employeeId;
    document.getElementById('editShiftDate').value = shift.date.split('T')[0];
    document.getElementById('editShiftTypeId').value = shift.shiftTypeId;
    document.getElementById('editShiftIsFixed').checked = shift.isFixed || false;
    document.getElementById('editShiftNotes').value = shift.notes || '';

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

export async function showNewShiftModal() {
    if (!canPlanShifts()) {
        showToast('Sie haben keine Berechtigung, Schichten zu erstellen.', 'error');
        return;
    }

    await loadEmployees();
    if (allShiftTypes.length === 0) {
        await loadShiftTypes();
    }

    document.getElementById('editShiftForm').reset();
    document.getElementById('editShiftId').value = '';

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

export function closeEditShiftModal() {
    document.getElementById('editShiftModal').style.display = 'none';
    document.getElementById('editShiftForm').reset();
    document.getElementById('editShiftWarning').style.display = 'none';
}

export async function saveShiftAssignment(event) {
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
            showToast(isNewShift ? 'Schicht erfolgreich erstellt!' : 'Schicht erfolgreich aktualisiert!', 'success');
            closeEditShiftModal();
            loadSchedule();
        } else if (response.status === 400) {
            const error = await response.json();
            if (error.warning) {
                document.getElementById('editShiftWarningText').textContent = error.error;
                document.getElementById('editShiftWarning').style.display = 'block';

                if (confirm(`⚠️ Regelverstoß:\n\n${error.error}\n\nMöchten Sie die Änderung trotzdem vornehmen?`)) {
                    showToast('Erzwungene Änderungen sind noch nicht implementiert. Die Schicht muss den Regeln entsprechen.', 'warning');
                }
            } else {
                showToast(`Fehler: ${error.error}`, 'error');
            }
        } else if (response.status === 401) {
            showToast('Bitte melden Sie sich an.', 'warning');
        } else if (response.status === 403) {
            showToast('Sie haben keine Berechtigung für diese Aktion.', 'error');
        } else {
            showToast(isNewShift ? 'Fehler beim Erstellen der Schicht.' : 'Fehler beim Aktualisieren der Schicht.', 'error');
        }
    } catch (error) {
        console.error('Error saving shift:', error);
        showToast(`Fehler: ${error.message}`, 'error');
    }
}

export async function deleteShiftAssignment() {
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
            showToast('Schicht erfolgreich gelöscht!', 'success');
        } else if (response.status === 401) {
            showToast('Bitte melden Sie sich an.', 'warning');
        } else if (response.status === 403) {
            showToast('Sie haben keine Berechtigung für diese Aktion.', 'error');
        } else {
            showToast('Fehler beim Löschen der Schicht.', 'error');
        }
    } catch (error) {
        console.error('Error deleting shift:', error);
        showToast(`Fehler: ${error.message}`, 'error');
    }
}

// ============================================================================
// QUICK ENTRY MODAL
// ============================================================================

export async function showQuickEntryModal(employeeId, dateStr) {
    if (!canPlanShifts()) {
        showToast('Sie haben keine Berechtigung, Schichten oder Abwesenheiten zu erstellen. Diese Funktion ist nur für Administratoren und Disponenten verfügbar.', 'error');
        return;
    }

    await loadEmployees();
    if (allShiftTypes.length === 0) {
        await loadShiftTypes();
    }

    const employee = cachedEmployees.find(emp => emp.id === parseInt(employeeId));
    if (!employee) {
        showToast('Mitarbeiter nicht gefunden.', 'error');
        return;
    }

    document.getElementById('quickEntryEmployeeId').value = employeeId;
    document.getElementById('quickEntryDateValue').value = dateStr;

    const employeeName = `${employee.vorname} ${employee.name} (PN: ${employee.personalnummer})`;
    document.getElementById('quickEntryEmployee').textContent = employeeName;

    const dateObj = new Date(dateStr);
    const formattedDate = dateObj.toLocaleDateString('de-DE', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    document.getElementById('quickEntryDate').textContent = formattedDate;

    document.getElementById('quickEntryType').value = '';
    document.getElementById('quickEntryNotes').value = '';
    document.getElementById('quickEntryShiftGroup').style.display = 'none';
    document.getElementById('quickEntryAbsenceGroup').style.display = 'none';

    const shiftTypeSelect = document.getElementById('quickEntryShiftTypeId');
    shiftTypeSelect.innerHTML = '<option value="">Schichttyp wählen...</option>';
    allShiftTypes.forEach(type => {
        const option = document.createElement('option');
        option.value = type.id;
        option.textContent = `${type.name} (${type.code})`;
        shiftTypeSelect.appendChild(option);
    });

    try {
        const response = await fetch(`${API_BASE}/absencetypes`);
        if (response.ok) {
            const absenceTypes = await response.json();
            const absenceTypeSelect = document.getElementById('quickEntryAbsenceTypeId');
            absenceTypeSelect.innerHTML = '<option value="">Abwesenheitstyp wählen...</option>';

            absenceTypes.forEach(at => {
                if (at.code !== 'U') {
                    const option = document.createElement('option');
                    option.value = at.id;
                    option.textContent = `${at.name} (${at.code})`;
                    absenceTypeSelect.appendChild(option);
                }
            });
        }
    } catch (error) {
        console.error('Error loading absence types:', error);
    }

    document.getElementById('quickEntryModal').style.display = 'block';
}

export function updateQuickEntryOptions() {
    const entryType = document.getElementById('quickEntryType').value;

    const shiftGroup = document.getElementById('quickEntryShiftGroup');
    const absenceGroup = document.getElementById('quickEntryAbsenceGroup');

    if (entryType === 'shift') {
        shiftGroup.style.display = 'block';
        absenceGroup.style.display = 'none';
        document.getElementById('quickEntryShiftTypeId').required = true;
        document.getElementById('quickEntryAbsenceTypeId').required = false;
    } else if (entryType === 'absence') {
        shiftGroup.style.display = 'none';
        absenceGroup.style.display = 'block';
        document.getElementById('quickEntryShiftTypeId').required = false;
        document.getElementById('quickEntryAbsenceTypeId').required = true;
    } else {
        shiftGroup.style.display = 'none';
        absenceGroup.style.display = 'none';
        document.getElementById('quickEntryShiftTypeId').required = false;
        document.getElementById('quickEntryAbsenceTypeId').required = false;
    }
}

export function closeQuickEntryModal() {
    document.getElementById('quickEntryModal').style.display = 'none';
    document.getElementById('quickEntryType').value = '';
    document.getElementById('quickEntryNotes').value = '';
    document.getElementById('quickEntryShiftGroup').style.display = 'none';
    document.getElementById('quickEntryAbsenceGroup').style.display = 'none';
}

export async function saveQuickEntry() {
    const entryType = document.getElementById('quickEntryType').value;

    if (!entryType) {
        showToast('Bitte wählen Sie, ob Sie eine Schicht oder Abwesenheit hinzufügen möchten.', 'warning');
        return;
    }

    const employeeId = parseInt(document.getElementById('quickEntryEmployeeId').value);
    const dateValue = document.getElementById('quickEntryDateValue').value;
    const notes = document.getElementById('quickEntryNotes').value;

    try {
        if (entryType === 'shift') {
            const shiftTypeId = document.getElementById('quickEntryShiftTypeId').value;
            if (!shiftTypeId) {
                showToast('Bitte wählen Sie einen Schichttyp.', 'warning');
                return;
            }

            const shiftData = {
                employeeId: employeeId,
                date: dateValue,
                shiftTypeId: parseInt(shiftTypeId),
                isFixed: false,
                notes: notes || null
            };

            const response = await fetch(`${API_BASE}/shifts/assignments`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(shiftData)
            });

            if (response.ok) {
                showToast('Schicht erfolgreich erstellt!', 'success');
                closeQuickEntryModal();
                loadSchedule();
            } else if (response.status === 400) {
                const error = await response.json();
                if (error.warning) {
                    if (confirm(`⚠️ Regelverstoß:\n\n${error.error}\n\nMöchten Sie die Änderung trotzdem vornehmen?`)) {
                        showToast('Erzwungene Änderungen sind noch nicht implementiert. Die Schicht muss den Regeln entsprechen.', 'error');
                    }
                } else {
                    showToast(`Fehler: ${error.error}`, 'error');
                }
            } else {
                showToast('Fehler beim Erstellen der Schicht.', 'error');
            }
        } else if (entryType === 'absence') {
            const absenceTypeId = document.getElementById('quickEntryAbsenceTypeId').value;
            if (!absenceTypeId) {
                showToast('Bitte wählen Sie einen Abwesenheitstyp.', 'warning');
                return;
            }

            const absenceData = {
                employeeId: employeeId,
                startDate: dateValue,
                endDate: dateValue,
                absenceTypeId: parseInt(absenceTypeId),
                notes: notes || null
            };

            const response = await fetch(`${API_BASE}/absences`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(absenceData)
            });

            if (response.ok) {
                showToast('Abwesenheit erfolgreich erfasst!', 'success');
                closeQuickEntryModal();
                loadSchedule();
            } else {
                const error = await response.json();
                showToast(error.error || 'Fehler beim Speichern der Abwesenheit.', 'error');
            }
        }
    } catch (error) {
        console.error('Error saving quick entry:', error);
        showToast(`Fehler: ${error.message}`, 'error');
    }
}

// ============================================================================
// TOGGLE SHIFT FIXED
// ============================================================================

export async function toggleShiftFixed(shiftId) {
    if (!canPlanShifts()) {
        showToast('Sie haben keine Berechtigung, Schichten zu sperren/entsperren.', 'error');
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
            showToast(`Schicht erfolgreich ${status}!`, 'success');
            loadSchedule();
        } else if (response.status === 401) {
            showToast('Bitte melden Sie sich an.', 'warning');
        } else if (response.status === 403) {
            showToast('Sie haben keine Berechtigung für diese Aktion.', 'error');
        } else {
            const error = await response.json();
            showToast(`Fehler: ${error.error || 'Unbekannter Fehler'}`, 'error');
        }
    } catch (error) {
        console.error('Error toggling fixed status:', error);
        showToast(`Fehler: ${error.message}`, 'error');
    }
}

// ============================================================================
// MULTI-SELECT MODE
// ============================================================================

export function toggleMultiSelectMode() {
    multiSelectMode = !multiSelectMode;
    selectedShifts.clear();

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

    updateSelectionCounter();
    loadSchedule();
}

export function toggleShiftSelection(shiftId) {
    if (!multiSelectMode) {
        return;
    }

    if (selectedShifts.has(shiftId)) {
        selectedShifts.delete(shiftId);
    } else {
        selectedShifts.add(shiftId);
    }

    loadSchedule();
    updateSelectionCounter();
}

export function clearShiftSelection() {
    selectedShifts.clear();
    loadSchedule();
    updateSelectionCounter();
}

export function updateSelectionCounter() {
    const counter = document.getElementById('selectionCounter');
    if (counter) {
        const count = selectedShifts.size;
        counter.textContent = count > 0 ? `${count} Schicht${count !== 1 ? 'en' : ''} ausgewählt` : '';
    }
}

export async function showBulkEditModal() {
    if (selectedShifts.size === 0) {
        showToast('Bitte wählen Sie mindestens eine Schicht aus.', 'warning');
        return;
    }

    if (!canPlanShifts()) {
        showToast('Sie haben keine Berechtigung, Schichten zu bearbeiten.', 'error');
        return;
    }

    await loadEmployees();
    if (allShiftTypes.length === 0) {
        await loadShiftTypes();
    }

    const selectedShiftDetails = Array.from(selectedShifts).map(id =>
        allShifts.find(s => s.id === id)
    ).filter(s => s !== undefined);

    document.getElementById('bulkEditShiftCount').textContent = selectedShifts.size;

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

    const shiftTypeSelect = document.getElementById('bulkEditShiftTypeId');
    shiftTypeSelect.innerHTML = '<option value="">Keine Änderung</option>';
    allShiftTypes.forEach(type => {
        const option = document.createElement('option');
        option.value = type.id;
        option.textContent = `${type.name} (${type.code})`;
        shiftTypeSelect.appendChild(option);
    });

    const summaryDiv = document.getElementById('bulkEditSummary');
    let summaryHtml = '<div style="max-height: 200px; overflow-y: auto; margin: 10px 0; padding: 10px; background: #f5f5f5; border-radius: 4px;">';
    summaryHtml += '<strong>Ausgewählte Schichten:</strong><ul style="margin: 5px 0; padding-left: 20px;">';

    selectedShiftDetails.forEach(shift => {
        const date = new Date(shift.date).toLocaleDateString('de-DE');
        summaryHtml += `<li>${shift.employeeName} - ${date} - ${shift.shiftCode}</li>`;
    });

    summaryHtml += '</ul></div>';
    summaryDiv.innerHTML = summaryHtml;

    document.getElementById('bulkEditForm').reset();
    document.getElementById('bulkEditWarning').style.display = 'none';

    document.getElementById('bulkEditModal').style.display = 'block';
}

export function closeBulkEditModal() {
    document.getElementById('bulkEditModal').style.display = 'none';
    document.getElementById('bulkEditForm').reset();
    document.getElementById('bulkEditWarning').style.display = 'none';
}

export async function saveBulkEdit(event) {
    event.preventDefault();

    const employeeId = document.getElementById('bulkEditEmployeeId').value;
    const shiftTypeId = document.getElementById('bulkEditShiftTypeId').value;
    const isFixedChecked = document.getElementById('bulkEditIsFixed').checked;
    const notes = document.getElementById('bulkEditNotes').value.trim();

    const changes = {};
    if (employeeId) changes.employeeId = parseInt(employeeId);
    if (shiftTypeId) changes.shiftTypeId = parseInt(shiftTypeId);
    if (isFixedChecked) changes.isFixed = true;
    if (notes) changes.notes = notes;

    if (Object.keys(changes).length === 0) {
        showToast('Bitte wählen Sie mindestens eine Änderung aus.', 'warning');
        return;
    }

    if (!confirm(`Möchten Sie ${selectedShifts.size} Schicht${selectedShifts.size !== 1 ? 'en' : ''} wirklich ändern?`)) {
        return;
    }

    try {
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
            showToast(`Erfolgreich ${result.updated || selectedShifts.size} Schicht${(result.updated || selectedShifts.size) !== 1 ? 'en' : ''} aktualisiert!`, 'success');
            closeBulkEditModal();

            if (multiSelectMode) {
                toggleMultiSelectMode();
            }
        } else if (response.status === 400) {
            const error = await response.json();
            document.getElementById('bulkEditWarningText').textContent = error.error || 'Validierungsfehler';
            document.getElementById('bulkEditWarning').style.display = 'block';
        } else if (response.status === 401) {
            showToast('Bitte melden Sie sich an.', 'warning');
        } else if (response.status === 403) {
            showToast('Sie haben keine Berechtigung für diese Aktion.', 'error');
        } else {
            showToast('Fehler beim Aktualisieren der Schichten.', 'error');
        }
    } catch (error) {
        console.error('Error saving bulk edit:', error);
        showToast(`Fehler: ${error.message}`, 'error');
    }
}

// ============================================================================
// APPROVAL STATUS
// ============================================================================

export async function updateApprovalStatus() {
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

export async function togglePlanApproval() {
    const month = document.getElementById('monthSelect').value;
    const year = document.getElementById('monthYearSelect').value;

    try {
        const statusResponse = await fetch(`${API_BASE}/shifts/plan/approvals/${year}/${month}`, {
            credentials: 'include'
        });

        if (!statusResponse.ok) {
            showToast('Fehler beim Abrufen des aktuellen Status.', 'error');
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
            showToast(data.message || `Dienstplan wurde ${action}.`, 'success');
            await updateApprovalStatus();
            await loadSchedule();
        } else if (response.status === 401) {
            showToast('Bitte melden Sie sich an.', 'warning');
        } else if (response.status === 403) {
            showToast('Sie haben keine Berechtigung, Dienstpläne freizugeben.', 'error');
        } else {
            const error = await response.json();
            showToast(`Fehler: ${error.error || 'Unbekannter Fehler'}`, 'error');
        }
    } catch (error) {
        console.error('Error toggling approval:', error);
        showToast(`Fehler beim Ändern des Freigabestatus.`, 'error');
    }
}
