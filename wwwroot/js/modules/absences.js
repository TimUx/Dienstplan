import { API_BASE, escapeHtml, ABSENCE_TYPES } from './utils.js';
import { hasRole, canPlanShifts } from './auth.js';
import { loadSchedule } from './schedule.js';

// ============================================================================
// VACATION REQUESTS
// ============================================================================

export async function loadVacationRequests(filter = 'all') {
    const content = document.getElementById('vacation-requests-content');
    content.innerHTML = '<p class="loading">Lade Urlaubsanträge...</p>';

    try {
        let url = `${API_BASE}/vacationrequests`;
        if (filter === 'pending') {
            url += '/pending';
        }

        const response = await fetch(url, {
            credentials: 'include'
        });

        if (response.ok) {
            let requests = await response.json();
            const { currentUser } = await import('./auth.js');
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

export function displayVacationRequests(requests) {
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
        } else if (canProcess && req.status === 'Genehmigt') {
            html += `
                <td>
                    <button onclick="deleteVacationRequest(${req.id}, '${escapeHtml(req.employeeName)}')" class="btn-small btn-danger">🗑️ Stornieren</button>
                </td>`;
        } else if (canProcess) {
            html += '<td>-</td>';
        }

        html += '</tr>';
    });
    html += '</tbody></table>';
    content.innerHTML = html;
}

