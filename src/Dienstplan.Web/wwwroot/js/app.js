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
    
    if (isAdmin) {
        document.body.classList.add('admin');
        document.getElementById('nav-admin').style.display = 'inline-block';
        document.getElementById('nav-vacations').style.display = 'inline-block';
    } else if (isDisponent) {
        document.body.classList.add('disponent');
        document.getElementById('nav-vacations').style.display = 'inline-block';
    }
}

function updateUIForAnonymousUser() {
    document.getElementById('user-info').style.display = 'none';
    document.getElementById('login-prompt').style.display = 'block';
    currentUser = null;
    userRoles = [];
    document.body.classList.remove('admin', 'disponent');
    document.getElementById('nav-admin').style.display = 'none';
    document.getElementById('nav-vacations').style.display = 'none';
}
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
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('startDate').value = today;
    
    const lastMonth = new Date();
    lastMonth.setMonth(lastMonth.getMonth() - 1);
    document.getElementById('statsStartDate').value = lastMonth.toISOString().split('T')[0];
    document.getElementById('statsEndDate').value = today;
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
    } else if (viewName === 'vacations') {
        loadVacationRequests('all');
    } else if (viewName === 'statistics') {
        loadStatistics();
    } else if (viewName === 'admin') {
        loadAdminView();
    } else if (viewName === 'manual') {
        initializeManualAnchors();
    }
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
function changeDate(days) {
    const dateInput = document.getElementById('startDate');
    const date = new Date(dateInput.value);
    date.setDate(date.getDate() + (days * 7));
    dateInput.value = date.toISOString().split('T')[0];
    loadSchedule();
}

async function loadSchedule() {
    const startDate = document.getElementById('startDate').value;
    const viewType = document.getElementById('viewType').value;
    
    const content = document.getElementById('schedule-content');
    content.innerHTML = '<p class="loading">Lade Dienstplan...</p>';
    
    try {
        const response = await fetch(`${API_BASE}/shifts/schedule?startDate=${startDate}&view=${viewType}`);
        const data = await response.json();
        
        displaySchedule(data);
    } catch (error) {
        content.innerHTML = `<p class="error">Fehler beim Laden: ${error.message}</p>`;
    }
}

function displaySchedule(data) {
    const content = document.getElementById('schedule-content');
    
    if (data.assignments.length === 0) {
        content.innerHTML = '<p>Keine Schichten geplant. Klicken Sie auf "Schichten planen" um automatisch Schichten zu erstellen.</p>';
        return;
    }
    
    // Group by date and employee
    const byDate = {};
    data.assignments.forEach(a => {
        const dateKey = a.date.split('T')[0];
        if (!byDate[dateKey]) byDate[dateKey] = {};
        if (!byDate[dateKey][a.employeeId]) byDate[dateKey][a.employeeId] = [];
        byDate[dateKey][a.employeeId].push(a);
    });
    
    let html = '<table class="schedule-table"><thead><tr><th>Datum</th><th>Mitarbeiter</th><th>Schichten</th></tr></thead><tbody>';
    
    Object.keys(byDate).sort().forEach(date => {
        const dateObj = new Date(date);
        const dayName = dateObj.toLocaleDateString('de-DE', { weekday: 'short', day: '2-digit', month: '2-digit' });
        
        Object.entries(byDate[date]).forEach(([employeeId, shifts]) => {
            const employee = shifts[0].employeeName;
            const shiftBadges = shifts.map(s => 
                `<span class="shift-badge shift-${s.shiftCode}">${s.shiftCode}</span>
                ${s.isSpringerAssignment ? '<span class="springer-badge">Springer</span>' : ''}`
            ).join(' ');
            
            html += `<tr>
                <td>${dayName}</td>
                <td>${employee}</td>
                <td>${shiftBadges}</td>
            </tr>`;
        });
    });
    
    html += '</tbody></table>';
    content.innerHTML = html;
}

async function planShifts() {
    if (!canPlanShifts()) {
        alert('Sie haben keine Berechtigung, Schichten zu planen. Bitte melden Sie sich als Admin oder Disponent an.');
        return;
    }
    
    const startDate = document.getElementById('startDate').value;
    const endDate = new Date(startDate);
    endDate.setDate(endDate.getDate() + 30); // Plan 30 days ahead
    
    const force = confirm('Möchten Sie bestehende Schichten überschreiben?');
    
    try {
        const response = await fetch(
            `${API_BASE}/shifts/plan?startDate=${startDate}&endDate=${endDate.toISOString().split('T')[0]}&force=${force}`,
            { 
                method: 'POST',
                credentials: 'include'
            }
        );
        
        if (response.ok) {
            alert('Schichten erfolgreich geplant!');
            loadSchedule();
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an, um Schichten zu planen.');
        } else if (response.status === 403) {
            alert('Sie haben keine Berechtigung, Schichten zu planen.');
        } else {
            alert('Fehler beim Planen der Schichten');
        }
    } catch (error) {
        alert(`Fehler: ${error.message}`);
    }
}

