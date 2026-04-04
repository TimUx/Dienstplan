import { API_BASE, escapeHtml, escapeJsString, sanitizeColorCode, formatImportResult, showToast } from './utils.js';
import { hasRole, canEditEmployees, canPlanShifts } from './auth.js';
import { store } from './store.js';

// ============================================================================
// EMPLOYEE MANAGEMENT
// ============================================================================

export async function loadEmployees() {
    const content = document.getElementById('employees-content');
    content.innerHTML = '<p class="loading">Lade Mitarbeiter...</p>';

    try {
        const response = await fetch(`${API_BASE}/employees`);
        const employees = await response.json();

        cachedEmployees = employees;
        store.setState('cachedEmployees', cachedEmployees);

        displayEmployees(employees);
    } catch (error) {
        content.innerHTML = `<p class="error">Fehler beim Laden: ${error.message}</p>`;
    }
}

// cachedEmployees is exported so schedule.js can access it
export let cachedEmployees = [];

export function displayEmployees(employees) {
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

export async function showAddEmployeeModal() {
    if (!canEditEmployees()) {
        showToast('Sie haben keine Berechtigung, Mitarbeiter hinzuzufügen. Bitte melden Sie sich als Admin oder Disponent an.', 'warning');
        return;
    }

    document.getElementById('employeeForm').reset();
    document.getElementById('employeeId').value = '';
    document.getElementById('employeeModalTitle').textContent = 'Mitarbeiter hinzufügen';

    document.getElementById('employeePasswordGroup').style.display = 'block';
    document.getElementById('employeePassword').required = true;
    document.getElementById('employeePasswordLabel').textContent = 'Passwort*';

    await loadTeamsForDropdown();

    document.getElementById('employeeModal').style.display = 'block';
}

export async function editEmployee(id) {
    if (!canEditEmployees()) {
        showToast('Sie haben keine Berechtigung, Mitarbeiter zu bearbeiten.', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/employees/${id}`);
        if (!response.ok) {
            showToast('Fehler beim Laden der Mitarbeiterdaten', 'error');
            return;
        }

        const employee = await response.json();

        await loadTeamsForDropdown();

        document.getElementById('employeeId').value = employee.id;
        document.getElementById('vorname').value = employee.vorname;
        document.getElementById('name').value = employee.name;
        document.getElementById('personalnummer').value = employee.personalnummer;
        document.getElementById('email').value = employee.email || '';
        document.getElementById('geburtsdatum').value = employee.geburtsdatum ? employee.geburtsdatum.split('T')[0] : '';
        document.getElementById('teamId').value = employee.teamId || '';
        document.getElementById('isTeamLeader').checked = employee.isTeamLeader || false;

        const roles = employee.roles ? employee.roles.split(',') : [];
        document.getElementById('isAdmin').checked = roles.includes('Admin');

        document.getElementById('isBrandmeldetechniker').checked = employee.isBrandmeldetechniker || false;
        document.getElementById('isBrandschutzbeauftragter').checked = employee.isBrandschutzbeauftragter || false;

        document.getElementById('employeePasswordGroup').style.display = 'block';
        document.getElementById('employeePassword').required = false;
        document.getElementById('employeePassword').value = '';
        document.getElementById('employeePasswordLabel').textContent = 'Neues Passwort (optional)';

        document.getElementById('employeeModalTitle').textContent = 'Mitarbeiter bearbeiten';
        document.getElementById('employeeModal').style.display = 'block';
    } catch (error) {
        showToast(`Fehler: ${error.message}`, 'error');
    }
}

export async function deleteEmployee(id, name) {
    if (!hasRole('Admin')) {
        showToast('Nur Administratoren können Mitarbeiter löschen.', 'error');
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
            showToast('Mitarbeiter erfolgreich gelöscht!', 'success');
            loadEmployees();
        } else if (response.status === 401) {
            showToast('Bitte melden Sie sich an.', 'warning');
        } else if (response.status === 403) {
            showToast('Sie haben keine Berechtigung zum Löschen.', 'error');
        } else {
            showToast('Fehler beim Löschen', 'error');
        }
    } catch (error) {
        showToast(`Fehler: ${error.message}`, 'error');
    }
}

export async function loadTeamsForDropdown() {
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

export function closeEmployeeModal() {
    document.getElementById('employeeModal').style.display = 'none';
    document.getElementById('employeeForm').reset();
}

export async function saveEmployee(event) {
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
        isSpringer: false,
        isTeamLeader: document.getElementById('isTeamLeader').checked,
        isAdmin: document.getElementById('isAdmin').checked,
        isBrandmeldetechniker: document.getElementById('isBrandmeldetechniker').checked,
        isBrandschutzbeauftragter: document.getElementById('isBrandschutzbeauftragter').checked
    };

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
            showToast(id ? 'Mitarbeiter erfolgreich aktualisiert!' : 'Mitarbeiter erfolgreich hinzugefügt!', 'success');
            closeEmployeeModal();
            loadEmployees();
        } else if (response.status === 401) {
            showToast('Bitte melden Sie sich an.', 'warning');
        } else if (response.status === 403) {
            showToast('Sie haben keine Berechtigung für diese Aktion.', 'error');
        } else {
            const error = await response.json();
            showToast(`Fehler beim Speichern: ${error.message || 'Unbekannter Fehler'}`, 'error');
        }
    } catch (error) {
        showToast(`Fehler: ${error.message}`, 'error');
    }
}

// ============================================================================
// TEAMS MANAGEMENT
// ============================================================================

export async function loadTeams() {
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

export function displayTeams(teams) {
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

export async function showAddTeamModal() {
    if (!canEditEmployees()) {
        showToast('Sie haben keine Berechtigung, Teams hinzuzufügen.', 'error');
        return;
    }

    document.getElementById('teamForm').reset();
    document.getElementById('teamEditId').value = '';
    document.getElementById('teamModalTitle').textContent = 'Team hinzufügen';
    document.getElementById('teamModal').style.display = 'block';
}

export async function editTeam(id) {
    if (!canEditEmployees()) {
        showToast('Sie haben keine Berechtigung, Teams zu bearbeiten.', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/teams/${id}`, {
            credentials: 'include'
        });
        if (!response.ok) {
            showToast('Fehler beim Laden der Teamdaten', 'error');
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
        showToast(`Fehler: ${error.message}`, 'error');
    }
}

export async function deleteTeam(id, name) {
    if (!hasRole('Admin')) {
        showToast('Nur Administratoren können Teams löschen.', 'error');
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
            showToast('Team erfolgreich gelöscht!', 'success');
            loadTeams();
        } else if (response.status === 401) {
            showToast('Bitte melden Sie sich an.', 'warning');
        } else if (response.status === 403) {
            showToast('Sie haben keine Berechtigung zum Löschen.', 'error');
        } else if (response.status === 400) {
            const errorData = await response.json();
            showToast(errorData.error || 'Fehler beim Löschen', 'error');
        } else {
            const errorData = await response.json().catch(() => ({}));
            showToast(errorData.error || 'Fehler beim Löschen', 'error');
        }
    } catch (error) {
        console.error('Error deleting team:', error);
        showToast(`Fehler: ${error.message}`, 'error');
    }
}

export function closeTeamModal() {
    document.getElementById('teamModal').style.display = 'none';
    document.getElementById('teamForm').reset();
}

export async function saveTeam(event) {
    event.preventDefault();

    const idValue = document.getElementById('teamEditId').value;
    const id = idValue ? parseInt(idValue) : null;
    const team = {
        name: document.getElementById('teamName').value,
        description: document.getElementById('teamDescription').value || null,
        email: document.getElementById('teamEmail').value || null,
        isVirtual: false
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
            showToast(id ? 'Team erfolgreich aktualisiert!' : 'Team erfolgreich hinzugefügt!', 'success');
            closeTeamModal();
            loadTeams();
        } else if (response.status === 401) {
            showToast('Bitte melden Sie sich an.', 'warning');
        } else if (response.status === 403) {
            showToast('Sie haben keine Berechtigung für diese Aktion.', 'error');
        } else {
            showToast('Fehler beim Speichern', 'error');
        }
    } catch (error) {
        showToast(`Fehler: ${error.message}`, 'error');
    }
}

