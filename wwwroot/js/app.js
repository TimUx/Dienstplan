// ============================================================================
// MAIN APP MODULE - imports all sub-modules and exposes globals for HTML handlers
// ============================================================================

import * as auth from './modules/auth.js';
import * as employees from './modules/employees.js';
import * as schedule from './modules/schedule.js';
import * as absences from './modules/absences.js';
import * as stats from './modules/statistics.js';
import * as utils from './modules/utils.js';
import { showToast } from './modules/utils.js';
import * as planningReport from './modules/planning_report.js';
import * as audit from './modules/audit.js';

// ============================================================================
// VIEW NAVIGATION - LAZY LOADING
// ============================================================================

const VIEW_PARTIALS = {
    'schedule': '/partials/schedule.html',
    'management': '/partials/management.html',
    'statistics': '/partials/statistics.html',
    'planning-report': '/partials/statistics.html',
    'absences': '/partials/absences.html',
    'shiftexchange': '/partials/absences.html',
    'vacationyearplan': '/partials/absences.html',
    'admin': '/partials/admin.html',
    'manual': '/partials/manual.html',
};

const loadedPartials = new Set();
const trackedShiftSettingsButtons = new WeakSet();
let headerMenuInitialized = false;

function closeHeaderMenu() {
    const headerMenu = document.getElementById('header-menu');
    const menuToggle = document.getElementById('header-menu-toggle');
    if (!headerMenu || !menuToggle) return;

    headerMenu.classList.remove('open');
    menuToggle.setAttribute('aria-expanded', 'false');
}

function initHeaderMenu() {
    if (headerMenuInitialized) return;

    const headerMenu = document.getElementById('header-menu');
    const menuToggle = document.getElementById('header-menu-toggle');
    if (!headerMenu || !menuToggle) return;

    menuToggle.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        const shouldOpen = !headerMenu.classList.contains('open');
        headerMenu.classList.toggle('open', shouldOpen);
        menuToggle.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
    });

    document.addEventListener('click', (event) => {
        if (!headerMenu.classList.contains('open')) return;
        if (headerMenu.contains(event.target)) return;
        closeHeaderMenu();
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeHeaderMenu();
        }
    });

    headerMenuInitialized = true;
}

async function ensurePartialLoaded(partialUrl) {
    if (loadedPartials.has(partialUrl)) return;

    const response = await fetch(partialUrl);
    if (!response.ok) throw new Error(`Failed to load partial: ${partialUrl}`);
    const html = await response.text();
    const container = document.getElementById('view-container');
    container.insertAdjacentHTML('beforeend', html);
    if (partialUrl === '/partials/management.html') {
        bindShiftSettingsJsonButtons();
    }
    loadedPartials.add(partialUrl);
}

function bindShiftSettingsJsonButtons() {
    const handlers = {
        exportShiftSettings: () => employees.exportShiftSettings(),
        showImportShiftSettingsModal: () => employees.showImportShiftSettingsModal(),
    };
    // Build selector from registered handler keys so action names stay in sync.
    const shiftSettingsActionSelector = Object.keys(handlers)
        .map((action) => `[data-action="${action}"]`)
        .join(', ');

    document.querySelectorAll(shiftSettingsActionSelector).forEach((button) => {
        if (trackedShiftSettingsButtons.has(button)) return;

        const action = button.dataset.action;
        const handler = handlers[action];
        if (!handler) return;

        button.addEventListener('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            handler();
        });
        trackedShiftSettingsButtons.add(button);
    });
}