// PDF Export
async function exportScheduleToPdf() {
    const startDateInput = document.getElementById('startDate');
    const startDate = startDateInput.value;
    
    if (!startDate) {
        alert('Bitte wählen Sie ein Startdatum aus.');
        return;
    }
    
    const viewType = document.getElementById('viewType').value;
    
    // Calculate end date based on view type
    const start = new Date(startDate);
    let end = new Date(startDate);
    
    switch(viewType) {
        case 'week':
            end.setDate(end.getDate() + 7);
            break;
        case 'month':
            end.setMonth(end.getMonth() + 1);
            break;
        case 'year':
            end.setFullYear(end.getFullYear() + 1);
            break;
        default:
            end.setDate(end.getDate() + 7);
    }
    
    const endDate = end.toISOString().split('T')[0];
    
    try {
        // Use fetch to download PDF with authentication
        const response = await fetch(`${API_BASE}/shifts/export/pdf?startDate=${startDate}&endDate=${endDate}`, {
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
        } else {
            alert('Fehler beim PDF-Export. Bitte versuchen Sie es erneut.');
        }
    } catch (error) {
        alert(`Fehler beim PDF-Export: ${error.message}`);
    }
}

// Employee Management
async function loadEmployees() {
    const content = document.getElementById('employees-content');
    content.innerHTML = '<p class="loading">Lade Mitarbeiter...</p>';
    
    try {
        const response = await fetch(`${API_BASE}/employees`);
        const employees = await response.json();
        
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
    
    let html = '<div class="employees-grid">';
    employees.forEach(e => {
        html += `
            <div class="employee-card">
                <h3>${e.vorname} ${e.name}</h3>
                <div class="employee-info">
                    <span><strong>Personalnr:</strong> ${e.personalnummer}</span>
                    <span><strong>Team:</strong> ${e.teamName || 'Kein Team'}</span>
                    ${e.isSpringer ? '<span class="springer-badge">Springer</span>' : ''}
                </div>
            </div>
        `;
    });
    html += '</div>';
    
    content.innerHTML = html;
}

function showAddEmployeeModal() {
    if (!canEditEmployees()) {
        alert('Sie haben keine Berechtigung, Mitarbeiter hinzuzufügen. Bitte melden Sie sich als Admin oder Disponent an.');
        return;
    }
    document.getElementById('employeeModal').classList.add('active');
}

function closeEmployeeModal() {
    document.getElementById('employeeModal').classList.remove('active');
    document.getElementById('employeeForm').reset();
}

async function saveEmployee(event) {
    event.preventDefault();
    
    const employee = {
        vorname: document.getElementById('vorname').value,
        name: document.getElementById('name').value,
        personalnummer: document.getElementById('personalnummer').value,
        isSpringer: document.getElementById('isSpringer').checked
    };
    
    try {
        const response = await fetch(`${API_BASE}/employees`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(employee)
        });
        
        if (response.ok) {
            alert('Mitarbeiter erfolgreich hinzugefügt!');
            closeEmployeeModal();
            loadEmployees();
        } else if (response.status === 401) {
            alert('Bitte melden Sie sich an, um Mitarbeiter hinzuzufügen.');
        } else if (response.status === 403) {
            alert('Sie haben keine Berechtigung, Mitarbeiter hinzuzufügen.');
        } else {
            alert('Fehler beim Speichern');
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
    
    let html = '<div class="grid">';
    teams.forEach(team => {
        html += `
            <div class="card">
                <h3>${team.name}</h3>
                <p>${team.description || 'Keine Beschreibung'}</p>
                <p><strong>E-Mail:</strong> ${team.email || 'Nicht angegeben'}</p>
                <p><strong>Mitarbeiter:</strong> ${team.employeeCount || 0}</p>
            </div>
        `;
    });
    html += '</div>';
    content.innerHTML = html;
}

function showAddTeamModal() {
    alert('Team hinzufügen - Funktion wird implementiert');
}

// Vacation Management Functions
function showVacationTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    document.getElementById(`tab-${tabName}`).classList.add('active');
    
    if (tabName === 'requests') {
        document.getElementById('vacation-requests-tab').classList.add('active');
        loadVacationRequests('all');
    } else if (tabName === 'exchanges') {
        document.getElementById('shift-exchanges-tab').classList.add('active');
        loadShiftExchanges('available');
    }
}

async function loadVacationRequests(filter = 'all') {
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
            const requests = await response.json();
            displayVacationRequests(requests);
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
    
    let html = '<table class="data-table"><thead><tr><th>Mitarbeiter</th><th>Von</th><th>Bis</th><th>Status</th><th>Erstellt</th></tr></thead><tbody>';
    requests.forEach(req => {
        const statusClass = req.status === 'Genehmigt' ? 'success' : req.status === 'NichtGenehmigt' ? 'danger' : 'warning';
        html += `
            <tr>
                <td>${req.employeeName}</td>
                <td>${new Date(req.startDate).toLocaleDateString('de-DE')}</td>
                <td>${new Date(req.endDate).toLocaleDateString('de-DE')}</td>
                <td><span class="badge ${statusClass}">${req.status}</span></td>
                <td>${new Date(req.createdAt).toLocaleDateString('de-DE')}</td>
            </tr>
        `;
    });
    html += '</tbody></table>';
    content.innerHTML = html;
}

function showAddVacationRequestModal() {
    alert('Urlaubsantrag stellen - Funktion wird implementiert');
}

async function loadShiftExchanges(filter = 'available') {
    const content = document.getElementById('shift-exchanges-content');
    content.innerHTML = '<p class="loading">Lade Diensttausch-Angebote...</p>';
    
    try {
        let url = `${API_BASE}/shiftexchanges/${filter}`;
        
        const response = await fetch(url, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const exchanges = await response.json();
            displayShiftExchanges(exchanges);
        } else {
            content.innerHTML = '<p class="error">Fehler beim Laden der Diensttausch-Angebote.</p>';
        }
    } catch (error) {
        console.error('Error loading shift exchanges:', error);
        content.innerHTML = '<p class="error">Fehler beim Laden der Diensttausch-Angebote.</p>';
    }
}

function displayShiftExchanges(exchanges) {
    const content = document.getElementById('shift-exchanges-content');
    
    if (exchanges.length === 0) {
        content.innerHTML = '<p>Keine Diensttausch-Angebote vorhanden.</p>';
        return;
    }
    
    let html = '<table class="data-table"><thead><tr><th>Anbieter</th><th>Schicht-Datum</th><th>Status</th><th>Erstellt</th></tr></thead><tbody>';
    exchanges.forEach(ex => {
        html += `
            <tr>
                <td>${ex.offeringEmployeeName}</td>
                <td>${new Date(ex.shiftDate).toLocaleDateString('de-DE')}</td>
                <td><span class="badge">${ex.status}</span></td>
                <td>${new Date(ex.createdAt).toLocaleDateString('de-DE')}</td>
            </tr>
        `;
    });
    html += '</tbody></table>';
    content.innerHTML = html;
}

function showOfferShiftExchangeModal() {
    alert('Dienst zum Tausch anbieten - Funktion wird implementiert');
}

// Admin View Functions
async function loadAdminView() {
    loadUsers();
    loadEmailSettings();
}

async function loadUsers() {
    const content = document.getElementById('users-content');
    content.innerHTML = '<p class="loading">Lade Benutzer...</p>';
    
    // For now, show a placeholder
    content.innerHTML = `
        <div class="info-box">
            <p>Benutzerverwaltung über die ASP.NET Identity API.</p>
            <p>Verwenden Sie die Identity-Endpunkte um Benutzer zu verwalten.</p>
        </div>
    `;
}

function showAddUserModal() {
    alert('Benutzer hinzufügen - Funktion wird implementiert');
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
        content.innerHTML = '<p class="error">Fehler beim Laden der E-Mail-Einstellungen.</p>';
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
            <p><strong>Status:</strong> <span class="badge success">Aktiv</span></p>
        </div>
    `;
}

function showEmailSettingsModal() {
    alert('E-Mail-Einstellungen bearbeiten - Funktion wird implementiert');
}

function saveGlobalSettings() {
    const maxHoursMonth = document.getElementById('setting-max-hours-month').value;
    const maxHoursWeek = document.getElementById('setting-max-hours-week').value;
    const maxConsecutiveShifts = document.getElementById('setting-max-consecutive-shifts').value;
    const maxConsecutiveNights = document.getElementById('setting-max-consecutive-nights').value;
    
    alert(`Einstellungen gespeichert:\n- Max Stunden/Monat: ${maxHoursMonth}\n- Max Stunden/Woche: ${maxHoursWeek}\n- Max aufeinanderfolgende Schichten: ${maxConsecutiveShifts}\n- Max aufeinanderfolgende Nachtschichten: ${maxConsecutiveNights}`);
}

