import { API_BASE, escapeHtml } from './utils.js';

// ============================================================================
// STATISTICS
// ============================================================================

export async function loadStatistics() {
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

export function displayStatistics(stats) {
    const content = document.getElementById('statistics-content');

    let html = '<div class="statistics-grid">';

    // Work Hours
    html += '<div class="stat-card"><h3>⏱️ Arbeitsstunden</h3>';
    stats.employeeWorkHours.forEach(e => {
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
    html += '<div class="stat-card"><h3>📅 Abwesenheiten</h3>';
    stats.employeeAbsenceDays.forEach(e => {
        const typeNames = {
            'AU': 'Krank/AU',
            'U': 'Urlaub',
            'L': 'Lehrgang'
        };

        let typeBreakdown = '';
        if (e.byType) {
            const types = Object.entries(e.byType)
                .map(([type, days]) => `${typeNames[type] || type}: ${days}`)
                .join(', ');
            typeBreakdown = types ? ` (${types})` : '';
        }

        html += `<div class="stat-item">
            <span>${e.employeeName}</span>
            <span>${e.totalDays} Tage${typeBreakdown}</span>
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

    // Employee Shift Details Table
    if (stats.employeeShiftDetails && stats.employeeShiftDetails.length > 0) {
        html += '<div class="stat-table-container">';
        html += '<h3>👤 Detaillierte Schichtübersicht pro Mitarbeiter</h3>';
        html += '<table class="stat-table">';
        html += '<thead><tr>';
        html += '<th>Mitarbeiter</th>';

        const allShiftTypes = new Set();
        stats.employeeShiftDetails.forEach(emp => {
            Object.keys(emp.shiftTypes).forEach(code => allShiftTypes.add(code));
        });
        const sortedShiftTypes = Array.from(allShiftTypes).sort();

        sortedShiftTypes.forEach(code => {
            html += `<th>${escapeHtml(code)}</th>`;
        });

        html += '<th class="stat-highlight">Samstage</th>';
        html += '<th class="stat-highlight">Sonntage</th>';
        html += '</tr></thead>';
        html += '<tbody>';

        stats.employeeShiftDetails.forEach(emp => {
            html += '<tr>';
            html += `<td><strong>${escapeHtml(emp.employeeName)}</strong></td>`;

            sortedShiftTypes.forEach(code => {
                const days = emp.shiftTypes[code] ? emp.shiftTypes[code].days : 0;
                html += `<td class="stat-number">${days}</td>`;
            });

            html += `<td class="stat-number stat-highlight">${emp.totalSaturdays}</td>`;
            html += `<td class="stat-number stat-highlight">${emp.totalSundays}</td>`;
            html += '</tr>';
        });

        html += '</tbody></table>';
        html += '</div>';
    }

    content.innerHTML = html;
}
