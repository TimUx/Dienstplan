// API Base URL
export const API_BASE = window.location.origin + '/api';

// Configuration constants
export const YEAR_VIEW_SCROLL_PADDING = 100;
export const YEAR_VIEW_SCROLL_DELAY = 200;
export const MS_PER_DAY = 86400000;

// Constant for employees without team assignment
export const UNASSIGNED_TEAM_ID = -1;

// Absence type constants (must match database enum)
export const ABSENCE_TYPES = {
    AU: 1,
    U: 2,
    L: 3
};

// Helper function to format date as YYYY-MM-DD in local timezone
export function formatLocalDate(year, month, day) {
    return `${year}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
}

// Helper function to escape HTML to prevent XSS
export function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Helper function to escape strings for use in JavaScript inline event handlers
export function escapeJsString(text) {
    if (!text) return '';
    return text.replace(/\\/g, '\\\\')
               .replace(/'/g, "\\'")
               .replace(/"/g, '\\"')
               .replace(/\n/g, '\\n')
               .replace(/\r/g, '\\r');
}

// Helper function to sanitize color codes to prevent CSS injection
export function sanitizeColorCode(colorCode) {
    if (!colorCode) return '#CCCCCC';

    if (/^#[0-9A-Fa-f]{3}$|^#[0-9A-Fa-f]{6}$/.test(colorCode)) {
        return colorCode;
    }

    const validColors = ['red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink', 'brown', 'gray', 'grey', 'black', 'white'];
    if (validColors.includes(colorCode.toLowerCase())) {
        return colorCode.toLowerCase();
    }

    if (/^rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(,\s*[\d.]+)?\s*\)$/.test(colorCode)) {
        return colorCode;
    }

    console.warn('Invalid color code:', colorCode);
    return '#CCCCCC';
}

// Helper function to format import result with error details
export function formatImportResult(result) {
    const errorCount = (result.errors && result.errors.length) || 0;
    const successCount = (result.imported || 0) + (result.updated || 0);

    let errorDetails = '';
    if (errorCount > 0) {
        errorDetails = '<div class="error-list"><p><strong>Fehler Details:</strong></p><ul>';
        result.errors.forEach(err => {
            errorDetails += `<li>${escapeHtml(err)}</li>`;
        });
        errorDetails += '</ul></div>';
    }

    let cssClass, icon, heading;
    if (errorCount === 0) {
        cssClass = 'success-message';
        icon = '✓';
        heading = 'Import erfolgreich!';
    } else if (successCount > 0) {
        cssClass = 'warning-message';
        icon = '⚠';
        heading = 'Import teilweise erfolgreich!';
    } else {
        cssClass = 'error-message';
        icon = '✗';
        heading = 'Import fehlgeschlagen!';
    }

    return `
        <div class="${cssClass}">
            <p><strong>${icon} ${heading}</strong></p>
            <p>Gesamt in Datei gefunden: ${result.total || 0}</p>
            <p>Neu importiert: ${result.imported || 0}</p>
            <p>Aktualisiert: ${result.updated || 0}</p>
            <p>Übersprungen: ${result.skipped || 0}</p>
            ${errorDetails}
        </div>
    `;
}

/**
 * Get absence code from absence type string
 */
export function getAbsenceCode(typeString) {
    if (typeString === 'Krank / AU' || typeString === 'Krank') {
        return 'AU';
    } else if (typeString === 'Urlaub' || typeString.startsWith('Urlaub')) {
        return 'U';
    } else if (typeString === 'Lehrgang') {
        return 'L';
    }
    return 'A';
}

/**
 * Calculate appropriate text color based on background color brightness
 */
export function getContrastTextColor(hexColor) {
    if (!hexColor || hexColor.length < 6) {
        return '#000000';
    }

    const hex = hexColor.replace('#', '');
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

    return luminance > 0.5 ? '#000000' : '#FFFFFF';
}

/**
 * Formats employee display name with personnel number in parentheses
 */
export function formatEmployeeDisplayName(employeeName, personalnummer) {
    return personalnummer ? `${employeeName} (${personalnummer})` : employeeName;
}

/**
 * Determines if an employee should be excluded from the unassigned team listing.
 */
export function shouldExcludeFromUnassigned(emp) {
    if (emp.teamId && emp.teamId > 0) {
        return false;
    }
    return emp.isBrandmeldetechniker || emp.isBrandschutzbeauftragter || emp.isFerienjobber;
}

export function groupByTeamAndEmployee(assignments, allEmployees, absences = []) {
    const teams = {};

    const employeeMap = new Map(allEmployees.map(emp => [emp.id, emp]));

    allEmployees.forEach(emp => {
        if (shouldExcludeFromUnassigned(emp)) {
            return;
        }

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
                absences: []
            };
        }
    });

    assignments.forEach(a => {
        const employee = employeeMap.get(a.employeeId);

        const teamId = a.teamId || UNASSIGNED_TEAM_ID;

        if (!teams[teamId]) {
            const teamName = 'Ohne Team';
            teams[teamId] = {
                teamId: teamId,
                teamName: teamName,
                employees: {}
            };
        }

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

    absences.forEach(absence => {
        const employee = employeeMap.get(absence.employeeId);

        const teamId = absence.teamId || UNASSIGNED_TEAM_ID;

        if (!teams[teamId]) {
            teams[teamId] = {
                teamId: teamId,
                teamName: 'Ohne Team',
                employees: {}
            };
        }

        if (!teams[teamId].employees[absence.employeeId]) {
            const displayName = formatEmployeeDisplayName(
                absence.employeeName,
                employee?.personalnummer || ''
            );

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

    return Object.values(teams).map(team => ({
        teamId: team.teamId,
        teamName: team.teamName,
        employees: Object.values(team.employees).sort((a, b) => {
            if (a.isTeamLeader && !b.isTeamLeader) return -1;
            if (!a.isTeamLeader && b.isTeamLeader) return 1;
            return a.name.localeCompare(b.name);
        })
    })).sort((a, b) => {
        if (a.teamId === UNASSIGNED_TEAM_ID) return 1;
        if (b.teamId === UNASSIGNED_TEAM_ID) return -1;
        return a.teamName.localeCompare(b.teamName);
    });
}

export function getUniqueDates(assignments) {
    const dates = new Set();
    assignments.forEach(a => {
        dates.add(a.date.split('T')[0]);
    });
    return Array.from(dates);
}

/**
 * Generate a range of dates from start to end
 */
export function generateDateRange(start, end) {
    const dates = [];
    const startDate = typeof start === 'string' ? new Date(start) : start;
    const endDate = typeof end === 'string' ? new Date(end) : end;

    for (let d = new Date(startDate); d <= endDate; d = new Date(d.getTime() + MS_PER_DAY)) {
        dates.push(d.toISOString().split('T')[0]);
    }
    return dates;
}

/**
 * Check if employee has an absence on a specific date
 */
export function getAbsenceForDate(absences, dateStr) {
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
 */
export function getWeekNumber(date) {
    const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
    const dayNum = d.getUTCDay() || 7;
    d.setUTCDate(d.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    return Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
}

export function groupDatesByWeek(dates) {
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

export function groupDatesByMonth(dates) {
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

    return Object.values(months).map(month => ({
        ...month,
        weeks: Array.from(month.weeks).sort((a, b) => a - b)
    })).sort((a, b) => a.key.localeCompare(b.key));
}

/**
 * Calculate Easter Sunday for a given year using the Meeus/Jones/Butcher algorithm
 */
export function calculateEaster(year) {
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
 */
export function isHessianHoliday(date) {
    const year = date.getFullYear();
    const month = date.getMonth();
    const day = date.getDate();

    const fixedHolidays = [
        [0, 1],
        [4, 1],
        [9, 3],
        [11, 25],
        [11, 26]
    ];

    for (const [m, d] of fixedHolidays) {
        if (month === m && day === d) {
            return true;
        }
    }

    const easter = calculateEaster(year);
    const easterTime = easter.getTime();
    const dateTime = date.getTime();

    if (dateTime === easterTime - 2 * MS_PER_DAY) return true;
    if (dateTime === easterTime + 1 * MS_PER_DAY) return true;
    if (dateTime === easterTime + 39 * MS_PER_DAY) return true;
    if (dateTime === easterTime + 50 * MS_PER_DAY) return true;
    if (dateTime === easterTime + 60 * MS_PER_DAY) return true;

    return false;
}

// ============================================================================
// TOAST NOTIFICATION SYSTEM
// ============================================================================

/**
 * Show a toast notification.
 * @param {string} message - The message to display
 * @param {'success'|'error'|'warning'|'info'} type - Toast type
 * @param {number} duration - Auto-dismiss duration in ms (default 4000)
 */
export function showToast(message, type = 'info', duration = 4000) {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || icons.info}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" aria-label="Schließen">&times;</button>
    `;

    const close = toast.querySelector('.toast-close');
    let removed = false;
    const removeToast = () => {
        if (removed) return;
        removed = true;
        toast.remove();
    };
    const dismiss = () => {
        toast.classList.add('toast-hiding');
        toast.addEventListener('transitionend', removeToast, { once: true });
        setTimeout(removeToast, 350);
    };
    close.addEventListener('click', dismiss);

    container.appendChild(toast);

    // Trigger entrance animation
    requestAnimationFrame(() => toast.classList.add('toast-visible'));

    if (duration > 0) {
        setTimeout(dismiss, duration);
    }
}