export async function showAddVacationRequestModal() {
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

export function closeVacationRequestModal() {
    document.getElementById('vacationRequestModal').style.display = 'none';
    document.getElementById('vacationRequestForm').reset();
}

export async function saveVacationRequest(event) {
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

export async function processVacationRequest(id, status) {
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

export async function deleteVacationRequest(id, employeeName) {
    if (!confirm(`Möchten Sie den Urlaubsantrag von "${employeeName}" wirklich stornieren?\n\nDieser genehmigte Urlaub wird gelöscht.`)) {
        return;
    }

    try {
        const result = await fetch(`${API_BASE}/vacationrequests/${id}`, {
            method: 'DELETE',
            credentials: 'include'
        });

        if (result.ok) {
            alert('Urlaubsantrag wurde erfolgreich storniert!');
            loadVacationRequests('all');
        } else if (result.status === 401) {
            alert('Bitte melden Sie sich an.');
        } else if (result.status === 403) {
            alert('Sie haben keine Berechtigung für diese Aktion.');
        } else {
            const error = await result.json();
            alert(error.error || 'Fehler beim Stornieren des Urlaubsantrags.');
        }
    } catch (error) {
        alert(`Fehler: ${error.message}`);
    }
}

// ============================================================================
// ABSENCE TAB SWITCHING
// ============================================================================

export function switchAbsenceTab(tabName) {
    document.querySelectorAll('#absences-view .tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    document.querySelectorAll('#absences-view .tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    const selectedTab = document.getElementById(`${tabName}-tab`);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }

    const tabButtons = document.querySelectorAll('#absences-view .tab-btn');
    tabButtons.forEach(btn => {
        const btnOnclick = btn.getAttribute('onclick');
        if (btnOnclick && btnOnclick.includes(`'${tabName}'`)) {
            btn.classList.add('active');
        }
    });

    if (tabName === 'vacation') {
        loadVacationRequests('all');
    } else if (tabName === 'general') {
        loadAbsences('general');
    } else if (tabName === 'vacation-periods') {
        loadVacationPeriods();
    } else if (tabName === 'vacation-year-approvals') {
        loadVacationYearApprovalsAbsence();
    } else if (tabName === 'absence-types') {
        loadAbsenceTypes();
    }
}

// ============================================================================
// GENERAL ABSENCES
// ============================================================================

export async function loadAbsences(type) {
    const contentId = 'general-absences-content';

    const content = document.getElementById(contentId);
    if (!content) {
        console.error(`Content element not found: ${contentId}`);
        return;
    }

    content.innerHTML = '<p class="loading">Lade Abwesenheiten...</p>';

    try {
        const response = await fetch(`${API_BASE}/absences`, {
            credentials: 'include'
        });

        if (response.ok) {
            const absences = await response.json();
            const filteredAbsences = absences.filter(a => a.typeCode !== 'U' && a.type !== 'Urlaub');
            displayAbsences(filteredAbsences, type);
        } else {
            content.innerHTML = '<p class="error">Fehler beim Laden der Abwesenheiten.</p>';
        }
    } catch (error) {
        console.error('Error loading absences:', error);
        content.innerHTML = '<p class="error">Fehler beim Laden der Abwesenheiten.</p>';
    }
}

export function displayAbsences(absences, type) {
    const contentId = 'general-absences-content';

    const content = document.getElementById(contentId);
    if (!content) {
        console.error(`Content element not found: ${contentId}`);
        return;
    }

    if (absences.length === 0) {
        content.innerHTML = '<p>Keine Abwesenheiten vorhanden.</p>';
        return;
    }

    const canDelete = hasRole('Admin') || hasRole('Disponent');

    let html = '<table class="data-table"><thead><tr>';
    html += '<th>Mitarbeiter</th>';
    html += '<th>Typ</th>';
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

        const typeColor = absence.typeColor || '#E0E0E0';
        html += `<td><span style="display: inline-block; padding: 2px 8px; background: ${typeColor}; border: 1px solid #ccc; border-radius: 4px; font-weight: bold;">${absence.typeCode || absence.type}</span></td>`;

        html += `<td>${new Date(absence.startDate).toLocaleDateString('de-DE')}</td>`;
        html += `<td>${new Date(absence.endDate).toLocaleDateString('de-DE')}</td>`;
        html += `<td>${absence.notes || '-'}</td>`;
        html += `<td>${absence.createdAt ? new Date(absence.createdAt).toLocaleDateString('de-DE') : '-'}</td>`;

        if (canDelete) {
            html += `<td><button onclick="deleteAbsence(${absence.id}, '${type}')" class="btn-small btn-danger">Löschen</button></td>`;
        }

        html += '</tr>';
    });
    html += '</tbody></table>';
    content.innerHTML = html;
}

export async function showAddAbsenceModal(type) {
    const modalTitle = document.getElementById('absenceModalTitle');

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

    if (!type || type === 'all' || type === 'general') {
        try {
            const response = await fetch(`${API_BASE}/absencetypes`);
            if (response.ok) {
                const absenceTypes = await response.json();
                const select = document.getElementById('absenceTypeIdSelect');
                select.innerHTML = '<option value="">Abwesenheitstyp wählen...</option>';
                absenceTypes.forEach(at => {
                    if (type === 'general' && (at.code === 'U' || at.name === 'Urlaub')) {
                        return;
                    }
                    select.innerHTML += `<option value="${at.id}">${at.name} (${at.code})</option>`;
                });
                document.getElementById('absenceTypeSelectGroup').style.display = 'block';
                document.getElementById('absenceType').value = '';
            }
        } catch (error) {
            console.error('Error loading absence types:', error);
        }
        modalTitle.textContent = 'Abwesenheit erfassen';
    } else {
        document.getElementById('absenceTypeSelectGroup').style.display = 'none';
        document.getElementById('absenceType').value = type;
    }

    if (type === 'AU') {
        modalTitle.textContent = 'Arbeitsunfähigkeit (AU) erfassen';
    } else if (type === 'L') {
        modalTitle.textContent = 'Lehrgang erfassen';
    } else if (!type || type === 'all') {
        modalTitle.textContent = 'Abwesenheit erfassen';
    }

    document.getElementById('absenceForm').reset();
    if (type && type !== 'all' && type !== 'general') {
        document.getElementById('absenceType').value = type;
    }
    document.getElementById('absenceModal').style.display = 'block';
}

export function closeAbsenceModal() {
    document.getElementById('absenceModal').style.display = 'none';
    document.getElementById('absenceForm').reset();
}

export async function saveAbsence(event) {
    event.preventDefault();

    const type = document.getElementById('absenceType').value;
    const absenceTypeId = document.getElementById('absenceTypeIdSelect').value;

    const absence = {
        employeeId: parseInt(document.getElementById('absenceEmployeeId').value),
        startDate: document.getElementById('absenceStartDate').value,
        endDate: document.getElementById('absenceEndDate').value,
        notes: document.getElementById('absenceNotes').value || null
    };

    if (absenceTypeId) {
        absence.absenceTypeId = parseInt(absenceTypeId);
    } else if (type) {
        const typeValue = type === 'AU' ? ABSENCE_TYPES.AU : ABSENCE_TYPES.L;
        absence.type = typeValue;
    } else {
        alert('Bitte wählen Sie einen Abwesenheitstyp.');
        return;
    }

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
            if (type) {
                loadAbsences(type);
            } else {
                const activeTab = document.querySelector('#absences-view .tab-content.active');
                if (activeTab) {
                    const tabId = activeTab.id.replace('-tab', '');
                    if (tabId === 'general') {
                        loadAbsences('general');
                    }
                }
            }
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an.');
        } else if (response.status === 403) {
            alert('Sie haben keine Berechtigung für diese Aktion.');
        } else {
            const error = await response.json();
            alert(error.error || 'Fehler beim Speichern der Abwesenheit.');
        }
    } catch (error) {
        alert(`Fehler: ${error.message}`);
    }
}