async function showView(viewName) {
    closeHeaderMenu();

    const partialUrl = VIEW_PARTIALS[viewName];
    if (partialUrl) {
        try {
            await ensurePartialLoaded(partialUrl);
        } catch (error) {
            console.error('Could not load view:', viewName, error);
            showToast('Diese Ansicht konnte nicht geladen werden. Bitte Seite neu laden.', 'error');
            return;
        }
    }

    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    const viewEl = document.getElementById(`${viewName}-view`);
    if (viewEl) {
        viewEl.classList.add('active');
    }

    document.querySelectorAll('.nav-btn').forEach(btn => {
        if (btn.getAttribute('data-view') === viewName) {
            btn.classList.add('active');
        }
    });

    if (viewName === 'schedule') {
        schedule.loadSchedule();
    } else if (viewName === 'management') {
        employees.switchManagementTab('employees');
    } else if (viewName === 'employees') {
        showView('management');
        return;
    } else if (viewName === 'teams') {
        showView('management');
        employees.switchManagementTab('teams');
        return;
    } else if (viewName === 'absences') {
        absences.initAbsenceTypeColorPicker();
        absences.switchAbsenceTab('vacation');
    } else if (viewName === 'vacations') {
        showView('absences');
        return;
    } else if (viewName === 'shiftexchange') {
        absences.loadShiftExchanges('available');
    } else if (viewName === 'vacationyearplan') {
        absences.initVacationYearPlan();
        absences.loadVacationYearPlan();
    } else if (viewName === 'statistics') {
        stats.loadStatistics();
    } else if (viewName === 'planning-report') {
        planningReport.initPlanningReport();
        planningReport.loadPlanningReport();
    } else if (viewName === 'admin') {
        loadAdminView();
    } else if (viewName === 'manual') {
        initializeManualAnchors();
    }
}

function loadAdminView() {
    employees.loadAuditLogs(1, 50);
    employees.startAuditLogAutoRefresh(employees.AUDIT_LOG_DEFAULT_REFRESH_INTERVAL);
}

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

// ============================================================================
// IMPORT FORM HANDLERS (DOMContentLoaded)
// ============================================================================

function initImportFormHandlers() {
    document.addEventListener('submit', async (e) => {
        const form = e.target;

        if (form.id === 'importEmployeesForm') {
            e.preventDefault();
            const fileInput = document.getElementById('employeesFile');
            const conflictResolution = document.getElementById('employeesConflictResolution').value;
            const resultDiv = document.getElementById('importEmployeesResult');

            if (!fileInput.files || fileInput.files.length === 0) {
                showToast('Bitte wählen Sie eine CSV-Datei aus.', 'warning');
                return;
            }

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            resultDiv.innerHTML = '<p class="loading">Importiere Mitarbeiter...</p>';

            try {
                const response = await fetch(`${utils.API_BASE}/employees/import/csv?conflict_mode=${conflictResolution}`, {
                    method: 'POST',
                    credentials: 'include',
                    headers: { 'X-CSRF-Token': utils.getCsrfToken() || '' },
                    body: formData
                });
                const result = await response.json();
                if (response.ok) {
                    resultDiv.innerHTML = utils.formatImportResult(result);
                    if (!result.errors || result.errors.length === 0) {
                        setTimeout(() => {
                            employees.loadEmployees();
                            employees.closeImportEmployeesModal();
                        }, 2000);
                    } else {
                        employees.loadEmployees();
                    }
                } else {
                    resultDiv.innerHTML = `<div class="error-message"><p><strong>✗ Fehler beim Import:</strong></p><p>${result.error || 'Unbekannter Fehler'}</p></div>`;
                }
            } catch (error) {
                console.error('Import error:', error);
                resultDiv.innerHTML = `<div class="error-message"><p><strong>✗ Fehler:</strong></p><p>${utils.escapeHtml(error.message)}</p></div>`;
            }
        }

        if (form.id === 'importTeamsForm') {
            e.preventDefault();
            const fileInput = document.getElementById('teamsFile');
            const conflictResolution = document.getElementById('teamsConflictResolution').value;
            const resultDiv = document.getElementById('importTeamsResult');

            if (!fileInput.files || fileInput.files.length === 0) {
                showToast('Bitte wählen Sie eine CSV-Datei aus.', 'warning');
                return;
            }

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            resultDiv.innerHTML = '<p class="loading">Importiere Teams...</p>';

            try {
                const response = await fetch(`${utils.API_BASE}/teams/import/csv?conflict_mode=${conflictResolution}`, {
                    method: 'POST',
                    credentials: 'include',
                    headers: { 'X-CSRF-Token': utils.getCsrfToken() || '' },
                    body: formData
                });
                const result = await response.json();
                if (response.ok) {
                    resultDiv.innerHTML = utils.formatImportResult(result);
                    if (!result.errors || result.errors.length === 0) {
                        setTimeout(() => {
                            employees.loadTeams();
                            employees.closeImportTeamsModal();
                        }, 2000);
                    } else {
                        employees.loadTeams();
                    }
                } else {
                    resultDiv.innerHTML = `<div class="error-message"><p><strong>✗ Fehler beim Import:</strong></p><p>${result.error || 'Unbekannter Fehler'}</p></div>`;
                }
            } catch (error) {
                console.error('Import error:', error);
                resultDiv.innerHTML = `<div class="error-message"><p><strong>✗ Fehler:</strong></p><p>${utils.escapeHtml(error.message)}</p></div>`;
            }
        }

        if (form.id === 'importShiftSettingsForm') {
            e.preventDefault();
            const fileInput = document.getElementById('shiftSettingsFile');
            const conflictResolution = document.getElementById('shiftSettingsConflictResolution').value;
            const resultDiv = document.getElementById('importShiftSettingsResult');

            if (!fileInput.files || fileInput.files.length === 0) {
                showToast('Bitte wählen Sie eine JSON-Datei aus.', 'warning');
                return;
            }

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            resultDiv.innerHTML = '<p class="loading">Importiere Schichteinstellungen...</p>';

            try {
                const response = await fetch(`${utils.API_BASE}/settings/shifts/import?conflict_mode=${conflictResolution}`, {
                    method: 'POST',
                    credentials: 'include',
                    headers: { 'X-CSRF-Token': utils.getCsrfToken() || '' },
                    body: formData
                });
                const result = await response.json();
                if (response.ok) {
                    resultDiv.innerHTML = utils.formatImportResult(result);
                    if (!result.errors || result.errors.length === 0) {
                        setTimeout(() => {
                            employees.loadShiftTypesManagement();
                            employees.loadRotationGroups();
                            employees.closeImportShiftSettingsModal();
                        }, 2000);
                    } else {
                        employees.loadShiftTypesManagement();
                        employees.loadRotationGroups();
                    }
                } else {
                    resultDiv.innerHTML = `<div class="error-message"><p><strong>✗ Fehler beim Import:</strong></p><p>${result.error || 'Unbekannter Fehler'}</p></div>`;
                }
            } catch (error) {
                console.error('Import shift settings error:', error);
                resultDiv.innerHTML = `<div class="error-message"><p><strong>✗ Fehler:</strong></p><p>${utils.escapeHtml(error.message)}</p></div>`;
            }
        }
    });
}