function buildDialogShell(title) {
    const overlay = document.createElement('div');
    overlay.className = 'modal';
    overlay.style.display = 'block';

    const content = document.createElement('div');
    content.className = 'modal-content';

    const heading = document.createElement('h2');
    heading.textContent = title;

    const body = document.createElement('p');
    body.style.marginBottom = '16px';

    const actions = document.createElement('div');
    actions.className = 'form-actions';

    content.appendChild(heading);
    content.appendChild(body);
    content.appendChild(actions);
    overlay.appendChild(content);
    document.body.appendChild(overlay);

    return { overlay, content, body, actions };
}

/**
 * Promise-based confirm dialog with app styling.
 */
export function confirmDialog(
    message,
    {
        title = 'Bestätigung',
        confirmText = 'Bestätigen',
        cancelText = 'Abbrechen',
    } = {}
) {
    return new Promise((resolve) => {
        const { overlay, content, body, actions } = buildDialogShell(title);
        body.textContent = message;

        const cancelButton = document.createElement('button');
        cancelButton.type = 'button';
        cancelButton.className = 'btn-secondary';
        cancelButton.textContent = cancelText;

        const confirmButton = document.createElement('button');
        confirmButton.type = 'button';
        confirmButton.className = 'btn-primary';
        confirmButton.textContent = confirmText;

        const cleanup = (result) => {
            document.removeEventListener('keydown', onKeyDown);
            overlay.remove();
            resolve(result);
        };

        const onKeyDown = (event) => {
            if (event.key === 'Escape') cleanup(false);
            if (event.key === 'Enter') cleanup(true);
        };

        cancelButton.addEventListener('click', () => cleanup(false));
        confirmButton.addEventListener('click', () => cleanup(true));
        overlay.addEventListener('click', (event) => {
            if (event.target === overlay) cleanup(false);
        });

        document.addEventListener('keydown', onKeyDown);
        actions.appendChild(cancelButton);
        actions.appendChild(confirmButton);

        setTimeout(() => confirmButton.focus(), 0);
    });
}

