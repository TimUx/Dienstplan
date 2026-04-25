import { API_BASE, escapeHtml, showToast } from './utils.js';

// ============================================================================
// PLANNING REPORT
// ============================================================================

const MONTH_NAMES = [
    'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
    'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'
];

const STATUS_CONFIG = {
    OPTIMAL:     { label: 'Optimal geplant',        cssClass: 'report-status-optimal' },
    FEASIBLE:    { label: 'Machbar geplant',         cssClass: 'report-status-optimal' },
    FALLBACK_L1: { label: 'Mit Abweichungen',        cssClass: 'report-status-warning' },
    FALLBACK_L2: { label: 'Mit Abweichungen',        cssClass: 'report-status-warning' },
    EMERGENCY:   { label: 'Notfallplan',             cssClass: 'report-status-emergency' },
};

const SEVERITY_LABELS = {
    HARD:          'Hart',
    SOFT_CRITICAL: 'Kritisch',
    SOFT_MEDIUM:   'Mittel',
    SOFT_LOW:      'Niedrig',
};

function getReportYear() {
    return parseInt(document.getElementById('reportYear').value, 10);
}

function getReportMonth() {
    return parseInt(document.getElementById('reportMonth').value, 10);
}

export async function loadPlanningReport() {
    const year  = getReportYear();
    const month = getReportMonth();
    const content = document.getElementById('planning-report-content');
    content.innerHTML = '<p class="loading">Lade Planungsbericht...</p>';

    try {
        const response = await fetch(`${API_BASE}/planning/report/${year}/${month}`, {
            credentials: 'include'
        });

        if (response.status === 404) {
            content.innerHTML = '<p class="info">Kein Planungsbericht für diesen Monat vorhanden.</p>';
            return;
        }
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            content.innerHTML = `<p class="error">Fehler beim Laden: ${escapeHtml(err.error || response.statusText)}</p>`;
            return;
        }

        const report = await response.json();
        renderReport(report, content);
    } catch (error) {
        content.innerHTML = `<p class="error">Fehler beim Laden: ${escapeHtml(error.message)}</p>`;
    }
}