// ============================================================================
// EXPORT / IMPORT FUNCTIONS
// ============================================================================

export async function exportEmployeesCsv() {
    try {
        const response = await fetch(`${API_BASE}/employees/export/csv`, {
            credentials: 'include'
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `mitarbeiter_export_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            showToast('Mitarbeiter erfolgreich exportiert!', 'success');
        } else {
            const error = await response.json();
            showToast(`Fehler beim Export: ${error.error || 'Unbekannter Fehler'}`, 'error');
        }
    } catch (error) {
        console.error('Export error:', error);
        showToast(`Fehler beim Export: ${error.message}`, 'error');
    }
}

export async function exportTeamsCsv() {
    try {
        const response = await fetch(`${API_BASE}/teams/export/csv`, {
            credentials: 'include'
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `teams_export_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            showToast('Teams erfolgreich exportiert!', 'success');
        } else {
            const error = await response.json();
            showToast(`Fehler beim Export: ${error.error || 'Unbekannter Fehler'}`, 'error');
        }
    } catch (error) {
        console.error('Export error:', error);
        showToast(`Fehler beim Export: ${error.message}`, 'error');
    }
}

export function showImportEmployeesModal() {
    document.getElementById('importEmployeesModal').style.display = 'block';
    document.getElementById('importEmployeesForm').reset();
    document.getElementById('importEmployeesResult').innerHTML = '';
}

export function closeImportEmployeesModal() {
    document.getElementById('importEmployeesModal').style.display = 'none';
}

export function showImportTeamsModal() {
    document.getElementById('importTeamsModal').style.display = 'block';
    document.getElementById('importTeamsForm').reset();
    document.getElementById('importTeamsResult').innerHTML = '';
}

export function closeImportTeamsModal() {
    document.getElementById('importTeamsModal').style.display = 'none';
}

// ============================================================================
// TAB NAVIGATION
// ============================================================================

export function switchManagementTab(tabName) {
    document.querySelectorAll('#management-view .tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    document.querySelectorAll('#management-view .tabs:not(.sub-tabs) .tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    const selectedTab = document.getElementById(`management-${tabName}-tab`);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }

    const tabButtons = document.querySelectorAll('#management-view .tabs:not(.sub-tabs) .tab-btn');
    tabButtons.forEach(btn => {
        const btnOnclick = btn.getAttribute('onclick');
        if (btnOnclick && btnOnclick.includes(`'${tabName}'`)) {
            btn.classList.add('active');
        }
    });

    if (tabName === 'employees') {
        loadEmployees();
    } else if (tabName === 'teams') {
        loadTeams();
    } else if (tabName === 'shift-types') {
        switchShiftManagementTab('types');
    }
}

export function switchShiftManagementTab(subTabName) {
    document.querySelectorAll('#management-shift-types-tab > .tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    document.querySelectorAll('.sub-tabs .tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    if (subTabName === 'types') {
        document.getElementById('shift-types-content-tab').classList.add('active');
        loadShiftTypesManagement();
    } else if (subTabName === 'rotation-groups') {
        document.getElementById('shift-rotation-groups-content-tab').classList.add('active');
        loadRotationGroups();
    } else if (subTabName === 'settings') {
        document.getElementById('shift-settings-content-tab').classList.add('active');
        loadGlobalSettings();
    }

    document.querySelectorAll('.sub-tabs .tab-btn').forEach(btn => {
        const btnOnclick = btn.getAttribute('onclick');
        if (btnOnclick && btnOnclick.includes(`'${subTabName}'`)) {
            btn.classList.add('active');
        }
    });
}

// ============================================================================
// SHIFT TYPE MANAGEMENT
// ============================================================================

export function showShiftTypeModal(shiftTypeId = null) {
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

export async function loadShiftTypeForEdit(shiftTypeId) {
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
        document.getElementById('shiftTypeMaxConsecutiveDays').value = shiftType.maxConsecutiveDays || 6;
        document.getElementById('shiftTypeIsActive').checked = shiftType.isActive !== false;
    } catch (error) {
        console.error('Error loading shift type:', error);
        showToast('Fehler beim Laden des Schichttyps.', 'error');
        closeShiftTypeModal();
    }
}

export function editShiftType(shiftTypeId) {
    showShiftTypeModal(shiftTypeId);
}

export function closeShiftTypeModal() {
    document.getElementById('shiftTypeModal').style.display = 'none';
}

export async function saveShiftType(event) {
    event.preventDefault();

    const shiftTypeId = document.getElementById('shiftTypeId').value;
    const minStaffWeekday = parseInt(document.getElementById('shiftTypeMinStaffWeekday').value);
    const maxStaffWeekday = parseInt(document.getElementById('shiftTypeMaxStaffWeekday').value);
    const minStaffWeekend = parseInt(document.getElementById('shiftTypeMinStaffWeekend').value);
    const maxStaffWeekend = parseInt(document.getElementById('shiftTypeMaxStaffWeekend').value);
    const maxConsecutiveDays = parseInt(document.getElementById('shiftTypeMaxConsecutiveDays').value);

    if (minStaffWeekday > maxStaffWeekday) {
        showToast('Fehler: Minimale Personalstärke an Wochentagen darf nicht größer sein als die maximale Personalstärke.', 'error');
        return;
    }
    if (minStaffWeekend > maxStaffWeekend) {
        showToast('Fehler: Minimale Personalstärke am Wochenende darf nicht größer sein als die maximale Personalstärke.', 'error');
        return;
    }
    if (maxConsecutiveDays < 1 || maxConsecutiveDays > 10) {
        showToast('Fehler: Maximale aufeinanderfolgende Tage muss zwischen 1 und 10 liegen.', 'error');
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
        maxConsecutiveDays: maxConsecutiveDays,
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
            showToast(shiftTypeId ? 'Schichttyp erfolgreich aktualisiert!' : 'Schichttyp erfolgreich erstellt!', 'success');
            closeShiftTypeModal();
            loadShiftTypesManagement();
        } else {
            showToast(`Fehler: ${result.error || 'Unbekannter Fehler'}`, 'error');
        }
    } catch (error) {
        console.error('Error saving shift type:', error);
        showToast('Fehler beim Speichern des Schichttyps.', 'error');
    }
}

export async function deleteShiftType(shiftTypeId, shiftCode) {
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
            showToast('Schichttyp erfolgreich gelöscht!', 'success');
            loadShiftTypesManagement();
        } else {
            showToast(`Fehler: ${result.error || 'Unbekannter Fehler'}`, 'error');
        }
    } catch (error) {
        console.error('Error deleting shift type:', error);
        showToast('Fehler beim Löschen des Schichttyps.', 'error');
    }
}