/**
 * Promise-based input dialog with app styling.
 */
export function promptDialog(
    message,
    {
        title = 'Eingabe erforderlich',
        placeholder = '',
        defaultValue = '',
        confirmText = 'Übernehmen',
        cancelText = 'Abbrechen',
    } = {}
) {
    return new Promise((resolve) => {
        const { overlay, content, body, actions } = buildDialogShell(title);
        body.textContent = message;

        const input = document.createElement('input');
        input.type = 'text';
        input.placeholder = placeholder;
        input.value = defaultValue;
        input.style.width = '100%';
        input.style.marginBottom = '16px';
        input.style.padding = '10px 12px';
        input.style.border = '2px solid var(--border-color)';
        input.style.borderRadius = '6px';
        content.insertBefore(input, actions);

        const cancelButton = document.createElement('button');
        cancelButton.type = 'button';
        cancelButton.className = 'btn-secondary';
        cancelButton.textContent = cancelText;

        const confirmButton = document.createElement('button');
        confirmButton.type = 'button';
        confirmButton.className = 'btn-primary';
        confirmButton.textContent = confirmText;

        const cleanup = (result) => {
            document.removeEventListener('keydown', onKeyDown);
            overlay.remove();
            resolve(result);
        };

        const onKeyDown = (event) => {
            if (event.key === 'Escape') cleanup(null);
            if (event.key === 'Enter') cleanup(input.value.trim());
        };

        cancelButton.addEventListener('click', () => cleanup(null));
        confirmButton.addEventListener('click', () => cleanup(input.value.trim()));
        overlay.addEventListener('click', (event) => {
            if (event.target === overlay) cleanup(null);
        });

        document.addEventListener('keydown', onKeyDown);
        actions.appendChild(cancelButton);
        actions.appendChild(confirmButton);

        setTimeout(() => {
            input.focus();
            input.select();
        }, 0);
    });
}