export async function exportPlanningReportSummary() {
    const year  = getReportYear();
    const month = getReportMonth();

    try {
        const response = await fetch(`${API_BASE}/planning/report/${year}/${month}/summary`, {
            credentials: 'include'
        });

        if (response.status === 404) {
            showToast('Kein Planungsbericht für diesen Monat vorhanden.', 'warning');
            return;
        }
        if (!response.ok) {
            showToast('Fehler beim Abrufen des Berichts.', 'error');
            return;
        }

        const text = await response.text();
        const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement('a');
        a.href     = url;
        a.download = `Planungsbericht_${year}_${String(month).padStart(2, '0')}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (error) {
        showToast(`Fehler beim Export: ${error.message}`, 'error');
    }
}

function renderReport(report, container) {
    let html = '';

    // 1 – Status banner
    html += renderStatusBanner(report);

    // 2 – Summary tiles
    html += renderSummaryTiles(report);

    // 3 – Deviation table
    html += renderDeviationTable(report);

    // 4 – Relaxed constraints
    html += renderRelaxedConstraints(report);

    container.innerHTML = html;
}

function renderStatusBanner(report) {
    const hasHardViolations = (report.rule_violations || []).some(v => v.severity === 'HARD');
    let config = STATUS_CONFIG[report.status] || { label: report.status, cssClass: 'report-status-warning' };

    // Upgrade to emergency banner if there are hard violations regardless of status
    if (hasHardViolations && config.cssClass !== 'report-status-emergency') {
        config = STATUS_CONFIG.EMERGENCY;
    }

    const period = report.planning_period || [];
    const periodStr = period.length === 2
        ? `${formatDate(period[0])} – ${formatDate(period[1])}`
        : '';

    return `
        <div class="report-status-banner ${config.cssClass}">
            <span class="report-status-label">${escapeHtml(config.label)}</span>
            ${periodStr ? `<span class="report-status-period">${escapeHtml(periodStr)}</span>` : ''}
        </div>`;
}

function renderSummaryTiles(report) {
    const totalShifts = Object.values(report.shifts_assigned || {}).reduce((a, b) => a + b, 0);
    const absenceCount = (report.absent_employees || []).length;

    const tiles = [
        { icon: '👥', label: 'Mitarbeiter',        value: report.total_employees ?? '–' },
        { icon: '📋', label: 'Zugewiesene Schichten', value: totalShifts },
        { icon: '🏖️', label: 'Abwesenheiten',       value: absenceCount },
    ];

    let html = '<div class="report-summary-tiles">';
    tiles.forEach(t => {
        html += `
            <div class="report-summary-tile">
                <div class="report-tile-icon">${t.icon}</div>
                <div class="report-tile-value">${escapeHtml(String(t.value))}</div>
                <div class="report-tile-label">${escapeHtml(t.label)}</div>
            </div>`;
    });
    html += '</div>';
    return html;
}

function renderDeviationTable(report) {
    const violations = report.rule_violations || [];
    if (violations.length === 0) {
        return '<div class="stat-card" style="margin-top:20px;"><h3>✅ Abweichungen</h3><p>Keine Regelverstöße.</p></div>';
    }

    let html = `
        <div class="stat-table-container" style="margin-top:20px;">
            <h3>⚠️ Abweichungen (${violations.length})</h3>
            <table class="stat-table">
                <thead>
                    <tr>
                        <th>Datum</th>
                        <th>Regel</th>
                        <th>Schwere</th>
                        <th>Ursache</th>
                        <th>Auswirkung</th>
                    </tr>
                </thead>
                <tbody>`;

    violations.forEach(v => {
        const rowClass = v.severity === 'HARD' ? 'report-violation-hard'
            : (v.severity === 'SOFT_CRITICAL' ? 'report-violation-soft-critical' : '');

        const dates = (v.affected_dates || []).slice(0, 3).map(formatDate).join(', ')
            + ((v.affected_dates || []).length > 3 ? ` (+${v.affected_dates.length - 3})` : '');

        const severityLabel = SEVERITY_LABELS[v.severity] || escapeHtml(v.severity);

        html += `
                    <tr class="${rowClass}">
                        <td>${escapeHtml(dates || '–')}</td>
                        <td><strong>${escapeHtml(v.rule_id || '')}</strong><br><small>${escapeHtml(v.description || '')}</small></td>
                        <td><span class="report-severity-badge report-severity-${(v.severity || '').toLowerCase().replace('_', '-')}">${escapeHtml(severityLabel)}</span></td>
                        <td>${escapeHtml(v.cause || '–')}</td>
                        <td>${escapeHtml(v.impact || '–')}</td>
                    </tr>`;
    });

    html += '</tbody></table></div>';
    return html;
}

function renderRelaxedConstraints(report) {
    const constraints = report.relaxed_constraints || [];

    let html = `
        <div class="stat-card" style="margin-top:20px;">
            <h3>🔧 Entspannte Regeln`;

    if (constraints.length === 0) {
        html += '</h3><p>Alle Planungsregeln wurden vollständig eingehalten.</p></div>';
        return html;
    }

    html += ` (${constraints.length})</h3><ul class="report-relaxed-list">`;
    constraints.forEach(rc => {
        html += `
            <li class="report-relaxed-item">
                <strong>${escapeHtml(rc.constraint_name || '')}</strong>
                <span class="report-relaxed-reason">Grund: ${escapeHtml(rc.reason || '–')}</span>
                ${rc.description ? `<span class="report-relaxed-desc">${escapeHtml(rc.description)}</span>` : ''}
            </li>`;
    });
    html += '</ul></div>';
    return html;
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

export function initPlanningReport() {
    const now = new Date();
    const yearEl  = document.getElementById('reportYear');
    const monthEl = document.getElementById('reportMonth');
    if (yearEl && !yearEl.value)  yearEl.value  = now.getFullYear();
    if (monthEl && !monthEl.value) monthEl.value = now.getMonth() + 1;
}

// ============================================================================
// PLANNING RESULT MODAL (shown automatically after planning completes)
// ============================================================================

export function closePlanningResultModal() {
    document.getElementById('planningResultModal').style.display = 'none';
}

export async function showPlanningResultModal(year, month, periodText) {
    const modal   = document.getElementById('planningResultModal');
    const titleEl = document.getElementById('planningResultTitle');
    const content = document.getElementById('planningResultContent');
    const detailsBtn = document.getElementById('planningResultDetailsBtn');

    titleEl.textContent = `Planung abgeschlossen – ${periodText}`;
    content.innerHTML   = '<p class="loading">Lade Zusammenfassung…</p>';
    modal.style.display = 'block';

    detailsBtn.onclick = () => {
        closePlanningResultModal();
        const yearEl  = document.getElementById('reportYear');
        const monthEl = document.getElementById('reportMonth');
        if (yearEl)  yearEl.value  = year;
        if (monthEl) monthEl.value = month;
        window.showView('planning-report');
    };

    try {
        const response = await fetch(`${API_BASE}/planning/report/${year}/${month}`, {
            credentials: 'include'
        });

        if (!response.ok) {
            content.innerHTML = `<p>Zusammenfassung konnte nicht geladen werden (Status: ${escapeHtml(String(response.status))}).</p>`;
            return;
        }

        const report = await response.json();
        content.innerHTML = renderResultSummary(report);
    } catch (_err) {
        content.innerHTML = '<p>Zusammenfassung konnte nicht geladen werden. Bitte überprüfen Sie Ihre Verbindung.</p>';
    }
}

function getResultStatusConfig(status, violations) {
    const hasHard = (violations || []).some(v => v.severity === 'HARD');
    if (hasHard || status === 'EMERGENCY') {
        return { icon: '🚨', label: 'Notfallplan', cssClass: 'planning-result-status-emergency' };
    }
    if (status === 'OPTIMAL' || status === 'FEASIBLE') {
        return { icon: '✅', label: 'Optimal geplant', cssClass: 'planning-result-status-optimal' };
    }
    return { icon: '⚠️', label: 'Mit Abweichungen', cssClass: 'planning-result-status-warning' };
}

function renderResultSummary(report) {
    const violations  = report.rule_violations || [];
    const totalShifts = Object.values(report.shifts_assigned || {}).reduce((a, b) => a + b, 0);
    const absenceCount = (report.absent_employees || []).length;
    const cfg = getResultStatusConfig(report.status, violations);

    let html = '';

    html += `<div class="planning-result-status ${escapeHtml(cfg.cssClass)}">${cfg.icon} ${escapeHtml(cfg.label)}</div>`;

    html += '<div class="planning-result-summary">';
    html += `<p>👥 ${escapeHtml(String(report.total_employees ?? 0))} Mitarbeiter berücksichtigt</p>`;
    html += `<p>📋 ${escapeHtml(String(totalShifts))} Schichten erfolgreich vergeben</p>`;
    if (absenceCount > 0) {
        html += `<p>🏖️ ${escapeHtml(String(absenceCount))} Abwesenheit${absenceCount !== 1 ? 'en' : ''} berücksichtigt</p>`;
    }
    if (violations.length > 0) {
        html += `<p>⚠️ ${escapeHtml(String(violations.length))} Regelabweichung${violations.length !== 1 ? 'en' : ''} festgestellt</p>`;
    } else {
        html += '<p>✅ Alle Regeln vollständig eingehalten</p>';
    }
    const relaxedCount = (report.relaxed_constraints || []).length;
    if (relaxedCount > 0) {
        html += `<p>🔧 ${escapeHtml(String(relaxedCount))} Regel${relaxedCount !== 1 ? 'n' : ''} entspannt</p>`;
    }
    html += '</div>';

    if (violations.length > 0) {
        html += '<div class="planning-result-violations"><h4>Wichtigste Regelabweichungen</h4><ul>';
        violations.slice(0, 5).forEach(v => {
            html += `<li>${escapeHtml(v.description || v.rule_id || 'Unbekannte Regel')}</li>`;
        });
        if (violations.length > 5) {
            html += `<li class="planning-result-more">… und ${escapeHtml(String(violations.length - 5))} weitere</li>`;
        }
        html += '</ul></div>';
    }

    return html;
}