export async function showShiftTypeTeamsModal(shiftTypeId, shiftCode) {
    const modal = document.getElementById('shiftTypeTeamsModal');
    const title = document.getElementById('shiftTypeTeamsModalTitle');

    title.textContent = `Teams für Schicht "${shiftCode}" zuweisen`;
    document.getElementById('shiftTypeTeamsId').value = shiftTypeId;

    modal.style.display = 'block';

    await loadShiftTypeTeams(shiftTypeId);
}

export async function loadShiftTypeTeams(shiftTypeId) {
    try {
        const teamsResponse = await fetch(`${API_BASE}/teams`, {
            credentials: 'include'
        });

        if (!teamsResponse.ok) {
            throw new Error('Failed to load teams');
        }

        const allTeams = await teamsResponse.json();
        const nonVirtualTeams = allTeams.filter(t => !t.isVirtual);

        const assignedResponse = await fetch(`${API_BASE}/shifttypes/${shiftTypeId}/teams`, {
            credentials: 'include'
        });

        if (!assignedResponse.ok) {
            throw new Error('Failed to load assigned teams');
        }

        const assignedTeams = await assignedResponse.json();
        const assignedTeamIds = assignedTeams.map(t => t.id);

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

export function closeShiftTypeTeamsModal() {
    document.getElementById('shiftTypeTeamsModal').style.display = 'none';
}

export async function saveShiftTypeTeams(event) {
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
            showToast('Team-Zuweisungen erfolgreich gespeichert!', 'success');
            closeShiftTypeTeamsModal();
        } else {
            showToast(`Fehler: ${result.error || 'Unbekannter Fehler'}`, 'error');
        }
    } catch (error) {
        console.error('Error saving shift type teams:', error);
        showToast('Fehler beim Speichern der Team-Zuweisungen.', 'error');
    }
}