export async function deleteAbsence(id, type) {
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

// ============================================================================
// SHIFT EXCHANGES
// ============================================================================

export async function loadShiftExchanges(filter = 'available') {
    const content = document.getElementById('shift-exchanges-content');
    content.innerHTML = '<p class="loading">Lade Diensttausch-Angebote...</p>';

    try {
        let url = `${API_BASE}/shiftexchanges/${filter}`;
        if (filter === 'my') {
            url = `${API_BASE}/shiftexchanges/available`;
        }

        const response = await fetch(url, {
            credentials: 'include'
        });

        if (response.ok) {
            const exchanges = await response.json();
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

export function displayShiftExchanges(exchanges, filter) {
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

export async function showOfferShiftExchangeModal() {
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

        document.getElementById('exchangeDate').onchange = loadShiftsForExchange;
        document.getElementById('exchangeEmployeeId').onchange = loadShiftsForExchange;

    } catch (error) {
        console.error('Error loading employees:', error);
    }

    document.getElementById('shiftExchangeForm').reset();
    document.getElementById('shiftExchangeModal').style.display = 'block';
}

export async function loadShiftsForExchange() {
    const date = document.getElementById('exchangeDate').value;
    const employeeId = document.getElementById('exchangeEmployeeId').value;
    const select = document.getElementById('exchangeShiftId');

    if (!date || !employeeId) {
        select.innerHTML = '<option value="">Zuerst Datum und Mitarbeiter wählen...</option>';
        return;
    }

    try {
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

export function closeShiftExchangeModal() {
    document.getElementById('shiftExchangeModal').style.display = 'none';
    document.getElementById('shiftExchangeForm').reset();
}

export async function saveShiftExchange(event) {
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

export async function requestShiftExchange(id) {
    const { currentUser } = await import('./auth.js');
    if (!currentUser) {
        alert('Bitte melden Sie sich an.');
        return;
    }

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

export async function processShiftExchange(id, status) {
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

// ============================================================================
// VACATION PERIODS (FERIENZEITEN)
// ============================================================================

export async function loadVacationPeriods() {
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

export function displayVacationPeriods(periods) {
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

export function showVacationPeriodModal(periodId = null) {
    if (!canPlanShifts()) {
        alert('Sie haben keine Berechtigung, Ferienzeiten zu verwalten.');
        return;
    }

    document.getElementById('vacationPeriodForm').reset();
    document.getElementById('vacationPeriodId').value = '';
    document.getElementById('vacationPeriodColor').value = '#E8F5E9';

    if (periodId) {
        document.getElementById('vacationPeriodModalTitle').textContent = 'Ferienzeit bearbeiten';
        loadVacationPeriodForEdit(periodId);
    } else {
        document.getElementById('vacationPeriodModalTitle').textContent = 'Ferienzeit hinzufügen';
    }

    document.getElementById('vacationPeriodModal').style.display = 'block';
}

export async function loadVacationPeriodForEdit(periodId) {
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

export function editVacationPeriod(periodId) {
    showVacationPeriodModal(periodId);
}

export function closeVacationPeriodModal() {
    document.getElementById('vacationPeriodModal').style.display = 'none';
    document.getElementById('vacationPeriodForm').reset();
}

export async function saveVacationPeriod(event) {
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

export async function deleteVacationPeriod(periodId, periodName) {
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
// VACATION YEAR PLAN
// ============================================================================

export function initVacationYearPlan() {
    const yearSelect = document.getElementById('vacationYearSelect');
    if (!yearSelect) return;

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

export async function loadVacationYearPlan() {
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

            legendDiv.style.display = 'block';
            displayVacationYearPlan(data, year);

        } else {
            contentDiv.innerHTML = '<p class="error">Fehler beim Laden des Urlaubsjahresplans.</p>';
        }
    } catch (error) {
        console.error('Error loading vacation year plan:', error);
        contentDiv.innerHTML = '<p class="error">Fehler beim Laden des Urlaubsjahresplans.</p>';
    }
}

export function displayVacationYearPlan(data, year) {
    const contentDiv = document.getElementById('vacation-year-plan-content');

    const allVacations = [];

    if (data.vacationRequests && data.vacationRequests.length > 0) {
        allVacations.push(...data.vacationRequests);
    }

    if (data.absences && data.absences.length > 0) {
        allVacations.push(...data.absences);
    }

    if (allVacations.length === 0) {
        contentDiv.innerHTML = `<p>Keine Urlaube für ${year} vorhanden.</p>`;
        return;
    }

    allVacations.sort((a, b) => new Date(a.startDate) - new Date(b.startDate));

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
// VACATION YEAR APPROVALS (Admin)
// ============================================================================

export async function loadVacationYearApprovals() {
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

export function displayVacationYearApprovals(approvals) {
    const contentDiv = document.getElementById('vacation-year-approvals-content');

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

export async function toggleYearApproval(year, approve) {
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

export async function loadVacationYearApprovalsAbsence() {
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

export function displayVacationYearApprovalsAbsence(approvals) {
    const contentDiv = document.getElementById('vacation-year-approvals-absence-content');

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

export async function toggleYearApprovalAbsence(year, approve) {
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
// ABSENCE TYPES
// ============================================================================

export async function loadAbsenceTypes() {
    try {
        const result = await fetch('/api/absencetypes');
        const absenceTypes = await result.json();

        const content = document.getElementById('absence-types-content');

        if (absenceTypes.length === 0) {
            content.innerHTML = '<p class="info">Keine Abwesenheitstypen definiert.</p>';
            return;
        }

        const systemTypes = absenceTypes.filter(t => t.isSystemType);
        const customTypes = absenceTypes.filter(t => !t.isSystemType);

        let html = '';

        if (systemTypes.length > 0) {
            html += '<h4>Systemtypen (Standard)</h4>';
            html += '<table class="data-table"><thead><tr>';
            html += '<th>Bezeichnung</th>';
            html += '<th>Kürzel</th>';
            html += '<th>Farbe</th>';
            html += '<th>Status</th>';
            html += '</tr></thead><tbody>';

            systemTypes.forEach(type => {
                html += '<tr>';
                html += `<td>${escapeHtml(type.name)}</td>`;
                html += `<td><strong>${escapeHtml(type.code)}</strong></td>`;
                html += `<td><span style="display: inline-block; padding: 4px 12px; background: ${type.colorCode}; border: 1px solid #ccc; border-radius: 4px;">${type.colorCode}</span></td>`;
                html += '<td><span style="color: #666;">Systemtyp (nicht änderbar)</span></td>';
                html += '</tr>';
            });

            html += '</tbody></table><br>';
        }

        if (customTypes.length > 0) {
            html += '<h4>Benutzerdefinierte Typen</h4>';
            html += '<table class="data-table"><thead><tr>';
            html += '<th>Bezeichnung</th>';
            html += '<th>Kürzel</th>';
            html += '<th>Farbe</th>';
            html += '<th>Erstellt</th>';
            html += '<th class="admin-only">Aktionen</th>';
            html += '</tr></thead><tbody>';

            customTypes.forEach(type => {
                html += '<tr>';
                html += `<td>${escapeHtml(type.name)}</td>`;
                html += `<td><strong>${escapeHtml(type.code)}</strong></td>`;
                html += `<td><span style="display: inline-block; padding: 4px 12px; background: ${type.colorCode}; border: 1px solid #ccc; border-radius: 4px;">${type.colorCode}</span></td>`;
                html += `<td>${new Date(type.createdAt).toLocaleDateString('de-DE')}</td>`;
                html += '<td class="admin-only">';
                html += `<button onclick="editAbsenceType(${type.id})" class="btn-secondary btn-small">✏️ Bearbeiten</button> `;
                html += `<button onclick="deleteAbsenceType(${type.id}, ${JSON.stringify(type.name)})" class="btn-danger btn-small">🗑️ Löschen</button>`;
                html += '</td>';
                html += '</tr>';
            });

            html += '</tbody></table>';
        } else {
            html += '<p class="info">Keine benutzerdefinierten Abwesenheitstypen vorhanden. Klicken Sie auf "+ Abwesenheitstyp hinzufügen", um einen zu erstellen.</p>';
        }

        content.innerHTML = html;

    } catch (error) {
        console.error('Error loading absence types:', error);
        document.getElementById('absence-types-content').innerHTML =
            '<p class="error">Fehler beim Laden der Abwesenheitstypen.</p>';
    }
}

export function showAbsenceTypeModal(id = null) {
    const modal = document.getElementById('absenceTypeModal');
    const form = document.getElementById('absenceTypeForm');
    const title = document.getElementById('absenceTypeModalTitle');

    form.reset();
    document.getElementById('absenceTypeId').value = '';
    document.getElementById('absenceTypeColor').value = '#E0E0E0';
    updateAbsenceTypeColorPreview('#E0E0E0');

    if (id) {
        title.textContent = 'Abwesenheitstyp bearbeiten';
        loadAbsenceTypeForEdit(id);
    } else {
        title.textContent = 'Abwesenheitstyp hinzufügen';
    }

    modal.style.display = 'block';
}

export async function loadAbsenceTypeForEdit(id) {
    try {
        const result = await fetch('/api/absencetypes');
        const absenceTypes = await result.json();
        const type = absenceTypes.find(t => t.id === id);

        if (type) {
            document.getElementById('absenceTypeId').value = type.id;
            document.getElementById('absenceTypeName').value = type.name;
            document.getElementById('absenceTypeCode').value = type.code;
            document.getElementById('absenceTypeColor').value = type.colorCode;
            updateAbsenceTypeColorPreview(type.colorCode);
        }
    } catch (error) {
        console.error('Error loading absence type:', error);
        alert('Fehler beim Laden des Abwesenheitstyps');
    }
}

export function closeAbsenceTypeModal() {
    document.getElementById('absenceTypeModal').style.display = 'none';
}

export async function saveAbsenceType(event) {
    event.preventDefault();

    const id = document.getElementById('absenceTypeId').value;
    const data = {
        name: document.getElementById('absenceTypeName').value,
        code: document.getElementById('absenceTypeCode').value.toUpperCase(),
        colorCode: document.getElementById('absenceTypeColor').value
    };

    try {
        const url = id ? `/api/absencetypes/${id}` : '/api/absencetypes';
        const method = id ? 'PUT' : 'POST';

        const result = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (result.ok) {
            closeAbsenceTypeModal();
            loadAbsenceTypes();
            alert(id ? 'Abwesenheitstyp erfolgreich aktualisiert!' : 'Abwesenheitstyp erfolgreich erstellt!');
        } else {
            const error = await result.json();
            alert(error.error || 'Fehler beim Speichern des Abwesenheitstyps');
        }
    } catch (error) {
        console.error('Error saving absence type:', error);
        alert('Fehler beim Speichern des Abwesenheitstyps');
    }
}

export function editAbsenceType(id) {
    showAbsenceTypeModal(id);
}

export async function deleteAbsenceType(id, name) {
    if (!confirm(`Möchten Sie den Abwesenheitstyp "${name}" wirklich löschen?`)) {
        return;
    }

    try {
        const result = await fetch(`/api/absencetypes/${id}`, {
            method: 'DELETE'
        });

        if (result.ok) {
            loadAbsenceTypes();
            alert('Abwesenheitstyp erfolgreich gelöscht!');
        } else {
            const error = await result.json();
            alert(error.error || 'Fehler beim Löschen des Abwesenheitstyps');
        }
    } catch (error) {
        console.error('Error deleting absence type:', error);
        alert('Fehler beim Löschen des Abwesenheitstyps');
    }
}

export function updateAbsenceTypeColorPreview(color) {
    const preview = document.getElementById('absenceTypeColorPreview');
    if (preview) {
        preview.style.backgroundColor = color;
    }
}

export function initAbsenceTypeColorPicker() {
    const colorInput = document.getElementById('absenceTypeColor');
    if (colorInput) {
        colorInput.addEventListener('input', (e) => {
            updateAbsenceTypeColorPreview(e.target.value);
        });
    }
}
