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

// ============================================================================
// VIEW NAVIGATION
// ============================================================================

function showView(viewName) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    const viewEl = document.getElementById(`${viewName}-view`);
    if (viewEl) {
        viewEl.classList.add('active');
    }

    const navButtons = document.querySelectorAll('.nav-btn');
    navButtons.forEach(btn => {
        if (btn.getAttribute('onclick') === `showView('${viewName}')`) {
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
    const importEmployeesForm = document.getElementById('importEmployeesForm');
    if (importEmployeesForm) {
        importEmployeesForm.addEventListener('submit', async (e) => {
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
                    body: formData
                });

                const result = await response.json();

                if (response.ok) {
                    resultDiv.innerHTML = utils.formatImportResult(result);
                    setTimeout(() => {
                        employees.loadEmployees();
                        employees.closeImportEmployeesModal();
                    }, 2000);
                } else {
                    resultDiv.innerHTML = `<div class="error-message"><p><strong>✗ Fehler beim Import:</strong></p><p>${result.error || 'Unbekannter Fehler'}</p></div>`;
                }
            } catch (error) {
                console.error('Import error:', error);
                resultDiv.innerHTML = `<div class="error-message"><p><strong>✗ Fehler:</strong></p><p>${error.message}</p></div>`;
            }
        });
    }

    const importTeamsForm = document.getElementById('importTeamsForm');
    if (importTeamsForm) {
        importTeamsForm.addEventListener('submit', async (e) => {
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
                    body: formData
                });

                const result = await response.json();

                if (response.ok) {
                    resultDiv.innerHTML = utils.formatImportResult(result);
                    setTimeout(() => {
                        employees.loadTeams();
                        employees.closeImportTeamsModal();
                    }, 2000);
                } else {
                    resultDiv.innerHTML = `<div class="error-message"><p><strong>✗ Fehler beim Import:</strong></p><p>${result.error || 'Unbekannter Fehler'}</p></div>`;
                }
            } catch (error) {
                console.error('Import error:', error);
                resultDiv.innerHTML = `<div class="error-message"><p><strong>✗ Fehler:</strong></p><p>${error.message}</p></div>`;
            }
        });
    }
}

// ============================================================================
// EXPOSE ALL FUNCTIONS AS GLOBALS (required for HTML inline event handlers)
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

    // Planning Report
    window.loadPlanningReport = planningReport.loadPlanningReport;
    window.exportPlanningReportSummary = planningReport.exportPlanningReportSummary;
    window.closePlanningResultModal = planningReport.closePlanningResultModal;
}

// ============================================================================
// APP INIT
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    registerGlobals();
    schedule.initializeDatePickers();
    absences.initAbsenceTypeColorPicker();
    initImportFormHandlers();
    auth.initPasswordResetCheck();
    auth.checkAuthenticationStatus();
});