// ============================================================================
// CENTRAL EVENT DELEGATION
// ============================================================================

function buildActionMap() {
    return {
        // Navigation
        'showView': (el) => showView(el.dataset.view),
        'showNotificationModal': () => auth.showNotificationModal(),
        'showChangePasswordModal': () => auth.showChangePasswordModal(),
        'logout': () => auth.logout(),
        'showLoginModal': () => auth.showLoginModal(),

        // Schedule tabs
        'switchScheduleView': (el) => schedule.switchScheduleView(el.dataset.view, el),

        // Schedule controls
        'changeDate': (el) => schedule.changeDate(parseInt(el.dataset.delta, 10)),
        'changeMonth': (el) => schedule.changeMonth(parseInt(el.dataset.delta, 10)),
        'changeYear': (el) => schedule.changeYear(parseInt(el.dataset.delta, 10)),
        'togglePlanApproval': () => schedule.togglePlanApproval(),

        // Schedule actions
        'showPlanShiftsModal': () => schedule.showPlanShiftsModal(),
        'showNewShiftModal': () => schedule.showNewShiftModal(),
        'toggleMultiSelectMode': () => schedule.toggleMultiSelectMode(),
        'showBulkEditModal': () => schedule.showBulkEditModal(),
        'clearShiftSelection': () => schedule.clearShiftSelection(),
        'exportScheduleToCsv': () => schedule.exportScheduleToCsv(),
        'exportScheduleToPdf': () => schedule.exportScheduleToPdf(),
        'exportScheduleToExcel': () => schedule.exportScheduleToExcel(),
        'closePlanShiftsModal': () => schedule.closePlanShiftsModal(),
        'cancelPlanning': () => schedule.cancelPlanning(),
        'closePlanningResultModal': () => planningReport.closePlanningResultModal(),
        'closeEditShiftModal': () => schedule.closeEditShiftModal(),
        'saveShiftAssignment': () => schedule.saveShiftAssignment(),
        'deleteShiftAssignment': () => schedule.deleteShiftAssignment(),
        'closeBulkEditModal': () => schedule.closeBulkEditModal(),
        'saveBulkEdit': () => schedule.saveBulkEdit(),
        'closeQuickEntryModal': () => schedule.closeQuickEntryModal(),
        'saveQuickEntry': () => schedule.saveQuickEntry(),
        'updateQuickEntryOptions': () => schedule.updateQuickEntryOptions(),

        // Management tabs
        'switchManagementTab': (el) => employees.switchManagementTab(el.dataset.tab),
        'switchShiftManagementTab': (el) => employees.switchShiftManagementTab(el.dataset.tab),

        // Employee actions
        'showAddEmployeeModal': () => employees.showAddEmployeeModal(),
        'exportEmployeesCsv': () => employees.exportEmployeesCsv(),
        'showImportEmployeesModal': () => employees.showImportEmployeesModal(),
        'closeImportEmployeesModal': () => employees.closeImportEmployeesModal(),
        'showAddTeamModal': () => employees.showAddTeamModal(),
        'exportTeamsCsv': () => employees.exportTeamsCsv(),
        'showImportTeamsModal': () => employees.showImportTeamsModal(),
        'closeImportTeamsModal': () => employees.closeImportTeamsModal(),
        'showShiftTypeModal': () => employees.showShiftTypeModal(),
        'loadShiftTypesManagement': () => employees.loadShiftTypesManagement(),
        'showRotationGroupModal': () => employees.showRotationGroupModal(),
        'loadRotationGroups': () => employees.loadRotationGroups(),
        'loadGlobalSettings': () => employees.loadGlobalSettings(),
        'saveGlobalSettings': () => employees.saveGlobalSettings(),
        'exportShiftSettings': () => employees.exportShiftSettings(),
        'showImportShiftSettingsModal': () => employees.showImportShiftSettingsModal(),
        'closeImportShiftSettingsModal': () => employees.closeImportShiftSettingsModal(),
        'closeEmployeeModal': () => employees.closeEmployeeModal(),
        'saveEmployee': () => employees.saveEmployee(),
        'closeTeamModal': () => employees.closeTeamModal(),
        'saveTeam': () => employees.saveTeam(),
        'closeShiftTypeModal': () => employees.closeShiftTypeModal(),
        'saveShiftType': () => employees.saveShiftType(),
        'closeShiftTypeTeamsModal': () => employees.closeShiftTypeTeamsModal(),
        'saveShiftTypeTeams': () => employees.saveShiftTypeTeams(),
        'closeRotationGroupModal': () => employees.closeRotationGroupModal(),
        'saveRotationGroup': () => employees.saveRotationGroup(),
        'showAddUserModal': () => employees.showAddUserModal(),
        'closeUserModal': () => employees.closeUserModal(),
        'saveUser': () => employees.saveUser(),
        'showEmailSettingsModal': () => employees.showEmailSettingsModal(),
        'closeEmailSettingsModal': () => employees.closeEmailSettingsModal(),
        'saveEmailSettings': () => employees.saveEmailSettings(),
        'testEmailSettings': () => employees.testEmailSettings(),

        // Admin
        'showAdminTab': (el) => employees.showAdminTab(el.dataset.tab, el),
        'applyAuditFilters': () => employees.applyAuditFilters(),
        'clearAuditFilters': () => employees.clearAuditFilters(),
        'loadAuditLogs': (el) => employees.loadAuditLogs(parseInt(el.dataset.page || '1', 10), parseInt(el.dataset.limit || '50', 10)),
        'loadAuditLogsPreviousPage': () => employees.loadAuditLogsPreviousPage(),
        'loadAuditLogsNextPage': () => employees.loadAuditLogsNextPage(),
        'loadEmailSettings': () => employees.loadEmailSettings(),

        // Statistics
        'loadStatistics': () => stats.loadStatistics(),
        'loadPlanningReport': () => planningReport.loadPlanningReport(),
        'exportPlanningReportSummary': () => planningReport.exportPlanningReportSummary(),

        // Absences
        'switchAbsenceTab': (el) => absences.switchAbsenceTab(el.dataset.tab),
        'showAddVacationRequestModal': () => absences.showAddVacationRequestModal(),
        'loadVacationRequests': (el) => absences.loadVacationRequests(el.dataset.filter),
        'showAddAbsenceModal': (el) => absences.showAddAbsenceModal(el.dataset.type),
        'loadAbsences': (el) => absences.loadAbsences(el.dataset.filter),
        'showVacationPeriodModal': () => absences.showVacationPeriodModal(),
        'loadVacationYearApprovalsAbsence': () => absences.loadVacationYearApprovalsAbsence(),
        'showAbsenceTypeModal': () => absences.showAbsenceTypeModal(),
        'loadAbsenceTypes': () => absences.loadAbsenceTypes(),
        'showOfferShiftExchangeModal': () => absences.showOfferShiftExchangeModal(),
        'loadShiftExchanges': (el) => absences.loadShiftExchanges(el.dataset.filter),
        'loadVacationYearPlan': () => absences.loadVacationYearPlan(),
        'closeVacationRequestModal': () => absences.closeVacationRequestModal(),
        'saveVacationRequest': () => absences.saveVacationRequest(),
        'closeAbsenceModal': () => absences.closeAbsenceModal(),
        'saveAbsence': () => absences.saveAbsence(),
        'closeVacationPeriodModal': () => absences.closeVacationPeriodModal(),
        'saveVacationPeriod': () => absences.saveVacationPeriod(),
        'closeAbsenceTypeModal': () => absences.closeAbsenceTypeModal(),
        'saveAbsenceType': () => absences.saveAbsenceType(),
        'closeShiftExchangeModal': () => absences.closeShiftExchangeModal(),
        'saveShiftExchange': () => absences.saveShiftExchange(),

        // Auth modals
        'closeLoginModal': () => auth.closeLoginModal(),
        'login': () => auth.login(),
        'showForgotPasswordModal': () => auth.showForgotPasswordModal(),
        'closeChangePasswordModal': () => auth.closeChangePasswordModal(),
        'submitChangePassword': () => auth.submitChangePassword(),
        'closeForgotPasswordModal': () => auth.closeForgotPasswordModal(),
        'submitForgotPassword': () => auth.submitForgotPassword(),
        'closeResetPasswordModal': () => auth.closeResetPasswordModal(),
        'submitResetPassword': () => auth.submitResetPassword(),
        'filterNotifications': (el) => auth.filterNotifications(el.dataset.filter),
        'markAllNotificationsRead': () => auth.markAllNotificationsRead(),
        'closeNotificationModal': () => auth.closeNotificationModal(),
    };
}

