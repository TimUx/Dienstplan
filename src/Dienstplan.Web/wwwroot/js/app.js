// API Base URL
const API_BASE = window.location.origin + '/api';

// State
let currentDate = new Date();
let currentView = 'week';

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    initializeDatePickers();
    loadSchedule();
});

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
    event.target.classList.add('active');
    
    if (viewName === 'schedule') {
        loadSchedule();
    } else if (viewName === 'employees') {
        loadEmployees();
    } else if (viewName === 'statistics') {
        loadStatistics();
    }
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
    const startDate = document.getElementById('startDate').value;
    const endDate = new Date(startDate);
    endDate.setDate(endDate.getDate() + 30); // Plan 30 days ahead
    
    const force = confirm('Möchten Sie bestehende Schichten überschreiben?');
    
    try {
        const response = await fetch(
            `${API_BASE}/shifts/plan?startDate=${startDate}&endDate=${endDate.toISOString().split('T')[0]}&force=${force}`,
            { method: 'POST' }
        );
        
        if (response.ok) {
            alert('Schichten erfolgreich geplant!');
            loadSchedule();
        } else {
            alert('Fehler beim Planen der Schichten');
        }
    } catch (error) {
        alert(`Fehler: ${error.message}`);
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
            body: JSON.stringify(employee)
        });
        
        if (response.ok) {
            alert('Mitarbeiter erfolgreich hinzugefügt!');
            closeEmployeeModal();
            loadEmployees();
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
