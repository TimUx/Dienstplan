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
}

function updateUIForAnonymousUser() {
    document.getElementById('user-info').style.display = 'none';
    document.getElementById('login-prompt').style.display = 'block';
    currentUser = null;
    userRoles = [];
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
    
    // Add active class to the clicked button
    const buttons = {
        'schedule': 0,
        'employees': 1,
        'statistics': 2,
        'manual': 3
    };
    const buttonIndex = buttons[viewName];
    if (buttonIndex !== undefined) {
        document.querySelectorAll('.nav-btn')[buttonIndex].classList.add('active');
    }
    
    if (viewName === 'schedule') {
        loadSchedule();
    } else if (viewName === 'employees') {
        loadEmployees();
    } else if (viewName === 'statistics') {
        loadStatistics();
    } else if (viewName === 'manual') {
        // Manual view is static HTML, no loading needed
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
    const startDate = document.getElementById('startDate').value;
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
        // Create a link to download the PDF
        const url = `${API_BASE}/shifts/export/pdf?startDate=${startDate}&endDate=${endDate}`;
        window.open(url, '_blank');
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