/**
 * Debounce helper for high-frequency UI events.
 */
export function debounce(fn, delay = 200) {
    let timer = null;
    return (...args) => {
        if (timer) {
            clearTimeout(timer);
        }
        timer = setTimeout(() => fn(...args), delay);
    };
}

// ============================================================================
// CENTRAL API CALL WRAPPER
// ============================================================================

let _csrfToken = null;

export async function fetchCsrfToken() {
    for (let attempt = 0; attempt < 2; attempt++) {
        try {
            const resp = await fetch(`${API_BASE}/csrf-token`, { credentials: 'include' });
            if (resp.ok) {
                const data = await resp.json();
                _csrfToken = data.token;
                return;
            }
        } catch (e) {
            console.warn('Could not fetch CSRF token', e);
        }
    }
}

export function getCsrfToken() { return _csrfToken; }

export async function apiCall(url, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const isMutating = ['POST', 'PUT', 'DELETE', 'PATCH'].includes(method);

    if (isMutating && !_csrfToken) {
        await fetchCsrfToken();
    }

    const headers = { ...(options.headers || {}) };
    if (isMutating && _csrfToken) {
        headers['X-CSRF-Token'] = _csrfToken;
    }
    
    const defaultOptions = {
        credentials: 'include',
        ...options,
        headers,
    };

    let response;
    try {
        response = await fetch(url, defaultOptions);
    } catch (networkError) {
        showToast(`Netzwerkfehler: ${networkError.message}`, 'error');
        throw networkError;
    }

    if (!response.ok) {
        let errorMessage = `HTTP ${response.status}`;
        try {
            const data = await response.clone().json();
            errorMessage = data.error || data.message || errorMessage;
        } catch {
            // ignore JSON parse error
        }

        if (response.status === 401) {
            showToast('Bitte melden Sie sich an.', 'warning');
        } else if (response.status === 403) {
            showToast('Keine Berechtigung für diese Aktion.', 'error');
        } else if (response.status === 429) {
            showToast('Zu viele Anfragen. Bitte warten Sie kurz.', 'warning');
        } else {
            showToast(errorMessage, 'error');
        }
    }

    return response;
}

export function showLoading(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = '<div class="loading-spinner" role="status" aria-label="Wird geladen..."></div>';
    }
}

export function hideLoading(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        const spinner = container.querySelector('.loading-spinner');
        if (spinner) spinner.remove();
    }
}