export async function loadShiftTypesManagement() {
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

export function displayShiftTypesManagement(shiftTypes) {
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
        html += `<button onclick="deleteShiftType(${shift.id}, '${escapeHtml(shift.code)}')" class="btn-small btn-danger">🗑️ Löschen</button>`;
        html += '</td>';
        html += '</tr>';
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

// ============================================================================
// ROTATION GROUPS MANAGEMENT
// ============================================================================

export async function loadRotationGroups() {
    try {
        const response = await fetch(`${API_BASE}/rotationgroups`, {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error('Failed to load rotation groups');
        }

        const groups = await response.json();
        displayRotationGroups(groups);
    } catch (error) {
        console.error('Error loading rotation groups:', error);
        document.getElementById('rotation-groups-content').innerHTML = '<p class="error">Fehler beim Laden der Rotationsgruppen.</p>';
    }
}

export function displayRotationGroups(groups) {
    const container = document.getElementById('rotation-groups-content');

    if (groups.length === 0) {
        container.innerHTML = '<p class="info">Keine Rotationsgruppen vorhanden. Klicken Sie auf "+ Rotationsgruppe hinzufügen" um eine neue Gruppe anzulegen.</p>';
        return;
    }

    let html = '<table class="data-table"><thead><tr>';
    html += '<th>Name</th><th>Beschreibung</th><th>Schichtrotation</th><th>Status</th><th>Aktionen</th>';
    html += '</tr></thead><tbody>';

    groups.forEach(group => {
        const isActive = group.isActive !== false;
        const statusBadge = isActive ? '<span class="badge badge-success">Aktiv</span>' : '<span class="badge badge-secondary">Inaktiv</span>';

        const shiftRotation = group.shifts.map(shift =>
            `<span class="shift-badge" style="background-color: ${sanitizeColorCode(shift.colorCode)}">${escapeHtml(shift.code)}</span>`
        ).join(' → ');

        html += '<tr>';
        html += `<td><strong>${escapeHtml(group.name)}</strong></td>`;
        html += `<td>${group.description ? escapeHtml(group.description) : '<em>Keine Beschreibung</em>'}</td>`;
        html += `<td>${shiftRotation || '<em>Keine Schichten</em>'}</td>`;
        html += `<td>${statusBadge}</td>`;
        html += '<td class="actions">';
        html += `<button onclick="editRotationGroup(${group.id})" class="btn-small btn-secondary">✏️ Bearbeiten</button> `;
        html += `<button onclick="deleteRotationGroup(${group.id}, '${escapeJsString(group.name)}')" class="btn-small btn-danger">🗑️ Löschen</button>`;
        html += '</td>';
        html += '</tr>';
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

export async function showRotationGroupModal(groupId = null) {
    const modal = document.getElementById('rotationGroupModal');
    const title = document.getElementById('rotationGroupModalTitle');

    document.getElementById('rotationGroupForm').reset();
    document.getElementById('rotationGroupId').value = '';
    document.getElementById('rotationGroupIsActive').checked = true;

    if (groupId) {
        title.textContent = 'Rotationsgruppe bearbeiten';
        await loadRotationGroupForEdit(groupId);
    } else {
        title.textContent = 'Rotationsgruppe erstellen';
        await loadAvailableShiftsForRotation();
    }

    modal.style.display = 'block';
}

export async function loadRotationGroupForEdit(groupId) {
    try {
        const response = await fetch(`${API_BASE}/rotationgroups/${groupId}`, {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error('Failed to load rotation group');
        }

        const group = await response.json();

        document.getElementById('rotationGroupId').value = group.id;
        document.getElementById('rotationGroupName').value = group.name;
        document.getElementById('rotationGroupDescription').value = group.description || '';
        document.getElementById('rotationGroupIsActive').checked = group.isActive;

        await loadAvailableShiftsForRotation(group.shifts);
    } catch (error) {
        console.error('Error loading rotation group:', error);
        showToast('Fehler beim Laden der Rotationsgruppe.', 'error');
    }
}

export async function loadAvailableShiftsForRotation(selectedShifts = []) {
    try {
        const response = await fetch(`${API_BASE}/shifttypes`, {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error('Failed to load shift types');
        }

        const allShifts = await response.json();
        const container = document.getElementById('rotationGroupShiftsList');
        let html = '';

        if (selectedShifts.length > 0) {
            selectedShifts.forEach(shift => {
                html += '<div class="sortable-item" data-shift-id="' + shift.id + '">';
                html += '<span class="drag-handle">☰</span>';
                html += `<span class="shift-badge" style="background-color: ${sanitizeColorCode(shift.colorCode)}">${escapeHtml(shift.code)}</span>`;
                html += `<span>${escapeHtml(shift.name)}</span>`;
                html += `<button type="button" class="btn-small btn-danger" onclick="removeShiftFromRotation(this)">✖</button>`;
                html += '</div>';
            });
        }

        const selectedIds = selectedShifts.map(s => s.id);
        const availableShifts = allShifts.filter(s => !selectedIds.includes(s.id));

        if (availableShifts.length > 0) {
            html += '<div class="form-group" style="margin-top: 20px;"><label>Weitere Schichten hinzufügen:</label></div>';
            availableShifts.forEach(shift => {
                html += '<div class="checkbox-item">';
                html += `<label><input type="checkbox" name="available-shift-${shift.id}" value="${shift.id}" onchange="addShiftToRotation(${shift.id}, '${escapeJsString(shift.code)}', '${escapeJsString(shift.name)}', '${sanitizeColorCode(shift.colorCode)}')">`;
                html += `<span class="shift-badge" style="background-color: ${sanitizeColorCode(shift.colorCode)}">${escapeHtml(shift.code)}</span> ${escapeHtml(shift.name)}`;
                html += '</label></div>';
            });
        }

        container.innerHTML = html || '<p>Keine Schichten verfügbar.</p>';

        makeRotationShiftsSortable();
    } catch (error) {
        console.error('Error loading shifts:', error);
        document.getElementById('rotationGroupShiftsList').innerHTML = '<p class="error">Fehler beim Laden der Schichten.</p>';
    }
}

export function addShiftToRotation(shiftId, shiftCode, shiftName, colorCode) {
    const checkbox = document.querySelector(`input[name="available-shift-${shiftId}"]`);
    if (!checkbox.checked) return;

    const container = document.getElementById('rotationGroupShiftsList');
    const formGroup = container.querySelector('.form-group');

    const safeColorCode = sanitizeColorCode(colorCode);

    const newItem = document.createElement('div');
    newItem.className = 'sortable-item';
    newItem.setAttribute('data-shift-id', shiftId);
    newItem.innerHTML = `
        <span class="drag-handle">☰</span>
        <span class="shift-badge" style="background-color: ${safeColorCode}">${escapeHtml(shiftCode)}</span>
        <span>${escapeHtml(shiftName)}</span>
        <button type="button" class="btn-small btn-danger" onclick="removeShiftFromRotation(this)">✖</button>
    `;

    if (formGroup) {
        container.insertBefore(newItem, formGroup);
    } else {
        container.appendChild(newItem);
    }

    checkbox.parentElement.parentElement.remove();

    makeRotationShiftsSortable();
}

export function removeShiftFromRotation(button) {
    const item = button.parentElement;
    const shiftId = item.getAttribute('data-shift-id');
    const shiftBadge = item.querySelector('.shift-badge');
    const shiftName = item.querySelector('span:nth-child(3)').textContent;
    const colorCode = shiftBadge.style.backgroundColor;
    const shiftCode = shiftBadge.textContent;

    const safeColorCode = sanitizeColorCode(colorCode);

    item.remove();

    const container = document.getElementById('rotationGroupShiftsList');
    let checkboxGroup = container.querySelector('.form-group');

    if (!checkboxGroup) {
        checkboxGroup = document.createElement('div');
        checkboxGroup.className = 'form-group';
        checkboxGroup.style.marginTop = '20px';
        checkboxGroup.innerHTML = '<label>Weitere Schichten hinzufügen:</label>';
        container.appendChild(checkboxGroup);
    }

    const newCheckbox = document.createElement('div');
    newCheckbox.className = 'checkbox-item';
    newCheckbox.innerHTML = `
        <label><input type="checkbox" name="available-shift-${shiftId}" value="${shiftId}" onchange="addShiftToRotation(${shiftId}, '${escapeJsString(shiftCode)}', '${escapeJsString(shiftName)}', '${safeColorCode}')">
        <span class="shift-badge" style="background-color: ${safeColorCode}">${escapeHtml(shiftCode)}</span> ${escapeHtml(shiftName)}
        </label>
    `;

    container.appendChild(newCheckbox);
}

export function makeRotationShiftsSortable() {
    const container = document.getElementById('rotationGroupShiftsList');
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
            if (!dragging) return;

            const allSortables = [...container.querySelectorAll('.sortable-item:not(.dragging)')];
            let targetElement = null;

            for (const sortableItem of allSortables) {
                const rect = sortableItem.getBoundingClientRect();
                const itemCenter = rect.top + rect.height / 2;

                if (e.clientY < itemCenter) {
                    targetElement = sortableItem;
                    break;
                }
            }

            if (targetElement) {
                container.insertBefore(dragging, targetElement);
            } else {
                const formGroupElement = container.querySelector('.form-group');
                if (formGroupElement) {
                    container.insertBefore(dragging, formGroupElement);
                } else {
                    container.appendChild(dragging);
                }
            }
        });
    });
}

export async function saveRotationGroup(event) {
    event.preventDefault();

    const groupId = document.getElementById('rotationGroupId').value;
    const name = document.getElementById('rotationGroupName').value;
    const description = document.getElementById('rotationGroupDescription').value;
    const isActive = document.getElementById('rotationGroupIsActive').checked;

    const sortableItems = document.querySelectorAll('#rotationGroupShiftsList .sortable-item');
    const shifts = [];
    sortableItems.forEach((item, index) => {
        shifts.push({
            shiftTypeId: parseInt(item.getAttribute('data-shift-id')),
            rotationOrder: index + 1
        });
    });

    if (shifts.length === 0) {
        showToast('Bitte fügen Sie mindestens eine Schicht zur Rotationsgruppe hinzu.', 'warning');
        return;
    }

    const data = {
        name: name,
        description: description,
        isActive: isActive,
        shifts: shifts
    };

    try {
        const url = groupId ? `${API_BASE}/rotationgroups/${groupId}` : `${API_BASE}/rotationgroups`;
        const method = groupId ? 'PUT' : 'POST';

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Fehler beim Speichern');
        }

        closeRotationGroupModal();
        loadRotationGroups();
        showToast(groupId ? 'Rotationsgruppe erfolgreich aktualisiert!' : 'Rotationsgruppe erfolgreich erstellt!', 'success');
    } catch (error) {
        console.error('Error saving rotation group:', error);
        showToast('Fehler beim Speichern: ' + error.message, 'error');
    }
}

export async function editRotationGroup(groupId) {
    await showRotationGroupModal(groupId);
}

export async function deleteRotationGroup(groupId, groupName) {
    if (!confirm(`Möchten Sie die Rotationsgruppe "${groupName}" wirklich löschen?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/rotationgroups/${groupId}`, {
            method: 'DELETE',
            credentials: 'include'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Fehler beim Löschen');
        }

        loadRotationGroups();
        showToast('Rotationsgruppe erfolgreich gelöscht!', 'success');
    } catch (error) {
        console.error('Error deleting rotation group:', error);
        showToast('Fehler beim Löschen: ' + error.message, 'error');
    }
}

export function closeRotationGroupModal() {
    document.getElementById('rotationGroupModal').style.display = 'none';
}

// ============================================================================
// GLOBAL SETTINGS
// ============================================================================

export async function loadGlobalSettings() {
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

export function displayGlobalSettings(settings) {
    const container = document.getElementById('global-settings-content');

    const isAdmin = hasRole('Admin');
    const readonly = !isAdmin ? 'readonly' : '';

    let html = '<div class="settings-form">';
    html += '<div class="info-box info">';
    html += '<p>ℹ️ Diese Einstellungen gelten für die automatische Schichtplanung und Validierung.</p>';
    html += '</div>';

    html += '<form id="global-settings-form" onsubmit="saveGlobalSettings(event)">';

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

export async function saveGlobalSettings(event) {
    event.preventDefault();

    if (!hasRole('Admin')) {
        showToast('Nur Administratoren können Einstellungen ändern.', 'error');
        return;
    }

    const form = document.getElementById('global-settings-form');
    const formData = new FormData(form);

    const settings = {
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
            showToast('Einstellungen erfolgreich gespeichert!', 'success');
            loadGlobalSettings();
        } else if (response.status === 401) {
            showToast('Bitte melden Sie sich an.', 'warning');
        } else if (response.status === 403) {
            showToast('Sie haben keine Berechtigung für diese Aktion.', 'error');
        } else {
            const error = await response.json();
            showToast(`Fehler beim Speichern: ${error.error || 'Unbekannter Fehler'}`, 'error');
        }
    } catch (error) {
        console.error('Error saving global settings:', error);
        showToast(`Fehler: ${error.message}`, 'error');
    }
}

// ============================================================================
// ADMIN: USER MANAGEMENT
// ============================================================================

export async function loadAdminView() {
    loadUsers();
    loadEmailSettings();
}

export async function loadUsers() {
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

export function displayUsers(users) {
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

export async function editUser(userId) {
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
            document.getElementById('passwordGroup').style.display = 'block';
            document.getElementById('userPassword').required = false;
            document.getElementById('userPassword').value = '';
            document.getElementById('passwordLabel').textContent = 'Neues Passwort (optional)';
            document.getElementById('userModal').style.display = 'block';
        } else {
            showToast('Fehler beim Laden des Benutzers.', 'error');
        }
    } catch (error) {
        console.error('Error loading user:', error);
        showToast('Fehler beim Laden des Benutzers.', 'error');
    }
}

export async function deleteUser(userId, userEmail) {
    if (!confirm(`Möchten Sie den Benutzer "${userEmail}" wirklich löschen?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/auth/users/${userId}`, {
            method: 'DELETE',
            credentials: 'include'
        });

        if (response.ok) {
            showToast('Benutzer erfolgreich gelöscht!', 'success');
            loadUsers();
        } else {
            const error = await response.json();
            showToast(`Fehler beim Löschen: ${error.error || 'Unbekannter Fehler'}`, 'error');
        }
    } catch (error) {
        console.error('Error deleting user:', error);
        showToast(`Fehler: ${error.message}`, 'error');
    }
}

export async function showAddUserModal() {
    if (!hasRole('Admin')) {
        showToast('Nur Administratoren können Benutzer hinzufügen.', 'error');
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

export function closeUserModal() {
    document.getElementById('userModal').style.display = 'none';
    document.getElementById('userForm').reset();
}

export async function saveUser(event) {
    event.preventDefault();

    const userId = document.getElementById('userId').value;
    const isEdit = userId !== '';

    const userData = {
        fullName: document.getElementById('userFullName').value,
        email: document.getElementById('userEmail').value,
        role: document.getElementById('userRole').value
    };

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
            showToast(isEdit ? 'Benutzer erfolgreich aktualisiert!' : 'Benutzer erfolgreich erstellt!', 'success');
            closeUserModal();
            loadUsers();
        } else if (response.status === 401) {
            showToast('Bitte melden Sie sich an.', 'warning');
        } else if (response.status === 403) {
            showToast('Sie haben keine Berechtigung für diese Aktion.', 'error');
        } else {
            const error = await response.json();
            showToast(`Fehler beim ${isEdit ? 'Aktualisieren' : 'Erstellen'}: ${error.error || 'Unbekannter Fehler'}`, 'error');
        }
    } catch (error) {
        showToast(`Fehler: ${error.message}`, 'error');
    }
}

// ============================================================================
// EMAIL SETTINGS
// ============================================================================

export async function loadEmailSettings() {
    const content = document.getElementById('email-settings-content');

    try {
        const response = await fetch(`${API_BASE}/email-settings`, {
            credentials: 'include'
        });

        if (response.ok) {
            const settings = await response.json();
            displayEmailSettings(settings);
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

export function displayEmailSettings(settings) {
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

export async function showEmailSettingsModal() {
    if (!hasRole('Admin')) {
        showToast('Nur Administratoren können E-Mail-Einstellungen bearbeiten.', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/email-settings`, {
            credentials: 'include'
        });

        if (response.ok) {
            const settings = await response.json();
            document.getElementById('smtpServer').value = settings.smtpHost || '';
            document.getElementById('smtpPort').value = settings.smtpPort || 587;
            document.getElementById('smtpSecurity').value = settings.useSsl ? 'SSL' : 'NONE';
            document.getElementById('requiresAuth').checked = settings.requiresAuthentication !== false;
            document.getElementById('smtpUsername').value = settings.username || '';
            document.getElementById('senderEmail').value = settings.senderEmail || '';
            document.getElementById('senderName').value = settings.senderName || '';
            document.getElementById('replyToEmail').value = settings.replyToEmail || '';
            document.getElementById('emailEnabled').checked = settings.isEnabled !== false;
        } else {
            document.getElementById('emailSettingsForm').reset();
            document.getElementById('smtpPort').value = 587;
            document.getElementById('emailEnabled').checked = false;
        }
    } catch (error) {
        console.error('Error loading email settings:', error);
        document.getElementById('emailSettingsForm').reset();
    }

    document.getElementById('requiresAuth').onchange = function() {
        document.getElementById('authFields').style.display = this.checked ? 'block' : 'none';
    };
    document.getElementById('authFields').style.display = document.getElementById('requiresAuth').checked ? 'block' : 'none';

    document.getElementById('emailSettingsModal').style.display = 'block';
}

export function closeEmailSettingsModal() {
    document.getElementById('emailSettingsModal').style.display = 'none';
    document.getElementById('emailSettingsForm').reset();
}

export async function saveEmailSettings(event) {
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
            showToast('E-Mail-Einstellungen erfolgreich gespeichert!', 'success');
            closeEmailSettingsModal();
            loadEmailSettings();
        } else {
            const error = await response.json();
            showToast(`Fehler beim Speichern: ${error.error || 'Unbekannter Fehler'}`, 'error');
        }
    } catch (error) {
        console.error('Error saving email settings:', error);
        showToast(`Fehler: ${error.message}`, 'error');
    }
}

export async function testEmailSettings() {
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
            showToast(`Test-E-Mail wurde erfolgreich an ${testEmail} gesendet!`, 'success');
        } else {
            const error = await response.json();
            showToast(`Fehler beim Senden der Test-E-Mail: ${error.error || 'Unbekannter Fehler'}`, 'error');
        }
    } catch (error) {
        console.error('Error testing email settings:', error);
        showToast(`Fehler: ${error.message}`, 'error');
    }
}

// ============================================================================
// ADMIN TAB NAVIGATION
// ============================================================================

export const AUDIT_LOG_DEFAULT_REFRESH_INTERVAL = 60;
export const AUDIT_LOG_MIN_REFRESH_INTERVAL = 5;

export let currentAuditPage = 1;
export let currentAuditPageSize = 50;
export let currentAuditFilters = {};
export let auditLogRefreshInterval = null;
export let auditLogRefreshIntervalTime = AUDIT_LOG_DEFAULT_REFRESH_INTERVAL * 1000;

export function showAdminTab(tabName, clickedElement) {
    const allTabContents = document.querySelectorAll('.admin-tab-content');
    allTabContents.forEach(content => content.classList.remove('active'));

    const allTabs = document.querySelectorAll('.admin-tab');
    allTabs.forEach(tab => tab.classList.remove('active'));

    const selectedContent = document.getElementById(`admin-tab-${tabName}`);
    if (selectedContent) {
        selectedContent.classList.add('active');
    }

    if (clickedElement) {
        clickedElement.classList.add('active');
    } else {
        const tabButton = document.querySelector(`.admin-tab[onclick*="${tabName}"]`);
        if (tabButton) {
            tabButton.classList.add('active');
        }
    }

    if (tabName === 'audit-logs') {
        loadAuditLogs(1, 50);
        startAuditLogAutoRefresh(AUDIT_LOG_DEFAULT_REFRESH_INTERVAL);
    } else if (tabName === 'email') {
        stopAuditLogAutoRefresh();
        loadEmailSettings();
    } else {
        stopAuditLogAutoRefresh();
    }
}

// ============================================================================
// AUDIT LOG FUNCTIONS (paginated version)
// ============================================================================

export async function loadAuditLogs(page = 1, pageSize = 50) {
    const content = document.getElementById('audit-logs-content');
    content.innerHTML = '<p class="loading">Lade Änderungsprotokoll...</p>';

    currentAuditPage = page;
    currentAuditPageSize = pageSize;

    try {
        let queryParams = new URLSearchParams({
            page: page,
            pageSize: pageSize
        });

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

export function displayAuditLogsPaginated(result) {
    const content = document.getElementById('audit-logs-content');
    const pagination = document.getElementById('audit-pagination');

    if (!result.items || result.items.length === 0) {
        content.innerHTML = '<p>Keine Einträge im Änderungsprotokoll gefunden.</p>';
        pagination.style.display = 'none';
        return;
    }

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

    pagination.style.display = 'flex';
    document.getElementById('audit-page-info').textContent = `Seite ${result.page} von ${result.totalPages} (${result.totalCount} Einträge)`;
    document.getElementById('audit-prev-btn').disabled = !result.hasPreviousPage;
    document.getElementById('audit-next-btn').disabled = !result.hasNextPage;
}

export function applyAuditFilters() {
    currentAuditFilters = {
        entityName: document.getElementById('audit-filter-entity').value,
        action: document.getElementById('audit-filter-action').value,
        startDate: document.getElementById('audit-filter-start-date').value,
        endDate: document.getElementById('audit-filter-end-date').value
    };

    loadAuditLogs(1, currentAuditPageSize);
}

export function clearAuditFilters() {
    document.getElementById('audit-filter-entity').value = '';
    document.getElementById('audit-filter-action').value = '';
    document.getElementById('audit-filter-start-date').value = '';
    document.getElementById('audit-filter-end-date').value = '';

    currentAuditFilters = {};
    loadAuditLogs(1, currentAuditPageSize);
}

export function loadAuditLogsPreviousPage() {
    if (currentAuditPage > 1) {
        loadAuditLogs(currentAuditPage - 1, currentAuditPageSize);
    }
}

export function loadAuditLogsNextPage() {
    loadAuditLogs(currentAuditPage + 1, currentAuditPageSize);
}

export function startAuditLogAutoRefresh(intervalSeconds = 60) {
    stopAuditLogAutoRefresh();

    auditLogRefreshIntervalTime = intervalSeconds * 1000;

    auditLogRefreshInterval = setInterval(() => {
        const auditLogsTab = document.getElementById('admin-tab-audit-logs');
        if (auditLogsTab && auditLogsTab.classList.contains('active')) {
            console.log('Auto-refreshing audit logs...');
            loadAuditLogs(currentAuditPage, currentAuditPageSize);
        }
    }, auditLogRefreshIntervalTime);

    const statusElement = document.getElementById('audit-auto-refresh-status');
    if (statusElement) {
        statusElement.textContent = `🔄 Auto-Aktualisierung: Aktiv (${intervalSeconds}s)`;
        statusElement.style.color = '#4CAF50';
    }

    console.log(`Audit log auto-refresh started with ${intervalSeconds} second interval`);
}

export function stopAuditLogAutoRefresh() {
    if (auditLogRefreshInterval) {
        clearInterval(auditLogRefreshInterval);
        auditLogRefreshInterval = null;

        const statusElement = document.getElementById('audit-auto-refresh-status');
        if (statusElement) {
            statusElement.textContent = '⏸ Auto-Aktualisierung: Inaktiv';
            statusElement.style.color = '#999';
        }

        console.log('Audit log auto-refresh stopped');
    }
}

export function setAuditLogRefreshInterval(intervalSeconds) {
    if (intervalSeconds < AUDIT_LOG_MIN_REFRESH_INTERVAL) {
        console.warn(`Minimum refresh interval is ${AUDIT_LOG_MIN_REFRESH_INTERVAL} seconds`);
        intervalSeconds = AUDIT_LOG_MIN_REFRESH_INTERVAL;
    }

    auditLogRefreshIntervalTime = intervalSeconds * 1000;

    if (auditLogRefreshInterval) {
        startAuditLogAutoRefresh(intervalSeconds);
    }

    console.log(`Audit log refresh interval set to ${intervalSeconds} seconds`);
}

export function getActionBadge(action) {
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

export function getEntityNameTranslation(entityName) {
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
