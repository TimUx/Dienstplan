import { API_BASE, apiCall, escapeHtml } from './utils.js';

export async function loadAuditLog() {
    const container = document.getElementById('audit-log-content');
    if (!container) return;
    
    const entityFilter = document.getElementById('audit-entity-filter')?.value || '';
    const actionFilter = document.getElementById('audit-action-filter')?.value || '';
    const startDate = document.getElementById('audit-start-date')?.value || '';
    const endDate = document.getElementById('audit-end-date')?.value || '';
    
    container.innerHTML = '<p class="loading">Lade Audit-Log...</p>';
    
    try {
        const params = new URLSearchParams({ limit: 100, page: 1 });
        if (entityFilter) params.set('entity_name', entityFilter);
        if (actionFilter) params.set('action', actionFilter);
        if (startDate) params.set('startDate', startDate);
        if (endDate) params.set('endDate', endDate);
        
        const resp = await apiCall(`${API_BASE}/audit-logs?${params}`);
        if (!resp.ok) {
            container.innerHTML = '<p class="error">Fehler beim Laden des Audit-Logs.</p>';
            return;
        }
        const data = await resp.json();
        const logs = data.data || [];
        
        if (logs.length === 0) {
            container.innerHTML = '<p>Keine Eintr\u00e4ge gefunden.</p>';
            return;
        }
        
        container.innerHTML = `
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Zeitstempel</th>
                        <th>Benutzer</th>
                        <th>Entity</th>
                        <th>Aktion</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
                    ${logs.map(log => `
                        <tr>
                            <td>${escapeHtml(log.timestamp || '')}</td>
                            <td>${escapeHtml(log.userName || log.userId || '')}</td>
                            <td>${escapeHtml(log.entityName || '')}</td>
                            <td>${escapeHtml(log.action || '')}</td>
                            <td><small>${escapeHtml(log.changes || '')}</small></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            <p><small>Gesamt: ${data.total} Eintr\u00e4ge (Seite ${data.page}/${data.totalPages})</small></p>
        `;
    } catch (e) {
        container.innerHTML = `<p class="error">Fehler: ${escapeHtml(e.message)}</p>`;
    }
}