function initEventDelegation() {
    const actionMap = buildActionMap();

    document.addEventListener('click', (event) => {
        const el = event.target.closest('[data-action]');
        if (!el) return;

        const action = el.dataset.action;
        const handler = actionMap[action];

        if (handler) {
            event.preventDefault();
            handler(el, event);
        } else {
            console.warn(`No handler for action: ${action}`);
        }
    });
}

// ============================================================================
// EXPOSE ALL FUNCTIONS AS GLOBALS (required for dynamically-generated HTML)
// ============================================================================

function registerGlobals() {
    // App-level
    window.showView = showView;

    // Auth
    window.showLoginModal = auth.showLoginModal;
    window.closeLoginModal = auth.closeLoginModal;
    window.login = auth.login;
    window.logout = auth.logout;
    window.showChangePasswordModal = auth.showChangePasswordModal;
    window.closeChangePasswordModal = auth.closeChangePasswordModal;
    window.submitChangePassword = auth.submitChangePassword;
    window.showForgotPasswordModal = auth.showForgotPasswordModal;
    window.closeForgotPasswordModal = auth.closeForgotPasswordModal;
    window.submitForgotPassword = auth.submitForgotPassword;
    window.closeResetPasswordModal = auth.closeResetPasswordModal;
    window.submitResetPassword = auth.submitResetPassword;
    window.showNotificationModal = auth.showNotificationModal;
    window.closeNotificationModal = auth.closeNotificationModal;
    window.filterNotifications = auth.filterNotifications;
    window.markAllNotificationsRead = auth.markAllNotificationsRead;
    window.markNotificationRead = auth.markNotificationRead;

    // Schedule
    window.switchScheduleView = schedule.switchScheduleView;
    window.changeDate = schedule.changeDate;
    window.changeMonth = schedule.changeMonth;
    window.changeYear = schedule.changeYear;
    window.loadSchedule = schedule.loadSchedule;
    window.showPlanShiftsModal = schedule.showPlanShiftsModal;
    window.closePlanShiftsModal = schedule.closePlanShiftsModal;
    window.executePlanShifts = schedule.executePlanShifts;
    window.planShifts = schedule.planShifts;
    window.cancelPlanning = schedule.cancelPlanning;
    window.exportScheduleToPdf = schedule.exportScheduleToPdf;
    window.exportScheduleToExcel = schedule.exportScheduleToExcel;
    window.exportScheduleToCsv = schedule.exportScheduleToCsv;
    window.editShiftAssignment = schedule.editShiftAssignment;
    window.showNewShiftModal = schedule.showNewShiftModal;
    window.closeEditShiftModal = schedule.closeEditShiftModal;
    window.saveShiftAssignment = schedule.saveShiftAssignment;
    window.deleteShiftAssignment = schedule.deleteShiftAssignment;
    window.showQuickEntryModal = schedule.showQuickEntryModal;
    window.updateQuickEntryOptions = schedule.updateQuickEntryOptions;
    window.closeQuickEntryModal = schedule.closeQuickEntryModal;
    window.saveQuickEntry = schedule.saveQuickEntry;
    window.toggleShiftFixed = schedule.toggleShiftFixed;
    window.toggleMultiSelectMode = schedule.toggleMultiSelectMode;
    window.toggleShiftSelection = schedule.toggleShiftSelection;
    window.clearShiftSelection = schedule.clearShiftSelection;
    window.showBulkEditModal = schedule.showBulkEditModal;
    window.closeBulkEditModal = schedule.closeBulkEditModal;
    window.saveBulkEdit = schedule.saveBulkEdit;
    window.togglePlanApproval = schedule.togglePlanApproval;

    // Employees & Teams & Management
    window.loadEmployees = employees.loadEmployees;
    window.showAddEmployeeModal = employees.showAddEmployeeModal;
    window.editEmployee = employees.editEmployee;
    window.deleteEmployee = employees.deleteEmployee;
    window.closeEmployeeModal = employees.closeEmployeeModal;
    window.saveEmployee = employees.saveEmployee;
    window.loadTeams = employees.loadTeams;
    window.showAddTeamModal = employees.showAddTeamModal;
    window.editTeam = employees.editTeam;
    window.deleteTeam = employees.deleteTeam;
    window.closeTeamModal = employees.closeTeamModal;
    window.saveTeam = employees.saveTeam;
    window.exportEmployeesCsv = employees.exportEmployeesCsv;
    window.exportTeamsCsv = employees.exportTeamsCsv;
    window.showImportEmployeesModal = employees.showImportEmployeesModal;
    window.closeImportEmployeesModal = employees.closeImportEmployeesModal;
    window.showImportTeamsModal = employees.showImportTeamsModal;
    window.closeImportTeamsModal = employees.closeImportTeamsModal;
    window.switchManagementTab = employees.switchManagementTab;
    window.switchShiftManagementTab = employees.switchShiftManagementTab;
    window.showShiftTypeModal = employees.showShiftTypeModal;
    window.editShiftType = employees.editShiftType;
    window.closeShiftTypeModal = employees.closeShiftTypeModal;
    window.saveShiftType = employees.saveShiftType;
    window.deleteShiftType = employees.deleteShiftType;
    window.showShiftTypeTeamsModal = employees.showShiftTypeTeamsModal;
    window.closeShiftTypeTeamsModal = employees.closeShiftTypeTeamsModal;
    window.saveShiftTypeTeams = employees.saveShiftTypeTeams;
    window.loadShiftTypesManagement = employees.loadShiftTypesManagement;
    window.loadRotationGroups = employees.loadRotationGroups;
    window.showRotationGroupModal = employees.showRotationGroupModal;
    window.editRotationGroup = employees.editRotationGroup;
    window.deleteRotationGroup = employees.deleteRotationGroup;
    window.closeRotationGroupModal = employees.closeRotationGroupModal;
    window.saveRotationGroup = employees.saveRotationGroup;
    window.addShiftToRotation = employees.addShiftToRotation;
    window.removeShiftFromRotation = employees.removeShiftFromRotation;
    window.loadGlobalSettings = employees.loadGlobalSettings;
    window.saveGlobalSettings = employees.saveGlobalSettings;
    window.exportShiftSettings = employees.exportShiftSettings;
    window.showImportShiftSettingsModal = employees.showImportShiftSettingsModal;
    window.closeImportShiftSettingsModal = employees.closeImportShiftSettingsModal;
    // Admin / Users
    window.showAddUserModal = employees.showAddUserModal;
    window.closeUserModal = employees.closeUserModal;
    window.saveUser = employees.saveUser;
    window.editUser = employees.editUser;
    window.deleteUser = employees.deleteUser;
    window.loadEmailSettings = employees.loadEmailSettings;
    window.showEmailSettingsModal = employees.showEmailSettingsModal;
    window.closeEmailSettingsModal = employees.closeEmailSettingsModal;
    window.saveEmailSettings = employees.saveEmailSettings;
    window.testEmailSettings = employees.testEmailSettings;
    window.showAdminTab = employees.showAdminTab;
    window.loadAuditLogs = employees.loadAuditLogs;
    window.applyAuditFilters = employees.applyAuditFilters;
    window.clearAuditFilters = employees.clearAuditFilters;
    window.loadAuditLogsPreviousPage = employees.loadAuditLogsPreviousPage;
    window.loadAuditLogsNextPage = employees.loadAuditLogsNextPage;

    // Absences
    window.switchAbsenceTab = absences.switchAbsenceTab;
    window.loadVacationRequests = absences.loadVacationRequests;
    window.showAddVacationRequestModal = absences.showAddVacationRequestModal;
    window.closeVacationRequestModal = absences.closeVacationRequestModal;
    window.saveVacationRequest = absences.saveVacationRequest;
    window.processVacationRequest = absences.processVacationRequest;
    window.deleteVacationRequest = absences.deleteVacationRequest;
    window.loadAbsences = absences.loadAbsences;
    window.showAddAbsenceModal = absences.showAddAbsenceModal;
    window.closeAbsenceModal = absences.closeAbsenceModal;
    window.saveAbsence = absences.saveAbsence;
    window.deleteAbsence = absences.deleteAbsence;
    window.loadShiftExchanges = absences.loadShiftExchanges;
    window.showOfferShiftExchangeModal = absences.showOfferShiftExchangeModal;
    window.closeShiftExchangeModal = absences.closeShiftExchangeModal;
    window.saveShiftExchange = absences.saveShiftExchange;
    window.requestShiftExchange = absences.requestShiftExchange;
    window.processShiftExchange = absences.processShiftExchange;
    window.loadVacationPeriods = absences.loadVacationPeriods;
    window.showVacationPeriodModal = absences.showVacationPeriodModal;
    window.editVacationPeriod = absences.editVacationPeriod;
    window.closeVacationPeriodModal = absences.closeVacationPeriodModal;
    window.saveVacationPeriod = absences.saveVacationPeriod;
    window.deleteVacationPeriod = absences.deleteVacationPeriod;
    window.loadVacationYearPlan = absences.loadVacationYearPlan;
    window.loadVacationYearApprovals = absences.loadVacationYearApprovals;
    window.toggleYearApproval = absences.toggleYearApproval;
    window.loadVacationYearApprovalsAbsence = absences.loadVacationYearApprovalsAbsence;
    window.toggleYearApprovalAbsence = absences.toggleYearApprovalAbsence;
    window.loadAbsenceTypes = absences.loadAbsenceTypes;
    window.showAbsenceTypeModal = absences.showAbsenceTypeModal;
    window.closeAbsenceTypeModal = absences.closeAbsenceTypeModal;
    window.saveAbsenceType = absences.saveAbsenceType;
    window.editAbsenceType = absences.editAbsenceType;
    window.deleteAbsenceType = absences.deleteAbsenceType;

    // Statistics
    window.loadStatistics = stats.loadStatistics;
    window.loadAuditLog = audit.loadAuditLog;

    // Planning Report
    window.loadPlanningReport = planningReport.loadPlanningReport;
    window.exportPlanningReportSummary = planningReport.exportPlanningReportSummary;
    window.closePlanningResultModal = planningReport.closePlanningResultModal;
}

// ============================================================================
// APP INIT
// ============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    registerGlobals();
    initHeaderMenu();
    initEventDelegation();
    initImportFormHandlers();
    auth.initPasswordResetCheck();
    auth.checkAuthenticationStatus();

    // Load default view (schedule) immediately
    try {
        await ensurePartialLoaded('/partials/schedule.html');
        const scheduleView = document.getElementById('schedule-view');
        if (scheduleView) {
            scheduleView.classList.add('active');
        }
        schedule.initializeDatePickers();
        absences.initAbsenceTypeColorPicker();
        schedule.loadSchedule();
    } catch (error) {
        console.error('Failed to load initial schedule view:', error);
    }
});
